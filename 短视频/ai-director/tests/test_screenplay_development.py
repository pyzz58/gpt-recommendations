"""QO-W01: public invented story, full writer craft stages, not model quality."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import screenplay_development as development
import screenplay_fulltext_intake as full
import screenplay_director_handoff as handoff
import screenplay_adaptation as adaptation
import screenplay_professional_review as professional


ARTICLE = (
    "村里人带着一张旧地图来到河边。地图上画出了桥，却没有标出桥通向哪里。"
    "有人只关心工程需要多少时间，另一人关心抵达对岸以后会发生什么。"
    "他们争论整整一个下午，最后决定先把桥两侧的道路画清楚。"
    "故事并没有回答哪条道路一定正确，而是留下了一个更重要的问题："
    "这座桥究竟是为了谁而修建？"
)
PROTECTED = "这座桥究竟是为了谁而修建"
FREEDOM = "有人只关心工程需要多少时间"


class CreativeDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.intake = full.prepare_fulltext(ARTICLE, risk_domain="none")
        self.diagnosis = {
            "version": development.VERSION, "genre": "essay",
            "scope_digest": self.intake["scope_digest"],
            "work_essence": "这不是单纯关于桥梁进度的故事，而是关于建设究竟服务于谁。",
            "why_it_matters": "从技术可以做什么转向社会究竟应该做什么，留下开放性的价值追问。",
            "distinct_voice": "平实、克制、不把结论强加给观众，而是让人看见争论背后的空白。",
            "translation_to_screen": "让空白地图和不断被擦去的工程数字形成具体可见的认知反差。",
            "audience_before": "观众开始时认为工程只需要决定最快的施工办法。",
            "audience_after": "观众最终意识到，施工的目的和服务对象比速度更值得首先回答。",
            "protected": [{
                "quote": PROTECTED,
                "reason": "开放的社会价值追问是作品的落点，不能篡改成单一速度标准。",
            }],
            "freedom": [{
                "quote": FREEDOM,
                "reason": "工程时长讨论可以通过行为和地图上的记号表现，不必全文照搬。",
            }],
            "uncertainties": ["作者没有确定回答桥为谁而建，需要保留开放而非替作者判定。"],
        }
        self.takes = {
            "version": development.VERSION,
            "source_digest": self.intake["scope_digest"],
            "diagnosis_digest": development._fingerprint(self.diagnosis),
            "takes": [
                {
                    "id": "TAKE-A", "angle": "人物争论驱动的极简短剧情改编",
                    "narrative_engine": "争论从修桥进度转向道路服务对象的选择",
                    "opening": "工匠在地图上用笔画出预定桥梁，却发现终点留白。",
                    "turn": "众人停止互相计算工期，开始问谁需要走这条桥。",
                    "ending": "地图的留白没有被填满，留下开放社会价值问题。",
                    "screen_expression": "以演员的行动、等待和擦掉数字的行为承载戏剧转折。",
                    "expected_change": "观众从关注项目速度转为思考修建目的。",
                    "artistic_tradeoff": "人物更具情绪共鸣，但可能弱化原稿平静议论口吻。",
                    "ai_short_video_note": "涉及两个演员互动时应允许分镜及后期配音。",
                    "estimated_duration_s": 45,
                    "source_choices": [{
                        "quote": FREEDOM, "choice": "compress",
                        "reason": "压缩工程时间的口头解释，以人物的行为展示技术视角的局限。",
                    }],
                    "new_fact_risks": [],
                },
                {
                    "id": "TAKE-B", "angle": "地图作为概念对象的纯视觉哲学短片",
                    "narrative_engine": "逐层揭示地图信息的不完整性，使观众认识不断改变",
                    "opening": "地图上已有一座桥的图形，但桥后面是一片空白。",
                    "turn": "关于进度的数字越来越多，却始终填不上桥的另一侧。",
                    "ending": "最后只出现开放问题：这座桥究竟是为了谁而修建？",
                    "screen_expression": "纸、道路与擦写留下的痕迹逐步传达信息差距。",
                    "expected_change": "观众从把建设视为速度问题转为把它看成目的问题。",
                    "artistic_tradeoff": "突出作者思想，但缺少角色关系和个体戏剧力度。",
                    "ai_short_video_note": "可以由静帧后期动画呈现准确文字，不强求视频模型生成汉字。",
                    "estimated_duration_s": 40,
                    "source_choices": [{
                        "quote": FREEDOM, "choice": "reframe",
                        "reason": "把口头讨论改成逐步增加的工程数字，避免机械旁白重复。",
                    }, {
                        "quote": PROTECTED, "choice": "retain",
                        "reason": "最后仍以开放问题而不是确切答案收束作者表达。",
                    }],
                    "new_fact_risks": [],
                },
            ],
        }
        self.selection = {
            "version": development.VERSION,
            "source_digest": self.intake["scope_digest"],
            "takes_digest": development._fingerprint(self.takes),
            "decision": "TAKE-B",
            "comparisons": [{
                "id": "TAKE-A",
                "advantage": "人物争论更容易有情绪强度和行为性推进。",
                "cost": "双人互动增加生成风险，也可能偏离原文克制的思想声音。",
            }, {
                "id": "TAKE-B",
                "advantage": "让地图本身承载技术和目的之间的认识反差。",
                "cost": "角色张力较少，可能需要严格审查视觉段落是否真正推进。",
            }],
            "choice_reason": "作者的核心是开放的建设目的，地图视觉叙事更能体现论证结构。",
            "risk_to_author_intent": "不得以确定的工程速度标准替代作者最后的开放提问。",
            "author_consultation_needed": False,
        }
        self.treatment = {
            "version": development.VERSION,
            "scope_digest": self.intake["scope_digest"],
            "takes_digest": self.selection["takes_digest"],
            "selection_digest": development._fingerprint(self.selection),
            "selected_take_id": "TAKE-B",
            "premise": "旧地图正在逐步变得精确，但最重要的目的始终无法用速度计算。",
            "scenes": [{
                "id": "SC01",
                "starting_state": "观众初看地图，以为只是缺少一处施工进度安排。",
                "visible_or_audible_event": "旧地图放在桌上，一支笔画出桥的起点和一行速度数据。",
                "changed_understanding_or_choice": "地图上已经有了数字，但桥通向的地方仍然是一片空白。",
                "ending_state": "观众开始怀疑技术数据能否回答关于目的的问题。",
                "reason_for_scene": "建立技术回答与真正的建设目的之间最初的不一致。",
                "estimated_duration_s": 18,
            }, {
                "id": "SC02",
                "starting_state": "观众已经察觉仅靠工程数字无法说明目的。",
                "visible_or_audible_event": "纸页上画出桥的一侧道路，另一侧始终留白，没有直接填入答案。",
                "changed_understanding_or_choice": "观众从追求速度转而询问建桥究竟服务什么人。",
                "ending_state": "影片将开放问题交给观众，不把作者未给出的答案填进去。",
                "reason_for_scene": "回应原稿最后的开放式追问，同时保留观众自己的判断。",
                "estimated_duration_s": 22,
            }],
            "ending_reverberation": "让桥后面的空白与观众心中的问题同时保留下来。",
            "unsolved_writer_questions": ["具体社会人群未在原稿说明，不能凭空确定这座桥为谁而建。"],
        }
        self.packet = development.development_packet(
            self.intake, ARTICLE, self.diagnosis, self.takes,
            self.selection, self.treatment)

        beats = [{
            "id": "B%03d" % (i + 1), "source_ids": [u["id"]],
            "operation": "keep", "dramatic_function": "为目的与效率的差异提供进展",
            "action": (
                "一张桥梁地图上只有起点被画出来，后面留下一大片空白。"
                if i == 0 else
                "地图再次展开，工期数字旁边有人写下一个悬而未决的问题。"),
            "dialogue": [],
            "voiceover": "", "duration_s": 9.0,
            "editorial_reason": "省去重复解释，保留作者从速度到目的的认知推进",
        } for i, u in enumerate(self.intake["scope_units"])]
        self.proposal = {
            "version": adaptation.VERSION, "theme": "桥梁的空白",
            "dramatic_question": "修桥究竟是为了谁？",
            "turning_point": "数字无法解释桥另一侧的空白。",
            "payoff": "真正的建设目的是开放问题",
            "scenes": [{"id": "SC01", "heading": "INT. 村会议室 - 日",
                        "beats": beats}],
            "omissions": [],
        }
        self.wrapper = development.screenplay_review_packet(
            self.intake, ARTICLE, self.packet, self.proposal)

    def _alignment(self, revise=False):
        script = self.wrapper["screenplay_review_packet"]["screenplay_fountain"]
        return {
            "version": development.VERSION,
            "development_digest": development._fingerprint(self.packet),
            "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
            "scene_assessments": [{
                "scene_id": "SC01",
                "judgment": "realized",
                "screenplay_quote": "桥梁地图上只有起点被画出来",
                "viewer_effect": "观众能看到只有技术起点却缺少目的地的关键信息。",
                "specific_reason": "剧本将地图不完整变成可见物件而非重复说明。",
                "rewrite_action": "",
            }, {
                "scene_id": "SC02",
                "judgment": "unjustified_loss" if revise else "creative_reinterpretation",
                "screenplay_quote": "工期数字旁边有人写下",
                "viewer_effect": "观众能够看见工期数字已经无法直接回答目的。",
                "specific_reason": "把最后质问移到地图内部是合理且清楚的影像转译。",
                "rewrite_action": "需要明确恢复对桥的目的的开放追问，避免以速度作终局结论。",
            }],
            "overall_recommendation": "revise" if revise else "ready_for_author_review",
        }

    def _critic(self):
        packet = self.wrapper["screenplay_review_packet"]
        script = packet["screenplay_fountain"]
        return {
            "version": professional.VERSION, "genre": "essay",
            "screenplay_sha256": hashlib.sha256(script.encode()).hexdigest(),
            "proposal_digest": packet["proposal_digest"],
            "criteria": [{
                "category": c, "assessment": "effective",
                "screenplay_quote": "桥梁的空白",
                "specific_reason": "经过改编的文本能够准确呈现桥梁目的与工程速度的认识差距。",
                "rewrite_action": "",
            } for c in professional.CRITERIA],
            "blockers": [], "overall_recommendation": "ready_for_author_review",
        }

    def _author_form(self):
        form = handoff.review_form(self.wrapper["screenplay_review_packet"])
        form["review_intent"] = "accept_for_director_planning"
        for change in form["changes"]:
            change["choice"] = "accept"
        return form

    def test_unsent_deep_read_has_full_source_and_no_auto_craft_certification(self):
        request = development.diagnosis_request(self.intake, ARTICLE, genre="essay")
        self.assertFalse(request["dispatch_allowed"])
        payload = json.loads(request["messages"][1]["content"])
        self.assertEqual(payload["source"], ARTICLE)
        self.assertEqual(payload["source_units"], self.intake["scope_units"])
        receipt = development.validate_diagnosis(self.intake, ARTICLE, self.diagnosis)
        self.assertFalse(receipt["author_intent_verified"])

    def test_two_different_creative_takes_can_delete_or_reframe_source(self):
        request = development.takes_request(self.intake, ARTICLE, self.diagnosis)
        self.assertFalse(request["dispatch_allowed"])
        receipt = development.validate_takes(
            self.intake, ARTICLE, self.diagnosis, self.takes)
        self.assertEqual(receipt["take_count"], 2)
        self.assertFalse(receipt["take_difference_artistically_verified"])
        self.assertIn("reframe", [x["choice"] for x in
                                  self.takes["takes"][1]["source_choices"]])
        self.assertFalse(self.intake["claims_or_citations_invented"])

    def test_mere_reworded_duplicate_is_rejected(self):
        bad = deepcopy(self.takes)
        for key in ("angle", "narrative_engine", "opening", "screen_expression"):
            bad["takes"][1][key] = bad["takes"][0][key]
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "IDENTICAL_TAKES"):
            development.validate_takes(
                self.intake, ARTICLE, self.diagnosis, bad)

    def test_selection_includes_cost_of_rejected_option(self):
        request = development.selection_review_request(
            self.intake, ARTICLE, self.diagnosis, self.takes)
        self.assertFalse(request["dispatch_allowed"])
        receipt = development.validate_selection(
            self.intake, ARTICLE, self.diagnosis, self.takes, self.selection)
        self.assertEqual(receipt["status"], "selected_for_treatment_review")
        rejected = deepcopy(self.selection)
        rejected["decision"] = "revise_all"
        self.assertEqual(development.validate_selection(
            self.intake, ARTICLE, self.diagnosis, self.takes, rejected)["status"],
            "revise_takes")
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "ALL_TAKES_REJECTED"):
            development.treatment_request(
                self.intake, ARTICLE, self.diagnosis, self.takes, rejected)

    def test_treatment_is_story_change_not_director_shot_list(self):
        prompt = development.treatment_request(
            self.intake, ARTICLE, self.diagnosis, self.takes, self.selection)
        self.assertFalse(prompt["dispatch_allowed"])
        proof = development.validate_treatment(
            self.intake, ARTICLE, self.diagnosis, self.takes, self.selection,
            self.treatment)
        self.assertEqual(proof["estimated_duration_s"], 40)
        self.assertFalse(proof["director_shots_defined"])
        self.assertEqual(len(self.treatment["scenes"]), 2)

    def test_full_screenplay_writer_message_uses_selected_treatment(self):
        request = development.screenplay_request(self.intake, ARTICLE, self.packet)
        self.assertTrue(request["creative_development_completed_before_screenplay"])
        self.assertFalse(request["writer_quality_human_verified"])
        self.assertFalse(request["dispatch_allowed"])
        message = json.loads(request["messages"][1]["content"])
        self.assertEqual(message["creative_development_packet"], self.packet)
        self.assertEqual(message["source"], ARTICLE)
        self.assertEqual(message["development_packet_digest"],
                         development._fingerprint(self.packet))

    def test_revision_of_selected_treatment_invalidates_old_packet(self):
        fake = deepcopy(self.packet)
        fake["treatment"]["scenes"][0]["visible_or_audible_event"] += "新事件"
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "PACKET_TAMPERED"):
            development.validate_packet(self.intake, ARTICLE, fake)
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "INTAKE_STALE"):
            development.validate_packet(self.intake, ARTICLE + "补写一句。", self.packet)

    def test_reviewed_screenplay_has_bound_selected_take_and_treatment(self):
        request = development.alignment_review_request(
            self.intake, ARTICLE, self.packet, self.wrapper)
        self.assertFalse(request["dispatch_allowed"])
        payload = json.loads(request["messages"][1]["content"])
        self.assertEqual(payload["source"], ARTICLE)
        self.assertEqual(payload["development"]["selection"]["decision"], "TAKE-B")
        receipt = development.validate_alignment_review(
            self.intake, ARTICLE, self.packet, self.wrapper, self._alignment())
        self.assertEqual(receipt["recommendation"], "ready_for_author_review")
        self.assertFalse(receipt["creative_quality_verified_by_human"])

    def test_missing_scene_or_false_quote_block_editorial_acceptance(self):
        wrong = self._alignment()
        wrong["scene_assessments"].pop()
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "SCENE_COUNT"):
            development.validate_alignment_review(
                self.intake, ARTICLE, self.packet, self.wrapper, wrong)
        wrong = self._alignment()
        wrong["scene_assessments"][0]["screenplay_quote"] = "没有出现在剧本里的文字"
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "FALSE_QUOTE"):
            development.validate_alignment_review(
                self.intake, ARTICLE, self.packet, self.wrapper, wrong)
        wrong = self._alignment(revise=True)
        wrong["overall_recommendation"] = "ready_for_author_review"
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "FALSE_READY"):
            development.validate_alignment_review(
                self.intake, ARTICLE, self.packet, self.wrapper, wrong)

    def test_creative_departure_is_allowed_but_unjustified_loss_blocks_director(self):
        accepted = development.validate_alignment_review(
            self.intake, ARTICLE, self.packet, self.wrapper, self._alignment())
        self.assertEqual(accepted["unjustified_losses"], [])
        with self.assertRaisesRegex(development.CreativeDevelopmentError,
                                    "UNRESOLVED_WRITER_REVISIONS"):
            development.director_handoff(
                self.intake, ARTICLE, self.packet, self.wrapper,
                self._alignment(revise=True), self._author_form(), {},
                self._critic(), genre="essay")
        routed = development.director_handoff(
            self.intake, ARTICLE, self.packet, self.wrapper,
            self._alignment(), self._author_form(), {},
            self._critic(), genre="essay")
        self.assertEqual(routed["next_professional_role"], "director_brief")
        self.assertTrue(routed["treatment_not_a_director_shot_list"])
        self.assertFalse(routed["creative_quality_verified_by_human"])
        self.assertFalse(routed["author_approval_authenticated"])

    def test_old_legacy_writer_and_director_route_still_available(self):
        old = full.editor_request(self.intake, ARTICLE, mode="essay")
        self.assertNotIn("creative_development_packet",
                         json.loads(old["messages"][1]["content"]))
        self.assertFalse(old["dispatch_allowed"])
        self.assertEqual(full.review_packet(
            self.intake, ARTICLE, self.proposal)["kind"],
            "fulltext_screenplay_review_wrapper_v1")


if __name__ == "__main__":
    unittest.main()
