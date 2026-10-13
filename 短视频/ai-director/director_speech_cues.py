#!/usr/bin/env python3
"""QO-D03: independent, source-exact speech and subtitle cue timeline.

No audio is synthesized here. Timing is asserted by the planner, never
inferred from text length. Every cue is bound to the reviewed screenplay.
"""
from __future__ import annotations

import math

import agent_team

VERSION = "director-speech-cues-v1"
EPS = 1e-6
PLAN_FIELDS = {"version", "episode_id", "source_screenplay_digest",
               "director_breakdown_digest", "cues", "subtitles"}
CUE_FIELDS = {"cue_id", "beat_id", "source_kind", "source_index", "speaker",
              "text_exact", "from_s", "to_s", "audio_mode"}
SUB_FIELDS = {"subtitle_id", "beat_id", "text_exact", "from_s", "to_s"}


class SpeechCueError(ValueError):
    """Safe failures contain codes, not confidential screenplay excerpts."""


def _need(condition, code):
    if not condition:
        raise SpeechCueError(code)


def _interval(row, duration):
    a, b = row["from_s"], row["to_s"]
    _need(type(a) in (int, float) and type(b) in (int, float) and
          math.isfinite(a) and math.isfinite(b) and
          0 <= a < b <= duration + EPS, "CUE_INVALID_INTERVAL")


def _expected(episode, beat_index, original_shots):
    audio, captions = [], []
    for beat_id in episode["beat_ids"]:
        beat = beat_index[beat_id]
        original = original_shots[beat_id]
        for idx, utterance in enumerate(beat["dialogue"]):
            audio.append((beat_id, "dialogue", idx,
                          utterance["speaker"], utterance["line"]))
        if beat["voiceover"]:
            audio.append((beat_id, "voiceover", 0, "NARRATOR",
                          beat["voiceover"]))
            _need(original["narration"] == beat["voiceover"],
                  "CUE_SOURCE_VOICEOVER_NARRATION_CONFLICT")
        elif original["narration"]:
            audio.append((beat_id, "narration", 0, "NARRATOR",
                          original["narration"]))
        if original["subtitles"]["text"]:
            captions.append((beat_id, original["subtitles"]["text"]))
    return audio, captions


def validate(handoff, breakdown, episode, proof, timeline):
    """Validate source words, identity, order, durations and cue uniqueness."""
    _need(isinstance(timeline, dict) and set(timeline) == PLAN_FIELDS,
          "CUE_PLAN_SHAPE")
    _need(timeline["version"] == VERSION and
          timeline["episode_id"] == episode["episode_id"] and
          timeline["source_screenplay_digest"] == proof["screenplay_digest"] and
          timeline["director_breakdown_digest"] == proof["director_breakdown_digest"],
          "CUE_STALE_SCRIPT_OR_EPISODE")
    by_beat = {b["id"]: b for scene in handoff["screenplay_scenes"]
               for b in scene["beats"]}
    originals = {s["source_adaptation"]["beat_id"]: s for s in
                 handoff["reconstructed_base"]["shots"]}
    expected_audio, expected_subtitles = _expected(episode, by_beat, originals)
    audio = timeline["cues"]
    subtitles = timeline["subtitles"]
    _need(isinstance(audio, list) and len(audio) == len(expected_audio) and
          isinstance(subtitles, list) and
          len(subtitles) == len(expected_subtitles), "CUE_SOURCE_ITEM_COUNT")
    durations = {b: by_beat[b]["duration_s"] for b in episode["beat_ids"]}
    last_end = {}
    beat_offsets = {}
    cursor = 0.0
    for bid in episode["beat_ids"]:
        beat_offsets[bid] = cursor
        cursor += durations[bid]
    seen = set()
    for i, (cue, original) in enumerate(zip(audio, expected_audio), 1):
        _need(isinstance(cue, dict) and set(cue) == CUE_FIELDS,
              "CUE_ITEM_SHAPE")
        bid, kind, idx, speaker, words = original
        _need(cue["cue_id"] == f"C{i:03d}" and cue["cue_id"] not in seen,
              "CUE_ID_ORDER")
        seen.add(cue["cue_id"])
        _need((cue["beat_id"], cue["source_kind"], cue["source_index"],
               cue["speaker"], cue["text_exact"]) == original,
              "CUE_SOURCE_WORDS_SPEAKER_OR_ORDER_CHANGED")
        mode = cue["audio_mode"]
        _need(mode in {"on_screen", "off_screen", "voiceover"} and
              (kind == "dialogue" or mode == "voiceover"),
              "CUE_AUDIO_MODE_INVALID")
        _interval(cue, durations[bid])
        _need(cue["from_s"] >= last_end.get(bid, 0) - EPS,
              "CUE_OVERLAPPING_OR_REORDERED_AUDIO")
        last_end[bid] = cue["to_s"]
    seen_subs = set()
    for i, (sub, original) in enumerate(zip(subtitles, expected_subtitles), 1):
        _need(isinstance(sub, dict) and set(sub) == SUB_FIELDS,
              "CUE_SUBTITLE_SHAPE")
        _need(sub["subtitle_id"] == f"T{i:03d}" and
              sub["subtitle_id"] not in seen_subs,
              "CUE_SUBTITLE_ID_ORDER")
        seen_subs.add(sub["subtitle_id"])
        _need((sub["beat_id"], sub["text_exact"]) == original,
              "CUE_SUBTITLE_TEXT_OR_ORDER_CHANGED")
        _interval(sub, durations[sub["beat_id"]])
    return {
        "kind": "director_source_exact_speech_timeline_receipt",
        "timeline_digest": agent_team.fingerprint(timeline),
        "speech_cue_count": len(audio),
        "subtitle_cue_count": len(subtitles),
        "source_text_exact": True,
        "timing_is_planner_asserted_not_media_verified": True,
        "lip_sync_verified": False,
        "media_generated": False,
    }


def cue_bindings_for_shots(coverage, timeline):
    """Map ONE authoritative sound/caption timeline to visual shot spans.

    Cross-shot audio is referenced with source-relative times. Source words are
    never duplicated in per-shot binding references.
    """
    def bindings(events, id_key):
        result = {}
        for shot in coverage["shots"]:
            connected = []
            for span in shot["source_spans"]:
                for event in events:
                    if event["beat_id"] != span["beat_id"]:
                        continue
                    a = max(span["from_s"], event["from_s"])
                    b = min(span["to_s"], event["to_s"])
                    if b > a + EPS:
                        connected.append({
                            "id": event[id_key], "beat_id": event["beat_id"],
                            "from_s": a, "to_s": b,
                        })
            result[shot["shot_id"]] = connected
        return result
    return (bindings(timeline["cues"], "cue_id"),
            bindings(timeline["subtitles"], "subtitle_id"))


def first_visual_owner(coverage, events, id_key):
    """A cue's exact start belongs to one shot; cross-shot tails use refs."""
    owned = {}
    for event in events:
        matched = [shot["shot_id"] for shot in coverage["shots"]
                   for span in shot["source_spans"]
                   if span["beat_id"] == event["beat_id"] and
                   span["from_s"] - EPS <= event["from_s"] <
                   span["to_s"] - EPS]
        _need(len(matched) == 1, "CUE_NO_UNIQUE_VISUAL_OWNER")
        owned[event[id_key]] = matched[0]
    return owned
