from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatasetVersionKind(StrEnum):
    RAW = "raw"
    DERIVED = "derived"


class DatasetVersionState(StrEnum):
    READY = "ready"
    PARTIAL = "partial"
    REJECTED = "rejected"


class StatisticalMethod(StrEnum):
    DESCRIPTIVE_CONTINUOUS = "descriptive_continuous"
    TWO_GROUP_MEAN_DIFFERENCE = "two_group_mean_difference"
    PROPORTION_WILSON = "proportion_wilson"


class AnalysisState(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CleaningSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    select_columns: list[str] = Field(min_length=1)
    numeric_columns: list[str] = Field(default_factory=list)
    rename_columns: dict[str, str] = Field(default_factory=dict)
    drop_missing_columns: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_columns(self) -> CleaningSpec:
        selected = set(self.select_columns)
        renamed = set(self.rename_columns)
        dropped = set(self.drop_missing_columns)
        if not renamed.issubset(selected):
            raise ValueError("Renamed columns must be selected columns")
        if not dropped.issubset(selected):
            raise ValueError("Drop-missing columns must be selected columns")
        if not set(self.numeric_columns).issubset(selected):
            raise ValueError("Numeric columns must be selected columns")
        output_names = [self.rename_columns.get(column, column) for column in self.select_columns]
        if len(output_names) != len(set(output_names)):
            raise ValueError("Renaming would create duplicate output columns")
        return self


class StatisticalPlanSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=1, max_length=4_000)
    endpoint_column: str = Field(min_length=1)
    method: StatisticalMethod
    group_column: str | None = None
    analysis_set: str = Field(min_length=1, max_length=1_000)
    missing_policy: Literal["exclude_endpoint_missing", "fail_if_missing"] = (
        "exclude_endpoint_missing"
    )
    unit: str | None = Field(default=None, max_length=100)
    alpha: float = Field(default=0.05, gt=0, lt=1)
    expected_groups: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(min_length=1)
    exploratory: bool = False

    @model_validator(mode="after")
    def validate_method_contract(self) -> StatisticalPlanSpec:
        if self.method == StatisticalMethod.TWO_GROUP_MEAN_DIFFERENCE:
            if not self.group_column:
                raise ValueError("Two-group method requires a group column")
            if len(self.expected_groups) != 2:
                raise ValueError("Two-group method requires exactly two expected groups")
        elif self.group_column is not None:
            raise ValueError("Only the two-group method may declare a group column")
        if self.method == StatisticalMethod.PROPORTION_WILSON and self.unit:
            raise ValueError("Proportion analyses must not declare a measurement unit")
        return self
