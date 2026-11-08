from __future__ import annotations

import hashlib
import smtplib
from email.message import EmailMessage
from uuid import uuid4

import pytest

from medical_one_person.domain.mail import (
    MailAccountDescriptor,
    MailAccountState,
    MailAddressSet,
    MailMode,
    MailOutcomeUnknown,
    MailSendRejected,
    ProviderAttachment,
    ProviderSendRequest,
)
from medical_one_person.infrastructure.mail.smtp import SmtpMailAdapter


class FakeSmtpConnection:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.sent: EmailMessage | None = None

    def __enter__(self):
        self.calls.append("enter")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.calls.append("exit")
        return False

    def ehlo(self) -> None:
        self.calls.append("ehlo")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, username: str, password: str) -> None:
        self.calls.append(f"login:{username}:{password}")

    def send_message(self, message, from_addr, to_addrs) -> None:
        self.calls.append(f"send:{from_addr}:{','.join(to_addrs)}")
        self.sent = message


def send_request(*, recipient: str = "owner@example.test") -> ProviderSendRequest:
    content = b"synthetic attachment"
    return ProviderSendRequest(
        operation_key="smtp-operation-1",
        account=MailAccountDescriptor(
            account_id=uuid4(),
            workspace_id=uuid4(),
            address="sender@example.test",
            display_name="SMTP sender",
            mode=MailMode.LIVE,
        ),
        draft_id=uuid4(),
        provider_thread_id=None,
        in_reply_to=None,
        references=(),
        recipients=MailAddressSet(to=[recipient], cc=[], bcc=[]),
        subject="Synthetic SMTP test",
        body_text="No external delivery occurs in this test.",
        body_sha256=hashlib.sha256(b"body").hexdigest(),
        attachments=(
            ProviderAttachment(
                filename="synthetic.txt",
                media_type="text/plain",
                content=content,
                sha256=hashlib.sha256(content).hexdigest(),
            ),
        ),
    )


def adapter(connection: FakeSmtpConnection, **overrides) -> SmtpMailAdapter:
    values = {
        "host": "smtp.example.test",
        "port": 587,
        "username": "sender@example.test",
        "password": "test-secret-not-real",
        "security": "starttls",
        "from_address": "sender@example.test",
        "from_name": "Medical One",
        "timeout_seconds": 2,
        "live_enabled": True,
        "allowed_recipients": ("owner@example.test",),
    }
    values.update(overrides)
    return SmtpMailAdapter(
        **values,
        smtp_factory=lambda host, port, timeout: connection,
    )


def test_smtp_send_builds_message_and_is_explicitly_send_only() -> None:
    connection = FakeSmtpConnection()
    mail = adapter(connection)
    request = send_request()

    status = mail.account_status(request.account)
    result = mail.send(request)

    assert status == MailAccountState.SEND_ONLY
    assert connection.calls == [
        "enter",
        "ehlo",
        "starttls",
        "ehlo",
        "login:sender@example.test:test-secret-not-real",
        "send:sender@example.test:owner@example.test",
        "exit",
    ]
    assert connection.sent is not None
    assert connection.sent["Subject"] == "Synthetic SMTP test"
    assert connection.sent["X-Medical-One-Operation-Key"] == "smtp-operation-1"
    assert any(part.get_filename() == "synthetic.txt" for part in connection.sent.walk())
    assert result.outcome == "sent"
    assert mail.receive_supported is False
    assert mail.list_threads(request.account) == []


def test_smtp_recipient_allowlist_rejects_before_connect() -> None:
    connection = FakeSmtpConnection()
    with pytest.raises(MailSendRejected, match="allowlist"):
        adapter(connection).send(send_request(recipient="stranger@example.com"))
    assert connection.calls == []


def test_smtp_incomplete_or_disabled_config_is_not_ready() -> None:
    connection = FakeSmtpConnection()
    request = send_request()

    disabled = adapter(connection, live_enabled=False)
    incomplete = adapter(connection, allowed_recipients=())

    assert disabled.account_status(request.account) == MailAccountState.DISABLED
    assert incomplete.account_status(request.account) == MailAccountState.UNCONFIGURED


def test_smtp_transport_failure_is_unknown_and_reconcile_stays_unknown() -> None:
    class FailingConnection(FakeSmtpConnection):
        def __enter__(self):
            raise ConnectionResetError("synthetic network loss")

    mail = adapter(FailingConnection())
    request = send_request()

    with pytest.raises(MailOutcomeUnknown):
        mail.send(request)

    reconciled = mail.reconcile_send(
        operation_key=request.operation_key,
        provider_message_id=None,
    )
    assert reconciled.state == "unknown"
    assert reconciled.result is None


def test_smtp_5xx_authentication_is_a_failure_not_unknown() -> None:
    class RejectingConnection(FakeSmtpConnection):
        def login(self, username: str, password: str) -> None:
            del username, password
            raise smtplib.SMTPAuthenticationError(535, b"denied")

    with pytest.raises(MailSendRejected, match="authentication"):
        adapter(RejectingConnection()).send(send_request())
