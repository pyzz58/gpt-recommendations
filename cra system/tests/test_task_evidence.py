"""Negative claims and source-bound CI evidence; all GitHub responses are synthetic."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from task_evidence import record_errors, remote_errors, subject_digest, verify
from implementation_plan import validate_implementation


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "cra system"
        self.root.mkdir()
        (self.root / "plan").mkdir()
        (self.root / "theory").mkdir()
        self.task = {
            "id": "CRA-W01", "status": "planned", "depends_on": [],
            "clinical_goal": "synthetic provenance test, not a real business task",
            "deliverables": [{"path": "implementation.py", "kind": "code", "purpose": "synthetic function"}],
            "contracts": ["return input plus one"], "steps": ["implement and test"],
            "done_when": ["synthetic function works"], "scenario_ids": [],
            "requirement_ids": [], "verification": [{"command": "synthetic test", "purpose": "provenance boundary", "availability": "available"}],
        }
        self.profile = {"task_id": "CRA-W01", "required_job": "cra-w01", "required_steps": ["test"], "workflow_path": ".github/workflows/cra-system.yml"}
        (self.root / "implementation.py").write_text("def add_one(value):\n    return value + 1\n")
        (self.root / "theory/requirements.json").write_text('{"requirements": []}')
        self.save_plan()

    def tearDown(self):
        self.tmp.cleanup()

    def save_plan(self):
        (self.root / "plan/tasks.json").write_text(json.dumps({"tasks": [self.task]}))
        (self.root / "plan/implementation.json").write_text(json.dumps({"verification_profiles": [self.profile]}))

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, text=True, capture_output=True, check=True).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "synthetic")
        return self.git("rev-parse", "HEAD")

    def record(self, sha="a" * 40):
        return {"kind": "github_actions", "profile_id": "CRA-W01", "run_id": 123, "tested_commit": sha, "subject_digest": subject_digest(self.root, self.task, self.profile)}

    def response(self, path):
        if "/jobs?" in path:
            return {"total_count": 1, "jobs": [{"name": "cra-w01", "status": "completed", "conclusion": "success", "steps": [{"name": "test", "status": "completed", "conclusion": "success"}]}]}
        return {"repository": {"full_name": "example/repo"}, "head_sha": self.task["completion_evidence"]["tested_commit"], "path": ".github/workflows/cra-system.yml", "event": "push", "status": "completed", "conclusion": "success"}

    def test_self_report_without_machine_evidence_is_rejected(self):
        self.task.update(status="verified", evidence=["I finished"])
        self.assertTrue(any("structured completion_evidence" in e for e in record_errors(self.root, self.task, self.profile)))

    def test_empty_file_is_rejected_even_with_forged_record(self):
        self.task["completion_evidence"] = self.record()
        self.task["status"] = "verified"
        (self.root / "implementation.py").write_text("")
        self.assertTrue(any("empty" in e for e in record_errors(self.root, self.task, self.profile)))

    def test_different_commit_and_missing_task_job_are_rejected(self):
        self.task["completion_evidence"] = self.record()
        def wrong(path):
            if "/jobs?" in path:
                return {"total_count": 1, "jobs": [{"name": "baseline", "status": "completed", "conclusion": "success", "steps": []}]}
            return {**self.response(path), "head_sha": "b" * 40}
        errors = remote_errors("example/repo", self.task, self.profile, wrong)
        self.assertTrue(any("commit mismatch" in e for e in errors))
        self.assertTrue(any("task-specific CI job" in e for e in errors))

    def test_skipped_step_cannot_prove_completion(self):
        self.task["completion_evidence"] = self.record()
        def skipped(path):
            response = self.response(path)
            if "/jobs?" in path:
                response["jobs"][0]["steps"][0]["conclusion"] = "skipped"
            return response
        self.assertTrue(any("missing/failed/skipped" in e for e in remote_errors("example/repo", self.task, self.profile, skipped)))

    def test_bound_input_change_invalidates_evidence(self):
        (self.root / "fixtures").mkdir()
        data = self.root / "fixtures/input.json"
        data.write_text('{"value": 1}')
        self.profile["binding_paths"] = ["fixtures/"]
        self.task["completion_evidence"] = self.record()
        self.task["status"] = "verified"
        data.write_text('{"value": 2}')
        self.assertTrue(any("stale" in e for e in record_errors(self.root, self.task, self.profile)))

    def test_other_repository_or_pr_run_is_rejected(self):
        self.task["completion_evidence"] = self.record()
        def wrong(path):
            value = self.response(path)
            if "/jobs?" not in path:
                value.update(repository={"full_name": "someone/else"}, event="pull_request")
            return value
        errors = remote_errors("example/repo", self.task, self.profile, wrong)
        self.assertTrue(any("another repository" in e for e in errors))
        self.assertTrue(any("workflow/event" in e for e in errors))

    def test_status_only_commit_can_reuse_actual_source_bound_run(self):
        self.git("init", "-q")
        tested = self.commit()
        self.task["completion_evidence"] = self.record(tested)
        self.task["status"] = "verified"
        self.save_plan()
        self.commit()
        self.assertEqual(verify(self.root, "example/repo", self.response), ([], 1))
        (self.root / "implementation.py").write_text("def add_one(value):\n    return 999\n")
        errors, checked = verify(self.root, "example/repo", self.response)
        self.assertEqual(checked, 1)
        self.assertTrue(any("stale" in e for e in errors))

    def test_changed_test_profile_after_run_is_rejected(self):
        self.git("init", "-q")
        tested = self.commit()
        self.profile["required_steps"] = ["different-test"]
        self.task["completion_evidence"] = self.record(tested)
        self.task["status"] = "verified"
        self.save_plan()
        self.commit()
        errors, _ = verify(self.root, "example/repo", self.response)
        self.assertTrue(any("specification/profile" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
