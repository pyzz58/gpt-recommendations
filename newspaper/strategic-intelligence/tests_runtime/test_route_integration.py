"""W36 offline R01/R07 route integration over the shared Archive.

The fixture is owned synthetic material. It proves interface composition,
copyable evidence and restart boundaries, not real research quality, model
reception, user reading, publication or production recovery.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from intelligence.archive import Archive, Conflict, MissingVersion
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState,
                                    ReferenceUse, Representation, RightsBasis,
                                    RightsGrant, Scope, ScopeMode, UseContext,
                                    UsePermission, ValidityMode,
                                    VersionReference, VersionSubmission)
from intelligence.editorial import EditorialController
from intelligence.editorial_review import (EditorialReviewController,
                                           ReviewDisposition)
from intelligence.gating import (AdmissionMode, BudgetEnvelope, BudgetLine,
                                 CapabilityAdmission, PreCallGate,
                                 ReservationEstimate)
from intelligence.history import (HistoryArchiveController, HistoryMode,
                                  HistoryQueryRequest)
from intelligence.operations import (AdapterDescriptor, AdapterReturn,
                                     CostObservation, ObservationKind,
                                     OperationKind, OperationRequest,
                                     OperationStatus)
from intelligence.presentation import EditionPresentationController
from intelligence.workflow import (DossierStartRequest, Participant,
                                   ParticipantQuestion, ResearchStep,
                                   ResearchStepSubmission,
                                   ResearchWorkflowController,
                                   StepDisposition, StepOwner)


class _GatedAdapter:
    def __init__(self):
        self.calls = 0

    def descriptor(self):
        return AdapterDescriptor(
            tool_id="tool-w36", tool_version="1.0.0",
            provider_id="provider-w36", max_internal_retries=0)

    def invoke(self, operation, payload):
        self.calls += 1
        started = datetime.now(timezone.utc)
        return AdapterReturn(
            status=OperationStatus.SUCCEEDED,
            provider_request_id="provider-request-w36",
            response_body=b"Owned W36 gated result",
            usage=(),
            cost=CostObservation(
                kind=ObservationKind.ACTUAL,
                amount=Decimal("0.03"),
                currency="USD",
                basis="Owned W36 adapter observation"),
            error_code=None,
            error_message=None,
            observed_internal_retries=0,
            started_at=started,
            ended_at=started + timedelta(seconds=1))


class RouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_presentation import EditionPresentationTests
        self.fx = EditionPresentationTests(
            methodName="test_composes_reviewed_readable_edition_without_publication_authority")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.archive = self.fx.archive
        self.rights = self.fx.rights

    def _current_query(self, version_id, index):
        stored = self.archive.get(version_id)
        at = self.fx.time + timedelta(minutes=2)
        return HistoryArchiveController(
            self.archive, self.rights).query(HistoryQueryRequest(
                query_id=f"W36-QUERY-{index}",
                object_id=stored.submission.object_id,
                mode=HistoryMode.CURRENT,
                intended_use=MaterialUse.INDEX,
                use_context=UseContext(
                    at=at, provider="owned-local", territory="NZ",
                    content=("w36-route",)),
                include_body=False,
                created_at=at))

    def test_discovery_to_reviewed_edition_is_replayable_in_one_chain(self):
        proposal = self.fx.editorial.load_current_edition_proposal(
            "EDITION-PROPOSAL-W32")
        decision = self.fx.editorial.current_decision("TOPIC-W32")
        admission = self.fx.editorial.load_research_admission(
            "ADMISSION-W32")
        self.assertEqual(decision.decision_id, proposal.placements[0].topic_decision_id)
        self.assertEqual(
            admission.research_admission_id,
            proposal.placements[0].research_admission_id)
        self.assertFalse(admission.publication_authorized)

        result = self.fx.controller.compose(self.fx.request())
        edition = self.fx.controller.load_edition(
            result.edition_version_id)
        self.assertFalse(edition.publication_authorized)
        self.assertFalse(edition.delivery_authorized)
        self.assertTrue(edition.content_review_required)
        self.assertEqual(
            hashlib.sha256(Path(result.output_path).read_bytes()).hexdigest(),
            result.output_sha256)
        self.assertEqual(
            os.stat(result.output_path).st_size, result.output_bytes)

        article_stored = self.archive.get(
            self.fx.main_article.submission.version_id)
        self.assertIn(
            self.fx.w23_decision_version_id,
            {item.target_version_id
             for item in article_stored.submission.references})
        self.assertIn(
            self.fx.w23_admission_version_id,
            {item.target_version_id
             for item in article_stored.submission.references})
        review = self.fx.rf.reviewer.load_review(
            self.fx.main_review.review_version_id)
        self.assertIs(review.decision, ReviewDisposition.PASS)
        self.assertFalse(review.author_self_approved)
        self.assertFalse(review.publication_authorized)

        chain_versions = (
            self.fx.index_stored.submission.version_id,
            self.fx.discovery_stored.submission.version_id,
            self.fx.coverage_plan_stored.submission.version_id,
            self.fx.coverage_audit_stored.submission.version_id,
            self.fx.package_stored.submission.version_id,
            self.fx.w23_decision_version_id,
            self.fx.w23_admission_version_id,
            self.fx.proposal.submission.version_id,
            self.fx.main_article.submission.version_id,
            self.fx.main_review.review_version_id,
            self.fx.main_review.adoption_decision_version_id,
            result.edition_version_id,
        )
        for index, version_id in enumerate(chain_versions):
            replay = self._current_query(version_id, index)
            self.assertEqual(replay.current_version_id, version_id)

        html = Path(result.output_path).read_text(encoding="utf-8")
        self.assertIn("Bounded Commitment", html)
        self.assertIn(
            "The commitment is documented, while execution remains unobserved.",
            html)
        self.assertNotIn("<script>alert", html)

    def test_restart_rehydrates_archive_state_and_rejects_chat_summary(self):
        stored, snapshot = self.fx.rf.pf.workflow.current_snapshot(
            "DOSSIER-W29")
        restarted = ResearchWorkflowController(
            self.archive, self.rights)
        restarted.restore_checkpoint(stored.submission.version_id)
        checkpoint = restarted.checkpoint_values(
            snapshot.graph_thread_id)
        self.assertEqual(checkpoint["active_steps"][-1][0], "M12")
        self.assertEqual(
            set(checkpoint["completed_steps"]),
            {item.step.value for item in snapshot.active_steps})

        reopened_review = EditorialReviewController(
            self.archive, self.rights)
        self.assertIs(
            reopened_review.load_review(
                self.fx.main_review.review_version_id).decision,
            ReviewDisposition.PASS)
        self.assertTrue(reopened_review.adoption.is_current(
            self.fx.main_review.adoption_decision_version_id))
        reopened_presentation = EditionPresentationController(
            self.archive, self.rights, reopened_review,
            reopened_review.adoption)
        self.assertEqual(
            reopened_presentation.editorial.load_current_edition_proposal(
                "EDITION-PROPOSAL-W32").edition_id,
            "EDITION-W32")

        with self.assertRaises(MissingVersion):
            restarted.restore_checkpoint(
                "CHAT-SUMMARY-IS-NOT-A-DOSSIER-SNAPSHOT")

        revision = self.fx.rf.pf.revision
        resumed_at = self.fx.time + timedelta(minutes=5)
        resumed_workflow = ResearchWorkflowController(
            self.archive, self.rights)
        resumed_workflow.start_dossier(DossierStartRequest(
            dossier_id="DOSSIER-W36-RESUME",
            theme_id=revision.theme_id,
            spec_sha256=revision.spec_sha256,
            revision_id=revision.revision_id,
            question_version_id=revision.question_version_id,
            knowledge_cutoff=resumed_at,
            created_at=resumed_at))

        def artifact(step):
            return self.archive.append(VersionSubmission(
                schema_version=2,
                object_id=f"ARTIFACT-W36-{step.value}",
                version_id=f"ARTIFACT-W36-{step.value}-v001",
                kind=ObjectKind.ARTICLE,
                title=f"Owned W36 {step.value} artifact",
                spec_sha256=revision.spec_sha256,
                created_at=resumed_at,
                rights=self.rights,
                representation=Representation.FULL_BODY,
                references=(VersionReference(
                    target_version_id=revision.revision_id,
                    use=ReferenceUse.BASIS,
                    locator="exact resumed research revision"),)),
                f"Owned W36 {step.value} artifact".encode())

        first_stored, _ = resumed_workflow.current_snapshot(
            "DOSSIER-W36-RESUME")
        first = resumed_workflow.submit_step(ResearchStepSubmission(
            step_record_id="STEP-W36-M01-001",
            previous_step_record_version_id=None,
            dossier_id="DOSSIER-W36-RESUME",
            expected_snapshot_version_id=(
                first_stored.submission.version_id),
            theme_id=revision.theme_id,
            spec_sha256=revision.spec_sha256,
            revision_id=revision.revision_id,
            step=ResearchStep.M01,
            owner=StepOwner.JOINT,
            disposition=StepDisposition.READY_FOR_NEXT,
            artifact_version_ids=(
                artifact(ResearchStep.M01).submission.version_id,),
            created_at=resumed_at + timedelta(seconds=1)))
        first_snapshot = resumed_workflow.load_snapshot(
            first.submission.version_id)
        first_record = next(
            item.record_version_id
            for item in first_snapshot.active_steps
            if item.step is ResearchStep.M01)

        after_loss = ResearchWorkflowController(
            self.archive, self.rights)
        after_loss.restore_checkpoint(first.submission.version_id)
        resumed_values = after_loss.checkpoint_values(
            first_snapshot.graph_thread_id)
        self.assertEqual(resumed_values["completed_steps"], ["M01"])
        second_stored, _ = after_loss.current_snapshot(
            "DOSSIER-W36-RESUME")
        after_loss.submit_step(ResearchStepSubmission(
            step_record_id="STEP-W36-M02-001",
            previous_step_record_version_id=None,
            dossier_id="DOSSIER-W36-RESUME",
            expected_snapshot_version_id=(
                second_stored.submission.version_id),
            theme_id=revision.theme_id,
            spec_sha256=revision.spec_sha256,
            revision_id=revision.revision_id,
            step=ResearchStep.M02,
            owner=StepOwner.JOINT,
            disposition=StepDisposition.READY_FOR_NEXT,
            artifact_version_ids=(
                artifact(ResearchStep.M02).submission.version_id,),
            participant_questions=(
                ParticipantQuestion(
                    participant=Participant.B1,
                    question="Which bounded action could this evidence alter?",
                    rationale="B1 joins at M02"),
                ParticipantQuestion(
                    participant=Participant.B2,
                    question="Which transferable mechanism should be taught?",
                    rationale="B2 joins at M02"),
            ),
            created_at=resumed_at + timedelta(seconds=2)))
        final_resume = after_loss.current_snapshot(
            "DOSSIER-W36-RESUME")[1]
        by_step = {item.step: item for item in final_resume.active_steps}
        self.assertEqual(
            set(by_step), {ResearchStep.M01, ResearchStep.M02})
        self.assertEqual(by_step[ResearchStep.M01].record_version_id,
                         first_record)
        self.assertEqual(
            sum(item.step is ResearchStep.M02
                for item in final_resume.active_steps), 1)

    def test_external_identity_and_budget_survive_controller_restart(self):
        now = datetime.now(timezone.utc)
        internal = self.rights
        material_rights = RightsGrant(
            rights_id="RIGHTS-W36-OP",
            basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({
                MaterialUse.INDEX,
                MaterialUse.STORE_BODY,
                MaterialUse.MODEL_PROCESS,
            }),
            evidence="Owned W36 operation fixture",
            checked_by="test fixture",
            checked_at=now - timedelta(hours=1),
            permissions=(
                UsePermission(
                    use=MaterialUse.STORE_BODY,
                    state=PermissionState.ALLOWED,
                    validity=ValidityMode.OPEN_ENDED,
                    territories=Scope(mode=ScopeMode.ANY),
                    providers=Scope(mode=ScopeMode.ANY),
                    content_scope=Scope(mode=ScopeMode.ANY)),
                UsePermission(
                    use=MaterialUse.MODEL_PROCESS,
                    state=PermissionState.ALLOWED,
                    validity=ValidityMode.OPEN_ENDED,
                    territories=Scope(
                        mode=ScopeMode.LIST, values=("NZ",)),
                    providers=Scope(
                        mode=ScopeMode.LIST, values=("provider-w36",)),
                    content_scope=Scope(mode=ScopeMode.ANY),
                    conditions_satisfied=True),
            ))
        spec = self.fx.rf.pf.revision.spec_sha256

        def store(object_id, version_id, kind, rights, references=()):
            return self.archive.append(VersionSubmission(
                schema_version=2,
                object_id=object_id,
                version_id=version_id,
                kind=kind,
                title=f"Owned W36 operation {object_id}",
                spec_sha256=spec,
                created_at=now - timedelta(minutes=30),
                rights=rights,
                representation=Representation.FULL_BODY,
                references=tuple(references)),
                f"Owned W36 operation body {object_id}".encode())

        task = store(
            "TASK-W36-OP", "TASK-W36-OP-v001", ObjectKind.TASK, internal)
        review = store(
            "REVIEW-W36-OP", "REVIEW-W36-OP-v001",
            ObjectKind.REVIEW, internal,
            (VersionReference(
                target_version_id=task.submission.version_id,
                use=ReferenceUse.REVIEW_OF,
                locator="exact W36 operation task"),))
        material = store(
            "SOURCE-W36-OP", "SOURCE-W36-OP-v001",
            ObjectKind.DOCUMENT, material_rights)
        payload = b"Owned W36 bounded operation input"
        budget = BudgetEnvelope(
            budget_id="BUDGET-W36-OP",
            run_id="RUN-W36-OP",
            task_version_id=task.submission.version_id,
            quotas=(
                BudgetLine(metric="calls", amount=Decimal("2")),
                BudgetLine(metric="cost:USD", amount=Decimal("1.00")),
            ),
            valid_from=now - timedelta(minutes=20),
            valid_until=now + timedelta(days=1),
            created_at=now - timedelta(minutes=20))
        admission = CapabilityAdmission(
            admission_id="ADMISSION-W36-OP",
            spec_sha256=spec,
            task_version_id=task.submission.version_id,
            step_ids=("M10",),
            provider_id="provider-w36",
            tool_id="tool-w36",
            tool_version="1.0.0",
            configuration_sha256="c" * 64,
            operation_kinds=(OperationKind.MODEL,),
            material_uses=(MaterialUse.MODEL_PROCESS,),
            territory="NZ",
            external_processing_allowed=True,
            budget_id=budget.budget_id,
            max_attempts=1,
            max_internal_retries=0,
            mode=AdmissionMode.CONTROLLED_TRIAL,
            review_version_id=review.submission.version_id,
            valid_from=now - timedelta(minutes=10),
            valid_until=now + timedelta(days=1),
            created_at=now - timedelta(minutes=10))
        request = OperationRequest(
            operation_id="OP-W36-RESTART",
            idempotency_key="LOGICAL-W36-RESTART",
            run_id=budget.run_id,
            task_version_id=task.submission.version_id,
            step_id="M10",
            spec_sha256=spec,
            kind=OperationKind.MODEL,
            tool_id=admission.tool_id,
            tool_version=admission.tool_version,
            provider_id=admission.provider_id,
            configuration_sha256=admission.configuration_sha256,
            request_sha256=hashlib.sha256(payload).hexdigest(),
            material_use=MaterialUse.MODEL_PROCESS,
            input_version_ids=(material.submission.version_id,),
            attempt_number=1,
            max_attempts=1,
            created_at=now - timedelta(minutes=5))
        estimate = ReservationEstimate(
            operation_id=request.operation_id,
            basis=ObservationKind.ESTIMATED,
            lines=(
                BudgetLine(metric="calls", amount=Decimal("1")),
                BudgetLine(metric="cost:USD", amount=Decimal("0.10")),
            ))
        gate = PreCallGate(self.archive, internal)
        gate.create_budget(budget)
        gate.append_admission(admission)
        adapter = _GatedAdapter()
        first = gate.execute(
            admission.admission_id, request, adapter, payload, estimate)
        self.assertEqual(adapter.calls, 1)
        first_receipt = first.run.receipt.submission.version_id
        state = gate.ledger.state(budget.budget_id)
        self.assertEqual(state.consumed["calls"], Decimal("1"))
        self.assertEqual(state.consumed["cost:usd"], Decimal("0.03"))
        self.assertEqual(state.remaining["cost:usd"], Decimal("0.97"))

        restarted = PreCallGate(self.archive, internal)
        duplicate_adapter = _GatedAdapter()
        with self.assertRaises(Conflict):
            restarted.execute(
                admission.admission_id, request,
                duplicate_adapter, payload, estimate)
        self.assertEqual(duplicate_adapter.calls, 0)
        self.assertEqual(
            restarted.journal.receipt(request.operation_id).recorded_at,
            gate.journal.receipt(request.operation_id).recorded_at)
        self.assertEqual(
            first_receipt,
            self.archive.get(first_receipt).submission.version_id)
        self.assertEqual(
            restarted.ledger.state(budget.budget_id).consumed,
            state.consumed)


if __name__ == "__main__":
    unittest.main()
