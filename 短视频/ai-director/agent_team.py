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
    ("director_lock", "showrunner", ("script_edit",), "document",
     ("global_direction", "shot_objectives")),
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
GUIDANCE = {
    "director_brief": "Review the source story; establish audience, emotional target, immutable facts, runtime and style constraints. Do not rewrite text.",
    "script_edit": "Propose hook, beats and any optional source edits as clearly labeled proposals. Do not alter the source plan.",
    "director_lock": "Approve shared global directing bible AND concrete per-shot dramatic objective (emotion, observable turn, visual focus).",
    "acting": "Design every shot's physical beats, staging, identity/prop continuity and timecoded hand actions, including split-take fallbacks.",
    "camera_art": "Design camera coverage, lighting, scene geometry, lens feel and unified visual grammar for every shot.",
    "sound": "Design exact narration, spoken dialogue, music, sound effects, subtitles and cue timing without rewriting source text.",
    "editing_animation": "Motivate every cut, plan motion graphics and J/L-cut audio bridges, and reconcile animation/acting/camera/sound handoffs.",
    "ai_technical": "Translate approved creative shots to safe provider-neutral candidate prompts and postproduction work orders. No model calls.",
    "quality_review": "Read only: evaluate structured direction, source fidelity, art/style consistency, timing, props and feasibility. Assign blockers to owning tasks.",
    "director_final": "Reconcile departments, accept a blueprint only for human review or request scoped changes. Never claim human approval or spend.",
}
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


def start(base, source_text=None):
    """Produce a ledger; optional private source text is hashed, not stored."""
    _require(source_text is None or
             isinstance(source_text, str) and source_text.strip(),
             "source_text must be nonempty text when provided")
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
        "base_digest": fingerprint(base),
        "source_digest": (hashlib.sha256(source_text.encode("utf-8")).hexdigest()
                          if source_text is not None else None),
        "source_review_bound": source_text is not None,
        "shot_ids": ids,
        "team_roles": dict(TEAM), "tasks": tasks, "events": [],
        "budget_policy": {"llm_requests_enabled": False,
                          "paid_media_enabled": False,
                          "automatic_retries_enabled": False},
        "release": {"director_ai_review_complete": False,
                    "human_approved": False, "paid_api_authorized": False,
                    "media_generated": False, "publishing_allowed": False},
    }


def _ancestors(task_id):
    queue, found = list(SPECS[task_id]["depends_on"]), set()
    while queue:
        upstream = queue.pop()
        if upstream not in found:
            found.add(upstream)
            queue.extend(SPECS[upstream]["depends_on"])
    return sorted(found, key=PRECEDENCE.get)


