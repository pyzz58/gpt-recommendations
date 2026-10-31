"""W29 B2 knowledge research, continuous teaching and transfer records.

The record starts from B2's own M02 question and binds one exact W27 dossier,
one exact W16 revision and current W25 knowledge sources. It creates an M11
teaching output; it is not a content PASS, a reader-mastery measure, an
independent Review, an adoption decision or publication authorization.
"""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .advisor import AdvisorController
from .archive import Archive, ArchiveError, Conflict, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank,
                        ObjectKind, ReferenceUse, Representation, RightsGrant,
                        SourceTimes, StoredVersion, VersionReference,
                        VersionSubmission)
from .evidence import EvidenceController, EvidenceRelation
from .model_admission import ModelAdmissionController, ModelDuty
from .operations import (OperationJournal, OperationKind, OperationRequest,
                         OperationStatus)
from .research import ResearchRevisionController
from .workflow import (ExecutionMethod, Participant, ResearchStep,
                       ResearchStepSubmission, ResearchWorkflowController,
                       StepDisposition, StepOwner, WorkflowError)


class TeachingStrength(str, Enum):
    BOUNDED_EXPLANATION = "BOUNDED_EXPLANATION"
    PARTIAL_EXPLANATION = "PARTIAL_EXPLANATION"
    LIMITATION_OR_UNKNOWN = "LIMITATION_OR_UNKNOWN"


class KnowledgePropositionType(str, Enum):
    FORMAL_CONSTRAINT = "FORMAL_CONSTRAINT"
    EMPIRICAL_NATURAL_LAW = "EMPIRICAL_NATURAL_LAW"
    INSTITUTIONAL_RULE = "INSTITUTIONAL_RULE"
    CONDITIONAL_MECHANISM = "CONDITIONAL_MECHANISM"
    EMPIRICAL_PATTERN = "EMPIRICAL_PATTERN"
    HISTORICAL_ANALOGY = "HISTORICAL_ANALOGY"
    CONCEPT_DEFINITION = "CONCEPT_DEFINITION"
    NORMATIVE_PROPOSITION = "NORMATIVE_PROPOSITION"


class TeachingSectionKind(str, Enum):
    CASE_CONTEXT = "CASE_CONTEXT"
    NECESSARY_BASIS = "NECESSARY_BASIS"
    PROCESS = "PROCESS"
    EXAMPLE = "EXAMPLE"
    CALCULATION = "CALCULATION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    BOUNDARY = "BOUNDARY"
    KNOWLEDGE_SUMMARY = "KNOWLEDGE_SUMMARY"
    TRANSFER = "TRANSFER"
    RECAP = "RECAP"


class ConceptReuseMode(str, Enum):
    NEW_EXPLANATION = "NEW_EXPLANATION"
    NECESSARY_RECAP = "NECESSARY_RECAP"
    DIFFERENT_REALITY = "DIFFERENT_REALITY"
    CONDITION_CHANGE = "CONDITION_CHANGE"


class KnowledgeQuestion(Contract):
    question_id: Identifier
    early_question: NonBlank
    research_question: NonBlank
    relation_to_early_question: NonBlank
    why_material_requires_it: NonBlank
    what_it_should_explain: NonBlank


class KnowledgeProposition(Contract):
    proposition_id: Identifier
    statement: NonBlank
    proposition_type: KnowledgePropositionType
    conditions: tuple[NonBlank, ...]
    scope: NonBlank
    unknowns: tuple[NonBlank, ...]
    falsifiers: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("condition", self.conditions),
                ("unknown", self.unknowns),
                ("falsifier", self.falsifiers)):
            if (not values or len(values) != len(set(values))):
                raise ValueError(
                    f"Knowledge proposition needs unique explicit {name}s")
        return self


class TeachingSection(Contract):
    section_id: Identifier
    ordinal: int = Field(ge=1)
    kind: TeachingSectionKind
    plain_language_text: NonBlank
    claim_version_ids: tuple[Identifier, ...] = ()
    evidence_version_ids: tuple[Identifier, ...] = ()
    method_use_version_ids: tuple[Identifier, ...] = ()
    concept_version_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("claim", self.claim_version_ids),
                ("evidence", self.evidence_version_ids),
                ("method", self.method_use_version_ids),
                ("concept", self.concept_version_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate teaching section {name}")
        if self.kind in {
                TeachingSectionKind.CASE_CONTEXT,
                TeachingSectionKind.NECESSARY_BASIS,
                TeachingSectionKind.PROCESS,
                TeachingSectionKind.EXAMPLE,
                TeachingSectionKind.CALCULATION,
                TeachingSectionKind.COUNTEREXAMPLE,
                TeachingSectionKind.BOUNDARY,
                TeachingSectionKind.KNOWLEDGE_SUMMARY,
        } and not (self.claim_version_ids or self.evidence_version_ids):
            raise ValueError(
                "Source-bearing teaching paragraph needs Claim or Evidence")
        return self


class ProcessStep(Contract):
    step_id: Identifier
    ordinal: int = Field(ge=1)
    section_id: Identifier
    from_condition: NonBlank
    relation_or_action: NonBlank
    to_result: NonBlank
    conditions: tuple[NonBlank, ...]
    evidence_version_ids: tuple[Identifier, ...]
    uncertainty: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.conditions or len(self.conditions) != len(
                set(self.conditions)):
            raise ValueError("Process step needs unique explicit conditions")
        if (not self.evidence_version_ids
                or len(self.evidence_version_ids)
                != len(set(self.evidence_version_ids))):
            raise ValueError("Process step needs exact Evidence versions")
        return self


class TeachingBoundary(Contract):
    boundary_id: Identifier
    section_id: Identifier
    condition_that_changes_result: NonBlank
    counterexample_or_contrast: NonBlank
    unsupported_scope: NonBlank
    unknowns: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.unknowns or len(self.unknowns) != len(set(self.unknowns)):
            raise ValueError("Teaching boundary needs unique explicit unknowns")
        return self


class TransferCheck(Contract):
    transfer_id: Identifier
    section_id: Identifier
    target_scenario: NonBlank
    shared_relations: tuple[NonBlank, ...]
    changed_conditions: tuple[NonBlank, ...]
    facts_to_recheck: tuple[NonBlank, ...]
    what_must_not_be_assumed: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("shared relation", self.shared_relations),
                ("changed condition", self.changed_conditions),
                ("recheck fact", self.facts_to_recheck),
                ("non-assumption", self.what_must_not_be_assumed)):
            if (not values or len(values) != len(set(values))):
                raise ValueError(
                    f"Transfer check needs unique explicit {name}s")
        return self


