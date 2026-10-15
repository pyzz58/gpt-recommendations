"""P0 scheduler proof constraints: independent and strictly non-sending."""
import datetime as dt
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent.parent
WORKFLOW=ROOT/".github/workflows/newspaper.yml"
PROBE=ROOT/".github/workflows/newspaper-schedule-probe.yml"
POLICY=ROOT/"newspaper/production_policy.json"


class TriggerProofTests(unittest.TestCase):
    def test_probe_is_separate_and_cannot_send_mail_or_pay_for_generation(self):
        text=PROBE.read_text(encoding="utf-8")
        self.assertIn("name: Newspaper - Schedule Trigger Probe",text)
        self.assertIn("cron: '37 * * * *'",text)
        self.assertIn("NEWSPAPER_CRON_REAL_EVENT=true",text)
        self.assertIn("NEWSPAPER_CRON_REAL_EVENT=false",text)
        self.assertIn("schedule_probe_marker.txt",text)
        self.assertIn("timeout-minutes: 2",text)
        self.assertIn("contents: read",text)
        self.assertIn("actions: read",text)
        self.assertIn("NEWSPAPER_MAIN_WORKFLOW_STATE=",text)
        self.assertIn("api.github.com/repos/",text)
        self.assertNotIn("method=\"POST\"",text)
        self.assertNotIn("contents: write",text)
        forbidden=["send_email","send_bundle","prepared_delivery.py",
                   "SMTP_PASSWORD","NEWSPAPER_TO","secrets.","workflow_call",
                   "smtp.qq.com","NEWSPAPER_LLM_API_KEY"]
        for word in forbidden:
            with self.subTest(word=word):
                self.assertNotIn(word,text)
        self.assertNotIn("schedule_probe_marker.txt",
            WORKFLOW.read_text(encoding="utf-8"))

    def test_all_configured_crons_map_to_correct_beijing_date(self):
        import json
        cfg=json.loads(POLICY.read_text(encoding="utf-8"))
        workflow=WORKFLOW.read_text(encoding="utf-8")
        expected=cfg["prepare_crons_utc"]+cfg["send_crons_utc"]
        self.assertEqual(len(expected),9)
        for idx,cron in enumerate(expected):
            with self.subTest(cron=cron):
                self.assertIn(f"cron: '{cron}'",workflow)
                minute,hour,_,_,_=cron.split()
                utc=dt.datetime(2026,10,14,int(hour),int(minute),
                                tzinfo=dt.timezone.utc)
                beijing=utc.astimezone(ZoneInfo("Asia/Shanghai"))
                self.assertEqual(beijing.date(),dt.date(2026,10,15))
                self.assertEqual(beijing.hour,int(hour)-16)


if __name__=="__main__":
    unittest.main()
