"""Timecoded director editing tracks — all synthetic, no service calls."""
import copy
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import director_timeline as timeline
import director_workbook as workbook
import director_v2 as v2


class EditorialTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = v2.read_json(ROOT / "examples/quit-smoking/plan.json")
        cls.directions = v2.read_json(ROOT / "examples/quit-smoking/direction_v02.json")

    def samples(self):
        return copy.deepcopy(self.base), copy.deepcopy(self.directions)

    def test_absolute_timecodes_from_beats(self):
        base, d = self.samples()
        tracks, issues = timeline.assemble(base, d)
        self.assertEqual(len(tracks), len(base["shots"]))
        self.assertEqual(tracks[0]["picture_beats"][0]["absolute_in_s"], 0)
        self.assertEqual(tracks[0]["picture_beats"][-1]["absolute_out_s"], 5)
        self.assertEqual(tracks[1]["absolute_in_s"], 5)
        self.assertFalse(tracks[0]["source_media_exists"])
        self.assertFalse(tracks[0]["frame_accurate"])

    def test_sfx_absolute_timing_and_invalid_range(self):
        base, d = self.samples()
        d["shots"][0]["sound"]["effects"] = [{"time_s": 2.1, "cue": "paper"}]
        tracks, issues = timeline.assemble(base, d)
        self.assertEqual(tracks[0]["sound_effect_cues"][0]["absolute_at_s"], 2.1)
        d["shots"][0]["sound"]["effects"][0]["time_s"] = 100
        tracks, issues = timeline.assemble(base, d)
        self.assertIn("SFX_CUE_OUT_OF_RANGE", {f["code"] for f in issues})
        self.assertEqual(tracks[0]["sound_effect_cues"], [])

    def test_narration_not_falsely_promoted_to_exact_cues(self):
        base, d = self.samples()
        tracks, issues = timeline.assemble(base, d)
        self.assertEqual(tracks[0]["voiceover"]["cue_status"], "timing_unassigned")
        self.assertEqual(tracks[0]["voiceover"]["timed_cues"], [])
        self.assertIn("VOICEOVER_CUE_PENDING", {f["code"] for f in issues})

    def test_timecoded_vo_must_reproduce_original_narration(self):
        base, d = self.samples()
        full = base["shots"][0]["narration"]
        d["shots"][0]["speech"] = {"voiceover":{"cues":[
            {"from_s":0,"to_s":4,"text":full}
        ]}}
        _, issues = timeline.assemble(base, d)
        self.assertNotIn("VOICEOVER_CUE_DRIFT", {f["code"] for f in issues})
        d["shots"][0]["speech"]["voiceover"]["cues"][0]["text"] = "擅自修改文字"
        _, issues = timeline.assemble(base, d)
        self.assertIn("VOICEOVER_CUE_DRIFT", {f["code"] for f in issues})

    def test_voiceover_cues_overlap_is_blocker(self):
        base, d = self.samples()
        text = base["shots"][0]["narration"]
        d["shots"][0]["speech"] = {"voiceover":{"cues":[
            {"from_s":0,"to_s":3,"text":text[:4]},
            {"from_s":2,"to_s":4,"text":text[4:]}
        ]}}
        _, issues = timeline.assemble(base, d)
        self.assertIn("VOICEOVER_CUE_OVERLAP", {f["code"] for f in issues})
        self.assertTrue(any(f["severity"]=="blocker" for f in issues))

    def test_animation_out_of_range_is_blocker(self):
        base, d = self.samples()
        d["shots"][0]["animation"] = {"mode":"post", "elements":[
            {"layer":"title","action":"fade","timing":"from start", "from_s":0, "to_s":99}
        ]}
        _, issues = timeline.assemble(base, d)
        self.assertIn("EVENT_TIME_INVALID", {f["code"] for f in issues})

    def test_descriptive_animation_requires_manual_timecodes(self):
        base, d = self.samples()
        d["shots"][0]["animation"] = {"mode":"post", "elements":[
            {"layer":"title","action":"fade","timing":"when person looks down"}
        ]}
        tracks, issues = timeline.assemble(base, d)
        self.assertIn("ANIMATION_KEYFRAMES_NEED_TIMECODES", {f["code"] for f in issues})
        self.assertIsNone(tracks[0]["animation_layers"][0]["absolute_in_s"])

    def test_malformed_animation_does_not_crash(self):
        base, d = self.samples()
        d["shots"][0]["animation"]={"mode":"post","elements":["invalid"]}
        _, issues=timeline.assemble(base,d)
        self.assertIn("ANIMATION_ELEMENT_INVALID",{f["code"] for f in issues})

    def test_dialogue_and_voiceover_ducking_needs_review(self):
        base, d = self.samples()
        d["shots"][0]["speech"] = {"dialogue":[
            {"from_s":1,"to_s":2,"speaker_id":"CHAR01","text":"好","delivery":"quiet"}
        ]}
        tracks, issues = timeline.assemble(base, d)
        self.assertEqual(tracks[0]["sync_dialogue"][0]["absolute_in_s"], 1)
        self.assertIn("VO_DIALOGUE_MIX_REVIEW", {f["code"] for f in issues})

    def test_workbook_integrates_timecoded_editor_decisions(self):
        base, d = self.samples()
        book = workbook.compile_workbook(base, d)
        self.assertEqual(len(book["editor_decision_list"]),len(base["shots"]))
        self.assertGreater(len(book["director_review"]["timing_review_findings"]),0)
        text=workbook.render_markdown(book)
        self.assertIn("可交付剪辑工作台时间表",text)
        self.assertIn("节奏、配音与动画时间点待人工核查",text)

    def test_timing_blockers_prevent_complete_director_claim(self):
        base, d = self.samples()
        # Existing v0.2 validator does not check authored SFX ranges.
        d["shots"][0]["sound"]["effects"][0]["time_s"] = 77
        book = workbook.compile_workbook(base, d)
        self.assertFalse(book["director_review"]["creative_design_complete"])
        self.assertIn("SFX_CUE_OUT_OF_RANGE",
            {f["code"] for f in book["director_review"]["findings"]})


if __name__ == "__main__":
    unittest.main()
