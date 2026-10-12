"""Regression: no more jump-cut paragraphs or misleadingly short long reads."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reader


class CoherentLongformTests(unittest.TestCase):
    def test_long_read_uses_only_adjacent_complete_paragraphs(self):
        paragraphs = [
            "First: " + "what happened. " * 65,
            "Second: " + "the background. " * 65,
            "Third: " + "market effects. " * 65,
            "Fourth: " + "after this. " * 65,
            "Fifth: " + "older background. " * 65,
        ]
        limit = len(paragraphs[0]) + 2 + len(paragraphs[1]) + 20
        selected, abbreviated = reader._long_read(paragraphs, limit)
        self.assertTrue(abbreviated)
        self.assertEqual(selected, "\n\n".join(paragraphs[:2]))
        self.assertNotIn("Third:", selected)
        self.assertNotIn("Fifth:", selected)

    def test_full_accessible_article_is_not_arbitrarily_truncated(self):
        paragraphs = ["Intro " + "detail " * 100, "Body " + "evidence " * 80]
        selected, abbreviated = reader._long_read(paragraphs, 9000)
        self.assertFalse(abbreviated)
        self.assertEqual(selected, "\n\n".join(paragraphs))

    def test_splits_exceptional_one_paragraph_only_at_complete_sentences(self):
        full = "The central bank announced its decision. " * 30
        selected, abbreviated = reader._long_read([full], 175)
        self.assertTrue(abbreviated)
        self.assertTrue(selected.endswith("."))
        self.assertLessEqual(len(selected), 175)
        self.assertFalse("decision. The central bank annou" == selected[-36:])

    def test_oversize_single_sentence_is_skipped(self):
        selected, abbreviated = reader._long_read(["Unbroken sentence " * 50], 150)
        self.assertTrue(abbreviated)
        self.assertEqual(selected, "")

    def test_article_skipped_when_no_coherent_minimum(self):
        response = MagicMock()
        response.headers = {"Content-Type": "text/html"}
        response.text = "<html><body>stub</body></html>"
        response.raise_for_status.return_value = None
        source_text = (
            "First: " + "A" * 1050 + "\n"
            + "Second: " + "B" * 1050 + "\n"
            + "Third: " + "C" * 1050
        )
        article = {"url": "https://example.org/news/1", "title": "Headline"}
        with patch.object(reader.requests, "get", return_value=response), \
             patch.object(reader.trafilatura, "extract", return_value=source_text):
            result = reader.fetch_reading(article, min_chars=1400, max_chars=1600)
        self.assertIsNone(result)

    def test_article_good_length_and_metadata(self):
        response = MagicMock()
        response.headers = {"Content-Type": "text/html; charset=UTF-8"}
        response.text = "<article>dummy</article>"
        response.raise_for_status.return_value = None
        paragraphs = [
            "First: " + "Economic event. " * 110,
            "Second: " + "Background from yesterday. " * 70,
            "Third: " + "Longer-run uncertainty. " * 80,
        ]
        article = {"url": "https://example.org/news/2", "title": "Headline"}
        with patch.object(reader.requests, "get", return_value=response), \
             patch.object(reader.trafilatura, "extract", return_value="\n".join(paragraphs)):
            result = reader.fetch_reading(article, min_chars=1400, max_chars=4000)
        self.assertIsNotNone(result)
        self.assertEqual(result["reading_selection"], "consecutive_from_lead")
        self.assertTrue(result["reading_abbreviated"])
        self.assertIn("First:", result["reading_en"])
        self.assertIn("Second:", result["reading_en"])
        self.assertNotIn("Third:", result["reading_en"])
        self.assertGreaterEqual(result["reading_chars"], 1400)

    def test_longform_configuration_prefers_fewer_complete_items(self):
        config = json.loads((Path(__file__).parent / "feeds.json").read_text())
        self.assertGreaterEqual(config["longread_min_chars"], 1200)
        self.assertGreaterEqual(config["longread_max_chars"], 5000)
        self.assertLessEqual(sum(config["max_per_category"].values()), 16)


if __name__ == "__main__":
    unittest.main()
