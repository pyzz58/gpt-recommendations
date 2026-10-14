"""No drift permitted between canonical policy, UTC cron, and Python behavior."""
import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from production_policy import POLICY,BEIJING,edition_window,subject,check_send_window
from schedule_contract import choose_phase
from verify_schedule import verify,list_workflow_crons


class CanonicalSchedulePolicyTests(unittest.TestCase):
    def setUp(self):
        self.day=dt.date(2026,10,15)

    def test_workflow_cron_equals_canonical_json_exactly(self):
        self.assertTrue(verify())
        self.assertEqual(list_workflow_crons(),
            POLICY["prepare_crons_utc"]+POLICY["send_crons_utc"])

    def test_first_dispatch_is_beijing_one_am(self):
        self.assertEqual(POLICY["scheduled_delivery_bjt"],"01:00")
        self.assertEqual(POLICY["cutoff_bjt"],"00:00")
        self.assertEqual(POLICY["send_crons_utc"][0],"3 17 * * *")
        self.assertIn("00:00截稿",subject(self.day))

    def test_news_window_crosses_midnight(self):
        start,end,day=edition_window(dt.datetime(2026,10,15,0,15,tzinfo=BEIJING))
        self.assertEqual(day,self.day)
        self.assertEqual(start,dt.datetime(2026,10,14,0,0,tzinfo=BEIJING))
        self.assertEqual(end,dt.datetime(2026,10,15,0,0,tzinfo=BEIJING))

    def test_old_schedule_is_not_silently_sent(self):
        with self.assertRaises(RuntimeError):
            choose_phase("schedule","5 22 * * *","",dt.datetime(2026,10,15,1,2,tzinfo=BEIJING))

    def test_preparation_and_late_conversion(self):
        early=dt.datetime(2026,10,15,0,15,tzinfo=BEIJING)
        late=dt.datetime(2026,10,15,1,15,tzinfo=BEIJING)
        self.assertEqual(choose_phase("schedule",POLICY["prepare_crons_utc"][0],"",early),"prepare")
        self.assertEqual(choose_phase("schedule",POLICY["prepare_crons_utc"][0],"",late),"send")
        self.assertEqual(choose_phase("schedule",POLICY["send_crons_utc"][0],"",late),"send")

    def test_preview_never_sends(self):
        t=dt.datetime(2026,10,15,1,2,tzinfo=BEIJING)
        self.assertEqual(choose_phase("pull_request","","",t),"preview")
        self.assertEqual(choose_phase("workflow_dispatch","","true",t),"preview")

    def test_hard_send_window(self):
        check_send_window(dt.datetime(2026,10,15,1,3,tzinfo=BEIJING),self.day)
        for now in (dt.datetime(2026,10,15,0,59,tzinfo=BEIJING),
                    dt.datetime(2026,10,15,2,0,tzinfo=BEIJING),
                    dt.datetime(2026,10,16,1,3,tzinfo=BEIJING)):
            with self.subTest(now=now),self.assertRaises(RuntimeError):
                check_send_window(now,self.day)


if __name__=="__main__":
    unittest.main()
