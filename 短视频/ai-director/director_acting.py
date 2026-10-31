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
import json
import re

VERSION = "director-acting-contract-v1"
MODE = {
    "kind": "source_bound_acting_bible_required",
    "version": 1,
}
HANDS = frozenset({"left", "right", "both", "none"})
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
    return report
