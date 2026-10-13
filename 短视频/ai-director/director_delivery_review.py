#!/usr/bin/env python3
"""QO-D16: director reviews actual crew handoffs against creative intent.

Separate the director's *proposed* criticism from actual independent viewing.
All reviews are UNSENT. A precise single-department, shot-scoped revision can
be requested through the EXISTING 10-role ledger after explicit director action.
Never auto-approve source changes, spending, publication or a film.
"""
from __future__ import annotations

from copy import deepcopy
import json

import agent_team as team
import director_department_command as command
import director_visual_language as visual

VERSION = "director-delivery-feedback-v1"
VERDICTS = frozenset({
    "evidence_supports_intent", "revision_needed", "cannot_evaluate"})
EVIDENCE = frozenset({"submitted_design", "not_submitted"})
TARGETS = tuple(x for x in command.DEPARTMENTS if x != "director_final")


class DirectorReviewError(ValueError):
    pass


def _need(ok, error):
    if not ok:
        raise DirectorReviewError(error)


def _text(x, error, minimum=14):
    _need(isinstance(x, str) and minimum <= len(x.strip()) <= 2500 and
          "\0" not in x, error)


def _shape(obj, fields, code):
    _need(isinstance(obj, dict) and set(obj) == set(fields), code)


def _snapshot(base, state, meeting, language):
    meeting_proof = command.validate_command(base, state, meeting)
    vision_proof = visual.validate(base, state, meeting, language)
    proof = {}
    for department in TARGETS:
        task = state["tasks"][department]
        proof[department] = {
            "status": task["status"],
            "revision": task["revision"],
            "deliverable_digest": (
                team.fingerprint(task["deliverable"])
                if task["status"] == "completed" else None)}
    return {
        "source_digest": state["source_digest"],
        "base_digest": state["base_digest"],
        "meeting_digest": meeting_proof["command_digest"],
        "visual_language_digest": vision_proof["plan_digest"],
        "submitted_work": proof,
    }


def request(base, state, meeting, language):
    """Hand the director the ACTUAL role outputs, not just work assignments."""
    snapshot = _snapshot(base, state, meeting, language)
    context = {}
    for dept in TARGETS:
        task = state["tasks"][dept]
        context[dept] = {
            "status": task["status"],
            "revision": task["revision"],
            "provided_design": deepcopy(task["deliverable"])
                if task["status"] == "completed" else None,
            "director_instruction": deepcopy(meeting["departments"][dept]),
        }
    return {
        "kind": "unsent_director_review_of_department_deliveries",
        "version": VERSION,
        "dispatch_allowed": False,
        "independent_craft_review_completed": False,
        "media_viewed": False,
        "messages": [
            {"role": "system", "content": (
                "你是对作品最终意义负责的总导演，既已向七部门详细说明"
                "创作目的，现在必须根据各专业真正提交的产物复核，不能"
                "仅仅确认之前的导演指令有多少字段。"
                "逐镜头逐部门判断：演员关键动作是否被摄影看见，"
                "重要目光或选择是否被剪辑提前切走，声音/沉默是否恰好"
                "传递预定情绪，色彩和空间是否影响人物关系，"
                "AI失败降级有没有丢失论证/情感意义。"
                "每条评价要引用真实岗位交付中的具体内容作为证据，"
                "指出观众会得到或错过什么；如部门尚未交稿只能标记"
                "'不能评价'，绝不能捏造其输出或已拍好的影片。"
                "不能凭JSON完整度认定艺术成功；当前没有真正的媒体输入，"
                "因此任何正面判断最多表示文字设计支持意图，"
                "绝不可宣称实际成片审美已通过。"
                "不同专业意见冲突时，请列出双方实际意见和仲裁建议，"
                "允许负责部门提出更好替代方案，但导演最后负责一致性。"
                "返工要到具体镜头/责任部门/需配合部门/具体动作"
                "/验收方法；避免全部Agent从头写或互相覆盖权威素材。"
                "凡涉及新故事、人物抉择、事实、原文台词，交回编剧审核。"
                "单集最终仍<=90秒；禁止自动发布、付费、批准或生成视频。")},
            {"role": "user", "content": json.dumps({
                "versioned_source": snapshot,
                "episode_shots": base["shots"],
                "director_av_language": language,
                "director_department_meeting": meeting,
                "actual_department_deliveries": context,
                "required_findings_per_department_per_shot": {
                    "departments": TARGETS, "shot_ids": state["shot_ids"]},
                "finding_fields": [
                    "department", "shot_id", "verdict", "evidence_level",
                    "delivery_quote", "intended_viewer_effect", "observed_delivery_evidence",
                    "specific_viewer_consequence", "rewrite_instruction",
                    "professional_collaborators", "how_to_verify_next"],
                "conflict_fields": [
                    "shot_id", "left_department", "right_department",
                    "incompatible_work", "director_resolution", "human_decision_needed"],
                "required_review_fields": [
                    "version", "snapshot", "director_judgment",
                    "findings", "conflicts", "next_step"],
                "next_step_enum": [
                    "revise_specifications", "continue_department_work",
                    "ready_for_real_media_and_human_review"],
            }, ensure_ascii=False, separators=(",", ":"))}
        ],
    }


