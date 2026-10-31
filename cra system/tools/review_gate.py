"""Review-blocking gate for current engineering findings."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FINDINGS_PATH = "audit/current_findings.json"


def load_findings(root: Path) -> dict[str, Any]:
    return json.loads(
        (root / FINDINGS_PATH).read_text(encoding="utf-8")
    )


def _test_file(relative: str) -> str:
    return relative.split("::", 1)[0]


def validate_findings(root: Path) -> list[str]:
    try:
        payload = load_findings(root)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"review findings unavailable: {exc}"]
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("review findings schema_version must be 1")
    findings = payload.get("findings")
    if not isinstance(findings, list) or not findings:
        return errors + ["review findings must be a non-empty array"]
    seen: set[str] = set()
    for finding in findings:
        fid = str(finding.get("id", "")).strip()
        if not fid:
            errors.append("review finding missing id")
            continue
        if fid in seen:
            errors.append(f"{fid}: duplicate review finding")
        seen.add(fid)
        if finding.get("status") not in {"open", "closed"}:
            errors.append(f"{fid}: invalid status")
        if not isinstance(finding.get("blocking"), bool):
            errors.append(f"{fid}: blocking must be boolean")
        tasks = finding.get("affected_tasks")
        if not isinstance(tasks, list) or not tasks:
            errors.append(f"{fid}: affected_tasks required")
        repair_path = finding.get("repair_path")
        if not repair_path or not (root / repair_path).is_file():
            errors.append(f"{fid}: repair_path missing")
        tests = finding.get("required_tests")
        if not isinstance(tests, list) or not tests:
            errors.append(f"{fid}: required_tests required")
            tests = []
        for relative in tests:
            if not (root / _test_file(str(relative))).is_file():
                errors.append(f"{fid}: required test file missing: {relative}")
        evidence = finding.get("closure_evidence")
        if finding.get("status") == "open":
            if evidence is not None:
                errors.append(f"{fid}: open finding cannot carry closure evidence")
            continue
        if not isinstance(evidence, dict):
            errors.append(f"{fid}: closed finding requires closure_evidence")
            continue
        if evidence.get("kind") != "github_actions":
            errors.append(f"{fid}: closure evidence must be github_actions")
        run_id = evidence.get("run_id")
        if (
            not isinstance(run_id, int)
            or isinstance(run_id, bool)
            or run_id <= 0
        ):
            errors.append(f"{fid}: invalid closure run_id")
        if not re.fullmatch(
            r"[0-9a-f]{40}", str(evidence.get("tested_commit", ""))
        ):
            errors.append(f"{fid}: closure tested_commit required")
        if not str(evidence.get("job_name", "")).strip():
            errors.append(f"{fid}: closure job_name required")
        if evidence.get("acceptance_passed") is not True:
            errors.append(f"{fid}: closure acceptance_passed must be true")
        closure_tests = evidence.get("test_cases")
        if not isinstance(closure_tests, list) or not closure_tests:
            errors.append(f"{fid}: closure test_cases required")
        elif not set(map(str, tests)).issubset(set(map(str, closure_tests))):
            errors.append(f"{fid}: closure evidence omits required tests")
    return errors


def open_findings_for_task(
    payload: dict[str, Any], task_id: str
) -> list[dict[str, Any]]:
    return [
        finding
        for finding in payload.get("findings", [])
        if finding.get("status") == "open"
        and finding.get("blocking") is True
        and task_id in finding.get("affected_tasks", [])
    ]


def apply_review_gate(
    root: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    findings_errors = validate_findings(root)
    if findings_errors:
        return {
            **result,
            "state": "review_required",
            "review_errors": findings_errors,
            "review_findings": [],
            "repair_paths": [],
        }
    task_id = result.get("task_id")
    if not task_id:
        return result
    payload = load_findings(root)
    blockers = open_findings_for_task(payload, str(task_id))
    if not blockers:
        return result
    return {
        **result,
        "state": "review_required",
        "review_findings": [item["id"] for item in blockers],
        "repair_paths": sorted(
            {str(item["repair_path"]) for item in blockers}
        ),
    }


def task_evidence_errors(root: Path, task: dict[str, Any]) -> list[str]:
    if task.get("status") != "verified":
        return []
    try:
        payload = load_findings(root)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{task['id']}: review findings unavailable: {exc}"]
    return [
        f"{task['id']}: blocked by open review finding {item['id']}"
        for item in open_findings_for_task(payload, task["id"])
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=None)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors = validate_findings(root)
    payload = load_findings(root) if not errors else {"findings": []}
    blockers = (
        open_findings_for_task(payload, args.task) if args.task else []
    )
    print(
        json.dumps(
            {
                "findings_valid": not errors,
                "errors": errors,
                "task_id": args.task,
                "review_required": bool(blockers),
                "review_findings": [item["id"] for item in blockers],
                "repair_paths": sorted(
                    {item["repair_path"] for item in blockers}
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
