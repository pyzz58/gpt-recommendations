#!/usr/bin/env python3
"""QO-D14: professional director may REJECT, CONDENSE, or OMIT screenplay beats.

A director's proposed cut is NOT automatically the new authorized screenplay.
The full version remains immutable; structural/casual change is returned as an
unsent *writer revision request*. The existing 90-second per-episode production
route can run only on the separately reviewed new screenplay.

Motivated by first-party DGA director rights, ScreenSkills professional role,
and full BFI interviews (Scorsese, Soderbergh, Wiseman, Tlatli, Nolan).
No model/network calls or private-file writes.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy

import agent_team
import screenplay_series_delivery as series

VERSION = "director-creative-cut-v1"
OPERATIONS = frozenset({"retain", "condense", "omit"})
IMPACT = frozenset({"preserves_meaning", "meaning_uncertain", "meaning_changed"})
EP_LIMIT = 90
EPS = 1e-5


class DirectorCutError(ValueError):
    """Privacy-safe stable error code."""


def _require(cond, code):
    if not cond:
        raise DirectorCutError(code)


def _text(val, code, minimum=12, maximum=2200):
    _require(isinstance(val, str) and minimum <= len(val.strip()) <= maximum
             and "\0" not in val, code)


def _shape(value, keys, code):
    _require(isinstance(value, dict) and set(value) == set(keys), code)


def _beats(handoff, dossier):
    try:
        proof = series.validate_dossier(handoff, dossier)
        beats = series._handoff(handoff)
    except (series.SeriesDeliveryError, KeyError, ValueError, TypeError):
        raise DirectorCutError("CUT_SOURCE_OR_WRITER_DOSSIER_UNTRUSTED") from None
    return proof, beats


def creative_analysis_request(handoff, dossier):
    """Actual full-script professional thinking, prior to cutting into episodes."""
    proof, beats = _beats(handoff, dossier)
    return {
        "version": VERSION,
        "kind": "unsent_director_creative_diagnosis_and_cut_options",
        "dispatch_allowed": False,
        "quality_certified": False,
        "messages": [
            {"role": "system", "content": (
                "你是职业电影总导演，拥有否定编剧剧本节奏、建议大幅缩写、"
                "换用更有电影表达力的版本的创作职责。必须先读完整剧本及"
                "详细逐场逐节拍说明，不能机械执行编剧原估计时间。"
                "像 DGA/ScreenSkills 的导演职业工作那样，将叙事、表演、"
                "摄影、声音和剪辑统一为观众的戏剧与审美体验。"
                "对每个原剧本节拍问：删除后是否失去人物选择与代价、事实/论证因果、"
                "观众认知转折或情感余韵；能否以一个行动/视觉反差替代重复旁白；"
                "哪些慢节奏/沉默本身必须保留才能生效？"
                "必须构思至少两种真正不同的导演剪辑 take，包括不同集数/运行时长、"
                "具体删改的艺术代价、观众体验的变化与制作难度。"
                "导演可以主张10分钟稿剪成3集，但不能把压短自动等于更好，"
                "也不能按平均秒数无理由删场。"
                "电影式小说重视人物抉择/潜台词；观点科普重视认知推进与不把问题"
                "当结论；纪实重视事实公平、不能凭剪辑伪造因果。"
                "每集所有正文/片头/回顾/过渡/片尾合计最多90秒。"
                "只将创意决定当提案，涉及台词、整场、结局或人物核心的删改"
                "向编剧提出具体返修，作者批准、证据核实或独立审片绝不伪造。"
                "不修改权威母稿，不在此步骤生成镜头/支付AI生成费用。")},
            {"role": "user", "content": json.dumps({
                "complete_screenplay": handoff["screenplay_fountain"],
                "writer_dossier": dossier,
                "source_digest": handoff["screenplay_text_digest"],
                "dossier_digest": proof["dossier_digest"],
                "all_source_beats": [{
                    "scene_id": sid,
                    "beat_id": beat["id"],
                    "duration_s": beat["duration_s"],
                    "story_function": beat["dramatic_function"],
                    "action": beat["action"],
                    "spoken_dialogue": beat["dialogue"],
                    "voiceover": beat["voiceover"],
                } for sid, beat in beats],
                "alternatives": "at least two substantively distinct cuts",
                "max_episode_seconds": EP_LIMIT,
                "required_one_cut_fields": [
                    "version", "source_digest", "dossier_digest",
                    "directorial_thesis", "overall_audience_arc",
                    "why_this_cut_is_better", "lost_value_and_counterargument",
                    "decisions", "episodes"],
                "beat_decision_fields": [
                    "beat_id", "operation", "new_duration_s", "why",
                    "viewer_gain", "viewer_loss", "meaning_impact",
                    "writer_revision_required"],
                "episode_fields": [
                    "episode_id", "beat_ids", "episode_promise",
                    "episode_turn_and_payoff", "why_break_here",
                    "continuity_to_next", "intro_s", "recap_s", "bridge_s",
                    "outro_s", "evidence_s"],
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate_cut(handoff, dossier, cut):
    """Validates a real director's proposed SHORTER CUT, not literary merit."""
    proof, beats = _beats(handoff, dossier)
    _shape(cut, {
        "version", "source_digest", "dossier_digest", "directorial_thesis",
        "overall_audience_arc", "why_this_cut_is_better",
        "lost_value_and_counterargument", "decisions", "episodes",
    }, "CUT_SHAPE")
    _require(cut["version"] == VERSION and
             cut["source_digest"] == handoff["screenplay_text_digest"] and
             cut["dossier_digest"] == proof["dossier_digest"],
             "CUT_STALE_SOURCE_OR_DOSSIER")
    for k in ("directorial_thesis", "overall_audience_arc",
              "why_this_cut_is_better", "lost_value_and_counterargument"):
        _text(cut[k], "CUT_CREATIVE_JUDGMENT_MISSING")
    original = {beat["id"]: beat for _, beat in beats}
    rows = cut["decisions"]
    _require(isinstance(rows, list) and len(rows) == len(beats),
             "CUT_EVERY_BEAT_NEEDS_EDITORIAL_DECISION")
    compiled = {}
    writers, omissions, altered, risks = [], [], [], []
    old_secs = 0.0
    new_secs = 0.0
    for index, ((scene_id, old), row) in enumerate(zip(beats, rows)):
        _shape(row, {
            "beat_id", "operation", "new_duration_s", "why",
            "viewer_gain", "viewer_loss", "meaning_impact",
            "writer_revision_required",
        }, "CUT_BEAT_DECISION_SHAPE")
        bid = old["id"]
        _require(row["beat_id"] == bid and row["operation"] in OPERATIONS,
                 "CUT_BEAT_DECISIONS_NOT_IN_SCRIPT_ORDER")
        for k in ("why", "viewer_gain", "viewer_loss"):
            _text(row[k], "CUT_BEAT_REASON_INSUFFICIENT")
        _require(row["meaning_impact"] in IMPACT and
                 type(row["writer_revision_required"]) is bool,
                 "CUT_IMPACT_OR_REWRITE_INVALID")
        duration = row["new_duration_s"]
        orig_s = old["duration_s"]
        _require(type(duration) in (int, float) and math.isfinite(duration),
                 "CUT_DURATION_INVALID")
        if row["operation"] == "retain":
            _require(abs(duration - orig_s) < EPS and
                     row["writer_revision_required"] is False,
                     "CUT_RETAIN_CAN_NOT_SILENTLY_CHANGE_SCRIPT")
        elif row["operation"] == "condense":
            _require(0 < duration < orig_s and
                     row["writer_revision_required"] is True,
                     "CUT_CONDENSE_REQUIRES_SCRIPT_REVISION")
            altered.append(bid)
            writers.append(bid)
        else:
            _require(duration == 0 and
                     row["writer_revision_required"] is True,
                     "CUT_OMISSION_REQUIRES_SCRIPT_REVISION")
            omissions.append(bid)
            writers.append(bid)
        if row["meaning_impact"] != "preserves_meaning":
            risks.append(bid)
        old_secs += orig_s
        new_secs += duration
        compiled[bid] = {"scene_id": scene_id, "original": old,
                         "cut": row, "new_s": duration}

    _require(new_secs > 0 and new_secs <= old_secs + EPS,
             "CUT_EMPTY_OR_INCREASED_RUNTIME")
    episodes = cut["episodes"]
    _require(isinstance(episodes, list) and 1 <= len(episodes) <= 100,
             "CUT_EPISODE_COUNT")
    scheduled = []
    expected = [r["beat_id"] for r in rows if r["operation"] != "omit"]
    actual, reports = [], []
    has_sources = (
        handoff.get("source_supplied_reference_url_count", 0) > 0 or
        bool(handoff.get("reconstructed_base", {}).get("references", [])))
    for i, episode in enumerate(episodes, start=1):
        _shape(episode, {
            "episode_id", "beat_ids", "episode_promise",
            "episode_turn_and_payoff", "why_break_here",
            "continuity_to_next", "intro_s", "recap_s",
            "bridge_s", "outro_s", "evidence_s",
        }, "CUT_EPISODE_SHAPE")
        _require(episode["episode_id"] == f"EP{i:02d}",
                 "CUT_EPISODE_ORDER")
        for k in ("episode_promise", "episode_turn_and_payoff",
                  "why_break_here", "continuity_to_next"):
            _text(episode[k], "CUT_EPISODE_LACKS_STORY")
        ids = episode["beat_ids"]
        _require(isinstance(ids, list) and bool(ids) and
                 all(isinstance(x, str) and x in compiled and
                     compiled[x]["new_s"] > 0 for x in ids),
                 "CUT_EPISODE_UNKNOWN_OR_OMITTED_BEAT")
        actual += ids
        story = sum(compiled[x]["new_s"] for x in ids)
        extras = 0.0
        for k in ("intro_s", "recap_s", "bridge_s",
                  "outro_s", "evidence_s"):
            seconds = episode[k]
            _require(type(seconds) in (int, float) and
                     math.isfinite(seconds) and seconds >= 0,
                     "CUT_EXTRA_RUNTIME_INVALID")
            extras += seconds
        if episode["evidence_s"]:
            _require(has_sources and 1 <= episode["evidence_s"] <= 2,
                     "CUT_UNSUPPORTED_EVIDENCE_CARD")
        _require(story + extras <= EP_LIMIT + EPS,
                 "CUT_EPISODE_LONGER_THAN_90S")
        reports.append({
            "episode_id": episode["episode_id"],
            "beat_ids": list(ids),
            "story_seconds": story, "total_seconds": story + extras,
        })
    _require(actual == expected, "CUT_SCHEDULE_MISSING_OR_REORDERED_BEATS")
    _require(abs(new_secs - sum(x["story_seconds"] for x in reports)) < EPS,
             "CUT_STORY_SECONDS_MISMATCH")
    # Mapping every origin to a disposition is audit completeness, NOT an
    # artistic mandate that all beats survive into the cut.
    return {
        "kind": "director_creative_cut_proposal_receipt",
        "source_digest": handoff["screenplay_text_digest"],
        "writer_dossier_digest": proof["dossier_digest"],
        "director_cut_digest": agent_team.fingerprint(cut),
        "source_seconds": old_secs, "proposed_story_seconds": new_secs,
        "removed_seconds": old_secs - new_secs,
        "proposed_episode_count": len(episodes), "episode_budgets": reports,
        "omitted_source_beat_ids": omissions,
        "shortened_source_beat_ids": altered,
        "meaning_risk_beat_ids": risks,
        "script_revision_beat_ids": writers,
        "all_source_beats_audited": True,
        "all_source_beats_forced_into_movie": False,
        "script_revision_required": bool(writers),
        "approved_new_screenplay_available": False,
        "editorial_merit_certified": False,
        "independent_reviewer_authenticated": False,
        "author_approval_authenticated": False,
        "media_generated": False,
        "next_stage": (
            "writer_script_revision_then_independent_author_review" if writers
            else "director_series_breakdown_with_original_authoritative_script"),
    }


