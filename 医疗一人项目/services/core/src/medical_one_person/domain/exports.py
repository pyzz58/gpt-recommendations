from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExportFormat(StrEnum):
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    PDF = "pdf"

    @property
    def media_type(self) -> str:
        return {
            ExportFormat.DOCX: (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            ExportFormat.PPTX: (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
            ExportFormat.XLSX: (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            ExportFormat.PDF: "application/pdf",
        }[self]


class ExportState(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExportValidationStatus(StrEnum):
    NOT_CHECKED = "not_checked"
    PASSED = "passed"
    FAILED = "failed"


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heading: str = Field(min_length=1, max_length=200)
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_content(self) -> ReportSection:
        if not self.paragraphs and not self.bullets:
            raise ValueError("A report section must contain a paragraph or bullet")
        return self


class ReportTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=200)
    columns: list[str] = Field(min_length=1, max_length=8)
    rows: list[list[str]] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_rectangular_rows(self) -> ReportTable:
        width = len(self.columns)
        if any(len(row) != width for row in self.rows):
            raise ValueError("Every report table row must match the column count")
        return self


class ReportSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[
        "project",
        "dataset",
        "dataset_version",
        "statistical_plan",
        "analysis_run",
        "analysis_review",
        "code",
    ]
    object_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=300)
    version: str = Field(min_length=1, max_length=100)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ReportReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str
    reviewer_role: Literal["A14", "A25", "A26"]
    decision: Literal["accepted"]
    summary: str
    reviewed_at: datetime


class ReportCalculation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    method: Literal[
        "descriptive_continuous",
        "two_group_mean_difference",
        "proportion_wilson",
    ]
    endpoint_column: str
    group_column: str | None = None
    expected_groups: list[str] = Field(default_factory=list)
    reported_value: float
    reported_n: int = Field(ge=1)
    unit: str | None = None


class StructuredReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=300)
    subtitle: str = Field(min_length=1, max_length=300)
    data_origin: Literal["synthetic", "real", "unknown"]
    mode: Literal["mock", "live"]
    created_at: datetime
    question: str
    method: str
    result_summary: list[tuple[str, str]]
    chart: dict[str, Any]
    sections: list[ReportSection] = Field(min_length=1)
    tables: list[ReportTable] = Field(min_length=1)
    sources: list[ReportSource] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    review: ReportReview
    calculation: ReportCalculation


class ExportTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    template_id: str = Field(pattern=r"^[a-z][a-z0-9.-]{2,80}$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    format: ExportFormat
    description: str = Field(min_length=1, max_length=1000)
    required_sections: list[str] = Field(min_length=1)


class ExportTemplateCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    templates: list[ExportTemplate] = Field(min_length=4)

    @model_validator(mode="after")
    def require_one_default_per_format(self) -> ExportTemplateCatalog:
        formats = [template.format for template in self.templates]
        if set(formats) != set(ExportFormat):
            raise ValueError("Template catalog must define each supported export format")
        identities = {(template.template_id, template.version) for template in self.templates}
        if len(identities) != len(self.templates):
            raise ValueError("Template identities must be unique")
        return self
