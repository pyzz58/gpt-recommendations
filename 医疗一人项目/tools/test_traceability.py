#!/usr/bin/env python3
"""Fault-oriented tests of documentation consistency, using isolated copies."""
from __future__ import annotations
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("traceability_check", HERE / "check_traceability.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = HERE.parent
        (self.root / "traceability").mkdir()
        for name in ["最高思想.md", "技术路线与实施路径.md", "traceability/manifest.json"]:
            shutil.copyfile(self.project / name, self.root / name)

    def manifest(self):
        return json.loads((self.root / "traceability/manifest.json").read_text())

    def write_manifest(self, value):
        (self.root / "traceability/manifest.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def mutate(self, name, old, new):
        path = self.root / name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_current_baseline(self):
        self.assertEqual(checker.validate(self.root), [])

    def test_theory_change_reports_affected_requirement(self):
        self.mutate("最高思想.md", "| D-018 | 科学研究优先", "| D-018 | 科学研究应优先")
        errors = checker.validate(self.root)
        self.assertTrue(any("Theory content changed" in e for e in errors))
        result = checker.impact(self.root)
        self.assertIn("D-018", result["changed_sources"])
        self.assertIn("RQ-011", [r["requirement"] for r in result["affected"]])

    def test_deleted_decision_is_dead_reference(self):
        path = self.root / "最高思想.md"
        text = path.read_text()
        text = "\n".join(line for line in text.split("\n") if not line.startswith("| D-026 |"))
        path.write_text(text)
        self.assertTrue(any("missing source refs D-026" in e for e in checker.validate(self.root)))

    def test_new_decision_requires_mapping(self):
        path = self.root / "最高思想.md"
        path.write_text(path.read_text() + "\n| D-999 | 新增用户要求 | 测试 |\n")
        self.assertIn("Unmapped theory identifier: D-999", checker.validate(self.root))

    def test_new_role_requires_mapping(self):
        path = self.root / "最高思想.md"
        path.write_text(path.read_text() + "\n| A27 | 新增岗位 | 测试 |\n")
        self.assertIn("Unmapped theory identifier: A27", checker.validate(self.root))

    def test_duplicate_requirement_rejected(self):
        data = self.manifest()
        data["requirements"].append(data["requirements"][0].copy())
        self.write_manifest(data)
        self.assertIn("Duplicate requirement", checker.validate(self.root))

    def test_dead_technical_reference_rejected(self):
        data = self.manifest()
        data["requirements"][0]["technical_refs"].append("TR-99")
        self.write_manifest(data)
        self.assertTrue(any("dead technical_refs TR-99" in e for e in checker.validate(self.root)))

    def test_orphan_work_package_rejected(self):
        path = self.root / "技术路线与实施路径.md"
        path.write_text(path.read_text() + "\n| W99 | 漏映射工作包 | 测试 |\n")
        self.assertTrue(any("Unmapped work_packages: W99" in e for e in checker.validate(self.root)))

    def test_technical_edit_requires_rebaseline(self):
        path = self.root / "技术路线与实施路径.md"
        path.write_text(path.read_text() + "\n补充技术说明。\n")
        self.assertTrue(any("Technical document changed" in e for e in checker.validate(self.root)))

    def test_refresh_does_not_ignore_dead_source(self):
        data = self.manifest()
        data["requirements"][0]["source_refs"].append("D-999")
        self.write_manifest(data)
        before = (self.root / "traceability/manifest.json").read_bytes()
        with self.assertRaises(ValueError):
            checker.refresh(self.root, "已进行同步审阅，故意保留死引用来验证不得刷新。")
        self.assertEqual(before, (self.root / "traceability/manifest.json").read_bytes())

    def test_refresh_requires_substantive_note(self):
        with self.assertRaises(ValueError):
            checker.refresh(self.root, "ok")

    def test_reviewed_rebaseline_passes_structural_check(self):
        self.mutate("最高思想.md", "| D-018 | 科学研究优先", "| D-018 | 科学研究应优先")
        path = self.root / "技术路线与实施路径.md"
        path.write_text(path.read_text() + "\n同步说明：本次为措辞澄清，来源准入实现保持TR-09规定。\n")
        checker.refresh(self.root, "已核对来源准入仅为措辞澄清；技术说明已同步，应用状态仍为未实现。")
        self.assertEqual(checker.validate(self.root), [])

if __name__ == "__main__":
    unittest.main()

