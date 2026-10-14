"""Regression tests for fixed 06:00 Beijing cutoff and separate 07:00 handoff."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from digest import edition_window, require_live_delivery_window
from prepared_delivery import assert_delivery_window


class DeliveryScheduleTests(unittest.TestCase):
    def setUp(self):
        self.bj = ZoneInfo("Asia/Shanghai")

    def test_edition_window_is_fixed_to_six_am(self):
        start, end, edition = edition_window(
            dt.datetime(2026, 10, 13, 22, 5, tzinfo=dt.timezone.utc))
        self.assertEqual(edition, dt.date(2026, 10, 14))
        self.assertEqual(start, dt.datetime(2026, 10, 13, 6, 0, tzinfo=self.bj))
        self.assertEqual(end, dt.datetime(2026, 10, 14, 6, 0, tzinfo=self.bj))
        self.assertEqual(end-start, dt.timedelta(hours=24))

    def test_late_runner_does_not_shift_cutoff(self):
        start, end, edition = edition_window(
            dt.datetime(2026, 10, 14, 7, 39, tzinfo=self.bj))
        self.assertEqual(start.hour, 6)
        self.assertEqual(end.hour, 6)
        self.assertEqual(edition, dt.date(2026, 10, 14))

    def test_pre_cutoff_edition_is_yesterday(self):
        _, _, edition = edition_window(
            dt.datetime(2026, 10, 14, 5, 59, tzinfo=self.bj))
        self.assertEqual(edition, dt.date(2026, 10, 13))

    def test_prepare_window_rejects_stale_and_early(self):
        end = dt.datetime(2026, 10, 14, 6, 0, tzinfo=self.bj)
        for minute in (0, 5, 20, 61, 119):
            require_live_delivery_window(end+dt.timedelta(minutes=minute), end)
        for minute in (-1, 120, 250):
            with self.assertRaises(RuntimeError):
                require_live_delivery_window(end+dt.timedelta(minutes=minute), end)

    def test_send_boundary_and_wrong_date(self):
        edition = dt.date(2026, 10, 14)
        for minute in (0, 1, 17, 47, 59):
            assert_delivery_window(dt.datetime(2026, 10, 14, 7, minute, tzinfo=self.bj), edition)
        for when in (
            dt.datetime(2026, 10, 14, 6, 59, tzinfo=self.bj),
            dt.datetime(2026, 10, 14, 8, 0, tzinfo=self.bj),
            dt.datetime(2026, 10, 15, 7, 10, tzinfo=self.bj),
        ):
            with self.subTest(when=when), self.assertRaises(RuntimeError):
                assert_delivery_window(when, edition)

    def test_timezone_aware_only(self):
        with self.assertRaises(ValueError):
            edition_window(dt.datetime(2026, 10, 14, 6, 0))
        with self.assertRaises(ValueError):
            assert_delivery_window(dt.datetime(2026, 10, 14, 7, 1), dt.date(2026,10,14))


if __name__ == "__main__":
    unittest.main()
