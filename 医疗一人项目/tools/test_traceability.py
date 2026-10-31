#!/usr/bin/env python3
"""Fault-oriented tests of documentation consistency, using isolated copies."""
from __future__ import annotations
import importlib.util
import hashlib
import json
import shutil
import subprocess
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
        shutil.copyfile(
            self.project / "traceability/acceptance-records.json",
            self.root / "traceability/acceptance-records.json",
        )
        (self.root / "tools").mkdir()
        shutil.copyfile(
            self.project / "tools/check_traceability.py",
            self.root / "tools/check_traceability.py",
        )
        shutil.copyfile(
            self.project / "tools/test_traceability.py",
            self.root / "tools/test_traceability.py",
        )
        for item in self.manifest().get("supporting_artifacts", []):
            target = self.root / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.project / item["path"], target)
        for requirement in self.manifest().get("requirements", []):
            for name in requirement.get("implementation_paths", []):
                source = self.project / name
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        evidence = json.loads((self.root / "traceability/acceptance-records.json").read_text())
        for record in evidence.get("records", []):
            for item in record.get("code_paths", []):
                name = item["path"]
                source = self.project / name
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            artifact_paths = set(record.get("artifacts", []))
            for command in record.get("commands", []):
                artifact_paths.update(command.get("artifacts", []))
            for name in artifact_paths:
                source = self.project / name
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "traceability@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Traceability Test"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fixture baseline"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        fixture_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        path = self.root / "traceability/acceptance-records.json"
        evidence = json.loads(path.read_text())
        for record in evidence.get("records", []):
            record["source_commit"] = fixture_commit
            for item in record.get("code_paths", []):
                item["sha256"] = hashlib.sha256(
                    (self.root / item["path"]).read_bytes()
                ).hexdigest()
            record["source_tree_git_sha256"] = checker._tree_fingerprint(
                self.root,
                record["source_scope"],
                fixture_commit,
            )
            record["source_tree_worktree_sha256"] = checker._tree_fingerprint(
                self.root,
                record["source_scope"],
            )
            artifact_paths = set(record.get("artifacts", []))
            for command in record.get("commands", []):
                artifact_paths.update(command.get("artifacts", []))
            record["artifact_hashes"] = {
                name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
                for name in sorted(artifact_paths)
            }
        if not evidence["records"]:
            requirement = next(
                item for item in self.manifest()["requirements"] if item["id"] == "RQ-001"
            )
            source_scope = ["tools", "services/core/src", "config", "apps/web/src"]
            evidence["records"].append(
                {
                    "id": "ACC-BASELINE-TEST",
                    "requirements": ["RQ-001"],
                    "technical_refs": requirement["technical_refs"],
                    "work_packages": requirement["work_packages"],
                    "acceptance_refs": requirement["acceptance_refs"],
                    "source_commit": fixture_commit,
                    "result": "passed",
                    "commands": [
                        {
                            "cwd": ".",
                            "command": "python3 tools/check_traceability.py check",
                            "mode": "mock",
                            "started_at": "2026-11-01T00:00:00Z",
                            "finished_at": "2026-11-01T00:00:01Z",
                            "exit_code": 0,
                            "artifacts": ["traceability/acceptance-records.json"],
                        }
                    ],
                    "validation_levels": {
                        "mock": {"status": "passed", "evidence": ["checker"]},
                        "live": {"status": "not_run", "evidence": []},
                        "human_expert": {"status": "not_run", "evidence": []},
                        "real_outsourcing": {"status": "not_run", "evidence": []},
                    },
                    "code_paths": [
                        {
                            "path": "tools/check_traceability.py",
                            "sha256": hashlib.sha256(
                                (self.root / "tools/check_traceability.py").read_bytes()
                            ).hexdigest(),
                        }
                    ],
                    "artifacts": ["traceability/acceptance-records.json"],
                    "artifact_hashes": {
                        "traceability/acceptance-records.json": hashlib.sha256(
                            (self.root / "traceability/acceptance-records.json").read_bytes()
                        ).hexdigest()
                    },
                    "uncovered": ["No application or real-world validation."],
                    "source_scope": source_scope,
                    "source_tree_git_sha256": checker._tree_fingerprint(
                        self.root, source_scope, fixture_commit
                    ),
                    "source_tree_worktree_sha256": checker._tree_fingerprint(
                        self.root, source_scope
                    ),
                }
            )
        path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
        checker.refresh(
            self.root,
            "隔离测试仓库已重绑定验收记录到临时基线提交，源码内容保持一致。",
        )

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

    def test_supporting_design_change_has_impact(self):
        path = self.root / "design/knowledge-ui.svg"
        path.write_text(path.read_text() + "\n<!-- changed design fixture -->\n")
        self.assertTrue(any("supporting artifact fingerprint stale" in e for e in checker.validate(self.root)))
        result = checker.impact(self.root)
        self.assertIn("design/knowledge-ui.svg", result["changed_supporting_artifacts"])
        self.assertIn("RQ-034", [r["requirement"] for r in result["affected"]])

    def test_dead_contract_ref_cannot_be_refreshed(self):
        path = self.root / "schemas/knowledge.contracts.v1.schema.json"
        data = json.loads(path.read_text())
        data["$defs"]["CreateUploadRequest"]["properties"]["broken"] = {"$ref": "#/$defs/MissingContract"}
        path.write_text(json.dumps(data))
        self.assertTrue(any("unresolved schema ref" in e for e in checker.validate(self.root)))
        with self.assertRaises(ValueError):
            checker.refresh(self.root, "验证合同中的无效引用，刷新不得隐藏该结构错误。")

    def test_supporting_artifact_requires_known_requirement(self):
        data = self.manifest()
        data["supporting_artifacts"][0]["requirement_ids"] = ["RQ-999"]
        self.write_manifest(data)
        self.assertTrue(any("unmapped supporting artifact requirement" in e for e in checker.validate(self.root)))

    def test_refresh_requires_substantive_note(self):
        with self.assertRaises(ValueError):
            checker.refresh(self.root, "ok")

    def test_verified_requires_acceptance_record(self):
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-030")
        requirement["implementation_status"] = "verified"
        self.write_manifest(data)
        self.assertTrue(
            any(
                "RQ-030: verified requires passed acceptance evidence" in error
                for error in checker.validate(self.root)
            )
        )

    def test_mock_evidence_cannot_verify_real_outsourcing_requirement(self):
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-033")
        requirement["implementation_paths"] = ["tools/check_traceability.py"]
        self.write_manifest(data)
        evidence_path = self.root / "traceability/acceptance-records.json"
        evidence = json.loads(evidence_path.read_text())
        record = evidence["records"][0]
        record["requirements"].append("RQ-033")
        record["technical_refs"] = sorted(
            set(record["technical_refs"]) | set(requirement["technical_refs"])
        )
        record["acceptance_refs"] = sorted(
            set(record["acceptance_refs"]) | set(requirement["acceptance_refs"])
        )
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        data = self.manifest()
        for artifact in data["supporting_artifacts"]:
            if artifact["path"] == "traceability/acceptance-records.json":
                artifact["sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        self.write_manifest(data)
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-033")
        requirement["implementation_status"] = "verified"
        self.write_manifest(data)
        errors = checker.validate(self.root)
        self.assertTrue(
            any("RQ-033: required real_outsourcing validation" in error for error in errors)
        )

    def test_source_scope_detects_budget_code_change(self):
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-002")
        requirement["implementation_paths"] = [
            "services/core/src/medical_one_person/application/budgets.py"
        ]
        self.write_manifest(data)
        relative = requirement["implementation_paths"][0]
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.project / relative, target)
        subprocess.run(["git", "add", relative], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "include budget source"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        evidence_path = self.root / "traceability/acceptance-records.json"
        evidence = json.loads(evidence_path.read_text())
        record = evidence["records"][0]
        if "RQ-002" not in record["requirements"]:
            record["requirements"].append("RQ-002")
        record["technical_refs"] = sorted(
            set(record["technical_refs"]) | set(requirement["technical_refs"])
        )
        record["acceptance_refs"] = sorted(
            set(record["acceptance_refs"]) | set(requirement["acceptance_refs"])
        )
        for record in evidence["records"]:
            record["source_commit"] = source_commit
            record["source_tree_git_sha256"] = checker._tree_fingerprint(
                self.root,
                record["source_scope"],
                source_commit,
            )
            record["source_tree_worktree_sha256"] = checker._tree_fingerprint(
                self.root,
                record["source_scope"],
            )
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        checker.refresh(
            self.root,
            "隔离反例：预算代码已被源码树范围覆盖，修改后必须使证据待更新。",
        )
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-002")
        requirement["implementation_status"] = "verified"
        self.write_manifest(data)
        self.assertEqual(checker.validate(self.root), [])
        path = self.root / requirement["implementation_paths"][0]
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "budget.reserved_amount + budget.spent_amount + amount > budget.limit_amount",
                "False",
                1,
            ),
            encoding="utf-8",
        )
        self.assertTrue(
            any(
                "implementation tree changed after acceptance" in error
                for error in checker.validate(self.root)
            )
        )

    def test_implemented_requires_tracked_git_path(self):
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-006")
        requirement["implementation_paths"].append("services/not-tracked.py")
        self.write_manifest(data)
        self.assertTrue(
            any(
                "implementation path is not tracked by Git" in error
                for error in checker.validate(self.root)
            )
        )

    def test_tree_fingerprint_uses_repository_relative_paths_from_subdirectory(self):
        outer = self.root / "nested-project"
        outer.mkdir()
        source = self.project / "services/core/src/medical_one_person/agents/runner.py"
        target = outer / "services/core/src/medical_one_person/agents/runner.py"
        target.parent.mkdir(parents=True)
        shutil.copyfile(source, target)
        subprocess.run(["git", "add", "nested-project"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "add nested project"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        committed = checker._tree_fingerprint(
            outer,
            ["services/core/src"],
            commit,
        )
        worktree = checker._tree_fingerprint(outer, ["services/core/src"])
        self.assertNotEqual(committed, hashlib.sha256(b"").hexdigest())
        self.assertEqual(committed, worktree)

    def test_artifact_hash_detects_post_acceptance_change(self):
        self.assertEqual(checker.validate(self.root), [])
        (self.root / "docs/w01-w18-validation.md").write_text(
            (self.root / "docs/w01-w18-validation.md").read_text(encoding="utf-8")
            + "\n变更后的验收产物。\n",
            encoding="utf-8",
        )
        self.assertTrue(
            any(
                "artifact hash changed" in error
                for error in checker.validate(self.root)
            )
        )

    def test_acceptance_record_detects_post_verification_code_change(self):
        path = "services/core/src/medical_one_person/agents/runner.py"
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        file_sha256 = hashlib.sha256((self.root / path).read_bytes()).hexdigest()
        evidence_path = self.root / "traceability/acceptance-records.json"
        evidence = json.loads(evidence_path.read_text())
        evidence["records"].append(
            {
                "id": "ACC-RQ-006-test",
                "requirements": ["RQ-006"],
                "technical_refs": next(
                    item for item in self.manifest()["requirements"] if item["id"] == "RQ-006"
                )["technical_refs"],
                "work_packages": ["W05", "W17"],
                "acceptance_refs": ["AT-006"],
                "source_commit": source_commit,
                "result": "passed",
                "commands": [
                    {
                        "cwd": "services/core",
                        "command": "pytest tests/integration/test_w05_agents.py",
                        "mode": "mock+postgresql",
                        "started_at": "2026-11-01T00:00:00Z",
                        "finished_at": "2026-11-01T00:01:00Z",
                        "exit_code": 0,
                        "artifacts": [],
                    }
                ],
                "validation_levels": {
                    "mock": {"status": "passed", "evidence": ["pytest"]},
                    "live": {"status": "not_run", "evidence": []},
                    "human_expert": {"status": "not_run", "evidence": []},
                    "real_outsourcing": {
                        "status": "not_applicable",
                        "evidence": [],
                    },
                },
                "code_paths": [{"path": path, "sha256": file_sha256}],
                "artifacts": ["docs/w01-w18-validation.md"],
                "artifact_hashes": {
                    "docs/w01-w18-validation.md": hashlib.sha256(
                        (self.root / "docs/w01-w18-validation.md").read_bytes()
                    ).hexdigest()
                },
                "uncovered": ["No live or human expert verification."],
                "source_scope": ["tools", "services/core/src"],
                "source_tree_git_sha256": checker._tree_fingerprint(
                    self.root,
                    ["tools", "services/core/src"],
                    source_commit,
                ),
                "source_tree_worktree_sha256": checker._tree_fingerprint(
                    self.root,
                    ["tools", "services/core/src"],
                ),
            }
        )
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        checker.refresh(
            self.root,
            "测试验收证据已写入，并刷新其派生指纹；真实验证仍只覆盖mock命令。",
        )
        data = self.manifest()
        requirement = next(item for item in data["requirements"] if item["id"] == "RQ-006")
        requirement["implementation_status"] = "verified"
        self.write_manifest(data)
        self.assertEqual(checker.validate(self.root), [])
        (self.root / path).write_text(
            (self.root / path).read_text(encoding="utf-8") + "\n# later change\n",
            encoding="utf-8",
        )
        self.assertTrue(
            any(
                "implementation changed after tested source" in error
                for error in checker.validate(self.root)
            )
        )

    def test_reviewed_rebaseline_passes_structural_check(self):
        self.mutate("最高思想.md", "| D-018 | 科学研究优先", "| D-018 | 科学研究应优先")
        path = self.root / "技术路线与实施路径.md"
        path.write_text(path.read_text() + "\n同步说明：本次为措辞澄清，来源准入实现保持TR-09规定。\n")
        checker.refresh(self.root, "已核对来源准入仅为措辞澄清；技术说明已同步，应用状态仍为未实现。")
        self.assertEqual(checker.validate(self.root), [])

if __name__ == "__main__":
    unittest.main()


