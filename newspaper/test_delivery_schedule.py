"""P0 edition-date integrity across late GitHub cron and SMTP handoff."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parent))
from digest import edition_window, require_live_delivery_window
from prepared_delivery import assert_delivery_window


class DeliveryScheduleTests(unittest.TestCase):
    def setUp(self): self.bj=ZoneInfo("Asia/Shanghai")

    def test_cutoff_is_beijing_midnight(self):
        start,end,edition=edition_window(dt.datetime(2026,10,13,16,5,tzinfo=dt.timezone.utc))
        self.assertEqual(edition,dt.date(2026,10,14))
        self.assertEqual(start,dt.datetime(2026,10,13,0,0,tzinfo=self.bj))
        self.assertEqual(end,dt.datetime(2026,10,14,0,0,tzinfo=self.bj))
        self.assertEqual(end-start,dt.timedelta(days=1))

    def test_late_runner_does_not_change_source_window(self):
        start,end,edition=edition_window(dt.datetime(2026,10,14,4,39,tzinfo=self.bj))
        self.assertEqual((start.hour,end.hour,edition),(0,0,dt.date(2026,10,14)))

    def test_previous_day_stays_previous_before_cutoff(self):
        _,_,edition=edition_window(dt.datetime(2026,10,13,23,59,tzinfo=self.bj))
        self.assertEqual(edition,dt.date(2026,10,13))

    def test_late_same_day_preparation_allowed(self):
        end=dt.datetime(2026,10,14,0,0,tzinfo=self.bj)
        for minute in (0,5,20,61,119,250,1400):
            require_live_delivery_window(end+dt.timedelta(minutes=minute),end)
        for minute in (-1,1440):
            with self.assertRaises(RuntimeError):
                require_live_delivery_window(end+dt.timedelta(minutes=minute),end)

    def test_email_never_before_one_am_and_no_next_date(self):
        edition=dt.date(2026,10,14)
        for t in (dt.time(1,0),dt.time(1,47),dt.time(4,0),dt.time(23,59)):
            assert_delivery_window(dt.datetime.combine(edition,t,tzinfo=self.bj),edition)
        for when in (
            dt.datetime(2026,10,14,0,1,tzinfo=self.bj),
            dt.datetime(2026,10,14,0,59,tzinfo=self.bj),
            dt.datetime(2026,10,15,1,10,tzinfo=self.bj),
        ):
            with self.subTest(when=when),self.assertRaises(RuntimeError):
                assert_delivery_window(when,edition)

    def test_naive_clock_not_allowed(self):
        with self.assertRaises(ValueError):
            edition_window(dt.datetime(2026,10,14,0,0))
        with self.assertRaises(ValueError):
            assert_delivery_window(dt.datetime(2026,10,14,1,1),dt.date(2026,10,14))
if __name__=="__main__":
    unittest.main()
