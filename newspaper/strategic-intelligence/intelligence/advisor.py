"""W28 B1 adviser judgment and case-specific gain records.

The record binds one exact W27 dossier state and one exact W16 revision to
current W25 Claim, Evidence and assessment versions. It is not a content PASS,
independent Review, adoption decision or publication authorization.
"""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

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
from .workflow import (ExecutionMethod, ResearchStep, ResearchStepSubmission,
                       ResearchWorkflowController, StepDisposition, StepOwner,
                       WorkflowError)


class JudgmentStrength(str, Enum):
    BOUNDED_JUDGMENT = "BOUNDED_JUDGMENT"
    CANDIDATE_EXPLANATION = "CANDIDATE_EXPLANATION"
    LIMITATION_OR_UNKNOWN = "LIMITATION_OR_UNKNOWN"


class DecisionApplicability(str, Enum):
    SPECIFIC_ACTION_DECISION = "SPECIFIC_ACTION_DECISION"
    NO_ACTION_DECISION = "NO_ACTION_DECISION"


class BaselineUnderstanding(Contract):
    original_version_id: Identifier
    original_scope: NonBlank
    existing_explanation: NonBlank
    what_it_does_not_explain: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.what_it_does_not_explain
                or len(self.what_it_does_not_explain) != len(set(
                    self.what_it_does_not_explain))):
            raise ValueError("Baseline needs unique actual explanation gaps")
        return self


class AdvisorJudgment(Contract):
    core_judgment: NonBlank
    strength: JudgmentStrength
    conditions: tuple[NonBlank, ...]
    unknowns: tuple[NonBlank, ...]
    falsifiers: tuple[NonBlank, ...]
    evidence_sensitive_scope: NonBlank
    decision_applicability: DecisionApplicability
    decision_effect: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("condition", self.conditions),
                ("unknown", self.unknowns),
                ("falsifier", self.falsifiers)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate adviser judgment {name}")
            if not values:
                raise ValueError(f"Adviser judgment needs explicit {name}s")
        return self


class DecisionOption(Contract):
    option_id: Identifier
    action: NonBlank
    rationale: NonBlank
    costs: NonBlank
    beneficiaries: NonBlank
    likely_other_actor_response: NonBlank
    adjustment_or_exit: NonBlank
    observable_effect: NonBlank


class AdvisorDecisionContext(Contract):
    decision_question: NonBlank
    decision_maker: NonBlank
    options: tuple[DecisionOption, ...]
    comparison_basis: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if len(self.options) < 2 or len({item.option_id for item in self.options}) != len(
                self.options):
            raise ValueError("Decision context needs at least two unique options")
        return self


class UnderstandingGain(Contract):
    before_summary: NonBlank
    after_summary: NonBlank
    case_specific_gain: NonBlank
    original_contribution: NonBlank
    journal_contribution: NonBlank
    evidence_change_consequence: NonBlank
    limits: tuple[NonBlank, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.before_summary == self.after_summary:
            raise ValueError("Gain assessment must state what changed")
        if self.original_contribution.casefold() == self.journal_contribution.casefold():
            raise ValueError("Original and journal contributions must remain distinct")
        if self.case_specific_gain.casefold() in {
                self.original_contribution.casefold(),
                self.journal_contribution.casefold()}:
            raise ValueError("Case-specific gain must not relabel a contribution summary")
        if len(self.limits) != len(set(self.limits)):
            raise ValueError("Duplicate gain limitation")
        return self


class AdvisorOutputRequest(Contract):
    schema_version: Literal[1] = 1
    advisory_id: Identifier
    previous_version_id: Identifier | None = None
    dossier_id: Identifier
    expected_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    source_m09_record_version_id: Identifier
    baseline: BaselineUnderstanding
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    judgment: AdvisorJudgment
    gain: UnderstandingGain
    decision_context: AdvisorDecisionContext | None = None
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
                ("claim-evidence assessment",
                 self.claim_evidence_assessment_version_ids),
                ("limitation", self.limitations),
                ("model domain", self.model_domains)):
            if not values and name in (
                    "claim", "evidence", "claim-evidence assessment"):
                raise ValueError(f"Adviser output needs {name} versions")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate adviser {name}")
        if (self.judgment.decision_applicability
                is DecisionApplicability.SPECIFIC_ACTION_DECISION
                and self.decision_context is None):
            raise ValueError("Specific action decision needs a decision context")
        if (self.judgment.decision_applicability
                is DecisionApplicability.NO_ACTION_DECISION
                and self.decision_context is not None):
            raise ValueError("No-action judgment cannot carry invented action options")
        if (self.judgment.strength is JudgmentStrength.LIMITATION_OR_UNKNOWN
                and not self.limitations):
            raise ValueError("Limitation/unknown output needs explicit limitations")
        if self.execution_method is ExecutionMethod.ADMITTED_MODEL:
            if not all((self.model_admission_id, self.model_configuration_id,
                        self.operation_request_version_id, self.model_domains)):
                raise ValueError("Admitted adviser needs model admission and actual operation")
        elif any((self.model_admission_id, self.model_configuration_id,
                  self.operation_request_version_id)) or self.model_domains:
            raise ValueError("Manual adviser cannot carry model execution identity")
        return self


