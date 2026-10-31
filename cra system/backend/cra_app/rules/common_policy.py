"""Load traceable common-policy descriptors separately from local activations."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommonPolicySource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=255)
    locator: str = Field(min_length=1, max_length=512)
    quote: str | None = None
    source_kind: Literal[
        "official",
        "authorized_internal",
        "synthetic_illustration",
    ]


class CommonPolicyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    jurisdiction: str = Field(min_length=1, max_length=64)
    official_effective_on: date
    acquisition_status: Literal["available", "partial", "unavailable"]
    official_status: Literal["final", "draft", "unknown"]
    sources: list[CommonPolicySource] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_source_when_available(self) -> "CommonPolicyEntry":
        if self.acquisition_status == "available" and not self.sources:
            raise ValueError("available common policy requires a source")
        if any(
            source.source_kind == "synthetic_illustration"
            and self.official_status != "unknown"
            for source in self.sources
        ):
            raise ValueError(
                "synthetic common-policy illustrations cannot claim official status"
            )
        return self


class CommonPolicySet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    package_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    entries: list[CommonPolicyEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids(self) -> "CommonPolicySet":
        ids = [entry.policy_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("common policy ids must be unique")
        return self

    def applicable(
        self, event_date: date, jurisdiction: str
    ) -> tuple[list[CommonPolicyEntry], list[str]]:
        applicable: list[CommonPolicyEntry] = []
        unknowns: list[str] = []
        for entry in self.entries:
            if entry.jurisdiction not in {jurisdiction, "*"}:
                continue
            if entry.official_effective_on > event_date:
                continue
            if entry.acquisition_status != "available":
                unknowns.append(
                    f"{entry.policy_id} source status is "
                    f"{entry.acquisition_status}"
                )
                continue
            applicable.append(entry)
        return applicable, unknowns


def load_common_policy_set(
    path: str | Path | None,
) -> CommonPolicySet | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return CommonPolicySet.model_validate(value)
