from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.external import (
    ContactView,
    ContractView,
    DeliverableView,
    EngagementView,
    ExpertView,
    ExternalAuthorizationView,
    ExternalService,
    ExternalWorkspaceView,
    OrganizationView,
    ProfessionalRecordView,
    QuoteComparisonView,
    QuoteView,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.external import (
    ContactSpec,
    ContractSpec,
    ContractTransitionSpec,
    DeliverableReceiptSpec,
    DeliverableReviewSpec,
    DeliverableSpec,
    EngagementSpec,
    ExpertSpec,
    ExpertState,
    ExternalAuthorizationSpec,
    ExternalEngagementState,
    OrganizationSpec,
    ProfessionalRecordSpec,
    QuoteSpec,
)


class EngagementTransitionRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    state: ExternalEngagementState


class ExpertStateRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    state: ExpertState
    note: str = Field(min_length=1, max_length=5_000)


class DeliverableReceiptRequest(DeliverableReceiptSpec):
    expected_revision: int = Field(ge=1)


class DeliverableReviewRequest(DeliverableReviewSpec):
    expected_revision: int = Field(ge=1)


def build_external_router(
    session_factory: sessionmaker[Session],
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/projects/{project_id}/external",
        tags=["external"],
    )
    service = ExternalService(session_factory)

    @router.get("", response_model=ExternalWorkspaceView)
    def workspace(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ExternalWorkspaceView:
        return service.workspace(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/organizations", response_model=OrganizationView, status_code=201)
    def create_organization(
        project_id: UUID,
        spec: OrganizationSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> OrganizationView:
        return service.create_organization(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.post("/contacts", response_model=ContactView, status_code=201)
    def create_contact(
        project_id: UUID,
        spec: ContactSpec,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ContactView:
        return service.create_contact(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
        )

    @router.post("/experts", response_model=ExpertView, status_code=201)
    def create_expert(
        project_id: UUID,
        spec: ExpertSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ExpertView:
        return service.create_expert(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.put("/experts/{expert_id}/state", response_model=ExpertView)
    def update_expert_state(
        project_id: UUID,
        expert_id: UUID,
        request: ExpertStateRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ExpertView:
        return service.update_expert_state(
            project_id=project_id,
            expert_id=expert_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            state=request.state,
            note=request.note,
        )

    @router.post("/engagements", response_model=EngagementView, status_code=201)
    def create_engagement(
        project_id: UUID,
        spec: EngagementSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> EngagementView:
        return service.create_engagement(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.put("/engagements/{engagement_id}/state", response_model=EngagementView)
    def transition_engagement(
        project_id: UUID,
        engagement_id: UUID,
        request: EngagementTransitionRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> EngagementView:
        return service.transition_engagement(
            project_id=project_id,
            engagement_id=engagement_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            state=request.state,
        )

    @router.post("/quotes", response_model=QuoteView, status_code=201)
    def create_quote(
        project_id: UUID,
        spec: QuoteSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> QuoteView:
        return service.create_quote(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.get(
        "/engagements/{engagement_id}/quote-comparison",
        response_model=QuoteComparisonView,
    )
    def compare_quotes(
        project_id: UUID,
        engagement_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> QuoteComparisonView:
        return service.compare_quotes(
            project_id=project_id,
            engagement_id=engagement_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/contracts", response_model=ContractView, status_code=201)
    def create_contract(
        project_id: UUID,
        spec: ContractSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ContractView:
        return service.create_contract(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.put("/contracts/{contract_id}/state", response_model=ContractView)
    def transition_contract(
        project_id: UUID,
        contract_id: UUID,
        spec: ContractTransitionSpec,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ContractView:
        return service.transition_contract(
            project_id=project_id,
            contract_id=contract_id,
            actor_user_id=principal.user_id,
            spec=spec,
        )

    @router.post("/deliverables", response_model=DeliverableView, status_code=201)
    def create_deliverable(
        project_id: UUID,
        spec: DeliverableSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> DeliverableView:
        return service.create_deliverable(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/deliverables/{deliverable_id}/receive",
        response_model=DeliverableView,
    )
    def receive_deliverable(
        project_id: UUID,
        deliverable_id: UUID,
        request: DeliverableReceiptRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> DeliverableView:
        receipt = DeliverableReceiptSpec(
            knowledge_version_id=request.knowledge_version_id,
            manifest=request.manifest,
            missing_items=request.missing_items,
            summary=request.summary,
        )
        return service.receive_deliverable(
            project_id=project_id,
            deliverable_id=deliverable_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            spec=receipt,
        )

    @router.post(
        "/deliverables/{deliverable_id}/review",
        response_model=DeliverableView,
    )
    def review_deliverable(
        project_id: UUID,
        deliverable_id: UUID,
        request: DeliverableReviewRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> DeliverableView:
        review = DeliverableReviewSpec(
            decision=request.decision,
            reviewer_role=request.reviewer_role,
            summary=request.summary,
            findings=request.findings,
            missing_items=request.missing_items,
        )
        return service.review_deliverable(
            project_id=project_id,
            deliverable_id=deliverable_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            spec=review,
        )

    @router.post("/professional-records", response_model=ProfessionalRecordView, status_code=201)
    def create_professional_record(
        project_id: UUID,
        spec: ProfessionalRecordSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ProfessionalRecordView:
        return service.create_professional_record(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.post("/authorizations", response_model=ExternalAuthorizationView, status_code=201)
    def create_authorization(
        project_id: UUID,
        spec: ExternalAuthorizationSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ExternalAuthorizationView:
        return service.create_authorization(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/authorizations/{authorization_id}/revoke",
        response_model=ExternalAuthorizationView,
    )
    def revoke_authorization(
        project_id: UUID,
        authorization_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ExternalAuthorizationView:
        return service.revoke_authorization(
            project_id=project_id,
            authorization_id=authorization_id,
            actor_user_id=principal.user_id,
        )

    return router
