from __future__ import annotations

import hashlib
import threading
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from medical_one_person.domain.mail import (
    MailAccountDescriptor,
    MailAccountState,
    MailAddressSet,
    MailOutcomeUnknown,
    MailSendRejected,
    ProviderAttachment,
    ProviderMessage,
    ProviderReconcileResult,
    ProviderSendRequest,
    ProviderSendResult,
    ProviderThread,
)


class MailAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...

    @property
    def account_mode(self) -> str: ...

    @property
    def default_address(self) -> str | None: ...

    @property
    def receive_supported(self) -> bool: ...

    def account_status(self, account: MailAccountDescriptor) -> MailAccountState: ...

    def list_threads(self, account: MailAccountDescriptor) -> list[ProviderThread]: ...

    def fetch_message(
        self,
        account: MailAccountDescriptor,
        provider_message_id: str,
    ) -> ProviderMessage | None: ...

    def fetch_attachments(
        self,
        account: MailAccountDescriptor,
        provider_message_id: str,
    ) -> tuple[ProviderAttachment, ...]: ...

    def create_draft(self, account: MailAccountDescriptor, draft_id: str) -> str: ...

    def send(self, request: ProviderSendRequest) -> ProviderSendResult: ...

    def reconcile_send(
        self,
        *,
        operation_key: str,
        provider_message_id: str | None,
    ) -> ProviderReconcileResult: ...


class MockSendOutcome(StrEnum):
    SENT = "sent"
    UNKNOWN_AFTER_DELIVERY = "unknown_after_delivery"
    UNKNOWN_BEFORE_DELIVERY = "unknown_before_delivery"
    REJECTED = "rejected"


