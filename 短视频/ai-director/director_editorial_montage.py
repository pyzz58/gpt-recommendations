#!/usr/bin/env python3
"""QO-D09: director-owned editorial montages across physical shots/scenes.

A montage is a SEQUENCE OF SHOTS, never a fabricated single physical shot.
This module does not rewrite screenplay beats, reorder approved footage,
invent temporal chronology, produce audio/video or certify art quality.
"""
from __future__ import annotations

from copy import deepcopy

import agent_team

VERSION = "director-editorial-montage-v1"
PLAN = {"version", "episode_id", "source_screenplay_digest",
        "director_breakdown_digest", "coverage_digest", "sequences"}
SEQUENCE = {"sequence_id", "montage_kind", "shot_ids", "director_intention",
            "audience_orientation", "rejected_alternative", "ai_fallback",
            "seams"}
SEAM = {"out_shot_id", "in_shot_id", "out_scene_id", "in_scene_id",
        "edit_type", "time_relation", "source_time_evidence",
        "orientation_before", "orientation_after", "axis_light_bridge",
        "performer_prop_bridge", "sound_intention", "viewer_before",
        "viewer_after", "editorial_reason", "ai_fallback",
        "exit_state_digest", "entry_state_digest"}
KINDS = {"cross_scene", "time_shift"}
CUTS = {"hard_cut", "match_cut", "dissolve", "sound_bridge", "jump_cut"}
TIME = {"unstated", "earlier", "later", "parallel", "continuous"}


class MontageError(ValueError):
    """Error codes only: never leak unpublished screenplay to logs."""


def _need(ok, code):
    if not ok:
        raise MontageError(code)


def _words(value, code, minimum=16):
    _need(isinstance(value, str) and minimum <= len(value.strip()) <= 1600
          and "\0" not in value, code)


def _state(sh, side):
    continuity = sh.get("continuity_state", {})
    _need(isinstance(continuity, dict), "MONTAGE_SOURCE_STATE_INVALID")
    key = "props_after" if side == "exit" else "props_before"
    actor_key = "actors_after" if side == "exit" else "actors_before"
    _need(isinstance(continuity.get(key), dict) and
          isinstance(continuity.get(actor_key), dict),
          "MONTAGE_SOURCE_STATE_MISSING")
    return {"props": continuity[key], "actors": continuity[actor_key]}


