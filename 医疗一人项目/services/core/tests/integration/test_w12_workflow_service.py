from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.application.errors import ReviewPolicyError
from medical_one_person.application.knowledge import ClaimService
from medical_one_person.application.opportunities import OpportunityService
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.workflows import WorkflowService
from medical_one_person.domain.opportunities import OpportunityCard, Track
from medical_one_person.domain.workflows import (
    AssessmentRecommendation,
    AssessmentStatus,
    CriterionResult,
    CriterionResultStatus,
    StageDecisionStatus,
)
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AuditFinding,
    AuditRun,
    StageAssessment,
    StageDecision,
)
from medical_one_person.infrastructure.workflows import WorkflowRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _setup(session_factory: sessionmaker[Session]):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W12专业流程项目",
        scope="验证宠物药流程阶段、证据门与外部前置条件。",
        idempotency_key="create-w12-project",
    )
    fixture = json.loads(
        (PROJECT_ROOT / "fixtures" / "opportunity-contract-examples.json").read_text(
            encoding="utf-8"
        )
    )
    opportunity_service = OpportunityService(session_factory)
    opportunity = opportunity_service.create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        card=OpportunityCard.model_validate(fixture["opportunities"][0]),
    )
    decision = opportunity_service.select_opportunity(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        opportunity_id=opportunity.id,
        expected_revision=opportunity.revision,
        reason="仅用于W12合成专业流程测试。",
        scope="不授权外部动作。",
        evidence_version_ids=[],
        idempotency_key="w12-select",
    )
    claim = ClaimService(session_factory).create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        statement="W12合成阶段证据，仅用于契约测试。",
        directness="unknown",
    )
    roles = load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml")
    workflows = WorkflowRegistry.from_catalog(
        PROJECT_ROOT / "config" / "workflows" / "catalog.yaml",
        roles,
    )
    return (
        identity,
        project,
        decision.decision_id,
        claim.version_id,
        WorkflowService(session_factory, workflows, roles),
    )


def _met_results(stage, refs: list[str]) -> list[CriterionResult]:
    return [
        CriterionResult(
            criterion_id=criterion.id,
            status=CriterionResultStatus.MET,
            rationale=f"{criterion.id} 的合成测试依据。",
            evidence_refs=refs,
        )
        for criterion in stage.criteria
    ]


