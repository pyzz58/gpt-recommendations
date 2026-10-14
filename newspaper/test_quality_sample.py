"""Samples are isolated from production and V2 is prebuilt before emailing."""
import datetime as dt
import unittest
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from digest import quality_sample_window, edition_window, BEIJING_TZ, LATEST_SEND_START


class QualitySampleTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (Path(__file__).resolve().parent.parent /
                         ".github/workflows/newspaper.yml").read_text(encoding="utf-8")

    def test_sample_is_prior_24h_at_request_time(self):
        now=dt.datetime(2026,10,13,11,35,tzinfo=BEIJING_TZ)
        start,end,day=quality_sample_window(now)
        self.assertEqual(start,dt.datetime(2026,10,12,11,35,tzinfo=BEIJING_TZ))
        self.assertEqual(end,now)
        self.assertEqual(day,dt.date(2026,10,13))
        self.assertEqual(end-start,dt.timedelta(hours=24))

    def test_official_edition_fixed_at_0600(self):
        now=dt.datetime(2026,10,13,11,35,tzinfo=BEIJING_TZ)
        a,b,_=edition_window(now)
        self.assertEqual((a.hour,b.hour),(6,6))
        self.assertEqual(LATEST_SEND_START,dt.timedelta(hours=2))

    def test_preview_never_sends_or_uses_api_key(self):
        w=self.workflow
        self.assertIn("--dry-run --rolling-preview --output /tmp/newspaper-preview", w)
        self.assertIn("--dry-run --rolling-preview --output /tmp/newspaper-live-qa", w)
        preview=w.split("      - name: Preview without SMTP or LLM credentials",1)[1].split(
            "      - name: Live-source PDF integration",1)[0]
        self.assertIn("python newspaper/digest.py --demo",preview)
        self.assertNotIn("secrets.",preview)
        self.assertNotIn("SMTP_PASSWORD",preview)

    def test_daily_prepares_then_sends_only_bundle(self):
        w=self.workflow
        self.assertIn("python newspaper/digest.py --prepare --output /tmp/newspaper-ready",w)
        self.assertIn("python newspaper/prepared_delivery.py --bundle-dir /tmp/newspaper-ready",w)
        schedules=re.findall(r"cron: '([0-9]+) ([0-9]+) [*] [*] [*]'",w)
        self.assertGreaterEqual(len(schedules),6)
        local=[((int(h)+8)%24,int(m)) for m,h in schedules]
        self.assertTrue(any(hr==6 for hr,_ in local))
        self.assertTrue(any(hr==7 for hr,_ in local))
        self.assertTrue(all(hr in (6,7) for hr,_ in local))
        self.assertNotIn("[newspaper-recovery-20261014]",w)
        self.assertNotIn("[newspaper-v05-send-once]",w)

    def test_summary_cannot_confuse_ready_and_sent(self):
        w=self.workflow
        for state in ("PREPARED_NOT_SENT","ALREADY_SENT","SMTP_ACCEPTED",
                      "SMTP_ACCEPTED_RECEIPT_UNVERIFIED","FAILED"):
            self.assertIn(state,w)
        self.assertIn("steps.save_receipt.outcome",w)


if __name__=="__main__":
    unittest.main()