class TeachingDemonstration(Contract):
    demonstration_id: Identifier
    section_id: Identifier
    hypothetical: bool = False
    hypothetical_label: NonBlank | None = None
    inputs_and_units: tuple[NonBlank, ...] = ()
    assumptions: tuple[NonBlank, ...]
    steps: tuple[NonBlank, ...]
    result: NonBlank
    limits: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.hypothetical != (self.hypothetical_label is not None):
            raise ValueError(
                "Hypothetical demonstration needs an explicit label, and only then")
        for name, values in (
                ("input/unit", self.inputs_and_units),
                ("assumption", self.assumptions),
                ("step", self.steps)):
            if values and len(values) != len(set(values)):
                raise ValueError(f"Duplicate demonstration {name}")
        if not self.assumptions or not self.steps:
            raise ValueError(
                "Demonstration needs explicit assumptions and calculation/example steps")
        return self


class TermExplanation(Contract):
    term: NonBlank
    plain_explanation_section_id: Identifier
    named_in_section_id: Identifier
    definition: NonBlank
    case_application: NonBlank
    limits: NonBlank
    concept_version_id: Identifier | None = None


class ConceptUse(Contract):
    concept_version_id: Identifier
    reuse_mode: ConceptReuseMode
    case_application: NonBlank
    conditions_checked: tuple[NonBlank, ...]
    does_not_prove: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.conditions_checked
                or len(self.conditions_checked)
                != len(set(self.conditions_checked))):
            raise ValueError("Concept use needs unique checked conditions")
        return self


class TeachingGain(Contract):
    before_explanation: NonBlank
    after_explanation: NonBlank
    case_specific_bridge: NonBlank
    knowledge_contribution: NonBlank
    not_b1_restatement: NonBlank
    what_reader_can_examine: NonBlank
    what_this_cannot_prove: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.before_explanation == self.after_explanation:
            raise ValueError("Teaching gain must state an actual explanation change")
        if self.knowledge_contribution.casefold() == (
                self.not_b1_restatement.casefold()):
            raise ValueError("Knowledge contribution cannot relabel B1 restatement")
        return self


