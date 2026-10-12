"""QO-D14 public-only: director chooses justified 240s three-part cut of a 600s script."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import director_creative_cut as creative
from test_screenplay_series_delivery import long_story, dossier


def option(handoff, details, *, condense=True):
    original = [beat for scene in handoff["screenplay_scenes"]
                for beat in scene["beats"]]
    decisions = []
    for i, beat in enumerate(original):
        if condense:
            op = "omit" if i in (4, 9, 14, 19) else "condense"
            seconds = 0 if op == "omit" else 15
        else:
            op, seconds = "retain", 30
        decisions.append({
            "beat_id": beat["id"], "operation": op,
            "new_duration_s": seconds,
            "why": "本节拍和相邻事件的叙事功能重复，可以只保留新信息的可见转折。",
            "viewer_gain": "观众将更快看到选择的具体代价，不再被重复解释打断。",
            "viewer_loss": "省略的细节也许会减少环境感和人物沉默时的复杂情绪。",
            "meaning_impact": "preserves_meaning",
            "writer_revision_required": op != "retain",
        })
    ids = [r["beat_id"] for r in decisions if r["operation"] != "omit"]
    groups = [5, 5, 6] if condense else [2] * 10
    assert sum(groups) == len(ids)
    episodes = []
    pos = 0
    for i, n in enumerate(groups, 1):
        episodes.append({
            "episode_id": f"EP{i:02d}",
            "beat_ids": ids[pos:pos+n],
            "episode_promise": "观众将看到修桥讨论从技术细节走向人物和公共目的的冲突。",
            "episode_turn_and_payoff": "人物在可见行动中形成一次新的判断，而不是得到虚假悬念。",
            "why_break_here": "此处有具体认识转折，下一集可以据此自然提出新问题。",
            "continuity_to_next": "地图、人物身份、道具与上集结束状态保持逻辑连续。",
            "intro_s": 0, "recap_s": 0, "bridge_s": 0,
            "outro_s": 0, "evidence_s": 0,
        })
        pos += n
    return {
        "version": creative.VERSION,
        "source_digest": handoff["screenplay_text_digest"],
        "dossier_digest": __import__("agent_team").fingerprint(details),
        "directorial_thesis": "让观众具体感受到，桥梁的目的不是效率数字而是人应如何相处。",
        "overall_audience_arc": "最初追逐建设速度，随后面对对岸的用途，最终认识到公共选择的代价。",
        "why_this_cut_is_better": (
            "短版保留认知与情绪转折，删掉重复会议陈述，让行动和反应代替朗读。"
            if condense else
            "长版保留每个讨论的细节、人物的等待和社会环境，更重视慢节奏。"),
        "lost_value_and_counterargument": (
            "缩短对人物复杂关系的铺陈是艺术代价；若代价太大应保留较长版本。"
            if condense else
            "细节更完整但许多讨论重复，短视频观众可能提早失去看下去的动力。"),
        "decisions": decisions, "episodes": episodes,
    }


class DirectorCreativeCutTests(unittest.TestCase):
    def setUp(self):
        self.handoff = long_story()
        self.writer = dossier(self.handoff)
        self.short = option(self.handoff, self.writer)
        self.long = option(self.handoff, self.writer, condense=False)

    def test_unpaid_professional_first_read_requests_two_alternatives(self):
        req = creative.creative_analysis_request(self.handoff, self.writer)
        self.assertFalse(req["dispatch_allowed"])
        data = json.loads(req["messages"][1]["content"])
        self.assertIn("at least two", data["alternatives"])
        self.assertEqual(len(data["all_source_beats"]), 20)
        self.assertEqual(data["complete_screenplay"],
                         self.handoff["screenplay_fountain"])

    def test_director_can_propose_ten_minutes_in_three_80ish_episodes(self):
        result = creative.validate_cut(self.handoff, self.writer, self.short)
        self.assertEqual(result["source_seconds"], 600)
        self.assertEqual(result["proposed_story_seconds"], 240)
        self.assertEqual(result["removed_seconds"], 360)
        self.assertEqual(result["proposed_episode_count"], 3)
        self.assertEqual([e["total_seconds"] for e in result["episode_budgets"]],
                         [75, 75, 90])
        self.assertEqual(len(result["omitted_source_beat_ids"]), 4)
        self.assertEqual(len(result["shortened_source_beat_ids"]), 16)
        self.assertFalse(result["all_source_beats_forced_into_movie"])
        self.assertFalse(result["approved_new_screenplay_available"])
        self.assertEqual(result["next_stage"],
                         "writer_script_revision_then_independent_author_review")

    def test_longer_ten_episode_cut_also_legitimate_option(self):
        result = creative.validate_cut(self.handoff, self.writer, self.long)
        self.assertEqual(result["proposed_story_seconds"], 600)
        self.assertEqual(result["proposed_episode_count"], 10)
        self.assertFalse(result["script_revision_required"])
        self.assertEqual(result["next_stage"],
                         "director_series_breakdown_with_original_authoritative_script")

    def test_exact_beats_get_disposition_but_can_be_omitted(self):
        bad = deepcopy(self.short)
        bad["decisions"].pop()
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "EVERY_BEAT_NEEDS_EDITORIAL_DECISION"):
            creative.validate_cut(self.handoff, self.writer, bad)
        bad = deepcopy(self.short)
        bad["decisions"][0]["why"] = ""
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "BEAT_REASON_INSUFFICIENT"):
            creative.validate_cut(self.handoff, self.writer, bad)
        bad = deepcopy(self.short)
        bad["decisions"][0]["beat_id"] = "B999"
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "NOT_IN_SCRIPT_ORDER"):
            creative.validate_cut(self.handoff, self.writer, bad)

    def test_runtime_and_copy_paste_episode_does_not_hide_overflow(self):
        bad = deepcopy(self.short)
        bad["episodes"][2]["recap_s"] = 1
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "LONGER_THAN_90S"):
            creative.validate_cut(self.handoff, self.writer, bad)
        bad = deepcopy(self.short)
        bad["episodes"][0]["beat_ids"] += ["B006"]
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "MISSING_OR_REORDERED"):
            creative.validate_cut(self.handoff, self.writer, bad)

    def test_no_fake_source_card_on_uncited_manuscript(self):
        bad = deepcopy(self.short)
        bad["episodes"][0]["evidence_s"] = 1.8
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "UNSUPPORTED_EVIDENCE_CARD"):
            creative.validate_cut(self.handoff, self.writer, bad)

    def test_unapproved_script_change_cannot_avoid_writer_review(self):
        bad = deepcopy(self.short)
        bad["decisions"][0]["writer_revision_required"] = False
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "CONDENSE_REQUIRES_SCRIPT_REVISION"):
            creative.validate_cut(self.handoff, self.writer, bad)
        bad = deepcopy(self.short)
        bad["decisions"][4]["writer_revision_required"] = False
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "OMISSION_REQUIRES_SCRIPT_REVISION"):
            creative.validate_cut(self.handoff, self.writer, bad)

    def test_director_cannot_fake_new_meaning_as_verified(self):
        marked = deepcopy(self.short)
        marked["decisions"][4]["meaning_impact"] = "meaning_changed"
        check = creative.validate_cut(self.handoff, self.writer, marked)
        self.assertIn("B005", check["meaning_risk_beat_ids"])
        self.assertFalse(check["approved_new_screenplay_available"])
        req = creative.writer_revision_request(self.handoff, self.writer, marked)
        self.assertFalse(req["dispatch_allowed"])
        payload = json.loads(req["messages"][1]["content"])
        self.assertEqual(payload["unchanged_original_screenplay"],
                         self.handoff["screenplay_fountain"])
        self.assertTrue(payload["new_version_must_get_independent_review"])

    def test_unchanged_director_cut_does_not_need_writer_revision(self):
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "NO_SCRIPT_REVISION_REQUIRED"):
            creative.writer_revision_request(self.handoff, self.writer, self.long)

    def test_director_must_compare_both_short_and_long_for_artistic_reasons(self):
        import agent_team
        a = creative.validate_cut(self.handoff, self.writer, self.short)
        b = creative.validate_cut(self.handoff, self.writer, self.long)
        compare = {
            "version": creative.VERSION,
            "source_digest": self.handoff["screenplay_text_digest"],
            "candidate_digests": [a["director_cut_digest"], b["director_cut_digest"]],
            "selected_cut_digest": a["director_cut_digest"],
            "selection_reason": "三集短版让角色实际选择成为核心动作，去掉冗余解释比完整朗读更有意义。",
            "alternative_strengths": "十集长版会保留对人物复杂处境的沉默与铺陈，仍可能更感人。",
            "weaknesses_of_selected": "三集短版会失去部分背景，独立导演审片必须核查动机是否清楚。",
            "unresolved_core_idea_risk": "删除讨论是否让桥梁服务对象从开放问题变成已定结论仍需专业审稿。",
            "independent_craft_review_still_needed": True,
        }
        validated = creative.validate_cut_comparison(
            self.handoff, self.writer, [self.short, self.long], compare)
        self.assertTrue(validated["shorter_does_not_automatically_win"])
        self.assertFalse(validated["author_approved"])
        compare["selected_cut_digest"] = b["director_cut_digest"]
        validated = creative.validate_cut_comparison(
            self.handoff, self.writer, [self.short, self.long], compare)
        self.assertEqual(validated["selected_story_seconds"], 600)
        self.assertFalse(validated["script_revision_required"])

    def test_comparison_does_not_accept_duplicate_cuts(self):
        a = creative.validate_cut(self.handoff, self.writer, self.short)
        comparison = {
            "version": creative.VERSION,
            "source_digest": self.handoff["screenplay_text_digest"],
            "candidate_digests": [a["director_cut_digest"]] * 2,
            "selected_cut_digest": a["director_cut_digest"],
            "selection_reason": "三集短版让角色实际选择成为核心动作，去掉冗余解释比完整朗读更有意义。",
            "alternative_strengths": "十集长版会保留对人物复杂处境的沉默与铺陈，仍可能更感人。",
            "weaknesses_of_selected": "三集短版会失去部分背景，独立导演审片必须核查动机是否清楚。",
            "unresolved_core_idea_risk": "删除讨论是否让桥梁服务对象从开放问题变成已定结论仍需专业审稿。",
            "independent_craft_review_still_needed": True,
        }
        with self.assertRaisesRegex(creative.DirectorCutError,
                                    "DUPLICATE_ALTERNATIVES"):
            creative.validate_cut_comparison(self.handoff, self.writer,
                                             [self.short, self.short], comparison)

    def test_stale_dossier_or_script_is_rejected(self):
        bad = deepcopy(self.short)
        bad["source_digest"] = "not original"
        with self.assertRaisesRegex(creative.DirectorCutError, "STALE_SOURCE"):
            creative.validate_cut(self.handoff, self.writer, bad)
        bad = deepcopy(self.short)
        bad["dossier_digest"] = "different writer notes"
        with self.assertRaisesRegex(creative.DirectorCutError, "STALE_SOURCE"):
            creative.validate_cut(self.handoff, self.writer, bad)


if __name__ == "__main__":
    unittest.main()
