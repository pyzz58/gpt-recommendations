#!/usr/bin/env python3
"""QO-D06: one director's action feasibility with meaning-preserving alternatives.

Uses pre-existing source-locked director vision, department conference and
director_shootability.review() on ACTUALLY SUBMITTED crew designs. The director
must choose two implementable candidate strategies per shot, including action
continuity and audience cost. This does NOT prove any video model can execute.
No new Agent, private disk, paid call, footage, screenplay edit or auto-release.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

import agent_team as team
import director_department_command as command
import director_visual_language as visual
import director_shootability as risk

VERSION = "director-action-rescue-v1"
PHASES = frozenset(("before_specialist_design", "after_specialist_design"))
ROUTES = frozenset(risk.SEGMENT_ROUTES)
MODES = frozenset(risk.MODES)
STATES = frozenset(("design_not_verified", "blockers_need_redesign",
                   "await_real_media_review", "return_to_screenwriter"))
OWNERS = frozenset(("acting", "camera_art", "sound", "editing_animation",
                   "ai_technical", "director_final"))
CORE = ("narrative_necessity", "audience_must_perceive",
        "physical_start_state", "physical_end_state", "meaning_loss_if_omitted",
        "directors_performance_notes", "directors_camera_notes",
        "directors_editing_and_sound_notes")
CONTINUITY = (
    "cast_ids", "prop_ids", "start_screen_direction", "end_screen_direction",
    "camera_axis_and_eyeline", "lighting_and_geometry",
    "hands_and_prop_ownership_before", "hands_and_prop_ownership_after",
)
STEP = (
    "step_id", "from_s", "to_s", "execution_route",
    "visible_event_and_required_action", "blocking_hands_and_props",
    "camera_spatial_rule", "match_cut_or_sound_join",
    "specialist_dependency", "covered_action_unit_ids",
)
STRATEGY = (
    "strategy_id", "mode", "steps", "reason_to_try_this_route",
    "what_the_audience_still_understands", "artistic_loss_or_change",
    "known_model_uncertainty", "practical_test_and_repair",
    "estimated_max_generation_attempts",
)
SHOT = (
    "shot_id", "risk_codes_from_real_preflight", "risk_interpretation",
    "source_cast_ids", "continuity", *CORE,
    "strategies", "preferred_strategy_id", "selection_tradeoff",
    "escalate_to", "decision", "unresolved_reality_check",
)


class ActionRescueError(ValueError):
    """Fixed codes without user source text or local file paths."""


def _need(ok, code):
    if not ok:
        raise ActionRescueError(code)


def _shape(obj, fields, code):
    _need(isinstance(obj, dict) and set(obj) == set(fields), code)


def _text(obj, code, minimum=20, maximum=2500):
    _need(isinstance(obj, str) and minimum <= len(obj.strip()) <= maximum
          and "\0" not in obj, code)


def _seconds(v, duration):
    return type(v) in (int, float) and math.isfinite(v) and 0 <= v <= duration


def _real_preflight(base, state):
    """Only recompute risks from completed ACTING + AI TECHNICAL handoffs."""
    a = state["tasks"]["acting"]
    t = state["tasks"]["ai_technical"]
    _need(a["status"] == t["status"] == "completed",
          "RESCUE_CREW_DELIVERABLES_NOT_SUBMITTED")
    _need(isinstance(a["deliverable"], dict) and
          isinstance(t["deliverable"], dict) and
          isinstance(a["deliverable"].get("shots"), dict) and
          isinstance(t["deliverable"].get("shots"), dict),
          "RESCUE_CREW_SHAPE_INVALID")
    ids = state["shot_ids"]
    _need(set(a["deliverable"]["shots"]) == set(ids) and
          set(t["deliverable"]["shots"]) == set(ids),
          "RESCUE_REAL_SHOT_COVERAGE_MISSING")
    designs = []
    for sid in ids:
        acting = a["deliverable"]["shots"][sid]
        tech = t["deliverable"]["shots"][sid]
        _need(isinstance(acting, dict) and isinstance(tech, dict) and
              isinstance(tech.get("generation"), dict) and
              isinstance(acting.get("beats"), list),
              "RESCUE_ACTING_TECH_MISSING_INPUTS")
        designs.append({
            "shot_id": sid, "beats": deepcopy(acting["beats"]),
            "shootability": deepcopy(acting.get("shootability")),
            "generation": deepcopy(tech["generation"]),
        })
    report = risk.review(base, {"shots": designs},
                         lambda shot, generation: generation.get("route"))
    _need([s["shot_id"] for s in report["shots"]] == ids and
          report["status"] == "offline_shootability_review",
          "RESCUE_RISK_REVIEW_NOT_AUTHORITATIVE")
    return report


def _snapshot(base, state, meeting, av_plan, *,
              artistic_method_plan=None, phase):
    _need(phase in PHASES, "RESCUE_UNKNOWN_PHASE")
    m = command.validate_command(base, state, meeting)
    v = visual.validate(base, state, meeting, av_plan,
                        artistic_method_plan=artistic_method_plan)
    crew_state = {}
    for name in ("acting", "ai_technical"):
        t = state["tasks"][name]
        crew_state[name] = {
            "status": t["status"],
            "revision": t["revision"],
            "submitted_design_digest": (
                team.fingerprint(t["deliverable"])
                if t["status"] == "completed" else None),
        }
    report = (_real_preflight(base, state)
              if phase == "after_specialist_design" else None)
    return ({
        "phase": phase,
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_lock_digest": m["director_lock_digest"],
        "meeting_digest": m["command_digest"],
        "visual_digest": v["plan_digest"],
        "artistic_methods_digest": v["artistic_methods_digest"],
        "shot_ids": list(state["shot_ids"]),
        "crew_design_versions": crew_state,
        "actual_risk_review_digest": (team.fingerprint(report)
                                      if report is not None else None),
    }, report)


def request(base, state, meeting, av_plan, *,
            phase="before_specialist_design", artistic_method_plan=None):
    """Unsent director request, with actual risk report only if crew submitted."""
    snap, report = _snapshot(
        base, state, meeting, av_plan, phase=phase,
        artistic_method_plan=artistic_method_plan)
    return {
        "kind": "unsent_director_meaning_preserving_action_rescue",
        "version": VERSION,
        "dispatch_allowed": False,
        "real_media_reviewed": False,
        "model_capability_certified": False,
        "messages": [
            {"role": "system", "content": (
                "你是同一个总导演。要真正理解为何演员必须完成这一动作，"
                "它使人物选择或作品思想发生了什么具体变化。"
                "对模型做不到的动作不能机械删去，不能用空镜掩盖剧情断层，"
                "也不能假设大模型提示词越长就能生成人体、双手、接触或道具交接。"
                "首先写出观众必须亲眼看到的行动结果、人物和道具初末状态、"
                "左/右手握持、视线/空间轴线、光源与声音衔接的不可变条件。"
                "每镜必须提出两个不同且时长闭合的实际制作方案："
                "单镜拍摄、拆分拼接、静帧或实拍插入、后期合成等依作品取舍。"
                "每个步骤交代演员怎样动、镜头在哪、剪口和音效怎样接、"
                "AI最可能失败的物理状态、实际尝试上限、失败如何修。"
                "方案B不是简单把A再说一遍，要明确为何其艺术效果不同，"
                "包括具体损失与为保剧情不得牺牲的部分。"
                "绝不捏造模型试拍、实际演员演出、图片参考、成功率或人工批准。"
                "动作改变了编剧事实、人物决定、事件结果或台词，"
                "必须交回编剧核对，不可以导演层私自删除。"
                "如果已有实际演员与AI技术岗位设计，认真按下游已提交产物"
                "重新计算的动作风控报告逐项处理所有风险代码；"
                "尚未有岗位交付只能给预制作风险假设，不得伪造已经实测。"
                "要求摄影、美术、表演、声音、剪辑与AI技术解释"
                "替代方案将如何被拍摄和接成观众能理解的完整行为，"
                "而不是将多个场景瞬间塞进同一生成片段。"
                "该文件是未下发的导演建议，不调用模型或工具、不付费、不发布。")},
            {"role": "user", "content": json.dumps({
                "provenance_copy_exact": snap,
                "authoritative_episode_base": base,
                "director_audiovisual_language": av_plan,
                "director_department_meeting": meeting,
                "director_artistic_methods": artistic_method_plan,
                "actual_recomputed_shootability_report": report,
                "required_output_fields": [
                    "version", "snapshot", "whole_piece_action_philosophy",
                    "shots", "limitations"],
                "shot_fields": list(SHOT),
                "continuity_fields": list(CONTINUITY),
                "strategy_fields": list(STRATEGY),
                "step_fields": list(STEP),
                "strategy_modes": sorted(MODES),
                "step_routes": sorted(ROUTES),
                "allowable_decisions": sorted(STATES),
                "specialist_owners": sorted(OWNERS),
                "each_strategy_must_cover_full_original_shot_duration": True,
                "real_model_generation_attempts": 0,
                "render_or_publish_authorized": False,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate(base, state, meeting, av_plan, rescue_plan, *,
             artistic_method_plan=None):
    """Check source/crew freshness + executable candidate timing, not beauty."""
    _shape(rescue_plan, ("version", "snapshot",
                         "whole_piece_action_philosophy",
                         "shots", "limitations"), "RESCUE_PLAN_SHAPE")
    phase = rescue_plan.get("snapshot", {}).get("phase") if isinstance(
        rescue_plan.get("snapshot"), dict) else None
    snap, report = _snapshot(base, state, meeting, av_plan,
                             phase=phase,
                             artistic_method_plan=artistic_method_plan)
    _need(rescue_plan["version"] == VERSION and
          rescue_plan["snapshot"] == snap,
          "RESCUE_STALE_DIRECTOR_OR_CREW")
    _need(rescue_plan["limitations"] == {
        "actual_generated_clip_seen": False,
        "model_success_rate_known": False,
        "human_shootability_approved": False,
        "screenplay_or_facts_changed": False,
        "paid_api_authorized": False,
        "render_or_publish_authorized": False,
    }, "RESCUE_FAKE_MEDIA_OR_APPROVAL")
    _text(rescue_plan["whole_piece_action_philosophy"],
          "RESCUE_NO_DIRECTOR_WHOLE_FILM_JUDGMENT", minimum=42)
    shot_rows = rescue_plan["shots"]
    _need(isinstance(shot_rows, list) and
          len(shot_rows) == len(state["shot_ids"]),
          "RESCUE_MISSING_OR_EXTRA_SHOTS")
    source = {s["id"]: s for s in base["shots"]}
    known_props = set((base.get("continuity_contract") or {}).get("props", {}))
    by_risk = ({
        f["shot_id"]: sorted({r["code"] for r in report["findings"]
                              if r["shot_id"] == f["shot_id"]})
        for f in report["findings"]} if report else {})
    by_report = {r["shot_id"]: r for r in report["shots"]} if report else {}
    for expected, row in zip(state["shot_ids"], shot_rows):
        _shape(row, SHOT, "RESCUE_SHOT_SHAPE")
        _need(row["shot_id"] == expected,
              "RESCUE_UNGROUNDED_OR_REORDERED_SHOT")
        shot = source[expected]
        duration = shot["duration"]
        _need(type(duration) in (int, float) and math.isfinite(duration)
              and duration > 0, "RESCUE_INVALID_SHOT_DURATION")
        official_cast = shot.get("character_ids", [])
        _need(isinstance(official_cast, list) and
              row["source_cast_ids"] == official_cast,
              "RESCUE_CAST_OR_CHARACTER_DRIFT")
        continuity = row["continuity"]
        _shape(continuity, CONTINUITY, "RESCUE_CONTINUITY_SHAPE")
        _need(continuity["cast_ids"] == official_cast and
              isinstance(continuity["prop_ids"], list) and
              len(continuity["prop_ids"]) == len(set(continuity["prop_ids"])) and
              set(continuity["prop_ids"]) <= known_props,
              "RESCUE_UNAPPROVED_CAST_OR_PROP")
        for k in CONTINUITY:
            if k not in ("cast_ids", "prop_ids"):
                _text(continuity[k], "RESCUE_CONTINUITY_UNEXPLAINED")
        for field in CORE:
            _text(row[field], "RESCUE_DIRECTOR_INTENT_UNEXPLAINED")
        report_codes = by_risk.get(expected, [])
        _need(row["risk_codes_from_real_preflight"] == report_codes,
              "RESCUE_RISK_REPORT_FORGED_OR_INCOMPLETE")
        _text(row["risk_interpretation"],
              "RESCUE_NO_RISK_CAUSAL_ANALYSIS")
        strategies = row["strategies"]
        _need(isinstance(strategies, list) and len(strategies) == 2,
              "RESCUE_TWO_DISTINCT_FILMABLE_STRATEGIES_REQUIRED")
        selected = set()
        all_units = {unit["id"] for unit in
                     by_report.get(expected, {}).get("units", [])}
        for plan in strategies:
            _shape(plan, STRATEGY, "RESCUE_STRATEGY_SHAPE")
            key = plan["strategy_id"]
            _need(isinstance(key, str) and
                  2 <= len(key) <= 40 and key not in selected,
                  "RESCUE_STRATEGY_ID_DUPLICATE")
            selected.add(key)
            _need(plan["mode"] in MODES and
                  type(plan["estimated_max_generation_attempts"]) is int and
                  0 <= plan["estimated_max_generation_attempts"] <= 6,
                  "RESCUE_UNREALISTIC_MODE_OR_COST")
            for field in STRATEGY:
                if field not in ("strategy_id", "mode", "steps",
                                 "estimated_max_generation_attempts"):
                    _text(plan[field], "RESCUE_STRATEGY_VAGUE")
            steps = plan["steps"]
            _need(isinstance(steps, list) and
                  1 <= len(steps) <= 12 and
                  (plan["mode"] != "split_stitch" or len(steps) >= 2),
                  "RESCUE_MISSING_PHYSICAL_SEGMENTS")
            cursor, covered = 0.0, set()
            for step in steps:
                _shape(step, STEP, "RESCUE_STEP_SHAPE")
                a, b = step["from_s"], step["to_s"]
                _need(_seconds(a, duration) and _seconds(b, duration) and
                      abs(a - cursor) <= 0.011 and b > a,
                      "RESCUE_ACTION_TIME_GAP_OR_OVERLAP")
                cursor = b
                _need(step["execution_route"] in ROUTES and
                      isinstance(step["step_id"], str) and
                      step["step_id"].strip(),
                      "RESCUE_UNKNOWN_MEDIA_ROUTE")
                for k in STEP:
                    if k not in ("step_id", "from_s", "to_s",
                                 "execution_route", "covered_action_unit_ids"):
                        _text(step[k], "RESCUE_NO_EXECUTABLE_CRAFT_INSTRUCTION")
                ids = step["covered_action_unit_ids"]
                _need(isinstance(ids, list) and
                      len(ids) == len(set(ids)) and
                      set(ids) <= all_units,
                      "RESCUE_NONEXISTENT_ACTOR_ACTION_UNIT")
                covered.update(ids)
            _need(abs(cursor - duration) <= 0.011,
                  "RESCUE_UNFINISHED_SHOT_OR_EXTRA_RUNTIME")
            _need(covered == all_units,
                  "RESCUE_ACTUAL_ACTION_UNIT_SILENTLY_OMITTED")
        _need(len({p["mode"] for p in strategies}) == 2,
              "RESCUE_IDENTICAL_ALTERNATIVES")
        _need(row["preferred_strategy_id"] in selected and
              row["escalate_to"] in OWNERS and
              row["decision"] in STATES,
              "RESCUE_SELECTION_OR_OWNER_INVALID")
        for k in ("selection_tradeoff", "unresolved_reality_check"):
            _text(row[k], "RESCUE_CANNOT_JUSTIFY_CHOSEN_ROUTE")
        if report and (by_report[expected]["status"] in
                       ("blocked", "incomplete")):
            _need(row["decision"] != "design_not_verified",
                  "RESCUE_BLOCKED_SHOT_CANNOT_SILENTLY_ADVANCE")
    return {
        "kind": "director_meaning_preserving_action_rescue_receipt",
        "plan_digest": team.fingerprint(rescue_plan),
        "snapshot": deepcopy(snap),
        "shot_count": len(shot_rows),
        "actual_offline_risk_signals": (
            len(report["findings"]) if report else None),
        "before_crew_or_post_crew": phase,
        "human_craft_review_passed": False,
        "actual_AI_video_success_verified": False,
        "models_invoked": 0,
        "render_or_publish_authorized": False,
    }


def departmental_context(base, state, meeting, av_plan, rescue_plan, task_id, *,
                         artistic_method_plan=None):
    """Attach director's actual fallback and meaning to existing model input."""
    receipt = validate(base, state, meeting, av_plan, rescue_plan,
                       artistic_method_plan=artistic_method_plan)
    _need(task_id in command.DEPARTMENTS, "RESCUE_UNKNOWN_DEPARTMENT")
    _need(receipt["before_crew_or_post_crew"] == "before_specialist_design"
          or task_id in ("quality_review", "director_final"),
          "RESCUE_POST_CREW_PLAN_NEEDS_NEW_DIRECTOR_REVISION")
    focus = {
        "acting": ("directors_performance_notes",
                   "blocking_hands_and_props", "visible_event_and_required_action"),
        "camera_art": ("directors_camera_notes",
                       "camera_spatial_rule", "match_cut_or_sound_join"),
        "sound": ("directors_editing_and_sound_notes",
                  "match_cut_or_sound_join", "specialist_dependency"),
        "editing_animation": ("directors_editing_and_sound_notes",
                              "match_cut_or_sound_join", "camera_spatial_rule"),
        "ai_technical": ("risk_interpretation",
                         "execution_route", "practical_test_and_repair"),
        "quality_review": ("unresolved_reality_check",
                           "covered_action_unit_ids", "continuity"),
        "director_final": ("selection_tradeoff",
                           "artistic_loss_or_change", "continuity"),
    }
    return {
        "kind": "source_locked_director_action_rescue_for_existing_specialist",
        "plan_digest": receipt["plan_digest"],
        "snapshot": deepcopy(receipt["snapshot"]),
        "department": task_id,
        "role_specific_focus_fields": list(focus[task_id]),
        "whole_film_preservation_thesis":
            rescue_plan["whole_piece_action_philosophy"],
        "shot_directions": deepcopy(rescue_plan["shots"]),
        "do_not_change_dialogue_or_original_event": True,
        "candidate_not_real_model_capability": True,
        "must_report_missing_crew_evidence": True,
        "no_payment_or_publication": True,
    }
