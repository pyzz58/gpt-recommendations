"""W33 shared archive history, as-of queries and knowledge-reuse records."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
import hashlib
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, model_validator

from .adoption import AdoptionController
from .archive import (Archive, ArchiveError, BodyUnavailable, Conflict,
                      MissingVersion, canonical)
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank,
                        ObjectKind, Precision, ReferenceUse, Representation,
                        RightsGrant, SourceTimes, TimePoint, UseContext,
                        VersionReference, VersionSubmission)


class HistoryMode(str, Enum):
    CURRENT = "CURRENT"
    KNOWN_TO_SYSTEM_AS_OF = "KNOWN_TO_SYSTEM_AS_OF"
    PUBLICLY_AVAILABLE_AS_OF = "PUBLICLY_AVAILABLE_AS_OF"


class ReuseConclusion(str, Enum):
    SUPPORTED = "SUPPORTED"
    NARROWED = "NARROWED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class HistoryQueryRequest(Contract):
    schema_version: Literal[1] = 1
    query_id: Identifier
    object_id: Identifier
    mode: HistoryMode
    at: AwareDatetime | None = None
    expected_kind: ObjectKind | None = None
    intended_use: MaterialUse = MaterialUse.INDEX
    use_context: UseContext
    include_body: bool = False
    adoption_decision_id: Identifier | None = None
    required_scope: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.mode is not HistoryMode.CURRENT and self.at is None:
            raise ValueError("Historical mode needs an explicit as-of time")
        if self.mode is HistoryMode.CURRENT and self.at is not None:
            raise ValueError("Current mode uses creation/use time, not an as-of")
        if len(self.required_scope) != len(set(self.required_scope)):
            raise ValueError("Duplicate required adoption scope")
        if self.include_body and self.intended_use is MaterialUse.INDEX:
            raise ValueError("INDEX query cannot claim a full body")
        return self


class VersionSnapshot(Contract):
    version_id: Identifier
    object_id: Identifier
    kind: ObjectKind
    ordinal: int
    published_at: TimePoint
    recorded_at: AwareDatetime
    body_sha256: Digest | None
    body_bytes: int | None
    body_retention_revoked: bool


class HistoryQueryResult(Contract):
    query_id: Identifier
    mode: HistoryMode
    object_id: Identifier
    as_of: AwareDatetime
    selected: VersionSnapshot | None
    known_to_system_version_id: Identifier | None
    current_version_id: Identifier | None
    later_version_ids: tuple[Identifier, ...]
    system_unknown_at_as_of: bool
    body_text: str | None = None
    body_hex: str | None = None
    body_available: bool = False
    adoption_current: bool | None = None
    limitations: tuple[NonBlank, ...] = ()
    current_use_authorized: Literal[False] = False


class KnowledgeReuseRequest(Contract):
    schema_version: Literal[1] = 1
    reuse_id: Identifier
    source_version_id: Identifier
    article_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    intended_use: MaterialUse = MaterialUse.MODEL_PROCESS
    use_context: UseContext
    original_conditions: tuple[NonBlank, ...]
    current_conditions: tuple[NonBlank, ...]
    changed_conditions: tuple[NonBlank, ...]
    conclusion: ReuseConclusion
    evidence_version_ids: tuple[Identifier, ...]
    does_not_prove: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("original condition", self.original_conditions),
                ("current condition", self.current_conditions),
                ("changed condition", self.changed_conditions),
                ("evidence", self.evidence_version_ids)):
            if (not values and name in (
                    "original condition", "current condition", "evidence")):
                raise ValueError(f"Knowledge reuse needs {name}s")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate knowledge-reuse {name}")
        return self


class KnowledgeReuseRecord(Contract):
    schema_version: Literal[1] = 1
    reuse_id: Identifier
    reuse_version_id: Identifier
    source_version_id: Identifier
    current_source_version_id: Identifier
    article_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    intended_use: MaterialUse
    original_conditions: tuple[NonBlank, ...]
    current_conditions: tuple[NonBlank, ...]
    changed_conditions: tuple[NonBlank, ...]
    conclusion: ReuseConclusion
    evidence_version_ids: tuple[Identifier, ...]
    does_not_prove: NonBlank
    reader_state_recorded: Literal[False] = False
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime


class HistoryArchiveError(ArchiveError):
    """History query or reuse-record failure, never current adoption authority."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise HistoryArchiveError("Stored publication instant has no timezone")
    return parsed


