"""QO-D09 director montage: safe multi-shot / multi-scene plan, no paid media."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_team
import director
import director_editorial_montage as montage
import director_shot_coverage as coverage
import screenplay_series_delivery as series
from test_director_shot_coverage import proposal, shot, span
from test_screenplay_series_delivery import assemble_original, dossier, series_plan


def seam(h, out_beat, in_beat, out_shot, in_shot, out_scene, in_scene,
         relation="unstated", evidence="", edit="hard_cut"):
    original = {s["source_adaptation"]["beat_id"]: s
                for s in h["reconstructed_base"]["shots"]}
    def state(beat, before):
        c = original[beat]["continuity_state"]
        part = "before" if before else "after"
        return {"props": c["props_" + part], "actors": c["actors_" + part]}
    return {
        "out_shot_id": out_shot, "in_shot_id": in_shot,
        "out_scene_id": out_scene, "in_scene_id": in_scene,
        "edit_type": edit, "time_relation": relation,
        "source_time_evidence": evidence,
        "orientation_before": "观众此前看见母亲与女儿在桌边相处，明确掌握上一段的信息。",
        "orientation_after": "接镜的场景和人物焦点可辨，观众不应被虚假连续动作误导。",
        "axis_light_bridge": "明确镜头切口前后人物朝向和光线变化，而非默认同灯同轴。",
        "performer_prop_bridge": "对照来源剧本的手机与演员状态，不可凭空创造物品位置变化。",
        "sound_intention": "让原始对白仅出现一次，换场时声场与环境底噪区别需交由声音岗。",
        "viewer_before": "观众还不了解下一段镜头在何时何地发生。",
        "viewer_after": "观众知道发生了明确的叙事段落切换，而非同一镜头瞬移。",
        "editorial_reason": "只有切换能表现人物认识变化时才采用这组连续剪辑。",
        "ai_fallback": "画面连续性无法得到保障时，改用各场静帧和明确的剪辑连接。",
        "exit_state_digest": agent_team.fingerprint(state(out_beat, False)),
        "entry_state_digest": agent_team.fingerprint(state(in_beat, True)),
    }


def plan_fixture():
    h = assemble_original()
    ds = dossier(h)
    beats = [b for sc in h["screenplay_scenes"] for b in sc["beats"]]
    breakdown = series_plan(h, ds, [len(beats)])
    packet = series.build_per_episode_crew(h, ds, breakdown)
    rows = [shot(i, [span(b["id"], 0, b["duration_s"])])
            for i, b in enumerate(beats, 1)]
    cov = proposal(h, ds, breakdown, rows)
    proof = series.validate_breakdown(h, ds, breakdown)
    cov["montage_plan"] = {
        "version": montage.VERSION,
        "episode_id": "EP01",
        "source_screenplay_digest": proof["screenplay_digest"],
        "director_breakdown_digest": proof["director_breakdown_digest"],
        "coverage_digest": agent_team.fingerprint(cov),
        "sequences": [
            {
                "sequence_id": "M01", "montage_kind": "time_shift",
                "shot_ids": ["S01", "S02"],
                "director_intention": "用先给情感问题再回到之前日常的倒叙，重排观众理解但不重写剧本。",
                "audience_orientation": "利用餐桌与人物姿态先建立现在时刻，接着清楚指出画面回到几秒前。",
                "rejected_alternative": "若顺序播放会失去先提出情感冲突再澄清误解的效果，但更稳定。",
                "ai_fallback": "如果AI镜头难以维持餐厅状态，用明确回切字幕和声效提示代替复杂运动。",
                "seams": [
                    seam(h, "B01", "B02", "S01", "S02",
                         "SC01", "SC01", "earlier", "时间回到几秒前", "sound_bridge"),
                ],
            },
            {
                "sequence_id": "M02", "montage_kind": "cross_scene",
                "shot_ids": ["S03", "S04"],
                "director_intention": "以两个独立场次的相邻事件组织一组剪辑，而不是伪装为一镜穿越时空。",
                "audience_orientation": "结束第一场母女互动后明确切入下一场，留给观众辨识场次变化的提示。",
                "rejected_alternative": "直接长镜头无法自然跨越两个编剧物理场次，容易出现人物与道具瞬移。",
                "ai_fallback": "若跨场动态不稳则分别生成两段，并利用后期硬切和环境声进行组接。",
                "seams": [
                    seam(h, "B03", "B04", "S03", "S04",
                         "SC01", "SC02"),
                ],
            },
        ],
    }
    return h, ds, breakdown, packet, cov


class DirectorEditorialMontageTests(unittest.TestCase):
    def setUp(self):
        self.h, self.ds, self.plan, self.packet, self.cov = plan_fixture()

    def test_real_multiscene_and_time_shift_are_independent_editorial_shots(self):
        receipt = coverage.validate(self.h, self.ds, self.plan, self.cov)
        self.assertEqual(receipt["montage_receipt"]["montage_count"], 2)
        self.assertEqual(receipt["montage_receipt"]["cut_count"], 2)
        rebuilt = coverage.reblock_episode(
            self.h, self.ds, self.plan, self.packet, self.cov)
        ep = rebuilt["episodes"][0]
        base = ep["authoritative_episode_base"]
        self.assertEqual(len(base["shots"]), 6)
        self.assertEqual(base["duration"], sum(
            b["duration_s"] for sc in self.h["screenplay_scenes"]
            for b in sc["beats"]))
        self.assertFalse(director.validate(base)[0])
        self.assertEqual(agent_team.ready(ep["crew"]), ["director_brief"])
        self.assertEqual(base["shots"][2]["montage_membership"]["sequence_id"], "M02")
        self.assertEqual(base["shots"][3]["montage_membership"]["position"], 1)
        self.assertFalse(base["director_editorial_montage"]
                         ["actual_montage_cut_verified"])
        self.assertTrue(rebuilt["director_coverage_applied"]
                        ["editorial_montage_attached"])

    def test_old_renderers_must_not_silently_drop_montage_edits(self):
        import director_v2
        import production_delivery
        rebuilt = coverage.reblock_episode(
            self.h, self.ds, self.plan, self.packet, self.cov)
        base = rebuilt["episodes"][0]["authoritative_episode_base"]
        with self.assertRaisesRegex(ValueError, "EDITORIAL_MONTAGE_RENDERER_REQUIRED"):
            director.compile_prompts(base)
        with self.assertRaisesRegex(ValueError, "EDITORIAL_MONTAGE_PREVIEW_REQUIRED"):
            director.render_preview(base, "/tmp/no-montage-preview.html")
        with self.assertRaisesRegex(ValueError, "EDITORIAL_MONTAGE_RENDERER_REQUIRED"):
            director_v2.compile_package(base, {})
        with self.assertRaisesRegex(
                production_delivery.ProductionDeliveryError,
                "DELIVERY_EDITORIAL_MONTAGE_RENDERER_NOT_IMPLEMENTED"):
            production_delivery._make_bundle(base, {}, provenance={})

    def test_same_showrunner_prompt_receives_montage_not_just_metadata(self):
        packet = coverage.reblock_episode(
            self.h, self.ds, self.plan, self.packet, self.cov)
        req = series.episode_director_request(
            self.h, self.ds, self.plan, packet, "EP01",
            director_coverage=self.cov)
        self.assertFalse(req["external_model_call_authorized"])
        sep = "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n"
        obj = json.loads(req["messages"][1]["content"].split(sep, 1)[1])
        self.assertEqual(obj["director_creative_shot_coverage"]
                         ["montage_plan"], self.cov["montage_plan"])
        self.assertEqual(obj["director_editorial_montage_production_notes"]
                         ["plan"], self.cov["montage_plan"])
        self.assertIn("蒙太奇导演工单", req["messages"][0]["content"])

    def test_temporal_guess_or_forged_source_is_blocked(self):
        bad = deepcopy(self.cov)
        seam0 = bad["montage_plan"]["sequences"][0]["seams"][0]
        seam0["source_time_evidence"] = "几年以后她们来到另一座城市"
        with self.assertRaisesRegex(montage.MontageError, "TIME_EVIDENCE"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.cov)
        seam0 = bad["montage_plan"]["sequences"][0]["seams"][0]
        seam0["time_relation"] = "unstated"
        with self.assertRaisesRegex(montage.MontageError, "UNSUPPORTED_TIME_EVIDENCE"):
            coverage.validate(self.h, self.ds, self.plan, bad)

    def test_no_merging_cross_scene_into_single_physical_camera_shot(self):
        bad = deepcopy(self.cov)
        bad["shots"] = [
            shot(1, [span("B01", 0, 5)]),
            shot(2, [span("B02", 0, 6)]),
            shot(3, [span("B03", 0, 10), span("B04", 0, 6)]),
            shot(4, [span("B05", 0, 9)]),
            shot(5, [span("B06", 0, 8)]),
        ]
        with self.assertRaisesRegex(coverage.ShotCoverageError, "MULTIPLE_SCENES"):
            coverage.validate(self.h, self.ds, self.plan, bad)

    def test_missing_seam_reordered_shots_and_fake_scene_blocked(self):
        bad = deepcopy(self.cov)
        bad["montage_plan"]["sequences"][1]["seams"] = []
        with self.assertRaisesRegex(montage.MontageError, "SEAMS"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.cov)
        bad["montage_plan"]["sequences"][1]["shot_ids"] = ["S04", "S03"]
        with self.assertRaisesRegex(montage.MontageError, "NONADJACENT"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.cov)
        bad["montage_plan"]["sequences"][1]["seams"][0]["in_scene_id"] = "SC99"
        with self.assertRaisesRegex(montage.MontageError, "PROVENANCE_CHANGED"):
            coverage.validate(self.h, self.ds, self.plan, bad)

    def test_tampering_reviewed_state_or_coverage_provenance_blocks(self):
        bad = deepcopy(self.cov)
        bad["montage_plan"]["sequences"][0]["seams"][0]["exit_state_digest"] = "spoof"
        with self.assertRaisesRegex(montage.MontageError, "STATE_TAMPERED"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.cov)
        bad["montage_plan"]["coverage_digest"] = "stale"
        with self.assertRaisesRegex(montage.MontageError, "STALE"):
            coverage.validate(self.h, self.ds, self.plan, bad)

    def test_unknown_time_does_not_claim_simultaneous_action(self):
        bad = deepcopy(self.cov)
        x = bad["montage_plan"]["sequences"][1]["seams"][0]
        x["time_relation"] = "parallel"
        x["source_time_evidence"] = ""
        with self.assertRaisesRegex(montage.MontageError, "NEEDS_SOURCE"):
            coverage.validate(self.h, self.ds, self.plan, bad)
        bad = deepcopy(self.cov)
        x = bad["montage_plan"]["sequences"][1]["seams"][0]
        x["time_relation"] = "continuous"
        with self.assertRaisesRegex(montage.MontageError, "CONTINUOUS_ACROSS_SCENE"):
            coverage.validate(self.h, self.ds, self.plan, bad)


if __name__ == "__main__":
    unittest.main()
