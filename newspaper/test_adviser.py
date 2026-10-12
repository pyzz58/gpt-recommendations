"""Global Adviser regression tests: no highlights/glossary, interleaved exact pairs."""
import datetime as dt
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adviser
import digest
from english_lessons import attach_lessons


class FakeTranslation:
    def translate(self, text):
        return "中文译文：" + text


class TestGlobalAdviser(unittest.TestCase):
    def setUp(self):
        self.date = dt.datetime(2026, 10, 11, 7, tzinfo=dt.timezone.utc)
        self.article = {
            "category": "美联储与宏观",
            "title": "Central bank reports latest inflation outlook",
            "summary": "The central bank said the economy has slowed.",
            "source": "Central bank", "url": "https://example.com/report",
            "date": self.date, "reading_abbreviated": True,
            "reading_en": (
                "The central bank has maintained interest rates throughout the year. "
                "A new report was published after the policy meeting.\n\n"
                "Officials say that future decisions will depend on inflation."
            ),
            "importance_score": 72, "related_sources": ["Central bank"],
        }

    def test_bilingual_sentences_alternate_strictly(self):
        report = digest.bilingualize({"美联储与宏观": [self.article]}, FakeTranslation())
        a = report["美联储与宏观"][0]
        pairs = a["bilingual_pairs"]
        self.assertGreaterEqual(len(pairs), 3)
        self.assertTrue(all(p["zh"] == "中文译文:" + p["en"] for p in pairs))
        self.assertEqual(pairs[0]["paragraph_id"], 0)
        self.assertEqual(pairs[-1]["paragraph_id"], 1)
        html, txt = digest.render(report, self.date, self.date.date(), {})
        # Every English line is directly followed by Chinese, including in TXT.
        for pair in pairs:
            self.assertIn(pair["en"] + "\n\n" + pair["zh"], txt)
            self.assertLess(html.index(pair["en"]), html.index("中文译文:" + pair["en"]))
        self.assertNotIn("今日重点", html)
        self.assertNotIn("今日新闻速览", html)
        self.assertNotIn("Vocabulary", html)
        self.assertNotIn("本篇词汇", txt)

    def test_domain_analysis_is_evidence_limited(self):
        note = adviser.domain_advice("美联储与宏观", [self.article])
        self.assertIn("1篇", note["situation"])
        self.assertIn("1个", note["situation"])
        self.assertIn("采集样本", note["situation"])
        story = adviser.article_advice(self.article)
        self.assertIn("72/100", story["uncertainty"])
        self.assertIn("单个来源", story["uncertainty"])

    def test_empty_domain_does_not_claim_nothing_happened(self):
        html, text = digest.render({"AI与科技": []}, self.date, self.date.date(), {})
        self.assertIn("不表示该领域无事发生", html)
        self.assertIn("不作当天局势判断", text)

    def test_cross_domain_connections_are_scenarios_not_claimed_events(self):
        groups = {"美联储与宏观": [self.article], "美股与投资": [self.article]}
        scenario = adviser.global_linkages(groups)
        self.assertTrue(scenario)
        self.assertIn("不能", scenario[0]["caution"])

    def test_english_lessons_keep_grammar_only(self):
        groups = digest.bilingualize({"美联储与宏观": [self.article]}, FakeTranslation())
        with_grammar = attach_lessons(groups, FakeTranslation(), grammar_limit=2, vocab_limit=0)
        a = with_grammar["美联储与宏观"][0]
        self.assertEqual(a["vocabulary"], [])
        self.assertTrue(all(x["sentence_en"] in self.article["reading_en"]
                            for x in a["grammar_lessons"]))

    def test_one_sentence_quote_is_never_split_into_unrelated_translation(self):
        source = dict(self.article)
        source["reading_en"] = (
            "The company announced plans to expand. "
            "It said the policy could affect the market."
        )
        res = digest.bilingualize({"美股与投资": [source]}, FakeTranslation())
        pairs = res["美股与投资"][0]["bilingual_pairs"]
        self.assertEqual(len(pairs), 2)
        self.assertEqual(
            [x["en"] for x in pairs],
            ["The company announced plans to expand.",
             "It said the policy could affect the market."],
        )


if __name__ == "__main__":
    unittest.main()
