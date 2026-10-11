#!/usr/bin/env python3
"""Fail-closed offline execution harness for the AI directing crew.

Only literal, pre-authored fixtures may supply specialist deliverables. No LLM,
network, subprocess, tool execution, media generation, retry, automatic rework,
payment or publication. A later model transport requires a separate reviewed
adapter and a new explicit authorization path, not a flag in the team ledger.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

import agent_team as team
import agent_handoff_audit


class FixtureMissing(LookupError):
    """A role has no fixture for its next exact revision."""


class FixtureOnlyAdapter:
    """Deterministic, read-only response adapter; no generative capability.

    fixtures = {"director_brief": {"1": {"creative_brief": {...}}, ...}}
    Keys may also be positive ints in in-memory Python dictionaries.
    """

    def __init__(self, fixtures):
        if not isinstance(fixtures, dict):
            raise ValueError("fixtures must be a dictionary")
        self._fixtures = deepcopy(fixtures)

    def supply(self, context):
        task_id = context["task_id"]
        revision = context["next_revision"]
        choices = self._fixtures.get(task_id)
        if not isinstance(choices, dict):
            raise FixtureMissing(task_id + ": no fixtures")
        record = choices.get(str(revision), choices.get(revision))
        if record is None:
            raise FixtureMissing(task_id + ": fixture revision " + str(revision) + " missing")
        if not isinstance(record, dict):
            raise ValueError(task_id + ": fixture must be an object")
        return deepcopy(record)


def _check(base, state, source_text):
    team._check_state(state)
    if team.fingerprint(base) != state["base_digest"]:
        raise ValueError("base plan digest mismatch")
    if state["source_review_bound"]:
        if source_text is None or not team.source_matches(state, source_text):
            raise ValueError("private source text missing or fingerprint mismatch")
    elif source_text is not None:
        raise ValueError("cannot attach source text to a ledger not bound at start")


def role_context(base, state, task_id, *, source_text=None):
    """Private, ephemeral role input. NEVER save this object to public GitHub.

    The original script and full base are essential for actual creative work
    but may only be held in a future explicitly approved private runtime.
    """
    _check(base, state, source_text)
    task_packet = team.packet(state, task_id)
    return {
        "kind": "offline_role_input",
        "task_id": task_id, "role": task_packet["role"],
        "next_revision": state["tasks"][task_id]["revision"] + 1,
        "packet": task_packet, "authoritative_base": deepcopy(base),
        "original_script": source_text,
        "no_external_calls_authorized": True,
        "no_payment_authorized": True,
        "role_output_contract": list(team.SPECS[task_id]["fields"]),
    }


def _enforce_base_audit(state, base, task_id, payload):
    """Do not trust a successful QA decision when base-known facts contradict."""
    if task_id not in ("quality_review", "director_final"):
        return
    audit = agent_handoff_audit.audit_handoffs(state, base)
    if audit["status"] != "blocked":
        return
    if task_id == "quality_review":
        report = payload.get("qa_report")
        accepted = isinstance(report, dict) and report.get("recommendation") == "ready_for_director_review"
    else:
        decision = payload.get("director_decision")
        accepted = isinstance(decision, dict) and decision.get("decision") == "ready_for_user_review"
    if accepted:
        raise ValueError("source-aware department blockers forbid approval: " +
                         ", ".join(sorted({v["code"] for v in audit["issues"]
                                           if v["severity"] == "blocker"})))


def execute_one(base, state, adapter, task_id=None, *, source_text=None,
                allow_fixture_director_final=False):
    """Submit exactly one fixture-backed deliverable against a versioned packet.

    Returns (new ledger, privacy-safe receipt); no automatic saving. Invalid
    outputs raise rather than silently repair or enqueue paid retries.
    """
    if type(adapter) is not FixtureOnlyAdapter:
        raise ValueError("only exact FixtureOnlyAdapter is allowed; model adapters disabled")
    _check(base, state, source_text)
    ready = team.ready(state)
    if not ready:
        raise ValueError("no ready team tasks")
    if task_id is None:
        task_id = ready[0]
    if task_id not in ready:
        raise ValueError("task not ready: " + str(task_id))
    if task_id == "director_final" and not allow_fixture_director_final:
        raise ValueError("director_final requires explicit fixture-only review permission")

    context = role_context(base, state, task_id, source_text=source_text)
    proposal = adapter.supply(context)
    _enforce_base_audit(state, base, task_id, proposal)
    updated = team.submit(state, context["packet"], proposal)
    receipt = {
        "task_id": task_id, "role": context["role"],
        "revision": updated["tasks"][task_id]["revision"],
        "result": "accepted_by_structural_contract",
        "execution_mode": "fixture_only",
        "actual_ai_roles_invoked": 0,
        "model_requests": 0, "media_generated": False,
        "human_approved": False, "payment_authorized": False,
    }
    return updated, receipt


def execute_until_pause(base, state, adapter, *, source_text=None,
                        max_steps=10, allow_fixture_director_final=False):
    """Sequentially advance the ready DAG; halt at absent fixture/final gate.

    Independent acting, camera and sound are all eligible once director_lock
    is submitted, but this deterministic harness does NOT execute in parallel.
    The ledger and fixture adapter are never mutated.
    """
    if type(max_steps) is not int or not 1 <= max_steps <= 50:
        raise ValueError("max_steps must be an integer between 1 and 50")
    if type(adapter) is not FixtureOnlyAdapter:
        raise ValueError("model adapters disabled")
    _check(base, state, source_text)
    current = deepcopy(state)
    receipts = []
    stop = None
    for _ in range(max_steps):
        tasks = team.ready(current)
        if not tasks:
            stop = "no_ready_tasks"
            break
        next_task = tasks[0]
        if next_task == "director_final" and not allow_fixture_director_final:
            stop = "director_final_requires_explicit_fixture_permission"
            break
        try:
            current, receipt = execute_one(
                base, current, adapter, next_task, source_text=source_text,
                allow_fixture_director_final=allow_fixture_director_final)
        except FixtureMissing:
            stop = "fixture_missing"
            break
        receipts.append(receipt)
    if stop is None:
        stop = "step_limit_reached" if team.ready(current) else "no_ready_tasks"
    return current, {
        "kind": "offline_execution_receipt", "mode": "fixture_only",
        "status": stop,
        "processed": receipts, "processed_count": len(receipts),
        "ready_tasks": team.ready(current),
        "external_requests": 0, "actual_ai_roles_invoked": 0,
        "payment_authorized": False, "human_approved": False,
        "contains_source_text": False,
    }


def _write_new(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fixture-only AI director team runner (NO model calls)")
    parser.add_argument("--base", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--source", help="Private source script; not written to receipts")
    parser.add_argument("--out-state", required=True)
    parser.add_argument("--out-receipt", required=True)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--allow-fixture-director-final", action="store_true")
    args = parser.parse_args(argv)
    try:
        paths = [Path(args.out_state).resolve(), Path(args.out_receipt).resolve()]
        if paths[0] == paths[1] or any(x.exists() for x in paths):
            raise ValueError("outputs must differ and must not already exist")
        def read(path):
            return json.loads(Path(path).read_text(encoding="utf-8"))
        base, state = read(args.base), read(args.state)
        adapter = FixtureOnlyAdapter(read(args.fixtures))
        source_text = Path(args.source).read_text(encoding="utf-8") if args.source else None
        updated, receipt = execute_until_pause(
            base, state, adapter, source_text=source_text,
            max_steps=args.max_steps,
            allow_fixture_director_final=args.allow_fixture_director_final)
        _write_new(args.out_state, updated)
        _write_new(args.out_receipt, receipt)
        print("Fixture-only run:", receipt["status"], "steps:", receipt["processed_count"])
        return 0
    except (OSError, TypeError, KeyError, ValueError, FixtureMissing) as err:
        print("ERROR:", err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
