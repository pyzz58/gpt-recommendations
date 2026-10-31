"""Domain contracts for subject context, facts and local check decisions."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FactSourceKind = Literal[
    "original_record",
    "cra_confirmation",
    "other_response",
    "model_suggestion",
]
FactVerificationStatus = Literal[
    "original_record",
    "cra_confirmed",
    "reported_by_other",
    "model_candidate",
]
FactValueType = Literal["date", "datetime", "decimal", "string", "boolean", "json"]
DatePrecision = Literal["date", "minute", "second", "unknown"]
CoverageCategory = Literal[
    "laboratory",
    "documents",
    "consent",
    "medication",
    "safety",
    "visit_window",
    "other",
]
CoverageStatus = Literal["in_progress", "complete", "not_checked"]
CheckReason = Literal["declined_missing_data", "unreadable_skip"]


class SubjectContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactSourceRef(SubjectContract):
    source_type: Literal[
        "edc_row",
        "document_anchor",
        "user_action",
        "record",
        "external_query",
    ]
    source_id: str = Field(min_length=1, max_length=512)
    locator: str | None = Field(default=None, max_length=512)
    quote: str | None = None


class CreateSubjectCommand(SubjectContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    external_id: str = Field(min_length=1, max_length=128)
    identity_namespace: str = Field(min_length=1, max_length=64)
    deidentified_label: str | None = Field(default=None, max_length=128)


class MapSubjectIdentifierCommand(SubjectContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    identity_namespace: str = Field(min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=128)


class FactImportRow(SubjectContract):
    subject_external_id: str = Field(min_length=1, max_length=128)
    fact_key: str = Field(
        pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$"
    )
    value_raw: str = Field(min_length=1)
    value_type: FactValueType | None = None
    observed_on: date | None = None
    observed_at: datetime | None = None
    precision: DatePrecision | None = None
    unit: str | None = Field(default=None, max_length=32)
    repeat_instance: str | None = Field(default=None, max_length=128)
    visit_key: str | None = Field(default=None, max_length=64)
    source_kind: FactSourceKind = "original_record"
    verification_status: FactVerificationStatus | None = None
    source_ref: FactSourceRef

    @model_validator(mode="after")
    def validate_time_source(self) -> "FactImportRow":
        if self.observed_on is None and self.observed_at is None:
            raise ValueError("an imported fact requires observed_on or observed_at")
        if self.observed_on is not None and self.observed_at is not None:
            raise ValueError("observed_on and observed_at are mutually exclusive")
        if self.observed_at is not None and self.precision == "date":
            raise ValueError("datetime facts cannot claim date precision")
        if self.observed_on is not None and self.precision in {"minute", "second"}:
            raise ValueError("date-only facts cannot invent time precision")
        expected_status = {
            "original_record": "original_record",
            "cra_confirmation": "cra_confirmed",
            "other_response": "reported_by_other",
            "model_suggestion": "model_candidate",
        }[self.source_kind]
        if (
            self.verification_status is not None
            and self.verification_status != expected_status
        ):
            raise ValueError(
                "verification_status conflicts with source_kind"
            )
        return self


class ImportFactsCommand(SubjectContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    identity_namespace: str = Field(min_length=1, max_length=64)
    source_kind: FactSourceKind = "original_record"
    rows: list[FactImportRow] = Field(min_length=1, max_length=5000)


class ConfirmFactCommand(SubjectContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=500)


class CoverageBreakpointCommand(SubjectContract):
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)
    category: CoverageCategory
    scope_key: str = Field(min_length=1, max_length=128)
    status: CoverageStatus
    checked_through: str | None = Field(default=None, max_length=128)
    normal_scope_note: str | None = Field(default=None, max_length=1000)
    unverified_scope: list[str] = Field(default_factory=list, max_length=100)


class CheckDecisionCommand(SubjectContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    category: CoverageCategory
    check_type: str = Field(min_length=1, max_length=64)
    reason: CheckReason
    scope_start: date | None = None
    scope_end: date | None = None
    missing_keys: list[str] = Field(min_length=1, max_length=64)
    affected_paths: list[str] = Field(min_length=1, max_length=64)
    can_continue: list[str] = Field(default_factory=list, max_length=64)
    rule_version_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "CheckDecisionCommand":
        if (
            self.scope_start is not None
            and self.scope_end is not None
            and self.scope_end < self.scope_start
        ):
            raise ValueError("scope_end cannot precede scope_start")
        return self


class ResumeCheckDecisionCommand(SubjectContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=500)


class NormalizedFactValue(SubjectContract):
    value_type: FactValueType
    value: Any
    precision: DatePrecision
