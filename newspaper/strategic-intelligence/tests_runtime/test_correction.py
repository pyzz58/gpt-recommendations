"""W34 owned-fixture tests for correction dependency limits and recovery."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.adoption import (AdoptionController, CheckerRole,
                                   DecisionRequest, StepState, StepSubmission)
from intelligence.archive import Archive, PermissionDenied
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState,
                                    Precision, ReferenceUse, Representation,
                                    ReviewCoverage, RightsBasis, RightsGrant,
                                    Scope, ScopeMode, SourceTimes, TimePoint,
                                    UseContext, UsePermission, ValidityMode,
                                    VersionReference, VersionSubmission)
from intelligence.correction import (CorrectionBeginRequest,
                                     CorrectionController,
                                     CorrectionError, CorrectionKind,
                                     CorrectionPhase,
                                     CorrectionRecoveryRequest,
                                     CorrectionResult, ImpactAssessmentRequest,
                                     ImpactOutcome, RecoveryBinding,
                                     VersionImpactDecision,
                                     is_version_restricted)
from intelligence.history import (HistoryArchiveController, HistoryMode,
                                  HistoryQueryRequest)

BASE = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.rights = RightsGrant(
            rights_id="RIGHTS-W34", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({
                MaterialUse.INDEX, MaterialUse.STORE_BODY,
                MaterialUse.MODEL_PROCESS}),
            evidence="Owned W34 correction fixture", checked_by="test fixture",
            checked_at=BASE,
            permissions=tuple(UsePermission(
                use=use, state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY))
                for use in (
                    MaterialUse.STORE_BODY, MaterialUse.MODEL_PROCESS)))
        self.time = BASE + timedelta(seconds=1)
        self.correction = CorrectionController(
            self.archive, self.rights)
        self.adoption = AdoptionController(
            self.archive, self.rights)
        self.task = self.store(
            "TASK-W34", "TASK-W34-v001", ObjectKind.TASK,
            b"Owned correction task")
        self.source_old = self.store(
            "SOURCE-W34", "SOURCE-W34-v001", ObjectKind.DOCUMENT,
            b"Old source says 100", published=True)
        self.source_new = self.store(
            "SOURCE-W34", "SOURCE-W34-v002", ObjectKind.DOCUMENT,
            b"Corrected source says 90", published=True,
            parent=self.source_old.submission.version_id)
        self.evidence = self.store(
            "EVIDENCE-W34", "EVIDENCE-W34-v001", ObjectKind.EVIDENCE,
            b"Owned evidence uses old source",
            references=(VersionReference(
                target_version_id=self.source_old.submission.version_id,
                use=ReferenceUse.SOURCE, locator="old figure"),))
        self.claim = self.store(
            "CLAIM-W34", "CLAIM-W34-v001", ObjectKind.CLAIM,
            b"Owned claim uses the evidence",
            references=(VersionReference(
                target_version_id=self.evidence.submission.version_id,
                use=ReferenceUse.SUPPORT, locator="numeric support"),))
        self.article = self.store(
            "ARTICLE-W34", "ARTICLE-W34-v001", ObjectKind.ARTICLE,
            b"Owned Article repeats the affected claim",
            references=(VersionReference(
                target_version_id=self.claim.submission.version_id,
                use=ReferenceUse.BASIS, locator="affected claim"),))
        self.review = self.store(
            "REVIEW-W34", "REVIEW-W34-v001", ObjectKind.REVIEW,
            b"Owned initial PASS",
            references=(VersionReference(
                target_version_id=self.article.submission.version_id,
                use=ReferenceUse.REVIEW_OF, locator="initial Article"),),
            review_coverage=(ReviewCoverage(
                task_version_id=self.task.submission.version_id,
                subject_version_id=self.article.submission.version_id,
                reviewed_scope=("publication",)),))
        self.initial_decision = self.make_adoption(
            article=self.article, review=self.review,
            submission_id="SUB-W34-v001", decision_id="DEC-W34-v001",
            work_id="W34", checker="REVIEWER-W34")
        self.unrelated_article = self.store(
            "ARTICLE-UNRELATED", "ARTICLE-UNRELATED-v001",
            ObjectKind.ARTICLE, b"Unrelated Article")
        unrelated_review = self.store(
            "REVIEW-UNRELATED", "REVIEW-UNRELATED-v001",
            ObjectKind.REVIEW, b"Unrelated review",
            references=(VersionReference(
                target_version_id=self.unrelated_article.submission.version_id,
                use=ReferenceUse.REVIEW_OF, locator="unrelated Article"),),
            review_coverage=(ReviewCoverage(
                task_version_id=self.task.submission.version_id,
                subject_version_id=(
                    self.unrelated_article.submission.version_id),
                reviewed_scope=("publication",)),))
        self.unrelated_decision = self.make_adoption(
            article=self.unrelated_article, review=unrelated_review,
            submission_id="SUB-UNRELATED-v001",
            decision_id="DEC-UNRELATED-v001",
            work_id="W34-UNRELATED", checker="REVIEWER-UNRELATED")

    def store(self, object_id, version_id, kind, body, *, parent=None,
              references=(), published=True, review_coverage=()):
        self.time += timedelta(seconds=1)
        source_times = SourceTimes(published=TimePoint(
            precision=Precision.INSTANT, value=self.time.isoformat(),
            source_timezone="UTC",
            provenance="owned fixture")) if published else SourceTimes()
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            parent_version_id=parent, kind=kind, title=object_id,
            spec_sha256="a" * 64, created_at=self.time,
            source_times=source_times, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(references),
            review_coverage=tuple(review_coverage)), body)

    def make_adoption(self, *, article, review, submission_id, decision_id,
                      work_id, checker):
        submission = self.adoption.submit(StepSubmission(
            schema_version=2, submission_id=submission_id,
            work_id=work_id, step_id="CONTENT",
            spec_sha256="a" * 64,
            task_version_id=self.task.submission.version_id,
            subject_version_id=article.submission.version_id,
            producer_id="AUTHOR-W34", proposed_state=StepState.READY,
            claimed_scope=("publication",),
            input_version_ids=(article.submission.version_id,),
            evidence_version_ids=(review.submission.version_id,),
            created_at=self.time))
        self.adoption.decide(DecisionRequest(
            decision_id=decision_id,
            submission_version_id=submission.submission.version_id,
            state=StepState.READY,
            checker_id=checker, checker_role=CheckerRole.L5,
            review_version_id=review.submission.version_id,
            allowed_scope=("publication",),
            reason="Owned initial adoption",
            decided_at=self.time))
        return self.adoption.load(decision_id)

    def begin(self):
        self.time += timedelta(seconds=1)
        return self.correction.begin(CorrectionBeginRequest(
            correction_id="CORRECTION-W34",
            previous_version_id=self.source_old.submission.version_id,
            corrected_version_id=self.source_new.submission.version_id,
            kind=CorrectionKind.SOURCE_CORRECTION,
            reason="Owned source number corrected from 100 to 90",
            changed_at=self.time,
            affected_scopes=("publication",),
            adoption_decision_ids=(
                self.initial_decision.decision_id,),
            max_depth=12,
            scope_limitation=(
                "Uses not linked by explicit archive references remain outside this graph"),
            created_at=self.time))

    def assess(self, result: CorrectionResult):
        case = self.correction.load(result.correction_case_version_id)
        decisions = []
        for version_id in case.affected_version_ids:
            if version_id == self.article.submission.version_id:
                decisions.append(VersionImpactDecision(
                    target_version_id=version_id,
                    outcome=ImpactOutcome.NARROWED,
                    retained_scope=("publication",),
                    remaining_support_version_ids=(
                        self.source_new.submission.version_id,),
                    reason="Corrected figure supports only narrowed use",
                    next_owner="W40"))
            else:
                decisions.append(VersionImpactDecision(
                    target_version_id=version_id,
                    outcome=ImpactOutcome.UNRESOLVED,
                    reason="Dependent requires bounded recheck",
                    next_owner="T05"))
        self.time += timedelta(seconds=1)
        return self.correction.assess(ImpactAssessmentRequest(
            correction_case_version_id=result.correction_case_version_id,
            decisions=tuple(decisions),
            unsearched_scope=("unlinked external caches",),
            assessed_by="OWNED-W34-ASSESSOR",
            assessed_at=self.time))

    def recovery_review(self, case_version_id):
        self.time += timedelta(seconds=1)
        return self.store(
            "REVIEW-RECOVERY-W34", "REVIEW-RECOVERY-W34-v001",
            ObjectKind.REVIEW, b"Owned new recovery review",
            references=(
                VersionReference(
                    target_version_id=self.article.submission.version_id,
                    use=ReferenceUse.REVIEW_OF,
                    locator="recovered Article content"),
                VersionReference(
                    target_version_id=case_version_id,
                    use=ReferenceUse.BASIS,
                    locator="exact correction case"),
            ),
            review_coverage=(ReviewCoverage(
                task_version_id=self.task.submission.version_id,
                subject_version_id=self.article.submission.version_id,
                reviewed_scope=("publication",)),))

    def new_decision(self, review, *, decision_id="DEC-W34-RECOVERY"):
        initial_submission = self.archive.get(
            self.initial_decision.submission_version_id)
        old_submission = StepSubmission.model_validate_json(
            self.archive.read_body(initial_submission.submission.version_id))
        new_submission = self.adoption.submit(old_submission.model_copy(update={
            "submission_id": "SUB-W34-RECOVERY-v001",
            "evidence_version_ids": (
                *old_submission.evidence_version_ids,
                review.submission.version_id),
            "created_at": self.time,
        }))
        self.adoption.decide(DecisionRequest(
            decision_id=decision_id,
            submission_version_id=new_submission.submission.version_id,
            state=StepState.READY,
            checker_id="RECOVERY-REVIEWER-W34",
            checker_role=CheckerRole.L5,
            review_version_id=review.submission.version_id,
            allowed_scope=("publication",),
            reason="Owned correction recovery after new Review",
            decided_at=self.time))
        return self.adoption.load(decision_id)

    def test_begin_restricts_explicit_dependents_and_preserves_unrelated(self):
        result = self.begin()
        affected = set(result.affected_version_ids)
        self.assertIn(self.source_old.submission.version_id, affected)
        self.assertIn(self.evidence.submission.version_id, affected)
        self.assertIn(self.claim.submission.version_id, affected)
        self.assertIn(self.article.submission.version_id, affected)
        self.assertFalse(self.adoption.is_current(
            self.initial_decision.decision_id, self.time))
        self.assertTrue(self.adoption.is_current(
            self.unrelated_decision.decision_id, self.time))
        self.assertTrue(is_version_restricted(
            self.archive, self.article.submission.version_id,
            ("publication",)))
        self.assertFalse(is_version_restricted(
            self.archive, self.unrelated_article.submission.version_id,
            ("publication",)))

    def test_assessment_must_cover_every_explicit_dependency(self):
        result = self.begin()
        case = self.correction.load(result.correction_case_version_id)
        with self.assertRaisesRegex(CorrectionError, "every explicit dependent"):
            self.correction.assess(ImpactAssessmentRequest(
                correction_case_version_id=result.correction_case_version_id,
                decisions=(VersionImpactDecision(
                    target_version_id=self.article.submission.version_id,
                    outcome=ImpactOutcome.UNRESOLVED,
                    reason="Only one item", next_owner="T05"),),
                assessed_by="OWNED", assessed_at=self.time))
        self.assertEqual(case.phase, CorrectionPhase.RESTRICTED)

    def test_recovery_needs_new_review_and_old_adoption_stays_blocked(self):
        result = self.begin()
        assessed = self.assess(result)
        with self.assertRaisesRegex(CorrectionError, "does not cover"):
            self.correction.recover(CorrectionRecoveryRequest(
                correction_case_version_id=assessed.correction_case_version_id,
                expected_current_version_id=(
                    assessed.correction_case_version_id),
                bindings=(RecoveryBinding(
                    binding_id="BAD-RECOVERY",
                    target_version_id=self.article.submission.version_id,
                    recovery_review_version_id=(
                        self.review.submission.version_id),
                    recovered_scope=("publication",)),),
                restored_by="OWNED-W34",
                reason="Attempt with old review",
                restored_at=self.time))
        recovery_review = self.recovery_review(
            assessed.correction_case_version_id)
        self.time += timedelta(seconds=1)
        new_decision = self.new_decision(recovery_review)
        self.assertFalse(self.adoption.is_current(
            new_decision.decision_id, self.time))
        recovered = self.correction.recover(CorrectionRecoveryRequest(
            correction_case_version_id=assessed.correction_case_version_id,
            expected_current_version_id=assessed.correction_case_version_id,
            bindings=(RecoveryBinding(
                binding_id="RECOVERY-ARTICLE",
                target_version_id=self.article.submission.version_id,
                recovery_review_version_id=(
                    recovery_review.submission.version_id),
                recovered_scope=("publication",),
                allowed_decision_ids=(new_decision.decision_id,)),),
            restored_by="OWNED-W34",
            reason="Recover only the reviewed Article scope",
            restored_at=self.time + timedelta(seconds=1)))
        self.assertEqual(recovered.phase, CorrectionPhase.RECOVERED)
        self.assertTrue(self.adoption.is_current(
            new_decision.decision_id, self.time + timedelta(seconds=2)))
        self.assertFalse(self.adoption.is_current(
            self.initial_decision.decision_id,
            self.time + timedelta(seconds=2)))
        self.assertTrue(is_version_restricted(
            self.archive, self.evidence.submission.version_id,
            ("publication",)))

    def test_current_body_is_restricted_but_historical_body_remains(self):
        result = self.begin()
        history = HistoryArchiveController(self.archive, self.rights)
        historical_at = max(
            self.time,
            datetime.now(timezone.utc)) + timedelta(seconds=1)
        current = history.query(HistoryQueryRequest(
            query_id="W34-CURRENT", object_id="ARTICLE-W34",
            mode=HistoryMode.CURRENT,
            intended_use=MaterialUse.MODEL_PROCESS,
            use_context=UseContext(
                at=self.time, provider="owned", territory="NZ"),
            include_body=True, required_scope=("publication",),
            created_at=self.time))
        historical = history.query(HistoryQueryRequest(
            query_id="W34-HISTORICAL", object_id="ARTICLE-W34",
            mode=HistoryMode.KNOWN_TO_SYSTEM_AS_OF, at=historical_at,
            intended_use=MaterialUse.MODEL_PROCESS,
            use_context=UseContext(
                at=historical_at, provider="owned", territory="NZ"),
            include_body=True, created_at=historical_at))
        self.assertFalse(current.body_available)
        self.assertTrue(any(
            "correction restriction" in item
            for item in current.limitations))
        self.assertTrue(historical.body_available)

    def test_corrected_version_must_be_same_object_and_later(self):
        other = self.store(
            "OTHER-SOURCE", "OTHER-SOURCE-v001", ObjectKind.DOCUMENT,
            b"Other source")
        with self.assertRaisesRegex(CorrectionError, "does not follow"):
            self.correction.begin(CorrectionBeginRequest(
                correction_id="BAD-CORRECTION",
                previous_version_id=self.source_old.submission.version_id,
                corrected_version_id=other.submission.version_id,
                kind=CorrectionKind.SOURCE_CORRECTION,
                reason="Bad identity",
                changed_at=self.time,
                affected_scopes=("publication",),
                scope_limitation="owned", created_at=self.time))

    def test_unlinked_adoption_cannot_be_forced_into_dependency_graph(self):
        with self.assertRaisesRegex(CorrectionError, "outside the explicit"):
            self.correction.begin(CorrectionBeginRequest(
                correction_id="BAD-ADOPTION-GRAPH",
                previous_version_id=self.source_old.submission.version_id,
                corrected_version_id=self.source_new.submission.version_id,
                kind=CorrectionKind.SOURCE_CORRECTION,
                reason="Owned",
                changed_at=self.time,
                affected_scopes=("publication",),
                adoption_decision_ids=(
                    self.unrelated_decision.decision_id,),
                scope_limitation="owned", created_at=self.time))

    def test_retracted_content_cannot_be_restored_as_same_version(self):
        result = self.begin()
        case = self.correction.load(result.correction_case_version_id)
        decisions = tuple(
            VersionImpactDecision(
                target_version_id=version_id,
                outcome=(
                    ImpactOutcome.RETRACTED
                    if version_id == self.article.submission.version_id
                    else ImpactOutcome.UNRESOLVED),
                reason="Owned classification", next_owner="W40")
            for version_id in case.affected_version_ids)
        self.time += timedelta(seconds=1)
        assessed = self.correction.assess(ImpactAssessmentRequest(
            correction_case_version_id=result.correction_case_version_id,
            decisions=decisions, assessed_by="OWNED", assessed_at=self.time))
        review = self.recovery_review(
            assessed.correction_case_version_id)
        with self.assertRaisesRegex(CorrectionError, "Retracted"):
            self.correction.recover(CorrectionRecoveryRequest(
                correction_case_version_id=assessed.correction_case_version_id,
                expected_current_version_id=(
                    assessed.correction_case_version_id),
                bindings=(RecoveryBinding(
                    binding_id="RETRACTED-RECOVERY",
                    target_version_id=self.article.submission.version_id,
                    recovery_review_version_id=review.submission.version_id,
                    recovered_scope=("publication",)),),
                restored_by="OWNED", reason="Should fail",
                restored_at=self.time))

    def test_missing_scope_and_support_are_explicit(self):
        with self.assertRaisesRegex(ValidationError, "unique affected"):
            CorrectionBeginRequest(
                correction_id="NO-SCOPE",
                previous_version_id=self.source_old.submission.version_id,
                corrected_version_id=self.source_new.submission.version_id,
                kind=CorrectionKind.SOURCE_CORRECTION,
                reason="Owned", changed_at=self.time,
                affected_scopes=(), scope_limitation="Owned",
                created_at=self.time)
        with self.assertRaisesRegex(ValidationError, "remaining exact support"):
            VersionImpactDecision(
                target_version_id=self.article.submission.version_id,
                outcome=ImpactOutcome.MAINTAINED,
                reason="No support left", next_owner="W40")
        result = self.begin()
        assessed = self.assess(result)
        self.assertIn(
            "unlinked external caches", assessed.unsearched_scope)


if __name__ == "__main__":
    unittest.main()
