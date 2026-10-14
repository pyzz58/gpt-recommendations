#!/usr/bin/env python3
"""QO-D09 third stage: LOCAL media preflight and native OTIO interchange preview.

Explicitly NOT a renderer, dubbing/lip-sync verifier, author approval, or a
claim that any specific NLE has successfully imported these tracks. No network.
Media bytes are read ONLY at the caller's private local media_root. Asset paths
and original dialogue must never be logged or checked into public CI.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess

import agent_team

VERSION = "director-media-otio-export-v1"
MANIFEST = {"version", "work_order_digest", "assets"}
ENTRY = {"editor_segment_id", "relative_path", "source_in_frame", "expected_sha256"}
HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 2 * 1024 * 1024 * 1024


class MediaConformError(ValueError):
    """Machine-check code only; no original filenames or screenplay content."""


def _need(ok, code):
    if not ok:
        raise MediaConformError(code)


def _trusted_order(order):
    _need(isinstance(order, dict) and
          order.get("kind") == "director_editor_conform_work_order_nonrendered" and
          order.get("render_or_publish_authorized") is False and
          order.get("ready_for_rough_cut") is False and
          type(order.get("frame_rate_integer_fps")) is int and
          isinstance(order.get("segments"), list) and
          isinstance(order.get("montage_cut_jobs"), list),
          "MEDIA_CONFORM_WORK_ORDER_UNTRUSTED")
    segments = order["segments"]
    _need(bool(segments) and all(
        isinstance(s, dict) and
        type(s.get("in_frame")) is int and
        type(s.get("out_frame_exclusive")) is int and
        s["out_frame_exclusive"] > s["in_frame"] and
        s["out_frame_exclusive"]-s["in_frame"] == s.get("duration_frames")
        for s in segments), "MEDIA_CONFORM_SEGMENTS_INVALID")
    _need(all(a["out_frame_exclusive"] == b["in_frame"]
              for a, b in zip(segments, segments[1:])) and
          segments[0]["in_frame"] == 0 and
          segments[-1]["out_frame_exclusive"] == order["final_total_frames"],
          "MEDIA_CONFORM_TIME_DRIFT")


def _path(root, raw):
    _need(isinstance(raw, str) and raw and "\0" not in raw and
          "\\" not in raw and not raw.startswith(("/", "~")) and
          not re.match(r"^[A-Za-z]:", raw) and
          all(part not in ("", ".", "..") for part in raw.split("/")),
          "MEDIA_CONFORM_UNSAFE_RELATIVE_PATH")
    try:
        p = root.joinpath(*raw.split("/"))
        _need(p.is_file() and not p.is_symlink() and
              not any(x.is_symlink() for x in p.parents if x != root) and
              p.resolve(strict=True).is_relative_to(root),
              "MEDIA_CONFORM_MISSING_OR_UNSAFE_FILE")
    except (OSError, ValueError):
        raise MediaConformError("MEDIA_CONFORM_MISSING_OR_UNSAFE_FILE") from None
    return p


def _probe(path, fps, expected_sha):
    _need(path.stat().st_size > 0 and path.stat().st_size <= MAX_BYTES,
          "MEDIA_CONFORM_FILE_SIZE")
    hash_obj = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    _need(hash_obj.hexdigest() == expected_sha, "MEDIA_CONFORM_SHA256_MISMATCH")
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,nb_frames",
            "-of", "json", str(path)],
            text=True, capture_output=True, check=False, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        raise MediaConformError("MEDIA_CONFORM_FFPROBE_UNAVAILABLE_OR_TIMEOUT") from None
    _need(result.returncode == 0 and len(result.stdout) <= 65536,
          "MEDIA_CONFORM_FFPROBE_FAILED")
    try:
        streams = json.loads(result.stdout)["streams"]
        _need(len(streams) == 1 and isinstance(streams[0], dict),
              "MEDIA_CONFORM_ONE_VIDEO_STREAM_REQUIRED")
        row = streams[0]
        _need(Fraction(row["r_frame_rate"]) == Fraction(fps, 1) and
              Fraction(row["avg_frame_rate"]) == Fraction(fps, 1),
              "MEDIA_CONFORM_NONMATCHING_OR_VARIABLE_FPS")
        frames_str = row.get("nb_read_frames")
        _need(isinstance(frames_str, str) and frames_str.isdecimal(),
              "MEDIA_CONFORM_FRAME_COUNT_NOT_PROVEN")
        count = int(frames_str)
        _need(count > 0 and
              type(row["width"]) is int and row["width"] > 0 and
              type(row["height"]) is int and row["height"] > 0,
              "MEDIA_CONFORM_VIDEO_PROPERTIES_INVALID")
        return {"frame_count": count, "width": row["width"],
                "height": row["height"], "codec": row["codec_name"],
                "sha256": expected_sha}
    except MediaConformError:
        raise
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        raise MediaConformError("MEDIA_CONFORM_FFPROBE_UNTRUSTED_METADATA") from None


def inspect_local_media(order, manifest, *, media_root):
    """Probe and hash local files now; never trust a caller's 'verified' flag."""
    _trusted_order(order)
    _need(isinstance(manifest, dict) and set(manifest) == MANIFEST and
          manifest["version"] == VERSION and
          manifest["work_order_digest"] == agent_team.fingerprint(order),
          "MEDIA_CONFORM_STALE_OR_MALFORMED_MANIFEST")
    rows = manifest["assets"]
    _need(isinstance(rows, list) and len(rows) <= len(order["segments"]),
          "MEDIA_CONFORM_ASSETS_INVALID")
    slots = {s["editor_segment_id"]: s for s in order["segments"]}
    _need(len(slots) == len(order["segments"]),
          "MEDIA_CONFORM_DUPLICATE_WORK_ORDER_SLOT")
    root = Path(media_root).expanduser().resolve(strict=True)
    _need(root.is_dir(), "MEDIA_CONFORM_MEDIA_ROOT_INVALID")
    seen = set()
    validated = {}
    fps = order["frame_rate_integer_fps"]
    for row in rows:
        _need(isinstance(row, dict) and set(row) == ENTRY,
              "MEDIA_CONFORM_ASSET_ITEM_SHAPE")
        sid, start, sha = (row["editor_segment_id"],
                           row["source_in_frame"], row["expected_sha256"])
        _need(sid in slots and sid not in seen and type(start) is int and
              start >= 0 and isinstance(sha, str) and HEX.fullmatch(sha),
              "MEDIA_CONFORM_DUPLICATE_OR_INVALID_BINDING")
        seen.add(sid)
        file = _path(root, row["relative_path"])
        meta = _probe(file, fps, sha)
        duration = slots[sid]["duration_frames"]
        _need(start + duration <= meta["frame_count"],
              "MEDIA_CONFORM_INSUFFICIENT_SOURCE_FRAMES")
        validated[sid] = {
            "asset_uri": file.as_uri(),
            "asset_sha256": sha,
            "source_in_frame": start,
            "source_out_frame_exclusive": start + duration,
            "available_head_frames": start,
            "available_tail_frames": meta["frame_count"]-start-duration,
            "verified_video_metadata": meta,
            "local_probe_and_hash_passed": True,
            "picture_artistry_verified": False,
            "source_audio_synchronized": False,
        }
    cut_limits = []
    for cut in order["montage_cut_jobs"]:
        outgoing = next(s for s in order["segments"]
                        if s["source_shot_id"] == cut["out_shot_id"])
        incoming = next(s for s in order["segments"]
                        if s["source_shot_id"] == cut["in_shot_id"])
        out_ref = validated.get(outgoing["editor_segment_id"])
        in_ref = validated.get(incoming["editor_segment_id"])
        cut_limits.append({
            "sequence_id": cut["sequence_id"],
            "boundary_frame": cut["boundary_frame"],
            "edit_type": cut["edit_type_exact"],
            "both_picture_files_probed": bool(out_ref and in_ref),
            "maximum_symmetric_handle_frames": (
                min(out_ref["available_tail_frames"],
                    in_ref["available_head_frames"])
                if out_ref and in_ref else None),
            "nonhard_transition_effect_not_rendered": cut["edit_type_exact"] != "hard_cut",
            "director_art_review_verified": False,
        })
    missing = [sid for sid in slots if sid not in validated]
    return {
        "kind": "local_only_editor_media_inspection",
        "version": VERSION,
        "work_order_digest": agent_team.fingerprint(order),
        "frame_rate_integer_fps": fps,
        "assets": validated,
        "missing_editor_segments": missing,
        "montage_cut_handle_inspections": cut_limits,
        "picture_file_count_hashed_and_probed": len(validated),
        "all_media_segments_present": not missing,
        "sound_foley_or_lip_sync_verified": False,
        "montage_transitions_rendered": False,
        "permission_to_render_or_publish": False,
    }


