#!/usr/bin/env python3
"""One director, one coherent art/feasibility/revision authority (QO-D10/06/12).

The three specialized director faculties are NOT separate autonomous agents.
This module binds their outputs to the SAME source, director lock, meeting and
audiovisual plan, rejects unresolved script/story or director-level defects
before crew dispatch, and routes reviewed shortcomings through the existing
team DAG or author-bound script revision route. It never runs an LLM.
"""
from __future__ import annotations

from copy import deepcopy

import agent_team as team
import director_department_command as meeting_contract
import director_whole_film_critique as whole
import director_action_rescue as action
import director_revision_lineage as lineage

VERSION = "director-integrated-creative-gates-v1"
MODE = {"kind": "director_integrated_creative_review_required",
        "before_specialists": True}
DIRECTOR_ROLES = tuple(meeting_contract.DEPARTMENTS)
SCRIPT_TYPES = frozenset(lineage.SCRIPT_KINDS)
FOCUS = {
    "acting": "Preserve the exact human choice, intention and performed hesitation.",
    "camera_art": "Keep decisive behavior visible within coherent space and eyelines.",
    "sound": "Protect exact dialogue and the sound/silence revealing the choice.",
    "editing_animation": "Keep action consequence and editorial timing legible.",
    "ai_technical": "Choose a realistic route, not an unauthorized story shortcut.",
    "quality_review": "Challenge the director's own choice and its specific tradeoffs.",
    "director_final": "Arbitrate the whole piece; keep the author and media gates shut.",
}


class CreativeIntegrationError(ValueError):
    """Non-sensitive errors: no private screenplay content is printed."""


def _need(ok, code):
    if not ok:
        raise CreativeIntegrationError(code)


def check_mode(base):
    """Explicit opt-in; old projects run unchanged unless they choose this gate."""
    current = base.get("director_integrated_creative_mode")
    _need(current is None or current == MODE,
          "INTEGRATED_DIRECTOR_MODE_INVALID")
    return current is not None


def _bind(base, state, meeting, audiovisual, holistic, rescue, *,
          artistic_method_plan=None, post=False):
    meeting_contract.validate_command(base, state, meeting)
    reviewed = whole.validate(
        base, state, meeting, audiovisual, holistic,
        artistic_method_plan=artistic_method_plan)
    filmed = action.validate(
        base, state, meeting, audiovisual, rescue,
        artistic_method_plan=artistic_method_plan)
    _need(reviewed["phase"] == (
        "post_department_design" if post else "preproduction_plan"),
        "INTEGRATED_WRONG_HOLISTIC_PHASE")
    _need(filmed["before_crew_or_post_crew"] == (
        "after_specialist_design" if post else "before_specialist_design"),
        "INTEGRATED_WRONG_SHOOTABILITY_PHASE")
    hs, ac = reviewed["snapshot"], filmed["snapshot"]
    for key_a, key_b in (
        ("source_digest", "source_digest"),
        ("episode_base_digest", "base_digest"),
        ("director_lock_digest", "director_lock_digest"),
        ("department_command_digest", "meeting_digest"),
        ("audiovisual_language_digest", "visual_digest"),
        ("artistic_methods_digest", "artistic_methods_digest"),
        ("shot_ids", "shot_ids"),
    ):
        _need(hs[key_a] == ac[key_b],
              "INTEGRATED_DIFFERENT_FILMS_OR_DIRECTORS")
    return reviewed, filmed


