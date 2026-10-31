"""Explicit non-capabilities used when no approved provider is configured."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisabledProviderResult:
    provider: str
    status: str = "not_configured"
    automatic_completion_allowed: bool = False
    message: str = (
        "Provider is not configured. Existing data remains viewable and no "
        "automatic clinical conclusion is produced."
    )


class DisabledProvider:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def unavailable(self) -> DisabledProviderResult:
        return DisabledProviderResult(provider=self.provider_name)

    def extract_rules(self, **_: object) -> DisabledProviderResult:
        return self.unavailable()

    def recognize_lab(self, **_: object) -> DisabledProviderResult:
        return self.unavailable()

    def analyze_case(self, **_: object) -> DisabledProviderResult:
        return self.unavailable()
