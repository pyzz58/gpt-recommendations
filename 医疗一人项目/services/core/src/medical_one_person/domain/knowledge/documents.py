from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class IngestState:
    STORED = "stored"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True)
class ParsedPassage:
    locator: dict[str, Any]
    text: str
    quality: dict[str, Any]


@dataclass(frozen=True)
class ParsedTable:
    locator: dict[str, Any]
    data: dict[str, Any]


@dataclass(frozen=True)
class ExtractionResult:
    extractor_version: str
    state: str
    passages: list[ParsedPassage] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    quality_findings: list[dict[str, Any]] = field(default_factory=list)


class DocumentParseError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
