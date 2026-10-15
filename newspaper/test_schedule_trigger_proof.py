"""P0: scheduler must have one production cron and no competing probes."""
import datetime as dt
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo
import json

ROOT=Path(__file__).resolve().parent.parent
WORKFLOW=ROOT/".github/workflows/newspaper.yml"
POLICY=ROOT/"newspaper/production_policy.json"


class TriggerProofTests(unittest.TestCase):
    def test_one_authoritative_scheduled_entry(self):
        cfg=json.loads(POLICY.read_text(encoding="utf-8"))
        main=WORKFLOW.read_text(encoding="utf-8")
        crons=re.findall(r"^    - cron: '([^']+)'$",main,re.M)
        self.assertEqual(crons,[cfg["startup_cron_utc"]])
        self.assertNotIn("newspaper-ready-v22-",main)
        self.assertNotIn("PREPARED_NOT_SENT",main)
        self.assertIn("NEWSPAPER_DELIVERY_STATUS=",main)
        self.assertIn("newspaper/digest.py --prepare",main)
        self.assertIn("newspaper/prepared_delivery.py",main)

    def test_no_extra_temporary_news_schedulers(self):
        directory=ROOT/".github/workflows"
        self.assertFalse((directory/"newspaper-schedule-probe.yml").exists())
        self.assertFalse((directory/"newspaper-one-time-autonomous-test-20261015.yml").exists())

    def test_single_cron_maps_to_beijing_midnight_one(self):
        cfg=json.loads(POLICY.read_text(encoding="utf-8"))
        minute,hour,_,_,_=cfg["startup_cron_utc"].split()
        utc=dt.datetime(2026,10,14,int(hour),int(minute),tzinfo=dt.timezone.utc)
        bj=utc.astimezone(ZoneInfo("Asia/Shanghai"))
        self.assertEqual((bj.date(),bj.hour,bj.minute),(dt.date(2026,10,15),0,1))


if __name__=="__main__":
    unittest.main()
