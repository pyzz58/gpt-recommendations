"""Behavior tests for deterministic theory-to-technical traceability."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_technical_test", ROOT / "tools/sync_spec.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class TechnicalTraceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "intelligence"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        # These isolated fixtures start at a known correspondence baseline even
        # when production correctly has pending theory changes. Never change ROOT.
        now = {n["id"]: n for n in self.current()["nodes"]}
        self.edit_config(lambda c: [n.__setitem__("reviewed_binding", now[n["id"]]["current_binding"])
                                    for n in c["nodes"]])
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        sync.assert_technical_current(self.root)

    def text(self):
        return (self.root / sync.SPEC).read_text(encoding="utf-8")

    def change(self, fn):
        (self.root / sync.SPEC).write_text(fn(self.text()), encoding="utf-8")

    def config(self):
        return sync.trace.fenced_block(self.text(), "TECHNICAL_BINDINGS")

    def edit_config(self, fn):
        cfg = self.config()
        fn(cfg)
        def replace(text):
            a, b = text.index("<!-- BEGIN TECHNICAL_BINDINGS -->"), text.index("<!-- END TECHNICAL_BINDINGS -->")
            return text[:a] + "<!-- BEGIN TECHNICAL_BINDINGS -->\n```json\n" + json.dumps(cfg, ensure_ascii=False, indent=2) + "\n```\n" + text[b:]
        self.change(replace)

    def current(self):
        return sync.trace.build(self.text(), hashlib.sha256(self.text().encode()).hexdigest())

    def source_change(self):
        self.change(lambda s: s.replace("### 4.2 轻量候选卡（L1唯一必交）", "### 4.2 轻量候选卡（L1唯一必交）\n\n本测试理论变化：新增一种必须保留的候选限制。", 1))

    def outputs(self):
        return {name: (self.root / name).read_bytes() for name in sync.OUTPUTS}

    def test_all_nodes_logic_and_root_theories_are_traceable(self):
        t = self.current()
        self.assertEqual(len(t["nodes"]), 21)
        self.assertEqual(sum(len(n["logic"]) for n in t["nodes"]), 72)
        self.assertFalse(t["review_required"])
        for i in range(25):
            self.assertIn("th-" + str(i), t["theory_to_technical"])

    def test_theory_change_refreshes_view_and_blocks_affected_adoption_only(self):
        reviewed = self.config()
        self.source_change()
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        t = json.loads((self.root / "technical_trace.json").read_text())
        self.assertIn("T02", t["review_required"])
        self.assertIn("R01", t["review_required"])
        self.assertIn("th-4", next(n for n in t["nodes"] if n["id"] == "T02")["changed_theory_refs"])
        with self.assertRaisesRegex(ValueError, "requires review"):
            sync.assert_technical_current(self.root, ["T02"])
        sync.assert_technical_current(self.root, ["T04"])
        self.assertEqual([n["reviewed_binding"] for n in reviewed["nodes"]], [n["reviewed_binding"] for n in self.config()["nodes"]])
        first = self.outputs()
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(first, self.outputs())
        with self.assertRaises(ValueError):
            sync.assert_technical_current(self.root, ["R01"])

    def test_rename_and_renumber_resolve_same_stable_source(self):
        self.change(lambda s: s.replace("### 4.2 轻量候选卡（L1唯一必交）", "### 4.21 新名称：候选范围", 1))
        t = self.current()
        self.assertEqual(t["theory_to_technical"]["th-4-2"]["section"], "4.21")
        self.assertIn("新名称", t["theory_to_technical"]["th-4-2"]["title"])
        self.assertIn("T02", t["review_required"])

    def test_missing_or_duplicate_anchor_blocks_all_projection_writes(self):
        original = self.text()
        before = self.outputs()
        for bad in (original.replace('<a id="th-4"></a>\n', '', 1), original.replace('<a id="th-4"></a>', '<a id="th-4"></a>\n<a id="th-4"></a>', 1)):
            with self.subTest(prefix=bad[:20]):
                (self.root / sync.SPEC).write_text(bad)
                with self.assertRaises(ValueError):
                    sync.synchronize(self.root, write=True)
                self.assertEqual(before, self.outputs())

    def test_new_root_theory_cannot_be_silently_ignored(self):
        self.change(lambda s: s + "\n## 27. 未分类的新理论\n\n新增约束。\n")
        with self.assertRaisesRegex(ValueError, "Unclassified"):
            self.current()

    def test_unbound_root_theory_is_rejected(self):
        def edit(c):
            for n in c["nodes"]:
                n["theory_refs"] = [r for r in n["theory_refs"] if r != "th-5"]
                for step in n["logic"]:
                    step["theory_refs"] = [r for r in step["theory_refs"] if r != "th-5"]
        self.edit_config(edit)
        with self.assertRaisesRegex(ValueError, "Unbound theory root"):
            self.current()

    def test_design_prose_change_invalidates_its_consumers(self):
        self.change(lambda s: s.replace("- **设计**：从M02起提出知识、背景、比较和迁移问题", "- **设计**：从M02起提出不同的知识、背景、比较和迁移问题", 1))
        t = self.current()
        self.assertIn("T07", t["review_required"])
        self.assertIn("T09", t["review_required"])
        self.assertNotIn("T06", t["review_required"])

    def test_logic_change_is_not_hidden_by_unchanged_design_prose(self):
        def edit(c):
            n = next(n for n in c["nodes"] if n["id"] == "T07")
            n["logic"][0]["condition"] += "；本测试改变了条件"
        self.edit_config(edit)
        self.assertIn("T07", self.current()["review_required"])

    def test_shared_architecture_change_invalidates_bound_nodes(self):
        self.change(lambda s: s.replace("先以人工和已有工具完成内容验证", "先以本测试改变的方式完成内容验证", 1))
        t = self.current()
        self.assertEqual(len(t["review_required"]), 21)
        n = next(n for n in t["nodes"] if n["id"] == "T07")
        self.assertIn("tech-shared-25-3", n["changed_shared_context"])

    def test_extra_unbound_module_heading_is_rejected(self):
        self.change(lambda s: s + "\n#### 25.4.14 T14｜未登记的新模块\n\n未标注内容。\n")
        with self.assertRaisesRegex(ValueError, "Unbound/duplicate module"):
            self.current()

    def test_missing_logic_fields_and_invalid_targets_are_rejected(self):
        original = self.text()
        for field, value in (("condition", ""), ("theory_refs", []), ("executor", "T99"), ("failure_to", ["T99"]), ("success_to", [])):
            with self.subTest(field=field):
                (self.root / sync.SPEC).write_text(original)
                self.edit_config(lambda c: c["nodes"][0]["logic"][0].__setitem__(field, value))
                with self.assertRaises(ValueError):
                    self.current()

    def test_missing_module_and_duplicate_logic_are_rejected(self):
        original = self.text()
        self.edit_config(lambda c: c["nodes"].pop())
        with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
            self.current()
        (self.root / sync.SPEC).write_text(original)
        self.edit_config(lambda c: c["nodes"][0]["logic"].append(dict(c["nodes"][0]["logic"][0])))
        with self.assertRaisesRegex(ValueError, "logic ID"):
            self.current()

    def test_design_cycle_is_rejected_but_runtime_return_loops_are_valid(self):
        c = self.config()
        self.assertTrue(any(n["id"] in st["failure_to"] for n in c["nodes"] for st in n["logic"]))
        self.current()  # Existing legitimate return loops remain valid.
        self.edit_config(lambda c: next(n for n in c["nodes"] if n["id"] == "T01")["design_dependencies"].append("T13"))
        with self.assertRaisesRegex(ValueError, "Cyclic design"):
            self.current()

    def test_unknown_dependency_or_selected_node_cannot_be_adopted(self):
        with self.assertRaisesRegex(ValueError, "Unknown technical node"):
            sync.assert_technical_current(self.root, ["T99"])
        self.edit_config(lambda c: c["nodes"][0]["design_dependencies"].append("T99"))
        with self.assertRaisesRegex(ValueError, "Invalid design dependencies"):
            self.current()

    def test_suggestions_do_not_become_rules_but_issue_policy_is_tracked(self):
        self.change(lambda s: s.replace("<!-- END ISSUE_LEDGER -->", "\n未采纳建议：要求所有文章自动发行。\n<!-- END ISSUE_LEDGER -->", 1))
        self.assertFalse(self.current()["review_required"])
        self.change(lambda s: s.replace("已有明确授权的修复不重复请求确认。", "已有明确授权的修复不重复请求确认。本测试修改了问题维护效力。", 1))
        self.assertIn("T01", self.current()["review_required"])

    def test_upstream_pending_cannot_be_cleared_by_only_rebaselining_consumer(self):
        self.source_change()
        now = {n["id"]: n for n in self.current()["nodes"]}
        self.edit_config(lambda c: next(n for n in c["nodes"] if n["id"] == "T03").__setitem__("reviewed_binding", now["T03"]["current_binding"]))
        node = next(n for n in self.current()["nodes"] if n["id"] == "T03")
        self.assertEqual(node["binding_status"], "REVIEW_REQUIRED")
        self.assertIn("T02", node["unreviewed_dependencies"])

    def test_explicitly_reviewed_changed_scope_can_restore_binding(self):
        self.source_change()
        now = {n["id"]: n for n in self.current()["nodes"]}
        def record_review(c):
            for n in c["nodes"]:
                if now[n["id"]]["binding_status"] == "REVIEW_REQUIRED":
                    n["reviewed_binding"] = now[n["id"]]["current_binding"]
        self.edit_config(record_review)  # Explicit test action, never sync --write.
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        sync.assert_technical_current(self.root)

    def test_hand_editing_derived_technical_view_cannot_approve_change(self):
        self.source_change()
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        p = self.root / "technical_trace.json"
        p.write_text(p.read_text().replace("REVIEW_REQUIRED", "CURRENT_BINDING"))
        with self.assertRaisesRegex(ValueError, "Stale generated file"):
            sync.assert_technical_current(self.root, ["T02"])
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        with self.assertRaisesRegex(ValueError, "requires review"):
            sync.assert_technical_current(self.root, ["T02"])


if __name__ == "__main__":
    unittest.main()