def preproduction_receipt(base, state, meeting, audiovisual, holistic, rescue, *,
                          artistic_method_plan=None):
    """Validate same creative snapshot and block unaddressed issues, not taste."""
    h, a = _bind(base, state, meeting, audiovisual, holistic, rescue,
                 artistic_method_plan=artistic_method_plan, post=False)
    _need(holistic["overall_next_step"] == "keep_with_open_questions",
          "INTEGRATED_FIRST_RESOLVE_DIRECTOR_OR_WRITER_ISSUES")
    _need(not any(x["decision"] in (
        "blockers_need_redesign", "return_to_screenwriter")
        for x in rescue["shots"]),
        "INTEGRATED_ACTION_DESIGN_OR_SCRIPT_BLOCKER")
    _need(all(x["response"] == "defer_until_media_review"
              for x in holistic["problems"]),
          "INTEGRATED_CREATIVE_REVISION_CANNOT_BE_SILENTLY_BYPASSED")
    _need(holistic["limitations"]["actual_media_seen"] is False and
          rescue["limitations"]["actual_generated_clip_seen"] is False,
          "INTEGRATED_NO_REAL_MEDIA_AT_PLANNING_STAGE")
    return {
        "kind": "source_locked_integrated_director_preproduction_receipt",
        "version": VERSION,
        "source_digest": state["source_digest"],
        "director_lock_digest": h["snapshot"]["director_lock_digest"],
        "meeting_digest": h["snapshot"]["department_command_digest"],
        "audiovisual_digest": h["snapshot"]["audiovisual_language_digest"],
        "artistic_methods_digest": h["snapshot"]["artistic_methods_digest"],
        "holistic_critique_digest": h["critique_digest"],
        "action_rescue_digest": a["plan_digest"],
        "protected_choices_count": h["protected_artistic_choices"],
        "shot_count": a["shot_count"],
        "allowed_for_structural_specialist_planning_only": True,
        "artistic_success_certified": False,
        "actual_media_or_real_audience_verified": False,
        "paid_or_publish_authority": False,
    }


def departmental_context(base, state, meeting, audiovisual, holistic, rescue,
                         task_id, *, artistic_method_plan=None):
    """Inject same film's creative WHY into the *existing* model-facing role."""
    _need(task_id in DIRECTOR_ROLES,
          "INTEGRATED_NOT_A_DOWNSTREAM_DIRECTOR_ROLE")
    receipt = preproduction_receipt(
        base, state, meeting, audiovisual, holistic, rescue,
        artistic_method_plan=artistic_method_plan)
    shots = []
    for shot in rescue["shots"]:
        sid = shot["shot_id"]
        protect = [x for x in holistic["protected_choices"]
                   if sid in x["shot_ids"]]
        matters = [x for x in holistic["lens_judgments"]
                   if sid in x["shot_ids"]]
        issues = [x for x in holistic["problems"]
                  if sid in x["shot_ids"]]
        shots.append({
            "shot_id": sid,
            "director_emphasis": {
                "why_action_is_needed": shot["narrative_necessity"],
                "audience_must_perceive": shot["audience_must_perceive"],
                "loss_if_removed": shot["meaning_loss_if_omitted"],
            },
            "artistic_choices_to_protect": deepcopy(protect),
            "filmic_lens_judgments": deepcopy(matters),
            "known_unverified_media_questions": deepcopy(issues),
            "preferred_proposed_action_route": shot["preferred_strategy_id"],
        })
    return {
        "kind": "same_director_merged_creative_and_action_intent",
        "version": VERSION,
        "director_role": task_id,
        "professional_focus": FOCUS[task_id],
        "provenance": receipt,
        "film_thesis": holistic["whole_piece_thesis"],
        "viewer_journey": holistic["audience_journey_diagnosis"],
        "protected_creative_choices": deepcopy(holistic["protected_choices"]),
        "department_has_professional_execution_authority_only": True,
        "shots": shots,
        "not_evidence_of_finished_video_or_author_approval": True,
        "no_model_calls_made_or_authorized_by_this_context": True,
    }


