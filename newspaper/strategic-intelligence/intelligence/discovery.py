"""W21 event-cluster proposals, recorded lineage and exploration queue."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
from typing import Literal

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, Representation,
                        RightsGrant, SourceTimes, StoredVersion, TimePoint, VersionSubmission)
from .sources import CandidateIndex, CandidateRecord, CandidateStatus


class ClusterStatus(str, Enum):
    PROPOSED = "PROPOSED"
    NEEDS_EDITOR = "NEEDS_EDITOR"


class IndependenceStatus(str, Enum):
    RECORDED = "RECORDED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class LineageRole(str, Enum):
    ORIGINAL = "ORIGINAL"
    REPOST = "REPOST"
    UNKNOWN = "UNKNOWN"


class MergeBasis(str, Enum):
    EXPLICIT_EVENT_KEY = "EXPLICIT_EVENT_KEY"
    SHARED_LINEAGE_ROOT = "SHARED_LINEAGE_ROOT"
    CANONICAL_ORIGIN = "CANONICAL_ORIGIN"
    EXACT_URL = "EXACT_URL"
    SINGLE_CANDIDATE = "SINGLE_CANDIDATE"


class ExplorationReason(str, Enum):
    LOW_HEAT_OR_SINGLE_SOURCE = "LOW_HEAT_OR_SINGLE_SOURCE"
    NO_STRONG_EVENT_MATCH = "NO_STRONG_EVENT_MATCH"
    AMBIGUOUS_POSSIBLE_MATCH = "AMBIGUOUS_POSSIBLE_MATCH"
    NEEDS_CHECK_FIELDS = "NEEDS_CHECK_FIELDS"
    UNKNOWN_ORIGIN = "UNKNOWN_ORIGIN"
    EXTERNAL_ORIGIN_NOT_IN_BATCH = "EXTERNAL_ORIGIN_NOT_IN_BATCH"


class CandidateHint(Contract):
    schema_version: Literal[1] = 1
    candidate_index_id: Identifier
    candidate_id: Identifier
    event_key: Identifier | None = None
    lineage_role: LineageRole
    lineage_root_ids: tuple[Identifier, ...] = ()
    original_candidate_id: Identifier | None = None
    duplicate_of_candidate_id: Identifier | None = None
    possible_related_candidate_ids: tuple[Identifier, ...] = ()
    low_heat: bool = False
    note: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("lineage root", self.lineage_root_ids),
                ("possible related", self.possible_related_candidate_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate candidate hint {name}")
        if self.lineage_role is LineageRole.ORIGINAL and len(self.lineage_root_ids) != 1:
            raise ValueError("Original candidate needs exactly one lineage root")
        if self.lineage_role is LineageRole.REPOST and not self.lineage_root_ids:
            raise ValueError("Repost candidate needs a recorded lineage root")
        if self.lineage_role is LineageRole.UNKNOWN and self.lineage_root_ids:
            raise ValueError("Unknown origin cannot claim lineage roots")
        for value in (self.original_candidate_id, self.duplicate_of_candidate_id):
            if value == self.candidate_id:
                raise ValueError("Candidate cannot derive from itself")
        return self


class ClusterMember(Contract):
    candidate_index_id: Identifier
    candidate_id: Identifier
    source_id: Identifier
    title: NonBlank | None = None
    original_url: NonBlank | None = None
    published_at: TimePoint
    lineage_role: LineageRole
    lineage_root_ids: tuple[Identifier, ...]


class EventClusterProposal(Contract):
    schema_version: Literal[1] = 1
    cluster_id: Identifier
    event_key: Identifier | None = None
    candidate_ids: tuple[Identifier, ...]
    source_ids: tuple[Identifier, ...]
    members: tuple[ClusterMember, ...]
    merge_basis: tuple[MergeBasis, ...]
    merge_reasons: tuple[NonBlank, ...]
    independent_origin_ids: tuple[Identifier, ...]
    independence_status: IndependenceStatus
    status: ClusterStatus
    differences: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("candidate", self.candidate_ids),
                ("source", self.source_ids),
                ("member", [item.candidate_id for item in self.members]),
                ("merge basis", self.merge_basis),
                ("merge reason", self.merge_reasons),
                ("independent origin", self.independent_origin_ids),
                ("difference", self.differences)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate cluster {name}")
        if not self.candidate_ids or set(self.candidate_ids) != {
                item.candidate_id for item in self.members}:
            raise ValueError("Cluster members do not match candidate IDs")
        if not self.source_ids or set(self.source_ids) != {
                item.source_id for item in self.members}:
            raise ValueError("Cluster source IDs do not match members")
        if not self.merge_basis or not self.merge_reasons:
            raise ValueError("Cluster needs explicit merge basis and reason")
        if (self.independence_status is IndependenceStatus.RECORDED
                and not self.independent_origin_ids):
            raise ValueError("Recorded independence needs at least one origin")
        return self


class ExplorationItem(Contract):
    candidate_id: Identifier
    reasons: tuple[ExplorationReason, ...]
    action: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.reasons or len(self.reasons) != len(set(self.reasons)):
            raise ValueError("Exploration item needs unique reasons")
        return self


class DiscoveryReview(Contract):
    schema_version: Literal[1] = 1
    proposal_id: Identifier
    spec_sha256: Digest
    candidate_index_ids: tuple[Identifier, ...]
    candidate_ids: tuple[Identifier, ...]
    clusters: tuple[EventClusterProposal, ...]
    exploration_queue: tuple[ExplorationItem, ...]
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("candidate index", self.candidate_index_ids),
                ("candidate", self.candidate_ids),
                ("cluster", [item.cluster_id for item in self.clusters])):
            if not values or len(values) != len(set(values)):
                raise ValueError(f"Discovery review {name} list must be nonempty and unique")
        exploration_ids = [item.candidate_id for item in self.exploration_queue]
        if len(exploration_ids) != len(set(exploration_ids)):
            raise ValueError("Duplicate exploration candidate")
        clustered = [
            candidate_id
            for cluster in self.clusters for candidate_id in cluster.candidate_ids]
        if len(clustered) != len(set(clustered)):
            raise ValueError("A candidate appears in more than one cluster")
        if set(clustered) != set(self.candidate_ids):
            raise ValueError("Clusters must preserve every input candidate exactly once")
        if not {item.candidate_id for item in self.exploration_queue} <= set(self.candidate_ids):
            raise ValueError("Exploration queue contains a foreign candidate")
        return self


class DiscoveryError(ArchiveError):
    """A discovery proposal failure, never editorial selection or adoption."""


def _id(*values: str) -> str:
    return "ID-" + hashlib.sha256(canonical(list(values)).encode()).hexdigest()[:32]


class _UnionFind:
    def __init__(self, values):
        self.parent = {value: value for value in values}

    def find(self, value):
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            next_value = self.parent[value]
            self.parent[value] = root
            value = next_value
        return root

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


class EventClusterer:
    def build(self, indexes: tuple[CandidateIndex, ...],
              hints: tuple[CandidateHint, ...], *, proposal_id: str,
              spec_sha256: str, created_at: datetime) -> DiscoveryReview:
        if not indexes:
            raise DiscoveryError("Event clustering needs at least one candidate index")
        indexes = tuple(CandidateIndex.model_validate_json(
            item.model_dump_json(warnings=False)) for item in indexes)
        hints = tuple(CandidateHint.model_validate_json(
            item.model_dump_json(warnings=False)) for item in hints)
        index_ids = tuple(item.index_id for item in indexes)
        if len(index_ids) != len(set(index_ids)):
            raise DiscoveryError("Candidate indexes must be unique")
        if any(item.spec_sha256 != spec_sha256 for item in indexes):
            raise DiscoveryError("Candidate index and discovery specification differ")
        by_index = {item.index_id: item for item in indexes}
        candidate_index = {}
        for index in indexes:
            for candidate in index.candidates:
                if candidate.candidate_id in candidate_index:
                    raise DiscoveryError("Candidate ID appears more than once")
                candidate_index[candidate.candidate_id] = (index, candidate)
        hint_by_candidate = {}
        for hint in hints:
            if hint.candidate_id not in candidate_index:
                raise DiscoveryError("Hint references a foreign candidate")
            if candidate_index[hint.candidate_id][0].index_id != hint.candidate_index_id:
                raise DiscoveryError("Hint candidate index does not match")
            if hint.candidate_id in hint_by_candidate:
                raise DiscoveryError("Duplicate hint for candidate")
            hint_by_candidate[hint.candidate_id] = hint
        for hint in hints:
            for related in hint.possible_related_candidate_ids:
                if related not in candidate_index:
                    raise DiscoveryError("Hint references a foreign possible match")
            for related in (hint.original_candidate_id, hint.duplicate_of_candidate_id):
                if related is not None and related not in candidate_index:
                    # External original IDs are represented through lineage_root_ids.
                    pass

        uf = _UnionFind(candidate_index)
        edges: set[tuple[str, str, MergeBasis]] = set()

        def union(left, right, basis):
            if left == right or left not in candidate_index or right not in candidate_index:
                return
            uf.union(left, right)
            edges.add((*sorted((left, right)), basis))

        event_groups, root_groups, url_groups = {}, {}, {}
        for candidate_id, (index, candidate) in candidate_index.items():
            hint = hint_by_candidate.get(candidate_id)
            if hint and hint.event_key:
                event_groups.setdefault(hint.event_key, []).append(candidate_id)
            if hint:
                for root in hint.lineage_root_ids:
                    root_groups.setdefault(root, []).append(candidate_id)
                if hint.original_candidate_id in candidate_index:
                    union(candidate_id, hint.original_candidate_id, MergeBasis.CANONICAL_ORIGIN)
                if hint.duplicate_of_candidate_id in candidate_index:
                    union(candidate_id, hint.duplicate_of_candidate_id, MergeBasis.CANONICAL_ORIGIN)
            if candidate.original_url:
                url_groups.setdefault(candidate.original_url, []).append(candidate_id)
        for group in event_groups.values():
            for candidate_id in group[1:]:
                union(group[0], candidate_id, MergeBasis.EXPLICIT_EVENT_KEY)
        for group in root_groups.values():
            for candidate_id in group[1:]:
                union(group[0], candidate_id, MergeBasis.SHARED_LINEAGE_ROOT)
        for group in url_groups.values():
            for candidate_id in group[1:]:
                union(group[0], candidate_id, MergeBasis.EXACT_URL)

        grouped = {}
        for candidate_id in candidate_index:
            grouped.setdefault(uf.find(candidate_id), []).append(candidate_id)
        clusters = []
        for grouped_ids in grouped.values():
            candidate_ids = tuple(sorted(grouped_ids))
            member_hints = [hint_by_candidate.get(item) for item in candidate_ids]
            roots = tuple(sorted({
                root for hint in member_hints if hint for root in hint.lineage_root_ids}))
            covered = sum(bool(hint and hint.lineage_root_ids) for hint in member_hints)
            independence = (
                IndependenceStatus.RECORDED if covered == len(candidate_ids)
                else IndependenceStatus.PARTIAL if covered
                else IndependenceStatus.UNKNOWN)
            bases = tuple(sorted({
                basis for left, right, basis in edges
                if left in candidate_ids and right in candidate_ids}, key=lambda x: x.value))
            if not bases:
                bases = (MergeBasis.SINGLE_CANDIDATE,)
            event_keys = sorted({
                hint.event_key for hint in member_hints if hint and hint.event_key})
            ambiguous = any(
                hint and any(related not in candidate_ids
                             for related in hint.possible_related_candidate_ids)
                for hint in member_hints) or len(event_keys) > 1
            members = []
            differences = []
            for candidate_id in candidate_ids:
                index, candidate = candidate_index[candidate_id]
                hint = hint_by_candidate.get(candidate_id)
                members.append(ClusterMember(
                    candidate_index_id=index.index_id, candidate_id=candidate_id,
                    source_id=candidate.source_id, title=candidate.title,
                    original_url=candidate.original_url,
                    published_at=candidate.published_at,
                    lineage_role=hint.lineage_role if hint else LineageRole.UNKNOWN,
                    lineage_root_ids=hint.lineage_root_ids if hint else ()))
                differences.append(
                    f"{candidate_id}: source={candidate.source_id}; title={candidate.title!r}; "
                    f"url={candidate.original_url!r}; published={candidate.published_at.value!r}")
            reasons = [basis.value.lower().replace("_", " ") for basis in bases]
            clusters.append(EventClusterProposal(
                cluster_id=_id("cluster", *candidate_ids),
                event_key=event_keys[0] if len(event_keys) == 1 else None,
                candidate_ids=candidate_ids,
                source_ids=tuple(sorted({member.source_id for member in members})),
                members=tuple(members), merge_basis=bases,
                merge_reasons=tuple(reasons), independent_origin_ids=roots,
                independence_status=independence,
                status=ClusterStatus.NEEDS_EDITOR if ambiguous else ClusterStatus.PROPOSED,
                differences=tuple(differences)))

        cluster_for = {
            candidate_id: cluster for cluster in clusters
            for candidate_id in cluster.candidate_ids}
        exploration = []
        for candidate_id, (index, candidate) in candidate_index.items():
            hint = hint_by_candidate.get(candidate_id)
            cluster = cluster_for[candidate_id]
            reasons = set()
            if hint and hint.low_heat:
                reasons.add(ExplorationReason.LOW_HEAT_OR_SINGLE_SOURCE)
            if candidate.status is CandidateStatus.NEEDS_CHECK:
                reasons.add(ExplorationReason.NEEDS_CHECK_FIELDS)
            if not hint or hint.lineage_role is LineageRole.UNKNOWN:
                reasons.add(ExplorationReason.UNKNOWN_ORIGIN)
            if len(cluster.candidate_ids) == 1:
                reasons.add(ExplorationReason.NO_STRONG_EVENT_MATCH)
            if hint and any(
                    related not in cluster.candidate_ids
                    for related in hint.possible_related_candidate_ids):
                reasons.add(ExplorationReason.AMBIGUOUS_POSSIBLE_MATCH)
            if (hint and hint.original_candidate_id is not None
                    and hint.original_candidate_id not in candidate_index):
                reasons.add(ExplorationReason.EXTERNAL_ORIGIN_NOT_IN_BATCH)
            if reasons:
                exploration.append(ExplorationItem(
                    candidate_id=candidate_id,
                    reasons=tuple(sorted(reasons, key=lambda item: item.value)),
                    action="Editor to verify event identity, original source and missing fields before merge/selection"))
        return DiscoveryReview(
            proposal_id=proposal_id, spec_sha256=spec_sha256,
            candidate_index_ids=tuple(sorted(index_ids)),
            candidate_ids=tuple(sorted(candidate_index)),
            clusters=tuple(sorted(clusters, key=lambda item: item.cluster_id)),
            exploration_queue=tuple(sorted(exploration, key=lambda item: item.candidate_id)),
            created_at=created_at)


class EventClusterController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("EventClusterController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("EventClusterController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _version(proposal_id: str) -> str:
        return "DISCOVERY-" + hashlib.sha256(
            canonical(["event-cluster", proposal_id]).encode()).hexdigest()[:32]

    def append_proposal(self, proposal: DiscoveryReview) -> StoredVersion:
        if not isinstance(proposal, DiscoveryReview):
            raise TypeError("append_proposal requires DiscoveryReview")
        proposal = DiscoveryReview.model_validate_json(
            proposal.model_dump_json(warnings=False))
        version_id = self._version(proposal.proposal_id)
        submission = VersionSubmission(
            schema_version=2,
            object_id="DISCOVERY-" + hashlib.sha256(
                canonical([proposal.proposal_id]).encode()).hexdigest()[:32],
            kind=ObjectKind.EVENT_CLUSTER_PROPOSAL, version_id=version_id,
            title="event cluster and exploration proposal",
            spec_sha256=proposal.spec_sha256, created_at=proposal.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY)
        return self.archive.append(
            submission, canonical(proposal.model_dump(mode="json")).encode())

    def load_proposal(self, proposal_id: str) -> DiscoveryReview:
        version_id = self._version(proposal_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.EVENT_CLUSTER_PROPOSAL:
            raise DiscoveryError("Requested version is not an event-cluster proposal")
        proposal = DiscoveryReview.model_validate_json(
            self.archive.read_body(version_id))
        if proposal.proposal_id != proposal_id:
            raise DiscoveryError("Discovery proposal identity mismatch")
        return proposal
