"""Validated export scope, column mapping and confirmation commands."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StandardField = Literal[
    "subject_external_id",
    "visit_key",
    "analyte",
    "value_raw",
    "unit",
    "collected_on",
    "collected_at",
    "precision",
    "instance_type",
    "repeat_instance",
    "report_on",
    "report_revision",
    "specimen",
    "lower_limit",
    "upper_limit",
]


class EDCContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EDCExportScope(EDCContract):
    status: Literal["declared", "unknown"] = "unknown"
    forms: list[str] = Field(default_factory=list, max_length=100)
    subjects: list[str] = Field(default_factory=list, max_length=5000)
    sites: list[str] = Field(default_factory=list, max_length=500)
    date_start: date | None = None
    date_end: date | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    declared_complete: bool = False
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_scope(self) -> "EDCExportScope":
        if (
            self.date_start is not None
            and self.date_end is not None
            and self.date_end < self.date_start
        ):
            raise ValueError("date_end cannot precede date_start")
        if self.status == "unknown" and self.declared_complete:
            raise ValueError(
                "an unknown export scope cannot be declared complete"
            )
        return self


class EDCSheetMapping(EDCContract):
    header_row: int = Field(ge=1, le=10000)
    data_start_row: int = Field(ge=2, le=1000000)
    columns: dict[StandardField, str] = Field(default_factory=dict)
    included: bool = True

    @model_validator(mode="after")
    def validate_rows(self) -> "EDCSheetMapping":
        if self.data_start_row <= self.header_row:
            raise ValueError("data_start_row must follow header_row")
        return self


class EDCWorkbookMapping(EDCContract):
    sheets: dict[str, EDCSheetMapping] = Field(min_length=1)

    @model_validator(mode="after")
    def require_included_sheet(self) -> "EDCWorkbookMapping":
        if not any(item.included for item in self.sheets.values()):
            raise ValueError("at least one sheet must be included")
        return self


class ConfirmEDCImportCommand(EDCContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    mapping: EDCWorkbookMapping
    export_scope: EDCExportScope | None = None
    identity_namespace: str = Field(default="edc", min_length=1, max_length=64)
    save_mapping_name: str | None = Field(default=None, max_length=128)


class EDCImportUploadMetadata(EDCContract):
    site_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    export_started_at: datetime | None = None
    export_completed_at: datetime | None = None
    export_scope: EDCExportScope = Field(default_factory=EDCExportScope)
    included_sheets: list[str] = Field(default_factory=list, max_length=200)
    mapping_profile_id: uuid.UUID | None = None
    identity_namespace: str = Field(default="edc", min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_export_window(self) -> "EDCImportUploadMetadata":
        if self.export_started_at is not None:
            if self.export_started_at.tzinfo is None:
                raise ValueError(
                    "export_started_at requires an explicit UTC offset"
                )
        if self.export_completed_at is not None:
            if self.export_completed_at.tzinfo is None:
                raise ValueError(
                    "export_completed_at requires an explicit UTC offset"
                )
        if (
            self.export_started_at is not None
            and self.export_completed_at is not None
            and self.export_completed_at < self.export_started_at
        ):
            raise ValueError(
                "export_completed_at cannot precede export_started_at"
            )
        return self


class PreviewEDCImportCommand(EDCImportUploadMetadata):
    idempotency_key: str = Field(min_length=1, max_length=128)


class EDCSnapshotLookupCommand(EDCContract):
    subject_external_id: str = Field(min_length=1, max_length=128)
    analyte: str = Field(min_length=1, max_length=255)
    collected_on: date | None = None
    instance_type: str | None = Field(default=None, max_length=64)
