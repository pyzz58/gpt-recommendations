import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from traceability_lib import fingerprint, render_views, revision_errors, validate


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__", ".git", ".venv", "node_modules"))

    def tearDown(self):
        self.temp.cleanup()

    def read(self, path):
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def write(self, path, obj):
        (self.root / path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def regenerate(self):
        for path, text in render_views(self.root).items():
            (self.root / path).write_text(text, encoding="utf-8")

    def test_baseline_is_consistent(self):
        self.assertEqual(validate(self.root), [])

    def test_theory_only_change_is_rejected(self):
        data = self.read("theory/requirements.json")
        data["requirements"][0]["statement"] += " 新要求。"
        self.write("theory/requirements.json", data)
        self.assertTrue(any("stale technical review" in x for x in validate(self.root)))

    def test_missing_one_module_binding_is_rejected(self):
        data = self.read("traceability/bindings.json")
        data["bindings"].pop()
        self.write("traceability/bindings.json", data)
        self.assertTrue(any("missing technical binding" in x for x in validate(self.root)))

    def test_rebinding_without_new_change_record_is_rejected(self):
        data = self.read("theory/requirements.json")
        item = data["requirements"][0]
        item["statement"] += " 新要求。"
        item["revision"] += 1
        self.write("theory/requirements.json", data)
        bindings = self.read("traceability/bindings.json")
        for binding in bindings["bindings"]:
            if binding["requirement_id"] == item["id"]:
                binding["reviewed_digest"] = fingerprint(item)
                binding["reviewed_revision"] = item["revision"]
        self.write("traceability/bindings.json", bindings)
        self.regenerate()
        self.assertTrue(any("no matching change record" in x for x in validate(self.root)))

    def test_stale_readable_view_is_rejected(self):
        path = self.root / "theory/REQUIREMENTS.md"
        path.write_text(path.read_text(encoding="utf-8") + "unsynchronized edit\n", encoding="utf-8")
        self.assertTrue(any("generated view is stale" in x for x in validate(self.root)))

    def test_changed_revision_and_deleted_ids_are_rejected(self):
        previous = {"CRA-R001": {"revision": 1, "statement": "old"}}
        same_revision = {"CRA-R001": {"revision": 1, "statement": "new"}}
        self.assertTrue(revision_errors(same_revision, previous))
        self.assertTrue(revision_errors({}, previous))

    def test_duplicate_id_is_rejected(self):
        data = self.read("theory/requirements.json")
        data["requirements"].append(data["requirements"][0].copy())
        self.write("theory/requirements.json", data)
        self.assertTrue(any("duplicate requirement" in x for x in validate(self.root)))

    def test_unnecessary_technical_rewrite_is_not_forced(self):
        data = self.read("theory/requirements.json")
        item = data["requirements"][0]
        item["statement"] += "（文字说明，不改变操作。）"
        item["revision"] += 1
        self.write("theory/requirements.json", data)
        bindings = self.read("traceability/bindings.json")
        for binding in bindings["bindings"]:
            if binding["requirement_id"] == item["id"]:
                binding["reviewed_digest"] = fingerprint(item)
                binding["reviewed_revision"] = item["revision"]
        self.write("traceability/bindings.json", bindings)
        modules = self.read("traceability/modules.json")["modules"]
        record = {
            "id": "CR-TEST", "requirement_fingerprints": {item["id"]: fingerprint(item)},
            "module_reviews": {
                mid: {"decision": "no_technical_change", "reason": "仅补充文字，既有模块操作和契约已完整覆盖。",
                      "paths": [next(m["design_path"] for m in modules if m["id"] == mid)]}
                for mid in item["modules"]
            }
        }
        self.write("changes/CR-TEST.json", record)
        tasks = self.read("plan/tasks.json")
        for task in tasks["tasks"]:
            if (
                task["status"] == "verified"
                and item["id"] in task["requirement_ids"]
            ):
                task["status"] = "in_progress"
                task["completion_evidence"] = None
        changed = True
        while changed:
            changed = False
            statuses = {
                task["id"]: task["status"] for task in tasks["tasks"]
            }
            for task in tasks["tasks"]:
                if task["status"] != "verified":
                    continue
                if any(
                    statuses[dependency] != "verified"
                    for dependency in task["depends_on"]
                ):
                    task["status"] = "in_progress"
                    task["completion_evidence"] = None
                    changed = True
        self.write("plan/tasks.json", tasks)
        self.regenerate()
        self.assertEqual(validate(self.root), [])


if __name__ == "__main__":
    unittest.main()
