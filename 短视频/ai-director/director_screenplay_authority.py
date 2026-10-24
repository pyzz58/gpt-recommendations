#!/usr/bin/env python3
"""QO-D01: screenplay owns story facts, dialogue and character identity.

One showrunner may interpret images, editing, staging and rhythm freely;
downstream roles may only propose, never authorize, edits to the writer's
actual story. The ledger already locks the BASE digest. This guard also
validates the SCRIPT digest and the source dialogue carried into the sound
department, including a director shot covering multiple screenplay beats.
Explicit source-edit controls cannot be smuggled through specialist JSON.
Text-only semantic claims always need a real writer / editorial human review.
No tools, no model calls, no raw manuscript in logs.
"""
from __future__ import annotations

from copy import deepcopy

import agent_team as team

VERSION = "one-reviewed-screenplay-story-authority-v1"
ROLES = frozenset(team.SPECS)
EXPLICIT_STORY_MUTATIONS = frozenset({
    "replacement_screenplay", "new_screenplay", "approved_screenplay",
    "approved_story_changes", "new_story_events", "new_facts",
    "rewritten_dialogue", "dialogue_replacement", "approved_dialogue_changes",
    "new_character", "new_character_identity", "source_text_override",
    "source_adaptation_override", "source_beat_rewrites",
})


class ScreenplayAuthorityError(ValueError):
    """Only stable error codes: never echo private manuscript text."""


def _need(ok, code):
    if not ok:
        raise ScreenplayAuthorityError(code)


def _source_locked(base, state):
    _need(isinstance(base, dict) and isinstance(state, dict),
          "STORY_AUTHORITY_BASE_OR_LEDGER_INVALID")
    mode = base.get("screenplay_handoff_mode")
    if mode is None:
        _need(base.get("director_shot_coverage_mode") is None,
              "STORY_AUTHORITY_COVERAGE_WITHOUT_WRITER_SCREENPLAY")
        return False
    _need(isinstance(mode, dict) and
          mode.get("kind") == "adapted_screenplay_planning_only" and
          mode.get("no_silent_story_or_dialogue_rewrite") is True and
          mode.get("reviewer_identity_authenticated") is False and
          isinstance(mode.get("screenplay_sha256"), str) and
          mode["screenplay_sha256"] == state.get("source_digest") and
          state.get("source_review_bound") is True and
          state.get("base_digest") == team.fingerprint(base),
          "STORY_AUTHORITY_WRITER_SOURCE_OR_BASE_NOT_LOCKED")
    return True


def snapshot(base, state):
    """Private context for the original ten roles; no false human approval."""
    if not _source_locked(base, state):
        return None
    ordered = []
    for shot in base["shots"]:
        provenance = shot.get("source_adaptation", {})
        _need(isinstance(provenance, dict) and
              isinstance(provenance.get("beat_id"), str) and
              isinstance(provenance.get("dialogue"), list),
              "STORY_AUTHORITY_SHOT_PROVENANCE_MISSING")
        ids = provenance.get("covered_beat_ids", [provenance["beat_id"]])
        _need(isinstance(ids, list) and ids and
              all(isinstance(x, str) and x for x in ids),
              "STORY_AUTHORITY_BEAT_PROVENANCE_INVALID")
        records = provenance.get("covered_beat_source_records")
        if base.get("director_shot_coverage_mode") is not None:
            _need(isinstance(records, list) and
                  [r.get("beat_id") for r in records if isinstance(r, dict)] == ids,
                  "STORY_AUTHORITY_REBLOCKED_SOURCE_AUDIT_MISSING")
        ordered.append({
            "shot_id": shot["id"],
            "original_screenplay_beat_ids": list(ids),
            "source_character_ids": deepcopy(shot.get("character_ids", [])),
            "source_prop_ids": deepcopy(shot.get("prop_ids", [])),
            "source_claim_ids": deepcopy(shot.get("claim_ids", [])),
            "source_dialogue_digest": team.fingerprint(provenance["dialogue"]),
            "source_narration_digest": team.fingerprint(
                shot.get("narration", "")),
        })
    return {
        "kind": "source_bound_single_screenplay_story_authority",
        "version": VERSION,
        "screenplay_digest": state["source_digest"],
        "director_base_digest": state["base_digest"],
        "source_shot_provenance": ordered,
        "one_screenplay_source_not_an_auto_approval": True,
        "writer_must_author_story_rewrites": True,
        "director_may_choose_cinematography_coverage_rhythm_and_actor_direction":
            True,
        "crew_may_propose_but_never_approve_story_changes": True,
        "author_or_human_review_authenticated": False,
        "actual_video_story_accuracy_verified": False,
    }