def validate(handoff, episode, proof, coverage, plan):
    """Check exact adjacent cuts, source scenes, state digests and time claims."""
    _need(isinstance(plan, dict) and set(plan) == PLAN,
          "MONTAGE_PLAN_SHAPE")
    normalized_coverage = {k: v for k, v in coverage.items()
                           if k != "montage_plan"}
    _need(plan["version"] == VERSION and
          plan["episode_id"] == episode["episode_id"] and
          plan["source_screenplay_digest"] == proof["screenplay_digest"] and
          plan["director_breakdown_digest"] == proof["director_breakdown_digest"] and
          plan["coverage_digest"] == agent_team.fingerprint(normalized_coverage),
          "MONTAGE_STALE_SCRIPT_OR_COVERAGE")
    seqs = plan["sequences"]
    _need(isinstance(seqs, list) and 1 <= len(seqs) <= 30,
          "MONTAGE_SEQUENCE_COUNT")
    shots = coverage["shots"]
    shot_order = [s["shot_id"] for s in shots]
    _need(len(shot_order) == len(set(shot_order)),
          "MONTAGE_DUPLICATE_SHOT_IN_COVERAGE")
    by_scene_beat = {beat["id"]: (scene, beat)
                     for scene in handoff["screenplay_scenes"]
                     for beat in scene["beats"]}
    source = {s["source_adaptation"]["beat_id"]: s
              for s in handoff["reconstructed_base"]["shots"]}
    shot_info = {}
    for shot in shots:
        scene_ids = {by_scene_beat[sp["beat_id"]][0]["id"]
                     for sp in shot["source_spans"]}
        _need(len(scene_ids) == 1,
              "MONTAGE_ONE_SHOT_MUST_HAVE_ONE_SOURCE_SCENE")
        first = shot["source_spans"][0]["beat_id"]
        _need(source[first]["source_adaptation"]["scene_heading"] ==
              by_scene_beat[first][0]["heading"],
              "MONTAGE_SOURCE_SCENE_HEADING_DRIFT")
        shot_info[shot["shot_id"]] = {
            "source_scene_id": next(iter(scene_ids)),
            "physical_scene_id": source[first]["scene_id"],
            "first_beat": first,
            "last_beat": shot["source_spans"][-1]["beat_id"],
        }
    used, output = set(), []
    for i, seq in enumerate(seqs, 1):
        _need(isinstance(seq, dict) and set(seq) == SEQUENCE,
              "MONTAGE_SEQUENCE_SHAPE")
        _need(seq["sequence_id"] == f"M{i:02d}" and
              seq["montage_kind"] in KINDS,
              "MONTAGE_SEQUENCE_ID_OR_KIND")
        for field in ("director_intention", "audience_orientation",
                      "rejected_alternative", "ai_fallback"):
            _words(seq[field], "MONTAGE_UNEXPLAINED_DIRECTOR_CHOICE")
        ids = seq["shot_ids"]
        _need(isinstance(ids, list) and 2 <= len(ids) <= 100 and
              all(isinstance(x, str) and x in shot_info for x in ids) and
              len(set(ids)) == len(ids) and not used.intersection(ids),
              "MONTAGE_DUPLICATE_OR_UNKNOWN_SHOTS")
        positions = [shot_order.index(sid) for sid in ids]
        _need(positions == list(range(positions[0], positions[0] + len(ids))),
              "MONTAGE_NONADJACENT_OR_REORDERED_SHOTS")
        used.update(ids)
        joins = seq["seams"]
        _need(isinstance(joins, list) and len(joins) == len(ids)-1,
              "MONTAGE_MISSING_OR_EXTRA_SEAMS")
        scenes = {shot_info[x]["source_scene_id"] for x in ids}
        shifts = 0
        for j, seam in enumerate(joins):
            _need(isinstance(seam, dict) and set(seam) == SEAM,
                  "MONTAGE_SEAM_SHAPE")
            out_id, in_id = ids[j:j+2]
            out = shot_info[out_id]
            incoming = shot_info[in_id]
            _need((seam["out_shot_id"], seam["in_shot_id"],
                   seam["out_scene_id"], seam["in_scene_id"]) ==
                  (out_id, in_id, out["source_scene_id"],
                   incoming["source_scene_id"]),
                  "MONTAGE_SHOT_OR_SCENE_PROVENANCE_CHANGED")
            _need(seam["edit_type"] in CUTS and
                  seam["time_relation"] in TIME,
                  "MONTAGE_UNSUPPORTED_CUT_OR_TIME")
            if seam["time_relation"] != "unstated":
                _need(seam["time_relation"] != "continuous" or
                      out["source_scene_id"] == incoming["source_scene_id"],
                      "MONTAGE_CONTINUOUS_ACROSS_SCENE_UNPROVEN")
            if seam["time_relation"] in {"earlier", "later", "parallel"}:
                evidence = seam["source_time_evidence"]
                incoming_scene, incoming_beat = by_scene_beat[incoming["first_beat"]]
                corpus = (incoming_scene["heading"] + "\n" +
                          incoming_beat["action"])
                _words(evidence, "MONTAGE_TIME_RELATION_NEEDS_SOURCE", minimum=4)
                _need(evidence in corpus and
                      evidence in handoff["screenplay_fountain"],
                      "MONTAGE_TIME_EVIDENCE_NOT_IN_REVIEWED_SCRIPT")
                shifts += 1
            else:
                _need(seam["source_time_evidence"] == "",
                      "MONTAGE_UNSUPPORTED_TIME_EVIDENCE")
            for field in ("orientation_before", "orientation_after",
                          "axis_light_bridge", "performer_prop_bridge",
                          "sound_intention", "viewer_before", "viewer_after",
                          "editorial_reason", "ai_fallback"):
                _words(seam[field], "MONTAGE_UNEXPLAINED_CUT_OR_CONTINUITY")
            _need(seam["viewer_before"] != seam["viewer_after"],
                  "MONTAGE_NO_AUDIENCE_STATE_CHANGE")
            prev_source = source[out["last_beat"]]
            next_source = source[incoming["first_beat"]]
            exit_state = _state(prev_source, "exit")
            entry_state = _state(next_source, "entry")
            _need(seam["exit_state_digest"] == agent_team.fingerprint(exit_state) and
                  seam["entry_state_digest"] == agent_team.fingerprint(entry_state),
                  "MONTAGE_CONTINUITY_STATE_TAMPERED")
            if seam["time_relation"] == "continuous":
                for kind in ("actors", "props"):
                    for key in exit_state[kind].keys() & entry_state[kind].keys():
                        _need(exit_state[kind][key] == entry_state[kind][key],
                              "MONTAGE_CONTINUOUS_STATE_TELEPORTATION")
            output.append({
                "sequence_id": seq["sequence_id"],
                "out_shot_id": out_id,
                "in_shot_id": in_id,
                "source_scenes": [out["source_scene_id"],
                                  incoming["source_scene_id"]],
                "cut_type": seam["edit_type"],
                "time_relation": seam["time_relation"],
            })
        if seq["montage_kind"] == "cross_scene":
            _need(len(scenes) > 1, "MONTAGE_NOT_ACROSS_SCENES")
        else:
            _need(shifts > 0, "MONTAGE_TIME_SHIFT_NOT_GROUNDED")
    return {
        "kind": "director_editorial_montage_structural_receipt",
        "montage_count": len(seqs),
        "cut_count": len(output),
        "cuts": output,
        "original_screenplay_order_preserved": True,
        "source_time_quotes_exact_but_semantics_not_human_verified": True,
        "physical_shot_merging_permitted": False,
        "real_media_verified": False,
        "human_art_reviewed": False,
    }


def bind_to_base(base, plan, receipt):
    """Model-facing production notes; never assert real cuts already rendered."""
    revised = deepcopy(base)
    revised["director_editorial_montage"] = {
        "plan": deepcopy(plan),
        "receipt": deepcopy(receipt),
        "same_physical_shot_across_scenes": False,
        "changes_to_source_dialogue_or_episode_length": False,
        "actual_montage_cut_verified": False,
    }
    for seq in plan["sequences"]:
        for i, shot_id in enumerate(seq["shot_ids"]):
            shot = next(sh for sh in revised["shots"] if sh["id"] == shot_id)
            shot["montage_membership"] = {
                "sequence_id": seq["sequence_id"],
                "position": i,
                "has_incoming_cut": i > 0,
                "has_outgoing_cut": i < len(seq["shot_ids"])-1,
            }
    return revised
