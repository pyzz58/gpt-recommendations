from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.plans import PlanView
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.application.workflows import (
    StageAssessmentView,
    WorkflowDescriptor,
    WorkflowService,
)
from medical_one_person.domain.opportunities import Track
from medical_one_person.domain.workflows import (
    CriterionResult,
    StageDecisionStatus,
)
from medical_one_person.infrastructure.workflows import WorkflowRegistry


class StageAssessmentRequest(BaseModel):
    criterion_results: list[CriterionResult]
    rationale: str = Field(min_length=1, max_length=10_000)


class StageDecisionRequest(BaseModel):
    decision: StageDecisionStatus
    reviewer_role: str = Field(pattern=r"^A(25|26)$")
    reason: str = Field(min_length=1, max_length=10_000)


class StagePlanRequest(BaseModel):
    source_decision_id: UUID


def build_workflow_router(
    session_factory: sessionmaker[Session],
    workflows: WorkflowRegistry,
    roles: dict[str, AgentRoleConfig],
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["workflows"])
    service = WorkflowService(session_factory, workflows, roles)

    @router.get("/workflows", response_model=list[WorkflowDescriptor])
    def list_workflows(
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[WorkflowDescriptor]:
        return service.list_workflows()

    @router.get(
        "/projects/{project_id}/workflows",
        response_model=list[WorkflowDescriptor],
    )
    def project_workflows(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[WorkflowDescriptor]:
        return service.list_project_workflows(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.get(
        "/projects/{project_id}/workflows/{track}",
        response_model=WorkflowDescriptor,
    )
    def get_workflow(
        project_id: UUID,
        track: Track,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> WorkflowDescriptor:
        return service.get_project_workflow(
            project_id=project_id,
            actor_user_id=principal.user_id,
            track=track,
        )

    @router.get(
        "/projects/{project_id}/workflow-assessments",
        response_model=list[StageAssessmentView],
    )
    def list_assessments(
        project_id: UUID,
        track: Track | None = None,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[StageAssessmentView]:
        return service.list_assessments(
            project_id=project_id,
            actor_user_id=principal.user_id,
            track=track,
        )

    @router.post(
        "/projects/{project_id}/workflows/{track}/stages/{stage_id}/assessments",
        response_model=StageAssessmentView,
        status_code=201,
    )
    def assess_stage(
        project_id: UUID,
        track: Track,
        stage_id: str,
        request: StageAssessmentRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> StageAssessmentView:
        return service.assess_stage(
            project_id=project_id,
            actor_user_id=principal.user_id,
            track=track,
            stage_id=stage_id,
            criterion_results=request.criterion_results,
            rationale=request.rationale,
        )

    @router.post(
        "/projects/{project_id}/workflow-assessments/{assessment_id}/decision",
        response_model=StageAssessmentView,
    )
    def decide_stage(
        project_id: UUID,
        assessment_id: UUID,
        request: StageDecisionRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> StageAssessmentView:
        return service.decide_stage(
            project_id=project_id,
            assessment_id=assessment_id,
            actor_user_id=principal.user_id,
            decision=request.decision,
            reviewer_role=request.reviewer_role,
            reason=request.reason,
        )

    @router.post(
        "/projects/{project_id}/workflows/{track}/stages/{stage_id}/plans",
        response_model=PlanView,
        status_code=201,
    )
    def create_stage_plan(
        project_id: UUID,
        track: Track,
        stage_id: str,
        request: StagePlanRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.create_stage_plan(
            project_id=project_id,
            actor_user_id=principal.user_id,
            track=track,
            stage_id=stage_id,
            source_decision_id=request.source_decision_id,
            idempotency_key=idempotency_key,
        )

    return router
