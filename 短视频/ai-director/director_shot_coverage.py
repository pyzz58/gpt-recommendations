#!/usr/bin/env python3
"""QO-D02: director-owned scene/beat -> shot coverage, not one beat = one shot.

Repartitions the *reviewed production screenplay* into a director's shots.
This is a shot COVERAGE blueprint, not generated footage or a new screenplay.
No new/remixed dialogue, no changed fact, runtime or source beat; individual
dialogue-bearing beats cannot be split without future explicit speech-cue
authorization. All output stays in-memory and no API invocation occurs.
"""
from __future__ import annotations

from copy import deepcopy
import math
import json

import agent_team
import director
import director_speech_cues as speech
import screenplay_series_delivery as series

VERSION = "director-shot-coverage-v1"
EPS = 1e-6
DIRECTION = (
    "dramatic_purpose", "observable_screen_event",
    "viewer_before", "viewer_after", "why_this_coverage",
    "performance_blocking", "framing_and_space", "sound_and_silence",
    "cut_hold_intention", "ai_fallback",
)
SPAN = ("beat_id", "from_s", "to_s")
SHOT = ("shot_id", "source_spans", *DIRECTION)
PLAN = ("version", "source_screenplay_digest", "writer_dossier_digest",
        "director_breakdown_digest", "episode_id", "director_coverage_thesis",
        "shots")
PLAN_CUED = (*PLAN, "speech_cue_timeline")


class ShotCoverageError(ValueError):
    """Safe failure codes without user manuscript content."""


def _need(ok, code):
    if not ok:
        raise ShotCoverageError(code)


def _text(s, code, min_len=16):
    _need(isinstance(s, str) and min_len <= len(s.strip()) <= 1600
          and "\0" not in s, code)


def _shape(o, fields, code):
    _need(isinstance(o, dict) and set(o) == set(fields), code)


def _source_context(handoff, dossier, breakdown, episode_id):
    proof = series.validate_breakdown(handoff, dossier, breakdown)
    episode = next((e for e in breakdown["episodes"]
                    if e["episode_id"] == episode_id), None)
    _need(episode is not None, "COVERAGE_UNKNOWN_EPISODE")
    by_beat = {beat["id"]: (scene["id"], beat)
               for scene in handoff["screenplay_scenes"]
               for beat in scene["beats"]}
    originals = {shot["source_adaptation"]["beat_id"]: shot
                 for shot in handoff["reconstructed_base"]["shots"]}
    _need(set(episode["beat_ids"]) <= set(originals),
          "COVERAGE_SOURCE_NOT_IN_AUTHORITATIVE_BASE")
    return proof, episode, by_beat, originals


