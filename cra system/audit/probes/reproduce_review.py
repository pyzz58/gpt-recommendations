"""Diagnostic review probes. A successful run means observations were recorded, not defects fixed."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from traceability_lib import render_views, validate


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=repo, text=True, encoding="utf-8", capture_output=True, check=True)
    return completed.stdout.strip()


def manufactured_completion_probe() -> dict:
    with tempfile.TemporaryDirectory(prefix="cra-audit-") as temporary:
        repo = Path(temporary)
        project = repo / "cra system"
        shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__", "dist"))
        git(repo, "init", "-q")
        git(repo, "add", "--", "cra system")
        git(repo, "-c", "user.name=CRA Audit Probe", "-c", "user.email=audit@example.invalid", "commit", "-q", "-m", "synthetic audit baseline")
        baseline = git(repo, "rev-parse", "HEAD")
        data_path = project / "plan/tasks.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        task = next(item for item in data["tasks"] if item["id"] == "CRA-W01")
        missing_paths = []
        for item in task["deliverables"]:
            path = project / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
            missing_paths.append(item["path"])
        task["status"] = "verified"
        task["evidence"] = ["SYNTHETIC NEGATIVE PROBE: no implementation or application commands were run."]
        for check in task["verification"]:
            check["availability"] = "available"
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for relative, content in render_views(project).items():
            path = project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        errors = validate(project, base_ref=baseline)
        return {
            "finding_id": "CRA-AUD-001",
            "observation": "accepted_unimplemented_task" if not errors else "rejected_by_current_guard",
            "placeholder_files_in_temporary_repo": missing_paths,
            "application_commands_executed": False,
            "validator_errors": errors,
            "meaning": "This is a diagnostic reproduction, never evidence that CRA-W01 was implemented.",
        }


def dependency_phase_probe() -> dict:
    tasks = json.loads((ROOT / "plan/tasks.json").read_text(encoding="utf-8"))["tasks"]
    modules = json.loads((ROOT / "traceability/modules.json").read_text(encoding="utf-8"))["modules"]
    position = {task["id"]: index for index, task in enumerate(tasks)}
    first = {module["id"]: min(module["task_ids"], key=position.get) for module in modules}
    edges = []
    for module in modules:
        for dependency in module["depends_on"]:
            if position[first[dependency]] > position[first[module["id"]]]:
                edges.append({
                    "module": module["id"], "starts_at": first[module["id"]],
                    "declared_dependency": dependency, "dependency_starts_at": first[dependency],
                })
    return {
        "finding_id": "CRA-AUD-006", "observation": "phase_dependency_requires_clarification" if edges else "no_later_hard_dependency_found",
        "edges": edges, "meaning": "Not proof of a runtime cycle; distinguish hard dependencies from later optional capabilities.",
    }


def main():
    baseline_errors = validate(ROOT)
    if baseline_errors:
        print(json.dumps({"baseline_errors": baseline_errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "purpose": "diagnostic_review_not_acceptance",
        "reviewed_baseline": "60be8e67f4fa941a4663541351253296e5ee06a4",
        "results": [manufactured_completion_probe(), dependency_phase_probe()],
        "real_tasks_modified": False,
        "external_services_called": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
