from __future__ import annotations

import os
import select as select_module
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.budgets import BudgetService
from medical_one_person.application.errors import (
    BudgetExceededError,
    ConflictingOperationError,
    LeaseConflictError,
    TaskDependencyError,
    TaskNotReadyError,
)
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.application.tasks import TaskService
from medical_one_person.application.worker_loop import WorkerLoop
from medical_one_person.domain.tasks import InputValidity, TaskState
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentRun,
    Budget,
    BudgetLedgerEntry,
    Job,
    OutboxMessage,
    Task,
    TaskAttempt,
    TaskVersion,
)
from medical_one_person.providers import FakeModelProvider

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _project(
    session_factory: sessionmaker[Session],
    *,
    name: str = "W04项目",
    idempotency_key: str = "create-w04-project",
):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name=name,
        scope="W04合成调度测试。",
        idempotency_key=idempotency_key,
    )
    return identity, project


def _task(
    service: TaskService,
    *,
    actor_user_id: UUID,
    project_id: UUID,
    purpose: str,
    dependencies: tuple[UUID, ...] = (),
):
    return service.create_task(
        project_id=project_id,
        actor_user_id=actor_user_id,
        task_type="synthetic.review",
        purpose=purpose,
        assignee_role="A26",
        role_version="A26.v1",
        input_version=f"input:{purpose}",
        input_refs=[f"fixture:{purpose}"],
        goal="生成合成审核产物。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
        dependencies=dependencies,
    )


class _FailFirstProvider(FakeModelProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def generate_structured(self, request):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("synthetic provider outage")
        return super().generate_structured(request)


class _CountingProvider(FakeModelProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def generate_structured(self, request):
        self.calls += 1
        return super().generate_structured(request)


class _CountingFailQueue(JobQueue):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__(session_factory)
        self.fail_calls = 0

    def fail(self, **kwargs):
        self.fail_calls += 1
        return super().fail(**kwargs)


class _CrashBeforeCompleteQueue(JobQueue):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__(session_factory)
        self.crash_once = True

    def complete(self, **kwargs):
        if self.crash_once:
            self.crash_once = False
            raise RuntimeError("synthetic worker crash before job completion")
        return super().complete(**kwargs)


def test_task_dependency_cycle_queue_dedup_and_no_auto_acceptance(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(session_factory)
    tasks = TaskService(session_factory)
    upstream = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="upstream",
    )
    dependent = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="dependent",
        dependencies=(upstream.id,),
    )
    assert upstream.state == TaskState.READY
    assert upstream.input_validity == InputValidity.CURRENT
    assert upstream.input_snapshot_sha256 is not None
    assert dependent.state == TaskState.NEEDS_INPUT

    duplicate = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="upstream",
    )
    assert duplicate.id == upstream.id

    with pytest.raises(TaskDependencyError, match="cycle"):
        tasks.add_dependency(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_id=upstream.id,
            depends_on_task_id=dependent.id,
        )
    with pytest.raises(TaskNotReadyError, match="not ready"):
        tasks.enqueue(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_id=dependent.id,
        )

    queued = tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=upstream.id,
    )
    replay = tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=upstream.id,
    )
    assert queued.state == TaskState.QUEUED
    assert replay == queued

    dispatcher = OutboxDispatcher(session_factory)
    first_jobs = dispatcher.dispatch_once(workspace_id=identity.workspace_id)
    second_jobs = dispatcher.dispatch_once(workspace_id=identity.workspace_id)
    assert len(first_jobs) == 1
    assert second_jobs == []

    queue = JobQueue(session_factory)
    claim = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-1")
    assert claim is not None
    submitted = tasks.submit_for_review(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=upstream.id,
        expected_revision=claim.task_revision,
    )
    assert submitted.state == TaskState.SUBMITTED
    assert submitted.state != TaskState.ACCEPTED
    queue.complete(workspace_id=identity.workspace_id, claim=claim)

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(OutboxMessage)) == 1
        assert session.scalar(select(func.count()).select_from(Job)) == 1


