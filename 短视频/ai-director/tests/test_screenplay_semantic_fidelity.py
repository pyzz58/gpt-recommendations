"""QO-W01 synthetic: 100% source IDs can still invert the author's thesis."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agent_team
import screenplay_adaptation as adaptation
import screenplay_director_handoff as handoff
import screenplay_fulltext_intake as intake_module
import screenplay_professional_review as craft
import screenplay_semantic_fidelity as semantic


# All text is deliberately invented and safe to commit in a public repository.
FIRST = ("旧地图只画到了河边。先前的旅行者都在追求更快地抵达对岸，"
         "谁也没有检查河对面的道路是否仍然存在。")
MIDDLE = ("村里人讨论桥的材料、通行速度和工期，一次次找到可行的施工办法。"
          "但这些办法都没有回答这条道路最后应该连接哪一个地方。")
LAST = ("人们后来意识到，真正的问题并不是怎样更快过河，"
        "而是这座桥究竟应该通往哪里？这才是整个故事的开放式追问。")
ARTICLE = "\n\n".join([FIRST] + [MIDDLE] * 7 + [LAST])
FIRST_MARK = "旧地图只画到了河边"
QUESTION_MARK = "这座桥究竟应该通往哪里"


class QOW01SemanticFidelityTests(unittest.TestCase):
    def setUp(self):
        self.intake = intake_module.prepare_fulltext(ARTICLE, risk_domain="none")
        self.units = self.intake["scope_units"]
        self.first_unit = next(u["id"] for u in self.units
                               if FIRST_MARK in u["text"])
        self.last_unit = next(u["id"] for u in self.units
                              if QUESTION_MARK in u["text"])
        self.manifest = {
            "version": semantic.VERSION, "genre": "essay",
            "document_digest": self.intake["document_digest"],
            "scope_digest": self.intake["scope_digest"],
            "ideas": [
                {
                    "id": "IDEA-001", "kind": "central_question",
                    "importance": "critical", "source_unit_ids": [self.last_unit],
                    "source_quote": QUESTION_MARK,
                    "meaning": "全篇最后必须保留的追问，是造桥的目的而不是渡河的速度。",
                    "loss_if_missing": "观众会误以为全文只讨论工程效率，忽略最重要的价值选择。",
                },
                {
                    "id": "IDEA-002", "kind": "meaningful_nuance",
                    "importance": "supporting", "source_unit_ids": [self.first_unit],
                    "source_quote": FIRST_MARK,
                    "meaning": "开场交代已有知识的边界，并为最后目的之问建立前提。",
                    "loss_if_missing": "观众不理解为什么旧有旅行经验不足以判断新桥的终点。",
                },
            ]
        }
        beats = []
        for i, unit in enumerate(self.units):
            action = "有人把道路与桥的旧记录摊开，逐页整理以便检验。"
            if unit["id"] == self.first_unit:
                action = "有人发现旧地图只画到了河边，后面的道路未曾标注。"
            if unit["id"] == self.last_unit:
                action = "他们停下速度争论，写下一行字：这座桥究竟应该通往哪里？"
            beats.append({
                "id": "B%03d" % (i + 1), "source_ids": [unit["id"]],
                "operation": "keep", "dramatic_function": "推进思考与资料整理",
                "action": action, "dialogue": [], "voiceover": "",
                "duration_s": 3.0, "editorial_reason": "维护源文信息与认知转折",
            })
        self.proposal = {
            "version": adaptation.VERSION, "theme": "旧地图与桥",
            "dramatic_question": "桥的目的是什么？",
            "turning_point": "人们停止只讨论桥的工期",
            "payoff": "最后留下有关桥的去向的追问",
            "scenes": [{"id": "SC01", "heading": "INT. 村会议室 - 日",
                        "beats": beats}], "omissions": [],
        }
        self.wrapper = intake_module.review_packet(
            self.intake, ARTICLE, self.proposal)

    def _semantics(self, *, proposal_wrapper=None, override=None):
        wrapper = proposal_wrapper or self.wrapper
        script = wrapper["screenplay_review_packet"]["screenplay_fountain"]
        out = {
            "version": semantic.VERSION,
            "scope_digest": self.intake["scope_digest"],
            "manifest_digest": agent_team.fingerprint(self.manifest),
            "proposal_digest": wrapper["screenplay_review_packet"]["proposal_digest"],
            "screenplay_sha256": hashlib.sha256(script.encode()).hexdigest(),
            "review_items": [
                {
                    "idea_id": "IDEA-001",
                    "beat_ids": [self.proposal["scenes"][0]["beats"][-1]["id"]],
                    "screenplay_quote": QUESTION_MARK,
                    "assessment": "faithful",
                    "reason": "最后的追问在剧本正文中明确保留，且未被换成速度就是唯一目标。",
                    "viewer_consequence": "观众最终仍将问题理解为道路连接的目的，而不是简单追求速度。",
                    "rewrite_action": "",
                },
                {
                    "idea_id": "IDEA-002",
                    "beat_ids": [self.proposal["scenes"][0]["beats"][0]["id"]],
                    "screenplay_quote": FIRST_MARK,
                    "assessment": "faithful",
                    "reason": "开场保留旧地图的局限，为价值目的转折提供足够的前提。",
                    "viewer_consequence": "观众能够明白原有地图信息不足，后续判断仍需超越眼前经验。",
                    "rewrite_action": "",
                },
            ],
            "overall_recommendation": "ready_for_author_review",
        }
        if override:
            override(out)
        return out

    def _craft(self, wrapper):
        script = wrapper["screenplay_review_packet"]["screenplay_fountain"]
        return {
            "version": craft.VERSION, "genre": "essay",
            "screenplay_sha256": hashlib.sha256(script.encode()).hexdigest(),
            "proposal_digest": wrapper["screenplay_review_packet"]["proposal_digest"],
            "criteria": [{
                "category": cat, "assessment": "effective",
                "screenplay_quote": FIRST_MARK,
                "specific_reason": "开场旧地图明确呈现了故事问题的知识前提和边界。",
                "rewrite_action": "",
            } for cat in craft.CRITERIA],
            "blockers": [], "overall_recommendation": "ready_for_author_review",
        }

    def _decisions(self, wrapper):
        decisions = handoff.review_form(wrapper["screenplay_review_packet"])
        decisions["review_intent"] = "accept_for_director_planning"
        for item in decisions["changes"]:
            item["choice"] = "accept"
        return decisions

    def test_long_source_baseline_has_all_ids_but_semantic_gap_is_possible(self):
        self.assertGreater(len(ARTICLE), 400)
        self.assertIn(QUESTION_MARK, self.units[-1]["text"])
        check = self.wrapper["screenplay_review_packet"]["review"]
        self.assertEqual(check["source_coverage"], len(self.units))
        self.assertEqual(check["source_omitted"], 0)
        altered = deepcopy(self.proposal)
        altered["scenes"][0]["beats"][-1]["action"] = (
            "大家得出结论：只要过河速度最快，修桥的目的就已经实现。")
        packet = intake_module.review_packet(self.intake, ARTICLE, altered)
        # All source IDs mapped, no mechanical omissions -- but original
        # last question has been replaced by an assertive false conclusion.
        self.assertEqual(packet["screenplay_review_packet"]["review"]["source_omitted"], 0)
        self.assertNotIn(QUESTION_MARK,
                         packet["screenplay_review_packet"]["screenplay_fountain"])
        flagged = self._semantics(proposal_wrapper=packet)
        flagged["review_items"][0].update({
            "assessment": "contradicted", "screenplay_quote": "只要过河速度最快",
            "reason": "原稿追问桥要通向哪里，改稿却断言只要速度最快便已获得答案。",
            "viewer_consequence": "观众把作者的开放价值问题误解成只有速度才是成功标准。",
            "rewrite_action": "恢复对修桥目的的开放追问，而非以通行速度替代作者的核心论点。",
        })
        flagged["overall_recommendation"] = "revise"
        return packet, flagged

    def test_idea_source_bound_and_pre_adaptation_prompt_holds_manifest(self):
        receipt = semantic.validate_manifest(self.intake, ARTICLE, self.manifest)
        self.assertEqual(receipt["critical_count"], 1)
        self.assertFalse(receipt["source_idea_completeness_verified_by_human"])
        request = semantic.build_idea_extraction_request(
            self.intake, ARTICLE, genre="essay")
        self.assertFalse(request["dispatch_allowed"])
        data = json.loads(request["messages"][1]["content"])
        self.assertEqual(data["source_units"], self.units)
        editor = intake_module.editor_request(
            self.intake, ARTICLE, mode="essay",
            source_idea_manifest=self.manifest)
        payload = json.loads(editor["messages"][1]["content"])
        self.assertEqual(payload["pre_adaptation_source_ideas"], self.manifest)
        self.assertEqual(payload["source_ideas_manifest_digest"],
                         agent_team.fingerprint(self.manifest))
        self.assertTrue(editor["semantic_source_ideas_provided_before_adaptation"])
        self.assertFalse(editor["semantic_source_ideas_verified_by_human"])

    def test_exact_source_quote_and_source_unit_required(self):
        wrong = deepcopy(self.manifest)
        wrong["ideas"][0]["source_quote"] = "原文从来没有这样的观点，完全杜撰。"
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "UNGROUNDED_SOURCE_QUOTE"):
            semantic.validate_manifest(self.intake, ARTICLE, wrong)
        wrong = deepcopy(self.manifest)
        wrong["ideas"][0]["source_unit_ids"] = [self.first_unit]
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "UNGROUNDED_SOURCE_QUOTE"):
            semantic.validate_manifest(self.intake, ARTICLE, wrong)
        wrong = deepcopy(self.manifest)
        wrong["ideas"][0]["importance"] = "supporting"
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "NO_CRITICAL_IDEA"):
            semantic.validate_manifest(self.intake, ARTICLE, wrong)

    def test_negative_semantic_review_blocks_full_coverage_false_claim(self):
        bad_packet, flagged = self.test_long_source_baseline_has_all_ids_but_semantic_gap_is_possible()
        report = semantic.validate_semantic_review(
            self.intake, ARTICLE, bad_packet, self.manifest, flagged)
        self.assertEqual(report["critical_ideas_flagged"], ["IDEA-001"])
        self.assertEqual(report["recommendation"], "revise")
        edit = semantic.build_targeted_semantic_rewrite_request(
            self.intake, ARTICLE, bad_packet, self.manifest, flagged)
        self.assertFalse(edit["dispatch_allowed"])
        details = json.loads(edit["messages"][1]["content"])
        self.assertEqual(details["lost_or_distorted_ideas"][0]["idea"]["id"],
                         "IDEA-001")
        with self.assertRaisesRegex(intake_module.FulltextIntakeError,
                                    "CORE_MEANING_REVISION_REQUIRED"):
            intake_module.semantic_quality_director_handoff(
                self.intake, ARTICLE, bad_packet, self._decisions(bad_packet),
                {}, self._craft(bad_packet), self.manifest, flagged, genre="essay")

    def test_empty_or_fabricated_semantic_review_does_not_pass(self):
        r = self._semantics()
        r["review_items"].pop()
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "INCOMPLETE"):
            semantic.validate_semantic_review(
                self.intake, ARTICLE, self.wrapper, self.manifest, r)
        r = self._semantics()
        r["review_items"][0]["screenplay_quote"] = "从不存在的编剧正文"
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "FAKE_SCREENPLAY_QUOTE"):
            semantic.validate_semantic_review(
                self.intake, ARTICLE, self.wrapper, self.manifest, r)
        r = self._semantics()
        r["review_items"][0]["beat_ids"] = [self.proposal["scenes"][0]["beats"][0]["id"]]
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "UNGROUNDED_BEAT_LINK"):
            semantic.validate_semantic_review(
                self.intake, ARTICLE, self.wrapper, self.manifest, r)
        r = self._semantics()
        r["overall_recommendation"] = "revise"
        with self.assertRaisesRegex(semantic.MeaningReviewError,
                                    "FALSE_READINESS"):
            semantic.validate_semantic_review(
                self.intake, ARTICLE, self.wrapper, self.manifest, r)

    def test_strict_director_receives_meaning_review_but_no_fake_authentication(self):
        verdict = self._semantics()
        request = semantic.build_semantic_review_request(
            self.intake, ARTICLE, self.wrapper, self.manifest)
        data = json.loads(request["messages"][1]["content"])
        self.assertEqual(data["original_scope"], ARTICLE)
        self.assertEqual(data["manifest_digest"], agent_team.fingerprint(self.manifest))
        self.assertFalse(request["dispatch_allowed"])
        route = intake_module.semantic_quality_director_handoff(
            self.intake, ARTICLE, self.wrapper, self._decisions(self.wrapper),
            {}, self._craft(self.wrapper), self.manifest, verdict, genre="essay")
        self.assertEqual(route["next_professional_role"], "director_brief")
        self.assertTrue(route["semantic_fidelity_reviewed"])
        self.assertEqual(route["core_ideas_declared_preserved_by_editor"], 1)
        self.assertFalse(route["semantic_accuracy_verified_by_human"])
        self.assertFalse(route["author_approval_authenticated"])
        self.assertFalse(route["screenplay_artistic_quality_certified"])
        self.assertFalse(route["paid_video_authorized"])

    def test_stale_document_and_script_fail_closed(self):
        with self.assertRaisesRegex(semantic.MeaningReviewError, "STALE_SOURCE_INTAKE"):
            semantic.validate_manifest(self.intake, ARTICLE + "假结尾", self.manifest)
        change = deepcopy(self.proposal)
        change["scenes"][0]["beats"][-1]["action"] += "附带新改动"
        packet = intake_module.review_packet(self.intake, ARTICLE, change)
        with self.assertRaisesRegex(semantic.MeaningReviewError, "REVIEW_STALE"):
            semantic.validate_semantic_review(
                self.intake, ARTICLE, packet, self.manifest, self._semantics())

    def test_fiction_documentary_and_essay_share_meaning_not_mandatory_cast(self):
        for genre in ("fiction", "documentary", "essay"):
            with self.subTest(genre=genre):
                new_manifest = deepcopy(self.manifest)
                new_manifest["genre"] = genre
                self.assertEqual(semantic.validate_manifest(
                    self.intake, ARTICLE, new_manifest)["critical_count"], 1)
                request = semantic.build_idea_extraction_request(
                    self.intake, ARTICLE, genre=genre)
                self.assertFalse(request["dispatch_allowed"])

    def test_false_faithful_is_not_a_semantic_proof(self):
        # Even if an unqualified editor lies and marks a contradictory script
        # faithful, no deterministic scheme can claim verified human meaning.
        altered, _ = self.test_long_source_baseline_has_all_ids_but_semantic_gap_is_possible()
        fake = self._semantics(proposal_wrapper=altered)
        fake["review_items"][0]["screenplay_quote"] = "只要过河速度最快"
        result = semantic.validate_semantic_review(
            self.intake, ARTICLE, altered, self.manifest, fake)
        self.assertFalse(result["semantic_accuracy_verified_by_human"])
        self.assertFalse(result["source_idea_completeness_verified_by_human"])


if __name__ == "__main__":
    unittest.main()
