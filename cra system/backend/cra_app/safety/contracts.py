"""Validated safety-analysis, review and medical-response commands."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SafetyDimension = Literal[
    "ae_collection",
    "grade",
    "seriousness",
    "relatedness",
    "expectedness",
    "aesi",
    "dlt",
    "protocol_deviation",
    "reporting_timeliness",
]
SafetyEventType = Literal[
    "adverse_event",
    "serious_event_review",
    "laboratory_logic",
    "protocol_deviation",
    "mixed",
]


class SafetyContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CreateSafetyAssessmentCommand(SafetyContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    study_id: uuid.UUID
    site_id: uuid.UUID
    subject_id: uuid.UUID
    event_type: SafetyEventType
    event_date: date
    requested_dimensions: list[SafetyDimension] = Field(
        default_factory=list, max_length=32
    )
    lab_comparison_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "CreateSafetyAssessmentCommand":
        if len(self.requested_dimensions) != len(set(self.requested_dimensions)):
            raise ValueError("requested_dimensions must be unique")
        return self


class CraSafetyReviewCommand(SafetyContract):
    idempotency_key: str = Field(min_length=1, max_length=128)
    decision: Literal[
        "reviewed_candidate",
        "needs_clarification",
        "not_checked_by_user",
    ]
    dimensions: list[SafetyDimension] = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "CraSafetyReviewCommand":
        if len(self.dimensions) != len(set(self.dimensions)):
            raise ValueError("dimensions must be unique")
        return self


class MedicalSafetyResponseCommand(SafetyContract):
    idempotency_key: str = Field(min_length=1, max_length=128)
    respondent_role: Literal[
        "investigator",
        "medical_monitor",
        "medical_reviewer",
        "other",
    ]
    respondent_name: str | None = Field(default=None, max_length=255)
    response_text: str = Field(min_length=1, max_length=20000)
    dimension_responses: dict[SafetyDimension, str] = Field(
        default_factory=dict, max_length=32
    )
    source_note: str | None = Field(default=None, max_length=2000)


class LinkSafetyIssuesCommand(SafetyContract):
    idempotency_key: str = Field(min_length=1, max_length=128)
    dimensions: list[SafetyDimension] = Field(min_length=1, max_length=32)
    action_kind: Literal["medical_clarification", "other"] = (
        "medical_clarification"
    )
    requirement: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "LinkSafetyIssuesCommand":
        if len(self.dimensions) != len(set(self.dimensions)):
            raise ValueError("dimensions must be unique")
        return self
