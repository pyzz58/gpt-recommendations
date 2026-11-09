"""W28 owned-fixture tests for B1 judgment, gain and M10 submission."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.advisor import (AdvisorController, AdvisorDecisionContext,
                                  AdvisorError, AdvisorJudgment,
                                  AdvisorOutput, AdvisorOutputRequest,
                                  BaselineUnderstanding, DecisionApplicability,
                                  DecisionOption, JudgmentStrength,
                                  UnderstandingGain)
from intelligence.archive import Archive, PermissionDenied, canonical
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState,
                                    ReferenceUse, Representation, RightsBasis,
                                    RightsGrant, Scope, ScopeMode, UsePermission,
                                    ValidityMode, VersionReference,
                                    VersionSubmission)
from intelligence.discovery import LineageRole
from intelligence.evidence import (ClaimEvidenceAssessment, ClaimScope,
                                   ClaimType, ClaimVersion, EvidenceNature,
                                   EvidenceNodeBinding, EvidenceRecord,
                                   EvidenceRelation)
from intelligence.operations import (CostObservation, ObservationKind,
                                     OperationJournal, OperationKind,
                                     OperationRequest, OperationStatus,
                                     ToolResponse)
from intelligence.research import ResearchRevision, ResearchRevisionController
from intelligence.workflow import (DossierStartRequest, ExecutionMethod,
                                   MethodUseRecord, Participant,
                                   ParticipantQuestion, ResearchStep,
                                   ResearchStepSubmission,
                                   ResearchWorkflowController, StepDisposition,
                                   StepOwner, WorkflowError)

AT = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64


def _version(prefix, identity):
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


class AdvisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.rights = RightsGrant(
            rights_id="RIGHTS-W28", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({
                MaterialUse.INDEX, MaterialUse.STORE_BODY}),
            evidence="Owned W28 adviser fixtures", checked_by="test fixture",
            checked_at=AT,
            permissions=(UsePermission(
                use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.time = AT
        self.question = self.store(
            "QUESTION-W28", "QUESTION-W28-v001",
            ObjectKind.QUESTION_VERSION, b"Owned W28 question")
        self.baseline = self.store(
            "SOURCE-MATERIAL-W28", "SOURCE-MATERIAL-W28-v001",
            ObjectKind.SOURCE_MATERIAL, b"Owned original explanation")
        self.claim_scope = ClaimScope(
            subjects=("owned operator",),
            metric="stated commitment",
            comparison_basis="Owned original text",
            conditions=("The original statement remains current",))
        self.claim = ClaimVersion(
            claim_version_id="CLAIM-W28-v001",
            theme_id="THEME-W28", spec_sha256=SPEC,
            question_version_id=self.question.submission.version_id,
            claim_text="The owned operator stated a bounded commitment.",
            claim_type=ClaimType.OBSERVED_FACT,
            scope=self.claim_scope, created_at=AT)
        self.claim_stored = self.store(
            "CLAIM-OBJECT-W28", self.claim.claim_version_id,
            ObjectKind.CLAIM,
            canonical(self.claim.model_dump(mode="json")).encode())
        self.evidence_id = "EVIDENCE-W28-v001"
        self.evidence_version_id = _version(
            "EVIDENCE-RECORD-", "EVIDENCE-W28")
        evidence = EvidenceRecord(
            evidence_id="EVIDENCE-W28", theme_id="THEME-W28",
            spec_sha256=SPEC,
            intake_version_id="INTAKE-W28",
            structure_version_id="STRUCTURE-W28",
            source_id="SOURCE-W28",
            source_sha256="b" * 64,
            lineage_proposal_id="LINEAGE-W28",
            cluster_id="CLUSTER-W28",
            lineage_role=LineageRole.ORIGINAL,
            lineage_root_ids=("ROOT-W28",),
            independence_known=True,
            nodes=(EvidenceNodeBinding(
                node_id="NODE-W28", locator="paragraph 1",
                text_sha256="c" * 64),),
            nature=EvidenceNature.DOCUMENTED_FACT,
            created_at=AT)
        self.evidence_stored = self.store(
            "EVIDENCE-OBJECT-W28", self.evidence_version_id,
            ObjectKind.EVIDENCE,
            canonical(evidence.model_dump(mode="json")).encode())
        self.assessment_id = "ASSESSMENT-W28-v001"
        self.assessment_version_id = _version(
            "CLAIM-EVIDENCE-", "ASSESSMENT-W28")
        assessment = ClaimEvidenceAssessment(
            assessment_id="ASSESSMENT-W28",
            theme_id="THEME-W28", spec_sha256=SPEC,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(self.evidence_version_id,),
            relation=EvidenceRelation.SUPPORTS,
            supported_scope=self.claim.scope,
            conditions=self.claim.scope.conditions,
            unsupported_aspects=(), counterevidence=(), unknowns=(),
            independent_root_ids=("ROOT-W28",),
            independent_root_count=1,
            same_root_duplicate_count=0,
            independence_unknown_count=0,
            reviewed_by="owned fixture reviewer",
            reviewed_at=AT + timedelta(seconds=2),
            created_at=AT + timedelta(seconds=2))
        self.assessment_stored = self.store(
            "ASSESSMENT-OBJECT-W28", self.assessment_version_id,
            ObjectKind.CLAIM_EVIDENCE_ASSESSMENT,
            canonical(assessment.model_dump(mode="json")).encode())
        self.research = ResearchRevisionController(
            self.archive, self.rights)
        self.revision = ResearchRevision(
            revision_id="REV-W28-v001", theme_id="THEME-W28",
            spec_sha256=SPEC,
            input_version_ids=(
                self.question.submission.version_id,
                self.baseline.submission.version_id,
                self.claim.claim_version_id,
                self.evidence_version_id,
                self.assessment_version_id),
            question_version_id=self.question.submission.version_id,
            evidence_version_ids=(self.evidence_version_id,),
            reason="Owned W28 exact research basis",
            created_at=AT + timedelta(seconds=3))
        self.research.append_revision(self.revision, None)
        self.workflow = ResearchWorkflowController(
            self.archive, self.rights)
        self.workflow.start_dossier(DossierStartRequest(
            dossier_id="DOSSIER-W28", theme_id="THEME-W28",
            spec_sha256=SPEC, revision_id=self.revision.revision_id,
            question_version_id=self.question.submission.version_id,
            knowledge_cutoff=AT,
            created_at=AT + timedelta(seconds=4)))
        self.time = AT + timedelta(seconds=5)
        self.step_records = {}
        self.complete_through_m09()
        self.advisor = AdvisorController(
            self.archive, self.rights, self.workflow)

    def store(self, object_id, version_id, kind, body):
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=kind, title=object_id, spec_sha256=SPEC,
            created_at=AT, rights=self.rights,
            representation=Representation.FULL_BODY), body)

    def artifact(self, label):
        self.time += timedelta(seconds=1)
        return self.archive.append(VersionSubmission(
            schema_version=2,
            object_id="ARTIFACT-W28-" + label,
            version_id=f"ARTIFACT-W28-{label}-{int(self.time.timestamp())}",
            kind=ObjectKind.ARTICLE,
            title="ARTIFACT-W28-" + label,
            spec_sha256=SPEC, created_at=self.time, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(VersionReference(
                target_version_id=self.revision.revision_id,
                use=ReferenceUse.BASIS,
                locator="exact research revision"),)),
            f"Owned {label} artifact".encode())

    def submit(self, step, *, artifact, methods=(), participants=(),
               disposition=StepDisposition.READY_FOR_NEXT,
               limitations=(), previous=None):
        stored, snapshot = self.workflow.current_snapshot("DOSSIER-W28")
        self.time = max(
            self.time, stored.submission.created_at) + timedelta(seconds=1)
        active = {item.step: item for item in snapshot.active_steps}
        if previous is None and step in active:
            previous = active[step].record_version_id
        elif previous is None:
            for record_id in reversed(snapshot.record_history_version_ids):
                record = self.workflow.load_step_record(record_id)
                if record.step is step:
                    previous = record.step_record_version_id
                    break
        result = self.workflow.submit_step(ResearchStepSubmission(
            step_record_id=f"STEP-{step.value}-{int(self.time.timestamp())}",
            previous_step_record_version_id=previous,
            dossier_id="DOSSIER-W28",
            expected_snapshot_version_id=stored.submission.version_id,
            theme_id="THEME-W28", spec_sha256=SPEC,
            revision_id=self.revision.revision_id, step=step,
            owner={
                ResearchStep.M10: StepOwner.ADVISER,
                ResearchStep.M11: StepOwner.TEACHER,
                ResearchStep.M12: StepOwner.CONDITIONS,
            }.get(step, StepOwner.JOINT),
            disposition=disposition,
            artifact_version_ids=(artifact.submission.version_id,),
            method_use_version_ids=tuple(methods),
            participant_questions=tuple(participants),
            limitations=tuple(limitations),
            created_at=self.time))
        latest = self.workflow.load_snapshot(result.submission.version_id)
        binding = next(item for item in latest.active_steps if item.step is step)
        self.step_records[step] = binding.record_version_id
        return result

    def complete_through_m09(self):
        method = MethodUseRecord(
            method_use_id="METHOD-W28",
            theme_id="THEME-W28", spec_sha256=SPEC,
            introduced_at=ResearchStep.M02,
            proposition="Distinguish stated commitment from observed outcome",
            source_version_ids=(self.baseline.submission.version_id,),
            read_scope="Owned original explanation",
            applicability_conditions=("The same actor and statement are compared",),
            expected_effect="Prevents a stated intention from becoming an observed result",
            misuse_or_limit="Cannot establish unobserved action or motive",
            created_at=self.time)
        method_version = self.workflow.append_method(
            method).submission.version_id
        participants = (
            ParticipantQuestion(
                participant=Participant.B1,
                question="Which bounded interpretation is specific to this case?",
                rationale="B1 participates from the problem phase"),
            ParticipantQuestion(
                participant=Participant.B2,
                question="Which distinction should the reader learn?",
                rationale="B2 participates from the problem phase"),
        )
        self.submit(
            ResearchStep.M01, artifact=self.artifact("M01"))
        self.submit(
            ResearchStep.M02, artifact=self.artifact("M02"),
            methods=(method_version,), participants=participants)
        self.submit(
            ResearchStep.M03, artifact=self.artifact("M03"))
        self.submit(
            ResearchStep.M04, artifact=self.artifact("M04"))
        self.submit(
            ResearchStep.M05, artifact=self.artifact("M05"))
        self.submit(
            ResearchStep.M06, artifact=self.artifact("M06"))
        self.submit(
            ResearchStep.M07, artifact=self.artifact("M07"),
            methods=(method_version,))
        self.submit(
            ResearchStep.M08, artifact=self.artifact("M08"))
        self.submit(
            ResearchStep.M09, artifact=self.artifact("M09"))

    @staticmethod
    def no_action_judgment(
            strength=JudgmentStrength.BOUNDED_JUDGMENT):
        return AdvisorJudgment(
            core_judgment=(
                "The statement establishes a bounded commitment, not an executed outcome."),
            strength=strength,
            conditions=("The same actor and statement remain the object of analysis",),
            unknowns=("Observed implementation remains outside the selected evidence",),
            falsifiers=("A current contradictory statement from the same actor appears",),
            evidence_sensitive_scope=(
                "Any change to the exact actor, statement or supporting Evidence"),
            decision_applicability=DecisionApplicability.NO_ACTION_DECISION,
            decision_effect="No concrete action chooser is present in this research question.")

    @staticmethod
    def gain(original="The original explains the stated commitment.",
             journal=(
                 "This journal separates the commitment from an executed outcome "
                 "and states its unresolved implementation.")):
        return UnderstandingGain(
            before_summary=(
                "Before analysis, the original commitment could be read as an outcome."),
            after_summary=(
                "After exact evidence checking, only a bounded commitment is supported."),
            case_specific_gain=(
                "The B1 gain is the case-specific boundary between commitment "
                "and implementation."),
            original_contribution=original,
            journal_contribution=journal,
            evidence_change_consequence=(
                "Contradictory current actor evidence would weaken or replace the judgment."),
            limits=("Implementation and motive remain unknown",))

    def request(self, **updates):
        stored, snapshot = self.workflow.current_snapshot("DOSSIER-W28")
        base = AdvisorOutputRequest(
            advisory_id="ADVISOR-W28",
            dossier_id="DOSSIER-W28",
            expected_snapshot_version_id=stored.submission.version_id,
            revision_id=self.revision.revision_id,
            theme_id="THEME-W28", spec_sha256=SPEC,
            source_m09_record_version_id=self.step_records[ResearchStep.M09],
            baseline=BaselineUnderstanding(
                original_version_id=self.baseline.submission.version_id,
                original_scope="Owned original explanation",
                existing_explanation=(
                    "The original explains the actor's stated commitment."),
                what_it_does_not_explain=(
                    "It does not establish implementation or motive.",)),
            claim_version_ids=(self.claim.claim_version_id,),
            evidence_version_ids=(self.evidence_version_id,),
            claim_evidence_assessment_version_ids=(
                self.assessment_version_id,),
            judgment=self.no_action_judgment(),
            gain=self.gain(),
            limitations=(),
            next_action="Send the bounded B1 judgment to content review.",
            created_at=self.time + timedelta(seconds=10))
        return base.model_copy(update=updates)

    @staticmethod
    def revalidated(request):
        return AdvisorOutputRequest.model_validate_json(
            request.model_dump_json(warnings=False))

    def test_bounded_b1_and_m10_roundtrip_are_idempotent(self):
        request = self.request()
        result = self.advisor.record_advisor(request)
        output = self.advisor.load_advisor(result.advisor_output_version_id)
        self.assertEqual(output.role, "B1")
        self.assertIs(output.facts_verified, False)
        self.assertIs(output.causal_support, False)
        self.assertIs(output.content_review_required, True)
        self.assertIs(output.publication_authorized, False)
        record = self.workflow.load_step_record(
            result.m10_step_record_version_id)
        self.assertIs(record.step, ResearchStep.M10)
        self.assertIs(record.disposition, StepDisposition.READY_FOR_NEXT)
        self.assertEqual(
            record.artifact_version_ids,
            (result.advisor_output_version_id,))
        repeated = self.advisor.record_advisor(request)
        self.assertEqual(repeated, result)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W28")
        self.assertEqual(
            sum(1 for item in snapshot.active_steps
                if item.step is ResearchStep.M10), 1)

    def test_stale_snapshot_m09_and_revision_are_rejected(self):
        request = self.request()
        self.submit(
            ResearchStep.M11,
            artifact=self.artifact("M11"),
            previous=self.step_records.get(ResearchStep.M11))
        with self.assertRaisesRegex(WorkflowError, "stale dossier snapshot"):
            self.advisor.record_advisor(request)

        _, snapshot = self.workflow.current_snapshot("DOSSIER-W28")
        current = self.request(
            expected_snapshot_version_id=snapshot.previous_snapshot_version_id
            or next(item.record_version_id for item in snapshot.active_steps
                    if item.step is ResearchStep.M09))
        # Use an explicit non-current M09 record with the latest snapshot.
        stored, _ = self.workflow.current_snapshot("DOSSIER-W28")
        bad_m09 = self.request(
            expected_snapshot_version_id=stored.submission.version_id,
            source_m09_record_version_id=self.step_records[ResearchStep.M08])
        with self.assertRaisesRegex(AdvisorError, "active M09"):
            self.advisor.record_advisor(bad_m09)

        revision_two = ResearchRevision(
            revision_id="REV-W28-v002", theme_id="THEME-W28",
            spec_sha256=SPEC,
            based_on_revision_id="REV-W28-v001",
            input_version_ids=self.revision.input_version_ids,
            question_version_id=self.revision.question_version_id,
            evidence_version_ids=self.revision.evidence_version_ids,
            reason="Owned W28 revision supersession",
            created_at=self.time + timedelta(minutes=1))
        self.research.append_revision(revision_two, "REV-W28-v001")
        with self.assertRaisesRegex(AdvisorError, "revision is stale"):
            self.advisor.record_advisor(current)

    def test_current_exact_revision_inputs_and_versions_are_required(self):
        wrong_baseline = self.request(baseline=BaselineUnderstanding(
            original_version_id=next(
                item.record_version_id
                for item in self.workflow.current_snapshot("DOSSIER-W28")[1].active_steps
                if item.step is ResearchStep.M01),
            original_scope="Not the original",
            existing_explanation="Any article is not an author baseline",
            what_it_does_not_explain=("The type is wrong",)))
        with self.assertRaisesRegex(AdvisorError, "original source/document"):
            self.advisor.record_advisor(wrong_baseline)

        missing_assessment = self.request(
            claim_evidence_assessment_version_ids=("ASSESSMENT-OTHER",))
        with self.assertRaises(Exception):
            self.advisor.record_advisor(missing_assessment)

        wrong_evidence = self.request(
            evidence_version_ids=(self.claim.claim_version_id,))
        with self.assertRaisesRegex(Exception, "Evidence|EvidenceRecord"):
            self.advisor.record_advisor(wrong_evidence)

        revoked_request = self.request()
        self.archive.revoke_rights(
            self.rights.rights_id, (MaterialUse.STORE_BODY,),
            "Owned W28 withdrawal regression")
        with self.assertRaises(PermissionDenied):
            self.advisor.record_advisor(revoked_request)

    def test_gain_baseline_and_bounded_strength_prevent_relabelling(self):
        with self.assertRaisesRegex(ValidationError, "Original and journal"):
            AdvisorOutputRequest.model_validate_json(
                self.request(gain=self.gain(
                    original="Same contribution",
                    journal="Same contribution")).model_dump_json())
        with self.assertRaisesRegex(ValidationError, "what changed"):
            UnderstandingGain(
                before_summary="Same",
                after_summary="Same",
                case_specific_gain="A case-specific boundary",
                original_contribution="Original explanation",
                journal_contribution="Journal explanation",
                evidence_change_consequence="New evidence changes the boundary")
        with self.assertRaisesRegex(ValidationError, "judgment needs explicit falsifiers"):
            AdvisorJudgment(
                core_judgment="Unbounded claim",
                strength=JudgmentStrength.BOUNDED_JUDGMENT,
                conditions=("One condition",),
                unknowns=("One unknown",),
                falsifiers=(),
                evidence_sensitive_scope="The exact evidence",
                decision_applicability=DecisionApplicability.NO_ACTION_DECISION,
                decision_effect="No action")

    def test_action_options_are_complete_and_not_invented(self):
        judgment = self.no_action_judgment().model_copy(update={
            "decision_applicability":
                DecisionApplicability.SPECIFIC_ACTION_DECISION})
        with self.assertRaisesRegex(ValidationError, "decision context"):
            self.revalidated(self.request(judgment=judgment))
        option = DecisionOption(
            option_id="OPTION-A",
            action="Publish a bounded commitment clarification",
            rationale="The selected evidence supports only a commitment",
            costs="Editorial time and a narrower framing",
            beneficiaries="Readers deciding what the statement proves",
            likely_other_actor_response="The actor may clarify implementation",
            adjustment_or_exit="Exit if no current response can be verified",
            observable_effect="A dated clarification or no clarification")
        with self.assertRaisesRegex(ValidationError, "at least two"):
            AdvisorDecisionContext(
                decision_question=(
                    "Should the edition clarify the commitment boundary?"),
                decision_maker="Owned editorial decision-maker",
                options=(option,), comparison_basis="Same evidence cut")
        second = DecisionOption.model_validate_json(option.model_copy(
            update={"option_id": "OPTION-B",
                    "action": "Hold the item pending implementation evidence"}
        ).model_dump_json())
        full_context = AdvisorDecisionContext(
            decision_question=(
                "Should the edition clarify the commitment boundary?"),
            decision_maker="Owned editorial decision-maker",
            options=(option, second), comparison_basis="Same evidence cut")
        spec_request = self.request(
            judgment=judgment, decision_context=full_context)
        self.advisor.record_advisor(spec_request)
        with self.assertRaisesRegex(ValidationError, "invented action options"):
            self.revalidated(self.request(
                decision_context=full_context))

    def test_limitation_and_candidate_strengths_map_to_non_pass_states(self):
        limitation = self.request(
            judgment=self.no_action_judgment(
                JudgmentStrength.LIMITATION_OR_UNKNOWN),
            limitations=("Implementation evidence is still missing",))
        result = self.advisor.record_advisor(limitation)
        record = self.workflow.load_step_record(
            result.m10_step_record_version_id)
        self.assertIs(record.disposition, StepDisposition.LIMITED)
        self.assertEqual(
            record.limitations, ("Implementation evidence is still missing",))
        with self.assertRaisesRegex(ValidationError, "explicit limitations"):
            self.revalidated(self.request(
                judgment=self.no_action_judgment(
                    JudgmentStrength.LIMITATION_OR_UNKNOWN)))

    def test_candidate_explanation_is_not_promoted_to_ready(self):
        request = self.request(
            advisory_id="ADVISOR-W28-CANDIDATE",
            judgment=self.no_action_judgment(
                JudgmentStrength.CANDIDATE_EXPLANATION))
        result = self.advisor.record_advisor(request)
        record = self.workflow.load_step_record(
            result.m10_step_record_version_id)
        self.assertIs(record.disposition, StepDisposition.CANDIDATE)

    def test_model_execution_needs_w19_and_actual_successful_receipt(self):
        model_request = self.request(
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-MISSING",
            model_configuration_id="CONFIG-MISSING",
            operation_request_version_id="OPERATION-MISSING",
            model_domains=("strategic-analysis",))
        with self.assertRaisesRegex(AdvisorError, "admitted task scope"):
            self.advisor.record_advisor(model_request)
        with self.assertRaisesRegex(ValidationError, "Manual adviser"):
            self.revalidated(self.request(
                model_admission_id="ADMISSION-MISSING"))

    def test_failed_m10_is_recoverable_by_exact_retry_without_active_half_output(self):
        request = self.request()
        with patch.object(
                self.advisor.workflow, "submit_step",
                side_effect=WorkflowError("owned simulated M10 failure")):
            with self.assertRaisesRegex(AdvisorError, "unadopted attempt"):
                self.advisor.record_advisor(request)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W28")
        self.assertFalse(any(
            item.step is ResearchStep.M10 for item in snapshot.active_steps))
        result = self.advisor.record_advisor(request)
        record = self.workflow.load_step_record(
            result.m10_step_record_version_id)
        self.assertEqual(
            record.artifact_version_ids,
            (result.advisor_output_version_id,))

    def test_concurrent_exact_requests_leave_only_one_active_m10(self):
        request = self.request()

        def writer(_):
            with Archive(self.archive.root) as archive:
                controller = AdvisorController(
                    archive, self.rights,
                    ResearchWorkflowController(archive, self.rights))
                try:
                    return controller.record_advisor(request)
                except Exception as exc:
                    return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(writer, range(2)))
        self.assertTrue(outcomes)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W28")
        active_m10 = [
            item for item in snapshot.active_steps
            if item.step is ResearchStep.M10]
        self.assertEqual(len(active_m10), 1)
        m10_history = [
            record_id
            for record_id in snapshot.record_history_version_ids
            if self.workflow.load_step_record(record_id).step is ResearchStep.M10]
        self.assertEqual(len(m10_history), 1)

    def test_admitted_model_requires_bound_inputs_and_successful_actual_receipt(self):
        configuration_sha256 = "f" * 64
        required_inputs = (
            self.revision.revision_id,
            self.step_records[ResearchStep.M09],
            self.baseline.submission.version_id,
            self.claim.claim_version_id,
            self.evidence_version_id,
            self.assessment_version_id,
        )
        journal = OperationJournal(self.archive, self.rights)

        def operation(operation_id):
            return OperationRequest(
                operation_id=operation_id,
                idempotency_key="IDEM-" + operation_id,
                run_id="RUN-W28", task_version_id=self.baseline.submission.version_id,
                step_id="M10", spec_sha256=SPEC,
                kind=OperationKind.MODEL,
                tool_id="OWNED-MODEL", tool_version="fixture-v1",
                provider_id="owned-provider",
                configuration_sha256=configuration_sha256,
                request_sha256="d" * 64,
                material_use=MaterialUse.MODEL_PROCESS,
                input_version_ids=required_inputs,
                created_at=self.time)

        missing_receipt = journal.begin(operation("OP-W28-NO-RECEIPT"))
        fake_configuration = SimpleNamespace(
            configuration_sha256=configuration_sha256)
        model_request = self.request(
            advisory_id="ADVISOR-W28-MODEL-MISSING",
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W28",
            model_configuration_id="CONFIG-W28",
            operation_request_version_id=(
                missing_receipt.submission.version_id),
            model_domains=("strategic-analysis",))
        with patch.object(
                self.advisor.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.advisor.model_admission, "load_configuration",
                    return_value=fake_configuration):
            with self.assertRaisesRegex(AdvisorError, "successful operation receipt"):
                self.advisor.record_advisor(model_request)

        success = journal.begin(operation("OP-W28-SUCCESS"))
        journal.record_receipt(ToolResponse(
            status=OperationStatus.SUCCEEDED,
            result_sha256="e" * 64,
            cost=CostObservation(
                kind=ObservationKind.UNKNOWN,
                basis="Owned fixture has no provider bill"),
            started_at=self.time,
            ended_at=self.time + timedelta(seconds=1)),
            operation_id=success.submission.version_id,
            recorded_at=self.time + timedelta(seconds=1))
        model_request = self.request(
            advisory_id="ADVISOR-W28-MODEL-SUCCESS",
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W28",
            model_configuration_id="CONFIG-W28",
            operation_request_version_id=success.submission.version_id,
            model_domains=("strategic-analysis",),
            created_at=self.time + timedelta(seconds=2))
        with patch.object(
                self.advisor.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.advisor.model_admission, "load_configuration",
                    return_value=fake_configuration), patch.object(
                    self.workflow.model_admission, "authorizes",
                    return_value=True), patch.object(
                    self.workflow.model_admission, "load_configuration",
                    return_value=fake_configuration):
            result = self.advisor.record_advisor(model_request)
        output = self.advisor.load_advisor(result.advisor_output_version_id)
        self.assertEqual(
            output.operation_request_version_id,
            success.submission.version_id)
        self.assertEqual(
            self.workflow.load_step_record(
                result.m10_step_record_version_id).artifact_version_ids,
            (result.advisor_output_version_id,))

    def test_reworked_upstream_uses_previous_m10_and_new_b1_history(self):
        first = self.advisor.record_advisor(self.request())
        self.submit(
            ResearchStep.M05,
            artifact=self.artifact("M05-rework"),
            previous=self.step_records[ResearchStep.M05])
        self.submit(
            ResearchStep.M07,
            artifact=self.artifact("M07-rework"),
            methods=tuple(
                self.workflow.current_snapshot("DOSSIER-W28")[1]
                .method_use_version_ids))
        self.submit(
            ResearchStep.M08,
            artifact=self.artifact("M08-rework"))
        self.submit(
            ResearchStep.M09,
            artifact=self.artifact("M09-rework"))
        revised = self.request(
            previous_version_id=first.advisor_output_version_id,
            judgment=self.no_action_judgment().model_copy(update={
                "core_judgment": (
                    "The reworked comparison still supports only a bounded commitment."),
            }))
        second = self.advisor.record_advisor(revised)
        record = self.workflow.load_step_record(
            second.m10_step_record_version_id)
        self.assertEqual(
            record.previous_step_record_version_id,
            first.m10_step_record_version_id)
        output = self.advisor.load_advisor(second.advisor_output_version_id)
        self.assertEqual(
            output.previous_version_id, first.advisor_output_version_id)

    def test_output_cannot_claim_pass_review_or_publication(self):
        result = self.advisor.record_advisor(self.request())
        output = self.advisor.load_advisor(
            result.advisor_output_version_id)
        forged = output.model_dump(mode="json")
        forged.update({
            "facts_verified": True,
            "publication_authorized": True,
            "role": "GENERAL_ADVISOR",
        })
        with self.assertRaises(ValidationError):
            AdvisorOutput.model_validate_json(canonical(forged))
        payload = self.request().model_dump(mode="json")
        payload.update({"role": "GENERAL_ADVISOR", "self_score": 99})
        with self.assertRaisesRegex(ValidationError, "Extra inputs"):
            AdvisorOutputRequest.model_validate_json(canonical(payload))


if __name__ == "__main__":
    unittest.main()
