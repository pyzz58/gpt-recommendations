from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    status: Literal["ready", "not_configured", "not_checked", "unavailable"]
    detail: str


class ProviderCapability(BaseModel):
    provider_id: str
    mode: Literal["mock", "live"]
    status: Literal["ready", "not_configured", "disabled"]
    detail: str


class CapabilityReport(BaseModel):
    mode: Literal["mock", "live"]
    label: str
    implementation_scope: str
    providers: list[ProviderCapability]
    dependencies: dict[str, DependencyStatus]
    external_actions: DependencyStatus
    limitations: list[str]


class HealthReport(BaseModel):
    status: Literal["ok", "not_ready"]
    mode: Literal["mock", "live"]
    checks: dict[str, DependencyStatus]


class MockSmokeRequest(BaseModel):
    input: str = Field(min_length=1, max_length=2000)


class MockSmokeResponse(BaseModel):
    mode: Literal["mock"] = "mock"
    provider_id: str
    output: str
    disclaimer: str
