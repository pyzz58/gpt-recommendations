"""Offline shootability preflight for the script-to-AI-video director.

Examines *explicitly authored*, timecoded action units. No NLP guessing,
model benchmarking, footage generation, paid API or attempt to rate art.
A risk threshold is a rehearsal/review signal, not proof an AI cannot film it.
"""
from __future__ import annotations
from collections import Counter
import re

MODES = {"single_take", "split_stitch", "static_edit",
         "post_composite", "practical_insert"}
HANDS = {"none", "left", "right", "both"}
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def review(base, directions, route_fn):
    by_id = {d["shot_id"]: d for d in directions["shots"]}
    characters = {c["id"] for c in base.get("characters", [])}
    props = set((base.get("continuity_contract") or {}).get("props", {}))
    results, findings = [], []

    def flag(sid, code, severity, detail):
        findings.append({"shot_id": sid, "code": code, "severity": severity,
                         "detail": detail})

    def valid_time(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    for shot in base["shots"]:
        sid = shot["id"]
        d = by_id[sid]
        route = route_fn(shot, d["generation"])
        physical = bool(shot.get("character_ids")) and route == "ai_video"
        plan = d.get("shootability")
        row = {"shot_id": sid, "execution_route": route, "physical_ai_shot": physical,
               "status": "not_assessed", "units": [], "mode": None,
               "assessment_note": "No real model has been tested"}
        if plan is None:
            if physical:
                flag(sid, "PHYSICAL_ACTION_PLAN_MISSING", "pending",
                     "provide timed hand/action/prop units for a human AI-video shot")
            else:
                row["status"] = "not_required"  # non-physical/nonvideo case
            results.append(row)
            continue
        if not isinstance(plan, dict):
            flag(sid, "SHOOTABILITY_PLAN_INVALID", "blocker",
                 "shootability must be an object")
            results.append(row)
            continue
        mode = plan.get("mode")
        row["mode"] = mode if isinstance(mode, str) else None
        if not isinstance(mode, str) or mode not in MODES:
            flag(sid, "SHOOTABILITY_MODE_INVALID", "blocker",
                 "choose a documented single/split/static/post/practical approach")
        units = plan.get("action_units")
        if not isinstance(units, list):
            flag(sid, "ACTION_UNITS_INVALID", "blocker", "action_units must be a list")
            units = []
        if physical and not units:
            flag(sid, "ACTION_UNITS_MISSING", "pending",
                 "physical AI shot needs explicit timed actions")
        seen = set()
        parsed = []
        for ix, unit in enumerate(units):
            if not isinstance(unit, dict):
                flag(sid, "ACTION_UNIT_INVALID", "blocker", f"action_units[{ix}] must be an object")
                continue
            uid = unit.get("id")
            if not isinstance(uid, str) or not ID.fullmatch(uid) or uid in seen:
                flag(sid, "ACTION_ID_INVALID", "blocker",
                     f"unit {ix} needs unique stable id")
                continue
            seen.add(uid)
            index = unit.get("beat_index")
            beats = d.get("beats", [])
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(beats):
                flag(sid, "ACTION_BEAT_INVALID", "blocker",
                     f"{uid}: beat_index must reference a real director beat")
                continue
            a, b = unit.get("from_s"), unit.get("to_s")
            beat = beats[index]
            if (not valid_time(a) or not valid_time(b) or
                    not beat["from_s"] - 0.001 <= a < b <= beat["to_s"] + 0.001):
                flag(sid, "ACTION_TIME_INVALID", "blocker",
                     f"{uid}: action interval must sit inside selected beat")
                continue
            actor = unit.get("actor_id")
            if actor is not None and actor not in characters:
                flag(sid, "ACTION_ACTOR_UNKNOWN", "blocker",
                     f"{uid}: actor must be declared in the base plan")
            if physical and actor is None:
                flag(sid, "ACTION_ACTOR_MISSING", "pending",
                     f"{uid}: physical action requires character ID")
            hand = unit.get("hand")
            if not isinstance(hand, str) or hand not in HANDS:
                flag(sid, "ACTION_HAND_INVALID", "blocker",
                     f"{uid}: choose none, left, right or both")
                continue
            prop = unit.get("prop_id")
            if prop is not None and (not isinstance(prop, str) or prop not in props):
                flag(sid, "ACTION_PROP_NOT_DECLARED", "pending",
                     f"{uid}: prop ID needs explicit continuity_contract.props declaration")
            if any(not isinstance(unit.get(k), str) or not unit[k].strip()
                   for k in ("action", "visible_result")):
                flag(sid, "ACTION_DESCRIPTION_MISSING", "pending",
                     f"{uid}: describe concrete action and observable end state")
            parsed.append({"id": uid, "beat_index": index, "from_s": a, "to_s": b,
                           "actor_id": actor, "hand": hand, "prop_id": prop,
                           "action": unit.get("action"), "visible_result": unit.get("visible_result"),
                           "duration_s": round(b - a, 3)})
        row["units"] = parsed

        # Two simultaneous actions using the same hand (or both hands) by one
        # actor cannot be implemented literally unless the director changes
        # timing/blocks the motion. Simultaneous two-hand coordinated work is
        # allowed, but flagged if both hands hold the same prop.
        for ix, a in enumerate(parsed):
            for b in parsed[ix + 1:]:
                if not a["actor_id"] or a["actor_id"] != b["actor_id"]:
                    continue
                if not max(a["from_s"], b["from_s"]) < min(a["to_s"], b["to_s"]) - 0.001:
                    continue
                hand_conflict = (a["hand"] != "none" and b["hand"] != "none" and
                                 (a["hand"] == "both" or b["hand"] == "both"
                                  or a["hand"] == b["hand"]))
                if hand_conflict:
                    flag(sid, "SAME_HAND_OVERLAP", "blocker",
                         f"{a['id']} and {b['id']} assign the same hand concurrently")
                elif a["prop_id"] and a["prop_id"] == b["prop_id"]:
                    flag(sid, "SAME_PROP_TWO_HANDS_REVIEW", "review",
                         f"{a['id']} and {b['id']} manipulate one prop simultaneously; verify handoff")

        # Heuristics deliberately emit review signals, NEVER auto-declare a
        # model incapable of an action. Only count distinct explicit actions.
        prop_actions = [x for x in parsed if x["hand"] != "none" and x["prop_id"]]
        for item in prop_actions:
            if item["duration_s"] < 0.55:
                flag(sid, "FAST_FINE_MOTOR_REVIEW", "review",
                     f"{item['id']}: sub-0.55s prop manipulation; verify with a sample")
        by_actor = {}
        for item in prop_actions:
            by_actor.setdefault(item["actor_id"], []).append(item)
        crowded = False
        for actor, items in by_actor.items():
            for pos, first in enumerate(items):
                window = [x for x in items if first["from_s"] <= x["from_s"] <
                          first["from_s"] + 2.0]
                if len(window) >= 3:
                    crowded = True
                    flag(sid, "DENSE_PROP_SEQUENCE_REVIEW", "review",
                         f"{actor}: {len(window)} prop actions start within 2s near {first['from_s']:g}s")
                    break
        if physical and crowded and mode == "single_take":
            fallback = plan.get("fallback")
            if not isinstance(fallback, str) or not fallback.strip():
                flag(sid, "DENSE_ACTION_FALLBACK_PENDING", "pending",
                     "propose a split-take / practical insert / simplified version")
        elif physical and len(prop_actions) >= 4 and mode == "single_take":
            flag(sid, "MULTI_PROP_REHEARSAL_REVIEW", "review",
                 "four or more prop actions in one take; verify route and edit fallback")
        this = [f for f in findings if f["shot_id"] == sid]
        if any(f["severity"] == "blocker" for f in this):
            row["status"] = "blocked"
        elif any(f["severity"] == "pending" for f in this):
            row["status"] = "incomplete"
        else:
            row["status"] = "structured_review_only" if this else "structured"
        results.append(row)
    blocking = sum(f["severity"] == "blocker" for f in findings)
    pending = sum(f["severity"] == "pending" for f in findings)
    return {
        "status": "offline_shootability_review",
        "shots": results,
        "findings": findings,
        "blockers": blocking,
        "pending": pending,
        "review_signals": sum(f["severity"] == "review" for f in findings),
        "director_structure_ready": blocking == 0 and pending == 0,
        "model_capability_verified": False,
        "real_footage_tested": False,
    }
