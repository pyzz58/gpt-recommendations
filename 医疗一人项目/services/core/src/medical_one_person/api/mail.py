from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.mail import (
    MailAccountView,
    MailAttemptView,
    MailAuthorizationView,
    MailDraftView,
    MailSendResultView,
    MailService,
    MailThreadView,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.mail import (
    MailDraftSpec,
    MailSendAuthorizationSpec,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.mail.mock import MailAdapter


class MailDraftUpdateRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    spec: MailDraftSpec


class MailAuthorizationRequest(BaseModel):
    spec: MailSendAuthorizationSpec


class MailSendRequest(BaseModel):
    authorization_id: UUID


def build_mail_router(
    session_factory: sessionmaker[Session],
    store: LocalArtifactStore,
    adapter: MailAdapter,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects/{project_id}/mail", tags=["mail"])
    service = MailService(session_factory, store, adapter)

    @router.get("/account", response_model=MailAccountView)
    def mailbox(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailAccountView:
        return service.mailbox(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/inbox/sync-mock", response_model=list[MailThreadView])
    def sync_mock_inbox(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[MailThreadView]:
        return service.sync_mock_inbox(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.get("/threads", response_model=list[MailThreadView])
    def list_threads(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[MailThreadView]:
        return service.list_threads(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/threads/{thread_id}/link", response_model=MailThreadView)
    def link_thread(
        project_id: UUID,
        thread_id: UUID,
        expected_revision: int = Header(alias="X-Expected-Revision", ge=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailThreadView:
        return service.link_thread(
            project_id=project_id,
            thread_id=thread_id,
            actor_user_id=principal.user_id,
            expected_revision=expected_revision,
        )

    @router.get("/drafts", response_model=list[MailDraftView])
    def list_drafts(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[MailDraftView]:
        return service.list_drafts(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/drafts", response_model=MailDraftView, status_code=201)
    def create_draft(
        project_id: UUID,
        spec: MailDraftSpec,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailDraftView:
        return service.create_draft(
            project_id=project_id,
            actor_user_id=principal.user_id,
            spec=spec,
            idempotency_key=idempotency_key,
        )

    @router.put("/drafts/{draft_id}", response_model=MailDraftView)
    def update_draft(
        project_id: UUID,
        draft_id: UUID,
        request: MailDraftUpdateRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailDraftView:
        return service.update_draft(
            project_id=project_id,
            draft_id=draft_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            spec=request.spec,
        )

    @router.get(
        "/drafts/{draft_id}/authorizations",
        response_model=list[MailAuthorizationView],
    )
    def list_authorizations(
        project_id: UUID,
        draft_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[MailAuthorizationView]:
        return service.list_authorizations(
            project_id=project_id,
            draft_id=draft_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/drafts/{draft_id}/authorizations",
        response_model=MailAuthorizationView,
        status_code=201,
    )
    def authorize_draft(
        project_id: UUID,
        draft_id: UUID,
        request: MailAuthorizationRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailAuthorizationView:
        return service.authorize_draft(
            project_id=project_id,
            draft_id=draft_id,
            actor_user_id=principal.user_id,
            spec=request.spec,
            idempotency_key=idempotency_key,
        )

    @router.post(
        "/authorizations/{authorization_id}/revoke",
        response_model=MailAuthorizationView,
    )
    def revoke_authorization(
        project_id: UUID,
        authorization_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailAuthorizationView:
        return service.revoke_authorization(
            project_id=project_id,
            authorization_id=authorization_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/drafts/{draft_id}/send",
        response_model=MailSendResultView,
        status_code=201,
    )
    def send_draft(
        project_id: UUID,
        draft_id: UUID,
        request: MailSendRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailSendResultView:
        return service.send(
            project_id=project_id,
            draft_id=draft_id,
            authorization_id=request.authorization_id,
            actor_user_id=principal.user_id,
            idempotency_key=idempotency_key,
        )

    @router.get("/attempts", response_model=list[MailAttemptView])
    def list_attempts(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[MailAttemptView]:
        return service.list_attempts(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post(
        "/attempts/{attempt_id}/reconcile",
        response_model=MailSendResultView,
    )
    def reconcile_attempt(
        project_id: UUID,
        attempt_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> MailSendResultView:
        return service.reconcile(
            project_id=project_id,
            attempt_id=attempt_id,
            actor_user_id=principal.user_id,
        )

    return router
