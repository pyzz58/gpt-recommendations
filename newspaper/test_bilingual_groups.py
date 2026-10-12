"""User-requested short-group EN/ZH reading layout regression tests."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest


class DemoTranslation:
    def translate(self, text):
        return {
            "How are you? Where are you from?": "你好吗？你来自哪里？",
            "The market rose. Investors remained cautious.": "市场上涨了。投资者仍保持谨慎。",
            "Rates remained unchanged.": "利率维持不变。",
        }.get(text, "中文翻译：" + text)


class BilingualBlockTests(unittest.TestCase):
    def setUp(self):
        self.date = dt.datetime(2026, 10, 11, 8, tzinfo=dt.timezone.utc)
        self.article = {
            "category": "美联储与宏观", "source": "TEST OUTLET",
            "title": "How are you? Where are you from?",
            "date": self.date, "url": "https://example.org/realistic-fixture",
            "reading_en": (
                "How are you? Where are you from?\n\n"
                "The market rose. Investors remained cautious. "
                "Rates remained unchanged."
            ),
            "reading_abbreviated": False,
            "importance_score": 55,
        }

    def test_user_example_is_one_english_group_one_chinese_row(self):
        grouped = digest.group_sentences(["How are you?", "Where are you from?"])
        self.assertEqual(grouped, ["How are you? Where are you from?"])
        result = digest.bilingualize({"美联储与宏观": [self.article]}, DemoTranslation())
        pairs = result["美联储与宏观"][0]["bilingual_pairs"]
        self.assertEqual(pairs[0]["en"], "How are you? Where are you from?")
        self.assertEqual(pairs[0]["zh"], "你好吗？你来自哪里？")
        self.assertEqual(pairs[0]["paragraph_id"], 0)

    def test_short_sentence_groups_preserve_source_and_paragraphs(self):
        result = digest.bilingualize({"美联储与宏观": [self.article]}, DemoTranslation())
        pairs = result["美联储与宏观"][0]["bilingual_pairs"]
        self.assertEqual(len(pairs), 3)  # paragraph 1 one group, paragraph 2 two groups
        self.assertEqual([x["paragraph_id"] for x in pairs], [0, 1, 1])
        self.assertEqual(pairs[1]["en"], "The market rose. Investors remained cautious.")
        self.assertEqual(pairs[1]["zh"], "市场上涨了。投资者仍保持谨慎。")
        self.assertEqual(pairs[2]["en"], "Rates remained unchanged.")

    def test_long_sentence_is_not_cut_or_reordered(self):
        long_sentence = "The central bank " + "was monitoring inflation " * 12 + "throughout the year."
        out = digest.group_sentences([long_sentence, "A second report followed."], max_chars=100)
        self.assertEqual(out, [long_sentence, "A second report followed."])

    def test_user_format_in_html_and_plaintext_email(self):
        grouped = digest.bilingualize({"美联储与宏观": [self.article]}, DemoTranslation())
        html, plaintext = digest.render(grouped, self.date, self.date.date(), {})
        self.assertIn("How are you? Where are you from?\n你好吗？你来自哪里？", plaintext)
        self.assertNotIn("How are you? Where are you from?\n\n你好吗？你来自哪里？", plaintext)
        self.assertLess(html.index("How are you? Where are you from?</div>"), html.index("你好吗？你来自哪里？</div>"))
        self.assertNotIn("今日新闻速览", html)
        self.assertNotIn("重点单词", html)

    def test_grouping_limits_are_configurable(self):
        sentences = ["First event occurred.", "The market reacted.", "Other data followed."]
        self.assertEqual(
            digest.group_sentences(sentences, max_sentences=2, max_chars=180),
            ["First event occurred. The market reacted.", "Other data followed."],
        )
        self.assertEqual(
            digest.group_sentences(sentences, max_sentences=1, max_chars=180),
            sentences,
        )
        with self.assertRaises(ValueError):
            digest.group_sentences(sentences, max_sentences=0)

if __name__ == "__main__":
    unittest.main()
