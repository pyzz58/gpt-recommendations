"""Acceptance test: one English sentence then one matching Chinese line, never grouped."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest

class Translation:
    def translate(self, text):
        dictionary = {
            "Where are you from?": "你来自哪里？",
            "Are you OK?": "你好吗？",
            "Nice to see you.": "很高兴见到你。",
        }
        return dictionary.get(text, "测试标题翻译")

class ExactLineFormatTests(unittest.TestCase):
    def test_every_sentence_has_its_own_adjacent_chinese_line(self):
        when = dt.datetime(2026, 10, 11, tzinfo=dt.timezone.utc)
        article = {
            "category": "全球新闻", "title": "Sample", "source": "Fixture",
            "url": "https://example.org/fixture", "date": when,
            "reading_en": "Where are you from? Are you OK? Nice to see you.",
            "reading_abbreviated": False, "grammar_lessons": [],
            "importance_score": 0,
        }
        grouped = digest.bilingualize({"全球新闻": [article]}, Translation())
        units = grouped["全球新闻"][0]["bilingual_pairs"]
        self.assertEqual([p["en"] for p in units], [
            "Where are you from?", "Are you OK?", "Nice to see you."
        ])
        self.assertEqual([p["zh"] for p in units], [
            "你来自哪里？", "你好吗？", "很高兴见到你。"
        ])
        html, plain = digest.render(grouped, when, when.date(), {})
        expected = ("Where are you from?\n你来自哪里？\n\n"
                    "Are you OK?\n你好吗？\n\n"
                    "Nice to see you.\n很高兴见到你。")
        # Plain text uses paragraph separators *between* pairs but never
        # between an English line and its own Chinese translation.
        self.assertIn(expected, plain)
        self.assertNotIn("Where are you from? Are you OK?", plain)
        self.assertNotIn("Are you OK? Nice to see you.", plain)
        self.assertIn("Where are you from?</div>", html)
        self.assertIn("你来自哪里？</div>", html)
        self.assertIn("Are you OK?</div>", html)
        self.assertIn("你好吗？</div>", html)

if __name__ == "__main__":
    unittest.main()
