#!/usr/bin/env python3
"""F02 source-bound camera, lighting and art continuity preflight.

Offline structural review only: no model call, media generation, real-set
verification or claim that a design is visually beautiful. The F01 acting
contract remains the authority for body/hand/prop state; this module checks
the camera/art side of the same DAG.
"""
from __future__ import annotations

from copy import deepcopy

from creative_production_handoff import LIGHTING_STATES, VIDEO_SHOT_SIZES

VERSION = "director-photography-contract-v1"
MODE = {
    "kind": "source_bound_photography_plan_required",
    "version": 1,
}
SCREEN_SIDES = frozenset({"left", "right", "center"})
GENERIC_PHOTOGRAPHY = (
    "电影感", "大片感", "高级感", "高级质感", "视觉冲击",
    "唯美", "大气", "专业感", "自然地",
)
GENERIC_CAUSE = (
    "灯光不变", "无变化", "没有变化", "unchanged", "no change",
    "same as previous",
)


class PhotographyContractError(ValueError):
    """Static codes only; never echo private screenplay or prompt text."""


def _need(ok, code):
    if not ok:
        raise PhotographyContractError(code)


def _text(value, minimum=1):
    return isinstance(value, str) and len(value.strip()) >= minimum


def _add(items, code, detail, shot_id=None):
    row = {"code": code, "detail": detail}
    if shot_id is not None:
        row["shot_id"] = shot_id
    items.append(row)


def _geometry_ok(geometry):
    return (
        isinstance(geometry, dict)
        and set(geometry) == {"anchor_positions", "key_light_position", "camera_axis"}
        and isinstance(geometry["anchor_positions"], dict)
        and len(geometry["anchor_positions"]) >= 2
        and all(_text(value) for value in geometry["anchor_positions"].values())
        and _text(geometry["key_light_position"])
        and _text(geometry["camera_axis"])
    )


