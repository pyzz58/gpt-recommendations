#!/usr/bin/env python3
"""F01 source-bound acting contract for the existing acting/acting_coach role.

This is an offline professional preflight, not an acting-performance rating.
It separates:
  * a director-authored character performance bible (given circumstances,
    relationships, objective, obstacle, tactic habits, subtext, entry/exit), and
  * per-shot, per-character playable contracts (trigger, objective, obstacle,
    tactic, subtext, reaction, visible change, ending state, source beat).

No new agent, model call, private source copy, paid API or real-media claim.
Legacy bases without acting_contract_mode remain compatible.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from itertools import combinations
import json
import re

VERSION = "director-acting-contract-v1"
MODE = {
    "kind": "source_bound_acting_bible_required",
    "version": 1,
}
HANDS = frozenset({"left", "right", "both", "none"})
POSTURES = frozenset({"standing", "seated", "lying", "kneeling", "other"})
ENVIRONMENT_STATES = frozenset({"open", "closed"})
COMPLEXITIES = frozenset({"low", "medium", "high"})
CAPABILITY_EVIDENCE = frozenset({"none", "documented", "tested"})
GENERIC_FALLBACK_SIGNALS = ("TODO", "待定", "后续处理", "考虑一下", "以后再")
GENERIC_PHRASES = (
    "自然地", "自然表演", "表演自然", "情绪到位", "悲伤地看着",
    "很悲伤", "很生气", "开心地看着", "正常地",
)
BIBLE_FIELDS = (
    "given_circumstances", "relationships", "objective", "obstacle",
    "tactic_habits", "subtext", "entry_state", "exit_state", "source_spans",
)
SHOT_FIELDS = (
    "trigger", "objective", "obstacle", "tactic", "subtext",
    "reaction", "visible_change", "ending_state", "source_beat_id",
)
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class ActingContractError(ValueError):
    """Static codes only; never echo private screenplay text."""


def _need(ok, code):
    if not ok:
        raise ActingContractError(code)


def digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _text(value, minimum=1):
    return isinstance(value, str) and len(value.strip()) >= minimum


def _nonempty_strings(value):
    return (isinstance(value, list) and bool(value)
            and all(_text(item) for item in value))


def _source_beat_ids(source_shot):
    provenance = source_shot.get("source_adaptation") or {}
    values = []
    if _text(provenance.get("beat_id")):
        values.append(provenance["beat_id"])
    covered = provenance.get("covered_beat_ids")
    if isinstance(covered, list):
        values.extend(item for item in covered if _text(item))
    return values


def _findings():
    return {
        "version": VERSION,
        "mode": deepcopy(MODE),
        "bible_digest": None,
        "blockers": [],
        "reviews": [],
    }


def _add(items, code, detail, shot_id=None, character_id=None):
    row = {"code": code, "detail": detail}
    if shot_id is not None:
        row["shot_id"] = shot_id
    if character_id is not None:
        row["character_id"] = character_id
    items.append(row)


def inspect_bible(base, state, global_direction):
    """Validate the director-authored character performance bible."""
    report = _findings()
    mode = base.get("acting_contract_mode")
    if mode is None:
        report["not_required"] = True
        return report
    if mode != MODE:
        _add(report["blockers"], "ACTING_CONTRACT_MODE_INVALID",
             "acting_contract_mode must be the reviewed source-bound mode")
        return report
    if not isinstance(global_direction, dict):
        _add(report["blockers"], "ACTING_GLOBAL_DIRECTION_INVALID",
             "global_direction must be an object")
        return report
    bible = global_direction.get("performance_bible")
    if not isinstance(bible, dict):
        _add(report["blockers"], "ACTING_BIBLE_MISSING",
             "director_lock must author performance_bible for the strict acting mode")
        return report
    report["bible_digest"] = digest(bible)
    if bible.get("version") != 1:
        _add(report["blockers"], "ACTING_BIBLE_VERSION_INVALID",
             "performance_bible.version must be 1")
    source_digest = bible.get("source_digest")
    if (not isinstance(source_digest, str) or not _SHA256.fullmatch(source_digest)
            or source_digest != state.get("source_digest")):
        _add(report["blockers"], "ACTING_BIBLE_SOURCE_STALE",
             "performance_bible must bind the current reviewed source digest")
    characters = bible.get("characters")
    if not isinstance(characters, dict):
        _add(report["blockers"], "ACTING_BIBLE_CHARACTERS_INVALID",
             "performance_bible.characters must be an object keyed by character ID")
        return report
    declared = {c.get("id") for c in base.get("characters", [])
                if isinstance(c, dict) and _text(c.get("id"))}
    cast = sorted({cid for shot in base.get("shots", [])
                   for cid in (shot.get("character_ids") or [])
                   if _text(cid)})
    for cid in cast:
        if cid not in characters:
            _add(report["blockers"], "ACTING_BIBLE_CHARACTER_MISSING",
                 "every cast member in this episode needs a performance bible entry",
                 character_id=cid)
    for cid, item in characters.items():
        if cid not in declared:
            _add(report["blockers"], "ACTING_BIBLE_UNKNOWN_CHARACTER",
                 "performance bible cannot introduce a character absent from the plan",
                 character_id=cid)
            continue
        if not isinstance(item, dict):
            _add(report["blockers"], "ACTING_BIBLE_CHARACTER_INVALID",
                 "character performance entry must be an object",
                 character_id=cid)
            continue
        for field in BIBLE_FIELDS:
            if field not in item:
                _add(report["blockers"], "ACTING_BIBLE_FIELD_MISSING",
                     "character performance entry is missing " + field,
                     character_id=cid)
        for field in ("given_circumstances", "objective", "obstacle",
                      "subtext", "entry_state", "exit_state"):
            if not _text(item.get(field)):
                _add(report["blockers"], "ACTING_BIBLE_FIELD_EMPTY",
                     "character performance entry needs a concrete " + field,
                     character_id=cid)
        relationships = item.get("relationships")
        if not isinstance(relationships, list) or not relationships:
            _add(report["blockers"], "ACTING_BIBLE_RELATIONSHIPS_MISSING",
                 "character performance entry needs at least one relationship",
                 character_id=cid)
        else:
            for relation in relationships:
                if (not isinstance(relation, dict)
                        or not _text(relation.get("character_id"))
                        or not _text(relation.get("relation"))
                        or not _text(relation.get("stakes"))):
                    _add(report["blockers"], "ACTING_BIBLE_RELATIONSHIP_INVALID",
                         "relationship needs character_id, relation and stakes",
                         character_id=cid)
                elif relation["character_id"] not in declared:
                    _add(report["blockers"], "ACTING_BIBLE_RELATIONSHIP_UNKNOWN",
                         "relationship references an undeclared character",
                         character_id=cid)
        if not _nonempty_strings(item.get("tactic_habits")):
            _add(report["blockers"], "ACTING_BIBLE_TACTICS_MISSING",
                 "character performance entry needs concrete tactic_habits",
                 character_id=cid)
        spans = item.get("source_spans")
        if not isinstance(spans, list) or not spans:
            _add(report["blockers"], "ACTING_BIBLE_SOURCE_SPANS_MISSING",
                 "character performance entry needs at least one source span",
                 character_id=cid)
        else:
            scene_ids = {s.get("id") for s in base.get("scenes", [])
                         if isinstance(s, dict)}
            beat_ids = {beat for shot in base.get("shots", [])
                        for beat in _source_beat_ids(shot)}
            for span in spans:
                if (not isinstance(span, dict)
                        or not _text(span.get("scene_id"))
                        or not _text(span.get("beat_id"))
                        or not _text(span.get("quote"))):
                    _add(report["blockers"], "ACTING_BIBLE_SOURCE_SPAN_INVALID",
                         "source span needs scene_id, beat_id and quote",
                         character_id=cid)
                elif scene_ids and span["scene_id"] not in scene_ids:
                    _add(report["blockers"], "ACTING_BIBLE_SOURCE_SPAN_UNKNOWN",
                         "source span references an unknown scene",
                         character_id=cid)
                elif beat_ids and span["beat_id"] not in beat_ids:
                    _add(report["blockers"], "ACTING_BIBLE_SOURCE_BEAT_UNKNOWN",
                         "source span references a beat outside this episode shot plan",
                         character_id=cid)
        for field in ("objective", "obstacle", "subtext"):
            value = item.get(field)
            if _text(value) and any(signal in value for signal in GENERIC_PHRASES):
                _add(report["reviews"], "ACTING_BIBLE_GENERIC_LANGUAGE",
                     "review generic/emotional label in " + field,
                     character_id=cid)
    return report


def _inspect_hand_prop(source, shot, cast, report):
    staging = shot.get("staging") or {}
    hand_prop = staging.get("hand_prop")
    if hand_prop is None:
        moves = (source.get("continuity_state") or {}).get("prop_moves") or []
        if moves:
            _add(report["reviews"], "ACTING_HAND_PROP_UNDECLARED",
                 "physical prop moves should be paired with explicit hand ownership",
                 shot_id=source.get("id"))
        return
    if not isinstance(hand_prop, list):
        _add(report["blockers"], "ACTING_HAND_PROP_INVALID",
             "staging.hand_prop must be a list",
             shot_id=source.get("id"))
        return
    props = set((source.get("continuity_contract") or {}).get("props", {}))
    if not props:
        props = set((source.get("art") or {}).get("prop_ids", []))
    intervals = {}
    duration = source.get("duration")
    for entry in hand_prop:
        if not isinstance(entry, dict):
            _add(report["blockers"], "ACTING_HAND_PROP_INVALID",
                 "every hand_prop entry must be an object",
                 shot_id=source.get("id"))
            continue
        actor = entry.get("actor_id")
        hand = entry.get("hand")
        prop = entry.get("prop_id")
        start, end = entry.get("from_s"), entry.get("to_s")
        if actor not in cast:
            _add(report["blockers"], "ACTING_HAND_PROP_ACTOR_UNKNOWN",
                 "hand_prop actor must be in this shot's cast",
                 shot_id=source.get("id"))
        if hand not in HANDS:
            _add(report["blockers"], "ACTING_HAND_PROP_HAND_INVALID",
                 "hand must be left/right/both/none",
                 shot_id=source.get("id"), character_id=actor)
        if prop is not None and prop not in props:
            _add(report["blockers"], "ACTING_HAND_PROP_UNKNOWN",
                 "hand_prop prop_id must be declared in the continuity contract",
                 shot_id=source.get("id"), character_id=actor)
        if (not isinstance(start, (int, float)) or isinstance(start, bool)
                or not isinstance(end, (int, float)) or isinstance(end, bool)
                or start < 0 or end <= start or end > duration + 1e-9):
            _add(report["blockers"], "ACTING_HAND_PROP_TIME_INVALID",
                 "hand_prop time window must sit inside the shot",
                 shot_id=source.get("id"), character_id=actor)
            continue
        if not _text(entry.get("action")) or not _text(entry.get("visible_result")):
            _add(report["blockers"], "ACTING_HAND_PROP_ACTION_MISSING",
                 "hand_prop needs action and visible_result",
                 shot_id=source.get("id"), character_id=actor)
        key = (actor, hand)
        for old_start, old_end in intervals.get(key, []):
            if start < old_end and old_start < end:
                _add(report["blockers"], "ACTING_HAND_OVERLAP",
                     "one hand cannot perform two overlapping actions",
                     shot_id=source.get("id"), character_id=actor)
                break
        intervals.setdefault(key, []).append((start, end))


def _props_for(source):
    props = set((source.get("continuity_contract") or {}).get("props", {}))
    if not props:
        props = set((source.get("art") or {}).get("prop_ids", []))
    return props


def _hand_owner(phase, prop):
    for actor, entry in (phase or {}).items():
        hands = (entry or {}).get("hands") or {}
        for hand in ("left", "right"):
            if hands.get(hand) == prop:
                return actor, hand
    return None, None


def _validate_hands(hands, props, report, sid, cid):
    if not isinstance(hands, dict) or set(hands) != {"left", "right"}:
        _add(report["blockers"], "ACTING_HANDS_INVALID",
             "hands must contain exactly left and right",
             shot_id=sid, character_id=cid)
        return
    for hand, value in hands.items():
        if value not in ("free", "none") and value not in props:
            _add(report["blockers"], "ACTING_HAND_PROP_UNKNOWN",
                 "physical_state hand references an undeclared prop",
                 shot_id=sid, character_id=cid)


def _inspect_dual_person(source, shot, cast, report):
    sid = source.get("id")
    staging = shot.get("staging") or {}
    props = _props_for(source)
    cut_note = staging.get("cut_note")
    if cut_note:
        _add(report["reviews"], "ACTING_INTENTIONAL_CUT",
             "an explicit cut note changes physical state between shots",
             shot_id=sid)
    environment = staging.get("environment_state")
    if environment is not None:
        if not isinstance(environment, dict):
            _add(report["blockers"], "ACTING_ENVIRONMENT_STATE_INVALID",
                 "environment_state must be an object", shot_id=sid)
        else:
            for kind in ("doors", "windows"):
                entries = environment.get(kind)
                if entries is None:
                    continue
                if not isinstance(entries, dict):
                    _add(report["blockers"], "ACTING_ENVIRONMENT_STATE_INVALID",
                         kind + " must be an object keyed by stable ID", shot_id=sid)
                    continue
                for object_id, entry in entries.items():
                    if (not _text(object_id) or not isinstance(entry, dict)
                            or entry.get("start") not in ENVIRONMENT_STATES
                            or entry.get("end") not in ENVIRONMENT_STATES):
                        _add(report["blockers"], "ACTING_ENVIRONMENT_STATE_INVALID",
                             kind + " entries need a stable ID and open/closed start/end",
                             shot_id=sid)
                        continue
                    if entry["start"] != entry["end"]:
                        if entry.get("changed_by") not in cast or not _text(entry.get("cause")):
                            _add(report["blockers"], "ACTING_ENVIRONMENT_CHANGE_UNMOTIVATED",
                                 "door/window change needs an in-shot actor and cause",
                                 shot_id=sid)
    if not cast:
        return
    state = staging.get("physical_state")
    if not isinstance(state, dict):
        _add(report["blockers"], "ACTING_PHYSICAL_STATE_MISSING",
             "strict acting shots need physical_state start/end",
             shot_id=sid)
        return
    phases = {}
    for phase_name in ("start", "end"):
        phase = state.get(phase_name)
        if not isinstance(phase, dict):
            _add(report["blockers"], "ACTING_PHYSICAL_STATE_INVALID",
                 "physical_state needs start and end objects",
                 shot_id=sid)
            continue
        phases[phase_name] = phase
        for cid in cast:
            entry = phase.get(cid)
            if not isinstance(entry, dict):
                _add(report["blockers"], "ACTING_PHYSICAL_ACTOR_MISSING",
                     "each cast member needs a physical state at shot boundaries",
                     shot_id=sid, character_id=cid)
                continue
            if entry.get("posture") not in POSTURES:
                _add(report["blockers"], "ACTING_POSTURE_INVALID",
                     "posture must be standing/seated/lying/kneeling/other",
                     shot_id=sid, character_id=cid)
            if not _text(entry.get("facing")):
                _add(report["blockers"], "ACTING_FACING_MISSING",
                     "physical state needs a concrete facing direction",
                     shot_id=sid, character_id=cid)
            _validate_hands(entry.get("hands"), props, report, sid, cid)
        for cid in set(phase) - set(cast):
            _add(report["blockers"], "ACTING_PHYSICAL_ACTOR_UNKNOWN",
                 "physical state references an actor outside this shot",
                 shot_id=sid, character_id=cid)
    if len(phases) == 2:
        changes = state.get("posture_changes") or []
        for cid in cast:
            start = (phases["start"].get(cid) or {}).get("posture")
            end = (phases["end"].get(cid) or {}).get("posture")
            if start and end and start != end:
                ok = any(
                    isinstance(change, dict)
                    and change.get("actor_id") == cid
                    and change.get("from") == start
                    and change.get("to") == end
                    and _text(change.get("cause"))
                    for change in changes
                )
                if not ok:
                    _add(report["blockers"], "ACTING_POSTURE_CHANGE_UNMOTIVATED",
                         "posture change needs actor_id/from/to/cause",
                         shot_id=sid, character_id=cid)
    relationships = staging.get("relationship_map")
    if len(cast) >= 2:
        if not isinstance(relationships, list):
            _add(report["blockers"], "ACTING_RELATIONSHIP_MAP_MISSING",
                 "multi-person shots need a relationship_map",
                 shot_id=sid)
        else:
            valid_rows = []
            for row in relationships:
                if (not isinstance(row, dict) or row.get("actor_id") not in cast
                        or row.get("target_id") not in cast
                        or row.get("actor_id") == row.get("target_id")
                        or not all(_text(row.get(key)) for key in
                                   ("gaze", "body_orientation", "distance", "interaction"))):
                    _add(report["blockers"], "ACTING_RELATIONSHIP_ROW_INVALID",
                         "relationship_map rows need distinct in-cast actors and concrete interaction fields",
                         shot_id=sid)
                    continue
                valid_rows.append(row)
            if len(cast) == 2:
                for actor in cast:
                    target = next(cid for cid in cast if cid != actor)
                    if not any(row["actor_id"] == actor and row["target_id"] == target
                               for row in valid_rows):
                        _add(report["blockers"], "ACTING_RELATIONSHIP_ROW_MISSING",
                             "each dual-person actor needs gaze/body/distance/interaction toward the other",
                             shot_id=sid, character_id=actor)
            for first, second in combinations(sorted(cast), 2):
                if not any(
                    {row["actor_id"], row["target_id"]} == {first, second}
                    for row in valid_rows
                ):
                    _add(report["blockers"], "ACTING_RELATIONSHIP_PAIR_MISSING",
                         "relationship_map needs at least one interaction row for every cast pair",
                         shot_id=sid)
    handoffs = staging.get("handoffs")
    if handoffs is None:
        handoffs = []
    if not isinstance(handoffs, list):
        _add(report["blockers"], "ACTING_HANDOFF_INVALID",
             "handoffs must be a list",
             shot_id=sid)
        handoffs = []
    orders = set()
    for entry in handoffs:
        if not isinstance(entry, dict):
            _add(report["blockers"], "ACTING_HANDOFF_INVALID",
                 "every handoff must be an object", shot_id=sid)
            continue
        order = entry.get("order")
        if type(order) is not int or order in orders:
            _add(report["blockers"], "ACTING_HANDOFF_ORDER_INVALID",
                 "handoff order must be a unique integer", shot_id=sid)
        orders.add(order)
        from_actor, to_actor = entry.get("from_actor"), entry.get("to_actor")
        prop = entry.get("prop_id")
        if from_actor not in cast or to_actor not in cast or from_actor == to_actor:
            _add(report["blockers"], "ACTING_HANDOFF_ACTOR_INVALID",
                 "handoff needs two distinct actors from this shot",
                 shot_id=sid)
        if prop not in props:
            _add(report["blockers"], "ACTING_HANDOFF_PROP_UNKNOWN",
                 "handoff prop must be declared in the continuity contract",
                 shot_id=sid)
        start, end = entry.get("from_s"), entry.get("to_s")
        if (not isinstance(start, (int, float)) or isinstance(start, bool)
                or not isinstance(end, (int, float)) or isinstance(end, bool)
                or start < 0 or end <= start or end > source.get("duration", 0) + 1e-9):
            _add(report["blockers"], "ACTING_HANDOFF_TIME_INVALID",
                 "handoff time window must sit inside the shot", shot_id=sid)
        if not _text(entry.get("action")) or not _text(entry.get("visible_result")):
            _add(report["blockers"], "ACTING_HANDOFF_ACTION_MISSING",
                 "handoff needs action and visible_result", shot_id=sid)
        if entry.get("visible") is not True:
            if entry.get("visible") is False and _text(entry.get("note")):
                _add(report["reviews"], "ACTING_OFFSCREEN_HANDOFF",
                     "offscreen handoff needs human confirmation", shot_id=sid)
            else:
                _add(report["blockers"], "ACTING_HANDOFF_VISIBILITY_INVALID",
                     "handoff needs visible=true or visible=false with a note",
                     shot_id=sid)
    if len(phases) == 2:
        for prop in props:
            start_actor, _ = _hand_owner(phases["start"], prop)
            end_actor, _ = _hand_owner(phases["end"], prop)
            if start_actor == end_actor:
                continue
            evidence = any(
                isinstance(entry, dict) and entry.get("prop_id") == prop
                for entry in handoffs
            ) or any(
                isinstance(entry, dict) and entry.get("prop_id") == prop
                for entry in (staging.get("hand_prop") or [])
            )
            if not evidence:
                _add(report["blockers"], "ACTING_HAND_STATE_UNMOTIVATED",
                     "hand ownership changes need a pickup/place/handoff event",
                     shot_id=sid)
            if start_actor and end_actor and start_actor != end_actor:
                if not any(
                    isinstance(entry, dict)
                    and entry.get("prop_id") == prop
                    and entry.get("from_actor") == start_actor
                    and entry.get("to_actor") == end_actor
                    for entry in handoffs
                ):
                    _add(report["blockers"], "ACTING_HANDOFF_MISSING",
                         "cross-actor ownership needs an ordered handoff",
                         shot_id=sid)


def _inspect_cross_shot(base, payload, report):
    shots = payload.get("shots") or {}
    sources = [shot.get("id") for shot in base.get("shots", [])]
    if not sources or set(shots) != set(sources):
        return  # Scoped revision: per-shot checks plus ledger merge handle linkage.
    for before_id, after_id in zip(sources, sources[1:]):
        before = shots.get(before_id) or {}
        after = shots.get(after_id) or {}
        before_state = (before.get("staging") or {}).get("physical_state") or {}
        after_state = (after.get("staging") or {}).get("physical_state") or {}
        before_end = before_state.get("end") or {}
        after_start = after_state.get("start") or {}
        cut_note = (after.get("staging") or {}).get("cut_note") or ""
        for actor in set(before_end) & set(after_start):
            old = before_end.get(actor) or {}
            new = after_start.get(actor) or {}
            old_hands, new_hands = old.get("hands") or {}, new.get("hands") or {}
            if old_hands != new_hands:
                changed = {
                    value for value in list(old_hands.values()) + list(new_hands.values())
                    if value not in ("free", "none")
                }
                handoff = any(
                    isinstance(entry, dict) and entry.get("prop_id") in changed
                    for shot in (before, after)
                    for entry in ((shot.get("staging") or {}).get("handoffs") or [])
                )
                if not handoff:
                    if cut_note:
                        _add(report["reviews"], "ACTING_INTENTIONAL_CUT_STATE_CHANGE",
                             "cut note explains a hand-state change",
                             shot_id=after_id, character_id=actor)
                    else:
                        _add(report["blockers"], "ACTING_HAND_STATE_JUMP",
                             "hand ownership changes across a cut without a visible event or note",
                             shot_id=after_id, character_id=actor)
            if old.get("posture") != new.get("posture"):
                changes = (after_state.get("posture_changes") or [])
                explained = any(
                    isinstance(change, dict)
                    and change.get("actor_id") == actor
                    and change.get("from") == old.get("posture")
                    and change.get("to") == new.get("posture")
                    and _text(change.get("cause"))
                    for change in changes
                )
                if not explained:
                    if cut_note:
                        _add(report["reviews"], "ACTING_INTENTIONAL_CUT_STATE_CHANGE",
                             "cut note explains a posture change",
                             shot_id=after_id, character_id=actor)
                    else:
                        _add(report["blockers"], "ACTING_POSTURE_STATE_JUMP",
                             "posture changes across a cut without an action or note",
                             shot_id=after_id, character_id=actor)
        for kind in ("doors", "windows"):
            before_env = (((before.get("staging") or {}).get("environment_state") or {})
                          .get(kind) or {})
            after_env = (((after.get("staging") or {}).get("environment_state") or {})
                         .get(kind) or {})
            for object_id in set(before_env) & set(after_env):
                old_env = before_env.get(object_id) or {}
                new_env = after_env.get(object_id) or {}
                if not isinstance(old_env, dict) or not isinstance(new_env, dict):
                    continue
                if old_env.get("end") == new_env.get("start"):
                    continue
                if new_env.get("start") != new_env.get("end"):
                    continue
                if cut_note:
                    _add(report["reviews"], "ACTING_INTENTIONAL_CUT_STATE_CHANGE",
                         "cut note explains a door/window state change",
                         shot_id=after_id)
                else:
                    _add(report["blockers"], "ACTING_ENVIRONMENT_STATE_JUMP",
                         "door/window state changes across a cut without an action or note",
                         shot_id=after_id)


def _inspect_production_feasibility(source, shot, cast, report):
    """Separate professional staging choice from unverified model capability."""
    if not cast:
        return
    sid = source.get("id")
    staging = shot.get("staging") or {}
    feasibility = staging.get("production_feasibility")
    if not isinstance(feasibility, dict):
        _add(report["blockers"], "ACTING_FEASIBILITY_MISSING",
             "strict acting shots need production_feasibility for model-risk planning",
             shot_id=sid)
        return
    for field in ("professional_intent", "model_risk", "fallback_route",
                  "fallback_preserves_story"):
        if not _text(feasibility.get(field)):
            _add(report["blockers"], "ACTING_FEASIBILITY_FIELD_MISSING",
                 "production_feasibility needs concrete " + field,
                 shot_id=sid)
    complexity = feasibility.get("physical_complexity")
    if complexity not in COMPLEXITIES:
        _add(report["blockers"], "ACTING_COMPLEXITY_INVALID",
             "physical_complexity must be low/medium/high",
             shot_id=sid)
    evidence = feasibility.get("capability_evidence")
    if evidence not in CAPABILITY_EVIDENCE:
        _add(report["blockers"], "ACTING_CAPABILITY_EVIDENCE_INVALID",
             "capability_evidence must be none/documented/tested",
             shot_id=sid)
    if evidence in ("documented", "tested") and not _text(feasibility.get("evidence_ref")):
        _add(report["blockers"], "ACTING_CAPABILITY_EVIDENCE_MISSING",
             "documented/tested capability claims need an evidence_ref",
             shot_id=sid)
    if evidence == "tested" and not _text(feasibility.get("test_environment")):
        _add(report["blockers"], "ACTING_TEST_ENVIRONMENT_MISSING",
             "tested capability claims need the actual test environment",
             shot_id=sid)
    if evidence == "tested":
        _add(report["reviews"], "ACTING_TESTED_CAPABILITY_HUMAN_VERIFY",
             "a tested capability claim still requires human evidence review",
             shot_id=sid)
    fallback = feasibility.get("fallback_route")
    if _text(fallback) and any(signal in fallback for signal in GENERIC_FALLBACK_SIGNALS):
        _add(report["reviews"], "ACTING_FALLBACK_GENERIC",
             "fallback_route reads generic; specify the actual alternate shot/edit",
             shot_id=sid)
    handoffs = staging.get("handoffs") or []
    action_units = (shot.get("shootability") or {}).get("action_units") or []
    hand_props = staging.get("hand_prop") or []
    posture_changes = (staging.get("physical_state") or {}).get("posture_changes") or []
    computed = "low"
    if (len(cast) >= 3 or handoffs or len(action_units) >= 2
            or len(hand_props) >= 2 or posture_changes):
        computed = "medium"
    if (len(action_units) >= 4 or len(hand_props) >= 3
            or (handoffs and len(cast) >= 3)
            or (handoffs and posture_changes)):
        computed = "high"
    rank = {"low": 0, "medium": 1, "high": 2}
    if complexity in rank and rank[complexity] < rank[computed]:
        _add(report["reviews"], "ACTING_COMPLEXITY_UNDERREPORTED",
             "physical_complexity is lower than the authored interaction signals",
             shot_id=sid)
    mode = (shot.get("shootability") or {}).get("mode")
    if computed == "high" and mode == "single_take":
        if not _text(fallback):
            _add(report["blockers"], "ACTING_FALLBACK_MISSING",
                 "a high-complexity single take needs a concrete fallback route",
                 shot_id=sid)
        else:
            _add(report["reviews"], "ACTING_SINGLE_TAKE_REVIEW",
                 "high-complexity single take is a rehearsal risk, not a proven model failure",
                 shot_id=sid)


def inspect_delivery(base, state, payload):
    """Validate per-shot/per-character acting contracts and hand ownership."""
    report = _findings()
    mode = base.get("acting_contract_mode")
    if mode is None:
        report["not_required"] = True
        return report
    if mode != MODE:
        _add(report["blockers"], "ACTING_CONTRACT_MODE_INVALID",
             "acting_contract_mode must be the reviewed source-bound mode")
        return report
    lock = (state.get("tasks", {}).get("director_lock", {})
            .get("deliverable") or {})
    global_direction = lock.get("global_direction") if isinstance(lock, dict) else None
    bible_report = inspect_bible(base, state, global_direction)
    report["blockers"].extend(bible_report["blockers"])
    report["reviews"].extend(bible_report["reviews"])
    report["bible_digest"] = bible_report["bible_digest"]
    bible = ((global_direction or {}).get("performance_bible")
             if isinstance(global_direction, dict) else None)
    if not isinstance(bible, dict):
        return report
    digest_value = digest(bible)
    shots = payload.get("shots")
    if not isinstance(shots, dict):
        _add(report["blockers"], "ACTING_SHOTS_INVALID",
             "acting payload must contain a shots object")
        return report
    sources = {s.get("id"): s for s in base.get("shots", [])
               if isinstance(s, dict)}
    for sid, shot in shots.items():
        source = sources.get(sid)
        if source is None or not isinstance(shot, dict):
            _add(report["blockers"], "ACTING_SHOT_UNKNOWN",
                 "acting delivery references an unknown shot", shot_id=sid)
            continue
        continuity = shot.get("continuity") or {}
        bound_digest = continuity.get("performance_bible_digest")
        if bound_digest is not None and bound_digest != digest_value:
            _add(report["blockers"], "ACTING_BIBLE_DIGEST_MISMATCH",
                 "acting shot references a stale director performance bible",
                 shot_id=sid)
        cast = [cid for cid in (source.get("character_ids") or []) if _text(cid)]
        performance = shot.get("performance") or {}
        contracts = performance.get("character_contracts")
        if not cast:
            if not _text(performance.get("no_performer_reason")):
                _add(report["blockers"], "ACTING_NO_PERFORMER_REASON_MISSING",
                     "zero-actor shot needs an explicit no_performer_reason",
                     shot_id=sid)
            if contracts not in (None, {}):
                _add(report["blockers"], "ACTING_ZERO_ACTOR_CONTRACT_FORBIDDEN",
                     "zero-actor shot must not invent a performer contract",
                     shot_id=sid)
            continue
        if not isinstance(contracts, dict):
            _add(report["blockers"], "ACTING_CHARACTER_CONTRACTS_MISSING",
                 "strict acting shots need per-character contracts",
                 shot_id=sid)
            continue
        for cid in cast:
            if cid not in contracts:
                _add(report["blockers"], "ACTING_CHARACTER_CONTRACT_MISSING",
                     "every cast member needs a per-shot performance contract",
                     shot_id=sid, character_id=cid)
        for cid, contract in contracts.items():
            if cid not in cast:
                _add(report["blockers"], "ACTING_CHARACTER_CONTRACT_UNKNOWN",
                     "performance contract references a character not in this shot",
                     shot_id=sid, character_id=cid)
                continue
            if not isinstance(contract, dict):
                _add(report["blockers"], "ACTING_CHARACTER_CONTRACT_INVALID",
                     "per-character contract must be an object",
                     shot_id=sid, character_id=cid)
                continue
            for field in SHOT_FIELDS:
                if not _text(contract.get(field)):
                    _add(report["blockers"], "ACTING_SHOT_FIELD_MISSING",
                         "per-character contract needs concrete " + field,
                         shot_id=sid, character_id=cid)
            if (_text(contract.get("objective"))
                    and contract.get("objective", "").strip()
                    == contract.get("tactic", "").strip()):
                _add(report["blockers"], "ACTING_TACTIC_EQUALS_OBJECTIVE",
                     "tactic must be a playable strategy, not a restatement of the objective",
                     shot_id=sid, character_id=cid)
            allowed_beats = _source_beat_ids(source)
            source_beat = contract.get("source_beat_id")
            if allowed_beats and _text(source_beat) and source_beat not in allowed_beats:
                _add(report["blockers"], "ACTING_SOURCE_BEAT_MISMATCH",
                     "per-shot character contract references a different source beat",
                     shot_id=sid, character_id=cid)
            for field in ("objective", "obstacle", "tactic", "subtext",
                          "reaction", "visible_change"):
                value = contract.get(field)
                if _text(value) and any(signal in value for signal in GENERIC_PHRASES):
                    _add(report["reviews"], "ACTING_GENERIC_LANGUAGE",
                         "review generic/emotional label in " + field,
                         shot_id=sid, character_id=cid)
        beats = shot.get("beats") or []
        if beats:
            performances = {str(b.get("performance")) for b in beats
                            if isinstance(b, dict)}
            if len(performances) == 1:
                _add(report["reviews"], "ACTING_BEATS_REPEAT",
                     "all beats repeat one performance phrase; verify a real change",
                     shot_id=sid)
        _inspect_hand_prop(source, shot, set(cast), report)
        _inspect_dual_person(source, shot, set(cast), report)
        _inspect_production_feasibility(source, shot, set(cast), report)
    _inspect_cross_shot(base, payload, report)
    return report
