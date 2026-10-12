"""Offline screenplay-adaptation contract tests; only synthetic fiction."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import article_intake
import screenplay_adaptation as a


TEXT = '她看着门口。母亲说：“先吃饭。”'


class ScreenplayAdaptationTests(unittest.TestCase):
    def setUp(self):
        self.plan = article_intake.prepare_episode(TEXT)["plan"]
        self.assertIsNotNone(self.plan)
        self.scenes = [{
            "id": "SC01", "heading": "INT. 餐厅 - 夜",
            "beats": [{
                "id": "B%02d" % (i + 1), "source_ids": [s["id"]],
                "operation": "keep", "dramatic_function": "推进关系",
                "action": "女孩停在门边，手攥着衣角。",
                "dialogue": [], "voiceover": s["narration"],
                "duration_s": s["duration"], "editorial_reason": "保持人物冲突"
            } for i, s in enumerate(self.plan["shots"])]
        }]
        self.proposal = {
            "version": a.VERSION, "theme": "先吃饭",
            "dramatic_question": "她会留下吗？",
            "turning_point": "母亲没有追问",
            "payoff": "她坐下来",
            "scenes": self.scenes, "omissions": [],
        }

    def test_basic_packet_and_fountain_are_review_only(self):
        brief = a.build_editor_request(self.plan, TEXT)
        self.assertFalse(brief["dispatch_allowed"])
        packet = a.build_review_packet(self.plan, TEXT, self.proposal)
        self.assertEqual(packet["status"], "pending_author_adaptation_review")
        self.assertEqual(packet["review"]["screenplay_beats"], len(self.plan["shots"]))
        self.assertIn("INT. 餐厅 - 夜", packet["screenplay_fountain"])
        self.assertFalse(packet["applied_to_director_plan"])
        self.assertFalse(packet["author_approval_authenticated"])
        self.assertFalse(packet["api_authorized"])

    def test_omitted_source_must_be_explained(self):
        proposed = deepcopy(self.proposal)
        removed = proposed["scenes"][0]["beats"].pop()
        with self.assertRaisesRegex(a.AdaptationError, "UNACKNOWLEDGED_SOURCE_LOSS"):
            a.validate_proposal(self.plan, TEXT, proposed)
        proposed["omissions"] = [{
            "source_id": removed["source_ids"][0], "reason": "压缩反复信息"
        }]
        report = a.validate_proposal(self.plan, TEXT, proposed)
        self.assertEqual(report["source_omitted"], 1)
        self.assertTrue(any(x["type"] == "omit" for x in report["proposed_changes"]))

    def test_false_verbatim_is_rejected_and_new_dialogue_is_explicit(self):
        proposed = deepcopy(self.proposal)
        beat = proposed["scenes"][0]["beats"][0]
        beat["dialogue"] = [{"speaker": "母亲", "line": "这句原文不存在", "origin": "source"}]
        with self.assertRaisesRegex(a.AdaptationError, "FALSE_VERBATIM"):
            a.validate_proposal(self.plan, TEXT, proposed)
        beat["dialogue"][0]["origin"] = "proposed"
        report = a.validate_proposal(self.plan, TEXT, proposed)
        self.assertTrue(any(x["type"] == "proposed_dialogue"
                            for x in report["proposed_changes"]))

    def test_split_source_is_tracked_not_silently_duplicated(self):
        proposed = deepcopy(self.proposal)
        first = proposed["scenes"][0]["beats"][0]
        extra = deepcopy(first)
        extra["id"] = "B-SPLIT-2"
        proposed["scenes"][0]["beats"].insert(1, extra)
        with self.assertRaisesRegex(a.AdaptationError, "DUPLICATE_SOURCE_WITHOUT_SPLIT"):
            a.validate_proposal(self.plan, TEXT, proposed)
        first["operation"] = "split"
        extra["operation"] = "split"
        report = a.validate_proposal(self.plan, TEXT, proposed)
        self.assertEqual(report["screenplay_beats"], len(self.plan["shots"]) + 1)

    def test_can_merge_two_source_beats_with_precise_provenance(self):
        if len(self.plan["shots"]) < 2:
            self.skipTest("needs two source shots")
        proposed = deepcopy(self.proposal)
        scene_beats = proposed["scenes"][0]["beats"]
        first, second = scene_beats[:2]
        first["source_ids"] = [first["source_ids"][0], second["source_ids"][0]]
        first["operation"] = "merge"
        first["voiceover"] = ""
        del scene_beats[1]
        report = a.validate_proposal(self.plan, TEXT, proposed)
        self.assertEqual(report["source_coverage"], len(self.plan["shots"]))
        self.assertTrue(any(x["type"] == "merge" for x in report["proposed_changes"]))

    def test_source_data_is_not_changed(self):
        original = deepcopy(self.plan)
        a.build_review_packet(self.plan, TEXT, self.proposal)
        self.assertEqual(original, self.plan)


    def test_public_dinner_sample_restructures_source_without_new_dialogue(self):
        import json
        folder = ROOT / "examples" / "dinner-dialogue-review"
        plan = json.loads((folder / "plan.json").read_text("utf-8"))
        source = (folder / "source.md").read_text("utf-8")
        proposal = json.loads((folder / "adaptation_proposal.json").read_text("utf-8"))
        report = a.validate_proposal(plan, source, proposal)
        operations = {b["operation"] for s in proposal["scenes"] for b in s["beats"]}
        self.assertTrue({"reorder", "split", "merge"} <= operations)
        self.assertEqual(report["source_coverage"], len(plan["shots"]))
        self.assertEqual(report["source_omitted"], 0)
        packet = a.build_review_packet(plan, source, proposal)
        self.assertIn("我问的是你，不是工作。", packet["screenplay_fountain"])
        self.assertEqual(packet["review"]["screenplay_beats"], 6)
        self.assertFalse(packet["api_authorized"])


if __name__ == "__main__":
    unittest.main()
