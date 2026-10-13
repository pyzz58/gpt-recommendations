"""Machine-translation headline quality regression using real sample failure modes."""
import datetime as dt
import unittest
from translation_editor import polish_news_title
from editorial_quality import edition_quality_report
from clippings import build_clippings_html


class HeadlineQualityTests(unittest.TestCase):
    def test_obviously_truncated_machine_translation_uses_original(self):
        source = "Microsoft president says UK is best placed to drive AI regulation"
        result, flags = polish_news_title(source, "微软总裁说,")
        self.assertEqual(result, source)
        self.assertIn("title_translation_ends_mid_clause", flags)

    def test_valid_chinese_headline_stays_as_chinese(self):
        source = "The Federal Reserve announces new interest rate decision"
        result, flags = polish_news_title(source, "美联储宣布新的利率决定")
        self.assertEqual(result, "美联储宣布新的利率决定")
        self.assertEqual(flags, [])

    def test_very_low_chinese_content_does_not_disguise_machine_garbage(self):
        original = "European markets react to new inflation figures"
        title, flags = polish_news_title(original, "Zelenskyy reports")
        self.assertEqual(title, original)
        self.assertIn("title_translation_too_little_chinese", flags)

    def test_fallback_note_and_editorial_audit(self):
        source = "Microsoft president says UK is best placed to drive AI regulation"
        item = {
            "title": source, "title_zh": source,
            "title_qa_flags": ["title_translation_ends_mid_clause"],
            "source": "Verified Newspaper",
            "url": "https://example.org/story",
            "date": dt.datetime(2026, 10, 13, tzinfo=dt.timezone.utc),
            "reading_en": "This is a clearly sourced full text. " * 30,
            "bilingual_pairs": [{"en": "The company issued a statement.",
                                "zh": "公司发表了一项声明。", "paragraph_id": 0}],
        }
        data = {"AI与数字产业": [item]}
        audit = edition_quality_report(data)
        self.assertEqual(len(audit["title_translation_alerts"]), 1)
        self.assertIn("machine_translated_titles_need_review", audit["warnings"])
        html, _ = build_clippings_html(data, dt.date(2026, 10, 13))
        self.assertIn("中文机译标题疑似残缺", html)
        self.assertIn(source, html)


if __name__ == "__main__":
    unittest.main()
