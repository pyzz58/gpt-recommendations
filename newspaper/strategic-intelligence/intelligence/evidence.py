"""W25 claim-evidence ranges, actual decimal calculations and gap follow-up."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import hashlib
import re
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, MissingVersion, canonical
from .contracts import (Contract, DataPeriod, Digest, Identifier, MaterialUse, NonBlank,
                        ObjectKind, ReferenceUse, Representation, RightsGrant,
                        SourceTimes, StoredVersion, UseContext, VersionReference,
                        VersionSubmission)
from .discovery import EventClusterController, LineageRole
from .editorial import EditorialController
from .original import (OriginalMaterialController, RetentionMode, SourceIntake,
                       SourceNodeRead)


class ClaimType(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    AUTHOR_ASSERTION = "AUTHOR_ASSERTION"
    CALCULATION = "CALCULATION"
    EXPLANATION = "EXPLANATION"
    PREDICTION = "PREDICTION"
    VALUE_PREMISE = "VALUE_PREMISE"


class EvidenceNature(str, Enum):
    DOCUMENTED_FACT = "DOCUMENTED_FACT"
    AUTHOR_STATEMENT = "AUTHOR_STATEMENT"
    METHOD = "METHOD"
    BACKGROUND = "BACKGROUND"
    COMPARISON = "COMPARISON"
    CONTRADICTION = "CONTRADICTION"


class EvidenceRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    PARTIALLY_SUPPORTS = "PARTIALLY_SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    BACKGROUND_ONLY = "BACKGROUND_ONLY"
    IRRELEVANT = "IRRELEVANT"
    UNRESOLVED = "UNRESOLVED"


class CalculationOperation(str, Enum):
    SUM = "SUM"
    DIFFERENCE = "DIFFERENCE"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    PERCENT_CHANGE = "PERCENT_CHANGE"


class SupplementGapType(str, Enum):
    MISSING_SOURCE = "MISSING_SOURCE"
    PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    METHOD_OR_PROFESSIONAL_CONDITION = "METHOD_OR_PROFESSIONAL_CONDITION"
    CALCULATION_INPUT = "CALCULATION_INPUT"
    UNRESOLVED_EXPLANATION = "UNRESOLVED_EXPLANATION"


class SupplementStatus(str, Enum):
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    PARTIAL = "PARTIAL"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    NO_NEW_EVIDENCE = "NO_NEW_EVIDENCE"


class SupplementImpact(str, Enum):
    UNCHANGED = "UNCHANGED"
    STRENGTHENED = "STRENGTHENED"
    WEAKENED = "WEAKENED"
    UNRESOLVED = "UNRESOLVED"
    OBJECT_OR_SCOPE_CHANGED = "OBJECT_OR_SCOPE_CHANGED"


class SupplementMethod(str, Enum):
    MANUAL = "MANUAL"
    LOCAL_AUTHORIZED_ADAPTER = "LOCAL_AUTHORIZED_ADAPTER"
    GPT_RESEARCHER_TRIAL = "GPT_RESEARCHER_TRIAL"


class ClaimScope(Contract):
    subjects: tuple[NonBlank, ...]
    metric: NonBlank
    period: DataPeriod | None = None
    unit: NonBlank | None = None
    denominator: NonBlank | None = None
    comparison_basis: NonBlank
    conditions: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("subject", self.subjects),
                ("condition", self.conditions)):
            if len(values) != len(set(values)):
                raise ValueError(f"Claim scope {name} list must be unique")
        if not self.subjects:
            raise ValueError("Claim scope needs at least one subject")
        return self


class ClaimVersion(Contract):
    schema_version: Literal[1] = 1
    claim_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    question_version_id: Identifier
    claim_text: NonBlank
    claim_type: ClaimType
    scope: ClaimScope
    created_at: AwareDatetime


class EvidenceNodeBinding(Contract):
    node_id: Identifier
    locator: NonBlank
    text_sha256: Digest


class EvidenceRequest(Contract):
    schema_version: Literal[1] = 1
    evidence_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    intake_version_id: Identifier
    structure_version_id: Identifier
    lineage_proposal_id: Identifier
    cluster_id: Identifier
    node_ids: tuple[Identifier, ...]
    nature: EvidenceNature
    limitations: tuple[NonBlank, ...] = ()
    use_context: UseContext
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.node_ids or len(self.node_ids) != len(set(self.node_ids)):
            raise ValueError("Evidence needs nonempty unique structure nodes")
        if len(self.limitations) != len(set(self.limitations)):
            raise ValueError("Duplicate evidence limitation")
        return self


class EvidenceRecord(Contract):
    schema_version: Literal[1] = 1
    evidence_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    intake_version_id: Identifier
    structure_version_id: Identifier
    source_id: Identifier
    source_sha256: Digest
    lineage_proposal_id: Identifier
    cluster_id: Identifier
    lineage_role: LineageRole
    lineage_root_ids: tuple[Identifier, ...]
    independence_known: bool
    nodes: tuple[EvidenceNodeBinding, ...]
    nature: EvidenceNature
    limitations: tuple[NonBlank, ...] = ()
    content_verification: Literal["LOCATOR_REPLAY_ONLY"] = "LOCATOR_REPLAY_ONLY"
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.nodes or len({item.node_id for item in self.nodes}) != len(self.nodes):
            raise ValueError("EvidenceRecord needs locatable nodes")
        if self.independence_known != bool(self.lineage_root_ids):
            raise ValueError("Known independence requires exact lineage roots")
        return self


class ClaimEvidenceRequest(Contract):
    schema_version: Literal[1] = 1
    assessment_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    claim_version_id: Identifier
    evidence_version_ids: tuple[Identifier, ...]
    relation: EvidenceRelation
    supported_scope: ClaimScope | None = None
    conditions: tuple[NonBlank, ...] = ()
    unsupported_aspects: tuple[NonBlank, ...] = ()
    counterevidence: tuple[NonBlank, ...] = ()
    unknowns: tuple[NonBlank, ...] = ()
    reviewed_by: NonBlank
    reviewed_at: AwareDatetime
    use_context: UseContext
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        groups = (
            ("evidence", self.evidence_version_ids),
            ("condition", self.conditions),
            ("unsupported aspect", self.unsupported_aspects),
            ("counterevidence", self.counterevidence),
            ("unknown", self.unknowns),
        )
        for name, values in groups:
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate claim-evidence {name}")
        if not self.evidence_version_ids:
            raise ValueError("Claim-evidence assessment needs exact evidence versions")
        if self.relation in (
                EvidenceRelation.SUPPORTS,
                EvidenceRelation.PARTIALLY_SUPPORTS,
                EvidenceRelation.CONTRADICTS) and self.supported_scope is None:
            raise ValueError("Supported/contradicted scope must be explicit")
        if (self.relation is EvidenceRelation.PARTIALLY_SUPPORTS
                and not self.unsupported_aspects):
            raise ValueError("Partial support must state unsupported aspects")
        return self


class ClaimEvidenceAssessment(Contract):
    schema_version: Literal[1] = 1
    assessment_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    claim_version_id: Identifier
    evidence_version_ids: tuple[Identifier, ...]
    relation: EvidenceRelation
    supported_scope: ClaimScope | None
    conditions: tuple[NonBlank, ...]
    unsupported_aspects: tuple[NonBlank, ...]
    counterevidence: tuple[NonBlank, ...]
    unknowns: tuple[NonBlank, ...]
    independent_root_ids: tuple[Identifier, ...]
    independent_root_count: int = Field(ge=0)
    same_root_duplicate_count: int = Field(ge=0)
    independence_unknown_count: int = Field(ge=0)
    reviewed_by: NonBlank
    reviewed_at: AwareDatetime
    content_verification: Literal["LOCATOR_REPLAY_ONLY"] = "LOCATOR_REPLAY_ONLY"
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.evidence_version_ids or len(
                self.evidence_version_ids) != len(set(self.evidence_version_ids)):
            raise ValueError("Assessment evidence versions must be nonempty and unique")
        if self.independent_root_count != len(self.independent_root_ids):
            raise ValueError("Independent root count does not match exact roots")
        return self


class CalculationInput(Contract):
    input_id: Identifier
    intake_version_id: Identifier
    node_id: Identifier
    node_text_sha256: Digest
    value_text: NonBlank
    unit: NonBlank
    dimension: NonBlank
    period: DataPeriod


class CalculationRequest(Contract):
    schema_version: Literal[1] = 1
    calculation_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    claim_version_id: Identifier | None = None
    operation: CalculationOperation
    inputs: tuple[CalculationInput, ...]
    output_unit: NonBlank
    output_dimension: NonBlank
    rounding_places: int = Field(default=2, ge=0, le=12)
    expected_result: Decimal | None = None
    use_context: UseContext
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.inputs) < 2:
            raise ValueError("A calculation needs at least two exact inputs")
        if len({item.input_id for item in self.inputs}) != len(self.inputs):
            raise ValueError("Duplicate calculation input ID")
        if len({(item.intake_version_id, item.node_id) for item in self.inputs}) != len(
                self.inputs):
            raise ValueError("Duplicate calculation source-node binding")
        if self.operation in (
                CalculationOperation.DIFFERENCE,
                CalculationOperation.MULTIPLY,
                CalculationOperation.DIVIDE,
                CalculationOperation.PERCENT_CHANGE) and len(self.inputs) != 2:
            raise ValueError(f"{self.operation.value} requires exactly two inputs")
        return self


class CalculationInputRecord(Contract):
    input_id: Identifier
    intake_version_id: Identifier
    node_id: Identifier
    node_text_sha256: Digest
    value: Decimal
    unit: NonBlank
    dimension: NonBlank
    period: DataPeriod


class CalculationRecord(Contract):
    schema_version: Literal[1] = 1
    calculation_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    claim_version_id: Identifier | None
    operation: CalculationOperation
    inputs: tuple[CalculationInputRecord, ...]
    formula: NonBlank
    output_unit: NonBlank
    output_dimension: NonBlank
    rounding_places: int = Field(ge=0, le=12)
    declared_expected_result: Decimal | None = None
    result: Decimal
    result_sha256: Digest
    execution_status: Literal["EXECUTED"] = "EXECUTED"
    evaluator: Literal["LOCAL_DECIMAL_EVALUATOR"] = "LOCAL_DECIMAL_EVALUATOR"
    evaluator_version: NonBlank = "W25-DECIMAL-v1"
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    created_at: AwareDatetime


class SupplementRequest(Contract):
    schema_version: Literal[1] = 1
    supplement_request_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    claim_version_id: Identifier | None = None
    assessment_version_id: Identifier | None = None
    gap_type: SupplementGapType
    missing_information: NonBlank
    distinguishing_evidence: NonBlank
    next_owner: Literal["T04", "T05"]
    continuation_trigger: NonBlank
    restrictions: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.restrictions) != len(set(self.restrictions)):
            raise ValueError("Duplicate supplement restriction")
        return self


class SupplementResult(Contract):
    schema_version: Literal[1] = 1
    result_id: Identifier
    supplement_request_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    status: SupplementStatus
    method: SupplementMethod
    source_intake_version_ids: tuple[Identifier, ...] = ()
    evidence_version_ids: tuple[Identifier, ...] = ()
    assessment_version_ids: tuple[Identifier, ...] = ()
    before_relation: EvidenceRelation | None = None
    after_relation: EvidenceRelation | None = None
    impact: SupplementImpact
    affected_claim_version_ids: tuple[Identifier, ...] = ()
    object_or_scope_changed: bool = False
    s8_review_required: bool = False
    reason: NonBlank
    continuation_trigger: NonBlank
    facts_verified: Literal[False] = False
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("source", self.source_intake_version_ids),
                ("evidence", self.evidence_version_ids),
                ("assessment", self.assessment_version_ids),
                ("affected claim", self.affected_claim_version_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate supplement result {name}")
        if self.object_or_scope_changed and not self.s8_review_required:
            raise ValueError("Object/scope change requires S8 review")
        if self.impact is SupplementImpact.OBJECT_OR_SCOPE_CHANGED and not self.s8_review_required:
            raise ValueError("Object/scope impact must require S8 review")
        if self.status is SupplementStatus.EVIDENCE_ADDED:
            if not self.source_intake_version_ids or not self.evidence_version_ids:
                raise ValueError("Added supplement result needs actual source and evidence versions")
            if not self.assessment_version_ids:
                raise ValueError("Added supplement result needs a new claim assessment")
        return self


class EvidenceError(ArchiveError):
    """Evidence/support failure, never automatic factual or causal approval."""


class CalculationError(ArchiveError):
    """Calculation input/execution failure, never factual support."""


class SupplementError(ArchiveError):
    """A gap-follow-up record failure, never publication approval."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _decimal(value_text: str) -> Decimal:
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", value_text):
        raise CalculationError(f"Source value is not a plain decimal: {value_text!r}")
    try:
        return Decimal(value_text)
    except InvalidOperation as exc:
        raise CalculationError(f"Invalid decimal input: {value_text!r}") from exc


