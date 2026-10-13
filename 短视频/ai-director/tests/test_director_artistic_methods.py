"""QO-D17: public fictional two-shot screenplay tests professional artistic methods.

Tests only authorize *proposals* and strictly no paid model/media or approval.
Comedy uses already-authorized character hesitation, not fabricated events.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent_team as team
import agent_role_contracts as roles
import director_artistic_methods as art
import director_visual_language as visual
from test_director_department_command import _ready_team, _command
from test_director_audiovisual_delivery import _visual


def plan_for(base, state, meeting, *, comedy=False):
    proof = _command_receipt(base, state, meeting)
    thesis = {
        "story_understanding": "人物一开始不敢打开信封，最终仍然选择承担阅读答案带来的不确定性。",
        "deep_emotional_or_ideational_question":
            "真正的冲突不是纸张难以打开，而是人物是否能够诚实面对自己害怕知道的答案。",
        "directorial_position":
            "本片站在一个普通人犹豫的瞬间，不急于嘲笑恐惧，也不替人物作出决定。",
        "audience_start_and_end":
            "开始时观众以为动作轻而易举，结束时明白这个动作其实意味着某种承担。",
        "artistic_style_reason":
            "用手部和纸张的真实相对位置替代华丽光效，让观众自己认出人物的选择。",
        "visual_motif_and_evolution":
            "未拆的封口第一次像威胁，第二次成为可改变的事物，视觉形式承载人物变化。",
        "sound_silence_and_rhythm":
            "衣服摩擦与纸张撕裂声前后形成对照，让静音成为等待而非背景声空缺。",
        "protect_meaning_over_spectacle":
            "不加没有剧本依据的特技和虚假结果，人物犹豫及实际拆开封口必须被看见。",
        "what_the_director_refuses":
            "拒绝通过无关快切、演员夸张大叫或持续配乐直接告诉观众该感到悲伤。",
        "departmental_creative_freedom":
            "导演规定观众必须见证决定发生，演员、摄影、声音、剪辑可提出更准确的实现方案。",
    }
    methods = (["chow_absurdity_from_character",
                "chow_visual_gag_over_verbal_label",
                "chow_underdog_laughter_and_pathos"] if comedy else
               ["leigh_truthful_behavior", "scorsese_emotion_reveal"])
    chosen = [{
        "method_id": ident,
        "why_this_story":
            "这里的人物虽只拿着一封信，却真正在面对害怕结果的处境，这种拍法有明确依据。",
        "when_to_reject":
            "若节奏只是在拖延、不体现人物的真实欲望或造成事实改变，就应该撤回。",
        "audience_effect":
            "观众将注意到角色从规避答案到最终承担结果的行为转折，而不是只听旁白。",
        "alternative_and_cost":
            "另一方案是直接切到拆信，但观众可能不会理解这个微小动作对人物的意义。",
    } for ident in methods]
    shots = []
    for i, sid in enumerate(state["shot_ids"]):
        shots.append({
            "shot_id": sid,
            "applied_methods": methods[:2],
            "audience_before": (
                "观众以为人物只是伸手取信，尚不知道为何碰到封口之前会停下。" if i == 0
                else "观众已注意到害怕，接下来等待看到角色是否真的会拆开封口。"),
            "audience_after": (
                "观众终于理解，迟疑不是迟钝，而是人物把答案当成值得害怕的事。" if i == 0
                else "观众看见信封被真正拆开，人物开始面对自己曾经回避的结果。"),
            "visible_or_audible_change": (
                "角色伸出右手却在封口前停住，袖口发出很轻的摩擦声。" if i == 0
                else "同一只手终于撕开封口，纸张声音替代之前漫长的安静。"),
            "chosen_screen_language": (
                "固定画面保留手、封口与人物视线之间的真实空间关系，停留到犹豫出现。" if i == 0
                else "保持相同空间方向，让撕开动作完成后暂时不切走观察人物反应。"),
            "rejected_alternative": (
                "另一方案是快速推进人物面部并提前加入惊悚音乐，会太早断言人物害怕。" if i == 0
                else "另一方案是在刚接触纸张时切到夸张特写，会丢失人物完成选择的过程。"),
            "why_choice_works_better": (
                "本方案让观众从动作中自行发现迟疑，避免用剪辑暗示代替真实的行为。" if i == 0
                else "本方案让两镜的手部状态在同一个方向下连续，观众明确看到决定兑现。"),
            "emotion_or_meaning_lost_if_generic":
                "若剪成普通的恐惧B-roll，观众无法看到人物在具体封口前改变选择的代价。",
            "acting_direction":
                "演员维持明确的手部姿态，停顿不能用大喊取代；以真实想知道答案的欲望演出迟疑。",
            "camera_art_direction":
                "保持手和封口都能被看清，机位与光线服务动作可见性，不使用无缘由的运镜。",
            "sound_direction":
                "不用夸张配乐解释内心；安排袖口细响与纸张撕裂声形成具体情绪和节奏变化。",
            "editing_direction":
                "保留观众观察手部迟疑的时长，纸面未发生变化前不要用快切制造虚假因果。",
            "ai_production_fallback":
                "如果模型无法自然生成手指和纸面接触，采用连贯关键帧与后期纸声，不添加新剧情。",
            "gag_function": ("expectation" if i == 0 else "emotional_payoff") if comedy else "none",
        })
    comic_design = None
    if comedy:
        comic_design = {
            "why_comedy_belongs_here":
                "角色越想表现得镇定，越不敢打开一封普通的信；这种反差来自真正的恐惧。",
            "real_character_need":
                "他需要知道答案来继续生活，但同时害怕答案会改变熟悉的人际关系。",
            "worlds_internal_logic":
                "保持真实物理空间，荒诞程度只来自迟疑被不断放大，而不让信纸凭空魔法变化。",
            "comic_target_not_a_vulnerable_person":
                "观众笑的是人类过度自我包装的窘境，不是羞辱他害怕或心理脆弱。",
            "timing_and_visual_readability":
                "笑点依靠拿信动作反复中断与最后真正撕开时的反差，声音必须清楚可听。",
            "underlying_emotional_stakes":
                "观众笑过后仍应感到小人物认真面对命运的勇气，不能让最后选择失去重量。",
            "avoid_random_gags_and_fake_facts":
                "不让信纸说话、不编造信中内容、不添加与人物处境无关的无厘头插科打诨。",
            "beat_ladder": [{
                "stage": stage,
                "concrete_story_event":
                    "同一个人和封口之间的接触不断被真实的犹豫打断，最终由角色自己完成动作。",
                "audience_expectation_shift":
                    "观众最初以为他会直接打开，经过反复停顿后变成期待他终于肯承担答案。",
            } for stage in art.GAG_LADDER],
        }
    return {
        "version": art.VERSION,
        "genre": "absurd_comedy" if comedy else "fiction",
        "provenance": proof,
        "director": thesis,
        "comic_mode": "character_based" if comedy else "off",
        "comic_design": comic_design,
        "chosen_methods": chosen,
        "shots": shots,
    }


def _command_receipt(base, state, meeting):
    import director_department_command as command
    x = command.validate_command(base, state, meeting)
    return {
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_lock_digest": x["director_lock_digest"],
        "director_command_digest": x["command_digest"],
    }


class DirectorArtisticMethodsTests(unittest.TestCase):
    def setUp(self):
        self.source, self.base, self.state = _ready_team()
        self.meeting = _command(self.base, self.state)
        self.serious = plan_for(self.base, self.state, self.meeting)
        self.comic = plan_for(self.base, self.state, self.meeting, comedy=True)

    def test_artistic_director_request_contains_primary_craft_and_optional_comedy(self):
        req = art.request(self.base, self.state, self.meeting,
                          genre="fiction", source_text=self.source)
        self.assertFalse(req["dispatch_allowed"])
        self.assertFalse(req["artistic_quality_certified"])
        self.assertIn("周星驰", req["messages"][0]["content"])
        payload = json.loads(req["messages"][1]["content"])
        self.assertEqual(payload["complete_source_script"], self.source)
        self.assertGreaterEqual(len(payload["available_transferable_methods"]), 9)
        for key in ("chow_absurdity_from_character",
                    "chow_underdog_laughter_and_pathos",
                    "chow_visual_gag_over_verbal_label"):
            self.assertIn(key, payload["available_transferable_methods"])

    def test_serious_story_does_not_become_comedy(self):
        got = art.validate(self.base, self.state, self.meeting, self.serious)
        self.assertEqual(got["comic_mode"], "off")
        self.assertEqual(got["shot_count"], 2)
        self.assertFalse(got["independent_art_quality_certified"])
        self.assertFalse(got["video_or_paid_model_generated"])
        bad = deepcopy(self.serious)
        bad["shots"][0]["gag_function"] = "setup"
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "COMEDY_FORCED_INTO_SERIOUS_FILM"):
            art.validate(self.base, self.state, self.meeting, bad)
        bad = deepcopy(self.serious)
        bad["comic_design"] = self.comic["comic_design"]
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "UNREQUESTED_COMEDY"):
            art.validate(self.base, self.state, self.meeting, bad)

    def test_chow_absurdism_depends_on_real_character_need_not_random_jokes(self):
        got = art.validate(self.base, self.state, self.meeting, self.comic)
        self.assertEqual(got["comic_mode"], "character_based")
        self.assertIn("chow_absurdity_from_character", got["chosen_method_ids"])
        payload = art.departmental_context(
            self.base, self.state, self.meeting, self.comic, "acting")
        self.assertEqual(payload["this_department"], "acting")
        self.assertIn("演员维持明确的手部姿态", payload["per_shot"][0]["detailed_department_direction"])
        self.assertEqual(len(payload["genre_comic_design_if_any"]["beat_ladder"]), 6)

    def test_absurd_must_have_character_logic_real_beats_and_chow_method(self):
        bad = deepcopy(self.comic)
        bad["comic_design"]["worlds_internal_logic"] = "随机好笑"
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "COMEDY_CAUSALITY_MISSING"):
            art.validate(self.base, self.state, self.meeting, bad)
        bad = deepcopy(self.comic)
        bad["comic_design"]["beat_ladder"].pop()
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "COMEDY_LADDER_CAUSALITY"):
            art.validate(self.base, self.state, self.meeting, bad)
        bad = deepcopy(self.comic)
        bad["chosen_methods"] = [{
            **deepcopy(self.serious["chosen_methods"][0]),
            "method_id": "leigh_truthful_behavior"}]
        for shot in bad["shots"]:
            shot["applied_methods"] = ["leigh_truthful_behavior"]
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "COMEDY_CRAFT_NOT_SELECTED"):
            art.validate(self.base, self.state, self.meeting, bad)

    def test_craft_plan_uses_authoritative_source_and_locked_director(self):
        bad = deepcopy(self.serious)
        bad["provenance"]["source_digest"] = "forged"
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "DIRECTOR_PLAN_STALE"):
            art.validate(self.base, self.state, self.meeting, bad)
        bad = deepcopy(self.serious)
        bad["chosen_methods"][0]["method_id"] = "invented celebrity"
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "UNKNOWN_OR_DUPLICATE"):
            art.validate(self.base, self.state, self.meeting, bad)
        bad = deepcopy(self.serious)
        bad["shots"][1] = deepcopy(bad["shots"][0])
        bad["shots"][1]["shot_id"] = "S02"
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "COPY_PASTED_SHOT_JUDGMENTS"):
            art.validate(self.base, self.state, self.meeting, bad)

    def test_new_role_request_carries_director_artistic_plan_to_real_department(self):
        base = deepcopy(self.base)
        base["director_artistic_mode"] = {
            "kind": "director_artistic_method_required",
            "artistic_intent_before_specialists": True,
        }
        state = team.start(base, source_text=self.source)
        for task in ("director_brief", "script_edit", "director_lock"):
            original = deepcopy(self.state["tasks"][task]["deliverable"])
            state = team.submit(state, team.packet(state, task), original)
        meeting = _command(base, state)
        plan = plan_for(base, state, meeting, comedy=True)
        rec = art.validate(base, state, meeting, plan)
        vis = _visual(base, state, meeting)
        vis["artistic_methods_digest"] = rec["plan_digest"]
        with self.assertRaisesRegex(
                ValueError, "CREW_ARTISTIC_METHOD_PLAN_REQUIRED"):
            roles.build_role_messages(
                base, state, "acting", source_text=self.source,
                department_command=meeting, audiovisual_plan=vis)
        actual = roles.build_role_messages(
            base, state, "acting", source_text=self.source,
            department_command=meeting, audiovisual_plan=vis,
            artistic_method_plan=plan)
        data = json.loads(actual["messages"][1]["content"].split(
            "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n", 1)[1])
        self.assertEqual(
            data["director_artistic_method_context"]["comic_mode"],
            "character_based")
        self.assertEqual(
            data["director_artistic_method_context"]["per_shot"][0]
            ["detailed_department_direction"],
            plan["shots"][0]["acting_direction"])
        self.assertEqual(
            data["director_audiovisual_intention"]["artistic_methods_digest"],
            rec["plan_digest"])
        # The same bound director plan is verified at response acceptance;
        # do not let a model answer to a different artistic proposal.
        with self.assertRaisesRegex(ValueError,
                                    "CREW_ARTISTIC_METHOD_PLAN_REQUIRED"):
            roles.validate_role_output(
                base, state, "acting", '{"shots":{}}',
                source_text=self.source, department_command=meeting,
                audiovisual_plan=vis)
        with self.assertRaises(ValueError) as ex:
            roles.validate_role_output(
                base, state, "acting", '{"shots":{}}',
                source_text=self.source, department_command=meeting,
                audiovisual_plan=vis, artistic_method_plan=plan)
        self.assertNotIn("ARTISTIC_METHOD_PLAN_REQUIRED", str(ex.exception))
        wrong = deepcopy(plan)
        wrong["comic_design"]["real_character_need"] += "此处未经审核添加了额外动机。"
        with self.assertRaisesRegex(
                visual.VisualLanguageError, "ARTISTIC_PRECEDENT_CHANGED"):
            visual.validate(base, state, meeting, vis,
                            artistic_method_plan=wrong)

    def test_genre_is_not_a_nickname_and_art_method_before_visual(self):
        with self.assertRaisesRegex(art.ArtisticMethodError,
                                    "UNSUPPORTED_GENRE"):
            art.request(self.base, self.state, self.meeting, genre="ChowStyle")
        with self.assertRaisesRegex(art.ArtisticMethodError, "SOURCE_STALE"):
            art.request(self.base, self.state, self.meeting,
                        genre="fiction", source_text="other private screenplay")
        report = art.validate(self.base, self.state, self.meeting, self.comic)
        vis = _visual(self.base, self.state, self.meeting)
        vis["artistic_methods_digest"] = report["plan_digest"]
        # Artistic 'absurd_comedy' is deliberately mapped to fiction
        # cinematography/scene genre, not forced into a nonexistent style code.
        got = visual.validate(self.base, self.state, self.meeting, vis,
                              artistic_method_plan=self.comic)
        self.assertEqual(got["artistic_methods_digest"], report["plan_digest"])


if __name__ == "__main__":
    unittest.main()
