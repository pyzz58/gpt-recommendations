"""W31 owned-fixture tests for independent review and author response closure."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.adoption import StepState
from intelligence.archive import Archive, canonical
from intelligence.contracts import (MaterialUse, ObjectKind, ReferenceUse,
                                    Representation, VersionReference,
                                    VersionSubmission)
from intelligence.editorial_review import (AuthorResponseItem,
                                           AuthorResponseRequest,
                                           ClosureOutcome,
                                           EditorialReviewController,
                                           EditorialReviewDecision,
                                           EditorialReviewError,
                                           FinalReviewRequest, InquiryType,
                                           IssueClosure, IssueSeverity,
                                           OpenReviewRequest, ReviewCaseState,
                                           ReviewDisposition, ReviewExposure,
                                           ReviewerInquiry)
from intelligence.operations import (CostObservation, ObservationKind,
                                     OperationJournal, OperationKind,
                                     OperationRequest, OperationStatus,
                                     ToolResponse)
from intelligence.workflow import ExecutionMethod, ResearchStep

AT = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)


def _version(prefix, identity):
    import json
    raw = json.dumps([prefix, identity], ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:32]


class EditorialReviewTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_prospective import ProspectiveTests
        self.pf = ProspectiveTests(
            methodName="test_multi_path_c_and_m12_roundtrip_are_idempotent")
        self.pf.setUp()
        self.addCleanup(self.pf.doCleanups)
        self.archive = self.pf.archive
        self.rights = self.pf.rights
        self.workflow = self.pf.workflow
        self.research = self.pf.research
        self.prospective_result = self.pf.controller.record(
            self.pf.request())
        _, snapshot = self.workflow.current_snapshot("DOSSIER-W29")
        self.pf.step_records[ResearchStep.M12] = next(
            item.record_version_id for item in snapshot.active_steps
            if item.step is ResearchStep.M12)
        self.prospective_output = self.pf.controller.load(
            self.prospective_result.prospective_output_version_id)
        self.time = max(
            self.pf.time, snapshot.created_at) + timedelta(seconds=2)
        self.task = self.store(
            "TASK-W31", "TASK-W31-v001", ObjectKind.TASK,
            b"Owned W31 content-review task")
        self.initial_article = self.make_article(
            "ARTICLE-W31-v001", None,
            b"The announcement proves execution and the commitment-to-execution "
            b"distinction should guide this case.")
        self.reviewer = EditorialReviewController(
            self.archive, self.rights, self.workflow)

    def store(self, object_id, version_id, kind, body,
              *, parent=None, references=()):
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            parent_version_id=parent, kind=kind,
            title=object_id, spec_sha256=self.pf.revision.spec_sha256,
            created_at=self.time, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(references)), body)

    def article_references(self):
        return (
            VersionReference(
                target_version_id=self.pf.revision.revision_id,
                use=ReferenceUse.BASIS, locator="exact research revision"),
            VersionReference(
                target_version_id=self.task.submission.version_id,
                use=ReferenceUse.BASIS, locator="review task"),
            VersionReference(
                target_version_id=self.pf.step_records[ResearchStep.M10],
                use=ReferenceUse.SUPPORT, locator="B1 M10"),
            VersionReference(
                target_version_id=self.pf.step_records[ResearchStep.M11],
                use=ReferenceUse.SUPPORT, locator="B2 M11"),
            VersionReference(
                target_version_id=self.pf.step_records[ResearchStep.M12],
                use=ReferenceUse.SUPPORT, locator="C M12"),
            VersionReference(
                target_version_id=(
                    self.prospective_output.source_advisor_output_version_id),
                use=ReferenceUse.SUPPORT, locator="B1 output"),
            VersionReference(
                target_version_id=(
                    self.prospective_output.source_teacher_output_version_id),
                use=ReferenceUse.SUPPORT, locator="B2 output"),
            VersionReference(
                target_version_id=(
                    self.prospective_result.prospective_output_version_id),
                use=ReferenceUse.SUPPORT, locator="C output"),
        )

    def make_article(self, version_id, parent, body):
        self.time += timedelta(seconds=1)
        return self.store(
            "ARTICLE-OBJECT-W31", version_id, ObjectKind.ARTICLE, body,
            parent=parent, references=self.article_references())

    @staticmethod
    def exposure():
        return ReviewExposure(
            started_from_draft=True,
            author_self_assessment_seen=False,
            prior_review_seen=False,
            limitations=())

    def inquiries(self):
        evidence_id = self.pf.fx.evidence_version_id
        claim_id = self.pf.fx.claim.claim_version_id
        method_id = self.pf.fx.method_version_id
        return (
            ReviewerInquiry(
                inquiry_id="INQ-FACT",
                inquiry_type=InquiryType.FACT_SUPPORT,
                severity=IssueSeverity.CRITICAL,
                article_locator="opening sentence",
                quoted_text="The announcement proves execution",
                concern=(
                    "The selected Evidence records a commitment, not execution."),
                required_check=(
                    "Check whether execution is directly supported in the exact Evidence."),
                claim_version_ids=(claim_id,),
                evidence_version_ids=(evidence_id,),
                formed_at=self.time),
            ReviewerInquiry(
                inquiry_id="INQ-TEACHING",
                inquiry_type=InquiryType.TEACHING,
                severity=IssueSeverity.MINOR,
                article_locator="closing clause",
                quoted_text="commitment-to-execution distinction",
                concern=(
                    "The phrase needs the already-written process boundary to be self-contained."),
                required_check=(
                    "Check that the final sentence retains the implementation boundary."),
                claim_version_ids=(claim_id,),
                evidence_version_ids=(evidence_id,),
                method_use_version_ids=(method_id,),
                formed_at=self.time),
        )

    def open_request(self, **updates):
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        created_at = max(
            self.time, stored.submission.created_at) + timedelta(seconds=2)
        base = OpenReviewRequest(
            review_case_id="REVIEW-CASE-W31",
            dossier_id="DOSSIER-W29",
            expected_snapshot_version_id=stored.submission.version_id,
            revision_id=self.pf.revision.revision_id,
            theme_id="THEME-W29",
            spec_sha256=self.pf.revision.spec_sha256,
            task_version_id=self.task.submission.version_id,
            article_version_id=self.initial_article.submission.version_id,
            source_m10_record_version_id=self.pf.step_records[ResearchStep.M10],
            source_m11_record_version_id=self.pf.step_records[ResearchStep.M11],
            source_m12_record_version_id=self.pf.step_records[ResearchStep.M12],
            source_advisor_output_version_id=(
                self.prospective_output.source_advisor_output_version_id),
            source_teacher_output_version_id=(
                self.prospective_output.source_teacher_output_version_id),
            source_prospective_output_version_id=(
                self.prospective_result.prospective_output_version_id),
            reviewer_id="REVIEWER-W31",
            author_ids=("AUTHOR-W31",),
            producer_id="AUTHOR-W31",
            reviewed_scope=("W31_CONTENT_REVIEW", "B1_B2_C_ARTICLE"),
            exposure=self.exposure(),
            inquiries=self.inquiries(),
            claim_version_ids=self.prospective_output.claim_version_ids,
            evidence_version_ids=self.prospective_output.evidence_version_ids,
            claim_evidence_assessment_version_ids=(
                self.prospective_output.claim_evidence_assessment_version_ids),
            method_use_version_ids=(
                self.prospective_output.method_use_version_ids),
            created_at=created_at)
        return base.model_copy(update=updates)

    def open_case(self):
        return self.reviewer.open_case(self.open_request())

    def respond_request(self, case, **updates):
        revised = self.make_article(
            "ARTICLE-W31-v002",
            self.initial_article.submission.version_id,
            b"The announcement is a bounded commitment; execution remains "
            b"unobserved. The commitment-to-execution distinction guides the "
            b"next evidence check.")
        self.time += timedelta(seconds=1)
        evidence_id = self.pf.fx.evidence_version_id
        base = AuthorResponseRequest(
            review_case_version_id=case.review_case_version_id,
            expected_current_case_version_id=case.review_case_version_id,
            responder_id="AUTHOR-W31",
            article_version_id=revised.submission.version_id,
            responses=(
                AuthorResponseItem(
                    inquiry_id="INQ-FACT", responder_id="AUTHOR-W31",
                    response=(
                        "Removed the claim that the announcement proves execution."),
                    evidence_version_ids=(evidence_id,),
                    proposed_resolution="Use the bounded commitment wording.",
                    responded_at=self.time),
                AuthorResponseItem(
                    inquiry_id="INQ-TEACHING", responder_id="AUTHOR-W31",
                    response=(
                        "Retained the distinction and stated that execution is unobserved."),
                    evidence_version_ids=(evidence_id,),
                    proposed_resolution=(
                        "Keep the final distinction and evidence check."),
                    responded_at=self.time),
            ),
            note="Owned author response after the fixed inquiries.",
            responded_at=self.time)
        return base.model_copy(update=updates), revised

    def final_request(self, case, article, *, decision=ReviewDisposition.PASS,
                      outcomes=None, **updates):
        self.time += timedelta(seconds=1)
        if outcomes is None:
            outcomes = {
                "INQ-FACT": ClosureOutcome.RESOLVED,
                "INQ-TEACHING": ClosureOutcome.RESOLVED,
            }
        base = FinalReviewRequest(
            review_case_version_id=case.review_case_version_id,
            expected_current_case_version_id=case.review_case_version_id,
            review_id="REVIEW-W31-001",
            article_version_id=article.submission.version_id,
            reviewer_id="REVIEWER-W31",
            decision=decision,
            reviewed_scope=case.reviewed_scope,
            closures=tuple(
                IssueClosure(
                    inquiry_id=issue.inquiry_id,
                    outcome=outcomes[issue.inquiry_id],
                    basis_version_ids=(self.pf.fx.evidence_version_id,),
                    rationale="Owned reviewer checked the exact revision.",
                    checked_at=self.time)
                for issue in case.inquiries),
            decision_reason="Owned content review decision.",
            remaining_limitations=(
                "Execution remains unobserved in the selected evidence",),
            expires_at=self.time + timedelta(days=30),
            decided_at=self.time)
        return base.model_copy(update=updates)

    def responded(self):
        initial = self.open_case()
        response, revised = self.respond_request(initial)
        updated = self.reviewer.respond(response)
        return initial, updated, revised

    def test_independent_review_pass_is_bound_to_actual_revision_and_w15(self):
        initial, case, revised = self.responded()
        request = self.final_request(case, revised)
        result = self.reviewer.decide(request)
        review = self.reviewer.load_review(result.review_version_id)
        self.assertEqual(review.decision, ReviewDisposition.PASS)
        self.assertIs(review.author_self_approved, False)
        self.assertIs(review.model_self_passed, False)
        self.assertIs(review.publication_authorized, False)
        self.assertIs(review.review_capability_certified, False)
        decision = self.reviewer.adoption.load(
            result.adoption_decision_version_id)
        self.assertIs(decision.state, StepState.READY)
        self.assertTrue(self.reviewer.adoption.is_current(
            result.adoption_decision_version_id))
        self.assertEqual(
            decision.subject_version_id,
            revised.submission.version_id)
        self.assertNotEqual(decision.subject_version_id,
                            initial.initial_article_version_id)
        self.assertEqual(self.reviewer.decide(request), result)

    def test_reviewer_cannot_be_author_or_producer_self_signer(self):
        with self.assertRaisesRegex(ValidationError, "Reviewer cannot be an author"):
            self.revalidated(self.open_request(reviewer_id="AUTHOR-W31"))
        with self.assertRaisesRegex(ValidationError, "Reviewer cannot be the producer"):
            self.revalidated(self.open_request(
                reviewer_id="SAME-W31", producer_id="SAME-W31"))

    def test_review_requires_actual_article_body_and_exact_quote(self):
        with self.assertRaisesRegex(EditorialReviewError, "not an Article"):
            self.reviewer.open_case(self.open_request(
                article_version_id=self.task.submission.version_id))
        nonmatching = self.inquiries()[0].model_copy(
            update={"quoted_text": "This text is absent from the reader draft"})
        with self.assertRaisesRegex(EditorialReviewError, "quotation does not occur"):
            self.reviewer.open_case(self.open_request(
                inquiries=(nonmatching, self.inquiries()[1])))

    def test_substantive_inquiries_need_their_corresponding_sources(self):
        with self.assertRaisesRegex(ValidationError, "needs exact Evidence"):
            ReviewerInquiry(
                inquiry_id="BAD-FACT",
                inquiry_type=InquiryType.FACT_SUPPORT,
                severity=IssueSeverity.MAJOR,
                article_locator="opening",
                quoted_text="The announcement proves execution",
                concern="Unsupported",
                required_check="Check evidence",
                claim_version_ids=(self.pf.fx.claim.claim_version_id,),
                formed_at=self.time)
        with self.assertRaisesRegex(ValidationError, "needs MethodUse or Evidence"):
            ReviewerInquiry(
                inquiry_id="BAD-METHOD",
                inquiry_type=InquiryType.METHOD_OR_PROFESSIONAL,
                severity=IssueSeverity.MAJOR,
                article_locator="process",
                quoted_text="commitment-to-execution distinction",
                concern="Method unclear",
                required_check="Check method",
                claim_version_ids=(self.pf.fx.claim.claim_version_id,),
                formed_at=self.time)

    def test_author_response_is_complete_ordered_and_from_declared_author(self):
        case = self.open_case()
        request, _ = self.respond_request(case)
        other = request.model_copy(update={
            "responder_id": "OTHER-W31",
            "responses": tuple(item.model_copy(update={
                "responder_id": "OTHER-W31"}) for item in request.responses)})
        with self.assertRaisesRegex(EditorialReviewError, "undeclared author"):
            self.reviewer.respond(other)
        incomplete = request.model_copy(update={
            "responses": (request.responses[0],)})
        with self.assertRaisesRegex(EditorialReviewError, "every reviewer inquiry"):
            self.reviewer.respond(incomplete)
        early = request.model_copy(update={
            "responded_at": case.created_at - timedelta(seconds=1),
            "responses": tuple(item.model_copy(update={
                "responded_at": case.created_at - timedelta(seconds=1)})
                for item in request.responses)})
        with self.assertRaisesRegex(EditorialReviewError, "cannot predate"):
            self.reviewer.respond(early)

    def test_pass_cannot_leave_open_or_unverified_inquiries(self):
        _, case, revised = self.responded()
        with self.assertRaisesRegex(ValidationError, "PASS cannot leave"):
            self.final_request(
                case, revised,
                outcomes={
                    "INQ-FACT": ClosureOutcome.UNVERIFIED,
                    "INQ-TEACHING": ClosureOutcome.RESOLVED,
                })

    def test_pass_can_accept_a_supported_dispute_without_inventing_a_new_claim(self):
        _, case, revised = self.responded()
        request = self.final_request(
            case, revised,
            outcomes={
                "INQ-FACT": ClosureOutcome.ACCEPTED_DISPUTE,
                "INQ-TEACHING": ClosureOutcome.RESOLVED,
            },
            review_id="REVIEW-W31-DISPUTE")
        result = self.reviewer.decide(request)
        review = self.reviewer.load_review(result.review_version_id)
        self.assertEqual(review.decision, ReviewDisposition.PASS)
        dispute = next(
            item for item in review.closures
            if item.inquiry_id == "INQ-FACT")
        self.assertIs(dispute.outcome, ClosureOutcome.ACCEPTED_DISPUTE)
        self.assertEqual(
            review.remaining_limitations,
            ("Execution remains unobserved in the selected evidence",))

    def test_revise_is_return_in_w15(self):
        _, case, revised = self.responded()
        revise = self.final_request(
            case, revised, decision=ReviewDisposition.REVISE,
            outcomes={
                "INQ-FACT": ClosureOutcome.OPEN,
                "INQ-TEACHING": ClosureOutcome.RESOLVED,
            },
            review_id="REVIEW-W31-REVISE")
        revise_result = self.reviewer.decide(revise)
        revise_decision = self.reviewer.adoption.load(
            revise_result.adoption_decision_version_id)
        self.assertIs(revise_decision.state, StepState.RETURN)

    def test_block_is_blocked_in_w15(self):
        _, case, revised = self.responded()
        block = self.final_request(
            case, revised, decision=ReviewDisposition.BLOCK,
            outcomes={
                "INQ-FACT": ClosureOutcome.OPEN,
                "INQ-TEACHING": ClosureOutcome.REVIEWER_WITHDRAWN,
            },
            review_id="REVIEW-W31-BLOCK")
        block_result = self.reviewer.decide(block)
        block_decision = self.reviewer.adoption.load(
            block_result.adoption_decision_version_id)
        self.assertIs(block_decision.state, StepState.BLOCKED)

    def test_block_needs_unresolved_critical_inquiry(self):
        _, case, revised = self.responded()
        with self.assertRaisesRegex(EditorialReviewError, "unresolved critical"):
            self.reviewer.decide(self.final_request(
                case, revised, decision=ReviewDisposition.BLOCK,
                outcomes={
                    "INQ-FACT": ClosureOutcome.RESOLVED,
                    "INQ-TEACHING": ClosureOutcome.REVIEWER_WITHDRAWN,
                }))

    def test_new_article_cannot_be_covered_by_old_review_case(self):
        _, case, revised = self.responded()
        later = self.make_article(
            "ARTICLE-W31-v003",
            revised.submission.version_id,
            b"A later reader draft after the response.")
        with self.assertRaisesRegex(EditorialReviewError, "responded Article"):
            self.reviewer.decide(self.final_request(
                case, later, review_id="REVIEW-W31-LATE"))

    def test_upstream_research_change_invalidates_fixed_review_case(self):
        _, case, revised = self.responded()
        self.pf.fx.submit(
            ResearchStep.M05,
            artifact=self.pf.fx.artifact("M05-W31-stale"),
            previous=self.pf.step_records[ResearchStep.M05])
        with self.assertRaisesRegex(EditorialReviewError, "current active M1"):
            self.reviewer.decide(self.final_request(
                case, revised, review_id="REVIEW-W31-STALE"))

    def test_draft_first_exposure_cannot_claim_hidden_author_or_prior_review(self):
        with self.assertRaisesRegex(ValidationError, "draft-first"):
            ReviewExposure(
                started_from_draft=True,
                author_self_assessment_seen=True,
                prior_review_seen=False,
                limitations=("Saw author summary",))
        with self.assertRaisesRegex(ValidationError, "exposure limitation"):
            ReviewExposure(
                started_from_draft=False,
                author_self_assessment_seen=False,
                prior_review_seen=False,
                limitations=())
        with self.assertRaises(ValidationError):
            ReviewExposure(
                started_from_draft=True,
                author_self_assessment_seen=False,
                prior_review_seen=False,
                answer_key_seen=True,
                limitations=())

    def test_model_review_needs_w19_receipt_and_is_not_writer_self_pass(self):
        configuration_sha256 = "f" * 64
        journal = OperationJournal(self.archive, self.rights)
        stored, _ = self.workflow.current_snapshot("DOSSIER-W29")
        operation = OperationRequest(
            operation_id="OP-W31-MISSING",
            idempotency_key="IDEM-W31-MISSING",
            run_id="RUN-W31",
            task_version_id=self.task.submission.version_id,
            step_id="W31", spec_sha256=self.pf.revision.spec_sha256,
            kind=OperationKind.MODEL,
            tool_id="OWNED-REVIEWER", tool_version="fixture-v1",
            provider_id="owned-provider",
            configuration_sha256=configuration_sha256,
            request_sha256="d" * 64,
            material_use=MaterialUse.MODEL_PROCESS,
            input_version_ids=(
                stored.submission.version_id,
                self.initial_article.submission.version_id,
                self.pf.revision.revision_id,
                self.task.submission.version_id,
                self.pf.step_records[ResearchStep.M10],
                self.pf.step_records[ResearchStep.M11],
                self.pf.step_records[ResearchStep.M12],
                self.prospective_output.source_advisor_output_version_id,
                self.prospective_output.source_teacher_output_version_id,
                self.prospective_result.prospective_output_version_id,
                *self.prospective_output.claim_version_ids,
                *self.prospective_output.evidence_version_ids,
                *self.prospective_output.claim_evidence_assessment_version_ids,
                *self.prospective_output.method_use_version_ids,
            ),
            created_at=self.time)
        request_stored = journal.begin(operation)
        request = self.open_request(
            execution_method=ExecutionMethod.ADMITTED_MODEL,
            model_admission_id="ADMISSION-W31",
            model_configuration_id="CONFIG-W31",
            operation_request_version_id=request_stored.submission.version_id,
            model_domains=("editorial-review",))
        fake_configuration = SimpleNamespace(
            configuration_sha256=configuration_sha256)
        with patch.object(
                self.reviewer.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.reviewer.model_admission, "load_configuration",
                    return_value=fake_configuration):
            with self.assertRaisesRegex(EditorialReviewError, "successful operation receipt"):
                self.reviewer.open_case(request)

        success_operation = operation.model_copy(update={
            "operation_id": "OP-W31-SUCCESS",
            "idempotency_key": "IDEM-W31-SUCCESS"})
        success = journal.begin(success_operation)
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
        valid = request.model_copy(update={
            "review_case_id": "REVIEW-CASE-W31-MODEL-SUCCESS",
            "operation_request_version_id": success.submission.version_id,
            "created_at": max(
                self.time, stored.submission.created_at)
            + timedelta(seconds=2)})
        with patch.object(
                self.reviewer.model_admission, "authorizes",
                return_value=True), patch.object(
                    self.reviewer.model_admission, "load_configuration",
                    return_value=fake_configuration):
            case = self.reviewer.open_case(valid)
        self.assertIs(case.state, ReviewCaseState.OPEN)

    def test_final_decision_is_concurrent_idempotent(self):
        _, case, revised = self.responded()
        request = self.final_request(case, revised)

        def worker(_):
            with Archive(self.archive.root) as archive:
                controller = EditorialReviewController(
                    archive, self.rights,
                    self.workflow.__class__(archive, self.rights))
                try:
                    return controller.decide(request)
                except Exception as exc:
                    return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(worker, range(2)))
        errors = [item for item in outcomes if isinstance(item, Exception)]
        self.assertFalse(errors, errors)
        self.assertEqual(outcomes[0], outcomes[1])
        decision = self.reviewer.adoption.load(
            outcomes[0].adoption_decision_version_id)
        self.assertIs(decision.state, StepState.READY)

    def test_forged_self_pass_or_library_score_is_rejected(self):
        _, case, revised = self.responded()
        result = self.reviewer.decide(self.final_request(case, revised))
        review = self.reviewer.load_review(result.review_version_id)
        forged = review.model_dump(mode="json")
        forged.update({
            "author_self_approved": True,
            "model_self_passed": True,
            "publication_authorized": True,
            "library_score": 99,
        })
        with self.assertRaises(ValidationError):
            EditorialReviewDecision.model_validate_json(canonical(forged))
        payload = self.open_request().model_dump(mode="json")
        payload["review_expected_result"] = "PASS"
        with self.assertRaisesRegex(ValidationError, "Extra inputs"):
            OpenReviewRequest.model_validate_json(canonical(payload))

    @staticmethod
    def revalidated(request):
        return OpenReviewRequest.model_validate_json(
            request.model_dump_json(warnings=False))


if __name__ == "__main__":
    unittest.main()
