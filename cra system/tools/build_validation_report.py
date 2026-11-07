"""Validate and summarize CRA V1A evidence without inventing trial results.

The report is intentionally an engineering summary. A provider passing a
synthetic sample does not establish clinical validation, and old provider
evidence is not relabelled as an authorized CRA workflow-time comparison.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "validation/capability-manifest.json"
QUALITY = "architecture/QUALITY.md"
TASKS = "plan/tasks.json"

CAPABILITY_STATUSES = {
    "implemented",
    "configured",
    "validated",
    "disabled",
}
SCENARIO_STATUSES = {
    "synthetic_validated",
    "engineering_verified",
    "not_evaluated",
    "unmet",
}
EVALUATION_GROUPS = {
    "synthetic_development",
    "synthetic_independent",
    "engineering_record",
    "not_run",
}
EVIDENCE_KINDS = {"test", "document", "ci_run"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario_ids_from_quality(root: Path) -> set[str]:
    text = (root / QUALITY).read_text(encoding="utf-8")
    return set(re.findall(r"\bCRA-S\d{2}\b", text))


def _w13_task(root: Path) -> dict[str, Any]:
    tasks = _load(root / TASKS)["tasks"]
    return next(task for task in tasks if task["id"] == "CRA-W13")


def _relative_path_error(root: Path, value: Any, label: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return label + ": path is required"
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        return label + ": path escapes project"
    if not path.is_file():
        return label + ": file does not exist: " + value
    return None


def _evidence_errors(
    root: Path, evidence: Any, label: str
) -> list[str]:
    if not isinstance(evidence, list) or not evidence:
        return [label + ": at least one evidence item is required"]
    errors: list[str] = []
    for index, item in enumerate(evidence):
        prefix = f"{label}[{index}]"
        if not isinstance(item, dict):
            errors.append(prefix + ": evidence must be an object")
            continue
        kind = item.get("kind")
        if kind not in EVIDENCE_KINDS:
            errors.append(prefix + ": invalid evidence kind")
            continue
        if kind in {"test", "document"}:
            path = item.get("path")
            if error := _relative_path_error(root, path, prefix):
                errors.append(error)
            elif kind == "test":
                case = item.get("case")
                if not isinstance(case, str) or not case.strip():
                    errors.append(prefix + ": exact test case is required")
                else:
                    method = re.split(r"(?:::|\.)", case)[-1]
                    if not method.startswith("test_"):
                        errors.append(prefix + ": exact test case is required")
                    elif f"def {method}(" not in (
                        root / str(path)
                    ).read_text(encoding="utf-8"):
                        errors.append(
                            prefix + ": test case is not in its test file"
                        )
        else:
            run_id = item.get("run_id")
            if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
                errors.append(prefix + ": CI run_id is required")
            if not isinstance(item.get("job_name"), str) or not item["job_name"].strip():
                errors.append(prefix + ": CI job_name is required")
            commit = str(item.get("tested_commit", ""))
            if not re.fullmatch(r"[0-9a-f]{40}", commit):
                errors.append(prefix + ": exact tested_commit is required")
            steps = item.get("steps")
            if not isinstance(steps, list) or not steps:
                errors.append(prefix + ": successful CI steps are required")
    return errors


def _validate_scenarios(
    root: Path,
    scenarios: Any,
    expected_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(scenarios, list):
        return ["scenarios must be an array"]
    found: list[str] = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            errors.append(f"scenario[{index}] must be an object")
            continue
        sid = scenario.get("id")
        label = f"scenario {sid or index}"
        if not isinstance(sid, str):
            errors.append(label + ": id is required")
            continue
        found.append(sid)
        if not re.fullmatch(r"CRA-S\d{2}", sid):
            errors.append(label + ": invalid id")
        for key in (
            "title",
            "input",
            "expected",
            "expected_basis",
            "sample_source",
            "actual_result",
        ):
            if not isinstance(scenario.get(key), str) or not scenario[key].strip():
                errors.append(f"{label}: {key} is required")
        requirements = scenario.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            errors.append(label + ": requirements are required")
        status = scenario.get("status")
        if status not in SCENARIO_STATUSES:
            errors.append(label + ": invalid status")
        group = scenario.get("evaluation_group")
        if group not in EVALUATION_GROUPS:
            errors.append(label + ": invalid evaluation_group")
        if not isinstance(scenario.get("failures"), list):
            errors.append(label + ": failures array is required")
        uncovered = scenario.get("uncovered")
        if not isinstance(uncovered, list):
            errors.append(label + ": uncovered array is required")
        evidence = scenario.get("evidence", [])
        if status in {"synthetic_validated", "engineering_verified"}:
            errors.extend(_evidence_errors(root, evidence, label))
            if not scenario.get("failures") and uncovered == []:
                # Empty failures and empty limitations are allowed for a
                # narrowly validated scenario, but providers still carry a
                # broader capability boundary.
                pass
        elif evidence:
            errors.extend(_evidence_errors(root, evidence, label))
        if status in {"not_evaluated", "unmet"} and not uncovered:
            errors.append(label + ": non-complete status must state uncovered scope")
        if status == "synthetic_validated" and group not in {
            "synthetic_development",
            "synthetic_independent",
        }:
            errors.append(label + ": synthetic validation needs a synthetic group")
        if status == "engineering_verified" and group != "engineering_record":
            errors.append(label + ": engineering verification needs engineering_record")
    duplicates = sorted(
        sid for sid, count in Counter(found).items() if count > 1
    )
    if duplicates:
        errors.append("duplicate scenarios: " + ", ".join(duplicates))
    missing = sorted(expected_ids - set(found))
    extra = sorted(set(found) - expected_ids)
    if missing:
        errors.append("missing scenarios: " + ", ".join(missing))
    if extra:
        errors.append("unknown scenarios: " + ", ".join(extra))
    return errors


def _validate_capabilities(root: Path, capabilities: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(capabilities, list) or not capabilities:
        return ["capabilities must be a non-empty array"]
    seen: set[str] = set()
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            errors.append(f"capability[{index}] must be an object")
            continue
        cid = capability.get("id")
        label = f"capability {cid or index}"
        if not isinstance(cid, str) or not cid.strip():
            errors.append(label + ": id is required")
            continue
        if cid in seen:
            errors.append(label + ": duplicate id")
        seen.add(cid)
        status = capability.get("status")
        if status not in CAPABILITY_STATUSES:
            errors.append(label + ": invalid status")
        for key in ("title", "human_step", "validated_scope", "limitation"):
            if not isinstance(capability.get(key), str) or not capability[key].strip():
                errors.append(f"{label}: {key} is required")
        if capability.get("automatic_completion_allowed") is not False:
            errors.append(label + ": automatic completion must remain disabled")
        remaining = capability.get("remaining_work")
        if not isinstance(remaining, list):
            errors.append(label + ": remaining_work array is required")
        if status != "disabled":
            errors.extend(
                _evidence_errors(
                    root, capability.get("evidence"), label
                )
            )
        elif remaining == []:
            errors.append(label + ": disabled capability must list remaining work")
        if status == "validated" and capability.get("validated_scope") in {
            "",
            "none",
        }:
            errors.append(label + ": validated capability needs an explicit scope")
        if capability.get("clinical_validation") is True:
            errors.append(
                label
                + ": clinical_validation requires an authorized-trial release record"
            )
    return errors


def _validate_time_study(root: Path, value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["time_study must be an object"]
    if value.get("human_workflow_comparison_status") not in {
        "measured",
        "not_measured",
    }:
        errors.append("time_study: invalid human workflow comparison status")
    if value.get("time_saving_claim") is True and (
        value.get("human_workflow_comparison_status") != "measured"
    ):
        errors.append(
            "time_study: cannot claim savings without a human workflow comparison"
        )
    measurements = value.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        return errors + ["time_study: measurements are required"]
    seen: set[str] = set()
    required_components = {
        "provider_recognition_and_comparison",
        "browser_end_to_end",
        "human_workflow_total",
    }
    for index, item in enumerate(measurements):
        label = f"time_study.measurements[{index}]"
        if not isinstance(item, dict):
            errors.append(label + ": must be an object")
            continue
        mid = item.get("id")
        if not isinstance(mid, str) or not mid:
            errors.append(label + ": id is required")
            continue
        if mid in seen:
            errors.append(label + ": duplicate id")
        seen.add(mid)
        status = item.get("status")
        if status not in {"measured", "not_measured"}:
            errors.append(label + ": invalid status")
        if status == "measured":
            seconds = item.get("seconds")
            if (
                not isinstance(seconds, (int, float))
                or isinstance(seconds, bool)
                or seconds <= 0
            ):
                errors.append(label + ": positive measured seconds are required")
            if not isinstance(item.get("source"), str) or not item["source"].strip():
                errors.append(label + ": evidence source is required")
        elif not isinstance(item.get("reason"), str) or not item["reason"].strip():
            errors.append(label + ": unmeasured item needs a reason")
    missing = required_components - seen
    if missing:
        errors.append(
            "time_study: required components missing: "
            + ", ".join(sorted(missing))
        )
    return errors


def _validate_release(root: Path, value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["release_assessment must be an object"]
    tasks = {
        task["id"]: task for task in _load(root / TASKS)["tasks"]
    }
    trial_ready = value.get("authorized_trial_ready")
    clinical_ready = value.get("clinical_use_ready")
    if not isinstance(trial_ready, bool):
        errors.append("release_assessment: authorized_trial_ready must be boolean")
    if not isinstance(clinical_ready, bool):
        errors.append("release_assessment: clinical_use_ready must be boolean")
    if trial_ready is True:
        if tasks["CRA-W15"].get("status") != "verified":
            errors.append(
                "release_assessment: authorized_trial_ready requires verified W15"
            )
        evidence = value.get("trial_evidence")
        errors.extend(
            _evidence_errors(root, evidence, "release_assessment.trial_evidence")
        ) if evidence else errors.append(
            "release_assessment: authorized trial evidence is required"
        )
    if clinical_ready is True and trial_ready is not True:
        errors.append(
            "release_assessment: clinical_use_ready cannot exceed trial readiness"
        )
    return errors


def validate_manifest(
    root: Path, manifest: dict[str, Any]
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    task = _w13_task(root)
    expected_ids = set(task["scenario_ids"])
    quality_ids = _scenario_ids_from_quality(root)
    if quality_ids != expected_ids:
        errors.append(
            "W13 scenario IDs differ from architecture/QUALITY.md"
        )
    errors.extend(
        _validate_scenarios(
            root, manifest.get("scenarios"), expected_ids
        )
    )
    errors.extend(
        _validate_capabilities(
            root, manifest.get("capabilities")
        )
    )
    errors.extend(
        _validate_time_study(root, manifest.get("time_study"))
    )
    errors.extend(
        _validate_release(root, manifest.get("release_assessment"))
    )
    if manifest.get("clinical_validation") is not False:
        errors.append(
            "clinical_validation must be false without authorized real-use evidence"
        )
    return errors


def build_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    scenarios = manifest["scenarios"]
    capabilities = manifest["capabilities"]
    scenario_counts = Counter(item["status"] for item in scenarios)
    capability_counts = Counter(item["status"] for item in capabilities)
    time_study = manifest["time_study"]
    incomplete_times = [
        item["id"]
        for item in time_study["measurements"]
        if item["status"] != "measured"
    ]
    gaps = [
        {
            "capability_id": item["id"],
            "status": item["status"],
            "limitation": item["limitation"],
            "remaining_work": item["remaining_work"],
        }
        for item in capabilities
        if item["status"] in {"configured", "disabled"}
        or item["remaining_work"]
    ]
    incomplete_scenarios = [
        {
            "scenario_id": item["id"],
            "status": item["status"],
            "actual_result": item["actual_result"],
            "uncovered": item["uncovered"],
        }
        for item in scenarios
        if item["status"] in {"not_evaluated", "unmet"}
    ]
    return {
        "schema_version": 1,
        "source_policy": (
            "deidentified engineering summary; no raw clinical files, patient "
            "identifiers, prompts or trial results are included"
        ),
        "engineering_evidence": True,
        "clinical_validation": False,
        "scenario_summary": dict(sorted(scenario_counts.items())),
        "capability_summary": dict(sorted(capability_counts.items())),
        "release_assessment": copy.deepcopy(
            manifest["release_assessment"]
        ),
        "time_study": {
            "human_workflow_comparison_status": time_study[
                "human_workflow_comparison_status"
            ],
            "time_saving_claim": time_study["time_saving_claim"],
            "measurements": copy.deepcopy(time_study["measurements"]),
            "incomplete_measurements": incomplete_times,
        },
        "capability_gaps": gaps,
        "scenario_gaps": incomplete_scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--manifest", default=MANIFEST)
    args = parser.parse_args()
    path = ROOT / args.manifest
    manifest = _load(path)
    summary = build_summary(manifest)
    if args.check:
        errors = validate_manifest(ROOT, manifest)
        summary["check"] = {
            "passed": not errors,
            "errors": errors,
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.check and summary["check"]["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