class TeacherOutputRequest(Contract):
    schema_version: Literal[1] = 1
    teaching_id: Identifier
    previous_version_id: Identifier | None = None
    dossier_id: Identifier
    expected_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    source_m02_record_version_id: Identifier
    source_m09_record_version_id: Identifier
    source_m10_record_version_id: Identifier | None = None
    source_advisor_output_version_id: Identifier | None = None
    knowledge_question: KnowledgeQuestion
    proposition: KnowledgeProposition
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...] = ()
    concept_uses: tuple[ConceptUse, ...] = ()
    sections: tuple[TeachingSection, ...]
    process_steps: tuple[ProcessStep, ...]
    boundaries: tuple[TeachingBoundary, ...]
    transfers: tuple[TransferCheck, ...]
    demonstrations: tuple[TeachingDemonstration, ...] = ()
    terms: tuple[TermExplanation, ...] = ()
    gain: TeachingGain
    strength: TeachingStrength
    limitations: tuple[NonBlank, ...] = ()
    next_action: NonBlank
    execution_method: ExecutionMethod = ExecutionMethod.MANUAL
    model_admission_id: Identifier | None = None
    model_configuration_id: Identifier | None = None
    operation_request_version_id: Identifier | None = None
    model_domains: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("claim", self.claim_version_ids),
                ("evidence", self.evidence_version_ids),
                ("assessment", self.claim_evidence_assessment_version_ids),
                ("method", self.method_use_version_ids),
                ("limits", self.limitations),
                ("model domain", self.model_domains)):
            if not values and name in ("claim", "evidence", "assessment"):
                raise ValueError(f"Teacher output needs {name} versions")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate teacher {name}")
        if (self.source_m10_record_version_id is None) != (
                self.source_advisor_output_version_id is None):
            raise ValueError(
                "Optional B1 source needs both current M10 and Advisor output")
        section_ids = [item.section_id for item in self.sections]
        if (not self.sections or len(section_ids) != len(set(section_ids))
                or [item.ordinal for item in self.sections]
                != list(range(1, len(self.sections) + 1))):
            raise ValueError(
                "Teaching sections need unique IDs and continuous ordinals")
        section_by_id = {item.section_id: item for item in self.sections}
        required = {
            TeachingSectionKind.CASE_CONTEXT,
            TeachingSectionKind.NECESSARY_BASIS,
            TeachingSectionKind.PROCESS,
            TeachingSectionKind.BOUNDARY,
            TeachingSectionKind.TRANSFER,
            TeachingSectionKind.KNOWLEDGE_SUMMARY,
        }
        if not required <= {item.kind for item in self.sections}:
            raise ValueError(
                "Teaching needs context, basis, process, boundary, knowledge and transfer paragraphs")
        by_kind = {}
        for item in self.sections:
            by_kind.setdefault(item.kind, []).append(item)
        order = {
            kind: min(item.ordinal for item in by_kind[kind])
            for kind in required
        }
        if not (
                order[TeachingSectionKind.CASE_CONTEXT]
                < order[TeachingSectionKind.NECESSARY_BASIS]
                < order[TeachingSectionKind.PROCESS]
                < order[TeachingSectionKind.BOUNDARY]
                < order[TeachingSectionKind.KNOWLEDGE_SUMMARY]
                < order[TeachingSectionKind.TRANSFER]
        ):
            raise ValueError(
                "Teaching must move from case to basis, process, boundary, knowledge and transfer")
        if len(self.process_steps) < 2:
            raise ValueError("Teaching needs at least two connected process steps")
        if len({item.step_id for item in self.process_steps}) != len(
                self.process_steps):
            raise ValueError("Duplicate teaching process step ID")
        if [item.ordinal for item in self.process_steps] != list(
                range(1, len(self.process_steps) + 1)):
            raise ValueError("Process step ordinals must be continuous")
        if any(
                item.section_id not in section_by_id
                or section_by_id[item.section_id].kind
                is not TeachingSectionKind.PROCESS
                for item in self.process_steps):
            raise ValueError("Every process step needs an actual PROCESS paragraph")
        process_section_ids = {
            item.section_id for item in self.process_steps}
        if any(
                item.section_id not in process_section_ids
                for item in self.sections
                if item.kind is TeachingSectionKind.PROCESS):
            raise ValueError("Every PROCESS paragraph must contain a process step")
        if not self.boundaries or any(
                item.section_id not in section_by_id
                or section_by_id[item.section_id].kind not in (
                    TeachingSectionKind.BOUNDARY,
                    TeachingSectionKind.COUNTEREXAMPLE)
                for item in self.boundaries):
            raise ValueError(
                "Boundary record needs an actual BOUNDARY/COUNTEREXAMPLE paragraph")
        if len({item.boundary_id for item in self.boundaries}) != len(
                self.boundaries):
            raise ValueError("Duplicate teaching boundary ID")
        if not self.transfers or any(
                item.section_id not in section_by_id
                or section_by_id[item.section_id].kind
                is not TeachingSectionKind.TRANSFER
                for item in self.transfers):
            raise ValueError(
                "Transfer record needs an actual TRANSFER paragraph")
        if len({item.transfer_id for item in self.transfers}) != len(
                self.transfers):
            raise ValueError("Duplicate teaching transfer ID")
        demonstration_sections = {
            item.section_id for item in self.sections
            if item.kind in (
                TeachingSectionKind.EXAMPLE,
                TeachingSectionKind.CALCULATION)}
        demonstration_ids = [item.demonstration_id for item in self.demonstrations]
        if (len(demonstration_ids) != len(set(demonstration_ids))
                or {item.section_id for item in self.demonstrations}
                != demonstration_sections):
            raise ValueError(
                "Example/calculation paragraphs and demonstrations must match one-to-one")
        demonstrations_by_section = {
            item.section_id: item for item in self.demonstrations}
        for section in self.sections:
            if (section.kind is TeachingSectionKind.CALCULATION
                    and not demonstrations_by_section[
                        section.section_id].inputs_and_units):
                raise ValueError(
                    "Calculation demonstration needs values and units")
        if len({item.term.casefold() for item in self.terms}) != len(
                self.terms):
            raise ValueError("Duplicate explained professional term")
        if len({item.concept_version_id for item in self.concept_uses}) != len(
                self.concept_uses):
            raise ValueError("Duplicate teaching Concept version")
        if (self.proposition.proposition_type
                in (
                    KnowledgePropositionType.CONDITIONAL_MECHANISM,
                    KnowledgePropositionType.EMPIRICAL_PATTERN,
                )
                and not self.method_use_version_ids):
            raise ValueError(
                "Mechanism/pattern teaching needs an explicit MethodUse")
        if (self.proposition.proposition_type
                is KnowledgePropositionType.CONCEPT_DEFINITION
                and not self.concept_uses):
            raise ValueError(
                "Concept definition needs a current Concept version")
        if (self.strength in (
                TeachingStrength.PARTIAL_EXPLANATION,
                TeachingStrength.LIMITATION_OR_UNKNOWN)
                and not self.limitations):
            raise ValueError(
                "Partial/limitation teaching needs explicit limitations")
        plain_ordinals = {
            item.section_id: item.ordinal for item in self.sections}
        for term in self.terms:
            if (term.plain_explanation_section_id not in plain_ordinals
                    or term.named_in_section_id not in plain_ordinals
                    or plain_ordinals[term.plain_explanation_section_id]
                    > plain_ordinals[term.named_in_section_id]):
                raise ValueError(
                    "Professional term must be named after its plain-language explanation")
            plain_section = section_by_id[term.plain_explanation_section_id]
            if plain_section.kind not in (
                    TeachingSectionKind.NECESSARY_BASIS,
                    TeachingSectionKind.PROCESS):
                raise ValueError(
                    "Professional term needs a basis or process explanation first")
        for concept in self.concept_uses:
            if (concept.reuse_mode is ConceptReuseMode.NECESSARY_RECAP
                    and not any(
                        item.kind is TeachingSectionKind.RECAP
                        and concept.concept_version_id
                        in item.concept_version_ids
                        for item in self.sections)):
                raise ValueError(
                    "Necessary concept recap needs an actual RECAP paragraph")
        if self.execution_method is ExecutionMethod.ADMITTED_MODEL:
            if not all((self.model_admission_id, self.model_configuration_id,
                        self.operation_request_version_id, self.model_domains)):
                raise ValueError(
                    "Admitted teacher needs admission, config and actual operation")
        elif any((self.model_admission_id, self.model_configuration_id,
                  self.operation_request_version_id)) or self.model_domains:
            raise ValueError(
                "Manual teacher cannot carry model execution identity")
        return self


