"""W30 conditional paths, prospective tests and bounded M12 closure.

The record joins current B1/M10 and B2/M11 outputs to one exact research basis.
It stores conditional pathways and falsifiable review conditions before future
outcomes are known. It is not a forecast fact, probability estimate, content
PASS, independent Review or publication authorization.
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
from .teacher import TeacherController
from .workflow import (ExecutionMethod, ResearchClosure, ResearchStep,
                       ResearchStepSubmission, ResearchWorkflowController,
                       StepDisposition, StepOwner, WorkflowError)


class ProspectiveMode(str, Enum):
    MULTI_PATH = "MULTI_PATH"
    SINGLE_LIMITED = "SINGLE_LIMITED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReviewWindow(Contract):
    start: AwareDatetime
    end: AwareDatetime
    source_timezone: NonBlank
    rationale: NonBlank

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("Review window must end after it starts")
        return self


class OriginalJudgmentReference(Contract):
    exact_judgment: NonBlank
    supported_scope: NonBlank
    knowledge_cutoff: AwareDatetime


class TeachingReference(Contract):
    exact_proposition: NonBlank
    teaching_boundary: NonBlank


class ConditionalPathStep(Contract):
    step_id: Identifier
    ordinal: int = Field(ge=1)
    actor_or_system: NonBlank
    authority_or_resource: NonBlank
    decision_or_transfer: NonBlank
    precondition: NonBlank
    resulting_state: NonBlank
    minimum_lag: NonBlank
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...] = ()
    uncertainty: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("claim", self.claim_version_ids),
                ("evidence", self.evidence_version_ids),
                ("method", self.method_use_version_ids)):
            if not values and name in ("claim", "evidence"):
                raise ValueError(
                    f"Conditional path step needs exact {name} versions")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate path step {name}")
        return self


class ConditionalPath(Contract):
    path_id: Identifier
    branch_condition: NonBlank
    first_distinguishing_observation: NonBlank
    steps: tuple[ConditionalPathStep, ...]
    beneficiaries: tuple[NonBlank, ...]
    cost_bearers: tuple[NonBlank, ...]
    feedback_conditions: tuple[NonBlank, ...]
    failure_or_exit_conditions: tuple[NonBlank, ...]
    not_established_fact: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.steps) < 2 or [item.ordinal for item in self.steps] != list(
                range(1, len(self.steps) + 1)):
            raise ValueError(
                "Conditional path needs at least two ordered transmission steps")
        if len({item.step_id for item in self.steps}) != len(self.steps):
            raise ValueError("Duplicate conditional path step ID")
        for name, values in (
                ("beneficiary", self.beneficiaries),
                ("cost bearer", self.cost_bearers),
                ("feedback condition", self.feedback_conditions),
                ("failure/exit condition", self.failure_or_exit_conditions)):
            if (not values or len(values) != len(set(values))):
                raise ValueError(
                    f"Conditional path needs unique explicit {name}s")
        return self


class AmbiguityAssessment(Contract):
    missing_information: NonBlank
    cannot_distinguish_because: NonBlank
    next_discriminating_observations: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.next_discriminating_observations
                or len(self.next_discriminating_observations)
                != len(set(self.next_discriminating_observations))):
            raise ValueError(
                "Ambiguity assessment needs unique next discriminating observations")
        return self


class EvaluationCondition(Contract):
    supports_if: tuple[NonBlank, ...]
    weakens_if: tuple[NonBlank, ...]
    overturns_if: tuple[NonBlank, ...]
    mechanism_checks: tuple[NonBlank, ...]
    alternative_explanation_checks: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("support", self.supports_if),
                ("weakening", self.weakens_if),
                ("overturning", self.overturns_if),
                ("mechanism check", self.mechanism_checks),
                ("alternative check", self.alternative_explanation_checks)):
            if (not values or len(values) != len(set(values))):
                raise ValueError(
                    f"Evaluation condition needs unique explicit {name} items")
        return self


class OpenQuestion(Contract):
    question_id: Identifier
    question: NonBlank
    why_open: NonBlank
    evidence_that_would_narrow_it: NonBlank


class ProspectiveRequest(Contract):
    schema_version: Literal[1] = 1
    prospective_id: Identifier
    previous_version_id: Identifier | None = None
    dossier_id: Identifier
    expected_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    source_m10_record_version_id: Identifier
    source_m11_record_version_id: Identifier
    source_advisor_output_version_id: Identifier
    source_teacher_output_version_id: Identifier
    original_judgment: OriginalJudgmentReference
    teaching: TeachingReference
    mode: ProspectiveMode
    mode_reason: NonBlank
    paths: tuple[ConditionalPath, ...] = ()
    ambiguity: AmbiguityAssessment
    evaluation: EvaluationCondition
    review_window: ReviewWindow
    future_review_owner: Literal["W39", "W40"]
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...] = ()
    open_questions: tuple[OpenQuestion, ...] = ()
    closure: ResearchClosure
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
                ("limitation", self.limitations),
                ("open question", [item.question_id for item in self.open_questions]),
                ("model domain", self.model_domains)):
            if not values and name in ("claim", "evidence", "assessment"):
                raise ValueError(f"Prospective record needs {name} versions")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate prospective {name}")
        if self.original_judgment.knowledge_cutoff > self.created_at:
            raise ValueError(
                "Conditional record cannot predate its original knowledge cutoff")
        path_ids = [item.path_id for item in self.paths]
        if len(path_ids) != len(set(path_ids)):
            raise ValueError("Duplicate conditional path ID")
        if self.mode is ProspectiveMode.MULTI_PATH:
            if len(self.paths) < 2:
                raise ValueError(
                    "Multi-path mode needs at least two substantively different paths")
            if (len({item.branch_condition for item in self.paths}) != len(
                    self.paths)
                    or len({
                        item.first_distinguishing_observation
                        for item in self.paths}) != len(self.paths)):
                raise ValueError(
                    "Each path needs a distinct branch condition and first observation")
        elif self.mode is ProspectiveMode.SINGLE_LIMITED:
            if len(self.paths) != 1:
                raise ValueError(
                    "Single-limited mode needs exactly one bounded path")
        elif self.paths:
            raise ValueError(
                "Not-applicable mode cannot invent conditional paths")
        step_ids = [
            step.step_id for path in self.paths for step in path.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Path step IDs must be unique across paths")
        path_claim_ids = {
            item for path in self.paths for step in path.steps
            for item in step.claim_version_ids}
        path_evidence_ids = {
            item for path in self.paths for step in path.steps
            for item in step.evidence_version_ids}
        path_method_ids = {
            item for path in self.paths for step in path.steps
            for item in step.method_use_version_ids}
        if self.mode is not ProspectiveMode.NOT_APPLICABLE:
            if path_claim_ids != set(self.claim_version_ids):
                raise ValueError(
                    "Conditional paths must use exactly the declared Claims")
            if path_evidence_ids != set(self.evidence_version_ids):
                raise ValueError(
                    "Conditional paths must use exactly the declared Evidence")
            if path_method_ids != set(self.method_use_version_ids):
                raise ValueError(
                    "Conditional paths must use exactly the declared MethodUse")
        elif path_method_ids:
            raise ValueError(
                "Not-applicable mode cannot carry path-only MethodUse")
        if self.mode is not ProspectiveMode.MULTI_PATH and not self.limitations:
            raise ValueError(
                "Single/not-applicable mode needs explicit limitations")
        if self.execution_method is ExecutionMethod.ADMITTED_MODEL:
            if not all((self.model_admission_id, self.model_configuration_id,
                        self.operation_request_version_id, self.model_domains)):
                raise ValueError(
                    "Admitted C record needs admission, config and actual operation")
        elif any((self.model_admission_id, self.model_configuration_id,
                  self.operation_request_version_id)) or self.model_domains:
            raise ValueError(
                "Manual C record cannot carry model execution identity")
        return self


class ProspectiveOutput(Contract):
    schema_version: Literal[1] = 1
    prospective_id: Identifier
    prospective_output_version_id: Identifier
    previous_version_id: Identifier | None
    dossier_id: Identifier
    previous_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    source_m10_record_version_id: Identifier
    source_m11_record_version_id: Identifier
    source_advisor_output_version_id: Identifier
    source_teacher_output_version_id: Identifier
    original_judgment: OriginalJudgmentReference
    teaching: TeachingReference
    mode: ProspectiveMode
    mode_reason: NonBlank
    paths: tuple[ConditionalPath, ...]
    ambiguity: AmbiguityAssessment
    evaluation: EvaluationCondition
    review_window: ReviewWindow
    future_review_owner: Literal["W39", "W40"]
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...]
    open_questions: tuple[OpenQuestion, ...]
    closure: ResearchClosure
    limitations: tuple[NonBlank, ...]
    next_action: NonBlank
    execution_method: ExecutionMethod
    model_admission_id: Identifier | None
    model_configuration_id: Identifier | None
    operation_request_version_id: Identifier | None
    model_domains: tuple[NonBlank, ...]
    role: Literal["C"] = "C"
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    forecast_is_fact: Literal[False] = False
    observed_outcome_claimed: Literal[False] = False
    reader_answers_collected: Literal[False] = False
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    thesis_storage_target: Literal["W33"] = "W33"
    created_at: AwareDatetime


class ProspectiveResult(Contract):
    prospective_output_version_id: Identifier
    m12_step_record_version_id: Identifier
    dossier_snapshot_version_id: Identifier


class ProspectiveError(ArchiveError):
    """Conditional-path/review-boundary failure, never a forecast or PASS."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