def request(handoff, dossier, breakdown, episode_id):
    """UNSENT prompt to the SAME showrunner before detailed specialist work."""
    proof, ep, by_beat, original = _source_context(
        handoff, dossier, breakdown, episode_id)
    localized = []
    for scene in dossier["scenes"]:
        relevant = [row for row in scene["beats"]
                    if row["beat_id"] in ep["beat_ids"]]
        if relevant:
            row = deepcopy(scene)
            row["beats"] = relevant
            localized.append(row)
    return {
        "kind": "unsent_professional_director_shot_coverage",
        "version": VERSION, "dispatch_allowed": False,
        "messages": [
            {"role": "system", "content": (
                "你是电影总导演，不是把每个编剧beat自动变成一个镜头的分句器。"
                "真正根据表演/摄影/声画/剪辑的观众体验，决定一场多镜、"
                "同一节拍的反打与插入，或相邻节拍合并到同一有意义镜头。"
                "你必须完整读审过的制作剧本、编剧逐场说明和本集分集结构。"
                "每个制作版beat都要在时间轴上连续恰好覆盖；"
                "任何beat被拆镜，所有source_spans的时间必须无缝覆盖原节拍。"
                "有原剧本对白或旁白的节拍不得切碎其文字或随意改写。"
                "仅在已有逐句声音与字幕时间码并能逐项匹配原剧本时，"
                "可选交付speech_cue_timeline，让声音跨视觉镜头保持一次播放。"
                "没有精确逐句时码就保持完整，不得仅按字数估算后假称已核准。"
                "真实口型与字幕逐帧校验必须留给后续实际媒体验收。"
                "保留所有权威事实、角色、台词、旁白及论证前后关系；"
                "如果需要改剧情，提出编剧返修而非在coverage中偷改。"
                "每个镜头讲清可见动作、人物调度、画面和声音重心、"
                "观众认识变化及切点原因；不能只写“电影级运镜”。"
                "在剪辑覆盖中，空镜与反打必须承担信息或情绪功能。"
                "此步骤是导演的制作镜头规划，不代表已有素材或作者批准，"
                "不调用模型、不申请费用，每集最终含全部额外时间<=90秒。")},
            {"role": "user", "content": json.dumps({
                "complete_screenplay": handoff["screenplay_fountain"],
                "current_episode": ep,
                "localized_writer_dossier": localized,
                "approved_script_beats": [{
                    "beat_id": bid,
                    "scene_id": by_beat[bid][0],
                    "duration_s": by_beat[bid][1]["duration_s"],
                    "dialogue": by_beat[bid][1]["dialogue"],
                    "voiceover": by_beat[bid][1]["voiceover"],
                    "source_adaptation": original[bid]["source_adaptation"],
                } for bid in ep["beat_ids"]],
                "required_plan_fields": PLAN,
                "optional_extended_plan_fields": PLAN_CUED,
                "optional_speech_cue_contract": {
                    "version": speech.VERSION,
                    "plan_fields": sorted(speech.PLAN_FIELDS),
                    "audio_cue_fields": sorted(speech.CUE_FIELDS),
                    "subtitle_cue_fields": sorted(speech.SUB_FIELDS),
                    "must_use_exact_approved_source_words": True,
                    "timing_must_not_be_invented": True,
                    "actual_media_sync_not_verified": True,
                },
                "required_shot_fields": SHOT,
                "required_span_fields": SPAN,
                "provenance": {
                    "source_screenplay_digest": proof["screenplay_digest"],
                    "writer_dossier_digest": proof["writer_dossier_digest"],
                    "director_breakdown_digest": proof["director_breakdown_digest"],
                },
                "episode_id": episode_id,
                "never_auto_change_source_or_author_approval": True,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate(handoff, dossier, breakdown, coverage):
    """Source-preserving structural check; does NOT score cinematic merit."""
    _shape(coverage, PLAN_CUED if "speech_cue_timeline" in coverage else PLAN,
           "COVERAGE_PLAN_SHAPE")
    cue_timeline = coverage.get("speech_cue_timeline")
    proof, ep, by_beat, originals = _source_context(
        handoff, dossier, breakdown, coverage["episode_id"])
    _need(coverage["version"] == VERSION and
          coverage["source_screenplay_digest"] == proof["screenplay_digest"] and
          coverage["writer_dossier_digest"] == proof["writer_dossier_digest"] and
          coverage["director_breakdown_digest"] == proof["director_breakdown_digest"],
          "COVERAGE_STALE_SCRIPT_OR_DIRECTOR")
    _text(coverage["director_coverage_thesis"], "COVERAGE_NO_DIRECTOR_REASON",
          min_len=28)
    shots = coverage["shots"]
    _need(isinstance(shots, list) and 1 <= len(shots) <= 300,
          "COVERAGE_SHOT_COUNT")
    beat_order = ep["beat_ids"]
    order = {bid: i for i, bid in enumerate(beat_order)}
    segments = []
    seen_shots = set()
    runtime = 0.0
    durations = {bid: by_beat[bid][1]["duration_s"] for bid in beat_order}
    splits = {}
    merged = 0
    for idx, row in enumerate(shots, 1):
        _shape(row, SHOT, "COVERAGE_SHOT_SHAPE")
        sid = row["shot_id"]
        _need(sid == "S%02d" % idx and sid not in seen_shots,
              "COVERAGE_SHOT_ORDER_OR_DUPLICATE")
        seen_shots.add(sid)
        for k in DIRECTION:
            _text(row[k], "COVERAGE_UNEXPLAINED_FILM_LANGUAGE")
        _need(row["viewer_before"].strip() != row["viewer_after"].strip(),
              "COVERAGE_NO_AUDIENCE_CHANGE")
        spans = row["source_spans"]
        _need(isinstance(spans, list) and spans and len(spans) <= len(beat_order),
              "COVERAGE_SHOT_SOURCE_SPANS")
        local_scene = None
        last_index = None
        for sp in spans:
            _shape(sp, SPAN, "COVERAGE_SPAN_SHAPE")
            bid = sp["beat_id"]
            _need(bid in order, "COVERAGE_UNKNOWN_SOURCE_BEAT")
            a, b = sp["from_s"], sp["to_s"]
            _need(type(a) in (int, float) and type(b) in (int, float)
                  and math.isfinite(a) and math.isfinite(b) and
                  0 <= a < b <= durations[bid] + EPS,
                  "COVERAGE_SOURCE_SPAN_INVALID")
            scene_id = by_beat[bid][0]
            _need(local_scene is None or local_scene == scene_id,
                  "COVERAGE_MULTIPLE_SCENES_IN_ONE_PHYSICAL_SHOT")
            local_scene = scene_id
            current = order[bid]
            _need(last_index is None or current == last_index + 1,
                  "COVERAGE_NONADJACENT_BEAT_MERGE")
            last_index = current
            segments.append((bid, a, b))
            runtime += b - a
        if len(spans) > 1:
            merged += 1

    _need(segments, "COVERAGE_NO_BEATS")
    # Splitting a spoken beat would otherwise assign full dialogue to one
    # generated shot with invented timing. Refuse until cue-aware editor exists.
    for bid in beat_order:
        parts = [(a, b) for key, a, b in segments if key == bid]
        _need(bool(parts), "COVERAGE_MISSING_BEAT")
        pos = 0.0
        for a, b in parts:
            _need(abs(a-pos) <= EPS, "COVERAGE_BEAT_GAP_OVERLAP_OR_REORDER")
            pos = b
        _need(abs(pos - durations[bid]) <= EPS,
              "COVERAGE_BEAT_NOT_FULLY_COVERED")
        splits[bid] = len(parts)
        beat = by_beat[bid][1]
        if len(parts) > 1 and cue_timeline is None:
            _need(not beat["dialogue"] and not beat["voiceover"] and
                  not originals[bid]["narration"] and
                  not originals[bid]["subtitles"]["text"],
                  "COVERAGE_CANNOT_SPLIT_UNTIMED_SPEECH_OR_CAPTIONS")
    compressed = []
    for bid, a, b in segments:
        if not compressed or compressed[-1] != bid:
            compressed.append(bid)
    _need(compressed == beat_order,
          "COVERAGE_BEATS_MISSING_DUPLICATED_OR_REORDERED")
    expected_story_s = sum(durations.values())
    _need(abs(runtime - expected_story_s) <= EPS,
          "COVERAGE_RUNTIME_DRIFT")
    _need(abs(runtime - proof["episodes"][
        [e["episode_id"] for e in proof["episodes"]].index(ep["episode_id"])
    ]["story_s"]) <= EPS, "COVERAGE_EPISODE_STORY_RUNTIME_DRIFT")
    cue_receipt = (speech.validate(handoff, breakdown, ep, proof, cue_timeline)
                   if cue_timeline is not None else None)
    if cue_receipt is not None:
        # A cue may outlive its original speaking shot; both picture cuts
        # and the source speech/subtitle timeline remain authoritative.
        speech.first_visual_owner(coverage, cue_timeline["cues"], "cue_id")
        speech.first_visual_owner(coverage, cue_timeline["subtitles"], "subtitle_id")
    return {
        "kind": "director_new_shot_coverage_receipt",
        "episode_id": ep["episode_id"],
        "source_screenplay_digest": proof["screenplay_digest"],
        "breakdown_digest": proof["director_breakdown_digest"],
        "coverage_digest": agent_team.fingerprint(coverage),
        "original_script_beat_count": len(beat_order),
        "director_shot_count": len(shots),
        "shot_merge_count": merged,
        "split_beats": [bid for bid, count in splits.items() if count > 1],
        "source_beats_exactly_covered": True,
        "speech_cue_receipt": cue_receipt,
        "runtime_s": runtime,
        "author_approval_authenticated": False,
        "real_cinematic_quality_verified": False,
        "media_generated": False,
    }


def reblock_episode(handoff, dossier, breakdown, packet, coverage):
    """Rebuild a planning-only EPISODE base using director-chosen shot layout.

    Runs original 10-role ledger anew: no stale camera/sound/actor deliverables
    can silently survive a change in the basic shot grammar.
    """
    proof = validate(handoff, dossier, breakdown, coverage)
    expected = series.build_per_episode_crew(handoff, dossier, breakdown)
    _need(isinstance(packet, dict) and
          agent_team.fingerprint(packet) == agent_team.fingerprint(expected),
          "COVERAGE_EPISODE_PACKET_TAMPERED")
    ep = next(e for e in packet["episodes"]
              if e["episode_id"] == coverage["episode_id"])
    base = deepcopy(ep["authoritative_episode_base"])
    source_shots = {
        shot["source_adaptation"]["beat_id"]: shot
        for shot in base["shots"]
    }
    _need(len(source_shots) == len(base["shots"]),
          "COVERAGE_SOURCE_BEAT_MAPPING_NOT_UNIQUE")
    by_beat = {b["id"]: b for scene in handoff["screenplay_scenes"]
               for b in scene["beats"]}
    output, position = [], 0.0
    cue_timeline = coverage.get("speech_cue_timeline")
    if cue_timeline is not None:
        audio_bindings, caption_bindings = speech.cue_bindings_for_shots(
            coverage, cue_timeline)
        audio_owners = speech.first_visual_owner(
            coverage, cue_timeline["cues"], "cue_id")
        caption_owners = speech.first_visual_owner(
            coverage, cue_timeline["subtitles"], "subtitle_id")
    covered_total = set()
    for row in coverage["shots"]:
        spans = row["source_spans"]
        first = source_shots[spans[0]["beat_id"]]
        shot = deepcopy(first)
        ids = [sp["beat_id"] for sp in spans]
        # The same beat may occupy two consecutive visual shots; its original
        # text may occur only once. Spoken beats are unsplittable above.
        text_owners = []
        for sp in spans:
            bid = sp["beat_id"]
            if bid not in covered_total:
                text_owners.append(bid)
                covered_total.add(bid)
        shot["id"] = row["shot_id"]
        shot["start"] = position
        shot["duration"] = sum(sp["to_s"]-sp["from_s"] for sp in spans)
        position += shot["duration"]
        shot["purpose"] = row["dramatic_purpose"]
        shot["visual"] = row["observable_screen_event"]
        if cue_timeline is None:
            shot["narration"] = "".join(source_shots[bid]["narration"]
                                       for bid in text_owners)
            shot["subtitles"]["text"] = " ".join(
                source_shots[bid]["subtitles"]["text"]
                for bid in text_owners if source_shots[bid]["subtitles"]["text"])
        else:
            shot["narration"] = "".join(
                source_shots[c["beat_id"]]["narration"]
                for c in cue_timeline["cues"]
                if c["source_kind"] in {"narration", "voiceover"} and
                audio_owners[c["cue_id"]] == row["shot_id"])
            shot["subtitles"]["text"] = " ".join(
                c["text_exact"] for c in cue_timeline["subtitles"]
                if caption_owners[c["subtitle_id"]] == row["shot_id"])
            shot["speech_cue_refs"] = audio_bindings[row["shot_id"]]
            shot["subtitle_cue_refs"] = caption_bindings[row["shot_id"]]
            shot["requires_timed_cue_rendering"] = True
        shot["character_ids"] = list(dict.fromkeys(
            cid for bid in ids for cid in source_shots[bid]["character_ids"]))
        shot["claim_ids"] = list(dict.fromkeys(
            cid for bid in ids for cid in source_shots[bid]["claim_ids"]))
        shot["action"]["action"] = row["observable_screen_event"]
        shot["camera"]["movement"] = row["framing_and_space"]
        shot["art"]["lighting"] = "待摄影美术依据导演镜头覆盖图制定具体光源，不表示已试拍"
        shot["audio"]["voice"] = row["sound_and_silence"]
        shot["continuity"] = row["performance_blocking"]
        shot["transition"] = "fade_in" if not output else "hard_cut"
        shot["source_adaptation"] = {
            **deepcopy(first["source_adaptation"]),
            "beat_id": spans[0]["beat_id"],
            "covered_beat_ids": list(dict.fromkeys(ids)),
            "coverage_source_spans": deepcopy(spans),
            "coverage_digest": proof["coverage_digest"],
            "dialogue": ([deepcopy(d) for bid in text_owners
                          for d in by_beat[bid]["dialogue"]]
                         if cue_timeline is None else
                         [deepcopy(by_beat[c["beat_id"]]["dialogue"][c["source_index"]])
                          for c in cue_timeline["cues"]
                          if c["source_kind"] == "dialogue" and
                          audio_owners[c["cue_id"]] == row["shot_id"]]),
            "original_source_shot_ids": list(dict.fromkeys(
                x for bid in ids
                for x in source_shots[bid]["source_adaptation"]
                    ["original_source_shot_ids"])),
        }
        shot["director_shot_craft"] = {field: row[field] for field in DIRECTION}
        output.append(shot)
    base["shots"] = output
    base["duration"] = position
    if cue_timeline is not None:
        base["director_speech_cue_timeline"] = deepcopy(cue_timeline)
        base["director_editor_cue_sheet"] = speech.compile_editor_timeline(
            handoff, next(e for e in breakdown["episodes"]
                          if e["episode_id"] == coverage["episode_id"]),
            series.validate_breakdown(handoff, dossier, breakdown),
            coverage, cue_timeline)
        base["requires_timed_cue_rendering"] = True
    base["editorial"]["narration_script"] = "".join(
        shot["narration"] for shot in output)
    # Source fidelity also covers words which aren't narration (screenplay
    # dialogue is independently retained through source_adaptation).
    original_narration = "".join(shot["narration"]
                                 for shot in ep["authoritative_episode_base"]
                                     ["shots"])
    _need(original_narration == base["editorial"]["narration_script"],
          "COVERAGE_ORIGINAL_NARRATION_DRIFT")
    original_lines = [deepcopy(d)
                      for shot in ep["authoritative_episode_base"]["shots"]
                      for d in shot["source_adaptation"]["dialogue"]]
    new_lines = [deepcopy(d) for shot in output
                 for d in shot["source_adaptation"]["dialogue"]]
    _need(original_lines == new_lines, "COVERAGE_DIALOGUE_DRIFT")
    base["director_shot_coverage_mode"] = {
        "kind": "director_authored_shots_from_screenplay_beats",
        "coverage_digest": proof["coverage_digest"],
        "original_beat_count": proof["original_script_beat_count"],
        "revised_director_shot_count": proof["director_shot_count"],
        "story_rewrite_permitted": False,
        "real_filming_completed": False,
    }
    base["series_context"]["director_shot_coverage_digest"] = proof["coverage_digest"]
    errs, _ = director.validate(base)
    _need(not errs, "COVERAGE_REBLOCKED_EPISODE_SCHEMA_INVALID")
    team = agent_team.start(base, source_text=handoff["screenplay_fountain"])
    output_packet = deepcopy(packet)
    selected = next(e for e in output_packet["episodes"]
                    if e["episode_id"] == coverage["episode_id"])
    selected["authoritative_episode_base"] = base
    selected["crew"] = team
    selected["director_coverage_digest"] = proof["coverage_digest"]
    selected["status"] = "planning_only_not_authorized"
    output_packet["director_coverage_applied"] = {
        "episode_id": coverage["episode_id"],
        "coverage_digest": proof["coverage_digest"],
        "new_shots": [s["id"] for s in output],
        "all_source_dialogue_exact": True,
        "speech_cue_timeline_attached": cue_timeline is not None,
        "lip_sync_verified": False,
        "human_approved": False,
        "media_generated": False,
    }
    return output_packet
