"""W39 owned-fixture two-snapshot theme continuation and T03 re-entry."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.archive import canonical
from intelligence.contracts import (ObjectKind, Precision, ReferenceUse,
                                    Representation, SourceTimes, TimePoint,
                                    UseContext, VersionReference,
                                    VersionSubmission)
from intelligence.editorial import (DecisionStage, PublicationBasis,
                                    TopicDecision, TopicDecisionCode,
                                    ValueBasis)
from intelligence.evidence import (EvidenceRelation, SupplementImpact,
                                   SupplementStatus)
from intelligence.weekly_continuation import (
    ContinuationDisposition, CrossWeekContinuationController,
    CrossWeekContinuationError, CrossWeekContinuationRequest, IssueSnapshot,
    TemporalEvidenceScope)


class FixedDateTime(datetime):
    value = datetime(2026, 10, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.value if tz is None else cls.value.astimezone(tz)


class CrossWeekContinuationTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_supplement_route import TargetedSupplementRouteTests
        self.sf = TargetedSupplementRouteTests(
            methodName="test_independent_evidence_strengthens_without_automatic_pass")
        self.sf.setUp()
        self.addCleanup(self.sf.doCleanups)
        self.archive = self.sf.archive
        self.rights = self.sf.rights
        self.controller = CrossWeekContinuationController(
            self.archive, self.rights)
        self.earlier = IssueSnapshot(
            issue_id="WEEKLY-2026-W43",
            coverage_start=datetime(
                2026, 10, 23, 0, 0, tzinfo=timezone.utc),
            coverage_end_exclusive=datetime(
                2026, 10, 30, 0, 0, tzinfo=timezone.utc),
            publicly_available_as_of=datetime(
                2026, 10, 30, 0, 0, tzinfo=timezone.utc),
            source_timezone="UTC")
        self.later = IssueSnapshot(
            issue_id="WEEKLY-2026-W44",
            coverage_start=datetime(
                2026, 10, 30, 0, 0, tzinfo=timezone.utc),
            coverage_end_exclusive=datetime(
                2026, 11, 6, 0, 0, tzinfo=timezone.utc),
            publicly_available_as_of=datetime(
                2026, 11, 6, 0, 0, tzinfo=timezone.utc),
            source_timezone="UTC")
        self.use_context = self.sf.fx.use_context.model_copy(update={
            "at": self.later.publicly_available_as_of})
        self.old_article, self.later_article = self.make_articles()
        self.supplement = self.make_supplement()

    def make_articles(self):
        def article(version_id, body, *, parent, published, recorded):
            FixedDateTime.value = recorded
            with patch("intelligence.archive.datetime", FixedDateTime):
                return self.archive.append(VersionSubmission(
                    schema_version=2,
                    object_id="ARTICLE-W39-THEME",
                    version_id=version_id,
                    parent_version_id=parent,
                    kind=ObjectKind.ARTICLE,
                    title="Persistent theme Article",
                    spec_sha256="a" * 64,
                    created_at=published,
                    source_times=SourceTimes(published=TimePoint(
                        precision=Precision.INSTANT,
                        value=published.isoformat(),
                        source_timezone="UTC",
                        provenance="Owned W39 publication time")),
                    rights=self.rights,
                    representation=Representation.FULL_BODY,
                    references=(VersionReference(
                        target_version_id=self.sf.claim.claim_version_id,
                        use=ReferenceUse.BASIS,
                        locator="persistent theme Claim"),)),
                    body.encode())

        old = article(
            "ARTICLE-W39-THEME-v001",
            "# Week One\n\nThe old judgment says implementation was not yet demonstrated.",
            parent=None,
            published=datetime(
                2026, 10, 29, 12, 0, tzinfo=timezone.utc),
            recorded=datetime(
                2026, 10, 29, 13, 0, tzinfo=timezone.utc))
        later = article(
            "ARTICLE-W39-THEME-v002",
            "# Week Two\n\nA new independent observation showed implementation began.",
            parent=old.submission.version_id,
            published=datetime(
                2026, 10, 31, 12, 0, tzinfo=timezone.utc),
            recorded=datetime(
                2026, 11, 6, 1, 0, tzinfo=timezone.utc))
        return old, later

    def make_supplement(self):
        after = self.sf.assess(
            "W39-STRONG",
            (
                self.sf.fx.evidence_a.submission.version_id,
                self.sf.fx.evidence_b.submission.version_id,
            ),
            EvidenceRelation.SUPPORTS)
        result = self.sf.supplement_result(
            "W39-STRONG",
            status=SupplementStatus.EVIDENCE_ADDED,
            impact=SupplementImpact.STRENGTHENED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.SUPPORTS,
            source_ids=(
                self.sf.fx.intake_a_version,
                self.sf.fx.intake_b_version,
            ),
            evidence_ids=(
                self.sf.fx.evidence_a.submission.version_id,
                self.sf.fx.evidence_b.submission.version_id,
            ),
            assessment_ids=(after.submission.version_id,))
        revision, snapshot = self.sf.continuation(
            "W39",
            (
                self.sf.fx.evidence_a.submission.version_id,
                self.sf.fx.evidence_b.submission.version_id,
            ),
            (after.submission.version_id,))
        route = self.sf.route(
            "W39", result, revision, snapshot,
            next_action="Recheck the explanation against the second root")
        record = self.sf.routes.load(route.submission.version_id)
        return {
            "stored": route,
            "record": record,
            "result": result,
            "revision": revision,
            "snapshot": snapshot,
        }

    def make_t03_decision(self, *, basis=PublicationBasis.CURRENT_WEEK,
                          article_type=None):
        self.sf.time = max(
            self.sf.time, self.later.publicly_available_as_of
        ) + timedelta(hours=1)
        decision = TopicDecision(
            decision_id="DECISION-W39-T03",
            topic_id=self.sf.fx.cover.topic_id,
            theme_id=self.sf.fx.cover.theme_id,
            edition_id="EDITION-W45",
            spec_sha256="a" * 64,
            discovery_proposal_id=(
                self.sf.fx.cover.discovery_proposal_id),
            question_version_id=self.sf.fx.cover.question_version_id,
            candidate_index_ids=self.sf.fx.cover.candidate_index_ids,
            candidate_ids=self.sf.fx.cover.candidate_ids,
            cluster_ids=self.sf.fx.cover.cluster_ids,
            stage=DecisionStage.S8,
            publication_basis=basis,
            article_type=(
                article_type or self.sf.fx.cover.article_type),
            value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=TopicDecisionCode.WATCH,
            reasons=("Two-week record is mature for editorial recheck",),
            next_action="Decide whether the mature theme belongs in a current issue",
            previous_decision_id=self.sf.fx.cover.decision_id,
            created_at=self.sf.time)
        self.sf.fx.editorial.append_decision(decision)
        return decision

    def request(self, **updates):
        base = CrossWeekContinuationRequest(
            continuation_id="CONTINUATION-W39",
            spec_sha256="a" * 64,
            theme_id="THEME-W26",
            claim_version_id=self.sf.claim.claim_version_id,
            earlier=self.earlier,
            later=self.later,
            old_article_version_id=(
                self.old_article.submission.version_id),
            old_exact_excerpt=(
                "The old judgment says implementation was not yet demonstrated."),
            later_article_version_id=(
                self.later_article.submission.version_id),
            continuation_dossier_snapshot_version_id=(
                self.supplement["record"].continuation_dossier_snapshot_version_id),
            supplement_route_version_id=(
                self.supplement["stored"].submission.version_id),
            disposition=ContinuationDisposition.CONTINUE,
            publication_basis=None,
            t03_decision_id=None,
            use_context=self.use_context,
            next_action="Continue bounded research against the second root",
            stop_reason=None,
            temporal_scope=TemporalEvidenceScope.SYNTHETIC_FIXTURE,
            created_at=self.sf.time + timedelta(days=1))
        return base.model_copy(update=updates)

    def test_two_snapshots_preserve_old_words_and_do_not_count_as_stage_evidence(
            self):
        result = self.controller.record(self.request())
        record = self.controller.load(result.submission.version_id)
        self.assertEqual(record.earlier_issue_id, "WEEKLY-2026-W43")
        self.assertEqual(record.later_issue_id, "WEEKLY-2026-W44")
        self.assertEqual(
            record.old_exact_excerpt,
            "The old judgment says implementation was not yet demonstrated.")
        self.assertTrue(record.later_system_unknown)
        self.assertIs(record.handoff_owner, "T05")
        self.assertTrue(record.requires_editorial_placement)
        self.assertFalse(record.automatic_issue_addition)
        self.assertFalse(record.stage_evidence_eligible)
        self.assertFalse(record.publication_authorized)

    def test_mature_theme_needs_current_T03_after_second_snapshot(self):
        decision = self.make_t03_decision()
        result = self.controller.record(self.request(
            disposition=ContinuationDisposition.MATURE_FOR_T03,
            publication_basis=PublicationBasis.CURRENT_WEEK,
            t03_decision_id=decision.decision_id,
            next_action="Send the mature theme to editorial placement"))
        record = self.controller.load(result.submission.version_id)
        self.assertIs(
            record.disposition, ContinuationDisposition.MATURE_FOR_T03)
        self.assertIs(record.handoff_owner, "T03")
        self.assertTrue(record.independent_review_recheck_required)
        self.assertTrue(record.requires_editorial_placement)
        self.assertFalse(record.automatic_issue_addition)

    def test_later_version_cannot_be_backfilled_as_old_snapshot(self):
        request = self.request(
            old_article_version_id=self.later_article.submission.version_id)
        with self.assertRaisesRegex(
                CrossWeekContinuationError, "Old Article"):
            self.controller.record(request)

    def test_overlap_and_long_term_short_downgrade_are_rejected(self):
        with self.assertRaisesRegex(ValidationError, "overlap"):
            CrossWeekContinuationRequest.model_validate_json(
                self.request(later=IssueSnapshot(
                    issue_id="WEEKLY-OVERLAP",
                    coverage_start=datetime(
                        2026, 10, 29, tzinfo=timezone.utc),
                    coverage_end_exclusive=datetime(
                        2026, 11, 5, tzinfo=timezone.utc),
                    publicly_available_as_of=datetime(
                        2026, 11, 5, tzinfo=timezone.utc),
                    source_timezone="UTC")).model_dump_json())

        decision = self.make_t03_decision(
            basis=PublicationBasis.LONG_TERM_FEATURE,
            article_type=__import__(
                "intelligence.editorial", fromlist=["ArticleType"]
            ).ArticleType.SOURCE_SELECTION)
        with self.assertRaisesRegex(
                CrossWeekContinuationError, "downgraded"):
            self.controller.record(self.request(
                disposition=ContinuationDisposition.MATURE_FOR_T03,
                publication_basis=PublicationBasis.LONG_TERM_FEATURE,
                t03_decision_id=decision.decision_id,
                next_action="Do not auto-downgrade the long-term theme"))

    def test_suspended_or_closed_theme_requires_a_stop_reason(self):
        with self.assertRaisesRegex(ValidationError, "concrete reason"):
            CrossWeekContinuationRequest.model_validate_json(
                self.request(
                    disposition=ContinuationDisposition.SUSPEND,
                    stop_reason=None).model_dump_json())
        result = self.controller.record(self.request(
            disposition=ContinuationDisposition.CLOSE,
            stop_reason="The research question was answered by an authoritative ruling",
            next_action="Retain the record for historical reuse"))
        record = self.controller.load(result.submission.version_id)
        self.assertIs(record.disposition, ContinuationDisposition.CLOSE)
        self.assertIs(record.handoff_owner, "T11")
        self.assertFalse(record.publication_authorized)


if __name__ == "__main__":
    unittest.main()