def validate(base, state, meeting, language, review):
    snapshot = _snapshot(base, state, meeting, language)
    _shape(review, {
        "version", "snapshot", "director_judgment",
        "findings", "conflicts", "next_step",
    }, "REVIEW_SHAPE")
    _need(review["version"] == VERSION and
          review["snapshot"] == snapshot, "REVIEW_STALE_DEPARTMENT_WORK")
    _text(review["director_judgment"], "REVIEW_NO_DIRECTOR_POSITION", minimum=24)
    target_keys = {(dept, sid) for dept in TARGETS for sid in state["shot_ids"]}
    rows = review["findings"]
    _need(isinstance(rows, list) and len(rows) == len(target_keys),
          "REVIEW_EVERY_SPECIALIST_SHOT_REQUIRED")
    seen, needs, pending = set(), [], []
    for entry in rows:
        _shape(entry, {
            "department", "shot_id", "verdict", "evidence_level",
            "delivery_quote", "intended_viewer_effect", "observed_delivery_evidence",
            "specific_viewer_consequence", "rewrite_instruction",
            "professional_collaborators", "how_to_verify_next",
        }, "REVIEW_FINDING_SHAPE")
        key = (entry["department"], entry["shot_id"])
        _need(key in target_keys and key not in seen, "REVIEW_DUPLICATE_OR_INVALID_TARGET")
        seen.add(key)
        _need(entry["verdict"] in VERDICTS and entry["evidence_level"] in EVIDENCE,
              "REVIEW_VERDICT_INVALID")
        completed = state["tasks"][entry["department"]]["status"] == "completed"
        _need((entry["evidence_level"] == "submitted_design") == completed,
              "REVIEW_INVENTED_DEPARTMENT_EVIDENCE")
        quote = entry["delivery_quote"]
        if completed:
            _need(isinstance(quote, str) and 6 <= len(quote) <= 240 and
                  quote in json.dumps(state["tasks"][entry["department"]]
                                      ["deliverable"], ensure_ascii=False),
                  "REVIEW_QUOTE_NOT_IN_ACTUAL_DELIVERY")
        else:
            _need(quote == "", "REVIEW_FAKE_MISSING_DELIVERY_QUOTE")
        if not completed:
            _need(entry["verdict"] == "cannot_evaluate",
                  "REVIEW_CANNOT_PASS_MISSING_DEPARTMENT")
            pending.append(key)
        else:
            _need(entry["verdict"] != "cannot_evaluate",
                  "REVIEW_SUBMITTED_WORK_NOT_ASSESSED")
        for field in ("intended_viewer_effect", "observed_delivery_evidence",
                      "specific_viewer_consequence", "how_to_verify_next"):
            _text(entry[field], "REVIEW_NO_SPECIFIC_REASON")
        collabs = entry["professional_collaborators"]
        _need(isinstance(collabs, list) and
              len(collabs) == len(set(collabs)) and
              all(dept in command.DEPARTMENTS and dept != entry["department"]
                  for dept in collabs), "REVIEW_COLLABORATION_INVALID")
        if entry["verdict"] == "revision_needed":
            _text(entry["rewrite_instruction"], "REVIEW_REPAIR_NOT_SPECIFIC")
            needs.append(key)
        else:
            _need(entry["rewrite_instruction"] == "",
                  "REVIEW_UNREQUESTED_REWRITE")
    _need(seen == target_keys, "REVIEW_TARGETS_MISSING")
    conflicts = review["conflicts"]
    _need(isinstance(conflicts, list) and len(conflicts) <= 80,
          "REVIEW_CONFLICT_COUNT")
    for c in conflicts:
        _shape(c, {
            "shot_id", "left_department", "right_department",
            "incompatible_work", "director_resolution", "human_decision_needed",
        }, "REVIEW_CONFLICT_SHAPE")
        _need(c["shot_id"] in state["shot_ids"] and
              c["left_department"] in command.DEPARTMENTS and
              c["right_department"] in command.DEPARTMENTS and
              c["left_department"] != c["right_department"] and
              type(c["human_decision_needed"]) is bool,
              "REVIEW_CONFLICT_TARGET")
        _text(c["incompatible_work"], "REVIEW_CONFLICT_UNEXPLAINED")
        _text(c["director_resolution"], "REVIEW_CONFLICT_UNRESOLVED")
    next_step = review["next_step"]
    _need(next_step in {
        "revise_specifications", "continue_department_work",
        "ready_for_real_media_and_human_review"}, "REVIEW_NEXT_STEP")
    _need((bool(needs) and next_step == "revise_specifications") or
          (not needs and bool(pending) and next_step == "continue_department_work") or
          (not needs and not pending and
           next_step == "ready_for_real_media_and_human_review"),
          "REVIEW_FALSE_READINESS")
    return {
        "kind": "director_department_delivery_review_receipt",
        "review_digest": team.fingerprint(review),
        "snapshot_digest": team.fingerprint(snapshot),
        "requested_revisions": [{"department": d, "shot_id": sid}
                                for d, sid in needs],
        "still_missing_deliveries": [{"department": d, "shot_id": sid}
                                    for d, sid in pending],
        "next_step": next_step,
        "real_media_seen": False,
        "independent_human_craft_verified": False,
        "author_approval_authenticated": False,
        "paid_calls": 0,
    }


