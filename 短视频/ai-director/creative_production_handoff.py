#!/usr/bin/env python3
"""Preproduction gap audit and immutable creative-intent bridge.

A real early creative proposal is NOT a usable AI video specification. This
module copies only source-bound editorial directions into a future team's
*private* prompt and emits missing physical decisions; it never invents a
character appearance, apartment floorplan, lamp, lens or approved reference.

Use only with a verified planning snapshot; this performs NO model/media calls.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

import agent_team as team

VERSION = "editorial-to-production-handoff-v1"
# These are clearly scaffolding, NOT a chosen cinematic parameter.
UNDECIDED = frozenset({
    "", "n/a", "na", "none", "null", "tbd", "todo", "pending",
    "postproduction", "post_production", "not_applicable",
    "待统一", "待定", "待填写", "未确定", "纯后期", "图卡", "占位",
})
PLACEHOLDER_TEXT = ("待摄影", "纯后期图卡", "图卡占位", "文字或数据图形")


class HandoffError(ValueError):
    """Only static error identifiers: no original manuscript in exceptions."""


def _require(ok, code):
    if not ok:
        raise HandoffError(code)


def _empty(value):
    if not isinstance(value, str):
        return True
    normalized = value.strip().lower().replace(" ", "").replace("-", "_")
    return normalized in UNDECIDED or any(
        word in normalized for word in PLACEHOLDER_TEXT)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def bound_handoff(candidate, episode_source):
    """Build an unapproved, hashed creative brief bound to the candidate plan.

    The payload will only be stored in a *private* planning snapshot. The
    caller must never commit real scripts or raw model output to public GitHub.
    """
    _require(isinstance(candidate, dict) and
             candidate.get("kind") == "creative_storyboard_candidate" and
             candidate.get("status") == "author_review_required" and
             candidate.get("author_approved") is False,
             "HANDOFF_UNTRUSTED_CANDIDATE")
    plan = candidate.get("candidate_plan")
    _require(isinstance(plan, dict) and
             team.fingerprint(plan) == candidate.get("candidate_base_digest"),
             "HANDOFF_PLAN_DIGEST_MISMATCH")
    _require(type(episode_source) is str and
             _sha(episode_source) == candidate.get("episode_source_sha256"),
             "HANDOFF_SOURCE_DIGEST_MISMATCH")
    concept = candidate.get("editorial_concept")
    _require(isinstance(concept, dict) and
             isinstance(concept.get("shot_designs"), list),
             "HANDOFF_MISSING_CREATIVE_CONCEPT")
    ids = [s.get("id") for s in plan.get("shots", [])]
    designs = concept["shot_designs"]
    _require(len(ids) == len(designs) and bool(ids) and len(set(ids)) == len(ids),
             "HANDOFF_SHOT_COVERAGE_MISMATCH")
    for shot, design in zip(plan["shots"], designs):
        _require(isinstance(design, dict) and
                 design.get("shot_id") == shot["id"] and
                 design.get("visual_type") == shot.get("visual_type") and
                 design.get("evidence_quote") == shot.get("narration") and
                 all(isinstance(design.get(name), str) and design[name].strip()
                     for name in ("visual_intention", "camera_intention",
                                  "light_intention", "transition_intention")),
                 "HANDOFF_CREATIVE_SOURCE_OR_SHOT_DRIFT")
    return {
        "version": VERSION, "candidate_plan_digest": team.fingerprint(plan),
        "episode_source_digest": candidate["episode_source_sha256"],
        "creative_concept": deepcopy(concept),
        "status": "planning_only_no_approval",
        "human_approved": False, "media_generated": False,
        "paid_dispatch_authorized": False,
    }


def validate_locked_handoff(snapshot, episode_source):
    """Verify a handoff cannot be swapped, dropped or replayed on new source."""
    _require(isinstance(snapshot, dict) and
             isinstance(snapshot.get("plan"), dict),
             "HANDOFF_UNTRUSTED_SNAPSHOT")
    handoff = snapshot.get("creative_handoff")
    _require(isinstance(handoff, dict) and
             snapshot.get("creative_handoff_digest") ==
             team.fingerprint(handoff) and
             handoff.get("version") == VERSION and
             handoff.get("status") == "planning_only_no_approval" and
             handoff.get("human_approved") is False and
             handoff.get("paid_dispatch_authorized") is False and
             handoff.get("media_generated") is False,
             "HANDOFF_LOCKED_INTENT_MISSING_OR_CHANGED")
    _require(handoff.get("candidate_plan_digest") ==
             snapshot.get("plan_digest") ==
             team.fingerprint(snapshot["plan"]),
             "HANDOFF_SNAPSHOT_PLAN_MISMATCH")
    _require(isinstance(episode_source, str) and
             handoff.get("episode_source_digest") ==
             snapshot.get("source_digest") == _sha(episode_source),
             "HANDOFF_SNAPSHOT_SOURCE_MISMATCH")
    concept = handoff.get("creative_concept")
    _require(isinstance(concept, dict) and
             isinstance(concept.get("shot_designs"), list),
             "HANDOFF_CONCEPT_INVALID")
    shots = snapshot["plan"].get("shots")
    _require(isinstance(shots, list) and
             len(concept["shot_designs"]) == len(shots),
             "HANDOFF_CONCEPT_COVERAGE")
    for shot, direction in zip(shots, concept["shot_designs"]):
        _require(isinstance(shot, dict) and isinstance(direction, dict) and
                 shot.get("id") == direction.get("shot_id") and
                 shot.get("visual_type") == direction.get("visual_type") and
                 shot.get("narration") == direction.get("evidence_quote"),
                 "HANDOFF_CONCEPT_SOURCE_DRIFT")
    return deepcopy(handoff)


def inspect_preproduction(plan, handoff):
    """Advisory gaps, with accountable owner. No free-text semantic assertions.

    Camera/template gaps are syntactically observable. Physical-light changes,
    character reference identity, room map and true video generation need
    real-world/art review; the checker never guesses their status or fix.
    """
    _require(isinstance(plan, dict) and isinstance(plan.get("shots"), list)
             and isinstance(handoff, dict) and
             handoff.get("candidate_plan_digest") == team.fingerprint(plan),
             "HANDOFF_PREFLIGHT_WRONG_VERSION")
    concept = handoff.get("creative_concept")
    _require(isinstance(concept, dict) and
             isinstance(concept.get("shot_designs"), list) and
             len(concept["shot_designs"]) == len(plan["shots"]),
             "HANDOFF_PREFLIGHT_MISSING_INTENT")
    issues = []
    def warn(code, owner, shot_ids, review_requirement, *, severity="review"):
        issues.append({"code": code, "owner": owner, "shot_ids": list(shot_ids),
                       "required_decision": review_requirement, "severity": severity})
    lookup = {s.get("id"): s for s in plan.get("scenes", [])
              if isinstance(s, dict)}
    for shot, vision in zip(plan["shots"], concept["shot_designs"]):
        _require(vision.get("shot_id") == shot.get("id"),
                 "HANDOFF_PREFLIGHT_SHOT_ORDER_DRIFT")
        sid = shot["id"]
        if shot.get("visual_type") == "ai_video":
            camera = shot.get("camera") or {}
            for key in ("shot_size", "angle", "lens"):
                if _empty(camera.get(key)):
                    warn("VIDEO_CAMERA_" + key.upper() + "_UNRESOLVED",
                         "camera_art", [sid],
                         "摄影岗位须给实际机位、景别、镜头焦段/视角和理由；不可沿用图卡模板")
            if _empty((shot.get("art") or {}).get("set_props")):
                warn("VIDEO_PHYSICAL_PROPS_UNRESOLVED", "camera_art", [sid],
                     "美术岗位应建立真实空间与道具的位置关系，不能保留图卡占位")
            location = lookup.get(shot.get("scene_id"))
            if not location or _empty(location.get("description")):
                warn("VIDEO_SCENE_FLOORPLAN_UNRESOLVED", "camera_art", [sid],
                     "建立门、桌、灯、演员站位及门缝光的物理关系，验证轴线和连续性")
            # A video with observable human staging but no character IDs is
            # *potentially* a character-binding omission. Never invent an ID.
            if not shot.get("character_ids") and isinstance(
                    vision.get("observable_action"), dict):
                warn("VIDEO_CAST_BINDING_NOT_DECLARED", "acting", [sid],
                     "确认画面是否有人；如有，登记统一角色 ID、服化道和参考图；纯物镜可标明不需")
        elif shot.get("visual_type") in ("ai_image", "motion_graphic",
                                       "text_card"):
            warn("NONVIDEO_POSTPRODUCTION_ROUTE_REVIEW", "ai_technical", [sid],
                 "确认静态图片或图形镜头是否仅需静态/后期，不得强制生成运动视频",
                 severity="info")
    for previous, current in zip(concept["shot_designs"],
                                 concept["shot_designs"][1:]):
        if previous.get("light_intention") != current.get("light_intention"):
            warn("ADJACENT_LIGHT_SOURCE_TRANSITION_UNVERIFIED",
                 "camera_art", [previous["shot_id"], current["shot_id"]],
                 "标注两镜光源、是否有断电或门缝漏光以及改变原因，未经现场核对不得推断连续")
    return {
        "version": VERSION,
        "status": "production_specs_need_human_or_department_review"
                  if any(x["severity"] == "review" for x in issues)
                  else "only_information_notes",
        "plan_digest": team.fingerprint(plan),
        "issue_count": len(issues),
        "issues": issues,
        "director_source_intent_preserved": True,
        "identity_reference_verified": False,
        "physical_floorplan_verified": False,
        "lighting_continuity_verified": False,
        "video_provider_tested": False,
        "production_ready": False,
        "human_approved": False,
    }