class AdvisorOutput(Contract):
    schema_version: Literal[1] = 1
    advisory_id: Identifier
    advisor_version_id: Identifier
    previous_version_id: Identifier | None
    dossier_id: Identifier
    previous_snapshot_version_id: Identifier
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    source_m09_record_version_id: Identifier
    baseline: BaselineUnderstanding
    claim_version_ids: tuple[Identifier, ...]
    evidence_version_ids: tuple[Identifier, ...]
    claim_evidence_assessment_version_ids: tuple[Identifier, ...]
    judgment: AdvisorJudgment
    gain: UnderstandingGain
    decision_context: AdvisorDecisionContext | None
    limitations: tuple[NonBlank, ...]
    next_action: NonBlank
    execution_method: ExecutionMethod
    model_admission_id: Identifier | None
    model_configuration_id: Identifier | None
    operation_request_version_id: Identifier | None
    model_domains: tuple[NonBlank, ...]
    role: Literal["B1"] = "B1"
    facts_verified: Literal[False] = False
    causal_support: Literal[False] = False
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime


class AdvisorResult(Contract):
    advisor_output_version_id: Identifier
    m10_step_record_version_id: Identifier
    dossier_snapshot_version_id: Identifier


class AdvisorError(ArchiveError):
    """Adviser output boundary failure, never content or publication approval."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


class AdvisorController:
    def __init__(self, archive: Archive, rights: RightsGrant,
                 workflow: ResearchWorkflowController | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("AdvisorController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("AdvisorController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.workflow = workflow or ResearchWorkflowController(archive, rights)
        self.research = ResearchRevisionController(archive, rights)
        self.model_admission = ModelAdmissionController(archive, rights)
        self.evidence = EvidenceController(archive, rights)

    def _validate_model_execution(self, request: AdvisorOutputRequest) -> None:
        if request.execution_method is ExecutionMethod.MANUAL:
            return
        if not self.model_admission.authorizes(
                request.model_admission_id,
                configuration_id=request.model_configuration_id,
                duty=ModelDuty.ADVISER, domains=request.model_domains,
                require_given_material=True, at=request.created_at):
            raise AdvisorError("Adviser execution is outside a current admitted task scope")
        operation = self.archive.get(request.operation_request_version_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise AdvisorError("Adviser execution has no actual OperationRequest")
        operation_body = OperationRequest.model_validate_json(
            self.archive.read_body(request.operation_request_version_id))
        if operation_body.kind is not OperationKind.MODEL:
            raise AdvisorError("Adviser execution request is not a model operation")
        if operation_body.step_id != "M10":
            raise AdvisorError("Adviser model operation is not the M10 task")
        if operation_body.material_use is not MaterialUse.MODEL_PROCESS:
            raise AdvisorError("Adviser model operation lacks model-processing authority")
        configuration = self.model_admission.load_configuration(
            request.model_configuration_id)
        if (operation_body.spec_sha256 != request.spec_sha256
                or operation_body.configuration_sha256
                != configuration.configuration_sha256):
            raise AdvisorError("Adviser operation and configuration differ")
        required_inputs = {
            request.revision_id,
            request.source_m09_record_version_id,
            request.baseline.original_version_id,
            *request.claim_version_ids,
            *request.evidence_version_ids,
            *request.claim_evidence_assessment_version_ids,
        }
        if not required_inputs <= set(operation_body.input_version_ids):
            raise AdvisorError(
                "Adviser operation does not bind every judgment input")
        receipt = OperationJournal(self.archive, self.rights).receipt(
            request.operation_request_version_id)
        if receipt is None or receipt.status is not OperationStatus.SUCCEEDED:
            raise AdvisorError("Adviser execution has no successful operation receipt")
        if (request.created_at < receipt.ended_at
                or request.created_at < receipt.recorded_at
                or operation_body.created_at > receipt.started_at):
            raise AdvisorError("Adviser output predates its actual model operation")

    @staticmethod
    def _require_current(stored: StoredVersion, latest: StoredVersion | None,
                         label: str) -> None:
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise AdvisorError(f"Adviser {label} is not the current version")

    def _validate_basis(self, request: AdvisorOutputRequest,
                        revision) -> None:
        revision_inputs = set(revision.input_version_ids)
        baseline = self.archive.get(request.baseline.original_version_id)
        if baseline.submission.kind not in (
                ObjectKind.SOURCE, ObjectKind.DOCUMENT,
                ObjectKind.SOURCE_MATERIAL):
            raise AdvisorError(
                "Adviser baseline must be an original source/document, not a research version")
        if baseline.body_retention_revoked:
            raise AdvisorError("Adviser baseline source is unavailable")
        if baseline.submission.spec_sha256 != request.spec_sha256:
            raise AdvisorError("Adviser baseline source uses another specification")
        if request.baseline.original_version_id not in revision_inputs:
            raise AdvisorError("Adviser baseline is outside the exact research revision")
        self._require_current(
            baseline,
            self.archive.latest(baseline.submission.object_id),
            "baseline source")

        for claim_id in request.claim_version_ids:
            claim_stored = self.archive.get(claim_id)
            claim = self.evidence.load_claim(claim_id)
            if claim_stored.body_retention_revoked:
                raise AdvisorError("Adviser judgment references a withdrawn Claim")
            if (claim.theme_id != request.theme_id
                    or claim.spec_sha256 != request.spec_sha256):
                raise AdvisorError("Adviser Claim crosses the dossier theme or specification")
            if claim_id not in revision_inputs:
                raise AdvisorError("Adviser Claim is outside the exact research revision")
            self._require_current(
                claim_stored,
                self.archive.latest(claim_stored.submission.object_id),
                "Claim")

        revision_evidence = set(revision.evidence_version_ids)
        for evidence_id in request.evidence_version_ids:
            evidence_stored = self.archive.get(evidence_id)
            evidence = self.evidence.load_evidence(evidence_id)
            if evidence_stored.body_retention_revoked:
                raise AdvisorError("Adviser judgment references withdrawn Evidence")
            if (evidence.theme_id != request.theme_id
                    or evidence.spec_sha256 != request.spec_sha256):
                raise AdvisorError(
                    "Adviser Evidence crosses the dossier theme or specification")
            if evidence_id not in revision_inputs or evidence_id not in revision_evidence:
                raise AdvisorError(
                    "Adviser Evidence is outside the exact research revision")
            self._require_current(
                evidence_stored,
                self.archive.latest(evidence_stored.submission.object_id),
                "Evidence")

        assessments = []
        for assessment_id in request.claim_evidence_assessment_version_ids:
            assessment_stored = self.archive.get(assessment_id)
            assessment = self.evidence.load_assessment(assessment_id)
            if assessment_stored.body_retention_revoked:
                raise AdvisorError(
                    "Adviser judgment references a withdrawn W25 assessment")
            if (assessment.theme_id != request.theme_id
                    or assessment.spec_sha256 != request.spec_sha256):
                raise AdvisorError(
                    "Adviser W25 assessment crosses the dossier theme or specification")
            if assessment_id not in revision_inputs:
                raise AdvisorError(
                    "Adviser W25 assessment is outside the exact research revision")
            self._require_current(
                assessment_stored,
                self.archive.latest(assessment_stored.submission.object_id),
                "W25 assessment")
            assessments.append(assessment)

        claim_ids = set(request.claim_version_ids)
        evidence_ids = set(request.evidence_version_ids)
        assessment_claim_ids = {item.claim_version_id for item in assessments}
        if assessment_claim_ids != claim_ids:
            raise AdvisorError(
                "W25 assessments must cover exactly the selected Adviser Claims")
        assessed_evidence = {
            evidence_id
            for assessment in assessments
            for evidence_id in assessment.evidence_version_ids
        }
        if assessed_evidence != evidence_ids:
            raise AdvisorError(
                "Adviser Evidence must match the exact assessed Evidence set")
        if any(
                assessment.relation in {
                    EvidenceRelation.IRRELEVANT,
                    EvidenceRelation.BACKGROUND_ONLY,
                }
                for assessment in assessments):
            raise AdvisorError("Irrelevant/background-only Evidence cannot ground B1 judgement")
        if (request.judgment.strength is JudgmentStrength.BOUNDED_JUDGMENT
                and not any(assessment.relation is EvidenceRelation.SUPPORTS
                            for assessment in assessments)):
            raise AdvisorError("Bounded judgment needs at least one supported Claim")

    def record_advisor(self, request: AdvisorOutputRequest) -> AdvisorResult:
        if not isinstance(request, AdvisorOutputRequest):
            raise TypeError("record_advisor requires AdvisorOutputRequest")
        request = AdvisorOutputRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        content_hash = _digest(request.model_dump(mode="json"))
        advisor_version_id = _version("ADVISOR-OUTPUT-", canonical([
            request.advisory_id, request.previous_version_id, content_hash]))
        object_id = _object("ADVISOR-OBJECT-", request.advisory_id)
        output = AdvisorOutput(
            advisory_id=request.advisory_id,
            advisor_version_id=advisor_version_id,
            previous_version_id=request.previous_version_id,
            dossier_id=request.dossier_id,
            previous_snapshot_version_id=request.expected_snapshot_version_id,
            revision_id=request.revision_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256,
            source_m09_record_version_id=request.source_m09_record_version_id,
            baseline=request.baseline,
            claim_version_ids=request.claim_version_ids,
            evidence_version_ids=request.evidence_version_ids,
            claim_evidence_assessment_version_ids=(
                request.claim_evidence_assessment_version_ids),
            judgment=request.judgment, gain=request.gain,
            decision_context=request.decision_context,
            limitations=request.limitations, next_action=request.next_action,
            execution_method=request.execution_method,
            model_admission_id=request.model_admission_id,
            model_configuration_id=request.model_configuration_id,
            operation_request_version_id=request.operation_request_version_id,
            model_domains=request.model_domains,
            created_at=request.created_at)
        snapshot_stored, snapshot = self.workflow.current_snapshot(request.dossier_id)
        if (snapshot.theme_id != request.theme_id
                or snapshot.spec_sha256 != request.spec_sha256
                or snapshot.revision_id != request.revision_id):
            raise AdvisorError("Adviser task and dossier identity differ")
        revision = self.research.load_revision(request.revision_id)
        current_revision = self.research.current_revision(request.theme_id)
        if (current_revision is None
                or current_revision.revision_id != revision.revision_id):
            raise AdvisorError("Adviser task revision is stale")
        active = {item.step: item for item in snapshot.active_steps}
        m09_binding = active.get(ResearchStep.M09)
        if (m09_binding is None
                or m09_binding.record_version_id
                != request.source_m09_record_version_id):
            raise AdvisorError("Adviser task needs the current active M09 record")
        source_step = self.workflow.load_step_record(
            request.source_m09_record_version_id)
        if (source_step.step is not ResearchStep.M09
                or source_step.dossier_id != request.dossier_id
                or source_step.revision_id != request.revision_id
                or source_step.disposition not in (
                    StepDisposition.READY_FOR_NEXT, StepDisposition.LIMITED)):
            raise AdvisorError("Adviser task needs a ready M09 record from this dossier revision")
        self._validate_basis(request, revision)
        self._validate_model_execution(request)
        expected_body_sha256 = _digest(
            canonical(output.model_dump(mode="json")).encode())
        active_m10 = active.get(ResearchStep.M10)
        if active_m10 is not None:
            active_m10_record = self.workflow.load_step_record(
                active_m10.record_version_id)
            if advisor_version_id in active_m10_record.artifact_version_ids:
                latest_output = self.archive.latest(object_id)
                if (latest_output is None
                        or latest_output.submission.version_id
                        != advisor_version_id
                        or active_m10_record.artifact_version_ids
                        != (advisor_version_id,)):
                    raise AdvisorError(
                        "Current M10 does not bind the latest exact Adviser output")
                if (active_m10_record.previous_snapshot_version_id
                        != request.expected_snapshot_version_id):
                    raise AdvisorError(
                        "Current M10 does not descend from the requested Adviser snapshot")
                return AdvisorResult(
                    advisor_output_version_id=advisor_version_id,
                    m10_step_record_version_id=active_m10.record_version_id,
                    dossier_snapshot_version_id=snapshot_stored.submission.version_id)
        if snapshot_stored.submission.version_id != request.expected_snapshot_version_id:
            raise WorkflowError("Adviser task uses a stale dossier snapshot")
        try:
            existing = self.archive.get(advisor_version_id)
            if (existing.submission.kind is not ObjectKind.ADVISOR_OUTPUT
                    or existing.body_sha256 != expected_body_sha256):
                raise AdvisorError("Advisor output version ID is already in use")
        except MissingVersion:
            latest = self.archive.latest(object_id)
            if request.previous_version_id is None:
                if latest is not None:
                    raise AdvisorError("Adviser output history requires previous version")
            elif latest is None or latest.submission.version_id != request.previous_version_id:
                raise AdvisorError("Adviser output previous version is not current")
            refs = [
                VersionReference(target_version_id=request.expected_snapshot_version_id,
                    use=ReferenceUse.BASIS, locator="exact dossier snapshot"),
                VersionReference(target_version_id=request.revision_id,
                    use=ReferenceUse.BASIS, locator="exact research revision"),
                VersionReference(target_version_id=request.source_m09_record_version_id,
                    use=ReferenceUse.BASIS, locator="ready M09 research"),
                VersionReference(target_version_id=request.baseline.original_version_id,
                    use=ReferenceUse.BACKGROUND, locator="author/original baseline"),
                *(
                    VersionReference(target_version_id=claim_id,
                        use=ReferenceUse.SUPPORT, locator=f"adviser claim {index}")
                    for index, claim_id in enumerate(request.claim_version_ids)
                ),
                *(
                    VersionReference(target_version_id=evidence_id,
                        use=ReferenceUse.SUPPORT, locator=f"adviser evidence {index}")
                    for index, evidence_id in enumerate(request.evidence_version_ids)
                ),
                *(
                    VersionReference(
                        target_version_id=assessment_id,
                        use=ReferenceUse.SUPPORT,
                        locator=f"claim-evidence assessment {index}")
                    for index, assessment_id in enumerate(
                        request.claim_evidence_assessment_version_ids)
                ),
            ]
            if request.operation_request_version_id is not None:
                refs.append(VersionReference(
                    target_version_id=request.operation_request_version_id,
                    use=ReferenceUse.SUPPORT, locator="actual adviser operation"))
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=advisor_version_id,
                parent_version_id=request.previous_version_id,
                kind=ObjectKind.ADVISOR_OUTPUT,
                title=f"B1 adviser output {request.advisory_id}",
                spec_sha256=request.spec_sha256, created_at=request.created_at,
                source_times=SourceTimes(), rights=self.rights,
                representation=Representation.FULL_BODY,
                references=tuple(refs))
            expected = {
                object_id: latest.submission.version_id if latest else None,
                snapshot_stored.submission.object_id: snapshot_stored.submission.version_id,
                self.research._revision_object(request.theme_id): request.revision_id,
            }
            for version_id in (
                    request.source_m09_record_version_id,
                    request.baseline.original_version_id,
                    *request.claim_version_ids,
                    *request.evidence_version_ids,
                    *request.claim_evidence_assessment_version_ids):
                stored = self.archive.get(version_id)
                expected[stored.submission.object_id] = stored.submission.version_id
            try:
                self.archive.append(
                    submission, canonical(output.model_dump(mode="json")).encode(),
                    expected_current=expected)
            except Conflict:
                concurrent = self.archive.get(advisor_version_id)
                if (concurrent.submission.kind is not ObjectKind.ADVISOR_OUTPUT
                        or concurrent.body_sha256 != expected_body_sha256):
                    raise
        existing = self.archive.get(advisor_version_id)
        if (existing.submission.kind is not ObjectKind.ADVISOR_OUTPUT
                or existing.body_sha256 != expected_body_sha256):
            raise AdvisorError("Adviser output append was not recoverable")
        disposition = (
            {
                JudgmentStrength.BOUNDED_JUDGMENT:
                    StepDisposition.READY_FOR_NEXT,
                JudgmentStrength.CANDIDATE_EXPLANATION:
                    StepDisposition.CANDIDATE,
                JudgmentStrength.LIMITATION_OR_UNKNOWN:
                    StepDisposition.LIMITED,
            }[request.judgment.strength])
        previous_m10 = None
        for record_id in reversed(snapshot.record_history_version_ids):
            record = self.workflow.load_step_record(record_id)
            if record.step is ResearchStep.M10:
                previous_m10 = record.step_record_version_id
                break
        try:
            snapshot_result = self.workflow.submit_step(ResearchStepSubmission(
                step_record_id="ADVISOR-M10-" + _digest([
                    advisor_version_id, request.expected_snapshot_version_id])[:32],
                previous_step_record_version_id=previous_m10,
                dossier_id=request.dossier_id,
                expected_snapshot_version_id=request.expected_snapshot_version_id,
                theme_id=request.theme_id, spec_sha256=request.spec_sha256,
                revision_id=request.revision_id, step=ResearchStep.M10,
                owner=StepOwner.ADVISER, disposition=disposition,
                artifact_version_ids=(advisor_version_id,),
                limitations=request.limitations, next_action=request.next_action,
                execution_method=request.execution_method,
                model_admission_id=request.model_admission_id,
                model_configuration_id=request.model_configuration_id,
                operation_request_version_id=request.operation_request_version_id,
                model_domains=request.model_domains, created_at=request.created_at))
        except (ArchiveError, ValueError) as exc:
            raise AdvisorError(
                "Adviser output is recorded as an unadopted attempt; exact retry "
                "on this same dossier basis resumes M10, while a changed basis "
                "requires a new Adviser request") from exc
        return AdvisorResult(
            advisor_output_version_id=advisor_version_id,
            m10_step_record_version_id=next(
                item.record_version_id
                for item in self.workflow.load_snapshot(
                    snapshot_result.submission.version_id).active_steps
                if item.step is ResearchStep.M10),
            dossier_snapshot_version_id=snapshot_result.submission.version_id)

    def load_advisor(self, advisor_version_id: str) -> AdvisorOutput:
        stored = self.archive.get(advisor_version_id)
        if stored.submission.kind is not ObjectKind.ADVISOR_OUTPUT:
            raise AdvisorError("Requested version is not an AdvisorOutput")
        output = AdvisorOutput.model_validate_json(
            self.archive.read_body(advisor_version_id))
        if (output.advisor_version_id != advisor_version_id
                or stored.submission.spec_sha256 != output.spec_sha256
                or stored.submission.created_at != output.created_at):
            raise AdvisorError("Adviser output identity mismatch")
        return output
