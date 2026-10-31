from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.errors import (
    ConflictingOperationError,
    PlanStateError,
    ReviewPolicyError,
    TaskNotReadyError,
)
from medical_one_person.application.opportunities import OpportunityService
from medical_one_person.application.plans import PlanService
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.domain.opportunities import OpportunityCard
from medical_one_person.domain.plans import (
    FindingSeverity,
    PlanSpec,
    PlanStatus,
    ReviewDecision,
    ReviewFinding,
)
from medical_one_person.domain.tasks import TaskState
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    OutboxMessage,
    Plan,
    Task,
    TaskReview,
)
from medical_one_person.providers import FakeModelProvider

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _roles():
    return load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml")


def _setup(session_factory: sessionmaker[Session]):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W11 计划与审核项目",
        scope="验证有界DAG、派工、独立审核、退回和暂停，不执行外部动作。",
        idempotency_key="create-w11-project",
    )
    fixture = json.loads(
        (PROJECT_ROOT / "fixtures" / "opportunity-contract-examples.json").read_text(
            encoding="utf-8"
        )
    )
    opportunity = OpportunityService(session_factory).create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        card=OpportunityCard.model_validate(fixture["opportunities"][0]),
    )
    decision = OpportunityService(session_factory).select_opportunity(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        opportunity_id=opportunity.id,
        expected_revision=opportunity.revision,
        reason="仅用于W11合成流程测试。",
        scope="只做mock桌面流程，不授权外联、采购或实验。",
        evidence_version_ids=[],
        idempotency_key="w11-select-opportunity",
    )
    return identity, project, decision.decision_id


def _spec(*, max_rework_rounds: int = 3, with_audit: bool = True) -> PlanSpec:
    nodes = [
        {
            "key": "research",
            "task_type": "scientific.core_review",
            "purpose": "w11-research",
            "assignee_role": "A02",
            "role_version": "1",
            "input_version": "selection-v1",
            "input_refs": ["fixture:w11-selection"],
            "goal": "形成合成科学核查草案并明确未知。",
            "deliverable_schema": "agent_delivery.v1",
            "acceptance_policy": "independent_review.v1",
        }
    ]
    if with_audit:
        nodes.append(
            {
                "key": "audit",
                "task_type": "scientific.audit",
                "purpose": "w11-audit",
                "assignee_role": "A26",
                "role_version": "1",
                "input_version": "selection-v1",
                "input_refs": ["fixture:w11-selection"],
                "goal": "独立检查合成草案的反证与限制。",
                "deliverable_schema": "agent_delivery.v1",
                "acceptance_policy": "independent_review.v1",
                "depends_on": ["research"],
            }
        )
    return PlanSpec.model_validate(
        {
            "title": "W11有界核查计划",
            "objective": "只验证计划、派工、审核和退回合同。",
            "nodes": nodes,
            "max_rework_rounds": max_rework_rounds,
        }
    )


def _run_ready_task(
    session_factory: sessionmaker[Session],
    *,
    workspace_id: UUID,
    worker_name: str,
):
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=workspace_id)
    queue = JobQueue(session_factory)
    claim = queue.claim(
        workspace_id=workspace_id,
        worker_id=worker_name,
        lease_seconds=60,
    )
    assert claim is not None
    runner = AgentRunner(
        session_factory,
        FakeModelProvider(),
        _roles(),
        theory_hash="d" * 64,
        job_queue=queue,
    )
    runner.run_claim(claim)


def _task_in_plan(
    session_factory: sessionmaker[Session],
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    task_id: UUID,
) -> Task:
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=workspace_id, user_id=actor_user_id)
        task = session.get(Task, task_id)
        assert task is not None
        session.expunge(task)
        return task


