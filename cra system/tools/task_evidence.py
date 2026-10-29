"""Bind verified task claims to source content and successful GitHub Actions jobs.

This is engineering provenance, not clinical validation or proof of test quality.
W00 is the historical bootstrap only. Every later verified task needs live evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

WORKFLOW = ".github/workflows/cra-system.yml"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def subject_digest(root, task, profile, reader=None):
    root = root.resolve()
    files = {}
    for item in task["deliverables"]:
        relative = item["path"]
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("deliverable outside project")
        raw = reader(relative) if reader else path.read_bytes()
        if not raw.strip():
            raise ValueError("empty deliverable: " + relative)
        files[relative] = hashlib.sha256(raw).hexdigest()
    for prefix in profile.get("binding_paths", []):
        base = (root / prefix).resolve()
        if not base.is_relative_to(root):
            raise ValueError("evidence binding outside project")
        if reader:
            paths = reader.paths(prefix)
        elif base.is_file():
            paths = [prefix]
        else:
            paths = [p.relative_to(root).as_posix() for p in base.rglob("*")
                     if p.is_file() and not set(p.parts).intersection({"__pycache__", ".venv", "node_modules", ".pytest_cache", "dist"})
                     and p.suffix != ".pyc"]
        if not paths:
            raise ValueError("evidence binding has no files: " + prefix)
        for relative in sorted(paths):
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                raise ValueError("bound source outside project")
            raw = reader(relative) if reader else path.read_bytes()
            files[relative] = hashlib.sha256(raw).hexdigest()
    requirement_data = (reader("theory/requirements.json") if reader else (root / "theory/requirements.json").read_bytes())
    selected = [r for r in json.loads(requirement_data)["requirements"] if r["id"] in task["requirement_ids"]]
    spec_keys = ("depends_on", "clinical_goal", "deliverables", "contracts", "steps", "done_when", "scenario_ids", "requirement_ids")
    spec = {key: task[key] for key in spec_keys}
    spec["verification"] = [{k: c[k] for k in ("command", "purpose")} for c in task["verification"]]
    return digest({"schema": 1, "task_id": task["id"], "spec": spec, "profile": profile, "requirements": selected, "files": files})


def record_errors(root, task, profile):
    if task["status"] != "verified" or task["id"] == "CRA-W00":
        return []
    errors, tid = [], task["id"]
    record = task.get("completion_evidence")
    if not isinstance(record, dict):
        return [tid + ": structured completion_evidence required; self-reported text is insufficient"]
    if record.get("kind") != "github_actions" or record.get("profile_id") != tid:
        errors.append(tid + ": invalid completion evidence kind/profile")
    if not isinstance(record.get("run_id"), int) or isinstance(record.get("run_id"), bool) or record["run_id"] <= 0:
        errors.append(tid + ": invalid evidence run ID")
    if not re.fullmatch(r"[0-9a-f]{40}", str(record.get("tested_commit", ""))):
        errors.append(tid + ": exact tested commit required")
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("subject_digest", ""))):
        errors.append(tid + ": evidence subject digest required")
    try:
        current = subject_digest(root, task, profile)
        if record.get("subject_digest") != current:
            errors.append(tid + ": completion evidence is stale for current source/specification")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(tid + ": evidence source unavailable or empty: " + str(exc))
    return errors


def remote_errors(repository, task, profile, get_json):
    tid, record = task["id"], task["completion_evidence"]
    run = get_json(f"/repos/{repository}/actions/runs/{record['run_id']}")
    errors = []
    if run.get("repository", {}).get("full_name") != repository:
        errors.append(tid + ": evidence run is from another repository")
    if run.get("head_sha") != record["tested_commit"]:
        errors.append(tid + ": evidence run commit mismatch")
    if run.get("path") != WORKFLOW or run.get("event") != "push":
        errors.append(tid + ": untrusted evidence workflow/event")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        errors.append(tid + ": evidence run did not complete successfully")
    jobs = []
    for page in range(1, 11):
        data = get_json(f"/repos/{repository}/actions/runs/{record['run_id']}/jobs?per_page=100&page={page}")
        jobs.extend(data["jobs"])
        if len(jobs) >= data["total_count"]:
            break
    matching = [j for j in jobs if j.get("name") == profile["required_job"]]
    if len(matching) != 1:
        errors.append(tid + ": required task-specific CI job missing or ambiguous")
    else:
        job = matching[0]
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            errors.append(tid + ": task-specific job failed or was skipped")
        for name in profile["required_steps"]:
            steps = [s for s in job.get("steps", []) if s.get("name") == name]
            if len(steps) != 1 or steps[0].get("status") != "completed" or steps[0].get("conclusion") != "success":
                errors.append(tid + ": required CI step missing/failed/skipped: " + name)
    return errors


def verify(root, repository, get_json):
    tasks = json.loads((root / "plan/tasks.json").read_text())["tasks"]
    profiles = {p["task_id"]: p for p in json.loads((root / "plan/implementation.json").read_text())["verification_profiles"]}
    errors, checked = [], 0
    for task in tasks:
        if task["status"] != "verified" or task["id"] == "CRA-W00":
            continue
        checked += 1
        profile = profiles[task["id"]]
        local = record_errors(root, task, profile)
        if local:
            errors.extend(local)
            continue
        sha = task["completion_evidence"]["tested_commit"]
        ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=root, capture_output=True)
        if ancestor.returncode:
            errors.append(task["id"] + ": tested commit is unavailable or not an ancestor; fetch history")
            continue
        def reader(relative):
            value = subprocess.run(["git", "show", f"{sha}:cra system/{relative}"], cwd=root, capture_output=True)
            if value.returncode:
                raise ValueError("tested source missing: " + relative)
            return value.stdout
        def paths(prefix):
            result = subprocess.run(["git", "ls-tree", "-rz", "--name-only", sha, "--", "cra system/" + prefix], cwd=root, capture_output=True)
            if result.returncode:
                raise ValueError("tested source listing unavailable")
            return [p.removeprefix("cra system/") for p in result.stdout.decode("utf-8").split(chr(0)) if p]
        reader.paths = paths
        try:
            tested = subject_digest(root, task, profile, reader)
            if tested != task["completion_evidence"]["subject_digest"]:
                errors.append(task["id"] + ": tested source differs from current evidence subject")
                continue
            # The producer must have used the same specification, not a later invented test profile.
            tested_tasks = json.loads(reader("plan/tasks.json"))["tasks"]
            tested_task = next(t for t in tested_tasks if t["id"] == task["id"])
            tested_profiles = json.loads(reader("plan/implementation.json"))["verification_profiles"]
            tested_profile = next(p for p in tested_profiles if p["task_id"] == task["id"])
            if subject_digest(root, tested_task, tested_profile, reader) != tested:
                errors.append(task["id"] + ": evidence specification/profile was changed after the tested commit")
                continue
            errors.extend(remote_errors(repository, task, profile, get_json))
        except (OSError, ValueError, KeyError, StopIteration, TypeError):
            errors.append(task["id"] + ": unable to verify source or authoritative GitHub evidence; no fallback to a self-report")
    return errors, checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "pyzz58/gpt-recommendations"))
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("repository must be owner/name")
    cache = {}
    def get_json(path):
        if path in cache:
            return cache[path]
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "cra-task-evidence"}
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=15) as response:
            cache[path] = json.load(response)
            return cache[path]
    try:
        errors, checked = verify(Path(__file__).resolve().parents[1], args.repository, get_json)
    except (OSError, ValueError, KeyError, TypeError):
        print("EVIDENCE ERROR: authoritative verification unavailable; no task was approved.")
        return 1
    for error in errors:
        print("ERROR:", error)
    print(json.dumps({"task_evidence_checked": checked, "historical_bootstrap": "CRA-W00", "authoritative_verification": not errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
