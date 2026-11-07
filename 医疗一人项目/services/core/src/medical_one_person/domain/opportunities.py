from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Track(StrEnum):
    PET_REPURPOSING = "pet_repurposing"
    IVD = "ivd"
    DEVICE = "device"


class OpportunityStatus(StrEnum):
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    NEEDS_EVIDENCE = "needs_evidence"
    SHORTLISTED = "shortlisted"
    SELECTED = "selected"
    WATCHLIST = "watchlist"
    REJECTED = "rejected"


class MechanismStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(min_length=1)
    status: Literal["fact", "inference", "hypothesis"]
    evidence_refs: list[str]

    @model_validator(mode="after")
    def fact_requires_evidence(self) -> MechanismStep:
        if self.status == "fact" and not self.evidence_refs:
            raise ValueError("A mechanism fact requires at least one evidence reference")
        return self


class ProbabilityEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event: str = Field(min_length=1)
    conditions: str = Field(min_length=1)
    horizon: str = Field(min_length=1)
    success_criterion: str = Field(min_length=1)
    method: Literal["empirical", "validated_model", "subjective_scenario", "unknown"]
    basis_refs: list[str]
    population_or_base_rate: str | None
    lower: float | None = Field(default=None, ge=0, le=1)
    upper: float | None = Field(default=None, ge=0, le=1)
    calibration_status: Literal["calibrated", "uncalibrated", "not_applicable"]
    limitations: list[str] = Field(min_length=1)
    unknown_reason: str | None = None

    @model_validator(mode="after")
    def validate_probability(self) -> ProbabilityEstimate:
        if self.method == "unknown":
            if self.lower is not None or self.upper is not None:
                raise ValueError("Unknown probability must not contain numeric bounds")
            if not self.unknown_reason:
                raise ValueError("Unknown probability requires an explicit reason")
            if self.calibration_status != "not_applicable":
                raise ValueError("Unknown probability cannot claim calibration")
            return self
        if self.lower is None or self.upper is None:
            raise ValueError("Estimated probability requires lower and upper bounds")
        if self.lower > self.upper:
            raise ValueError("Probability lower bound cannot exceed upper bound")
        if self.method in {"empirical", "validated_model"} and not self.basis_refs:
            raise ValueError("Empirical or validated probability requires basis references")
        if self.method in {"empirical", "validated_model"} and (
            self.calibration_status == "not_applicable"
        ):
            raise ValueError("Estimated probability requires a calibration status")
        if self.method == "subjective_scenario" and self.calibration_status == "calibrated":
            raise ValueError("A subjective scenario cannot be labelled calibrated")
        if self.unknown_reason is not None:
            raise ValueError("Known probability must not contain an unknown reason")
        return self


class CostLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item: str = Field(min_length=1)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str = Field(min_length=1)
    unit_cost_lower: Decimal | None = Field(default=None, ge=0)
    unit_cost_upper: Decimal | None = Field(default=None, ge=0)
    source_type: Literal["quote", "published_price", "historical", "assumption", "unknown"]
    source_ref: str | None

    @model_validator(mode="after")
    def validate_line(self) -> CostLineItem:
        if self.source_type == "unknown":
            if any(
                value is not None
                for value in (
                    self.quantity,
                    self.unit_cost_lower,
                    self.unit_cost_upper,
                )
            ):
                raise ValueError("Unknown cost line must not contain numeric costs")
            if self.source_ref is not None:
                raise ValueError("Unknown cost line must not claim a source")
            return self
        if self.quantity is None or self.unit_cost_lower is None or self.unit_cost_upper is None:
            raise ValueError("Known cost line requires quantity and cost range")
        if self.unit_cost_lower > self.unit_cost_upper:
            raise ValueError("Unit cost lower bound cannot exceed upper bound")
        if self.source_type in {"quote", "published_price", "historical"} and not self.source_ref:
            raise ValueError("Sourced cost line requires a source reference")
        return self


class CostEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    currency: str = Field(pattern=r"^[A-Z]{3}$")
    scope: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    line_items: list[CostLineItem] = Field(min_length=1)
    price_date: date | None
    expiry: date | None
    tax_shipping_assumption: str | None
    excluded_work: list[str]
    contingency_basis: str | None
    total_range: tuple[Decimal | None, Decimal | None]
    unknown_items: list[str]

    @model_validator(mode="after")
    def validate_total(self) -> CostEstimate:
        lower, upper = self.total_range
        if (lower is None) != (upper is None):
            raise ValueError("Cost total requires both bounds or neither")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("Cost lower bound cannot exceed upper bound")
        if (
            any(line.source_type == "unknown" for line in self.line_items)
            and not self.unknown_items
        ):
            raise ValueError("Unknown cost lines must be named in unknown_items")
        if lower is None and not self.unknown_items:
            raise ValueError("A cost estimate without a total must name its unknown items")
        return self


class NextValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: str
    success_criteria: list[str] = Field(min_length=1)
    stop_criteria: list[str] = Field(min_length=1)
    possible_outcomes: list[str] = Field(min_length=1)


class OpportunityCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    track: Track
    proposed_use: str = Field(min_length=1)
    target_population_or_scene: str = Field(min_length=1)
    need_evidence_refs: list[str]
    mechanism_steps: list[MechanismStep] = Field(min_length=1)
    current_alternatives: list[str]
    proposed_advantage: str
    comparison_metrics: list[str] = Field(min_length=1)
    gaps: dict[str, list[str]]
    next_validation: NextValidation
    probabilities: list[ProbabilityEstimate] = Field(min_length=1)
    costs: list[CostEstimate] = Field(min_length=1)
    change_trigger: str = Field(min_length=1)
    professional_opinions: dict[str, str]
    review_findings: list[str]
    evidence_cutoff: datetime
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def required_comparison_dimensions(self) -> OpportunityCard:
        required = {"science", "regulatory", "ip", "manufacturing", "commercial"}
        if not required.issubset(self.gaps):
            raise ValueError("Opportunity gaps must separate required professional dimensions")
        if not self.need_evidence_refs and not self.limitations:
            raise ValueError("Missing need evidence must remain explicit")
        return self


class ScientificBrief(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    problem_and_use: str = Field(min_length=1)
    facts: list[str] = Field(min_length=1)
    mechanism_chain: list[MechanismStep] = Field(min_length=1)
    strongest_support: list[str]
    strongest_counterevidence: list[str]
    direct_and_extrapolated_evidence: dict[str, list[str]]
    alternative_explanations: list[str]
    key_unknowns: list[str]
    proposed_verification: str = Field(min_length=1)
    resources: str = Field(min_length=1)
    falsification_conditions: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
