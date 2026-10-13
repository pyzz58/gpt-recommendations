#!/usr/bin/env python3
"""QO-D03: director visual and sonic grammar before the specialist meeting.

This is not shot-camera glamour scoring. The director must identify the
observable audience change, why a particular audiovisual choice causes it,
and what is lost if the choice is replaced by generic coverage.

The plan binds to the pre-existing director lock and specialist conference.
All results are un-sent proposals; no video viewing or merit is claimed.
"""
from __future__ import annotations

from copy import deepcopy
import json

import agent_team
import director_department_command as command

VERSION = "director-audiovisual-language-v1"
MODES = frozenset({"hold", "cut", "move", "reframe", "sound-led"})
GENRES = frozenset({"fiction", "documentary", "essay", "hybrid"})


class VisualLanguageError(ValueError):
    pass


def _need(ok, error):
    if not ok:
        raise VisualLanguageError(error)


def _text(x, error, minimum=18):
    _need(isinstance(x, str) and minimum <= len(x.strip()) <= 2200
          and "\0" not in x, error)


def _object(x, fields, error):
    _need(isinstance(x, dict) and set(x) == set(fields), error)


def request(base, state, director_command, *, genre, source_text=None):
    """Deep director's audiovisual articulation, then distribute to departments."""
    _need(genre in GENRES, "VISION_GENRE")
    meeting = command.validate_command(base, state, director_command)
    if source_text is not None:
        import hashlib
        _need(hashlib.sha256(source_text.encode()).hexdigest() ==
              state["source_digest"], "VISION_SCRIPT_STALE")
    brief = state["tasks"]["director_brief"]["deliverable"]
    lock = state["tasks"]["director_lock"]["deliverable"]
    return {
        "kind": "unsent_director_visual_and_sound_language",
        "version": VERSION, "dispatch_allowed": False,
        "quality_certified": False,
        "messages": [
            {"role": "system", "content": (
                "你是总导演，负责用摄影空间关系、表演动作、视觉母题、"
                "沉默/声音、剪辑的先后关系将故事转化为可感的思想和情绪。"
                "先理解为什么这一秒必须给观众看/听特定信息，然后才选择"
                "镜头移动或静止、景别、构图、遮挡、光色、声音透视与切点。"
                "不能套用'大片电影感、压迫感推镜、每3秒一切'等通用装饰。"
                "以场景的因果、角色的选择与观众认识为依据，可刻意留白或"
                "保留长时间凝视，前提是写出期间观众具体感受的变化。"
                "对每镜写清画面里实际发生的事、为何安排此视觉重心、"
                "声音/沉默如何与事件交互、前镜提供的信息和下镜将改变什么。"
                "明确对比如果换成平庸B-roll/过早切镜/全程旁白，"
                "观众将失去哪些具体信息或情感（counterfactual）。"
                "小说以表演中的选择和代价驱动；纪录片不伪造素材因果；"
                "思想科学文案必须用可见关系体现概念，不能只给旁白配插图。"
                "竖屏9:16需考虑人物与关键动作安全区域、跨镜动作/手部/道具"
                "连续性与小屏可读性。每集总时长90秒以内、AI单clip时长"
                "由技术岗位核对，精确字幕/文字/数字在后期制作。"
                "给演员、摄影、美术、声音、剪辑、AI技术分别讲清目的和"
                "跨部门协作依赖，但不替代各岗位对技术实施方式的专业选择。"
                "你交出的是具体创作判断和可被实际作品验证的假设，"
                "不是已试拍、已通过真人审片或已授权的最终成片。")},
            {"role": "user", "content": json.dumps({
                "genre": genre,
                "original_script": source_text,
                "episode_base": base,
                "director_brief": brief,
                "director_locked_vision": lock,
                "department_conference": director_command,
                "director_command_digest": meeting["command_digest"],
                "director_lock_digest": meeting["director_lock_digest"],
                "required_overall_fields": [
                    "version", "source_digest", "base_digest",
                    "director_lock_digest", "director_command_digest",
                    "genre", "point_of_view", "emotional_question",
                    "visual_motif_evolution", "sound_silence_arc",
                    "rhythm_and_attention_strategy", "shots", "handoffs"],
                "required_shot_fields": [
                    "shot_id", "incoming_viewer_belief",
                    "observable_screen_event", "viewer_belief_after",
                    "visual_emphasis_and_reason",
                    "mise_en_scene_and_performance",
                    "framing_movement_or_stillness",
                    "sound_or_silence_contribution",
                    "cut_or_hold_causal_reason",
                    "counterfactual_if_generic_coverage",
                    "ai_fallback_without_story_loss"],
                "handoff_fields": [
                    "from_shot", "to_shot", "audience_question",
                    "information_or_emotion_change", "image_sound_link",
                    "why_this_boundary"],
                "allowed_cut_intentions": sorted(MODES),
            }, ensure_ascii=False, separators=(",", ":"))}
        ],
    }


