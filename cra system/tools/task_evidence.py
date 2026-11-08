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
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.request import HTTPRedirectHandler, build_opener
from review_gate import load_findings, task_evidence_errors, validate_findings

WORKFLOW = ".github/workflows/cra-system.yml"


class _SafeLogRedirectHandler(HTTPRedirectHandler):
    """Do not forward a GitHub token to the signed log-storage host."""

    def redirect_request(
        self, req, fp, code, msg, headers, newurl
    ):
        redirected = super().redirect_request(
            req, fp, code, msg, headers, newurl
        )
        if (
            redirected is not None
            and urlsplit(req.full_url).netloc
            != urlsplit(newurl).netloc
        ):
            redirected.remove_header("Authorization")
        return redirected


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _worktree_binding_paths(root, prefix):
    """List source files that Git considers part of the worktree.

    Runtime output can appear below a bound directory (for example Playwright
    test-results). Ignored files must not change evidence for otherwise
    unchanged source, while untracked, non-ignored additions remain binding.
    """
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            prefix,
        ],
        cwd=root,
        capture_output=True,
    )
    if result.returncode:
        # Synthetic traceability fixtures and standalone source snapshots do
        # not always have Git metadata. Authoritative task verification still
        # requires an exact Git commit; this fallback only preserves local
        # digesting for those isolated callers.
        base = (root / prefix).resolve()
        if base.is_file():
            return [prefix]
        return sorted(
            path.relative_to(root).as_posix()
            for path in base.rglob("*")
            if path.is_file()
            and not set(path.parts).intersection(
                {
                    "__pycache__",
                    ".venv",
                    "node_modules",
                    ".pytest_cache",
                    "dist",
                }
            )
            and path.suffix != ".pyc"
        )
    return sorted(
        {
            relative
            for relative in result.stdout.decode("utf-8").split("\0")
            if relative
        }
    )


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
        else:
            paths = _worktree_binding_paths(root, prefix)
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


