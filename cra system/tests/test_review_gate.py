import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from review_gate import (
    apply_review_gate,
    task_evidence_errors,
    validate_findings,
)


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "audit").mkdir()
        (self.root / "plan/work_packages").mkdir(parents=True)
        (self.root / "tests").mkdir()
        (self.root / "plan/work_packages/CRA-W01.md").write_text(
            "# CRA-W01\n", encoding="utf-8"
        )
        (self.root / "tests/test_feature.py").write_text(
            "def test_correct_behavior():\n    assert True\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def finding(self, *, status="open", evidence=None):
        return {
            "id": "CRA-REV-TEST-01",
            "guard": "CRA-GUARD-01",
            "status": status,
            "blocking": True,
            "summary": "Synthetic review gate",
            "affected_tasks": ["CRA-W01"],
            "repair_path": "plan/work_packages/CRA-W01.md",
            "closure_criteria": ["Correct behavior asserted"],
            "required_tests": [
                "tests/test_feature.py::test_correct_behavior"
            ],
            "closure_evidence": evidence,
        }

    def save(self, finding):
        payload = {
            "schema_version": 1,
            "sources": {},
            "findings": [finding],
        }
        (self.root / "audit/current_findings.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def test_open_finding_changes_affected_task_to_review_required(self):
        self.save(self.finding())
        result = apply_review_gate(
            self.root,
            {"state": "in_progress", "task_id": "CRA-W01"},
        )
        self.assertEqual(result["state"], "review_required")
        self.assertEqual(result["review_findings"], ["CRA-REV-TEST-01"])
        self.assertEqual(
            result["repair_paths"], ["plan/work_packages/CRA-W01.md"]
        )

    def test_open_finding_does_not_block_unrelated_task(self):
        self.save(self.finding())
        result = apply_review_gate(
            self.root,
            {"state": "ready", "task_id": "CRA-W02"},
        )
        self.assertEqual(result["state"], "ready")

    def test_closed_finding_requires_bound_correct_behavior_test(self):
        self.save(self.finding(status="closed"))
        self.assertTrue(
            any("requires closure_evidence" in error for error in validate_findings(self.root))
        )
        evidence = {
            "kind": "github_actions",
            "run_id": 123,
            "tested_commit": "a" * 40,
            "job_name": "cra-w01",
            "test_cases": [
                "tests/test_feature.py::test_correct_behavior"
            ],
            "acceptance_passed": True,
        }
        self.save(self.finding(status="closed", evidence=evidence))
        self.assertEqual(validate_findings(self.root), [])

    def test_verified_task_cannot_bypass_open_finding(self):
        self.save(self.finding())
        errors = task_evidence_errors(
            self.root, {"id": "CRA-W01", "status": "verified"}
        )
        self.assertTrue(any("blocked by open review finding" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
