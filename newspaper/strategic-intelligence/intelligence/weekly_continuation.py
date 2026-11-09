"""W39 two-snapshot theme continuation and T03 re-entry.

The controller first reads the old Article from the known-to-system snapshot and
the later Article from the publicly-available snapshot. It then binds the W38
supplement route, current W27 Dossier and any current W23 re-selection. A
continuation record never inserts the theme into an Edition.
"""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, Conflict, canonical
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank,
                        ObjectKind, ReferenceUse, Representation, RightsGrant,
                        SourceTimes, StoredVersion, UseContext,
                        VersionReference, VersionSubmission)
from .editorial import (ArticleType, EditorialController,
                        PublicationBasis, TopicDecisionCode)
from .history import (HistoryArchiveController, HistoryMode,
                      HistoryQueryRequest)
from .supplement_route import (SupplementRouteController,
                               SupplementRouteError)
from .workflow import ResearchWorkflowController


class ContinuationDisposition(str, Enum):
    HOLD = "HOLD"
    CONTINUE = "CONTINUE"
    MATURE_FOR_T03 = "MATURE_FOR_T03"
    SUSPEND = "SUSPEND"
    CLOSE = "CLOSE"


class TemporalEvidenceScope(str, Enum):
    PUBLICATION_TIMESTAMPS = "PUBLICATION_TIMESTAMPS"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class IssueSnapshot(Contract):
    issue_id: Identifier
    coverage_start: AwareDatetime
    coverage_end_exclusive: AwareDatetime
    publicly_available_as_of: AwareDatetime
    source_timezone: NonBlank

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if not (self.coverage_start < self.coverage_end_exclusive
                <= self.publicly_available_as_of):
            raise ValueError(
                "Issue coverage and public as-of are not ordered")
        return self


class CrossWeekContinuationRequest(Contract):
    schema_version: Literal[1] = 1
    continuation_id: Identifier
    spec_sha256: Digest
    theme_id: Identifier
    claim_version_id: Identifier
    earlier: IssueSnapshot
    later: IssueSnapshot
    old_article_version_id: Identifier
    old_exact_excerpt: NonBlank
    later_article_version_id: Identifier
    continuation_dossier_snapshot_version_id: Identifier
    supplement_route_version_id: Identifier | None = None
    t03_decision_id: Identifier | None = None
    disposition: ContinuationDisposition
    publication_basis: PublicationBasis | None = None
    use_context: UseContext
    next_action: NonBlank
    stop_reason: NonBlank | None = None
    temporal_scope: TemporalEvidenceScope
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.earlier.issue_id == self.later.issue_id:
            raise ValueError("Continuation needs two distinct issues")
        if not (
                self.earlier.coverage_end_exclusive
                <= self.later.coverage_start
        ):
            raise ValueError("Continuation issues overlap or are reversed")
        if self.disposition in (
                ContinuationDisposition.CONTINUE,
                ContinuationDisposition.MATURE_FOR_T03,
        ) and self.supplement_route_version_id is None:
            raise ValueError(
                "Continuing/maturing theme needs an exact supplement route")
        if self.disposition is ContinuationDisposition.MATURE_FOR_T03:
            if self.t03_decision_id is None or self.publication_basis is None:
                raise ValueError(
                    "Mature theme needs current T03 decision and publication basis")
        elif self.t03_decision_id is not None or self.publication_basis is not None:
            raise ValueError(
                "Only MATURE_FOR_T03 can carry a T03 decision/basis")
        if self.disposition in (
                ContinuationDisposition.SUSPEND,
                ContinuationDisposition.CLOSE,
        ) and not self.stop_reason:
            raise ValueError(
                "Suspended/closed continuation needs a concrete reason")
        return self


class CrossWeekContinuationRecord(Contract):
    schema_version: Literal[1] = 1
    continuation_id: Identifier
    continuation_version_id: Identifier
    spec_sha256: Digest
    theme_id: Identifier
    claim_version_id: Identifier
    earlier_issue_id: Identifier
    later_issue_id: Identifier
    earlier_public_as_of: AwareDatetime
    later_public_as_of: AwareDatetime
    old_article_version_id: Identifier
    later_article_version_id: Identifier
    old_exact_excerpt: NonBlank
    old_body_sha256: Digest
    later_body_sha256: Digest
    later_system_unknown: bool
    continuation_dossier_snapshot_version_id: Identifier
    supplement_route_version_id: Identifier | None
    t03_decision_id: Identifier | None
    disposition: ContinuationDisposition
    publication_basis: PublicationBasis | None
    handoff_owner: Literal["T03", "T05", "T11"]
    research_recheck_required: Literal[True] = True
    independent_review_recheck_required: bool
    requires_editorial_placement: Literal[True] = True
    automatic_issue_addition: Literal[False] = False
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    temporal_scope: TemporalEvidenceScope
    stage_evidence_eligible: Literal[False] = False
    next_action: NonBlank
    stop_reason: NonBlank | None
    created_at: AwareDatetime


