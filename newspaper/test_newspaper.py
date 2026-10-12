"""Offline unit tests for newspaper scheduling, dedup and fallback behavior."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import digest
import reader

class NewspaperTests(unittest.TestCase):
    def setUp(self):
        self.tz = digest.ZoneInfo("Asia/Shanghai")
        self.start = dt.datetime(2026, 10, 11, 0, 0, tzinfo=self.tz)
        self.end = self.start + dt.timedelta(days=1)

    def test_yesterday_window_uses_beijing_local_day(self):
        # UTC 2026-10-10 16:00 becomes Beijing Oct 11 00:00.
        valid = dt.datetime(2026, 10, 10, 16, 0, tzinfo=dt.timezone.utc)
        self.assertTrue(self.start <= valid.astimezone(self.tz) < self.end)
        # Beijing October 12 at 00:00 belongs to the next edition.
        invalid = dt.datetime(2026, 10, 11, 16, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(self.start <= invalid.astimezone(self.tz) < self.end)

    def test_extract_fallback_skips_unreadable_and_selects_accessible(self):
        items = [
            {"title": "Headline about markets one", "url": "https://example.com/blocked",
             "source": "Blocked", "category": "美股与投资", "date": self.start},
            {"title": "Headline about markets two", "url": "https://example.com/open",
             "source": "Open", "category": "美股与投资", "date": self.start},
        ]
        def fake_fetch(item, *args):
            if "blocked" in item["url"]:
                return None
            return {**item, "reading_en": "Article with context", "reading_abbreviated": True}
        with patch.object(digest, "fetch_reading", side_effect=fake_fetch):
            out, diag = digest.build_readings(
                {"美股与投资": items},
                {"longread_min_chars": 10, "longread_max_chars": 200,
                 "max_per_category": {"美股与投资": 1}, "source_limit_per_category": 2},
            )
        self.assertEqual(out["美股与投资"][0]["source"], "Open")
        self.assertEqual(diag["美股与投资"]["selected"], 1)

    def test_reading_excerpt_is_not_claimed_as_full_article(self):
        text, abbreviated = reader._long_read([
            "first paragraph " * 40, "middle paragraph " * 40, "last paragraph " * 40
        ], 400)
        self.assertTrue(abbreviated)
        self.assertLessEqual(len(text), 400)

    def test_no_external_api_in_preview(self):
        fixture = {
          "全球新闻": [{
            "category": "全球新闻", "source": "DEMO",
            "title": "Market headline", "title_zh": "市场标题",
            "reading_en": "English article text", "reading_zh": "中文报道正文",
            "reading_abbreviated": True,
            "url": "https://example.com", "date": self.start
          }]
        }
        html, plain = digest.render(fixture, self.start, self.start.date(), {})
        self.assertIn("中文报道正文", html)
        self.assertIn("English article text", html)
        self.assertIn("2026-10-11", plain)

if __name__ == "__main__":
    unittest.main()
