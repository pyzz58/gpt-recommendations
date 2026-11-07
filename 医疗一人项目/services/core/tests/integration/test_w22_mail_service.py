from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.mail import MailService
from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.mail import (
    MailAccountState,
    MailDraftSpec,
    MailSendAuthorizationSpec,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.mail.smtp import SmtpMailAdapter


class _FakeSmtpConnection:
    def __init__(self) -> None:
        self.sent = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def ehlo(self) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        del username, password

    def send_message(self, message, from_addr, to_addrs) -> None:
        del message, from_addr, to_addrs
        self.sent = True


def test_w22_smtp_send_only_passes_existing_authorization_and_ledger(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W22 SMTP离线集成",
        scope="验证SMTP fake transport与既有草稿/授权/账本合同。",
        idempotency_key="w22-smtp-service-project",
    )
    connection = _FakeSmtpConnection()
    adapter = SmtpMailAdapter(
        host="smtp.example.test",
        port=587,
        username="sender@example.test",
        password="test-secret-not-real",
        security="starttls",
        from_address="sender@example.test",
        timeout_seconds=2,
        live_enabled=True,
        allowed_recipients=("expert@example.test",),
        smtp_factory=lambda host, port, timeout: connection,
    )
    service = MailService(
        session_factory,
        LocalArtifactStore(tmp_path / "artifacts"),
        adapter,
    )

    account = service.mailbox(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    draft = service.create_draft(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        spec=MailDraftSpec(
            to_addresses=["expert@example.test"],
            subject="W22 synthetic SMTP",
            body_text="Offline transport only; no external delivery.",
        ),
        idempotency_key="w22-smtp-draft",
    )
    authorization = service.authorize_draft(
        project_id=project.id,
        draft_id=draft.id,
        actor_user_id=identity.owner_user_id,
        spec=MailSendAuthorizationSpec(expires_in_minutes=10, max_sends=1),
        idempotency_key="w22-smtp-authorization",
    )
    result = service.send(
        project_id=project.id,
        draft_id=draft.id,
        authorization_id=authorization.id,
        actor_user_id=identity.owner_user_id,
        idempotency_key="w22-smtp-send",
    )

    assert account.mode.value == "live"
    assert account.state == MailAccountState.SEND_ONLY
    assert account.external_send_enabled is True
    assert connection.sent is True
    assert result.attempt.state.value == "sent"