class CrossWeekContinuationError(ArchiveError):
    """Continuation identity/basis failure, never an issue or content PASS."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


class CrossWeekContinuationController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError(
                "CrossWeekContinuationController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError(
                "CrossWeekContinuationController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.history = HistoryArchiveController(archive, rights)
        self.supplements = SupplementRouteController(archive, rights)
        self.workflow = ResearchWorkflowController(archive, rights)
        self.editorial = EditorialController(archive, rights)

    @staticmethod
    def _current(stored: StoredVersion, label: str,
                 archive: Archive) -> None:
        latest = archive.latest(stored.submission.object_id)
        if latest is None or latest.submission.version_id != (
                stored.submission.version_id):
            raise CrossWeekContinuationError(f"{label} is not current")

    def _old_query(self, request: CrossWeekContinuationRequest):
        stored = self.archive.get(request.old_article_version_id)
        if stored.submission.kind is not ObjectKind.ARTICLE:
            raise CrossWeekContinuationError("Old continuation item is not an Article")
        return self.history.query(HistoryQueryRequest(
            query_id=request.continuation_id + "-OLD",
            object_id=stored.submission.object_id,
            mode=HistoryMode.KNOWN_TO_SYSTEM_AS_OF,
            at=request.earlier.publicly_available_as_of,
            expected_kind=ObjectKind.ARTICLE,
            intended_use=MaterialUse.STORE_BODY,
            use_context=request.use_context.model_copy(
                update={"at": request.earlier.publicly_available_as_of}),
            include_body=True,
            created_at=request.earlier.publicly_available_as_of))

    def _later_query(self, request: CrossWeekContinuationRequest):
        stored = self.archive.get(request.later_article_version_id)
        if stored.submission.kind is not ObjectKind.ARTICLE:
            raise CrossWeekContinuationError(
                "Later continuation item is not an Article")
        return self.history.query(HistoryQueryRequest(
            query_id=request.continuation_id + "-LATER",
            object_id=stored.submission.object_id,
            mode=HistoryMode.PUBLICLY_AVAILABLE_AS_OF,
            at=request.later.publicly_available_as_of,
            expected_kind=ObjectKind.ARTICLE,
            intended_use=MaterialUse.STORE_BODY,
            use_context=request.use_context.model_copy(
                update={"at": request.later.publicly_available_as_of}),
            include_body=True,
            created_at=request.later.publicly_available_as_of))

    def record(
            self, request: CrossWeekContinuationRequest) -> StoredVersion:
        if not isinstance(request, CrossWeekContinuationRequest):
            raise TypeError(
                "record requires CrossWeekContinuationRequest")
        request = CrossWeekContinuationRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        old_query = self._old_query(request)
        later_query = self._later_query(request)
        if (old_query.selected is None
                or old_query.selected.version_id != (
                    request.old_article_version_id)
                or not old_query.body_available
                or old_query.body_text is None
                or request.old_exact_excerpt not in old_query.body_text):
            raise CrossWeekContinuationError(
                "Old Article/excerpt cannot be recovered from the earlier known snapshot")
        if (later_query.selected is None
                or later_query.selected.version_id != (
                    request.later_article_version_id)
                or not later_query.body_available
                or later_query.body_text is None):
            raise CrossWeekContinuationError(
                "Later Article cannot be recovered from the later public snapshot")
        if later_query.selected.ordinal <= old_query.selected.ordinal:
            raise CrossWeekContinuationError(
                "Later snapshot did not advance to a later Article version")

        continuation_stored = self.archive.get(
            request.continuation_dossier_snapshot_version_id)
        continuation_snapshot = self.workflow.load_snapshot(
            request.continuation_dossier_snapshot_version_id)
        self._current(
            continuation_stored, "continuation Dossier snapshot", self.archive)
        if (continuation_snapshot.theme_id != request.theme_id
                or continuation_snapshot.spec_sha256 != request.spec_sha256):
            raise CrossWeekContinuationError(
                "Continuation Dossier crosses theme or specification")

        supplement_record = None
        if request.supplement_route_version_id is not None:
            supplement_stored = self.archive.get(
                request.supplement_route_version_id)
            supplement_record = self.supplements.load(
                request.supplement_route_version_id)
            self._current(
                supplement_stored, "supplement route", self.archive)
            supplement_result = self.archive.get(
                supplement_record.supplement_result_version_id)
            if (supplement_record.theme_id != request.theme_id
                    or supplement_record.spec_sha256 != request.spec_sha256
                    or supplement_record.claim_version_id != (
                        request.claim_version_id)
                    or not (
                        request.earlier.publicly_available_as_of
                        <= supplement_result.submission.created_at
                        <= request.later.publicly_available_as_of)
                    or supplement_record.continuation_dossier_snapshot_version_id
                    != request.continuation_dossier_snapshot_version_id):
                raise CrossWeekContinuationError(
                    "Supplement route is outside the two-week continuation basis")

        t03_decision = None
        if request.disposition is ContinuationDisposition.MATURE_FOR_T03:
            t03_decision = self.editorial.load_decision(
                request.t03_decision_id)
            current = self.editorial.current_decision(t03_decision.topic_id)
            if (current is None
                    or current.decision_id != t03_decision.decision_id
                    or t03_decision.created_at < (
                        request.later.publicly_available_as_of)
                    or t03_decision.theme_id != request.theme_id
                    or t03_decision.spec_sha256 != request.spec_sha256
                    or t03_decision.publication_basis is not (
                        request.publication_basis)):
                raise CrossWeekContinuationError(
                    "Mature continuation lacks a current post-snapshot T03 decision")
            if (request.publication_basis is PublicationBasis.LONG_TERM_FEATURE
                    and t03_decision.article_type is not ArticleType.DEEP_THEME):
                raise CrossWeekContinuationError(
                    "Long-term theme cannot be downgraded to an automatic short form")

        handoff = {
            ContinuationDisposition.HOLD: "T05",
            ContinuationDisposition.CONTINUE: "T05",
            ContinuationDisposition.MATURE_FOR_T03: "T03",
            ContinuationDisposition.SUSPEND: "T11",
            ContinuationDisposition.CLOSE: "T11",
        }[request.disposition]
        version_id = _version(
            "CROSS-WEEK-CONTINUATION-",
            canonical([request.continuation_id, _digest(
                request.model_dump(mode="json"))]))
        object_id = _object(
            "CROSS-WEEK-CONTINUATION-OBJECT-",
            request.continuation_id)
        record = CrossWeekContinuationRecord(
            continuation_id=request.continuation_id,
            continuation_version_id=version_id,
            spec_sha256=request.spec_sha256,
            theme_id=request.theme_id,
            claim_version_id=request.claim_version_id,
            earlier_issue_id=request.earlier.issue_id,
            later_issue_id=request.later.issue_id,
            earlier_public_as_of=(
                request.earlier.publicly_available_as_of),
            later_public_as_of=(
                request.later.publicly_available_as_of),
            old_article_version_id=request.old_article_version_id,
            later_article_version_id=request.later_article_version_id,
            old_exact_excerpt=request.old_exact_excerpt,
            old_body_sha256=old_query.selected.body_sha256,
            later_body_sha256=later_query.selected.body_sha256,
            later_system_unknown=later_query.system_unknown_at_as_of,
            continuation_dossier_snapshot_version_id=(
                request.continuation_dossier_snapshot_version_id),
            supplement_route_version_id=(
                request.supplement_route_version_id),
            t03_decision_id=request.t03_decision_id,
            disposition=request.disposition,
            publication_basis=request.publication_basis,
            handoff_owner=handoff,
            independent_review_recheck_required=(
                request.disposition is ContinuationDisposition.MATURE_FOR_T03),
            temporal_scope=request.temporal_scope,
            next_action=request.next_action,
            stop_reason=request.stop_reason,
            created_at=request.created_at)
        refs = [
            VersionReference(
                target_version_id=request.old_article_version_id,
                use=ReferenceUse.REVIEW_OF,
                locator="earlier known Article"),
            VersionReference(
                target_version_id=request.later_article_version_id,
                use=ReferenceUse.SUPPORT,
                locator="later public Article"),
            VersionReference(
                target_version_id=request.claim_version_id,
                use=ReferenceUse.BASIS, locator="persistent theme Claim"),
            VersionReference(
                target_version_id=(
                    request.continuation_dossier_snapshot_version_id),
                use=ReferenceUse.BASIS,
                locator="current continuation Dossier"),
        ]
        if supplement_record is not None:
            refs.append(VersionReference(
                target_version_id=request.supplement_route_version_id,
                use=ReferenceUse.BASIS, locator="between-week supplement route"))
        if t03_decision is not None:
            refs.append(VersionReference(
                target_version_id=EditorialController._version(
                    "TOPIC-DECISION-", t03_decision.decision_id),
                use=ReferenceUse.REVIEW_OF,
                locator="current T03 after second snapshot"))
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=version_id,
            kind=ObjectKind.CROSS_WEEK_CONTINUATION,
            title=f"cross-week continuation {request.continuation_id}",
            spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=tuple(refs))
        latest = self.archive.latest(object_id)
        if latest is not None:
            existing = self.load(latest.submission.version_id)
            if existing.continuation_version_id == version_id:
                return latest
            raise Conflict(
                "Continuation ID already has different current content")
        return self.archive.append(
            submission,
            canonical(record.model_dump(mode="json")).encode(),
            expected_current={object_id: None})

    def load(
            self, continuation_version_id: str) -> CrossWeekContinuationRecord:
        stored = self.archive.get(continuation_version_id)
        if stored.submission.kind is not (
                ObjectKind.CROSS_WEEK_CONTINUATION):
            raise CrossWeekContinuationError(
                "Requested version is not a CrossWeekContinuation")
        record = CrossWeekContinuationRecord.model_validate_json(
            self.archive.read_body(continuation_version_id))
        if (record.continuation_version_id != continuation_version_id
                or stored.submission.spec_sha256 != record.spec_sha256
                or stored.submission.created_at != record.created_at):
            raise CrossWeekContinuationError(
                "Cross-week continuation identity mismatch")
        return record
