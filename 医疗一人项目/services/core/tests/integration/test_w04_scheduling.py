from __future__ import annotations

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
