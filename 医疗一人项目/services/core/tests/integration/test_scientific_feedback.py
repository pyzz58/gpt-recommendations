"""Synthetic ADC/cat task flow; no claim about ADC efficacy or real research."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select
from test_w11_plans import _roles, _setup

from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.errors import TaskNotReadyError
from medical_one_person.application.handoffs import accepted_run_payload
from medical_one_person.application.plans import PlanService
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.application.tasks import resolve_task_inputs
from medical_one_person.domain.plans import PlanSpec, ReviewDecision, ReviewFinding
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import AgentRun, Plan, Project, Task
from medical_one_person.providers import FakeModelProvider


def _spec(*, rounds=1):
    return PlanSpec.model_validate(
        {
            "title": "ADC与猫肿瘤：合成流程案例",
            "objective": "合成案例：梳理理论及未知，不作疗效判断。",
            "max_followup_rounds": rounds,
            "nodes": [
                {
                    "key": "evidence",
                    "task_type": "scientific.evidence",
                    "purpose": "synthetic-adc-evidence",
                    "assignee_role": "A04",
                    "role_version": "1",
                    "input_version": "fixture-v1",
                    "input_refs": ["fixture:adc-cat-workflow-only"],
                    "goal": "提交合成理论资料包及缺证说明。",
                    "deliverable_schema": "agent_delivery.v1",
                    "acceptance_policy": "independent_review.v1",
                }
            ],
        }
    )


class ScriptedProvider(FakeModelProvider):
    def __init__(self, action="gather_evidence", *, outside_scope=False):
        self.action = action
        self.outside_scope = outside_scope

    def generate_structured(self, request):
        result = super().generate_structured(request)
        if request.context_sections["task_type"] == "scientific.integration":
            update = result.output["scientific_update"]
            update["action"] = self.action
            update["judgment_change"] = "合成案例：已区分理论资料与目标动物证据，结论仍未知。"
            update["rationale"] = "合成流程决定，仅验证反馈与补证派工。"
            if self.action in {"continue", "gather_evidence", "revise"}:
                spec = _spec().model_dump(mode="json")
                if self.outside_scope:
                    spec["nodes"][0]["task_type"] = "external.commission"
                update["next_plan"] = spec
        else:
            result.output["analysis"] = "合成资料包：目标动物证据缺口需要继续核查。"
        return result


def _start(session_factory, *, rounds=1):
    identity, project, decision_id = _setup(session_factory)
    service = PlanService(session_factory, _roles())
    plan = service.submit_plan(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        source_decision_id=decision_id,
        spec=_spec(rounds=rounds),
        idempotency_key="feedback-plan",
    )
    plan = service.activate_plan(
        project_id=project.id,
        plan_id=plan.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=plan.revision,
    )
    service.dispatch_plan(
        project_id=project.id,
        plan_id=plan.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=plan.revision,
    )
    return identity, project, service, plan.id


def _run(session_factory, identity, provider=None):
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    claim = queue.claim(workspace_id=identity.workspace_id, worker_id="feedback-test")
    assert claim is not None
    return AgentRunner(
        session_factory,
        provider or ScriptedProvider(),
        _roles(),
        theory_hash="d" * 64,
        job_queue=queue,
    ).run_claim(claim)


def _review(service, identity, project, plan_id, key, *, decision=ReviewDecision.ACCEPTED):
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    node = next(node for node in plan.nodes if node.node_key == key)
    return service.review_task(
        project_id=project.id,
        plan_id=plan_id,
        task_id=node.task_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=node.task_revision,
        reviewer_role=node.reviewer_roles[0],
        decision=decision,
        summary="合成验收：检查交付与未知，不证明科学正确。",
        findings=(
            [
                ReviewFinding(
                    code="MISSING_SOURCE", severity="major", message="合成缺口：补充原文定位。"
                )
            ]
            if decision == ReviewDecision.CHANGES_REQUESTED
            else []
        ),
        idempotency_key=f"{plan_id}:{key}:{node.task_revision}",
    )


def test_reviewed_content_returns_to_chief_then_creates_bounded_followup(session_factory):
    identity, project, service, plan_id = _start(session_factory)
    initial = _run(session_factory, identity)
    _review(
        service, identity, project, plan_id, "evidence", decision=ReviewDecision.CHANGES_REQUESTED
    )
    revised = _run(session_factory, identity)
    assert initial.task_id == revised.task_id
    _review(service, identity, project, plan_id, "evidence")
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    assert plan.status == "active"  # Work accepted; chief has not integrated it yet.
    chief = _run(session_factory, identity)
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=identity.owner_user_id)
        run = session.scalar(select(AgentRun).where(AgentRun.task_id == chief.task_id))
        packet = run.input_snapshot["upstream_deliveries"][0]
        assert packet["delivery"]["analysis"] == revised.analysis
        assert len(packet["reviews"]) == 2
        assert packet["reviews"][0]["findings"][0]["code"] == "MISSING_SOURCE"
        assert run.input_snapshot["role_id"] == "A02"
    chief_review = _review(service, identity, project, plan_id, "chief-integration")
    replay = service.review_task(
        project_id=project.id,
        plan_id=plan_id,
        task_id=chief.task_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=chief_review.task_revision - 1,
        reviewer_role="A25",
        decision=ReviewDecision.ACCEPTED,
        summary="合成验收：检查交付与未知，不证明科学正确。",
        findings=[],
        idempotency_key=f"{plan_id}:chief-integration:{chief_review.task_revision - 1}",
    )
    assert replay.review_id == chief_review.review_id
    # A fresh service reads the persisted judgment and the linked, already queued next plan.
    service = PlanService(session_factory, _roles())
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    assert plan.status == "completed"
    update = plan.scientific_updates[0]
    assert update["update"]["action"] == "gather_evidence"
    child_id = UUID(update["next_plan_id"])
    child = service.get_plan(
        project_id=project.id, plan_id=child_id, actor_user_id=identity.owner_user_id
    )
    assert child.parent_plan_id == plan_id
    assert child.feedback_round == 1
    assert child.source_decision_id == plan.source_decision_id
    assert child.objective == plan.objective
    assert next(n for n in child.nodes if n.node_key == "evidence").task_state == "queued"
    _run(session_factory, identity)
    _review(service, identity, project, child_id, "evidence")
    _run(session_factory, identity)
    _review(service, identity, project, child_id, "chief-integration")
    child = service.get_plan(
        project_id=project.id, plan_id=child_id, actor_user_id=identity.owner_user_id
    )
    assert child.scientific_updates[0]["block_reason"] == "followup_round_limit"
    assert child.scientific_updates[0]["next_plan_id"] is None
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=identity.owner_user_id)
        assert len(session.scalars(select(Plan).where(Plan.project_id == project.id)).all()) == 2
        assert session.get(Project, project.id).status == "paused"


@pytest.mark.parametrize("action", ["wait", "pause", "stop"])
def test_unknown_and_negative_results_close_without_unwanted_dispatch(session_factory, action):
    identity, project, service, plan_id = _start(session_factory)
    _run(session_factory, identity)
    _review(service, identity, project, plan_id, "evidence")
    _run(session_factory, identity, ScriptedProvider(action))
    _review(service, identity, project, plan_id, "chief-integration")
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    assert len(plan.scientific_updates) == 1
    assert plan.scientific_updates[0]["next_plan_id"] is None
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=identity.owner_user_id)
        assert session.get(Project, project.id).status == (
            "stopped" if action == "stop" else "paused"
        )


def test_outside_scope_proposal_is_retained_but_never_dispatched(session_factory):
    identity, project, service, plan_id = _start(session_factory)
    _run(session_factory, identity)
    _review(service, identity, project, plan_id, "evidence")
    _run(session_factory, identity, ScriptedProvider(outside_scope=True))
    _review(service, identity, project, plan_id, "chief-integration")
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    assert plan.scientific_updates[0]["block_reason"] == "outside_desktop_research"
    assert plan.scientific_updates[0]["update"]["next_plan"] is not None
    assert len(service.list_plans(project_id=project.id, actor_user_id=identity.owner_user_id)) == 1


def test_accepting_chief_result_while_paused_does_not_restart_research(session_factory):
    identity, project, service, plan_id = _start(session_factory)
    _run(session_factory, identity)
    _review(service, identity, project, plan_id, "evidence")
    _run(session_factory, identity)
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    service.pause_plan(
        project_id=project.id,
        plan_id=plan_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=plan.revision,
        reason="合成测试：暂停期间只接收判断。",
    )
    _review(service, identity, project, plan_id, "chief-integration")
    plan = service.get_plan(
        project_id=project.id, plan_id=plan_id, actor_user_id=identity.owner_user_id
    )
    assert plan.scientific_updates[0]["block_reason"] == "plan_paused"
    assert plan.scientific_updates[0]["next_plan_id"] is None
    assert len(service.list_plans(project_id=project.id, actor_user_id=identity.owner_user_id)) == 1


def test_unaccepted_or_foreign_delivery_cannot_enter_chief_context(session_factory):
    identity, project, _, _ = _start(session_factory)
    delivery = _run(session_factory, identity)
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=identity.owner_user_id)
        run = session.scalar(select(AgentRun).where(AgentRun.task_id == delivery.task_id))
        with pytest.raises(TaskNotReadyError, match="not been accepted"):
            accepted_run_payload(session, project_id=project.id, run_id=run.id)
        from uuid import uuid4

        with pytest.raises(TaskNotReadyError, match="unavailable"):
            accepted_run_payload(session, project_id=uuid4(), run_id=run.id)
        with pytest.raises(TaskNotReadyError, match="UUID"):
            resolve_task_inputs(
                session,
                project_id=project.id,
                input_version="v1",
                input_refs=["agent_run:not-an-id"],
                captured_at=run.created_at,
            )
        assert session.get(Task, delivery.task_id).state == "submitted"


@pytest.mark.parametrize("failure", ["changed_output", "stale_input"])
def test_reviewed_delivery_is_rechecked_before_reuse(session_factory, failure):
    identity, project, service, plan_id = _start(session_factory)
    delivery = _run(session_factory, identity)
    _review(service, identity, project, plan_id, "evidence")
    with session_factory.begin() as session:
        set_rls_context(session, workspace_id=identity.workspace_id, user_id=identity.owner_user_id)
        run = session.scalar(select(AgentRun).where(AgentRun.task_id == delivery.task_id))
        if failure == "changed_output":
            run.output = {**run.output, "analysis": "changed after review"}
        else:
            from medical_one_person.application.tasks import invalidate_task_inputs

            invalidate_task_inputs(
                session,
                project_id=project.id,
                task_ids=[delivery.task_id],
                actor_user_id=identity.owner_user_id,
                reason="synthetic source revision",
                now=run.created_at,
            )
        session.flush()
        with pytest.raises(TaskNotReadyError):
            accepted_run_payload(session, project_id=project.id, run_id=run.id)