def test_plan_dag_dispatch_independent_review_and_unlock(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, decision_id = _setup(session_factory)
    service = PlanService(session_factory, _roles())
    submitted = service.submit_plan(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        source_decision_id=decision_id,
        spec=_spec(),
        idempotency_key="w11-plan",
    )
    replay = service.submit_plan(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        source_decision_id=decision_id,
        spec=_spec(),
        idempotency_key="w11-plan",
    )
    assert replay == submitted
    assert submitted.status == PlanStatus.DRAFT
    assert len(submitted.nodes) == 2
    research = next(node for node in submitted.nodes if node.node_key == "research")
    audit = next(node for node in submitted.nodes if node.node_key == "audit")
    assert research.task_state == "ready"
    assert audit.task_state == "needs_input"

    with pytest.raises(ConflictingOperationError):
        service.submit_plan(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            source_decision_id=decision_id,
            spec=_spec(max_rework_rounds=2),
            idempotency_key="w11-plan",
        )

    activated = service.activate_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=submitted.revision,
    )
    assert activated.status == PlanStatus.ACTIVE
    dispatched = service.dispatch_plan(
        project_id=project.id,
        plan_id=activated.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=activated.revision,
    )
    assert [item.node_key for item in dispatched.dispatched] == ["research"]

    _run_ready_task(
        session_factory,
        workspace_id=identity.workspace_id,
        worker_name="w11-worker-research",
    )
    research_task = _task_in_plan(
        session_factory,
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=research.task_id,
    )
    assert research_task.state == TaskState.SUBMITTED

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored = session.get(Task, research.task_id)
        assert stored is not None
        stored.input_validity = "stale"
    with pytest.raises(TaskNotReadyError, match="input validity"):
        service.review_task(
            project_id=project.id,
            plan_id=submitted.id,
            task_id=research.task_id,
            actor_user_id=identity.owner_user_id,
            expected_revision=research_task.revision,
            reviewer_role="A25",
            decision=ReviewDecision.ACCEPTED,
            summary="失效输入不得通过。",
            findings=[],
            idempotency_key="w11-stale-input-review",
        )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored = session.get(Task, research.task_id)
        assert stored is not None
        stored.input_validity = "current"

    with pytest.raises(ReviewPolicyError):
        service.review_task(
            project_id=project.id,
            plan_id=submitted.id,
            task_id=research.task_id,
            actor_user_id=identity.owner_user_id,
            expected_revision=research_task.revision,
            reviewer_role="A02",
            decision=ReviewDecision.ACCEPTED,
            summary="错误的自审角色。",
            findings=[],
            idempotency_key="w11-invalid-reviewer",
        )
    with pytest.raises(ReviewPolicyError, match="critical"):
        service.review_task(
            project_id=project.id,
            plan_id=submitted.id,
            task_id=research.task_id,
            actor_user_id=identity.owner_user_id,
            expected_revision=research_task.revision,
            reviewer_role="A25",
            decision=ReviewDecision.ACCEPTED,
            summary="critical缺陷不得通过。",
            findings=[
                ReviewFinding(
                    code="CITATION_MISMATCH",
                    severity=FindingSeverity.CRITICAL,
                    message="合成关键引文与原文不一致。",
                    evidence_refs=["fixture:w11-review"],
                )
            ],
            idempotency_key="w11-critical-accept",
        )

    changes = service.review_task(
        project_id=project.id,
        plan_id=submitted.id,
        task_id=research.task_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=research_task.revision,
        reviewer_role="A25",
        decision=ReviewDecision.CHANGES_REQUESTED,
        summary="补齐合成证据定位后重做。",
        findings=[
            ReviewFinding(
                code="MISSING_LOCATOR",
                severity=FindingSeverity.MAJOR,
                message="缺少可核查定位。",
                evidence_refs=[],
            )
        ],
        idempotency_key="w11-changes",
    )
    assert changes.task_state == TaskState.REWORK
    assert changes.plan_status == PlanStatus.ACTIVE
    replay_changes = service.review_task(
        project_id=project.id,
        plan_id=submitted.id,
        task_id=research.task_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=research_task.revision,
        reviewer_role="A25",
        decision=ReviewDecision.CHANGES_REQUESTED,
        summary="补齐合成证据定位后重做。",
        findings=[
            ReviewFinding(
                code="MISSING_LOCATOR",
                severity=FindingSeverity.MAJOR,
                message="缺少可核查定位。",
                evidence_refs=[],
            )
        ],
        idempotency_key="w11-changes",
    )
    assert replay_changes == changes

    current_plan = service.get_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
    )
    assert (
        next(node for node in current_plan.nodes if node.node_key == "audit").task_state
        == "needs_input"
    )
    redispatch = service.dispatch_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=current_plan.revision,
    )
    assert redispatch.dispatched[0].task_state == TaskState.QUEUED
    _run_ready_task(
        session_factory,
        workspace_id=identity.workspace_id,
        worker_name="w11-worker-research-rework",
    )
    research_task = _task_in_plan(
        session_factory,
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=research.task_id,
    )
    accepted = service.review_task(
        project_id=project.id,
        plan_id=submitted.id,
        task_id=research.task_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=research_task.revision,
        reviewer_role="A25",
        decision=ReviewDecision.ACCEPTED,
        summary="合成返工通过合同检查。",
        findings=[],
        idempotency_key="w11-accept-research",
    )
    assert accepted.task_state == TaskState.ACCEPTED
    assert accepted.unlocked_task_ids == [audit.task_id]

    current_plan = service.get_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
    )
    audit_node = next(node for node in current_plan.nodes if node.node_key == "audit")
    assert audit_node.task_state == "ready"
    audit_dispatch = service.dispatch_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=current_plan.revision,
    )
    assert audit_dispatch.dispatched[0].node_key == "audit"
    _run_ready_task(
        session_factory,
        workspace_id=identity.workspace_id,
        worker_name="w11-worker-audit",
    )
    audit_task = _task_in_plan(
        session_factory,
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=audit.task_id,
    )
    completed = service.review_task(
        project_id=project.id,
        plan_id=submitted.id,
        task_id=audit.task_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=audit_task.revision,
        reviewer_role="A25",
        decision=ReviewDecision.ACCEPTED,
        summary="合成审计任务通过合同检查。",
        findings=[],
        idempotency_key="w11-accept-audit",
    )
    assert completed.plan_status == PlanStatus.COMPLETED
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(TaskReview)) == 3


