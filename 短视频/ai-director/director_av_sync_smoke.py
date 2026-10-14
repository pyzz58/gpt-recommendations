#!/usr/bin/env python3
"""QO-D19: *public synthetic only* subtitle/audio mux and decoded timing proof.

This is a restricted offline validation fixture. It CANNOT dub a private story,
cannot infer dialogue timestamps, cannot lip-sync an actor, and never grants
a render/publication approval. Inputs are a previously proven silent picture,
an explicit frame-bound source cue plan and a synthetic PCM test-tone WAV.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import struct
import subprocess
import wave

import director_media_otio_export as media

VERSION = "director-synthetic-av-timing-smoke-v1"
SAMPLE_RATE = 48000
MAX_FRAMES = 300
SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}\.(?:mp4|wav|mkv)$")
SAFE_FILTER_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")
MAX_BYTES = 32 * 1024 * 1024


class AVSmokeError(ValueError):
    """Fixed machine error codes, never user footage, dialogue or local paths."""


def _need(ok, code):
    if not ok:
        raise AVSmokeError(code)


def _hash(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _path(root, name):
    _need(isinstance(name, str) and SAFE_NAME.fullmatch(name),
          "AV_SMOKE_UNSAFE_FILENAME")
    p = root / name
    _need(p.is_file() and not p.is_symlink() and
          p.resolve(strict=True).is_relative_to(root) and
          0 < p.stat().st_size <= MAX_BYTES,
          "AV_SMOKE_LOCAL_FILE_MISSING_OR_INVALID")
    return p


def _intervals(rows, total, label):
    _need(isinstance(rows, list) and 1 <= len(rows) <= 12,
          "AV_SMOKE_"+label+"_CUES_REQUIRED")
    spans, position = [], 0
    for row in rows:
        _need(isinstance(row, dict) and
              type(row.get("start_frame")) is int and
              type(row.get("end_frame_exclusive")) is int and
              position <= row["start_frame"] < row["end_frame_exclusive"] <= total,
              "AV_SMOKE_"+label+"_INTERVAL_INVALID")
        spans.append((row["start_frame"], row["end_frame_exclusive"]))
        position = row["end_frame_exclusive"]
    return spans


def _pcm(path, expected_samples):
    try:
        with wave.open(str(path), "rb") as fh:
            _need(fh.getnchannels() == 1 and fh.getframerate() == SAMPLE_RATE
                  and fh.getsampwidth() == 2 and
                  fh.getnframes() == expected_samples and
                  fh.getcomptype() == "NONE",
                  "AV_SMOKE_SYNTHETIC_PCM_FORMAT_INVALID")
            return fh.readframes(expected_samples)
    except (wave.Error, EOFError):
        raise AVSmokeError("AV_SMOKE_SYNTHETIC_PCM_INVALID") from None


def _verify_tone_envelope(pcm_bytes, spans, fps):
    # Exact 48kHz samples; project frame-rate must divide sample rate.
    per_frame = SAMPLE_RATE // fps
    count = len(pcm_bytes) // 2
    samples = struct.unpack("<"+str(count)+"h", pcm_bytes)
    active = [False] * (count // per_frame)
    for start, end in spans:
        for frame in range(start, end):
            active[frame] = True
    for frame, required in enumerate(active):
        a = frame * per_frame
        b = (frame+1) * per_frame
        peak = max(abs(x) for x in samples[a:b])
        if required:
            _need(peak >= 800, "AV_SMOKE_TONE_MISSING_IN_CUE_FRAME")
        else:
            _need(peak <= 2, "AV_SMOKE_TONE_LEAK_OUTSIDE_CUE")


def render_public_synthetic_av_smoke(picture_receipt, av_order, *, source_dir,
                                     output_dir, picture_name, tone_name,
                                     output_name="synthetic_av_check.mkv"):
    """Actual libass subtitle overlay and bit-exact PCM mux, then decode QA."""
    media._trusted_order(av_order)
    fps = av_order["frame_rate_integer_fps"]
    total = av_order["final_total_frames"]
    _need(type(fps) is int and fps in (24,25,30,50,60) and
          SAMPLE_RATE % fps == 0 and type(total) is int and
          1 <= total <= MAX_FRAMES and
          len(av_order["segments"]) >= 2 and
          all(s["kind"] == "story_shot_unrendered"
              for s in av_order["segments"]),
          "AV_SMOKE_SHORT_SYNTHETIC_PICTURE_ONLY")
    _need(isinstance(picture_receipt, dict) and
          picture_receipt.get("kind") == "unpublishable_synthetic_picture_smoke_receipt" and
          picture_receipt.get("only_hard_cuts_tested") is True and
          picture_receipt.get("render_or_publish_authorized") is False and
          picture_receipt.get("frames_decoded_verified") == total and
          picture_receipt.get("frame_rate") == fps,
          "AV_SMOKE_PICTURE_PROOF_REQUIRED")
    _need(not any(c["edit_type_exact"] != "hard_cut"
                  for c in av_order["montage_cut_jobs"]),
          "AV_SMOKE_NONHARDCUT_NOT_IMPLEMENTED")
    _need(av_order["render_or_publish_authorized"] is False,
          "AV_SMOKE_PUBLICATION_GATE")
    speech = _intervals(av_order["speech_events"], total, "AUDIO")
    _intervals(av_order["subtitle_events"], total, "SUBTITLE")
    srt = media.export_subtitle_srt_plan(av_order)
    _need(srt["subtitle_count"] == len(av_order["subtitle_events"])
          and srt["render_or_publish_authorized"] is False,
          "AV_SMOKE_SRT_UNTRUSTED")
    source = Path(source_dir).resolve(strict=True)
    target = Path(output_dir).resolve(strict=True)
    _need(source.is_dir() and target.is_dir() and source != target and
          not target.is_symlink(),
          "AV_SMOKE_OUTPUT_DIR_UNSAFE")
    picture = _path(source, picture_name)
    tone = _path(source, tone_name)
    _need(_hash(picture) == picture_receipt["output_sha256"],
          "AV_SMOKE_PICTURE_CHANGED")
    _need(media._probe(picture, fps, _hash(picture))["frame_count"] == total,
          "AV_SMOKE_PICTURE_FRAMES_CHANGED")
    length = total * (SAMPLE_RATE // fps)
    raw_pcm = _pcm(tone, length)
    _verify_tone_envelope(raw_pcm, speech, fps)
    _need(isinstance(output_name, str) and
          SAFE_NAME.fullmatch(output_name) and output_name.endswith(".mkv"),
          "AV_SMOKE_OUTPUT_FILENAME_INVALID")
    output = target / output_name
    captions_path = target / "synthetic_cue_overlay.srt"
    _need(not output.exists() and not captions_path.exists(),
          "AV_SMOKE_REFUSE_OVERWRITE")
    _need(bool(SAFE_FILTER_PATH.fullmatch(str(captions_path))),
          "AV_SMOKE_FILTER_PATH_UNSAFE")
    captions_path.write_text(srt["srt_text"], encoding="utf-8")
    filter_spec = (
        "subtitles=filename="+str(captions_path)+
        ":force_style='FontName=DejaVu Sans,Fontsize=24,"
        "PrimaryColour=&H00FFFFFF,Outline=2,MarginV=20,Alignment=2'")
    try:
        job = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-i", str(picture), "-i", str(tone),
            "-vf", filter_spec, "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "mpeg4", "-q:v", "2", "-c:a", "pcm_s16le",
            "-pix_fmt", "yuv420p", "-metadata",
            "comment=UNPUBLISHABLE_PUBLIC_SYNTHETIC_AV_QA",
            "-f", "matroska", str(output)
        ], capture_output=True, check=False, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        raise AVSmokeError("AV_SMOKE_FFMPEG_UNAVAILABLE_OR_TIMEOUT") from None
    _need(job.returncode == 0 and output.is_file(),
          "AV_SMOKE_FFMPEG_MUX_OR_SUBTITLE_FAILED")
    probe = media._probe(output, fps, _hash(output))
    _need(probe["frame_count"] == total, "AV_SMOKE_OUTPUT_VIDEO_FRAME_DRIFT")
    try:
        audio = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-i", str(output), "-map", "0:a:0", "-ac", "1", "-ar",
            str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-f", "s16le", "-"
        ], capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        raise AVSmokeError("AV_SMOKE_AUDIO_DECODE_UNAVAILABLE") from None
    _need(audio.returncode == 0 and len(audio.stdout) == len(raw_pcm),
          "AV_SMOKE_DECODED_AUDIO_DURATION_CHANGED")
    _need(audio.stdout == raw_pcm, "AV_SMOKE_DECODED_AUDIO_SAMPLE_DRIFT")
    return {
        "kind": "public_synthetic_av_composite_not_a_film",
        "version": VERSION,
        "frames_picture_verified": total,
        "fps": fps,
        "pcm_samples_verified": length,
        "audio_cue_windows_verified": len(speech),
        "subtitle_cue_windows_scheduled": len(av_order["subtitle_events"]),
        "subtitle_overlay_filter_executed": True,
        "sample_exact_audio_roundtrip_verified": True,
        "output_sha256": _hash(output),
        "local_synthetic_preview_uri": output.as_uri(),
        "subtitle_pixel_content_verified": False,
        "real_speech_or_lip_sync_verified": False,
        "nle_gui_import_verified": False,
        "real_media_production_verified": False,
        "render_or_publish_authorized": False,
    }
