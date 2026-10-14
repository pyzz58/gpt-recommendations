#!/usr/bin/env python3
"""QO-D09 real decoded-frame smoke test of the director picture assembly.

NOT a professional renderer, NOT a private-video production path, and NOT
evidence of successful import into Kdenlive/Premiere/Resolve. Deliberately
supports only local synthetic, silent, all-hard-cut picture timelines with no
missing source. Every audio, subtitle, extra, transition and permission path
fails closed. Files are never sent to any service.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import subprocess
from urllib.parse import unquote, urlparse

import director_media_otio_export as media

VERSION = "director-synthetic-hardcut-smoke-v1"
MAX_FRAMES = 1200
SUFFIX = ".mp4"
NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}\.mp4$")


class SmokeError(ValueError):
    """Fixed code, no filenames or unpublished script lines."""


def _need(ok, code):
    if not ok:
        raise SmokeError(code)


def _read_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render_synthetic_picture_smoke(order, manifest, *, otio_json,
                                   media_root, output_dir,
                                   filename="synthetic_smoke.mp4"):
    """Render and decode-check silent picture-only synthetic montage.

    All inputs must be public synthetic test clips, never real user content.
    This is a restricted integration harness, not a publishing pipeline.
    """
    media._trusted_order(order)
    segments = order["segments"]
    total = order["final_total_frames"]
    fps = order["frame_rate_integer_fps"]
    _need(type(total) is int and 1 <= total <= MAX_FRAMES and
          type(fps) is int and fps in (24, 25, 30, 50, 60) and
          len(segments) >= 2 and
          all(s["kind"] == "story_shot_unrendered" and
              isinstance(s["source_shot_id"], str) and s["source_shot_id"]
              for s in segments),
          "SMOKE_ONLY_SHORT_SYNTHETIC_PICTURE_SHOTS")
    _need(not order["speech_events"] and not order["subtitle_events"] and
          not any(x in order["operator_blockers"] for x in (
              "SOURCE_CAPTION_TIMING_REQUIRED",
              "AUTHORITATIVE_SPEECH_AND_SUBTITLE_TIMING_REQUIRED")),
          "SMOKE_REJECTS_UNRENDERED_SPEECH_OR_SUBTITLES")
    edits = order["montage_cut_jobs"]
    _need(len(edits) == len(segments) - 1,
          "SMOKE_ALL_CUTS_MUST_BE_EXPLICIT")
    for i, edit in enumerate(edits):
        _need(edit["edit_type_exact"] == "hard_cut" and
              edit["out_shot_id"] == segments[i]["source_shot_id"] and
              edit["in_shot_id"] == segments[i+1]["source_shot_id"] and
              edit["boundary_frame"] == segments[i]["out_frame_exclusive"] and
              edit["transition_duration_frames"] == 0 and
              edit["required_gate"] is None,
              "SMOKE_REFUSES_COMPLEX_OR_UNVERIFIED_TRANSITION")
    inspection = media.inspect_local_media(order, manifest, media_root=media_root)
    _need(inspection["all_media_segments_present"] and
          len(inspection["assets"]) == len(segments),
          "SMOKE_SOURCE_MEDIA_MISSING")
    _need(isinstance(otio_json, str) and 20 <= len(otio_json) <= 1_000_000,
          "SMOKE_NATIVE_OTIO_REQUIRED")
    try:
        import opentimelineio as otio
        timeline = otio.adapters.read_from_string(
            otio_json, adapter_name="otio_json")
        metadata = timeline.metadata["ai_director"]
        loaded_edits = metadata["montage_cut_jobs"]
        _need(len(timeline.tracks) == 1 and
              len(timeline.tracks[0]) == len(segments) and
              timeline.duration().rescaled_to(fps).value == total and
              metadata["render_or_publish_authorized"] is False and
              len(loaded_edits) == len(edits),
              "SMOKE_OTIO_TIMELINE_OR_AUTHORITY_DRIFT")
        # OTIO deserializes metadata collections into AnyVector/AnyDictionary.
        # Compare source-bound cut values, never container-class equality.
        essential = ("sequence_id", "out_shot_id", "in_shot_id",
                     "boundary_frame", "edit_type_exact",
                     "transition_duration_frames", "required_gate")
        for actual, expected in zip(loaded_edits, edits):
            _need(all(actual[k] == expected[k] for k in essential),
                  "SMOKE_OTIO_CUT_PROVENANCE_DRIFT")
        for segment, item in zip(segments, timeline.tracks[0]):
            ref = inspection["assets"][segment["editor_segment_id"]]
            src = item.source_range
            _need(isinstance(item, otio.schema.Clip) and
                  item.name == segment["editor_segment_id"] and
                  item.media_reference.target_url == ref["asset_uri"] and
                  src.start_time.rescaled_to(fps).value == ref["source_in_frame"] and
                  src.duration.rescaled_to(fps).value == segment["duration_frames"],
                  "SMOKE_OTIO_MEDIA_BINDING_OR_FRAME_DRIFT")
    except SmokeError:
        raise
    except (ImportError, KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise SmokeError("SMOKE_OTIO_IMPORT_INVALID") from None
    _need(isinstance(filename, str) and NAME.fullmatch(filename),
          "SMOKE_OUTPUT_FILENAME_UNSAFE")
    root = Path(output_dir).expanduser().resolve(strict=True)
    _need(root.is_dir() and not root.is_symlink() and
          root != Path(media_root).expanduser().resolve(strict=True),
          "SMOKE_INVALID_SEPARATE_OUTPUT_DIR")
    output = root / filename
    _need(not output.exists() and not output.is_symlink(),
          "SMOKE_OUTPUT_ALREADY_EXISTS")
    sources, chains = [], []
    for i, seg in enumerate(segments):
        ref = inspection["assets"][seg["editor_segment_id"]]
        uri = urlparse(ref["asset_uri"])
        _need(uri.scheme == "file" and uri.netloc in ("", "localhost") and
              not uri.query and not uri.fragment,
              "SMOKE_NONLOCAL_MEDIA_REFERENCE")
        src = Path(unquote(uri.path))
        _need(src.is_file() and _read_hash(src) == ref["asset_sha256"],
              "SMOKE_MEDIA_CHANGED_DURING_PREFLIGHT")
        sources.extend(["-i", str(src)])
        start = ref["source_in_frame"]
        last = ref["source_out_frame_exclusive"]-1
        chains.append(
            f"[{i}:v:0]select=between(n\\,{start}\\,{last}),"
            f"setpts=N/({fps}*TB),scale=160:288:flags=bilinear,"
            f"format=yuv420p[v{i}]")
    concat = "".join(f"[v{i}]" for i in range(len(segments)))
    chains.append(f"{concat}concat=n={len(segments)}:v=1:a=0[picture]")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        *sources, "-filter_complex", ";".join(chains),
        "-map", "[picture]", "-an", "-c:v", "mpeg4", "-q:v", "5",
        "-pix_fmt", "yuv420p", "-metadata", "comment=UNPUBLISHABLE_SYNTHETIC_TEST",
        "-f", "mp4", str(output),
    ]
    try:
        process = subprocess.run(
            cmd, text=True, capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise SmokeError("SMOKE_FFMPEG_UNAVAILABLE_OR_TIMEOUT") from None
    _need(process.returncode == 0 and output.is_file(),
          "SMOKE_FFMPEG_PICTURE_ASSEMBLY_FAILED")
    probe = media._probe(output, fps, _read_hash(output))
    _need(probe["frame_count"] == total,
          "SMOKE_ACTUAL_DECODED_FRAME_COUNT_WRONG")
    return {
        "kind": "unpublishable_synthetic_picture_smoke_receipt",
        "version": VERSION,
        "frames_expected": total,
        "frames_decoded_verified": probe["frame_count"],
        "frame_rate": fps,
        "output_sha256": probe["sha256"],
        "synthetic_output_local_uri": output.as_uri(),
        "only_hard_cuts_tested": True,
        "sound_tracks_present": False,
        "subtitles_rendered": False,
        "complex_transitions_verified": False,
        "nle_import_verified": False,
        "real_story_media_verified": False,
        "render_or_publish_authorized": False,
    }