def test_upstream_change_reopens_ready_dependents(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="上游变更项目",
        idempotency_key="create-invalidation-project",
    )
    tasks = TaskService(session_factory)
    upstream = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="approve-upstream",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        upstream_model = session.get(Task, upstream.id)
        assert upstream_model is not None
        upstream_model.state = TaskState.ACCEPTED.value

    dependent = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="downstream",
        dependencies=(upstream.id,),
    )
    assert dependent.state == TaskState.READY

    invalidated = tasks.invalidate_dependents(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        upstream_task_id=upstream.id,
    )
    assert invalidated == [dependent.id]
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        refreshed = session.get(Task, dependent.id)
        assert refreshed is not None
        assert refreshed.state == TaskState.NEEDS_INPUT.value
        assert refreshed.input_validity == InputValidity.STALE.value
        assert refreshed.input_invalidated_reason == f"UPSTREAM_TASK_CHANGED:{upstream.id}"
        stale_revision = refreshed.revision
    revised = tasks.revise_inputs(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=dependent.id,
        expected_revision=stale_revision,
        input_version="input:v2",
        input_refs=[f"fixture:{dependent.id}:v2"],
    )
    assert revised.state == TaskState.READY
    assert revised.input_validity == InputValidity.CURRENT
    assert revised.input_snapshot_sha256 != dependent.input_snapshot_sha256
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        versions = session.scalars(
            select(TaskVersion)
            .where(TaskVersion.task_id == dependent.id)
            .order_by(TaskVersion.task_revision)
        ).all()
    assert [item.state for item in versions] == [
        "ready",
        "needs_input",
        "ready",
    ]
    assert [item.input_validity for item in versions] == [
        "current",
        "stale",
        "current",
    ]


def test_stale_input_is_cancelled_at_scheduler_claim(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="输入失效调度项目",
        idempotency_key="create-stale-scheduler-project",
    )
    tasks = TaskService(session_factory)
    task = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="stale-claim",
    )
    queued = tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    assert queued.state == TaskState.QUEUED
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored = session.get(Task, task.id)
        assert stored is not None
        stored.input_validity = "stale"
        stored.input_invalidated_reason = "SYNTHETIC_STALE_INPUT"
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    claim = JobQueue(session_factory).claim(
        workspace_id=identity.workspace_id,
        worker_id="stale-worker",
    )
    assert claim is None
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        job = session.scalar(select(Job).where(Job.task_id == task.id))
        assert job is not None
        assert job.state == "cancelled"
        assert job.last_error_code == "TASK_INPUT_STALE"


def test_budget_reservation_is_atomic_and_settlement_is_idempotent(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="预算并发项目",
        idempotency_key="create-budget-project",
    )
    budgets = BudgetService(session_factory)
    budget = budgets.create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        name="研究预算",
        currency="CNY",
        limit_amount=Decimal("10"),
    )
    barrier = Barrier(2)

    def reserve(key: str):
        barrier.wait()
        return budgets.reserve(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            budget_id=budget.id,
            amount=Decimal("7"),
            operation_key=key,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reserve, "reserve-a"), pool.submit(reserve, "reserve-b")]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except BudgetExceededError as exc:
            outcomes.append(exc)
    reservations = [result for result in outcomes if not isinstance(result, Exception)]
    assert len(reservations) == 1
    assert sum(isinstance(result, BudgetExceededError) for result in outcomes) == 1

    reservation = reservations[0]
    settled = budgets.settle(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        reservation_id=reservation.id,
        actual_amount=Decimal("5"),
        ledger_key="settle-a",
    )
    replay = budgets.settle(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        reservation_id=reservation.id,
        actual_amount=Decimal("5"),
        ledger_key="settle-a",
    )
    assert settled.state.value == "settled"
    assert replay == settled
    with pytest.raises(ConflictingOperationError):
        budgets.settle(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            reservation_id=reservation.id,
            actual_amount=Decimal("5"),
            ledger_key="settle-b",
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored_budget = session.get(Budget, budget.id)
        assert stored_budget is not None
        assert stored_budget.reserved_amount == Decimal("0")
        assert stored_budget.spent_amount == Decimal("5")
        assert (
            session.scalar(
                select(func.count())
                .select_from(BudgetLedgerEntry)
                .where(BudgetLedgerEntry.kind == "settle")
            )
            == 1
        )

    with pytest.raises(ValueError, match="positive"):
        budgets.reserve(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            budget_id=budget.id,
            amount=Decimal("0"),
            operation_key="unknown-zero",
        )


def test_lease_expiry_rejects_late_worker_and_recovery_reclaims_job(
    session_factory: sessionmaker[Session],
    app_database,
) -> None:
    identity, project = _project(
        session_factory,
        name="租约恢复项目",
        idempotency_key="create-lease-project",
    )
    tasks = TaskService(session_factory)
    task = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="lease",
    )
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)

    queue = JobQueue(session_factory)
    first = queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="worker-old",
        lease_seconds=30,
    )
    assert first is not None

    app_database.dispose()
    restarted_factory = sessionmaker(bind=app_database, expire_on_commit=False)
    restarted_queue = JobQueue(restarted_factory)
    assert (
        restarted_queue.claim(
            workspace_id=identity.workspace_id,
            worker_id="worker-before-expiry",
        )
        is None
    )

    with restarted_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=None)
        job = session.get(Job, first.job_id)
        assert job is not None
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)

    second = restarted_queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="worker-new",
        lease_seconds=30,
    )
    assert second is not None
    assert second.fence_token == first.fence_token + 1
    assert second.attempt_number == 2
    with pytest.raises(LeaseConflictError):
        restarted_queue.complete(workspace_id=identity.workspace_id, claim=first)
    restarted_queue.complete(workspace_id=identity.workspace_id, claim=second)

    with restarted_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=None)
        attempts = session.scalars(select(TaskAttempt).order_by(TaskAttempt.attempt_number)).all()
        assert [attempt.state for attempt in attempts] == ["interrupted", "succeeded"]


