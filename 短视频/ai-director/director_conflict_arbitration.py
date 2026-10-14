#!/usr/bin/env python3
"""QO-D16: one master director arbitrates ACTUAL interdepartment conflicts.

QO-D16 already detects conflicting designs, but its simple textual
'director_resolution' cannot authorize a solution or distinguish a director
mistake, specialist correction, screenplay rewrite and media-only uncertainty.
This supplement requires both actual deliverables, a source-locked whole-film
artistic critique and two contrasted cinematic routes before proposing a
scoped, unsent QO-D12 change. It never certifies the result as a good film.
"""
from __future__ import annotations

from copy import deepcopy
import json

import agent_team as team
import director_department_command as meeting_contract
import director_delivery_review as delivery
import director_whole_film_critique as whole
import director_revision_lineage as lineage

VERSION = "director-interdepartment-artistic-arbitration-v1"
DECISIONS = frozenset({
    "revise_specialist", "revise_director_lock",
    "return_to_screenwriter", "await_real_media",
})
SPECIALISTS = frozenset({
    "acting", "camera_art", "sound", "editing_animation", "ai_technical",
})
PARTICIPANTS = SPECIALISTS | {"quality_review"}
OWNERS = SPECIALISTS | {"director_lock", "screenwriter", "none"}
FIELDS = (
    "conflict_index", "conflict_digest", "shot_id",
    "left_department", "right_department",
    "audience_understanding_at_stake", "how_left_plan_works",
    "how_right_plan_works", "why_plans_cannot_both_work",
    "protected_artistic_choice_digests", "director_authored_priority",
    "candidate_A", "candidate_B", "preferred_candidate",
    "reason_and_artistic_price", "decision", "responsible_owner",
    "participating_departments", "specific_rework_instruction",
    "screenplay_change_kind", "observable_media_acceptance",
    "known_uncertainty", "requires_human_decision", "human_decision_authenticated",
)
ALTERNATIVE_FIELDS = (
    "image_performance_sound_edit_execution", "viewer_gain",
    "visual_or_ethical_artistic_cost", "what_remains_unresolved",
)
LIMITATIONS = {
    "film_watched": False,
    "audience_response_measured": False,
    "human_director_authenticated": False,
    "author_screenplay_change_approved": False,
    "automatic_revision_authorized": False,
    "render_or_publish_authorized": False,
}


class ArtisticArbitrationError(ValueError):
    """Error codes exclude private screenplay, actors and their submitted work."""


def _need(value, code):
    if not value:
        raise ArtisticArbitrationError(code)


def _shape(value, fields, code):
    _need(isinstance(value, dict) and set(value) == set(fields), code)


def _text(value, code, minimum=22):
    _need(isinstance(value, str) and
          minimum <= len(value.strip()) <= 2200 and "\0" not in value, code)


def _quoted_value(source, excerpt):
    """Require actual authored string content, not JSON schema/key text."""
    if isinstance(source, str):
        return excerpt in source
    if isinstance(source, list):
        return any(_quoted_value(item, excerpt) for item in source)
    if isinstance(source, dict):
        return any(_quoted_value(v, excerpt) for v in source.values())
    return False


def _submitted_shot(state, department, shot_id):
    _need(department in delivery.TARGETS,
          "ARBITRATION_UNKNOWN_OR_UNDELIVERED_ROLE")
    task = state["tasks"][department]
    _need(task["status"] == "completed",
          "ARBITRATION_CANNOT_INVENT_DEPARTMENT_DELIVERY")
    work = task["deliverable"]
    _need(isinstance(work, dict), "ARBITRATION_DELIVERY_SHAPE")
    if team.SPECS[department]["kind"] == "shots":
        _need(isinstance(work.get("shots"), dict) and
              isinstance(work["shots"].get(shot_id), dict),
              "ARBITRATION_SHOT_DELIVERY_MISSING")
        return work["shots"][shot_id]
    return work


