#!/usr/bin/env python3
"""QO-D05/D07: source-locked director of photography/continuity judgment.

The existing film_continuity.inspect_tracks is the mechanical SCRIPT-world
event checker; director_visual_language validates expressive shot/edge design.
This same director separately arbitrates the FILM meaning of adjacent framing,
eyeline, light, set geometry, blocking and motivated stylistic breaks, based on
ACTUALLY submitted acting, camera and editing work. Never infers visual
identity, actual film quality, audience response, physical camera coordinates,
or approved rights from textual assertions.
"""
from __future__ import annotations

from copy import deepcopy
import json

import agent_team as team
import film_continuity as film
import director_visual_language as vision
import director_department_command as commands
import director_revision_lineage as lineage

VERSION = "director-visual-continuity-v1"
ROLES = ("acting", "camera_art", "editing_animation")
LENSES = (
    "character_identity_costume_and_screen_presence",
    "hand_prop_transfer_and_state_causality",
    "scene_geometry_and_direction_of_travel",
    "eyeline_and_screen_axis",
    "motivated_framing_or_camera_movement",
    "light_source_and_time_of_day",
    "color_texture_and_visual_motif",
    "cut_reorientation_and_earned_discontinuity",
)
OUTCOMES = frozenset((
    "continuity_supported_by_text_design",
    "deliberate_discontinuity_requires_review",
    "revision_required",
    "unverifiable_without_real_media",
))
OWNERS = frozenset((
    "director_lock", "acting", "camera_art", "editing_animation",
    "none",
))
INTERVENTION = {
    "director_lock": "director_whole_film_vision",
    "acting": "actor_performance",
    "camera_art": "camera_or_art_design",
    "editing_animation": "editing_or_animation",
}
FIELDS = (
    "from_shot_id", "to_shot_id", "lens", "outcome",
    "source_design_quote", "source_design_shot_id",
    "actual_department_quotes", "audience_before", "audience_after",
    "essential_invariant", "camera_axis_and_eyeline",
    "world_lighting_and_geometry", "character_prop_state",
    "purpose_of_matching_or_breaking_continuity",
    "visual_motif_evolution", "why_generic_coverage_would_fail",
    "alternative_a", "alternative_b", "director_choice_and_cost",
    "owner", "exact_rework_if_needed", "how_to_check_actual_frames",
)
ALTERNATIVE = (
    "filmic_technique", "audience_benefit",
    "creative_tradeoff", "required_departments",
)
QUOTE_FIELDS = ("department", "shot_id", "exact_excerpt")
COVERAGE = (
    "from_shot_id", "to_shot_id", "lens",
)
LIMITATIONS = {
    "real_video_seen": False,
    "face_or_costume_identity_verified": False,
    "light_and_axis_verified_in_actual_frames": False,
    "human_director_review_authenticated": False,
    "media_production_authorized": False,
    "story_or_dialogue_mutated": False,
}


class VisualContinuityError(ValueError):
    """Fixed code only, no user-supplied passage in failure messages."""


def _need(value, code):
    if not value:
        raise VisualContinuityError(code)


def _shape(obj, fields, code):
    _need(type(obj) is dict and set(obj) == set(fields), code)


def _text(value, code, minimum=20):
    _need(isinstance(value, str) and
          minimum <= len(value.strip()) <= 2500 and "\0" not in value, code)


def _value_contains(value, quote):
    """Evidence from authored string VALUES, not schema keys or formatting."""
    if isinstance(value, str):
        return quote in value
    if isinstance(value, list):
        return any(_value_contains(v, quote) for v in value)
    if isinstance(value, dict):
        return any(_value_contains(v, quote) for v in value.values())
    return False


def _actual(state, dept, sid):
    _need(dept in ROLES, "VISUAL_UNKNOWN_SPECIALIST")
    task = state["tasks"][dept]
    _need(task["status"] == "completed" and
          isinstance(task["deliverable"], dict) and
          isinstance(task["deliverable"].get("shots"), dict) and
          isinstance(task["deliverable"]["shots"].get(sid), dict),
          "VISUAL_ACTUAL_SPECIALIST_SHOT_MISSING")
    return task["deliverable"]["shots"][sid]


def _report(base, state):
    """Reuse existing source-bound event checker only when complete tracks exist.

    Never transform generic acting prose into purported audited entity events.
    """
    tracks = {}
    for sid in state["shot_ids"]:
        shot = _actual(state, "acting", sid)
        c = shot.get("continuity")
        if (not isinstance(c, dict) or
                not isinstance(c.get("entity_tracks"), list) or
                "scene_id" not in c):
            return None
        tracks[sid] = {
            "scene_id": c["scene_id"],
            "entity_tracks": deepcopy(c["entity_tracks"]),
        }
    return film.inspect_tracks(
        base, tracks, source_digest=state["source_digest"])


