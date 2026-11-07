"""W40 cross-module correction, current use and historical replay tests."""
from datetime import datetime, timedelta, timezone
import unittest

from intelligence.adoption import (AdoptionController, CheckerRole,
                                   DecisionRequest, StepState, StepSubmission)
from intelligence.archive import canonical
from intelligence.contracts import (MaterialUse, ObjectKind, ReferenceUse,
                                    Representation, ReviewCoverage,
                                    SourceTimes, UseContext, VersionReference,
                                    VersionSubmission)
from intelligence.correction import (CorrectionBeginRequest,
                                     CorrectionController, CorrectionKind,
                                     CorrectionRecoveryRequest,
                                     ImpactAssessmentRequest, ImpactOutcome,
                                     RecoveryBinding, VersionImpactDecision)
from intelligence.history import (HistoryArchiveController, HistoryMode,
                                  HistoryQueryRequest)


class CorrectionIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_presentation import EditionPresentationTests
        self.fx = EditionPresentationTests(
            methodName="test_composes_reviewed_readable_edition_without_publication_authority")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.archive = self.fx.archive
        self.rights = self.fx.rights
        self.correction = CorrectionController(self.archive, self.rights)
        self.adoption = AdoptionController(self.archive, self.rights)
        self.history = HistoryArchiveController(self.archive, self.rights)
        self.initial_edition = self.fx.controller.compose(
            self.fx.request())
        self.old_evidence = self.archive.get(
            self.fx.rf.pf.fx.evidence_version_id)
        self.time = max(
            self.fx.time, self.old_evidence.submission.created_at
        ) + timedelta(seconds=1)
        self.new_evidence = self.archive.append(VersionSubmission(
            schema_version=2,
            object_id=self.old_evidence.submission.object_id,
            version_id="EVIDENCE-W29-v002",
            parent_version_id=self.old_evidence.submission.version_id,
            kind=ObjectKind.EVIDENCE,
            title="Corrected Evidence",
            spec_sha256=self.old_evidence.submission.spec_sha256,
            created_at=self.time,
            rights=self.rights,
            representation=Representation.FULL_BODY),
            b"Owned corrected Evidence body")
        self.scope = ("W31_CONTENT_REVIEW", "B1_B2_C_ARTICLE")
        self.correction_result = self.correction.begin(
            CorrectionBeginRequest(
                correction_id="CORRECTION-W40",
                previous_version_id=(
                    self.old_evidence.submission.version_id),
                corrected_version_id=(
                    self.new_evidence.submission.version_id),
                kind=CorrectionKind.METHOD_OR_ARGUMENT_ERROR,
                reason="Owned integration correction of the research support",
                changed_at=self.time,
                affected_scopes=self.scope,
                adoption_decision_ids=(
                    self.fx.main_review.adoption_decision_version_id,),
                max_depth=20,
                scope_limitation=(
                    "Only explicit archive dependencies are covered"),
                created_at=self.time + timedelta(seconds=1)))

    def context(self, at):
        return UseContext(
            at=at, provider="owned-local", territory="NZ",
            content=("correction-integration",))

    def current_query(self, version_id):
        stored = self.archive.get(version_id)
        at = datetime.now(timezone.utc) + timedelta(seconds=2)
        return self.history.query(HistoryQueryRequest(
            query_id="W40-CURRENT-" + version_id,
            object_id=stored.submission.object_id,
            mode=HistoryMode.CURRENT,
            expected_kind=stored.submission.kind,
            intended_use=MaterialUse.STORE_BODY,
            use_context=self.context(at),
            include_body=True,
            required_scope=self.scope,
            created_at=at))

    def historical_query(self, version_id):
        stored = self.archive.get(version_id)
        at = datetime.now(timezone.utc) + timedelta(days=1)
        return self.history.query(HistoryQueryRequest(
            query_id="W40-HIST-" + version_id,
            object_id=stored.submission.object_id,
            mode=HistoryMode.KNOWN_TO_SYSTEM_AS_OF,
            at=at,
            expected_kind=stored.submission.kind,
            intended_use=MaterialUse.STORE_BODY,
            use_context=self.context(at),
            include_body=True,
            created_at=at))

    def test_correction_propagates_but_old_edition_cannot_be_recomposed(self):
        affected = set(self.correction_result.affected_version_ids)
        kinds = {
            self.archive.get(item).submission.kind
            for item in affected
        }
        self.assertIn(ObjectKind.EVIDENCE, kinds)
        self.assertIn(ObjectKind.RESEARCH_REVISION, kinds)
        self.assertIn(ObjectKind.ADVISOR_OUTPUT, kinds)
        self.assertIn(ObjectKind.TEACHER_OUTPUT, kinds)
        self.assertIn(ObjectKind.CONDITIONAL_OUTPUT, kinds)
        self.assertIn(ObjectKind.REVIEW, kinds)
        self.assertIn(ObjectKind.ARTICLE, kinds)
        self.assertIn(ObjectKind.EDITION, kinds)
        self.assertIn(
            self.initial_edition.edition_version_id, affected)
        self.assertFalse(self.adoption.is_current(
            self.fx.main_review.adoption_decision_version_id))

        current = self.current_query(
            self.fx.main_article.submission.version_id)
        historical = self.historical_query(
            self.fx.main_article.submission.version_id)
        self.assertFalse(current.body_available)
        self.assertTrue(any(
            "correction restriction" in item
            for item in current.limitations))
        self.assertTrue(historical.body_available)
        self.assertIn(
            "The commitment is documented",
            historical.body_text)
        edition_current = self.current_query(
            self.initial_edition.edition_version_id)
        self.assertFalse(edition_current.body_available)
        self.assertTrue(any(
            "correction restriction" in item
            for item in edition_current.limitations))

        with self.assertRaisesRegex(
                Exception, "Evidence is not the current version"):
            self.fx.controller.compose(self.fx.request(
                composition_id="COMPOSITION-W40-BLOCKED",
                coverage_end=self.time + timedelta(seconds=3),
                knowledge_cutoff=self.time + timedelta(seconds=3),
                created_at=self.time + timedelta(seconds=3)))

    def test_article_only_recovery_cannot_ignore_restricted_upstream_inputs(
            self):
        case = self.correction.load(
            self.correction_result.correction_case_version_id)
        decisions = []
        for version_id in case.affected_version_ids:
            stored = self.archive.get(version_id)
            if stored.submission.kind is ObjectKind.ARTICLE:
                decisions.append(VersionImpactDecision(
                    target_version_id=version_id,
                    outcome=ImpactOutcome.NARROWED,
                    retained_scope=self.scope,
                    remaining_support_version_ids=(
                        self.new_evidence.submission.version_id,),
                    reason="Owned correction narrows this Article",
                    next_owner="W40"))
            else:
                decisions.append(VersionImpactDecision(
                    target_version_id=version_id,
                    outcome=ImpactOutcome.UNRESOLVED,
                    reason="Explicit upstream dependency still requires recheck",
                    next_owner="T05"))
        assessed = self.correction.assess(ImpactAssessmentRequest(
            correction_case_version_id=(
                case.correction_case_version_id),
            decisions=tuple(decisions),
            unsearched_scope=("unlinked caches",),
            assessed_by="OWNED-W40-ASSESSOR",
            assessed_at=self.time + timedelta(seconds=2)))

        self.time += timedelta(seconds=3)
        article = self.archive.get(
            self.fx.main_article.submission.version_id)
        task = self.fx.rf.task
        recovery_review = self.archive.append(VersionSubmission(
            schema_version=2,
            object_id="REVIEW-W40-RECOVERY",
            version_id="REVIEW-W40-RECOVERY-v001",
            kind=ObjectKind.REVIEW,
            title="W40 bounded recovery review",
            spec_sha256=article.submission.spec_sha256,
            created_at=self.time,
            rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(
                VersionReference(
                    target_version_id=article.submission.version_id,
                    use=ReferenceUse.REVIEW_OF,
                    locator="target Article"),
                VersionReference(
                    target_version_id=(
                        assessed.correction_case_version_id),
                    use=ReferenceUse.BASIS,
                    locator="exact correction case"),
            ),
            review_coverage=(ReviewCoverage(
                task_version_id=task.submission.version_id,
                subject_version_id=article.submission.version_id,
                reviewed_scope=self.scope),)),
            b"Owned W40 bounded recovery review body")
        m10 = self.fx.rf.pf.step_records[
            __import__("intelligence.workflow", fromlist=[
                "ResearchStep"]).ResearchStep.M10]
        m11 = self.fx.rf.pf.step_records[
            __import__("intelligence.workflow", fromlist=[
                "ResearchStep"]).ResearchStep.M11]
        m12 = self.fx.rf.pf.step_records[
            __import__("intelligence.workflow", fromlist=[
                "ResearchStep"]).ResearchStep.M12]
        submission = self.adoption.submit(StepSubmission(
            schema_version=2,
            submission_id="SUB-W40-RECOVERY",
            work_id="W40",
            step_id="CONTENT_RECOVERY",
            spec_sha256=article.submission.spec_sha256,
            task_version_id=task.submission.version_id,
            subject_version_id=article.submission.version_id,
            producer_id="AUTHOR-W40",
            proposed_state=StepState.READY,
            claimed_scope=self.scope,
            input_version_ids=(
                article.submission.version_id, m10, m11, m12),
            evidence_version_ids=(
                recovery_review.submission.version_id,),
            gaps=(
                "Upstream M10-M12 remain under correction review",),
            created_at=self.time))
        self.adoption.decide(DecisionRequest(
            decision_id="DEC-W40-RECOVERY",
            submission_version_id=submission.submission.version_id,
            state=StepState.READY,
            checker_id="REVIEWER-W40",
            checker_role=CheckerRole.L5,
            review_version_id=(
                recovery_review.submission.version_id),
            allowed_scope=self.scope,
            reason="Owned Article-scope recovery after new Review",
            decided_at=self.time))
        self.assertFalse(self.adoption.is_current("DEC-W40-RECOVERY"))

        self.correction.recover(CorrectionRecoveryRequest(
            correction_case_version_id=(
                assessed.correction_case_version_id),
            expected_current_version_id=(
                assessed.correction_case_version_id),
            bindings=(RecoveryBinding(
                binding_id="RECOVERY-W40-ARTICLE",
                target_version_id=article.submission.version_id,
                recovery_review_version_id=(
                    recovery_review.submission.version_id),
                recovered_scope=self.scope,
                allowed_decision_ids=("DEC-W40-RECOVERY",)),),
            restored_by="OWNED-W40-RESTORER",
            reason="Recover Article scope only",
            restored_at=self.time + timedelta(seconds=1)))

        self.assertFalse(self.adoption.is_current("DEC-W40-RECOVERY"))
        self.assertFalse(self.adoption.authorizes(
            "DEC-W40-RECOVERY", self.scope))
        historical = self.historical_query(
            article.submission.version_id)
        self.assertTrue(historical.body_available)


if __name__ == "__main__":
    unittest.main()