def test_429_is_retried_without_duplicate_attempt_side_effect(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="重试项目",
        idempotency_key="create-retry-project",
    )
    tasks = TaskService(session_factory)
    task = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="rate-limit",
    )
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)

    first = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-a")
    assert first is not None
    state = queue.fail(
        workspace_id=identity.workspace_id,
        claim=first,
        error_code="RATE_LIMITED",
        retryable=True,
        retry_delay_seconds=0,
    )
    assert state == "queued"
    second = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-b")
    assert second is not None
    assert second.attempt_number == 2
    assert second.fence_token == first.fence_token + 1
    queue.complete(workspace_id=identity.workspace_id, claim=second)

    with pytest.raises(LeaseConflictError):
        queue.complete(workspace_id=identity.workspace_id, claim=second)


def test_durable_worker_loop_dispatches_claims_runs_and_submits(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="后台worker项目",
        idempotency_key="create-worker-project",
    )
    tasks = TaskService(session_factory)
    task = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="worker-loop",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored = session.get(Task, task.id)
        assert stored is not None
        stored.role_version = "1"
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    worker = WorkerLoop(
        session_factory,
        FakeModelProvider(),
        load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml"),
        theory_hash="0" * 64,
        worker_id="w04-test-worker",
    )
    result = worker.run_once(workspace_id=identity.workspace_id)
    assert result.claimed_job_id is not None
    assert result.task_id == task.id
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        refreshed = session.get(Task, task.id)
        assert refreshed is not None
        assert refreshed.state == TaskState.SUBMITTED.value


def test_worker_continues_after_one_task_failure_and_settles_once(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="worker故障隔离",
        idempotency_key="create-worker-failure-project",
    )
    tasks = TaskService(session_factory)
    failing = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="provider-failure",
    )
    succeeding = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="after-failure",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        for task_id in (failing.id, succeeding.id):
            row = session.get(Task, task_id)
            assert row is not None
            row.role_version = "1"
            row.max_attempts = 1
    for task_id in (failing.id, succeeding.id):
        tasks.enqueue(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            task_id=task_id,
        )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)

    queue = _CountingFailQueue(session_factory)
    provider = _FailFirstProvider()
    worker = WorkerLoop(
        session_factory,
        provider,
        load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml"),
        theory_hash="1" * 64,
        worker_id="w04-failure-isolation",
        job_queue=queue,
    )
    failed = worker.run_once(workspace_id=identity.workspace_id)
    assert failed.task_id == failing.id
    assert failed.failure_code == "PROVIDER_ERROR"
    assert queue.fail_calls == 1
    recovered = worker.run_once(workspace_id=identity.workspace_id)
    assert recovered.task_id == succeeding.id
    assert recovered.failure_code is None

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        failed_task = session.get(Task, failing.id)
        failed_job = session.scalar(select(Job).where(Job.task_id == failing.id))
        successful_task = session.get(Task, succeeding.id)
        failed_attempt = session.scalar(
            select(TaskAttempt).where(TaskAttempt.task_id == failing.id)
        )
    assert failed_task is not None and failed_task.state == TaskState.FAILED.value
    assert failed_job is not None and failed_job.state == "dead"
    assert failed_job.last_error_code == "PROVIDER_ERROR"
    assert failed_attempt is not None
    assert failed_attempt.state == "failed"
    assert failed_attempt.error_code == "PROVIDER_ERROR"
    assert successful_task is not None
    assert successful_task.state == TaskState.SUBMITTED.value