def _snapshot(base, state, meeting, audiovisual,
              artistic_method_plan=None):
    _need(len(state["shot_ids"]) >= 2,
          "VISUAL_REQUIRES_ADJACENT_SHOTS")
    m = commands.validate_command(base, state, meeting)
    v = vision.validate(
        base, state, meeting, audiovisual,
        artistic_method_plan=artistic_method_plan)
    versions = {}
    for name in ROLES:
        task = state["tasks"][name]
        _need(task["status"] == "completed",
              "VISUAL_NEEDS_REAL_ACTING_CAMERA_EDIT_DELIVERIES")
        versions[name] = {
            "revision": task["revision"],
            "digest": team.fingerprint(task["deliverable"]),
        }
        for sid in state["shot_ids"]:
            _actual(state, name, sid)
    source_inventory = film.inventory(
        base, source_digest=state["source_digest"])
    report = _report(base, state)
    return ({
        "source_digest": state["source_digest"],
        "episode_base_digest": state["base_digest"],
        "director_lock_digest": m["director_lock_digest"],
        "conference_digest": m["command_digest"],
        "audiovisual_language_digest": v["plan_digest"],
        "artistic_methods_digest": v["artistic_methods_digest"],
        "shot_ids": list(state["shot_ids"]),
        "real_submitted_department_versions": versions,
        "source_entity_inventory_digest": team.fingerprint(source_inventory),
        "real_complete_entity_track_report_digest": (
            team.fingerprint(report) if report is not None else None),
        "real_complete_entity_track_coverage": report is not None,
    }, source_inventory, report)


