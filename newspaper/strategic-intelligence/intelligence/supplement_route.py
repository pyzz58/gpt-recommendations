"""W38 targeted supplementation impact and handoff routing.

This joins a W25 request/result to the exact base and continuation W16
revisions, W27 Dossiers, optional W23 S8 reselection, and downstream review
requirements. It never turns added material into automatic stronger support.
"""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, Conflict, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind,
                        ReferenceUse, Representation, RightsGrant,
                        SourceTimes, StoredVersion, VersionReference,
                        VersionSubmission)
from .editorial import EditorialController, TopicDecisionCode
from .evidence import (EvidenceController, EvidenceRelation,
                       SupplementController, SupplementImpact,
                       SupplementMethod, SupplementStatus)
from .research import ResearchRevisionController
from .workflow import ResearchWorkflowController


class SupplementHandoff(str, Enum):
    MAINTAINED = "MAINTAINED"
    STRENGTHENED = "STRENGTHENED"
    WEAKENED = "WEAKENED"
    UNRESOLVED = "UNRESOLVED"
    PAUSE_SOURCE = "PAUSE_SOURCE"
    RETURN_TO_T03_S8 = "RETURN_TO_T03_S8"


class SupplementRouteRequest(Contract):
    schema_version: Literal[1] = 1
    route_id: Identifier
    spec_sha256: Digest
    theme_id: Identifier
    claim_version_id: Identifier
    supplement_request_version_id: Identifier
    supplement_result_version_id: Identifier
    base_revision_id: Identifier
    continuation_revision_id: Identifier
    base_dossier_snapshot_version_id: Identifier
    continuation_dossier_snapshot_version_id: Identifier
    original_topic_decision_id: Identifier
    s8_recheck_decision_id: Identifier | None = None
    next_action: NonBlank
    stop_reason: NonBlank | None = None
    created_at: AwareDatetime


class SupplementRouteRecord(Contract):
    schema_version: Literal[1] = 1
    route_id: Identifier
    route_version_id: Identifier
    spec_sha256: Digest
    theme_id: Identifier
    claim_version_id: Identifier
    supplement_request_version_id: Identifier
    supplement_result_version_id: Identifier
    base_revision_id: Identifier
    continuation_revision_id: Identifier
    base_dossier_snapshot_version_id: Identifier
    continuation_dossier_snapshot_version_id: Identifier
    original_topic_decision_id: Identifier
    s8_recheck_decision_id: Identifier | None
    handoff: SupplementHandoff
    before_relation: EvidenceRelation | None
    after_relation: EvidenceRelation | None
    impact: SupplementImpact
    new_evidence_version_ids: tuple[Identifier, ...]
    new_independent_root_ids: tuple[Identifier, ...]
    s8_review_required: bool
    research_recheck_required: bool
    independent_review_recheck_required: bool
    retry_requires_new_trigger: Literal[True] = True
    automatic_strength_granted: Literal[False] = False
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    next_action: NonBlank
    stop_reason: NonBlank | None
    created_at: AwareDatetime


