#!/usr/bin/env python3
"""Offline author-review worksheet, exact-version decisions, and locked crew intake.

This module is NOT an authentication or model gateway. A complete external
editorial decision can lock a *planning snapshot*, but cannot prove that a
human actually approved it, verify research claims, authorize paid APIs, or
publish media. User identity/consent requires a separate trusted private UI.
No private source, review worksheet or model prompt is persisted here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import html
import json

import agent_team as team
import creative_production_handoff as handoff
import asset_reference_manifest as assetrefs
import director

VERSION = "editorial-review-lock-v1"
MAX_NOTE_CHARS = 700
CHOICES = frozenset({"keep", "revise", "reject"})
SOURCE_EDIT_CHOICES = frozenset({"do_not_apply", "defer_for_separate_approval"})


class EditorialReviewError(ValueError):
    """Error codes only. Do not include user manuscript or review notes."""


def _hash(value):
    return team.fingerprint(value)


def _str(value, code, *, required=False):
    if not isinstance(value, str) or len(value) > MAX_NOTE_CHARS or (
            required and not value.strip()):
        raise EditorialReviewError(code)
    return value


def _candidate(candidate, episode_source):
    if not isinstance(candidate, dict) or candidate.get("kind") != "creative_storyboard_candidate" or (
            candidate.get("status") != "author_review_required") or (
            candidate.get("author_approved") is not False) or (
            candidate.get("paid_model_authorized") is not False) or (
            candidate.get("actual_provider_calls") != 0 or
            candidate.get("actual_billed_cny") != "0" or
            candidate.get("ai_media_generated") is not False):
        raise EditorialReviewError("REVIEW_UNTRUSTED_CANDIDATE")
    if not isinstance(episode_source, str) or not episode_source or (
            hashlib.sha256(episode_source.encode("utf-8")).hexdigest() !=
            candidate.get("episode_source_sha256")):
        raise EditorialReviewError("REVIEW_EPISODE_SOURCE_MISMATCH")
    plan = candidate.get("candidate_plan")
    if not isinstance(plan, dict) or _hash(plan) != candidate.get("candidate_base_digest"):
        raise EditorialReviewError("REVIEW_CANDIDATE_DIGEST_MISMATCH")
    if not isinstance(plan.get("shots"), list) or not plan["shots"]:
        raise EditorialReviewError("REVIEW_EMPTY_SHOTS")
    err, _ = director.validate(plan)
    if err:
        raise EditorialReviewError("REVIEW_PLAN_INVALID")
    proposals = candidate.get("unapproved_source_edit_proposals")
    if not isinstance(proposals, list) or any(
            not isinstance(p, dict) or
            p.get("requires_user_approval") is not True or
            p.get("approved") is not False for p in proposals):
        raise EditorialReviewError("REVIEW_SOURCE_EDITS_UNTRUSTED")
    return plan, proposals


def build_review_sheet(candidate, episode_source):
    """Return review items: PRIVATE; never commit to GitHub or public CI logs.

    No decision defaults to keep/approve. The sheet is only an invitation to
    inspect; it is not an approval certificate.
    """
    plan, edits = _candidate(candidate, episode_source)
    shot_ids = [s["id"] for s in plan["shots"]]
    if len(set(shot_ids)) != len(shot_ids):
        raise EditorialReviewError("REVIEW_DUPLICATE_SHOT_ID")
    return {
        "kind": VERSION, "status": "awaiting_author_review",
        "candidate_base_digest": candidate["candidate_base_digest"],
        "source_digest": candidate["episode_source_sha256"],
        "article_source_digest": candidate["source_sha256"],
        "title": plan["title"], "duration": plan["duration"],
        "shots": [{
            "shot_id": shot["id"], "shot_digest": _hash(shot),
            "time_start": shot["start"], "duration": shot["duration"],
            "original_candidate_narration": shot["narration"],
            "visual_type": shot["visual_type"], "visual_intention": shot["visual"],
            "action_design": deepcopy(shot["action"]),
            "camera_design": deepcopy(shot["camera"]),
            "claim_ids": deepcopy(shot["claim_ids"]),
            "choice": None, "review_note": "",
        } for shot in plan["shots"]],
        "source_change_proposals": [{
            "proposal_index": i, "proposal_digest": _hash(p),
            "proposal": deepcopy(p),
            "choice": None,
            "review_note": "",
        } for i, p in enumerate(edits)],
        "omissions": {
            "digest": _hash(plan["editorial"]["omissions"]),
            "items": deepcopy(plan["editorial"]["omissions"]),
            "choice": None,
        },
        "claims": {
            "digest": _hash(plan["claims"]),
            "items": deepcopy(plan["claims"]),
            "choice": None,
            "publication_verification_complete": False,
        },
        "global_direction": {
            "digest": _hash({"audience": plan["audience"], "hook": plan["editorial"]["hook"],
                            "visual_bible": plan["visual_bible"]}),
            "audience": plan["audience"], "hook": plan["editorial"]["hook"],
            "visual_bible": deepcopy(plan["visual_bible"]),
            "choice": None,
        },
        "actual_llm_calls": 0, "paid_api_authorized": False,
        "media_generated": False, "human_identity_verified": False,
        "author_approval_authenticated": False,
        "private_material": True,
    }


def decision_template(sheet):
    """Everything explicitly undecided. Never fill approvals on user's behalf."""
    if not isinstance(sheet, dict) or sheet.get("kind") != VERSION:
        raise EditorialReviewError("REVIEW_SHEET_REQUIRED")
    return {
        "version": VERSION,
        "candidate_base_digest": sheet["candidate_base_digest"],
        "source_digest": sheet["source_digest"],
        "review_intent": None,
        "review_note": "",
        "global_direction": {
            "digest": sheet["global_direction"]["digest"], "choice": None},
        "shots": [{
            "shot_id": x["shot_id"], "shot_digest": x["shot_digest"],
            "choice": None, "review_note": "",
        } for x in sheet["shots"]],
        "omissions": {"digest": sheet["omissions"]["digest"], "choice": None},
        "claims": {"digest": sheet["claims"]["digest"], "choice": None},
        "source_change_proposals": [{
            "proposal_index": x["proposal_index"],
            "proposal_digest": x["proposal_digest"],
            "choice": None, "review_note": "",
        } for x in sheet["source_change_proposals"]],
    }