def _published_by(value: TimePoint, at: datetime) -> bool:
    if value.precision is Precision.INSTANT and value.value is not None:
        return _parse_datetime(value.value) <= at
    if value.precision is Precision.DATE and value.value is not None:
        if not value.source_timezone:
            raise HistoryArchiveError(
                "Date publication needs its source timezone for as-of evaluation")
        try:
            zone = ZoneInfo(value.source_timezone)
        except ZoneInfoNotFoundError as exc:
            raise HistoryArchiveError(
                "Unknown publication source timezone") from exc
        published_date = date.fromisoformat(value.value)
        next_day = datetime.combine(
            published_date + timedelta(days=1), datetime.min.time(), zone)
        return at >= next_day
    if value.precision in (Precision.INSTANT_RANGE, Precision.DATE_RANGE):
        if value.end_value is None:
            return False
        if value.precision is Precision.INSTANT_RANGE:
            return _parse_datetime(value.end_value) <= at
        if not value.source_timezone:
            raise HistoryArchiveError(
                "Date publication range needs its source timezone")
        try:
            zone = ZoneInfo(value.source_timezone)
        except ZoneInfoNotFoundError as exc:
            raise HistoryArchiveError(
                "Unknown publication source timezone") from exc
        end_date = date.fromisoformat(value.end_value)
        end_of_day = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time(), zone)
        return at >= end_of_day
    return False