def inspect_delivery(base, payload):
    report = {"version": VERSION, "mode": deepcopy(MODE),
              "blockers": [], "reviews": []}
    mode = base.get("photography_contract_mode")
    if mode is None:
        report["not_required"] = True
        return report
    if mode != MODE:
        _add(report["blockers"], "PHOTOGRAPHY_CONTRACT_MODE_INVALID",
             "photography_contract_mode must be the reviewed source-bound mode")
        return report
    shots = payload.get("shots")
    if not isinstance(shots, dict):
        _add(report["blockers"], "PHOTOGRAPHY_SHOTS_INVALID",
             "camera_art payload must contain a shots object")
        return report
    sources = {shot.get("id"): shot for shot in base.get("shots", [])
               if isinstance(shot, dict)}
    previous_by_scene = {}
    for sid, source in sources.items():
        authored = shots.get(sid)
        if authored is None:
            continue
        camera = authored.get("camera") if isinstance(authored, dict) else None
        art = authored.get("art") if isinstance(authored, dict) else None
        if not isinstance(camera, dict) or not isinstance(art, dict):
            _add(report["blockers"], "PHOTOGRAPHY_ART_SECTIONS_REQUIRED",
                 "camera and art must both be authored objects", shot_id=sid)
            continue
        for field, code, minimum in (
            ("start_frame", "PHOTOGRAPHY_START_FRAME_MISSING", 1),
            ("movement", "PHOTOGRAPHY_MOVEMENT_MISSING", 1),
            ("end_frame", "PHOTOGRAPHY_END_FRAME_MISSING", 1),
            ("lens_feel", "PHOTOGRAPHY_LENS_FEEL_MISSING", 1),
            ("reason", "PHOTOGRAPHY_CAMERA_REASON_MISSING", 1),
            ("screen_axis", "PHOTOGRAPHY_SCREEN_AXIS_MISSING", 6),
            ("eyeline", "PHOTOGRAPHY_EYELINE_MISSING", 1),
            ("movement_trigger_event", "PHOTOGRAPHY_MOVEMENT_TRIGGER_MISSING", 1),
        ):
            if not _text(camera.get(field), minimum):
                _add(report["blockers"], code,
                     "camera needs concrete " + field, shot_id=sid)
        if camera.get("shot_size") not in VIDEO_SHOT_SIZES:
            _add(report["blockers"], "PHOTOGRAPHY_SHOT_SIZE_INVALID",
                 "shot_size must be a reviewed video shot size", shot_id=sid)
        focal = camera.get("focal_length_mm")
        if not isinstance(focal, (int, float)) or isinstance(focal, bool) or not 14 <= focal <= 135:
            _add(report["blockers"], "PHOTOGRAPHY_FOCAL_LENGTH_INVALID",
                 "focal_length_mm must be between 14 and 135", shot_id=sid)
        if camera.get("camera_side") not in SCREEN_SIDES:
            _add(report["blockers"], "PHOTOGRAPHY_CAMERA_SIDE_INVALID",
                 "camera_side must be left/right/center", shot_id=sid)
        trigger = camera.get("move_trigger_s")
        duration = source.get("duration")
        if (not isinstance(trigger, (int, float)) or isinstance(trigger, bool)
                or not 0 <= trigger <= duration):
            _add(report["blockers"], "PHOTOGRAPHY_MOVE_TRIGGER_TIME_INVALID",
                 "move_trigger_s must sit inside the shot", shot_id=sid)
        if not _text(art.get("environment")):
            _add(report["blockers"], "PHOTOGRAPHY_ENVIRONMENT_MISSING",
                 "art needs a concrete environment", shot_id=sid)
        if art.get("lighting_state") not in LIGHTING_STATES:
            _add(report["blockers"], "PHOTOGRAPHY_LIGHTING_STATE_INVALID",
                 "lighting_state must be a reviewed state", shot_id=sid)
        practical = art.get("practical_sources")
        if (not isinstance(practical, list) or not practical
                or not all(_text(value) for value in practical)):
            _add(report["blockers"], "PHOTOGRAPHY_PRACTICAL_SOURCES_MISSING",
                 "art needs explicit practical light sources", shot_id=sid)
        if not _text(art.get("key_light_position")):
            _add(report["blockers"], "PHOTOGRAPHY_KEY_LIGHT_POSITION_MISSING",
                 "art needs a physical key-light position", shot_id=sid)
        if not _text(art.get("key_light_direction")):
            _add(report["blockers"], "PHOTOGRAPHY_KEY_LIGHT_DIRECTION_MISSING",
                 "art needs a key-light direction", shot_id=sid)
        if not _text(art.get("color_path")):
            _add(report["blockers"], "PHOTOGRAPHY_COLOR_PATH_MISSING",
                 "art needs a color path", shot_id=sid)
        if not _text(art.get("safe_area")):
            _add(report["blockers"], "PHOTOGRAPHY_SAFE_AREA_MISSING",
                 "art needs a 9:16 subject/action safe-area plan", shot_id=sid)
        if not _text(art.get("lighting_change_reason"), 6):
            _add(report["blockers"], "PHOTOGRAPHY_LIGHT_CHANGE_CAUSE_MISSING",
                 "art needs a lighting change cause", shot_id=sid)
        geometry = art.get("scene_geometry")
        if not _geometry_ok(geometry):
            _add(report["blockers"], "PHOTOGRAPHY_SCENE_GEOMETRY_INVALID",
                 "scene_geometry needs anchors, key light and camera axis", shot_id=sid)
        elif art.get("key_light_position") != geometry["key_light_position"]:
            _add(report["blockers"], "PHOTOGRAPHY_LIGHT_GEOMETRY_MISMATCH",
                 "art key-light position must match scene geometry", shot_id=sid)
        for field in ("lens_feel", "reason", "color_path", "movement_trigger_event"):
            value = camera.get(field) if field in camera else art.get(field)
            if _text(value) and any(signal in value for signal in GENERIC_PHOTOGRAPHY):
                _add(report["reviews"], "PHOTOGRAPHY_GENERIC_LANGUAGE",
                     "review generic photography language in " + field, shot_id=sid)
        scene_id = source.get("scene_id")
        previous = previous_by_scene.get(scene_id)
        if previous is not None and isinstance(geometry, dict) and _geometry_ok(geometry):
            old_geometry = previous["geometry"]
            if old_geometry != geometry:
                _add(report["blockers"], "PHOTOGRAPHY_GEOMETRY_DRIFT",
                     "scene geometry must remain identical within one declared scene",
                     shot_id=sid)
            old_camera = previous["camera"]
            old_side, new_side = old_camera.get("camera_side"), camera.get("camera_side")
            if {old_side, new_side} == {"left", "right"}:
                if _text(camera.get("axis_break_reason"), 6):
                    _add(report["reviews"], "PHOTOGRAPHY_AXIS_BREAK_REVIEW",
                         "an intentional 180-degree axis break needs human review",
                         shot_id=sid)
                else:
                    _add(report["blockers"], "PHOTOGRAPHY_AXIS_JUMP",
                         "camera crosses the action axis without an explicit reason",
                         shot_id=sid)
            old_light = previous["art"].get("key_light_position")
            new_light = art.get("key_light_position")
            old_direction = previous["art"].get("key_light_direction")
            new_direction = art.get("key_light_direction")
            if (old_light != new_light or old_direction != new_direction):
                cause = art.get("lighting_change_reason", "").strip().lower()
                if not cause or cause in GENERIC_CAUSE:
                    _add(report["blockers"], "PHOTOGRAPHY_LIGHT_SOURCE_JUMP",
                         "key light changes without a concrete motivated cause",
                         shot_id=sid)
                else:
                    _add(report["reviews"], "PHOTOGRAPHY_LIGHT_CHANGE_REVIEW",
                         "motivated key-light change needs human visual review",
                         shot_id=sid)
        previous_by_scene[scene_id] = {
            "geometry": deepcopy(geometry),
            "camera": deepcopy(camera),
            "art": deepcopy(art),
        }
    return report
