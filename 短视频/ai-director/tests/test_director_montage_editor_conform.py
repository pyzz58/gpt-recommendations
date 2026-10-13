"""QO-D09: frame-accurate editor assembly contract, public synthetic scenes."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_team
import director_montage_editor_conform as conform
import director_shot_coverage as coverage
import screenplay_series_delivery as series
from test_director_editorial_montage import plan_fixture
from test_director_speech_cues import timed_plan
from test_director_shot_coverage import proposal, shot, span
from test_screenplay_series_delivery import assemble_original, dossier, series_plan


class MontageEditorConformTests(unittest.TestCase):
    def setUp(self):
        self.h, self.ds, self.plan, self.packet, self.coverage = plan_fixture()

    def make(self, fps=30):
        return conform.compile_work_order(
            self.h, self.ds, self.plan, self.packet, self.coverage, fps=fps)

    def test_exact_frame_boundaries_two_montages_and_unrendered_media(self):
        order = self.make()
        self.assertEqual(order["final_total_s"], 44)
        self.assertEqual(order["final_total_frames"], 1320)
        self.assertEqual(len(order["segments"]), 6)
        self.assertEqual(len(order["montage_cut_jobs"]), 2)
        cuts = order["montage_cut_jobs"]
        self.assertEqual([(x["out_shot_id"], x["in_shot_id"],
                           x["boundary_frame"], x["edit_type_exact"]) for x in cuts],
                         [("S01", "S02", 150, "sound_bridge"),
                          ("S03", "S04", 630, "hard_cut")])
        self.assertEqual(cuts[0]["required_gate"],
                         "J_L_AUDIO_BRIDGE_TIMING_AND_MEDIA_REQUIRED")
        self.assertIsNone(cuts[1]["required_gate"])
        self.assertTrue(cuts[1]["visual_transition_ready_for_media_conform"])
        self.assertEqual(order["story_first_frame"], 0)
        self.assertTrue(order["final_card_is_last"])
        self.assertFalse(order["ready_for_rough_cut"])
        self.assertFalse(order["render_or_publish_authorized"])
        self.assertIn("SOURCE_MEDIA_ASSETS_NOT_PROVIDED", order["operator_blockers"])
        self.assertIn("AUTHORITATIVE_SPEECH_AND_SUBTITLE_TIMING_REQUIRED",
                      order["operator_blockers"])
        report = conform.editor_instructions(order)
        self.assertIn("S01 -> S02 帧 150", report)
        self.assertIn("sound_bridge", report)
        self.assertIn("不可发布", report)

    def test_final_episode_extras_move_story_and_cuts_without_losing_budget(self):
        self.plan["episodes"][0]["intro_s"] = 2
        self.packet = series.build_per_episode_crew(self.h, self.ds, self.plan)
        proof = series.validate_breakdown(self.h, self.ds, self.plan)
        self.coverage["director_breakdown_digest"] = proof["director_breakdown_digest"]
        self.coverage["montage_plan"]["director_breakdown_digest"] = proof[
            "director_breakdown_digest"]
        self.coverage["montage_plan"]["coverage_digest"] = agent_team.fingerprint({
            k:v for k,v in self.coverage.items() if k != "montage_plan"})
        order = self.make()
        self.assertEqual(order["final_total_s"], 46)
        self.assertEqual(order["final_total_frames"], 1380)
        self.assertEqual(order["story_first_frame"], 60)
        self.assertEqual(order["montage_cut_jobs"][0]["boundary_frame"], 210)
        self.assertEqual(order["segments"][0]["kind"],
                         "reserved_postproduction")
        self.assertEqual(order["segments"][-1]["source_shot_id"], "S06")
        self.assertIn("RESERVED_INTRO_RECAP_BRIDGE_OUTRO_NOT_RENDERED",
                      order["operator_blockers"])

    def test_exact_timed_dialogue_audio_and_captions_are_shifted_once(self):
        h = assemble_original()
        ds = dossier(h)
        beats = [b for sc in h["screenplay_scenes"] for b in sc["beats"]]
        plan = series_plan(h, ds, [len(beats)])
        packet = series.build_per_episode_crew(h, ds, plan)
        cov = proposal(h, ds, plan, [
            shot(i, [span(b["id"], 0, b["duration_s"])])
            for i, b in enumerate(beats, 1)])
        cued = timed_plan(h, ds, plan)
        cov["speech_cue_timeline"] = cued
        # Cross-scene montage remains literal and source-locks the cue-aware
        # coverage digest (the montage never authoritatively rewrites words).
        old = self.coverage["montage_plan"]
        new = deepcopy(old)
        new["sequences"] = [deepcopy(old["sequences"][1])]
        new["sequences"][0]["sequence_id"] = "M01"
        new["director_breakdown_digest"] = plan["writer_dossier_digest"]  # overwritten below
        proof = series.validate_breakdown(h, ds, plan)
        new["director_breakdown_digest"] = proof["director_breakdown_digest"]
        new["coverage_digest"] = agent_team.fingerprint(cov)
        cov["montage_plan"] = new
        result = conform.compile_work_order(h, ds, plan, packet, cov, fps=30)
        self.assertGreater(len(result["speech_events"]), 0)
        self.assertGreater(len(result["subtitle_events"]), 0)
        self.assertEqual(result["speech_events"][0]["source_text_exact"],
                         beats[0]["dialogue"][0]["line"])
        self.assertEqual(result["speech_events"][0]["start_frame"], 30)
        self.assertEqual(result["speech_events"][0]["end_frame_exclusive"], 120)
        self.assertIn("REAL_LIP_SYNC_NOT_VERIFIED", result["operator_blockers"])

    def test_unknown_fps_and_tampered_source_packet_refused(self):
        for fps in (0, 29.97, True, 120):
            with self.subTest(fps=fps), self.assertRaisesRegex(
                    conform.ConformError, "EXPLICIT_SUPPORTED"):
                self.make(fps)
        bad = deepcopy(self.packet)
        bad["episodes"][0]["authoritative_episode_base"]["title"] = "forged"
        with self.assertRaisesRegex(coverage.ShotCoverageError,
                                    "PACKET_TAMPERED"):
            conform.compile_work_order(
                self.h, self.ds, self.plan, bad, self.coverage, fps=30)

    def test_subframe_timing_must_not_be_rounded_silently(self):
        h = deepcopy(self.h)
        h["screenplay_scenes"][0]["beats"][0]["duration_s"] = 5.01
        with self.assertRaises((conform.ConformError, coverage.ShotCoverageError,
                                series.SeriesDeliveryError)):
            conform.compile_work_order(
                h, self.ds, self.plan, self.packet, self.coverage, fps=30)

    def test_visual_transitions_require_specific_editorial_proof(self):
        for kind, code in (
                ("dissolve", "TRANSITION_HANDLES_AND_DURATION_REQUIRED"),
                ("match_cut", "MATCH_FRAME_VISUAL_VERIFICATION_REQUIRED"),
                ("jump_cut", "JUMP_CUT_ARTISTIC_REVIEW_REQUIRED")):
            with self.subTest(kind=kind):
                cov = deepcopy(self.coverage)
                cov["montage_plan"]["sequences"][0]["seams"][0][
                    "edit_type"] = kind
                result = conform.compile_work_order(
                    self.h, self.ds, self.plan, self.packet, cov, fps=30)
                self.assertIn(code, result["operator_blockers"])
                self.assertFalse(result["montage_cut_jobs"][0]
                                 ["visual_transition_ready_for_media_conform"])
                self.assertIsNone(result["montage_cut_jobs"][0]
                                  ["transition_duration_frames"])

    def test_no_montage_no_conform_export(self):
        cov = deepcopy(self.coverage)
        del cov["montage_plan"]
        with self.assertRaisesRegex(conform.ConformError, "MONTAGE_REQUIRED"):
            conform.compile_work_order(
                self.h, self.ds, self.plan, self.packet, cov, fps=30)


if __name__ == "__main__":
    unittest.main()
