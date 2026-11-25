from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceChannel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    channel_id: str
    host: str | None
    source_kind: Literal[
        "bibliographic_database",
        "fulltext_archive",
        "publisher",
        "preprint",
        "regulator",
        "patent_office",
        "local_library",
    ]
    official: bool


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str
    description: str
    general_web_search: Literal[False]
    preprint_policy: Literal["label_separately", "prohibited"]
    fulltext_policy: str
    channels: list[SourceChannel] = Field(min_length=1)

    @field_validator("policy_id")
    @classmethod
    def versioned_policy_id(cls, value: str) -> str:
        if not value.endswith(".v1"):
            raise ValueError("Source policy IDs must be versioned")
        return value


class SourcePolicyCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    policies: list[SourcePolicy]


class SourceSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str = Field(min_length=1, max_length=2000)
    policy_id: str
    date_from: date | None = None
    date_to: date | None = None


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    title: str
    abstract: str | None
    journal: str | None
    publication_date: date | None
    source_url: str
    source_kind: str
    peer_reviewed: bool
    preprint: bool
    retracted: bool
    doi: str | None
    pmid: str | None
    raw_fulltext_available: bool
    limitations: list[str]
