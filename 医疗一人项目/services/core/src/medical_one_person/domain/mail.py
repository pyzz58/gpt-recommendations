from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MailMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"


class MailAccountState(StrEnum):
    MOCK_READY = "mock_ready"
    CONNECTED = "connected"
    SEND_ONLY = "send_only"
    UNCONFIGURED = "unconfigured"
    DISABLED = "disabled"


class MailThreadLinkState(StrEnum):
    UNLINKED = "unlinked"
    LINKED = "linked"


class MailDraftState(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SENDING = "sending"
    SENT = "sent"
    OUTCOME_UNKNOWN = "outcome_unknown"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MailAuthorizationState(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"


class MailAttemptState(StrEnum):
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"
    NOT_SENT = "not_sent"


class MailAttachmentSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: Literal["artifact_version", "knowledge_version"]
    source_id: UUID


class MailDraftSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    to_addresses: list[str] = Field(min_length=1, max_length=10)
    cc_addresses: list[str] = Field(default_factory=list, max_length=10)
    bcc_addresses: list[str] = Field(default_factory=list, max_length=10)
    subject: str = Field(min_length=1, max_length=300)
    body_text: str = Field(min_length=1, max_length=50_000)
    attachments: list[MailAttachmentSource] = Field(default_factory=list, max_length=10)
    thread_id: UUID | None = None

    @field_validator("to_addresses", "cc_addresses", "bcc_addresses")
    @classmethod
    def validate_addresses(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            address = value.strip().lower()
            local, separator, domain = address.partition("@")
            if (
                not separator
                or not local
                or "." not in domain
                or " " in address
                or "\n" in address
                or "\r" in address
            ):
                raise ValueError("Mail addresses must use a simple local@domain format")
            if address not in normalized:
                normalized.append(address)
        return normalized

    @field_validator("subject", "body_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Mail subject and body cannot be blank")
        return value.strip()

    @field_validator("subject")
    @classmethod
    def reject_subject_control_characters(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("Mail subject cannot contain line breaks")
        return value


class MailSendAuthorizationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expires_in_minutes: int = Field(default=60, ge=1, le=24 * 60)
    max_sends: int = Field(default=1, ge=1, le=20)


class MailAddressSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    to: list[str]
    cc: list[str]
    bcc: list[str]


@dataclass(frozen=True)
class MailAccountDescriptor:
    account_id: UUID
    workspace_id: UUID
    address: str
    display_name: str
    mode: MailMode


@dataclass(frozen=True)
class ProviderAttachment:
    filename: str
    media_type: str
    content: bytes
    sha256: str


@dataclass(frozen=True)
class ProviderSendRequest:
    operation_key: str
    account: MailAccountDescriptor
    draft_id: UUID
    provider_thread_id: str | None
    in_reply_to: str | None
    references: tuple[str, ...]
    recipients: MailAddressSet
    subject: str
    body_text: str
    body_sha256: str
    attachments: tuple[ProviderAttachment, ...]


@dataclass(frozen=True)
class ProviderSendResult:
    provider_message_id: str
    provider_thread_id: str
    internet_message_id: str
    sent_at: datetime
    outcome: Literal["sent"]


@dataclass(frozen=True)
class ProviderReconcileResult:
    state: Literal["sent", "not_found", "unknown"]
    result: ProviderSendResult | None


@dataclass(frozen=True)
class ProviderMessage:
    provider_message_id: str
    provider_thread_id: str
    internet_message_id: str | None
    in_reply_to: str | None
    references: tuple[str, ...]
    sender: str
    recipients: MailAddressSet
    subject: str
    body_text: str
    sent_at: datetime
    raw_headers: dict[str, str]


@dataclass(frozen=True)
class ProviderThread:
    provider_thread_id: str
    subject: str
    last_message_at: datetime
    messages: tuple[ProviderMessage, ...]


class MailOutcomeUnknown(Exception):
    def __init__(self, operation_key: str, provider_message_id: str | None = None) -> None:
        super().__init__("Mail provider outcome is unknown; reconcile before any retry")
        self.operation_key = operation_key
        self.provider_message_id = provider_message_id


class MailSendRejected(Exception):
    pass
