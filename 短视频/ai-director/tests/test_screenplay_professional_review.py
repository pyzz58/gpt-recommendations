"""Offline independent screenplay-critique contract tests, all public fiction."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import screenplay_adaptation as adapter
import screenplay_professional_review as review


class ScriptCraftReviewTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / "examples" / "dinner-dialogue-review"
        plan = json.loads((folder / "plan.json").read_text("utf-8"))
        source = (folder / "source.md").read_text("utf-8")
        proposal = json.loads((folder / "adaptation_proposal.json").read_text("utf-8"))
        self.source = source
        self.packet = adapter.build_review_packet(plan, source, proposal)
        self.quote = "我问的是你，不是工作。"

    def fixture(self, genre="fiction", deficient=()):
        flagged = set(deficient)
        rows = []
        blockers = []
        for key in review.CRITERIA:
            issue = key in flagged
            rows.append({
                "category": key,
                "assessment": "needs_revision" if issue else "effective",
                "screenplay_quote": self.quote,
                "specific_reason": "该处提供了具体可见的关系变化和观众可以识别的问题。",
                "rewrite_action": "重新阅读该场的前后节拍并判断人物回应是否具体。",
            })
            if issue:
                blockers.append({
                    "category": key,
                    "screenplay_quote": self.quote,
                    "viewer_consequence": "观众可能无法理解这一场为何触发人物态度变化。",
                    "rewrite_action": "把这一场动机与随后的行为写得更清楚。",
                })
        return {
            "version": review.VERSION,
            "genre": genre,
            "screenplay_sha256": hashlib.sha256(
                self.packet["screenplay_fountain"].encode("utf-8")).hexdigest(),
            "proposal_digest": self.packet["proposal_digest"],
            "criteria": rows,
            "blockers": blockers,
            "overall_recommendation": (
                "revise" if flagged else "ready_for_author_review"),
        }

    def test_editor_request_is_independent_unsent_not_professional_certification(self):
        request = review.build_review_request(self.packet, self.source, genre="essay")
        self.assertEqual(request["status"], "unsent_no_model_calls")
        self.assertFalse(request["dispatch_allowed"])
        self.assertTrue(request["requires_different_editor_perspective"])
        payload = json.loads(request["messages"][1]["content"])
        self.assertEqual(payload["screenplay"], self.packet["screenplay_fountain"])
        self.assertIn("essay", request["messages"][0]["content"])
        self.assertIn("绝不因无人物而扣分", request["messages"][0]["content"])

    def test_evidence_linked_critique_cannot_claim_automated_elite_quality(self):
        verdict = review.validate_review(
            self.packet, self.source, self.fixture(), genre="fiction")
        self.assertEqual(verdict["recommendation"], "ready_for_author_review")
        self.assertFalse(verdict["aesthetic_quality_verified"])
        self.assertFalse(verdict["professional_expertise_authenticated"])
        self.assertFalse(verdict["director_ready_authorized"])

    def test_real_problem_requires_located_blocker_and_revision_not_praise(self):
        sample = self.fixture(deficient=["scene_craft"])
        result = review.validate_review(self.packet, self.source, sample, genre="fiction")
        self.assertEqual(result["revision_categories"], ["scene_craft"])
        wrong = deepcopy(sample)
        wrong["blockers"] = []
        with self.assertRaisesRegex(review.ProfessionalReviewError, "MISSING_BLOCKERS"):
            review.validate_review(self.packet, self.source, wrong, genre="fiction")
        wrong = deepcopy(sample)
        wrong["overall_recommendation"] = "ready_for_author_review"
        with self.assertRaisesRegex(review.ProfessionalReviewError, "FALSE_READY"):
            review.validate_review(self.packet, self.source, wrong, genre="fiction")

    def test_hallucinated_quote_and_generic_note_fail(self):
        fake = self.fixture()
        fake["criteria"][0]["screenplay_quote"] = "这个世界上根本不存在的台词。"
        with self.assertRaisesRegex(review.ProfessionalReviewError, "QUOTE_NOT_IN_SCRIPT"):
            review.validate_review(self.packet, self.source, fake, genre="fiction")
        fake = self.fixture()
        fake["criteria"][0]["specific_reason"] = "很好"
        with self.assertRaisesRegex(review.ProfessionalReviewError, "GENERIC_EXPLANATION"):
            review.validate_review(self.packet, self.source, fake, genre="fiction")

    def test_nonfiction_cannot_be_penalized_for_no_fictional_cast(self):
        essay = self.fixture(genre="essay")
        row = next(x for x in essay["criteria"] if x["category"] == "characters_or_ideas")
        row.update({"assessment": "not_applicable", "screenplay_quote": "",
                    "rewrite_action": "", "specific_reason": "没有虚构人物，因此我认为这一项不适用。"})
        with self.assertRaisesRegex(review.ProfessionalReviewError, "NONFICTION_IDEAS_REQUIRED"):
            review.validate_review(self.packet, self.source, essay, genre="essay")
        row.update({"assessment": "effective", "screenplay_quote": self.quote,
                    "rewrite_action": "改为审查观众对中心论点的理解变化而非角色数量。"})
        self.assertEqual(review.validate_review(
            self.packet, self.source, essay, genre="essay")["genre"], "essay")

    def test_targeted_rewrite_not_dispatched_or_auto_approved(self):
        assessed = self.fixture(deficient=["story_journey", "scene_craft"])
        request = review.build_revision_request(
            self.packet, self.source, assessed, genre="fiction")
        self.assertFalse(request["dispatch_allowed"])
        self.assertTrue(request["needs_new_full_source_mapping"])
        self.assertTrue(request["human_author_approval_required"])
        data = json.loads(request["messages"][1]["content"])
        self.assertEqual(len(data["problems_to_fix"]), 2)
        self.assertEqual(data["original_source"], self.source)
        self.assertIn(self.quote, data["previous_screenplay"])
        with self.assertRaisesRegex(review.ProfessionalReviewError,
                                    "NO_REVISION_NEEDED"):
            review.build_revision_request(
                self.packet, self.source, self.fixture(), genre="fiction")

    def test_effective_criterion_may_have_no_forced_rewrite(self):
        report = self.fixture()
        for item in report["criteria"]:
            item["rewrite_action"] = ""
        result = review.validate_review(self.packet, self.source, report, genre="fiction")
        self.assertEqual(result["recommendation"], "ready_for_author_review")

    def test_replacing_an_input_script_invalidates_old_review(self):
        changed = deepcopy(self.packet)
        changed["screenplay_fountain"] += "\n伪造的额外片段"
        with self.assertRaisesRegex(review.ProfessionalReviewError, "SCRIPT_TAMPERED"):
            review.validate_review(
                changed, self.source, self.fixture(), genre="fiction")
        with self.assertRaisesRegex(review.ProfessionalReviewError, "SOURCE_STALE"):
            review.build_review_request(self.packet, self.source + "新稿", genre="fiction")


if __name__ == "__main__":
    unittest.main()