def validate(base, state, director_command, plan):
    meeting = command.validate_command(base, state, director_command)
    _object(plan, {
        "version", "source_digest", "base_digest", "director_lock_digest",
        "director_command_digest", "genre", "point_of_view",
        "emotional_question", "visual_motif_evolution", "sound_silence_arc",
        "rhythm_and_attention_strategy", "shots", "handoffs",
    }, "VISION_SHAPE")
    _need(plan["version"] == VERSION and plan["genre"] in GENRES and
          plan["source_digest"] == state["source_digest"] and
          plan["base_digest"] == state["base_digest"] and
          plan["director_lock_digest"] == meeting["director_lock_digest"] and
          plan["director_command_digest"] == meeting["command_digest"],
          "VISION_STALE_DIRECTOR_OR_SOURCE")
    for k in ("point_of_view", "emotional_question",
              "visual_motif_evolution", "sound_silence_arc",
              "rhythm_and_attention_strategy"):
        _text(plan[k], "VISION_EMPTY_ARTISTIC_ARGUMENT")
    expected_ids = state["shot_ids"]
    shots = plan["shots"]
    _need(isinstance(shots, list) and len(shots) == len(expected_ids),
          "VISION_SHOT_COUNT")
    signatures = set()
    for sid, shot in zip(expected_ids, shots):
        _object(shot, {
            "shot_id", "incoming_viewer_belief",
            "observable_screen_event", "viewer_belief_after",
            "visual_emphasis_and_reason", "mise_en_scene_and_performance",
            "framing_movement_or_stillness", "sound_or_silence_contribution",
            "cut_or_hold_causal_reason", "counterfactual_if_generic_coverage",
            "ai_fallback_without_story_loss",
        }, "VISION_SHOT_SHAPE")
        _need(shot["shot_id"] == sid, "VISION_SHOT_ORDER_OR_MISSING")
        for key in shot:
            if key != "shot_id":
                _text(shot[key], "VISION_NOT_EXPLAINED")
        _need(shot["incoming_viewer_belief"] != shot["viewer_belief_after"],
              "VISION_NO_VIEWER_CHANGE")
        signature = (
            shot["observable_screen_event"].strip().casefold(),
            shot["visual_emphasis_and_reason"].strip().casefold(),
            shot["cut_or_hold_causal_reason"].strip().casefold())
        _need(signature not in signatures, "VISION_GENERIC_REPEATED_SHOTS")
        signatures.add(signature)
    edges = plan["handoffs"]
    _need(isinstance(edges, list) and
          len(edges) == max(0, len(expected_ids)-1), "VISION_BRIDGE_COUNT")
    for i, link in enumerate(edges):
        _object(link, {
            "from_shot", "to_shot", "audience_question",
            "information_or_emotion_change", "image_sound_link",
            "why_this_boundary",
        }, "VISION_BRIDGE_SHAPE")
        _need(link["from_shot"] == expected_ids[i] and
              link["to_shot"] == expected_ids[i+1], "VISION_BRIDGE_ORDER")
        for key in ("audience_question", "information_or_emotion_change",
                    "image_sound_link", "why_this_boundary"):
            _text(link[key], "VISION_BRIDGE_VAGUE")
    return {
        "kind": "director_audiovisual_language_receipt",
        "plan_digest": agent_team.fingerprint(plan),
        "source_digest": state["source_digest"],
        "director_lock_digest": meeting["director_lock_digest"],
        "director_command_digest": meeting["command_digest"],
        "shot_count": len(shots),
        "boundary_count": len(edges),
        "artistic_effect_verified": False,
        "media_seen": False,
        "model_calls_authorized": False,
    }


def departmental_context(base, state, director_command, plan, department):
    """Provide concrete director reasoning in the ACTUAL role-facing request."""
    proof = validate(base, state, director_command, plan)
    _need(department in command.DEPARTMENTS, "VISION_UNKNOWN_DEPARTMENT")
    shared = {
        "plan_digest": proof["plan_digest"],
        "director_point_of_view": plan["point_of_view"],
        "emotional_question": plan["emotional_question"],
        "visual_motif_evolution": plan["visual_motif_evolution"],
        "sound_silence_arc": plan["sound_silence_arc"],
        "rhythm_and_attention_strategy": plan["rhythm_and_attention_strategy"],
        "detailed_shots": deepcopy(plan["shots"]),
        "cross_shot_audiovisual_handoffs": deepcopy(plan["handoffs"]),
        "department": department,
        "must_answer_with_own_professional_solution": True,
        "creative_merit_not_certified": True,
    }
    return shared


# Creative decisions, not another obligatory AI role. A complete versioned
# comparison is authored by the SAME director and can be sent to existing
# specialists after human/model generation. No film merit is inferred.
CHOICE_VERSION = "director-audiovisual-choice-v1"
CHOICE_FIELDS = (
    "camera_and_space", "observable_performance", "sound_and_silence",
    "editing_and_hold", "viewer_effect", "creative_advantage",
    "emotional_or_factual_cost", "production_risk_and_fallback",
)