def postproduction_assessment(base, state, meeting, audiovisual,
                              holistic_post, rescue_post, *,
                              artistic_method_plan=None):
    """Review real submitted crew *designs*, never pretend rendered video."""
    h, a = _bind(
        base, state, meeting, audiovisual, holistic_post, rescue_post,
        artistic_method_plan=artistic_method_plan, post=True)
    issues = whole.route_critique_proposals(
        base, state, meeting, audiovisual, holistic_post,
        artistic_method_plan=artistic_method_plan)
    return {
        "kind": "unsent_integrated_director_after_crew_design_report",
        "version": VERSION,
        "holistic_critique_digest": h["critique_digest"],
        "action_rescue_digest": a["plan_digest"],
        "source_digest": state["source_digest"],
        "actual_offline_risk_signal_count": a["actual_offline_risk_signals"],
        "holistic_revision_routes": deepcopy(
            issues["actions_by_existing_role"]),
        "action_shots_needing_redesign": [
            x["shot_id"] for x in rescue_post["shots"]
            if x["decision"] in (
                "blockers_need_redesign", "return_to_screenwriter")],
        "director_lock_or_screenplay_changes_must_invalidate_prior_plans": True,
        "all_reviews_are_of_text_design_not_real_footage": True,
        "authority_to_dispatch_or_render": False,
        "independent_human_film_review_done": False,
    }


def make_lineage_change_from_finding(
        base, state, meeting, audiovisual, holistic, *,
        finding_id, request_id, source_beat_ids=None,
        what_must_remain_unchanged, artistic_method_plan=None,
        screenplay_change_kind=None):
    """One reviewed finding -> exactly one *unsent* QO-D12 revision proposal.

    Caller must explicitly classify screenplay scope; model cannot auto-approve
    screenplay edits. NEVER call local_rework here: explicit director action is
    separately required for any state mutation.
    """
    _need(isinstance(finding_id, str), "INTEGRATED_FINDING_ID_MISSING")
    result = whole.validate(
        base, state, meeting, audiovisual, holistic,
        artistic_method_plan=artistic_method_plan)
    found = next(
        (x for x in holistic["problems"] if x["issue_id"] == finding_id),
        None)
    _need(found is not None, "INTEGRATED_FINDING_NOT_IN_CURRENT_REVIEW")
    response = found["response"]
    if response == "return_to_screenwriter":
        _need(screenplay_change_kind in SCRIPT_TYPES,
              "INTEGRATED_WRITER_CHANGE_TYPE_MUST_BE_EXPLICIT")
        kind = screenplay_change_kind
    elif response == "director_revise":
        _need(screenplay_change_kind is None,
              "INTEGRATED_DIRECTOR_CANNOT_APPROVE_STORY_EDIT")
        kind = "director_whole_film_vision"
    elif response == "department_refine":
        _need(screenplay_change_kind is None,
              "INTEGRATED_DEPARTMENT_CANNOT_APPROVE_STORY_EDIT")
        kind = {
            "acting": "actor_performance",
            "camera_art": "camera_or_art_design",
            "sound": "voice_or_sound_design",
            "editing_animation": "editing_or_animation",
            "ai_technical": "ai_technical_generation_plan",
        }.get(found["owner"])
        _need(kind is not None, "INTEGRATED_UNKNOWN_SPECIALIST_OWNERSHIP")
    else:
        _need(False, "INTEGRATED_MEDIA_ONLY_QUESTION_NOT_REVISION")
    proposals = found["alternatives"]
    tradeoff = (
        "A: " + proposals[0]["approach"] +
        " (cost: " + proposals[0]["artistic_cost"] +
        "); B: " + proposals[1]["approach"] +
        " (cost: " + proposals[1]["artistic_cost"] + ")")
    return {
        "kind": "unsent_director_finding_to_original_team_revision",
        "creative_review_digest": result["critique_digest"],
        "change_request": lineage.request(
            base, state,
            request_id=request_id,
            origin_role="director_final",
            kind=kind,
            shot_ids=list(found["shot_ids"]),
            scene_or_source_beat_ids=(
                list(source_beat_ids) if source_beat_ids is not None else []),
            observed_defect_or_creative_opportunity=found["diagnosis"],
            viewer_or_story_consequence=found["viewer_consequence"],
            proposed_change_in_own_words=found["exact_next_action"],
            what_must_remain_unchanged=what_must_remain_unchanged,
            alternative_and_artistic_cost=tradeoff),
        "director_or_author_approved": False,
        "existing_ledger_mutated": False,
        "external_dispatch_authorized": False,
    }
