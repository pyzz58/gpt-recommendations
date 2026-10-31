"""W20 minimal source parsing and candidate-index interfaces.

The caller supplies already-authorized bytes. This module never fetches a URL,
does not infer facts from titles, and does not retain the full source body in a
candidate index.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Literal, Self

import feedparser
from lxml import html as lxml_html
from pydantic import AwareDatetime, model_validator
import trafilatura

from .archive import Archive, ArchiveError, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, Precision,
                        Representation, RightsGrant, SourceTimes, StoredVersion, TimePoint,
                        VersionSubmission)


class SourceType(str, Enum):
    FEED = "FEED"
    HTML = "HTML"
    JSON_API = "JSON_API"


class PermissionStateW20(str, Enum):
    CLEARED = "CLEARED"
    NOT_CLEARED = "NOT_CLEARED"
    UNKNOWN = "UNKNOWN"


class AcquisitionMethod(str, Enum):
    PROVIDED_BYTES = "PROVIDED_BYTES"
    MANUAL_PROBE = "MANUAL_PROBE"


class AcquisitionStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PARSE_FAILED = "PARSE_FAILED"


class CandidateStatus(str, Enum):
    READY_FOR_L2 = "READY_FOR_L2"
    NEEDS_CHECK = "NEEDS_CHECK"


class ExcerptKind(str, Enum):
    NONE = "NONE"
    SOURCE_PROVIDED = "SOURCE_PROVIDED"
    EXTRACTED = "EXTRACTED"


class IndexStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class GapCode(str, Enum):
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    PERMISSION_UNKNOWN = "PERMISSION_UNKNOWN"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
    EMPTY_SOURCE = "EMPTY_SOURCE"
    PARSE_ERROR = "PARSE_ERROR"
    MISSING_TITLE = "MISSING_TITLE"
    MISSING_LINK = "MISSING_LINK"
    MISSING_DATE = "MISSING_DATE"
    INVALID_DATE = "INVALID_DATE"
    FEED_BOZO = "FEED_BOZO"


class SourceDescriptor(Contract):
    schema_version: Literal[1] = 1
    source_id: Identifier
    name: NonBlank
    source_url: NonBlank
    source_type: SourceType
    language: NonBlank | None = None
    region: NonBlank | None = None
    sector: NonBlank | None = None
    ownership: NonBlank | None = None
    permission_state: PermissionStateW20
    permission_evidence: NonBlank
    acquisition_method: AcquisitionMethod = AcquisitionMethod.PROVIDED_BYTES

    @model_validator(mode="after")
    def permitted(self) -> Self:
        if self.permission_state is not PermissionStateW20.CLEARED:
            raise ValueError("Source bytes are not cleared for local parsing")
        return self


class AcquisitionRecord(Contract):
    schema_version: Literal[1] = 1
    source_id: Identifier
    requested_url: NonBlank
    method: AcquisitionMethod
    content_type: NonBlank
    acquired_at: AwareDatetime
    status: AcquisitionStatus
    raw_sha256: Digest | None = None
    byte_count: int
    error: NonBlank | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.status is AcquisitionStatus.AVAILABLE:
            if self.raw_sha256 is None or self.byte_count <= 0:
                raise ValueError("Available acquisition needs bytes and digest")
        elif self.status is AcquisitionStatus.PARSE_FAILED:
            if self.raw_sha256 is None or self.byte_count <= 0:
                raise ValueError("Parse failure still records the received bytes")
        elif self.raw_sha256 is not None or self.byte_count != 0:
            raise ValueError("Failed acquisition cannot claim bytes")
        if self.status is AcquisitionStatus.AVAILABLE and self.error is not None:
            raise ValueError("Available acquisition cannot carry an error")
        if self.status is not AcquisitionStatus.AVAILABLE and self.error is None:
            raise ValueError("Failed acquisition needs an error")
        return self


class SourceGap(Contract):
    source_id: Identifier
    code: GapCode
    message: NonBlank
    item_id: Identifier | None = None


class LineageLink(Contract):
    source_id: Identifier
    url: NonBlank | None = None
    relation: Literal["INDEX_SOURCE", "FEED_ENTRY", "SITE_ENTRY", "API_ENTRY"]


class CandidateRecord(Contract):
    schema_version: Literal[1] = 1
    candidate_id: Identifier
    source_id: Identifier
    title: NonBlank | None = None
    original_url: NonBlank | None = None
    excerpt: NonBlank | None = None
    excerpt_kind: ExcerptKind = ExcerptKind.NONE
    published_at: TimePoint = TimePoint(
        precision=Precision.UNKNOWN,
        reason="Publish time was not provided by the source")
    discovered_at: AwareDatetime
    source_timezone: NonBlank | None = None
    status: CandidateStatus
    lineage: tuple[LineageLink, ...]
    language: NonBlank | None = None
    region: NonBlank | None = None
    sector: NonBlank | None = None
    ownership: NonBlank | None = None
    gaps: tuple[SourceGap, ...] = ()
    evidence_status: Literal["L1_CLUE_ONLY"] = "L1_CLUE_ONLY"

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.excerpt is not None and len(self.excerpt) > 1000:
            raise ValueError("L1 excerpt is too long to be a lightweight clue")
        if (self.excerpt is None) != (self.excerpt_kind is ExcerptKind.NONE):
            raise ValueError("Excerpt text and kind must appear together")
        if not self.lineage:
            raise ValueError("Candidate needs source lineage")
        return self


class CandidateIndex(Contract):
    schema_version: Literal[1] = 1
    index_id: Identifier
    spec_sha256: Digest
    source: SourceDescriptor
    acquisition: AcquisitionRecord
    candidates: tuple[CandidateRecord, ...]
    gaps: tuple[SourceGap, ...]
    status: IndexStatus
    parser_versions: tuple[NonBlank, ...]
    coverage_note: NonBlank
    automatic_discovery_verified: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        ids = [item.candidate_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate candidate ID")
        if self.acquisition.source_id != self.source.source_id:
            raise ValueError("Acquisition source differs from index source")
        if any(item.source_id != self.source.source_id for item in self.candidates):
            raise ValueError("Candidate source differs from index source")
        if any(item.source_id != self.source.source_id for item in self.gaps):
            raise ValueError("Index gap source differs from index source")
        if self.status is IndexStatus.SUCCESS and self.gaps:
            raise ValueError("Successful index cannot carry gaps")
        if self.status is IndexStatus.FAILED and self.candidates:
            raise ValueError("Failed index cannot claim candidates")
        return self


class SourceAdapterError(ArchiveError):
    """A source parse/input failure, never evidence or editorial approval."""


def _id(*values: str) -> str:
    return "ID-" + hashlib.sha256(canonical(list(values)).encode()).hexdigest()[:32]


def _clean_text(value: str | None, *, limit: int = 1000) -> str | None:
    if value is None:
        return None
    text = lxml_html.fromstring(value).text_content()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if text else None


def _date_unknown(reason: str) -> TimePoint:
    return TimePoint(precision=Precision.UNKNOWN, reason=reason)


def _url_or_none(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value if re.match(r"^https?://", value, re.I) else None


def _parse_iso_time(value: str | None, *, provenance: str) -> TimePoint:
    if not value:
        return _date_unknown("Source item has no publication date")
    cleaned = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        try:
            parsed_date = date.fromisoformat(cleaned)
            return TimePoint(precision=Precision.DATE, value=parsed_date.isoformat(),
                             provenance=provenance,
                             uncertainty="Only a date, not an instant, was provided")
        except ValueError:
            return _date_unknown(f"Source publication date could not be parsed: {cleaned}")
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return _date_unknown("Source gave a local timestamp without a timezone")
        return TimePoint(precision=Precision.INSTANT, value=parsed.astimezone(timezone.utc).isoformat(),
                         source_timezone="UTC normalized from source timestamp",
                         provenance=provenance, uncertainty="Source timezone was not separately supplied")
    except ValueError:
        try:
            parsed_date = date.fromisoformat(cleaned)
            return TimePoint(precision=Precision.DATE, value=parsed_date.isoformat(),
                             provenance=provenance,
                             uncertainty="Only a date, not an instant, was provided")
        except ValueError:
            return _date_unknown(f"Source publication date could not be parsed: {cleaned}")


def _feed_time(entry, discovered_at: datetime) -> TimePoint:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    raw = entry.get("published") or entry.get("updated")
    if parsed is None:
        return _date_unknown("Feed item has no parseable publication/update time")
    try:
        value = datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return _date_unknown("Feed publication/update time is malformed")
    return TimePoint(
        precision=Precision.INSTANT, value=value.isoformat(),
        source_timezone="UTC normalized by feedparser from source timestamp",
        provenance=f"feedparser parsed timestamp; source text={raw!r}",
        uncertainty="Source timezone may have been normalized or omitted")


class SourceAdapter:
    def __init__(self):
        self.parser_versions = (
            f"feedparser {feedparser.__version__}",
            f"trafilatura {trafilatura.__version__}",
        )

    def _acquisition(self, source: SourceDescriptor, raw: bytes, content_type: str,
                     acquired_at: datetime, method: AcquisitionMethod) -> AcquisitionRecord:
        return AcquisitionRecord(
            source_id=source.source_id, requested_url=source.source_url,
            method=method, content_type=content_type, acquired_at=acquired_at,
            status=AcquisitionStatus.AVAILABLE,
            raw_sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw))

    def _candidate(self, *, source: SourceDescriptor, title: str | None,
                   url: str | None, excerpt: str | None, excerpt_kind: ExcerptKind,
                   published_at: TimePoint, discovered_at: datetime,
                   entry_key: str, relation: str, gaps: list[SourceGap]) -> CandidateRecord:
        candidate_id = _id("candidate", source.source_id, entry_key)
        if not title:
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.MISSING_TITLE,
                                  message="Source item has no title", item_id=candidate_id))
        if not url:
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.MISSING_LINK,
                                  message="Source item has no original URL", item_id=candidate_id))
        if published_at.precision is Precision.UNKNOWN and published_at.reason:
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.MISSING_DATE,
                                  message=published_at.reason, item_id=candidate_id))
        status = CandidateStatus.READY_FOR_L2 if title and url else CandidateStatus.NEEDS_CHECK
        return CandidateRecord(
            candidate_id=candidate_id, source_id=source.source_id,
            title=title, original_url=url, excerpt=excerpt,
            excerpt_kind=excerpt_kind, published_at=published_at,
            discovered_at=discovered_at,
            source_timezone=published_at.source_timezone, status=status,
            lineage=(LineageLink(source_id=source.source_id, url=url or source.source_url,
                                 relation=relation),),
            language=source.language, region=source.region,
            sector=source.sector, ownership=source.ownership,
            gaps=tuple(gaps), evidence_status="L1_CLUE_ONLY")

    def _feed(self, source: SourceDescriptor, raw: bytes, content_type: str,
              acquired_at: datetime, method: AcquisitionMethod,
              spec_sha256: str) -> CandidateIndex:
        parsed = feedparser.parse(raw)
        candidates = []
        gaps = []
        if getattr(parsed, "bozo", False):
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.FEED_BOZO,
                                  message=f"feedparser reported bozo: {getattr(parsed, 'bozo_exception', 'unknown')}"))
        for entry in parsed.entries:
            entry_gaps = []
            title = _clean_text(entry.get("title"), limit=300)
            url = _url_or_none(entry.get("link"))
            summary = _clean_text(entry.get("summary") or entry.get("description"))
            published_at = _feed_time(entry, acquired_at)
            candidates.append(self._candidate(
                source=source, title=title, url=url, excerpt=summary,
                excerpt_kind=ExcerptKind.SOURCE_PROVIDED if summary else ExcerptKind.NONE,
                published_at=published_at, discovered_at=acquired_at,
                entry_key=entry.get("id") or entry.get("guid") or url or title or str(len(candidates)),
                relation="FEED_ENTRY", gaps=entry_gaps))
        if not candidates:
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.EMPTY_SOURCE,
                                  message="Feed contained no candidate entries"))
        status = IndexStatus.FAILED if not candidates else (
            IndexStatus.PARTIAL if gaps or any(item.gaps for item in candidates)
            else IndexStatus.SUCCESS)
        acquisition = self._acquisition(source, raw, content_type, acquired_at, method)
        index_id = _id("index", source.source_id, acquisition.raw_sha256,
                       acquired_at.isoformat(), source.source_type.value)
        return CandidateIndex(
            index_id=index_id, spec_sha256=spec_sha256,
            source=source, acquisition=acquisition,
            candidates=tuple(candidates), gaps=tuple(gaps), status=status,
            parser_versions=self.parser_versions,
            coverage_note="Single supplied feed; no global or continuous coverage claim",
            automatic_discovery_verified=False, created_at=acquired_at)

    def _html(self, source: SourceDescriptor, raw: bytes, content_type: str,
              acquired_at: datetime, method: AcquisitionMethod,
              spec_sha256: str) -> CandidateIndex:
        result = trafilatura.extract(
            raw, url=source.source_url, output_format="json", with_metadata=True,
            include_comments=False, favor_precision=True, include_links=True)
        gaps = []
        candidates = []
        if result:
            data = json.loads(result)
            title = _clean_text(data.get("title"), limit=300)
            url = data.get("source") or source.source_url
            text = _clean_text(data.get("text"), limit=500)
            date_value = data.get("date")
            published_at = _parse_iso_time(
                date_value, provenance="trafilatura site metadata")
            entry_gaps = []
            candidates.append(self._candidate(
                source=source, title=title, url=url, excerpt=text,
                excerpt_kind=ExcerptKind.EXTRACTED if text else ExcerptKind.NONE,
                published_at=published_at, discovered_at=acquired_at,
                entry_key=url or title or "single-page", relation="SITE_ENTRY",
                gaps=entry_gaps))
        else:
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.EMPTY_SOURCE,
                                  message="Trafilatura extracted no usable page content"))
        acquisition = self._acquisition(source, raw, content_type, acquired_at, method)
        status = IndexStatus.FAILED if not candidates else (
            IndexStatus.PARTIAL if gaps or any(item.gaps for item in candidates)
            else IndexStatus.SUCCESS)
        return CandidateIndex(
            index_id=_id("index", source.source_id, acquisition.raw_sha256,
                         acquired_at.isoformat(), source.source_type.value),
            spec_sha256=spec_sha256,
            source=source, acquisition=acquisition, candidates=tuple(candidates),
            gaps=tuple(gaps), status=status, parser_versions=self.parser_versions,
            coverage_note="Single supplied page; extraction is not an original-source or body-rights decision",
            automatic_discovery_verified=False, created_at=acquired_at)

    def _json_api(self, source: SourceDescriptor, raw: bytes, content_type: str,
                  acquired_at: datetime, method: AcquisitionMethod,
                  spec_sha256: str) -> CandidateIndex:
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceAdapterError(f"Invalid JSON API payload: {exc}") from exc
        items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise SourceAdapterError("JSON API payload must be a list or contain an items list")
        candidates = []
        gaps = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                gaps.append(SourceGap(source_id=source.source_id, code=GapCode.PARSE_ERROR,
                                      message=f"API item {index} is not an object"))
                continue
            item_gaps = []
            title = _clean_text(item.get("title"), limit=300)
            url = _url_or_none(item.get("url") or item.get("link"))
            summary = _clean_text(item.get("summary") or item.get("description"))
            published_at = _parse_iso_time(
                item.get("published_at") or item.get("date"),
                provenance="JSON API item timestamp")
            candidates.append(self._candidate(
                source=source, title=title, url=url, excerpt=summary,
                excerpt_kind=ExcerptKind.SOURCE_PROVIDED if summary else ExcerptKind.NONE,
                published_at=published_at, discovered_at=acquired_at,
                entry_key=str(item.get("id") or url or title or index),
                relation="API_ENTRY", gaps=item_gaps))
        if not candidates:
            gaps.append(SourceGap(source_id=source.source_id, code=GapCode.EMPTY_SOURCE,
                                  message="JSON API returned no candidate items"))
        acquisition = self._acquisition(source, raw, content_type, acquired_at, method)
        status = IndexStatus.FAILED if not candidates else (
            IndexStatus.PARTIAL if gaps or any(item.gaps for item in candidates)
            else IndexStatus.SUCCESS)
        return CandidateIndex(
            index_id=_id("index", source.source_id, acquisition.raw_sha256,
                         acquired_at.isoformat(), source.source_type.value),
            spec_sha256=spec_sha256,
            source=source, acquisition=acquisition, candidates=tuple(candidates),
            gaps=tuple(gaps), status=status, parser_versions=self.parser_versions,
            coverage_note="Single supplied API response; no feed completeness or global coverage claim",
            automatic_discovery_verified=False, created_at=acquired_at)

    def _parse_failed(self, source: SourceDescriptor, raw: bytes, *,
                      acquired_at: datetime, content_type: str,
                      method: AcquisitionMethod, spec_sha256: str,
                      reason: str) -> CandidateIndex:
        acquisition = AcquisitionRecord(
            source_id=source.source_id, requested_url=source.source_url,
            method=method, content_type=content_type, acquired_at=acquired_at,
            status=AcquisitionStatus.PARSE_FAILED,
            raw_sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw),
            error=reason)
        gap = SourceGap(source_id=source.source_id, code=GapCode.PARSE_ERROR,
                        message=reason)
        return CandidateIndex(
            index_id=_id("parse-failed", source.source_id,
                         acquisition.raw_sha256, acquired_at.isoformat()),
            spec_sha256=spec_sha256, source=source, acquisition=acquisition,
            candidates=(), gaps=(gap,), status=IndexStatus.FAILED,
            parser_versions=self.parser_versions,
            coverage_note="Source bytes were received but no candidate was inferred from a parse failure",
            automatic_discovery_verified=False, created_at=acquired_at)

    def parse(self, source: SourceDescriptor, raw: bytes, *,
              acquired_at: datetime, content_type: str,
              method: AcquisitionMethod = AcquisitionMethod.PROVIDED_BYTES,
              spec_sha256: str) -> CandidateIndex:
        if not isinstance(source, SourceDescriptor):
            raise TypeError("parse requires SourceDescriptor")
        source = SourceDescriptor.model_validate_json(source.model_dump_json(warnings=False))
        if type(raw) is not bytes:
            raise TypeError("Source adapter requires exact authorized bytes")
        if not raw:
            return self.record_unavailable(
                source, acquired_at=acquired_at, content_type=content_type,
                method=method, spec_sha256=spec_sha256,
                reason="No bytes were returned")
        try:
            if source.source_type is SourceType.FEED:
                return self._feed(
                    source, raw, content_type, acquired_at, method, spec_sha256)
            if source.source_type is SourceType.HTML:
                return self._html(
                    source, raw, content_type, acquired_at, method, spec_sha256)
            return self._json_api(
                source, raw, content_type, acquired_at, method, spec_sha256)
        except Exception as exc:
            return self._parse_failed(
                source, raw, acquired_at=acquired_at, content_type=content_type,
                method=method, spec_sha256=spec_sha256,
                reason=f"Source parsing failed: {exc}")

    def record_unavailable(self, source: SourceDescriptor, *, acquired_at: datetime,
                           content_type: str,
                           method: AcquisitionMethod = AcquisitionMethod.PROVIDED_BYTES,
                           spec_sha256: str, reason: str) -> CandidateIndex:
        if not isinstance(source, SourceDescriptor):
            raise TypeError("record_unavailable requires SourceDescriptor")
        source = SourceDescriptor.model_validate_json(
            source.model_dump_json(warnings=False))
        acquisition = AcquisitionRecord(
            source_id=source.source_id, requested_url=source.source_url,
            method=method, content_type=content_type, acquired_at=acquired_at,
            status=AcquisitionStatus.UNAVAILABLE, raw_sha256=None, byte_count=0,
            error=reason)
        gap = SourceGap(source_id=source.source_id, code=GapCode.SOURCE_UNAVAILABLE,
                        message=reason)
        return CandidateIndex(
            index_id=_id("unavailable", source.source_id, acquired_at.isoformat()),
            spec_sha256=spec_sha256,
            source=source, acquisition=acquisition, candidates=(), gaps=(gap,),
            status=IndexStatus.FAILED, parser_versions=self.parser_versions,
            coverage_note="Source unavailable; no candidates inferred from title or memory",
            automatic_discovery_verified=False, created_at=acquired_at)


class SourceAdapterController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("SourceAdapterController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("SourceAdapterController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _version(index_id: str) -> str:
        return "CANDIDATE-INDEX-" + hashlib.sha256(
            canonical(["candidate-index", index_id]).encode()).hexdigest()[:32]

    def append_index(self, index: CandidateIndex) -> StoredVersion:
        if not isinstance(index, CandidateIndex):
            raise TypeError("append_index requires CandidateIndex")
        index = CandidateIndex.model_validate_json(index.model_dump_json(warnings=False))
        version_id = self._version(index.index_id)
        submission = VersionSubmission(
            schema_version=2, object_id="SOURCE-INDEX-" + hashlib.sha256(
                canonical([index.index_id]).encode()).hexdigest()[:32],
            kind=ObjectKind.CANDIDATE_INDEX, version_id=version_id,
            title=f"candidate index {index.source.source_id}",
            spec_sha256=index.spec_sha256, created_at=index.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY)
        return self.archive.append(
            submission, canonical(index.model_dump(mode="json")).encode())

    def load_index(self, index_id: str) -> CandidateIndex:
        version_id = self._version(index_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.CANDIDATE_INDEX:
            raise SourceAdapterError("Requested version is not a candidate index")
        index = CandidateIndex.model_validate_json(self.archive.read_body(version_id))
        if index.index_id != index_id:
            raise SourceAdapterError("Candidate index identity mismatch")
        return index
