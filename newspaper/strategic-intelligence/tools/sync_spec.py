#!/usr/bin/env python3
"""Deterministic projections of CANONICAL_SYSTEM_SPEC_V5.md; no LLM/network."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

SPEC = "CANONICAL_SYSTEM_SPEC_V5.md"
OUTPUTS = ("README.md", "AGENTS.md", "runtime_contract.json", "问题.md",
           "technical_trace.json", "TECHNICAL_TRACE.md", "work_plan.json", "WORK_PLAN.md")
ROOT = Path(__file__).resolve().parents[1]
_trace_spec = importlib.util.spec_from_file_location("technical_trace", ROOT / "tools/technical_trace.py")
trace = importlib.util.module_from_spec(_trace_spec)
_trace_spec.loader.exec_module(trace)
_plan_spec = importlib.util.spec_from_file_location("work_plan", ROOT / "tools/work_plan.py")
work_plan = importlib.util.module_from_spec(_plan_spec)
_plan_spec.loader.exec_module(work_plan)


def block(text: str, name: str) -> str:
    start, end = f"<!-- BEGIN {name} -->", f"<!-- END {name} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Missing or duplicate canonical block: {name}")
    a, b = text.index(start) + len(start), text.index(end)
    if b <= a:
        raise ValueError(f"Invalid canonical block order: {name}")
    return text[a:b].strip() + "\n"


def relative_name(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"Invalid managed path: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or p.as_posix() != value or value == ".":
        raise ValueError(f"Unsafe managed path: {value}")
    return value


def projected(root: Path) -> dict[str, bytes]:
    raw = (root / SPEC).read_bytes()
    text = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    machine = block(text, "MACHINE_CONTRACT").strip()
    if not machine.startswith("```json\n") or not machine.endswith("\n```"):
        raise ValueError("Machine contract must be a fenced JSON object")
    contract = json.loads(machine[len("```json\n"):-len("\n```")])
    if contract.get("schema_version") != 1 or contract.get("canonical") != SPEC:
        raise ValueError("Unsupported canonical contract")
    if contract.get("generated_files") != list(OUTPUTS):
        raise ValueError("Generated outputs require explicit generator support")
    for key in ("manual_code_files", "data_files", "evidence_dirs"):
        if not isinstance(contract.get(key), list):
            raise ValueError(f"Missing inventory: {key}")
        for path in contract[key]:
            relative_name(path)
    probe = contract["source_probe"]
    if probe.get("selection_mode") != "explicit_source_ids" or "default_limit" in probe:
        raise ValueError("source_probe requires explicit_source_ids and no implicit default_limit")
    for key in ("max_bytes", "timeout_seconds"):
        if type(probe.get(key)) is not int or probe[key] <= 0:
            raise ValueError(f"Invalid source_probe.{key}")
    for key in ("default_delay_seconds", "minimum_delay_seconds"):
        if type(probe.get(key)) not in (int, float) or not (0 < probe[key] < float("inf")):
            raise ValueError(f"Invalid source_probe.{key}")
    if probe["default_delay_seconds"] < probe["minimum_delay_seconds"]:
        raise ValueError("Default delay is below minimum delay")
    relative_name(probe["default_output"])
    result = {}
    for filename in ("README.md", "AGENTS.md", "问题.md"):
        body = block(text, f"GENERATED {filename}")
        body = body.replace("{{SPEC_FILE}}", SPEC).replace("{{SPEC_SHA256}}", digest)
        if filename == "问题.md":
            if body.count("{{ISSUE_LEDGER}}") != 1:
                raise ValueError("Issue projection must include exactly one canonical ledger")
            # Validate template placeholders before inserting the verbatim ledger;
            # future issue evidence may legitimately contain literal braces.
            template = body.replace("{{ISSUE_LEDGER}}", "")
            if "{{" in template or "}}" in template:
                raise ValueError(f"Unknown template placeholder in {filename}")
            result[filename] = body.replace("{{ISSUE_LEDGER}}", block(text, "ISSUE_LEDGER").rstrip("\n")).encode("utf-8")
            continue
        if "{{" in body or "}}" in body:
            raise ValueError(f"Unknown template placeholder in {filename}")
        result[filename] = body.encode("utf-8")
    contract["spec_sha256"] = digest
    result[OUTPUTS[2]] = (json.dumps(contract, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    technical = trace.project(text, digest)
    result.update(technical)
    result.update(work_plan.project(text, digest, json.loads(technical["technical_trace.json"]), trace))
    return result


def inventory_errors(root: Path, outputs: dict[str, bytes]) -> list[str]:
    c = json.loads(outputs[OUTPUTS[2]])
    allowed = {SPEC, *OUTPUTS, *c["manual_code_files"], *c["data_files"]}
    errors = []
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            errors.append(f"Symlink is not a managed artifact: {rel}")
            continue
        if not p.is_file():
            continue
        if "__pycache__" in p.parts and p.suffix == ".pyc":
            continue
        if rel in allowed:
            continue
        if p.suffix == ".json" and any(rel.startswith(d + "/") for d in c["evidence_dirs"]):
            continue
        errors.append(f"Unregistered file; merge rules into {SPEC} or register necessary data/code: {rel}")
    for rel in sorted(allowed - set(OUTPUTS)):
        if not (root / rel).is_file():
            errors.append(f"Missing registered file: {rel}")
    # Only validate live local links in the canonical text, never rewrite historical records.
    text = (root / SPEC).read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^\s)]+)\)", text):
        if "://" in target or target.startswith(("#", "mailto:", "{{")):
            continue
        path = target.split("#", 1)[0]
        if path and not (root / path).exists() and path not in OUTPUTS:
            errors.append(f"Broken canonical local link: {target}")
    return errors


def synchronize(root: Path = ROOT, write: bool = False) -> list[str]:
    outputs = projected(root)
    errors = inventory_errors(root, outputs)
    if errors:
        return errors  # Never delete unknown files or partially update an invalid inventory.
    for name, expected in outputs.items():
        p = root / name
        actual = p.read_bytes() if p.exists() else None
        if actual != expected:
            if write:
                p.write_bytes(expected)
            else:
                errors.append(f"Stale generated file: {name}; run tools/sync_spec.py --write")
    return errors


def assert_current(root: Path = ROOT) -> dict:
    errors = synchronize(root, write=False)
    if errors:
        raise ValueError("\n".join(errors))
    return json.loads((root / OUTPUTS[2]).read_text(encoding="utf-8"))


def assert_technical_current(root: Path = ROOT, node_ids=None) -> dict:
    """Check binding freshness only; never authorize research/publication."""
    assert_current(root)
    result = json.loads((root / "technical_trace.json").read_text(encoding="utf-8"))
    errors = trace.pending_errors(result, node_ids)
    if errors:
        raise ValueError("\n".join(errors))
    return result


def assert_work_plan_current(root: Path = ROOT, work_ids=None) -> dict:
    """Check checklist correspondence, not completion, stage approval or permission."""
    assert_current(root)
    result = json.loads((root / "work_plan.json").read_text(encoding="utf-8"))
    errors = work_plan.pending_errors(result, work_ids)
    if errors:
        raise ValueError("\n".join(errors))
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--check-technical", action="store_true")
    modes.add_argument("--check-work-plan", action="store_true")
    p.add_argument("--node", action="append", help="T/R ID to check; repeat to select several")
    p.add_argument("--work", action="append", help="W/G ID to check; repeat to select several")
    args = p.parse_args()
    try:
        if args.node and not args.check_technical:
            raise ValueError("--node requires --check-technical")
        if args.work and not args.check_work_plan:
            raise ValueError("--work requires --check-work-plan")
        if args.check_technical:
            assert_technical_current(node_ids=args.node)
            errors = []
        elif args.check_work_plan:
            assert_work_plan_current(work_ids=args.work)
            errors = []
        else:
            errors = synchronize(write=args.write)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        errors = [str(exc)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Canonical projections synchronized; inventory and links checked.")
    if args.check_technical:
        print("Technical bindings match reviewed versions; implementation/content/authorization not verified.")
    if args.check_work_plan:
        print("Work-plan bindings match reviewed versions; completion/stage/content/authorization not verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
