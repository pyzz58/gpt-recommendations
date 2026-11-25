from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import pytest

from medical_one_person.config import Settings
from medical_one_person.providers.base import StructuredGenerationRequest
from medical_one_person.providers.errors import (
    ProviderAuthenticationError,
    ProviderBudgetExceeded,
)
from medical_one_person.providers.factory import build_model_provider
from medical_one_person.providers.fake import UnavailableLiveProvider
from medical_one_person.providers.openai_compatible import OpenAICompatibleProvider


def request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        role_id="A04",
        role_version=1,
        project_id=uuid4(),
        task_id=uuid4(),
        goal="形成合成研究摘要",
        input_refs=["fixture:w22"],
        context_sections={"evidence": "合成输入"},
        system_instructions="按岗位输出结构化交付。",
        output_schema="agent_delivery.v1",
        delivery_type="scientific_summary",
        independent_context=False,
    )


def provider(transport, *, max_cost: str = "1.00") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="https://provider.example/v1",
        api_key="test-secret-not-real",
        model_id="reviewed-model-test",
        timeout_seconds=2,
        max_context_tokens=2_000,
        max_output_tokens=100,
        max_cost_per_call=Decimal(max_cost),
        input_cost_per_million=Decimal("1"),
        output_cost_per_million=Decimal("2"),
        currency="USD",
        live_enabled=True,
        transport=transport,
    )


def test_openai_compatible_transport_contract_is_offline_and_metered() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append((url, headers, json.loads(body), timeout))
        return (
            200,
            json.dumps(
                {
                    "model": "reviewed-model-test",
                    "choices": [
                        {
                            "message": {"content": '{"schema_version":"agent_delivery.v1"}'},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10},
                }
            ).encode(),
        )

    response = provider(transport).generate_structured(request())

    assert response.mode == "live"
    assert response.output == {"schema_version": "agent_delivery.v1"}
    assert response.usage.input_tokens == 20
    assert response.usage.output_tokens == 10
    assert response.usage.estimated_cost == Decimal("0.000040")
    assert calls[0][0] == "https://provider.example/v1/chat/completions"
    assert calls[0][1]["Authorization"] == "Bearer test-secret-not-real"
    assert calls[0][2]["model"] == "reviewed-model-test"
    assert calls[0][2]["max_tokens"] == 100


def test_cost_cap_rejects_before_transport_call() -> None:
    calls = 0

    def transport(url, headers, body, timeout):
        nonlocal calls
        del url, headers, body, timeout
        calls += 1
        raise AssertionError("transport must not be called")

    with pytest.raises(ProviderBudgetExceeded):
        provider(transport, max_cost="0.000001").generate_structured(request())
    assert calls == 0


def test_authentication_failure_is_explicit() -> None:
    def transport(url, headers, body, timeout):
        del url, headers, body, timeout
        return 401, b'{"error":"invalid key"}'

    with pytest.raises(ProviderAuthenticationError):
        provider(transport).generate_structured(request())


def test_factory_keeps_live_disabled_and_reports_missing_configuration() -> None:
    settings = Settings(
        app_mode="live",
        model_provider="openai_compatible",
        model_provider_live_enabled=False,
    )

    built = build_model_provider(settings)

    assert isinstance(built, UnavailableLiveProvider)
    assert "model_provider_live_enabled" in built.reason


def test_factory_builds_configured_live_provider_without_network() -> None:
    settings = Settings(
        app_mode="live",
        model_provider="openai_compatible",
        model_provider_live_enabled=True,
        model_provider_base_url="https://provider.example/v1",
        model_provider_api_key="test-secret-not-real",
        model_provider_model="reviewed-model-test",
        model_provider_max_cost_per_call=1.0,
        model_provider_input_cost_per_million=1.0,
        model_provider_output_cost_per_million=2.0,
        model_provider_currency="USD",
    )

    built = build_model_provider(settings)

    assert isinstance(built, OpenAICompatibleProvider)
    assert built.capabilities().structured_output is True
    assert built.capabilities().mode == "live"
