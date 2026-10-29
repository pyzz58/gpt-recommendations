import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from execution_plan import next_task, validate_execution
from traceability_lib import validate
from implementation_plan import validate_implementation


class TaskSelectionTests(unittest.TestCase):
    def tasks(self):
        return [
            {"id": "CRA-W00", "title": "baseline", "status": "verified", "track": "baseline", "depends_on": [], "instruction_path": "plan/work_packages/CRA-W00.md"},
            {"id": "CRA-W01", "title": "first", "status": "planned", "track": "v1a", "depends_on": ["CRA-W00"], "instruction_path": "plan/work_packages/CRA-W01.md"},
            {"id": "CRA-W02", "title": "second", "status": "planned", "track": "v1a", "depends_on": ["CRA-W01"], "instruction_path": "plan/work_packages/CRA-W02.md"},
            {"id": "CRA-W14", "title": "OCR", "status": "planned", "track": "v1b", "depends_on": ["CRA-W01"], "instruction_path": "plan/work_packages/CRA-W14.md"},
        ]

    def test_next_is_first_unfinished_mainline_task(self):
        self.assertEqual(next_task(self.tasks())["task_id"], "CRA-W01")

    def test_blocked_task_is_not_silently_skipped(self):
        tasks = self.tasks()
        tasks[1]["status"] = "blocked"
        result = next_task(tasks)
        self.assertEqual((result["task_id"], result["state"]), ("CRA-W01", "blocked"))

    def test_in_progress_task_is_resumed(self):
        tasks = self.tasks()
        tasks[1]["status"] = "in_progress"
        self.assertEqual(next_task(tasks)["state"], "in_progress")

    def test_unverified_dependency_blocks_selected_task(self):
        tasks = self.tasks()
        tasks[1]["depends_on"].append("CRA-W99")
        result = next_task(tasks)
        self.assertEqual(result["state"], "blocked")
        self.assertIn("CRA-W99", result["blocked_by"])

    def test_optional_ocr_is_not_automatically_inserted(self):
        tasks = self.tasks()
        for task in tasks:
            if task["track"] in ("baseline", "v1a"):
                task["status"] = "verified"
        self.assertEqual(next_task(tasks)["state"], "complete")
        self.assertEqual(next_task(tasks, "v1b")["task_id"], "CRA-W14")


class ExecutionContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__", ".git", ".venv", "node_modules"))
        self.tasks = self.read("plan/tasks.json")["tasks"]
        self.modules = {x["id"]: x for x in self.read("traceability/modules.json")["modules"]}
        self.requirements = {x["id"]: x for x in self.read("theory/requirements.json")["requirements"]}
        self.scenarios = {x["id"]: x for x in self.read("traceability/scenarios.json")["scenarios"]}

    def tearDown(self):
        self.temp.cleanup()

    def read(self, path):
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def check(self, tasks):
        return validate_execution(self.root, tasks, self.modules, self.requirements, self.scenarios)

    def test_steps_are_required_for_a_code_ready_task(self):
        tasks = copy.deepcopy(self.tasks)
        tasks[1].pop("steps")
        self.assertTrue(any("missing execution field steps" in error for error in self.check(tasks)))

    def test_verified_task_needs_real_deliverables_and_available_commands(self):
        tasks = copy.deepcopy(self.tasks)
        task = tasks[1]
        task["status"] = "verified"
        task["deliverables"].append({"path": "missing-by-design.py", "kind": "code", "purpose": "negative test"})
        task["verification"].append({"command": "future command", "availability": "to_implement", "purpose": "negative test"})
        errors = self.check(tasks)
        self.assertTrue(any("verified task missing deliverable" in error for error in errors))
        self.assertTrue(any("still has a to_implement command" in error for error in errors))

    def test_task_design_reference_must_exist(self):
        tasks = copy.deepcopy(self.tasks)
        tasks[1]["design_refs"] = ["architecture/missing-by-design.md"]
        self.assertTrue(any("missing/outside implementation reference" in e for e in validate_implementation(self.root, tasks)))

    def test_stale_task_card_is_rejected(self):
        path = self.root / self.tasks[1]["instruction_path"]
        path.write_text(path.read_text(encoding="utf-8") + "stale edit\n", encoding="utf-8")
        self.assertTrue(any("generated view is stale" in error for error in validate(self.root)))


if __name__ == "__main__":
    unittest.main()
