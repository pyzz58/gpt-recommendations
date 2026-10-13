#!/usr/bin/env python3
"""Writer detail dossier -> director's autonomous <=90s episodic plan.

New strict route only; legacy calls remain for existing public fixtures.
A complete screenplay may be many minutes; each *delivered* episode
includes any reserved head/tail/credit seconds and must be <=90 seconds.
Series breaks are director-owned decisions, not writer/source-unit shots.
No network calls, paywalls, private disk persistence, or actual rendering.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

import agent_team
import director
import screenplay_director_handoff as handoff_module

VERSION = "screenplay-to-series-v1"
MAX_EPISODE_S = 90
MAX_EPISODES = 100
EPS = 1e-6
EXTRAS = ("intro_s", "recap_s", "bridge_s", "outro_s", "evidence_s")


class SeriesDeliveryError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise SeriesDeliveryError(code)


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _digest(value):
    return agent_team.fingerprint(value)


def _txt(value, code, minimum=10, maximum=2400):
    _need(isinstance(value, str) and minimum <= len(value.strip()) <= maximum
          and "\0" not in value, code)
    return value


def _strict_object(value, keys, code):
    _need(isinstance(value, dict) and set(value) == set(keys), code)


def _handoff(value):
    _need(isinstance(value, dict) and
          value.get("kind") == handoff_module.VERSION and
          value.get("status") == "director_planning_intake_only" and
          isinstance(value.get("screenplay_scenes"), list) and
          isinstance(value.get("screenplay_fountain"), str) and
          _sha(value["screenplay_fountain"]) == value.get("screenplay_text_digest") and
          value.get("director_must_rewrite_screenplay") is False and
          value.get("paid_video_authorized") is False and
          isinstance(value.get("reconstructed_base"), dict) and
          _digest(value["reconstructed_base"]) == value.get("director_base_digest"),
          "SERIES_UNTRUSTED_SCRIPT_HANDOFF")
    beats = []
    for scene in value["screenplay_scenes"]:
        _need(isinstance(scene, dict) and
              isinstance(scene.get("id"), str) and
              isinstance(scene.get("beats"), list) and bool(scene["beats"]),
              "SERIES_SCENE_SHAPE")
        for beat in scene["beats"]:
            _need(isinstance(beat, dict) and
                  isinstance(beat.get("id"), str) and
                  type(beat.get("duration_s")) in (int, float) and
                  math.isfinite(beat["duration_s"]) and
                  beat["duration_s"] > 0, "SERIES_BEAT_DURATION")
            beats.append((scene["id"], beat))
    _need(beats and len({b["id"] for _, b in beats}) == len(beats),
          "SERIES_DUPLICATE_BEAT")
    return beats


def dossier_request(handoff):
    """UNSENT request to the screenwriter: detailed *story* not camera settings."""
    beats = _handoff(handoff)
    return {
        "kind": "unsent_writer_director_readability_dossier",
        "version": VERSION,
        "dispatch_allowed": False,
        "messages": [{
            "role": "system", "content": (
                "你是编剧，不是摄影师。剧本定稿后，为总导演提供充分、具体、"
                "便于执行的逐场逐节拍说明。必须逐一说明场景时空和环境、"
                "正在发生的事、人物/物体前后状态、动作刺激和反应、"
                "人物为什么选择这样做或思想为何产生变化、潜台词和可感的情绪、"
                "道具连续性、台词/旁白与沉默的创作目的、场次怎样因果衔接。"
                "让导演无需猜测故事、但仍可以自由设计机位/镜头/演员调度。"
                "不要凭空扩写剧本没有的新情节或史实；未知处提出编剧返修。"
                "细节不是填字数，不重复空洞视觉形容词。"
                "该说明必须覆盖所有既有 scene_id 和 beat_id，严禁截断。"
                "总导演另行决定将全剧本分成多少集，每集严格<=90秒。"
                "本岗位不得预先按90秒删改完整剧本或规划最终镜头。")},
            {"role": "user", "content": json.dumps({
                "full_screenplay": handoff["screenplay_fountain"],
                "scenes": handoff["screenplay_scenes"],
                "beat_order": [b["id"] for _, b in beats],
                "screenplay_digest": handoff["screenplay_text_digest"],
                "proposal_digest": handoff["accepted_screenplay_proposal_digest"],
                "scene_required_fields": [
                    "scene_id", "setting_and_time", "starting_state",
                    "story_purpose", "character_or_idea_objective",
                    "physical_progression", "emotional_or_cognitive_shift",
                    "sound_dialogue_silence_intent", "props_and_continuity",
                    "handoff_to_next", "beats"],
                "beat_required_fields": [
                    "beat_id", "observable_action_and_reaction",
                    "motivation_or_argument_link", "change_in_state",
                    "what_director_must_understand"],
                "schema_version": VERSION,
            }, ensure_ascii=False, separators=(",", ":"))},
        ],
    }


def validate_dossier(handoff, dossier):
    beats = _handoff(handoff)
    _strict_object(dossier, {
        "version", "screenplay_digest", "proposal_digest", "scenes",
    }, "SERIES_DOSSIER_SHAPE")
    _need(dossier["version"] == VERSION and
          dossier["screenplay_digest"] == handoff["screenplay_text_digest"] and
          dossier["proposal_digest"] == handoff["accepted_screenplay_proposal_digest"],
          "SERIES_DOSSIER_STALE")
    all_scenes = handoff["screenplay_scenes"]
    rows = dossier["scenes"]
    _need(isinstance(rows, list) and len(rows) == len(all_scenes),
          "SERIES_DOSSIER_SCENE_COVERAGE")
    for row, scene in zip(rows, all_scenes):
        _strict_object(row, {
            "scene_id", "setting_and_time", "starting_state", "story_purpose",
            "character_or_idea_objective", "physical_progression",
            "emotional_or_cognitive_shift", "sound_dialogue_silence_intent",
            "props_and_continuity", "handoff_to_next", "beats",
        }, "SERIES_DOSSIER_SCENE_SHAPE")
        _need(row["scene_id"] == scene["id"],
              "SERIES_DOSSIER_SCENE_ORDER")
        for k in ("setting_and_time", "starting_state", "story_purpose",
                  "character_or_idea_objective", "physical_progression",
                  "emotional_or_cognitive_shift", "sound_dialogue_silence_intent",
                  "props_and_continuity", "handoff_to_next"):
            _txt(row[k], "SERIES_DOSSIER_MISSING_DETAIL")
        details = row["beats"]
        _need(isinstance(details, list) and len(details) == len(scene["beats"]),
              "SERIES_DOSSIER_BEAT_COVERAGE")
        for entry, beat in zip(details, scene["beats"]):
            _strict_object(entry, {
                "beat_id", "observable_action_and_reaction",
                "motivation_or_argument_link", "change_in_state",
                "what_director_must_understand",
            }, "SERIES_DOSSIER_BEAT_SHAPE")
            _need(entry["beat_id"] == beat["id"],
                  "SERIES_DOSSIER_BEAT_ORDER")
            for key in ("observable_action_and_reaction",
                        "motivation_or_argument_link", "change_in_state",
                        "what_director_must_understand"):
                _txt(entry[key], "SERIES_DOSSIER_MISSING_BEAT_DETAIL")
    return {
        "kind": "writer_detailed_handoff_receipt", "dossier_digest": _digest(dossier),
        "screenplay_digest": handoff["screenplay_text_digest"],
        "fully_explained_scenes": len(rows), "fully_explained_beats": len(beats),
        "director_can_make_shots": True,
        "actual_creative_quality_human_verified": False,
    }


def director_breakdown_request(handoff, dossier):
    validated = validate_dossier(handoff, dossier)
    beats = _handoff(handoff)
    _need(handoff.get("reconstructed_base", {}).get("duration") ==
          sum(b["duration_s"] for _, b in beats),
          "SERIES_BASE_RUNTIME_MISMATCH")
    return {
        "kind": "unsent_director_series_breakdown", "version": VERSION,
        "dispatch_allowed": False,
        "max_episode_seconds": MAX_EPISODE_S,
        "full_screenplay_preserved": True,
        "messages": [{
            "role": "system", "content": (
                "你是总导演，已收到编剧的完整剧本和详尽的场次/节拍说明。"
                "你负责先统筹整部故事，再自主决定分成几集。"
                "每集的绝对上限为90秒（含片头、回顾、过渡、结尾及可选来源页）。"
                "可以只有一集、上下两集、上中下三集，也可以多于三集："
                "十分钟内容绝不可以硬塞三集。集数应以自然剧情转折、"
                "人物情绪或观众认识变化为依据，不是机械按90秒均分。"
                "注意：这里是对**导演最终选择、并经编剧审核的权威剪辑新版**做常规分集，"
                "所以这些已选节拍按原顺序恰好覆盖一次；对原始冗长剧本的删减压缩"
                "必须先走 director_creative_cut 专业导演改稿提案与编剧重审，"
                "不能把本分集函数的全覆盖误解为原稿不得删场。"
                "不得删去此已审定新剧本的节拍，也不能复制、改写、篡改人物台词；"
                "所有节拍按原顺序恰好覆盖一次。"
                "每集要提供观众可以进入的开端、具体推进、阶段性回报、"
                "下一集连接、断集理由和跨集人/道具/思想连续性。"
                "不得为强行悬念制造不存在的剧情或虚假结论。"
                "不以原文来源单元数量决定分集，也不把AI生成clip与单集混淆。"
                "短剧剧本是母稿，集数和独立分镜由导演决定；"
                "跨越90秒的不可分节拍需要向编剧请求细拆，不得假装能压缩。"
                "引用证据页只在原稿确实提供且核实后可选，页长1–2秒，"
                "位于相关集最后并计入90秒；不得强加。",
            )},
            {"role": "user", "content": json.dumps({
                "complete_screenplay": handoff["screenplay_fountain"],
                "full_writer_dossier": dossier,
                "beat_timeline": [{
                    "scene_id": sid, "beat_id": beat["id"],
                    "duration_s": beat["duration_s"],
                    "dramatic_function": beat["dramatic_function"],
                } for sid, beat in beats],
                "max_episode_s": MAX_EPISODE_S,
                "screenplay_digest": handoff["screenplay_text_digest"],
                "writer_dossier_digest": validated["dossier_digest"],
                "output_required": [
                    "version", "screenplay_digest", "writer_dossier_digest",
                    "director_reason_for_episode_count", "episodes"],
                "episode_fields": [
                    "episode_id", "episode_title", "beat_ids",
                    "opening_hook", "narrative_progression",
                    "emotional_or_idea_shift", "local_payoff",
                    "connection_to_next", "break_reason", "continuity_note",
                    "intro_s", "recap_s", "bridge_s", "outro_s", "evidence_s"],
                "no_authorization_claims": True,
                "episode_count_is_director_decision": True,
            }, ensure_ascii=False, separators=(",", ":"))}
        ],
    }


def validate_breakdown(handoff, dossier, breakdown):
    receipt = validate_dossier(handoff, dossier)
    beats = _handoff(handoff)
    _strict_object(breakdown, {
        "version", "screenplay_digest", "writer_dossier_digest",
        "director_reason_for_episode_count", "episodes",
    }, "SERIES_BREAKDOWN_SHAPE")
    _need(breakdown["version"] == VERSION and
          breakdown["screenplay_digest"] == handoff["screenplay_text_digest"] and
          breakdown["writer_dossier_digest"] == receipt["dossier_digest"],
          "SERIES_BREAKDOWN_STALE")
    _txt(breakdown["director_reason_for_episode_count"],
         "SERIES_COUNT_REASON_MISSING")
    episodes = breakdown["episodes"]
    _need(isinstance(episodes, list) and
          1 <= len(episodes) <= MAX_EPISODES,
          "SERIES_EPISODE_COUNT")
    seen_ids, flattened, reports = set(), [], []
    by_id = {beat["id"]: beat for _, beat in beats}
    # If the source contains no cited references, evidence remains optional
    # and defaults to zero. It cannot be made a compulsory title/credit.
    references_supplied = (
        handoff.get("source_supplied_reference_url_count", 0) > 0 or
        bool(handoff.get("reconstructed_base", {}).get("references", [])))
    for i, ep in enumerate(episodes, 1):
        _strict_object(ep, {
            "episode_id", "episode_title", "beat_ids", "opening_hook",
            "narrative_progression", "emotional_or_idea_shift", "local_payoff",
            "connection_to_next", "break_reason", "continuity_note",
            *EXTRAS,
        }, "SERIES_EPISODE_SHAPE")
        _need(ep["episode_id"] == "EP%02d" % i and
              ep["episode_id"] not in seen_ids,
              "SERIES_EPISODE_ID_ORDER")
        seen_ids.add(ep["episode_id"])
        for k in ("episode_title", "opening_hook", "narrative_progression",
                  "emotional_or_idea_shift", "local_payoff",
                  "connection_to_next", "break_reason", "continuity_note"):
            _txt(ep[k], "SERIES_EPISODE_LACKS_STORY",
                 minimum=3 if k == "episode_title" else 10)
        ids = ep["beat_ids"]
        _need(isinstance(ids, list) and bool(ids) and
              all(isinstance(bid, str) and bid in by_id for bid in ids),
              "SERIES_UNKNOWN_BEAT")
        flattened.extend(ids)
        extras = 0.0
        for key in EXTRAS:
            value = ep[key]
            _need(type(value) in (int, float) and math.isfinite(value) and
                  value >= 0, "SERIES_EXTRA_TIME_INVALID")
            extras += value
        if ep["evidence_s"]:
            _need(references_supplied and 1 <= ep["evidence_s"] <= 2,
                  "SERIES_UNSUPPORTED_EVIDENCE_PAGE")
        story = sum(by_id[bid]["duration_s"] for bid in ids)
        total = story + extras
        _need(total <= MAX_EPISODE_S + EPS,
              "SERIES_EPISODE_EXCEEDS_90_SECONDS")
        reports.append({
            "episode_id": ep["episode_id"],
            "story_s": story, "reserved_s": extras,
            "total_s": total, "max_s": MAX_EPISODE_S,
            "beat_ids": list(ids),
        })
    required = [beat["id"] for _, beat in beats]
    _need(flattened == required, "SERIES_BEATS_MISSING_DUPLICATED_OR_REORDERED")
    _need(abs(sum(r["story_s"] for r in reports) -
              sum(beat["duration_s"] for _, beat in beats)) < EPS,
          "SERIES_STORY_RUNTIME_LOST")
    return {
        "kind": "director_series_breakdown_receipt",
        "screenplay_digest": handoff["screenplay_text_digest"],
        "writer_dossier_digest": receipt["dossier_digest"],
        "director_breakdown_digest": _digest(breakdown),
        "episode_count": len(reports), "episodes": reports,
        "whole_story_duration_s": sum(x["story_s"] for x in reports),
        "total_delivery_estimate_s": sum(x["total_s"] for x in reports),
        "each_episode_lte_90": True,
        "all_screenplay_beats_preserved": True,
        "director_choices_human_approved": False,
        "media_rendered": False,
    }


def build_per_episode_crew(handoff, dossier, breakdown):
    """Build separate existing specialist teams; keep whole script as context.

    Clip generation, actual video and paid calls are NOT performed here.
    Reserved credits/recaps exist only in episode budget, not as phantom shots.
    """
    checked = validate_breakdown(handoff, dossier, breakdown)
    original = handoff["reconstructed_base"]
    _need(isinstance(original, dict) and
          _digest(original) == handoff.get("director_base_digest"),
          "SERIES_ORIGINAL_DIRECTOR_BASE_STALE")
    allshots = original["shots"]
    original_ids = [shot.get("source_adaptation", {}).get("beat_id")
                    for shot in allshots]
    _need(original_ids == [
        beat["id"] for _, beat in _handoff(handoff)],
        "SERIES_REBUILT_SHOTS_NOT_AUTHORITATIVE_BEATS")
    result = []
    for episode, receipt in zip(breakdown["episodes"], checked["episodes"]):
        chosen = set(episode["beat_ids"])
        sub = deepcopy(original)
        sub["shots"] = []
        pos = 0.0
        for shot in allshots:
            if shot["source_adaptation"]["beat_id"] in chosen:
                copy = deepcopy(shot)
                copy["start"] = pos
                copy["id"] = "S%02d" % (len(sub["shots"]) + 1)
                pos += copy["duration"]
                sub["shots"].append(copy)
        sub["duration"] = pos
        active_scenes = {x["scene_id"] for x in sub["shots"]}
        sub["scenes"] = [s for s in original["scenes"]
                         if s["id"] in active_scenes]
        sub["editorial"]["narration_script"] = "".join(
            x["narration"] for x in sub["shots"])
        sub["director_command_mode"] = {"kind": "director_department_conference_required", "command_before_specialists": True}
        sub["director_audiovisual_mode"] = {
            "kind": "director_audiovisual_plan_required",
            "audiovisual_intent_before_specialists": True}
        sub["director_artistic_mode"] = {
            "kind": "director_artistic_method_required",
            "artistic_intent_before_specialists": True}
        sub["series_context"] = {
            "kind": "director_episode_from_complete_screenplay",
            "episode_id": episode["episode_id"],
            "episode_title": episode["episode_title"],
            "full_screenplay_sha256": handoff["screenplay_text_digest"],
            "beat_ids": list(episode["beat_ids"]),
            "episode_story_s": receipt["story_s"],
            "reserved_additional_s": receipt["reserved_s"],
            "reserved_extra_components_s": {
                field: episode[field] for field in EXTRAS},
            "include_final_evidence_card": episode["evidence_s"] > 0,
            "episode_total_planned_s": receipt["total_s"],
            "max_total_duration_s": MAX_EPISODE_S,
            "director_breakdown_digest": checked["director_breakdown_digest"],
            "director_must_not_rewrite_screenplay": True,
        }
        errors, _ = director.validate(sub)
        _need(not errors, "SERIES_EPISODE_DIRECTOR_BASE_INVALID")
        _need(pos <= MAX_EPISODE_S + EPS, "SERIES_EPISODE_EXCEEDS_90_SECONDS")
        # Feed the entire screenplay so the director can maintain series
        # continuity, but execute existing crew on just this episode's beats.
        crew = agent_team.start(
            sub, source_text=handoff["screenplay_fountain"])
        _need(agent_team.ready(crew) == ["director_brief"],
              "SERIES_CREW_DAG_NOT_READY")
        result.append({
            "episode_id": episode["episode_id"],
            "episode_total_planned_s": receipt["total_s"],
            "authoritative_episode_base": sub,
            "crew": crew,
            "source_screenplay_sha256": handoff["screenplay_text_digest"],
            "screenwriter_dossier_digest": checked["writer_dossier_digest"],
            "director_breakdown_digest": checked["director_breakdown_digest"],
            "status": "planning_only_not_authorized",
            "paid_model_calls": 0,
        })
    return {
        "kind": "director_multi_episode_crew_packet",
        "version": VERSION,
        "complete_story_digest": handoff["screenplay_text_digest"],
        "series_breakdown": deepcopy(breakdown),
        "episodes": result,
        "all_screenplay_beats_preserved": True,
        "paid_model_calls": 0,
        "media_generated": False,
    }


def episode_director_request(handoff, dossier, breakdown, packet, episode_id,
                             *, director_coverage=None):
    """Actual original role request, optionally with director-authored shot plan.

    The optional coverage is recomputed from the original immutable reviewed
    screenplay and compared by digest; no arbitrary altered packet is trusted.
    """
    from agent_role_contracts import build_role_messages
    proof = validate_breakdown(handoff, dossier, breakdown)
    expected = build_per_episode_crew(handoff, dossier, breakdown)
    if director_coverage is not None:
        import director_shot_coverage
        _need(director_coverage["episode_id"] == episode_id,
              "SERIES_COVERAGE_WRONG_EPISODE")
        expected = director_shot_coverage.reblock_episode(
            handoff, dossier, breakdown, expected, director_coverage)
    _need(isinstance(packet, dict) and
          _digest(packet) == _digest(expected),
          "SERIES_EPISODE_CREW_PACKET_TAMPERED")
    episode = next((x for x in packet["episodes"]
                    if x["episode_id"] == episode_id), None)
    _need(episode is not None, "SERIES_UNKNOWN_EPISODE")
    result = build_role_messages(
        episode["authoritative_episode_base"], episode["crew"],
        "director_brief", source_text=handoff["screenplay_fountain"])
    result["messages"][0]["content"] += (
        "\n【导演90秒分集硬约束】你正在统筹完整剧本的其中一集。"
        "本集总时长（故事片段+额外片头/回顾/结尾/可选证据页）不能超过90秒。"
        "全剧本用于理解前后文，不允许把其他集节拍偷塞进当前集。"
        "编剧详细场次说明必须作为叙事理解的依据，但不构成机位指令。"
        "不得暗改原剧本或增加新台词，变更需要返回编剧。")
    # The director's actual model-facing message must receive the specific
    # per-episode artistic brief and relevant detailed writer scene notes.
    # Returning them only in result metadata would not guide a real Agent.
    separator = "\n仅返回符合 output_json_schema 的 JSON，内容还必须满足专业岗位细则：\n"
    before, found, encoded = result["messages"][1]["content"].partition(separator)
    _need(bool(found), "SERIES_ROLE_PROMPT_FORMAT")
    try:
        context = json.loads(encoded)
    except ValueError:
        raise SeriesDeliveryError("SERIES_ROLE_PROMPT_JSON") from None
    _need(context.get("original_script") == handoff["screenplay_fountain"] and
          context.get("authoritative_base") == episode["authoritative_episode_base"],
          "SERIES_ROLE_PROMPT_SOURCE_TAMPERED")
    episode_brief = next(x for x in breakdown["episodes"]
                         if x["episode_id"] == episode_id)
    active = set(episode_brief["beat_ids"])
    localized_dossier = []
    for scene in dossier["scenes"]:
        selected_beats = [b for b in scene["beats"] if b["beat_id"] in active]
        if selected_beats:
            detail = deepcopy(scene)
            detail["beats"] = selected_beats
            localized_dossier.append(detail)
    context["current_episode_story_and_break_reason"] = deepcopy(episode_brief)
    context["current_episode_detailed_writer_intent"] = localized_dossier
    context["entire_series_director_plan_digest"] = proof["director_breakdown_digest"]
    if director_coverage is not None:
        # The *real* director model request must see the shot relationships,
        # not only a digest or a comment in documentation.
        context["director_creative_shot_coverage"] = deepcopy(director_coverage)
        context["coverage_is_approved_screenplay_only_not_rendered_footage"] = True
        if "montage_plan" in director_coverage:
            context["director_editorial_montage_production_notes"] = deepcopy(
                episode["authoritative_episode_base"]["director_editorial_montage"])
            result["messages"][0]["content"] += (
                "\n【蒙太奇导演工单】跨场景以多个真实镜头执行，不允许同一物理镜头跨地点。"
                "每道剪切说明时空来源、人物道具状态、声音剪接、观众理解变化。"
                "文本规划不等于成片或艺术验收。")
        result["messages"][0]["content"] += (
            "\n【导演自由镜头覆盖】这些专业镜头由总导演按已审稿"
            "自行分合原场次节拍，source_spans是对剧本时间的"
            "完整来源映射而非一镜一beat。你需要保留已审稿台词、"
            "人物选择及事实；逐镜开展实际表演、摄影、声画设计，"
            "不得将该文字版误称成片。")
    result["messages"][1]["content"] = before + found + json.dumps(
        context, ensure_ascii=False, separators=(",", ":"))
    result["episode_director_context"] = {
        "episode_id": episode_id,
        "full_screenplay_digest": proof["screenplay_digest"],
        "director_breakdown": deepcopy(breakdown),
        "writer_dossier": deepcopy(dossier),
        "max_episode_s": MAX_EPISODE_S,
        "this_episode_total_s": episode["episode_total_planned_s"],
        "author_approval_authenticated": False,
    }
    result["external_model_call_authorized"] = False
    return result