def writer_revision_request(handoff, dossier, cut):
    """Give the actual original writer detailed notes, not forged final cut."""
    proof = validate_cut(handoff, dossier, cut)
    _require(proof["script_revision_required"],
             "CUT_NO_SCRIPT_REVISION_REQUIRED")
    req = {
        "kind": "unsent_director_to_writer_compression_notes",
        "version": VERSION, "dispatch_allowed": False,
        "approved_to_modify_original": False,
        "author_consent_authenticated": False,
        "original_screenplay_digest": handoff["screenplay_text_digest"],
        "cut_digest": proof["director_cut_digest"],
        "messages": [
            {"role": "system", "content": (
                "你是原项目职业编剧。总导演有权认为你写的10分钟剧本拖沓，"
                "建议压成例如3集80秒，并提交逐节拍理由。"
                "请先真正阅读未改原稿和导演提案，根据导演节拍批注独立重写新的"
                "完整短版本，而不是把源文本一刀截断。"
                "可以删除无意义的交代、改旁白/对白、合并可视化段落，"
                "但必须保住核心人物选择、论证因果、事实诚信和情绪回声。"
                "对于导演方案会改变原意的地方有权建议驳回，具体指出原因。"
                "原权威稿保持独立存档；新版需要独立剧本审核和作者授权流程，"
                "不要声称导演的 cut 自己已经被批准，也不要给出拍摄API prompt。")},
            {"role": "user", "content": json.dumps({
                "unchanged_original_screenplay": handoff["screenplay_fountain"],
                "writer_dossier": dossier, "proposed_director_cut": cut,
                "original_screenplay_digest": proof["source_digest"],
                "director_cut_digest": proof["director_cut_digest"],
                "director_origin_changes": [{
                    "beat_id": row["beat_id"], "operation": row["operation"],
                    "from_s": next(beat["duration_s"] for scene in handoff["screenplay_scenes"]
                                   for beat in scene["beats"]
                                   if beat["id"] == row["beat_id"]),
                    "to_s": row["new_duration_s"],
                    "reason": row["why"], "viewer_loss": row["viewer_loss"],
                    "meaning_impact": row["meaning_impact"],
                } for row in cut["decisions"] if row["writer_revision_required"]],
                "new_version_must_get_independent_review": True,
                "target_is_story_duration_not_per_generation_clip": True,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }
    return req
