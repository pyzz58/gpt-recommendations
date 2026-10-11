#!/usr/bin/env python3
"""Explicit MANUAL, GITHUB CLOUD ONLY, public fiction, at most two DeepSeek calls.

No executable server, automatic trigger, secret storage or private manuscript
support. Secret exists only in GitHub Actions encrypted secret -> process env.
This creates an intentionally PUBLIC GitHub artifact with *fictional* model
outputs for external review. It never exposes the API key or HTTP bodies in
logs. AI results are untrusted data and not approved director work.

No automatic retries: each requested role has one attempt and any failure
stops the chain. GitHub job re-runs remain possible while the key still exists:
the operator MUST promptly revoke and remove the secret after the one run.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
import sys

import agent_live_pilot as pilot
import article_intake as intake
import editorial_storyboard as creative
import live_pilot_readiness as readiness
import agent_team as team

VERSION = "deepseek-one-time-public-fiction-cloud-trial-v1"
AUTHORIZED_ACTOR = "pyzz58"
REPO = "pyzz58/gpt-recommendations"
TRIAL_ROLES = ("director_brief", "script_edit")
MAX_REQUESTS = 2
RUBRIC = {
    "opening_hook_story_structure": 20,
    "blocking_performance_shootability": 20,
    "camera_lighting_spatial_logic": 20,
    "audio_editing_postproduction": 15,
    "source_fidelity": 15,
    "video_model_feasibility": 10,
}


class CloudTrialError(ValueError):
    """No private text or credentials in error messages."""


def _guard(condition, code):
    if not condition:
        raise CloudTrialError(code)


def _json_safe_write(folder, name, data):
    # The caller owns all data. Only fictional scenes and model results may be
    # serialized here; never persist prompts, secrets or raw HTTP.
    p = Path(folder) / name
    with p.open("x", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2, allow_nan=False)
        fp.write("\n")


def _cloud_gate():
    _guard(os.environ.get("GITHUB_ACTIONS") == "true", "CLOUD_GITHUB_ONLY")
    _guard(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch",
           "CLOUD_MANUAL_DISPATCH_ONLY")
    _guard(os.environ.get("GITHUB_REPOSITORY") == REPO,
           "CLOUD_WRONG_REPOSITORY")
    _guard(os.environ.get("GITHUB_REF") == "refs/heads/main",
           "CLOUD_MAIN_ONLY")
    _guard(os.environ.get("GITHUB_ACTOR") == AUTHORIZED_ACTOR,
           "CLOUD_OWNER_ONLY")
    # 'Re-run jobs' would otherwise repeat chargeable API requests.
    _guard(os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
           "CLOUD_WORKFLOW_RERUN_FORBIDDEN")
    _guard(os.environ.get("DEEPSEEK_ONE_TIME_APPROVED") == "YES_ONLY_TWO_CALLS",
           "CLOUD_EXPLICIT_MANUAL_APPROVAL_MISSING")


def _review_summary(state, intake_result):
    """Machine checks only. Human artistic quality needs real manual scoring."""
    brief = state["tasks"]["director_brief"]["deliverable"]
    script = state["tasks"]["script_edit"]["deliverable"]
    pitch = creative.validate_editorial_pitch(
        intake_result, state,
        intake.episode_source_for_team(readiness.PUBLIC_FICTION, "EP01"))
    proposed = creative.propose_directed_storyboard(
        intake_result, state,
        intake.episode_source_for_team(readiness.PUBLIC_FICTION, "EP01"))
    return {
        "kind": "post_real_two_role_response_structural_review",
        "director_role_passed_schema": True,
        "script_editor_passed_extended_storyboard_schema": True,
        "shot_count": len(proposed["candidate_plan"]["shots"]),
        "shot_coverages_complete": len(pitch["shot_designs"]) ==
                                 len(proposed["candidate_plan"]["shots"]),
        "source_narration_unchanged": [a["narration"] for a in
            proposed["candidate_plan"]["shots"]] == [a["narration"] for a in
            intake_result["plan"]["shots"]],
        "source_edits_applied": False,
        "candidate_needs_author_review": proposed["author_approved"] is False,
        "human_creative_quality_score": None,
        "human_review_needed": True,
        "rubric_weights": RUBRIC,
        "rubric_criteria_score_0_to_5": {k: None for k in RUBRIC},
        "director_brief": deepcopy(brief),
        "script_editor_treatment": deepcopy(script),
        "shot_pitch": deepcopy(pitch),
        "proposed_candidate": deepcopy(proposed),
    }


def run_once_public_fiction(folder, *, api_key):
    """Intentionally charged path, ONLY reachable after the cloud gate.

    Secret comes only from an encrypted GitHub Actions temporary secret.
    Public fictional inputs only. NO attempts to accept a user manuscript.
    """
    _cloud_gate()
    _guard(type(api_key) is str and 10 <= len(api_key) <= 1024
           and "\n" not in api_key and "\r" not in api_key,
           "CLOUD_SECRET_REQUIRED")
    root = Path(folder)
    _guard(not root.exists() or (root.is_dir() and not any(root.iterdir())),
           "CLOUD_OUTPUT_DIRECTORY_NOT_EMPTY")
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "kind": VERSION,
        "status": "NOT_STARTED",
        "fictional_public_story_only": True,
        "source_title": "门后的信",
        "model": readiness.MODEL,
        "planned_max_requests": MAX_REQUESTS,
        "price_reference": readiness.PRICE_OFFICIAL_URL,
        "pricing_may_change": True,
        "requested_cap_cny": readiness.SUGGESTED_TOTAL_CAP_CNY,
        "cap_is_not_guaranteed_provider_invoice_limit": True,
        "prompts_and_api_key_saved_to_artifacts": False,
        "workflow_re_run_is_not_forbidden_by_this_program": True,
        "human_identity_cryptographically_verified": False,
        "real_network_attempts_recorded": 0,
        "replies_accepted": 0,
        "provider_invoice_verified": False,
        "actual_spend_confirmed": False,
        "estimates_cny": [],
        "outcome_by_role": [],
        "release_authorized": False,
        "video_generated": False,
    }
    # Always create a report, including first-call failures. The only user
    # content in this environment is the hard-coded public fictional story.
    first = intake.prepare_episode(readiness.PUBLIC_FICTION, "EP01")
    episode = intake.episode_source_for_team(readiness.PUBLIC_FICTION, "EP01")
    _guard(first["status"] == "editorial_review_required",
           "CLOUD_FICTION_INTAKE_FAILED")
    _guard(team.ready(first["team"]) == ["director_brief"],
           "CLOUD_UNEXPECTED_FIRST_TASK")
    config = pilot.create_pilot_config(
        model=readiness.MODEL,
        source_digest=first["team"]["source_digest"],
        base_digest=first["team"]["base_digest"],
        cap_cny=readiness.SUGGESTED_TOTAL_CAP_CNY,
        cache_hit_cny_m=readiness.PEAK_CNY_PER_M["cache_hit"],
        cache_miss_cny_m=readiness.PEAK_CNY_PER_M["cache_miss"],
        output_cny_m=readiness.PEAK_CNY_PER_M["output"],
        max_output_tokens=readiness.MAX_OUTPUT_TOKENS_PER_ROLE,
        max_attempts=MAX_REQUESTS)
    # Extra hard guard: the one-call preflight's pinned source/price/model
    # must still match what is about to be sent.
    check = readiness.price_director_request()
    _guard(check["episode_source_sha256"] == config["source_digest"]
           and check["base_plan_digest"] == config["base_digest"]
           and check["model"] == config["model"],
           "CLOUD_PREFLIGHT_BINDING_MISMATCH")
    state = first["team"]
    with tempfile.TemporaryDirectory(prefix="one-time-deepseek-spend-ledger-") as tmp:
        with pilot.PilotJournal(tmp, config) as journal:
            for task in TRIAL_ROLES:
                # Intentionally no retry path. The second role is only
                # accessible once a valid first role has been completed.
                _guard(task in team.ready(state), "CLOUD_ROLE_NOT_READY")
                permit = pilot.explicit_pilot_permit(
                    config, task_id=task,
                    revision=state["tasks"][task]["revision"] + 1,
                    acknowledgement=pilot.CONSENT_TEXT,
                    privacy_consent=True, spending_consent=True)
                try:
                    updated, receipt = pilot.run_one_creative_task(
                        first, state, episode, journal,
                        permit=permit,
                        client=pilot.DeepSeekHTTPSClient(timeout_s=45),
                        api_key=api_key, task_id=task)
                    record = journal.summary()["attempts"][-1]
                    report["real_network_attempts_recorded"] = len(
                        journal.summary()["attempts"])
                    report["replies_accepted"] += 1
                    report["estimates_cny"].append(
                        receipt["estimated_usage_cny"])
                    report["outcome_by_role"].append({
                        "role": task, "status": "RESPONSE_ACCEPTED",
                        "total_tokens_reported": receipt["reported_total_tokens"],
                        "estimated_cost_cny": receipt["estimated_usage_cny"],
                        "price_basis": "pinned_peak_fee",
                        "source_or_secret_in_receipt": False})
                    state = updated
                except pilot.PilotError as e:
                    report["real_network_attempts_recorded"] = len(
                        journal.summary()["attempts"])
                    report["status"] = "HALTED_NO_AUTOMATIC_RETRY"
                    report["outcome_by_role"].append({
                        "role": task, "status": "FAILED_SAFE",
                        "error_code": str(e),
                        "manual_vendor_billing_check_needed": True})
                    break
                except Exception:
                    report["real_network_attempts_recorded"] = len(
                        journal.summary()["attempts"])
                    report["status"] = "HALTED_NO_AUTOMATIC_RETRY"
                    report["outcome_by_role"].append({
                        "role": task, "status": "UNKNOWN_ERROR",
                        "error_code": "CLOUD_UNEXPECTED_SAFE_STOP",
                        "manual_vendor_billing_check_needed": True})
                    break
    if report["replies_accepted"] == 1:
        # Preserve a legitimately completed first department so a rejected
        # editor response still leaves useful evidence for human review.
        _json_safe_write(root, "PARTIAL_DIRECTOR_ONLY_PUBLIC_FICTION.json", {
            "kind": "public_fiction_partial_creative_result",
            "status": "EDITOR_NOT_ACCEPTED_DO_NOT_CLAIM_TWO_ROLE_SUCCESS",
            "model": readiness.MODEL,
            "director_brief": deepcopy(
                state["tasks"]["director_brief"]["deliverable"]),
            "human_approved": False,
            "provider_invoice_verified": False,
            "further_paid_requests_authorized": False,
        })
    if report["replies_accepted"] == 2:
        try:
            review = _review_summary(state, first)
            _json_safe_write(root, "REAL_DEEPSEEK_PUBLIC_FICTION_ROLE_OUTPUTS.json",
                             review)
            report["status"] = "TWO_VALID_RESPONSES_NEED_HUMAN_QUALITY_REVIEW"
        except Exception:
            report["status"] = "TWO_RESPONSES_BUT_REVIEW_COMPILATION_FAILED"
    _json_safe_write(root, "REAL_DEEPSEEK_ONE_TIME_RUN_RECEIPT.json", report)
    _json_safe_write(root, "README_PUBLIC_FICTION_ONLY.json", {
        "warning": "PUBLIC GitHub artifact. Fictional source only. The model responses are untrusted and NOT human approved.",
        "secret_never_in_artifact": True,
        "model_requests_not_equivalent_to_video_generation": True,
        "user_must_revoke_key_and_delete_gitHub_secret_after_run": True,
        "provider_bill_must_be_checked_separately": True,
        "no_automatic_retries": True,
    })
    # Safe log only; report's output file has typed error codes and summary.
    print("DEEPSEEK_ONE_TIME_CLOUD_TRIAL_COMPLETE: status=%s attempts=%s accepted=%s" %
          (report["status"], report["real_network_attempts_recorded"],
           report["replies_accepted"]))
    return report


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Manually authorized one-time DeepSeek public fiction cloud test")
    sub = p.add_mutually_exclusive_group(required=True)
    sub.add_argument("--offline-preflight", action="store_true")
    sub.add_argument("--execute-once", action="store_true")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        out = Path(args.out)
        if args.offline_preflight:
            # This path must remain CI-safe with no secret, token or API calls.
            if out.exists():
                raise CloudTrialError("CLOUD_PREVIEW_PATH_EXISTS")
            out.mkdir(parents=True)
            _json_safe_write(out, "REAL_TEST_PREVIEW_ONLY_NO_CALL.json",
                             readiness.price_director_request())
            print("DEEPSEEK_ONE_TIME_CLOUD_PREFLIGHT_ONLY: network_calls=0")
            return 0
        key = os.environ.get("DEEPSEEK_ONE_TIME_API_KEY")
        result = run_once_public_fiction(out, api_key=key)
        return 0 if result["status"] == (
            "TWO_VALID_RESPONSES_NEED_HUMAN_QUALITY_REVIEW") else 2
    except (OSError, ValueError, TypeError):
        print("DEEPSEEK_ONE_TIME_CLOUD_SAFE_STOP", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