def _contains_value(text: str, value_text: str) -> bool:
    pattern = r"(?<![\d.])" + re.escape(value_text) + r"(?![\d.])"
    return re.search(pattern, text) is not None


def _store(
        archive: Archive, rights: RightsGrant, *, version_id: str, object_id: str,
        kind: ObjectKind, title: str, spec_sha256: str, created_at: datetime,
        body: Contract, references: tuple[VersionReference, ...],
        expected_current: dict[str, str | None]) -> StoredVersion:
    body_bytes = canonical(body.model_dump(mode="json")).encode()
    try:
        existing = archive.get(version_id)
        if existing.submission.kind is kind and existing.body_sha256 == _digest(body_bytes):
            return existing
        raise ArchiveError("Version ID is already used by different content")
    except MissingVersion:
        pass
    submission = VersionSubmission(
        schema_version=2, object_id=object_id, version_id=version_id,
        kind=kind, title=title, spec_sha256=spec_sha256, created_at=created_at,
        source_times=SourceTimes(), rights=rights,
        representation=Representation.FULL_BODY, references=references)
    return archive.append(
        submission, body_bytes, expected_current=expected_current)


class EvidenceController:
    def __init__(self, archive: Archive, journal_rights: RightsGrant,
                 original: OriginalMaterialController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("EvidenceController requires the shared Archive")
        if not isinstance(journal_rights, RightsGrant):
            raise TypeError("EvidenceController requires an internal journal grant")
        self.archive = archive
        self.rights = journal_rights
        self.original = original or OriginalMaterialController(archive, journal_rights)
        self.editorial = EditorialController(archive, journal_rights)

    def append_claim(self, claim: ClaimVersion) -> StoredVersion:
        if not isinstance(claim, ClaimVersion):
            raise TypeError("append_claim requires ClaimVersion")
        claim = ClaimVersion.model_validate_json(
            claim.model_dump_json(warnings=False))
        question = self.archive.get(claim.question_version_id)
        if question.submission.kind is not ObjectKind.QUESTION_VERSION:
            raise EvidenceError("Claim question dependency is not a QuestionVersion")
        if question.submission.spec_sha256 != claim.spec_sha256:
            raise EvidenceError("Claim and question specifications differ")
        version_id = claim.claim_version_id
        return _store(
            self.archive, self.rights, version_id=version_id,
            object_id=_object("CLAIM-OBJECT-", claim.claim_version_id),
            kind=ObjectKind.CLAIM, title=f"claim {claim.claim_version_id}",
            spec_sha256=claim.spec_sha256, created_at=claim.created_at,
            body=claim,
            references=(VersionReference(
                target_version_id=claim.question_version_id,
                use=ReferenceUse.BASIS, locator="exact claim question version"),),
            expected_current={
                _object("CLAIM-OBJECT-", claim.claim_version_id): None})

    def load_claim(self, claim_version_id: str) -> ClaimVersion:
        stored = self.archive.get(claim_version_id)
        if stored.submission.kind is not ObjectKind.CLAIM:
            raise EvidenceError("Requested version is not a Claim")
        claim = ClaimVersion.model_validate_json(
            self.archive.read_body(claim_version_id))
        if stored.submission.version_id != claim.claim_version_id:
            raise EvidenceError("Claim identity mismatch")
        return claim

    def append_evidence(self, request: EvidenceRequest) -> StoredVersion:
        if not isinstance(request, EvidenceRequest):
            raise TypeError("append_evidence requires EvidenceRequest")
        request = EvidenceRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        intake = self.original.load_intake_version(request.intake_version_id)
        if intake.spec_sha256 != request.spec_sha256:
            raise EvidenceError("Evidence and SourceIntake specifications differ")
        if intake.structure_version_id != request.structure_version_id:
            raise EvidenceError("Evidence structure does not match its SourceIntake")
        if intake.retention is not RetentionMode.RETAINED:
            raise EvidenceError("Evidence needs a retained exact source body")
        structure = self.original.load_structure(request.structure_version_id)
        proposal = EventClusterController(
            self.archive, self.rights).load_proposal(request.lineage_proposal_id)
        if proposal.spec_sha256 != request.spec_sha256:
            raise EvidenceError("Evidence lineage proposal uses another specification")
        cluster = next(
            (item for item in proposal.clusters
             if item.cluster_id == request.cluster_id), None)
        if cluster is None:
            raise EvidenceError("Evidence cluster is outside its lineage proposal")
        members = [
            item for item in cluster.members
            if (item.source_id == intake.source_id
                and item.original_url == intake.original_url)]
        if not members:
            raise EvidenceError(
                "Evidence source/URL is not a member of the declared event cluster")
        root_sets = {frozenset(member.lineage_root_ids) for member in members}
        if len(root_sets) != 1:
            raise EvidenceError("One source has conflicting lineage roots in its cluster")
        roots = tuple(sorted(root_sets.pop()))
        roles = {member.lineage_role for member in members}
        if len(roles) != 1:
            raise EvidenceError("One source has conflicting lineage roles")
        role = next(iter(roles))
        nodes_by_id = {node.node_id: node for node in structure.nodes}
        bindings = []
        for node_id in request.node_ids:
            node = nodes_by_id.get(node_id)
            if node is None:
                raise EvidenceError(f"Evidence node is outside its exact structure: {node_id}")
            read: SourceNodeRead = self.original.read_node(
                intake.intake_id, node_id, MaterialUse.MODEL_PROCESS,
                request.use_context)
            if read.node != node:
                raise EvidenceError("Evidence node no longer matches the structure")
            bindings.append(EvidenceNodeBinding(
                node_id=node.node_id, locator=node.locator,
                text_sha256=node.text_sha256))
        evidence = EvidenceRecord(
            evidence_id=request.evidence_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            intake_version_id=request.intake_version_id,
            structure_version_id=request.structure_version_id,
            source_id=intake.source_id, source_sha256=intake.source_sha256,
            lineage_proposal_id=request.lineage_proposal_id,
            cluster_id=request.cluster_id, lineage_role=role,
            lineage_root_ids=roots, independence_known=bool(roots),
            nodes=tuple(bindings), nature=request.nature,
            limitations=request.limitations, created_at=request.created_at)
        proposal_version_id = EventClusterController._version(
            request.lineage_proposal_id)
        intake_stored = self.archive.get(request.intake_version_id)
        structure_stored = self.archive.get(request.structure_version_id)
        proposal_stored = self.archive.get(proposal_version_id)
        version_id = _version("EVIDENCE-RECORD-", evidence.evidence_id)
        return _store(
            self.archive, self.rights, version_id=version_id,
            object_id=_object("EVIDENCE-RECORD-OBJECT-", evidence.evidence_id),
            kind=ObjectKind.EVIDENCE, title=f"evidence {evidence.evidence_id}",
            spec_sha256=evidence.spec_sha256, created_at=evidence.created_at,
            body=evidence,
            references=(
                VersionReference(target_version_id=request.intake_version_id,
                    use=ReferenceUse.SOURCE, locator="exact source intake"),
                VersionReference(target_version_id=request.structure_version_id,
                    use=ReferenceUse.SUPPORT, locator="exact locator structure"),
                VersionReference(target_version_id=proposal_version_id,
                    use=ReferenceUse.LINEAGE, locator="declared event lineage"),
            ),
            expected_current={
                _object("EVIDENCE-RECORD-OBJECT-", evidence.evidence_id): None,
                intake_stored.submission.object_id: intake_stored.submission.version_id,
                structure_stored.submission.object_id: structure_stored.submission.version_id,
                proposal_stored.submission.object_id: proposal_stored.submission.version_id,
            })

    def load_evidence(self, evidence_version_id: str) -> EvidenceRecord:
        stored = self.archive.get(evidence_version_id)
        if stored.submission.kind is not ObjectKind.EVIDENCE:
            raise EvidenceError("Requested version is not an EvidenceRecord")
        evidence = EvidenceRecord.model_validate_json(
            self.archive.read_body(evidence_version_id))
        if stored.submission.version_id != _version(
                "EVIDENCE-RECORD-", evidence.evidence_id):
            raise EvidenceError("Evidence identity mismatch")
        return evidence

    def assess_claim(self, request: ClaimEvidenceRequest) -> StoredVersion:
        if not isinstance(request, ClaimEvidenceRequest):
            raise TypeError("assess_claim requires ClaimEvidenceRequest")
        request = ClaimEvidenceRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        claim = self.load_claim(request.claim_version_id)
        if claim.theme_id != request.theme_id or claim.spec_sha256 != request.spec_sha256:
            raise EvidenceError("Claim and assessment theme/specification differ")
        evidence_records = []
        for evidence_version_id in request.evidence_version_ids:
            evidence = self.load_evidence(evidence_version_id)
            if (evidence.theme_id != request.theme_id
                    or evidence.spec_sha256 != request.spec_sha256):
                raise EvidenceError("Evidence and assessment theme/specification differ")
            intake = self.original.load_intake_version(evidence.intake_version_id)
            for binding in evidence.nodes:
                read = self.original.read_node(
                    intake.intake_id, binding.node_id, MaterialUse.MODEL_PROCESS,
                    request.use_context)
                if read.node.text_sha256 != binding.text_sha256:
                    raise EvidenceError("Evidence node hash changed before assessment")
            evidence_records.append(evidence)
        roots = set()
        same_root_duplicates = 0
        unknown = 0
        for evidence in evidence_records:
            evidence_roots = set(evidence.lineage_root_ids)
            if not evidence_roots:
                unknown += 1
                continue
            if evidence_roots <= roots:
                same_root_duplicates += 1
            roots.update(evidence_roots)
        assessment = ClaimEvidenceAssessment(
            assessment_id=request.assessment_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            claim_version_id=request.claim_version_id,
            evidence_version_ids=request.evidence_version_ids,
            relation=request.relation, supported_scope=request.supported_scope,
            conditions=request.conditions,
            unsupported_aspects=request.unsupported_aspects,
            counterevidence=request.counterevidence, unknowns=request.unknowns,
            independent_root_ids=tuple(sorted(roots)),
            independent_root_count=len(roots),
            same_root_duplicate_count=same_root_duplicates,
            independence_unknown_count=unknown,
            reviewed_by=request.reviewed_by, reviewed_at=request.reviewed_at,
            created_at=request.created_at)
        version_id = _version("CLAIM-EVIDENCE-", assessment.assessment_id)
        claim_stored = self.archive.get(request.claim_version_id)
        evidence_stored = tuple(
            self.archive.get(item) for item in request.evidence_version_ids)
        references = [
            VersionReference(target_version_id=request.claim_version_id,
                use=ReferenceUse.BASIS, locator="exact claim version"),
            *(VersionReference(target_version_id=item,
                use=ReferenceUse.SUPPORT, locator=f"evidence {index}")
              for index, item in enumerate(request.evidence_version_ids)),
        ]
        expected = {
            _object("CLAIM-EVIDENCE-OBJECT-", assessment.assessment_id): None,
            claim_stored.submission.object_id: claim_stored.submission.version_id,
        }
        for stored in evidence_stored:
            expected[stored.submission.object_id] = stored.submission.version_id
        return _store(
            self.archive, self.rights, version_id=version_id,
            object_id=_object("CLAIM-EVIDENCE-OBJECT-", assessment.assessment_id),
            kind=ObjectKind.CLAIM_EVIDENCE_ASSESSMENT,
            title=f"claim evidence {assessment.assessment_id}",
            spec_sha256=assessment.spec_sha256, created_at=assessment.created_at,
            body=assessment, references=tuple(references),
            expected_current=expected)

    def load_assessment(self, assessment_version_id: str) -> ClaimEvidenceAssessment:
        stored = self.archive.get(assessment_version_id)
        if stored.submission.kind is not ObjectKind.CLAIM_EVIDENCE_ASSESSMENT:
            raise EvidenceError("Requested version is not a ClaimEvidenceAssessment")
        assessment = ClaimEvidenceAssessment.model_validate_json(
            self.archive.read_body(assessment_version_id))
        if stored.submission.version_id != _version(
                "CLAIM-EVIDENCE-", assessment.assessment_id):
            raise EvidenceError("Claim-evidence identity mismatch")
        return assessment


class CalculationController:
    def __init__(self, archive: Archive, journal_rights: RightsGrant,
                 original: OriginalMaterialController | None = None):
        self.archive = archive
        self.rights = journal_rights
        self.original = original or OriginalMaterialController(archive, journal_rights)

    def _load_input(self, item: CalculationInput,
                    context: UseContext) -> tuple[SourceIntake, SourceNodeRead, Decimal]:
        intake = self.original.load_intake_version(item.intake_version_id)
        if intake.data_period != item.period:
            raise CalculationError("Calculation input period differs from the source data period")
        structure = self.original.load_structure(intake.structure_version_id)
        node = next((node for node in structure.nodes if node.node_id == item.node_id), None)
        if node is None:
            raise CalculationError("Calculation node is outside the exact source structure")
        if node.text_sha256 != item.node_text_sha256:
            raise CalculationError("Calculation input does not bind the current node hash")
        read = self.original.read_node(
            intake.intake_id, item.node_id, MaterialUse.MODEL_PROCESS, context)
        if not _contains_value(read.text, item.value_text):
            raise CalculationError("Declared numeric value does not occur in the exact source node")
        if item.unit.casefold() not in read.text.casefold():
            raise CalculationError("Declared unit does not occur in the exact source node")
        return intake, read, _decimal(item.value_text)

    def calculate(self, request: CalculationRequest) -> StoredVersion:
        if not isinstance(request, CalculationRequest):
            raise TypeError("calculate requires CalculationRequest")
        request = CalculationRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        if request.claim_version_id is not None:
            claim_stored = self.archive.get(request.claim_version_id)
            if claim_stored.submission.kind is not ObjectKind.CLAIM:
                raise CalculationError("Calculation claim dependency is not a Claim")
            claim = ClaimVersion.model_validate_json(
                self.archive.read_body(request.claim_version_id))
            if (claim.theme_id != request.theme_id
                    or claim.spec_sha256 != request.spec_sha256):
                raise CalculationError("Calculation and claim theme/specification differ")
        inputs = []
        intakes = []
        intake_versions = []
        for item in request.inputs:
            intake, _, value = self._load_input(item, request.use_context)
            intakes.append(intake)
            intake_versions.append(self.archive.get(item.intake_version_id))
            inputs.append(CalculationInputRecord(
                input_id=item.input_id, intake_version_id=item.intake_version_id,
                node_id=item.node_id, node_text_sha256=item.node_text_sha256,
                value=value, unit=item.unit, dimension=item.dimension,
                period=item.period))
        values = [item.value for item in inputs]
        if request.operation in (
                CalculationOperation.SUM, CalculationOperation.DIFFERENCE):
            if len({(item.unit, item.dimension) for item in inputs}) != 1:
                raise CalculationError("Addition/subtraction requires one exact unit and dimension")
            if len({item.period for item in inputs}) != 1:
                raise CalculationError("Addition/subtraction requires one exact data period")
            if request.output_unit != inputs[0].unit or request.output_dimension != inputs[0].dimension:
                raise CalculationError("Output unit/dimension differs from additive inputs")
            if request.operation is CalculationOperation.SUM:
                raw_result = sum(values, Decimal("0"))
                formula = " + ".join(item.input_id for item in inputs)
            else:
                raw_result = values[0] - values[1]
                formula = f"{inputs[0].input_id} - {inputs[1].input_id}"
        elif request.operation is CalculationOperation.MULTIPLY:
            expected_unit = f"{inputs[0].unit}*{inputs[1].unit}"
            expected_dimension = f"{inputs[0].dimension}*{inputs[1].dimension}"
            if (request.output_unit != expected_unit
                    or request.output_dimension != expected_dimension):
                raise CalculationError("Output unit/dimension does not match multiplication")
            raw_result = values[0] * values[1]
            formula = f"{inputs[0].input_id} * {inputs[1].input_id}"
        elif request.operation is CalculationOperation.DIVIDE:
            if values[1] == 0:
                raise CalculationError("Division denominator is zero")
            expected_unit = f"{inputs[0].unit}/{inputs[1].unit}"
            expected_dimension = f"{inputs[0].dimension}/{inputs[1].dimension}"
            if (request.output_unit != expected_unit
                    or request.output_dimension != expected_dimension):
                raise CalculationError("Output unit/dimension does not match division")
            raw_result = values[0] / values[1]
            formula = f"{inputs[0].input_id} / {inputs[1].input_id}"
        else:
            if len({(item.unit, item.dimension) for item in inputs}) != 1:
                raise CalculationError("Percent change requires one exact unit and dimension")
            if request.output_unit != "%" or request.output_dimension != "RATIO":
                raise CalculationError("Percent change output must be %/RATIO")
            if values[0] == 0:
                raise CalculationError("Percent-change baseline is zero")
            raw_result = (values[1] - values[0]) / values[0] * Decimal("100")
            formula = (
                f"({inputs[1].input_id} - {inputs[0].input_id})"
                f" / {inputs[0].input_id} * 100")
        quantum = Decimal("1").scaleb(-request.rounding_places)
        try:
            result = raw_result.quantize(quantum, rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise CalculationError("Calculation result cannot be represented at requested precision") from exc
        if request.expected_result is not None and request.expected_result != result:
            raise CalculationError(
                f"Executed calculation produced {result}, not the declared expected result")
        result_sha = _digest({
            "operation": request.operation.value,
            "inputs": [item.model_dump(mode="json") for item in inputs],
            "formula": formula,
            "result": str(result),
            "unit": request.output_unit,
            "dimension": request.output_dimension,
            "rounding_places": request.rounding_places,
            "evaluator_version": "W25-DECIMAL-v1",
        })
        record = CalculationRecord(
            calculation_id=request.calculation_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            claim_version_id=request.claim_version_id,
            operation=request.operation, inputs=tuple(inputs), formula=formula,
            output_unit=request.output_unit,
            output_dimension=request.output_dimension,
            rounding_places=request.rounding_places,
            declared_expected_result=request.expected_result, result=result,
            result_sha256=result_sha, created_at=request.created_at)
        refs = [
            VersionReference(target_version_id=item.intake_version_id,
                use=ReferenceUse.SOURCE, locator=f"calculation input {item.input_id}")
            for item in inputs]
        if request.claim_version_id is not None:
            refs.append(VersionReference(
                target_version_id=request.claim_version_id,
                use=ReferenceUse.BASIS, locator="exact claim calculation"))
        expected = {
            _object("CALCULATION-OBJECT-", request.calculation_id): None}
        for intake in intakes:
            stored = self.archive.get(intake.source_version_id)
            expected[stored.submission.object_id] = stored.submission.version_id
        for stored in intake_versions:
            expected[stored.submission.object_id] = stored.submission.version_id
        if request.claim_version_id is not None:
            claim_stored = self.archive.get(request.claim_version_id)
            expected[claim_stored.submission.object_id] = claim_stored.submission.version_id
        return _store(
            self.archive, self.rights,
            version_id=_version("CALCULATION-", request.calculation_id),
            object_id=_object("CALCULATION-OBJECT-", request.calculation_id),
            kind=ObjectKind.CALCULATION_RECORD,
            title=f"calculation {request.calculation_id}",
            spec_sha256=request.spec_sha256, created_at=request.created_at,
            body=record, references=tuple(refs), expected_current=expected)

    def load_calculation(self, calculation_version_id: str) -> CalculationRecord:
        stored = self.archive.get(calculation_version_id)
        if stored.submission.kind is not ObjectKind.CALCULATION_RECORD:
            raise CalculationError("Requested version is not a CalculationRecord")
        record = CalculationRecord.model_validate_json(
            self.archive.read_body(calculation_version_id))
        if stored.submission.version_id != _version(
                "CALCULATION-", record.calculation_id):
            raise CalculationError("Calculation identity mismatch")
        return record


class SupplementController:
    def __init__(self, archive: Archive, journal_rights: RightsGrant,
                 evidence: EvidenceController | None = None):
        self.archive = archive
        self.rights = journal_rights
        self.evidence = evidence or EvidenceController(archive, journal_rights)

    def append_request(self, request: SupplementRequest) -> StoredVersion:
        if not isinstance(request, SupplementRequest):
            raise TypeError("append_request requires SupplementRequest")
        request = SupplementRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        references = []
        expected = {
            _object("SUPPLEMENT-REQUEST-OBJECT-", request.supplement_request_id): None}
        if request.claim_version_id is not None:
            claim = self.evidence.load_claim(request.claim_version_id)
            if claim.theme_id != request.theme_id or claim.spec_sha256 != request.spec_sha256:
                raise SupplementError("Supplement claim theme/specification differs")
            stored = self.archive.get(request.claim_version_id)
            expected[stored.submission.object_id] = stored.submission.version_id
            references.append(VersionReference(
                target_version_id=request.claim_version_id,
                use=ReferenceUse.BASIS, locator="supplement target claim"))
        if request.assessment_version_id is not None:
            assessment = self.evidence.load_assessment(request.assessment_version_id)
            if (assessment.theme_id != request.theme_id
                    or assessment.spec_sha256 != request.spec_sha256
                    or (request.claim_version_id is not None
                        and assessment.claim_version_id != request.claim_version_id)):
                raise SupplementError("Supplement prior assessment does not bind claim/theme/spec")
            stored = self.archive.get(request.assessment_version_id)
            expected[stored.submission.object_id] = stored.submission.version_id
            references.append(VersionReference(
                target_version_id=request.assessment_version_id,
                use=ReferenceUse.BASIS, locator="prior claim-evidence assessment"))
        return _store(
            self.archive, self.rights,
            version_id=_version("SUPPLEMENT-REQUEST-", request.supplement_request_id),
            object_id=_object("SUPPLEMENT-REQUEST-OBJECT-", request.supplement_request_id),
            kind=ObjectKind.SUPPLEMENT_REQUEST,
            title=f"supplement request {request.supplement_request_id}",
            spec_sha256=request.spec_sha256, created_at=request.created_at,
            body=request, references=tuple(references), expected_current=expected)

    def load_request(self, request_version_id: str) -> SupplementRequest:
        stored = self.archive.get(request_version_id)
        if stored.submission.kind is not ObjectKind.SUPPLEMENT_REQUEST:
            raise SupplementError("Requested version is not a SupplementRequest")
        request = SupplementRequest.model_validate_json(
            self.archive.read_body(request_version_id))
        if stored.submission.version_id != _version(
                "SUPPLEMENT-REQUEST-", request.supplement_request_id):
            raise SupplementError("Supplement request identity mismatch")
        return request

    def append_result(self, result: SupplementResult) -> StoredVersion:
        if not isinstance(result, SupplementResult):
            raise TypeError("append_result requires SupplementResult")
        result = SupplementResult.model_validate_json(
            result.model_dump_json(warnings=False))
        if result.method is SupplementMethod.GPT_RESEARCHER_TRIAL:
            raise SupplementError(
                "GPT Researcher trial adapter is not implemented; use a later controlled integration")
        request = self.load_request(result.supplement_request_version_id)
        if (request.theme_id != result.theme_id
                or request.spec_sha256 != result.spec_sha256):
            raise SupplementError("Supplement result and request theme/specification differ")
        references = [VersionReference(
            target_version_id=result.supplement_request_version_id,
            use=ReferenceUse.BASIS, locator="exact supplement request")]
        expected = {
            _object("SUPPLEMENT-RESULT-OBJECT-", result.result_id): None}
        if request.assessment_version_id is not None:
            prior = self.evidence.load_assessment(request.assessment_version_id)
            if result.before_relation != prior.relation:
                raise SupplementError("Supplement before-relation differs from its prior assessment")
        for intake_id in result.source_intake_version_ids:
            intake = self.evidence.original.load_intake_version(intake_id)
            if intake.spec_sha256 != result.spec_sha256:
                raise SupplementError("Supplement source intake uses another specification")
            stored = self.archive.get(intake_id)
            expected[stored.submission.object_id] = stored.submission.version_id
            references.append(VersionReference(
                target_version_id=intake_id, use=ReferenceUse.SOURCE,
                locator="actual supplement source intake"))
        for evidence_id in result.evidence_version_ids:
            evidence = self.evidence.load_evidence(evidence_id)
            if (evidence.theme_id != result.theme_id
                    or evidence.spec_sha256 != result.spec_sha256):
                raise SupplementError("Supplement evidence theme/specification differs")
            if evidence.intake_version_id not in result.source_intake_version_ids:
                raise SupplementError("Supplement evidence source is absent from its actual source list")
            stored = self.archive.get(evidence_id)
            expected[stored.submission.object_id] = stored.submission.version_id
            references.append(VersionReference(
                target_version_id=evidence_id, use=ReferenceUse.SUPPORT,
                locator="actual supplement evidence"))
        assessed_evidence = set()
        for assessment_id in result.assessment_version_ids:
            assessment = self.evidence.load_assessment(assessment_id)
            if (assessment.theme_id != result.theme_id
                    or assessment.spec_sha256 != result.spec_sha256):
                raise SupplementError("Supplement assessment theme/specification differs")
            if not set(assessment.evidence_version_ids) <= set(
                    result.evidence_version_ids):
                raise SupplementError("Supplement assessment cites evidence outside the result")
            assessed_evidence.update(assessment.evidence_version_ids)
            stored = self.archive.get(assessment_id)
            expected[stored.submission.object_id] = stored.submission.version_id
            references.append(VersionReference(
                target_version_id=assessment_id, use=ReferenceUse.REVIEW_OF,
                locator="new claim-evidence assessment"))
            if result.after_relation != assessment.relation:
                raise SupplementError("Supplement after-relation differs from every new assessment")
        for claim_id in result.affected_claim_version_ids:
            claim = self.evidence.load_claim(claim_id)
            if claim.theme_id != result.theme_id or claim.spec_sha256 != result.spec_sha256:
                raise SupplementError("Supplement affected claim theme/specification differs")
            stored = self.archive.get(claim_id)
            expected[stored.submission.object_id] = stored.submission.version_id
            references.append(VersionReference(
                target_version_id=claim_id, use=ReferenceUse.REVIEW_OF,
                locator="affected claim version"))
        if result.status is SupplementStatus.EVIDENCE_ADDED and result.after_relation is None:
            raise SupplementError("Added evidence must state the resulting relation")
        if result.status is SupplementStatus.EVIDENCE_ADDED and not set(
                result.evidence_version_ids) <= assessed_evidence:
            raise SupplementError("Every added evidence version needs the resulting assessment")
        if (request.claim_version_id is not None
                and request.claim_version_id not in result.affected_claim_version_ids):
            raise SupplementError("Supplement result must list its target claim as affected")
        return _store(
            self.archive, self.rights,
            version_id=_version("SUPPLEMENT-RESULT-", result.result_id),
            object_id=_object("SUPPLEMENT-RESULT-OBJECT-", result.result_id),
            kind=ObjectKind.SUPPLEMENT_RESULT,
            title=f"supplement result {result.result_id}",
            spec_sha256=result.spec_sha256, created_at=result.created_at,
            body=result, references=tuple(references), expected_current=expected)

    def load_result(self, result_version_id: str) -> SupplementResult:
        stored = self.archive.get(result_version_id)
        if stored.submission.kind is not ObjectKind.SUPPLEMENT_RESULT:
            raise SupplementError("Requested version is not a SupplementResult")
        result = SupplementResult.model_validate_json(
            self.archive.read_body(result_version_id))
        if stored.submission.version_id != _version(
                "SUPPLEMENT-RESULT-", result.result_id):
            raise SupplementError("Supplement result identity mismatch")
        return result
