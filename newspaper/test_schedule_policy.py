"""P0: daily 00:00 cutoff, start at 00:01, hand off as soon as PDF is verified."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from production_policy import POLICY, BEIJING, edition_window, subject, check_send_window, check_preparation_window
from schedule_contract import choose_phase
from verify_schedule import verify,list_workflow_crons


class CanonicalSchedulePolicyTests(unittest.TestCase):
    def setUp(self):
        self.day=dt.date(2026,10,15)

    def test_workflow_cron_equals_canonical_json_exactly(self):
        self.assertTrue(verify())
        self.assertEqual(list_workflow_crons(),
            [POLICY["startup_cron_utc"]])

    def test_midnight_start_and_immediate_send(self):
        self.assertEqual(POLICY["scheduled_delivery_bjt"],"00:01")
        self.assertEqual(POLICY["cutoff_bjt"],"00:00")
        self.assertEqual(POLICY["startup_cron_utc"],"1 16 * * *")
        self.assertIn("00:00截稿",subject(self.day))

    def test_news_window_crosses_midnight(self):
        start,end,day=edition_window(dt.datetime(2026,10,15,0,15,tzinfo=BEIJING))
        self.assertEqual(day,self.day)
        self.assertEqual(start,dt.datetime(2026,10,14,0,0,tzinfo=BEIJING))
        self.assertEqual(end,dt.datetime(2026,10,15,0,0,tzinfo=BEIJING))

    def test_unknown_schedule_is_not_silently_sent(self):
        with self.assertRaises(RuntimeError):
            choose_phase("schedule","5 22 * * *","",dt.datetime(2026,10,15,1,2,tzinfo=BEIJING))

    def test_one_scheduled_start_generates_then_sends_when_ready(self):
        cron=POLICY["startup_cron_utc"]
        for hour,minute in ((0,1),(0,59),(4,15)):
            clock=dt.datetime(2026,10,15,hour,minute,tzinfo=BEIJING)
            self.assertEqual(choose_phase("schedule",cron,"",clock),"send")

    def test_preview_never_sends_and_manual_send_honors_time_guard(self):
        t=dt.datetime(2026,10,15,1,2,tzinfo=BEIJING)
        self.assertEqual(choose_phase("pull_request","","",t),"preview")
        self.assertEqual(choose_phase("workflow_dispatch","","true",t),"preview")
        self.assertEqual(choose_phase("workflow_dispatch","","false",t),"send")

    def test_preparation_same_day_allows_late_recovery(self):
        end=dt.datetime(2026,10,15,0,0,tzinfo=BEIJING)
        for hour in (0,1,4,12,23):
            check_preparation_window(end+dt.timedelta(hours=hour),end)
        for when in (end-dt.timedelta(seconds=1),end+dt.timedelta(days=1)):
            with self.assertRaises(RuntimeError):
                check_preparation_window(when,end)

    def test_immediate_send_and_same_day_late_recovery(self):
        for t in (dt.time(0,1),dt.time(0,30),dt.time(1,0),dt.time(4,8),dt.time(23,59)):
            check_send_window(dt.datetime.combine(self.day,t,tzinfo=BEIJING),self.day)
        for now in (dt.datetime(2026,10,14,23,59,tzinfo=BEIJING),
                    dt.datetime(2026,10,16,1,3,tzinfo=BEIJING)):
            with self.subTest(now=now),self.assertRaises(RuntimeError):
                check_send_window(now,self.day)

if __name__=="__main__":
    unittest.main()