def targeted_rework(base, state, meeting, language, review, *,
                    department, shot_id):
    """Director-authorized *single* targeted revision in existing team ledger.

    Do not use this as an automatic review loop: each invocation is a specific
    deliberate decision, and the next review must refer to the NEW ledger.
    """
    receipt = validate(base, state, meeting, language, review)
    _need({"department": department, "shot_id": shot_id}
          in receipt["requested_revisions"], "REWORK_NOT_RECOMMENDED")
    _need(department in team.SPECS and
          department not in ("quality_review", "director_final"),
          "REWORK_NONEDITABLE_DEPARTMENT")
    item = next(x for x in review["findings"]
                if x["department"] == department and x["shot_id"] == shot_id)
    try:
        updated = team.request_revision(
            state, department,
            [shot_id] if team.SPECS[department]["kind"] == "shots" else [],
            f"Director QO-D16: {item['specific_viewer_consequence']} "
            f"Please {item['rewrite_instruction']} "
            f"Acceptance: {item['how_to_verify_next']}",
            source_task="director_final")
    except ValueError:
        raise DirectorReviewError("REWORK_LEDGER_REJECTED") from None
    return {
        "kind": "director_single_revision_authorized_in_ledger",
        "reworked_department": department,
        "reworked_shot_id": shot_id,
        "previous_review_digest": receipt["review_digest"],
        "updated_team": updated,
        "remaining_reviews_are_stale": True,
        "no_external_model_calls": True,
        "requires_new_department_deliverable": True,
    }
