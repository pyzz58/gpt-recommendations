"""Offline production phase safety tests; never use SMTP."""
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule_contract import choose_phase
from production_policy import BEIJING

PREPARE = "5 16 * * *"
SEND = "3 17 * * *"

def clock(hour, minute):
    return dt.datetime(2026, 10, 15, hour, minute, tzinfo=BEIJING)

class ScheduleContractTests(unittest.TestCase):
    def test_preparation_before_one(self):
        self.assertEqual(choose_phase("schedule", PREPARE, "", clock(0, 5)), "prepare")
    def test_late_preparation_enters_send_window(self):
        self.assertEqual(choose_phase("schedule", PREPARE, "", clock(1, 20)), "send")
    def test_expired_scheduled_run(self):
        self.assertEqual(choose_phase("schedule", SEND, "", clock(2, 1)), "expired")
    def test_early_send_run(self):
        self.assertEqual(choose_phase("schedule", SEND, "", clock(0, 59)), "wait")
    def test_manual_live_outside_window(self):
        self.assertEqual(choose_phase("workflow_dispatch", "", "false", clock(2, 0)), "expired")
    def test_unknown_cron_fails_closed(self):
        with self.assertRaises(RuntimeError):
            choose_phase("schedule", "0 0 * * *", "", clock(1, 10))
    def test_preview_never_sends(self):
        self.assertEqual(choose_phase("workflow_dispatch", "", "true", clock(1, 10)), "preview")

if __name__ == "__main__":
    unittest.main()
