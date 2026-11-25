"""Independent closure probes against extracted original functions, using explicit doubles.

These probes do not run the application database, provider, or subprocess. A zero exit
code means that the audit ran; consult findings, rather than treating it as acceptance.
The archived probes require the original source-file hashes; use application regression
tests to validate fixes on newer source instead of relabeling this historical evidence.
Run: python3 docs/audits/pr81-closure-probes.py --output /tmp/pr81-probes.json
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MethodType, SimpleNamespace
from uuid import UUID, uuid4

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "services/core/src/medical_one_person"
TESTED_SOURCE = "4320e35bcd18ab8bb4a143853ed7bdce3267d4e7"
BASELINE_HASHES = {
    "application/readiness.py": "ff5bcec4f6e5c6b3a132137389a27a9f96a80c89e51726ae4d58e3391331a2ba",
    "application/tasks.py": "c945c4d6743a51d46310c56e6b838a7d2c22504b2483df1f98e949733c1af81c",
    "worker/__main__.py": "51d29587667c7fb3bc215f53d040f41fd2ca59fe7ce2e867956a2e2c1e429fcf",
    "agents/runner.py": "099548d38291867d78a0a284d02140b6e3fc8f3ff049817d32ffc262956fdec0",
    "application/worker_loop.py": "7630f90f270c86b80c5132b02c7b6b6cdca6a4263b451ecde9dfe8b9fc9cbc64",
}
source_hashes: dict[str, str] = {}


def extract(relative: str, names: set[str], namespace: dict, owner: str | None = None):
    path = SOURCE / relative
    data = path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != BASELINE_HASHES[relative]:
        raise SystemExit(
            f"Archived probe targets {TESTED_SOURCE}; source {relative} changed. "
            "Use application regression tests for newer source."
        )
    source_hashes[str(path.relative_to(PROJECT))] = actual_hash
    tree = ast.parse(data)
    body = tree.body
    if owner:
        body = next(n for n in body if isinstance(n, ast.ClassDef) and n.name == owner).body
    selected = [n for n in body if getattr(n, "name", None) in names]
    assert len(selected) == len(names)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[]))
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


class Field:
    def __eq__(self, other):
        return self

    def desc(self):
        return self


class Query:
    def __init__(self, model):
        self.model = model

    def where(self, *conditions):
        return self

    def order_by(self, *conditions):
        return self


def model():
    return SimpleNamespace(id=Field(), project_id=Field(), created_at=Field(), audit_id=Field())


class Rows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class TaskNotReadyError(Exception):
    pass


class LeaseConflictError(Exception):
    pass


class AgentExecutionFailure(Exception):
    def __init__(self, message, *, error_code, retryable):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable


def probe_audit_scope():
    models = {name: model() for name in ("AuditRun", "AuditFinding", "Task", "TaskDependency")}
    ns = {"__name__": __name__, "dataclass": dataclass, "select": Query, **models}
    extract("application/readiness.py", {"AuditBlocker", "active_audit_blockers", "_task_consumes_target"}, ns)
    target, project_id, upstream_id, downstream_id, unrelated_id = [uuid4() for _ in range(5)]
    run = SimpleNamespace(id=uuid4(), target_type="analysis_run", target_id=target,
                          reviewer_role="A26", review_version=1, linked_task_id=None, state="blocked")
    tasks = [SimpleNamespace(id=upstream_id, input_snapshot={"refs": [{"kind": "analysis", "object_id": str(target)}]}),
             SimpleNamespace(id=downstream_id, input_snapshot={"refs": []}),
             SimpleNamespace(id=unrelated_id, input_snapshot={"refs": []})]
    findings = [SimpleNamespace(status="open", severity="critical", code="AUDIT_BLOCKED")]
    dependencies = [SimpleNamespace(depends_on_task_id=upstream_id, task_id=downstream_id)]

    class Session:
        def scalars(self, query):
            values = {id(models["AuditRun"]): [run], id(models["AuditFinding"]): findings,
                      id(models["Task"]): tasks, id(models["TaskDependency"]): dependencies}
            return Rows(values[id(query.model)])

    guard = ns["active_audit_blockers"]
    checks = {
        "unrelated_target_allowed": not guard(Session(), project_id=project_id, target_ids={uuid4()}),
        "unlinked_consumer_blocked": bool(guard(Session(), project_id=project_id, task_id=upstream_id)),
        "consumer_descendant_blocked": bool(guard(Session(), project_id=project_id, task_id=downstream_id)),
        "unrelated_task_allowed": not guard(Session(), project_id=project_id, task_id=unrelated_id),
    }
    tasks[0].input_snapshot = {"refs": []}
    run.linked_task_id = upstream_id
    checks["explicit_upstream_descendant_blocked"] = bool(guard(Session(), project_id=project_id, task_id=downstream_id))
    assert all(checks.values()), checks
    return checks


def probe_inputs():
    names = ("KnowledgeDocumentVersion", "Citation", "ClaimVersion", "AnalysisRun", "ExternalDeliverable", "Decision")
    models = {name: model() for name in names}
    ns = {"__name__": __name__, "UUID": UUID, "hashlib": hashlib, "json": json,
          "TaskNotReadyError": TaskNotReadyError, "select": Query, **models}
    extract("application/tasks.py", {"_digest", "resolve_task_inputs"}, ns)
    document = SimpleNamespace(id=uuid4(), document_id=uuid4(), content_hash="a" * 64,
                               version_status="current", access_state="active")
    citation = SimpleNamespace(id=uuid4(), version_id=document.id, review_status="valid", content_sha256="b" * 64)
    claim = SimpleNamespace(id=uuid4(), status="stale")
    analysis = SimpleNamespace(id=uuid4(), state="failed")
    objects = {id(models["KnowledgeDocumentVersion"]): document, id(models["Citation"]): citation,
               id(models["ClaimVersion"]): claim, id(models["AnalysisRun"]): analysis}

    class Session:
        def scalar(self, query):
            return objects.get(id(query.model))

    def resolve(ref):
        return ns["resolve_task_inputs"](Session(), project_id=uuid4(), input_version="v1",
                                         input_refs=[ref], captured_at=datetime(2026, 11, 1, tzinfo=UTC))

    def rejected(ref):
        try:
            resolve(ref)
        except TaskNotReadyError:
            return True
        return False

    checks = {f"malformed_{kind}_rejected": rejected(kind + ":not-a-uuid")
              for kind in ("document", "citation", "claim", "analysis", "deliverable", "decision")}
    checks["unknown_type_rejected"] = rejected("unknown:value")
    checks["valid_current_document_resolved"] = resolve("document:" + str(document.id))[0]["refs"][0]["resolution_status"] == "resolved"
    for state in ("trashed", "revoked", "quarantined"):
        document.access_state = state
        checks[state + "_document_rejected"] = rejected("document:" + str(document.id))
        checks[state + "_citation_source_rejected"] = rejected("citation:" + str(citation.id))
    document.access_state = "active"
    document.version_status = "historical"
    checks["historical_document_rejected"] = rejected("document:" + str(document.id))
    document.version_status = "current"
    citation.review_status = "invalid"
    checks["invalid_citation_rejected"] = rejected("citation:" + str(citation.id))
    for state in ("stale", "disputed"):
        claim.status = state
        checks[state + "_claim_rejected"] = rejected("claim:" + str(claim.id))
    checks["failed_analysis_rejected"] = rejected("analysis:" + str(analysis.id))
    assert all(checks.values()), checks
    return checks


def probe_worker_cli():
    calls = []
    ns = {"__name__": "__main__", "UUID": UUID, "argparse": argparse,
          "os": SimpleNamespace(getenv=lambda name: None),
          "asyncio": SimpleNamespace(run=lambda value: calls.append(value)), "run": lambda **kwargs: kwargs}
    extract("worker/__main__.py", {"parse_workspace_id"}, ns)
    tree = ast.parse((SOURCE / "worker/__main__.py").read_text())
    main = next(n for n in tree.body if isinstance(n, ast.If))
    previous_argv = sys.argv
    try:
        sys.argv = ["medical_one_person.worker"]
        exec(compile(ast.Module(body=[main], type_ignores=[]), "worker/__main__.py", "exec"), ns)
        assert calls[0]["workspace_id"] is None
    finally:
        sys.argv = previous_argv
    return {"default_reaches_workspace_discovery": True}


def probe_execution_identity():
    ns = {"hashlib": hashlib}
    extract("agents/runner.py", {"_run_key"}, ns)
    task = SimpleNamespace(project_id=uuid4(), id=uuid4(), input_version="v1", input_snapshot_sha256="a" * 64,
                           revision=3, review_id=None, purpose="same-execution")
    role = SimpleNamespace(role_id="A04", version=1)
    first = ns["_run_key"](task, role)
    task.revision = 7
    checks = {"lease_revision_keeps_identity": ns["_run_key"](task, role) == first}
    task.input_snapshot_sha256 = "b" * 64
    checks["new_input_changes_identity"] = ns["_run_key"](task, role) != first
    task.input_snapshot_sha256 = "a" * 64
    task.review_id = uuid4()
    checks["new_review_changes_identity"] = ns["_run_key"](task, role) != first
    assert all(checks.values()), checks
    return checks


def probe_worker_settlement():
    ns = {"__name__": __name__, "dataclass": dataclass, "logger": logging.getLogger(__name__),
          "AgentExecutionFailure": AgentExecutionFailure, "LeaseConflictError": LeaseConflictError}
    extract("application/worker_loop.py", {"WorkerIteration"}, ns)
    extract("application/worker_loop.py", {"run_once", "_settle_failure"}, ns, owner="WorkerLoop")
    claim = SimpleNamespace(job_id=uuid4(), task_id=uuid4())

    class Queue:
        fail_calls = 0

        def recover_expired(self, **kwargs):
            return 0

        def claim(self, **kwargs):
            return claim

        def fail(self, **kwargs):
            self.fail_calls += 1
            assert kwargs["error_code"] == "PROVIDER_ERROR"

    def fail(_claim):
        raise AgentExecutionFailure("provider failure", error_code="PROVIDER_ERROR", retryable=True)

    queue = Queue()
    worker = SimpleNamespace(_queue=queue, _worker_id="probe", _outbox=SimpleNamespace(dispatch_once=lambda **kwargs: []),
                             _runner=SimpleNamespace(run_claim=fail))
    worker._settle_failure = MethodType(ns["_settle_failure"], worker)
    first = ns["run_once"](worker, workspace_id=uuid4())
    worker._runner.run_claim = lambda _claim: None
    second = ns["run_once"](worker, workspace_id=uuid4())
    checks = {"single_settlement": queue.fail_calls == 1, "original_error_preserved": first.failure_code == "PROVIDER_ERROR",
              "following_job_continues": second.failure_code is None}
    assert all(checks.values()), checks
    return checks


def probe_stale_start():
    ns = {"datetime": datetime, "UTC": UTC, "set_rls_context": lambda *a, **k: None, "AgentRun": object}
    extract("agents/runner.py", {"_start_run"}, ns, owner="AgentRunner")
    row = SimpleNamespace(id=uuid4(), job_id=uuid4(), state="succeeded", output={"result": "new worker success"},
                          ended_at=datetime.now(UTC))

    class Session:
        def get(self, *args):
            return row

    fence_checks = []

    def fence(*args):
        fence_checks.append(True)
        raise LeaseConflictError("old worker lease expired")

    worker = SimpleNamespace(_session_factory=SimpleNamespace(begin=lambda: contextlib.nullcontext(Session())),
                             _require_active_claim=fence)
    rejected = False
    try:
        ns["_start_run"](worker, claim=SimpleNamespace(workspace_id=uuid4(), job_id=row.job_id), task=None, role=None,
                         instance_id=uuid4(), context=SimpleNamespace(snapshot=lambda: {"context": "old worker"}),
                         run_key="same-semantic-run", existing=SimpleNamespace(id=row.id, state="running"))
    except LeaseConflictError:
        rejected = True
    return {"stale_start_rejected": rejected, "fence_checks": len(fence_checks), "persisted_state": row.state,
            "ended_at_erased": row.ended_at is None, "stale_context_persisted": getattr(row, "input_snapshot", None) == {"context": "old worker"},
            "C01_reproduced": not rejected and row.state == "running" and row.ended_at is None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    observations = {"audit_scope": probe_audit_scope(), "input_admission": probe_inputs(),
                    "worker_cli": probe_worker_cli(), "semantic_identity": probe_execution_identity(),
                    "single_settlement": probe_worker_settlement(), "stale_start": probe_stale_start()}
    output = {"reviewed_source_commit": TESTED_SOURCE,
              "method": "Extracted original AST functions with explicit session/provider doubles; not full application acceptance.",
              "source_file_sha256": source_hashes, "observations": observations,
              "findings": ["C01 (P2): stale _start_run can reset a succeeded AgentRun"] if observations["stale_start"]["C01_reproduced"] else []}
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
