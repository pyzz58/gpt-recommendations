"""Director D03/D16 audiovisual craft and versioned feedback, public letter story."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as team
import agent_role_contracts as roles
import director_department_command as command
import director_visual_language as visual
import director_delivery_review as review
from test_director_department_command import _ready_team, _command


def _visual(base, state, meeting):
    proof = command.validate_command(base, state, meeting)
    shots = [
        {
            "shot_id": "S01",
            "incoming_viewer_belief": "观众以为角色只是准备完成一次普通的拿取动作。",
            "observable_screen_event": "角色右手接近封口，却在接触纸面之前短暂停住，没有打开信。",
            "viewer_belief_after": "观众理解封口不是物理障碍，角色内心的恐惧才是阻力。",
            "visual_emphasis_and_reason": "让未打开的封口与悬停的手同时可见，突出选择尚未发生。",
            "mise_en_scene_and_performance": "手掌只微微收紧，视线落向封口，不用夸张地颤抖或尖叫。",
            "framing_movement_or_stillness": "保持安静的中近景不移动，允许观众亲眼发现犹豫的时长。",
            "sound_or_silence_contribution": "压低其他声音，只保留真实衣袖轻响，不用音乐命令观众紧张。",
            "cut_or_hold_causal_reason": "手没有碰到封口之前不能切走，犹豫本身是人物可见的决定。",
            "counterfactual_if_generic_coverage": "若换普通紧张背景素材或频繁推镜，观众看不到明确的恐惧行为。",
            "ai_fallback_without_story_loss": "AI无法生成自然手指时，可用已有静帧叠加轻微动作与后期声音。",
        },
        {
            "shot_id": "S02",
            "incoming_viewer_belief": "观众已看懂角色害怕打开信，但尚不知道他是否愿意承担答案。",
            "observable_screen_event": "同一只手抓住封口，慢慢撕开纸面，之后才把手放下。",
            "viewer_belief_after": "观众看到人物不再只是在害怕，而是选择承担不可知的后果。",
            "visual_emphasis_and_reason": "让完整的封口破裂行为清楚发生，选择比信纸内部文字更重要。",
            "mise_en_scene_and_performance": "动作从僵硬过渡到稳定，眼神先跟随破开的纸，然后停下来。",
            "framing_movement_or_stillness": "保持前镜相同的方位和距离，只让封口的状态变化成为焦点。",
            "sound_or_silence_contribution": "纸张撕开的清脆声音成为情绪释放，不引入响亮的胜利音乐。",
            "cut_or_hold_causal_reason": "封口破裂后留出短暂停顿，给观众确认这一决定带来的状态变化。",
            "counterfactual_if_generic_coverage": "若只剪信纸特写且过早给出文字答案，角色承担未知的意义会丢失。",
            "ai_fallback_without_story_loss": "生成无法维持纸张形变时，用两张连续手部关键帧与后期拟音完成。",
        },
    ]
    return {
        "version": visual.VERSION,
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_lock_digest": proof["director_lock_digest"],
        "director_command_digest": proof["command_digest"],
        "genre": "fiction",
        "point_of_view": "片子选择站在不敢确定未来的角色旁边，让观众跟随一次具体行动。",
        "emotional_question": "人物能否用一个几乎微不足道的动作面对自己不敢知道的答案？",
        "visual_motif_evolution": "完整封口从不可碰触的威胁变成被人主动打开的现实，意义发生变化。",
        "sound_silence_arc": "开场降低人声与音乐，打开封口的短促纸声承担整个情绪转折。",
        "rhythm_and_attention_strategy": "不机械每三秒剪一镜：先延迟揭示，再通过动作完成转折并留余韵。",
        "shots": shots,
        "handoffs": [{
            "from_shot": "S01", "to_shot": "S02",
            "audience_question": "观众已经看到犹豫，下一步最想知道是否真的会打开信。",
            "information_or_emotion_change": "前镜停在恐惧，后镜用真实拆信行为回答是否承担代价。",
            "image_sound_link": "保留手和封口的画面轴线，纸张轻响跨过切点使动作可连贯。",
            "why_this_boundary": "只有停顿完成且手重新向前移动时剪，才能让行为和理解同时改变。",
        }],
    }


def _acting_completed(base, state):
    beats = {}
    for sid in state["shot_ids"]:
        beats[sid] = {
            "staging": {"action": "The character faces the sealed envelope"},
            "performance": {"motivation": "Fear of what the message may contain"},
            "beats": [{"visible_change": "The hand reaches or withdraws"}],
            "continuity": {"prop": "Same paper envelope on desk"},
            "shootability": None,
        }
    return team.submit(state, team.packet(state, "acting"), {"shots": beats})


def _review(base, state, meeting, plan, *, one_revision=False):
    req = review.request(base, state, meeting, plan)
    provenance = json.loads(req["messages"][1]["content"])["versioned_source"]
    findings = []
    for dept in review.TARGETS:
        finished = state["tasks"][dept]["status"] == "completed"
        for sid in state["shot_ids"]:
            change = one_revision and finished and dept == "acting" and sid == "S01"
            findings.append({
                "department": dept, "shot_id": sid,
                "verdict": ("revision_needed" if change else
                            "evidence_supports_intent" if finished else
                            "cannot_evaluate"),
                "evidence_level": "submitted_design" if finished else "not_submitted",
                "delivery_quote": "The character faces the sealed envelope" if finished else "",
                "intended_viewer_effect": f"镜头{sid}需要在具体手部动作中让观众经历意义变化。",
                "observed_delivery_evidence": (
                    f"{dept}实际提交了相关镜头的已规划动作，但还没有真实影片证据。"
                    if finished else
                    f"{dept}在当前锁定版本还未提交可供导演观看的具体专业设计。"),
                "specific_viewer_consequence": (
                    "演员如果没有停顿，观众无法理解角色是在惧怕而非普通拿信。"
                    if change else
                    "只凭文字设计无法保证观众真正看见这一次选择和情绪的变化。"),
                "rewrite_instruction": (
                    "修改该镜头手部动作先停在封口前，再逐渐伸出，保留可见的迟疑。"
                    if change else ""),
                "professional_collaborators": (
                    ["camera_art", "editing_animation"] if change else []),
                "how_to_verify_next": "检查同一版本镜头是否保留停顿与拆封之间的连续动作关系。",
            })
    needs = any(x["verdict"] == "revision_needed" for x in findings)
    pending = any(x["verdict"] == "cannot_evaluate" for x in findings)
    return {
        "version": review.VERSION, "snapshot": provenance,
        "director_judgment": "导演认为原有设计能够形成明确选择，但必须检查手部动作是否传达人物的犹豫。",
        "findings": findings, "conflicts": [],
        "next_step": ("revise_specifications" if needs else
                      "continue_department_work" if pending else
                      "ready_for_real_media_and_human_review"),
    }


class DirectorAudiovisualReviewTests(unittest.TestCase):
    def setUp(self):
        self.source, self.base, self.state = _ready_team()
        self.command = _command(self.base, self.state)
        self.language = _visual(self.base, self.state, self.command)

    def test_full_director_audiovisual_thesis_and_boundary(self):
        prompt = visual.request(self.base, self.state, self.command,
                                genre="fiction", source_text=self.source)
        self.assertFalse(prompt["dispatch_allowed"])
        self.assertIn("沉默", prompt["messages"][0]["content"])
        out = visual.validate(self.base, self.state, self.command, self.language)
        self.assertEqual(out["shot_count"], 2)
        self.assertEqual(out["boundary_count"], 1)
        self.assertFalse(out["artistic_effect_verified"])

    def test_real_model_facing_specialist_receives_camera_sound_rhythm_reasoning(self):
        result = roles.build_role_messages(
            self.base, self.state, "acting", source_text=self.source,
            department_command=self.command, audiovisual_plan=self.language)
        payload = json.loads(result["messages"][1]["content"].split(
            "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n", 1)[1])
        data = payload["director_audiovisual_intention"]
        self.assertEqual(data["department"], "acting")
        self.assertIn("封口", data["detailed_shots"][0]["observable_screen_event"])
        self.assertIn("纸张轻响", data["cross_shot_audiovisual_handoffs"][0]["image_sound_link"])
        with self.assertRaisesRegex(ValueError, "DIRECTOR_DEPARTMENT_COMMAND_REQUIRED"):
            roles.build_role_messages(
                self.base, self.state, "acting", source_text=self.source,
                audiovisual_plan=self.language)

    def test_new_episode_requires_audiovisual_plan_for_actual_professional_work(self):
        new_base = deepcopy(self.base)
        new_base["director_command_mode"] = {
            "kind": "director_department_conference_required",
            "command_before_specialists": True}
        new_base["director_audiovisual_mode"] = {
            "kind": "director_audiovisual_plan_required",
            "audiovisual_intent_before_specialists": True}
        newer = team.start(new_base, source_text=self.source)
        for task_id in ("director_brief", "script_edit", "director_lock"):
            previous_output = deepcopy(self.state["tasks"][task_id]["deliverable"])
            newer = team.submit(newer, team.packet(newer, task_id), previous_output)
        meeting = _command(new_base, newer)
        visual_plan = _visual(new_base, newer, meeting)
        with self.assertRaisesRegex(ValueError, "DIRECTOR_AUDIOVISUAL_PLAN_REQUIRED"):
            roles.build_role_messages(
                new_base, newer, "acting", source_text=self.source,
                department_command=meeting)
        actual = roles.build_role_messages(
            new_base, newer, "acting", source_text=self.source,
            department_command=meeting, audiovisual_plan=visual_plan)
        self.assertIn("director_audiovisual_intention",
                      actual["messages"][1]["content"])
        with self.assertRaisesRegex(ValueError, "DIRECTOR_AUDIOVISUAL_PLAN_REQUIRED"):
            roles.validate_role_output(new_base, newer, "acting", '{"shots":{}}',
                                       source_text=self.source,
                                       department_command=meeting)
        with self.assertRaises(ValueError) as ex:
            roles.validate_role_output(new_base, newer, "acting", '{"shots":{}}',
                                       source_text=self.source,
                                       department_command=meeting,
                                       audiovisual_plan=visual_plan)
        self.assertNotIn("DIRECTOR_AUDIOVISUAL_PLAN_REQUIRED", str(ex.exception))

    def test_false_visual_progress_and_generic_repetition_rejected(self):
        bad = deepcopy(self.language)
        bad["shots"][0]["viewer_belief_after"] = bad["shots"][0]["incoming_viewer_belief"]
        with self.assertRaisesRegex(visual.VisualLanguageError, "NO_VIEWER_CHANGE"):
            visual.validate(self.base, self.state, self.command, bad)
        bad = deepcopy(self.language)
        for k in ("observable_screen_event", "visual_emphasis_and_reason",
                  "cut_or_hold_causal_reason"):
            bad["shots"][1][k] = bad["shots"][0][k]
        with self.assertRaisesRegex(visual.VisualLanguageError, "GENERIC_REPEATED_SHOTS"):
            visual.validate(self.base, self.state, self.command, bad)
        bad = deepcopy(self.language)
        bad["handoffs"][0]["to_shot"] = "S99"
        with self.assertRaisesRegex(visual.VisualLanguageError, "BRIDGE_ORDER"):
            visual.validate(self.base, self.state, self.command, bad)
        bad = deepcopy(self.language)
        bad["director_command_digest"] = "forged"
        with self.assertRaisesRegex(visual.VisualLanguageError, "STALE_DIRECTOR"):
            visual.validate(self.base, self.state, self.command, bad)

    def test_review_missing_department_can_never_pretend_media_success(self):
        req = review.request(self.base, self.state, self.command, self.language)
        self.assertFalse(req["dispatch_allowed"])
        data = json.loads(req["messages"][1]["content"])
        self.assertEqual(
            data["actual_department_deliveries"]["acting"]["status"], "pending")
        row = _review(self.base, self.state, self.command, self.language)
        result = review.validate(self.base, self.state, self.command,
                                 self.language, row)
        self.assertEqual(len(result["still_missing_deliveries"]),
                         len(review.TARGETS)*2)
        self.assertFalse(result["real_media_seen"])
        bad = deepcopy(row)
        bad["findings"][0]["verdict"] = "evidence_supports_intent"
        with self.assertRaisesRegex(review.DirectorReviewError, "CANNOT_PASS_MISSING"):
            review.validate(self.base, self.state, self.command, self.language, bad)

    def test_claimed_department_evidence_must_quote_real_submitted_work(self):
        delivered = _acting_completed(self.base, self.state)
        assessed = _review(self.base, delivered, self.command, self.language)
        tampered = deepcopy(assessed)
        tampered["findings"][0]["delivery_quote"] = "this quote never appeared in any specialist deliverable"
        with self.assertRaisesRegex(review.DirectorReviewError, "QUOTE_NOT_IN_ACTUAL_DELIVERY"):
            review.validate(self.base, delivered, self.command, self.language, tampered)
        pending = _review(self.base, self.state, self.command, self.language)
        pending["findings"][0]["delivery_quote"] = "fabricated"
        with self.assertRaisesRegex(review.DirectorReviewError, "FAKE_MISSING_DELIVERY_QUOTE"):
            review.validate(self.base, self.state, self.command, self.language, pending)

    def test_scoped_director_rework_only_after_a_real_delivery(self):
        completed = _acting_completed(self.base, self.state)
        notes = _review(self.base, completed, self.command, self.language,
                        one_revision=True)
        result = review.validate(self.base, completed, self.command,
                                 self.language, notes)
        self.assertEqual(result["requested_revisions"],
                         [{"department": "acting", "shot_id": "S01"}])
        change = review.targeted_rework(
            self.base, completed, self.command, self.language, notes,
            department="acting", shot_id="S01")
        self.assertEqual(change["updated_team"]["tasks"]["acting"]["status"],
                         "needs_revision")
        self.assertEqual(change["updated_team"]["tasks"]["acting"]["revision_scope"],
                         ["S01"])
        self.assertTrue(change["remaining_reviews_are_stale"])
        with self.assertRaisesRegex(review.DirectorReviewError, "REWORK_NOT_RECOMMENDED"):
            review.targeted_rework(
                self.base, completed, self.command, self.language, notes,
                department="acting", shot_id="S02")
        with self.assertRaisesRegex(review.DirectorReviewError, "STALE_DEPARTMENT_WORK"):
            review.validate(self.base, change["updated_team"], self.command,
                            self.language, notes)

    def test_review_requires_real_output_and_precise_guidance_not_generic_praise(self):
        completed = _acting_completed(self.base, self.state)
        notes = _review(self.base, completed, self.command, self.language)
        bad = deepcopy(notes)
        bad["findings"][0]["observed_delivery_evidence"] = "非常好"
        with self.assertRaisesRegex(review.DirectorReviewError, "NO_SPECIFIC_REASON"):
            review.validate(self.base, completed, self.command,
                            self.language, bad)
        bad = deepcopy(notes)
        bad["findings"].pop()
        with self.assertRaisesRegex(review.DirectorReviewError, "EVERY_SPECIALIST_SHOT"):
            review.validate(self.base, completed, self.command,
                            self.language, bad)
        bad = deepcopy(notes)
        bad["next_step"] = "ready_for_real_media_and_human_review"
        with self.assertRaisesRegex(review.DirectorReviewError, "FALSE_READINESS"):
            review.validate(self.base, completed, self.command,
                            self.language, bad)


    def test_audit_quote_must_belong_to_that_specific_shot(self):
        original = _acting_completed(self.base, self.state)
        candidate = deepcopy(original["tasks"]["acting"]["deliverable"])
        candidate["shots"]["S02"]["staging"]["action"] = (
            "Second scene actor opens the envelope while facing the window.")
        delivered = team.submit(
            self.state, team.packet(self.state, "acting"), candidate)
        notes = _review(self.base, delivered, self.command, self.language)
        for line in notes["findings"]:
            if line["department"] == "acting" and line["shot_id"] == "S02":
                line["delivery_quote"] = (
                    "Second scene actor opens the envelope while facing the window.")
        self.assertEqual(
            review.validate(self.base, delivered, self.command,
                            self.language, notes)["next_step"],
            "continue_department_work")
        fake = deepcopy(notes)
        for line in fake["findings"]:
            if line["department"] == "acting" and line["shot_id"] == "S02":
                line["delivery_quote"] = "The character faces the sealed envelope"
        with self.assertRaisesRegex(review.DirectorReviewError,
                                    "QUOTE_NOT_IN_ACTUAL_DELIVERY"):
            review.validate(self.base, delivered, self.command,
                            self.language, fake)

    def test_real_actor_camera_conflict_blocks_even_if_other_work_pending(self):
        acting = _acting_completed(self.base, self.state)
        camera_payload = {"shots": {sid: {
            "camera": {"composition": (
                "Camera tight crop hides the character's reaching right hand")},
            "art": {"light_source": (
                "Single table lamp shows only the envelope and top of desk")},
        } for sid in acting["shot_ids"]}}
        delivered = team.submit(
            acting, team.packet(acting, "camera_art"), camera_payload)
        notes = _review(self.base, delivered, self.command, self.language)
        for line in notes["findings"]:
            if line["department"] == "camera_art":
                line["delivery_quote"] = (
                    "Camera tight crop hides the character's reaching right hand")
        notes["conflicts"] = [{
            "shot_id": "S01",
            "left_department": "acting",
            "right_department": "camera_art",
            "left_delivery_quote": "The character faces the sealed envelope",
            "right_delivery_quote": (
                "Camera tight crop hides the character's reaching right hand"),
            "incompatible_work": (
                "Actor's critical hand hesitation must be visible, "
                "but camera framing cuts the hand from the image."),
            "director_resolution": (
                "Director must first decide whether to widen framing "
                "or adapt staging; consult acting and camera."),
            "human_decision_needed": True,
        }]
        notes["next_step"] = "resolve_cross_department_conflict"
        receipt = review.validate(
            self.base, delivered, self.command, self.language, notes)
        self.assertFalse(receipt["can_enter_real_media_review"])
        self.assertEqual(len(receipt["unresolved_cross_department_conflicts"]), 1)
        fake_ready = deepcopy(notes)
        fake_ready["next_step"] = "continue_department_work"
        with self.assertRaisesRegex(review.DirectorReviewError,
                                    "FALSE_READINESS"):
            review.validate(
                self.base, delivered, self.command, self.language, fake_ready)
        false_evidence = deepcopy(notes)
        false_evidence["conflicts"][0]["right_delivery_quote"] = (
            "An invented camera instruction never written by cinematographer.")
        with self.assertRaisesRegex(review.DirectorReviewError,
                                    "CONFLICT_NOT_GROUNDED"):
            review.validate(self.base, delivered, self.command,
                            self.language, false_evidence)
        absent_department = deepcopy(notes)
        absent_department["conflicts"][0]["right_department"] = "sound"
        with self.assertRaisesRegex(review.DirectorReviewError,
                                    "MISSING_ACTUAL_DELIVERIES"):
            review.validate(self.base, delivered, self.command,
                            self.language, absent_department)

    def test_conflicts_cannot_be_ignored_by_final_review_prompt(self):
        prompt = review.request(
            self.base, self.state, self.command, self.language)
        sent = json.loads(prompt["messages"][1]["content"])
        self.assertTrue(
            sent["unresolved_cross_department_conflicts_block_readiness"])
        self.assertIn(
            "resolve_cross_department_conflict", sent["next_step_enum"])


if __name__ == "__main__":
    unittest.main()
