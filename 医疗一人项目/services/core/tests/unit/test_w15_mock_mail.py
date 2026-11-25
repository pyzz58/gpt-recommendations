from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from medical_one_person.domain.mail import (
    MailAccountDescriptor,
    MailAddressSet,
    MailDraftSpec,
    MailMode,
    MailOutcomeUnknown,
    MailSendRejected,
    ProviderSendRequest,
)
from medical_one_person.infrastructure.mail.mock import (
    MockMailAdapter,
    MockSendOutcome,
)


def _account() -> MailAccountDescriptor:
    return MailAccountDescriptor(
        account_id=uuid4(),
        workspace_id=uuid4(),
        address="owner@medical-one.invalid",
        display_name="合成负责人",
        mode=MailMode.MOCK,
    )


def _request() -> ProviderSendRequest:
    return ProviderSendRequest(
        operation_key="operation-1",
        account=_account(),
        draft_id=uuid4(),
        provider_thread_id=None,
        in_reply_to=None,
        references=(),
        recipients=MailAddressSet(
            to=["expert@example.test"],
            cc=[],
            bcc=[],
        ),
        subject="合成专家问题",
        body_text="这是本地模拟邮件。",
        body_sha256="1" * 64,
        attachments=(),
    )


def test_mock_inbox_is_synthetic_and_contains_reply_headers() -> None:
    adapter = MockMailAdapter()
    threads = adapter.list_threads(_account())
    assert len(threads) == 1
    assert len(threads[0].messages) == 2
    assert threads[0].messages[1].in_reply_to == threads[0].messages[0].internet_message_id
    assert threads[0].messages[0].sender == "laboratory@example.test"
    assert threads[0].messages[0].raw_headers["X-Synthetic"] == "true"
    message = adapter.fetch_message(_account(), threads[0].messages[0].provider_message_id)
    assert message is not None
    assert message.subject == "合成资料接收确认"
    assert adapter.fetch_attachments(_account(), message.provider_message_id) == ()


def test_mock_send_success_and_repeated_reconcile_are_stable() -> None:
    adapter = MockMailAdapter(seed_inbox=False)
    first = adapter.send(_request())
    second = adapter.reconcile_send(
        operation_key="operation-1",
        provider_message_id=first.provider_message_id,
    )
    assert second.state == "sent"
    assert second.result is not None
    assert second.result.provider_message_id == first.provider_message_id
    assert second.result.sent_at <= datetime.now(UTC)


def test_mock_unknown_after_delivery_reconciles_without_resend() -> None:
    adapter = MockMailAdapter(
        seed_inbox=False,
        send_outcome=MockSendOutcome.UNKNOWN_AFTER_DELIVERY,
    )
    with pytest.raises(MailOutcomeUnknown):
        adapter.send(_request())
    result = adapter.reconcile_send(
        operation_key="operation-1",
        provider_message_id=None,
    )
    assert result.state == "sent"
    assert result.result is not None


def test_mock_unknown_before_delivery_reconciles_not_found() -> None:
    adapter = MockMailAdapter(
        seed_inbox=False,
        send_outcome=MockSendOutcome.UNKNOWN_BEFORE_DELIVERY,
    )
    with pytest.raises(MailOutcomeUnknown):
        adapter.send(_request())
    result = adapter.reconcile_send(
        operation_key="operation-1",
        provider_message_id=None,
    )
    assert result.state == "not_found"
    assert result.result is None


def test_mock_adapter_rejects_real_recipients() -> None:
    adapter = MockMailAdapter(seed_inbox=False)
    request = _request()
    unsafe = ProviderSendRequest(
        **{
            **request.__dict__,
            "recipients": MailAddressSet(to=["person@example.com"], cc=[], bcc=[]),
        }
    )
    with pytest.raises(MailSendRejected, match="test"):
        adapter.send(unsafe)


def test_mail_addresses_are_normalized_and_validated() -> None:
    draft = MailDraftSpec(
        to_addresses=["Expert@Example.Test", "expert@example.test"],
        subject="问题",
        body_text="正文",
    )
    assert draft.to_addresses == ["expert@example.test"]
    with pytest.raises(ValueError):
        MailDraftSpec(
            to_addresses=["not-an-address"],
            subject="问题",
            body_text="正文",
        )
    with pytest.raises(ValueError, match="line breaks"):
        MailDraftSpec(
            to_addresses=["expert@example.test"],
            subject="问题\r\nBcc: another@example.test",
            body_text="正文",
        )
