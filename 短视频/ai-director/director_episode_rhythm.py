#!/usr/bin/env python3
"""QO-D03/D09: source-bound director episode attention, rhythm and sonic arc.

Not a second editor, renderer, director or generic shot-duration scorecard.
Reuses QO-D03 authored audiovisual shot meaning, the immutable team/episode
timeline, and actual SOUND/EDIT submitted designs for post-specialist review.
One artistic decision per source shot and one A/B choice per REAL adjacent cut.
Proposed trim/extend/move is a QO-D12 request, not a silent edit or OTIO write.
No runtime tests, model calls, media review, author assent or production rights.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

import agent_team as team
import director_department_command as commands
import director_visual_language as vision
import director_revision_lineage as lineage

VERSION = "director-episode-rhythm-and-sonic-arc-v1"
PHASES = frozenset({"before_specialists", "after_sound_and_edit_design"})
TYPES = frozenset({
    "information_arrives", "performance_or_observation",
    "emotional_delay", "visual_or_acoustic_revelation", "earned_silence",
})
OPTIONS = frozenset({
    "hard_cut", "match_action", "match_gaze", "graphic_match",
    "sound_led_cut", "j_cut_candidate", "l_cut_candidate",
    "held_cut", "motivated_jump",
})
RESULTS = frozenset({
    "keep_as_directed", "director_redesign_required",
    "specialist_revision_required", "screenwriter_change_required",
    "defer_until_real_media",
})
OWNER = frozenset({
    "none", "director_lock", "sound", "editing_animation", "screenwriter",
})
REVISIONS = {
    "director_lock": "director_whole_film_vision",
    "sound": "voice_or_sound_design",
    "editing_animation": "editing_or_animation",
}
BEAT = (
    "beat_id", "from_s", "to_s", "purpose", "action_or_visible_change",
    "what_viewer_learns_or_feels", "sound_silence_or_music",
    "why_this_time_is_necessary",
)
SHOT = (
    "shot_id", "source_start_s", "source_duration_s", "source_end_s",
    "visual_vision_exact_excerpt", "viewer_arrives_with",
    "viewer_leaves_with", "performance_and_attention_strategy",
    "motif_or_image_evolution", "sonic_curve_inside_shot",
    "timecoded_attention_beats", "rejected_generic_edit",
    "why_shorter_or_longer_is_not_automatically_better",
    "proposed_deviation_from_locked_runtime", "decision", "owner",
    "exact_revision_instruction", "how_real_audience_media_would_refute",
)
OPTION = (
    "technique", "what_eye_hears_and_sees", "viewer_advantage",
    "emotional_or_information_cost", "media_or_sound_dependency",
)
SEAM = (
    "from_shot_id", "to_shot_id", "locked_boundary_s",
    "attention_state_out", "attention_state_in",
    "critical_action_and_information_at_cut",
    "outgoing_visual_quote", "incoming_visual_quote",
    "real_sound_or_edit_quotes", "alternative_a", "alternative_b",
    "directors_preferred_alternative", "reason_for_choice",
    "music_silence_dialogue_handoff", "orientation_and_motif_connection",
    "cut_handle_or_media_uncertainty",
    "decision", "owner", "exact_revision_instruction",
    "human_media_review_condition",
)
QUOTE = ("department", "shot_id", "exact_excerpt")
LIMITS = {
    "locked_screenplay_retimed": False,
    "rendered_media_reviewed": False,
    "real_audio_waveform_or_lip_sync_verified": False,
    "editorial_software_or_OTIO_export_verified": False,
    "artistic_quality_human_approved": False,
    "external_model_or_paid_edit_authorized": False,
    "publication_authorized": False,
}


class RhythmError(ValueError):
    """Code-only errors must never expose original text/character names."""


def _need(v, code):
    if not v:
        raise RhythmError(code)


def _shape(v, fields, code):
    _need(type(v) is dict and set(v) == set(fields), code)


def _text(v, code, minlen=20, maxlen=2800):
    _need(isinstance(v, str) and
          minlen <= len(v.strip()) <= maxlen and "\0" not in v, code)


def _number(v):
    return type(v) in (int, float) and math.isfinite(v)


def _literal_contains(value, text):
    """Quote AUTHORED values only, never field names / JSON syntax."""
    if isinstance(value, str):
        return text in value
    if isinstance(value, list):
        return any(_literal_contains(a, text) for a in value)
    if isinstance(value, dict):
        return any(_literal_contains(v, text) for v in value.values())
    return False


def _role_shot(state, dept, sid):
    _need(dept in ("sound", "editing_animation"),
          "RHYTHM_WRONG_CREW_ROLE")
    task = state["tasks"][dept]
    _need(task["status"] == "completed" and
          isinstance(task["deliverable"], dict) and
          isinstance(task["deliverable"].get("shots"), dict) and
          isinstance(task["deliverable"]["shots"].get(sid), dict),
          "RHYTHM_ACTUAL_SOUND_OR_EDIT_DELIVERY_REQUIRED")
    return task["deliverable"]["shots"][sid]


def _snapshot(base, state, meeting, audiovisual, phase, *,
              artistic_method_plan=None):
    _need(phase in PHASES, "RHYTHM_UNKNOWN_PHASE")
    m = commands.validate_command(base, state, meeting)
    v = vision.validate(
        base, state, meeting, audiovisual,
        artistic_method_plan=artistic_method_plan)
    shots = base["shots"]
    _need([x["id"] for x in shots] == state["shot_ids"],
          "RHYTHM_SOURCE_SHOT_ORDER_CHANGED")
    _need(_number(base["duration"]) and 0 < base["duration"] <= 90,
          "RHYTHM_EPISODE_DURATION_OVER_90S")
    for shot in shots:
        _need(_number(shot.get("start")) and
              _number(shot.get("duration")) and shot["duration"] > 0 and
              0 <= shot["start"] and
              shot["start"] + shot["duration"] <= base["duration"] + 0.0001,
              "RHYTHM_INVALID_ABSOLUTE_SHOT_BUDGET")
    for left, right in zip(shots, shots[1:]):
        _need(left["start"] < right["start"] and
              abs(left["start"] + left["duration"] - right["start"]) < 0.011,
              "RHYTHM_SOURCE_SHOTS_NOT_CONTIGUOUS")
    crews = {}
    if phase == "after_sound_and_edit_design":
        for dept in ("sound", "editing_animation"):
            t = state["tasks"][dept]
            _need(t["status"] == "completed",
                  "RHYTHM_WAIT_FOR_ACTUAL_SOUND_EDIT")
            for sid in state["shot_ids"]:
                _role_shot(state, dept, sid)
            crews[dept] = {
                "revision": t["revision"],
                "deliverable_digest": team.fingerprint(t["deliverable"]),
            }
    return {
        "phase": phase,
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "director_lock_digest": m["director_lock_digest"],
        "meeting_digest": m["command_digest"],
        "visual_language_digest": v["plan_digest"],
        "artistic_methods_digest": v["artistic_methods_digest"],
        "shot_ids": list(state["shot_ids"]),
        "fixed_total_episode_duration_s": base["duration"],
        "real_sound_edit_deliveries": crews,
    }


def request(base, state, meeting, audiovisual, *,
            phase="before_specialists", artistic_method_plan=None):
    """UNSENT prompt for the same director's one-film time/attention choices."""
    snap = _snapshot(
        base, state, meeting, audiovisual, phase,
        artistic_method_plan=artistic_method_plan)
    real_crew = (
        {dept: deepcopy(state["tasks"][dept]["deliverable"]["shots"])
         for dept in ("sound", "editing_animation")}
        if phase == "after_sound_and_edit_design" else None)
    return {
        "kind": "unsent_one_director_episode_attention_and_editing_arc",
        "version": VERSION,
        "dispatch_allowed": False,
        "film_seen": False,
        "messages": [
            {"role": "system", "content": (
                "你仍是这部影片的唯一总导演。以整体人物、思想和观众的"
                "认知节奏为先，不要套用短视频每三秒切一次的公式。"
                "逐镜写清这一秒观众为什么该看/听该信息、镜头中哪些"
                "表演与沉默让决定被理解、声音如何在画面之前或之后"
                "产生意义、母题如何从开头到结尾变化。"
                "每镜把原来已经锁定的绝对秒数划为1至6段，无缝"
                "覆盖，不扩大或偷偷削掉剧本时长；段落每一秒都有"
                "具体可见的事件/注意力转移，不能用慢动作泛化填充。"
                "每个真实剪口只作一次总导演裁决，但要给两套不同"
                "声画切法及其观众收益/代价。J/L-cut只有当真实音轨"
                "与编辑把柄存在时才可能制作；没有不能虚构成功。"
                "已提交专业设计时必须引用声音与剪辑的实际原句"
                "论证选择，不要用结构字段名冒充证据。"
                "不要让结尾总结抢走最后一个角色抉择的情绪重量；"
                "同时必须保留片头片尾预算、90秒绝对上限以及"
                "仅按源剧本要求最后出现的约1.8秒证据名单式尾页。"
                "来源页存在时只可位于最终片尾，不在本模块直接"
                "改动其时间/文字。小说、纪录、论述、荒诞喜剧应"
                "根据人物/事实/反预期节奏自主决定长停顿或突切，"
                "不能强迫一个统一情绪波形。"
                "需要删减、延长、换镜顺序或者改台词/事件只能"
                "提出未派发的定点修改，返回总导演或编剧权威，"
                "不能改原计划/演员动作/事实。"
                "对每种方案说明观众会失去什么，不准伪造"
                "已试听声波、看片、真人盲评、付费或发布权。")},
            {"role": "user", "content": json.dumps({
                "source_locked_snapshot_copy_exact": snap,
                "authoritative_episode_shots_and_runtime": base["shots"],
                "directors_existing_visual_sound_language": audiovisual,
                "actual_submitted_sound_and_edit_shot_designs": real_crew,
                "whole_episode_review_fields": [
                    "version", "snapshot", "opening_attention_contract",
                    "audience_information_and_emotion_arc",
                    "silence_music_dialogue_global_arc",
                    "motif_reprise_and_ending_payoff", "rejected_generic_pacing",
                    "shots", "seams", "limitations"],
                "shot_fields": list(SHOT),
                "attention_beat_fields": list(BEAT),
                "attention_beat_purposes": sorted(TYPES),
                "seam_fields": list(SEAM),
                "seam_cut_fields": list(OPTION),
                "actual_quote_fields": list(QUOTE),
                "edit_candidates": sorted(OPTIONS),
                "review_decisions": sorted(RESULTS),
                "per_shot_max_attention_beats": 6,
                "no_retiming_or_editorial_overrides": LIMITS,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def _decision(decision, owner, proposed, code):
    _need(isinstance(decision, str) and decision in RESULTS and
          isinstance(owner, str) and owner in OWNER,
          code)
    correct = {
        "keep_as_directed": "none",
        "director_redesign_required": "director_lock",
        "screenwriter_change_required": "screenwriter",
        "defer_until_real_media": "none",
    }
    if decision in correct:
        _need(owner == correct[decision], code)
    if decision == "specialist_revision_required":
        _need(owner in ("sound", "editing_animation"), code)
    if decision in ("director_redesign_required",
                    "specialist_revision_required",
                    "screenwriter_change_required"):
        _text(proposed, "RHYTHM_REQUIRED_REWORK_INSTRUCTION")
    else:
        _need(proposed == "", "RHYTHM_FALSE_PREAPPROVED_REWORK")


def validate(base, state, meeting, audiovisual, rhythm, *,
             artistic_method_plan=None):
    """Validate sourced decisions and temporal conservation, not film beauty."""
    _shape(rhythm, (
        "version", "snapshot", "opening_attention_contract",
        "audience_information_and_emotion_arc",
        "silence_music_dialogue_global_arc",
        "motif_reprise_and_ending_payoff", "rejected_generic_pacing",
        "shots", "seams", "limitations"), "RHYTHM_PLAN_SHAPE")
    phase = rhythm["snapshot"].get("phase") if isinstance(
        rhythm.get("snapshot"), dict) else None
    snap = _snapshot(
        base, state, meeting, audiovisual, phase,
        artistic_method_plan=artistic_method_plan)
    _need(rhythm["version"] == VERSION and rhythm["snapshot"] == snap,
          "RHYTHM_SOURCE_DIRECTOR_OR_CREW_VERSION_STALE")
    _need(rhythm["limitations"] == LIMITS,
          "RHYTHM_FAKE_MEDIA_OR_EDITORIAL_AUTHORITY")
    for k in (
        "opening_attention_contract",
        "audience_information_and_emotion_arc",
        "silence_music_dialogue_global_arc",
        "motif_reprise_and_ending_payoff",
        "rejected_generic_pacing",
    ):
        _text(rhythm[k], "RHYTHM_UNSPECIFIED_WHOLE_EPISODE_JUDGMENT",
              minlen=45)
    physical = {row["id"]: row for row in base["shots"]}
    visual = {row["shot_id"]: row for row in audiovisual["shots"]}
    plans = rhythm["shots"]
    _need(isinstance(plans, list) and len(plans) == len(state["shot_ids"]),
          "RHYTHM_INCOMPLETE_SHOT_COVERAGE")
    for sid, row in zip(state["shot_ids"], plans):
        _shape(row, SHOT, "RHYTHM_SHOT_SHAPE")
        b = physical[sid]
        a, duration = b["start"], b["duration"]
        _need(row["shot_id"] == sid and
              all(_number(row[key]) for key in (
                  "source_start_s", "source_duration_s", "source_end_s")) and
              abs(row["source_start_s"]-a) <= .011 and
              abs(row["source_duration_s"]-duration) <= .011 and
              abs(row["source_end_s"]-(a+duration)) <= .011,
              "RHYTHM_SILENT_TIMELINE_REWRITE")
        quote = row["visual_vision_exact_excerpt"]
        _need(isinstance(quote, str) and
              8 <= len(quote) <= 220 and
              _literal_contains(visual[sid], quote),
              "RHYTHM_NO_ACTUAL_DIRECTOR_VISUAL_QUOTE")
        for field in (
            "viewer_arrives_with", "viewer_leaves_with",
            "performance_and_attention_strategy",
            "motif_or_image_evolution", "sonic_curve_inside_shot",
            "rejected_generic_edit", "why_shorter_or_longer_is_not_automatically_better",
            "how_real_audience_media_would_refute",
        ):
            _text(row[field], "RHYTHM_NO_AUDIENCE_CAUSAL_RATIONALE")
        _need(row["viewer_arrives_with"] != row["viewer_leaves_with"],
              "RHYTHM_VIEWER_STATE_STAGNANT")
        proposed = row["exact_revision_instruction"]
        _decision(row["decision"], row["owner"], proposed,
                  "RHYTHM_UNAUTHORIZED_CHANGE_SCOPE")
        _need(type(row["proposed_deviation_from_locked_runtime"]) is bool,
              "RHYTHM_EDITING_DEVIATION_FLAG")
        _need(row["proposed_deviation_from_locked_runtime"] is False
              or row["decision"] in (
                  "director_redesign_required",
                  "screenwriter_change_required"),
              "RHYTHM_RUNTIME_CHANGE_CANNOT_BE_AUTOMATICALLY_APPROVED")
        beats = row["timecoded_attention_beats"]
        _need(isinstance(beats, list) and 1 <= len(beats) <= 6,
              "RHYTHM_BEAT_COUNT")
        cursor, seen = 0.0, set()
        for beat in beats:
            _shape(beat, BEAT, "RHYTHM_BEAT_SHAPE")
            _need(isinstance(beat["beat_id"], str) and
                  2 <= len(beat["beat_id"]) <= 70 and
                  beat["beat_id"] not in seen,
                  "RHYTHM_BEAT_ID_DUPLICATE")
            seen.add(beat["beat_id"])
            left, right = beat["from_s"], beat["to_s"]
            _need(_number(left) and _number(right) and
                  abs(left-cursor) < .011 and right > left and
                  right <= duration+.011,
                  "RHYTHM_ATTENTION_SPANS_GAP_OR_OVERLAP")
            cursor = right
            _need(beat["purpose"] in TYPES,
                  "RHYTHM_BEAT_PURPOSE_INVALID")
            for key in BEAT:
                if key not in (
                    "beat_id", "from_s", "to_s", "purpose"):
                    _text(beat[key], "RHYTHM_UNEXPLAINED_MOMENT")
        _need(abs(cursor-duration) < .011,
              "RHYTHM_BEATS_DO_NOT_END_AT_LOCKED_SHOT_DURATION")
    cut_count = max(0, len(state["shot_ids"])-1)
    joins = rhythm["seams"]
    _need(isinstance(joins, list) and len(joins) == cut_count,
          "RHYTHM_EVERY_ACTUAL_CUT_REQUIRED_ONCE")
    revision_requests, media_questions, unknown_audio = [], [], []
    for i, row in enumerate(joins):
        _shape(row, SEAM, "RHYTHM_SEAM_SHAPE")
        before, after = state["shot_ids"][i:i+2]
        edge = physical[before]["start"]+physical[before]["duration"]
        _need(row["from_shot_id"] == before and
              row["to_shot_id"] == after and
              _number(row["locked_boundary_s"]) and
              abs(row["locked_boundary_s"] - edge) <= .011,
              "RHYTHM_SILENT_CUT_BOUNDARY_CHANGE")
        for k in (
            "attention_state_out", "attention_state_in",
            "critical_action_and_information_at_cut", "reason_for_choice",
            "music_silence_dialogue_handoff",
            "orientation_and_motif_connection",
            "cut_handle_or_media_uncertainty", "human_media_review_condition",
        ):
            _text(row[k], "RHYTHM_NO_RELEVANT_EDITORIAL_REASON")
        for k, target in (
            ("outgoing_visual_quote", before),
            ("incoming_visual_quote", after),
        ):
            quote = row[k]
            _need(isinstance(quote, str) and 8 <= len(quote) <= 220 and
                  _literal_contains(visual[target], quote),
                  "RHYTHM_EDIT_NOT_GROUNDED_IN_ORIGINAL_DIRECTOR_VISION")
        clips = row["real_sound_or_edit_quotes"]
        _need(isinstance(clips, list),
              "RHYTHM_REAL_CREW_EVIDENCE_SHAPE")
        if phase == "before_specialists":
            _need(clips == [],
                  "RHYTHM_PRE_CREW_CANNOT_FAKE_SOUND_DESIGNS")
        else:
            _need(2 <= len(clips) <= 4,
                  "RHYTHM_NEEDS_ACTUAL_SOUND_AND_EDIT_QUOTES")
            roles = set()
            for entry in clips:
                _shape(entry, QUOTE, "RHYTHM_CREW_QUOTE_SHAPE")
                dept, sid, quote = (
                    entry["department"], entry["shot_id"],
                    entry["exact_excerpt"])
                _need(dept in ("sound", "editing_animation") and
                      sid in (before, after) and
                      isinstance(quote, str) and 8 <= len(quote) <= 220 and
                      _literal_contains(_role_shot(state, dept, sid), quote),
                      "RHYTHM_CREW_QUOTE_NOT_IN_ACTUAL_DELIVERED_VALUE")
                roles.add(dept)
            _need(roles == {"sound", "editing_animation"},
                  "RHYTHM_BOTH_SOUND_AND_EDITOR_MUST_BE_ACTUALLY_READ")
        alternatives = []
        for key in ("alternative_a", "alternative_b"):
            a = row[key]
            _shape(a, OPTION, "RHYTHM_ALTERNATIVE_SHAPE")
            _need(a["technique"] in OPTIONS,
                  "RHYTHM_UNKNOWN_CUT_OR_AUDIO_ROUTE")
            for k in OPTION:
                if k != "technique":
                    _text(a[k], "RHYTHM_ALTERNATIVE_WITHOUT_ARTISTIC_COST")
            alternatives.append(a["technique"])
            if a["technique"] in ("j_cut_candidate", "l_cut_candidate"):
                unknown_audio.append({
                    "cut": [before, after],
                    "requires_actual_sound_overlap_and_handles": True})
        _need(len(set(alternatives)) == 2,
              "RHYTHM_FALSE_ALTERNATIVE_SAME_TECHNIQUE")
        _need(row["directors_preferred_alternative"] in ("a", "b", "undecided"),
              "RHYTHM_ALTERNATIVE_SELECTION")
        _decision(row["decision"], row["owner"],
                  row["exact_revision_instruction"],
                  "RHYTHM_EDITORIAL_AUTHORITY_INVALID")
        _need(row["directors_preferred_alternative"] != "undecided" or
              row["decision"] == "defer_until_real_media",
              "RHYTHM_UNDECIDED_CUT_CANNOT_PRETEND_FINAL")
        if row["decision"] in (
            "director_redesign_required", "specialist_revision_required",
            "screenwriter_change_required"):
            revision_requests.append({
                "cut": [before, after], "owner": row["owner"],
                "reason": row["exact_revision_instruction"]})
        if row["decision"] == "defer_until_real_media":
            media_questions.append([before, after])
    return {
        "kind": "source_locked_director_episode_rhythm_receipt",
        "version": VERSION,
        "plan_digest": team.fingerprint(rhythm),
        "snapshot": deepcopy(snap),
        "phase": phase,
        "number_of_original_shots": len(plans),
        "real_cut_boundaries": cut_count,
        "proposed_revisions": revision_requests,
        "unresolved_media_cut_choices": media_questions,
        "possible_j_l_cut_media_handle_dependencies": unknown_audio,
        "source_total_duration_unchanged": True,
        "same_episode_sound_edit_deliveries_verified": (
            phase == "after_sound_and_edit_design"),
        "has_unresolved_director_or_editor_decisions": bool(
            revision_requests or media_questions or any(
                r["decision"] not in (
                    "keep_as_directed", "defer_until_real_media")
                for r in plans)),
        "real_media_or_human_aesthetic_quality_verified": False,
        "no_model_or_paid_media_calls": True,
        "may_render_or_publish": False,
    }


def departmental_context(base, state, meeting, audiovisual, rhythm, task_id,
                         *, artistic_method_plan=None):
    """Source-bound director WHY supplied to real sound/edit/QA/director roles."""
    proof = validate(
        base, state, meeting, audiovisual, rhythm,
        artistic_method_plan=artistic_method_plan)
    _need(task_id in ("sound", "editing_animation", "quality_review",
                      "director_final"), "RHYTHM_ROLE_NOT_RELEVANT")
    _need(proof["phase"] == "before_specialists" or
          task_id in ("quality_review", "director_final"),
          "RHYTHM_POST_CREW_REPORT_NOT_NEW_SOUND_EDIT_PROMPT")
    return {
        "kind": "source_locked_director_rhythm_for_existing_crew",
        "plan_digest": proof["plan_digest"],
        "phase": proof["phase"],
        "specialist": task_id,
        "episode_information_emotion_arc": rhythm[
            "audience_information_and_emotion_arc"],
        "silence_music_dialogue_arc": rhythm[
            "silence_music_dialogue_global_arc"],
        "full_original_shot_timing_is_immutable": True,
        "all_director_attention_beat_specs": deepcopy(rhythm["shots"]),
        "all_real_cut_decision_options": deepcopy(rhythm["seams"]),
        "profession_must_not_modify_script_or_authority": True,
        "do_not_infer_artist_approval_or_media_success": True,
    }


def propose_rework(base, state, meeting, audiovisual, rhythm, *,
                   shot_id=None, seam_from_shot_id=None, request_id,
                   what_must_remain_unchanged,
                   artistic_method_plan=None,
                   screenplay_change_kind=None):
    """One genuine proposed change routed through QO-D12; no state mutation."""
    r = validate(base, state, meeting, audiovisual, rhythm,
                 artistic_method_plan=artistic_method_plan)
    _need((shot_id is None) != (seam_from_shot_id is None),
          "RHYTHM_SELECT_ONE_SHOT_OR_CUT")
    if shot_id is not None:
        row = next((x for x in rhythm["shots"]
                    if x["shot_id"] == shot_id), None)
        ids = [shot_id]
        description = row["performance_and_attention_strategy"] if row else ""
    else:
        row = next((x for x in rhythm["seams"]
                    if x["from_shot_id"] == seam_from_shot_id), None)
        ids = [row["from_shot_id"], row["to_shot_id"]] if row else []
        description = row["critical_action_and_information_at_cut"] if row else ""
    _need(row is not None and row["decision"] in (
        "director_redesign_required", "specialist_revision_required",
        "screenwriter_change_required"),
          "RHYTHM_NO_REVISION_TO_ROUTE")
    if row["decision"] == "screenwriter_change_required":
        _need(screenplay_change_kind in lineage.SCRIPT_KINDS,
              "RHYTHM_EXPLICIT_SCREENPLAY_CHANGE_KIND_REQUIRED")
        kind = screenplay_change_kind
    else:
        _need(screenplay_change_kind is None,
              "RHYTHM_DIRECTOR_CANNOT_REWRITE_SCRIPT")
        kind = REVISIONS[row["owner"]]
    _text(what_must_remain_unchanged,
          "RHYTHM_MUST_IDENTIFY_MEANING_TO_PRESERVE")
    change = lineage.request(
        base, state, request_id=request_id, origin_role="director_final",
        kind=kind, shot_ids=ids, scene_or_source_beat_ids=[],
        observed_defect_or_creative_opportunity=description,
        viewer_or_story_consequence=(
            row["viewer_leaves_with"] if shot_id is not None else
            row["attention_state_in"]),
        proposed_change_in_own_words=row["exact_revision_instruction"],
        what_must_remain_unchanged=what_must_remain_unchanged,
        alternative_and_artistic_cost=(
            row["why_shorter_or_longer_is_not_automatically_better"]
            if shot_id is not None else
            row["alternative_a"]["emotional_or_information_cost"]+" vs "+
            row["alternative_b"]["emotional_or_information_cost"]),
    )
    return {
        "kind": "unsent_one_director_episode_rhythm_rework",
        "rhythm_digest": r["plan_digest"],
        "affected_approved_shot_ids": ids,
        "change_request": change,
        "old_locked_episode_runtime_unchanged": True,
        "director_or_writer_authority_authenticated": False,
        "no_local_media_or_model_calls": True,
    }
