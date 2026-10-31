from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FactClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    status: Literal["supported", "inferred", "hypothesis", "conflicting", "unknown"]
    source_refs: list[str]


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str = Field(min_length=1)
    source_kind: Literal["fixture", "internal", "external", "data"]
    locator: str | None = None


class AgentDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["agent_delivery.v1"] = "agent_delivery.v1"
    mode: Literal["mock", "live"]
    role_id: str = Field(pattern=r"^A\d{2}$")
    role_version: int = Field(ge=1)
    project_id: UUID
    task_id: UUID
    delivery_type: str = Field(min_length=1)
    problem_statement: str = Field(min_length=1)
    facts: list[FactClaim]
    analysis: str = Field(min_length=1)
    counterpoints: list[str] = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    evidence_refs: list[EvidenceReference]
    limitations: list[str] = Field(min_length=1)
    independent_review: bool
