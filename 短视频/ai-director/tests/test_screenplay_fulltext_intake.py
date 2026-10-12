"""Public SYNTHETIC fulltext writer tests; never upload a private user script."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import article_intake
import closing_evidence_card
import screenplay_fulltext_intake as full
import screenplay_adaptation as adaptation
import screenplay_director_handoff as handoff


FIRST = "城里有人靠旧地图寻路。图上只有街道和一条尚未完工的桥。"
MIDDLE = "会议室里的人尝试列出可以穿过河流的方式。他们争论的不是速度，而是谁能安全抵达。"
LAST = "到了夜晚，所有人终于提出真正的问题：这座桥应当通向什么地方？"
SYNTH = "\n\n".join([FIRST] + [MIDDLE] * 12 + [LAST])


class FulltextScreenplayIntakeTests(unittest.TestCase):
    def setUp(self):
        self.intake = full.prepare_fulltext(SYNTH, risk_domain="none")
        self.units = self.intake["scope_units"]
        beats = []
        for i, u in enumerate(self.units):
            beats.append({
                "id": "B%03d" % (i + 1),
                "source_ids": [u["id"]],
                "operation": "keep",
                "dramatic_function": "完整故事源段 " + u["id"],
                "action": "有人阅读一段记录，并将它放入整理好的资料夹。",
                "dialogue": [], "voiceover": "",
                "duration_s": 3.0, "editorial_reason": "保留全文审读来源对照",
            })
        self.proposal = {
            "version": adaptation.VERSION, "theme": "旧地图与河流",
            "dramatic_question": "桥通向什么地方？",
            "turning_point": "从通行方式转向真正目的",
            "payoff": "最后一个段落提出开放问题",
            "scenes": [{"id": "SC01", "heading": "INT. 会议室 - 日",
                        "beats": beats}],
            "omissions": [],
        }

    def test_full_400_plus_chars_complete_and_old_preview_is_abridged(self):
        self.assertGreater(len(SYNTH), 400)
        self.assertIn("这座桥应当通向什么地方", SYNTH)
        legacy = article_intake.prepare_episode(SYNTH)["plan"]
        self.assertTrue(any("preview length/shot limit" in o["reason"]
                            for o in legacy["editorial"]["omissions"]))
        self.assertNotIn("这座桥应当通向什么地方", legacy["editorial"]["narration_script"])
        self.assertEqual(self.intake["scope_span"], [0, len(SYNTH)])
        self.assertTrue(self.intake["document_exact_nonwhitespace_coverage"])
        self.assertTrue(self.intake["scope_exact_nonwhitespace_coverage"])
        self.assertEqual("".join(c for u in self.units for c in u["text"] if not c.isspace()),
                         "".join(c for c in SYNTH if not c.isspace()))
        self.assertIn("这座桥应当通向什么地方", self.units[-1]["text"])
        self.assertEqual(self.intake["base"]["claims"], [])
        self.assertIsNone(closing_evidence_card.build_card(self.intake["base"]))

    def test_actual_unsent_editor_prompt_has_fulltext_all_unit_text(self):
        task = full.editor_request(self.intake, SYNTH, mode="documentary")
        payload = json.loads(task["messages"][1]["content"])
        self.assertEqual(payload["source"], SYNTH)
        self.assertEqual(payload["source_units"], self.units)
        self.assertEqual(payload["source_scope_sha256"],
                         hashlib.sha256(SYNTH.encode()).hexdigest())
        self.assertIn(LAST, payload["source"])
        self.assertFalse(task["dispatch_allowed"])
        self.assertFalse(self.intake["paid_text_model_authorized"])

    def test_source_bound_review_and_existing_director_team(self):
        wrapper = full.review_packet(self.intake, SYNTH, self.proposal)
        self.assertEqual(wrapper["scope_vs_document"], "complete_document")
        self.assertEqual(wrapper["source_unit_count"], len(self.units))
        self.assertEqual(wrapper["critical_ideas_retained"],
                         "requires_human_editorial_review")
        self.assertEqual(wrapper["screenplay_review_packet"]["review"]["source_coverage"],
                         len(self.units))
        self.assertEqual(wrapper["screenplay_review_packet"]["review"]["source_omitted"], 0)
        form = handoff.review_form(wrapper["screenplay_review_packet"])
        form["review_intent"] = "accept_for_director_planning"
        for entry in form["changes"]:
            entry["choice"] = "accept"
        routed = full.director_handoff(self.intake, SYNTH, wrapper, form, {})
        director_task = handoff.director_request(routed)
        self.assertEqual(director_task["task_id"], "director_brief")
        self.assertEqual(routed["original_manuscript_digest"],
                         hashlib.sha256(SYNTH.encode()).hexdigest())
        self.assertEqual(routed["source_units_covered_or_explicitly_omitted"], True)
        self.assertFalse(routed["fulltext_critical_ideas_retained_verified"])
        self.assertFalse(routed["human_approval_authenticated"])
        self.assertTrue(all(x["status"] == "pending"
                            for x in routed["crew"]["tasks"].values()))

    def test_rejected_changes_or_missing_scope_units_block_handoff(self):
        altered = deepcopy(self.proposal)
        altered["scenes"][0]["beats"].pop()
        with self.assertRaisesRegex(adaptation.AdaptationError,
                                    "ADAPTATION_UNACKNOWLEDGED_SOURCE_LOSS"):
            full.review_packet(self.intake, SYNTH, altered)
        wrapped = full.review_packet(self.intake, SYNTH, self.proposal)
        decisions = handoff.review_form(wrapped["screenplay_review_packet"])
        with self.assertRaisesRegex(handoff.ScriptHandoffError, "SCRIPT_NOT_ACCEPTED"):
            full.director_handoff(self.intake, SYNTH, wrapped, decisions, {})

    def test_tamper_and_wrong_document_rejected(self):
        wrong = deepcopy(self.intake)
        wrong["scope_units"][-1]["text"] = "伪造"
        with self.assertRaisesRegex(full.FulltextIntakeError, "FULLTEXT_INTAKE_TAMPERED"):
            full.editor_request(wrong, SYNTH)
        with self.assertRaisesRegex(full.FulltextIntakeError, "FULLTEXT_DOCUMENT_STALE"):
            full.editor_request(self.intake, SYNTH + "另一个结尾。")
        wrapper = full.review_packet(self.intake, SYNTH, self.proposal)
        wrapper["source_unit_count"] += 1
        form = handoff.review_form(wrapper["screenplay_review_packet"])
        form["review_intent"] = "accept_for_director_planning"
        for entry in form["changes"]:
            entry["choice"] = "accept"
        with self.assertRaisesRegex(full.FulltextIntakeError, "FULLTEXT_REVIEW_TAMPERED"):
            full.director_handoff(self.intake, SYNTH, wrapper, form, {})

    def test_literal_source_link_is_optional_unverified_candidate(self):
        document = "仅供测试的资料链接：https://example.org/study。其它观点没有出处。"
        intake = full.prepare_fulltext(document, risk_domain="none")
        self.assertEqual(intake["source_supplied_reference_url_count"], 1)
        link = intake["source_supplied_reference_urls"][0]
        self.assertEqual(link["url"], "https://example.org/study")
        self.assertEqual(document[slice(*link["source_span"])], link["url"])
        self.assertEqual(link["status"], "source_supplied_unverified")
        self.assertEqual(intake["base"]["references"], [])
        self.assertIsNone(closing_evidence_card.build_card(intake["base"]))
        prompt = full.editor_request(intake, document)
        self.assertEqual(prompt["unverified_source_reference_candidates"], [link])
        self.assertEqual(prompt["citation_policy"],
                         "use_source_materials_if_present_never_invent")

    def test_titled_chapter_scope_keeps_whole_document_fingerprint(self):
        document = "前言没有剧本拍摄。\n## 第一章\n写给第一章的几个字。\n## 第二章\n第二章提出另一个问题。"
        intake = full.prepare_fulltext(document, episode_id="EP02")
        self.assertFalse(intake["entire_document_selected"])
        self.assertEqual(intake["document_digest"], hashlib.sha256(document.encode()).hexdigest())
        self.assertTrue(intake["scope_exact_nonwhitespace_coverage"])
        self.assertIn("第二章提出", intake["scope_units"][-1]["text"])
        self.assertNotIn("前言没有", "".join(x["text"] for x in intake["scope_units"]))

    def test_explicit_sentence_aligned_span_for_unheaded_long_manuscript(self):
        document = "这是一段完整的公开虚构素材。" * 700
        with self.assertRaisesRegex(full.FulltextIntakeError,
                                    "FULLTEXT_SELECT_CHAPTER_OR_SHORTER_SCOPE"):
            full.prepare_fulltext(document)
        sentence = "这是一段完整的公开虚构素材。"
        selected = full.prepare_fulltext(
            document, source_span=[0, len(sentence) * 10])
        self.assertEqual(selected["episode_id"], "SPAN")
        self.assertFalse(selected["entire_document_selected"])
        self.assertGreater(selected["document_units_indexed"], len(selected["scope_units"]))
        self.assertEqual(selected["scope_span"], [0, len(sentence) * 10])
        self.assertTrue(selected["scope_exact_nonwhitespace_coverage"])
        self.assertEqual(json.loads(
            full.editor_request(selected, document)["messages"][1]["content"])["source"],
            sentence * 10)
        with self.assertRaisesRegex(full.FulltextIntakeError,
                                    "FULLTEXT_SCOPE_SPLITS_SENTENCE"):
            full.prepare_fulltext(
                document, source_span=[0, len(sentence) * 10 - 1])

    def test_unpunctuated_long_text_requires_explicit_smaller_scope(self):
        # Source-content presence, not film runtime, governs this gate.
        text = ("无标点测试素材" * 2600)
        with self.assertRaisesRegex(full.FulltextIntakeError,
                                    "FULLTEXT_SELECT_CHAPTER_OR_SHORTER_SCOPE"):
            full.prepare_fulltext(text)

    def test_no_leakage_of_private_text_into_catalog_validation_messages(self):
        new = full.prepare_fulltext("天空很亮。\n\n街上没有人。")
        self.assertEqual(new["document_units_indexed"], len(new["scope_units"]))
        self.assertFalse(new["claims_or_citations_invented"])
        self.assertFalse(new["video_shots_created"])
        self.assertEqual(new["base"]["editorial"]["narration_script"], "")


if __name__ == "__main__":
    unittest.main()
