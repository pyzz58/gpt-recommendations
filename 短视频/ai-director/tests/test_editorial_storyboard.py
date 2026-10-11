"""Offline editorial showrunner/script-editor creative bridge regression.

All stories, director concepts, voices and JSON responses are synthetic.
NO real user script, model API, real spending, video media or private logs.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import article_intake as intake
import agent_team as team
import agent_role_contracts as roles
import agent_model_gateway as gateway
import editorial_storyboard as creative
import director


SYNTHETIC = """# 纸灯实验
### 1. 桌上的信
- 说人话：门口传来敲门声。小林走到桌前，看到一封没有署名的信。她的手停在信封上方。最后她选择打开信。
- 来源：https://example.invalid/fiction

### 2. 雨伞
- 说人话：门外下雨了。小林拿起雨伞。
"""


class EditorialStoryboardTests(unittest.TestCase):
    def setUp(self):
        self.intake = intake.prepare_episode(SYNTHETIC, "EP01")
        self.source = intake.episode_source_for_team(SYNTHETIC, "EP01")
        self.base = self.intake["plan"]
        self.state = self.intake["team"]
        self.options = {
            "profiles": {
                "synthetic": {"provider": "synthetic_only", "model": "no-live-model",
                              "max_input_tokens": 220000,
                              "max_output_tokens": 4096,
                              "input_cny_per_m": "5",
                              "output_cny_per_m": "20"}},
            "routing": {"*": "synthetic"}, "cap_cny": "20",
            "max_attempts": 3}
        self.book = gateway.OfflineBudgetBook(gateway.configure_profiles(**self.options))
        self.brief = {"creative_brief": {
            "audience": "喜欢细微悬念和情绪观察的读者",
            "core_conflict": "未知来信带来的好奇与迟疑",
            "hook_intention": "敲门声之后突然静下来",
            "target_emotion": "从安静到惊讶，再进入期待",
            "ending_payoff": "最后一秒展示打开信的行为",
            "visual_strategy": "信封是视觉主体，镜头逐步逼近人的指尖",
            "immutable_facts": ["信没有署名", "她最终打开信"],
            "assumptions_to_verify": []}}
        self.treatment = {"story_treatment": {
            "hook": "敲门响起，镜头却对着无人走廊",
            "central_question": "无署名信里究竟有什么",
            "beat_map": [{
                "shot_id": s["id"],
                "dramatic_function": "第%s幕：把视线导向信封" % (i+1),
                "handoff_to_next": "让下一个镜头回答未完成动作"
            } for i,s in enumerate(self.base["shots"])],
            "source_change_proposals": [],
            "storyboard_pitch": {
                "creative_angle": "把一次拆信变成极简悬念的视觉过程",
                "hook_strategy": "第一个画面以门口敲击声吸引注意，不提早解释",
                "audience_question": "她会不会打开没有署名的信",
                "ending_payoff": "用手指撕开封口作为明确的动作回报",
                "shot_designs": [
                    {
                        "shot_id": s["id"],
                        "visual_type": "ai_video" if i in (0, 1) else "text_card",
                        "visual_intention": "具体镜头%02d：手在纸面上停顿而后逐渐靠近" % i,
                        "observable_action": {
                            "start": "手掌张开停在桌面上",
                            "action": "拇指缓慢划过桌上的信封边缘",
                            "micro_action": "食指微微蜷起",
                            "reaction": "身体稍向前倾",
                            "end": "手指回到信封封口",
                        },
                        "camera_intention": "缓缓向桌面推进并稳定聚焦",
                        "light_intention": "早晨窗边散射光，纸面微暖",
                        "transition_intention": "沿手掌行进方向与下一镜衔接",
                        "post_overlay": "",
                        "evidence_quote": s["narration"],
                        "reason": "借可见动作把紧张感呈现给观众",
                    } for i,s in enumerate(self.base["shots"])
                ],
                "open_risks": ["人物形象和实拍条件还未确认",
                               "导演方案尚未经过专业摄影和动作部门"]
            }}}

    def _run(self, *, treatment=None, brief=None):
        transport = gateway.OfflineMockTransport({
            "director_brief": {"1": json.dumps(brief or self.brief, ensure_ascii=False)},
            "script_edit": {"1": json.dumps(treatment or self.treatment, ensure_ascii=False)},
        })
        state, _ = gateway.simulate_one(
            self.base, self.state, self.book, transport,
            source_text=self.source)
        state, _ = gateway.simulate_one(
            self.base, state, self.book, transport, source_text=self.source)
        return state

    def test_ten_stage_team_has_real_first_two_artifacts_without_live_calls(self):
        state = self._run()
        self.assertEqual(state["tasks"]["director_brief"]["status"], "completed")
        self.assertEqual(state["tasks"]["script_edit"]["status"], "completed")
        self.assertEqual(team.ready(state), ["director_lock"])
        self.assertEqual(self.book.safe_summary()["actual_provider_calls"], 0)
        self.assertEqual(self.book.safe_summary()["actual_billed_cny"], "0")
        self.assertTrue(creative.validate_editorial_pitch(self.intake, state, self.source))

    def test_offline_creative_model_prompt_contains_exact_schema(self):
        first = creative.build_director_brief_request(self.intake, self.source)
        self.assertIn("长文章改编专项", first["messages"][0]["content"])
        self.assertFalse(first["external_model_call_authorized"])
        state, _ = gateway.simulate_one(
            self.base, self.state, self.book,
            gateway.OfflineMockTransport({
                "director_brief": {"1": json.dumps(self.brief, ensure_ascii=False)}}),
            source_text=self.source)
        packet = creative.build_script_editor_request(self.intake, state, self.source)
        self.assertEqual(packet["creative_extension"], creative.VERSION)
        self.assertIn("分镜提案专项", packet["messages"][0]["content"])
        self.assertFalse(packet["external_model_call_authorized"])
        schema = packet["output_json_schema"]["properties"]["story_treatment"]
        self.assertIn("storyboard_pitch", schema["required"])
        self.assertIn("storyboard_pitch", packet["messages"][1]["content"])
        self.assertEqual(
            schema["properties"]["storyboard_pitch"]["properties"]
                  ["shot_designs"]["maxItems"], len(self.base["shots"]))

    def test_more_specific_candidate_replaces_placeholders_but_preserves_narration(self):
        state = self._run()
        original = deepcopy(self.base)
        candidate = creative.propose_directed_storyboard(self.intake, state, self.source)
        self.assertEqual(candidate["status"], "author_review_required")
        self.assertFalse(candidate["author_approved"])
        self.assertFalse(candidate["paid_model_authorized"])
        self.assertEqual(candidate["actual_provider_calls"], 0)
        self.assertNotEqual(candidate["candidate_base_digest"], team.fingerprint(self.base))
        revised = candidate["candidate_plan"]
        self.assertEqual([x["narration"] for x in revised["shots"]],
                         [x["narration"] for x in original["shots"]])
        self.assertEqual([x["duration"] for x in revised["shots"]],
                         [x["duration"] for x in original["shots"]])
        self.assertEqual([x["claim_ids"] for x in revised["shots"]],
                         [x["claim_ids"] for x in original["shots"]])
        self.assertEqual(revised["shots"][0]["visual_type"], "ai_video")
        self.assertIn("指尖", revised["visual_bible"]["style"])
        self.assertNotEqual(revised["editorial"]["hook"], original["editorial"]["hook"])
        errors, _ = director.validate(revised)
        self.assertEqual(errors, [])
        self.assertEqual(self.base, original)
        self.assertEqual(self.intake["team"], self.state)

    def test_stage_candidate_requires_clean_digest_and_starts_fresh_team(self):
        state = self._run()
        candidate = creative.propose_directed_storyboard(self.intake, state, self.source)
        staged = creative.stage_new_team(candidate, self.source)
        self.assertEqual(staged["stage_status"], "pending_author_editorial_review")
        self.assertEqual(staged["ready_tasks"], ["director_brief"])
        self.assertTrue(all(t["revision"] == 0
                            for t in staged["team"]["tasks"].values()))
        self.assertFalse(staged["human_approved"])
        self.assertNotEqual(staged["team"]["base_digest"], state["base_digest"])
        with self.assertRaisesRegex(ValueError, "base plan digest mismatch"):
            roles.build_role_messages(candidate["candidate_plan"], state,
                                      "director_lock", source_text=self.source)

    def test_manipulated_candidate_provenance_rejected(self):
        state = self._run()
        candidate = creative.propose_directed_storyboard(self.intake, state, self.source)
        candidate["candidate_plan"]["shots"][0]["narration"] = "一个伪造的新内容"
        with self.assertRaisesRegex(creative.CreativeContractError, "CANDIDATE_TAMPERED"):
            creative.stage_new_team(candidate, self.source)

    def test_fake_human_approval_rejected_as_invalid_candidate(self):
        state = self._run()
        candidate = creative.propose_directed_storyboard(self.intake, state, self.source)
        candidate["author_approved"] = True
        with self.assertRaisesRegex(creative.CreativeContractError, "INVALID_CANDIDATE"):
            creative.stage_new_team(candidate, self.source)

    def test_unsourced_overlay_number_is_blocked_for_high_stakes_too(self):
        treatment = deepcopy(self.treatment)
        treatment["story_treatment"]["storyboard_pitch"]["shot_designs"][0]["post_overlay"] = "研究证实97.2%"
        state = self._run(treatment=treatment)
        with self.assertRaisesRegex(creative.CreativeContractError, "UNSOURCED_OVERLAY_NUMBER"):
            creative.validate_editorial_pitch(self.intake, state, self.source)

    def test_exact_source_quote_required_not_paraphrase(self):
        treatment = deepcopy(self.treatment)
        treatment["story_treatment"]["storyboard_pitch"]["shot_designs"][0]["evidence_quote"] = "凭空改写的原稿"
        state = self._run(treatment=treatment)
        with self.assertRaisesRegex(creative.CreativeContractError, "SOURCE_QUOTE_DRIFT"):
            creative.propose_directed_storyboard(self.intake, state, self.source)

    def test_missing_or_duplicate_shot_design_fails_closed(self):
        bad = deepcopy(self.treatment)
        bad["story_treatment"]["storyboard_pitch"]["shot_designs"] = bad[
            "story_treatment"]["storyboard_pitch"]["shot_designs"][:-1]
        state = self._run(treatment=bad)
        with self.assertRaisesRegex(creative.CreativeContractError, "SHOT_COVERAGE_OR_ORDER"):
            creative.validate_editorial_pitch(self.intake, state, self.source)

    def test_repeated_visual_intentions_rejected(self):
        bad = deepcopy(self.treatment)
        designs = bad["story_treatment"]["storyboard_pitch"]["shot_designs"]
        designs[1]["visual_intention"] = designs[0]["visual_intention"]
        state = self._run(treatment=bad)
        with self.assertRaisesRegex(creative.CreativeContractError, "DUPLICATED_VISUAL_INTENT"):
            creative.validate_editorial_pitch(self.intake, state, self.source)

    def test_script_edit_unapproved_change_remains_unapplied(self):
        t = deepcopy(self.treatment)
        t["story_treatment"]["source_change_proposals"].append({
            "reason": "开头悬念需要更紧",
            "proposed_change": "建议把开始换成疑问句，不改原始来源数字",
            "requires_user_approval": True, "approved": False})
        state = self._run(treatment=t)
        candidate = creative.propose_directed_storyboard(self.intake, state, self.source)
        self.assertEqual(candidate["unapproved_source_edit_proposals"][0]["approved"], False)
        self.assertEqual(candidate["candidate_plan"]["editorial"]["narration_script"],
                         self.base["editorial"]["narration_script"])

    def test_script_edit_self_approved_change_rejected_by_original_role_contract(self):
        t = deepcopy(self.treatment)
        t["story_treatment"]["source_change_proposals"].append({
            "reason": "为了戏剧性虚构",
            "proposed_change": "马上能根治",
            "requires_user_approval": True, "approved": True})
        with self.assertRaisesRegex(ValueError, "CREW_SOURCE_CHANGE_MUST_REMAIN_UNAPPROVED"):
            self._run(treatment=t)

    def test_wrong_episode_source_refused_before_model_execution(self):
        with self.assertRaisesRegex(creative.CreativeContractError, "SOURCE_DIGEST_MISMATCH"):
            creative.build_director_brief_request(self.intake, SYNTHETIC)

    def test_no_completed_team_roles_does_not_produce_fake_creative_candidate(self):
        with self.assertRaisesRegex(creative.CreativeContractError, "FIRST_TWO_ROLES_INCOMPLETE"):
            creative.validate_editorial_pitch(self.intake, self.state, self.source)

    def test_preexisting_role_only_without_storyboard_pitch_cannot_pretend_usable(self):
        plain = deepcopy(self.treatment)
        del plain["story_treatment"]["storyboard_pitch"]
        state = self._run(treatment=plain)
        with self.assertRaisesRegex(creative.CreativeContractError, "PITCH_CONTRACT_MISSING"):
            creative.propose_directed_storyboard(self.intake, state, self.source)

    def test_staged_storyboard_does_not_claim_footage_or_release(self):
        state = self._run()
        proposal = creative.propose_directed_storyboard(self.intake, state, self.source)
        self.assertIn("MISSING_PROFESSIONAL_CAMERA_ACTING_AUDIO_EDITING_HANDOFFS", proposal["warnings"])
        new = creative.stage_new_team(proposal, self.source)
        self.assertFalse(new["team"]["release"]["human_approved"])
        self.assertFalse(new["team"]["release"]["paid_api_authorized"])
        self.assertFalse(new["team"]["release"]["media_generated"])


if __name__ == "__main__":
    unittest.main()
