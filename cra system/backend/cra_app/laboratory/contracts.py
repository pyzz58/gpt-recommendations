"""Validated commands for laboratory review and comparison."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LabContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


CORRECTABLE_FIELDS = {
    "subject_external_id",
    "visit_key",
    "analyte_raw",
    "specimen",
    "collected_on",
    "collected_at",
    "instance_type_raw",
    "report_on",
    "report_revision",
    "value_raw",
    "unit_raw",
    "lower_limit_raw",
    "upper_limit_raw",
}


class ReviewLabObservationCommand(LabContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    action: Literal["confirm", "correct", "skip"]
    corrected_fields: dict[str, Any] = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ReviewLabObservationCommand":
        unknown = sorted(set(self.corrected_fields) - CORRECTABLE_FIELDS)
        if unknown:
            raise ValueError(
                "unsupported corrected fields: " + ", ".join(unknown)
            )
        if self.action == "correct" and not self.corrected_fields:
            raise ValueError("correct requires at least one corrected field")
        if self.action != "correct" and self.corrected_fields:
            raise ValueError("corrected_fields are only valid for correct")
        return self


class BatchConfirmLabObservationsCommand(LabContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    observation_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_ids(self) -> "BatchConfirmLabObservationsCommand":
        if len(self.observation_ids) != len(set(self.observation_ids)):
            raise ValueError("observation_ids must be unique")
        return self


class ManualLabObservationCommand(LabContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    subject_external_id: str = Field(min_length=1, max_length=128)
    visit_key: str | None = Field(default=None, max_length=128)
    analyte_raw: str = Field(min_length=1, max_length=255)
    specimen: str | None = Field(default=None, max_length=128)
    collected_on: date
    collected_at: datetime | None = None
    instance_type_raw: str = Field(min_length=1, max_length=128)
    report_on: date | None = None
    report_revision: str | None = Field(default=None, max_length=64)
    value_raw: str = Field(min_length=1, max_length=1000)
    unit_raw: str | None = Field(default=None, max_length=64)
    lower_limit_raw: str | None = Field(default=None, max_length=128)
    upper_limit_raw: str | None = Field(default=None, max_length=128)
    source_note: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_datetime(self) -> "ManualLabObservationCommand":
        if self.collected_at is not None:
            if self.collected_at.tzinfo is None:
                raise ValueError(
                    "collected_at requires an explicit UTC offset"
                )
            if self.collected_at.date() != self.collected_on:
                raise ValueError(
                    "collected_at date must match collected_on"
                )
        return self


class CreateLabComparisonCommand(LabContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    report_id: uuid.UUID
    edc_snapshot_id: uuid.UUID


class LinkLabIssuesCommand(LabContract):
    idempotency_key: str = Field(min_length=1, max_length=128)
    field_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_ids(self) -> "LinkLabIssuesCommand":
        if len(self.field_ids) != len(set(self.field_ids)):
            raise ValueError("field_ids must be unique")
        return self
