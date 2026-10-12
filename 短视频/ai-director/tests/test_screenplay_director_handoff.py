"""Synthetic, source-bound screenwriter -> EXISTING director pipeline tests."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team
import agent_role_contracts
import director
import screenplay_adaptation as script
import screenplay_director_handoff as handoff

FIXTURE = ROOT / "examples" / "dinner-dialogue-review"


class ScreenplayDirectorHandoffTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((FIXTURE / "plan.json").read_text("utf-8"))
        self.source = (FIXTURE / "source.md").read_text("utf-8")
        self.proposal = json.loads((FIXTURE / "adaptation_proposal.json").read_text("utf-8"))
        self.packet = script.build_review_packet(self.base, self.source, self.proposal)
        self.form = handoff.review_form(self.packet)
        self.bindings = {
            "小宁": {"character_id": "CHAR01", "identity_note": "成年女儿小宁"},
            "母亲": {"character_id": "CHAR02", "identity_note": "小宁的母亲"},
        }

    def decide(self):
        decision = deepcopy(self.form)
        decision["review_intent"] = "accept_for_director_planning"
        for entry in decision["changes"]:
            entry["choice"] = "accept"
        return decision

    def accept(self):
        return handoff.prepare_handoff(
            self.base, self.source, self.packet, self.decide(), self.bindings)

    def test_director_receives_full_screenplay_as_its_actual_original_script(self):
        compiled = self.accept()
        self.assertEqual(compiled["next_professional_role"], "director_brief")
        self.assertEqual(agent_team.ready(compiled["crew"]), ["director_brief"])
        self.assertEqual(compiled["director_source_digest"], compiled["screenplay_text_digest"])
        self.assertNotEqual(compiled["director_source_digest"],
                            compiled["original_manuscript_digest"])
        self.assertEqual(compiled["reconstructed_base"]["duration"], 44)
        self.assertEqual(compiled["reconstructed_base"]["shots"][0]["source_adaptation"]["beat_id"],
                         "B01")
        self.assertEqual(compiled["reconstructed_base"]["shots"][0]["subtitles"]["text"],
                         "我问的是你，不是工作。")
        self.assertFalse(director.validate(compiled["reconstructed_base"])[0])
        model_task = handoff.director_request(compiled)
        self.assertEqual(model_task["task_id"], "director_brief")
        self.assertIn("original_script", model_task["messages"][1]["content"])
        self.assertIn("我问的是你，不是工作。", model_task["messages"][1]["content"])
        self.assertIn("先吃饭", model_task["messages"][1]["content"])
        self.assertIn("已经完成结构改编的剧本", model_task["messages"][0]["content"])
        self.assertTrue(model_task["contains_private_material"])
        self.assertFalse(model_task["external_model_call_authorized"])
        self.assertFalse(compiled["reviewer_identity_authenticated"])
        self.assertFalse(compiled["paid_video_authorized"])

    def test_adapted_screenplay_changes_downstream_script_edit_to_continuity_only(self):
        assembled = self.accept()
        source = assembled["screenplay_fountain"]
        base = assembled["reconstructed_base"]
        self.assertEqual(base["screenplay_handoff_mode"]["kind"],
                         "adapted_screenplay_planning_only")
        director_role = agent_role_contracts.build_role_messages(
            base, assembled["crew"], "director_brief", source_text=source)
        self.assertIn("总导演与编剧分工", director_role["messages"][0]["content"])
        self.assertIn("有权判断原编剧稿存在冗余", director_role["messages"][0]["content"])
        self.assertIn("不得自己悄然替换故事", director_role["messages"][0]["content"])
        self.assertNotIn("未经核准自行重写", director_role["messages"][0]["content"])
        team = agent_team.submit(
            assembled["crew"], agent_team.packet(assembled["crew"], "director_brief"),
            {"creative_brief": {"audience": "虚构观众", "core_conflict": "母女沟通"}})
        self.assertEqual(agent_team.ready(team), ["script_edit"])
        script_role = agent_role_contracts.build_role_messages(
            base, team, "script_edit", source_text=source)
        msg = script_role["messages"][0]["content"]
        self.assertIn("本阶段转为剧本连续性审查", msg)
        self.assertIn("不再重复重写剧情", msg)
        self.assertIn("requires_user_approval=true", msg)
        self.assertFalse(script_role["external_model_call_authorized"])
        tampered = deepcopy(base)
        tampered["screenplay_handoff_mode"]["screenplay_sha256"] = "wrong"
        stale = agent_team.start(tampered, source_text=source)
        with self.assertRaisesRegex(ValueError, "CREW_SCREENPLAY_BOUNDARY_INVALID"):
            agent_role_contracts.build_role_messages(
                tampered, stale, "director_brief", source_text=source)

    def test_legacy_screenwriter_stage_unchanged_for_old_plan(self):
        ordinary_team = agent_team.start(self.base, source_text=self.source)
        msg = agent_role_contracts.build_role_messages(
            self.base, ordinary_team, "director_brief", source_text=self.source)
        self.assertNotIn("总导演与编剧分工", msg["messages"][0]["content"])

    def test_review_has_no_prechecked_approvals(self):
        self.assertIsNone(self.form["review_intent"])
        self.assertTrue(self.form["changes"])
        self.assertTrue(all(c["choice"] is None for c in self.form["changes"]))
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_NOT_ACCEPTED"):
            handoff.prepare_handoff(
                self.base, self.source, self.packet, self.form, self.bindings)

    def test_every_revision_needs_separate_review(self):
        choice = self.decide()
        choice["changes"][0]["choice"] = "reject"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_CHANGE_REJECTED"):
            handoff.prepare_handoff(
                self.base, self.source, self.packet, choice, self.bindings)
        choice = self.decide()
        choice["changes"].pop()
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_CHANGE_REVIEW_INCOMPLETE"):
            handoff.prepare_handoff(
                self.base, self.source, self.packet, choice, self.bindings)

    def test_new_or_other_source_is_rejected(self):
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_SOURCE_STALE"):
            handoff.prepare_handoff(
                self.base, self.source + "\n换了源文本",
                self.packet, self.decide(), self.bindings)

    def test_changed_base_after_review_is_rejected(self):
        changed = deepcopy(self.base)
        changed["core_message"] = "另一个故事"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_BASE_STALE"):
            handoff.prepare_handoff(
                changed, self.source, self.packet, self.decide(), self.bindings)

    def test_abridged_article_preview_cannot_masquerade_as_complete_screenplay(self):
        abridged = deepcopy(self.base)
        abridged["editorial"]["omissions"].append({
            "text": "另有重要章节未进入分镜",
            "reason": "preview length/shot limit; author and script editor must review"
        })
        packet = script.build_review_packet(abridged, self.source, self.proposal)
        form = handoff.review_form(packet)
        form["review_intent"] = "accept_for_director_planning"
        for change in form["changes"]:
            change["choice"] = "accept"
        with self.assertRaisesRegex(handoff.ScriptHandoffError,
                                    "SCRIPT_LONG_SOURCE_PREVIEW_TRUNCATED"):
            handoff.prepare_handoff(
                abridged, self.source, packet, form, self.bindings)

    def test_unreviewed_packet_mutation_fails_closed(self):
        wrong = deepcopy(self.packet)
        wrong["screenplay_fountain"] += "\n新结局"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_PACKET_TAMPERED"):
            handoff.prepare_handoff(
                self.base, self.source, wrong, self.decide(), self.bindings)
        wrong = deepcopy(self.packet)
        wrong["shot_plan_preview"]["plan"]["shots"][0]["narration"] = "伪造"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_PACKET_TAMPERED"):
            handoff.prepare_handoff(
                self.base, self.source, wrong, self.decide(), self.bindings)

    def test_stale_proposal_review_form_fails(self):
        choice = self.decide()
        choice["proposal_digest"] = "not-the-same-script"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_REVIEW_STALE"):
            handoff.prepare_handoff(
                self.base, self.source, self.packet, choice, self.bindings)

    def test_all_dialogue_speakers_must_have_explicit_identity_binding(self):
        missing = deepcopy(self.bindings)
        del missing["小宁"]
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_SPEAKER_CAST_COVERAGE"):
            handoff.prepare_handoff(
                self.base, self.source, self.packet, self.decide(), missing)
        ambiguous = deepcopy(self.bindings)
        ambiguous["小宁"]["character_id"] = "CHAR02"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_CAST_AMBIGUOUS_IDENTITY"):
            handoff.prepare_handoff(
                self.base, self.source, self.packet, self.decide(), ambiguous)

    def test_new_character_can_be_named_without_fabricating_visual_identity(self):
        altered = deepcopy(self.proposal)
        altered["scenes"][1]["beats"][2]["dialogue"][0]["speaker"] = "旁观者"
        altered["scenes"][1]["beats"][2]["dialogue"][0]["origin"] = "proposed"
        # This is a structural test for a newly proposed speaker, not an
        # assertion that such a dramatic rewrite is aesthetically good.
        packet = script.build_review_packet(self.base, self.source, altered)
        form = handoff.review_form(packet)
        form["review_intent"] = "accept_for_director_planning"
        for c in form["changes"]:
            c["choice"] = "accept"
        bindings = {
            "母亲": self.bindings["母亲"],
            "小宁": self.bindings["小宁"],
            "旁观者": {"character_id": "CHAR99", "identity_note": "新提案中的旁观者"}
        }
        finished = handoff.prepare_handoff(
            self.base, self.source, packet, form, bindings)
        assert any(c["id"] == "CHAR99" for c in finished["reconstructed_base"]["characters"])
        self.assertIn("CHAR99", finished["reconstructed_base"]["shots"][-1]["character_ids"])

    def test_spoken_dialogue_too_long_for_beat_is_not_claimed_ready(self):
        altered = deepcopy(self.proposal)
        altered["scenes"][0]["beats"][0]["dialogue"][0]["line"] = "我问的是你，不是工作。" * 30
        altered["scenes"][0]["beats"][0]["dialogue"][0]["origin"] = "proposed"
        packet = script.build_review_packet(self.base, self.source, altered)
        form = handoff.review_form(packet)
        form["review_intent"] = "accept_for_director_planning"
        for c in form["changes"]:
            c["choice"] = "accept"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_SPOKEN_RUNTIME_OVERFLOW"):
            handoff.prepare_handoff(
                self.base, self.source, packet, form, self.bindings)

    def test_tampered_director_ledger_and_base_are_not_accepted(self):
        ready = self.accept()
        forged = deepcopy(ready)
        forged["reconstructed_base"]["shots"][0]["duration"] = 900
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_DIRECTOR_PLAN_TAMPERED"):
            handoff.director_request(forged)
        forged = deepcopy(ready)
        forged["crew"]["tasks"]["director_brief"]["status"] = "completed"
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_DIRECTOR_CREW_TAMPERED"):
            handoff.director_request(forged)

    def test_inputs_unchanged_and_no_live_agents_called(self):
        original_base = deepcopy(self.base)
        original_packet = deepcopy(self.packet)
        original_form = self.decide()
        ready = handoff.prepare_handoff(
            self.base, self.source, self.packet, original_form, self.bindings)
        self.assertEqual(original_base, self.base)
        self.assertEqual(original_packet, self.packet)
        self.assertTrue(all(v["status"] == "pending"
                            for v in ready["crew"]["tasks"].values()))
        self.assertEqual(ready["crew"]["events"], [])
        self.assertFalse(ready["crew"]["budget_policy"]["llm_requests_enabled"])
        self.assertFalse(ready["crew"]["release"]["human_approved"])


if __name__ == "__main__":
    unittest.main()