class TeacherOutput(Contract):
    schema_version: Literal[1] = 1
    teaching_id: Identifier
    teacher_output_version_id: Identifier
    previous_version_id: Identifier | None
    dossier_id: Identifier
    previous_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    source_m02_record_version_id: Identifier
    source_m09_record_version_id: Identifier
    source_m10_record_version_id: Identifier | None
    source_advisor_output_version_id: Identifier | None
    knowledge_question: KnowledgeQuestion
    proposition: KnowledgeProposition
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...]
    concept_uses: tuple[ConceptUse, ...]
    sections: tuple[TeachingSection, ...]
    process_steps: tuple[ProcessStep, ...]
    boundaries: tuple[TeachingBoundary, ...]
    transfers: tuple[TransferCheck, ...]
    demonstrations: tuple[TeachingDemonstration, ...]
    terms: tuple[TermExplanation, ...]
    gain: TeachingGain
    strength: TeachingStrength
    limitations: tuple[NonBlank, ...]
    next_action: NonBlank
    execution_method: ExecutionMethod
    model_admission_id: Identifier | None
    model_configuration_id: Identifier | None
    operation_request_version_id: Identifier | None
    model_domains: tuple[NonBlank, ...]
    role: Literal["B2"] = "B2"
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    reader_mastery_measured: Literal[False] = False
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime


class TeacherResult(Contract):
    teacher_output_version_id: Identifier
    m11_step_record_version_id: Identifier
    dossier_snapshot_version_id: Identifier


