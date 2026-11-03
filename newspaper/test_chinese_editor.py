"""Chinese copy-editing integration with deterministic transport responses."""
import copy
import json
import unittest
from unittest.mock import Mock
import requests
from chinese_editor import edit_chinese_reports
from edition_budget import EditionBudget


def response(translations):
    r = Mock(status_code=200)
    r.json.return_value = {"choices": [{"finish_reason": "stop", "message": {
        "content": json.dumps({"translations": translations}, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500}}
    return r


class ChineseEditorTests(unittest.TestCase):
    def setUp(self):
        self.article = {"title": "Company reports revenue growth", "title_zh": "公司报告收入增长",
                        "importance_score": 85, "reading_zh": "旧译文",
                        "bilingual_pairs": [
                            {"en": "Revenue rose 5 percent.", "zh": "收入上涨5%。", "paragraph_id": 0},
                            {"en": "The proposal may change costs. It is not approved.",
                             "zh": "提议可能改变成本。尚未获批。", "paragraph_id": 1}]}
        self.translations = [{"id": "title", "zh": "公司营收增长"},
                             {"id": "0", "zh": "公司营收增长5%。"},
                             {"id": "1", "zh": "这项提议可能改变成本，但尚未获批。"}]

    def edit(self, translations=None, **kwargs):
        api = Mock(return_value=response(translations if translations is not None else self.translations))
        result = edit_chinese_reports({"desk": [self.article]}, "dummy", EditionBudget(), transport=api, **kwargs)
        return result["desk"][0], api

    def test_context_edit_keeps_english_and_paragraph_mapping_and_does_not_mutate_input(self):
        before = copy.deepcopy(self.article)
        result, api = self.edit()
        self.assertEqual(self.article, before)
        self.assertEqual(result["chinese_editing_mode"], "context_edited")
        self.assertEqual(result["title_zh"], "公司营收增长")
        self.assertEqual([p["en"] for p in result["bilingual_pairs"]], [p["en"] for p in before["bilingual_pairs"]])
        self.assertEqual([p["paragraph_id"] for p in result["bilingual_pairs"]], [0, 1])
        self.assertIn("\n\n", result["reading_zh"])
        api.assert_called_once()
        self.assertIn("sentences", json.loads(api.call_args.kwargs["json"]["messages"][1]["content"]))

    def test_added_or_missing_number_percent_negation_or_uncertainty_reverts_entire_article(self):
        for identifier, text in (("0", "公司营收增长6%。"), ("0", "公司营收增长5。"),
                                 ("0", "公司营收增长。"), ("1", "这项提议可能改变成本，已经获批。"),
                                 ("1", "这项提议改变成本，但尚未获批。")):
            rows = copy.deepcopy(self.translations)
            next(r for r in rows if r["id"] == identifier)["zh"] = text
            with self.subTest(text=text):
                result, api = self.edit(rows)
                self.assertEqual(result["bilingual_pairs"], self.article["bilingual_pairs"])
                self.assertEqual(result["title_zh"], self.article["title_zh"])
                self.assertEqual(result["chinese_editing_mode"], "mt_fallback")
                self.assertNotEqual(result["chinese_editing_reason"], "ValueError")

    def test_missing_duplicate_unknown_ids_or_invalid_json_are_not_partially_applied(self):
        for rows in (self.translations[:2], [self.translations[0]] * 3,
                     [self.translations[0], self.translations[1], {"id": "99", "zh": "未知"}]):
            result, _ = self.edit(rows)
            self.assertEqual(result["reading_zh"], "旧译文")

    def test_no_credentials_preview_and_chinese_original_never_call_provider(self):
        api = Mock()
        edit_chinese_reports({"desk": [self.article]}, "", None, transport=api)
        edit_chinese_reports({"desk": [{**self.article, "source_language": "zh"}]},
                             "dummy", EditionBudget(), transport=api)
        api.assert_not_called()

    def test_headline_can_use_body_facts_but_not_invent_a_number(self):
        rows = copy.deepcopy(self.translations)
        rows[0]["zh"] = "公司营收增长5%"
        result, _ = self.edit(rows)
        self.assertEqual(result["chinese_editing_mode"], "context_edited")
        rows[0]["zh"] = "公司营收增长9%"
        result, _ = self.edit(rows)
        self.assertEqual(result["chinese_editing_mode"], "mt_fallback")

    def test_budget_reserves_original_commentary_and_stops_before_request(self):
        api = Mock()
        ledger = EditionBudget(cap="0.03")
        result = edit_chinese_reports({"desk": [self.article]}, "dummy", ledger, transport=api)
        api.assert_not_called()
        self.assertEqual(ledger.requests, 0)
        self.assertEqual(result["desk"][0]["reading_zh"], "旧译文")

    def test_timeout_not_retried_and_response_text_not_logged(self):
        api = Mock(side_effect=requests.Timeout("private provider text"))
        ledger = EditionBudget()
        with self.assertLogs("newspaper.chinese_editor") as logs:
            edit_chinese_reports({"desk": [self.article]}, "dummy", ledger, transport=api)
        api.assert_called_once()
        self.assertEqual(ledger.requests, 1)
        self.assertNotIn("private provider text", "".join(logs.output))


if __name__ == "__main__":
    unittest.main()
