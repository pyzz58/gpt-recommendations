"""Offline public-fiction real-model readiness, no network or credentials."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import live_pilot_readiness as ready
import article_intake as intake
import agent_live_pilot as pilot
import agent_provider_wire as wire


class PilotReadinessTests(unittest.TestCase):
    def test_fiction_first_role_generates_source_bound_preflight(self):
        r=ready.price_director_request()
        self.assertEqual(r["model"],"deepseek-flash")
        self.assertEqual(r["model_version_label"],"DeepSeek-V4.1-Flash")
        self.assertEqual(r["catalog_topics"],1)
        self.assertGreater(r["source_shots"],1)
        self.assertEqual(r["first_task"],"director_brief")
        self.assertEqual(r["second_task"],"script_edit")
        self.assertEqual(r["second_task_quote"],
                         "NOT_YET_KNOWN_NEEDS_DIRECTOR_OUTPUT")
        self.assertFalse(r["ready_for_live_dispatch"])
        self.assertEqual(r["actual_provider_calls"],0)
        self.assertEqual(r["actual_spend_cny"],"0")

    def test_authoritative_source_hashes_match_original_in_memory(self):
        pre=ready.price_director_request()
        result=intake.prepare_episode(ready.PUBLIC_FICTION,"EP01")
        self.assertEqual(pre["episode_source_sha256"],
                         result["episode_source_sha256"])
        self.assertEqual(pre["base_plan_digest"],result["team"]["base_digest"])
        self.assertEqual(pre["source_shots"],len(result["plan"]["shots"]))
        self.assertFalse(pre["human_approved"])

    def test_budget_proxy_is_bounded_but_never_claims_hard_provider_cap(self):
        r=ready.price_director_request()
        from decimal import Decimal
        self.assertGreater(Decimal(r["first_task_estimated_max_reservation_cny"]),0)
        self.assertLess(Decimal(r["first_task_estimated_max_reservation_cny"]),
                        Decimal(r["planning_cap_cny"]))
        self.assertTrue(r["cap_is_not_provider_invoice_limit"])
        self.assertEqual(r["pricing_peak_cny_per_m"]["cache_miss"],"2")
        self.assertEqual(r["pricing_peak_cny_per_m"]["output"],"8")
        self.assertIn("SUPPLIER_ACCOUNT_LEVEL_BILLING_LIMITS",
                      r["run_preconditions"])

    def test_dry_run_never_leaks_secret_or_masquerades_as_real(self):
        report=ready.price_director_request()
        content=json.dumps(report,ensure_ascii=False)
        self.assertNotIn("Authorization",content)
        self.assertNotIn("api_key",content)
        self.assertNotIn("Bearer ",content)
        self.assertNotIn("林禾",content)
        self.assertIn("OFFLINE_PREFLIGHT_ONLY_BLOCK_REAL_DISPATCH",content)
        self.assertIn("NO_PRIVATE_EXECUTION_ACCOUNT_SUPPLIED_TO_THIS_REHEARSAL",
                      report["missing_preconditions"])
        self.assertFalse(report["ready_for_video_generation"])

    def test_cli_requires_public_fiction_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"pilot.json"
            cli=[sys.executable,str(ROOT/"live_pilot_readiness.py"),"--out",str(output)]
            missing=subprocess.run(cli,text=True,capture_output=True,check=False)
            self.assertNotEqual(missing.returncode,0)
            self.assertFalse(output.exists())
            success=subprocess.run(cli+["--public-fiction-only"],
                                   text=True,capture_output=True,check=False)
            self.assertEqual(success.returncode,0,success.stderr[:200])
            self.assertIn("external_calls=0",success.stdout)
            first=output.read_bytes()
            second=subprocess.run(cli+["--public-fiction-only"],
                                  text=True,capture_output=True,check=False)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(output.read_bytes(),first)

    def test_no_dispatch_implementation_inside_preflight(self):
        # This is purely a response-cost check; all live transport lives in the
        # separate restricted class. No runtime API Key entry point here.
        self.assertFalse(hasattr(ready,"DeepSeekHTTPSClient"))
        self.assertFalse(hasattr(ready,"run_one_creative_task"))
        self.assertEqual(ready.MODEL, "deepseek-flash")


if __name__=="__main__":
    unittest.main()
