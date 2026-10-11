"""Synthetic offline tests: creative evidence is advisory, not approval."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_creative_review as qa


class CreativeReviewTests(unittest.TestCase):
    def test_empty_or_generic_department_sections_flagged(self):
        payload = {"shots": {"S01": {
            "camera": {"note": "电影感"},
            "art": {"light": "专业"}}}}
        issues = qa.review_deliverable("camera_art", payload, ["S01"])
        self.assertEqual(sum(i["code"] == "CREATIVE_EMPTY_SECTION" for i in issues), 2)

    def test_specific_camera_evidence_reduces_warnings(self):
        payload = {"shots": {"S01": {
            "camera": {"movement": "三秒内从中景推至演员右手拿起信封的特写"},
            "art": {"lighting": "左侧窗光映出信封封口，背景压暗两档"}}}}
        self.assertEqual(qa.review_deliverable("camera_art", payload, ["S01"]), [])

    def test_scoped_revision_missing_shot_is_detected(self):
        issue = qa.review_deliverable("camera_art", {"shots": {}}, ["S09"])
        self.assertEqual(issue[0]["code"], "CREATIVE_SHOT_MISSING")
        self.assertEqual(issue[0]["severity"], "blocker")

    def test_action_needs_visible_change(self):
        payload = {"shots": {"S01": {
            "staging": {"detail": "演员站在桌边，手放在信封右侧"},
            "performance": {"detail": "眼睛落向纸面，随后短暂看向门口"},
            "beats": [{"remark": "动作未交接"}],
            "continuity": {"detail": "道具信封从桌子右侧转移到手中"},
            "shootability": None}}}
        names = {v["code"] for v in qa.review_deliverable("acting", payload)}
        self.assertIn("ACTING_NO_VISIBLE_CHANGE", names)
        self.assertIn("SHOOTABILITY_UNDESIGNED", names)

    def test_sound_distinguishes_speech_plan(self):
        payload = {"shots": {"S01": {
            "sound": {"sfx": "信封摩擦声在第2.3秒开始持续半秒"},
            "speech": {"idea": "声音应该活泼且有感染力"}}}}
        names = {v["code"] for v in qa.review_deliverable("sound", payload)}
        self.assertIn("SOUND_NO_SPEECH_PLAN", names)

    def test_edit_bridge_and_generation_route(self):
        edit = {"shots": {"S01": {
            "editing": {"cut": "信封落在桌面的瞬间硬切下一镜"},
            "animation": {"mode": "none; this is live-action only"},
            "graphics": {"mode": "none; no graphics needed here"}}}}
        self.assertIn("EDIT_NO_NARRATIVE_BRIDGE",
                      [x["code"] for x in qa.review_deliverable("editing_animation", edit)])
        gen = {"shots": {"S01": {"generation": {"prompt": "close-up slow push to letter"}}}}
        self.assertIn("GEN_NO_ROUTE",
                      [x["code"] for x in qa.review_deliverable("ai_technical", gen)])

    def test_non_human_graphic_shot_does_not_require_shootability(self):
        payload = {"shots": {"S02": {
            "staging": {"blocking": "矢量图标位于画面的左上三分区，保留字幕区"},
            "performance": {"timing": "金额进入画面后，日历逐格推进两次"},
            "beats": [{"visible_change": "第一格日历亮起，随后出现第二格"}],
            "continuity": {"state": "烟盒图标在所有帧内保持位置不变"},
            "shootability": None}}}
        source = {"S02": {"id": "S02", "visual_type": "data_graphic",
                          "character_ids": []}}
        result = qa.review_deliverable("acting", payload, ["S02"],
                                       shot_context=source)
        self.assertNotIn("SHOOTABILITY_UNDESIGNED",
                         [x["code"] for x in result])

    def test_human_ai_video_still_requires_shootability(self):
        payload = {"shots": {"S01": {
            "staging": {"blocking": "演员右手伸向桌上的信封"},
            "performance": {"timing": "先停顿，再抬起信封检查署名"},
            "beats": [{"visible_change": "演员握住信封并拿起"}],
            "continuity": {"state": "信封从桌面移动至演员右手"},
            "shootability": None}}}
        source = {"S01": {"id": "S01", "visual_type": "ai_video",
                          "character_ids": ["CHAR01"]}}
        result = qa.review_deliverable("acting", payload, ["S01"],
                                       shot_context=source)
        self.assertIn("SHOOTABILITY_UNDESIGNED",
                      [x["code"] for x in result])

    def test_final_shot_needs_no_outgoing_narrative_bridge(self):
        payload = {"shots": {"S03": {
            "editing": {"cut_reason": "影片最后一镜以黑场停顿结束"},
            "animation": {"style": "不需要额外图层，保持原生镜头画面"},
            "graphics": {"plan": "画面中央没有额外字幕或图形"}}}
        result = qa.review_deliverable(
            "editing_animation", payload, ["S03"], terminal_shot_id="S03")
        self.assertNotIn("EDIT_NO_NARRATIVE_BRIDGE",
                         [x["code"] for x in result])

    def test_preterminal_shot_still_needs_bridge(self):
        payload = {"shots": {"S02": {
            "editing": {"cut_reason": "下一镜将显示打开后的信封内容"},
            "animation": {"style": "不加入与故事无关的动效元素"},
            "graphics": {"plan": "不加入任何额外图形或统计"}}}
        result = qa.review_deliverable(
            "editing_animation", payload, ["S02"], terminal_shot_id="S03")
        self.assertIn("EDIT_NO_NARRATIVE_BRIDGE",
                      [x["code"] for x in result])

    def test_incomplete_team_cannot_be_reported_as_ready(self):
        state = {"shot_ids": ["S01"], "tasks": {}}
        original = copy.deepcopy(state)
        report = qa.review_team(state)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["human_approved"])
        self.assertFalse(report["paid_api_authorized"])
        self.assertEqual(state, original)

    def test_non_specialist_review_requires_human(self):
        result = qa.review_packet({}, "director_final")
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(result["checks"], [])


if __name__ == "__main__":
    unittest.main()
