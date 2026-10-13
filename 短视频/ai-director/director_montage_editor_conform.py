#!/usr/bin/env python3
"""QO-D09: source-locked editor conform sheet, not an executable render.

The editor receives frame-accurate shot slots, montage cuts, optional D19 audio
and captions, and the existing QO-D13 absolute extra/credits timeline.
No clip files are invented, no cut is silently substituted, no paid calls.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import math

import agent_team
import closing_evidence_card
import director_shot_coverage
import series_final_timeline

VERSION = "director-montage-editor-conform-v1"
ALLOWED_FPS = {24, 25, 30, 50, 60}
MONTAGE_RENDER_GATES = {
    "dissolve": "TRANSITION_HANDLES_AND_DURATION_REQUIRED",
    "match_cut": "MATCH_FRAME_VISUAL_VERIFICATION_REQUIRED",
    "sound_bridge": "J_L_AUDIO_BRIDGE_TIMING_AND_MEDIA_REQUIRED",
    "jump_cut": "JUMP_CUT_ARTISTIC_REVIEW_REQUIRED",
    "hard_cut": None,
}


class ConformError(ValueError):
    """Safe machine-check codes; never echo screenplay/audio source."""


def _need(ok, code):
    if not ok:
        raise ConformError(code)


def _frame(seconds, fps):
    _need(type(seconds) in (int, float) and math.isfinite(seconds) and
          seconds >= 0, "CONFORM_INVALID_SECONDS")
    try:
        count = Decimal(str(seconds)) * fps
    except (InvalidOperation, ValueError):
        raise ConformError("CONFORM_INVALID_SECONDS") from None
    _need(count == count.to_integral_value(),
          "CONFORM_OFF_FRAME_GRID")
    return int(count)


def _validate_absolute_story(absolute, base, fps):
    _need(absolute is not None, "CONFORM_SERIES_TIMELINE_REQUIRED")
    segments = absolute["absolute_segments"]
    story = [s for s in segments if s["kind"] == "story_shot_unrendered"]
    shots = base["shots"]
    _need(len(story) == len(shots),
          "CONFORM_STORY_SHOT_COUNT_DRIFT")
    shot_slots = {}
    entries = []
    position = 0
    for segment in segments:
        start = _frame(segment["start_s"], fps)
        end = _frame(segment["end_s"], fps)
        _need(start == position and end > start,
              "CONFORM_ABSOLUTE_TIME_GAP_OVERLAP")
        position = end
        entry = {
            "editor_segment_id": segment["editor_segment_id"],
            "kind": segment["kind"],
            "source_shot_id": segment.get("source_shot_id"),
            "in_frame": start, "out_frame_exclusive": end,
            "duration_frames": end-start,
            "source_media_asset": None,
            "source_media_verified": False,
        }
        entries.append(entry)
    for row, shot in zip(story, shots):
        _need(row["source_shot_id"] == shot["id"] and
              abs((row["end_s"]-row["start_s"])-shot["duration"]) < 0.0001,
              "CONFORM_SHOT_ORDER_OR_DURATION_DRIFT")
        absolute_start = _frame(row["start_s"], fps)
        absolute_end = _frame(row["end_s"], fps)
        _need(absolute_end - absolute_start == _frame(shot["duration"], fps),
              "CONFORM_SHOT_FRAME_BUDGET_DRIFT")
        shot_slots[shot["id"]] = (absolute_start, absolute_end)
    _need(position == _frame(absolute["planned_final_duration_s"], fps) and
          absolute["fits_90_second_budget"] is True and
          position <= 90 * fps, "CONFORM_FINAL_RUNTIME_BUDGET_DRIFT")
    return entries, shot_slots


def compile_work_order(handoff, dossier, breakdown, original_packet,
                       director_coverage, *, fps):
    """Return a deterministic in-memory editor's assembly & punch list.

    Recomputes script-bound director coverage and crew from the ORIGINAL
    immutable episode packet, not from a mutable downstream memo.
    """
    _need(type(fps) is int and fps in ALLOWED_FPS,
          "CONFORM_EXPLICIT_SUPPORTED_INTEGER_FPS_REQUIRED")
    _need("montage_plan" in director_coverage,
          "CONFORM_DIRECTOR_MONTAGE_REQUIRED")
    rebuilt = director_shot_coverage.reblock_episode(
        handoff, dossier, breakdown, original_packet, director_coverage)
    ep = next(x for x in rebuilt["episodes"]
              if x["episode_id"] == director_coverage["episode_id"])
    base = ep["authoritative_episode_base"]
    source_digest = agent_team.fingerprint(base)
    try:
        card = closing_evidence_card.build_card(base)
        timeline = series_final_timeline.compile_final_timeline(base, card)
    except (closing_evidence_card.ClosingCardError,
            series_final_timeline.SeriesTimelineError) as exc:
        raise ConformError("CONFORM_FINAL_" + str(exc)) from None
    entries, slots = _validate_absolute_story(timeline, base, fps)
    _need(bool(slots), "CONFORM_MISSING_SHOTS")
    origin = min(a for a, _ in slots.values())
    cut_jobs = []
    blocked = set()
    plan = director_coverage["montage_plan"]
    for sequence in plan["sequences"]:
        ids = sequence["shot_ids"]
        for i, seam in enumerate(sequence["seams"]):
            out_id, in_id = ids[i], ids[i+1]
            out_end = slots[out_id][1]
            in_start = slots[in_id][0]
            _need(out_end == in_start, "CONFORM_MONTAGE_CUT_NOT_CONTIGUOUS")
            kind = seam["edit_type"]
            gate = MONTAGE_RENDER_GATES[kind]
            if gate:
                blocked.add(gate)
            cut_jobs.append({
                "sequence_id": sequence["sequence_id"],
                "out_shot_id": out_id,
                "in_shot_id": in_id,
                "boundary_frame": out_end,
                "boundary_s": out_end / fps,
                "edit_type_exact": kind,
                "time_relation": seam["time_relation"],
                "time_claim_source_exact": seam["source_time_evidence"],
                "source_scene_pair": [seam["out_scene_id"],
                                      seam["in_scene_id"]],
                "director_intention": sequence["director_intention"],
                "viewer_before": seam["viewer_before"],
                "viewer_after": seam["viewer_after"],
                "editorial_reason": seam["editorial_reason"],
                "actor_prop_handoff": seam["performer_prop_bridge"],
                "space_light_handoff": seam["axis_light_bridge"],
                "sound_handoff": seam["sound_intention"],
                "fallback_for_editor_review_only": seam["ai_fallback"],
                "visual_transition_ready_for_media_conform": gate is None,
                "required_gate": gate,
                "transition_duration_frames": 0 if kind == "hard_cut" else None,
                "audio_overlap_frames": None,
                "media_and_aesthetic_review_verified": False,
            })
    _need(len(cut_jobs) == base["director_editorial_montage"]
          ["receipt"]["cut_count"], "CONFORM_CUT_COUNT_DRIFT")

    speech, captions = [], []
    sheet = base.get("director_editor_cue_sheet")
    if sheet is not None:
        _need(sheet.get("legacy_shot_text_rendering_allowed") is False and
              sheet.get("lip_sync_verified") is False,
              "CONFORM_CUE_AUTHORITY_INVALID")
        for track_name, dest in (("speech_cues", speech),
                                 ("subtitle_cues", captions)):
            for cue in sheet[track_name]:
                start = _frame(cue["story_from_s"], fps) + origin
                end = _frame(cue["story_to_s"], fps) + origin
                _need(start < end, "CONFORM_CUE_DURATION")
                picture_segments = []
                for frag in cue["picture_segments"]:
                    fa = _frame(frag["story_from_s"], fps) + origin
                    fb = _frame(frag["story_to_s"], fps) + origin
                    _need(frag["director_shot_id"] in slots and
                          slots[frag["director_shot_id"]][0] <= fa < fb <=
                          slots[frag["director_shot_id"]][1],
                          "CONFORM_CUE_OUTSIDE_ASSOCIATED_SHOT")
                    picture_segments.append({
                        "shot_id": frag["director_shot_id"],
                        "start_frame": fa, "end_frame_exclusive": fb,
                        "source_beat_id": frag["beat_id"],
                    })
                _need(bool(picture_segments) and
                      picture_segments[0]["start_frame"] == start and
                      picture_segments[-1]["end_frame_exclusive"] == end and
                      all(a["end_frame_exclusive"] == b["start_frame"]
                          for a, b in zip(picture_segments, picture_segments[1:])),
                      "CONFORM_CUE_FRAME_COVERAGE_INCOMPLETE")
                dest.append({
                    "source_cue_id": cue.get("cue_id", cue.get("subtitle_id")),
                    "source_beat_id": cue["beat_id"],
                    "start_frame": start, "end_frame_exclusive": end,
                    "source_text_exact": cue["text_exact"],
                    "source_speaker": cue.get("speaker"),
                    "video_picture_segments": picture_segments,
                    "audio_asset": None if track_name == "speech_cues" else "not_applicable",
                    "alignment_media_verified": False,
                })
    else:
        # Source words may exist in the screenplay without timing. Never
        # silently assume that old shot-embedded text can be played on time.
        _need("director_speech_cue_timeline" not in base,
              "CONFORM_TIMED_CUES_DROPPED")
        active = set(next(e["beat_ids"] for e in breakdown["episodes"]
                          if e["episode_id"] == ep["episode_id"]))
        has_speech = any(b["dialogue"] or b["voiceover"]
                         for sc in handoff["screenplay_scenes"]
                         for b in sc["beats"] if b["id"] in active)
        if has_speech:
            blocked.add("AUTHORITATIVE_SPEECH_AND_SUBTITLE_TIMING_REQUIRED")
        if any(shot.get("subtitles", {}).get("text") for shot in base["shots"]):
            blocked.add("SOURCE_CAPTION_TIMING_REQUIRED")

    for entry in entries:
        blocked.add("SOURCE_MEDIA_ASSETS_NOT_PROVIDED")
        if entry["kind"] == "reserved_postproduction":
            blocked.add("RESERVED_INTRO_RECAP_BRIDGE_OUTRO_NOT_RENDERED")
        elif entry["kind"] == "final_evidence_postproduction":
            blocked.add("FINAL_EVIDENCE_CARD_NOT_RENDERED")
    if speech:
        blocked.add("SPEECH_AUDIO_MEDIA_NOT_PROVIDED")
        blocked.add("REAL_LIP_SYNC_NOT_VERIFIED")
    if captions:
        blocked.add("SUBTITLE_OVERLAY_MEDIA_NOT_RENDERED")

    return {
        "kind": "director_editor_conform_work_order_nonrendered",
        "version": VERSION,
        "episode_id": ep["episode_id"],
        "source_screenplay_digest": handoff["screenplay_text_digest"],
        "director_coverage_digest": agent_team.fingerprint(director_coverage),
        "authoritative_reblocked_base_digest": source_digest,
        "frame_rate_integer_fps": fps,
        "story_first_frame": origin,
        "final_total_frames": _frame(timeline["planned_final_duration_s"], fps),
        "final_total_s": timeline["planned_final_duration_s"],
        "segments": entries,
        "montage_cut_jobs": cut_jobs,
        "speech_events": speech,
        "subtitle_events": captions,
        "reserved_components_s": deepcopy(timeline["reserved_components_s"]),
        "final_card_is_last": timeline["last_card_is_final_segment"],
        "operator_blockers": sorted(blocked),
        "author_and_art_review_authenticated": False,
        "real_media_available": False,
        "ready_for_rough_cut": False,
        "render_or_publish_authorized": False,
    }


def editor_instructions(work_order):
    """A readable editor checklist; deterministic and never writes files."""
    _need(work_order.get("kind") ==
          "director_editor_conform_work_order_nonrendered" and
          work_order.get("render_or_publish_authorized") is False,
          "CONFORM_WORK_ORDER_NOT_TRUSTED")
    lines = [
        f"导演剪辑工单 | {work_order['episode_id']} | "
        f"{work_order['frame_rate_integer_fps']} fps",
        f"总片长 {work_order['final_total_frames']} 帧"
        f"（{work_order['final_total_s']} 秒，含片头片尾与可选依据页）",
        "按 segments 逐项向后期申请真实素材；不可用占位字稿替代真实音画。",
    ]
    for j in work_order["montage_cut_jobs"]:
        lines.append(
            f"{j['sequence_id']}: {j['out_shot_id']} -> {j['in_shot_id']} "
            f"帧 {j['boundary_frame']}，{j['edit_type_exact']}；"
            f"观众变化：{j['viewer_before']} / {j['viewer_after']}；"
            f"剪切原因：{j['editorial_reason']}；"
            f"执行阻断：{j['required_gate'] or '待真实素材核验'}")
    lines.append("阻断清单：" + ("、".join(work_order["operator_blockers"]) or "无"))
    lines.append("只有文字规划与静态校验；未生成视频，不可发布。")
    return "\n".join(lines) + "\n"
