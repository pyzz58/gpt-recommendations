"""P0: exactly one external startup marker, no competing GitHub cron or probes."""
from pathlib import Path
import json
import re
import unittest

ROOT=Path(__file__).resolve().parent.parent
WORKFLOW=ROOT/".github/workflows/newspaper.yml"
POLICY=ROOT/"newspaper/production_policy.json"


class TriggerProofTests(unittest.TestCase):
    def test_authoritative_external_startup_entry(self):
        cfg=json.loads(POLICY.read_text(encoding="utf-8"))
        main=WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(cfg["startup_mode"],"external-marker-push")
        self.assertEqual(cfg["startup_marker_path"],"newspaper/.scheduler-tick")
        self.assertEqual(cfg["startup_timezone"],"Asia/Shanghai")
        self.assertEqual(cfg["startup_time_bjt"],"00:01")
        crons=re.findall(r"^    - cron: '([^']+)'$",main,re.M)
        self.assertEqual(crons,[])
        self.assertNotIn("  schedule:\n",main)
        self.assertIn("  push:\n    branches: [main]\n    paths:\n      - 'newspaper/.scheduler-tick'\n",main)
        self.assertNotIn("newspaper-ready-v22-",main)
        self.assertNotIn("PREPARED_NOT_SENT",main)
        self.assertIn("NEWSPAPER_DELIVERY_STATUS=",main)
        self.assertIn("newspaper/digest.py --prepare",main)
        self.assertIn("newspaper/prepared_delivery.py",main)

    def test_no_extra_temporary_news_schedulers(self):
        directory=ROOT/".github/workflows"
        self.assertFalse((directory/"newspaper-schedule-probe.yml").exists())
        self.assertFalse((directory/"newspaper-one-time-autonomous-test-20261015.yml").exists())
        self.assertFalse((directory/"newspaper-one-shot-20261015-0359.yml").exists())

    def test_pending_cloudflare_dispatch_adapter_matches_policy(self):
        cfg=json.loads(POLICY.read_text(encoding="utf-8"))
        replacement=cfg["startup_replacement"]
        self.assertEqual(replacement["deployment_status"], "code_ready_not_deployed")
        self.assertEqual(replacement["cron_utc"], "1 16 * * *")
        worker=(ROOT/replacement["worker"]).read_text(encoding="utf-8")
        wrangler=(ROOT/replacement["config"]).read_text(encoding="utf-8")
        self.assertIn('crons = ["1 16 * * *"]', wrangler)
        self.assertIn("GH_ACTIONS_TOKEN", worker)
        self.assertIn("/actions/workflows/newspaper.yml/dispatches", worker)
        self.assertIn('dry_run: "false"', worker)
        self.assertIn('  workflow_dispatch:', WORKFLOW.read_text(encoding="utf-8"))
        self.assertNotIn("ghp_", worker)

    def test_canonical_marker_file_exists(self):
        cfg=json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertTrue((ROOT/cfg["startup_marker_path"]).is_file())


if __name__=="__main__":
    unittest.main()
