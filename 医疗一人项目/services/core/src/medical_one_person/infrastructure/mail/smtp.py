from __future__ import annotations

import hashlib
import smtplib
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

from medical_one_person.domain.mail import (
    MailAccountDescriptor,
    MailAccountState,
    MailOutcomeUnknown,
    MailSendRejected,
    ProviderAttachment,
    ProviderMessage,
    ProviderReconcileResult,
    ProviderSendRequest,
    ProviderSendResult,
    ProviderThread,
)


class SmtpClient(Protocol):
    def ehlo(self) -> object: ...

    def starttls(self) -> object: ...

    def login(self, username: str, password: str) -> object: ...

    def send_message(
        self,
        message: EmailMessage,
        from_addr: str,
        to_addrs: list[str],
    ) -> object: ...


SmtpFactory = Callable[[str, int, float], AbstractContextManager[SmtpClient]]


def _default_smtp_factory(
    host: str,
    port: int,
    timeout: float,
    *,
    security: str,
) -> AbstractContextManager[SmtpClient]:
    if security == "ssl":
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    return smtplib.SMTP(host, port, timeout=timeout)


class SmtpMailAdapter:
    """Send-only SMTP adapter with explicit live and recipient gates."""

    def __init__(
        self,
        *,
        host: str | None,
        port: int = 587,
        username: str | None,
        password: str | None,
        security: str = "starttls",
        from_address: str | None,
        from_name: str = "医疗一人项目",
        timeout_seconds: float = 30,
        live_enabled: bool = False,
        allowed_recipients: tuple[str, ...] = (),
        smtp_factory: SmtpFactory | None = None,
    ) -> None:
        if security not in {"starttls", "ssl"}:
            raise ValueError("SMTP security must be starttls or ssl")
        if timeout_seconds <= 0:
            raise ValueError("SMTP timeout must be positive")
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._security = security
        self._from_address = from_address.strip().lower() if from_address else None
        self._from_name = from_name
        self._timeout_seconds = timeout_seconds
        self._live_enabled = live_enabled
        self._allowed_recipients = tuple(
            sorted({address.strip().lower() for address in allowed_recipients if address.strip()})
        )
        if smtp_factory is None:
            self._smtp_factory: SmtpFactory = (
                lambda smtp_host, smtp_port, timeout: _default_smtp_factory(
                    smtp_host,
                    smtp_port,
                    timeout,
                    security=self._security,
                )
            )
        else:
            self._smtp_factory = smtp_factory

    @property
    def adapter_id(self) -> str:
        return "smtp-send-only.v1"

    @property
    def account_mode(self) -> str:
        return "live"

    @property
    def default_address(self) -> str | None:
        return self._from_address

    @property
    def receive_supported(self) -> bool:
        return False

    def account_status(self, account: MailAccountDescriptor) -> MailAccountState:
        if not self._live_enabled:
            return MailAccountState.DISABLED
        if not self._configured():
            return MailAccountState.UNCONFIGURED
        if (
            account.mode.value != "live"
            or account.address.lower() != self._from_address
        ):
            return MailAccountState.DISABLED
        return MailAccountState.SEND_ONLY

    def list_threads(self, account: MailAccountDescriptor) -> list[ProviderThread]:
        del account
        return []

    def fetch_message(
        self,
        account: MailAccountDescriptor,
        provider_message_id: str,
    ) -> ProviderMessage | None:
        del account, provider_message_id
        return None

    def fetch_attachments(
        self,
        account: MailAccountDescriptor,
        provider_message_id: str,
    ) -> tuple[ProviderAttachment, ...]:
        del account, provider_message_id
        return ()

    def create_draft(self, account: MailAccountDescriptor, draft_id: str) -> str:
        del account
        digest = hashlib.sha256(draft_id.encode()).hexdigest()[:20]
        return f"smtp-local-draft-{digest}"

    def send(self, request: ProviderSendRequest) -> ProviderSendResult:
        if self.account_status(request.account) != MailAccountState.SEND_ONLY:
            raise MailSendRejected("SMTP account is disabled or incomplete")
        self._require_allowed_recipients(request)
        assert self._host is not None and self._from_address is not None
        message = self._build_message(request)
        recipients = [
            *request.recipients.to,
            *request.recipients.cc,
            *request.recipients.bcc,
        ]
        try:
            with self._smtp_factory(
                self._host,
                self._port,
                self._timeout_seconds,
            ) as client:
                client.ehlo()
                if self._security == "starttls":
                    client.starttls()
                    client.ehlo()
                if self._username is not None:
                    assert self._password is not None
                    client.login(self._username, self._password)
                client.send_message(message, self._from_address, recipients)
        except smtplib.SMTPAuthenticationError as exc:
            raise MailSendRejected("SMTP authentication was rejected") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise MailSendRejected("SMTP rejected one or more recipients") from exc
        except smtplib.SMTPDataError as exc:
            if 500 <= exc.smtp_code < 600:
                raise MailSendRejected("SMTP rejected the message data") from exc
            raise MailOutcomeUnknown(request.operation_key) from exc
        except (OSError, TimeoutError, smtplib.SMTPException) as exc:
            raise MailOutcomeUnknown(request.operation_key) from exc
        return self._result(request, message)

    def reconcile_send(
        self,
        *,
        operation_key: str,
        provider_message_id: str | None,
    ) -> ProviderReconcileResult:
        del operation_key, provider_message_id
        return ProviderReconcileResult(state="unknown", result=None)

    def _configured(self) -> bool:
        credentials_pair = (self._username is None) == (self._password is None)
        return bool(
            self._host
            and self._from_address
            and credentials_pair
            and self._allowed_recipients
        )

    def _require_allowed_recipients(self, request: ProviderSendRequest) -> None:
        recipients = {
            *request.recipients.to,
            *request.recipients.cc,
            *request.recipients.bcc,
        }
        forbidden = sorted(
            address.lower()
            for address in recipients
            if address.lower() not in self._allowed_recipients
        )
        if forbidden:
            raise MailSendRejected(
                "SMTP recipient allowlist rejected: " + ", ".join(forbidden)
            )

    def _build_message(self, request: ProviderSendRequest) -> EmailMessage:
        digest = hashlib.sha256(
            f"{request.account.address}\0{request.operation_key}".encode()
        ).hexdigest()
        message = EmailMessage()
        message["From"] = formataddr((self._from_name, request.account.address))
        message["To"] = ", ".join(request.recipients.to)
        if request.recipients.cc:
            message["Cc"] = ", ".join(request.recipients.cc)
        message["Subject"] = request.subject
        message["Message-ID"] = f"<medical-one-{digest}@localhost>"
        message["X-Medical-One-Operation-Key"] = request.operation_key
        if request.in_reply_to:
            message["In-Reply-To"] = request.in_reply_to
        if request.references:
            message["References"] = " ".join(request.references)
        message.set_content(request.body_text)
        for attachment in request.attachments:
            maintype, _, subtype = attachment.media_type.partition("/")
            message.add_attachment(
                attachment.content,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=attachment.filename,
            )
        return message

    def _result(
        self,
        request: ProviderSendRequest,
        message: EmailMessage,
    ) -> ProviderSendResult:
        digest = hashlib.sha256(request.operation_key.encode()).hexdigest()
        internet_message_id = str(message["Message-ID"])
        return ProviderSendResult(
            provider_message_id=f"smtp-message-{digest[:24]}",
            provider_thread_id=request.provider_thread_id or f"smtp-thread-{digest[:20]}",
            internet_message_id=internet_message_id,
            sent_at=datetime.now(UTC),
            outcome="sent",
        )
