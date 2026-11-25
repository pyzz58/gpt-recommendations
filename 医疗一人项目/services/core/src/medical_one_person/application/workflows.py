from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.errors import (
    NotFoundError,
    PlanStateError,
    ReviewPolicyError,
)
from medical_one_person.application.plans import PlanService, PlanView
from medical_one_person.application.readiness import require_no_active_audit_blockers
from medical_one_person.domain.opportunities import Track
from medical_one_person.domain.plans import PlanSpec
from medical_one_person.domain.workflows import (
    AssessmentRecommendation,
    AssessmentStatus,
    CriterionKind,
    CriterionResult,
    CriterionResultStatus,
    StageDecisionStatus,
    WorkflowDefinition,
    WorkflowStage,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    ClaimVersion,
    Decision,
    KnowledgeDocumentVersion,
    Opportunity,
    Project,
    ProjectEvent,
    StageAssessment,
    StageDecision,
    User,
)
from medical_one_person.infrastructure.workflows import WorkflowRegistry


class WorkflowDescriptor(BaseModel):
    definition: WorkflowDefinition
    sha256: str


class StageAssessmentView(BaseModel):
    id: UUID
    project_id: UUID
    workflow_track: Track
    workflow_id: str
    workflow_version: int
    workflow_sha256: str
    stage_id: str
    assessment_version: int
    status: AssessmentStatus
    recommendation: AssessmentRecommendation
    criterion_results: list[CriterionResult]
    external_preconditions: list[dict[str, Any]]
    evidence_refs: list[str]
    rationale: str
    decision: StageDecisionStatus | None
    reviewer_role: str | None
    created_at: datetime


class StageAssessmentRequest(BaseModel):
    criterion_results: list[CriterionResult]
    rationale: str


class StageDecisionRequest(BaseModel):
    decision: StageDecisionStatus
    reviewer_role: str
    reason: str


