"""QO-D15: public synthetic director directs every specialist for actual shots.

A command receipt proves integrity, not that a director or specialist is talented.
No external creative provider or media is called.
"""
from __future__ import annotations

from copy import deepcopy
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team as team
import agent_role_contracts as roles
import director_department_command as command


def _ready_team(*, strict=True):
    src = "Public fiction: someone hesitates before opening a sealed letter."
    base = {
        "title": "Letter on desk",
        "shots": [
            {"id": "S01", "start": 0, "duration": 4,
             "narration": "They fear opening the letter.",
             "transition": "cut", "visual_type": "ai_video",
             "character_ids": ["CHAR01"]},
            {"id": "S02", "start": 4, "duration": 4,
             "narration": "The letter is finally opened.",
             "transition": "cut", "visual_type": "ai_video",
             "character_ids": ["CHAR01"]},
        ]}
    if strict:
        base["director_command_mode"] = {
            "kind": "director_department_conference_required",
            "command_before_specialists": True}
    state = team.start(base, source_text=src)
    brief = {"creative_brief": {
        "audience": "People awaiting an emotionally important private message",
        "core_conflict": "The character wants answers but fears opening the envelope",
        "hook_intention": "Unopened letter as a tangible decision that cannot wait",
        "target_emotion": "Unease becomes bravery as the character makes a choice",
        "ending_payoff": "The character opens the letter, accepting uncertainty",
        "visual_strategy": "Restrained observable action and no fake insert text",
        "immutable_facts": ["The envelope is closed at first"],
        "assumptions_to_verify": []}}
    state = team.submit(state, team.packet(state, "director_brief"), brief)
    script_edit = {"story_treatment": {
        "hook": "Hand hovers above an unopened envelope",
        "central_question": "Will this person choose to know the truth?",
        "beat_map": [
            {"shot_id": "S01", "dramatic_function": "Show hesitation",
             "handoff_to_next": "Hand begins to reach for the envelope"},
            {"shot_id": "S02", "dramatic_function": "Show choice",
             "handoff_to_next": "End of this short film"}],
        "source_change_proposals": []}}
    state = team.submit(state, team.packet(state, "script_edit"), script_edit)
    lock = {
        "global_direction": {
            "audience_emotion_arc": "Hesitation turns to decisive action",
            "visual_grammar": "Spare frame, no needless cutaways",
            "audio_grammar": "Room silence until the paper sound",
            "graphic_safety": "No baked-in AI text or names",
            "reference_strategy": "No real images or rights yet",
            "generation_budget": "All media requests remain disabled"},
        "shot_objectives": {
            "S01": {
                "emotion": "Worry that makes the viewer lean forward",
                "observable_turn": "The hand stops above the sealed letter",
                "visual_focus": "Hand hovering over unopened envelope"},
            "S02": {
                "emotion": "Release achieved by visible choice, not speech",
                "observable_turn": "Hand opens the seal and accepts what follows",
                "visual_focus": "Seal breaking and fingers lowering"}
        }}
    state = team.submit(state, team.packet(state, "director_lock"), lock)
    return src, base, state


def _command(base, state):
    ref = command._context(base, state)
    shops = {}
    for dept in command.DEPARTMENTS:
        work = {
            field: f"{dept}的这项职责将服务于人物面对信件的选择，而非额外制造故事。" +
                   f"本部门要特别执行{field}并同前后岗位核对。" for field in command.CONTENT_FIELDS}
        work["acceptance_checks"] = [
            f"验收第一项：检查{dept}对应的实际镜头动作是否支持人物决定。",
            f"验收第二项：检查{dept}与接收部门的时间码与状态是否相容。",
        ]
        work["per_shot"] = {}
        for i, sid in enumerate(state["shot_ids"]):
            work["per_shot"][sid] = {
                "dramatic_beat": f"{sid}发生第{i+1}次可见叙事变化，观众需要看到明确的决定。",
                "desired_viewer_effect": f"观众在{sid}的第{i+1}段先关注犹豫，然后理解选择。",
                "department_execution": f"{dept}执行镜头{sid}对应的第{i+1}项真实动作，与该镜头基准锁定的动作对齐。",
                "sync_with_other_departments": f"{dept}在镜头{sid}第{i+1}段与其他专业确认声音和行为转折的同一时刻。",
                "observable_acceptance": f"回看镜头{sid}：这一段必须看得见姿态变化，听得见正确的时间关系。",
            }
        shops[dept] = work
    return {
        "version": command.VERSION, "provenance": ref,
        "episode_intent": {
            "specific_audience_journey": "观众从害怕未知的状态，逐步见证角色亲自承担决定的后果。",
            "dramatic_or_conceptual_axis": "人物是否有勇气面对信件中的可能变化，先犹豫再付诸行动。",
            "style_and_visual_motif": "信封始终是具象的叙事锚点，用手的状态而非花哨运镜说明选择。",
            "sound_and_silence_logic": "人物停顿时不铺满音乐，让打开信封的真实声成为明确转折。",
            "final_aftertaste": "结尾不是完美答案，而是角色愿意面对不可预见结果的平静。",
            "things_not_to_do": "禁止未经授权增加信的真实内容、额外人物和不属于原剧本的旁白。",
        },
        "departments": shops,
        "interfaces": [
            {
                "from": src, "to": dst,
                "shared_artifact_or_state": f"从{src}交接到{dst}的手部位置、情绪变化与前后镜头动作。",
                "timing_and_handoff": f"{src}完成当前镜头真实状态说明后，{dst}才能按同一时间码实施。",
                "conflict_owner": "若演员动作和摄影/剪辑节奏冲突，反馈总导演决定并记录返工点。",
            } for src, dst in command.EDGES],
        "review_gaps": ["信纸内容在原稿未给出，不能由任何部门凭空补充具体文字。"]
    }


