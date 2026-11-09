"""W23 owned-fixture tests for S0-S8 selection and separate admissions."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.archive import Archive, ArchiveError, Conflict
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState, Precision,
                                    Representation, RightsBasis, RightsGrant, Scope,
                                    ScopeMode, TimePoint, UsePermission, ValidityMode,
                                    VersionSubmission)
from intelligence.coverage import (CandidateCoverageDecision, CoverageBasis,
                                   CoverageComparator, CoverageController,
                                   CoverageReferencePlan, EditorialDecision,
                                   ReferenceChannelAttempt, ReferenceChannelOutcome,
                                   ReferenceItem, ReferenceOrigin,
                                   SelectionCoverageSnapshot)
from intelligence.discovery import (CandidateHint, EventClusterController, EventClusterer,
                                    LineageRole)
from intelligence.editorial import (ArticleType, DecisionStage, EditionPlacement,
                                    EditionPlacementProposal, EditorialController,
                                    EditorialError, PublicationBasis, ResearchAdmission,
                                    S8PrerequisitePackage, TopicDecision,
                                    TopicDecisionCode, ValueBasis)
from intelligence.sources import (PermissionStateW20, SourceAdapter,
                                  SourceAdapterController, SourceDescriptor, SourceType)

BASE = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
SPEC = "a" * 64
TEXT = b"Owned synthetic W23 editorial fixture\n"


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.rights = RightsGrant(
            rights_id="RIGHTS-W23", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX, MaterialUse.STORE_BODY}),
            evidence="Owned synthetic W23 records", checked_by="test fixture",
            checked_at=BASE,
            permissions=(UsePermission(
                use=MaterialUse.STORE_BODY, state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.controller = EditorialController(self.archive, self.rights)
        self.question = self.record(
            "QUESTION-W23", "QUESTION-W23-v001", ObjectKind.QUESTION_VERSION)
        self.source = self.record(
            "SOURCE-MATERIAL-W23", "SOURCE-MATERIAL-W23-v001",
            ObjectKind.SOURCE_MATERIAL, created_at=BASE + timedelta(seconds=1))
        self.evidence = self.record(
            "EVIDENCE-W23", "EVIDENCE-W23-v001", ObjectKind.EVIDENCE,
            created_at=BASE + timedelta(seconds=2))
        self.rights_record = self.record(
            "RIGHTS-RECORD-W23", "RIGHTS-RECORD-W23-v001",
            ObjectKind.RIGHTS_RECORD, created_at=BASE + timedelta(seconds=3))
        self.reading_plan = self.record(
            "READING-PLAN-W23", "READING-PLAN-W23-v001",
            ObjectKind.READING_SCOPE_PLAN, created_at=BASE + timedelta(seconds=4))
        self.index = self.candidate_index()
        self.index_stored = SourceAdapterController(
            self.archive, self.rights).append_index(self.index)
        self.discovery, self.cluster, self.candidate = self.discovery_proposal()
        self.discovery_stored = EventClusterController(
            self.archive, self.rights).append_proposal(self.discovery)
        self.plan, self.audit = self.coverage_audit()
        coverage = CoverageController(self.archive, self.rights)
        coverage.append_plan(self.plan)
        coverage.append_audit(self.audit)
        self.package = S8PrerequisitePackage(
            package_id="PACKAGE-W23",
            topic_id="TOPIC-W23",
            edition_id="EDITION-W42",
            spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id=self.question.submission.version_id,
            source_material_version_ids=(self.source.submission.version_id,),
            evidence_version_ids=(self.evidence.submission.version_id,),
            rights_record_version_ids=(self.rights_record.submission.version_id,),
            reading_plan_version_id=self.reading_plan.submission.version_id,
            limitations=("Owned synthetic fixture; no real content acceptance",),
            candidate_index_ids=(self.index.index_id,),
            coverage_audit_ids=(self.audit.audit_id,),
            created_at=BASE + timedelta(minutes=4))
        self.package_stored = self.controller.append_package(self.package)
        self.watch = self.decision(
            "DECISION-W23-S0-WATCH", DecisionStage.S0, TopicDecisionCode.WATCH,
            BASE + timedelta(minutes=5), next_action="Acquire the named key source")
        self.watch_stored = self.controller.append_decision(self.watch)
        self.cover = self.decision(
            "DECISION-W23-S8-COVER", DecisionStage.S8, TopicDecisionCode.COVER,
            BASE + timedelta(minutes=6), previous=self.watch.decision_id,
            package_id=self.package.package_id).model_copy(update={
                "trial_score": Decimal("99.5"),
                "trial_score_basis": "Owned high-score fixture; not an automatic gate",
            })
        self.cover_stored = self.controller.append_decision(self.cover)

    def record(self, object_id, version_id, kind, *, created_at=BASE, parent=None):
        return self.archive.append(VersionSubmission(
            object_id=object_id, version_id=version_id, kind=kind,
            parent_version_id=parent, title=f"Owned fixture {object_id}",
            spec_sha256=SPEC, created_at=created_at, rights=self.rights,
            representation=Representation.FULL_BODY), TEXT)

    def candidate_index(self):
        source = SourceDescriptor(
            source_id="SRC-W23", name="Owned W23 candidate source",
            source_url="https://example.invalid/w23", source_type=SourceType.JSON_API,
            language="en", region="NZ", sector="fixture", ownership="Owned owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Owned synthetic source")
        raw = json.dumps({"items": [
            {"id": "event-a", "title": "Owned event A",
             "url": "https://example.invalid/event-a",
             "summary": "Owned clue A",
             "published_at": "2026-10-30T10:00:00Z"},
            {"id": "event-b", "title": "Owned event B",
             "url": "https://example.invalid/event-b",
             "summary": "Owned clue B",
             "published_at": "2026-10-30T11:00:00Z"},
        ]}).encode()
        return SourceAdapter().parse(
            source, raw, acquired_at=BASE + timedelta(minutes=1),
            content_type="application/json", spec_sha256=SPEC)

    def discovery_proposal(self):
        hints = (
            CandidateHint(
                candidate_index_id=self.index.index_id,
                candidate_id=self.index.candidates[0].candidate_id,
                event_key="EVENT-A", lineage_role=LineageRole.ORIGINAL,
                lineage_root_ids=("ORIGIN-A",), note="Owned event A mapping"),
            CandidateHint(
                candidate_index_id=self.index.index_id,
                candidate_id=self.index.candidates[1].candidate_id,
                event_key="EVENT-B", lineage_role=LineageRole.ORIGINAL,
                lineage_root_ids=("ORIGIN-B",), note="Owned event B mapping"),
        )
        proposal = EventClusterer().build(
            (self.index,), hints, proposal_id="DISCOVERY-W23", spec_sha256=SPEC,
            created_at=BASE + timedelta(minutes=2))
        candidate = self.index.candidates[0]
        cluster = next(item for item in proposal.clusters
                       if candidate.candidate_id in item.candidate_ids)
        return proposal, cluster, candidate

    def coverage_audit(self):
        fixed_at = BASE - timedelta(hours=1)
        channel = ReferenceChannelAttempt(
            channel_id="REFERENCE-CHANNEL-W23", source_id="SRC-REFERENCE-W23",
            method="Owned independent reference query", attempted_at=fixed_at,
            outcome=ReferenceChannelOutcome.AVAILABLE,
            note="Owned independent reference available")
        reference = ReferenceItem(
            item_id="REFERENCE-W23-A", title="Owned independent event A",
            source_id="SRC-REFERENCE-W23",
            source_url="https://example.invalid/reference/event-a",
            channel_id=channel.channel_id, origin=ReferenceOrigin.EXTERNAL_QUERY,
            observed_at=fixed_at,
            published_at=TimePoint(precision=Precision.DATE, value="2026-10-30"),
            region="NZ", language="en", domain="fixture", event_key="EVENT-A",
            priority_basis="Owned independent reference")
        plan = CoverageReferencePlan(
            plan_id="COVERAGE-PLAN-W23", spec_sha256=SPEC,
            basis=CoverageBasis.INDEPENDENT_REFERENCE, fixed_at=fixed_at,
            created_at=fixed_at + timedelta(minutes=5),
            window_start=fixed_at - timedelta(days=1), window_end=fixed_at,
            scope_description="Owned synthetic reference window",
            selection_viewed_at_fix=False, channels=(channel,), references=(reference,),
            limitations=("No global recall claim",))
        selection = SelectionCoverageSnapshot(
            snapshot_id="SELECTION-W23", proposal_id=self.discovery.proposal_id,
            decisions=(CandidateCoverageDecision(
                candidate_id=self.candidate.candidate_id,
                decision=EditorialDecision.SELECTED,
                reason="Owned synthetic S8 selection"),),
            created_at=BASE + timedelta(minutes=2, seconds=30))
        audit = CoverageComparator().compare(
            plan, (self.index,), self.discovery, audit_id="COVERAGE-AUDIT-W23",
            created_at=BASE + timedelta(minutes=3), selection=selection)
        return plan, audit

    def decision(self, decision_id, stage, code, created_at, *, previous=None,
                 package_id=None, publication_basis=PublicationBasis.CURRENT_WEEK,
                 article_type=ArticleType.DEEP_THEME, next_action=None,
                 candidate_ids=None, cluster_ids=None, candidate_index_ids=None):
        return TopicDecision(
            decision_id=decision_id, topic_id="TOPIC-W23", theme_id="THEME-W23",
            edition_id="EDITION-W42", spec_sha256=SPEC,
            discovery_proposal_id=self.discovery.proposal_id,
            question_version_id=self.question.submission.version_id,
            candidate_index_ids=candidate_index_ids or (self.index.index_id,),
            candidate_ids=candidate_ids or (self.candidate.candidate_id,),
            cluster_ids=cluster_ids or (self.cluster.cluster_id,),
            stage=stage, publication_basis=publication_basis,
            article_type=article_type, value_bases=(ValueBasis.RESEARCH_VALUE,),
            decision=code, reasons=("Owned synthetic editorial reason",),
            gaps=(), next_action=next_action, trial_score=None,
            trial_score_basis=None, research_investment_note="Owned fixture only",
            s8_package_id=package_id, previous_decision_id=previous,
            created_at=created_at)

    def admission(self, admission_id="ADMISSION-W23", created_at=None):
        return ResearchAdmission(
            research_admission_id=admission_id,
            topic_decision_id=self.cover.decision_id, topic_id="TOPIC-W23",
            theme_id="THEME-W23", edition_id="EDITION-W42", spec_sha256=SPEC,
            allowed_article_types=(ArticleType.DEEP_THEME,),
            scope="Produce the S8-approved deep-theme research material only",
            restrictions=("No publication authorization",),
            created_at=created_at or BASE + timedelta(minutes=7))

    def proposal(self, *, decision_id=None, publication_basis=PublicationBasis.CURRENT_WEEK,
                 created_at=None, proposal_id="EDITION-PROPOSAL-W23"):
        return EditionPlacementProposal(
            edition_proposal_id=proposal_id, edition_id="EDITION-W42",
            spec_sha256=SPEC,
            placements=(EditionPlacement(
                placement_id="PLACEMENT-W23",
                topic_decision_id=decision_id or self.cover.decision_id,
                research_admission_id="ADMISSION-W23", topic_id="TOPIC-W23",
                article_type=ArticleType.DEEP_THEME,
                publication_basis=publication_basis, slot_order=1,
                editorial_role="Lead deep-theme section",
                reason="Explicit owned editorial combination reason"),),
            combination_reason="Explicit placement after actual editorial comparison",
            created_at=created_at or BASE + timedelta(minutes=8))

    def test_s0_watch_to_s8_cover_history_and_explicit_placement_roundtrip(self):
        admission_stored = self.controller.append_research_admission(self.admission())
        proposal_stored = self.controller.append_edition_proposal(self.proposal())
        self.assertEqual(self.controller.current_decision("TOPIC-W23").decision_id,
                         self.cover.decision_id)
        self.assertEqual(self.controller.load_decision(
            self.watch.decision_id).decision, TopicDecisionCode.WATCH)
        self.assertEqual(self.controller.load_package(
            self.package.package_id).model_dump(mode="json"),
            self.package.model_dump(mode="json"))
        admission = self.controller.load_research_admission("ADMISSION-W23")
        proposal = self.controller.load_edition_proposal("EDITION-PROPOSAL-W23")
        self.assertTrue(admission.research_allowed)
        self.assertFalse(admission.publication_authorized)
        self.assertFalse(proposal.publication_authorized)
        self.assertTrue(proposal.content_review_required)
        self.assertEqual(admission_stored.submission.kind,
                         ObjectKind.RESEARCH_ADMISSION)
        self.assertEqual(proposal_stored.submission.kind,
                         ObjectKind.EDITION_PLACEMENT_PROPOSAL)

    def test_high_score_or_cover_does_not_auto_create_admission_or_placement(self):
        self.assertEqual(self.cover.trial_score, Decimal("99.5"))
        self.assertIsNone(self.archive.latest(
            self.controller._object("RESEARCH-ADMISSION-", "ADMISSION-W23")))
        self.assertIsNone(self.archive.latest(
            self.controller._object("EDITION-PROPOSAL-", "EDITION-W42")))
        with self.assertRaises(ValidationError):
            self.decision(
                "DECISION-W23-PREMATURE", DecisionStage.S7, TopicDecisionCode.COVER,
                BASE + timedelta(minutes=7), previous=self.cover.decision_id,
                package_id=self.package.package_id).model_copy(
                    update={"trial_score": 100, "trial_score_basis": "high score"})
        with self.assertRaises(ValidationError):
            TopicDecision(**{
                **self.decision(
                    "DECISION-W23-NO-PACKAGE", DecisionStage.S8,
                    TopicDecisionCode.COVER, BASE + timedelta(minutes=7),
                    previous=self.cover.decision_id).model_dump(),
                "s8_package_id": None,
                "trial_score": 100,
                "trial_score_basis": "high score",
            })

    def test_package_checks_actual_dependency_types_and_current_versions(self):
        bad_question = self.package.model_copy(update={
            "package_id": "PACKAGE-W23-WRONG-QUESTION",
            "question_version_id": self.index_stored.submission.version_id})
        with self.assertRaisesRegex(EditorialError, "question version"):
            self.controller.append_package(bad_question)

        bad_audit = self.package.model_copy(update={
            "package_id": "PACKAGE-W23-WRONG-AUDIT",
            "coverage_audit_ids": (self.question.submission.version_id,)})
        with self.assertRaises(ArchiveError):
            self.controller.append_package(bad_audit)

        self.record(
            "EVIDENCE-W23", "EVIDENCE-W23-v002", ObjectKind.EVIDENCE,
            created_at=BASE + timedelta(minutes=7),
            parent=self.evidence.submission.version_id)
        stale = self.package.model_copy(update={
            "package_id": "PACKAGE-W23-STALE",
            "created_at": BASE + timedelta(minutes=8)})
        with self.assertRaisesRegex(EditorialError, "not the current"):
            self.controller.append_package(stale)

    def test_decision_rejects_foreign_candidate_cluster_and_index_set(self):
        foreign_candidate = self.decision(
            "DECISION-W23-FOREIGN-CANDIDATE", DecisionStage.S8,
            TopicDecisionCode.DROP, BASE + timedelta(minutes=7),
            previous=self.cover.decision_id, candidate_ids=("CANDIDATE-FOREIGN",))
        with self.assertRaisesRegex(EditorialError, "outside its indexes"):
            self.controller.append_decision(foreign_candidate)
        foreign_cluster = self.decision(
            "DECISION-W23-FOREIGN-CLUSTER", DecisionStage.S8,
            TopicDecisionCode.DROP, BASE + timedelta(minutes=7),
            previous=self.cover.decision_id, cluster_ids=("CLUSTER-FOREIGN",))
        with self.assertRaisesRegex(EditorialError, "outside its discovery proposal"):
            self.controller.append_decision(foreign_cluster)
        foreign_index = self.decision(
            "DECISION-W23-FOREIGN-INDEX", DecisionStage.S8,
            TopicDecisionCode.DROP, BASE + timedelta(minutes=7),
            previous=self.cover.decision_id,
            candidate_index_ids=(self.index.index_id, "CANDIDATE-INDEX-FOREIGN"))
        with self.assertRaises(ArchiveError):
            self.controller.append_decision(foreign_index)
        self.assertEqual(self.controller.current_decision("TOPIC-W23").decision_id,
                         self.cover.decision_id)

    def test_new_current_decision_stales_old_cover_for_admission(self):
        later = self.decision(
            "DECISION-W23-S8-DROP", DecisionStage.S8, TopicDecisionCode.DROP,
            BASE + timedelta(minutes=7), previous=self.cover.decision_id)
        self.controller.append_decision(later)
        with self.assertRaisesRegex(EditorialError, "stale"):
            self.controller.append_research_admission(self.admission())

    def test_new_evidence_after_cover_stales_admission(self):
        self.record(
            "EVIDENCE-W23", "EVIDENCE-W23-v002", ObjectKind.EVIDENCE,
            created_at=BASE + timedelta(minutes=7),
            parent=self.evidence.submission.version_id)
        with self.assertRaisesRegex(EditorialError, "not the current"):
            self.controller.append_research_admission(self.admission())

    def test_admission_validation_context_is_atomic_with_append(self):
        original = self.controller._validate_decision_context

        def add_evidence_after_validation(decision, package):
            records = original(decision, package)
            self.record(
                "EVIDENCE-W23", "EVIDENCE-W23-v002", ObjectKind.EVIDENCE,
                created_at=BASE + timedelta(minutes=7),
                parent=self.evidence.submission.version_id)
            return records

        with patch.object(self.controller, "_validate_decision_context",
                          side_effect=add_evidence_after_validation):
            with self.assertRaises(Conflict):
                self.controller.append_research_admission(self.admission())
        self.assertFalse(self.archive.get("EVIDENCE-W23-v002").body_retention_revoked)
        with self.assertRaises(ArchiveError):
            self.controller.load_research_admission("ADMISSION-W23")

    def test_research_and_edition_records_cannot_claim_publication(self):
        self.controller.append_research_admission(self.admission())
        self.controller.append_edition_proposal(self.proposal())
        with self.assertRaises(ValidationError):
            ResearchAdmission(**{
                **self.admission("ADMISSION-PUBLISH").model_dump(),
                "publication_authorized": True,
            })
        with self.assertRaises(ValidationError):
            EditionPlacementProposal(**{
                **self.proposal(proposal_id="PROPOSAL-PUBLISH").model_dump(),
                "publication_authorized": True,
            })
        widened = self.admission("ADMISSION-WIDENED").model_copy(update={
            "allowed_article_types": (
                ArticleType.DEEP_THEME, ArticleType.SOURCE_SELECTION)})
        with self.assertRaisesRegex(EditorialError, "exact COVER article type"):
            self.controller.append_research_admission(widened)

    def test_edition_placement_rejects_stale_cover_or_wrong_basis(self):
        self.controller.append_research_admission(self.admission())
        stale = self.proposal(decision_id=self.watch.decision_id)
        with self.assertRaisesRegex(EditorialError, "stale"):
            self.controller.append_edition_proposal(stale)
        wrong_basis = self.proposal(
            publication_basis=PublicationBasis.LONG_TERM_FEATURE,
            proposal_id="EDITION-PROPOSAL-WRONG-BASIS")
        with self.assertRaisesRegex(EditorialError, "differs"):
            self.controller.append_edition_proposal(wrong_basis)

    def test_decision_model_enforces_s8_actions_next_action_and_type_boundaries(self):
        with self.assertRaises(ValidationError):
            self.decision(
                "DECISION-PREMATURE-COVER", DecisionStage.S7, TopicDecisionCode.COVER,
                BASE + timedelta(minutes=7), previous=self.cover.decision_id,
                package_id=self.package.package_id)
        with self.assertRaises(ValidationError):
            self.decision(
                "DECISION-WATCH-NO-ACTION", DecisionStage.S8, TopicDecisionCode.WATCH,
                BASE + timedelta(minutes=7), previous=self.cover.decision_id)
        with self.assertRaises(ValidationError):
            self.decision(
                "DECISION-LONG-TERM-SELECTION", DecisionStage.S8,
                TopicDecisionCode.COVER, BASE + timedelta(minutes=7),
                previous=self.cover.decision_id, package_id=self.package.package_id,
                publication_basis=PublicationBasis.LONG_TERM_FEATURE,
                article_type=ArticleType.SOURCE_SELECTION)
        with self.assertRaises(ValidationError):
            self.decision(
                "DECISION-LONG-TERM-UPDATE", DecisionStage.S8,
                TopicDecisionCode.COVER, BASE + timedelta(minutes=7),
                previous=self.cover.decision_id, package_id=self.package.package_id,
                publication_basis=PublicationBasis.LONG_TERM_FEATURE,
                article_type=ArticleType.UPDATE_CORRECTION)
        with self.assertRaises(ValidationError):
            EditionPlacement(
                placement_id="PLACEMENT-LONG-TERM-SELECTION",
                topic_decision_id=self.cover.decision_id,
                research_admission_id="ADMISSION-W23", topic_id="TOPIC-W23",
                article_type=ArticleType.SOURCE_SELECTION,
                publication_basis=PublicationBasis.LONG_TERM_FEATURE, slot_order=1,
                editorial_role="Invalid downgrade", reason="Expected validation failure")
        with self.assertRaises(ValidationError):
            self.decision(
                "DECISION-PRE-S8-PACKAGE", DecisionStage.S7,
                TopicDecisionCode.WATCH, BASE + timedelta(minutes=7),
                previous=self.cover.decision_id, package_id=self.package.package_id,
                next_action="Repeat review")


if __name__ == "__main__":
    unittest.main()