def test_iteration_limit_requires_explicit_rework_allowance(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, decision_id = _setup(session_factory)
    service = PlanService(session_factory, _roles())
    submitted = service.submit_plan(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        source_decision_id=decision_id,
        spec=_spec(max_rework_rounds=1, with_audit=False),
        idempotency_key="w11-limit-plan",
    )
    activated = service.activate_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=submitted.revision,
    )
    service.dispatch_plan(
        project_id=project.id,
        plan_id=activated.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=activated.revision,
    )
    _run_ready_task(
        session_factory,
        workspace_id=identity.workspace_id,
        worker_name="w11-limit-first",
    )
    task = _task_in_plan(
        session_factory,
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=submitted.nodes[0].task_id,
    )
    first = service.review_task(
        project_id=project.id,
        plan_id=submitted.id,
        task_id=task.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=task.revision,
        reviewer_role="A25",
        decision=ReviewDecision.CHANGES_REQUESTED,
        summary="第一次返工。",
        findings=[],
        idempotency_key="w11-limit-first-review",
    )
    assert first.task_state == TaskState.REWORK

    plan = service.get_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
    )
    service.dispatch_plan(
        project_id=project.id,
        plan_id=plan.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=plan.revision,
    )
    _run_ready_task(
        session_factory,
        workspace_id=identity.workspace_id,
        worker_name="w11-limit-second",
    )
    task = _task_in_plan(
        session_factory,
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
    )
    second = service.review_task(
        project_id=project.id,
        plan_id=submitted.id,
        task_id=task.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=task.revision,
        reviewer_role="A25",
        decision=ReviewDecision.CHANGES_REQUESTED,
        summary="第二次返工达到上限。",
        findings=[],
        idempotency_key="w11-limit-second-review",
    )
    assert second.task_state == TaskState.PAUSED
    assert second.plan_status == PlanStatus.PAUSED

    plan = service.get_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
    )
    assert plan.pause_reason == "iteration_limit"
    with pytest.raises(PlanStateError, match="additional"):
        service.resume_plan(
            project_id=project.id,
            plan_id=plan.id,
            actor_user_id=identity.owner_user_id,
            expected_revision=plan.revision,
            additional_rework_rounds=0,
        )
    resumed = service.resume_plan(
        project_id=project.id,
        plan_id=plan.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=plan.revision,
        additional_rework_rounds=1,
    )
    assert resumed.status == PlanStatus.ACTIVE
    assert resumed.max_rework_rounds == 2
    assert resumed.nodes[0].task_state == "rework"


def test_pause_resume_and_stop_cancel_unstarted_work(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, decision_id = _setup(session_factory)
    service = PlanService(session_factory, _roles())
    submitted = service.submit_plan(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        source_decision_id=decision_id,
        spec=_spec(with_audit=False),
        idempotency_key="w11-pause-plan",
    )
    activated = service.activate_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=submitted.revision,
    )
    paused = service.pause_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=activated.revision,
        reason="合成暂停检查",
    )
    assert paused.status == PlanStatus.PAUSED
    with pytest.raises(PlanStateError):
        service.dispatch_plan(
            project_id=project.id,
            plan_id=submitted.id,
            actor_user_id=identity.owner_user_id,
            expected_revision=paused.revision,
        )
    resumed = service.resume_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=paused.revision,
    )
    dispatched = service.dispatch_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=resumed.revision,
    )
    assert dispatched.dispatched
    stopped = service.stop_plan(
        project_id=project.id,
        plan_id=submitted.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=dispatched.plan_revision,
        reason="用户停止合成流程",
    )
    assert stopped.status == PlanStatus.STOPPED
    assert stopped.nodes[0].task_state == "cancelled"
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(OutboxMessage)) == 1
        assert session.scalar(select(OutboxMessage.state)) == "failed"
        plan = session.scalar(select(Plan))
        assert plan is not None and plan.status == "stopped"


def test_w11_tables_are_forced_through_workspace_rls(database: Engine) -> None:
    with database.connect() as connection:
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
        tables = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN ('plans', 'plan_nodes', 'task_reviews')
                ORDER BY c.relname
                """
            )
        ).all()
    assert policies == 79
    assert len(tables) == 3
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