def test_stage_evidence_gate_blocks_external_stage_until_real_records(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, decision_id, claim_version_id, service = _setup(session_factory)
    workflow = service.get_workflow(Track.PET_REPURPOSING).definition
    reference_ids = [str(claim_version_id), str(decision_id)]

    first = service.assess_stage(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        track=Track.PET_REPURPOSING,
        stage_id=workflow.stages[0].stage_id,
        criterion_results=_met_results(workflow.stages[0], reference_ids),
        rationale="第一阶段合成记录完整。",
    )
    assert first.status == AssessmentStatus.READY_FOR_REVIEW
    assert first.recommendation == AssessmentRecommendation.CONTINUE_TO_REVIEW
    audit_id = uuid4()
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        session.add(
            AuditRun(
                id=audit_id,
                workspace_id=identity.workspace_id,
                project_id=project.id,
                target_type="claim_version",
                target_id=claim_version_id,
                linked_task_id=None,
                target_sha256="a" * 64,
                input_sha256="b" * 64,
                reviewer_role="A26",
                producer_role="A02",
                method="deterministic_rules.v1",
                state="blocked",
                downstream_blocked=True,
                summary="合成阶段证据被独立审计阻断。",
                review_version=1,
                input_snapshot={},
                idempotency_key="w12-stage-audit-block",
                request_hash="c" * 64,
                created_by_user_id=identity.owner_user_id,
                created_at=datetime.now(UTC),
            )
        )
        session.flush()
        session.add(
            AuditFinding(
                id=uuid4(),
                workspace_id=identity.workspace_id,
                project_id=project.id,
                audit_id=audit_id,
                code="STAGE_EVIDENCE_BLOCKED",
                severity="critical",
                category="counter_evidence",
                message="阶段引用仍存在未解决独立审计缺陷。",
                evidence_refs=[str(claim_version_id)],
                affected_objects=[],
                status="open",
                created_at=datetime.now(UTC),
            )
        )
    with pytest.raises(ReviewPolicyError, match="Active audit findings"):
        service.decide_stage(
            project_id=project.id,
            assessment_id=first.id,
            actor_user_id=identity.owner_user_id,
            decision=StageDecisionStatus.ACCEPTED,
            reviewer_role="A25",
            reason="存在独立阻断时不得通过。",
        )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        finding = session.scalar(
            select(AuditFinding).where(AuditFinding.audit_id == audit_id)
        )
        assert finding is not None
        finding.status = "resolved"
        finding.resolution = "合成缺陷已修复并记录复审。"
        finding.resolved_by_user_id = identity.owner_user_id
        finding.resolved_at = datetime.now(UTC)
    first_decided = service.decide_stage(
        project_id=project.id,
        assessment_id=first.id,
        actor_user_id=identity.owner_user_id,
        decision=StageDecisionStatus.ACCEPTED,
        reviewer_role="A25",
        reason="本地流程合同接受，不代表真实科学批准。",
    )
    assert first_decided.decision == StageDecisionStatus.ACCEPTED

    stage_plan = service.create_stage_plan(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        track=Track.PET_REPURPOSING,
        stage_id=workflow.stages[1].stage_id,
        source_decision_id=decision_id,
        idempotency_key="w12-stage2-plan",
    )
    assert stage_plan.workflow_id == workflow.workflow_id
    assert stage_plan.stage_id == workflow.stages[1].stage_id
    assert stage_plan.workflow_sha256
    assert {node.assignee_role for node in stage_plan.nodes} == {
        "A02",
        "A04",
        "A07",
        "A20",
        "A26",
    }

    for stage in workflow.stages[1:3]:
        assessment = service.assess_stage(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            track=Track.PET_REPURPOSING,
            stage_id=stage.stage_id,
            criterion_results=_met_results(stage, reference_ids),
            rationale=f"{stage.stage_id} 合成记录完整。",
        )
        assert assessment.status == AssessmentStatus.READY_FOR_REVIEW
        service.decide_stage(
            project_id=project.id,
            assessment_id=assessment.id,
            actor_user_id=identity.owner_user_id,
            decision=StageDecisionStatus.ACCEPTED,
            reviewer_role="A25",
            reason="合成阶段门记录。",
        )

    external = service.assess_stage(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        track=Track.PET_REPURPOSING,
        stage_id=workflow.stages[3].stage_id,
        criterion_results=_met_results(workflow.stages[3], reference_ids),
        rationale="书面判据满足，但现实前置条件尚未取得。",
    )
    assert external.status == AssessmentStatus.BLOCKED
    assert external.recommendation == AssessmentRecommendation.WAIT_EXTERNAL
    assert all(item["status"] == "unverified_w16" for item in external.external_preconditions)
    with pytest.raises(ReviewPolicyError, match="External preconditions"):
        service.decide_stage(
            project_id=project.id,
            assessment_id=external.id,
            actor_user_id=identity.owner_user_id,
            decision=StageDecisionStatus.ACCEPTED,
            reviewer_role="A25",
            reason="不得用桌面材料替代现实前置条件。",
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(StageAssessment)) == 4
        assert session.scalar(select(func.count()).select_from(StageDecision)) == 3


def test_stage_criteria_require_complete_project_evidence(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, _, claim_version_id, service = _setup(session_factory)
    workflow = service.get_workflow(Track.PET_REPURPOSING).definition
    stage = workflow.stages[0]
    results = _met_results(stage, [str(claim_version_id)])
    with pytest.raises(ReviewPolicyError, match="every criterion"):
        service.assess_stage(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            track=Track.PET_REPURPOSING,
            stage_id=stage.stage_id,
            criterion_results=results[:-1],
            rationale="缺少一个判据结果。",
        )

    results = _met_results(stage, [])
    with pytest.raises(ReviewPolicyError, match="evidence references"):
        service.assess_stage(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            track=Track.PET_REPURPOSING,
            stage_id=stage.stage_id,
            criterion_results=results,
            rationale="声称满足但没有证据。",
        )


def test_w12_tables_are_forced_through_workspace_rls(database: Engine) -> None:
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
                  AND c.relname IN ('stage_assessments', 'stage_decisions')
                ORDER BY c.relname
                """
            )
        ).all()
    assert policies == 85
    assert len(tables) == 2
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
