"""Fault tests for a single canonical spec; no network or model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spec_sync", ROOT / "tools/sync_spec.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SynchronizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "intelligence"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
        self.assertEqual(sync.synchronize(self.root, write=True), [])

    def change_spec(self, transform):
        p = self.root / sync.SPEC
        p.write_text(transform(p.read_text(encoding="utf-8")), encoding="utf-8")

    def data_hashes(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*.json") if p.name != "runtime_contract.json"}

    def test_prose_change_invalidates_outputs_and_preserves_evidence(self):
        before = self.data_hashes()
        self.change_spec(lambda s: s + "\n同步测试：新增一条规范说明。\n")
        self.assertTrue(sync.synchronize(self.root))
        with self.assertRaises(ValueError):
            sync.assert_current(self.root)
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(sync.synchronize(self.root), [])
        self.assertEqual(self.data_hashes(), before)

    def test_parameter_change_reaches_runtime_contract(self):
        self.change_spec(lambda s: s.replace('"max_bytes": 350000', '"max_bytes": 12345'))
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(sync.assert_current(self.root)["source_probe"]["max_bytes"], 12345)

    def test_hand_edited_entry_is_detected_and_rebuilt(self):
        p = self.root / "AGENTS.md"
        expected = p.read_bytes()
        p.write_text("wrong independent rules", encoding="utf-8")
        self.assertTrue(sync.synchronize(self.root))
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(p.read_bytes(), expected)

    def test_unregistered_rules_block_without_deleting_user_content(self):
        p = self.root / "SIDE_RULES.md"
        p.write_text("do not delete", encoding="utf-8")
        self.assertTrue(sync.synchronize(self.root, write=True))
        self.assertEqual(p.read_text(), "do not delete")

    def test_duplicate_blocks_rejected(self):
        self.change_spec(lambda s: s + "\n<!-- BEGIN MACHINE_CONTRACT -->\n")
        with self.assertRaises(ValueError):
            sync.projected(self.root)

    def test_invalid_parameter_rejected(self):
        self.change_spec(lambda s: s.replace('"minimum_delay_seconds": 2.0', '"minimum_delay_seconds": 99.0'))
        with self.assertRaises(ValueError):
            sync.projected(self.root)

    def test_missing_registered_file_and_broken_link_block(self):
        (self.root / "SOURCE_REGISTRY.json").unlink()
        self.change_spec(lambda s: s + "\n[old](REMOVED_RULES.md)\n")
        errors = sync.synchronize(self.root)
        self.assertTrue(any("Missing registered" in e for e in errors))
        self.assertTrue(any("Broken canonical" in e for e in errors))

    def test_probe_refuses_stale_spec_before_network(self):
        self.change_spec(lambda s: s + "\n变更规范但未同步。\n")
        result = subprocess.run([sys.executable, str(self.root / "tools/source_probe.py"), "--execute", "--limit", "0"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Specification preflight failed", result.stderr)

    def test_idempotent_generation_and_dry_run(self):
        before = {p: (self.root / p).read_bytes() for p in sync.OUTPUTS}
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in sync.OUTPUTS})
        result = subprocess.run([sys.executable, str(self.root / "tools/source_probe.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY RUN", result.stdout)


if __name__ == "__main__":
    unittest.main()