class ProspectiveController:
    def __init__(self, archive: Archive, rights: RightsGrant,
                 workflow: ResearchWorkflowController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("ProspectiveController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("ProspectiveController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.workflow = workflow or ResearchWorkflowController(archive, rights)
        self.research = ResearchRevisionController(archive, rights)
        self.evidence = EvidenceController(archive, rights)
        self.advisors = AdvisorController(archive, rights, self.workflow)
        self.teachers = TeacherController(archive, rights, self.workflow)
        self.model_admission = ModelAdmissionController(archive, rights)

    @staticmethod
    def _require_current(stored: StoredVersion, latest: StoredVersion | None,
                         label: str) -> None:
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise ProspectiveError(
                f"Prospective {label} is not the current version")

    def _validate_basis(self, request: ProspectiveRequest,
                        revision) -> None:
        revision_inputs = set(revision.input_version_ids)
        for claim_id in request.claim_version_ids:
            stored = self.archive.get(claim_id)
            claim = self.evidence.load_claim(claim_id)
            if stored.body_retention_revoked:
                raise ProspectiveError(
                    "Conditional record references a withdrawn Claim")
            if (claim.theme_id != request.theme_id
                    or claim.spec_sha256 != request.spec_sha256):
                raise ProspectiveError(
                    "Conditional Claim crosses the dossier theme or specification")
            if claim_id not in revision_inputs:
                raise ProspectiveError(
                    "Conditional Claim is outside the exact research revision")
            self._require_current(
                stored, self.archive.latest(stored.submission.object_id),
                "Claim")
        revision_evidence = set(revision.evidence_version_ids)
        for evidence_id in request.evidence_version_ids:
            stored = self.archive.get(evidence_id)
            evidence = self.evidence.load_evidence(evidence_id)
            if stored.body_retention_revoked:
                raise ProspectiveError(
                    "Conditional record references withdrawn Evidence")
            if (evidence.theme_id != request.theme_id
                    or evidence.spec_sha256 != request.spec_sha256):
                raise ProspectiveError(
                    "Conditional Evidence crosses the dossier theme or specification")
            if (evidence_id not in revision_inputs
                    or evidence_id not in revision_evidence):
                raise ProspectiveError(
                    "Conditional Evidence is outside the exact research revision")
            self._require_current(
                stored, self.archive.latest(stored.submission.object_id),
                "Evidence")
        assessments = []
        for assessment_id in request.claim_evidence_assessment_version_ids:
            stored = self.archive.get(assessment_id)
            assessment = self.evidence.load_assessment(assessment_id)
            if stored.body_retention_revoked:
                raise ProspectiveError(
                    "Conditional record references a withdrawn W25 assessment")
            if (assessment.theme_id != request.theme_id
                    or assessment.spec_sha256 != request.spec_sha256):
                raise ProspectiveError(
                    "Conditional W25 assessment crosses theme or specification")
            if assessment_id not in revision_inputs:
                raise ProspectiveError(
                    "Conditional W25 assessment is outside the exact research revision")
            self._require_current(
                stored, self.archive.latest(stored.submission.object_id),
                "W25 assessment")
            assessments.append(assessment)
        if {item.claim_version_id for item in assessments} != set(
                request.claim_version_ids):
            raise ProspectiveError(
                "W25 assessments must cover exactly the conditional Claims")
        assessed_evidence = {
            evidence_id
            for assessment in assessments
            for evidence_id in assessment.evidence_version_ids
        }
        if assessed_evidence != set(request.evidence_version_ids):
            raise ProspectiveError(
                "Conditional Evidence must match the exact assessed Evidence set")
        if any(
                item.relation in {
                    EvidenceRelation.IRRELEVANT,
                    EvidenceRelation.BACKGROUND_ONLY,
                }
                for item in assessments):
            raise ProspectiveError(
                "Irrelevant/background-only Evidence cannot ground C")
        current_snapshot = self.workflow.current_snapshot(request.dossier_id)[1]
        snapshot_methods = set(current_snapshot.method_use_version_ids)
        if not set(request.method_use_version_ids) <= snapshot_methods:
            raise ProspectiveError(
                "Conditional MethodUse is outside the current dossier")
        for method_id in request.method_use_version_ids:
            method = self.workflow.load_method(method_id)
            if (method.theme_id != request.theme_id
                    or method.spec_sha256 != request.spec_sha256):
                raise ProspectiveError(
                    "Conditional MethodUse crosses theme or specification")

    def _validate_b1_b2(self, request: ProspectiveRequest,
                        snapshot) -> tuple:
        active = {item.step: item for item in snapshot.active_steps}
        m10 = active.get(ResearchStep.M10)
        m11 = active.get(ResearchStep.M11)
        if (m10 is None
                or m10.record_version_id
                != request.source_m10_record_version_id):
            raise ProspectiveError(
                "Conditional record needs the current active M10")
        if (m11 is None
                or m11.record_version_id
                != request.source_m11_record_version_id):
            raise ProspectiveError(
                "Conditional record needs the current active M11")
        m10_record = self.workflow.load_step_record(m10.record_version_id)
        m11_record = self.workflow.load_step_record(m11.record_version_id)
        if (m10_record.step is not ResearchStep.M10
                or m10_record.dossier_id != request.dossier_id
                or m10_record.revision_id != request.revision_id
                or m10_record.spec_sha256 != request.spec_sha256
                or m10_record.artifact_version_ids != (
                request.source_advisor_output_version_id,)
                or m10_record.disposition not in (
                    StepDisposition.READY_FOR_NEXT,
                    StepDisposition.CANDIDATE,
                    StepDisposition.LIMITED)):
            raise ProspectiveError(
                "Current M10 does not bind a usable B1 output")
        if (m11_record.step is not ResearchStep.M11
                or m11_record.dossier_id != request.dossier_id
                or m11_record.revision_id != request.revision_id
                or m11_record.spec_sha256 != request.spec_sha256
                or m11_record.artifact_version_ids != (
                request.source_teacher_output_version_id,)
                or m11_record.disposition not in (
                    StepDisposition.READY_FOR_NEXT,
                    StepDisposition.LIMITED)):
            raise ProspectiveError(
                "Current M11 does not bind a usable B2 output")
        advisor = self.advisors.load_advisor(
            request.source_advisor_output_version_id)
        teacher = self.teachers.load_teacher(
            request.source_teacher_output_version_id)
        advisor_latest = self.archive.latest(
            _object("ADVISOR-OBJECT-", advisor.advisory_id))
        teacher_latest = self.archive.latest(
            _object("TEACHER-OBJECT-", teacher.teaching_id))
        if (advisor_latest is None
                or advisor_latest.submission.version_id
                != request.source_advisor_output_version_id
                or teacher_latest is None
                or teacher_latest.submission.version_id
                != request.source_teacher_output_version_id):
            raise ProspectiveError(
                "Conditional record uses a superseded B1/B2 output")
        for label, output in (("B1", advisor), ("B2", teacher)):
            if (output.dossier_id != request.dossier_id
                    or output.revision_id != request.revision_id
                    or output.theme_id != request.theme_id
                    or output.spec_sha256 != request.spec_sha256):
                raise ProspectiveError(
                    f"{label} output crosses the conditional research basis")
        if request.original_judgment.exact_judgment != advisor.judgment.core_judgment:
            raise ProspectiveError(
                "Original judgment must preserve the exact B1 wording")
        if request.original_judgment.supported_scope != (
                advisor.judgment.evidence_sensitive_scope):
            raise ProspectiveError(
                "Original judgment changes the B1 supported scope")
        if request.teaching.exact_proposition != teacher.proposition.statement:
            raise ProspectiveError(
                "Teaching reference must preserve the exact B2 proposition")
        if request.teaching.teaching_boundary != teacher.proposition.scope:
            raise ProspectiveError(
                "Teaching reference changes the B2 proposition scope")
        expected_claims = set(advisor.claim_version_ids) | set(
            teacher.claim_version_ids)
        expected_evidence = set(advisor.evidence_version_ids) | set(
            teacher.evidence_version_ids)
        expected_assessments = set(
            advisor.claim_evidence_assessment_version_ids) | set(
                teacher.claim_evidence_assessment_version_ids)
        if set(request.claim_version_ids) != expected_claims:
            raise ProspectiveError(
                "Conditional Claims must exactly union current B1/B2 Claims")
        if set(request.evidence_version_ids) != expected_evidence:
            raise ProspectiveError(
                "Conditional Evidence must exactly union current B1/B2 Evidence")
        if set(request.claim_evidence_assessment_version_ids) != (
                expected_assessments):
            raise ProspectiveError(
                "Conditional assessments must exactly union current B1/B2 assessments")
        return advisor, teacher

    def _validate_model_execution(self, request: ProspectiveRequest,
                                  advisor, teacher) -> None:
        if request.execution_method is ExecutionMethod.MANUAL:
            return
        if not self.model_admission.authorizes(
                request.model_admission_id,
                configuration_id=request.model_configuration_id,
                duty=ModelDuty.EXPLANATION, domains=request.model_domains,
                require_given_material=True, at=request.created_at):
            raise ProspectiveError(
                "C execution is outside a current admitted explanation scope")
        operation = self.archive.get(request.operation_request_version_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise ProspectiveError(
                "C execution has no actual OperationRequest")
        operation_body = OperationRequest.model_validate_json(
            self.archive.read_body(request.operation_request_version_id))
        if operation_body.kind is not OperationKind.MODEL:
            raise ProspectiveError(
                "C execution request is not a model operation")
        if operation_body.step_id != "M12":
            raise ProspectiveError(
                "C model operation is not the M12 task")
        if operation_body.material_use is not MaterialUse.MODEL_PROCESS:
            raise ProspectiveError(
                "C model operation lacks model-processing authority")
        configuration = self.model_admission.load_configuration(
            request.model_configuration_id)
        if (operation_body.spec_sha256 != request.spec_sha256
                or operation_body.configuration_sha256
                != configuration.configuration_sha256):
            raise ProspectiveError(
                "C operation and configuration differ")
        required_inputs = {
            request.revision_id,
            request.source_m10_record_version_id,
            request.source_m11_record_version_id,
            request.source_advisor_output_version_id,
            request.source_teacher_output_version_id,
            *request.claim_version_ids,
            *request.evidence_version_ids,
            *request.claim_evidence_assessment_version_ids,
            *request.method_use_version_ids,
        }
        if not required_inputs <= set(operation_body.input_version_ids):
            raise ProspectiveError(
                "C operation does not bind every conditional input")
        receipt = OperationJournal(self.archive, self.rights).receipt(
            request.operation_request_version_id)
        if receipt is None or receipt.status is not OperationStatus.SUCCEEDED:
            raise ProspectiveError(
                "C execution has no successful operation receipt")
        if (request.created_at < receipt.ended_at
                or request.created_at < receipt.recorded_at
                or operation_body.created_at > receipt.started_at):
            raise ProspectiveError(
                "C output predates its actual model operation")

    def record(self, request: ProspectiveRequest) -> ProspectiveResult:
        if not isinstance(request, ProspectiveRequest):
            raise TypeError("record requires ProspectiveRequest")
        request = ProspectiveRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        content_hash = _digest(request.model_dump(mode="json"))
        output_version_id = _version("CONDITIONAL-OUTPUT-", canonical([
            request.prospective_id,
            request.previous_version_id,
            content_hash]))
        object_id = _object("CONDITIONAL-OBJECT-", request.prospective_id)
        output = ProspectiveOutput(
            prospective_id=request.prospective_id,
            prospective_output_version_id=output_version_id,
            previous_version_id=request.previous_version_id,
            dossier_id=request.dossier_id,
            previous_snapshot_version_id=request.expected_snapshot_version_id,
            revision_id=request.revision_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            source_m10_record_version_id=request.source_m10_record_version_id,
            source_m11_record_version_id=request.source_m11_record_version_id,
            source_advisor_output_version_id=(
                request.source_advisor_output_version_id),
            source_teacher_output_version_id=(
                request.source_teacher_output_version_id),
            original_judgment=request.original_judgment,
            teaching=request.teaching, mode=request.mode,
            mode_reason=request.mode_reason, paths=request.paths,
            ambiguity=request.ambiguity, evaluation=request.evaluation,
            review_window=request.review_window,
            future_review_owner=request.future_review_owner,
            claim_version_ids=request.claim_version_ids,
            evidence_version_ids=request.evidence_version_ids,
            claim_evidence_assessment_version_ids=(
                request.claim_evidence_assessment_version_ids),
            method_use_version_ids=request.method_use_version_ids,
            open_questions=request.open_questions,
            closure=request.closure, limitations=request.limitations,
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
            raise ProspectiveError(
                "Conditional task and dossier identity differ")
        revision = self.research.load_revision(request.revision_id)
        current_revision = self.research.current_revision(request.theme_id)
        if (current_revision is None
                or current_revision.revision_id != revision.revision_id):
            raise ProspectiveError("Conditional task revision is stale")
        advisor, teacher = self._validate_b1_b2(request, snapshot)
        self._validate_basis(request, revision)
        self._validate_model_execution(request, advisor, teacher)
        expected_body_sha256 = _digest(
            canonical(output.model_dump(mode="json")).encode())
        active_m12 = {
            item.step: item for item in snapshot.active_steps
        }.get(ResearchStep.M12)
        if active_m12 is not None:
            record = self.workflow.load_step_record(
                active_m12.record_version_id)
            if output_version_id in record.artifact_version_ids:
                latest_output = self.archive.latest(object_id)
                if (latest_output is None
                        or latest_output.submission.version_id
                        != output_version_id
                        or record.artifact_version_ids != (
                            output_version_id,)):
                    raise ProspectiveError(
                        "Current M12 does not bind the latest exact C output")
                if (record.previous_snapshot_version_id
                        != request.expected_snapshot_version_id):
                    raise ProspectiveError(
                        "Current M12 does not descend from the requested C snapshot")
                return ProspectiveResult(
                    prospective_output_version_id=output_version_id,
                    m12_step_record_version_id=active_m12.record_version_id,
                    dossier_snapshot_version_id=(
                        snapshot_stored.submission.version_id))
        if snapshot_stored.submission.version_id != request.expected_snapshot_version_id:
            raise WorkflowError("Conditional task uses a stale dossier snapshot")
        try:
            existing = self.archive.get(output_version_id)
            if (existing.submission.kind is not ObjectKind.CONDITIONAL_OUTPUT
                    or existing.body_sha256 != expected_body_sha256):
                raise ProspectiveError(
                    "Conditional output version ID is already in use")
        except MissingVersion:
            latest = self.archive.latest(object_id)
            if request.previous_version_id is None:
                if latest is not None:
                    raise ProspectiveError(
                        "Conditional output history requires previous version")
            elif (latest is None
                  or latest.submission.version_id
                  != request.previous_version_id):
                raise ProspectiveError(
                    "Conditional output previous version is not current")
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
                    target_version_id=request.source_m10_record_version_id,
                    use=ReferenceUse.BASIS,
                    locator="current B1 M10"),
                VersionReference(
                    target_version_id=request.source_m11_record_version_id,
                    use=ReferenceUse.BASIS,
                    locator="current B2 M11"),
                VersionReference(
                    target_version_id=request.source_advisor_output_version_id,
                    use=ReferenceUse.BASIS,
                    locator="original B1 judgment"),
                VersionReference(
                    target_version_id=request.source_teacher_output_version_id,
                    use=ReferenceUse.BASIS,
                    locator="current B2 teaching"),
                *(
                    VersionReference(
                        target_version_id=claim_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"conditional claim {index}")
                    for index, claim_id in enumerate(
                        request.claim_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=evidence_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"conditional evidence {index}")
                    for index, evidence_id in enumerate(
                        request.evidence_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=assessment_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"conditional assessment {index}")
                    for index, assessment_id in enumerate(
                        request.claim_evidence_assessment_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=method_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"conditional method {index}")
                    for index, method_id in enumerate(
                        request.method_use_version_ids)
                ),
            ]
            if request.operation_request_version_id is not None:
                refs.append(VersionReference(
                    target_version_id=request.operation_request_version_id,
                    use=ReferenceUse.SUPPORT,
                    locator="actual C operation"))
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=output_version_id,
                parent_version_id=request.previous_version_id,
                kind=ObjectKind.CONDITIONAL_OUTPUT,
                title=f"C conditional output {request.prospective_id}",
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
                request.source_m10_record_version_id,
                request.source_m11_record_version_id,
                request.source_advisor_output_version_id,
                request.source_teacher_output_version_id,
                *request.claim_version_ids,
                *request.evidence_version_ids,
                *request.claim_evidence_assessment_version_ids,
                *request.method_use_version_ids,
            ]
            for version_id in version_ids:
                stored = self.archive.get(version_id)
                expected[stored.submission.object_id] = stored.submission.version_id
            try:
                self.archive.append(
                    submission,
                    canonical(output.model_dump(mode="json")).encode(),
                    expected_current=expected)
            except Conflict:
                concurrent = self.archive.get(output_version_id)
                if (concurrent.submission.kind is not ObjectKind.CONDITIONAL_OUTPUT
                        or concurrent.body_sha256 != expected_body_sha256):
                    raise
        existing = self.archive.get(output_version_id)
        if (existing.submission.kind is not ObjectKind.CONDITIONAL_OUTPUT
                or existing.body_sha256 != expected_body_sha256):
            raise ProspectiveError(
                "Conditional output append was not recoverable")
        disposition = (
            StepDisposition.READY_FOR_NEXT
            if request.mode is ProspectiveMode.MULTI_PATH
            else StepDisposition.LIMITED)
        previous_m12 = None
        for record_id in reversed(snapshot.record_history_version_ids):
            record = self.workflow.load_step_record(record_id)
            if record.step is ResearchStep.M12:
                previous_m12 = record.step_record_version_id
                break
        try:
            snapshot_result = self.workflow.submit_step(ResearchStepSubmission(
                step_record_id="CONDITIONAL-M12-" + _digest([
                    output_version_id,
                    request.expected_snapshot_version_id])[:32],
                previous_step_record_version_id=previous_m12,
                dossier_id=request.dossier_id,
                expected_snapshot_version_id=(
                    request.expected_snapshot_version_id),
                theme_id=request.theme_id,
                spec_sha256=request.spec_sha256,
                revision_id=request.revision_id,
                step=ResearchStep.M12, owner=StepOwner.CONDITIONS,
                disposition=disposition,
                artifact_version_ids=(output_version_id,),
                method_use_version_ids=request.method_use_version_ids,
                closure=request.closure,
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
            raise ProspectiveError(
                "Conditional output is recorded as an unadopted attempt; "
                "exact retry on this same dossier basis resumes M12, while "
                "a changed basis requires a new C request") from exc
        return ProspectiveResult(
            prospective_output_version_id=output_version_id,
            m12_step_record_version_id=next(
                item.record_version_id
                for item in self.workflow.load_snapshot(
                    snapshot_result.submission.version_id).active_steps
                if item.step is ResearchStep.M12),
            dossier_snapshot_version_id=(
                snapshot_result.submission.version_id))

    def load(self, prospective_version_id: str) -> ProspectiveOutput:
        stored = self.archive.get(prospective_version_id)
        if stored.submission.kind is not ObjectKind.CONDITIONAL_OUTPUT:
            raise ProspectiveError(
                "Requested version is not a conditional output")
        output = ProspectiveOutput.model_validate_json(
            self.archive.read_body(prospective_version_id))
        if (output.prospective_output_version_id != prospective_version_id
                or stored.submission.spec_sha256 != output.spec_sha256
                or stored.submission.created_at != output.created_at):
            raise ProspectiveError(
                "Conditional output identity mismatch")
        return output