def export_native_otio_preview(order, manifest, *, media_root):
    """Native .otio JSON via the OSS package; picture gaps remain real gaps.

    Import/export guarantees only the native OTIO schema roundtrip, NOT that
    individual NLE software reproduces effects, subtitles, music or credits.
    """
    inspection = inspect_local_media(order, manifest, media_root=media_root)
    try:
        import opentimelineio as otio
    except ImportError:
        raise MediaConformError("MEDIA_CONFORM_OTIO_LIBRARY_NOT_INSTALLED") from None
    fps = order["frame_rate_integer_fps"]
    timeline = otio.schema.Timeline(name="AI Director editorial conform PREVIEW")
    timeline.metadata["ai_director"] = {
        "operator_review_required": True,
        "render_or_publish_authorized": False,
        "director_coverage_digest": order["director_coverage_digest"],
        "montage_cut_jobs": deepcopy(order["montage_cut_jobs"]),
        "speech_cue_schedule_not_rendered": deepcopy(order["speech_events"]),
        "subtitle_cue_schedule_not_rendered": deepcopy(order["subtitle_events"]),
        "picture_media_gaps_present": not inspection["all_media_segments_present"],
        "unsolved_editor_blockers": deepcopy(order["operator_blockers"]),
    }
    track = otio.schema.Track(name="Director picture track",
                              kind=otio.schema.TrackKind.Video)
    for segment in order["segments"]:
        sid = segment["editor_segment_id"]
        duration = segment["duration_frames"]
        ref = inspection["assets"].get(sid)
        tr = otio.opentime.TimeRange(
            otio.opentime.RationalTime(ref["source_in_frame"] if ref else 0, fps),
            otio.opentime.RationalTime(duration, fps))
        if ref:
            item = otio.schema.Clip(
                name=sid,
                media_reference=otio.schema.ExternalReference(
                    target_url=ref["asset_uri"]),
                source_range=tr)
        else:
            item = otio.schema.Gap(name=sid, source_range=tr)
        item.metadata["ai_director"] = {
            "source_shot_id": segment["source_shot_id"] or "",
            "editor_segment_id": sid,
            "asset_probed_on_local_disk": bool(ref),
            "lip_sync_and_sound_not_verified": True,
        }
        track.append(item)
    timeline.tracks.append(track)
    result = otio.adapters.write_to_string(timeline, adapter_name="otio_json")
    roundtrip = otio.adapters.read_from_string(result, adapter_name="otio_json")
    _need(roundtrip.duration().rescaled_to(fps).value ==
          order["final_total_frames"],
          "MEDIA_CONFORM_OTIO_ROUNDTRIP_DURATION_CHANGED")
    return {
        "kind": "nonrendered_native_otio_json_preview",
        "extension": ".otio",
        "otio_json": result,
        "frame_rate": fps,
        "total_frames": order["final_total_frames"],
        "media_clips_probed": len(inspection["assets"]),
        "missing_picture_slots": deepcopy(inspection["missing_editor_segments"]),
        "montage_effects_not_auto_rendered": True,
        "subtitle_tracks_not_auto_rendered": True,
        "render_or_publish_authorized": False,
    }


