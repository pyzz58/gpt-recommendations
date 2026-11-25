from __future__ import annotations

from medical_one_person.config import Settings
from medical_one_person.infrastructure.mail.mock import MailAdapter, MockMailAdapter
from medical_one_person.infrastructure.mail.smtp import SmtpMailAdapter


def build_mail_adapter(settings: Settings) -> MailAdapter:
    if settings.mail_adapter == "mock":
        return MockMailAdapter()
    return SmtpMailAdapter(
        host=settings.mail_smtp_host,
        port=settings.mail_smtp_port,
        username=settings.mail_smtp_username,
        password=settings.mail_smtp_password,
        security=settings.mail_smtp_security,
        from_address=settings.mail_smtp_from_address,
        from_name=settings.mail_smtp_from_name,
        timeout_seconds=settings.mail_smtp_timeout_seconds,
        live_enabled=settings.mail_smtp_live_enabled,
        allowed_recipients=tuple(
            address.strip()
            for address in settings.mail_smtp_allowed_recipients.split(",")
            if address.strip()
        ),
    )
