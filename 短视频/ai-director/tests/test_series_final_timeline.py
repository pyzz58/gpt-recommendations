"""QO-D13: full 90-second story + explicit extras + final credits, offline."""
from __future__ import annotations

from copy import deepcopy
import unittest
import json
from pathlib import Path

import closing_evidence_card as card
import production_delivery as delivery
import series_final_timeline as final
from test_closing_evidence_card import FinalCreditsTests


class FullSeriesTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make this test independent of discovery/order of legacy test modules.
        FinalCreditsTests.setUpClass()
        fixture = FinalCreditsTests("test_evidence_card_is_last_and_not_video_generation")
        cls.script = fixture
        cls.base = deepcopy(fixture.base)
        cls.direction = deepcopy(fixture.direction)

    def series(self, *, sourced=True, evidence=1.8, intro=0,
               recap=0, bridge=0, outro=0, decision=None):
        plan = self.script.evidence_base() if sourced else deepcopy(self.base)
        extras = {"intro_s":intro, "recap_s":recap, "bridge_s":bridge,
                  "outro_s":outro, "evidence_s":evidence}
        total = plan["duration"] + sum(extras.values())
        plan["series_context"] = {
            "kind": "director_episode_from_complete_screenplay",
            "episode_id": "EP01",
            "max_total_duration_s": 90,
            "episode_story_s": plan["duration"],
            "reserved_additional_s": sum(extras.values()),
            "reserved_extra_components_s": extras,
            "include_final_evidence_card": evidence > 0 if decision is None else decision,
            "episode_total_planned_s": total}
        return plan

    def test_series_abs_timeline_handles_real_intro_recap_outro_and_last_card(self):
        plan = self.series(intro=2, recap=1, bridge=1, outro=2)
        work = delivery.build_reference_delivery(plan,self.direction)
        timeline = work["series_final_editor_timeline"]
        self.assertEqual(timeline["planned_final_duration_s"],plan["series_context"]["episode_total_planned_s"])
        self.assertLessEqual(timeline["planned_final_duration_s"],90)
        self.assertFalse(timeline["actual_final_media_verified"])
        self.assertTrue(timeline["last_card_is_final_segment"])
        self.assertEqual(timeline["absolute_segments"][0]["editor_segment_id"],"intro_s")
        self.assertEqual(timeline["absolute_segments"][1]["editor_segment_id"],"recap_s")
        self.assertEqual(timeline["absolute_segments"][-1]["editor_segment_id"],"POST_END_CREDITS")
        self.assertEqual(work["project"]["final_edit_duration_s"],timeline["planned_final_duration_s"])
        self.assertEqual(work["final_closing_card"]["start_s"],
                         timeline["absolute_segments"][-1]["start_s"])
        self.assertEqual(work["final_closing_card"]["end_s"],
                         timeline["absolute_segments"][-1]["end_s"])
        segment_ids = [x["source_shot_id"] for x in timeline["absolute_segments"]
                       if x["kind"]=="story_shot_unrendered"]
        self.assertEqual(segment_ids,[x["id"] for x in plan["shots"]])
        self.assertFalse(work["publishing_allowed"])

    def test_source_material_does_not_force_unsolicited_final_card(self):
        plan = self.series(sourced=True,evidence=0,intro=1)
        self.assertIsNone(card.build_card(plan))
        out = delivery.build_reference_delivery(plan,self.direction)
        self.assertIsNone(out["final_closing_card"])
        self.assertEqual(out["series_final_editor_timeline"]["reserved_components_s"]["evidence_s"],0)

    def test_cited_card_must_match_actual_postproduction_duration(self):
        too_short = self.series(evidence=1)
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "CREDITS_RUNTIME_MISMATCH"):
            delivery.build_reference_delivery(too_short,self.direction)
        wrong = self.series(evidence=1.8,decision=False)
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "CREDITS_DECISION_CHANGED"):
            delivery.build_reference_delivery(wrong,self.direction)

    def test_missing_referenced_source_cannot_fake_evidence_page(self):
        unsourced = self.series(sourced=False,evidence=1.8)
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "CREDITS_MISSING_OR_UNRESERVED"):
            delivery.build_reference_delivery(unsourced,self.direction)

    def test_episode_story_or_components_can_not_lie_about_budget(self):
        bad = self.series(evidence=1.8,intro=1)
        bad["series_context"]["reserved_additional_s"] = 0
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "EXTRAS_BUDGET_DRIFT"):
            delivery.build_reference_delivery(bad,self.direction)
        bad = self.series(evidence=1.8,intro=1)
        bad["series_context"]["episode_total_planned_s"] -= 1
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "PLANNED_RUNTIME_DRIFT"):
            delivery.build_reference_delivery(bad,self.direction)
        bad = self.series(evidence=1.8,intro=1)
        del bad["series_context"]["reserved_extra_components_s"]
        with self.assertRaisesRegex(delivery.ProductionDeliveryError,
                                    "EXTRA_COMPONENTS_REQUIRED"):
            delivery.build_reference_delivery(bad,self.direction)

    def test_true_over_90_rejected_even_if_story_alone_is_under_cap(self):
        too_long = self.series(evidence=1.8,intro=90-self.base["duration"])
        self.assertEqual(too_long["duration"]+too_long["series_context"]["reserved_extra_components_s"]["intro_s"],90)
        # Direct editor preflight catches the full 91.8s composition, regardless
        # of what story-only constraints already reject at their own stage.
        with self.assertRaisesRegex(final.SeriesTimelineError,"OVER_90"):
            final.compile_final_timeline(too_long,card.build_card(too_long))

    def test_single_abs_story_and_optional_credits_no_video_rendered(self):
        plan=self.series(sourced=True,evidence=1.8)
        result=delivery.build_reference_delivery(plan,self.direction)
        self.assertEqual(result["series_final_editor_timeline"]["planned_final_duration_s"],
                         plan["duration"]+1.8)
        self.assertTrue(all(not x["real_media_available"]
                            for x in result["series_final_editor_timeline"]["absolute_segments"]))


if __name__=="__main__":
    unittest.main()
