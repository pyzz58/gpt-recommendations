#!/usr/bin/env python3
"""Offline showrunner-led AI filmmaking-team *planning* orchestrator.

No LLM, tool calls, agent autonomy, GPU, media generation, network or payments.
The "agents" are role contracts, task envelopes, scoped deliverables and
deterministic scheduling. A future model adapter must be separately authorized.

Shared source plan is immutable; proposals never silently rewrite narration,
claims, duration, character identity or prop state. No user approval is inferred.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import argparse

VERSION = "1.0"
TEAM = {
    "showrunner": "Creative intent, approved constraints, task assignment and final editorial review",
    "script_editor": "Narrative hook, structure and proposed script changes; never silently change source",
    "acting_coach": "Blocking, movement, beats, performance and hands/props continuity",
    "cinematographer": "Camera language, lighting, visual grammar and set design",
    "sound_director": "Voiceover, on-camera speech, sound effects and subtitle timecodes",
    "editing_director": "Shot transitions, animation, visual composition and edit timing",
    "ai_technical_director": "Translate approved creative specifications into AI/postproduction routes",
    "continuity_qa": "Independent read-only editorial, continuity and feasibility review",
}

# One task per department per EPISODE to avoid N-shots times N-departments
# expensive calls. Submissions may cover selected shots when revising.
STAGES = (
    ("director_brief", "showrunner", (), "document", ("creative_brief",)),
    ("script_edit", "script_editor", ("director_brief",), "document", ("story_treatment",)),
    ("director_lock", "showrunner", ("script_edit",), "document", ("global_direction",)),
    ("acting", "acting_coach", ("director_lock",), "shots",
     ("staging", "performance", "beats", "continuity", "shootability")),
    ("camera_art", "cinematographer", ("director_lock",), "shots", ("camera", "art")),
    ("sound", "sound_director", ("director_lock",), "shots", ("sound", "speech")),
    ("editing_animation", "editing_director", ("acting", "camera_art", "sound"),
     "shots", ("editing", "animation", "graphics")),
    ("ai_technical", "ai_technical_director", ("editing_animation",),
     "shots", ("generation",)),
    ("quality_review", "continuity_qa", ("ai_technical",), "review", ("qa_report",)),
    ("director_final", "showrunner", ("quality_review",), "decision", ("director_decision",)),
)
SPECS = {
    task: {"id": task, "role": role, "depends_on": list(deps), "kind": kind,
           "fields": list(fields)} for task, role, deps, kind, fields in STAGES
}
PRECEDENCE = {x[0]: i for i, x in enumerate(STAGES)}
DOWNSTREAM = {}
for task in SPECS:
    queue, descendants = [task], set()
    while queue:
        current = queue.pop()
        for tid, spec in SPECS.items():
            if current in spec["depends_on"] and tid not in descendants:
                descendants.add(tid)
                queue.append(tid)
    DOWNSTREAM[task] = sorted(descendants, key=PRECEDENCE.get)


def fingerprint(base):
    canonical = json.dumps(base, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def start(base):
    """Produce a new task ledger, without copying user prose into GitHub."""
    _require(isinstance(base, dict) and isinstance(base.get("shots"), list)
             and bool(base["shots"]), "base plan needs nonempty shots")
    ids = [s.get("id") if isinstance(s, dict) else None for s in base["shots"]]
    _require(all(isinstance(x, str) and x for x in ids) and
             len(set(ids)) == len(ids), "shot IDs must be unique and nonempty")
    tasks = {}
    for tid, spec in SPECS.items():
        tasks[tid] = {"role": spec["role"], "depends_on": spec["depends_on"],
                      "kind": spec["kind"], "fields": spec["fields"],
                      "status": "pending", "revision": 0,
                      "revision_scope": None, "deliverable": None,
                      "previous_versions": []}
    return {
        "schema_version": VERSION, "kind": "ai_director_team_ledger",
        "base_digest": fingerprint(base), "shot_ids": ids,
        "team_roles": dict(TEAM), "tasks": tasks, "events": [],
        "budget_policy": {"llm_requests_enabled": False,
                          "paid_media_enabled": False,
                          "automatic_retries_enabled": False},
        "release": {"director_ai_review_complete": False,
                    "human_approved": False, "paid_api_authorized": False,
                    "media_generated": False, "publishing_allowed": False},
    }


def _check_state(state):
    _require(isinstance(state, dict) and state.get("schema_version") == VERSION
             and state.get("kind") == "ai_director_team_ledger",
             "invalid team ledger")
    _require(isinstance(state.get("shot_ids"), list) and
             isinstance(state.get("tasks"), dict) and
             set(state["tasks"]) == set(SPECS), "team task registry mismatch")
    for tid, spec in SPECS.items():
        entry = state["tasks"][tid]
        _require(isinstance(entry, dict) and entry.get("role") == spec["role"]
                 and entry.get("depends_on") == spec["depends_on"]
                 and entry.get("fields") == spec["fields"]
                 and entry.get("kind") == spec["kind"], "task contract changed: " + tid)
        _require(entry.get("status") in ("pending", "completed", "stale", "needs_revision")
                 and type(entry.get("revision")) is int and entry["revision"] >= 0,
                 "task state invalid: " + tid)
    _require(state.get("budget_policy") == {
        "llm_requests_enabled": False,
        "paid_media_enabled": False,
        "automatic_retries_enabled": False
    }, "untrusted runtime budget flags")
    _require(isinstance(state.get("release"), dict)
             and all(state["release"].get(k) is False for k in
                     ("human_approved", "paid_api_authorized", "media_generated",
                      "publishing_allowed")), "offline ledger cannot grant release/payment")


def _deps_done(state, task_id):
    return all(state["tasks"][dep]["status"] == "completed"
               for dep in SPECS[task_id]["depends_on"])


def ready(state):
    _check_state(state)
    return [tid for tid in SPECS if state["tasks"][tid]["status"] in
            ("pending", "stale", "needs_revision") and _deps_done(state, tid)]


def packet(state, task_id):
    """A role-scoped task envelope; calling this never invokes an LLM."""
    _check_state(state)
    _require(task_id in SPECS, "unknown task")
    _require(task_id in ready(state), "task dependencies or status are not ready")
    spec, item = SPECS[task_id], state["tasks"][task_id]
    deps = {d: state["tasks"][d]["revision"] for d in spec["depends_on"]}
    return {"task_id": task_id, "role": spec["role"], "task_kind": spec["kind"],
            "allowed_fields": list(spec["fields"]), "shot_ids": list(state["shot_ids"]),
            "revision_scope": item["revision_scope"],
            "dependency_revisions": deps, "base_digest": state["base_digest"],
            "input_task_ids": list(spec["depends_on"]),
            "no_authorized_model_calls": True, "no_payments_or_media": True,
            "note": ("Work from the approved shared base and upstream deliverables. "
                     "Propose only your own fields; cross-department or source changes "
                     "must be requested for showrunner review.")}


def _validate_payload(state, task_id, payload):
    spec, task = SPECS[task_id], state["tasks"][task_id]
    _require(isinstance(payload, dict) and set(payload) == set(spec["fields"])
             if spec["kind"] != "shots" else
             isinstance(payload, dict) and set(payload) == {"shots"},
             "deliverable shape/ownership mismatch")
    if spec["kind"] == "shots":
        shots = payload["shots"]
        _require(isinstance(shots, dict) and bool(shots), "shot deliverable must not be empty")
        _require(set(shots) <= set(state["shot_ids"]), "unknown shot in specialist handoff")
        required = set(task["revision_scope"] if task["revision_scope"] is not None
                       else state["shot_ids"])
        _require(set(shots) == required,
                 "initial submission must cover all shots; revision must cover its scoped shots")
        for sid, data in shots.items():
            _require(isinstance(data, dict) and set(data) == set(spec["fields"]),
                     f"{task_id}/{sid}: specialists may edit only their owned sections")
            for field, value in data.items():
                _require(value is None and field == "shootability" or
                         isinstance(value, (dict, list)) and bool(value),
                         f"{task_id}/{sid}.{field}: expected a real direction object/list")
        return
    field = spec["fields"][0]
    value = payload[field]
    _require(isinstance(value, dict) and bool(value), field + " must be a nonempty object")
    if task_id == "quality_review":
        _require(isinstance(value.get("blockers"), list)
                 and isinstance(value.get("findings"), list)
                 and value.get("recommendation") in
                 ("revise", "ready_for_director_review"), "QA report needs blockers/findings/recommendation")
        if value["blockers"]:
            _require(value["recommendation"] == "revise", "QA blockers require revision")
        for finding in value["blockers"]:
            _require(isinstance(finding, dict) and finding.get("task_id")
                     in ("script_edit", "director_lock", "acting", "camera_art",
                         "sound", "editing_animation", "ai_technical"),
                     "QA blocker needs a valid owning department")
            ids = finding.get("shot_ids", [])
            _require(isinstance(ids, list) and set(ids) <= set(state["shot_ids"]),
                     "QA blocker references unknown shot")
    elif task_id == "director_final":
        decision = value.get("decision")
        _require(decision in ("ready_for_user_review", "request_changes")
                 and isinstance(value.get("rationale"), str)
                 and value["rationale"].strip(), "director decision needs rationale")
        qa = state["tasks"]["quality_review"]["deliverable"]["qa_report"]
        if qa["blockers"] or qa["recommendation"] != "ready_for_director_review":
            _require(decision == "request_changes",
                     "showrunner cannot override outstanding QA blockers")


def submit(state, envelope, payload):
    """Accept one role's scoped proposal if it matches exact task+dependency revisions.

    Does not merge into base plan, claim human signoff, publish or invoke a model.
    """
    _check_state(state)
    _require(isinstance(envelope, dict), "task envelope required")
    tid = envelope.get("task_id")
    _require(tid in SPECS, "unknown task")
    expected = packet(state, tid)  # also enforces dependencies
    for field in ("base_digest", "task_id", "dependency_revisions", "revision_scope"):
        _require(envelope.get(field) == expected[field], "stale or mismatched envelope: " + field)
    _validate_payload(state, tid, payload)
    out = deepcopy(state)
    task = out["tasks"][tid]
    if task["deliverable"] is not None:
        task["previous_versions"].append({"revision": task["revision"],
                                          "deliverable": deepcopy(task["deliverable"])})
    if SPECS[tid]["kind"] == "shots" and task["deliverable"] is not None:
        merged = deepcopy(task["deliverable"])
        merged["shots"].update(deepcopy(payload["shots"]))
        task["deliverable"] = merged
    else:
        task["deliverable"] = deepcopy(payload)
    task["revision"] += 1
    task["revision_scope"] = None
    task["status"] = "completed"
    out["events"].append({"type": "submitted", "task_id": tid,
                          "revision": task["revision"]})
    out["release"]["director_ai_review_complete"] = (
        tid == "director_final" and
        payload["director_decision"]["decision"] == "ready_for_user_review"
    ) if tid == "director_final" else False
    return out


def request_revision(state, task_id, shot_ids, reason, *, source_task="director_final"):
    """Director-governed targeted change request. No automatic revision loops."""
    _check_state(state)
    _require(source_task in ("director_final", "quality_review"),
             "only QA or showrunner may propose revisions")
    _require(task_id in SPECS and task_id not in ("quality_review", "director_final"),
             "invalid revision owner")
    _require(state["tasks"][task_id]["status"] == "completed",
             "target task must have a submitted deliverable")
    _require(isinstance(reason, str) and reason.strip(), "revision reason required")
    _require(isinstance(shot_ids, list) and len(set(shot_ids)) == len(shot_ids)
             and all(isinstance(s, str) and s in state["shot_ids"] for s in shot_ids),
             "revision targets must be known unique shots")
    _require(shot_ids or SPECS[task_id]["kind"] == "document",
             "shot-specific revisions require at least one shot")
    if SPECS[task_id]["kind"] == "document":
        _require(not shot_ids, "document revisions must use whole-document scope")
    out = deepcopy(state)
    target = out["tasks"][task_id]
    target["status"] = "needs_revision"
    target["revision_scope"] = list(shot_ids) if shot_ids else None
    # The edit department also needs the adjacent clips because it owns cuts.
    impacted = set(shot_ids)
    for sid in shot_ids:
        i = state["shot_ids"].index(sid)
        if i:
            impacted.add(state["shot_ids"][i - 1])
        if i + 1 < len(state["shot_ids"]):
            impacted.add(state["shot_ids"][i + 1])
    for dependent in DOWNSTREAM[task_id]:
        item = out["tasks"][dependent]
        if item["status"] == "completed":
            item["status"] = "stale"
        if SPECS[dependent]["kind"] == "shots":
            new_scope = set(impacted if dependent == "editing_animation"
                            else shot_ids)
            current = item["revision_scope"]
            item["revision_scope"] = sorted(new_scope | set(current or []))
    out["events"].append({"type": "revision_requested", "target": task_id,
                          "source": source_task, "shot_ids": list(shot_ids),
                          "reason": reason, "invalidated": DOWNSTREAM[task_id]})
    out["release"]["director_ai_review_complete"] = False
    return out


def overview(state):
    _check_state(state)
    return {"ready_tasks": ready(state),
            "completed": [k for k, v in state["tasks"].items() if v["status"] == "completed"],
            "stale": [k for k, v in state["tasks"].items() if v["status"] == "stale"],
            "pending": [k for k, v in state["tasks"].items() if v["status"] in
                        ("pending", "needs_revision")],
            "director_review_complete": state["release"]["director_ai_review_complete"],
            "user_approved": False, "paid_api_authorized": False}


def assemble_direction(base, state):
    """Merge owned sections into existing v0.2 direction format, for final QA.

    No source rewrite, no human approval. Reject partial stale team work.
    """
    _check_state(state)
    _require(fingerprint(base) == state["base_digest"], "base source changed")
    _require(all(t["status"] == "completed" for t in state["tasks"].values()),
             "team handoffs incomplete or stale")
    _require(state["tasks"]["director_final"]["deliverable"]["director_decision"]
             ["decision"] == "ready_for_user_review",
             "final director review did not accept this draft")
    full = state["tasks"]
    direction = {"schema_version": "0.2", "title": base["title"],
                 "global_direction": deepcopy(full["director_lock"]["deliverable"]
                                              ["global_direction"]), "shots": []}
    for sid in state["shot_ids"]:
        item = {"shot_id": sid, "review_status": "reviewed",
                "qa": {"acceptance_tests": ["await independent human review"],
                       "issues": [], "human_approved": False}}
        for tid in ("acting", "camera_art", "sound", "editing_animation", "ai_technical"):
            item.update(deepcopy(full[tid]["deliverable"]["shots"][sid]))
        direction["shots"].append(item)
    return direction


def main(argv=None):
    p = argparse.ArgumentParser(description="OFFLINE director-team task ledger. No LLM or media.")
    sub = p.add_subparsers(dest="command", required=True)
    p_new = sub.add_parser("plan")
    p_new.add_argument("--base", required=True)
    p_new.add_argument("--out", required=True)
    p_show = sub.add_parser("ready")
    p_show.add_argument("--state", required=True)
    args = p.parse_args(argv)
    try:
        if args.command == "plan":
            base = json.loads(Path(args.base).read_text(encoding="utf-8"))
            state = start(base)
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as fp:
                json.dump(state, fp, ensure_ascii=False, indent=2)
                fp.write("\n")
            print("Offline director team plan created; ready:", ", ".join(ready(state)))
        else:
            state = json.loads(Path(args.state).read_text(encoding="utf-8"))
            print(json.dumps(overview(state), ensure_ascii=False, indent=2))
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
