from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.audits import (
    AuditFindingView,
    AuditRunView,
    AuditService,
    AuditWorkspaceView,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.audits import (
    AuditEvaluationView,
    AuditFindingStatus,
    AuditTargetType,
)


class AuditReviewRequest(BaseModel):
    target_type: AuditTargetType
    target_id: UUID
    reviewer_role: str = Field(pattern=r"^A(25|26)$")
    producer_role: str | None = Field(
        default=None,
        pattern=r"^A(0[1-9]|1[0-9]|2[0-6])$",
    )
    linked_task_id: UUID | None = None


class AuditFindingResolutionRequest(BaseModel):
    status: AuditFindingStatus
    resolution: str = Field(min_length=1, max_length=10_000)


def build_audit_router(
    session_factory: sessionmaker[Session],
    roles: dict[str, AgentRoleConfig],
    fixture_path: Path,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects/{project_id}/audits", tags=["audits"])
    service = AuditService(session_factory, roles, fixture_path)

    @router.get("", response_model=AuditWorkspaceView)
    def workspace(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> AuditWorkspaceView:
        return service.workspace(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("", response_model=AuditRunView, status_code=201)
    def create_review(
        project_id: UUID,
        request: AuditReviewRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> AuditRunView:
        return service.create_review(
            project_id=project_id,
            actor_user_id=principal.user_id,
            target_type=request.target_type,
            target_id=request.target_id,
            reviewer_role=request.reviewer_role,
            producer_role=request.producer_role,
            linked_task_id=request.linked_task_id,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/{audit_id}/findings/{finding_id}/disposition",
        response_model=AuditFindingView,
    )
    def resolve_finding(
        project_id: UUID,
        audit_id: UUID,
        finding_id: UUID,
        request: AuditFindingResolutionRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> AuditFindingView:
        return service.resolve_finding(
            project_id=project_id,
            audit_id=audit_id,
            finding_id=finding_id,
            actor_user_id=principal.user_id,
            status=request.status,
            resolution=request.resolution,
        )

    @router.post("/evaluate", response_model=AuditEvaluationView, status_code=201)
    def evaluate(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> AuditEvaluationView:
        return service.run_evaluation(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    return router
