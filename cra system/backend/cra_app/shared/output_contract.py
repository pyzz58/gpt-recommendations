"""Shared output contract for every CRA review surface.

The contract keeps facts, automatic candidates, inferences and explicit user
confirmations separate. It deliberately has no single "medical conclusion" or
"clinical safe" shortcut.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OutputPurpose = Literal[
    "rule_candidate",
    "visit_window",
    "lab_comparison",
    "safety_analysis",
    "carryover_reminder",
    "directory_review",
    "report_draft",
    "platform_scope",
]
ClaimKind = Literal[
    "fact",
    "auto_candidate",
    "inference",
    "user_confirmation",
]
VerificationStatus = Literal[
    "unverified",
    "auto_extracted",
    "needs_review",
    "cra_confirmed",
    "medical_confirmed",
    "not_checked",
]
CapabilityLevel = Literal[
    "implemented",
    "configured",
    "validated",
    "limited",
    "unavailable",
    "not_implemented",
]
OutputStatus = Literal[
    "ready_to_review",
    "limited",
    "needs_clarification",
    "failed",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutputScope(ContractModel):
    tenant_id: str = Field(min_length=1)
    study_id: uuid.UUID
    site_id: uuid.UUID | None = None
    subject_id: str | None = None


class InputRevision(ContractModel):
    resource_type: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PolicyVersion(ContractModel):
    layer: Literal["common", "study", "site"]
    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    activation_date: str | None = None


class SourceRef(ContractModel):
    source_type: Literal[
        "document",
        "document_anchor",
        "edc_row",
        "image_region",
        "user_action",
        "record",
        "external_query",
    ]
    source_id: str = Field(min_length=1)
    version: str | None = None
    locator: str | None = None
    quote: str | None = None


class Claim(ContractModel):
    claim_id: str = Field(min_length=1)
    kind: ClaimKind
    label: str = Field(min_length=1)
    value: Any = None
    verification_status: VerificationStatus
    source_refs: list[SourceRef] = Field(default_factory=list)
    calculation: str | None = None

    @model_validator(mode="after")
    def preserve_semantics(self) -> "Claim":
        if self.kind == "fact" and self.verification_status == "auto_extracted":
            raise ValueError("a fact cannot be labelled as an automatic extraction")
        if (
            self.kind == "auto_candidate"
            and self.verification_status in {"cra_confirmed", "medical_confirmed"}
        ):
            raise ValueError(
                "automatic candidates must remain separate from confirmations"
            )
        return self


class UnknownItem(ContractModel):
    code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    affected_scope: str = Field(min_length=1)


class ConflictItem(ContractModel):
    conflict_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_refs: list[SourceRef] = Field(default_factory=list)


class NotCheckedItem(ContractModel):
    code: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    decision_ref: str | None = None


class OutputCapability(ContractModel):
    capability_id: str = Field(min_length=1)
    level: CapabilityLevel
    validated: bool = False
    limitations: list[str] = Field(default_factory=list)


class OutputEnvelope(ContractModel):
    schema_version: Literal[1] = 1
    output_id: uuid.UUID
    purpose: OutputPurpose
    scope: OutputScope
    input_revisions: list[InputRevision] = Field(default_factory=list)
    policy_versions: list[PolicyVersion] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    evidence_refs: list[SourceRef] = Field(default_factory=list)
    unknowns: list[UnknownItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    not_checked: list[NotCheckedItem] = Field(default_factory=list)
    capabilities: list[OutputCapability] = Field(default_factory=list)
    status: OutputStatus
    generated_at: datetime
    actor_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_limitations_for_limited_output(self) -> "OutputEnvelope":
        if self.status == "limited" and not (
            self.unknowns or self.conflicts or self.not_checked
        ):
            raise ValueError(
                "limited output must identify its unknown, conflict or skipped scope"
            )
        return self
