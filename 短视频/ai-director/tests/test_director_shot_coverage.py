"""QO-D02 source-bound creative shot coverage: no paid media, public synthetic film."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_team
import director
import director_shot_coverage as coverage
import screenplay_series_delivery as series
from test_screenplay_series_delivery import long_story, dossier, series_plan, assemble_original


def shot(i, spans):
    return {
        "shot_id": f"S{i:02d}", "source_spans": spans,
        "dramatic_purpose": "本镜头将人物犹豫转化为观众看得出来的公共选择争议。",
        "observable_screen_event": "角色在桥梁地图前停下，并将目光从数字移向等候的人。",
        "viewer_before": f"镜头{i}开始时观众把桥梁理解为计算速度的工程问题。",
        "viewer_after": f"镜头{i}结束时观众意识到工程选择涉及人真实的去向。",
        "why_this_coverage": "在同一场景中，局部镜头交替让观看者看到人物注意力的变换。",
        "performance_blocking": "人物从图纸边移到桌旁，明确手部与道具空间的前后位置。",
        "framing_and_space": "保留地图和对方站位的连续空间轴线，不为炫技频繁运镜。",
        "sound_and_silence": "采用房间真实环境声，并在实际观念变化时保留短暂停顿。",
        "cut_hold_intention": "看到人物目光开始转向人群时剪切，而非按固定三秒切镜。",
        "ai_fallback": "若AI视频无法保持道具连续性，可使用静态镜头与剪辑音效交接。",
    }


def span(bid, a, b):
    return {"beat_id": bid, "from_s": a, "to_s": b}


def proposal(h, ds, plan, rows):
    proof = series.validate_breakdown(h, ds, plan)
    return {
        "version": coverage.VERSION,
        "source_screenplay_digest": proof["screenplay_digest"],
        "writer_dossier_digest": proof["writer_dossier_digest"],
        "director_breakdown_digest": proof["director_breakdown_digest"],
        "episode_id": "EP01",
        "director_coverage_thesis": "真正把编剧节拍转成画面因果，采用停顿、空间和反应控制观众认识。",
        "shots": rows,
    }


class DirectorShotCoverageTests(unittest.TestCase):
    def setUp(self):
        self.h = long_story()
        self.ds = dossier(self.h)
        self.plan = series_plan(self.h, self.ds, [2]*10)
        self.packet = series.build_per_episode_crew(self.h, self.ds, self.plan)
        self.merged = proposal(self.h, self.ds, self.plan, [
            shot(1, [span("B001", 0, 30), span("B002", 0, 30)])])
        self.split = proposal(self.h, self.ds, self.plan, [
            shot(1, [span("B001", 0, 10)]),
            shot(2, [span("B001", 10, 20)]),
            shot(3, [span("B001", 20, 30), span("B002", 0, 30)])])

    def test_real_director_can_merge_two_beat_placeholders_into_one_shot(self):
        receipt = coverage.validate(self.h, self.ds, self.plan, self.merged)
        self.assertEqual(receipt["original_script_beat_count"], 2)
        self.assertEqual(receipt["director_shot_count"], 1)
        self.assertEqual(receipt["runtime_s"], 60)
        result = coverage.reblock_episode(self.h, self.ds, self.plan,
                                          self.packet, self.merged)
        ep = result["episodes"][0]
        self.assertEqual(len(ep["authoritative_episode_base"]["shots"]), 1)
        self.assertEqual(ep["authoritative_episode_base"]["shots"][0]["duration"], 60)
        self.assertEqual(
            ep["authoritative_episode_base"]["shots"][0]
            ["source_adaptation"]["covered_beat_ids"], ["B001", "B002"])
        self.assertEqual(agent_team.ready(ep["crew"]), ["director_brief"])
        self.assertFalse(director.validate(ep["authoritative_episode_base"])[0])
        self.assertFalse(result["director_coverage_applied"]["human_approved"])

    def test_real_director_can_split_silent_beat_without_dropping_any_piece(self):
        receipt = coverage.validate(self.h, self.ds, self.plan, self.split)
        self.assertEqual(receipt["director_shot_count"], 3)
        self.assertEqual(receipt["split_beats"], ["B001"])
        revised = coverage.reblock_episode(self.h, self.ds, self.plan,
                                            self.packet, self.split)
        ep = revised["episodes"][0]
        base = ep["authoritative_episode_base"]
        self.assertEqual([s["start"] for s in base["shots"]], [0, 10, 20])
        self.assertEqual([s["duration"] for s in base["shots"]], [10, 10, 40])
        self.assertEqual(base["duration"], 60)
        self.assertTrue(base["director_shot_coverage_mode"])
        self.assertEqual(len(ep["crew"]["shot_ids"]), 3)
        self.assertFalse(director.validate(base)[0])

    def test_actual_director_model_receives_detailed_coverage_and_not_metadata_only(self):
        packet = coverage.reblock_episode(self.h, self.ds, self.plan,
                                           self.packet, self.split)
        req = series.episode_director_request(
            self.h, self.ds, self.plan, packet, "EP01",
            director_coverage=self.split)
        self.assertFalse(req["external_model_call_authorized"])
        data = json.loads(req["messages"][1]["content"].split(
            "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n", 1)[1])
        self.assertEqual(
            len(data["director_creative_shot_coverage"]["shots"]), 3)
        self.assertEqual(
            len(data["authoritative_base"]["shots"]), 3)
        self.assertIn("导演自由镜头覆盖", req["messages"][0]["content"])

    def test_cannot_omit_duplicate_reverse_or_overlap_beat_times(self):
        bad = deepcopy(self.split)
        bad["shots"][1]["source_spans"][0]["from_s"] = 11
        with self.assertRaisesRegex(coverage.ShotCoverageError, "GAP_OVERLAP"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.split)
        bad["shots"][2]["source_spans"][1]["beat_id"] = "B001"
        with self.assertRaises(coverage.ShotCoverageError):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.split)
        bad["shots"].pop()
        with self.assertRaisesRegex(coverage.ShotCoverageError, "NOT_FULLY_COVERED|MISSING_BEAT"):
            coverage.validate(self.h, self.ds, self.plan, bad)

    def test_no_fictitious_separate_scene_inside_one_physical_shot(self):
        h = long_story()
        new_scene = deepcopy(h["screenplay_scenes"][0])
        new_scene["id"] = "SC02"
        new_scene["beats"] = [new_scene["beats"].pop(1)]
        h["screenplay_scenes"].append(new_scene)
        h["reconstructed_base"]["scenes"].append({
            "id": "LOC02", "description": "新的虚构夜间场景"})
        h["reconstructed_base"]["shots"][1]["scene_id"] = "LOC02"
        h["director_base_digest"] = agent_team.fingerprint(h["reconstructed_base"])
        new_dossier = dossier(h)
        plan = series_plan(h, new_dossier, [2]*10)
        bad = proposal(h, new_dossier, plan, [
            shot(1, [span("B001", 0, 30), span("B002", 0, 30)])])
        with self.assertRaises(coverage.ShotCoverageError):
            coverage.validate(h, new_dossier, plan, bad)

    def test_stale_or_forged_packet_rejected(self):
        bad = deepcopy(self.split)
        bad["director_breakdown_digest"] = "new"
        with self.assertRaisesRegex(coverage.ShotCoverageError, "STALE_SCRIPT"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        packet = deepcopy(self.packet)
        packet["episodes"][0]["authoritative_episode_base"]["title"] = "tampered"
        with self.assertRaisesRegex(coverage.ShotCoverageError, "PACKET_TAMPERED"):
            coverage.reblock_episode(self.h, self.ds, self.plan, packet,
                                     self.split)

    def test_director_cannot_split_unmapped_dialogue_or_voiceover(self):
        h = assemble_original()
        ds = dossier(h)
        beat_ids = [b["id"] for s in h["screenplay_scenes"] for b in s["beats"]]
        # Use exact one episode when <=90s, not override the original dialogue.
        plan = series_plan(h, ds, [len(beat_ids)])
        first = h["screenplay_scenes"][0]["beats"][0]
        self.assertTrue(first["dialogue"] or first["voiceover"] or
                        h["reconstructed_base"]["shots"][0]["subtitles"]["text"])
        d = first["duration_s"]
        rows = [
            shot(1, [span(first["id"], 0, d/2)]),
            shot(2, [span(first["id"], d/2, d)]),
        ]
        for i, beat in enumerate(
                [b for s in h["screenplay_scenes"] for b in s["beats"]][1:], 3):
            rows.append(shot(i, [span(beat["id"], 0, beat["duration_s"])]))
        bad = proposal(h, ds, plan, rows)
        with self.assertRaisesRegex(coverage.ShotCoverageError,
                                    "CANNOT_SPLIT_UNTIMED_SPEECH"):
            coverage.validate(h, ds, plan, bad)

    def test_unpaid_director_request_reads_full_script_and_dossier(self):
        req = coverage.request(self.h, self.ds, self.plan, "EP01")
        self.assertFalse(req["dispatch_allowed"])
        payload = json.loads(req["messages"][1]["content"])
        self.assertEqual(payload["complete_screenplay"], self.h["screenplay_fountain"])
        self.assertEqual(payload["approved_script_beats"][0]["beat_id"], "B001")


if __name__ == "__main__":
    unittest.main()
