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

    def test_rolling_preview_is_non_delivery_and_matches_source_audit_window(self):
        w=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text()
        self.assertIn("--dry-run --rolling-preview --output /tmp/newspaper-live-qa", w)
        self.assertIn("--dry-run --rolling-preview --output /tmp/newspaper-preview", w)
        now=dt.datetime(2026,10,13,17,52,tzinfo=BEIJING_TZ)
        rstart,rend,_=quality_sample_window(now)
        self.assertEqual((rend-rstart).total_seconds(), 24*3600)
        _,fixed_end,_=edition_window(now)
        self.assertEqual(fixed_end.hour, 1)
        self.assertNotEqual(fixed_end,rend)
        # The official scheduled mail uses neither --rolling-preview
        # nor the quality-sample path; it keeps the fixed edition cutoff.
        official_send=w.split("      - name: Send real PDF daily report",1)[1]
        self.assertNotIn("--rolling-preview", official_send)

    def test_special_push_trigger_not_daily_receipt(self):
        w=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text()
        self.assertIn("[newspaper-quality-sample]",w)
        self.assertIn("python newspaper/digest.py --quality-sample",w)
        receipt=w.split("      - name: Record successful daily delivery",1)[1]
        self.assertNotIn("[newspaper-quality-sample]",receipt)
        # Test the actual policy rather than stale historical minute values.
        import re
        schedules = re.findall(r"cron: '([0-9]+) ([0-9]+) [*] [*] [*]'",w)
        self.assertGreaterEqual(len(schedules), 3)
        local_minutes=[(int(h)+8)%24*60+int(m) for m,h in schedules]
        self.assertTrue(all(60 < minute <= 140 for minute in local_minutes))

    def test_late_start_and_send_boundary_consistent(self):
        from digest import require_live_delivery_window, LATEST_SEND_START
        self.assertEqual(LATEST_SEND_START,dt.timedelta(minutes=90))
        end=dt.datetime(2026,10,14,1,0,tzinfo=BEIJING_TZ)
        require_live_delivery_window(
            dt.datetime(2026,10,14,2,29,tzinfo=BEIJING_TZ),end)
        with self.assertRaises(RuntimeError):
            require_live_delivery_window(
                dt.datetime(2026,10,14,2,30,tzinfo=BEIJING_TZ),end)

    def test_delivery_summary_distinguishes_sent_from_duplicate_and_failure(self):
        w=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text()
        self.assertIn("NEWSPAPER_DELIVERY_STATUS=",w)
        self.assertIn('status="ALREADY_SENT"',w)
        self.assertIn('status="SENT"',w)
        self.assertIn('status="FAILED"',w)
        self.assertIn("steps.save_receipt.outcome",w)
        self.assertIn("python newspaper/digest.py --recovery-20261014",w)


if __name__=="__main__":
    unittest.main()
