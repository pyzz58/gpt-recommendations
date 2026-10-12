#!/usr/bin/env python3
"""QO-W01 professional creative development BEFORE screenplay drafting.

Professionally motivated stages:
  source diagnosis -> alternate film takes -> developmental selection ->
  short visual treatment -> writer draft -> existing independent script review.

Built after reading the project's primary-source craft audit, NOT from a
mechanical requirement to preserve every sentence or "critical idea".
These forms validate provenance, trade-offs and process order, not art.
All generated requests are UNSENT. Never upload private scripts to GitHub.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

import agent_team
import screenplay_fulltext_intake as fulltext

VERSION = "screenplay-creative-development-v1"
GENRES = frozenset({"fiction", "documentary", "essay", "hybrid"})
CHOICES = frozenset({"retain", "compress", "reframe", "omit"})
MAX_TREATMENT_SCENES = 20
MAX_SHORT_DURATION_S = 300


class CreativeDevelopmentError(ValueError):
    """Stable code-only errors to prevent leaking a user manuscript."""


def _need(condition, code):
    if not condition:
        raise CreativeDevelopmentError(code)


def _fingerprint(obj):
    return agent_team.fingerprint(obj)


def _text(value, code, min_length=10, max_length=1200):
    _need(isinstance(value, str) and
          min_length <= len(value.strip()) <= max_length and "\0" not in value,
          code)
    return value


def _verify(intake, document):
    try:
        fulltext._verify_intake(intake, document)
    except (fulltext.FulltextIntakeError, KeyError, TypeError, ValueError):
        raise CreativeDevelopmentError("DEVELOPMENT_INTAKE_STALE") from None


def _scope(intake, document):
    return document[slice(*intake["scope_span"])]


def _quote(quote, source):
    _need(isinstance(quote, str) and 4 <= len(quote) <= 300 and
          quote in source, "DEVELOPMENT_UNGROUNDED_SOURCE_QUOTE")


def _fields(value, keys, code):
    _need(isinstance(value, dict) and set(value) == set(keys), code)


def _message(system, payload):
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"))},
    ]


def diagnosis_request(intake, document, *, genre):
    """Deep read before inventing a plot; never claim an AI read equals understanding."""
    _verify(intake, document)
    _need(genre in GENRES, "DEVELOPMENT_GENRE")
    return {
        "kind": "unsent_source_diagnosis", "version": VERSION,
        "dispatch_allowed": False,
        "professional_quality_automatically_verified": False,
        "messages": _message(
            "你是职业编剧的原稿研究者，不是导演。仔细阅读 source_units 的全部原文，"
            "先分析作者为什么写、原文的独特声音、人物选择或论证认识轨迹、"
            "最适合呈现在屏幕上的核心变化。仅输出创作诊断，不要写剧本、"
            "摄影参数、提示词或镜头列表。"
            "将不能静默篡改的事实/关系/原作者特别强调的意思，与"
            "可大胆精简、重组、替代表现的叙述分开。"
            "必须从原稿取精确短引文，不要为了来源覆盖率强制保留每个段落。"
            "纪录片不杜撰历史人物口述，思想散文不强制英雄/三幕模型。"
            "原文没有资料/引用就不要补资料或安排片尾来源。"
            "区分作者已经说的事实和自己的推断。"
            "若不确定作者意图，应在 uncertainties 明确提出而非假称理解。",
            {
                "genre": genre,
                "source": _scope(intake, document),
                "source_units": deepcopy(intake["scope_units"]),
                "scope_digest": intake["scope_digest"],
                "required_fields": ["version", "genre", "scope_digest",
                                    "work_essence", "why_it_matters",
                                    "distinct_voice", "translation_to_screen",
                                    "audience_before", "audience_after",
                                    "protected", "freedom", "uncertainties"],
                "protected_item": ["quote", "reason"],
                "freedom_item": ["quote", "reason"],
                "must_keep_creative_choices_open": True,
            }),
    }


def validate_diagnosis(intake, document, diagnosis):
    _verify(intake, document)
    _fields(diagnosis, {
        "version", "genre", "scope_digest", "work_essence", "why_it_matters",
        "distinct_voice", "translation_to_screen", "audience_before",
        "audience_after", "protected", "freedom", "uncertainties",
    }, "DEVELOPMENT_DIAGNOSIS_SHAPE")
    _need(diagnosis["version"] == VERSION and
          diagnosis["genre"] in GENRES and
          diagnosis["scope_digest"] == intake["scope_digest"],
          "DEVELOPMENT_DIAGNOSIS_STALE")
    for key in ("work_essence", "why_it_matters", "distinct_voice",
                "translation_to_screen", "audience_before", "audience_after"):
        _text(diagnosis[key], "DEVELOPMENT_DIAGNOSIS_GENERIC")
    source = _scope(intake, document)
    for field in ("protected", "freedom"):
        rows = diagnosis[field]
        _need(isinstance(rows, list) and len(rows) <= 30,
              "DEVELOPMENT_DIAGNOSIS_REFERENCES")
        for row in rows:
            _fields(row, {"quote", "reason"}, "DEVELOPMENT_DIAGNOSIS_REFERENCE_SHAPE")
            _quote(row["quote"], source)
            _text(row["reason"], "DEVELOPMENT_DIAGNOSIS_REASON")
    _need(isinstance(diagnosis["uncertainties"], list) and
          len(diagnosis["uncertainties"]) <= 20 and
          all(isinstance(x, str) and len(x.strip()) >= 10
              for x in diagnosis["uncertainties"]),
          "DEVELOPMENT_DIAGNOSIS_UNCERTAINTIES")
    # No "protected" text by itself can prove any author's intention.
    return {
        "kind": "screenwriter_diagnosis_receipt",
        "source_digest": intake["scope_digest"],
        "diagnosis_digest": _fingerprint(diagnosis),
        "author_intent_verified": False,
        "literary_quality_verified": False,
    }


def takes_request(intake, document, diagnosis):
    proof = validate_diagnosis(intake, document, diagnosis)
    return {
        "kind": "unsent_alternative_film_takes", "version": VERSION,
        "dispatch_allowed": False,
        "messages": _message(
            "你是职业编剧开发编辑，提出2或3个真正不同、可被拍成AI短视频的"
            "改编 take，不能写成同一摘要的措辞变体。"
            "使用原文创作诊断作为创作起点，不把被引用的每个原文段落当作"
            "必须在剧本里出现的场次。每个方案须说清开场、作品驱动力、"
            "转折、结尾及具体可见可听的等价表达。"
            "诚实写出有意省略/合并/调整原文哪些部分以及其艺术代价，"
            "列出新事实风险、原作者保护项和超越来源的假设。"
            "小片段由未来导演/技术岗位拆成视频 clip，编剧只标记"
            "视觉/旁白/档案/字幕的制作挑战，不选择镜头焦距或供应商参数。"
            "绝不能为了呈现选择数量而制造三个虚假的换壳方案。",
            {
                "source": _scope(intake, document),
                "diagnosis": deepcopy(diagnosis),
                "diagnosis_digest": proof["diagnosis_digest"],
                "source_digest": intake["scope_digest"],
                "required_take_fields": [
                    "id", "angle", "narrative_engine", "opening", "turn",
                    "ending", "screen_expression", "expected_change",
                    "artistic_tradeoff", "ai_short_video_note",
                    "estimated_duration_s", "source_choices",
                    "new_fact_risks"],
                "source_choice_fields": ["quote", "choice", "reason"],
                "source_choices": sorted(CHOICES),
                "number_of_takes": "2 or 3 genuinely different",
            }),
    }


def validate_takes(intake, document, diagnosis, takes):
    receipt = validate_diagnosis(intake, document, diagnosis)
    _fields(takes, {"version", "source_digest", "diagnosis_digest", "takes"},
            "DEVELOPMENT_TAKES_SHAPE")
    _need(takes["version"] == VERSION and
          takes["source_digest"] == intake["scope_digest"] and
          takes["diagnosis_digest"] == receipt["diagnosis_digest"],
          "DEVELOPMENT_TAKES_STALE")
    options = takes["takes"]
    _need(isinstance(options, list) and 2 <= len(options) <= 3,
          "DEVELOPMENT_TAKE_COUNT")
    source = _scope(intake, document)
    ids, signatures = set(), set()
    for take in options:
        _fields(take, {
            "id", "angle", "narrative_engine", "opening", "turn", "ending",
            "screen_expression", "expected_change", "artistic_tradeoff",
            "ai_short_video_note", "estimated_duration_s",
            "source_choices", "new_fact_risks",
        }, "DEVELOPMENT_TAKE_SHAPE")
        _need(isinstance(take["id"], str) and
              re.fullmatch(r"TAKE-[A-Z]", take["id"]) and
              take["id"] not in ids, "DEVELOPMENT_DUPLICATE_TAKE")
        ids.add(take["id"])
        for key in ("angle", "narrative_engine", "opening", "turn",
                    "ending", "screen_expression", "expected_change",
                    "artistic_tradeoff", "ai_short_video_note"):
            _text(take[key], "DEVELOPMENT_TAKE_GENERIC")
        signature = tuple(take[key].strip().casefold()
                          for key in ("angle", "narrative_engine", "opening",
                                      "screen_expression"))
        _need(signature not in signatures, "DEVELOPMENT_IDENTICAL_TAKES")
        signatures.add(signature)
        duration = take["estimated_duration_s"]
        _need(type(duration) in (int, float) and
              10 <= duration <= MAX_SHORT_DURATION_S,
              "DEVELOPMENT_DURATION_NOT_SHORT_VIDEO")
        rows = take["source_choices"]
        _need(isinstance(rows, list) and 1 <= len(rows) <= 35,
              "DEVELOPMENT_SOURCE_CHOICE_REQUIRED")
        for row in rows:
            _fields(row, {"quote", "choice", "reason"},
                    "DEVELOPMENT_SOURCE_CHOICE_SHAPE")
            _quote(row["quote"], source)
            _need(row["choice"] in CHOICES, "DEVELOPMENT_SOURCE_CHOICE_INVALID")
            _text(row["reason"], "DEVELOPMENT_SOURCE_CHOICE_REASON")
        _need(isinstance(take["new_fact_risks"], list) and
              len(take["new_fact_risks"]) <= 15 and
              all(isinstance(x, str) and len(x.strip()) >= 10
                  for x in take["new_fact_risks"]),
              "DEVELOPMENT_NEW_FACT_RISKS_INVALID")
    return {
        "kind": "writer_alternative_takes_receipt",
        "source_digest": intake["scope_digest"],
        "diagnosis_digest": receipt["diagnosis_digest"],
        "takes_digest": _fingerprint(takes),
        "take_count": len(options),
        "take_difference_artistically_verified": False,
        "author_approval_authenticated": False,
    }


def selection_review_request(intake, document, diagnosis, takes):
    proof = validate_takes(intake, document, diagnosis, takes)
    return {
        "kind": "unsent_development_editor_selection", "version": VERSION,
        "dispatch_allowed": False, "editor_identity_authenticated": False,
        "messages": _message(
            "你是独立的编剧开发编辑。先独立阅读原稿，再看编剧的诊断和多个 takes。"
            "比较真正的叙事/信息旅程差异，指出哪一版保住作者独特性同时"
            "增加影像表达价值、哪一版仅是机械梳理原稿，以及每种方式的"
            "艺术代价。允许选择一个 take，也允许拒绝全部并要求重新提案。"
            "对正常合并、删减和重排不能一概判定失真；对错误事实归属、"
            "把开放问题篡改成已证明的结论等必须指出。"
            "只填写本次文学判断，不能声称获得作者本人认可或满足一流认证。",
            {
                "source": _scope(intake, document), "diagnosis": diagnosis,
                "takes": takes, "takes_digest": proof["takes_digest"],
                "decision_values": ["TAKE-A", "TAKE-B", "TAKE-C", "revise_all"],
                "selection_fields": [
                    "version", "source_digest", "takes_digest", "decision",
                    "comparisons", "choice_reason", "risk_to_author_intent",
                    "author_consultation_needed"],
                "comparison_item_fields": ["id", "advantage", "cost"],
            }),
    }


def validate_selection(intake, document, diagnosis, takes, selection):
    proof = validate_takes(intake, document, diagnosis, takes)
    _fields(selection, {
        "version", "source_digest", "takes_digest", "decision",
        "comparisons", "choice_reason", "risk_to_author_intent",
        "author_consultation_needed",
    }, "DEVELOPMENT_SELECTION_SHAPE")
    _need(selection["version"] == VERSION and
          selection["source_digest"] == proof["source_digest"] and
          selection["takes_digest"] == proof["takes_digest"],
          "DEVELOPMENT_SELECTION_STALE")
    ids = {x["id"] for x in takes["takes"]}
    _need(selection["decision"] in ids | {"revise_all"},
          "DEVELOPMENT_SELECTION_CHOICE")
    _text(selection["choice_reason"], "DEVELOPMENT_SELECTION_GENERIC")
    _text(selection["risk_to_author_intent"], "DEVELOPMENT_SELECTION_RISK")
    _need(type(selection["author_consultation_needed"]) is bool,
          "DEVELOPMENT_SELECTION_AUTHORITY")
    comps = selection["comparisons"]
    _need(isinstance(comps, list) and len(comps) == len(ids),
          "DEVELOPMENT_SELECTION_INCOMPLETE")
    seen = set()
    for x in comps:
        _fields(x, {"id", "advantage", "cost"}, "DEVELOPMENT_COMPARISON_SHAPE")
        _need(x["id"] in ids and x["id"] not in seen,
              "DEVELOPMENT_COMPARISON_DUPLICATE")
        seen.add(x["id"])
        _text(x["advantage"], "DEVELOPMENT_COMPARISON_VAGUE")
        _text(x["cost"], "DEVELOPMENT_COMPARISON_VAGUE")
    _need(seen == ids, "DEVELOPMENT_COMPARISON_MISSING")
    return {
        "kind": "writer_takes_selection_receipt",
        "source_digest": proof["source_digest"],
        "takes_digest": proof["takes_digest"],
        "selection_digest": _fingerprint(selection),
        "status": "revise_takes" if selection["decision"] == "revise_all"
                  else "selected_for_treatment_review",
        "real_editor_authenticated": False,
        "human_author_approval_authenticated": False,
    }


def treatment_request(intake, document, diagnosis, takes, selection):
    proof = validate_selection(intake, document, diagnosis, takes, selection)
    _need(proof["status"] == "selected_for_treatment_review",
          "DEVELOPMENT_ALL_TAKES_REJECTED")
    selected = next(x for x in takes["takes"]
                    if x["id"] == selection["decision"])
    return {
        "kind": "unsent_writer_treatment_request", "version": VERSION,
        "dispatch_allowed": False,
        "messages": _message(
            "你是负责最终成稿的职业编剧，已有经比较的影视改编角度。"
            "先完成短 treatment，**暂不写完整台词/机位/分镜**。"
            "每场写清开始状态、屏幕上可见可听的发生事件、"
            "观众认识或人物状态变化以及结果。"
            "纪录/论证类可由观众认知变化驱动，不强造人物欲望；"
            "小说则优先把必要的内心转化为人物的行动与选择。"
            "以可拍的视觉叙事为中心，而不是复述同一段旁白并依次播放插图。"
            "让每一场有必要性，同时给导演保留机位和声音制作自由。"
            "仅用 AI 短视频适用的长度方案，不因为单次clip上限破坏作者思想。",
            {
                "source": _scope(intake, document),
                "diagnosis": diagnosis,
                "selected_take": selected,
                "selection_review": selection,
                "scope_digest": intake["scope_digest"],
                "takes_digest": proof["takes_digest"],
                "selection_digest": proof["selection_digest"],
                "treatment_fields": [
                    "version", "scope_digest", "takes_digest", "selection_digest",
                    "selected_take_id", "premise", "scenes",
                    "ending_reverberation", "unsolved_writer_questions"],
                "scene_fields": [
                    "id", "starting_state", "visible_or_audible_event",
                    "changed_understanding_or_choice", "ending_state",
                    "reason_for_scene", "estimated_duration_s"],
            }),
    }


def validate_treatment(intake, document, diagnosis, takes, selection, treatment):
    proof = validate_selection(intake, document, diagnosis, takes, selection)
    _need(proof["status"] == "selected_for_treatment_review",
          "DEVELOPMENT_ALL_TAKES_REJECTED")
    _fields(treatment, {
        "version", "scope_digest", "takes_digest", "selection_digest",
        "selected_take_id", "premise", "scenes",
        "ending_reverberation", "unsolved_writer_questions",
    }, "DEVELOPMENT_TREATMENT_SHAPE")
    _need(treatment["version"] == VERSION and
          treatment["scope_digest"] == intake["scope_digest"] and
          treatment["takes_digest"] == proof["takes_digest"] and
          treatment["selection_digest"] == proof["selection_digest"] and
          treatment["selected_take_id"] == selection["decision"],
          "DEVELOPMENT_TREATMENT_STALE")
    _text(treatment["premise"], "DEVELOPMENT_TREATMENT_GENERIC")
    _text(treatment["ending_reverberation"], "DEVELOPMENT_TREATMENT_GENERIC")
    scenes = treatment["scenes"]
    _need(isinstance(scenes, list) and
          1 <= len(scenes) <= MAX_TREATMENT_SCENES,
          "DEVELOPMENT_TREATMENT_SCENE_COUNT")
    seen = set()
    total = 0.0
    for scene in scenes:
        _fields(scene, {
            "id", "starting_state", "visible_or_audible_event",
            "changed_understanding_or_choice", "ending_state",
            "reason_for_scene", "estimated_duration_s",
        }, "DEVELOPMENT_TREATMENT_SCENE_SHAPE")
        _need(isinstance(scene["id"], str) and
              re.fullmatch(r"SC\d{2,3}", scene["id"]) and
              scene["id"] not in seen, "DEVELOPMENT_TREATMENT_SCENE_ID")
        seen.add(scene["id"])
        for field in ("starting_state", "visible_or_audible_event",
                      "changed_understanding_or_choice", "ending_state",
                      "reason_for_scene"):
            _text(scene[field], "DEVELOPMENT_TREATMENT_SCENE_GENERIC")
        seconds = scene["estimated_duration_s"]
        _need(type(seconds) in (int, float) and 2 <= seconds <= 120,
              "DEVELOPMENT_TREATMENT_SCENE_DURATION")
        total += seconds
    _need(10 <= total <= MAX_SHORT_DURATION_S,
          "DEVELOPMENT_TREATMENT_TOTAL_DURATION")
    questions = treatment["unsolved_writer_questions"]
    _need(isinstance(questions, list) and len(questions) <= 15 and
          all(isinstance(x, str) and len(x.strip()) >= 10 for x in questions),
          "DEVELOPMENT_TREATMENT_QUESTIONS")
    return {
        "kind": "writer_visual_treatment_receipt",
        "source_digest": intake["scope_digest"],
        "takes_digest": proof["takes_digest"],
        "selection_digest": proof["selection_digest"],
        "treatment_digest": _fingerprint(treatment),
        "estimated_duration_s": total,
        "director_shots_defined": False,
        "real_writer_or_editor_quality_verified": False,
    }


def development_packet(intake, document, diagnosis, takes, selection, treatment):
    """Proof of stage ordering for the creative draft request, NOT author signoff."""
    proof = validate_treatment(
        intake, document, diagnosis, takes, selection, treatment)
    return {
        "kind": "screenplay_development_packet", "version": VERSION,
        "scope_digest": intake["scope_digest"],
        "diagnosis": deepcopy(diagnosis),
        "takes": deepcopy(takes),
        "selection": deepcopy(selection),
        "treatment": deepcopy(treatment),
        "treatment_digest": proof["treatment_digest"],
        "packet_integrity": _fingerprint({
            "diagnosis": diagnosis, "takes": takes, "selection": selection,
            "treatment": treatment}),
        "review_status": "development_completed_structurally_not_approved",
        "author_approval_authenticated": False,
        "creative_quality_verified": False,
        "paid_model_authorized": False,
    }


def validate_packet(intake, document, packet):
    _fields(packet, {
        "kind", "version", "scope_digest", "diagnosis", "takes",
        "selection", "treatment", "treatment_digest", "packet_integrity",
        "review_status", "author_approval_authenticated",
        "creative_quality_verified", "paid_model_authorized",
    }, "DEVELOPMENT_PACKET_SHAPE")
    _need(packet["kind"] == "screenplay_development_packet" and
          packet["version"] == VERSION and
          packet["scope_digest"] == intake["scope_digest"] and
          packet["review_status"] ==
              "development_completed_structurally_not_approved" and
          packet["author_approval_authenticated"] is False and
          packet["creative_quality_verified"] is False and
          packet["paid_model_authorized"] is False,
          "DEVELOPMENT_PACKET_AUTHORITY")
    valid = development_packet(intake, document,
        packet["diagnosis"], packet["takes"], packet["selection"], packet["treatment"])
    _need(_fingerprint(valid) == _fingerprint(packet),
          "DEVELOPMENT_PACKET_TAMPERED")
    return {
        "kind": "writer_development_integrity_receipt",
        "source_digest": packet["scope_digest"],
        "packet_digest": _fingerprint(packet),
        "selected_take_id": packet["selection"]["decision"],
        "treatment_digest": packet["treatment_digest"],
        "author_approval_authenticated": False,
        "quality_certified": False,
    }


def screenplay_request(intake, document, packet):
    """Actually bind selected treatment to the existing writer's UNSENT prompt."""
    proof = validate_packet(intake, document, packet)
    task = fulltext.editor_request(
        intake, document, mode=packet["diagnosis"]["genre"])
    payload = json.loads(task["messages"][1]["content"])
    payload["creative_development_packet"] = deepcopy(packet)
    payload["development_packet_digest"] = proof["packet_digest"]
    payload["required_draft_intention"] = (
        "Write a complete screenplay from SELECTED treatment, not a prose summary; "
        "retain source creative essence while respecting justified omissions. "
        "If there is a material change from selected treatment, label and justify "
        "it for the editor/author rather than silently revising it.")
    task["messages"][1]["content"] = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"))
    task["messages"][0]["content"] += (
        "\n【职业编剧开发稿已完成】下方包含先于写作独立建立的原著诊断、"
        "不同改编方案、逐方案比较及被选中 treatment。"
        "以选定方案发展完整剧本，不机械逐句拍原稿。"
        "重要取舍要有可供审阅的理由；受保护事实和结论不得暗改。"
        "导演的镜头分配、摄影、镜头时长和视频模型提示词不由本岗位决定。")
    task["professional_development_packet_digest"] = proof["packet_digest"]
    task["creative_development_completed_before_screenplay"] = True
    task["writer_quality_human_verified"] = False
    task["dispatch_allowed"] = False
    return task
