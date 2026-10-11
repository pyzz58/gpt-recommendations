"""Script-first professional director workbook regressions, no model access."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import director_v2 as v2
import director_workbook as workbook


class WorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=v2.read_json(ROOT/"examples/quit-smoking/plan.json")
        cls.direction=v2.read_json(ROOT/"examples/quit-smoking/direction_v02.json")

    def completed(self):
        d=copy.deepcopy(self.direction)
        previous=None
        for shot, directed in zip(self.base["shots"],d["shots"]):
            directed["editing"]={
                "incoming_transition": previous["transition"] if previous else "start",
                "outgoing_transition": shot["transition"],
                "cut_reason": "Motivated by visible change in the previous and current shot",
                "rhythm": "Hold final image long enough to see its intended change",
                "assembly_instructions": "Maintain one visual axis and clean audio handoff"}
            directed["animation"]={
                "mode":"none","timing":"no additional motion required",
                "elements":[],"render_in_post":False,"style":"natural photographed movement"}
            directed["speech"]={
                "voiceover":{"text":shot["narration"],
                             "delivery":"spoken Mandarin, restrained pace" if shot["narration"] else "none, silent credit card",
                             "timing":"align with opening visual beat" if shot["narration"] else "no narration"},
                "dialogue":[],"subtitle_direction":"high contrast, platform safe margins",
                "lip_sync_policy":"voiceover only, no lip movements"}
            previous=shot
        return d

    def test_old_direction_reports_missing_creative_core_not_approved(self):
        w=workbook.compile_workbook(self.base,self.direction)
        self.assertFalse(w["director_review"]["creative_design_complete"])
        self.assertGreater(w["director_review"]["unresolved"],0)
        self.assertFalse(w["human_approved"])
        self.assertFalse(w["is_video"])
        codes={f["code"] for f in w["director_review"]["findings"]}
        self.assertIn("EDITING_MISSING",codes)
        self.assertIn("ANIMATION_MISSING",codes)
        self.assertIn("SPEECH_MISSING",codes)

    def test_full_filled_directions_produce_creative_complete_workbook(self):
        w=workbook.compile_workbook(self.base,self.completed())
        self.assertTrue(w["director_review"]["creative_design_complete"])
        self.assertEqual(w["director_review"]["unresolved"],0)
        self.assertFalse(w["human_approved"])
        self.assertFalse(w["paid_api_authorized"])
        self.assertFalse(w["publishing_allowed"])
        self.assertEqual(len(w["shots"]),len(self.base["shots"]))

    def test_story_structure_and_timeline_preserved(self):
        w=workbook.compile_workbook(self.base,self.completed())
        self.assertEqual(w["overview"]["core_message"],self.base["core_message"])
        self.assertEqual(w["overview"]["duration_s"],self.base["duration"])
        self.assertEqual(w["assembly_timeline"][0]["start_s"],0)
        self.assertEqual(w["assembly_timeline"][-1]["end_s"],self.base["duration"])
        for s,original in zip(w["shots"],self.base["shots"]):
            self.assertEqual(s["script"]["narration"],original["narration"])
            self.assertEqual(s["script"]["subtitle"],original["subtitles"])
            self.assertEqual(s["performance"]["action"],original["action"])
            self.assertEqual(s["production"]["route"],
                             v2.production_route(original,next(d for d in self.completed()["shots"]
                                                              if d["shot_id"]==original["id"])["generation"]))

    def test_voiceover_cannot_be_changed_only_in_direction(self):
        d=self.completed()
        d["shots"][0]["speech"]["voiceover"]["text"]="new unauthorized voiceover"
        w=workbook.compile_workbook(self.base,d)
        self.assertIn("VOICEOVER_DRIFT",{f["code"] for f in w["director_review"]["findings"]})
        self.assertEqual(w["shots"][0]["script"]["narration"],self.base["shots"][0]["narration"])

    def test_detect_cut_conflict_between_base_and_direction(self):
        d=self.completed()
        d["shots"][0]["editing"]["outgoing_transition"]="dissolve"
        w=workbook.compile_workbook(self.base,d)
        self.assertIn("EDIT_CONFLICTS_BASE",{f["code"] for f in w["director_review"]["findings"]})
        self.assertEqual(w["assembly_timeline"][0]["base_out_transition"],self.base["shots"][0]["transition"])

    def test_unrecognized_dialogue_speaker_or_bad_timing(self):
        d=self.completed()
        d["shots"][0]["speech"]["dialogue"]=[
            {"speaker_id":"EXTRA99","text":"Hello","delivery":"whisper",
             "from_s":-1,"to_s":100}]
        w=workbook.compile_workbook(self.base,d)
        codes={f["code"] for f in w["director_review"]["findings"]}
        self.assertIn("DIALOGUE_UNKNOWN_SPEAKER",codes)
        self.assertIn("DIALOGUE_TIME_INVALID",codes)

    def test_invalid_animation_cannot_be_called_complete(self):
        d=self.completed()
        d["shots"][0]["animation"]["mode"]="none"
        d["shots"][0]["animation"]["elements"]=[
            {"layer":"text","action":"fade","timing":"0-1s"}]
        w=workbook.compile_workbook(self.base,d)
        self.assertIn("ANIMATION_CONTRADICTION",{f["code"] for f in w["director_review"]["findings"]})

    def test_markdown_contains_every_director_department(self):
        txt=workbook.render_markdown(workbook.compile_workbook(self.base,self.completed()))
        for label in ("台词、配音与字幕","动作、走位与逐秒表演","镜头","场景、灯光与美术",
                      "剪辑与转场","动画与视觉特效","音乐与环境音效","AI 制作提示词与后期工单"):
            self.assertIn(label,txt)

    def test_cli_strict_refuses_unfinished_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=root/"workbook.json"
            cmd=[sys.executable,str(ROOT/"director_workbook.py"),
                 "--base",str(ROOT/"examples/quit-smoking/plan.json"),
                 "--direction",str(ROOT/"examples/quit-smoking/direction_v02.json"),
                 "--out",str(out),"--strict"]
            p=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(out.exists())

    def test_cli_draft_is_non_destructive_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/"workbook.json";md=root/"workbook.md"
            cmd=[sys.executable,str(ROOT/"director_workbook.py"),
                 "--base",str(ROOT/"examples/quit-smoking/plan.json"),
                 "--direction",str(ROOT/"examples/quit-smoking/direction_v02.json"),
                 "--out",str(out),"--markdown",str(md)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            self.assertTrue(out.exists())
            self.assertTrue(md.exists())
            old=out.read_bytes()
            second=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(old,out.read_bytes())


if __name__=="__main__":
    unittest.main()