class DirectorDepartmentCommandTests(unittest.TestCase):
    def setUp(self):
        self.source, self.base, self.state = _ready_team()
        self.bible = _command(self.base, self.state)

    def test_director_confers_after_lock_and_each_department_has_real_shot_work(self):
        request = command.command_request(
            self.base, self.state, source_text=self.source)
        self.assertFalse(request["dispatch_allowed"])
        data = json.loads(request["messages"][1]["content"])
        self.assertEqual(data["locked_shot_objectives"],
                         self.state["tasks"]["director_lock"]["deliverable"]["shot_objectives"])
        proof = command.validate_command(self.base, self.state, self.bible)
        self.assertEqual(proof["department_count"], len(command.DEPARTMENTS))
        self.assertEqual(proof["interfaces_count"], len(command.EDGES))
        self.assertFalse(proof["director_artistic_quality_verified"])

    def test_actual_model_facing_role_message_receives_director_specific_work(self):
        for dept in ("acting", "camera_art", "sound"):
            self.assertIn(dept, team.ready(self.state))
            with self.assertRaisesRegex(ValueError, "COMMAND_REQUIRED"):
                roles.build_role_messages(self.base, self.state, dept,
                                          source_text=self.source)
            result = roles.build_role_messages(
                self.base, self.state, dept, source_text=self.source,
                department_command=self.bible)
            self.assertIn("部门任务书", result["messages"][0]["content"])
            expected = '"director_department_command":'
            self.assertIn(expected, result["messages"][1]["content"])
            payload = json.loads(result["messages"][1]["content"].split(
                "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n", 1)[1])
            task = payload["director_department_command"]
            self.assertEqual(task["this_department"], dept)
            self.assertEqual(task["director_mission_and_execution"],
                             self.bible["departments"][dept])
            self.assertTrue(task["cross_department_handoffs"])
            self.assertEqual(task["episode_intent"],
                             self.bible["episode_intent"])
            self.assertFalse(result["external_model_call_authorized"])

    def test_generic_copy_paste_for_distinct_shots_rejected(self):
        altered = deepcopy(self.bible)
        altered["departments"]["acting"]["per_shot"]["S02"] = deepcopy(
            altered["departments"]["acting"]["per_shot"]["S01"])
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "REPEATED_GENERIC_SHOT"):
            command.validate_command(self.base, self.state, altered)

    def test_absent_department_or_shot_and_incomplete_qa_constraints_rejected(self):
        bad = deepcopy(self.bible)
        del bad["departments"]["sound"]
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "DEPARTMENT_MISSING"):
            command.validate_command(self.base, self.state, bad)
        bad = deepcopy(self.bible)
        del bad["departments"]["ai_technical"]["per_shot"]["S02"]
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "SHOT_COVERAGE"):
            command.validate_command(self.base, self.state, bad)
        bad = deepcopy(self.bible)
        bad["departments"]["quality_review"]["acceptance_checks"] = ["测试"]
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "ACCEPTANCE_UNSPECIFIED"):
            command.validate_command(self.base, self.state, bad)

    def test_no_hidden_version_change_of_director_lock_or_script(self):
        wrong = deepcopy(self.bible)
        wrong["provenance"]["director_lock_digest"] = "old"
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "STALE_CREATIVE_VERSION"):
            command.validate_command(self.base, self.state, wrong)
        changed = deepcopy(self.state)
        changed["tasks"]["director_lock"]["deliverable"]["global_direction"][
            "audio_grammar"] = "Different creative vision after conference"
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "STALE_CREATIVE_VERSION"):
            command.validate_command(self.base, changed, self.bible)
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "WRONG_SOURCE_SCRIPT"):
            command.command_request(self.base, self.state, source_text="not the source")

    def test_no_cross_department_connection_may_disappear(self):
        wrong = deepcopy(self.bible)
        wrong["interfaces"].pop()
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "CROSS_DEPARTMENT_COUNT"):
            command.validate_command(self.base, self.state, wrong)
        wrong = deepcopy(self.bible)
        wrong["interfaces"][0]["from"] = "unknown department"
        with self.assertRaisesRegex(command.DirectorCommandError,
                                    "CROSS_DEPARTMENT_INVALID"):
            command.validate_command(self.base, self.state, wrong)

    def test_legacy_team_remains_compatible_without_command_mode(self):
        src, base, state = _ready_team(strict=False)
        result = roles.build_role_messages(base, state, "acting",
                                           source_text=src)
        self.assertNotIn('"director_department_command":',
                         result["messages"][1]["content"])
        with self.assertRaisesRegex(ValueError, "WRONG_STAGE"):
            roles.build_role_messages(base, state, "director_brief",
                                      source_text=src,
                                      department_command=self.bible)


if __name__ == "__main__":
    unittest.main()
