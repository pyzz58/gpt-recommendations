"""Regression coverage for transparent editorial ranking and attested English lessons."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ranking
import english_lessons as lessons
import digest


class EditorAndEnglishTests(unittest.TestCase):
    def setUp(self):
        self.start = dt.datetime(2026, 10, 11, tzinfo=dt.timezone.utc)

    def item(self, title: str, source: str, category: str, index: int):
        return {
            "title": title, "source": source, "category": category,
            "date": self.start + dt.timedelta(hours=12),
            "url": f"https://news.example/{index}",
            "summary": title,
        }

    def test_related_reporters_form_one_event_with_audit_signal(self):
        articles = [
            self.item(
                "Federal Reserve signals possible rate cuts after new inflation data",
                "Outlet A", "美联储与宏观", 1,
            ),
            self.item(
                "Federal Reserve signals possible rate cuts after new inflation data in statement",
                "Outlet B", "美联储与宏观", 2,
            ),
            self.item(
                "Startup launches new satellite manufacturing platform for research",
                "Outlet C", "美联储与宏观", 3,
            ),
        ]
        ranked = ranking.rank_and_pool(articles, pool_size=3, news_start=self.start)
        fed = [a for a in ranked if "Federal Reserve" in a["title"]]
        self.assertEqual(len(fed), 2)
        self.assertEqual(fed[0]["story_id"], fed[1]["story_id"])
        self.assertEqual(fed[0]["related_sources"], ["Outlet A", "Outlet B"])
        self.assertIn("不代表事实核验", fed[0]["why_recommended"])
        self.assertTrue(all(0 <= a["importance_score"] <= 100 for a in ranked))

    def test_duplicate_url_across_feeds_is_one_candidate(self):
        a = self.item("Fed announces rate decision following policy meeting", "Outlet A", "美联储与宏观", 1)
        result = ranking.rank_and_pool([a, dict(a)], pool_size=6, news_start=self.start)
        self.assertEqual(len(result), 1)

    def test_recommendation_keywords_not_sole_measure(self):
        noimpact = self.item("A local exhibition opens to the public", "A", "全球新闻", 1)
        policy = self.item("Federal Reserve announces policy rate cut after inflation report", "B", "全球新闻", 2)
        self.assertGreater(
            ranking._score(policy, 1, self.start)[0],
            ranking._score(noimpact, 1, self.start)[0]
        )

    def test_article_words_must_appear_in_source(self):
        article = (
            "The Federal Reserve discussed inflation and the monetary policy "
            "outlook while investors assessed quarterly earnings."
        )
        found = lessons._pick_vocab(article, None, maximum=5)
        self.assertTrue(found)
        for entry in found:
            self.assertIn(entry["word"].lower(), article.lower())
        self.assertFalse(any(e["word"] == "diplomacy" for e in found))

    def test_grammar_sentences_from_real_text(self):
        text = (
            "The central bank has maintained its policy rate throughout the year. "
            "The decision was announced after the meeting concluded. "
            "If inflation falls further, policymakers may reduce borrowing costs. "
            "Officials who were present at the meeting discussed the risks."
        )
        nlp = lessons.english_parser()
        examples = lessons._pick_grammar(text, nlp, count=3)
        self.assertGreaterEqual(len(examples), 2)
        self.assertLessEqual(len(examples), 3)
        self.assertEqual(len(set(x["type"] for x in examples)), len(examples))
        for e in examples:
            self.assertIn(e["sentence_en"], text)
            self.assertIn(e["type"], lessons.EXPLANATIONS)

    def test_render_places_lessons_after_article_and_shows_score(self):
        article = {
            "category": "美股与投资", "source": "DEMO",
            "title": "Stocks rose after policy announcement",
            "title_zh": "政策公布后股市上涨",
            "reading_en": "Stocks rose after a new policy was announced.",
            "reading_zh": "新政策公布后股市上涨。",
            "reading_abbreviated": False,
            "date": self.start, "url": "https://example.org/story",
            "importance_score": 85, "why_recommended": "包含宏观事件线索",
            "vocabulary": [{"word": "policy", "definition": "政策"}],
            "grammar_lessons": [{
                "type": "passive", "title": "被动语态 · Passive Voice",
                "sentence_en": "Stocks rose after a new policy was announced.",
                "sentence_zh": "新政策公布后股市上涨。",
                "pattern": "be + 过去分词",
                "explanation": "强调动作的承受者。",
            }],
        }
        html, plain = digest.render({"美股与投资": [article]}, self.start, self.start.date(), {})
        self.assertLess(html.index("Sentence-by-sentence bilingual reading"), html.index("Grammar Focus · 本篇语法"))
        self.assertLess(plain.index("【事实材料：一句英文紧跟一句中文】"), plain.index("【本篇语法】"))
        self.assertNotIn("今日重点", html)
        self.assertNotIn("Vocabulary · 词汇", html)
        self.assertIn("85/100", html)
        self.assertIn("被动语态", html)
        self.assertIn("新政策公布后股市上涨", html)


if __name__ == "__main__":
    unittest.main()