class HistoryArchiveController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("HistoryArchiveController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError(
                "HistoryArchiveController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.adoption = AdoptionController(archive, rights)

    @staticmethod
    def _snapshot(stored) -> VersionSnapshot:
        return VersionSnapshot(
            version_id=stored.submission.version_id,
            object_id=stored.submission.object_id,
            kind=stored.submission.kind,
            ordinal=stored.ordinal,
            published_at=stored.submission.source_times.published,
            recorded_at=stored.recorded_at,
            body_sha256=stored.body_sha256,
            body_bytes=stored.body_bytes,
            body_retention_revoked=stored.body_retention_revoked)

    def _read_body_safely(self, request: HistoryQueryRequest,
                          version_id: str | None) -> tuple[
                              str | None, str | None, bool, tuple[str, ...]]:
        if not request.include_body or version_id is None:
            return None, None, False, ()
        if request.mode is HistoryMode.CURRENT:
            from .correction import is_version_restricted
            if is_version_restricted(
                    self.archive, version_id,
                    request.required_scope
                    or (request.intended_use.value,)):
                return None, None, False, (
                    "Current body is withheld by an active correction restriction",)
        try:
            self.archive.check_version_use(
                version_id, request.intended_use, request.use_context)
            body = self.archive.read_body(version_id)
        except ArchiveError as exc:
            return None, None, False, (
                f"Body withheld under current use/retention limits: {exc}",)
        if request.intended_use is MaterialUse.INDEX:
            return None, None, False, ("INDEX never returns original body",)
        try:
            return body.decode("utf-8"), None, True, ()
        except UnicodeDecodeError:
            return None, body.hex(), True, ()

    def query(self, request: HistoryQueryRequest) -> HistoryQueryResult:
        if not isinstance(request, HistoryQueryRequest):
            raise TypeError("query requires HistoryQueryRequest")
        request = HistoryQueryRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        history = self.archive.history(request.object_id)
        if not history:
            raise HistoryArchiveError("History object does not exist")
        if request.expected_kind is not None and any(
                item.submission.kind is not request.expected_kind
                for item in history):
            raise HistoryArchiveError(
                "History object kind does not match the requested kind")
        current = history[-1]
        at = request.created_at if request.mode is HistoryMode.CURRENT else request.at
        assert at is not None
        known = [
            item for item in history
            if item.recorded_at <= at
            and _published_by(item.submission.source_times.published, at)
        ]
        public = [
            item for item in history
            if _published_by(item.submission.source_times.published, at)
        ]
        limitations = []
        if request.mode is HistoryMode.CURRENT:
            selected = current
            known_selected = (
                history[-1] if history[-1].recorded_at <= at else None)
        elif request.mode is HistoryMode.KNOWN_TO_SYSTEM_AS_OF:
            selected = known[-1] if known else None
            known_selected = selected
            if selected is None:
                limitations.append(
                    "No version was both published and recorded by the as-of time")
        else:
            selected = public[-1] if public else None
            known_selected = known[-1] if known else None
            if selected is None:
                limitations.append(
                    "No version had confirmable public availability by the as-of time")
        system_unknown = bool(
            selected is not None
            and selected.recorded_at > at)
        if system_unknown:
            limitations.append(
                "Later-recorded version was publicly available but unknown to the system at as-of")
        later = ()
        if selected is not None:
            later = tuple(
                item.submission.version_id for item in history
                if item.ordinal > selected.ordinal)
        body_text, body_hex, body_available, body_limits = (
            self._read_body_safely(
                request,
                selected.submission.version_id if selected is not None else None))
        limitations.extend(body_limits)
        adoption_current = None
        if request.adoption_decision_id is not None:
            try:
                adoption = self.adoption.load(request.adoption_decision_id)
            except ArchiveError:
                adoption_current = False
            else:
                adoption_current = (
                    adoption.decided_at <= at
                    and self.adoption.is_current(
                        request.adoption_decision_id, at))
            if (adoption_current and request.required_scope
                    and not self.adoption.authorizes(
                        request.adoption_decision_id,
                        request.required_scope, at)):
                adoption_current = False
                limitations.append(
                    "Adoption is current but does not cover the requested use")
        return HistoryQueryResult(
            query_id=request.query_id, mode=request.mode,
            object_id=request.object_id, as_of=at,
            selected=self._snapshot(selected) if selected else None,
            known_to_system_version_id=(
                known_selected.submission.version_id
                if known_selected else None),
            current_version_id=current.submission.version_id,
            later_version_ids=later,
            system_unknown_at_as_of=system_unknown,
            body_text=body_text, body_hex=body_hex,
            body_available=body_available,
            adoption_current=adoption_current,
            limitations=tuple(limitations))

    def rebuild_index(self) -> int:
        """Rebuild navigation from Archive source records; never a second source."""
        return self.archive.rebuild_index()

    def record_reuse(
            self, request: KnowledgeReuseRequest) -> KnowledgeReuseRecord:
        if not isinstance(request, KnowledgeReuseRequest):
            raise TypeError("record_reuse requires KnowledgeReuseRequest")
        request = KnowledgeReuseRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        source = self.archive.get(request.source_version_id)
        if source.submission.kind not in (
                ObjectKind.CONCEPT, ObjectKind.BACKGROUND,
                ObjectKind.METHOD_USE, ObjectKind.TRANSMISSION_LINK):
            raise HistoryArchiveError(
                "Knowledge reuse source is not Concept/Background/MethodUse/TransmissionLink")
        if source.submission.spec_sha256 != request.spec_sha256:
            raise HistoryArchiveError(
                "Knowledge reuse source uses another specification")
        latest_source = self.archive.latest(source.submission.object_id)
        if latest_source is None:
            raise HistoryArchiveError("Knowledge reuse source has no current history")
        article = self.archive.get(request.article_version_id)
        if article.submission.kind is not ObjectKind.ARTICLE:
            raise HistoryArchiveError("Knowledge reuse target is not an Article")
        if (article.submission.spec_sha256 != request.spec_sha256
                or article.body_retention_revoked):
            raise HistoryArchiveError(
                "Knowledge reuse Article is unavailable or cross-specification")
        latest_article = self.archive.latest(article.submission.object_id)
        if (latest_article is None
                or latest_article.submission.version_id
                != article.submission.version_id):
            raise HistoryArchiveError(
                "Knowledge reuse Article is not current")
        for evidence_id in request.evidence_version_ids:
            self.archive.get(evidence_id)
        self.archive.check_version_use(
            request.source_version_id, request.intended_use,
            request.use_context)
        from .correction import is_version_restricted
        if is_version_restricted(
                self.archive, request.source_version_id,
                (request.intended_use.value,)):
            raise HistoryArchiveError(
                "Knowledge reuse source is under an active correction restriction")
        reuse_version_id = _version(
            "KNOWLEDGE-REUSE-", canonical([
                request.reuse_id, _digest(request.model_dump(mode="json"))]))
        record = KnowledgeReuseRecord(
            reuse_id=request.reuse_id,
            reuse_version_id=reuse_version_id,
            source_version_id=request.source_version_id,
            current_source_version_id=latest_source.submission.version_id,
            article_version_id=request.article_version_id,
            theme_id=request.theme_id, spec_sha256=request.spec_sha256,
            intended_use=request.intended_use,
            original_conditions=request.original_conditions,
            current_conditions=request.current_conditions,
            changed_conditions=request.changed_conditions,
            conclusion=request.conclusion,
            evidence_version_ids=request.evidence_version_ids,
            does_not_prove=request.does_not_prove,
            created_at=request.created_at)
        object_id = _object("KNOWLEDGE-REUSE-OBJECT-", request.reuse_id)
        try:
            existing = self.archive.get(reuse_version_id)
            expected_bytes = canonical(record.model_dump(mode="json")).encode()
            if (existing.submission.kind is not ObjectKind.KNOWLEDGE_REUSE
                    or self.archive.read_body(reuse_version_id)
                    != expected_bytes):
                raise HistoryArchiveError(
                    "Knowledge reuse version ID is already in use")
            return record
        except MissingVersion:
            pass
        latest = self.archive.latest(object_id)
        references = (
            VersionReference(
                target_version_id=request.source_version_id,
                use=ReferenceUse.BACKGROUND, locator="exact reused source"),
            VersionReference(
                target_version_id=latest_source.submission.version_id,
                use=ReferenceUse.BASIS, locator="current source version"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.BASIS, locator="reuse target Article"),
            *(
                VersionReference(
                    target_version_id=version_id,
                    use=ReferenceUse.SUPPORT,
                    locator=f"reuse evidence {index}")
                for index, version_id in enumerate(
                    request.evidence_version_ids)
            ),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=reuse_version_id,
            parent_version_id=(
                latest.submission.version_id if latest else None),
            kind=ObjectKind.KNOWLEDGE_REUSE,
            title=f"knowledge reuse {request.reuse_id}",
            spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=references)
        expected = {
            object_id: latest.submission.version_id if latest else None,
            source.submission.object_id: source.submission.version_id,
            latest_source.submission.object_id:
                latest_source.submission.version_id,
            article.submission.object_id: article.submission.version_id,
        }
        for evidence_id in request.evidence_version_ids:
            stored = self.archive.get(evidence_id)
            expected[stored.submission.object_id] = stored.submission.version_id
        record_bytes = canonical(record.model_dump(mode="json")).encode()
        try:
            self.archive.append(
                submission, record_bytes, expected_current=expected)
        except Conflict:
            concurrent = self.archive.get(reuse_version_id)
            if (concurrent.submission.kind is not ObjectKind.KNOWLEDGE_REUSE
                    or self.archive.read_body(reuse_version_id)
                    != record_bytes):
                raise
        return record
