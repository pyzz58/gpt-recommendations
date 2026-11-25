from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PilotProcessStep(StrEnum):
    INVESTMENT_CHARTER = "investment_charter"
    SOURCE_REVIEW = "source_review"
    UNMET_NEED = "unmet_need"
    MECHANISM_TRANSLATION = "mechanism_translation"
    SAFETY_CMC = "safety_cmc"
    STUDY_DESIGN_STATISTICS = "study_design_statistics"
    CANDIDATE_SELECTION = "candidate_selection"
    PROVIDER_MATCHING = "provider_matching"
    QUOTE_BUDGET = "quote_budget"
    RIGHTS_CONTRACT = "rights_contract"
    HANDOFF_EXECUTION = "handoff_execution"
    RAW_DELIVERY = "raw_delivery"
    CLEANING_STATISTICS = "cleaning_statistics"
    INDEPENDENT_QUALITY = "independent_quality"
    REPORTING_DECISION = "reporting_decision"
    ARCHIVE_RETROSPECTIVE = "archive_retrospective"


class PilotEvidenceLevel(StrEnum):
    NOT_STARTED = "not_started"
    DESIGNED = "designed"
    MOCK_REHEARSED = "mock_rehearsed"
    CONTACTED = "contacted"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    NOT_APPLICABLE = "not_applicable"


REAL_EVIDENCE_LEVELS = {
    PilotEvidenceLevel.CONTACTED,
    PilotEvidenceLevel.AUTHORIZED,
    PilotEvidenceLevel.EXECUTING,
    PilotEvidenceLevel.DELIVERED,
    PilotEvidenceLevel.ACCEPTED,
}


class PilotCoverageEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step: PilotProcessStep
    level: PilotEvidenceLevel
    owner_role: str = Field(pattern=r"^A(0[1-9]|1[0-9]|2[0-6])$")
    provider_interfaces: list[str] = Field(default_factory=list, max_length=20)
    input_refs: list[str] = Field(default_factory=list, max_length=50)
    output_refs: list[str] = Field(default_factory=list, max_length=50)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    authorization_refs: list[str] = Field(default_factory=list, max_length=50)
    execution_refs: list[str] = Field(default_factory=list, max_length=50)
    delivery_refs: list[str] = Field(default_factory=list, max_length=50)
    acceptance_refs: list[str] = Field(default_factory=list, max_length=50)
    gap: str | None = Field(default=None, max_length=5_000)
    not_applicable_reason: str | None = Field(default=None, max_length=5_000)

    @model_validator(mode="after")
    def evidence_matches_level(self) -> PilotCoverageEntry:
        if self.level == PilotEvidenceLevel.NOT_APPLICABLE:
            if not self.not_applicable_reason:
                raise ValueError("not_applicable requires a concrete reason")
            return self
        if self.not_applicable_reason is not None:
            raise ValueError("not_applicable_reason is only valid for not_applicable")
        if self.level in REAL_EVIDENCE_LEVELS and not self.evidence_refs:
            raise ValueError(f"{self.level.value} requires real evidence references")
        if self.level in {
            PilotEvidenceLevel.AUTHORIZED,
            PilotEvidenceLevel.EXECUTING,
            PilotEvidenceLevel.DELIVERED,
            PilotEvidenceLevel.ACCEPTED,
        } and not self.authorization_refs:
            raise ValueError(f"{self.level.value} requires authorization references")
        if self.level in {
            PilotEvidenceLevel.EXECUTING,
            PilotEvidenceLevel.DELIVERED,
            PilotEvidenceLevel.ACCEPTED,
        } and not self.execution_refs:
            raise ValueError(f"{self.level.value} requires execution references")
        if self.level in {
            PilotEvidenceLevel.DELIVERED,
            PilotEvidenceLevel.ACCEPTED,
        } and not self.delivery_refs:
            raise ValueError(f"{self.level.value} requires delivery references")
        if self.level == PilotEvidenceLevel.ACCEPTED and not self.acceptance_refs:
            raise ValueError("accepted requires acceptance references")
        return self


class PilotReadinessInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=1, ge=1, le=1)
    pilot_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    candidate_defined: bool
    charter_ref: str = Field(min_length=1, max_length=1_000)
    coverage: list[PilotCoverageEntry] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_steps(self) -> PilotReadinessInput:
        steps = [entry.step for entry in self.coverage]
        if len(steps) != len(set(steps)):
            raise ValueError("coverage steps must be unique")
        return self


class PilotReadinessReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pilot_id: str
    version: int
    status: str
    candidate_defined: bool
    required_steps: int
    declared_steps: int
    real_evidence_steps: list[str]
    missing_steps: list[str]
    gaps: list[str]
    declared_coverage_complete: bool
    phase_one_complete: bool = False
    human_confirmation_required: bool = True
    limitation: str


def evaluate_pilot_readiness(data: PilotReadinessInput) -> PilotReadinessReport:
    declared = {entry.step: entry for entry in data.coverage}
    required = set(PilotProcessStep)
    missing = sorted(step.value for step in required - set(declared))
    real = sorted(
        entry.step.value
        for entry in data.coverage
        if entry.level in REAL_EVIDENCE_LEVELS
    )
    gaps = sorted(
        f"{entry.step.value}: {entry.gap}"
        for entry in data.coverage
        if entry.gap
    )
    declared_complete = (
        data.candidate_defined
        and not missing
        and not gaps
        and all(
            entry.level in {
                PilotEvidenceLevel.ACCEPTED,
                PilotEvidenceLevel.NOT_APPLICABLE,
            }
            for entry in data.coverage
        )
    )
    if not real:
        status = "prepared_no_real_evidence"
    elif declared_complete:
        status = "declared_complete_pending_human_review"
    else:
        status = "partially_validated"
    return PilotReadinessReport(
        pilot_id=data.pilot_id,
        version=data.version,
        status=status,
        candidate_defined=data.candidate_defined,
        required_steps=len(required),
        declared_steps=len(declared),
        real_evidence_steps=real,
        missing_steps=missing,
        gaps=gaps,
        declared_coverage_complete=declared_complete,
        limitation=(
            "This report validates declared structure and references only. "
            "It does not authenticate contacts, authorization, execution, delivery "
            "or acceptance, and never marks phase one complete automatically."
        ),
    )