def _check_state(state):
    _require(isinstance(state, dict) and state.get("schema_version") == VERSION
             and state.get("kind") == "ai_director_team_ledger",
             "invalid team ledger")
    _require(state.get("source_review_bound") is
             (state.get("source_digest") is not None),
             "source intake status inconsistent")
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
    ancestry = _ancestors(task_id)
    upstream = {key: deepcopy(state["tasks"][key]["deliverable"])
                for key in ancestry if state["tasks"][key]["status"] == "completed"}
    audit = None
    if task_id in ("quality_review", "director_final"):
        import agent_handoff_audit
        audit = agent_handoff_audit.audit_handoffs(state)
    return {"task_id": task_id, "role": spec["role"], "task_kind": spec["kind"],
            "instructions": GUIDANCE[task_id],
            "upstream_artifacts": upstream, "source_plan_required": True,
            "allowed_fields": list(spec["fields"]), "shot_ids": list(state["shot_ids"]),
            "revision_scope": item["revision_scope"],
            "dependency_revisions": deps, "base_digest": state["base_digest"],
            "source_digest": state["source_digest"],
            "source_review_bound": state["source_review_bound"],
            "input_task_ids": list(spec["depends_on"]),
            "no_authorized_model_calls": True, "no_payments_or_media": True,
            "creative_review_contract": "ROLE_CREATIVE_CONTRACTS.md",
            "independent_handoff_audit": audit,
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
    for field in spec["fields"]:
        _require(isinstance(payload[field], dict) and bool(payload[field]),
                 field + " must be a nonempty object")
    field = spec["fields"][0]
    value = payload[field]
    if task_id == "director_lock":
        mandatory = ("audience_emotion_arc", "visual_grammar", "audio_grammar",
                     "graphic_safety", "reference_strategy", "generation_budget")
        _require(all(isinstance(value.get(k), str) and value[k].strip()
                     for k in mandatory),
                 "locked director bible lacks required global directing fields")
        objectives = payload["shot_objectives"]
        _require(set(objectives) == set(state["shot_ids"]),
                 "showrunner must define a distinct objective for each shot")
        for shot_id, item in objectives.items():
            _require(isinstance(item, dict)
                     and all(isinstance(item.get(k), str) and item[k].strip()
                             for k in ("emotion", "observable_turn", "visual_focus")),
                     f"{shot_id}: director objective needs emotion, visible turn and focus")
    if task_id == "quality_review":
        import agent_handoff_audit
        independent = agent_handoff_audit.audit_handoffs(state)
        if independent["status"] == "blocked":
            _require(value.get("recommendation") != "ready_for_director_review",
                     "independent department contradictions must be marked for revision")
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
            _require(isinstance(ids, list) and
                     all(isinstance(i, str) for i in ids) and
                     set(ids) <= set(state["shot_ids"]),
                     "QA blocker references unknown shot")
    elif task_id == "director_final":
        decision = value.get("decision")
        _require(decision in ("ready_for_user_review", "request_changes")
                 and isinstance(value.get("rationale"), str)
                 and value["rationale"].strip(), "director decision needs rationale")
        qa = state["tasks"]["quality_review"]["deliverable"]["qa_report"]
        if decision == "ready_for_user_review":
            import agent_handoff_audit
            _require(agent_handoff_audit.audit_handoffs(state)["status"] != "blocked",
                     "independent handoff blockers prevent final director acceptance")
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
    for field in ("base_digest", "source_digest", "task_id",
                  "dependency_revisions", "revision_scope"):
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
    _require(source_task == "director_final",
             "QA may recommend revisions, but only showrunner may authorize rework")
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
            if SPECS[task_id]["kind"] == "document":
                item["revision_scope"] = None  # whole episode bible changed
            else:
                new_scope = set(impacted if dependent == "editing_animation"
                                else shot_ids)
                current = item["revision_scope"]
                item["revision_scope"] = sorted(new_scope | set(current or []))
    out["events"].append({"type": "revision_requested", "target": task_id,
                          "source": source_task, "shot_ids": list(shot_ids),
                          "reason": reason, "invalidated": DOWNSTREAM[task_id]})
    out["release"]["director_ai_review_complete"] = False
    return out


def compile_team_workbook(base, state, *, strict=False):
    """Compile review draft; reject independent hard conflicts before delivery.

    strict=True also demands the existing director's production blueprint gate.
    Human signoff, footage and payment authorization always remain separate.
    """
    import director_v2
    import director_workbook
    import agent_creative_review
    import agent_handoff_audit
    _check_state(state)
    _require(fingerprint(base) == state["base_digest"],
             "source plan changed since crew was assigned")
    qa = state["tasks"]["quality_review"]["deliverable"]
    _require(isinstance(qa, dict) and isinstance(qa.get("qa_report"), dict),
             "independent QA deliverable missing")
    _require(not qa["qa_report"].get("blockers") and
             qa["qa_report"].get("recommendation") == "ready_for_director_review",
             "QA blockers or unresolved review prevent final workbook")
    handoffs = agent_handoff_audit.audit_handoffs(state, base)
    _require(handoffs["status"] != "blocked",
             "independent handoff blockers prevent workbook: " +
             ", ".join(x["code"] for x in handoffs["issues"] if
                       x["severity"] == "blocker")[:350])
    draft = assemble_direction(base, state)
    errors, warnings = director_v2.validate(base, draft)
    _require(not errors, "merged direction invalid: " + "; ".join(errors[:8]))
    book = director_workbook.compile_workbook(base, draft)
    creative = agent_creative_review.review_team(state)
    book["creative_quality_review"] = creative
    book["independent_handoff_audit"] = handoffs
    review_ready = (bool(book["director_review"]["production_blueprint_ready"]) and
                    creative["status"] == "structured_evidence_present" and
                    handoffs["status"] == "no_explicit_conflicts")
    if strict:
        _require(review_ready,
                 "strict director handoff requires complete blueprint and no open creative review")
    book["team_delivery_gate"] = {
        "status": "ready_for_human_review" if review_ready else "draft_needs_review",
        "hard_conflicts": 0, "creative_review_findings": len(creative["findings"]),
        "blueprint_complete": bool(book["director_review"]["production_blueprint_ready"]),
        "automated_evidence_checked": True, "human_approved": False,
        "actual_video_approved": False, "paid_api_authorized": False}
    book["team_handoff"] = {
        "specialist_task_revisions": {k: v["revision"] for k, v in
                                      state["tasks"].items()},
        "manager_review_only": True,
        "human_approved": False, "llm_calls_executed": False,
        "paid_media_generated": False}
    return book


def propose_director_revisions(base, state, *, include_reviews=False):
    """Generate non-mutating revision proposals from independent QA evidence."""
    import agent_handoff_audit
    _check_state(state)
    _require(fingerprint(base) == state["base_digest"],
             "base digest mismatch; cannot propose revisions")
    return agent_handoff_audit.propose_revisions(
        state, base, include_reviews=include_reviews)


def request_planned_revision(base, state, proposal, *, showrunner_approved=False):
    """Apply only a current, approved suggestion via the existing revision DAG.

    The approval flag records an orchestration decision, NOT a verified human
    identity, model-payment authorization or user signoff.
    """
    _require(showrunner_approved is True, "showrunner decision required")
    _require(isinstance(proposal, dict), "revision proposal must be an object")
    options = (propose_director_revisions(base, state)["proposals"] +
               propose_director_revisions(base, state, include_reviews=True)["proposals"])
    _require(proposal in options, "proposal no longer matches the current QA evidence")
    return request_revision(state, proposal["task_id"], proposal["shot_ids"],
                            proposal["reason"], source_task="director_final")


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
                "objective": deepcopy(full["director_lock"]["deliverable"]
                                      ["shot_objectives"][sid]),
                "qa": {"acceptance_tests": ["await independent human review"],
                       "issues": [], "human_approved": False}}
        for tid in ("acting", "camera_art", "sound", "editing_animation", "ai_technical"):
            item.update(deepcopy(full[tid]["deliverable"]["shots"][sid]))
        direction["shots"].append(item)
    return direction


