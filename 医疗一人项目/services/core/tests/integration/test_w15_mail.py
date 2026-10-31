from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.artifacts import ArtifactService
from medical_one_person.application.errors import NotFoundError
from medical_one_person.application.mail import MailAuthorizationError, MailService
from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.artifacts import ArtifactMode, ArtifactOrigin
from medical_one_person.domain.mail import (
    MailAttachmentSource,
    MailDraftSpec,
    MailDraftState,
    MailSendAuthorizationSpec,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    MailMessage,
    MailSendAttempt,
    MailSendAuthorization,
)
from medical_one_person.infrastructure.mail.mock import (
    MockMailAdapter,
    MockSendOutcome,
)


def _draft_spec(attachment_id=None) -> MailDraftSpec:
    return MailDraftSpec(
        to_addresses=["expert@example.test"],
        subject="合成专家问题",
        body_text="请界定这个合成问题需要哪些真实数据。本邮件仅用于本地模拟。",
        attachments=(
            [
                MailAttachmentSource(
                    source_type="artifact_version",
                    source_id=attachment_id,
                )
            ]
            if attachment_id
            else []
        ),
    )


def test_mock_mail_draft_requires_explicit_send_authorization_and_attachment_hash(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W15邮件项目",
        scope="验证草稿、授权、附件与模拟发送。",
        idempotency_key="w15-mail-project",
    )
    store = LocalArtifactStore(tmp_path / "mail-artifacts")
    artifact = ArtifactService(session_factory, store).create_version(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        title="合成专家材料",
        media_type="application/pdf",
        content=b"%PDF-1.7\nsynthetic attachment\n",
        mode=ArtifactMode.MOCK,
        origin=ArtifactOrigin.DERIVED,
        producer="w15-test",
    )
    adapter = MockMailAdapter()
    service = MailService(session_factory, store, adapter)

    account = service.mailbox(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert account.mode.value == "mock"
    assert account.external_send_enabled is False
    threads = service.sync_mock_inbox(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert len(threads) == 1
    assert len(threads[0].messages) == 2
    assert all(message.synthetic for message in threads[0].messages)
    assert [message.direction for message in threads[0].messages] == [
        "inbound",
        "outbound",
    ]

    draft = service.create_draft(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=_draft_spec(artifact.id),
        idempotency_key="w15-draft-1",
    )
    assert draft.state == MailDraftState.DRAFT
    assert draft.attachments[0].sha256 == artifact.sha256
    assert draft.attachments[0].source_type == "artifact_version"

    authorization = service.authorize_draft(
        project_id=project.id,
        draft_id=draft.id,
        actor_user_id=identity.owner_user_id,
        spec=MailSendAuthorizationSpec(expires_in_minutes=10, max_sends=1),
        idempotency_key="w15-authorize-1",
    )
    assert authorization.action == "mail.send"
    assert authorization.attachment_hashes == [artifact.sha256]

    result = service.send(
        project_id=project.id,
        draft_id=draft.id,
        authorization_id=authorization.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w15-send-1",
    )
    assert result.attempt.state.value == "sent"
    assert result.draft_state == MailDraftState.SENT
    assert result.attempt.provider_message_id
    assert result.attempt.internet_message_id

    replay = service.send(
        project_id=project.id,
        draft_id=draft.id,
        authorization_id=authorization.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w15-send-1",
    )
    assert replay.attempt.id == result.attempt.id

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        assert session.scalar(select(func.count()).select_from(MailSendAttempt)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(MailMessage)
                .where(MailMessage.direction == "outbound")
            )
            == 2
        )
        authorization_row = session.get(MailSendAuthorization, authorization.id)
        assert authorization_row is not None
        assert authorization_row.used_sends == 1
        assert authorization_row.state == "exhausted"


def test_mail_content_revocation_expiry_and_cross_project_attachment_are_rejected(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    projects = ProjectService(session_factory)
    first = projects.create_project(
        actor_user_id=identity.owner_user_id,
        name="W15项目A",
        scope="邮件授权测试。",
        idempotency_key="w15-project-a",
    )
    second = projects.create_project(
        actor_user_id=identity.owner_user_id,
        name="W15项目B",
        scope="跨项目附件测试。",
        idempotency_key="w15-project-b",
    )
    store = LocalArtifactStore(tmp_path / "mail-artifacts")
    artifact = ArtifactService(session_factory, store).create_version(
        project_id=first.id,
        actor_user_id=identity.owner_user_id,
        title="项目A附件",
        media_type="application/octet-stream",
        content=b"project-a-only",
        mode=ArtifactMode.MOCK,
        origin=ArtifactOrigin.DERIVED,
        producer="w15-test",
    )
    service = MailService(session_factory, store, MockMailAdapter())
    with pytest.raises(NotFoundError, match="not found"):
        service.create_draft(
            project_id=second.id,
            actor_user_id=identity.owner_user_id,
            spec=_draft_spec(artifact.id),
            idempotency_key="w15-cross-project",
        )

    draft = service.create_draft(
        project_id=first.id,
        actor_user_id=identity.owner_user_id,
        spec=_draft_spec(),
        idempotency_key="w15-draft-content",
    )
    authorization = service.authorize_draft(
        project_id=first.id,
        draft_id=draft.id,
        actor_user_id=identity.owner_user_id,
        spec=MailSendAuthorizationSpec(expires_in_minutes=10, max_sends=5),
        idempotency_key="w15-authorize-content",
    )
    changed = service.update_draft(
        project_id=first.id,
        draft_id=draft.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=draft.revision + 1,
        spec=MailDraftSpec(
            to_addresses=["expert@example.test"],
            subject="已更改的合成问题",
            body_text="内容已更改，原授权不得继续使用。",
        ),
    )
    assert changed.content_sha256 != authorization.content_sha256
    with pytest.raises(MailAuthorizationError, match="no longer covers"):
        service.send(
            project_id=first.id,
            draft_id=draft.id,
            authorization_id=authorization.id,
            actor_user_id=identity.owner_user_id,
            idempotency_key="w15-send-changed",
        )

    second_draft = service.create_draft(
        project_id=first.id,
        actor_user_id=identity.owner_user_id,
        spec=_draft_spec(),
        idempotency_key="w15-draft-revoke",
    )
    revoked = service.authorize_draft(
        project_id=first.id,
        draft_id=second_draft.id,
        actor_user_id=identity.owner_user_id,
        spec=MailSendAuthorizationSpec(expires_in_minutes=10, max_sends=1),
        idempotency_key="w15-authorize-revoke",
    )
    service.revoke_authorization(
        project_id=first.id,
        authorization_id=revoked.id,
        actor_user_id=identity.owner_user_id,
    )
    with pytest.raises(MailAuthorizationError, match="revoked"):
        service.send(
            project_id=first.id,
            draft_id=second_draft.id,
            authorization_id=revoked.id,
            actor_user_id=identity.owner_user_id,
            idempotency_key="w15-send-revoked",
        )

    third_draft = service.create_draft(
        project_id=first.id,
        actor_user_id=identity.owner_user_id,
        spec=_draft_spec(),
        idempotency_key="w15-draft-expiry",
    )
    expired = service.authorize_draft(
        project_id=first.id,
        draft_id=third_draft.id,
        actor_user_id=identity.owner_user_id,
        spec=MailSendAuthorizationSpec(expires_in_minutes=10, max_sends=1),
        idempotency_key="w15-authorize-expiry",
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        row = session.get(MailSendAuthorization, expired.id)
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(MailAuthorizationError, match="expired"):
        service.send(
            project_id=first.id,
            draft_id=third_draft.id,
            authorization_id=expired.id,
            actor_user_id=identity.owner_user_id,
            idempotency_key="w15-send-expired",
        )


def test_unknown_send_requires_reconciliation_and_does_not_resend(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W15不确定态项目",
        scope="验证发送结果不确定时不自动重发。",
        idempotency_key="w15-unknown-project",
    )
    store = LocalArtifactStore(tmp_path / "mail-artifacts")
    adapter = MockMailAdapter(
        seed_inbox=False,
        send_outcome=MockSendOutcome.UNKNOWN_AFTER_DELIVERY,
    )
    service = MailService(session_factory, store, adapter)
    draft = service.create_draft(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=_draft_spec(),
        idempotency_key="w15-unknown-draft",
    )
    authorization = service.authorize_draft(
        project_id=project.id,
        draft_id=draft.id,
        actor_user_id=identity.owner_user_id,
        spec=MailSendAuthorizationSpec(expires_in_minutes=10, max_sends=1),
        idempotency_key="w15-unknown-authorize",
    )
    unknown = service.send(
        project_id=project.id,
        draft_id=draft.id,
        authorization_id=authorization.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w15-unknown-send",
    )
    assert unknown.attempt.state.value == "outcome_unknown"
    assert unknown.draft_state == MailDraftState.OUTCOME_UNKNOWN

    replay = service.send(
        project_id=project.id,
        draft_id=draft.id,
        authorization_id=authorization.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w15-unknown-send",
    )
    assert replay.attempt.id == unknown.attempt.id
    assert replay.attempt.state.value == "outcome_unknown"

    reconciled = service.reconcile(
        project_id=project.id,
        attempt_id=unknown.attempt.id,
        actor_user_id=identity.owner_user_id,
    )
    assert reconciled.attempt.state.value == "sent"
    assert reconciled.draft_state == MailDraftState.SENT


def test_w15_mail_tables_are_forced_through_rls(database: Engine) -> None:
    with database.connect() as connection:
        tables = connection.execute(
            text(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname IN (
                  'mail_accounts',
                  'mail_threads',
                  'mail_messages',
                  'mail_drafts',
                  'mail_draft_attachments',
                  'mail_send_authorizations',
                  'mail_send_attempts'
                )
                ORDER BY relname
                """
            )
        ).all()
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
    assert len(tables) == 7
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
    assert policies == 83