class SupplementRouteError(ArchiveError):
    """Supplement route mismatch, never automatic content or publication PASS."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _relation_strength(relation: EvidenceRelation | None) -> int:
    return {
        EvidenceRelation.CONTRADICTS: -2,
        EvidenceRelation.IRRELEVANT: -1,
        EvidenceRelation.UNRESOLVED: 0,
        EvidenceRelation.BACKGROUND_ONLY: 1,
        EvidenceRelation.PARTIALLY_SUPPORTS: 2,
        EvidenceRelation.SUPPORTS: 3,
    }.get(relation, 0)


class SupplementRouteController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError(
                "SupplementRouteController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError(
                "SupplementRouteController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.supplements = SupplementController(archive, rights)
        self.evidence = EvidenceController(archive, rights)
        self.research = ResearchRevisionController(archive, rights)
        self.workflow = ResearchWorkflowController(archive, rights)
        self.editorial = EditorialController(archive, rights)

    @staticmethod
    def _current(stored: StoredVersion, label: str,
                 archive: Archive) -> None:
        latest = archive.latest(stored.submission.object_id)
        if latest is None or latest.submission.version_id != (
                stored.submission.version_id):
            raise SupplementRouteError(f"{label} is not current")

    def _decision_history(
            self, current_id: str) -> tuple[str, ...]:
        seen = set()
        history = []
        cursor = current_id
        while cursor is not None and cursor not in seen:
            seen.add(cursor)
            history.append(cursor)
            decision = self.editorial.load_decision(cursor)
            cursor = decision.previous_decision_id
        return tuple(history)

    def record(self, request: SupplementRouteRequest) -> StoredVersion:
        if not isinstance(request, SupplementRouteRequest):
            raise TypeError("record requires SupplementRouteRequest")
        request = SupplementRouteRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        supplement_request = self.supplements.load_request(
            request.supplement_request_version_id)
        result = self.supplements.load_result(
            request.supplement_result_version_id)
        if (supplement_request.theme_id != request.theme_id
                or supplement_request.spec_sha256 != request.spec_sha256
                or supplement_request.claim_version_id != (
                    request.claim_version_id)
                or supplement_request.assessment_version_id is None
                or result.theme_id != request.theme_id
                or result.spec_sha256 != request.spec_sha256
                or request.claim_version_id not in (
                    result.affected_claim_version_ids)):
            raise SupplementRouteError(
                "Supplement request/result do not bind the exact target claim")
        if result.method is not SupplementMethod.MANUAL:
            raise SupplementRouteError(
                "Only the manual supplement path is implemented")
        before = self.evidence.load_assessment(
            supplement_request.assessment_version_id)
        after_assessments = tuple(
            self.evidence.load_assessment(version_id)
            for version_id in result.assessment_version_ids)
        after_relation = (
            after_assessments[0].relation if after_assessments
            else result.after_relation)
        before_evidence = set(before.evidence_version_ids)
        after_evidence = {
            version_id for assessment in after_assessments
            for version_id in assessment.evidence_version_ids}
        new_evidence = tuple(sorted(
            after_evidence - before_evidence))
        before_roots = set(before.independent_root_ids)
        after_roots = {
            root_id for assessment in after_assessments
            for root_id in assessment.independent_root_ids}
        new_roots = tuple(sorted(after_roots - before_roots))

        if result.status is SupplementStatus.EVIDENCE_ADDED:
            if not new_evidence:
                raise SupplementRouteError(
                    "Added-evidence result does not add Evidence beyond the prior assessment")
            if result.impact is SupplementImpact.STRENGTHENED:
                if (_relation_strength(after_relation)
                        <= _relation_strength(before.relation)
                        or not new_roots):
                    raise SupplementRouteError(
                        "Strengthening needs stronger support and a new independent root")
            if result.impact is SupplementImpact.WEAKENED:
                if (_relation_strength(after_relation)
                        >= _relation_strength(before.relation)
                        and not any(
                            item.counterevidence for item in after_assessments)):
                    raise SupplementRouteError(
                        "Weakening needs weaker support or actual counterevidence")
        if result.impact is SupplementImpact.OBJECT_OR_SCOPE_CHANGED and not (
                result.s8_review_required):
            raise SupplementRouteError(
                "Object/scope change must require W23 S8 re-selection")
        needs_new_basis = (
            result.status is SupplementStatus.EVIDENCE_ADDED
            or result.impact in (
                SupplementImpact.STRENGTHENED,
                SupplementImpact.WEAKENED,
                SupplementImpact.OBJECT_OR_SCOPE_CHANGED))
        if needs_new_basis and (
                request.continuation_revision_id == request.base_revision_id
                or request.continuation_dossier_snapshot_version_id == (
                    request.base_dossier_snapshot_version_id)):
            raise SupplementRouteError(
                "Changed supplementation needs new W16/W27 versions")

        base_snapshot = self.workflow.load_snapshot(
            request.base_dossier_snapshot_version_id)
        continuation_snapshot = self.workflow.load_snapshot(
            request.continuation_dossier_snapshot_version_id)
        self._current(
            self.archive.get(
                request.continuation_dossier_snapshot_version_id),
            "continuation Dossier snapshot", self.archive)
        base_revision = self.research.load_revision(
            request.base_revision_id)
        continuation_revision = self.research.load_revision(
            request.continuation_revision_id)
        current_revision = self.research.current_revision(request.theme_id)
        if (base_snapshot.revision_id != base_revision.revision_id
                or continuation_snapshot.revision_id != (
                    continuation_revision.revision_id)
                or current_revision is None
                or current_revision.revision_id != (
                    continuation_revision.revision_id)
                or (
                    continuation_revision.revision_id
                    != base_revision.revision_id
                    and continuation_revision.based_on_revision_id
                    != base_revision.revision_id
                )
                or continuation_revision.theme_id != request.theme_id
                or continuation_revision.spec_sha256 != request.spec_sha256
                or request.claim_version_id not in (
                    continuation_revision.input_version_ids)
                or not set(result.evidence_version_ids) <= set(
                    continuation_revision.input_version_ids)
                or not set(result.assessment_version_ids) <= set(
                    continuation_revision.input_version_ids)):
            raise SupplementRouteError(
                "Continuation W16/W27 basis does not bind the supplement result")

        original = self.editorial.load_decision(
            request.original_topic_decision_id)
        if (original.decision is not TopicDecisionCode.COVER
                or original.theme_id != request.theme_id
                or original.spec_sha256 != request.spec_sha256):
            raise SupplementRouteError(
                "Original W23 selection is not an exact COVER")

        s8_required = (
            result.impact is SupplementImpact.OBJECT_OR_SCOPE_CHANGED
            or result.s8_review_required)
        recheck_decision = None
        if s8_required:
            if request.s8_recheck_decision_id is None:
                raise SupplementRouteError(
                    "S8-required supplement needs a new current W23 decision")
            recheck_decision = self.editorial.load_decision(
                request.s8_recheck_decision_id)
            current_decision = self.editorial.current_decision(
                recheck_decision.topic_id)
            if (current_decision is None
                    or current_decision.decision_id != (
                        recheck_decision.decision_id)
                    or recheck_decision.created_at < result.created_at
                    or request.original_topic_decision_id not in (
                        self._decision_history(
                            recheck_decision.decision_id))):
                raise SupplementRouteError(
                    "S8 recheck is not a current descendant of the original selection")
            if recheck_decision.decision is TopicDecisionCode.COVER:
                if (recheck_decision.s8_package_id is None
                        or recheck_decision.s8_package_id == (
                            original.s8_package_id)):
                    raise SupplementRouteError(
                        "Changed-scope COVER needs a new S8 prerequisite package")
                package_stored = self.archive.get(
                    EditorialController._version(
                        "S8-PACKAGE-",
                        recheck_decision.s8_package_id))
                if package_stored.submission.created_at < result.created_at:
                    raise SupplementRouteError(
                        "Changed-scope S8 package predates the supplement result")
            elif recheck_decision.decision not in (
                    TopicDecisionCode.REVISE,
                    TopicDecisionCode.WATCH,
                    TopicDecisionCode.DROP):
                raise SupplementRouteError(
                    "Unsupported W23 recheck disposition")
        else:
            current_decision = self.editorial.current_decision(
                original.topic_id)
            if (request.s8_recheck_decision_id is not None
                    or current_decision is None
                    or current_decision.decision_id != (
                        original.decision_id)):
                raise SupplementRouteError(
                    "Non-S8 supplement cannot carry or imply a changed W23 selection")

        if result.impact is SupplementImpact.OBJECT_OR_SCOPE_CHANGED:
            handoff = SupplementHandoff.RETURN_TO_T03_S8
        elif result.status is SupplementStatus.SOURCE_UNAVAILABLE:
            handoff = SupplementHandoff.PAUSE_SOURCE
        else:
            handoff = {
                SupplementImpact.UNCHANGED: SupplementHandoff.MAINTAINED,
                SupplementImpact.STRENGTHENED: SupplementHandoff.STRENGTHENED,
                SupplementImpact.WEAKENED: SupplementHandoff.WEAKENED,
                SupplementImpact.UNRESOLVED: SupplementHandoff.UNRESOLVED,
            }[result.impact]
        independent_review_recheck = (
            bool(new_evidence)
            or result.impact in (
                SupplementImpact.STRENGTHENED,
                SupplementImpact.WEAKENED,
                SupplementImpact.OBJECT_OR_SCOPE_CHANGED))
        if handoff is SupplementHandoff.PAUSE_SOURCE and not request.stop_reason:
            raise SupplementRouteError(
                "Source-unavailable route needs a concrete stop reason")

        version_id = _version(
            "SUPPLEMENT-ROUTE-", canonical([
                request.route_id, _digest(
                    request.model_dump(mode="json"))]))
        object_id = _object("SUPPLEMENT-ROUTE-OBJECT-", request.route_id)
        record = SupplementRouteRecord(
            route_id=request.route_id, route_version_id=version_id,
            spec_sha256=request.spec_sha256,
            theme_id=request.theme_id,
            claim_version_id=request.claim_version_id,
            supplement_request_version_id=(
                request.supplement_request_version_id),
            supplement_result_version_id=(
                request.supplement_result_version_id),
            base_revision_id=request.base_revision_id,
            continuation_revision_id=request.continuation_revision_id,
            base_dossier_snapshot_version_id=(
                request.base_dossier_snapshot_version_id),
            continuation_dossier_snapshot_version_id=(
                request.continuation_dossier_snapshot_version_id),
            original_topic_decision_id=(
                request.original_topic_decision_id),
            s8_recheck_decision_id=request.s8_recheck_decision_id,
            handoff=handoff,
            before_relation=before.relation,
            after_relation=after_relation,
            impact=result.impact,
            new_evidence_version_ids=new_evidence,
            new_independent_root_ids=new_roots,
            s8_review_required=s8_required,
            research_recheck_required=True,
            independent_review_recheck_required=(
                independent_review_recheck),
            next_action=request.next_action,
            stop_reason=request.stop_reason,
            created_at=request.created_at)
        refs = (
            VersionReference(
                target_version_id=request.supplement_request_version_id,
                use=ReferenceUse.BASIS, locator="exact supplement request"),
            VersionReference(
                target_version_id=request.supplement_result_version_id,
                use=ReferenceUse.BASIS, locator="exact supplement result"),
            VersionReference(
                target_version_id=request.claim_version_id,
                use=ReferenceUse.REVIEW_OF, locator="affected claim"),
            VersionReference(
                target_version_id=(
                    request.base_dossier_snapshot_version_id),
                use=ReferenceUse.BASIS, locator="base Dossier snapshot"),
            VersionReference(
                target_version_id=(
                    request.continuation_dossier_snapshot_version_id),
                use=ReferenceUse.BASIS,
                locator="continuation Dossier snapshot"),
            VersionReference(
                target_version_id=request.base_revision_id,
                use=ReferenceUse.BASIS, locator="base research revision"),
            VersionReference(
                target_version_id=request.continuation_revision_id,
                use=ReferenceUse.BASIS,
                locator="continuation research revision"),
            VersionReference(
                target_version_id=EditorialController._version(
                    "TOPIC-DECISION-",
                    request.original_topic_decision_id),
                use=ReferenceUse.BASIS, locator="original W23 COVER"),
            *(
                (VersionReference(
                    target_version_id=EditorialController._version(
                        "TOPIC-DECISION-",
                        request.s8_recheck_decision_id),
                    use=ReferenceUse.REVIEW_OF,
                    locator="W23 S8 recheck"),)
                if request.s8_recheck_decision_id is not None else ()
            ),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=ObjectKind.SUPPLEMENT_ROUTE,
            title=f"supplement route {request.route_id}",
            spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=refs)
        latest = self.archive.latest(object_id)
        if latest is not None:
            existing = self.load(latest.submission.version_id)
            if existing.route_version_id == version_id:
                return latest
            raise Conflict(
                "Supplement route ID already has different current content")
        try:
            return self.archive.append(
                submission,
                canonical(record.model_dump(mode="json")).encode(),
                expected_current={object_id: None})
        except Conflict:
            current = self.archive.latest(object_id)
            if current is not None and current.submission.version_id == (
                    version_id):
                return current
            raise

    def load(self, route_version_id: str) -> SupplementRouteRecord:
        stored = self.archive.get(route_version_id)
        if stored.submission.kind is not ObjectKind.SUPPLEMENT_ROUTE:
            raise SupplementRouteError(
                "Requested version is not a SupplementRoute")
        record = SupplementRouteRecord.model_validate_json(
            self.archive.read_body(route_version_id))
        if (record.route_version_id != route_version_id
                or stored.submission.spec_sha256 != record.spec_sha256
                or stored.submission.created_at != record.created_at):
            raise SupplementRouteError("Supplement route identity mismatch")
        return record
