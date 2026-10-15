"""Fault tests for a single canonical spec; no network or model calls."""
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spec_sync", ROOT / "tools/sync_spec.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
probe_spec = importlib.util.spec_from_file_location("source_probe", ROOT / "tools/source_probe.py")
probe = importlib.util.module_from_spec(probe_spec)
with patch.dict(sys.modules, {"sync_spec": sync}):
    probe_spec.loader.exec_module(probe)


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
        result = subprocess.run([sys.executable, str(self.root / "tools/source_probe.py"), "--execute", "--source-id", "SRC-001"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Specification preflight failed", result.stderr)

    def test_idempotent_generation_and_dry_run(self):
        before = {p: (self.root / p).read_bytes() for p in sync.OUTPUTS}
        self.assertEqual(sync.synchronize(self.root, write=True), [])
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in sync.OUTPUTS})
        result = subprocess.run([sys.executable, str(self.root / "tools/source_probe.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertIn("would check 0 URLs", result.stdout)

    def test_implicit_selection_contract_is_rejected(self):
        original = (self.root / sync.SPEC).read_text(encoding="utf-8")
        for replacement in ('"selection_mode": "first_n"',
                            '"selection_mode": "explicit_source_ids", "default_limit": 1'):
            with self.subTest(replacement=replacement):
                (self.root / sync.SPEC).write_text(original.replace('"selection_mode": "explicit_source_ids"', replacement), encoding="utf-8")
                with self.assertRaises(ValueError):
                    sync.projected(self.root)

    def test_probe_without_ids_cannot_execute(self):
        with patch.object(probe, "urlopen") as network, patch.object(probe, "check") as check:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                probe.main(["--execute"], root=self.root)
            network.assert_not_called()
            check.assert_not_called()

    def test_invalid_selection_rejects_whole_batch_before_network(self):
        registry = json.loads((self.root / "SOURCE_REGISTRY.json").read_text())
        valid = registry["entries"][0]["id"]
        abandoned = json.loads((self.root / "SOURCE_ABANDONED_2026-10-13.json").read_text())["records"][0]["id"]
        # Also defend against a discarded source being accidentally reintroduced into the candidate file.
        registry["entries"].append({"id": abandoned, "name": "discarded test entry"})
        (self.root / "SOURCE_REGISTRY.json").write_text(json.dumps(registry))
        for invalid in ("NO-SUCH-SOURCE", abandoned):
            with self.subTest(source=invalid), patch.object(probe, "check") as check, patch.object(probe, "urlopen") as network:
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    probe.main(["--execute", "--source-id", valid, "--source-id", invalid], root=self.root)
                check.assert_not_called()
                network.assert_not_called()

    def test_explicit_selection_dry_run_and_execution(self):
        ids = [e["id"] for e in json.loads((self.root / "SOURCE_REGISTRY.json").read_text())["entries"][:2]]
        args = ["--source-id", ids[1], "--source-id", ids[0], "--source-id", ids[1]]
        before = self.data_hashes()
        with patch.object(probe, "check") as check, patch.object(probe, "urlopen") as network, redirect_stdout(io.StringIO()) as output:
            probe.main(args, root=self.root)
            self.assertIn("would check 2 URLs", output.getvalue())
            check.assert_not_called()
            network.assert_not_called()
        self.assertEqual(self.data_hashes(), before)
        output_path = self.root / "audits/explicit_selection_test.json"
        with patch.object(probe, "check", side_effect=lambda entry, ua: {"id": entry["id"], "status": "OFFLINE_TEST", "http_status": None}) as check, patch.object(probe, "urlopen") as network, patch.object(probe.time, "sleep") as sleep, redirect_stdout(io.StringIO()):
            probe.main(args + ["--execute", "--out", str(output_path)], root=self.root)
            self.assertEqual([call.args[0]["id"] for call in check.call_args_list], [ids[1], ids[0]])
            network.assert_not_called()
            sleep.assert_called_once_with(sync.assert_current(self.root)["source_probe"]["default_delay_seconds"])
        saved = json.loads(output_path.read_text())
        self.assertEqual(saved["selected_source_ids"], [ids[1], ids[0]])
        self.assertEqual([item["id"] for item in saved["results"]], [ids[1], ids[0]])
        self.assertEqual(saved["spec_sha256"], sync.assert_current(self.root)["spec_sha256"])
        self.assertTrue(all(self.data_hashes()[name] == digest for name, digest in before.items()))

    def test_existing_audit_is_preserved_before_network(self):
        output = self.root / "audits/do_not_overwrite.json"
        output.write_text('{"original": true}')
        with patch.object(probe, "check") as check, patch.object(probe, "urlopen") as network:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                probe.main(["--execute", "--source-id", "SRC-001", "--out", str(output)], root=self.root)
            check.assert_not_called()
            network.assert_not_called()
        self.assertEqual(output.read_text(), '{"original": true}')


if __name__ == "__main__":
    unittest.main()
