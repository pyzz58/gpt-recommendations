"""W22 independent reference plans and scoped coverage-gap audits."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
from typing import Literal

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, Representation,
                        RightsGrant, SourceTimes, StoredVersion, TimePoint, VersionSubmission)
from .discovery import DiscoveryReview
from .sources import CandidateIndex


class CoverageBasis(str, Enum):
    INDEPENDENT_REFERENCE = "INDEPENDENT_REFERENCE"
    DOMAIN_QUOTA = "DOMAIN_QUOTA"
    CANDIDATE_DERIVED = "CANDIDATE_DERIVED"
    SELECTION_DERIVED = "SELECTION_DERIVED"


class ReferenceOrigin(str, Enum):
    EXTERNAL_QUERY = "EXTERNAL_QUERY"
    COPIED_FROM_CANDIDATE = "COPIED_FROM_CANDIDATE"
    COPIED_FROM_SELECTION = "COPIED_FROM_SELECTION"


class ReferenceChannelOutcome(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class ReferenceResult(str, Enum):
    COVERED_SELECTED = "COVERED_SELECTED"
    COVERED_UNDER_OTHER_TITLE = "COVERED_UNDER_OTHER_TITLE"
    DISCOVERED_PENDING_SELECTION = "DISCOVERED_PENDING_SELECTION"
    NOT_DISCOVERED = "NOT_DISCOVERED"
    CLUSTER_OR_FILTER_MISSED = "CLUSTER_OR_FILTER_MISSED"
    EDITOR_DISCARDED = "EDITOR_DISCARDED"
    MATERIAL_INSUFFICIENT = "MATERIAL_INSUFFICIENT"
    IMMATURE = "IMMATURE"
    DUPLICATE_COVERAGE = "DUPLICATE_COVERAGE"


class EditorialDecision(str, Enum):
    SELECTED = "SELECTED"
    DISCARDED = "DISCARDED"
    WATCH = "WATCH"
    MATERIAL_GAP = "MATERIAL_GAP"
    COVERED_UNDER_OTHER_TITLE = "COVERED_UNDER_OTHER_TITLE"
    NOT_EVALUATED = "NOT_EVALUATED"


class CoverageGapKind(str, Enum):
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    NOT_DISCOVERED_IN_SCOPE = "NOT_DISCOVERED_IN_SCOPE"
    CLUSTER_OR_FILTER_MISSED = "CLUSTER_OR_FILTER_MISSED"
    EDITOR_DISCARDED = "EDITOR_DISCARDED"
    MATERIAL_INSUFFICIENT = "MATERIAL_INSUFFICIENT"
    IMMATURE = "IMMATURE"
    DUPLICATE_COVERAGE = "DUPLICATE_COVERAGE"


class ReferenceChannelAttempt(Contract):
    channel_id: Identifier
    source_id: Identifier
    method: NonBlank
    attempted_at: AwareDatetime
    outcome: ReferenceChannelOutcome
    evidence_version_ids: tuple[Identifier, ...] = ()
    note: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.evidence_version_ids) != len(set(self.evidence_version_ids)):
            raise ValueError("Duplicate reference-channel evidence")
        return self


class ReferenceItem(Contract):
    item_id: Identifier
    title: NonBlank
    source_id: Identifier
    source_url: NonBlank
    channel_id: Identifier
    origin: ReferenceOrigin
    observed_at: AwareDatetime
    published_at: TimePoint
    region: NonBlank
    language: NonBlank
    domain: NonBlank
    event_key: Identifier | None = None
    evidence_version_ids: tuple[Identifier, ...] = ()
    positive_or_undercovered: bool = False
    priority_basis: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.origin is not ReferenceOrigin.EXTERNAL_QUERY:
            raise ValueError("Reference items must come from an independent external query")
        if len(self.evidence_version_ids) != len(set(self.evidence_version_ids)):
            raise ValueError("Duplicate reference evidence")
        return self


class CoverageReferencePlan(Contract):
    schema_version: Literal[1] = 1
    plan_id: Identifier
    spec_sha256: Digest
    basis: CoverageBasis
    fixed_at: AwareDatetime
    created_at: AwareDatetime
    window_start: AwareDatetime
    window_end: AwareDatetime
    scope_description: NonBlank
    selection_viewed_at_fix: Literal[False] = False
    channels: tuple[ReferenceChannelAttempt, ...]
    references: tuple[ReferenceItem, ...]
    limitations: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.basis is not CoverageBasis.INDEPENDENT_REFERENCE:
            raise ValueError("Coverage comparison requires an independent reference basis")
        if self.fixed_at > self.created_at:
            raise ValueError("Reference plan cannot be created before it was fixed")
        if self.window_end <= self.window_start:
            raise ValueError("Reference window must end after it starts")
        channel_ids = [item.channel_id for item in self.channels]
        reference_ids = [item.item_id for item in self.references]
        if not channel_ids or len(channel_ids) != len(set(channel_ids)):
            raise ValueError("Reference channels must be nonempty and unique")
        if not reference_ids or len(reference_ids) != len(set(reference_ids)):
            raise ValueError("References must be nonempty and unique")
        if any(item.channel_id not in set(channel_ids) for item in self.references):
            raise ValueError("Reference item points outside declared channels")
        return self


class ReferenceMatch(Contract):
    reference_item_id: Identifier
    candidate_ids: tuple[Identifier, ...]
    cluster_ids: tuple[Identifier, ...] = ()
    basis: NonBlank
    note: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("candidate", self.candidate_ids),
                ("cluster", self.cluster_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate reference match {name}")
        if not self.candidate_ids and not self.cluster_ids:
            raise ValueError("Reference match needs candidate or cluster identity")
        return self


class CandidateCoverageDecision(Contract):
    candidate_id: Identifier
    decision: EditorialDecision
    reason: NonBlank
    alternative_title: NonBlank | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.decision is EditorialDecision.COVERED_UNDER_OTHER_TITLE and not self.alternative_title:
            raise ValueError("Covered-under-other-title needs the actual alternative title")
        return self


class SelectionCoverageSnapshot(Contract):
    schema_version: Literal[1] = 1
    snapshot_id: Identifier
    proposal_id: Identifier
    decisions: tuple[CandidateCoverageDecision, ...]
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        ids = [item.candidate_id for item in self.decisions]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Selection snapshot candidates must be nonempty and unique")
        return self


class ReferenceComparison(Contract):
    reference_item_id: Identifier
    candidate_ids: tuple[Identifier, ...]
    cluster_ids: tuple[Identifier, ...]
    result: ReferenceResult
    reason: NonBlank


class CoverageGapRecord(Contract):
    gap_id: Identifier
    kind: CoverageGapKind
    reference_item_id: Identifier | None = None
    channel_id: Identifier | None = None
    reason: NonBlank
    next_owner: Literal["T02", "T03", "T04"]
    next_action: NonBlank
    priority: bool = False


class CoverageAudit(Contract):
    schema_version: Literal[1] = 1
    audit_id: Identifier
    plan_id: Identifier
    spec_sha256: Digest
    candidate_index_ids: tuple[Identifier, ...]
    proposal_id: Identifier
    selection_snapshot_id: Identifier | None = None
    comparisons: tuple[ReferenceComparison, ...]
    gaps: tuple[CoverageGapRecord, ...]
    scope_statement: NonBlank
    global_recall_claim: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("candidate index", self.candidate_index_ids),
                ("reference comparison", [item.reference_item_id for item in self.comparisons])):
            if not values or len(values) != len(set(values)):
                raise ValueError(f"Coverage audit {name} list must be nonempty and unique")
        if len({item.gap_id for item in self.gaps}) != len(self.gaps):
            raise ValueError("Duplicate coverage gap")
        return self


class CoverageError(ArchiveError):
    """A reference/comparison failure, never a global recall claim."""


def _id(*values: str) -> str:
    return "ID-" + hashlib.sha256(canonical(list(values)).encode()).hexdigest()[:32]


class CoverageComparator:
    def compare(self, plan: CoverageReferencePlan, indexes: tuple[CandidateIndex, ...],
                proposal: DiscoveryReview, *, audit_id: str, created_at: datetime,
                selection: SelectionCoverageSnapshot | None = None,
                matches: tuple[ReferenceMatch, ...] = ()) -> CoverageAudit:
        plan = CoverageReferencePlan.model_validate_json(
            plan.model_dump_json(warnings=False))
        proposal = DiscoveryReview.model_validate_json(
            proposal.model_dump_json(warnings=False))
        indexes = tuple(CandidateIndex.model_validate_json(
            item.model_dump_json(warnings=False)) for item in indexes)
        matches = tuple(ReferenceMatch.model_validate_json(
            item.model_dump_json(warnings=False)) for item in matches)
        if selection is not None:
            selection = SelectionCoverageSnapshot.model_validate_json(
                selection.model_dump_json(warnings=False))
            if selection.proposal_id != proposal.proposal_id:
                raise CoverageError("Selection snapshot does not belong to this discovery proposal")
        candidate_ids = {item.candidate_id for index in indexes for item in index.candidates}
        index_ids = {item.index_id for item in indexes}
        if index_ids != set(proposal.candidate_index_ids):
            raise CoverageError("Coverage indexes do not match the discovery proposal")
        if candidate_ids != set(proposal.candidate_ids):
            raise CoverageError("Coverage candidates do not match the discovery proposal")
        if any(plan.fixed_at > item.created_at for item in indexes):
            raise CoverageError("Reference plan was not fixed before every candidate index")
        if plan.fixed_at > proposal.created_at:
            raise CoverageError("Reference plan was not fixed before event clustering")
        reference_ids = {item.item_id for item in plan.references}
        if len({item.reference_item_id for item in matches}) != len(matches):
            raise CoverageError("Duplicate reference match")
        if any(item.reference_item_id not in reference_ids for item in matches):
            raise CoverageError("Reference match points to an unknown reference")
        for match in matches:
            if not set(match.candidate_ids) <= candidate_ids:
                raise CoverageError("Reference match contains a foreign candidate")
            if not set(match.cluster_ids) <= {
                    cluster.cluster_id for cluster in proposal.clusters}:
                raise CoverageError("Reference match contains a foreign cluster")
        decisions = {} if selection is None else {
            item.candidate_id: item for item in selection.decisions}
        if decisions and not set(decisions) <= candidate_ids:
            raise CoverageError("Selection snapshot contains a foreign candidate")
        match_by_reference = {item.reference_item_id: item for item in matches}
        cluster_by_id = {item.cluster_id: item for item in proposal.clusters}
        candidate_to_cluster = {
            candidate_id: cluster.cluster_id
            for cluster in proposal.clusters for candidate_id in cluster.candidate_ids}
        comparisons = []
        gaps = []
        covered_selection_ids: set[str] = set()

        for channel in plan.channels:
            if channel.outcome is ReferenceChannelOutcome.UNAVAILABLE:
                gaps.append(CoverageGapRecord(
                    gap_id=_id("gap", plan.plan_id, channel.channel_id, "unavailable"),
                    kind=CoverageGapKind.SOURCE_UNAVAILABLE,
                    channel_id=channel.channel_id,
                    reason=channel.note,
                    next_owner="T02",
                    next_action="Repair or replace this reference channel; do not infer that no important event occurred",
                    priority=False))

        for reference in plan.references:
            match = match_by_reference.get(reference.item_id)
            matched_candidates = set(match.candidate_ids) if match else set()
            matched_clusters = set(match.cluster_ids) if match else set()
            for cluster_id in matched_clusters:
                if cluster_id in cluster_by_id:
                    matched_candidates.update(cluster_by_id[cluster_id].candidate_ids)
            if not match and reference.event_key:
                matched_clusters.update(
                    cluster.cluster_id for cluster in proposal.clusters
                    if cluster.event_key == reference.event_key)
                for cluster_id in matched_clusters:
                    matched_candidates.update(cluster_by_id[cluster_id].candidate_ids)
            if not matched_candidates and not matched_clusters:
                result = ReferenceResult.NOT_DISCOVERED
                reason = "No matching candidate/cluster in the declared comparison scope"
                gaps.append(CoverageGapRecord(
                    gap_id=_id("gap", plan.plan_id, reference.item_id, "not-discovered"),
                    kind=CoverageGapKind.NOT_DISCOVERED_IN_SCOPE,
                    reference_item_id=reference.item_id,
                    reason=reason, next_owner="T02",
                    next_action="Check discovery route, language/region coverage and acquisition timing",
                    priority=reference.positive_or_undercovered))
            else:
                candidate_decisions = [
                    decisions.get(candidate_id) for candidate_id in matched_candidates]
                selected = [item for item in candidate_decisions
                            if item and item.decision is EditorialDecision.SELECTED]
                alternate = [item for item in candidate_decisions
                             if item and item.decision is EditorialDecision.COVERED_UNDER_OTHER_TITLE]
                material = [item for item in candidate_decisions
                            if item and item.decision is EditorialDecision.MATERIAL_GAP]
                watch = [item for item in candidate_decisions
                         if item and item.decision is EditorialDecision.WATCH]
                discarded = [item for item in candidate_decisions
                             if item and item.decision is EditorialDecision.DISCARDED]
                selection_key = (
                    min(matched_clusters) if matched_clusters else min(matched_candidates))
                if selection is None:
                    result = ReferenceResult.DISCOVERED_PENDING_SELECTION
                    reason = "Reference is represented in the candidate batch; no selection snapshot"
                elif selected and selection_key in covered_selection_ids:
                    result = ReferenceResult.DUPLICATE_COVERAGE
                    reason = "Reference maps to a selected event already covered by another reference"
                elif selected:
                    result = ReferenceResult.COVERED_SELECTED
                    reason = "Reference maps to a selected candidate"
                    covered_selection_ids.add(selection_key)
                elif alternate:
                    result = ReferenceResult.COVERED_UNDER_OTHER_TITLE
                    reason = alternate[0].reason
                elif material:
                    result = ReferenceResult.MATERIAL_INSUFFICIENT
                    reason = material[0].reason
                elif watch:
                    result = ReferenceResult.IMMATURE
                    reason = watch[0].reason
                elif discarded:
                    result = ReferenceResult.EDITOR_DISCARDED
                    reason = discarded[0].reason
                else:
                    result = ReferenceResult.CLUSTER_OR_FILTER_MISSED
                    reason = "Reference mapped to a cluster without an inspected selection outcome"
                gap_map = {
                    ReferenceResult.CLUSTER_OR_FILTER_MISSED: (
                        CoverageGapKind.CLUSTER_OR_FILTER_MISSED, "T03",
                        "Inspect clustering/filtering and retain raw candidates"),
                    ReferenceResult.EDITOR_DISCARDED: (
                        CoverageGapKind.EDITOR_DISCARDED, "T03",
                        "Review the editorial discard reason against the independent reference"),
                    ReferenceResult.MATERIAL_INSUFFICIENT: (
                        CoverageGapKind.MATERIAL_INSUFFICIENT, "T04",
                        "Targeted source or evidence acquisition needed before publication"),
                    ReferenceResult.IMMATURE: (
                        CoverageGapKind.IMMATURE, "T03",
                        "Keep in watch/research continuation with a concrete trigger"),
                    ReferenceResult.DUPLICATE_COVERAGE: (
                        CoverageGapKind.DUPLICATE_COVERAGE, "T03",
                        "Merge the reference comparison or identify distinct value"),
                }
                if result in gap_map:
                    kind, owner, action = gap_map[result]
                    gaps.append(CoverageGapRecord(
                        gap_id=_id("gap", plan.plan_id, reference.item_id, result.value),
                        kind=kind, reference_item_id=reference.item_id,
                        reason=reason, next_owner=owner, next_action=action,
                        priority=reference.positive_or_undercovered))
            comparisons.append(ReferenceComparison(
                reference_item_id=reference.item_id,
                candidate_ids=tuple(sorted(matched_candidates)),
                cluster_ids=tuple(sorted(matched_clusters)),
                result=result, reason=reason))
        return CoverageAudit(
            audit_id=audit_id, plan_id=plan.plan_id, spec_sha256=plan.spec_sha256,
            candidate_index_ids=tuple(sorted(index_ids)), proposal_id=proposal.proposal_id,
            selection_snapshot_id=selection.snapshot_id if selection else None,
            comparisons=tuple(comparisons), gaps=tuple(gaps),
            scope_statement=(
                f"Independent reference scope: {plan.scope_description}. "
                "Results apply only to the declared channels, window and references; no global recall rate."),
            global_recall_claim=False, created_at=created_at)


class CoverageController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("CoverageController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("CoverageController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _version(prefix: str, record_id: str) -> str:
        return prefix + hashlib.sha256(
            canonical([prefix, record_id]).encode()).hexdigest()[:32]

    def append_plan(self, plan: CoverageReferencePlan) -> StoredVersion:
        if not isinstance(plan, CoverageReferencePlan):
            raise TypeError("append_plan requires CoverageReferencePlan")
        plan = CoverageReferencePlan.model_validate_json(plan.model_dump_json(warnings=False))
        version_id = self._version("COVERAGE-PLAN-", plan.plan_id)
        submission = VersionSubmission(
            schema_version=2, object_id="COVERAGE-PLAN-" + hashlib.sha256(
                canonical([plan.plan_id]).encode()).hexdigest()[:32],
            kind=ObjectKind.COVERAGE_REFERENCE_PLAN, version_id=version_id,
            title="independent coverage reference plan", spec_sha256=plan.spec_sha256,
            created_at=plan.created_at, source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY)
        return self.archive.append(submission, canonical(plan.model_dump(mode="json")).encode())

    def load_plan(self, plan_id: str) -> CoverageReferencePlan:
        version_id = self._version("COVERAGE-PLAN-", plan_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.COVERAGE_REFERENCE_PLAN:
            raise CoverageError("Requested version is not a coverage reference plan")
        return CoverageReferencePlan.model_validate_json(self.archive.read_body(version_id))

    def append_audit(self, audit: CoverageAudit) -> StoredVersion:
        if not isinstance(audit, CoverageAudit):
            raise TypeError("append_audit requires CoverageAudit")
        audit = CoverageAudit.model_validate_json(audit.model_dump_json(warnings=False))
        version_id = self._version("COVERAGE-AUDIT-", audit.audit_id)
        submission = VersionSubmission(
            schema_version=2, object_id="COVERAGE-AUDIT-" + hashlib.sha256(
                canonical([audit.audit_id]).encode()).hexdigest()[:32],
            kind=ObjectKind.COVERAGE_AUDIT, version_id=version_id,
            title="scoped coverage gap audit", spec_sha256=audit.spec_sha256,
            created_at=audit.created_at, source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY)
        return self.archive.append(submission, canonical(audit.model_dump(mode="json")).encode())

    def load_audit(self, audit_id: str) -> CoverageAudit:
        version_id = self._version("COVERAGE-AUDIT-", audit_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.COVERAGE_AUDIT:
            raise CoverageError("Requested version is not a coverage audit")
        return CoverageAudit.model_validate_json(self.archive.read_body(version_id))