def _review_error(label):
    raise EditorialReviewError("REVIEW_" + label)


def _exact(record, keys, label):
    if not isinstance(record, dict) or set(record) != set(keys):
        _review_error(label + "_SHAPE")


def _match_sha(item, digest, label):
    if item.get("digest") != digest:
        _review_error(label + "_STALE_DIGEST")


def evaluate_review(candidate, episode_source, decision):
    """Review supplied *untrusted* decisions and produce a bounded audit result.

    This does not authenticate the human reviewer, and the result can only be
    used to prepare a new offline planning ledger, not to authorize real spend.
    """
    sheet = build_review_sheet(candidate, episode_source)
    template = decision_template(sheet)
    _exact(decision, template, "DECISION")
    if decision["version"] != VERSION or (
            decision["candidate_base_digest"] != sheet["candidate_base_digest"]) or (
            decision["source_digest"] != sheet["source_digest"]):
        _review_error("STALE_OR_OTHER_EPISODE")
    _str(decision["review_note"], "REVIEW_NOTE_INVALID")
    if decision["review_intent"] not in ("accept_for_planning", "request_changes",
                                         "reject_candidate"):
        _review_error("INTENT_REQUIRED")
    if decision["review_intent"] != "accept_for_planning" and not decision["review_note"].strip():
        _review_error("EXPLANATION_REQUIRED")

    _exact(decision["global_direction"], template["global_direction"], "GLOBAL")
    _match_sha(decision["global_direction"], sheet["global_direction"]["digest"], "GLOBAL")
    if decision["global_direction"]["choice"] not in CHOICES:
        _review_error("GLOBAL_CHOICE_REQUIRED")

    sent = decision["shots"]
    expected = sheet["shots"]
    if not isinstance(sent, list) or len(sent) != len(expected):
        _review_error("SHOT_COVERAGE")
    requests = []
    for actual, reference in zip(sent, expected):
        _exact(actual, ("shot_id", "shot_digest", "choice", "review_note"), "SHOT")
        if actual["shot_id"] != reference["shot_id"] or (
                actual["shot_digest"] != reference["shot_digest"]):
            _review_error("SHOT_STALE_OR_REORDERED")
        if actual["choice"] not in CHOICES:
            _review_error("SHOT_CHOICE_REQUIRED")
        _str(actual["review_note"], "REVIEW_SHOT_NOTE_INVALID",
             required=(actual["choice"] != "keep"))
        if actual["choice"] != "keep":
            requests.append({
                "shot_id": actual["shot_id"], "requested_action": actual["choice"],
                "note": actual["review_note"]})

    _exact(decision["omissions"], template["omissions"], "OMISSIONS")
    _match_sha(decision["omissions"], sheet["omissions"]["digest"], "OMISSIONS")
    if decision["omissions"]["choice"] not in ("acknowledge_as_omitted", "revise"):
        _review_error("OMISSIONS_CHOICE_REQUIRED")

    _exact(decision["claims"], template["claims"], "CLAIMS")
    _match_sha(decision["claims"], sheet["claims"]["digest"], "CLAIMS")
    if decision["claims"]["choice"] not in (
            "acknowledge_unverified_for_planning", "request_fact_review"):
        _review_error("CLAIMS_CHOICE_REQUIRED")

    submitted_edits = decision["source_change_proposals"]
    expected_edits = sheet["source_change_proposals"]
    if not isinstance(submitted_edits, list) or len(submitted_edits) != len(expected_edits):
        _review_error("PROPOSALS_COVERAGE")
    pending_source_edits = []
    for actual, reference in zip(submitted_edits, expected_edits):
        _exact(actual, ("proposal_index", "proposal_digest", "choice", "review_note"),
               "PROPOSAL")
        if actual["proposal_index"] != reference["proposal_index"] or (
                actual["proposal_digest"] != reference["proposal_digest"]):
            _review_error("PROPOSAL_STALE_OR_REORDERED")
        if actual["choice"] not in SOURCE_EDIT_CHOICES:
            _review_error("PROPOSAL_REQUIRES_EXPLICIT_CHOICE")
        _str(actual["review_note"], "REVIEW_PROPOSAL_NOTE_INVALID")
        if actual["choice"] == "defer_for_separate_approval":
            pending_source_edits.append(reference["proposal_index"])

    blockers = []
    if decision["global_direction"]["choice"] != "keep":
        blockers.append("GLOBAL_REVIEW_REQUIRED")
    if requests:
        blockers.append("SHOT_REVISIONS_REQUIRED")
    if decision["omissions"]["choice"] != "acknowledge_as_omitted":
        blockers.append("OMISSIONS_UNRESOLVED")
    if decision["claims"]["choice"] != "acknowledge_unverified_for_planning":
        blockers.append("FACT_REVIEW_PENDING")
    if pending_source_edits:
        blockers.append("SOURCE_EDITS_PENDING_SEPARATE_APPROVAL")
    if decision["review_intent"] != "accept_for_planning":
        blockers.append("REVIEWER_REJECTED_OR_REQUESTED_CHANGES")
    outcome = "planning_snapshot_lockable" if not blockers else "revision_required"
    return {
        "version": VERSION, "status": outcome,
        "candidate_base_digest": sheet["candidate_base_digest"],
        "source_digest": sheet["source_digest"],
        "decision_digest": _hash(decision),
        "review_intent": decision["review_intent"],
        "blockers": blockers, "shot_rework": requests,
        "source_changes_applied": False,
        "fact_checked": False, "publication_approved": False,
        "trusted_reviewer_identity_verified": False,
        "external_paid_api_authorized": False,
        "private_material": bool(requests),  # review notes may be private
    }


