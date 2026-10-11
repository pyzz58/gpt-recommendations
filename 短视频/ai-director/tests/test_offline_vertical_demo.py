"""Public synthetic 10-role vertical film production demo regression, no APIs."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import offline_vertical_demo as demo


class FullVerticalDemoTests(unittest.TestCase):
    def test_public_synthetic_demo_emits_real_operator_workorders(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"public-fixture-only"
            manifest=demo.run_synthetic_only(output)
            self.assertEqual(manifest["roles_count"],10)
            self.assertEqual(manifest["real_deepseek_calls"],0)
            self.assertFalse(manifest["human_identity_or_approval_verified"])
            self.assertFalse(manifest["ready_for_publication"])
            self.assertGreater(manifest["shots_count"],1)
            self.assertEqual(manifest["shots_count"],
                             manifest["video_prompt_jobs"]+manifest["postproduction_jobs"])
            bundle=json.loads((output/"SYNTHETIC_DEMO_NOT_REAL_AI.json").read_text("utf-8"))
            self.assertEqual(bundle["provenance"],"locked_ten_role_crew")
            self.assertEqual(bundle["project"]["total_shots"],manifest["shots_count"])
            self.assertFalse(bundle["ready_to_call_video_model"])
            self.assertEqual(bundle["external_model_calls"],0)
            self.assertTrue(all(x["target_type"] in
                                ("postproduction_only","video_generation_candidate")
                                for x in bundle["shots"]))
            md=(output/"SYNTHETIC_DEMO_NOT_REAL_AI.md").read_text("utf-8")
            self.assertIn("AI 视频制作工作单",md)
            self.assertIn("Wan".lower(),md.lower()) if manifest["video_prompt_jobs"] else None
            self.assertIn("逐镜生产工单",md)
            self.assertIn("不是已生成的视频",md)

    def test_zero_network_public_fixture_evidence_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"demo"
            demo.run_synthetic_only(output)
            summary=json.loads((output/"SYNTHETIC_DEMO_EXECUTION_EVIDENCE.json").read_text("utf-8"))
            self.assertEqual(summary["kind"],"PUBLIC_SYNTHETIC_VERTICAL_DEMO_NOT_REAL_AI")
            self.assertEqual(len(summary["stages"]),10)
            self.assertTrue(all(x["source"]=="PREWRITTEN_SYNTHETIC_JSON_NOT_AI"
                                for x in summary["stages"]))
            self.assertEqual(summary["real_video_calls"],0)
            self.assertFalse(summary["paid_model_authorized"])
            readme=(output/"README.txt").read_text("utf-8")
            self.assertIn("NOT REAL AI OUTPUT",readme)
            self.assertIn("NOT genuine DeepSeek",readme)

    def test_no_auto_overwrite_existing_public_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"example"
            demo.run_synthetic_only(target)
            existing=(target/"SYNTHETIC_DEMO_NOT_REAL_AI.md").read_bytes()
            with self.assertRaisesRegex(ValueError,"MUST_BE_EMPTY"):
                demo.run_synthetic_only(target)
            self.assertEqual((target/"SYNTHETIC_DEMO_NOT_REAL_AI.md").read_bytes(),
                             existing)

    def test_cli_refuses_run_without_explicit_synthetic_only_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"should-not-exist"
            p=subprocess.run(
                [sys.executable,str(ROOT/"offline_vertical_demo.py"),
                 "--output-dir",str(out)],
                text=True,capture_output=True,check=False)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(out.exists())

    def test_cli_success_writes_only_synthetic_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"ci-demo"
            p=subprocess.run(
                [sys.executable,str(ROOT/"offline_vertical_demo.py"),
                 "--synthetic-only","--output-dir",str(out)],
                text=True,capture_output=True,check=False)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("external_calls=0",p.stdout)
            self.assertEqual(set(x.name for x in out.iterdir()),{
                "SYNTHETIC_DEMO_NOT_REAL_AI.json",
                "SYNTHETIC_DEMO_NOT_REAL_AI.md",
                "SYNTHETIC_DEMO_EXECUTION_EVIDENCE.json",
                "README.txt"})
            self.assertNotIn("api_key",
                             (out/"SYNTHETIC_DEMO_EXECUTION_EVIDENCE.json").read_text("utf-8"))


if __name__=="__main__":
    unittest.main()
