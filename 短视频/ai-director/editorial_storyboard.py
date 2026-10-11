#!/usr/bin/env python3
"""Creative showrunner + script-editor bridge for article-derived storyboard options.

OFFLINE ONLY: prepares a private enhanced script-editor contract, validates
pre-authored JSON against actual source, and proposes a more concrete,
filmable *candidate* plan. Does NOT generate AI prose on its own, call an
LLM, assert author approval, alter immutable narration, or make media.

The previously created crew's first two official roles are still used, with
the same team revision, scope and source-digest rules.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

import article_intake as intake
import agent_team as team
import agent_role_contracts as roles
import director

VERSION = "creative-storyboard-proposal-v1"
VISUAL_MODES = frozenset({"ai_video", "text_card", "data_graphic", "motion_graphic",
                          "medical_animation", "real_broll", "stock", "ai_image"})
MAX_BEATS = 20
MAX_NOTE = 800
NUMERIC = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?:%|％)?")
ACTION_FIELDS = ("start", "action", "micro_action", "reaction", "end")
SHOT_FIELDS = ("shot_id", "visual_type", "visual_intention", "observable_action",
               "camera_intention", "light_intention", "transition_intention",
               "post_overlay", "evidence_quote", "reason")


class CreativeContractError(ValueError):
    """Only stable error codes: never concatenate private source or model text."""


def _digest(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _string(item, field):
    value = item.get(field) if isinstance(item, dict) else None
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_NOTE:
        raise CreativeContractError("CREATIVE_MISSING_OR_INVALID_" + field.upper())
    return value


def _ensure_source(result, episode_source):
    if not isinstance(result, dict) or result.get("kind") != "episode_intake_result":
        raise CreativeContractError("CREATIVE_NOT_EPISODE_INTAKE")
    if result.get("status") != "editorial_review_required":
        raise CreativeContractError("CREATIVE_INTAKE_NEEDS_EDITOR")
    state = result.get("team")
    plan = result.get("plan")
    if not isinstance(plan, dict) or not isinstance(state, dict):
        raise CreativeContractError("CREATIVE_MISSING_PLAN_OR_TEAM")
    if not isinstance(episode_source, str) or _digest(episode_source) != state["source_digest"]:
        raise CreativeContractError("CREATIVE_SOURCE_DIGEST_MISMATCH")
    if team.fingerprint(plan) != state["base_digest"]:
        raise CreativeContractError("CREATIVE_BASE_DIGEST_MISMATCH")
    return plan, state


def build_director_brief_request(result, episode_source):
    """System/user model messages in *private memory*. No dispatch or writes."""
    plan, state = _ensure_source(result, episode_source)
    if team.ready(state) != ["director_brief"]:
        raise CreativeContractError("CREATIVE_BRIEF_NOT_READY")
    request = roles.build_role_messages(plan, state, "director_brief",
                                        source_text=episode_source)
    result = deepcopy(request)
    result["messages"][0]["content"] += (
        "\n【长文章改编专项】你面对的是尚未由导演改编的逐字片段。"
        "必须从观众困境、情绪转折、视觉钩子、结尾回报提出可拍摄而非口号式方案。"
        "所有事实和数字都来自 source_script；证据没有核实就标成风险。"
        "只是提出艺术决策；不能擅自改写 source_shot.narration。")
    return result


def build_script_editor_request(result, state, episode_source):
    """Extend existing specialist JSON Schema with real storyboard beat ideas.

    Added storyboard_pitch is inside the original story_treatment envelope,
    so it remains owned solely by script_edit. No model transport is included.
    """
    plan, bound = _ensure_source(result, episode_source)
    if state.get("base_digest") != bound["base_digest"] or (
            state.get("source_digest") != bound["source_digest"]):
        raise CreativeContractError("CREATIVE_SCRIPT_STATE_MISMATCH")
    if "script_edit" not in team.ready(state):
        raise CreativeContractError("CREATIVE_SCRIPT_NOT_READY")
    request = roles.build_role_messages(
        plan, state, "script_edit", source_text=episode_source)
    out = deepcopy(request)
    shot_schema = {
        "type": "object", "required": list(SHOT_FIELDS),
        "properties": {
            "shot_id": {"type": "string", "enum": list(state["shot_ids"])},
            "visual_type": {"type": "string", "enum": sorted(VISUAL_MODES)},
            **{name: {"type": "string", "minLength": 1}
               for name in SHOT_FIELDS if name not in (
                   "shot_id", "visual_type", "observable_action", "post_overlay")},
            "observable_action": {"type": "object",
                                  "required": list(ACTION_FIELDS),
                                  "properties": {
                                      k: {"type": "string", "minLength": 1}
                                      for k in ACTION_FIELDS},
                                  "additionalProperties": False},
            "post_overlay": {"type": "string"},
        }, "additionalProperties": False}
    pitch_schema = {
        "type": "object",
        "required": ["creative_angle", "hook_strategy", "audience_question",
                     "ending_payoff", "shot_designs", "open_risks"],
        "properties": {
            **{x: {"type": "string", "minLength": 1}
               for x in ("creative_angle", "hook_strategy",
                         "audience_question", "ending_payoff")},
            "shot_designs": {"type": "array", "items": shot_schema,
                             "minItems": len(state["shot_ids"]),
                             "maxItems": len(state["shot_ids"])},
            "open_risks": {"type": "array", "items": {"type": "string"}},
        }, "additionalProperties": False}
    tr = out["output_json_schema"]["properties"]["story_treatment"]
    tr["properties"]["storyboard_pitch"] = pitch_schema
    tr["required"].append("storyboard_pitch")
    # Original request embeds schema in user JSON as well; carefully replace
    # the whole embedded request via string-json boundary, NOT string surgery.
    marker = "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n"
    before, sep, data = out["messages"][1]["content"].partition(marker)
    if not sep:
        raise CreativeContractError("CREATIVE_SCRIPT_PROMPT_FORMAT_UNEXPECTED")
    try:
        context = json.loads(data)
    except (ValueError, TypeError):
        raise CreativeContractError("CREATIVE_SCRIPT_CONTEXT_INVALID") from None
    context["output_json_schema"] = out["output_json_schema"]
    out["messages"][1]["content"] = before + sep + json.dumps(
        context, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    out["messages"][0]["content"] += (
        "\n【创意导演分镜提案专项】除原 story_treatment 字段外，必须给 storyboard_pitch。"
        "按每一个原 shot_id 设计真正不同的视觉冲突、行为变化、景别/镜头方向和"
        "后期字幕策略，写清导演因果。ai_video 要可在单镜完成，"
        "data_graphic 必须由后期做准确数据，不把汉字数字交给生成模型。"
        "evidence_quote 必须逐字等于该 shot 的 source narration。"
        "严禁捏造源文数字/法规/医学结论；所有新配音/删稿仅放到"
        "source_change_proposals 并保持 requires_user_approval=true, approved=false。"
        "不能将任何艺术构想声明为已制作、已试拍或真人批准。")
    out["creative_extension"] = VERSION
    return out


def validate_editorial_pitch(result, state, episode_source):
    """Independently validate real creative *content* on top of role contract.

    The role contract already checks source/shot scope. This layer checks
    visual design coverage, provenance, numeric overlay hallucinations, and
    non-placeholder per-shot intent. NO professional aesthetic guarantee.
    """
    plan, intake_state = _ensure_source(result, episode_source)
    if state.get("base_digest") != intake_state["base_digest"] or (
            state.get("source_digest") != intake_state["source_digest"]):
        raise CreativeContractError("CREATIVE_STATE_SOURCE_MISMATCH")
    if (state["tasks"]["director_brief"]["status"] != "completed" or
            state["tasks"]["script_edit"]["status"] != "completed"):
        raise CreativeContractError("CREATIVE_FIRST_TWO_ROLES_INCOMPLETE")
    treatment = state["tasks"]["script_edit"]["deliverable"]["story_treatment"]
    brief = state["tasks"]["director_brief"]["deliverable"]["creative_brief"]
    pitch = treatment.get("storyboard_pitch")
    if not isinstance(pitch, dict) or set(pitch) != {
            "creative_angle", "hook_strategy", "audience_question",
            "ending_payoff", "shot_designs", "open_risks"}:
        raise CreativeContractError("CREATIVE_PITCH_CONTRACT_MISSING")
    for key in ("creative_angle", "hook_strategy", "audience_question",
                "ending_payoff"):
        _string(pitch, key)
    designs = pitch["shot_designs"]
    if not isinstance(designs, list) or not 1 <= len(designs) <= MAX_BEATS:
        raise CreativeContractError("CREATIVE_SHOT_DESIGNS_INVALID")
    if not isinstance(pitch["open_risks"], list) or any(
            not isinstance(r, str) or not r.strip() or len(r) > MAX_NOTE
            for r in pitch["open_risks"]):
        raise CreativeContractError("CREATIVE_RISKS_INVALID")
    original = {s["id"]: s for s in plan["shots"]}
    ids = [x.get("shot_id") if isinstance(x, dict) else None for x in designs]
    if ids != list(original):
        raise CreativeContractError("CREATIVE_SHOT_COVERAGE_OR_ORDER")
    visual_intents = []
    for beat in designs:
        if set(beat) != set(SHOT_FIELDS):
            raise CreativeContractError("CREATIVE_SHOT_FIELDS_INVALID")
        for key in ("visual_intention", "camera_intention", "light_intention",
                    "transition_intention", "evidence_quote", "reason"):
            _string(beat, key)
        if beat["visual_type"] not in VISUAL_MODES:
            raise CreativeContractError("CREATIVE_VISUAL_TYPE_INVALID")
        action = beat["observable_action"]
        if not isinstance(action, dict) or set(action) != set(ACTION_FIELDS):
            raise CreativeContractError("CREATIVE_ACTION_FIELDS_INVALID")
        for key in ACTION_FIELDS:
            _string(action, key)
        shot = original[beat["shot_id"]]
        if beat["evidence_quote"] != shot["narration"]:
            raise CreativeContractError("CREATIVE_SOURCE_QUOTE_DRIFT")
        overlay = beat["post_overlay"]
        if not isinstance(overlay, str) or len(overlay) > MAX_NOTE:
            raise CreativeContractError("CREATIVE_OVERLAY_INVALID")
        # Freeform visual explanation is unverified direction, but any
        # numbers explicitly promised to viewers as an overlay must be
        # traceable to this episode's authoritative source.
        if (any(n not in episode_source for n in NUMERIC.findall(overlay))):
            raise CreativeContractError("CREATIVE_UNSOURCED_OVERLAY_NUMBER")
        visual_intents.append(beat["visual_intention"].strip())
    if len(set(visual_intents)) != len(visual_intents):
        raise CreativeContractError("CREATIVE_DUPLICATED_VISUAL_INTENT")
    if not isinstance(brief.get("visual_strategy"), str):
        raise CreativeContractError("CREATIVE_BRIEF_INCOMPLETE")
    for p in treatment["source_change_proposals"]:
        if p.get("requires_user_approval") is not True or p.get("approved") is not False:
            raise CreativeContractError("CREATIVE_SOURCE_EDIT_NOT_UNAPPROVED")
    return deepcopy(pitch)


def submit_director_brief(result, episode_source, raw_json):
    """Validate a supplied showrunner JSON response; no provider invocation."""
    plan, state = _ensure_source(result, episode_source)
    if team.ready(state) != ["director_brief"]:
        raise CreativeContractError("CREATIVE_BRIEF_NOT_READY")
    return roles.submit_role_output(
        plan, state, "director_brief", raw_json,
        source_text=episode_source)


def submit_creative_script_edit(result, state, episode_source, raw_json):
    """Atomic creative acceptance: check extended film pitch BEFORE advancing.

    Generic crew roles need only their original fields. This stronger
    editorial stage does not allow a missing/invalid shot design to silently
    unblock director_lock; the input state is never mutated.
    """
    plan, bound = _ensure_source(result, episode_source)
    if (state.get("base_digest") != bound["base_digest"] or
            state.get("source_digest") != bound["source_digest"]):
        raise CreativeContractError("CREATIVE_SCRIPT_STATE_MISMATCH")
    proposed = roles.submit_role_output(
        plan, state, "script_edit", raw_json, source_text=episode_source)
    validate_editorial_pitch(result, proposed, episode_source)
    return proposed


def propose_directed_storyboard(result, state, episode_source):
    """Stage an alternate *not approved* shot plan from creative role output.

    Replaces generic picture placeholders with actual proposed actions and
    camera concepts, while keeping narration/duration/claims fixed. This
    DOES NOT amend the existing team ledger or mislabel the new plan as accepted.
    """
    plan, bound = _ensure_source(result, episode_source)
    pitch = validate_editorial_pitch(result, state, episode_source)
    brief = state["tasks"]["director_brief"]["deliverable"]["creative_brief"]
    treatment = state["tasks"]["script_edit"]["deliverable"]["story_treatment"]
    candidate = deepcopy(plan)
    candidate["audience"] = brief["audience"]
    candidate["editorial"]["hook"] = pitch["hook_strategy"]
    candidate["visual_bible"]["style"] = brief["visual_strategy"]
    edits = {b["shot_id"]: b for b in treatment["beat_map"]}
    for shot, proposed in zip(candidate["shots"], pitch["shot_designs"]):
        sid = shot["id"]
        shot["visual_type"] = proposed["visual_type"]
        shot["purpose"] = edits[sid]["dramatic_function"]
        shot["visual"] = proposed["visual_intention"]
        shot["action"] = deepcopy(proposed["observable_action"])
        shot["camera"]["movement"] = proposed["camera_intention"]
        shot["art"]["lighting"] = proposed["light_intention"]
        shot["graphics"]["text"] = proposed["post_overlay"]
        shot["graphics"]["type"] = (
            "post_overlay" if proposed["post_overlay"] else
            ("none" if proposed["visual_type"] == "ai_video" else
             proposed["visual_type"]))
        shot["continuity"] = proposed["transition_intention"]
        # In addition, avoid claiming images, actors or camera work already
        # exist. Downstream departments must produce full production work.
    errors, warnings = director.validate(candidate)
    if errors:
        raise CreativeContractError("CREATIVE_CANDIDATE_INVALID_LEGACY_PLAN")
    baseline = plan["shots"]
    for old, new in zip(baseline, candidate["shots"]):
        if (old["narration"] != new["narration"] or
                old["start"] != new["start"] or
                old["duration"] != new["duration"] or
                old["claim_ids"] != new["claim_ids"]):
            raise CreativeContractError("CREATIVE_SOURCE_INVARIANT_DRIFT")
    # The new candidate has a new digest. Never re-use the old team ledger
    # or trick specialist tasks into accepting an old base fingerprint.
    return {
        "kind": "creative_storyboard_candidate",
        "status": "author_review_required",
        "source_sha256": result["source_sha256"],
        "episode_source_sha256": result["episode_source_sha256"],
        "from_base_digest": bound["base_digest"],
        "candidate_base_digest": team.fingerprint(candidate),
        "candidate_plan": candidate,
        "editorial_concept": deepcopy(pitch),
        "unapproved_source_edit_proposals": deepcopy(
            treatment["source_change_proposals"]),
        "warnings": list(dict.fromkeys(warnings + [
            "NOT_VALIDATED_AS_FINISHED_VIDEO",
            "NO_AUTHORIZATION_TO_APPLY_SOURCE_EDITS",
            "MISSING_PROFESSIONAL_CAMERA_ACTING_AUDIO_EDITING_HANDOFFS",
        ])),
        "author_approved": False, "paid_model_authorized": False,
        "ai_media_generated": False, "actual_provider_calls": 0,
        "actual_billed_cny": "0",
    }


def stage_new_team(candidate, episode_source):
    """Explicitly stage ONLY a new *pending* ledger for an altered candidate.

    A user-facing application must separately collect editorial approval
    before shipping the candidate into the actual production workflow.
    """
    if not isinstance(candidate, dict) or (
            candidate.get("kind") != "creative_storyboard_candidate") or (
            candidate.get("status") != "author_review_required") or (
            candidate.get("author_approved") is not False):
        raise CreativeContractError("CREATIVE_INVALID_CANDIDATE")
    plan = candidate.get("candidate_plan")
    if not isinstance(plan, dict) or (
            candidate.get("candidate_base_digest") != team.fingerprint(plan)):
        raise CreativeContractError("CREATIVE_CANDIDATE_TAMPERED")
    if not isinstance(episode_source, str) or (
            _digest(episode_source) != candidate.get("episode_source_sha256")):
        raise CreativeContractError("CREATIVE_STAGED_SOURCE_MISMATCH")
    errors, _ = director.validate(plan)
    if errors:
        raise CreativeContractError("CREATIVE_CANDIDATE_PLAN_INVALID")
    state = team.start(deepcopy(plan), source_text=episode_source)
    return {"stage_status": "pending_author_editorial_review",
            "plan": deepcopy(plan), "team": state,
            "ready_tasks": team.ready(state),
            "human_approved": False, "paid_api_authorized": False,
            "media_generated": False}
