"""Regression tests for director/editor handoff readiness and J/L-cut decisions.

Uses the public synthetic/educational example only. No media, video APIs or
third-party post-production packages are loaded.
"""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_v2 as v2
import director_workbook as workbook
import director_timeline as timeline


class EditorHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=v2.read_json(ROOT/"examples/quit-smoking/plan.json")
        cls.direction=v2.read_json(ROOT/"examples/quit-smoking/direction_v02.json")

    def base_direction(self):
        d=copy.deepcopy(self.direction)
        prev=None
        for shot,directed in zip(self.plan["shots"],d["shots"]):
            directed["editing"]={
                "incoming_transition":prev["transition"] if prev else "start",
                "outgoing_transition":shot["transition"],
                "cut_reason":"At the visible story change, cut to the next shot",
                "rhythm":"Hold the final action until the audience understands the beat",
                "assembly_instructions":"Respect the action axis and cut on the intended beat"}
            directed["animation"]={
                "mode":"none", "timing":"no additional layers",
                "elements":[], "render_in_post":False, "style":"natural footage"}
            if shot["graphics"]["type"] not in ("none", "None", None):
                directed["animation"]={
                    "mode":"post", "timing":"fade and hold on the beat",
                    "elements":[{"layer":"graphic", "action":"fade-in",
                                 "timing":"0s through shot end",
                                 "from_s":0,"to_s":shot["duration"]}],
                    "render_in_post":True, "style":"readable vector text"}
            directed["speech"]={
                "voiceover":{"text":shot["narration"],
                             "delivery":"restrained Mandarin" if shot["narration"] else "silent",
                             "timing":"from 0 to end" if shot["narration"] else "silence"},
                "dialogue":[], "subtitle_direction":"lower safe area",
                "lip_sync_policy":"narrator VO only"}
            prev=shot
        return d

    def complete_direction(self):
        d=self.base_direction()
        for shot,directed in zip(self.plan["shots"],d["shots"]):
            directed["editing"]["audio_bridge"]={
                "type":"none","duration_s":0,"track":"none",
                "reason":"Use hard picture cut; sound stops on the same boundary"}
            if shot["narration"]:
                directed["speech"]["voiceover"]["cues"]=[{
                    "from_s":0,"to_s":shot["duration"],"text":shot["narration"]}]
        return d

    def test_filled_fields_without_timecodes_not_handoff_ready(self):
        book=workbook.compile_workbook(self.plan,self.base_direction())
        self.assertTrue(book["director_review"]["creative_design_complete"])
        self.assertFalse(book["director_review"]["editor_handoff_ready"])
        self.assertGreater(book["director_review"]["editor_handoff_pending"],0)
        self.assertIn("AUDIO_BRIDGE_DECISION_PENDING",
                      {x["code"] for x in book["director_review"]["handoff_findings"]})
        self.assertFalse(book["human_approved"])

    def test_explicit_timed_draft_is_handoff_ready_but_not_approved(self):
        book=workbook.compile_workbook(self.plan,self.complete_direction())
        self.assertTrue(book["director_review"]["creative_design_complete"])
        self.assertTrue(book["director_review"]["editor_handoff_ready"])
        self.assertEqual(book["director_review"]["editor_handoff_pending"],0)
        self.assertFalse(book["human_approved"])
        self.assertFalse(book["paid_api_authorized"])
        self.assertFalse(book["publishing_allowed"])

    def test_simple_no_bridge_creates_non_invented_decision(self):
        tracks,issues=timeline.assemble(self.plan,self.complete_direction())
        self.assertEqual(issues.count({"code":"AUDIO_BRIDGE_DECISION_PENDING"}),0)
        self.assertEqual(tracks[0]["edit"]["audio_bridge"]["type"],"none")

    def test_j_cut_maps_next_audio_before_picture_cut(self):
        d=self.complete_direction()
        d["shots"][0]["editing"]["audio_bridge"]={
            "type":"j_cut","duration_s":1,"track":"music",
            "reason":"new scene audio foreshadows the cut"}
        tracks,issues=timeline.assemble(self.plan,d)
        self.assertFalse(any(x["severity"]=="blocker" for x in issues),issues)
        bridge=tracks[0]["edit"]["audio_bridge"]
        self.assertEqual(bridge["next_shot_id"],"S02")
        self.assertEqual(bridge["absolute_in_s"],4)
        self.assertEqual(bridge["absolute_out_s"],5)

    def test_l_cut_maps_previous_audio_after_picture_cut(self):
        d=self.complete_direction()
        d["shots"][0]["editing"]["audio_bridge"]={
            "type":"l_cut","duration_s":1.5,"track":"ambience",
            "reason":"residual room sound helps scene transition"}
        tracks,issues=timeline.assemble(self.plan,d)
        self.assertFalse(any(x["severity"]=="blocker" for x in issues),issues)
        bridge=tracks[0]["edit"]["audio_bridge"]
        self.assertEqual(bridge["absolute_in_s"],5)
        self.assertEqual(bridge["absolute_out_s"],6.5)

    def test_last_shot_cannot_cross_into_nonexistent_next(self):
        d=self.complete_direction()
        d["shots"][-1]["editing"]["audio_bridge"]={
            "type":"j_cut","duration_s":1,"track":"voiceover",
            "reason":"not actually permitted because there is no next shot"}
        tracks,issues=timeline.assemble(self.plan,d)
        self.assertIn("AUDIO_BRIDGE_TIME_INVALID",{x["code"] for x in issues})
        self.assertIsNone(tracks[-1]["edit"]["audio_bridge"])

    def test_incorrect_bridge_duration_does_not_pass(self):
        d=self.complete_direction()
        d["shots"][0]["editing"]["audio_bridge"]={
            "type":"l_cut","duration_s":100,"track":"music",
            "reason":"overlong"}
        _,issues=timeline.assemble(self.plan,d)
        self.assertIn("AUDIO_BRIDGE_TIME_INVALID",{x["code"] for x in issues})

    def test_invalid_bridge_is_reported_not_crashed(self):
        d=self.complete_direction()
        d["shots"][0]["editing"]["audio_bridge"]={
            "type":[],"duration_s":2,"track":[],"reason":"invalid"}
        _,issues=timeline.assemble(self.plan,d)
        self.assertIn("AUDIO_BRIDGE_INVALID",{x["code"] for x in issues})

    def test_audio_bridge_none_cannot_claim_length_or_voice_track(self):
        d=self.complete_direction()
        d["shots"][0]["editing"]["audio_bridge"]={
            "type":"none","duration_s":0.5,"track":"voiceover"}
        _,issues=timeline.assemble(self.plan,d)
        self.assertIn("AUDIO_BRIDGE_NONE_CONFLICT",{x["code"] for x in issues})

    def test_animation_requested_but_no_elements_is_creative_gap(self):
        d=self.complete_direction()
        d["shots"][0]["animation"]["mode"]="post"
        d["shots"][0]["animation"]["elements"]=[]
        book=workbook.compile_workbook(self.plan,d)
        self.assertFalse(book["director_review"]["creative_design_complete"])
        self.assertIn("ANIMATION_ELEMENTS_REQUIRED",
                      {x["code"] for x in book["director_review"]["findings"]})

    def test_voiceover_cues_drift_blocks_handoff(self):
        d=self.complete_direction()
        d["shots"][0]["speech"]["voiceover"]["cues"][0]["text"]="changed script"
        book=workbook.compile_workbook(self.plan,d)
        self.assertFalse(book["director_review"]["editor_handoff_ready"])
        self.assertIn("VOICEOVER_CUE_DRIFT",
                      {x["code"] for x in book["director_review"]["findings"]})

    def test_markdown_exposes_handoff_readiness(self):
        w=workbook.compile_workbook(self.plan,self.base_direction())
        self.assertIn("剪辑交接就绪：否",workbook.render_markdown(w))
        w=workbook.compile_workbook(self.plan,self.complete_direction())
        self.assertIn("剪辑交接就绪：是",workbook.render_markdown(w))


if __name__=="__main__":
    unittest.main()
