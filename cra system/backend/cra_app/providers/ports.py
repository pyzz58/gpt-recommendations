"""Provider-neutral source parsing and restricted capability ports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

CoverageStatus = Literal[
    "processed",
    "background",
    "not_applicable",
    "unsupported",
    "failed",
    "pending",
]


@dataclass(frozen=True)
class ParsedAnchor:
    anchor_type: str
    logical_node_id: str
    text: str
    ordinal: int
    section_path: list[str] = field(default_factory=list)
    style: dict[str, Any] = field(default_factory=dict)
    page_number: int | None = None
    bbox: list[float] | None = None
    table_index: int | None = None
    row_index: int | None = None
    column_index: int | None = None
    footnote_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CoverageUnit:
    unit_key: str
    unit_type: str
    status: CoverageStatus
    reason: str | None = None
    anchor_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseResult:
    parser_name: str
    parser_version: str
    anchors: tuple[ParsedAnchor, ...]
    coverage: tuple[CoverageUnit, ...]
    status: Literal["completed", "partial", "failed"]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderFailure:
    code: str
    message: str
    retryable: bool = False


class ParseDocumentPort(Protocol):
    name: str
    version: str

    def supports(self, media_type: str, filename: str) -> bool: ...

    def parse(
        self, content: bytes, *, media_type: str, filename: str
    ) -> ParseResult: ...


class ExtractRulesPort(Protocol):
    def extract_rules(self, *, anchors: list[ParsedAnchor]) -> Any: ...


class RecognizeLabPort(Protocol):
    def recognize_lab(self, *, content: bytes, media_type: str) -> Any: ...


class AnalyzeCasePort(Protocol):
    def analyze_case(self, *, facts: dict[str, Any]) -> Any: ...
