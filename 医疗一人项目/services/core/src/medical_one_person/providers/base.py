from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from medical_one_person.contracts import MockSmokeResponse


class ProviderCapabilities(BaseModel):
    provider_id: str
    mode: Literal["mock", "live"]
    structured_output: bool
    streaming: bool
    max_context_tokens: int


class ModelUsage(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost: Decimal | None
    currency: str | None


class StructuredGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: str
    role_version: int
    project_id: UUID
    task_id: UUID
    goal: str
    input_refs: list[str]
    context_sections: dict[str, str]
    system_instructions: str
    output_schema: str
    delivery_type: str
    independent_context: bool
    repair_feedback: str | None = None


class StructuredGenerationResponse(BaseModel):
    provider_id: str
    model_id: str
    mode: Literal["mock", "live"]
    output: dict[str, Any]
    usage: ModelUsage
    finish_reason: str


class ModelProvider(Protocol):
    provider_id: str

    def capabilities(self) -> ProviderCapabilities:
        """Describe actual provider capabilities without inferring from model names."""

    def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        """Generate a candidate object that the caller must schema-validate."""

    def estimate_cost(self, request: StructuredGenerationRequest) -> Decimal | None:
        """Return a conservative cost estimate or None when unknown."""

    def smoke(self, value: str) -> MockSmokeResponse:
        """Return a marked response without performing external side effects."""