def _snapshot(base, state, meeting, language, holistic_post,
              delivery_review, *, artistic_method_plan=None):
    h = whole.validate(
        base, state, meeting, language, holistic_post,
        artistic_method_plan=artistic_method_plan)
    _need(h["phase"] == "post_department_design",
          "ARBITRATION_NEEDS_AFTER_CREW_ARTISTIC_REVIEW")
    d = delivery.validate(
        base, state, meeting, language, delivery_review,
        artistic_method_plan=artistic_method_plan)
    _need(d["unresolved_cross_department_conflicts"],
          "ARBITRATION_NO_ACTUAL_CONFLICT_TO_ARBITRATE")
    return {
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_lock_digest": h["snapshot"]["director_lock_digest"],
        "department_meeting_digest": h["snapshot"]["department_command_digest"],
        "visual_language_digest": h["snapshot"]["audiovisual_language_digest"],
        "holistic_critique_digest": h["critique_digest"],
        "department_delivery_review_digest": d["review_digest"],
        "department_snapshot_digest": d["snapshot_digest"],
        "conflict_digests": [
            team.fingerprint(row) for row in delivery_review["conflicts"]
        ],
        "shot_ids": list(state["shot_ids"]),
    }


def request(base, state, meeting, language, holistic_post,
            delivery_review, *, artistic_method_plan=None):
    """Unsent original director prompt with two-sided REAL work evidence."""
    snap = _snapshot(
        base, state, meeting, language, holistic_post, delivery_review,
        artistic_method_plan=artistic_method_plan)
    return {
        "kind": "unsent_one_director_interdepartment_artistic_arbitration",
        "version": VERSION,
        "dispatch_allowed": False,
        "media_seen": False,
        "messages": [
            {"role": "system", "content": (
                "你仍然是同一位总导演，不是第三方裁判AI，也不是"
                "仅核对字段的质量管理员。演员、摄影、声音、剪辑等"
                "专业岗位各自的方案可能局部合格，但组装后互相损害。"
                "逐一阅读两个部门实际提交的原句；不可虚构没交的工作。"
                "首先说明冲突损害了观众看到或听到的具体因果、"
                "人物选择、情绪以及作品思想。公平陈述双方为什么"
                "各有合理性，不用主观形容词单方面否定技术岗位。"
                "同时对照整片艺术审查中被保护的独特镜头，避免"
                "为了工业化易拍而删除人物停顿、荒诞因果或纪录证据。"
                "每个冲突至少提出两种实质不同的摄影/表演/声音/"
                "剪辑处理，写出每种方案的观众收益、电影语言成本。"
                "必须明确判断根因在导演方向、专业执行、编剧"
                "事实/台词还是缺乏真实媒体；归属不同则走不同"
                "版号返工。不能拿导演自己的剧本意见强迫剪辑师"
                "偷偷改成另一个人物的行为。"
                "涉及事实、原台词、人物抉择必须返编剧及作者"
                "审核；涉及总导演的错误必须由导演修改锁稿；"
                "声画和物理效果尚未看到真实影片时只能标待检。"
                "无真人导演签核、无真实视频、无付费调用或发布权。")},
            {"role": "user", "content": json.dumps({
                "snapshot_copy_exactly": snap,
                "director_artistic_intent": holistic_post,
                "genuine_two_department_conflicts": deepcopy(
                    delivery_review["conflicts"]),
                "source_locked_audiovisual_plan": language,
                "required_fields": {
                    "top": ["version", "snapshot", "whole_film_principle",
                            "decisions", "limitations"],
                    "each_conflict_decision": list(FIELDS),
                    "each_alternative": list(ALTERNATIVE_FIELDS),
                },
                "outcomes": sorted(DECISIONS),
                "responsible_owners": sorted(OWNERS),
                "immutable_limitations": LIMITATIONS,
                "no_creative_conclusion_can_claim_finished_film": True,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate(base, state, meeting, language, holistic_post, delivery_review,
             arbitration_plan, *, artistic_method_plan=None):
    """Ensure provenance, exact conflict coverage, actual work and scope."""
    _shape(arbitration_plan, (
        "version", "snapshot", "whole_film_principle", "decisions",
        "limitations"), "ARBITRATION_PLAN_SHAPE")
    snap = _snapshot(
        base, state, meeting, language, holistic_post, delivery_review,
        artistic_method_plan=artistic_method_plan)
    _need(arbitration_plan["version"] == VERSION and
          arbitration_plan["snapshot"] == snap,
          "ARBITRATION_OLD_DIRECTOR_OR_CREW_VERSION")
    _need(arbitration_plan["limitations"] == LIMITATIONS,
          "ARBITRATION_FAKE_AUTHOR_MEDIA_OR_RELEASE")
    _text(arbitration_plan["whole_film_principle"],
          "ARBITRATION_EMPTY_WHOLE_FILM_VIEW", minimum=45)
    conflicts = delivery_review["conflicts"]
    rows = arbitration_plan["decisions"]
    _need(isinstance(rows, list) and len(rows) == len(conflicts),
          "ARBITRATION_MISSING_ACTUAL_CONFLICT")
    protected = {
        team.fingerprint(choice): choice
        for choice in holistic_post["protected_choices"]
    }
    for index, (source, row) in enumerate(zip(conflicts, rows)):
        _shape(row, FIELDS, "ARBITRATION_DECISION_SHAPE")
        _need(type(row["conflict_index"]) is int and
              row["conflict_index"] == index and
              row["conflict_digest"] == snap["conflict_digests"][index] and
              row["shot_id"] == source["shot_id"] and
              row["left_department"] == source["left_department"] and
              row["right_department"] == source["right_department"],
              "ARBITRATION_CONFLICT_NOT_FROM_REAL_CREW")
        for side in ("left", "right"):
            role = row[side + "_department"]
            work = _submitted_shot(state, role, row["shot_id"])
            _need(_quoted_value(work, source[side + "_delivery_quote"]),
                  "ARBITRATION_QUOTE_MUST_BE_ACTUAL_AUTHOR_TEXT_VALUE")
        choices = {
            digest for digest, choice in protected.items()
            if row["shot_id"] in choice["shot_ids"]
        }
        selected = row["protected_artistic_choice_digests"]
        _need(isinstance(selected, list) and
              len(selected) == len(set(selected)) and
              all(isinstance(x, str) and x in choices for x in selected)
              and set(selected) == choices,
              "ARBITRATION_LOST_PROTECTED_ARTISTIC_CHOICE")
        for field in (
                "audience_understanding_at_stake", "how_left_plan_works",
                "how_right_plan_works", "why_plans_cannot_both_work",
                "director_authored_priority", "reason_and_artistic_price",
                "specific_rework_instruction", "observable_media_acceptance",
                "known_uncertainty"):
            _text(row[field], "ARBITRATION_NO_FILMIC_REASON")
        candidates = []
        for key in ("candidate_A", "candidate_B"):
            candidate = row[key]
            _shape(candidate, ALTERNATIVE_FIELDS,
                   "ARBITRATION_ARTISTIC_ALTERNATIVE_SHAPE")
            for val in candidate.values():
                _text(val, "ARBITRATION_NO_ARTISTIC_GAIN_AND_COST")
            candidates.append(candidate["image_performance_sound_edit_execution"].strip().casefold())
        _need(candidates[0] != candidates[1],
              "ARBITRATION_SAME_TECHNIQUE_AS_FAKE_ALTERNATIVE")
        _need(row["decision"] in DECISIONS and
              row["responsible_owner"] in OWNERS and
              row["preferred_candidate"] in ("A", "B", "undecided_real_media"),
              "ARBITRATION_WRONG_AUTHORITY_OR_CHOICE")
        deps = row["participating_departments"]
        _need(isinstance(deps, list) and
              all(isinstance(x, str) and x in PARTICIPANTS for x in deps)
              and len(set(deps)) == len(deps)
              and set((source["left_department"], source["right_department"])) <= set(deps),
              "ARBITRATION_NOT_COORDINATING_BOTH_SPECIALISTS")
        _need(type(row["requires_human_decision"]) is bool and
              row["requires_human_decision"] is source["human_decision_needed"]
              and row["human_decision_authenticated"] is False,
              "ARBITRATION_FAKE_HUMAN_DECISION")
        action = row["decision"]
        owner = row["responsible_owner"]
        writer_kind = row["screenplay_change_kind"]
        if action == "return_to_screenwriter":
            _need(owner == "screenwriter" and writer_kind in lineage.SCRIPT_KINDS,
                  "ARBITRATION_WRITER_ONLY_CAN_CHANGE_SOURCE")
        elif action == "revise_director_lock":
            _need(owner == "director_lock" and writer_kind is None,
                  "ARBITRATION_DIRECTOR_REVISION_OWNERSHIP")
        elif action == "revise_specialist":
            _need(owner in SPECIALISTS and owner in deps and writer_kind is None,
                  "ARBITRATION_SPECIALIST_OWNER_INVALID")
        else:
            _need(owner == "none" and writer_kind is None and
                  row["preferred_candidate"] == "undecided_real_media",
                  "ARBITRATION_MEDIA_ONLY_NOT_REAL_REVISION")
        if action != "await_real_media":
            _need(row["preferred_candidate"] != "undecided_real_media",
                  "ARBITRATION_NO_CANDIDATE_SELECTED")
    return {
        "kind": "source_locked_one_director_arbitration_receipt",
        "arbitration_digest": team.fingerprint(arbitration_plan),
        "snapshot": deepcopy(snap),
        "conflicts_in_original_delivery_review": len(conflicts),
        "choices_protected_against_generic_overrides": sum(
            len(row["protected_artistic_choice_digests"]) for row in rows),
        "writer_revisions_proposed": sum(
            row["decision"] == "return_to_screenwriter" for row in rows),
        "director_design_revisions_proposed": sum(
            row["decision"] == "revise_director_lock" for row in rows),
        "specialist_revisions_proposed": sum(
            row["decision"] == "revise_specialist" for row in rows),
        "cannot_pass_until_original_crew_review_revalidated": True,
        "actual_video_or_human_art_certified": False,
        "any_models_called": False,
        "render_or_publish_authorized": False,
    }


def propose_lineage_change(base, state, meeting, language, holistic_post,
                           delivery_review, arbitration_plan, *,
                           conflict_index, request_id,
                           what_must_remain_unchanged,
                           artistic_method_plan=None):
    """One arbitrated conflict -> unexecuted QO-D12 proposal, never auto-fix."""
    receipt = validate(
        base, state, meeting, language, holistic_post,
        delivery_review, arbitration_plan,
        artistic_method_plan=artistic_method_plan)
    _need(type(conflict_index) is int and
          0 <= conflict_index < len(arbitration_plan["decisions"]),
          "ARBITRATION_UNKNOWN_CONFLICT_INDEX")
    row = arbitration_plan["decisions"][conflict_index]
    route = {
        "revise_specialist": {
            "acting": "actor_performance",
            "camera_art": "camera_or_art_design",
            "sound": "voice_or_sound_design",
            "editing_animation": "editing_or_animation",
            "ai_technical": "ai_technical_generation_plan",
        },
        "revise_director_lock": "director_whole_film_vision",
        "return_to_screenwriter": row["screenplay_change_kind"],
    }
    _need(row["decision"] in route,
          "ARBITRATION_MEDIA_ONLY_MUST_AWAIT_ACTUAL_SHOT")
    kind = (route["revise_specialist"][row["responsible_owner"]]
            if row["decision"] == "revise_specialist"
            else route[row["decision"]])
    _text(what_must_remain_unchanged, "ARBITRATION_PRESERVATION_NOT_DEFINED")
    choice = row["candidate_" + row["preferred_candidate"]]
    req = lineage.request(
        base, state, request_id=request_id,
        origin_role="director_final", kind=kind,
        shot_ids=[row["shot_id"]],
        scene_or_source_beat_ids=[],
        observed_defect_or_creative_opportunity=row["why_plans_cannot_both_work"],
        viewer_or_story_consequence=row["audience_understanding_at_stake"],
        proposed_change_in_own_words=row["specific_rework_instruction"],
        what_must_remain_unchanged=what_must_remain_unchanged,
        alternative_and_artistic_cost=(
            choice["image_performance_sound_edit_execution"] +
            " | Gain: " + choice["viewer_gain"] +
            " | Cost: " + choice["visual_or_ethical_artistic_cost"]))
    return {
        "kind": "unsent_same_director_arbitration_to_qod12_rework",
        "original_arbitration_digest": receipt["arbitration_digest"],
        "conflict_index": conflict_index,
        "source_review_still_has_unresolved_conflicts": True,
        "change_request": req,
        "cannot_overwrite_original_screenplay": True,
        "existing_task_ledger_unchanged": True,
        "no_external_model_or_media_call_authorized": True,
    }