def export_subtitle_srt_plan(order):
    """SRT text from EXACT planner cues, not media-recognized speech timing."""
    _trusted_order(order)
    fps = order["frame_rate_integer_fps"]

    def timestamp(frame):
        ms = (frame * 1000 * 2 + fps) // (2 * fps)
        hours, ms = divmod(ms, 3600000)
        minutes, ms = divmod(ms, 60000)
        seconds, millis = divmod(ms, 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    lines = []
    prior = 0
    for i, cue in enumerate(order["subtitle_events"], 1):
        start, end = cue["start_frame"], cue["end_frame_exclusive"]
        _need(type(start) is int and type(end) is int and
              0 <= prior <= start < end <= order["final_total_frames"],
              "MEDIA_CONFORM_SUBTITLE_FRAME_OVERLAP_OR_OOB")
        words = cue["source_text_exact"]
        _need(isinstance(words, str) and words.strip() and
              "\0" not in words and "\r" not in words and
              "-->" not in words,
              "MEDIA_CONFORM_SUBTITLE_TEXT_UNSAFE")
        lines.extend([str(i), f"{timestamp(start)} --> {timestamp(end)}",
                      words, ""])
        prior = end
    return {
        "kind": "unverified_srt_subtitle_plan",
        "extension": ".srt",
        "srt_text": "\n".join(lines),
        "subtitle_count": len(order["subtitle_events"]),
        "subtitle_timing_is_director_planned_not_media_verified": True,
        "render_or_publish_authorized": False,
    }
