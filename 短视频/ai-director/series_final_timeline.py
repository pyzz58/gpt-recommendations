#!/usr/bin/env python3
"""Real postproduction episode budget: story + optional intro/recap/bridge/outro/card.

The authoritative story shots remain unchanged and keep their relative
timestamps. This emits an explicit ABSOLUTE editor timeline including each
reserved extra. It does not claim extras have been rendered. Sources and
versions are never silently rewritten.
"""
from __future__ import annotations

import math

from closing_evidence_card import DURATION_S

VERSION = "series-final-editor-timeline-v1"
EXTRAS = ("intro_s", "recap_s", "bridge_s", "outro_s", "evidence_s")
LIMIT = 90.0
EPS = 0.0001


class SeriesTimelineError(ValueError):
    """Privacy-safe and stable failure code."""


def _need(ok, code):
    if not ok:
        raise SeriesTimelineError(code)


def _seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def compile_final_timeline(base, evidence_card):
    """Validate the FULL duration at operator-bundle creation (no model calls).

    Return None only for truly legacy/non-series plans; an episode with a
    series_context cannot escape full-story/extras/credits checking.
    """
    series = base.get("series_context")
    if series is None:
        return None
    _need(isinstance(series, dict) and
          series.get("kind") == "director_episode_from_complete_screenplay" and
          series.get("max_total_duration_s") == LIMIT,
          "SERIES_FINAL_CONTEXT_UNTRUSTED")
    extra = series.get("reserved_extra_components_s")
    _need(isinstance(extra, dict) and set(extra) == set(EXTRAS) and
          all(_seconds(x) for x in extra.values()),
          "SERIES_FINAL_EXTRA_COMPONENTS_REQUIRED")
    story = base.get("duration")
    planned_story = series.get("episode_story_s")
    reserved = series.get("reserved_additional_s")
    planned_total = series.get("episode_total_planned_s")
    _need(_seconds(story) and _seconds(planned_story) and
          abs(story - planned_story) <= EPS,
          "SERIES_FINAL_STORY_DURATION_DRIFT")
    _need(_seconds(reserved) and
          abs(sum(extra.values()) - reserved) <= EPS,
          "SERIES_FINAL_EXTRAS_BUDGET_DRIFT")
    total = story + sum(extra.values())
    _need(_seconds(planned_total) and
          abs(total - planned_total) <= EPS,
          "SERIES_FINAL_PLANNED_RUNTIME_DRIFT")
    _need(total <= LIMIT + EPS, "SERIES_FINAL_OVER_90_SECONDS")

    card_requested = extra["evidence_s"] > 0
    _need(series.get("include_final_evidence_card") is card_requested,
          "SERIES_FINAL_CREDITS_DECISION_CHANGED")
    _need((evidence_card is not None) == card_requested,
          "SERIES_FINAL_CREDITS_MISSING_OR_UNRESERVED")
    if card_requested:
        _need(type(evidence_card.get("duration_s")) in (int, float) and
              abs(evidence_card["duration_s"] - DURATION_S) <= EPS and
              abs(extra["evidence_s"] - DURATION_S) <= EPS,
              "SERIES_FINAL_CREDITS_RUNTIME_MISMATCH")
    segments = []
    t = 0.0

    def append(name, duration, kind, *, shot_id=None):
        nonlocal t
        if duration <= EPS:
            return
        data = {
            "kind": kind, "editor_segment_id": name,
            "start_s": round(t, 4),
            "end_s": round(t + duration, 4),
            "duration_s": round(duration, 4),
            "real_media_available": False,
        }
        if shot_id is not None:
            data["source_shot_id"] = shot_id
        segments.append(data)
        t += duration

    for key in ("intro_s", "recap_s"):
        append(key, extra[key], "reserved_postproduction")
    shots = base.get("shots")
    _need(isinstance(shots, list) and shots,
          "SERIES_FINAL_STORY_SHOTS_MISSING")
    original_clock = 0.0
    for i, shot in enumerate(shots):
        _need(isinstance(shot, dict) and
              _seconds(shot.get("start")) and
              abs(shot["start"] - original_clock) <= EPS and
              type(shot.get("duration")) in (int, float) and
              math.isfinite(shot["duration"]) and shot["duration"] > 0 and
              isinstance(shot.get("id"), str) and shot["id"],
              "SERIES_FINAL_RELATIVE_SHOT_TIME_INVALID")
        append(f"story_{i+1:02d}", shot["duration"],
               "story_shot_unrendered", shot_id=shot["id"])
        original_clock += shot["duration"]
    _need(abs(original_clock - story) <= EPS,
          "SERIES_FINAL_STORY_SHOT_DURATION_MISMATCH")
    for key in ("bridge_s", "outro_s"):
        append(key, extra[key], "reserved_postproduction")
    if card_requested:
        append("POST_END_CREDITS", evidence_card["duration_s"],
               "final_evidence_postproduction")
    _need(abs(t - planned_total) <= EPS and t <= LIMIT + EPS,
          "SERIES_FINAL_ACTUAL_TIMELINE_OVER_90")
    _need(all(abs(a["end_s"] - b["start_s"]) <= EPS
              for a, b in zip(segments, segments[1:])),
          "SERIES_FINAL_TIMELINE_GAP_OR_OVERLAP")
    _need(not segments or
          segments[-1]["kind"] != "final_evidence_postproduction" or
          segments[-1]["end_s"] <= LIMIT + EPS,
          "SERIES_FINAL_EVIDENCE_MUST_BE_LAST")
    return {
        "kind": "unrendered_but_absolute_series_editor_timeline",
        "version": VERSION,
        "episode_id": series.get("episode_id"),
        "story_duration_s": story,
        "reserved_components_s": dict(extra),
        "planned_final_duration_s": round(t, 4),
        "absolute_segments": segments,
        "last_card_is_final_segment": (
            not card_requested or
            segments[-1]["kind"] == "final_evidence_postproduction"),
        "all_extra_media_still_unrendered": True,
        "actual_final_media_verified": False,
        "fits_90_second_budget": True,
    }