def lock_planning_snapshot(candidate, episode_source, decision):
    """Lock exact candidate + decision values for PLANNING, not release.

    A forged approval decision might pass this local structural check. The
    surrounding private app MUST verify identity and consent independently
    before describing it as a user's real approval.
    """
    result = evaluate_review(candidate, episode_source, decision)
    if result["status"] != "planning_snapshot_lockable":
        raise EditorialReviewError("REVIEW_UNRESOLVED_BLOCKERS")
    candidate_plan = deepcopy(candidate["candidate_plan"])
    # Keep the original director/editor pitch bound to this exact candidate.
    # Previously the new ten-role team restarted from a plan and silently
    # lost the first real creative work, leading to inconsistent departments.
    creative_handoff = handoff.bound_handoff(candidate, episode_source)
    preflight = handoff.inspect_preproduction(candidate_plan, creative_handoff)
    return {
        "creative_handoff": creative_handoff,
        "creative_handoff_digest": team.fingerprint(creative_handoff),
        "production_preflight": preflight,
        "production_preflight_digest": team.fingerprint(preflight),
        "kind": "editorial_planning_snapshot",
        "version": VERSION,
        "status": "planning_locked_identity_unverified",
        "plan": candidate_plan,
        "plan_digest": team.fingerprint(candidate_plan),
        "source_digest": candidate["episode_source_sha256"],
        "article_source_digest": candidate["source_sha256"],
        "review_decision_digest": result["decision_digest"],
        "source_edits_applied": False,
        "claims_verified": False,
        "author_identity_verified": False,
        "human_release_approved": False,
        "paid_model_authorized": False,
        "actual_provider_calls": 0,
        "media_generated": False,
    }


