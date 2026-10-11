"""Synthetic offline review lock tests. No real article or provider API used."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))

import article_intake as intake
import editorial_storyboard as creative
import editorial_review_lock as review
import agent_team as team
import director
import test_editorial_storyboard as creative_test_fixture


class EditorialReviewLockTests(unittest.TestCase):
    def setUp(self):
        sample = creative_test_fixture.EditorialStoryboardTests(methodName="test_strict_editorial_submit_end_to_end_without_model")
        sample.setUp()
        self.source = sample.source
        self.base = sample.base
        self.state = sample._run()
        self.candidate = creative.propose_directed_storyboard(
            sample.intake, self.state, self.source)
        self.sheet = review.build_review_sheet(self.candidate, self.source)

    def decide(self):
        d = review.decision_template(self.sheet)
        d["review_intent"] = "accept_for_planning"
        d["global_direction"]["choice"] = "keep"
        for s in d["shots"]:
            s["choice"] = "keep"
        d["omissions"]["choice"] = "acknowledge_as_omitted"
        d["claims"]["choice"] = "acknowledge_unverified_for_planning"
        for p in d["source_change_proposals"]:
            p["choice"] = "do_not_apply"
        return d

    def test_review_sheet_never_assumes_approval(self):
        self.assertEqual(self.sheet["status"], "awaiting_author_review")
        self.assertIsNone(self.sheet["shots"][0]["choice"])
        self.assertIsNone(self.sheet["global_direction"]["choice"])
        self.assertIsNone(self.sheet["claims"]["choice"])
        self.assertFalse(self.sheet["human_identity_verified"])
        self.assertFalse(self.sheet["author_approval_authenticated"])
        self.assertTrue(self.sheet["private_material"])

    def test_decision_template_all_undecided(self):
        decisions = review.decision_template(self.sheet)
        self.assertIsNone(decisions["review_intent"])
        self.assertTrue(all(s["choice"] is None for s in decisions["shots"]))
        self.assertIsNone(decisions["omissions"]["choice"])
        with self.assertRaisesRegex(review.EditorialReviewError, "INTENT_REQUIRED"):
            review.evaluate_review(self.candidate, self.source, decisions)

    def test_complete_review_locks_only_planning_snapshot(self):
        choices = self.decide()
        status = review.evaluate_review(self.candidate, self.source, choices)
        self.assertEqual(status["status"], "planning_snapshot_lockable")
        self.assertEqual(status["blockers"], [])
        self.assertFalse(status["fact_checked"])
        self.assertFalse(status["trusted_reviewer_identity_verified"])
        self.assertFalse(status["external_paid_api_authorized"])
        locked = review.lock_planning_snapshot(self.candidate, self.source, choices)
        self.assertEqual(locked["status"], "planning_locked_identity_unverified")
        self.assertEqual(locked["plan_digest"], team.fingerprint(self.candidate["candidate_plan"]))
        self.assertFalse(locked["human_release_approved"])
        self.assertFalse(locked["author_identity_verified"])
        self.assertFalse(locked["paid_model_authorized"])
        self.assertFalse(locked["claims_verified"])

    def test_offline_team_bound_only_to_new_locked_plan(self):
        lock = review.lock_planning_snapshot(self.candidate, self.source, self.decide())
        staged = review.stage_locked_team(lock, self.source)
        self.assertEqual(staged["status"], "offline_planning_only_not_authorized_to_dispatch")
        self.assertEqual(staged["ready_tasks"], ["director_brief"])
        self.assertEqual(staged["team"]["base_digest"], lock["plan_digest"])
        self.assertEqual(staged["team"]["source_digest"], lock["source_digest"])
        self.assertFalse(staged["team"]["release"]["paid_api_authorized"])
        self.assertFalse(staged["team"]["release"]["human_approved"])
        self.assertNotEqual(staged["team"]["base_digest"], self.state["base_digest"])

    def test_revision_request_blocks_lock_and_is_per_shot(self):
        choices = self.decide()
        choices["review_intent"] = "request_changes"
        choices["review_note"] = "这条需要换一个能够拍出来的动作"
        choices["shots"][0]["choice"] = "revise"
        choices["shots"][0]["review_note"] = "不要突然出现另一只手"
        result = review.evaluate_review(self.candidate, self.source, choices)
        self.assertEqual(result["status"], "revision_required")
        self.assertEqual(result["shot_rework"][0]["shot_id"], self.sheet["shots"][0]["shot_id"])
        self.assertIn("SHOT_REVISIONS_REQUIRED", result["blockers"])
        with self.assertRaisesRegex(review.EditorialReviewError, "UNRESOLVED_BLOCKERS"):
            review.lock_planning_snapshot(self.candidate, self.source, choices)

    def test_request_changes_requires_explanation(self):
        choices = self.decide()
        choices["review_intent"] = "request_changes"
        with self.assertRaisesRegex(review.EditorialReviewError, "EXPLANATION_REQUIRED"):
            review.evaluate_review(self.candidate, self.source, choices)

    def test_reject_candidate_blocks_lock_without_fake_approval(self):
        d = self.decide()
        d["review_intent"] = "reject_candidate"
        d["review_note"] = "完全不是想要的风格"
        result = review.evaluate_review(self.candidate, self.source, d)
        self.assertIn("REVIEWER_REJECTED_OR_REQUESTED_CHANGES", result["blockers"])
        with self.assertRaises(review.EditorialReviewError):
            review.lock_planning_snapshot(self.candidate, self.source, d)

    def test_incomplete_shot_decisions_fail_closed(self):
        d = self.decide()
        d["shots"] = d["shots"][:-1]
        with self.assertRaisesRegex(review.EditorialReviewError, "SHOT_COVERAGE"):
            review.evaluate_review(self.candidate, self.source, d)

    def test_shot_reorder_or_other_shot_digest_rejected(self):
        d = self.decide()
        d["shots"] = list(reversed(d["shots"]))
        with self.assertRaisesRegex(review.EditorialReviewError, "SHOT_STALE_OR_REORDERED"):
            review.evaluate_review(self.candidate, self.source, d)
        d = self.decide()
        d["shots"][0]["shot_digest"] = "0"*64
        with self.assertRaisesRegex(review.EditorialReviewError, "SHOT_STALE_OR_REORDERED"):
            review.evaluate_review(self.candidate, self.source, d)

    def test_other_candidate_digest_rejected(self):
        d = self.decide()
        d["candidate_base_digest"] = "0"*64
        with self.assertRaisesRegex(review.EditorialReviewError, "STALE_OR_OTHER_EPISODE"):
            review.evaluate_review(self.candidate, self.source, d)

    def test_external_source_mutation_rejected(self):
        with self.assertRaisesRegex(review.EditorialReviewError, "EPISODE_SOURCE_MISMATCH"):
            review.build_review_sheet(self.candidate, self.source + "改动")

    def test_candidate_plan_mutation_rejected_before_review(self):
        corrupt = deepcopy(self.candidate)
        corrupt["candidate_plan"]["shots"][0]["narration"] += "不应出现的台词"
        with self.assertRaisesRegex(review.EditorialReviewError, "CANDIDATE_DIGEST_MISMATCH"):
            review.build_review_sheet(corrupt, self.source)

    def test_snapshot_plan_mutation_rejected_before_team(self):
        snapshot = review.lock_planning_snapshot(self.candidate, self.source, self.decide())
        snapshot["plan"]["shots"][0]["duration"] += 1
        with self.assertRaisesRegex(review.EditorialReviewError, "LOCK_PLAN_MUTATED"):
            review.stage_locked_team(snapshot, self.source)

    def test_fake_identity_and_payment_flags_rejected(self):
        snap = review.lock_planning_snapshot(self.candidate, self.source, self.decide())
        for field in ("author_identity_verified", "paid_model_authorized", "human_release_approved"):
            corrupt = deepcopy(snap)
            corrupt[field] = True
            with self.assertRaisesRegex(review.EditorialReviewError, "UNTRUSTED_LOCK"):
                review.stage_locked_team(corrupt, self.source)

    def test_omissions_must_be_explicitly_reviewed(self):
        d = self.decide()
        d["omissions"]["choice"] = "revise"
        result = review.evaluate_review(self.candidate, self.source, d)
        self.assertIn("OMISSIONS_UNRESOLVED", result["blockers"])
        d["omissions"]["digest"] = "0"*64
        with self.assertRaisesRegex(review.EditorialReviewError, "OMISSIONS_STALE_DIGEST"):
            review.evaluate_review(self.candidate, self.source, d)

    def test_unverified_claims_not_treated_as_verified(self):
        d = self.decide()
        d["claims"]["choice"] = "request_fact_review"
        result = review.evaluate_review(self.candidate, self.source, d)
        self.assertIn("FACT_REVIEW_PENDING", result["blockers"])
        d["claims"]["choice"] = "acknowledge_unverified_for_planning"
        snap = review.lock_planning_snapshot(self.candidate, self.source, d)
        self.assertFalse(snap["claims_verified"])
        self.assertTrue(all(c["status"] == "needs_review" for c in snap["plan"]["claims"]))

    def test_global_direction_must_be_kept_to_lock(self):
        d = self.decide()
        d["global_direction"]["choice"] = "revise"
        result = review.evaluate_review(self.candidate, self.source, d)
        self.assertIn("GLOBAL_REVIEW_REQUIRED", result["blockers"])

    def test_nonempty_notes_required_for_requested_shot_change(self):
        d = self.decide()
        d["shots"][0]["choice"] = "revise"
        with self.assertRaisesRegex(review.EditorialReviewError, "SHOT_NOTE_INVALID"):
            review.evaluate_review(self.candidate, self.source, d)

    def test_source_change_proposals_must_be_resolved_separately(self):
        sample = creative_test_fixture.EditorialStoryboardTests(methodName="test_script_edit_unapproved_change_remains_unapplied")
        sample.setUp()
        treatment = deepcopy(sample.treatment)
        treatment["story_treatment"]["source_change_proposals"].append({
            "reason": "开头更短", "proposed_change": "能否更改开头",
            "requires_user_approval": True, "approved": False})
        state = sample._run(treatment=treatment)
        candidate = creative.propose_directed_storyboard(sample.intake,state,sample.source)
        sheet = review.build_review_sheet(candidate,sample.source)
        self.assertEqual(len(sheet["source_change_proposals"]),1)
        d = review.decision_template(sheet)
        d["review_intent"] = "accept_for_planning"
        d["global_direction"]["choice"] = "keep"
        for item in d["shots"]: item["choice"] = "keep"
        d["omissions"]["choice"] = "acknowledge_as_omitted"
        d["claims"]["choice"] = "acknowledge_unverified_for_planning"
        d["source_change_proposals"][0]["choice"] = "defer_for_separate_approval"
        x = review.evaluate_review(candidate,sample.source,d)
        self.assertIn("SOURCE_EDITS_PENDING_SEPARATE_APPROVAL",x["blockers"])
        d["source_change_proposals"][0]["choice"] = "do_not_apply"
        lock = review.lock_planning_snapshot(candidate,sample.source,d)
        self.assertFalse(lock["source_edits_applied"])

    def test_proposal_reordering_or_digest_change_rejected(self):
        sample = creative_test_fixture.EditorialStoryboardTests(methodName="test_script_edit_unapproved_change_remains_unapplied")
        sample.setUp()
        treatment = deepcopy(sample.treatment)
        treatment["story_treatment"]["source_change_proposals"].append({
            "reason": "改短", "proposed_change": "删一句话",
            "requires_user_approval": True, "approved": False})
        state=sample._run(treatment=treatment)
        candidate=creative.propose_directed_storyboard(sample.intake,state,sample.source)
        sh=review.build_review_sheet(candidate,sample.source)
        d=review.decision_template(sh)
        d["review_intent"]="accept_for_planning"
        d["global_direction"]["choice"]="keep"
        for item in d["shots"]:item["choice"]="keep"
        d["omissions"]["choice"]="acknowledge_as_omitted"
        d["claims"]["choice"]="acknowledge_unverified_for_planning"
        d["source_change_proposals"][0]["choice"]="do_not_apply"
        d["source_change_proposals"][0]["proposal_digest"]="0"*64
        with self.assertRaisesRegex(review.EditorialReviewError, "PROPOSAL_STALE_OR_REORDERED"):
            review.evaluate_review(candidate,sample.source,d)

    def test_missing_source_proposal_decision_rejected(self):
        d=self.decide()
        d["source_change_proposals"]=[{"proposal_index":0,"proposal_digest":"fake",
                                      "choice":"do_not_apply","review_note":""}]
        with self.assertRaisesRegex(review.EditorialReviewError, "PROPOSALS_COVERAGE"):
            review.evaluate_review(self.candidate,self.source,d)

    def test_unexpected_review_fields_fail_closed(self):
        d=self.decide()
        d["approved"]=True
        with self.assertRaisesRegex(review.EditorialReviewError, "DECISION_SHAPE"):
            review.evaluate_review(self.candidate,self.source,d)

    def test_review_html_escapes_untrusted_private_source(self):
        malicious = deepcopy(self.sheet)
        malicious["title"] = "</h1><script>alert('bad')</script>"
        malicious["shots"][0]["visual_intention"] = "<img src=x onerror=alert(1)>"
        page = review.render_private_review_html(malicious)
        self.assertNotIn("<script>",page)
        self.assertNotIn("<img src=",page)
        self.assertIn("&lt;script&gt;",page)
        self.assertIn("没有授权按钮",page)

    def test_source_hash_and_review_notes_not_written_to_public(self):
        snap=review.lock_planning_snapshot(self.candidate,self.source,self.decide())
        self.assertEqual(snap["actual_provider_calls"],0)
        self.assertFalse(snap["paid_model_authorized"])
        self.assertNotIn("api_key", json.dumps(snap).lower())
        self.assertEqual(snap["source_digest"],
                         self.candidate["episode_source_sha256"])


if __name__=="__main__":
    unittest.main()
