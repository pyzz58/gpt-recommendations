"""Regression tests for the 01:00 Beijing rolling-window newspaper contract."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from digest import edition_window, require_live_delivery_window


class DeliveryScheduleTests(unittest.TestCase):
    def setUp(self):
        self.bj = ZoneInfo("Asia/Shanghai")

    def test_cutoff_exact_24_hour_window(self):
        start, end, edition = edition_window(
            dt.datetime(2026, 10, 13, 17, 0, tzinfo=dt.timezone.utc)
        )
        self.assertEqual(edition, dt.date(2026, 10, 14))
        self.assertEqual(start, dt.datetime(2026, 10, 13, 1, 0, tzinfo=self.bj))
        self.assertEqual(end, dt.datetime(2026, 10, 14, 1, 0, tzinfo=self.bj))
        self.assertEqual(end - start, dt.timedelta(hours=24))

    def test_delayed_runner_does_not_shift_news_cutoff(self):
        start, end, edition = edition_window(
            dt.datetime(2026, 10, 14, 1, 39, tzinfo=self.bj)
        )
        self.assertEqual(start, dt.datetime(2026, 10, 13, 1, 0, tzinfo=self.bj))
        self.assertEqual(end, dt.datetime(2026, 10, 14, 1, 0, tzinfo=self.bj))
        self.assertEqual(edition, dt.date(2026, 10, 14))

    def test_before_one_am_is_preceding_edition_and_cannot_send(self):
        start, end, edition = edition_window(
            dt.datetime(2026, 10, 14, 0, 59, tzinfo=self.bj)
        )
        self.assertEqual(edition, dt.date(2026, 10, 13))
        with self.assertRaises(RuntimeError):
            require_live_delivery_window(
                dt.datetime(2026, 10, 14, 0, 59, tzinfo=self.bj), end
            )

    def test_send_window_boundaries_and_timeout(self):
        end = dt.datetime(2026, 10, 14, 1, 0, tzinfo=self.bj)
        for minute in (0, 10, 20, 56):
            require_live_delivery_window(end + dt.timedelta(minutes=minute), end)
        for when in (
            end - dt.timedelta(seconds=1),
            end + dt.timedelta(minutes=57),
            end + dt.timedelta(hours=1),
            end + dt.timedelta(hours=10),
        ):
            with self.subTest(when=when), self.assertRaises(RuntimeError):
                require_live_delivery_window(when, end)

    def test_timezone_aware_only(self):
        with self.assertRaises(ValueError):
            edition_window(dt.datetime(2026, 10, 14, 1, 0))
        with self.assertRaises(ValueError):
            require_live_delivery_window(
                dt.datetime(2026, 10, 14, 1, 1),
                dt.datetime(2026, 10, 14, 1, 0, tzinfo=self.bj),
            )


if __name__ == "__main__":
    unittest.main()