def source_matches(state, private_source_text):
    """Verify a private source without copying it into the task ledger."""
    _check_state(state)
    _require(state["source_review_bound"], "source text was not bound at intake")
    _require(isinstance(private_source_text, str), "source text must be a string")
    return hashlib.sha256(private_source_text.encode("utf-8")).hexdigest() == state["source_digest"]


def _save_new(path, obj):
    """No silent overwrites: a handoff history is an artifact, not cache."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as fp:
        json.dump(obj, fp, ensure_ascii=False, indent=2)
        fp.write("\n")


def main(argv=None):
    p = argparse.ArgumentParser(description="OFFLINE director-team task ledger. No LLM or media.")
    sub = p.add_subparsers(dest="command", required=True)
    p_new = sub.add_parser("plan")
    p_new.add_argument("--base", required=True)
    p_new.add_argument("--source", help="private original text, hashed but never stored")
    p_new.add_argument("--out", required=True)
    p_show = sub.add_parser("ready")
    p_show.add_argument("--state", required=True)
    p_packet = sub.add_parser("packet")
    p_packet.add_argument("--state", required=True)
    p_packet.add_argument("--task", required=True, choices=list(SPECS))
    p_packet.add_argument("--out", required=True)
    p_submit = sub.add_parser("submit")
    p_submit.add_argument("--state", required=True)
    p_submit.add_argument("--envelope", required=True)
    p_submit.add_argument("--deliverable", required=True)
    p_submit.add_argument("--out", required=True)
    p_revise = sub.add_parser("revise")
    p_revise.add_argument("--state", required=True)
    p_revise.add_argument("--task", required=True, choices=list(SPECS))
    p_revise.add_argument("--shot", action="append", default=[])
    p_revise.add_argument("--reason", required=True)
    p_revise.add_argument("--out", required=True)
    p_assemble = sub.add_parser("assemble")
    p_assemble.add_argument("--state", required=True)
    p_assemble.add_argument("--base", required=True)
    p_assemble.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        def load_json(file):
            return json.loads(Path(file).read_text(encoding="utf-8"))
        if args.command == "plan":
            source_text = (Path(args.source).read_text(encoding="utf-8")
                           if args.source else None)
            state = start(load_json(args.base), source_text=source_text)
            _save_new(args.out, state)
            print("Offline director team plan created; ready:", ", ".join(ready(state)))
        elif args.command == "ready":
            print(json.dumps(overview(load_json(args.state)), ensure_ascii=False, indent=2))
        elif args.command == "packet":
            _save_new(args.out, packet(load_json(args.state), args.task))
            print("Role-scoped envelope created (no model call):", args.task)
        elif args.command == "submit":
            state = submit(load_json(args.state), load_json(args.envelope),
                           load_json(args.deliverable))
            _save_new(args.out, state)
            print("Team ledger revised; next ready:", ", ".join(ready(state)))
        elif args.command == "revise":
            state = request_revision(load_json(args.state), args.task,
                                     args.shot, args.reason)
            _save_new(args.out, state)
            print("Scoped director rework requested:", args.task)
        elif args.command == "assemble":
            direction = assemble_direction(load_json(args.base), load_json(args.state))
            _save_new(args.out, direction)
            print("Draft direction assembled. HUMAN_APPROVED=false; no media created.")
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
