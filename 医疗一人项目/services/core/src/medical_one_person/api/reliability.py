from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.reliability import ReliabilityService
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.reliability import (
    ReliabilityEvaluationView,
    ReliabilityProjectView,
)


def build_reliability_router(
    session_factory: sessionmaker[Session],
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["reliability"])
    service = ReliabilityService(session_factory)

    @router.get(
        "/projects/{project_id}/reliability",
        response_model=ReliabilityProjectView,
    )
    def project_reliability(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ReliabilityProjectView:
        return service.project_view(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/projects/{project_id}/reliability/evaluate",
        response_model=ReliabilityEvaluationView,
        status_code=201,
    )
    def evaluate_project_reliability(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ReliabilityEvaluationView:
        return service.evaluate(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    return router
