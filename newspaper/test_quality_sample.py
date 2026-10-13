"""Verify owner-requested quality samples cannot disrupt scheduled delivery."""
import datetime as dt
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from digest import quality_sample_window,edition_window,BEIJING_TZ

class QualitySampleTests(unittest.TestCase):
    def test_sample_is_prior_24h_at_request_time(self):
        now=dt.datetime(2026,10,13,11,35,tzinfo=BEIJING_TZ)
        start,end,day=quality_sample_window(now)
        self.assertEqual(start,dt.datetime(2026,10,12,11,35,tzinfo=BEIJING_TZ))
        self.assertEqual(end,now)
        self.assertEqual(day,dt.date(2026,10,13))
        self.assertEqual(end-start,dt.timedelta(hours=24))

    def test_official_edition_still_fixed_at_0100(self):
        now=dt.datetime(2026,10,13,11,35,tzinfo=BEIJING_TZ)
        a,b,_=edition_window(now)
        self.assertEqual((a.hour,b.hour),(1,1))

    def test_special_push_trigger_not_daily_receipt(self):
        w=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text()
        self.assertIn("[newspaper-quality-sample]",w)
        self.assertIn("python newspaper/digest.py --quality-sample",w)
        receipt=w.split("      - name: Record successful daily delivery",1)[1]
        self.assertNotIn("[newspaper-quality-sample]",receipt)
        self.assertIn("cron: '0 17 * * *'",w)

if __name__=="__main__":
    unittest.main()
