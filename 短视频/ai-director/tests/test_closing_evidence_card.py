"""Offline one-page evidence/credits tail tests; no media APIs."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import closing_evidence_card as c
import production_delivery as d


class FinalCreditsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = ROOT / "examples" / "quit-smoking"
        cls.base = json.loads((p / "plan.json").read_text("utf-8"))
        cls.direction = json.loads((p / "direction_v02.json").read_text("utf-8"))

    def test_evidence_card_is_last_and_not_video_generation(self):
        card = c.build_card(self.base)
        self.assertEqual(card["shot_id"], "POST_END_CREDITS")
        self.assertEqual(card["duration_s"], 1.8)
        self.assertEqual(card["start_s"], self.base["duration"])
        self.assertEqual(card["end_s"], self.base["duration"] + 1.8)
        self.assertEqual(len(card["visible_lines"]), len(self.base["claims"]))
        self.assertEqual(card["production_route"], "postproduction_only")
        self.assertEqual(card["audio"], "silent_no_voiceover")
        self.assertIsNone(card["video_model_prompt"])
        self.assertFalse(card["all_references_verified"])
        self.assertFalse(card["publication_approval"])
        self.assertFalse(card["requires_human_relayout"])
        svg = c.render_svg(card)
        self.assertEqual(svg.count("<svg "), 1)
        self.assertEqual(svg.count("<text "), len(self.base["claims"]) + 2)

    def test_integrated_workbook_export_keeps_original_story_shots(self):
        bundle = d.build_reference_delivery(self.base, self.direction)
        self.assertEqual(bundle["shooting_order"],
                         [s["id"] for s in self.base["shots"]])
        self.assertEqual(bundle["project"]["story_duration_s"], self.base["duration"])
        self.assertEqual(bundle["project"]["final_edit_duration_s"],
                         self.base["duration"] + 1.8)
        self.assertEqual(bundle["final_closing_card"]["position"],
                         "after_all_story_shots")
        md = d.render_operator_markdown(bundle)
        self.assertIn("最后一个镜头｜片尾依据与鸣谢", md)
        self.assertIn("POST", bundle["final_closing_card"]["shot_id"])

    def test_densely_cited_page_blocks_automatic_svg(self):
        plan = deepcopy(self.base)
        while len(plan["claims"]) < c.MAX_VISIBLE_LINES + 1:
            item = deepcopy(plan["claims"][0])
            item["id"] = "MORE" + str(len(plan["claims"]))
            plan["claims"].append(item)
        card = c.build_card(plan)
        self.assertTrue(card["requires_human_relayout"])
        with self.assertRaisesRegex(c.ClosingCardError, "DENSITY"):
            c.render_svg(card)

    def test_pure_fiction_has_no_evidence_page(self):
        plan = deepcopy(self.base)
        plan["claims"] = []
        self.assertIsNone(c.build_card(plan))

    def test_xml_escapes_untrusted_bibliography_strings(self):
        plan = deepcopy(self.base)
        plan["references"] = [{
            "claim_id": self.base["claims"][0]["id"],
            "author": "A&B <test>", "year": 2020, "journal": "Journal",
            "url": "https://example.org/paper"
        }]
        card = c.build_card(plan)
        svg = c.render_svg(card)
        self.assertIn("A&amp;B &lt;test&gt;", svg)
        self.assertNotIn("A&B <test>", svg)

    def test_invalid_duplicate_references_fail_closed(self):
        plan = deepcopy(self.base)
        plan["references"] = [
            {"claim_id": plan["claims"][0]["id"]},
            {"claim_id": plan["claims"][0]["id"]},
        ]
        with self.assertRaisesRegex(c.ClosingCardError, "REFERENCE_MAPPING"):
            c.build_card(plan)


if __name__ == "__main__":
    unittest.main()
