"""W23 topic selection, S8 research admission and tentative edition placement."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
                        Representation, RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)
from .coverage import CoverageAudit, CoverageController
from .discovery import DiscoveryReview, EventClusterController
from .sources import CandidateIndex, SourceAdapterController


class DecisionStage(str, Enum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    S5 = "S5"
    S6 = "S6"
    S7 = "S7"
    S8 = "S8"


class PublicationBasis(str, Enum):
    CURRENT_WEEK = "CURRENT_WEEK"
    LONG_TERM_FEATURE = "LONG_TERM_FEATURE"


class ArticleType(str, Enum):
    DEEP_THEME = "DEEP_THEME"
    SOURCE_SELECTION = "SOURCE_SELECTION"
    UPDATE_CORRECTION = "UPDATE_CORRECTION"


class TopicDecisionCode(str, Enum):
    COVER = "COVER"
    REVISE = "REVISE"
    WATCH = "WATCH"
    DROP = "DROP"


class ValueBasis(str, Enum):
    DIRECT_IMPACT = "DIRECT_IMPACT"
    REPRESENTATIVE = "REPRESENTATIVE"
    BREAKTHROUGH = "BREAKTHROUGH"
    RESEARCH_VALUE = "RESEARCH_VALUE"


class S8PrerequisitePackage(Contract):
    schema_version: Literal[1] = 1
    package_id: Identifier
    topic_id: Identifier
    edition_id: Identifier
    spec_sha256: Digest
    discovery_proposal_id: Identifier
    question_version_id: Identifier
    source_material_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    rights_record_version_ids: tuple[Identifier, ...]
    reading_plan_version_id: Identifier
    limitations: tuple[NonBlank, ...] = ()
    candidate_index_ids: tuple[Identifier, ...]
    coverage_audit_ids: tuple[Identifier, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("source material", self.source_material_version_ids),
                ("evidence", self.evidence_version_ids),
                ("rights record", self.rights_record_version_ids),
                ("candidate index", self.candidate_index_ids),
                ("coverage audit", self.coverage_audit_ids),
                ("limitation", self.limitations)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate S8 package {name}")
        if (not self.source_material_version_ids or not self.evidence_version_ids
                or not self.rights_record_version_ids or not self.candidate_index_ids):
            raise ValueError("S8 package needs source, evidence, rights and candidate-index versions")
        return self


class TopicDecision(Contract):
    schema_version: Literal[1] = 1
    decision_id: Identifier
    topic_id: Identifier
    theme_id: Identifier
    edition_id: Identifier
    spec_sha256: Digest
    discovery_proposal_id: Identifier
    question_version_id: Identifier
    candidate_index_ids: tuple[Identifier, ...]
    candidate_ids: tuple[Identifier, ...] = ()
    cluster_ids: tuple[Identifier, ...] = ()
    stage: DecisionStage
    publication_basis: PublicationBasis
    article_type: ArticleType | None = None
    value_bases: tuple[ValueBasis, ...]
    decision: TopicDecisionCode
    reasons: tuple[NonBlank, ...]
    gaps: tuple[NonBlank, ...] = ()
    next_action: NonBlank | None = None
    trial_score: Decimal | None = Field(default=None, ge=0, le=100)
    trial_score_basis: NonBlank | None = None
    research_investment_note: NonBlank | None = None
    s8_package_id: Identifier | None = None
    previous_decision_id: Identifier | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("candidate index", self.candidate_index_ids),
                ("candidate", self.candidate_ids),
                ("cluster", self.cluster_ids),
                ("value basis", self.value_bases),
                ("reason", self.reasons),
                ("gap", self.gaps)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate topic decision {name}")
        if not self.candidate_index_ids or not self.reasons:
            raise ValueError("Topic decision needs candidate indexes and reasons")
        if not self.candidate_ids and not self.cluster_ids:
            raise ValueError("Topic decision needs a candidate or event cluster")
        if self.trial_score is not None and not self.trial_score_basis:
            raise ValueError("A trial score needs an explicit basis")
        if self.trial_score is None and self.trial_score_basis is not None:
            raise ValueError("A score basis cannot exist without a trial score")
        if self.decision is TopicDecisionCode.COVER:
            if self.stage is not DecisionStage.S8:
                raise ValueError("COVER is only an S8 decision")
            if not self.s8_package_id or not self.value_bases or self.article_type is None:
                raise ValueError("COVER needs S8 package, value basis and article type")
            if (self.publication_basis is PublicationBasis.LONG_TERM_FEATURE
                    and self.article_type is not ArticleType.DEEP_THEME):
                raise ValueError("Long-term research COVER must remain DEEP_THEME")
            if (self.article_type is ArticleType.UPDATE_CORRECTION
                    and self.publication_basis is not PublicationBasis.CURRENT_WEEK):
                raise ValueError("UPDATE_CORRECTION must use CURRENT_WEEK")
        if self.s8_package_id is not None and self.stage is not DecisionStage.S8:
            raise ValueError("Only an S8 decision may reference an S8 prerequisite package")
        if self.decision in (TopicDecisionCode.REVISE, TopicDecisionCode.WATCH) and not self.next_action:
            raise ValueError("REVISE/WATCH needs a concrete next action")
        return self


class ResearchAdmission(Contract):
    schema_version: Literal[1] = 1
    research_admission_id: Identifier
    topic_decision_id: Identifier
    topic_id: Identifier
    theme_id: Identifier
    edition_id: Identifier
    spec_sha256: Digest
    allowed_article_types: tuple[ArticleType, ...]
    scope: NonBlank
    restrictions: tuple[NonBlank, ...] = ()
    research_allowed: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.allowed_article_types
                or len(self.allowed_article_types) != len(set(self.allowed_article_types))):
            raise ValueError("Research admission needs unique article types")
        if len(self.restrictions) != len(set(self.restrictions)):
            raise ValueError("Duplicate research-admission restriction")
        return self


class EditionPlacement(Contract):
    placement_id: Identifier
    topic_decision_id: Identifier
    research_admission_id: Identifier
    topic_id: Identifier
    article_type: ArticleType
    publication_basis: PublicationBasis
    slot_order: int = Field(ge=1)
    editorial_role: NonBlank
    reason: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (self.publication_basis is PublicationBasis.LONG_TERM_FEATURE
                and self.article_type is not ArticleType.DEEP_THEME):
            raise ValueError("A long-term edition placement must remain DEEP_THEME")
        return self


class EditionPlacementProposal(Contract):
    schema_version: Literal[1] = 1
    edition_proposal_id: Identifier
    edition_id: Identifier
    spec_sha256: Digest
    placements: tuple[EditionPlacement, ...]
    combination_reason: NonBlank
    publication_authorized: Literal[False] = False
    content_review_required: Literal[True] = True
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.placements:
            raise ValueError("Edition proposal needs at least one explicit placement")
        for name, values in (
                ("placement", [item.placement_id for item in self.placements]),
                ("topic", [item.topic_id for item in self.placements]),
                ("slot", [item.slot_order for item in self.placements])):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate edition {name}")
        return self


class EditorialError(ArchiveError):
    """An editorial record failure, never content PASS or publication approval."""


class EditorialController:
    _STAGE_ORDER = {stage: index for index, stage in enumerate(DecisionStage)}
    _PACKAGE_KINDS = {
        "question": frozenset({ObjectKind.QUESTION_VERSION}),
        "source material": frozenset({ObjectKind.SOURCE_MATERIAL, ObjectKind.DOCUMENT}),
        "evidence": frozenset({ObjectKind.EVIDENCE}),
        "rights record": frozenset({ObjectKind.RIGHTS_RECORD}),
        "reading plan": frozenset({ObjectKind.READING_SCOPE_PLAN}),
    }

    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("EditorialController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("EditorialController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _object(prefix: str, identity: str) -> str:
        return prefix + hashlib.sha256(canonical([identity]).encode()).hexdigest()[:32]

    @staticmethod
    def _version(prefix: str, identity: str) -> str:
        return prefix + hashlib.sha256(canonical([prefix, identity]).encode()).hexdigest()[:32]

    def _expect_kind(self, version_id: str, allowed: frozenset[ObjectKind],
                     label: str) -> StoredVersion:
        stored = self.archive.get(version_id)
        if stored.submission.kind not in allowed:
            kinds = ", ".join(sorted(item.value for item in allowed))
            raise EditorialError(
                f"{label} {version_id} is {stored.submission.kind.value}, not {kinds}")
        return stored

    def _ensure_current(self, stored: StoredVersion, label: str) -> None:
        latest = self.archive.latest(stored.submission.object_id)
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise EditorialError(f"{label} is not the current version; repeat S8 review")

    @staticmethod
    def _expected(records: tuple[StoredVersion, ...]) -> dict[str, str | None]:
        expected: dict[str, str | None] = {}
        for stored in records:
            object_id = stored.submission.object_id
            version_id = stored.submission.version_id
            if object_id in expected and expected[object_id] != version_id:
                raise EditorialError("One record binds two versions of the same object")
            expected[object_id] = version_id
        return expected

    @staticmethod
    def _unique(records: tuple[StoredVersion, ...]) -> tuple[StoredVersion, ...]:
        by_version = {}
        for stored in records:
            by_version[stored.submission.version_id] = stored
        return tuple(by_version.values())

    def _proposal(self, proposal_id: str) -> DiscoveryReview:
        return EventClusterController(self.archive, self.rights).load_proposal(proposal_id)

    def _indexes(self, index_ids: tuple[str, ...]) -> tuple[CandidateIndex, ...]:
        controller = SourceAdapterController(self.archive, self.rights)
        return tuple(controller.load_index(index_id) for index_id in index_ids)

    def _validate_coverage(
            self, package: S8PrerequisitePackage, proposal: DiscoveryReview,
            indexes: tuple[CandidateIndex, ...]) -> tuple[StoredVersion, ...]:
        controller = CoverageController(self.archive, self.rights)
        records = []
        for audit_id in package.coverage_audit_ids:
            audit = controller.load_audit(audit_id)
            audit_stored = self._expect_kind(
                controller._version("COVERAGE-AUDIT-", audit_id),
                frozenset({ObjectKind.COVERAGE_AUDIT}), "coverage audit")
            if (audit.audit_id != audit_id
                    or audit.spec_sha256 != package.spec_sha256
                    or audit.proposal_id != proposal.proposal_id
                    or set(audit.candidate_index_ids) != set(package.candidate_index_ids)):
                raise EditorialError(
                    "Coverage audit does not bind this package and discovery proposal")
            if audit.created_at > package.created_at:
                raise EditorialError("S8 package predates its coverage audit")
            plan = controller.load_plan(audit.plan_id)
            plan_stored = self._expect_kind(
                controller._version("COVERAGE-PLAN-", audit.plan_id),
                frozenset({ObjectKind.COVERAGE_REFERENCE_PLAN}), "coverage reference plan")
            if (plan.plan_id != audit.plan_id
                    or plan.spec_sha256 != package.spec_sha256
                    or plan.created_at > audit.created_at):
                raise EditorialError("Coverage audit has an invalid reference-plan basis")
            if (plan.fixed_at > proposal.created_at
                    or any(plan.fixed_at > index.created_at for index in indexes)):
                raise EditorialError(
                    "Coverage reference plan was not fixed before candidates and clustering")
            for stored in (audit_stored, plan_stored):
                self._ensure_current(stored, stored.submission.kind.value)
                records.append(stored)
        return self._unique(tuple(records))

    def _package_dependencies(
            self, package: S8PrerequisitePackage
    ) -> tuple[DiscoveryReview, tuple[StoredVersion, ...]]:
        records = [
            self._expect_kind(package.question_version_id,
                              self._PACKAGE_KINDS["question"], "question version"),
            self._expect_kind(package.reading_plan_version_id,
                              self._PACKAGE_KINDS["reading plan"], "reading plan"),
        ]
        for version_id in package.source_material_version_ids:
            records.append(self._expect_kind(
                version_id, self._PACKAGE_KINDS["source material"], "source material"))
        for version_id in package.evidence_version_ids:
            records.append(self._expect_kind(
                version_id, self._PACKAGE_KINDS["evidence"], "evidence version"))
        for version_id in package.rights_record_version_ids:
            records.append(self._expect_kind(
                version_id, self._PACKAGE_KINDS["rights record"], "rights record"))
        proposal = self._proposal(package.discovery_proposal_id)
        proposal_stored = self._expect_kind(
            EventClusterController._version(package.discovery_proposal_id),
            frozenset({ObjectKind.EVENT_CLUSTER_PROPOSAL}), "discovery proposal")
        if (proposal.spec_sha256 != package.spec_sha256
                or set(proposal.candidate_index_ids) != set(package.candidate_index_ids)):
            raise EditorialError("S8 package does not bind its declared discovery proposal")
        records.append(proposal_stored)
        index_controller = SourceAdapterController(self.archive, self.rights)
        indexes = []
        for index_id in package.candidate_index_ids:
            index = index_controller.load_index(index_id)
            indexes.append(index)
            stored = self._expect_kind(
                index_controller._version(index_id),
                frozenset({ObjectKind.CANDIDATE_INDEX}), "candidate index")
            if index.spec_sha256 != package.spec_sha256:
                raise EditorialError("Candidate index and S8 package specifications differ")
            records.append(stored)
        records.extend(self._validate_coverage(package, proposal, tuple(indexes)))
        records = self._unique(tuple(records))
        for record in records:
            if record.submission.spec_sha256 != package.spec_sha256:
                raise EditorialError("S8 prerequisite belongs to a different specification")
            if record.submission.created_at > package.created_at:
                raise EditorialError(
                    f"{record.submission.kind.value} was created after the S8 package")
            self._ensure_current(record, record.submission.kind.value)
        return proposal, records

    def append_package(self, package: S8PrerequisitePackage) -> StoredVersion:
        if not isinstance(package, S8PrerequisitePackage):
            raise TypeError("append_package requires S8PrerequisitePackage")
        package = S8PrerequisitePackage.model_validate_json(
            package.model_dump_json(warnings=False))
        _, dependencies = self._package_dependencies(package)
        references = []
        for record in dependencies:
            kind = record.submission.kind
            use = (ReferenceUse.SOURCE if kind in self._PACKAGE_KINDS["source material"]
                   else ReferenceUse.SUPPORT if kind is ObjectKind.EVIDENCE
                   else ReferenceUse.LINEAGE if kind in {
                       ObjectKind.CANDIDATE_INDEX, ObjectKind.EVENT_CLUSTER_PROPOSAL}
                   else ReferenceUse.BASIS)
            references.append(VersionReference(
                target_version_id=record.submission.version_id, use=use,
                locator=f"S8 prerequisite {kind.value}"))
        version_id = self._version("S8-PACKAGE-", package.package_id)
        object_id = self._object("S8-PACKAGE-", package.package_id)
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            kind=ObjectKind.S8_PREREQUISITE_PACKAGE, version_id=version_id,
            title=f"S8 prerequisite package {package.topic_id}",
            spec_sha256=package.spec_sha256, created_at=package.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        expected = self._expected(dependencies)
        expected[object_id] = None
        return self.archive.append(
            submission, canonical(package.model_dump(mode="json")).encode(),
            expected_current=expected)

    def load_package(self, package_id: str) -> S8PrerequisitePackage:
        version_id = self._version("S8-PACKAGE-", package_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.S8_PREREQUISITE_PACKAGE:
            raise EditorialError("Requested version is not an S8 prerequisite package")
        package = S8PrerequisitePackage.model_validate_json(self.archive.read_body(version_id))
        if (package.package_id != package_id
                or stored.submission.object_id != self._object(
                    "S8-PACKAGE-", package.package_id)
                or stored.submission.spec_sha256 != package.spec_sha256
                or stored.submission.created_at != package.created_at):
            raise EditorialError("S8 package identity mismatch")
        return package

    def _validate_decision_context(
            self, decision: TopicDecision, package: S8PrerequisitePackage | None
    ) -> tuple[StoredVersion, ...]:
        proposal = self._proposal(decision.discovery_proposal_id)
        proposal_stored = self._expect_kind(
            EventClusterController._version(decision.discovery_proposal_id),
            frozenset({ObjectKind.EVENT_CLUSTER_PROPOSAL}), "discovery proposal")
        if (proposal.spec_sha256 != decision.spec_sha256
                or set(proposal.candidate_index_ids) != set(decision.candidate_index_ids)
                or proposal.created_at > decision.created_at):
            raise EditorialError("TopicDecision does not bind this discovery proposal")
        question_stored = self._expect_kind(
            decision.question_version_id,
            self._PACKAGE_KINDS["question"], "question version")
        records = [proposal_stored, question_stored]
        indexes = self._indexes(decision.candidate_index_ids)
        index_controller = SourceAdapterController(self.archive, self.rights)
        for index in indexes:
            stored = self.archive.get(index_controller._version(index.index_id))
            if index.spec_sha256 != decision.spec_sha256 or index.created_at > decision.created_at:
                raise EditorialError("Candidate index does not bind this TopicDecision")
            records.append(stored)
        candidates = {
            candidate.candidate_id for index in indexes for candidate in index.candidates}
        cluster_by_id = {cluster.cluster_id: cluster for cluster in proposal.clusters}
        if not set(decision.candidate_ids) <= candidates:
            raise EditorialError("TopicDecision contains a candidate outside its indexes")
        if not set(decision.cluster_ids) <= set(cluster_by_id):
            raise EditorialError(
                "TopicDecision contains a cluster outside its discovery proposal")
        selected_cluster_candidates = {
            candidate_id for cluster_id in decision.cluster_ids
            for candidate_id in cluster_by_id[cluster_id].candidate_ids}
        if (not set(decision.candidate_ids) <= selected_cluster_candidates
                and decision.cluster_ids):
            raise EditorialError("TopicDecision candidates are not covered by its clusters")
        if package is None:
            records = self._unique(tuple(records))
        else:
            _, package_records = self._package_dependencies(package)
            if (package.topic_id != decision.topic_id
                    or package.edition_id != decision.edition_id
                    or package.spec_sha256 != decision.spec_sha256
                    or package.discovery_proposal_id != decision.discovery_proposal_id
                    or package.question_version_id != decision.question_version_id
                    or set(package.candidate_index_ids) != set(decision.candidate_index_ids)
                    or package.created_at > decision.created_at):
                raise EditorialError(
                    "S8 package does not bind this decision's topic, edition, question or candidates")
            package_stored = self.archive.get(
                self._version("S8-PACKAGE-", package.package_id))
            records.extend((*package_records, package_stored))
            records = self._unique(tuple(records))
        for record in records:
            self._ensure_current(record, record.submission.kind.value)
        return records

    def append_decision(self, decision: TopicDecision) -> StoredVersion:
        if not isinstance(decision, TopicDecision):
            raise TypeError("append_decision requires TopicDecision")
        decision = TopicDecision.model_validate_json(
            decision.model_dump_json(warnings=False))
        object_id = self._object("TOPIC-DECISION-", decision.topic_id)
        latest = self.archive.latest(object_id)
        if decision.previous_decision_id is None:
            if latest is not None:
                raise EditorialError("Topic already has a decision history; bind previous decision")
        else:
            expected_previous = self._version(
                "TOPIC-DECISION-", decision.previous_decision_id)
            if latest is None or latest.submission.version_id != expected_previous:
                raise EditorialError("Previous topic decision is not the current decision")
            previous = self.load_decision(decision.previous_decision_id)
            if (previous.topic_id != decision.topic_id
                    or previous.theme_id != decision.theme_id):
                raise EditorialError("Topic decision history crosses topic or theme IDs")
            if self._STAGE_ORDER[decision.stage] < self._STAGE_ORDER[previous.stage]:
                raise EditorialError("Topic decision cannot move back to an earlier S stage")
            if decision.created_at < previous.created_at:
                raise EditorialError("Topic decision history has inverted timestamps")
        package = None
        if decision.s8_package_id:
            package = self.load_package(decision.s8_package_id)
        context_records = self._validate_decision_context(decision, package)
        if decision.decision is TopicDecisionCode.COVER and package is None:
            raise EditorialError("COVER cannot be recorded without the S8 prerequisite package")
        references = [
            VersionReference(
                target_version_id=record.submission.version_id,
                use=(ReferenceUse.LINEAGE if record.submission.kind in {
                    ObjectKind.CANDIDATE_INDEX, ObjectKind.EVENT_CLUSTER_PROPOSAL}
                     else ReferenceUse.BASIS),
                locator=f"TopicDecision {record.submission.kind.value} basis")
            for record in context_records
        ]
        version_id = self._version("TOPIC-DECISION-", decision.decision_id)
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            kind=ObjectKind.TOPIC_DECISION, version_id=version_id,
            parent_version_id=latest.submission.version_id if latest else None,
            title=f"topic decision {decision.topic_id} {decision.decision.value}",
            spec_sha256=decision.spec_sha256, created_at=decision.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        expected = self._expected(context_records)
        expected[object_id] = latest.submission.version_id if latest else None
        return self.archive.append(
            submission, canonical(decision.model_dump(mode="json")).encode(),
            expected_current=expected)

    def _load_decision_version(self, version_id: str) -> TopicDecision:
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.TOPIC_DECISION:
            raise EditorialError("Requested version is not a TopicDecision")
        decision = TopicDecision.model_validate_json(self.archive.read_body(version_id))
        if (self._version("TOPIC-DECISION-", decision.decision_id) != version_id
                or stored.submission.object_id != self._object(
                    "TOPIC-DECISION-", decision.topic_id)
                or stored.submission.spec_sha256 != decision.spec_sha256
                or stored.submission.created_at != decision.created_at):
            raise EditorialError("Topic decision identity mismatch")
        return decision

    def load_decision(self, decision_id: str) -> TopicDecision:
        return self._load_decision_version(
            self._version("TOPIC-DECISION-", decision_id))

    def current_decision(self, topic_id: str) -> TopicDecision | None:
        stored = self.archive.latest(self._object("TOPIC-DECISION-", topic_id))
        return None if stored is None else self._load_decision_version(
            stored.submission.version_id)

    def _current_decision_context(
            self, decision_id: str) -> tuple[TopicDecision, tuple[StoredVersion, ...]]:
        decision = self.load_decision(decision_id)
        current = self.current_decision(decision.topic_id)
        if current is None or current.decision_id != decision_id:
            raise EditorialError("TopicDecision is stale")
        package = None
        if decision.s8_package_id:
            package = self.load_package(decision.s8_package_id)
        records = self._validate_decision_context(decision, package)
        decision_stored = self.archive.get(self._version("TOPIC-DECISION-", decision_id))
        return decision, self._unique((decision_stored, *records))

    def append_research_admission(self, admission: ResearchAdmission) -> StoredVersion:
        if not isinstance(admission, ResearchAdmission):
            raise TypeError("append_research_admission requires ResearchAdmission")
        admission = ResearchAdmission.model_validate_json(
            admission.model_dump_json(warnings=False))
        decision, context = self._current_decision_context(admission.topic_decision_id)
        if decision.decision is not TopicDecisionCode.COVER:
            raise EditorialError("Research admission needs an S8 TopicDecision COVER")
        if (decision.topic_id != admission.topic_id
                or decision.theme_id != admission.theme_id
                or decision.edition_id != admission.edition_id
                or decision.spec_sha256 != admission.spec_sha256):
            raise EditorialError("Research admission does not match TopicDecision identity")
        if (decision.article_type is None
                or set(admission.allowed_article_types) != {decision.article_type}):
            raise EditorialError("Research admission must preserve the exact COVER article type")
        if admission.created_at < decision.created_at:
            raise EditorialError("Research admission predates its TopicDecision")
        version_id = self._version("RESEARCH-ADMISSION-", admission.research_admission_id)
        object_id = self._object("RESEARCH-ADMISSION-", admission.research_admission_id)
        references = [VersionReference(
            target_version_id=self._version("TOPIC-DECISION-", decision.decision_id),
            use=ReferenceUse.BASIS,
            locator="research admission TopicDecision")]
        if decision.s8_package_id:
            references.append(VersionReference(
                target_version_id=self._version("S8-PACKAGE-", decision.s8_package_id),
                use=ReferenceUse.BASIS, locator="research admission S8 package"))
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            kind=ObjectKind.RESEARCH_ADMISSION, version_id=version_id,
            title=f"research admission {admission.topic_id}",
            spec_sha256=admission.spec_sha256, created_at=admission.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        expected = self._expected(context)
        expected[object_id] = None
        return self.archive.append(
            submission, canonical(admission.model_dump(mode="json")).encode(),
            expected_current=expected)

    def load_research_admission(self, admission_id: str) -> ResearchAdmission:
        version_id = self._version("RESEARCH-ADMISSION-", admission_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.RESEARCH_ADMISSION:
            raise EditorialError("Requested version is not a ResearchAdmission")
        admission = ResearchAdmission.model_validate_json(self.archive.read_body(version_id))
        if (admission.research_admission_id != admission_id
                or stored.submission.object_id != self._object(
                    "RESEARCH-ADMISSION-", admission.research_admission_id)
                or stored.submission.spec_sha256 != admission.spec_sha256
                or stored.submission.created_at != admission.created_at):
            raise EditorialError("Research admission identity mismatch")
        return admission

    def append_edition_proposal(self, proposal: EditionPlacementProposal) -> StoredVersion:
        if not isinstance(proposal, EditionPlacementProposal):
            raise TypeError("append_edition_proposal requires EditionPlacementProposal")
        proposal = EditionPlacementProposal.model_validate_json(
            proposal.model_dump_json(warnings=False))
        context_records = []
        for placement in proposal.placements:
            decision, records = self._current_decision_context(placement.topic_decision_id)
            context_records.extend(records)
            admission = self.load_research_admission(placement.research_admission_id)
            admission_stored = self.archive.get(
                self._version("RESEARCH-ADMISSION-", admission.research_admission_id))
            self._ensure_current(admission_stored, "research admission")
            context_records.append(admission_stored)
            if (decision.decision is not TopicDecisionCode.COVER
                    or decision.edition_id != proposal.edition_id
                    or decision.spec_sha256 != proposal.spec_sha256
                    or decision.topic_id != placement.topic_id
                    or decision.publication_basis is not placement.publication_basis
                    or decision.article_type is not placement.article_type):
                raise EditorialError("Edition placement differs from its COVER decision")
            if (admission.topic_decision_id != decision.decision_id
                    or admission.topic_id != decision.topic_id
                    or admission.theme_id != decision.theme_id
                    or admission.edition_id != proposal.edition_id
                    or admission.spec_sha256 != proposal.spec_sha256
                    or set(admission.allowed_article_types) != {placement.article_type}):
                raise EditorialError("Edition placement lacks matching research admission")
            if (admission.created_at < decision.created_at
                    or proposal.created_at < admission.created_at):
                raise EditorialError("Edition placement has inverted decision/admission time")
        context_records = list(self._unique(tuple(context_records)))
        version_id = self._version("EDITION-PROPOSAL-", proposal.edition_proposal_id)
        object_id = self._object("EDITION-PROPOSAL-", proposal.edition_proposal_id)
        referenced = [
            target for placement in proposal.placements
            for target in (
                self._version("TOPIC-DECISION-", placement.topic_decision_id),
                self._version("RESEARCH-ADMISSION-", placement.research_admission_id))]
        submission = VersionSubmission(
            schema_version=2, object_id=object_id,
            kind=ObjectKind.EDITION_PLACEMENT_PROPOSAL, version_id=version_id,
            title=f"tentative edition placement {proposal.edition_id}",
            spec_sha256=proposal.spec_sha256, created_at=proposal.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(VersionReference(
                target_version_id=target, use=ReferenceUse.BASIS,
                locator="tentative edition placement basis") for target in referenced))
        expected = self._expected(tuple(context_records))
        expected[object_id] = None
        return self.archive.append(
            submission, canonical(proposal.model_dump(mode="json")).encode(),
            expected_current=expected)

    def load_edition_proposal(self, proposal_id: str) -> EditionPlacementProposal:
        version_id = self._version("EDITION-PROPOSAL-", proposal_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.EDITION_PLACEMENT_PROPOSAL:
            raise EditorialError("Requested version is not an EditionPlacementProposal")
        proposal = EditionPlacementProposal.model_validate_json(
            self.archive.read_body(version_id))
        if (proposal.edition_proposal_id != proposal_id
                or stored.submission.object_id != self._object(
                    "EDITION-PROPOSAL-", proposal.edition_proposal_id)
                or stored.submission.spec_sha256 != proposal.spec_sha256
                or stored.submission.created_at != proposal.created_at):
            raise EditorialError("Edition placement identity mismatch")
        return proposal
