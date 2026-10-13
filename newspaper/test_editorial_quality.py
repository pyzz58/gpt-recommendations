"""Editorial output counts are derived from articles that render in the PDF."""
import datetime as dt
import unittest
from editorial_quality import edition_quality_report


class EditionQualityTests(unittest.TestCase):
    def test_printable_vs_selected_and_missing_evidence(self):
        common = {
            "title": "Fed policy publication", "title_zh": "美联储政策公告",
            "source": "Federal Reserve", "date": dt.datetime(2026, 10, 12),
            "reading_en": "Grounded, detailed, publicly verifiable reporting. " * 20,
            "bilingual_pairs": [{"en": "A sourced sentence.", "zh": "有来源的一句话。"}],
        }
        grouped = {
            "美股·全球金融市场": [
                {**common, "url": "https://example.com/1", "event_key": "e1"},
                {**common, "url": "https://example.com/2", "event_key": "e1"},
                {**common, "url": "https://example.com/3",
                 "event_key": "e3", "bilingual_pairs": []},
            ],
            "中国与美国": [],
        }
        out = edition_quality_report(grouped, expected_min=2)
        self.assertEqual(out["selected_articles"], 3)
        self.assertEqual(out["printable_articles"], 2)
        self.assertEqual(len(out["omitted"]), 1)
        self.assertEqual(len(out["possible_duplicates"]), 1)
        self.assertEqual(out["by_section"]["中国与美国"]["printable"], 0)
        self.assertIn("possible_duplicate_published_events", out["warnings"])
        self.assertNotIn("below_usual_edition_volume_no_padding", out["warnings"])

    def test_short_missing_source_is_flagged_without_fabricating(self):
        grouped = {"国际政治与全球事件": [{
            "title": "Story", "bilingual_pairs": [{"zh": "中文事实。", "en": ""}],
            "reading_zh": "中文事实。", "source": "Source",
        }]}
        out = edition_quality_report(grouped)
        self.assertEqual(out["printable_articles"], 1)
        self.assertEqual(len(out["metadata_gaps"]), 1)
        self.assertEqual(len(out["short_article_candidates"]), 1)
        self.assertIn("below_usual_edition_volume_no_padding", out["warnings"])


if __name__ == "__main__":
    unittest.main()