class MockMailAdapter:
    """In-process deterministic mailbox; no network or real recipient can be reached."""

    def __init__(
        self,
        *,
        send_outcome: MockSendOutcome = MockSendOutcome.SENT,
        seed_inbox: bool = True,
    ) -> None:
        self._adapter_id = "mock-mail.v1"
        self._send_outcome = send_outcome
        self._lock = threading.Lock()
        self._threads: dict[str, list[ProviderMessage]] = {}
        self._deliveries: dict[str, tuple[ProviderSendResult, ProviderMessage]] = {}
        self._seeded_accounts: set[str] = set()
        self._seed_inbox = seed_inbox

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def account_mode(self) -> str:
        return "mock"

    @property
    def default_address(self) -> str | None:
        return "owner@medical-one.invalid"

    @property
    def receive_supported(self) -> bool:
        return True

    def account_status(self, account: MailAccountDescriptor) -> MailAccountState:
        if account.mode.value != "mock" or account.address.endswith(".invalid"):
            return MailAccountState.MOCK_READY
        return MailAccountState.DISABLED

    def list_threads(self, account: MailAccountDescriptor) -> list[ProviderThread]:
        with self._lock:
            self._ensure_seeded(account)
            return [
                ProviderThread(
                    provider_thread_id=thread_id,
                    subject=messages[-1].subject,
                    last_message_at=messages[-1].sent_at,
                    messages=tuple(messages),
                )
                for thread_id, messages in sorted(
                    self._threads.items(),
                    key=lambda item: item[1][-1].sent_at,
                    reverse=True,
                )
            ]

    def create_draft(self, account: MailAccountDescriptor, draft_id: str) -> str:
        return f"mock-draft-{draft_id}"

    def fetch_message(
        self,
        account: MailAccountDescriptor,
        provider_message_id: str,
    ) -> ProviderMessage | None:
        with self._lock:
            self._ensure_seeded(account)
            for messages in self._threads.values():
                for message in messages:
                    if message.provider_message_id == provider_message_id:
                        return message
        return None

    def fetch_attachments(
        self,
        account: MailAccountDescriptor,
        provider_message_id: str,
    ) -> tuple[ProviderAttachment, ...]:
        message = self.fetch_message(account, provider_message_id)
        return () if message is None else ()

    def send(self, request: ProviderSendRequest) -> ProviderSendResult:
        self._ensure_mock_recipients(request.recipients)
        if self._send_outcome == MockSendOutcome.REJECTED:
            raise MailSendRejected("Mock provider rejected the message")
        result = self._build_result(request)
        message = ProviderMessage(
            provider_message_id=result.provider_message_id,
            provider_thread_id=result.provider_thread_id,
            internet_message_id=result.internet_message_id,
            in_reply_to=request.in_reply_to,
            references=request.references,
            sender=request.account.address,
            recipients=request.recipients,
            subject=request.subject,
            body_text=request.body_text,
            sent_at=result.sent_at,
            raw_headers={
                "Message-ID": result.internet_message_id,
                "In-Reply-To": request.in_reply_to or "",
                "References": " ".join(request.references),
            },
        )
        if self._send_outcome != MockSendOutcome.UNKNOWN_BEFORE_DELIVERY:
            with self._lock:
                self._threads.setdefault(result.provider_thread_id, []).append(message)
                self._deliveries[request.operation_key] = (result, message)
        if self._send_outcome != MockSendOutcome.SENT:
            raise MailOutcomeUnknown(
                request.operation_key,
                result.provider_message_id
                if self._send_outcome == MockSendOutcome.UNKNOWN_AFTER_DELIVERY
                else None,
            )
        return result

    def reconcile_send(
        self,
        *,
        operation_key: str,
        provider_message_id: str | None,
    ) -> ProviderReconcileResult:
        del provider_message_id
        with self._lock:
            delivery = self._deliveries.get(operation_key)
        if delivery is None:
            return ProviderReconcileResult(state="not_found", result=None)
        return ProviderReconcileResult(state="sent", result=delivery[0])

    def _build_result(self, request: ProviderSendRequest) -> ProviderSendResult:
        digest = hashlib.sha256(request.operation_key.encode("utf-8")).hexdigest()
        thread_id = request.provider_thread_id or f"mock-thread-{digest[:20]}"
        return ProviderSendResult(
            provider_message_id=f"mock-message-{digest[:24]}",
            provider_thread_id=thread_id,
            internet_message_id=f"<mock-{digest}@mail.invalid>",
            sent_at=datetime.now(UTC),
            outcome="sent",
        )

    def _ensure_mock_recipients(self, recipients: MailAddressSet) -> None:
        forbidden = [
            address
            for address in [*recipients.to, *recipients.cc, *recipients.bcc]
            if not (
                address.endswith(".test")
                or address.endswith(".invalid")
                or address.endswith(".example")
            )
        ]
        if forbidden:
            raise MailSendRejected(
                "Mock mail only accepts .test, .invalid or .example recipients"
            )

    def _ensure_seeded(self, account: MailAccountDescriptor) -> None:
        if not self._seed_inbox or account.address in self._seeded_accounts:
            return
        self._seeded_accounts.add(account.address)
        now = datetime.now(UTC)
        thread_id = f"mock-inbox-{hashlib.sha256(account.address.encode()).hexdigest()[:16]}"
        first = ProviderMessage(
            provider_message_id=f"mock-inbound-{thread_id}-1",
            provider_thread_id=thread_id,
            internet_message_id=f"<mock-inbound-{thread_id}-1@example.test>",
            in_reply_to=None,
            references=(),
            sender="laboratory@example.test",
            recipients=MailAddressSet(to=[account.address], cc=[], bcc=[]),
            subject="合成资料接收确认",
            body_text=(
                "已收到合成项目材料，但未提供原始分析文件。"
                "该模拟回复不构成科学性认可、合作承诺或真实实验室交付。"
            ),
            sent_at=now - timedelta(minutes=20),
            raw_headers={
                "Message-ID": f"<mock-inbound-{thread_id}-1@example.test>",
                "X-Synthetic": "true",
            },
        )
        second = ProviderMessage(
            provider_message_id=f"mock-inbound-{thread_id}-2",
            provider_thread_id=thread_id,
            internet_message_id=f"<mock-inbound-{thread_id}-2@example.test>",
            in_reply_to=first.internet_message_id,
            references=(first.internet_message_id or "",),
            sender=account.address,
            recipients=MailAddressSet(to=["laboratory@example.test"], cc=[], bcc=[]),
            subject="Re: 合成资料接收确认",
            body_text=(
                "请确认还缺少哪些原始文件。此消息由本地模拟适配器预先保存，"
                "不是实际发信记录。"
            ),
            sent_at=now - timedelta(minutes=15),
            raw_headers={
                "Message-ID": f"<mock-inbound-{thread_id}-2@example.test>",
                "In-Reply-To": first.internet_message_id or "",
                "X-Synthetic": "true",
            },
        )
        self._threads[thread_id] = [first, second]