def choices_request(base, state, director_command, visual_plan):
    proof = validate(base, state, director_command, visual_plan)
    return {
        "kind": "unsent_director_audiovisual_alternative_comparison",
        "version": CHOICE_VERSION, "dispatch_allowed": False,
        "messages": [
            {"role": "system", "content": (
                "你是总导演。对于每个已经有完整导演视听意图的镜头，"
                "另提出两套真正不同的电影化实现方案：两者必须在"
                "摄影空间、声音/沉默或剪辑时机至少两处有明确差异。"
                "两者都服务同一剧本事实和人物选择，不能偷加新故事。"
                "对两版的观众感受、专业部门可执行动作、失去的情绪/思想、"
                "AI模型的失败替代做具体反论证。"
                "可偏爱长镜/静默，不自动选择节奏更快、剪辑更多或成本更低的一版。"
                "做出明确的导演取舍，并写出没有选择另一版的具体原因。"
                "正式岗位应收到选中版本而非两个互相矛盾的拍摄要求。"
                "不声称已生成、已观影、已获真人批准。")},
            {"role": "user", "content": json.dumps({
                "original_director_visual_plan": visual_plan,
                "director_visual_plan_digest": proof["plan_digest"],
                "source_digest": proof["source_digest"],
                "director_command_digest": proof["director_command_digest"],
                "shot_ids": list(state["shot_ids"]),
                "required_option_fields": CHOICE_FIELDS,
                "required_per_shot": ["shot_id", "alternatives",
                                      "selected_index",
                                      "choice_and_rejection_reason"],
                "alternatives_per_shot": 2,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate_choices(base, state, director_command, visual_plan, choices):
    original = validate(base, state, director_command, visual_plan)
    _object(choices, {
        "version", "visual_plan_digest", "source_digest",
        "director_command_digest", "shots",
    }, "VISION_CHOICES_SHAPE")
    _need(choices["version"] == CHOICE_VERSION and
          choices["visual_plan_digest"] == original["plan_digest"] and
          choices["source_digest"] == original["source_digest"] and
          choices["director_command_digest"] == original["director_command_digest"],
          "VISION_CHOICES_STALE")
    rows = choices["shots"]
    _need(isinstance(rows, list) and len(rows) == len(state["shot_ids"]),
          "VISION_CHOICES_MISSING_SHOTS")
    for sid, row in zip(state["shot_ids"], rows):
        _object(row, {"shot_id", "alternatives", "selected_index",
                      "choice_and_rejection_reason"}, "VISION_CHOICES_SHOT_SHAPE")
        _need(row["shot_id"] == sid, "VISION_CHOICES_SHOT_ORDER")
        _need(type(row["selected_index"]) is int and
              row["selected_index"] in (0, 1), "VISION_CHOICES_NO_DIRECTOR_CHOICE")
        _text(row["choice_and_rejection_reason"], "VISION_CHOICES_NO_TRADEOFF",
              minimum=40)
        options = row["alternatives"]
        _need(isinstance(options, list) and len(options) == 2,
              "VISION_CHOICES_NEED_TWO_TAKES")
        for option in options:
            _object(option, CHOICE_FIELDS, "VISION_CHOICES_TAKE_SHAPE")
            for value in option.values():
                _text(value, "VISION_CHOICES_UNDEREXPLAINED", minimum=24)
        a, b = options
        # A syntactic guard against same plan twice. Film-level distinction
        # still requires independent reading of both proposed performances.
        _need(sum(a[key] != b[key] for key in (
            "camera_and_space", "sound_and_silence", "editing_and_hold")) >= 2,
            "VISION_CHOICES_NOT_SUBSTANTIALLY_DIFFERENT")
    return {
        "kind": "director_audiovisual_alternatives_receipt",
        "choices_digest": agent_team.fingerprint(choices),
        "visual_plan_digest": original["plan_digest"],
        "shot_count": len(rows),
        "selected_but_not_approved": True,
        "independent_creative_quality_unverified": True,
        "media_generated": False,
    }


def selected_choices_context(base, state, director_command, visual_plan,
                             choices, department):
    proof = validate_choices(base, state, director_command,
                             visual_plan, choices)
    _need(department in command.DEPARTMENTS, "VISION_CHOICES_UNKNOWN_DEPARTMENT")
    return {
        "kind": "director_selected_audiovisual_approach_for_department",
        "choices_digest": proof["choices_digest"],
        "department": department,
        "per_shot": [{
            "shot_id": row["shot_id"],
            "selected_execution": deepcopy(
                row["alternatives"][row["selected_index"]]),
            "director_selection_and_rejected_tradeoff":
                row["choice_and_rejection_reason"],
            "rejected_option_for_comparison_only": deepcopy(
                row["alternatives"][1-row["selected_index"]]),
        } for row in choices["shots"]],
        "only_selected_is_execution_direction": True,
        "not_model_generated_media": True,
    }