def stage_locked_team(snapshot, episode_source):
    """Bind specialist planning to one locked plan hash, with no live transport."""
    if not isinstance(snapshot, dict) or snapshot.get("kind") != (
            "editorial_planning_snapshot") or snapshot.get("version") != VERSION or (
            snapshot.get("status") != "planning_locked_identity_unverified") or (
            snapshot.get("author_identity_verified") is not False) or (
            snapshot.get("paid_model_authorized") is not False) or (
            snapshot.get("human_release_approved") is not False):
        raise EditorialReviewError("REVIEW_UNTRUSTED_LOCK")
    plan = snapshot.get("plan")
    if not isinstance(plan, dict) or team.fingerprint(plan) != snapshot.get("plan_digest"):
        raise EditorialReviewError("REVIEW_LOCK_PLAN_MUTATED")
    if not isinstance(episode_source, str) or (
            hashlib.sha256(episode_source.encode("utf-8")).hexdigest()
            != snapshot.get("source_digest")):
        raise EditorialReviewError("REVIEW_LOCK_SOURCE_MUTATED")
    errors, _ = director.validate(plan)
    if errors:
        raise EditorialReviewError("REVIEW_LOCK_PLAN_INVALID")
    # A snapshot missing its original creative vision is no longer a valid
    # downstream planning input. All fields are private and digest-bound.
    try:
        intent = handoff.validate_locked_handoff(snapshot, episode_source)
        expected = handoff.inspect_preproduction(plan, intent)
    except (handoff.HandoffError, ValueError, KeyError, TypeError):
        raise EditorialReviewError("REVIEW_LOCK_CREATIVE_HANDOFF_INVALID") from None
    if (snapshot.get("production_preflight_digest") !=
            team.fingerprint(snapshot.get("production_preflight")) or
            snapshot.get("production_preflight") != expected):
        raise EditorialReviewError("REVIEW_LOCK_PREFLIGHT_TAMPERED")
    reference_digest = None
    if ("asset_reference_manifest" in snapshot or
            "asset_reference_manifest_digest" in snapshot):
        try:
            manifest = snapshot["asset_reference_manifest"]
            if (snapshot["asset_reference_manifest_digest"] !=
                    team.fingerprint(manifest)):
                raise ValueError("manifest digest changed")
            assetrefs.validate(plan, snapshot["source_digest"], manifest)
            reference_digest = snapshot["asset_reference_manifest_digest"]
        except (assetrefs.AssetReferenceError, KeyError, ValueError, TypeError):
            raise EditorialReviewError(
                "REVIEW_LOCK_ASSET_MANIFEST_INVALID") from None
    state = team.start(deepcopy(plan), source_text=episode_source)
    state["asset_reference_manifest_digest"] = reference_digest
    return {
        "asset_reference_manifest_digest": reference_digest,
        "reference_media_identity_verified": False,
        "kind": "locked_team_planning_intake", "version": VERSION,
        "status": "offline_planning_only_not_authorized_to_dispatch",
        "team": state, "plan_digest": state["base_digest"],
        "source_digest": state["source_digest"], "ready_tasks": team.ready(state),
        "first_editorial_vision_bound": True,
        "production_gap_count": expected["issue_count"],
        "production_ready": False,
        "author_identity_verified": False,
        "paid_api_authorized": False, "media_generated": False,
    }