def _illegal_key_tree(value):
    """Inspect structure only, NEVER scan director's creative prose."""
    if isinstance(value, dict):
        for key, obj in value.items():
            if isinstance(key, str) and key in EXPLICIT_STORY_MUTATIONS:
                return True
            if _illegal_key_tree(obj):
                return True
    elif isinstance(value, list):
        return any(_illegal_key_tree(v) for v in value)
    return False


def _spoken_cues_exactly_match_source(source_lines, cues):
    """A line may have multiple cue segments; the exact words must survive."""
    _need(isinstance(source_lines, list) and isinstance(cues, list),
          "STORY_AUTHORITY_DIALOGUE_CUES_SHAPE")
    if not source_lines:
        _need(not cues, "STORY_AUTHORITY_UNSOURCED_ADDITIONAL_DIALOGUE")
        return
    cursor = 0
    for original in source_lines:
        _need(isinstance(original, dict) and
              isinstance(original.get("speaker"), str) and
              isinstance(original.get("line"), str),
              "STORY_AUTHORITY_CANONICAL_DIALOGUE_SHAPE")
        expected, found = original["line"], ""
        _need(bool(expected), "STORY_AUTHORITY_EMPTY_CANONICAL_LINE")
        while len(found) < len(expected):
            _need(cursor < len(cues),
                  "STORY_AUTHORITY_MISSING_OR_TRUNCATED_DIALOGUE")
            cue = cues[cursor]
            _need(isinstance(cue, dict),
                  "STORY_AUTHORITY_ACTUAL_DIALOGUE_CUE_SHAPE")
            text = cue.get("text", cue.get("line"))
            _need(isinstance(text, str) and text and
                  cue.get("speaker") == original["speaker"] and
                  expected.startswith(found + text),
                  "STORY_AUTHORITY_DIALOGUE_WORDS_OR_SPEAKER_CHANGED")
            found += text
            cursor += 1
        _need(found == expected,
              "STORY_AUTHORITY_DIALOGUE_LINE_NOT_EXACT")
    _need(cursor == len(cues),
          "STORY_AUTHORITY_EXTRA_DIALOGUE_NOT_IN_SCREENPLAY")


def validate_role(base, state, task_id, payload):
    """Fail on actual unsourced source edits, while allowing cinema decisions.

    Narrative assertions embedded in open prose cannot be proved by a local
    parser. Those stay explicitly pending editorial and human judgment.
    """
    receipt = snapshot(base, state)
    if receipt is None:
        return None
    _need(task_id in ROLES and isinstance(payload, dict),
          "STORY_AUTHORITY_SPECIALIST_UNKNOWN")
    _need(not _illegal_key_tree(payload),
          "STORY_AUTHORITY_EXPLICIT_UNAPPROVED_STORY_MUTATION")
    if task_id == "sound":
        sources = {s["id"]: s for s in base["shots"]}
        _need(isinstance(payload.get("shots"), dict),
              "STORY_AUTHORITY_MISSING_SOUND_SHOTS")
        for sid, item in payload["shots"].items():
            _need(sid in sources and isinstance(item, dict),
                  "STORY_AUTHORITY_UNKNOWN_SOUND_SHOT")
            speech = item.get("speech")
            _need(isinstance(speech, dict),
                  "STORY_AUTHORITY_SOUND_SPEECH_MISSING")
            _spoken_cues_exactly_match_source(
                sources[sid]["source_adaptation"]["dialogue"],
                speech.get("dialogue"))
    if task_id == "script_edit":
        treatment = payload.get("story_treatment", {})
        _need(all(isinstance(p, dict) and
                  p.get("approved") is False and
                  p.get("requires_user_approval") is True
                  for p in treatment.get("source_change_proposals", [])),
              "STORY_AUTHORITY_WRITER_PROPOSALS_NOT_APPROVED")
    return {
        "kind": "offline_screenplay_source_craft_guard_receipt",
        "version": VERSION,
        "source_digest": receipt["screenplay_digest"],
        "base_digest": receipt["director_base_digest"],
        "source_dialogue_exact_if_sound_role": task_id == "sound",
        "unauthorized_source_override_fields_found": False,
        "director_cinema_and_performance_interpretation_allowed": True,
        "real_semantic_fidelity_human_verified": False,
        "changes_to_canonical_script_authored_here": False,
    }