def request(base, state, meeting, audiovisual, *,
            artistic_method_plan=None):
    """Build an UNSENT same-director edge-by-edge moviecraft review prompt."""
    snap, inv, report = _snapshot(
        base, state, meeting, audiovisual,
        artistic_method_plan=artistic_method_plan)
    delivery = {
        dept: deepcopy(state["tasks"][dept]["deliverable"]["shots"])
        for dept in ROLES
    }
    return {
        "kind": "unsent_same_director_cross_shot_visual_continuity_review",
        "version": VERSION,
        "dispatch_allowed": False,
        "media_viewed": False,
        "messages": [
            {"role": "system", "content": (
                "你是同一个总导演，并正在指导摄影指导、演员与剪辑师协调"
                "全片视觉世界。首先完整阅读当前权威导演视听语言和三专业"
                "真正提交的镜头设计，再逐一审查前后镜头。"
                "你不是只查空间轴线和同色滤镜：人物在镜头间的具体选择、"
                "目光方向、道具从哪只手换到哪只手、空间左右关系、"
                "一天内光源与时间关系、画面视觉母题的演变，"
                "都必须服务观众理解与心理体验。"
                "对每一对邻镜给出8种不同的具体电影专业观察，"
                "标明镜头引用与真实演员/摄影/剪辑交稿的原句。"
                "如果实际记录缺同框身份/材质/光线实测数据，"
                "明确说未知，不得把文字相同认作真人脸、服装和光源实测通过。"
                "只有确有视觉或故事用意，才允许跳轴、闪回、跳切、"
                "荒诞时空断裂、故意色彩变换；写清观众为什么"
                "会有意被迷惑、以及何时如何重新建立方向。"
                "禁止要求纪录片必须连贯到掩盖真实事实，"
                "也不为统一风格抹除人物真实情绪与特殊视听句法。"
                "每项至少给两种不同拍摄或剪辑取舍及艺术代价，"
                "明确是总导演原指令错、表演站位错、摄影与光线错、"
                "还是剪辑桥错。真正改变故事/事实/对白另交编剧，"
                "不能让本模块私自重写剧本。"
                "已有角色和道具都必须引用权威表，不能创造未声明身份，"
                "任何已存在的film_continuity风险不能被一段好听的"
                "导演自我说明自动消除。"
                "本阶段只检查文本专业设计，不审真实生成片，"
                "不调用API、不发布或付费。")},
            {"role": "user", "content": json.dumps({
                "snapshot_copy_exactly": snap,
                "existing_source_entity_inventory": inv,
                "existing_explicit_event_continuity_report": report,
                "directors_original_visual_language": audiovisual,
                "actually_submitted_professional_shots": delivery,
                "required_lenses_every_adjacent_pair": list(LENSES),
                "required_result_top_fields": [
                    "version", "snapshot", "whole_film_visual_world",
                    "edge_judgments", "limitations"],
                "required_edge_fields": list(FIELDS),
                "required_authored_quote_fields": list(QUOTE_FIELDS),
                "required_alternative_fields": list(ALTERNATIVE),
                "outcomes": sorted(OUTCOMES),
                "owners": sorted(OWNERS),
                "do_not_claim_real_visual_identity_or_approval": LIMITATIONS,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate(base, state, meeting, audiovisual, review, *,
             artistic_method_plan=None):
    """Reject false evidence, missing edge/lens, stale crew and false readiness."""
    _shape(review, (
        "version", "snapshot", "whole_film_visual_world",
        "edge_judgments", "limitations"), "VISUAL_REVIEW_SHAPE")
    snap, inv, report = _snapshot(
        base, state, meeting, audiovisual,
        artistic_method_plan=artistic_method_plan)
    _need(review["version"] == VERSION and
          review["snapshot"] == snap and
          review["limitations"] == LIMITATIONS,
          "VISUAL_STALE_OR_UNTRUTHFUL_REVIEW")
    _text(review["whole_film_visual_world"],
          "VISUAL_NO_COMPLETE_DIRECTOR_VIEW", minimum=45)
    edges = [(a, b) for a, b in zip(
        state["shot_ids"], state["shot_ids"][1:])]
    entries = review["edge_judgments"]
    _need(isinstance(entries, list) and
          len(entries) == len(edges) * len(LENSES),
          "VISUAL_INCOMPLETE_ALL_EDGES_AND_LENSES")
    changed = []
    pending = []
    deliberate = []
    for i, row in enumerate(entries):
        _shape(row, FIELDS, "VISUAL_EDGE_SHAPE")
        eid = edges[i // len(LENSES)]
        lens = LENSES[i % len(LENSES)]
        _need(row["from_shot_id"] == eid[0] and
              row["to_shot_id"] == eid[1] and row["lens"] == lens,
              "VISUAL_EDGE_ORDER_OR_LENS_CHANGED")
        _need(row["outcome"] in OUTCOMES,
              "VISUAL_EDGE_VERDICT_INVALID")
        quote = row["source_design_quote"]
        _need(isinstance(quote, str) and 8 <= len(quote) <= 240 and
              row["source_design_shot_id"] in eid,
              "VISUAL_MISSING_ACTUAL_DIRECTOR_SHOT_QUOTE")
        source = next(
            sh for sh in audiovisual["shots"]
            if sh["shot_id"] == row["source_design_shot_id"])
        _need(_value_contains(source, quote),
              "VISUAL_QUOTE_NOT_IN_DIRECTOR_VISION")
        items = row["actual_department_quotes"]
        _need(isinstance(items, list) and len(items) >= 2 and
              len(items) <= 6, "VISUAL_TWO_REAL_CREW_QUOTES_REQUIRED")
        seen = set()
        for item in items:
            _shape(item, QUOTE_FIELDS, "VISUAL_SPECIALIST_QUOTE_SHAPE")
            dept, sid, excerpt = (
                item["department"], item["shot_id"],
                item["exact_excerpt"])
            _need(isinstance(dept, str) and dept in ROLES and
                  sid in eid and
                  isinstance(excerpt, str) and 8 <= len(excerpt) <= 240,
                  "VISUAL_SPECIALIST_QUOTE_MISSING_ID")
            actual = _actual(state, dept, sid)
            _need(_value_contains(actual, excerpt),
                  "VISUAL_SPECIALIST_QUOTE_NOT_SUBMITTED")
            seen.add(dept)
        _need({"acting", "camera_art"} <= seen,
              "VISUAL_MUST_CHECK_ACTOR_AND_CAMERA_IN_SAME_FILM")
        for k in (
            "audience_before", "audience_after", "essential_invariant",
            "camera_axis_and_eyeline", "world_lighting_and_geometry",
            "character_prop_state", "purpose_of_matching_or_breaking_continuity",
            "visual_motif_evolution", "why_generic_coverage_would_fail",
            "director_choice_and_cost", "exact_rework_if_needed",
            "how_to_check_actual_frames",
        ):
            _text(row[k], "VISUAL_EMPTY_FILMING_REASON")
        a = row["alternative_a"]
        b = row["alternative_b"]
        for alt in (a, b):
            _shape(alt, ALTERNATIVE, "VISUAL_FILMIC_ALTERNATIVE_SHAPE")
            for key in ("filmic_technique", "audience_benefit",
                        "creative_tradeoff"):
                _text(alt[key], "VISUAL_ALTERNATIVE_EMPTY_CINEMA_ARGUMENT")
            owners = alt["required_departments"]
            _need(isinstance(owners, list) and
                  all(isinstance(o, str) and o in ROLES for o in owners)
                  and len(owners) == len(set(owners)) and bool(owners),
                  "VISUAL_ALTERNATIVE_UNREAL_CREW_OWNERS")
        _need(
            a["filmic_technique"].strip().casefold() !=
            b["filmic_technique"].strip().casefold(),
            "VISUAL_ALTERNATIVES_NOT_DISTINCT")
        _need(row["owner"] in OWNERS,
              "VISUAL_UNKNOWN_REVISION_OWNER")
        if row["outcome"] == "revision_required":
            _need(row["owner"] != "none",
                  "VISUAL_REVISION_NO_RESPONSIBLE_DEPARTMENT")
            changed.append({"from_shot":eid[0],"to_shot":eid[1],
                            "lens":lens,"owner":row["owner"]})
        elif row["outcome"] == "deliberate_discontinuity_requires_review":
            deliberate.append({"from_shot":eid[0],"to_shot":eid[1],
                               "lens":lens})
        else:
            _need(row["owner"] == "none",
                  "VISUAL_NONREVISION_MUST_NOT_PREAUTHORIZE_CREW")
        if row["outcome"] == "unverifiable_without_real_media":
            pending.append({"from_shot":eid[0],"to_shot":eid[1],
                            "lens":lens})
    issue_codes = [i["code"] for i in report["issues"]] if report else []
    blockers = [
        i["code"] for i in report["issues"]
        if i["severity"] == "blocker"
    ] if report else []
    return {
        "kind": "director_cross_shot_visual_continuity_receipt",
        "review_digest": team.fingerprint(review),
        "snapshot": deepcopy(snap),
        "reviewed_cut_boundaries": len(edges),
        "professional_craft_lens_count": len(LENSES),
        "localized_visual_revisions": changed,
        "deliberate_style_breaks_pending_real_review": deliberate,
        "media_only_unverifiable_visual_questions": pending,
        "explicit_entity_track_report_available": report is not None,
        "actual_existing_entity_track_findings": issue_codes,
        "actual_existing_entity_track_blockers": blockers,
        "visual_rework_required": bool(changed) or bool(blockers),
        "actual_media_visual_identity_verified": False,
        "actual_lighting_geometry_verified": False,
        "ready_to_certify_or_publish": False,
        "external_model_calls": 0,
    }


def propose_rework(base, state, meeting, audiovisual, review, *,
                   from_shot_id, lens, request_id,
                   what_must_remain_unchanged,
                   artistic_method_plan=None):
    """One unsent QO-D12 change anchored to specific affected cut; NO mutation."""
    proof = validate(
        base, state, meeting, audiovisual, review,
        artistic_method_plan=artistic_method_plan)
    row = next((x for x in review["edge_judgments"]
                if x["from_shot_id"] == from_shot_id and
                x["lens"] == lens), None)
    _need(row is not None and row["outcome"] == "revision_required",
          "VISUAL_NO_ACTUAL_DIRECTOR_REWORK_DECISION")
    owner = row["owner"]
    _need(owner in INTERVENTION, "VISUAL_UNKNOWN_REVISION_OWNER")
    _text(what_must_remain_unchanged,
          "VISUAL_UNSPECIFIED_ARTISTIC_PRESERVATION")
    next_shot = row["to_shot_id"]
    change = lineage.request(
        base, state, request_id=request_id, origin_role="director_final",
        kind=INTERVENTION[owner],
        shot_ids=[from_shot_id, next_shot],
        scene_or_source_beat_ids=[],
        observed_defect_or_creative_opportunity=(
            row["essential_invariant"]+"; "+row["purpose_of_matching_or_breaking_continuity"]),
        viewer_or_story_consequence=row["audience_after"],
        proposed_change_in_own_words=row["exact_rework_if_needed"],
        what_must_remain_unchanged=what_must_remain_unchanged,
        alternative_and_artistic_cost=(
            row["alternative_a"]["filmic_technique"]+" | Cost: "+
            row["alternative_a"]["creative_tradeoff"]+
            " vs "+row["alternative_b"]["filmic_technique"]+
            " | Cost: "+row["alternative_b"]["creative_tradeoff"]),
    )
    return {
        "kind": "unsent_director_cut_boundary_rework_for_original_team",
        "review_digest": proof["review_digest"],
        "cut": [from_shot_id, next_shot],
        "lens": lens,
        "change_request": change,
        "original_sourced_entitities_and_screenplay_unchanged": True,
        "department_submission_or_media_render_authorized": False,
    }