def attach_reference_manifest(snapshot, episode_source, manifest):
    """Create a NEW private planning snapshot with source-bound references.

    Must run BEFORE any paid/specialist role starts; the team state gets the
    exact manifest digest, so changing wardrobe/reference later requires new
    role planning and permits. Never return a claim of author approval.
    """
    stage_locked_team(snapshot, episode_source)
    try:
        audit=assetrefs.validate(
            snapshot["plan"], snapshot["source_digest"], manifest)
    except (assetrefs.AssetReferenceError, ValueError, TypeError):
        raise EditorialReviewError("REVIEW_ASSET_MANIFEST_REJECTED") from None
    out=deepcopy(snapshot)
    out["asset_reference_manifest"]=deepcopy(manifest)
    out["asset_reference_manifest_digest"]=audit["manifest_digest"]
    # Existing values in an older snapshot are overwritten only if the caller
    # reconstructs a new locked version, never mutates the previous dict.
    return out


def render_private_review_html(sheet):
    """In-memory static offline review preview; no script, network or tracking."""
    if not isinstance(sheet, dict) or sheet.get("kind") != VERSION:
        raise EditorialReviewError("REVIEW_SHEET_REQUIRED")
    esc = lambda x: html.escape(str(x), quote=True)
    cells = []
    for s in sheet["shots"]:
        cells.append(
            "<article><h2>" + esc(s["shot_id"]) + " · " +
            esc(s["time_start"]) + "s / " + esc(s["duration"]) +
            "s</h2><p><b>原文候选旁白：</b>" +
            esc(s["original_candidate_narration"]) +
            "</p><p><b>拟制作形式：</b>" + esc(s["visual_type"]) +
            "</p><p><b>导演视觉设计：</b>" + esc(s["visual_intention"]) +
            "</p><p><b>摄影：</b>" + esc(s["camera_design"].get("movement", "")) +
            "</p><p><b>关联内容：</b>" + esc(", ".join(s["claim_ids"])) +
            "</p><p><b>复核：</b>未决定（请通过未来私有审阅界面提交）</p></article>")
    return ("<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>私有导演审阅草案</title><style>"
            "body{font-family:sans-serif;max-width:950px;margin:30px auto;padding:15px;"
            "background:#11151c;color:#e7edf6}article{padding:18px;border:1px solid #516078;"
            "border-radius:12px;margin:16px 0}p{line-height:1.7}small{color:#aab7c9}"
            "</style><h1>" + esc(sheet["title"]) +
            "</h1><p><strong>仅供审核，绝非已制作的视频。</strong></p><small>版本哈希：" +
            esc(sheet["candidate_base_digest"]) +
            "</small>" + "".join(cells) +
            "<p>未验证事实、遗漏和源稿改动均须分别审阅。"
            "此 HTML 没有授权按钮、没有外部连接、没有自动保存。</p></html>")
