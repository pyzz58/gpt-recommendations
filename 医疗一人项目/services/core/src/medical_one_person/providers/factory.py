from __future__ import annotations

from decimal import Decimal

from medical_one_person.config import Settings
from medical_one_person.providers.base import ModelProvider
from medical_one_person.providers.fake import FakeModelProvider, UnavailableLiveProvider
from medical_one_person.providers.openai_compatible import OpenAICompatibleProvider


def build_model_provider(settings: Settings) -> ModelProvider:
    if settings.app_mode == "mock":
        return FakeModelProvider()
    if settings.model_provider == "mock":
        return UnavailableLiveProvider(
            "Live app mode requires an explicitly enabled non-mock model provider"
        )
    required = {
        "model_provider_base_url": settings.model_provider_base_url,
        "model_provider_api_key": settings.model_provider_api_key,
        "model_provider_model": settings.model_provider_model,
        "model_provider_max_cost_per_call": settings.model_provider_max_cost_per_call,
        "model_provider_input_cost_per_million": (
            settings.model_provider_input_cost_per_million
        ),
        "model_provider_output_cost_per_million": (
            settings.model_provider_output_cost_per_million
        ),
        "model_provider_currency": settings.model_provider_currency,
    }
    missing = [name for name, value in required.items() if value in {None, ""}]
    if not settings.model_provider_live_enabled:
        missing.append("model_provider_live_enabled")
    if missing:
        return UnavailableLiveProvider(
            "Live model configuration is incomplete: " + ", ".join(sorted(missing))
        )
    return OpenAICompatibleProvider(
        base_url=str(settings.model_provider_base_url),
        api_key=str(settings.model_provider_api_key),
        model_id=str(settings.model_provider_model),
        timeout_seconds=settings.model_provider_timeout_seconds,
        max_context_tokens=settings.model_provider_max_context_tokens,
        max_output_tokens=settings.model_provider_max_output_tokens,
        max_cost_per_call=Decimal(str(settings.model_provider_max_cost_per_call)),
        input_cost_per_million=Decimal(
            str(settings.model_provider_input_cost_per_million)
        ),
        output_cost_per_million=Decimal(
            str(settings.model_provider_output_cost_per_million)
        ),
        currency=str(settings.model_provider_currency),
        live_enabled=settings.model_provider_live_enabled,
    )
