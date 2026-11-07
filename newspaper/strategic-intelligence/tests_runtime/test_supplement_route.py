"""W38 owned-fixture targeted supplementation and S8 handoff tests."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import unittest

from pydantic import ValidationError

from intelligence.archive import canonical
from intelligence.contracts import (ObjectKind, ReferenceUse,
                                    Representation, TimePoint, VersionReference,
                                    VersionSubmission)
from intelligence.editorial import (ArticleType, DecisionStage, ResearchAdmission,
                                    TopicDecision, TopicDecisionCode, ValueBasis)
from intelligence.evidence import (ClaimEvidenceAssessment, ClaimScope,
                                   ClaimType, ClaimVersion, EvidenceRelation,
                                   SupplementController, SupplementGapType,
                                   SupplementImpact, SupplementMethod,
                                   SupplementRequest, SupplementResult,
                                   SupplementStatus)
from intelligence.research import ResearchRevision, ResearchRevisionController
from intelligence.supplement_route import (SupplementHandoff,
                                           SupplementRouteController,
                                           SupplementRouteError,
                                           SupplementRouteRequest)
from intelligence.workflow import DossierStartRequest, ResearchWorkflowController

BASE = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)


def _version(prefix, identity):
    raw = json.dumps([prefix, identity], ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:32]


class TargetedSupplementRouteTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_materials import ChineseMaterialTests
        self.fx = ChineseMaterialTests(
            methodName="test_excerpt_translation_and_source_map_are_exact")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.archive = self.fx.archive
        self.rights = self.fx.journal_rights
        self.evidence = self.fx.evidence
        self.supplements = SupplementController(self.archive, self.rights)
        self.research = ResearchRevisionController(
            self.archive, self.rights)
        self.workflow = ResearchWorkflowController(self.archive, self.rights)
        self.routes = SupplementRouteController(self.archive, self.rights)
        self.time = BASE + timedelta(minutes=5)
        self.claim_scope = ClaimScope(
            subjects=("owned operator",),
            metric="observed implementation",
            comparison_basis="owned exact source period",
            conditions=("The same actor and period remain comparable",))
        self.claim = ClaimVersion(
            claim_version_id="CLAIM-W38-v001",
            theme_id="THEME-W26", spec_sha256="a" * 64,
            question_version_id="QUESTION-W26-v001",
            claim_text=(
                "The owned operator implemented the documented commitment "
                "during the measured period."),
            claim_type=ClaimType.OBSERVED_FACT,
            scope=self.claim_scope,
            created_at=self.time)
        self.evidence.append_claim(self.claim)
        self.before = self.assess(
            "BEFORE", (self.fx.evidence_a.submission.version_id,),
            EvidenceRelation.PARTIALLY_SUPPORTS,
            unsupported=("A second independent observation is absent",))
        self.base_revision = ResearchRevision(
            revision_id="REV-W38-v001",
            theme_id="THEME-W26",
            spec_sha256="a" * 64,
            input_version_ids=(
                "QUESTION-W26-v001",
                self.claim.claim_version_id,
                self.fx.evidence_a.submission.version_id,
                self.before.submission.version_id,
            ),
            question_version_id="QUESTION-W26-v001",
            evidence_version_ids=(
                self.fx.evidence_a.submission.version_id,),
            reason="Owned W38 base research revision",
            created_at=self.time + timedelta(seconds=1))
        self.research.append_revision(self.base_revision, None)
        self.base_dossier = self.workflow.start_dossier(
            DossierStartRequest(
                dossier_id="DOSSIER-W38-BASE",
                theme_id="THEME-W26",
                spec_sha256="a" * 64,
                revision_id=self.base_revision.revision_id,
                question_version_id="QUESTION-W26-v001",
                knowledge_cutoff=self.time,
                created_at=self.time + timedelta(seconds=2)))
        self.request_record = self.supplements.append_request(
            SupplementRequest(
                supplement_request_id="SUPPLEMENT-W38-REQ",
                theme_id="THEME-W26",
                spec_sha256="a" * 64,
                claim_version_id=self.claim.claim_version_id,
                assessment_version_id=self.before.submission.version_id,
                gap_type=SupplementGapType.PARTIAL_SUPPORT,
                missing_information=(
                    "A second independent observation"),
                distinguishing_evidence=(
                    "A different lineage root with the same metric"),
                next_owner="T04",
                continuation_trigger=(
                    "A qualifying independent source is acquired"),
                created_at=self.time + timedelta(seconds=3)))

    def assess(self, label, evidence_ids, relation, *, unsupported=()):
        self.time += timedelta(seconds=1)
        return self.evidence.assess_claim(
            __import__("intelligence.evidence", fromlist=[
                "ClaimEvidenceRequest"]).ClaimEvidenceRequest(
                    assessment_id="ASSESSMENT-W38-" + label,
                    theme_id="THEME-W26",
                    spec_sha256="a" * 64,
                    claim_version_id=self.claim.claim_version_id,
                    evidence_version_ids=tuple(evidence_ids),
                    relation=relation,
                    supported_scope=self.claim.scope,
                    unsupported_aspects=tuple(unsupported),
                    reviewed_by="OWNED-W38-REVIEWER",
                    reviewed_at=self.time,
                    use_context=self.fx.use_context.model_copy(
                        update={"at": self.time}),
                    created_at=self.time))

    def continuation(self, label, evidence_ids, assessment_ids):
        revision_id = "REV-W38-" + label
        revision = ResearchRevision(
            revision_id=revision_id,
            theme_id="THEME-W26",
            spec_sha256="a" * 64,
            based_on_revision_id=self.base_revision.revision_id,
            input_version_ids=tuple(dict.fromkeys((
                *self.base_revision.input_version_ids,
                *evidence_ids,
                *assessment_ids,
            ))),
            question_version_id="QUESTION-W26-v001",
            evidence_version_ids=tuple(dict.fromkeys((
                *self.base_revision.evidence_version_ids,
                *evidence_ids,
            ))),
            reason="Owned W38 continuation after targeted supplementation",
            created_at=self.time + timedelta(seconds=1))
        self.research.append_revision(
            revision, self.base_revision.revision_id)
        snapshot = self.workflow.start_dossier(DossierStartRequest(
            dossier_id="DOSSIER-W38-" + label,
            theme_id="THEME-W26",
            spec_sha256="a" * 64,
            revision_id=revision_id,
            question_version_id="QUESTION-W26-v001",
            knowledge_cutoff=self.time,
            created_at=self.time + timedelta(seconds=2)))
        return revision, snapshot

    def supplement_result(self, label, *, status, impact,
                          before_relation, after_relation,
                          source_ids=(), evidence_ids=(), assessment_ids=(),
                          object_changed=False, s8_required=False,
                          reason="Owned supplement result"):
        self.time += timedelta(seconds=1)
        return self.supplements.append_result(SupplementResult(
            result_id="SUPPLEMENT-W38-" + label,
            supplement_request_version_id=(
                self.request_record.submission.version_id),
            theme_id="THEME-W26",
            spec_sha256="a" * 64,
            status=status,
            method=SupplementMethod.MANUAL,
            source_intake_version_ids=tuple(source_ids),
            evidence_version_ids=tuple(evidence_ids),
            assessment_version_ids=tuple(assessment_ids),
            before_relation=before_relation,
            after_relation=after_relation,
            impact=impact,
            affected_claim_version_ids=(self.claim.claim_version_id,),
            object_or_scope_changed=object_changed,
            s8_review_required=s8_required,
            reason=reason,
            continuation_trigger=(
                "Reopen only after a new qualifying observation"),
            created_at=self.time))

    def route(self, label, result, revision, snapshot,
              *, s8_decision=None, next_action="Recheck affected research",
              stop_reason=None):
        self.time += timedelta(seconds=1)
        return self.routes.record(SupplementRouteRequest(
            route_id="ROUTE-W38-" + label,
            spec_sha256="a" * 64,
            theme_id="THEME-W26",
            claim_version_id=self.claim.claim_version_id,
            supplement_request_version_id=(
                self.request_record.submission.version_id),
            supplement_result_version_id=(
                result.submission.version_id),
            base_revision_id=self.base_revision.revision_id,
            continuation_revision_id=revision.revision_id,
            base_dossier_snapshot_version_id=(
                self.base_dossier.submission.version_id),
            continuation_dossier_snapshot_version_id=(
                snapshot.submission.version_id),
            original_topic_decision_id=self.fx.cover.decision_id,
            s8_recheck_decision_id=s8_decision,
            next_action=next_action,
            stop_reason=stop_reason,
            created_at=self.time))

    def test_independent_evidence_strengthens_without_automatic_pass(self):
        after = self.assess(
            "AFTER-STRONG",
            (
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            EvidenceRelation.SUPPORTS)
        result = self.supplement_result(
            "STRONG",
            status=SupplementStatus.EVIDENCE_ADDED,
            impact=SupplementImpact.STRENGTHENED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.SUPPORTS,
            source_ids=(
                self.fx.intake_a_version,
                self.fx.intake_b_version,
            ),
            evidence_ids=(
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            assessment_ids=(after.submission.version_id,))
        revision, snapshot = self.continuation(
            "STRONG",
            (
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            (after.submission.version_id,))
        stored = self.route(
            "STRONG", result, revision, snapshot,
            next_action="Recheck B1 and affected Article with the second root")
        record = self.routes.load(stored.submission.version_id)
        self.assertIs(record.handoff, SupplementHandoff.STRENGTHENED)
        self.assertIs(record.impact, SupplementImpact.STRENGTHENED)
        self.assertFalse(record.automatic_strength_granted)
        self.assertFalse(record.publication_authorized)
        self.assertTrue(record.independent_review_recheck_required)
        self.assertTrue(record.new_evidence_version_ids)
        self.assertTrue(record.new_independent_root_ids)

    def test_same_root_duplicate_cannot_claim_strengthening(self):
        duplicate = ClaimEvidenceAssessment(
            assessment_id="ASSESSMENT-W38-SAME-ROOT",
            theme_id="THEME-W26",
            spec_sha256="a" * 64,
            claim_version_id=self.claim.claim_version_id,
            evidence_version_ids=(
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            relation=EvidenceRelation.SUPPORTS,
            supported_scope=self.claim.scope,
            conditions=self.claim.scope.conditions,
            unsupported_aspects=(),
            counterevidence=(),
            unknowns=(),
            independent_root_ids=self.evidence.load_assessment(
                self.before.submission.version_id).independent_root_ids,
            independent_root_count=1,
            same_root_duplicate_count=1,
            independence_unknown_count=0,
            reviewed_by="OWNED-W38-REVIEWER",
            reviewed_at=self.time,
            created_at=self.time)
        duplicate_stored = self.archive.append(VersionSubmission(
            schema_version=2,
            object_id="ASSESSMENT-OBJECT-W38-SAME-ROOT",
            version_id=_version(
                "CLAIM-EVIDENCE-", duplicate.assessment_id),
            kind=ObjectKind.CLAIM_EVIDENCE_ASSESSMENT,
            title="Owned same-root assessment",
            spec_sha256="a" * 64,
            created_at=self.time,
            rights=self.rights,
            representation=Representation.FULL_BODY),
            canonical(duplicate.model_dump(mode="json")).encode())
        result = self.supplement_result(
            "SAME-ROOT",
            status=SupplementStatus.EVIDENCE_ADDED,
            impact=SupplementImpact.STRENGTHENED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.SUPPORTS,
            source_ids=(
                self.fx.intake_a_version,
                self.fx.intake_b_version,
            ),
            evidence_ids=(
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            assessment_ids=(duplicate_stored.submission.version_id,))
        revision, snapshot = self.continuation(
            "SAME-ROOT",
            duplicate.evidence_version_ids,
            (duplicate_stored.submission.version_id,))
        with self.assertRaisesRegex(
                SupplementRouteError, "new independent root"):
            self.route("SAME-ROOT", result, revision, snapshot)

    def test_bounded_addition_can_maintain_support(self):
        maintained_after = self.assess(
            "AFTER-MAINTAIN",
            (
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            EvidenceRelation.PARTIALLY_SUPPORTS,
            unsupported=("Implementation remains only partly observed",))
        maintained_result = self.supplement_result(
            "MAINTAIN",
            status=SupplementStatus.EVIDENCE_ADDED,
            impact=SupplementImpact.UNCHANGED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            source_ids=(
                self.fx.intake_a_version,
                self.fx.intake_b_version,
            ),
            evidence_ids=(
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            assessment_ids=(maintained_after.submission.version_id,))
        revision, snapshot = self.continuation(
            "MAINTAIN",
            (
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            (maintained_after.submission.version_id,))
        maintained = self.routes.load(self.route(
            "MAINTAIN", maintained_result, revision, snapshot
        ).submission.version_id)
        self.assertIs(maintained.handoff, SupplementHandoff.MAINTAINED)
        self.assertFalse(maintained.automatic_strength_granted)
        self.assertTrue(maintained.independent_review_recheck_required)

    def test_new_evidence_can_weaken_support(self):
        weakened_after = self.assess(
            "AFTER-WEAKEN",
            (
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            EvidenceRelation.CONTRADICTS)
        weakened_result = self.supplement_result(
            "WEAKEN",
            status=SupplementStatus.EVIDENCE_ADDED,
            impact=SupplementImpact.WEAKENED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.CONTRADICTS,
            source_ids=(
                self.fx.intake_a_version,
                self.fx.intake_b_version,
            ),
            evidence_ids=(
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            assessment_ids=(weakened_after.submission.version_id,))
        revision2, snapshot2 = self.continuation(
            "WEAKEN",
            (
                self.fx.evidence_a.submission.version_id,
                self.fx.evidence_b.submission.version_id,
            ),
            (weakened_after.submission.version_id,))
        weakened = self.routes.load(self.route(
            "WEAKEN", weakened_result, revision2, snapshot2
        ).submission.version_id)
        self.assertIs(weakened.handoff, SupplementHandoff.WEAKENED)
        self.assertFalse(weakened.automatic_strength_granted)
        self.assertTrue(weakened.independent_review_recheck_required)

    def test_no_new_evidence_is_unresolved_and_requires_a_new_trigger(self):
        result = self.supplement_result(
            "NO-NEW",
            status=SupplementStatus.NO_NEW_EVIDENCE,
            impact=SupplementImpact.UNRESOLVED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            reason="No qualifying independent source was found")
        stored = self.route(
            "NO-NEW", result, self.base_revision,
            self.base_dossier,
            next_action="Wait for the recorded independent-source trigger")
        record = self.routes.load(stored.submission.version_id)
        self.assertIs(record.handoff, SupplementHandoff.UNRESOLVED)
        self.assertTrue(record.retry_requires_new_trigger)
        self.assertFalse(record.automatic_strength_granted)
        self.assertTrue(record.research_recheck_required)

    def test_unavailable_source_pauses_with_explicit_reason(self):
        result = self.supplement_result(
            "SOURCE-OUT",
            status=SupplementStatus.SOURCE_UNAVAILABLE,
            impact=SupplementImpact.UNRESOLVED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            reason="The qualifying source was unavailable")
        with self.assertRaisesRegex(
                SupplementRouteError, "stop reason"):
            self.route(
                "SOURCE-OUT-NO-STOP", result, self.base_revision,
                self.base_dossier,
                next_action="Wait for the source to return")
        stored = self.route(
            "SOURCE-OUT", result, self.base_revision,
            self.base_dossier,
            next_action="Wait for the source to return",
            stop_reason="The only qualifying independent source was unavailable")
        record = self.routes.load(stored.submission.version_id)
        self.assertIs(record.handoff, SupplementHandoff.PAUSE_SOURCE)
        self.assertTrue(record.retry_requires_new_trigger)
        self.assertFalse(record.automatic_strength_granted)

    def test_object_scope_change_returns_to_current_w23_s8(self):
        result = self.supplement_result(
            "SCOPE",
            status=SupplementStatus.PARTIAL,
            impact=SupplementImpact.OBJECT_OR_SCOPE_CHANGED,
            before_relation=EvidenceRelation.PARTIALLY_SUPPORTS,
            after_relation=EvidenceRelation.UNRESOLVED,
            object_changed=True,
            s8_required=True,
            reason="The new evidence changes the object and comparison scope")
        revision, snapshot = self.continuation("SCOPE", (), ())
        self.time += timedelta(seconds=1)
        recheck = TopicDecision(
            decision_id="DECISION-W38-S8-WATCH",
            topic_id=self.fx.cover.topic_id,
            theme_id=self.fx.cover.theme_id,
            edition_id=self.fx.cover.edition_id,
            spec_sha256="a" * 64,
            discovery_proposal_id=(
                self.fx.cover.discovery_proposal_id),
            question_version_id=self.fx.cover.question_version_id,
            candidate_index_ids=self.fx.cover.candidate_index_ids,
            candidate_ids=self.fx.cover.candidate_ids,
            cluster_ids=self.fx.cover.cluster_ids,
            stage=DecisionStage.S8,
            publication_basis=self.fx.cover.publication_basis,
            article_type=ArticleType.SOURCE_SELECTION,
            value_bases=self.fx.cover.value_bases,
            decision=TopicDecisionCode.WATCH,
            reasons=("Added evidence changed the object and comparison scope",),
            gaps=("A new selection and research plan are required",),
            next_action="Repeat S8 with the changed object and scope",
            previous_decision_id=self.fx.cover.decision_id,
            created_at=self.time)
        self.fx.editorial.append_decision(recheck)
        stored = self.route(
            "SCOPE", result, revision, snapshot,
            s8_decision=recheck.decision_id,
            next_action="Return the changed object to T03/S8")
        record = self.routes.load(stored.submission.version_id)
        self.assertIs(record.handoff, SupplementHandoff.RETURN_TO_T03_S8)
        self.assertTrue(record.s8_review_required)
        self.assertEqual(
            record.s8_recheck_decision_id, recheck.decision_id)


if __name__ == "__main__":
    unittest.main()