def test_successful_run_is_reused_after_lease_recovery_changes_revision(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="worker恢复幂等",
        idempotency_key="create-worker-recovery-project",
    )
    tasks = TaskService(session_factory)
    task = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="recover-before-complete",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        row = session.get(Task, task.id)
        assert row is not None
        row.role_version = "1"
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = _CrashBeforeCompleteQueue(session_factory)
    provider = _CountingProvider()
    runner = AgentRunner(
        session_factory,
        provider,
        load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml"),
        theory_hash="2" * 64,
        job_queue=queue,
    )
    first = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-crash")
    assert first is not None
    with pytest.raises(RuntimeError, match="synthetic worker crash"):
        runner.run_claim(first)
    assert provider.calls == 1

    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=None)
        job = session.get(Job, first.job_id)
        assert job is not None
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    assert queue.recover_expired(workspace_id=identity.workspace_id) == 1
    second = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-recovered")
    assert second is not None
    assert second.task_revision != first.task_revision
    runner.run_claim(second)
    assert provider.calls == 1
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        recovered_task = session.get(Task, task.id)
        job = session.get(Job, first.job_id)
    assert recovered_task is not None
    assert recovered_task.state == TaskState.SUBMITTED.value
    assert job is not None and job.state == "succeeded"


def test_late_worker_cannot_persist_success_after_fence_takeover(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(
        session_factory,
        name="worker fencing",
        idempotency_key="create-worker-fencing-project",
    )
    tasks = TaskService(session_factory)
    task = _task(
        tasks,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        purpose="late-worker-write",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        row = session.get(Task, task.id)
        assert row is not None
        row.role_version = "1"
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    stale = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-stale")
    assert stale is not None
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=None)
        job = session.get(Job, stale.job_id)
        assert job is not None
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    current = queue.claim(workspace_id=identity.workspace_id, worker_id="worker-current")
    assert current is not None
    assert current.fence_token == stale.fence_token + 1

    provider = _CountingProvider()
    runner = AgentRunner(
        session_factory,
        provider,
        load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml"),
        theory_hash="3" * 64,
        job_queue=queue,
    )
    with pytest.raises(LeaseConflictError, match="owned by another worker"):
        runner.run_claim(stale)
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        run = session.scalar(select(AgentRun).where(AgentRun.task_id == task.id))
    assert run is not None
    assert run.state == "running"
    assert run.output is None

    runner.run_claim(current)
    assert provider.calls == 2
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        run = session.scalar(select(AgentRun).where(AgentRun.task_id == task.id))
    assert run is not None and run.state == "succeeded"


def test_worker_cli_discovers_workspace_and_exits_cleanly(
    session_factory: sessionmaker[Session],
    app_database_url: str,
) -> None:
    identity, _project_value = _project(
        session_factory,
        name="worker CLI自动发现",
        idempotency_key="create-worker-cli-project",
    )
    env = os.environ.copy()
    env["MEDICAL_ONE_DATABASE_URL"] = app_database_url
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("MEDICAL_ONE_WORKSPACE_ID", None)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "medical_one_person.worker",
            "--poll-seconds",
            "0.1",
        ],
        cwd=PROJECT_ROOT / "services" / "core",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        deadline = time.monotonic() + 15
        started = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            ready, _, _ = select_module.select([process.stdout], [], [], 0.1)
            if not ready:
                continue
            line = process.stdout.readline()
            if "mock worker started" in line:
                started = True
                break
        assert started, process.stderr.read() if process.poll() is not None else "startup timeout"
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    assert process.returncode == 0, stderr
    assert identity.workspace_id
    assert "mock worker stopped" in stdout
