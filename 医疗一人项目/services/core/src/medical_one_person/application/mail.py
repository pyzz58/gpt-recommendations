from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
)
from medical_one_person.domain.mail import (
    MailAccountDescriptor,
    MailAccountState,
    MailAddressSet,
    MailAttemptState,
    MailAuthorizationState,
    MailDraftSpec,
    MailDraftState,
    MailMode,
    MailOutcomeUnknown,
    MailSendAuthorizationSpec,
    MailSendRejected,
    MailThreadLinkState,
    ProviderAttachment,
    ProviderMessage,
    ProviderSendRequest,
    ProviderSendResult,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Artifact,
    ArtifactVersion,
    KnowledgeBlob,
    KnowledgeDocumentVersion,
    MailAccount,
    MailDraft,
    MailDraftAttachment,
    MailMessage,
    MailSendAttempt,
    MailSendAuthorization,
    MailThread,
    Project,
    ProjectEvent,
    User,
)
from medical_one_person.infrastructure.mail.mock import MailAdapter


class MailAuthorizationError(Exception):
    pass


class MailAccountView(BaseModel):
    id: UUID
    address: str
    display_name: str
    provider_id: str
    mode: MailMode
    state: MailAccountState
    external_send_enabled: bool
    note: str


class MailAttachmentView(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    filename: str
    media_type: str
    size_bytes: int
    sha256: str


class MailMessageView(BaseModel):
    id: UUID
    provider_message_id: str
    internet_message_id: str | None
    in_reply_to: str | None
    references: list[str]
    direction: str
    sender: str
    recipients: MailAddressSet
    subject: str
    body_text: str
    body_sha256: str
    sent_at: datetime
    delivery_state: str
    synthetic: bool


class MailThreadView(BaseModel):
    id: UUID
    project_id: UUID | None
    provider_thread_id: str
    subject: str
    link_state: MailThreadLinkState
    revision: int
    last_message_at: datetime
    messages: list[MailMessageView]


class MailDraftView(BaseModel):
    id: UUID
    project_id: UUID
    account_id: UUID
    thread_id: UUID | None
    recipients: MailAddressSet
    subject: str
    body_text: str
    body_sha256: str
    content_sha256: str
    state: MailDraftState
    revision: int
    attachments: list[MailAttachmentView]
    created_at: datetime
    updated_at: datetime


class MailAuthorizationView(BaseModel):
    id: UUID
    project_id: UUID
    account_id: UUID
    draft_id: UUID
    action: str
    recipients: MailAddressSet
    attachment_hashes: list[str]
    content_sha256: str
    max_sends: int
    used_sends: int
    valid_from: datetime
    expires_at: datetime
    state: MailAuthorizationState
    revision: int
    created_at: datetime


class MailAttemptView(BaseModel):
    id: UUID
    project_id: UUID
    draft_id: UUID
    authorization_id: UUID
    state: MailAttemptState
    subject: str
    recipients: MailAddressSet
    body_sha256: str
    attachment_manifest: list[dict[str, Any]]
    provider_message_id: str | None
    provider_thread_id: str | None
    internet_message_id: str | None
    outcome_detail: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class MailDraftResponse(BaseModel):
    draft: MailDraftView
    authorization: MailAuthorizationView | None = None


class MailSendResultView(BaseModel):
    attempt: MailAttemptView
    draft_state: MailDraftState


class MailService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: LocalArtifactStore,
        adapter: MailAdapter,
    ) -> None:
        self._session_factory = session_factory
        self._store = store
        self._adapter = adapter

    def mailbox(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> MailAccountView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            account = _ensure_account(session, project, actor, self._adapter)
            descriptor = _account_descriptor(account)
            state = self._adapter.account_status(descriptor)
            account.state = state.value
            return _account_view(account, state, self._adapter)

    def sync_mock_inbox(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[MailThreadView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            account = _ensure_account(session, project, actor, self._adapter)
            if not self._adapter.receive_supported:
                return []
            descriptor = _account_descriptor(account)
            provider_threads = self._adapter.list_threads(descriptor)
            now = datetime.now(UTC)
            created = 0
            for provider_thread in provider_threads:
                thread = session.scalar(
                    select(MailThread).where(
                        MailThread.account_id == account.id,
                        MailThread.provider_thread_id
                        == provider_thread.provider_thread_id,
                    )
                )
                if thread is None:
                    thread = MailThread(
                        id=uuid4(),
                        workspace_id=actor.workspace_id,
                        account_id=account.id,
                        project_id=None,
                        provider_thread_id=provider_thread.provider_thread_id,
                        subject=provider_thread.subject,
                        link_state=MailThreadLinkState.UNLINKED.value,
                        revision=1,
                        last_message_at=provider_thread.last_message_at,
                        created_at=now,
                    )
                    session.add(thread)
                    session.flush()
                else:
                    thread.subject = provider_thread.subject
                    thread.last_message_at = max(
                        thread.last_message_at,
                        provider_thread.last_message_at,
                    )
                for message in provider_thread.messages:
                    if self._persist_provider_message(
                        session,
                        account=account,
                        thread=thread,
                        message=message,
                        now=now,
                    ):
                        created += 1
            if created:
                _append_event(
                    session,
                    project=project,
                    actor_user_id=actor.id,
                    event_type="mail.inbox_synced",
                    object_id=account.id,
                    object_revision=1,
                    payload={"created_messages": created, "mode": "mock"},
                    now=now,
                )
            return self._thread_views(session, project=project, account=account)

    def list_threads(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[MailThreadView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            account = _ensure_account(session, project, actor, self._adapter)
            return self._thread_views(session, project=project, account=account)

    def link_thread(
        self,
        *,
        project_id: UUID,
        thread_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
    ) -> MailThreadView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            account = _ensure_account(session, project, actor, self._adapter)
            thread = session.scalar(
                select(MailThread)
                .where(
                    MailThread.id == thread_id,
                    MailThread.account_id == account.id,
                )
                .with_for_update()
            )
            if thread is None or (
                thread.project_id is not None and thread.project_id != project.id
            ):
                raise NotFoundError("Mail thread not found")
            if thread.revision != expected_revision:
                raise ConflictingOperationError("Mail thread revision is stale")
            if thread.project_id is None:
                thread.project_id = project.id
                thread.link_state = MailThreadLinkState.LINKED.value
                thread.revision += 1
                _append_event(
                    session,
                    project=project,
                    actor_user_id=actor.id,
                    event_type="mail.thread_linked",
                    object_id=thread.id,
                    object_revision=thread.revision,
                    payload={"provider_thread_id_hash": _digest(thread.provider_thread_id)},
                    now=datetime.now(UTC),
                )
            return _thread_view(session, thread)

    def create_draft(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: MailDraftSpec,
        idempotency_key: str,
    ) -> MailDraftView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            account = _ensure_account(session, project, actor, self._adapter)
            existing = session.scalar(
                select(MailDraft)
                .where(
                    MailDraft.project_id == project.id,
                    MailDraft.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Mail draft idempotency key was reused with different parameters"
                    )
                return _draft_view(session, existing)
            thread = _thread_for_draft(
                session,
                project=project,
                account=account,
                thread_id=spec.thread_id,
            )
            resolved_attachments = self._resolve_attachments(
                session,
                project=project,
                sources=spec.attachments,
            )
            content_sha = _draft_content_hash(spec, resolved_attachments)
            now = datetime.now(UTC)
            draft = MailDraft(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                account_id=account.id,
                thread_id=thread.id if thread else None,
                created_by_user_id=actor.id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                recipients=_recipient_dict(spec),
                subject=spec.subject,
                body_text=spec.body_text,
                body_sha256=_sha_text(spec.body_text),
                content_sha256=content_sha,
                state=MailDraftState.DRAFT.value,
                revision=1,
                created_at=now,
                updated_at=now,
            )
            session.add(draft)
            session.flush()
            _insert_attachments(
                session,
                draft=draft,
                resolved=resolved_attachments,
                now=now,
            )
            adapter_draft_id = self._adapter.create_draft(
                _account_descriptor(account),
                str(draft.id),
            )
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.draft_created",
                object_id=draft.id,
                object_revision=draft.revision,
                payload={
                    "state": draft.state,
                    "attachment_count": len(resolved_attachments),
                    "provider_draft_id_hash": _digest(adapter_draft_id),
                },
                now=now,
            )
            return _draft_view(session, draft)

    def update_draft(
        self,
        *,
        project_id: UUID,
        draft_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        spec: MailDraftSpec,
    ) -> MailDraftView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            draft = _draft(session, project_id, draft_id, lock=True)
            if draft.revision != expected_revision:
                raise ConflictingOperationError("Mail draft revision is stale")
            if draft.state in {
                MailDraftState.SENDING.value,
                MailDraftState.SENT.value,
                MailDraftState.OUTCOME_UNKNOWN.value,
            }:
                raise ValueError("A sending, sent or uncertain draft cannot be edited")
            account = session.get(MailAccount, draft.account_id)
            if account is None:
                raise NotFoundError("Mail account not found")
            thread = _thread_for_draft(
                session,
                project=project,
                account=account,
                thread_id=spec.thread_id,
            )
            resolved_attachments = self._resolve_attachments(
                session,
                project=project,
                sources=spec.attachments,
            )
            session.query(MailDraftAttachment).filter(
                MailDraftAttachment.draft_id == draft.id
            ).delete(synchronize_session=False)
            now = datetime.now(UTC)
            _insert_attachments(
                session,
                draft=draft,
                resolved=resolved_attachments,
                now=now,
            )
            draft.thread_id = thread.id if thread else None
            draft.recipients = _recipient_dict(spec)
            draft.subject = spec.subject
            draft.body_text = spec.body_text
            draft.body_sha256 = _sha_text(spec.body_text)
            draft.content_sha256 = _draft_content_hash(spec, resolved_attachments)
            draft.request_hash = _digest(spec.model_dump(mode="json"))
            draft.state = MailDraftState.DRAFT.value
            draft.revision += 1
            draft.updated_at = now
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.draft_updated",
                object_id=draft.id,
                object_revision=draft.revision,
                payload={"content_sha256": draft.content_sha256},
                now=now,
            )
            return _draft_view(session, draft)

    def list_drafts(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[MailDraftView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            drafts = session.scalars(
                select(MailDraft)
                .where(MailDraft.project_id == project_id)
                .order_by(MailDraft.updated_at.desc())
            ).all()
            return [_draft_view(session, draft) for draft in drafts]

    def authorize_draft(
        self,
        *,
        project_id: UUID,
        draft_id: UUID,
        actor_user_id: UUID,
        spec: MailSendAuthorizationSpec,
        idempotency_key: str,
    ) -> MailAuthorizationView:
        request_hash = _digest(
            {
                "draft_id": str(draft_id),
                **spec.model_dump(mode="json"),
            }
        )
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            existing = session.scalar(
                select(MailSendAuthorization)
                .where(
                    MailSendAuthorization.project_id == project.id,
                    MailSendAuthorization.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Mail authorization key was reused with different parameters"
                    )
                return _authorization_view(existing, now=datetime.now(UTC))
            draft = _draft(session, project.id, draft_id, lock=True)
            if draft.state not in {
                MailDraftState.DRAFT.value,
                MailDraftState.READY.value,
                MailDraftState.FAILED.value,
            }:
                raise ValueError("Only an editable unsent draft can be authorized")
            attachment_hashes = sorted(
                session.scalars(
                    select(MailDraftAttachment.sha256).where(
                        MailDraftAttachment.draft_id == draft.id
                    )
                ).all()
            )
            now = datetime.now(UTC)
            expires_at = now + timedelta(minutes=spec.expires_in_minutes)
            authorization = MailSendAuthorization(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                account_id=draft.account_id,
                draft_id=draft.id,
                granted_by_user_id=actor.id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                action="mail.send",
                recipients=draft.recipients,
                attachment_hashes=attachment_hashes,
                content_sha256=draft.content_sha256,
                max_sends=spec.max_sends,
                used_sends=0,
                valid_from=now,
                expires_at=expires_at,
                state=MailAuthorizationState.ACTIVE.value,
                revision=1,
                created_at=now,
            )
            session.add(authorization)
            draft.state = MailDraftState.READY.value
            draft.revision += 1
            draft.updated_at = now
            session.flush()
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.authorization_granted",
                object_id=authorization.id,
                object_revision=authorization.revision,
                payload={
                    "draft_id": str(draft.id),
                    "max_sends": authorization.max_sends,
                    "expires_at": expires_at.isoformat(),
                    "attachment_count": len(attachment_hashes),
                },
                now=now,
            )
            return _authorization_view(authorization, now=now)

    def revoke_authorization(
        self,
        *,
        project_id: UUID,
        authorization_id: UUID,
        actor_user_id: UUID,
    ) -> MailAuthorizationView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            authorization = session.scalar(
                select(MailSendAuthorization)
                .where(
                    MailSendAuthorization.id == authorization_id,
                    MailSendAuthorization.project_id == project.id,
                )
                .with_for_update()
            )
            if authorization is None:
                raise NotFoundError("Mail authorization not found")
            if authorization.state == MailAuthorizationState.ACTIVE.value:
                authorization.state = MailAuthorizationState.REVOKED.value
                authorization.revision += 1
                _append_event(
                    session,
                    project=project,
                    actor_user_id=actor.id,
                    event_type="mail.authorization_revoked",
                    object_id=authorization.id,
                    object_revision=authorization.revision,
                    payload={"draft_id": str(authorization.draft_id)},
                    now=datetime.now(UTC),
                )
            return _authorization_view(authorization, now=datetime.now(UTC))

    def list_authorizations(
        self,
        *,
        project_id: UUID,
        draft_id: UUID,
        actor_user_id: UUID,
    ) -> list[MailAuthorizationView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            draft = _draft(session, project_id, draft_id)
            authorizations = session.scalars(
                select(MailSendAuthorization)
                .where(
                    MailSendAuthorization.draft_id == draft.id,
                    MailSendAuthorization.project_id == project_id,
                )
                .order_by(MailSendAuthorization.created_at.desc())
            ).all()
            now = datetime.now(UTC)
            return [
                _authorization_view(authorization, now=now)
                for authorization in authorizations
            ]

    def send(
        self,
        *,
        project_id: UUID,
        draft_id: UUID,
        authorization_id: UUID,
        actor_user_id: UUID,
        idempotency_key: str,
    ) -> MailSendResultView:
        request_hash = _digest(
            {
                "draft_id": str(draft_id),
                "authorization_id": str(authorization_id),
            }
        )
        request, attempt_id, account = self._prepare_send(
            project_id=project_id,
            draft_id=draft_id,
            authorization_id=authorization_id,
            actor_user_id=actor_user_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if request is None:
            with self._session_factory.begin() as session:
                actor = _owner(session, actor_user_id)
                set_rls_context(
                    session,
                    workspace_id=actor.workspace_id,
                    user_id=actor.id,
                )
                attempt = _attempt(session, project_id, attempt_id)
                draft = _draft(session, project_id, attempt.draft_id)
                return MailSendResultView(
                    attempt=_attempt_view(attempt),
                    draft_state=MailDraftState(draft.state),
                )
        try:
            result = self._adapter.send(request)
        except MailOutcomeUnknown as exc:
            self._mark_attempt_unknown(
                attempt_id=attempt_id,
                actor_user_id=actor_user_id,
                project_id=project_id,
                detail=f"{exc}; provider_message_id={exc.provider_message_id or 'unknown'}",
            )
            return self.send(
                project_id=project_id,
                draft_id=draft_id,
                authorization_id=authorization_id,
                actor_user_id=actor_user_id,
                idempotency_key=idempotency_key,
            )
        except MailSendRejected as exc:
            self._mark_attempt_failed(
                attempt_id=attempt_id,
                actor_user_id=actor_user_id,
                project_id=project_id,
                detail=str(exc),
            )
            raise ValueError(f"Mail provider rejected the draft: {exc}") from exc
        except Exception as exc:
            self._mark_attempt_unknown(
                attempt_id=attempt_id,
                actor_user_id=actor_user_id,
                project_id=project_id,
                detail=f"Unexpected provider exception: {type(exc).__name__}",
            )
            return self.send(
                project_id=project_id,
                draft_id=draft_id,
                authorization_id=authorization_id,
                actor_user_id=actor_user_id,
                idempotency_key=idempotency_key,
            )
        self._mark_attempt_sent(
            attempt_id=attempt_id,
            actor_user_id=actor_user_id,
            project_id=project_id,
            result=result,
        )
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            attempt = _attempt(session, project_id, attempt_id)
            draft = _draft(session, project_id, attempt.draft_id)
            return MailSendResultView(
                attempt=_attempt_view(attempt),
                draft_state=MailDraftState(draft.state),
            )

    def reconcile(
        self,
        *,
        project_id: UUID,
        attempt_id: UUID,
        actor_user_id: UUID,
    ) -> MailSendResultView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            attempt = _attempt(session, project_id, attempt_id)
            if attempt.state == MailAttemptState.SENT.value:
                draft = _draft(session, project_id, attempt.draft_id)
                return MailSendResultView(
                    attempt=_attempt_view(attempt),
                    draft_state=MailDraftState(draft.state),
                )
            if attempt.state != MailAttemptState.OUTCOME_UNKNOWN.value:
                raise ValueError("Only an outcome_unknown attempt can be reconciled")
            operation_key = str(attempt.operation_key)
            provider_message_id = attempt.provider_message_id
        result = self._adapter.reconcile_send(
            operation_key=operation_key,
            provider_message_id=provider_message_id,
        )
        if result.state == "sent" and result.result is not None:
            self._mark_attempt_sent(
                attempt_id=attempt_id,
                actor_user_id=actor_user_id,
                project_id=project_id,
                result=result.result,
            )
        elif result.state == "not_found":
            self._mark_attempt_not_sent(
                attempt_id=attempt_id,
                actor_user_id=actor_user_id,
                project_id=project_id,
            )
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            attempt = _attempt(session, project_id, attempt_id)
            draft = _draft(session, project_id, attempt.draft_id)
            return MailSendResultView(
                attempt=_attempt_view(attempt),
                draft_state=MailDraftState(draft.state),
            )

    def list_attempts(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> list[MailAttemptView]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            attempts = session.scalars(
                select(MailSendAttempt)
                .where(MailSendAttempt.project_id == project_id)
                .order_by(MailSendAttempt.created_at.desc())
            ).all()
            return [_attempt_view(attempt) for attempt in attempts]

    def _prepare_send(
        self,
        *,
        project_id: UUID,
        draft_id: UUID,
        authorization_id: UUID,
        actor_user_id: UUID,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[ProviderSendRequest | None, UUID, MailAccount]:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            draft = _draft(session, project.id, draft_id, lock=True)
            authorization = session.scalar(
                select(MailSendAuthorization)
                .where(
                    MailSendAuthorization.id == authorization_id,
                    MailSendAuthorization.project_id == project.id,
                )
                .with_for_update()
            )
            if authorization is None:
                raise NotFoundError("Mail authorization not found")
            existing = session.scalar(
                select(MailSendAttempt)
                .where(
                    MailSendAttempt.project_id == project.id,
                    MailSendAttempt.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Mail send idempotency key was reused with different parameters"
                    )
                return None, existing.id, _account(session, authorization.account_id)
            if draft.state in {
                MailDraftState.SENDING.value,
                MailDraftState.SENT.value,
                MailDraftState.OUTCOME_UNKNOWN.value,
            }:
                raise ConflictingOperationError("Mail draft cannot be sent in its current state")
            now = datetime.now(UTC)
            if authorization.state == MailAuthorizationState.ACTIVE.value and (
                authorization.expires_at <= now
            ):
                authorization.state = MailAuthorizationState.EXPIRED.value
                authorization.revision += 1
            if authorization.state != MailAuthorizationState.ACTIVE.value:
                raise MailAuthorizationError(
                    f"Mail authorization is {authorization.state}, not active"
                )
            if authorization.used_sends >= authorization.max_sends:
                authorization.state = MailAuthorizationState.EXHAUSTED.value
                raise MailAuthorizationError("Mail authorization send limit is exhausted")
            if (
                authorization.draft_id != draft.id
                or authorization.account_id != draft.account_id
                or authorization.content_sha256 != draft.content_sha256
                or authorization.recipients != draft.recipients
            ):
                raise MailAuthorizationError(
                    "Mail authorization no longer covers the draft content or recipients"
                )
            attachments = list(
                session.scalars(
                    select(MailDraftAttachment)
                    .where(MailDraftAttachment.draft_id == draft.id)
                    .order_by(MailDraftAttachment.created_at)
                ).all()
            )
            attachment_hashes = sorted(attachment.sha256 for attachment in attachments)
            if attachment_hashes != sorted(authorization.attachment_hashes):
                raise MailAuthorizationError("Mail authorization does not cover attachments")
            account = _account(session, draft.account_id)
            if self._adapter.account_status(_account_descriptor(account)) not in {
                MailAccountState.MOCK_READY,
                MailAccountState.CONNECTED,
                MailAccountState.SEND_ONLY,
            }:
                raise ValueError("Mail account is not available")
            provider_attachments = tuple(
                ProviderAttachment(
                    filename=attachment.filename,
                    media_type=attachment.media_type,
                    content=self._store.read(attachment.object_key, attachment.sha256),
                    sha256=attachment.sha256,
                )
                for attachment in attachments
            )
            thread = session.get(MailThread, draft.thread_id) if draft.thread_id else None
            provider_thread_id = thread.provider_thread_id if thread else None
            latest_message = (
                session.scalar(
                    select(MailMessage)
                    .where(MailMessage.thread_id == thread.id)
                    .order_by(MailMessage.sent_at.desc())
                    .limit(1)
                )
                if thread
                else None
            )
            attempt_id = uuid4()
            operation_key = uuid4()
            manifest = [
                {
                    "filename": attachment.filename,
                    "media_type": attachment.media_type,
                    "size_bytes": attachment.size_bytes,
                    "sha256": attachment.sha256,
                }
                for attachment in attachments
            ]
            session.add(
                MailSendAttempt(
                    id=attempt_id,
                    workspace_id=actor.workspace_id,
                    project_id=project.id,
                    draft_id=draft.id,
                    authorization_id=authorization.id,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    operation_key=operation_key,
                    state=MailAttemptState.SENDING.value,
                    recipients=draft.recipients,
                    subject=draft.subject,
                    body_sha256=draft.body_sha256,
                    attachment_manifest=manifest,
                    created_at=now,
                    started_at=now,
                )
            )
            authorization.used_sends += 1
            authorization.revision += 1
            if authorization.used_sends >= authorization.max_sends:
                authorization.state = MailAuthorizationState.EXHAUSTED.value
            draft.state = MailDraftState.SENDING.value
            draft.revision += 1
            draft.updated_at = now
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.send_started",
                object_id=attempt_id,
                object_revision=1,
                payload={
                    "draft_id": str(draft.id),
                    "authorization_id": str(authorization.id),
                    "mode": "mock",
                },
                now=now,
            )
            return (
                ProviderSendRequest(
                    operation_key=str(operation_key),
                    account=_account_descriptor(account),
                    draft_id=draft.id,
                    provider_thread_id=provider_thread_id,
                    in_reply_to=latest_message.internet_message_id
                    if latest_message
                    else None,
                    references=tuple(latest_message.references)
                    if latest_message
                    else (),
                    recipients=MailAddressSet.model_validate(draft.recipients),
                    subject=draft.subject,
                    body_text=draft.body_text,
                    body_sha256=draft.body_sha256,
                    attachments=provider_attachments,
                ),
                attempt_id,
                account,
            )

    def _resolve_attachments(
        self,
        session: Session,
        *,
        project: Project,
        sources: list[Any],
    ) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        seen: set[tuple[str, UUID]] = set()
        for source in sources:
            key = (source.source_type, source.source_id)
            if key in seen:
                continue
            seen.add(key)
            if source.source_type == "artifact_version":
                artifact_row = session.execute(
                    select(ArtifactVersion, Artifact)
                    .join(Artifact, Artifact.id == ArtifactVersion.artifact_id)
                    .where(
                        ArtifactVersion.id == source.source_id,
                        ArtifactVersion.project_id == project.id,
                    )
                ).one_or_none()
                if artifact_row is None:
                    raise NotFoundError("Mail attachment artifact version not found")
                artifact_version, artifact = artifact_row
                filename = _artifact_filename(
                    artifact.title,
                    artifact_version.media_type,
                )
                resolved.append(
                    {
                        "source_type": source.source_type,
                        "source_id": source.source_id,
                        "filename": filename,
                        "media_type": artifact_version.media_type,
                        "size_bytes": artifact_version.size_bytes,
                        "sha256": artifact_version.sha256,
                        "object_key": artifact_version.object_key,
                    }
                )
            else:
                knowledge_row = session.execute(
                    select(KnowledgeDocumentVersion, KnowledgeBlob)
                    .join(
                        KnowledgeBlob,
                        KnowledgeBlob.id == KnowledgeDocumentVersion.blob_id,
                    )
                    .where(
                        KnowledgeDocumentVersion.id == source.source_id,
                        KnowledgeDocumentVersion.project_id == project.id,
                        KnowledgeDocumentVersion.access_state == "active",
                    )
                ).one_or_none()
                if knowledge_row is None:
                    raise NotFoundError("Mail attachment knowledge version not found")
                knowledge_version, blob = knowledge_row
                resolved.append(
                    {
                        "source_type": source.source_type,
                        "source_id": source.source_id,
                        "filename": knowledge_version.filename,
                        "media_type": knowledge_version.media_type,
                        "size_bytes": knowledge_version.size_bytes,
                        "sha256": knowledge_version.content_hash,
                        "object_key": blob.object_key,
                    }
                )
        return resolved

    def _thread_views(
        self,
        session: Session,
        *,
        project: Project,
        account: MailAccount,
    ) -> list[MailThreadView]:
        threads = session.scalars(
            select(MailThread)
            .where(
                MailThread.account_id == account.id,
                or_(
                    MailThread.project_id.is_(None),
                    MailThread.project_id == project.id,
                ),
            )
            .order_by(MailThread.last_message_at.desc())
        ).all()
        return [_thread_view(session, thread) for thread in threads]

    def _mark_attempt_sent(
        self,
        *,
        attempt_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        result: ProviderSendResult,
    ) -> None:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            attempt = session.scalar(
                select(MailSendAttempt)
                .where(MailSendAttempt.id == attempt_id)
                .with_for_update()
            )
            if attempt is None:
                raise NotFoundError("Mail attempt not found")
            draft = _draft(session, project.id, attempt.draft_id, lock=True)
            if attempt.state == MailAttemptState.SENT.value:
                return
            now = datetime.now(UTC)
            thread = session.scalar(
                select(MailThread).where(
                    MailThread.account_id == draft.account_id,
                    MailThread.provider_thread_id == result.provider_thread_id,
                )
            )
            if thread is None:
                thread = MailThread(
                    id=uuid4(),
                    workspace_id=actor.workspace_id,
                    account_id=draft.account_id,
                    project_id=project.id,
                    provider_thread_id=result.provider_thread_id,
                    subject=attempt.subject,
                    link_state=MailThreadLinkState.LINKED.value,
                    revision=1,
                    last_message_at=result.sent_at,
                    created_at=now,
                )
                session.add(thread)
                session.flush()
            elif thread.project_id not in {None, project.id}:
                raise MailAuthorizationError("Provider thread belongs to another project")
            else:
                thread.project_id = project.id
                thread.link_state = MailThreadLinkState.LINKED.value
                thread.last_message_at = result.sent_at
            account = _account(session, draft.account_id)
            existing_message = session.scalar(
                select(MailMessage).where(
                    MailMessage.account_id == draft.account_id,
                    MailMessage.provider_message_id == result.provider_message_id,
                )
            )
            if existing_message is None:
                session.add(
                    MailMessage(
                        id=uuid4(),
                        workspace_id=actor.workspace_id,
                        account_id=draft.account_id,
                        thread_id=thread.id,
                        provider_message_id=result.provider_message_id,
                        internet_message_id=result.internet_message_id,
                        in_reply_to=None,
                        references=[],
                        direction="outbound",
                        sender=account.address,
                        recipients=attempt.recipients,
                        subject=attempt.subject,
                        body_text=draft.body_text,
                        body_sha256=draft.body_sha256,
                        sent_at=result.sent_at,
                        received_at=now,
                        delivery_state="mock_sent",
                        raw_headers={"Message-ID": result.internet_message_id},
                        created_at=now,
                    )
                )
            attempt.state = MailAttemptState.SENT.value
            attempt.provider_message_id = result.provider_message_id
            attempt.provider_thread_id = result.provider_thread_id
            attempt.internet_message_id = result.internet_message_id
            attempt.completed_at = now
            draft.state = MailDraftState.SENT.value
            draft.thread_id = thread.id
            draft.revision += 1
            draft.updated_at = now
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.send_completed",
                object_id=attempt.id,
                object_revision=1,
                payload={
                    "draft_id": str(draft.id),
                    "provider_message_id_hash": _digest(result.provider_message_id),
                    "mode": "mock",
                },
                now=now,
            )

    def _mark_attempt_unknown(
        self,
        *,
        attempt_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        detail: str,
    ) -> None:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            attempt = session.scalar(
                select(MailSendAttempt)
                .where(MailSendAttempt.id == attempt_id)
                .with_for_update()
            )
            if attempt is None:
                raise NotFoundError("Mail attempt not found")
            if attempt.state != MailAttemptState.SENDING.value:
                return
            now = datetime.now(UTC)
            attempt.state = MailAttemptState.OUTCOME_UNKNOWN.value
            attempt.outcome_detail = detail[:10_000]
            draft = _draft(session, project.id, attempt.draft_id, lock=True)
            draft.state = MailDraftState.OUTCOME_UNKNOWN.value
            draft.revision += 1
            draft.updated_at = now
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.send_outcome_unknown",
                object_id=attempt.id,
                object_revision=1,
                payload={"draft_id": str(draft.id), "mode": "mock"},
                now=now,
            )

    def _mark_attempt_failed(
        self,
        *,
        attempt_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        detail: str,
    ) -> None:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            attempt = session.scalar(
                select(MailSendAttempt)
                .where(MailSendAttempt.id == attempt_id)
                .with_for_update()
            )
            if attempt is None:
                raise NotFoundError("Mail attempt not found")
            if attempt.state != MailAttemptState.SENDING.value:
                return
            authorization = session.get(MailSendAuthorization, attempt.authorization_id)
            now = datetime.now(UTC)
            attempt.state = MailAttemptState.FAILED.value
            attempt.outcome_detail = detail[:10_000]
            attempt.completed_at = now
            draft = _draft(session, project.id, attempt.draft_id, lock=True)
            draft.state = MailDraftState.FAILED.value
            draft.revision += 1
            draft.updated_at = now
            if authorization is not None and authorization.used_sends > 0:
                authorization.used_sends -= 1
                authorization.revision += 1
                if authorization.state == MailAuthorizationState.EXHAUSTED.value:
                    authorization.state = MailAuthorizationState.ACTIVE.value
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.send_failed",
                object_id=attempt.id,
                object_revision=1,
                payload={"draft_id": str(draft.id), "error": "PROVIDER_REJECTED"},
                now=now,
            )

    def _mark_attempt_not_sent(
        self,
        *,
        attempt_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
    ) -> None:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            attempt = session.scalar(
                select(MailSendAttempt)
                .where(MailSendAttempt.id == attempt_id)
                .with_for_update()
            )
            if attempt is None:
                raise NotFoundError("Mail attempt not found")
            if attempt.state != MailAttemptState.OUTCOME_UNKNOWN.value:
                return
            now = datetime.now(UTC)
            attempt.state = MailAttemptState.NOT_SENT.value
            attempt.outcome_detail = "Provider reconciliation found no delivered message"
            attempt.completed_at = now
            authorization = session.get(MailSendAuthorization, attempt.authorization_id)
            draft = _draft(session, project.id, attempt.draft_id, lock=True)
            draft.state = MailDraftState.FAILED.value
            draft.revision += 1
            draft.updated_at = now
            if authorization is not None and authorization.used_sends > 0:
                authorization.used_sends -= 1
                authorization.revision += 1
                if authorization.state == MailAuthorizationState.EXHAUSTED.value:
                    authorization.state = MailAuthorizationState.ACTIVE.value
            _append_event(
                session,
                project=project,
                actor_user_id=actor.id,
                event_type="mail.send_reconciled",
                object_id=attempt.id,
                object_revision=1,
                payload={"draft_id": str(draft.id), "result": "not_sent"},
                now=now,
            )

    def _persist_provider_message(
        self,
        session: Session,
        *,
        account: MailAccount,
        thread: MailThread,
        message: ProviderMessage,
        now: datetime,
    ) -> bool:
        existing = session.scalar(
            select(MailMessage).where(
                MailMessage.account_id == account.id,
                MailMessage.provider_message_id == message.provider_message_id,
            )
        )
        if existing is not None:
            return False
        direction = "outbound" if message.sender == account.address else "inbound"
        session.add(
            MailMessage(
                id=uuid4(),
                workspace_id=account.workspace_id,
                account_id=account.id,
                thread_id=thread.id,
                provider_message_id=message.provider_message_id,
                internet_message_id=message.internet_message_id,
                in_reply_to=message.in_reply_to,
                references=list(message.references),
                direction=direction,
                sender=message.sender,
                recipients=message.recipients.model_dump(mode="json"),
                subject=message.subject,
                body_text=message.body_text,
                body_sha256=_sha_text(message.body_text),
                sent_at=message.sent_at,
                received_at=now,
                delivery_state="mock_received" if direction == "inbound" else "mock_sent",
                raw_headers=message.raw_headers,
                created_at=now,
            )
        )
        return True


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage mail")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _ensure_account(
    session: Session,
    project: Project,
    actor: User,
    adapter: MailAdapter,
) -> MailAccount:
    del project
    account_mode = MailMode(adapter.account_mode)
    address = adapter.default_address
    if address is None:
        raise ValueError("Mail adapter has no configured sender address")
    account = session.scalar(
        select(MailAccount).where(
            MailAccount.workspace_id == actor.workspace_id,
            MailAccount.owner_user_id == actor.id,
            MailAccount.mode == account_mode.value,
        )
    )
    if account is None:
        now = datetime.now(UTC)
        account = MailAccount(
            id=uuid4(),
            workspace_id=actor.workspace_id,
            owner_user_id=actor.id,
            provider_id=adapter.adapter_id,
            address=address,
            display_name=(
                f"{actor.display_name}（模拟邮箱）"
                if account_mode == MailMode.MOCK
                else f"{actor.display_name}（SMTP发件）"
            ),
            mode=account_mode.value,
            state=(
                MailAccountState.MOCK_READY.value
                if account_mode == MailMode.MOCK
                else MailAccountState.UNCONFIGURED.value
            ),
            credential_ref=None,
            created_at=now,
            updated_at=now,
        )
        session.add(account)
        session.flush()
    return account


def _account(session: Session, account_id: UUID) -> MailAccount:
    account = session.get(MailAccount, account_id)
    if account is None:
        raise NotFoundError("Mail account not found")
    return account


def _account_descriptor(account: MailAccount) -> MailAccountDescriptor:
    return MailAccountDescriptor(
        account_id=account.id,
        workspace_id=account.workspace_id,
        address=account.address,
        display_name=account.display_name,
        mode=MailMode(account.mode),
    )


def _account_view(
    account: MailAccount,
    state: MailAccountState,
    adapter: MailAdapter,
) -> MailAccountView:
    external_send_enabled = state in {
        MailAccountState.CONNECTED,
        MailAccountState.SEND_ONLY,
    }
    return MailAccountView(
        id=account.id,
        address=account.address,
        display_name=account.display_name,
        provider_id=account.provider_id,
        mode=MailMode(account.mode),
        state=state,
        external_send_enabled=external_send_enabled,
        note=(
            "SMTP outbound is configured; inbox receive is unavailable. "
            "Every send still requires a valid project authorization."
            if adapter.account_mode == "live"
            else (
                "Local deterministic mock mailbox. Draft, authorization and simulated "
                "delivery are recorded; no external message is sent."
            )
        ),
    )


def _thread_for_draft(
    session: Session,
    *,
    project: Project,
    account: MailAccount,
    thread_id: UUID | None,
) -> MailThread | None:
    if thread_id is None:
        return None
    thread = session.scalar(
        select(MailThread).where(
            MailThread.id == thread_id,
            MailThread.account_id == account.id,
        )
    )
    if thread is None or (
        thread.project_id is not None and thread.project_id != project.id
    ):
        raise NotFoundError("Mail thread not found")
    return thread


def _thread_view(session: Session, thread: MailThread) -> MailThreadView:
    messages = session.scalars(
        select(MailMessage)
        .where(MailMessage.thread_id == thread.id)
        .order_by(MailMessage.sent_at, MailMessage.created_at)
    ).all()
    return MailThreadView(
        id=thread.id,
        project_id=thread.project_id,
        provider_thread_id=thread.provider_thread_id,
        subject=thread.subject,
        link_state=MailThreadLinkState(thread.link_state),
        revision=thread.revision,
        last_message_at=thread.last_message_at,
        messages=[_message_view(message) for message in messages],
    )


def _message_view(message: MailMessage) -> MailMessageView:
    return MailMessageView(
        id=message.id,
        provider_message_id=message.provider_message_id,
        internet_message_id=message.internet_message_id,
        in_reply_to=message.in_reply_to,
        references=message.references,
        direction=message.direction,
        sender=message.sender,
        recipients=MailAddressSet.model_validate(message.recipients),
        subject=message.subject,
        body_text=message.body_text,
        body_sha256=message.body_sha256,
        sent_at=message.sent_at,
        delivery_state=message.delivery_state,
        synthetic=message.delivery_state.startswith("mock_"),
    )


def _draft(session: Session, project_id: UUID, draft_id: UUID, *, lock: bool = False) -> MailDraft:
    statement = select(MailDraft).where(
        MailDraft.id == draft_id,
        MailDraft.project_id == project_id,
    )
    if lock:
        statement = statement.with_for_update()
    draft = session.scalar(statement)
    if draft is None:
        raise NotFoundError("Mail draft not found")
    return draft


def _attempt(session: Session, project_id: UUID, attempt_id: UUID) -> MailSendAttempt:
    attempt = session.scalar(
        select(MailSendAttempt).where(
            MailSendAttempt.id == attempt_id,
            MailSendAttempt.project_id == project_id,
        )
    )
    if attempt is None:
        raise NotFoundError("Mail attempt not found")
    return attempt


def _draft_view(session: Session, draft: MailDraft) -> MailDraftView:
    attachments = session.scalars(
        select(MailDraftAttachment)
        .where(MailDraftAttachment.draft_id == draft.id)
        .order_by(MailDraftAttachment.created_at)
    ).all()
    return MailDraftView(
        id=draft.id,
        project_id=draft.project_id,
        account_id=draft.account_id,
        thread_id=draft.thread_id,
        recipients=MailAddressSet.model_validate(draft.recipients),
        subject=draft.subject,
        body_text=draft.body_text,
        body_sha256=draft.body_sha256,
        content_sha256=draft.content_sha256,
        state=MailDraftState(draft.state),
        revision=draft.revision,
        attachments=[
            MailAttachmentView(
                id=attachment.id,
                source_type=attachment.source_type,
                source_id=attachment.source_id,
                filename=attachment.filename,
                media_type=attachment.media_type,
                size_bytes=attachment.size_bytes,
                sha256=attachment.sha256,
            )
            for attachment in attachments
        ],
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _authorization_view(
    authorization: MailSendAuthorization,
    *,
    now: datetime,
) -> MailAuthorizationView:
    state = MailAuthorizationState(authorization.state)
    if state == MailAuthorizationState.ACTIVE and authorization.expires_at <= now:
        state = MailAuthorizationState.EXPIRED
    return MailAuthorizationView(
        id=authorization.id,
        project_id=authorization.project_id,
        account_id=authorization.account_id,
        draft_id=authorization.draft_id,
        action=authorization.action,
        recipients=MailAddressSet.model_validate(authorization.recipients),
        attachment_hashes=authorization.attachment_hashes,
        content_sha256=authorization.content_sha256,
        max_sends=authorization.max_sends,
        used_sends=authorization.used_sends,
        valid_from=authorization.valid_from,
        expires_at=authorization.expires_at,
        state=state,
        revision=authorization.revision,
        created_at=authorization.created_at,
    )


def _attempt_view(attempt: MailSendAttempt) -> MailAttemptView:
    return MailAttemptView(
        id=attempt.id,
        project_id=attempt.project_id,
        draft_id=attempt.draft_id,
        authorization_id=attempt.authorization_id,
        state=MailAttemptState(attempt.state),
        subject=attempt.subject,
        recipients=MailAddressSet.model_validate(attempt.recipients),
        body_sha256=attempt.body_sha256,
        attachment_manifest=attempt.attachment_manifest,
        provider_message_id=attempt.provider_message_id,
        provider_thread_id=attempt.provider_thread_id,
        internet_message_id=attempt.internet_message_id,
        outcome_detail=attempt.outcome_detail,
        created_at=attempt.created_at,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
    )


def _recipient_dict(spec: MailDraftSpec) -> dict[str, list[str]]:
    return {
        "to": spec.to_addresses,
        "cc": spec.cc_addresses,
        "bcc": spec.bcc_addresses,
    }


def _draft_content_hash(
    spec: MailDraftSpec,
    attachments: list[dict[str, Any]],
) -> str:
    return _digest(
        {
            "recipients": _recipient_dict(spec),
            "subject": spec.subject,
            "body_sha256": _sha_text(spec.body_text),
            "attachments": sorted(
                (
                    {
                        "source_type": attachment["source_type"],
                        "source_id": str(attachment["source_id"]),
                        "sha256": attachment["sha256"],
                    }
                    for attachment in attachments
                ),
                key=lambda item: (item["source_type"], item["source_id"]),
            ),
        }
    )


def _insert_attachments(
    session: Session,
    *,
    draft: MailDraft,
    resolved: list[dict[str, Any]],
    now: datetime,
) -> None:
    for attachment in resolved:
        session.add(
            MailDraftAttachment(
                id=uuid4(),
                workspace_id=draft.workspace_id,
                project_id=draft.project_id,
                draft_id=draft.id,
                source_type=attachment["source_type"],
                source_id=attachment["source_id"],
                filename=attachment["filename"],
                media_type=attachment["media_type"],
                size_bytes=attachment["size_bytes"],
                sha256=attachment["sha256"],
                object_key=attachment["object_key"],
                created_at=now,
            )
        )
    session.flush()


def _artifact_filename(title: str, media_type: str) -> str:
    extension = {
        "application/pdf": "pdf",
        (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ): "docx",
        (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ): "pptx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }.get(media_type, "bin")
    safe = "".join(
        character if character not in {'"', "\\", "/", "\n", "\r"} else "-"
        for character in title
    ).strip(" .")
    return f"{safe or 'attachment'}.{extension}"


def _append_event(
    session: Session,
    *,
    project: Project,
    actor_user_id: UUID,
    event_type: str,
    object_id: UUID,
    object_revision: int,
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
            object_type="mail",
            object_id=object_id,
            object_revision=object_revision,
            payload=payload,
            correlation_id=uuid4(),
            created_at=now,
        )
    )


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value: Any) -> str:
    return _sha_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    )