class TeacherError(ArchiveError):
    """Teacher/teaching boundary failure, never learning or publication proof."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


class TeacherController:
    def __init__(self, archive: Archive, rights: RightsGrant,
                 workflow: ResearchWorkflowController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("TeacherController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("TeacherController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.workflow = workflow or ResearchWorkflowController(archive, rights)
        self.research = ResearchRevisionController(archive, rights)
        self.evidence = EvidenceController(archive, rights)
        self.advisors = AdvisorController(archive, rights, self.workflow)
        self.model_admission = ModelAdmissionController(archive, rights)

    @staticmethod
    def _require_current(stored: StoredVersion, latest: StoredVersion | None,
                         label: str) -> None:
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise TeacherError(f"Teacher {label} is not the current version")

    def _validate_basis(self, request: TeacherOutputRequest,
                        revision) -> None:
        revision_inputs = set(revision.input_version_ids)
        for claim_id in request.claim_version_ids:
            claim_stored = self.archive.get(claim_id)
            claim = self.evidence.load_claim(claim_id)
            if claim_stored.body_retention_revoked:
                raise TeacherError("Teaching references a withdrawn Claim")
            if (claim.theme_id != request.theme_id
                    or claim.spec_sha256 != request.spec_sha256):
                raise TeacherError(
                    "Teaching Claim crosses the dossier theme or specification")
            if claim_id not in revision_inputs:
                raise TeacherError(
                    "Teaching Claim is outside the exact research revision")
            self._require_current(
                claim_stored,
                self.archive.latest(claim_stored.submission.object_id),
                "Claim")
        revision_evidence = set(revision.evidence_version_ids)
        for evidence_id in request.evidence_version_ids:
            evidence_stored = self.archive.get(evidence_id)
            evidence = self.evidence.load_evidence(evidence_id)
            if evidence_stored.body_retention_revoked:
                raise TeacherError("Teaching references withdrawn Evidence")
            if (evidence.theme_id != request.theme_id
                    or evidence.spec_sha256 != request.spec_sha256):
                raise TeacherError(
                    "Teaching Evidence crosses the dossier theme or specification")
            if (evidence_id not in revision_inputs
                    or evidence_id not in revision_evidence):
                raise TeacherError(
                    "Teaching Evidence is outside the exact research revision")
            self._require_current(
                evidence_stored,
                self.archive.latest(evidence_stored.submission.object_id),
                "Evidence")
        assessments = []
        for assessment_id in request.claim_evidence_assessment_version_ids:
            assessment_stored = self.archive.get(assessment_id)
            assessment = self.evidence.load_assessment(assessment_id)
            if assessment_stored.body_retention_revoked:
                raise TeacherError(
                    "Teaching references a withdrawn W25 assessment")
            if (assessment.theme_id != request.theme_id
                    or assessment.spec_sha256 != request.spec_sha256):
                raise TeacherError(
                    "Teaching W25 assessment crosses theme or specification")
            if assessment_id not in revision_inputs:
                raise TeacherError(
                    "Teaching W25 assessment is outside the exact research revision")
            self._require_current(
                assessment_stored,
                self.archive.latest(assessment_stored.submission.object_id),
                "W25 assessment")
            assessments.append(assessment)
        if {item.claim_version_id for item in assessments} != set(
                request.claim_version_ids):
            raise TeacherError(
                "W25 assessments must cover exactly the taught Claims")
        assessed_evidence = {
            evidence_id
            for assessment in assessments
            for evidence_id in assessment.evidence_version_ids
        }
        if assessed_evidence != set(request.evidence_version_ids):
            raise TeacherError(
                "Taught Evidence must match the exact assessed Evidence set")
        if any(
                item.relation in {
                    EvidenceRelation.IRRELEVANT,
                    EvidenceRelation.BACKGROUND_ONLY,
                }
                for item in assessments):
            raise TeacherError(
                "Irrelevant/background-only Evidence cannot ground B2 teaching")
        if (request.strength is TeachingStrength.BOUNDED_EXPLANATION
                and not any(item.relation is EvidenceRelation.SUPPORTS
                            for item in assessments)):
            raise TeacherError(
                "Bounded teaching needs at least one supported Claim")

        claim_ids = set(request.claim_version_ids)
        evidence_ids = set(request.evidence_version_ids)
        method_ids = set(request.method_use_version_ids)
        concept_ids = {
            item.concept_version_id for item in request.concept_uses}
        section_claim_ids = {
            item for section in request.sections
            for item in section.claim_version_ids}
        section_evidence_ids = {
            item for section in request.sections
            for item in section.evidence_version_ids}
        section_method_ids = {
            item for section in request.sections
            for item in section.method_use_version_ids}
        section_concept_ids = {
            item for section in request.sections
            for item in section.concept_version_ids}
        process_evidence_ids = {
            item for step in request.process_steps
            for item in step.evidence_version_ids}
        if section_claim_ids != claim_ids:
            raise TeacherError(
                "Teaching paragraphs must use exactly the declared Claims")
        if section_evidence_ids != evidence_ids:
            raise TeacherError(
                "Teaching paragraphs must use exactly the declared Evidence")
        if section_method_ids != method_ids:
            raise TeacherError(
                "Teaching paragraphs must use exactly the declared MethodUse")
        if section_concept_ids != concept_ids:
            raise TeacherError(
                "Teaching paragraphs must use exactly the declared Concepts")
        if not process_evidence_ids <= evidence_ids:
            raise TeacherError(
                "Process step uses Evidence outside the teaching basis")
        sections_by_id = {
            item.section_id: item for item in request.sections}
        if any(
                not set(step.evidence_version_ids)
                <= set(sections_by_id[step.section_id].evidence_version_ids)
                for step in request.process_steps):
            raise TeacherError(
                "Process step Evidence is not bound by its PROCESS paragraph")

        active_methods = set(request.method_use_version_ids)
        snapshot_methods = set(
            self.workflow.current_snapshot(request.dossier_id)[1]
            .method_use_version_ids)
        if not active_methods <= snapshot_methods:
            raise TeacherError(
                "Teaching MethodUse is outside the current dossier")
        for method_id in request.method_use_version_ids:
            method = self.workflow.load_method(method_id)
            if (method.theme_id != request.theme_id
                    or method.spec_sha256 != request.spec_sha256):
                raise TeacherError(
                    "Teaching MethodUse crosses the dossier theme or specification")

        for concept in request.concept_uses:
            stored = self.archive.get(concept.concept_version_id)
            if stored.submission.kind is not ObjectKind.CONCEPT:
                raise TeacherError("Concept link is not an archived Concept")
            if stored.body_retention_revoked:
                raise TeacherError("Teaching references a withdrawn Concept")
            if stored.submission.spec_sha256 != request.spec_sha256:
                raise TeacherError(
                    "Teaching Concept uses another specification")
            if concept.concept_version_id not in revision_inputs:
                raise TeacherError(
                    "Teaching Concept is outside the exact research revision")
            self._require_current(
                stored, self.archive.latest(stored.submission.object_id),
                "Concept")

    def _validate_advisor_source(self, request: TeacherOutputRequest,
                                 snapshot) -> None:
        if request.source_advisor_output_version_id is None:
            return
        active = {item.step: item for item in snapshot.active_steps}
        m10 = active.get(ResearchStep.M10)
        if (m10 is None
                or m10.record_version_id
                != request.source_m10_record_version_id):
            raise TeacherError(
                "Optional B1 source is not the current active M10")
        record = self.workflow.load_step_record(m10.record_version_id)
        if (record.step is not ResearchStep.M10
                or record.disposition not in (
                    StepDisposition.READY_FOR_NEXT,
                    StepDisposition.CANDIDATE,
                    StepDisposition.LIMITED)
                or record.artifact_version_ids != (
                    request.source_advisor_output_version_id,)):
            raise TeacherError(
                "Current M10 does not bind the declared B1 output")
        advisor = self.advisors.load_advisor(
            request.source_advisor_output_version_id)
        if (advisor.dossier_id != request.dossier_id
                or advisor.revision_id != request.revision_id
                or advisor.theme_id != request.theme_id
                or advisor.spec_sha256 != request.spec_sha256):
            raise TeacherError("Optional B1 output crosses the teaching basis")
        if request.gain.not_b1_restatement.casefold() in {
                advisor.gain.case_specific_gain.casefold(),
                advisor.gain.journal_contribution.casefold()}:
            raise TeacherError(
                "B2 knowledge gain cannot relabel the selected B1 contribution")

    def _validate_model_execution(self, request: TeacherOutputRequest) -> None:
        if request.execution_method is ExecutionMethod.MANUAL:
            return
        if not self.model_admission.authorizes(
                request.model_admission_id,
                configuration_id=request.model_configuration_id,
                duty=ModelDuty.TEACHER, domains=request.model_domains,
                require_given_material=True, at=request.created_at):
            raise TeacherError(
                "Teacher execution is outside a current admitted task scope")
        operation = self.archive.get(request.operation_request_version_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise TeacherError(
                "Teacher execution has no actual OperationRequest")
        operation_body = OperationRequest.model_validate_json(
            self.archive.read_body(request.operation_request_version_id))
        if operation_body.kind is not OperationKind.MODEL:
            raise TeacherError(
                "Teacher execution request is not a model operation")
        if operation_body.step_id != "M11":
            raise TeacherError(
                "Teacher model operation is not the M11 task")
        if operation_body.material_use is not MaterialUse.MODEL_PROCESS:
            raise TeacherError(
                "Teacher model operation lacks model-processing authority")
        configuration = self.model_admission.load_configuration(
            request.model_configuration_id)
        if (operation_body.spec_sha256 != request.spec_sha256
                or operation_body.configuration_sha256
                != configuration.configuration_sha256):
            raise TeacherError(
                "Teacher operation and configuration differ")
        required_inputs = {
            request.revision_id,
            request.source_m02_record_version_id,
            request.source_m09_record_version_id,
            *request.claim_version_ids,
            *request.evidence_version_ids,
            *request.claim_evidence_assessment_version_ids,
            *request.method_use_version_ids,
            *(
                item.concept_version_id
                for item in request.concept_uses),
        }
        if request.source_m10_record_version_id is not None:
            required_inputs.update({
                request.source_m10_record_version_id,
                request.source_advisor_output_version_id,
            })
        if not required_inputs <= set(operation_body.input_version_ids):
            raise TeacherError(
                "Teacher operation does not bind every teaching input")
        receipt = OperationJournal(self.archive, self.rights).receipt(
            request.operation_request_version_id)
        if receipt is None or receipt.status is not OperationStatus.SUCCEEDED:
            raise TeacherError(
                "Teacher execution has no successful operation receipt")
        if (request.created_at < receipt.ended_at
                or request.created_at < receipt.recorded_at
                or operation_body.created_at > receipt.started_at):
            raise TeacherError(
                "Teacher output predates its actual model operation")

    def record_teacher(self, request: TeacherOutputRequest) -> TeacherResult:
        if not isinstance(request, TeacherOutputRequest):
            raise TypeError("record_teacher requires TeacherOutputRequest")
        request = TeacherOutputRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        content_hash = _digest(request.model_dump(mode="json"))
        teacher_version_id = _version("TEACHER-OUTPUT-", canonical([
            request.teaching_id, request.previous_version_id, content_hash]))
        object_id = _object("TEACHER-OBJECT-", request.teaching_id)
        output = TeacherOutput(
            teaching_id=request.teaching_id,
            teacher_output_version_id=teacher_version_id,
            previous_version_id=request.previous_version_id,
            dossier_id=request.dossier_id,
            previous_snapshot_version_id=request.expected_snapshot_version_id,
            revision_id=request.revision_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            source_m02_record_version_id=request.source_m02_record_version_id,
            source_m09_record_version_id=request.source_m09_record_version_id,
            source_m10_record_version_id=request.source_m10_record_version_id,
            source_advisor_output_version_id=(
                request.source_advisor_output_version_id),
            knowledge_question=request.knowledge_question,
            proposition=request.proposition,
            claim_version_ids=request.claim_version_ids,
            evidence_version_ids=request.evidence_version_ids,
            claim_evidence_assessment_version_ids=(
                request.claim_evidence_assessment_version_ids),
            method_use_version_ids=request.method_use_version_ids,
            concept_uses=request.concept_uses, sections=request.sections,
            process_steps=request.process_steps,
            boundaries=request.boundaries, transfers=request.transfers,
            demonstrations=request.demonstrations,
            terms=request.terms, gain=request.gain,
            strength=request.strength, limitations=request.limitations,
            next_action=request.next_action,
            execution_method=request.execution_method,
            model_admission_id=request.model_admission_id,
            model_configuration_id=request.model_configuration_id,
            operation_request_version_id=request.operation_request_version_id,
            model_domains=request.model_domains,
            created_at=request.created_at)
        snapshot_stored, snapshot = self.workflow.current_snapshot(
            request.dossier_id)
        if (snapshot.theme_id != request.theme_id
                or snapshot.spec_sha256 != request.spec_sha256
                or snapshot.revision_id != request.revision_id):
            raise TeacherError("Teacher task and dossier identity differ")
        revision = self.research.load_revision(request.revision_id)
        current_revision = self.research.current_revision(request.theme_id)
        if (current_revision is None
                or current_revision.revision_id != revision.revision_id):
            raise TeacherError("Teacher task revision is stale")
        active = {item.step: item for item in snapshot.active_steps}
        m02 = active.get(ResearchStep.M02)
        if (m02 is None
                or m02.record_version_id
                != request.source_m02_record_version_id):
            raise TeacherError(
                "Teaching needs the current active M02 record")
        m02_record = self.workflow.load_step_record(m02.record_version_id)
        if (m02_record.step is not ResearchStep.M02
                or m02_record.dossier_id != request.dossier_id
                or m02_record.revision_id != request.revision_id
                or m02_record.spec_sha256 != request.spec_sha256
                or m02_record.disposition not in (
                    StepDisposition.READY_FOR_NEXT,
                    StepDisposition.LIMITED)):
            raise TeacherError(
                "Teaching M02 record is not usable for this exact revision")
        b2_questions = {
            item.question for item in m02_record.participant_questions
            if item.participant is Participant.B2}
        if request.knowledge_question.early_question not in b2_questions:
            raise TeacherError(
                "Teaching question does not descend from the actual M02 B2 question")
        m09 = active.get(ResearchStep.M09)
        if (m09 is None
                or m09.record_version_id
                != request.source_m09_record_version_id):
            raise TeacherError(
                "Teaching needs the current active M09 record")
        m09_record = self.workflow.load_step_record(m09.record_version_id)
        if (m09_record.step is not ResearchStep.M09
                or m09_record.dossier_id != request.dossier_id
                or m09_record.revision_id != request.revision_id
                or m09_record.spec_sha256 != request.spec_sha256
                or m09_record.disposition not in (
                    StepDisposition.READY_FOR_NEXT,
                    StepDisposition.LIMITED)):
            raise TeacherError(
                "Teaching needs a ready M09 record")
        self._validate_basis(request, revision)
        self._validate_advisor_source(request, snapshot)
        self._validate_model_execution(request)
        expected_body_sha256 = _digest(
            canonical(output.model_dump(mode="json")).encode())
        active_m11 = active.get(ResearchStep.M11)
        if active_m11 is not None:
            record = self.workflow.load_step_record(
                active_m11.record_version_id)
            if teacher_version_id in record.artifact_version_ids:
                latest_output = self.archive.latest(object_id)
                if (latest_output is None
                        or latest_output.submission.version_id
                        != teacher_version_id
                        or record.artifact_version_ids != (
                            teacher_version_id,)):
                    raise TeacherError(
                        "Current M11 does not bind the latest exact Teacher output")
                if (record.previous_snapshot_version_id
                        != request.expected_snapshot_version_id):
                    raise TeacherError(
                        "Current M11 does not descend from the requested Teacher snapshot")
                return TeacherResult(
                    teacher_output_version_id=teacher_version_id,
                    m11_step_record_version_id=active_m11.record_version_id,
                    dossier_snapshot_version_id=(
                        snapshot_stored.submission.version_id))
        if snapshot_stored.submission.version_id != request.expected_snapshot_version_id:
            raise WorkflowError("Teacher task uses a stale dossier snapshot")
        try:
            existing = self.archive.get(teacher_version_id)
            if (existing.submission.kind is not ObjectKind.TEACHER_OUTPUT
                    or existing.body_sha256 != expected_body_sha256):
                raise TeacherError(
                    "Teacher output version ID is already in use")
        except MissingVersion:
            latest = self.archive.latest(object_id)
            if request.previous_version_id is None:
                if latest is not None:
                    raise TeacherError(
                        "Teacher output history requires previous version")
            elif (latest is None
                  or latest.submission.version_id
                  != request.previous_version_id):
                raise TeacherError(
                    "Teacher output previous version is not current")
            refs = [
                VersionReference(
                    target_version_id=request.expected_snapshot_version_id,
                    use=ReferenceUse.BASIS,
                    locator="exact dossier snapshot"),
                VersionReference(
                    target_version_id=request.revision_id,
                    use=ReferenceUse.BASIS,
                    locator="exact research revision"),
                VersionReference(
                    target_version_id=request.source_m02_record_version_id,
                    use=ReferenceUse.BASIS,
                    locator="early B2 question"),
                VersionReference(
                    target_version_id=request.source_m09_record_version_id,
                    use=ReferenceUse.BASIS,
                    locator="ready M09 research"),
                *(
                    VersionReference(
                        target_version_id=claim_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"teaching claim {index}")
                    for index, claim_id in enumerate(
                        request.claim_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=evidence_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"teaching evidence {index}")
                    for index, evidence_id in enumerate(
                        request.evidence_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=assessment_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"teaching assessment {index}")
                    for index, assessment_id in enumerate(
                        request.claim_evidence_assessment_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=method_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"teaching method {index}")
                    for index, method_id in enumerate(
                        request.method_use_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=item.concept_version_id,
                        use=ReferenceUse.BACKGROUND,
                        locator=f"concept link {index}")
                    for index, item in enumerate(request.concept_uses)
                ),
            ]
            if request.source_advisor_output_version_id is not None:
                refs.extend((
                    VersionReference(
                        target_version_id=request.source_m10_record_version_id,
                        use=ReferenceUse.SUPPORT,
                        locator="optional B1 M10"),
                    VersionReference(
                        target_version_id=request.source_advisor_output_version_id,
                        use=ReferenceUse.BACKGROUND,
                        locator="optional B1 research"),
                ))
            if request.operation_request_version_id is not None:
                refs.append(VersionReference(
                    target_version_id=request.operation_request_version_id,
                    use=ReferenceUse.SUPPORT,
                    locator="actual teacher operation"))
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=teacher_version_id,
                parent_version_id=request.previous_version_id,
                kind=ObjectKind.TEACHER_OUTPUT,
                title=f"B2 teacher output {request.teaching_id}",
                spec_sha256=request.spec_sha256,
                created_at=request.created_at,
                source_times=SourceTimes(), rights=self.rights,
                representation=Representation.FULL_BODY,
                references=tuple(refs))
            expected = {
                object_id: latest.submission.version_id if latest else None,
                snapshot_stored.submission.object_id:
                    snapshot_stored.submission.version_id,
                self.research._revision_object(request.theme_id):
                    request.revision_id,
            }
            version_ids = [
                request.source_m02_record_version_id,
                request.source_m09_record_version_id,
                *request.claim_version_ids,
                *request.evidence_version_ids,
                *request.claim_evidence_assessment_version_ids,
                *request.method_use_version_ids,
                *(item.concept_version_id for item in request.concept_uses),
            ]
            if request.source_m10_record_version_id is not None:
                version_ids.extend((
                    request.source_m10_record_version_id,
                    request.source_advisor_output_version_id,
                ))
            for version_id in version_ids:
                stored = self.archive.get(version_id)
                expected[stored.submission.object_id] = stored.submission.version_id
            try:
                self.archive.append(
                    submission,
                    canonical(output.model_dump(mode="json")).encode(),
                    expected_current=expected)
            except Conflict:
                concurrent = self.archive.get(teacher_version_id)
                if (concurrent.submission.kind is not ObjectKind.TEACHER_OUTPUT
                        or concurrent.body_sha256 != expected_body_sha256):
                    raise
        existing = self.archive.get(teacher_version_id)
        if (existing.submission.kind is not ObjectKind.TEACHER_OUTPUT
                or existing.body_sha256 != expected_body_sha256):
            raise TeacherError(
                "Teacher output append was not recoverable")
        disposition = (
            StepDisposition.READY_FOR_NEXT
            if request.strength is TeachingStrength.BOUNDED_EXPLANATION
            else StepDisposition.LIMITED)
        previous_m11 = None
        for record_id in reversed(snapshot.record_history_version_ids):
            record = self.workflow.load_step_record(record_id)
            if record.step is ResearchStep.M11:
                previous_m11 = record.step_record_version_id
                break
        try:
            snapshot_result = self.workflow.submit_step(ResearchStepSubmission(
                step_record_id="TEACHER-M11-" + _digest([
                    teacher_version_id,
                    request.expected_snapshot_version_id])[:32],
                previous_step_record_version_id=previous_m11,
                dossier_id=request.dossier_id,
                expected_snapshot_version_id=(
                    request.expected_snapshot_version_id),
                theme_id=request.theme_id,
                spec_sha256=request.spec_sha256,
                revision_id=request.revision_id,
                step=ResearchStep.M11, owner=StepOwner.TEACHER,
                disposition=disposition,
                artifact_version_ids=(teacher_version_id,),
                method_use_version_ids=request.method_use_version_ids,
                limitations=request.limitations,
                next_action=request.next_action,
                execution_method=request.execution_method,
                model_admission_id=request.model_admission_id,
                model_configuration_id=request.model_configuration_id,
                operation_request_version_id=(
                    request.operation_request_version_id),
                model_domains=request.model_domains,
                created_at=request.created_at))
        except (ArchiveError, ValueError) as exc:
            raise TeacherError(
                "Teacher output is recorded as an unadopted attempt; exact retry "
                "on this same dossier basis resumes M11, while a changed basis "
                "requires a new Teacher request") from exc
        return TeacherResult(
            teacher_output_version_id=teacher_version_id,
            m11_step_record_version_id=next(
                item.record_version_id
                for item in self.workflow.load_snapshot(
                    snapshot_result.submission.version_id).active_steps
                if item.step is ResearchStep.M11),
            dossier_snapshot_version_id=(
                snapshot_result.submission.version_id))

    def load_teacher(self, teacher_version_id: str) -> TeacherOutput:
        stored = self.archive.get(teacher_version_id)
        if stored.submission.kind is not ObjectKind.TEACHER_OUTPUT:
            raise TeacherError("Requested version is not a TeacherOutput")
        output = TeacherOutput.model_validate_json(
            self.archive.read_body(teacher_version_id))
        if (output.teacher_output_version_id != teacher_version_id
                or stored.submission.spec_sha256 != output.spec_sha256
                or stored.submission.created_at != output.created_at):
            raise TeacherError("Teacher output identity mismatch")
        return output
