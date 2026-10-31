from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.datasets import (
    AnalysisReviewView,
    AnalysisRunView,
    DatasetService,
    DatasetView,
    StatisticalPlanView,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.datasets import CleaningSpec, StatisticalPlanSpec
from medical_one_person.domain.plans import ReviewDecision, ReviewFinding
from medical_one_person.infrastructure.artifacts import LocalArtifactStore


class DatasetImportRequest(BaseModel):
    document_version_id: UUID
    title: str = Field(min_length=1, max_length=300)
    source_label: str = Field(min_length=1, max_length=300)
    synthetic: bool
    sheet_name: str | None = Field(default=None, max_length=200)


class DatasetDerivationRequest(BaseModel):
    parent_version_id: UUID
    spec: CleaningSpec


class StatisticalPlanCreateRequest(BaseModel):
    spec: StatisticalPlanSpec


class AnalysisReviewRequest(BaseModel):
    reviewer_role: str = Field(pattern=r"^A(14|25|26)$")
    decision: ReviewDecision
    summary: str = Field(min_length=1, max_length=10_000)
    findings: list[ReviewFinding] = Field(default_factory=list)


def build_dataset_router(
    session_factory: sessionmaker[Session],
    store: LocalArtifactStore,
    roles: dict[str, AgentRoleConfig],
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["datasets"])
    service = DatasetService(session_factory, store, roles)

    @router.get("/datasets", response_model=list[DatasetView])
    def list_datasets(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[DatasetView]:
        return service.list_datasets(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/datasets/import", response_model=DatasetView, status_code=201)
    def import_dataset(
        project_id: UUID,
        request: DatasetImportRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> DatasetView:
        return service.import_table(
            project_id=project_id,
            actor_user_id=principal.user_id,
            document_version_id=request.document_version_id,
            title=request.title,
            source_label=request.source_label,
            synthetic=request.synthetic,
            sheet_name=request.sheet_name,
            idempotency_key=idempotency_key,
        )

    @router.get("/datasets/{dataset_id}", response_model=DatasetView)
    def get_dataset(
        project_id: UUID,
        dataset_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> DatasetView:
        return service.get_dataset(
            project_id=project_id,
            dataset_id=dataset_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/datasets/{dataset_id}/versions",
        response_model=DatasetView,
        status_code=201,
    )
    def derive_dataset_version(
        project_id: UUID,
        dataset_id: UUID,
        request: DatasetDerivationRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> DatasetView:
        return service.derive_version(
            project_id=project_id,
            dataset_id=dataset_id,
            actor_user_id=principal.user_id,
            parent_version_id=request.parent_version_id,
            spec=request.spec,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/dataset-versions/{version_id}/statistical-plans",
        response_model=StatisticalPlanView,
        status_code=201,
    )
    def create_statistical_plan(
        project_id: UUID,
        version_id: UUID,
        request: StatisticalPlanCreateRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> StatisticalPlanView:
        return service.create_plan(
            project_id=project_id,
            dataset_version_id=version_id,
            actor_user_id=principal.user_id,
            spec=request.spec,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/statistical-plans/{plan_id}/run",
        response_model=AnalysisRunView,
        status_code=201,
    )
    def run_statistical_analysis(
        project_id: UUID,
        plan_id: UUID,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> AnalysisRunView:
        return service.run_analysis(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
        )

    @router.get(
        "/dataset-versions/{version_id}/analyses",
        response_model=list[AnalysisRunView],
    )
    def list_analyses(
        project_id: UUID,
        version_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[AnalysisRunView]:
        return service.list_analyses(
            project_id=project_id,
            dataset_version_id=version_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/analyses/{analysis_id}/review",
        response_model=AnalysisReviewView,
    )
    def review_analysis(
        project_id: UUID,
        analysis_id: UUID,
        request: AnalysisReviewRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> AnalysisReviewView:
        return service.review_analysis(
            project_id=project_id,
            analysis_id=analysis_id,
            actor_user_id=principal.user_id,
            reviewer_role=request.reviewer_role,
            decision=request.decision,
            summary=request.summary,
            findings=request.findings,
            idempotency_key=idempotency_key,
        )

    return router
