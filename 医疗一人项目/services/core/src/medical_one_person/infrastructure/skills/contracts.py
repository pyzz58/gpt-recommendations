from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NumericSummaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numbers: list[float] = Field(min_length=1, max_length=10_000)
    unit: str | None = Field(default=None, max_length=100)


class NumericSummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    sum: float
    mean: float
    minimum: float
    maximum: float
    unit: str | None
    limitations: list[str]


class ArtifactHashInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(max_length=1_000_000)
    media_type: str = Field(default="text/plain", max_length=100)


class ArtifactHashOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: str
    validation_status: str
