"""W30 owned-fixture tests for conditional paths and M12 review conditions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.archive import Archive, canonical
from intelligence.contracts import MaterialUse
from intelligence.operations import (CostObservation, ObservationKind,
                                     OperationJournal, OperationKind,
                                     OperationRequest, OperationStatus,
                                     ToolResponse)
from intelligence.prospective import (AmbiguityAssessment, ConditionalPath,
                                      ConditionalPathStep, EvaluationCondition,
                                      OpenQuestion, OriginalJudgmentReference,
                                      ProspectiveController, ProspectiveError,
                                      ProspectiveMode, ProspectiveOutput,
                                      ProspectiveRequest, ReviewWindow,
                                      TeachingReference)
from intelligence.research import ResearchRevision
from intelligence.workflow import (ExecutionMethod, ResearchClosure,
                                   ResearchStep, ResearchWorkflowController,
                                   StepDisposition, WorkflowError)

AT = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)


class ProspectiveTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_teacher import TeacherTests
        self.fx = TeacherTests(
            methodName="test_complete_b2_teaching_and_m11_roundtrip_are_idempotent")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.archive = self.fx.archive
        self.rights = self.fx.rights
        self.workflow = self.fx.workflow
        self.research = self.fx.research
        self.revision = self.fx.revision
        self.time = self.fx.time
        self.step_records = self.fx.step_records
        self.record_b1_b2()
        self.controller = ProspectiveController(
            self.archive, self.rights, self.workflow)

    def record_b1_b2(self, *, prior_advisor=None, prior_teacher=None):
        advisor_request = self.fx.advisor_request()
        if prior_advisor is not None:
            advisor_request = advisor_request.model_copy(
                update={"previous_version_id": prior_advisor})
        advisor_result = self.fx.advisor.record_advisor(advisor_request)
        self.advisor_output_version_id = (
            advisor_result.advisor_output_version_id)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.step_records[ResearchStep.M10] = next(
            item.record_version_id for item in snapshot.active_steps
            if item.step is ResearchStep.M10)
        teacher_request = self.fx.request()
        if prior_teacher is not None:
            teacher_request = teacher_request.model_copy(
                update={"previous_version_id": prior_teacher})
        teacher_result = self.fx.teacher.record_teacher(teacher_request)
        self.teacher_output_version_id = (
            teacher_result.teacher_output_version_id)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.step_records[ResearchStep.M11] = next(
            item.record_version_id for item in snapshot.active_steps
            if item.step is ResearchStep.M11)
        self.advisor_output = self.fx.advisor.load_advisor(
            self.advisor_output_version_id)
        self.teacher_output = self.fx.teacher.load_teacher(
            self.teacher_output_version_id)

    def path(self, path_id, branch, observation, *, authority):
        claim_id = "CLAIM-W29-v001"
        evidence_id = self.fx.evidence_version_id
        return ConditionalPath(
            path_id=path_id,
            branch_condition=branch,
            first_distinguishing_observation=observation,
            steps=(
                ConditionalPathStep(
                    step_id=path_id + "-1", ordinal=1,
                    actor_or_system="Owned operator",
                    authority_or_resource=authority,
                    decision_or_transfer=(
                        "Assign or decline an implementation action"),
                    precondition="The stated commitment remains active",
                    resulting_state="An action enters or exits preparation",
                    minimum_lag="Before the next observable review point",
                    claim_version_ids=(claim_id,),
                    evidence_version_ids=(evidence_id,),
                    uncertainty="The selected evidence does not show the decision"),
                ConditionalPathStep(
                    step_id=path_id + "-2", ordinal=2,
                    actor_or_system="Owned implementation unit",
                    authority_or_resource=authority,
                    decision_or_transfer=(
                        "Execute an approved action or stop at the authority limit"),
                    precondition="The first action has an assigned owner",
                    resulting_state="An observable action or non-action appears",
                    minimum_lag="One reporting period",
                    claim_version_ids=(claim_id,),
                    evidence_version_ids=(evidence_id,),
                    method_use_version_ids=(
                        "METHOD-METHOD-W29",
                    ) if path_id == "PATH-RESOURCE" else (),
                    uncertainty="Execution remains conditional and unobserved"),
            ),
            beneficiaries=("Owned beneficiaries",),
            cost_bearers=("Owned operator and affected users",),
            feedback_conditions=(
                "Implementation delays alter the next decision",
            ),
            failure_or_exit_conditions=(
                "No authority or resource is assigned",
            ),
            not_established_fact="This path is a conditional future possibility.")

    def build_paths(self):
        actual_method = self.fx.method_version_id
        paths = []
        for raw in (
                self.path(
                    "PATH-RESOURCE",
                    "Budget and staff are assigned",
                    "A dated budget or staffing decision appears",
                    authority="Formal authority plus a funded budget"),
                self.path(
                    "PATH-AUTHORITY",
                    "Authority remains legally unresolved",
                    "A formal legal instrument appears or is explicitly absent",
                    authority="A separate legal instrument is required")):
            steps = []
            for index, step in enumerate(raw.steps):
                methods = step.method_use_version_ids
                if raw.path_id == "PATH-RESOURCE" and index == 1:
                    methods = (actual_method,)
                steps.append(step.model_copy(
                    update={"method_use_version_ids": methods}))
            paths.append(raw.model_copy(update={"steps": tuple(steps)}))
        return tuple(paths)

    def request(self, **updates):
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        created_at = max(
            self.time, stored.submission.created_at) + timedelta(seconds=3)
        base = ProspectiveRequest(
            prospective_id="CONDITIONAL-W30",
            dossier_id="DOSSIER-W29",
            expected_snapshot_version_id=stored.submission.version_id,
            revision_id=self.revision.revision_id,
            theme_id="THEME-W29", spec_sha256=self.revision.spec_sha256,
            source_m10_record_version_id=self.step_records[ResearchStep.M10],
            source_m11_record_version_id=self.step_records[ResearchStep.M11],
            source_advisor_output_version_id=self.advisor_output_version_id,
            source_teacher_output_version_id=self.teacher_output_version_id,
            original_judgment=OriginalJudgmentReference(
                exact_judgment=self.advisor_output.judgment.core_judgment,
                supported_scope=(
                    self.advisor_output.judgment.evidence_sensitive_scope),
                knowledge_cutoff=AT),
            teaching=TeachingReference(
                exact_proposition=self.teacher_output.proposition.statement,
                teaching_boundary=self.teacher_output.proposition.scope),
            mode=ProspectiveMode.MULTI_PATH,
            mode_reason=(
                "Resource availability and legal authority produce distinct "
                "observable paths after the original judgment."),
            paths=self.build_paths(),
            ambiguity=AmbiguityAssessment(
                missing_information=(
                    "No approved implementation record is selected"),
                cannot_distinguish_because=(
                    "The current evidence contains neither a budget decision nor "
                    "a legal instrument"),
                next_discriminating_observations=(
                    "A dated budget allocation",
                    "A formal legal instrument",
                )),
            evaluation=EvaluationCondition(
                supports_if=(
                    "A dated allocation is followed by observed implementation",
                ),
                weakens_if=(
                    "The announcement remains unchanged beyond the review window",
                ),
                overturns_if=(
                    "Current authoritative evidence shows no authority or action was required",
                ),
                mechanism_checks=(
                    "Compare the decision, allocation and observed action sequence",
                ),
                alternative_explanation_checks=(
                    "Check whether another actor implemented the same change",
                )),
            review_window=ReviewWindow(
                start=created_at,
                end=created_at + timedelta(days=90),
                source_timezone="Pacific/Auckland",
                rationale="The mechanism requires one implementation cycle"),
            future_review_owner="W39",
            claim_version_ids=(self.fx.claim.claim_version_id,),
            evidence_version_ids=(self.fx.evidence_version_id,),
            claim_evidence_assessment_version_ids=(
                self.fx.assessment_version_id,),
            method_use_version_ids=(self.fx.method_version_id,),
            open_questions=(
                OpenQuestion(
                    question_id="OQ-W30-1",
                    question="Would removing a legal veto change the observed path?",
                    why_open="No current legal instrument is available",
                    evidence_that_would_narrow_it=(
                        "The actual legal authority and veto record")),
                OpenQuestion(
                    question_id="OQ-W30-2",
                    question="Which funded actor would move first?",
                    why_open="No allocation or implementation owner is selected",
                    evidence_that_would_narrow_it=(
                        "A dated allocation and named responsible unit")),
            ),
            closure=ResearchClosure(
                supported_scope=(
                    "Only a bounded conditional distinction is supported"),
                remaining_unknowns=(
                    "Actual authority, budget and implementation remain unknown",
                ),
                stop_reason=(
                    "The current evidence cannot select a future path"),
                next_trigger=(
                    "A dated authority, budget or implementation record appears"),
                reopen_owner="T03"),
            limitations=(),
            next_action="Send C and M12 conditions to independent review.",
            created_at=created_at)
        return base.model_copy(update=updates)

    @staticmethod
    def revalidated(request):
        return ProspectiveRequest.model_validate_json(
            request.model_dump_json(warnings=False))

    def test_multi_path_c_and_m12_roundtrip_are_idempotent(self):
        request = self.request()
        result = self.controller.record(request)
        output = self.controller.load(
            result.prospective_output_version_id)
        self.assertEqual(output.role, "C")
        self.assertIs(output.facts_verified, False)
        self.assertIs(output.causal_support, False)
        self.assertIs(output.forecast_is_fact, False)
        self.assertIs(output.observed_outcome_claimed, False)
        self.assertIs(output.reader_answers_collected, False)
        self.assertIs(output.content_review_required, True)
        self.assertIs(output.publication_authorized, False)
        self.assertEqual(output.thesis_storage_target, "W33")
        record = self.workflow.load_step_record(
            result.m12_step_record_version_id)
        self.assertIs(record.step, ResearchStep.M12)
        self.assertEqual(
            record.artifact_version_ids,
            (result.prospective_output_version_id,))
        self.assertEqual(self.controller.record(request), result)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.assertEqual(
            sum(1 for item in snapshot.active_steps
                if item.step is ResearchStep.M12), 1)

    def test_original_b1_and_b2_words_and_scope_are_not_rewritten(self):
        with self.assertRaisesRegex(ProspectiveError, "exact B1 wording"):
            self.controller.record(self.request(
                original_judgment=self.request().original_judgment.model_copy(
                    update={"exact_judgment": "A later rewritten prediction"})))
        with self.assertRaisesRegex(ProspectiveError, "B2 proposition"):
            self.controller.record(self.request(
                teaching=self.request().teaching.model_copy(
                    update={"exact_proposition": "A different lesson"})))

    def test_multi_path_needs_distinct_branches_and_first_observations(self):
        request = self.request()
        with self.assertRaisesRegex(ValidationError, "at least two"):
            self.revalidated(self.request(paths=(request.paths[0],)))
        duplicate = request.paths[1].model_copy(update={
            "branch_condition": request.paths[0].branch_condition,
            "first_distinguishing_observation": (
                request.paths[0].first_distinguishing_observation)})
        with self.assertRaisesRegex(ValidationError, "distinct branch"):
            self.revalidated(self.request(
                paths=(request.paths[0], duplicate)))

    def test_each_path_needs_two_links_and_real_actor_conditions(self):
        request = self.request()
        with self.assertRaisesRegex(ValidationError, "two ordered"):
            request.paths[0].__class__.model_validate_json(
                request.paths[0].model_copy(
                    update={"steps": (request.paths[0].steps[0],)})
                .model_dump_json())
        empty_authority = request.paths[0].steps[0].model_copy(
            update={"authority_or_resource": " "})
        with self.assertRaises(ValidationError):
            ConditionalPathStep.model_validate_json(
                empty_authority.model_dump_json())
        with self.assertRaisesRegex(ValidationError, "failure/exit condition"):
            ConditionalPath.model_validate_json(
                request.paths[0].model_copy(
                    update={"failure_or_exit_conditions": ()})
                .model_dump_json())

    def test_single_limited_path_and_not_applicable_close_as_limited(self):
        request = self.request()
        single = self.request(
            prospective_id="CONDITIONAL-W30-SINGLE",
            mode=ProspectiveMode.SINGLE_LIMITED,
            paths=(request.paths[0],),
            limitations=("Only one bounded path is supported",))
        result = self.controller.record(single)
        record = self.workflow.load_step_record(
            result.m12_step_record_version_id)
        self.assertIs(record.disposition, StepDisposition.LIMITED)
        with self.assertRaisesRegex(ValidationError, "explicit limitations"):
            self.revalidated(self.request(
                mode=ProspectiveMode.SINGLE_LIMITED,
                paths=(request.paths[0],)))

    def test_not_applicable_records_reason_without_fake_paths(self):
        request = self.request(
            prospective_id="CONDITIONAL-W30-NA",
            mode=ProspectiveMode.NOT_APPLICABLE,
            mode_reason=(
                "The evidence supports a bounded factual correction but no "
                "distinguishable future transition for a short update."),
            paths=(),
            limitations=("No conditional transition is supported",))
        result = self.controller.record(request)
        record = self.workflow.load_step_record(
            result.m12_step_record_version_id)
        self.assertIs(record.disposition, StepDisposition.LIMITED)
        with self.assertRaisesRegex(ValidationError, "cannot invent"):
            self.revalidated(self.request(
                mode=ProspectiveMode.NOT_APPLICABLE,
                paths=self.request().paths[:1],
                limitations=("No path",)))

    def test_evaluation_conditions_and_review_window_are_mandatory(self):
        request = self.request()
        with self.assertRaisesRegex(ValidationError, "support"):
            EvaluationCondition(
                supports_if=(), weakens_if=("A",), overturns_if=("B",),
                mechanism_checks=("C",), alternative_explanation_checks=("D",))
        with self.assertRaisesRegex(ValidationError, "end after"):
            ReviewWindow(
                start=AT, end=AT, source_timezone="UTC",
                rationale="Invalid zero window")
        self.controller.record(request)

    def test_path_sources_must_equal_declared_current_basis(self):
        request = self.request()
        original = request.paths[0].steps[0]
        foreign_evidence = original.model_copy(
            update={"evidence_version_ids": (
                self.fx.claim.claim_version_id,)})
        paths = []
        for path in request.paths:
            if path.path_id == "PATH-RESOURCE":
                steps = (foreign_evidence,) + path.steps[1:]
                path = path.model_copy(update={"steps": steps})
            paths.append(path)
        with self.assertRaisesRegex(ValidationError, "declared Evidence"):
            self.revalidated(self.request(paths=tuple(paths)))

    def test_new_revision_or_changed_m10_m11_blocks_old_conditions(self):
        request = self.request()
        with self.assertRaisesRegex(ProspectiveError, "active M10"):
            self.controller.record(self.request(
                source_m10_record_version_id=self.step_records[ResearchStep.M09]))
        with self.assertRaisesRegex(ProspectiveError, "active M11"):
            self.controller.record(self.request(
                source_m11_record_version_id=self.step_records[ResearchStep.M09]))
        replacement = ResearchRevision(
            revision_id="REV-W29-v002", theme_id="THEME-W29",
            spec_sha256=self.revision.spec_sha256,
            based_on_revision_id="REV-W29-v001",
            input_version_ids=self.revision.input_version_ids,
            question_version_id=self.revision.question_version_id,
            evidence_version_ids=self.revision.evidence_version_ids,
            reason="Owned W30 revision supersession",
            created_at=self.time + timedelta(minutes=1))
        self.research.append_revision(
            replacement, "REV-W29-v001")
        with self.assertRaisesRegex(ProspectiveError, "revision is stale"):
            self.controller.record(request)

    def test_model_execution_needs_explanation_admission_and_receipt(self):
        configuration_sha256 = "f" * 64
        journal = OperationJournal(self.archive, self.rights)

        def operation(operation_id):
            return OperationRequest(
                operation_id=operation_id,
                idempotency_key="IDEM-" + operation_id,
                run_id="RUN-W30",
                task_version_id=self.fx.question.submission.version_id,
                step_id="M12", spec_sha256=self.revision.spec_sha256,
                kind=OperationKind.MODEL,
                tool_id="OWNED-MODEL", tool_version="fixture-v1",
                provider_id="owned-provider",
                configuration_sha256=configuration_sha256,
                request_sha256="d" * 64,
                material_use=MaterialUse.MODEL_PROCESS,
                input_version_ids=(
                    self.revision.revision_id,
                    self.step_records[ResearchStep.M10],
                    self.step_records[ResearchStep.M11],
                    self.advisor_output_version_id,
                    self.teacher_output_version_id,
                    self.fx.claim.claim_version_id,
                    self.fx.evidence_version_id,
                    self.fx.assessment_version_id,
                    self.fx.method_version_id,
                ),
                created_at=self.time)

        missing = journal.begin(operation("OP-W30-NO-RECEIPT"))
        fake_configuration = SimpleNamespace(
            configuration_sha256=configuration_sha256)
        missing_request = self.request(
            prospective_id="CONDITIONAL-W30-MODEL-MISSING",
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W30",
            model_configuration_id="CONFIG-W30",
            operation_request_version_id=missing.submission.version_id,
            model_domains=("prospective-analysis",))
        with patch.object(
                self.controller.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.controller.model_admission, "load_configuration",
                    return_value=fake_configuration):
            with self.assertRaisesRegex(ProspectiveError, "successful operation receipt"):
                self.controller.record(missing_request)

        success = journal.begin(operation("OP-W30-SUCCESS"))
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
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        valid = self.request(
            prospective_id="CONDITIONAL-W30-MODEL-SUCCESS",
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W30",
            model_configuration_id="CONFIG-W30",
            operation_request_version_id=success.submission.version_id,
            model_domains=("prospective-analysis",),
            created_at=max(
                self.time, stored.submission.created_at)
            + timedelta(seconds=2))
        with patch.object(
                self.controller.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.controller.model_admission, "load_configuration",
                    return_value=fake_configuration), patch.object(
                    self.workflow.model_admission, "authorizes",
                    return_value=True), patch.object(
                    self.workflow.model_admission, "load_configuration",
                    return_value=fake_configuration):
            result = self.controller.record(valid)
        output = self.controller.load(result.prospective_output_version_id)
        self.assertEqual(
            output.operation_request_version_id,
            success.submission.version_id)

    def test_failed_m12_is_recoverable_without_active_half_output(self):
        request = self.request()
        with patch.object(
                self.workflow, "submit_step",
                side_effect=WorkflowError("owned simulated M12 failure")):
            with self.assertRaisesRegex(ProspectiveError, "unadopted attempt"):
                self.controller.record(request)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.assertFalse(any(
            item.step is ResearchStep.M12 for item in snapshot.active_steps))
        result = self.controller.record(request)
        self.assertEqual(
            self.workflow.load_step_record(
                result.m12_step_record_version_id).artifact_version_ids,
            (result.prospective_output_version_id,))

    def test_concurrent_exact_requests_leave_one_active_m12(self):
        request = self.request()

        def writer(_):
            with Archive(self.archive.root) as archive:
                controller = ProspectiveController(
                    archive, self.rights,
                    ResearchWorkflowController(archive, self.rights))
                try:
                    return controller.record(request)
                except Exception as exc:
                    return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(writer, range(2)))
        self.assertTrue(outcomes)
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        active_m12 = [
            item for item in snapshot.active_steps
            if item.step is ResearchStep.M12]
        self.assertEqual(len(active_m12), 1)
        history = [
            record_id for record_id in snapshot.record_history_version_ids
            if self.workflow.load_step_record(record_id).step is ResearchStep.M12]
        self.assertEqual(len(history), 1)

    def test_upstream_rework_links_new_m12_to_previous_condition_history(self):
        first = self.controller.record(self.request())
        self.fx.submit(
            ResearchStep.M05,
            artifact=self.fx.artifact("M05-W30-rework"),
            previous=self.step_records[ResearchStep.M05])
        self.fx.submit(
            ResearchStep.M07,
            artifact=self.fx.artifact("M07-W30-rework"),
            methods=tuple(
                self.workflow.current_snapshot("DOSSIER-W29")[1]
                .method_use_version_ids))
        self.fx.submit(
            ResearchStep.M08,
            artifact=self.fx.artifact("M08-W30-rework"))
        self.fx.submit(
            ResearchStep.M09,
            artifact=self.fx.artifact("M09-W30-rework"))
        prior_advisor = self.advisor_output_version_id
        prior_teacher = self.teacher_output_version_id
        self.record_b1_b2(
            prior_advisor=prior_advisor, prior_teacher=prior_teacher)
        second = self.controller.record(self.request(
            previous_version_id=first.prospective_output_version_id,
            mode_reason=(
                "The reworked research basis still leaves two distinguishable "
                "implementation paths.")))
        record = self.workflow.load_step_record(
            second.m12_step_record_version_id)
        self.assertEqual(
            record.previous_step_record_version_id,
            first.m12_step_record_version_id)
        output = self.controller.load(second.prospective_output_version_id)
        self.assertEqual(
            output.previous_version_id,
            first.prospective_output_version_id)

    def test_probabilities_or_future_results_cannot_be_smuggled_into_c(self):
        result = self.controller.record(self.request())
        output = self.controller.load(result.prospective_output_version_id)
        forged = output.model_dump(mode="json")
        forged.update({
            "observed_outcome_claimed": True,
            "forecast_is_fact": True,
            "future_result": "The predicted action occurred",
        })
        with self.assertRaises(ValidationError):
            ProspectiveOutput.model_validate_json(canonical(forged))
        payload = self.request().model_dump(mode="json")
        payload.update({
            "probabilities": [0.6, 0.4],
            "observed_result": "Already happened",
        })
        with self.assertRaisesRegex(ValidationError, "Extra inputs"):
            ProspectiveRequest.model_validate_json(canonical(payload))


if __name__ == "__main__":
    unittest.main()