def _normalise_job_log(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


def _job_steps_pending(payload, required_by_job=None):
    """GitHub can finish a run before its job step arrays are backfilled."""
    jobs = payload.get("jobs", [])
    if required_by_job is None:
        return any(
            job.get("status") == "completed" and not job.get("steps")
            for job in jobs
        )
    jobs_by_name = {
        job.get("name"): job
        for job in jobs
        if job.get("name")
    }
    for job_name, required_steps in required_by_job.items():
        job = jobs_by_name.get(job_name)
        if job is None or job.get("status") != "completed":
            return True
        if job.get("conclusion") != "success":
            continue
        steps_by_name = {
            step.get("name"): step
            for step in job.get("steps", [])
            if step.get("name")
        }
        for step_name in required_steps:
            step = steps_by_name.get(step_name)
            if step is None:
                return True
            if (
                step.get("status") != "completed"
                or step.get("conclusion") != "success"
            ):
                return False
    return False


def remote_finding_errors(
    root, repository, get_json, get_text
):
    """Verify each closed review record against its exact successful CI job."""
    payload = load_findings(root)
    profiles = json.loads(
        (root / "plan/implementation.json").read_text()
    )["verification_profiles"]
    profiles_by_job = {
        profile["required_job"]: profile for profile in profiles
    }
    errors, checked = [], 0
    jobs_cache = {}
    logs_cache = {}
    for finding in payload["findings"]:
        if finding.get("status") != "closed":
            continue
        checked += 1
        fid = finding["id"]
        evidence = finding["closure_evidence"]
        run_id = evidence["run_id"]
        run = get_json(f"/repos/{repository}/actions/runs/{run_id}")
        if run.get("repository", {}).get("full_name") != repository:
            errors.append(fid + ": closure CI run is from another repository")
        if run.get("head_sha") != evidence["tested_commit"]:
            errors.append(fid + ": closure CI commit mismatch")
        if run.get("path") != WORKFLOW or run.get("event") != "push":
            errors.append(fid + ": closure CI workflow/event is not trusted")
        if (
            run.get("status") != "completed"
            or run.get("conclusion") != "success"
        ):
            errors.append(fid + ": closure CI run is not successful")
        if run_id not in jobs_cache:
            jobs = []
            for page in range(1, 11):
                data = get_json(
                    f"/repos/{repository}/actions/runs/{run_id}/jobs"
                    f"?per_page=100&page={page}"
                )
                jobs.extend(data["jobs"])
                if len(jobs) >= data["total_count"]:
                    break
            jobs_cache[run_id] = jobs
        matching = [
            job
            for job in jobs_cache[run_id]
            if job.get("name") == evidence["job_name"]
        ]
        if len(matching) != 1:
            errors.append(
                fid + ": closure task-specific CI job missing or ambiguous"
            )
            continue
        job = matching[0]
        if (
            job.get("status") != "completed"
            or job.get("conclusion") != "success"
        ):
            errors.append(fid + ": closure task-specific CI job failed")
        profile = profiles_by_job.get(evidence["job_name"])
        if profile is None:
            errors.append(fid + ": closure CI job has no verification profile")
        else:
            for name in profile["required_steps"]:
                steps = [
                    step
                    for step in job.get("steps", [])
                    if step.get("name") == name
                ]
                if (
                    len(steps) != 1
                    or steps[0].get("status") != "completed"
                    or steps[0].get("conclusion") != "success"
                ):
                    errors.append(
                        fid
                        + ": closure required CI step missing/failed: "
                        + name
                    )
        job_id = job.get("id")
        if not isinstance(job_id, int) or isinstance(job_id, bool):
            errors.append(fid + ": closure CI job id required for log binding")
            continue
        if job_id not in logs_cache:
            logs_cache[job_id] = _normalise_job_log(
                get_text(
                    f"/repos/{repository}/actions/jobs/{job_id}/logs"
                )
            )
        log = logs_cache[job_id]
        for test_case in evidence["test_cases"]:
            if test_case not in log:
                errors.append(
                    fid
                    + ": closure test case not found in successful CI log: "
                    + test_case
                )
    return errors, checked


def verify(root, repository, get_json, get_text):
    tasks = json.loads((root / "plan/tasks.json").read_text())["tasks"]
    profiles = {p["task_id"]: p for p in json.loads((root / "plan/implementation.json").read_text())["verification_profiles"]}
    errors = [
        "review gate: " + error
        for error in validate_findings(root)
    ]
    findings_checked = 0
    if not errors:
        finding_errors, findings_checked = remote_finding_errors(
            root, repository, get_json, get_text
        )
        errors.extend(finding_errors)
    checked = 0
    for task in tasks:
        if task["status"] != "verified" or task["id"] == "CRA-W00":
            continue
        checked += 1
        errors.extend(task_evidence_errors(root, task))
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
            result = subprocess.run(["git", "ls-tree", "--full-tree", "-rz", "--name-only", sha, "--", "cra system/" + prefix], cwd=root, capture_output=True)
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
    return errors, checked, findings_checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "pyzz58/gpt-recommendations"))
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("repository must be owner/name")
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / "plan/tasks.json").read_text())["tasks"]
    profiles = {
        profile["task_id"]: profile
        for profile in json.loads(
            (root / "plan/implementation.json").read_text()
        )["verification_profiles"]
    }
    required_by_run = {}
    for task in tasks:
        if task["status"] != "verified" or task["id"] == "CRA-W00":
            continue
        record = task["completion_evidence"]
        profile = profiles[task["id"]]
        required_by_run.setdefault(record["run_id"], {})[
            profile["required_job"]
        ] = set(profile["required_steps"])
    cache = {}
    def get_json(path):
        if path in cache:
            return cache[path]
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "cra-task-evidence"}
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        deadline = time.monotonic() + 600
        while True:
            try:
                with urlopen(Request("https://api.github.com" + path, headers=headers), timeout=30) as response:
                    value = json.load(response)
            except (TimeoutError, URLError) as exc:
                if time.monotonic() >= deadline:
                    raise
                print(
                    f"retrying GitHub actions evidence API after {type(exc).__name__}",
                    flush=True,
                )
                time.sleep(10)
                continue
            run_match = re.search(r"/actions/runs/(\d+)/jobs", path)
            if run_match is None:
                break
            run_id = int(run_match.group(1))
            required = required_by_run.get(run_id)
            if not _job_steps_pending(value, required) or time.monotonic() >= deadline:
                break
            print("waiting for GitHub Actions to expose completed job steps", flush=True)
            time.sleep(20)
        cache[path] = value
        return cache[path]
    text_cache = {}
    def get_text(path):
        if path in text_cache:
            return text_cache[path]
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "cra-task-evidence"}
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        opener = build_opener(_SafeLogRedirectHandler())
        with opener.open(
            Request("https://api.github.com" + path, headers=headers),
            timeout=30,
        ) as response:
            text_cache[path] = response.read().decode("utf-8", errors="replace")
            return text_cache[path]
    try:
        errors, checked, findings_checked = verify(
            root,
            args.repository,
            get_json,
            get_text,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            "EVIDENCE ERROR: authoritative verification unavailable; "
            f"no task was approved ({type(exc).__name__}: {exc})."
        )
        return 1
    for error in errors:
        print("ERROR:", error)
    print(json.dumps({"task_evidence_checked": checked, "review_findings_checked": findings_checked, "historical_bootstrap": "CRA-W00", "authoritative_verification": not errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