class WorkflowService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        workflows: WorkflowRegistry,
        roles: dict[str, AgentRoleConfig],
    ) -> None:
        self._session_factory = session_factory
        self._workflows = workflows
        self._roles = roles

    def list_workflows(self) -> list[WorkflowDescriptor]:
        return [
            WorkflowDescriptor(
                definition=definition,
                sha256=self._workflows.fingerprint(definition.track),
            )
            for definition in self._workflows.list()
        ]

    def get_workflow(self, track: Track) -> WorkflowDescriptor:
        return WorkflowDescriptor(
            definition=self._workflows.get(track),
            sha256=self._workflows.fingerprint(track),
        )

    def list_project_workflows(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[WorkflowDescriptor]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
        return self.list_workflows()

    def get_project_workflow(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        track: Track,
    ) -> WorkflowDescriptor:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
        return self.get_workflow(track)

    def assess_stage(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        track: Track,
        stage_id: str,
        criterion_results: list[CriterionResult],
        rationale: str,
    ) -> StageAssessmentView:
        if not rationale.strip():
            raise ValueError("Stage assessment rationale is required")
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            _ensure_selected_track(session, project.id, track)
            workflow = self._workflows.get(track)
            stage = _stage(workflow, stage_id)
            self._require_prior_stage_accepted(
                session,
                project_id=project.id,
                workflow=workflow,
                stage=stage,
            )
            _validate_criterion_results(stage, criterion_results)
            evidence_ids = _validate_evidence_refs(
                session,
                project_id=project.id,
                values=sorted(
                    {
                        reference
                        for result in criterion_results
                        for reference in result.evidence_refs
                    }
                ),
            )
            external = [
                {
                    "id": item.id,
                    "description": item.description,
                    "provider_type": item.provider_type,
                    "evidence_type": item.evidence_type,
                    "status": "unverified_w16",
                    "cannot_self_confirm": True,
                }
                for item in stage.external_preconditions
            ]
            status, recommendation = _assess_status(
                stage,
                criterion_results,
                external_blocked=bool(external),
            )
            assessment_version = (
                session.scalar(
                    select(func.max(StageAssessment.assessment_version)).where(
                        StageAssessment.project_id == project.id,
                        StageAssessment.workflow_track == track.value,
                        StageAssessment.stage_id == stage.stage_id,
                    )
                )
                or 0
            ) + 1
            now = datetime.now(UTC)
            record = StageAssessment(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                workflow_track=track.value,
                workflow_id=workflow.workflow_id,
                workflow_version=workflow.version,
                workflow_sha256=self._workflows.fingerprint(track),
                stage_id=stage.stage_id,
                assessment_version=assessment_version,
                status=status.value,
                recommendation=recommendation.value,
                criterion_results=[result.model_dump(mode="json") for result in criterion_results],
                external_preconditions=external,
                evidence_refs=sorted(str(item) for item in evidence_ids),
                rationale=rationale,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(record)
            session.flush()
            _append_event(
                session,
                project=project,
                event_type="workflow.stage_assessed",
                object_id=record.id,
                object_revision=assessment_version,
                actor_user_id=actor.id,
                payload={
                    "workflow_id": workflow.workflow_id,
                    "stage_id": stage.stage_id,
                    "status": status.value,
                    "recommendation": recommendation.value,
                },
                now=now,
            )
            return _assessment_view(session, record)

    def decide_stage(
        self,
        *,
        project_id: UUID,
        assessment_id: UUID,
        actor_user_id: UUID,
        decision: StageDecisionStatus,
        reviewer_role: str,
        reason: str,
    ) -> StageAssessmentView:
        if not reason.strip():
            raise ValueError("Stage decision reason is required")
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            assessment = session.scalar(
                select(StageAssessment)
                .where(
                    StageAssessment.id == assessment_id,
                    StageAssessment.project_id == project.id,
                )
                .with_for_update()
            )
            if assessment is None:
                raise NotFoundError("Stage assessment not found")
            if assessment.external_preconditions:
                raise ReviewPolicyError(
                    "External preconditions cannot be accepted before W16 evidence"
                )
            if assessment.status != AssessmentStatus.READY_FOR_REVIEW.value:
                raise PlanStateError("Stage assessment is not ready for a gate decision")
            target_ids: set[UUID] = set()
            for value in assessment.evidence_refs:
                try:
                    target_ids.add(UUID(value))
                except ValueError:
                    continue
            require_no_active_audit_blockers(
                session,
                project_id=project.id,
                target_ids=target_ids,
            )
            reviewer = self._roles.get(reviewer_role)
            if (
                reviewer is None
                or not reviewer.independent_context
                or reviewer_role not in {"A25", "A26"}
            ):
                raise ReviewPolicyError(
                    "Stage decision requires an independent A25/A26 role contract"
                )
            existing = session.scalar(
                select(StageDecision).where(StageDecision.assessment_id == assessment.id)
            )
            if existing is not None:
                if (
                    existing.decision != decision.value
                    or existing.reviewer_role != reviewer_role
                    or existing.reason != reason
                ):
                    raise ReviewPolicyError("Stage assessment already has a different decision")
                return _assessment_view(session, assessment)
            now = datetime.now(UTC)
            session.add(
                StageDecision(
                    id=uuid4(),
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    assessment_id=assessment.id,
                    decision=decision.value,
                    reviewer_user_id=actor.id,
                    reviewer_role=reviewer_role,
                    reason=reason,
                    created_at=now,
                )
            )
            _append_event(
                session,
                project=project,
                event_type="workflow.stage_decided",
                object_id=assessment.id,
                object_revision=assessment.assessment_version,
                actor_user_id=actor.id,
                payload={
                    "stage_id": assessment.stage_id,
                    "decision": decision.value,
                    "reviewer_role": reviewer_role,
                },
                now=now,
            )
            session.flush()
            return _assessment_view(session, assessment)

    def create_stage_plan(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        track: Track,
        stage_id: str,
        source_decision_id: UUID,
        idempotency_key: str,
    ) -> PlanView:
        workflow = self._workflows.get(track)
        stage = _stage(workflow, stage_id)
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            _ensure_selected_track(session, project.id, track)
            self._require_prior_stage_accepted(
                session,
                project_id=project.id,
                workflow=workflow,
                stage=stage,
            )
        spec = PlanSpec.model_validate(
            {
                "title": f"{workflow.title}：{stage.title}",
                "objective": stage.purpose,
                "max_rework_rounds": 3,
                "workflow_track": track.value,
                "workflow_id": workflow.workflow_id,
                "workflow_version": workflow.version,
                "stage_id": stage.stage_id,
                "nodes": [
                    {
                        "key": node.key,
                        "task_type": node.task_type,
                        "purpose": node.purpose,
                        "assignee_role": node.assignee_role,
                        "role_version": str(self._roles[node.assignee_role].version),
                        "input_version": f"{workflow.workflow_id}:v{workflow.version}",
                        "input_refs": node.input_refs,
                        "goal": node.goal,
                        "deliverable_schema": node.deliverable_schema,
                        "acceptance_policy": node.acceptance_policy,
                        "depends_on": node.depends_on,
                    }
                    for node in stage.plan_nodes
                ],
            }
        )
        return PlanService(
            self._session_factory,
            self._roles,
            self._workflows,
        ).submit_plan(
            project_id=project_id,
            actor_user_id=actor_user_id,
            source_decision_id=source_decision_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    def list_assessments(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        track: Track | None = None,
    ) -> list[StageAssessmentView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            statement = select(StageAssessment).where(StageAssessment.project_id == project.id)
            if track is not None:
                statement = statement.where(StageAssessment.workflow_track == track.value)
            records = session.scalars(
                statement.order_by(
                    StageAssessment.created_at.desc(),
                    StageAssessment.assessment_version.desc(),
                )
            ).all()
            return [_assessment_view(session, record) for record in records]

    def _require_prior_stage_accepted(
        self,
        session: Session,
        *,
        project_id: UUID,
        workflow: WorkflowDefinition,
        stage: WorkflowStage,
    ) -> None:
        index = workflow.stages.index(stage)
        if index == 0:
            return
        previous = workflow.stages[index - 1]
        latest = session.scalar(
            select(StageAssessment)
            .where(
                StageAssessment.project_id == project_id,
                StageAssessment.workflow_track == workflow.track.value,
                StageAssessment.stage_id == previous.stage_id,
            )
            .order_by(StageAssessment.assessment_version.desc())
            .limit(1)
        )
        if latest is None:
            raise PlanStateError(f"Previous workflow stage {previous.stage_id} has no assessment")
        accepted = session.scalar(
            select(StageDecision).where(
                StageDecision.assessment_id == latest.id,
                StageDecision.decision == StageDecisionStatus.ACCEPTED.value,
            )
        )
        if accepted is None:
            raise PlanStateError(f"Previous workflow stage {previous.stage_id} is not accepted")


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage workflows")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _ensure_selected_track(
    session: Session,
    project_id: UUID,
    track: Track,
) -> Opportunity:
    opportunity = session.scalar(
        select(Opportunity)
        .join(Decision, Decision.selected_opportunity_id == Opportunity.id)
        .where(
            Decision.project_id == project_id,
            Decision.kind == "opportunity_selection",
            Opportunity.status == "selected",
        )
        .order_by(Decision.effective_at.desc())
        .limit(1)
    )
    if opportunity is None:
        raise PlanStateError("A selected opportunity is required for a workflow")
    if opportunity.track != track.value:
        raise PlanStateError("Workflow track does not match selected opportunity")
    return opportunity


def _stage(workflow: WorkflowDefinition, stage_id: str) -> WorkflowStage:
    stage = next(
        (item for item in workflow.stages if item.stage_id == stage_id),
        None,
    )
    if stage is None:
        raise NotFoundError("Workflow stage not found")
    return stage


def _validate_criterion_results(
    stage: WorkflowStage,
    results: list[CriterionResult],
) -> None:
    expected = {criterion.id for criterion in stage.criteria}
    actual = {result.criterion_id for result in results}
    if actual != expected:
        raise ReviewPolicyError(
            "Stage assessment must provide exactly one result for every criterion"
        )
    criteria = {criterion.id: criterion for criterion in stage.criteria}
    for result in results:
        criterion = criteria[result.criterion_id]
        if (
            result.status == CriterionResultStatus.MET
            and criterion.requires_refs
            and not result.evidence_refs
        ):
            raise ReviewPolicyError(f"Criterion {criterion.id} requires evidence references")
        if (
            criterion.kind == CriterionKind.EVIDENCE
            and result.status == CriterionResultStatus.MET
            and not result.evidence_refs
        ):
            raise ReviewPolicyError(
                f"Evidence criterion {criterion.id} cannot be met without evidence"
            )


def _validate_evidence_refs(
    session: Session,
    *,
    project_id: UUID,
    values: list[str],
) -> set[UUID]:
    try:
        requested = {UUID(value) for value in values}
    except (TypeError, ValueError) as exc:
        raise ReviewPolicyError("Stage evidence references must be UUIDs") from exc
    if not requested:
        return requested
    claim_ids = set(
        session.scalars(
            select(ClaimVersion.id).where(
                ClaimVersion.project_id == project_id,
                ClaimVersion.id.in_(requested),
            )
        )
    )
    version_ids = set(
        session.scalars(
            select(KnowledgeDocumentVersion.id).where(
                KnowledgeDocumentVersion.project_id == project_id,
                KnowledgeDocumentVersion.id.in_(requested),
            )
        )
    )
    decision_ids = set(
        session.scalars(
            select(Decision.id).where(
                Decision.project_id == project_id,
                Decision.id.in_(requested),
            )
        )
    )
    opportunity_ids = set(
        session.scalars(
            select(Opportunity.id).where(
                Opportunity.project_id == project_id,
                Opportunity.id.in_(requested),
            )
        )
    )
    assessment_ids = set(
        session.scalars(
            select(StageAssessment.id).where(
                StageAssessment.project_id == project_id,
                StageAssessment.id.in_(requested),
            )
        )
    )
    known = claim_ids | version_ids | decision_ids | opportunity_ids | assessment_ids
    if requested - known:
        raise NotFoundError("Stage evidence reference not found in project")
    return requested


def _assess_status(
    stage: WorkflowStage,
    results: list[CriterionResult],
    *,
    external_blocked: bool,
) -> tuple[AssessmentStatus, AssessmentRecommendation]:
    statuses = {result.status for result in results}
    if CriterionResultStatus.UNMET in statuses:
        route = stage.failure_routes.get("critical_counterevidence", "revise")
        return (
            AssessmentStatus.NEEDS_REVISION,
            AssessmentRecommendation.STOP if route == "stop" else AssessmentRecommendation.REVISE,
        )
    if CriterionResultStatus.UNKNOWN in statuses:
        return (
            AssessmentStatus.NEEDS_EVIDENCE,
            AssessmentRecommendation.GATHER_EVIDENCE,
        )
    if external_blocked:
        return (
            AssessmentStatus.BLOCKED,
            AssessmentRecommendation.WAIT_EXTERNAL,
        )
    return (
        AssessmentStatus.READY_FOR_REVIEW,
        AssessmentRecommendation.CONTINUE_TO_REVIEW,
    )


def _assessment_view(
    session: Session,
    assessment: StageAssessment,
) -> StageAssessmentView:
    decision = session.scalar(
        select(StageDecision).where(StageDecision.assessment_id == assessment.id)
    )
    return StageAssessmentView(
        id=assessment.id,
        project_id=assessment.project_id,
        workflow_track=Track(assessment.workflow_track),
        workflow_id=assessment.workflow_id,
        workflow_version=assessment.workflow_version,
        workflow_sha256=assessment.workflow_sha256,
        stage_id=assessment.stage_id,
        assessment_version=assessment.assessment_version,
        status=AssessmentStatus(assessment.status),
        recommendation=AssessmentRecommendation(assessment.recommendation),
        criterion_results=[
            CriterionResult.model_validate(item) for item in assessment.criterion_results
        ],
        external_preconditions=assessment.external_preconditions,
        evidence_refs=assessment.evidence_refs,
        rationale=assessment.rationale,
        decision=(StageDecisionStatus(decision.decision) if decision is not None else None),
        reviewer_role=decision.reviewer_role if decision is not None else None,
        created_at=assessment.created_at,
    )


def _append_event(
    session: Session,
    *,
    project: Project,
    event_type: str,
    object_id: UUID,
    object_revision: int,
    actor_user_id: UUID,
    payload: dict[str, Any],
    now: datetime,
) -> None:
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == project.id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=project.workspace_id,
            project_id=project.id,
            project_seq=(last_sequence or 0) + 1,
            type=event_type,
            actor_user_id=actor_user_id,
            object_type="stage_assessment",
            object_id=object_id,
            object_revision=object_revision,
            payload=payload,
            correlation_id=uuid4(),
            created_at=now,
        )
    )
