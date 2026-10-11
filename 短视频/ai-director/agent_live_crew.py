#!/usr/bin/env python3
"""Source-locked ten-department DeepSeek SINGLE-ROLE dispatch interface.

CAUTION: This contains a real HTTPS-capable path, but NO main(), background
worker, auto runner, payment permission, public repository upload or login.
Every call requires a separate operator permit, revision and budget journal.
GitHub CI exercises ONLY StaticHTTPSFrame. A consent dictionary IS NOT proof
of a verified human identity; a trustworthy private application must check it.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import agent_live_pilot as pilot
import agent_team as team
import agent_executor
import agent_role_contracts as roles
import agent_handoff_audit as handoff
import agent_creative_review as creative_review
import creative_production_handoff as creative_bridge
import agent_provider_wire as wire
import role_schema_guard as schema_guard
import editorial_review_lock as locks

VERSION = "locked-ten-role-pilot-v1"


def _check(ok, code):
    if not ok:
        raise pilot.PilotError(code)


def inspect_locked_role(snapshot, episode_source, state, task_id):
    """Offline role readiness and QA preview; no prompt/secret is returned.

    The decision and locked snapshot must have the exact matching source/base;
    a candidate decision is not proof of author identity or API permission.
    """
    try:
        locked = locks.stage_locked_team(snapshot, episode_source)
        base = snapshot["plan"]
        team._check_state(state)
        _check(state["base_digest"] == locked["plan_digest"],
               "PILOT_LOCKED_PLAN_VERSION_MISMATCH")
        _check(state["source_digest"] == locked["source_digest"] and
               state["source_review_bound"] is True,
               "PILOT_LOCKED_SOURCE_VERSION_MISMATCH")
        _check(team.fingerprint(base) == locked["plan_digest"],
               "PILOT_LOCKED_BASE_DRIFT")
        ready = team.ready(state)
    except pilot.PilotError:
        raise
    except (ValueError, KeyError, TypeError):
        raise pilot.PilotError("PILOT_LOCKED_SNAPSHOT_OR_TEAM_INVALID") from None
    _check(task_id in team.SPECS and task_id in ready,
           "PILOT_TASK_NOT_READY")
    status = None
    if task_id in ("quality_review", "director_final"):
        findings = handoff.audit_handoffs(state, base)
        structure = creative_review.review_team(state, base)
        status = {
            "handoff_status": findings["status"],
            "handoff_blocking_count": sum(x["severity"] == "blocker"
                                          for x in findings["issues"]),
            "creative_review_status": structure["status"],
            "creative_blocking_count": sum(x["severity"] == "blocker"
                                          for x in structure["findings"]),
        }
    return {
        "version": VERSION, "task_id": task_id,
        "next_revision": state["tasks"][task_id]["revision"] + 1,
        "source_digest": locked["source_digest"],
        "plan_digest": locked["plan_digest"],
        "stage_ready": True,
        "first_director_vision_bound": True,
        "preproduction_gap_count": snapshot["production_preflight"]["issue_count"],
        "preflight_review": status,
        "actor_camera_audio_work_fully_verified": False,
        "human_identity_verified": False,
        "actual_api_calls": 0, "paid_dispatch_authorized": False,
    }


def run_one_locked_role(snapshot, episode_source, state, journal, *,
                        permit=None, client=None, api_key=None, task_id,
                        result_vault=None):
    """One role, one declared revision, one budget reserve and one transport.

    No loop, no silent role switching, no retry, no approval shortcut.
    Production-model dispatch MUST come from authenticated private runtime
    after checking transfer and CNY cap. Script text must NOT be sent by CI.
    """
    _check(type(journal) is pilot.PilotJournal,
           "PILOT_DURABLE_JOURNAL_REQUIRED")
    _check(type(client) in (pilot.DeepSeekHTTPSClient, pilot.StaticHTTPSFrame),
           "PILOT_TRANSPORT_NOT_ALLOWED")
    _check(isinstance(permit, dict) and permit.get("kind") ==
           "per_task_operator_consent" and permit.get("version") == pilot.VERSION
           and permit.get("config_digest") == journal.digest
           and permit.get("private_transfer_consent") is True
           and permit.get("spending_consent") is True
           and permit.get("one_task_only") is True,
           "PILOT_EXPLICIT_CONSENT_MISSING")
    config = journal.config
    _check(permit.get("task_id") == task_id and
           permit.get("source_digest") == config["source_digest"] and
           permit.get("base_digest") == config["base_digest"] and
           permit.get("model") == config["model"] and
           permit.get("max_reserved_cny") == config["cap_cny"],
           "PILOT_PERMIT_WRONG_SCOPE")
    check = inspect_locked_role(snapshot, episode_source, state, task_id)
    _check(check["source_digest"] == config["source_digest"] and
           check["plan_digest"] == config["base_digest"],
           "PILOT_JOURNAL_WRONG_LOCKED_VERSION")
    _check(permit.get("revision") == check["next_revision"],
           "PILOT_PERMIT_WRONG_REVISION")
    # QA can inspect problems and recommend revisions; only a FINAL outcome
    # saying 'ready' must be prevented when known blockers are outstanding.
    base = snapshot["plan"]
    try:
        prompt = roles.build_role_messages(
            base, state, task_id, source_text=episode_source,
            editorial_handoff=snapshot["creative_handoff"])
        envelope = wire.prepare_chat_request(
            prompt["messages"], model=config["model"],
            max_output_tokens=config["max_output_tokens"])
        # A broken or unavailable JSON Schema validator must be caught
        # BEFORE an irreversible billable provider request.
        schema_guard.preflight_schema(prompt["output_json_schema"])
    except (ValueError, TypeError, KeyError):
        raise pilot.PilotError("PILOT_ROLE_PROMPT_INVALID") from None
    if type(client) is pilot.DeepSeekHTTPSClient:
        _check(type(api_key) is str and api_key.strip(),
               "PILOT_PRIVATE_API_KEY_MISSING")
    else:
        _check(api_key is None, "PILOT_NO_SECRETS_IN_FIXTURE")
    if type(client) is pilot.DeepSeekHTTPSClient or result_vault is not None:
        from private_result_checkpoint import PrivateResultVault
        _check(type(result_vault) is PrivateResultVault and
               result_vault.journal is journal,
               "PILOT_PRIVATE_RESULT_VAULT_REQUIRED")
        try:
            result_vault.assert_existing_accepted_checkpoint_chain(state)
        except Exception:
            raise pilot.PilotError("PILOT_PRIVATE_RESULT_CHAIN_NOT_SAFE") from None
    record_id = journal.reserve(task_id, check["next_revision"], envelope)
    parsed = None
    try:
        response = client.complete(envelope, api_key)
    except TimeoutError:
        journal.finish(record_id, "timeout_unknown")
        raise pilot.PilotError("PILOT_TIMEOUT_CHARGE_UNKNOWN") from None
    except Exception:
        journal.finish(record_id, "transport_unknown")
        raise pilot.PilotError("PILOT_NETWORK_OR_PROVIDER_STATUS_UNKNOWN") from None
    try:
        parsed = wire.parse_chat_completion(
            response, expected_model=config["model"],
            max_output_tokens=config["max_output_tokens"],
            hit_price_cny_m=config["cache_hit_cny_m"],
            miss_price_cny_m=config["cache_miss_cny_m"],
            output_price_cny_m=config["output_cny_m"])
        if Decimal(parsed["usage"]["estimated_usage_cost_cny"]) > Decimal(
                journal.records["attempts"][record_id-1]["reserved_cny"]):
            journal.finish(record_id, "usage_overrun_requires_review",
                           usage=parsed["usage"])
            raise pilot.PilotError("PILOT_USAGE_OVERRUN_REQUIRES_REVIEW")
        if task_id in ("quality_review", "director_final"):
            # The source-aware existing independent audit explicitly forbids
            # accepting conflicting handoffs; QA may report 'revise' instead.
            draft = roles.validate_role_output(
                base, state, task_id, parsed["content"],
                source_text=episode_source,
                editorial_handoff=snapshot["creative_handoff"])
            agent_executor._enforce_base_audit(state, base, task_id, draft)
            if task_id == "director_final" and (
                    draft["director_decision"]["decision"] ==
                    "ready_for_user_review"):
                _check(
                    check["preflight_review"]["creative_review_status"] !=
                    "blocked",
                    "PILOT_CREATIVE_QA_BLOCKS_FINAL_ACCEPTANCE")
                _check(state["tasks"]["quality_review"]["deliverable"]
                       ["qa_report"].get("recommendation") ==
                       "ready_for_director_review",
                       "PILOT_QA_REVISIONS_BLOCK_FINAL_ACCEPTANCE")
        updated = roles.submit_role_output(
            base, state, task_id, parsed["content"],
            source_text=episode_source,
            editorial_handoff=snapshot["creative_handoff"])
        if task_id == "camera_art":
            # A scoped rework is merged with *previous* shots. Audit that
            # resulting complete scene geometry, not only the revised shot,
            # so a door cannot teleport across a legitimate partial revision.
            creative_bridge.camera_requirements_for_role(
                base, updated["tasks"]["camera_art"]["deliverable"])
    except Exception:
        if journal.records["attempts"][record_id-1]["status"] == "pending_uncertain":
            journal.finish(
                record_id, "response_rejected",
                usage=parsed["usage"] if parsed is not None else None)
        raise pilot.PilotError("PILOT_SPECIALIST_RESPONSE_REJECTED_NO_RETRY") from None
    if result_vault is not None:
        try:
            result_vault.save(record_id, state, updated, usage=parsed["usage"])
        except Exception:
            raise pilot.PilotError(
                "PILOT_RESULT_CHECKPOINT_UNCERTAIN_NO_RETRY") from None
    try:
        journal.finish(record_id, "response_accepted", usage=parsed["usage"])
    except Exception:
        raise pilot.PilotError(
            "PILOT_LEDGER_COMMIT_UNCERTAIN_RECOVERY_REQUIRED") from None
    return updated, {
        "version": VERSION, "task_id": task_id,
        "revision": check["next_revision"],
        "model": config["model"],
        "transport": ("real_https" if type(client) is pilot.DeepSeekHTTPSClient
                      else "synthetic_fixture"),
        "network_attempted": type(client) is pilot.DeepSeekHTTPSClient,
        "provider_reported_total_tokens": parsed["usage"]["total_tokens"],
        "estimated_usage_cny": parsed["usage"]["estimated_usage_cost_cny"],
        "source_or_prompt_in_receipt": False,
        "provider_invoice_verified": False,
        "media_created": False, "human_approved": False,
        "publication_allowed": False,
    }


def locked_crew_overview(snapshot, episode_source, state):
    """Safe coordination summary for manual task selection (no model calls)."""
    locked = locks.stage_locked_team(snapshot, episode_source)
    _check(isinstance(state, dict) and
           state.get("base_digest") == locked["plan_digest"] and
           state.get("source_digest") == locked["source_digest"],
           "PILOT_TEAM_NOT_BOUND_TO_LOCK")
    team._check_state(state)
    ready = team.ready(state)
    return {
        "kind": VERSION,
        "ready_tasks": ready,
        "completed_tasks": [t for t in team.SPECS
                            if state["tasks"][t]["status"] == "completed"],
        "open_tasks": [t for t in team.SPECS
                       if state["tasks"][t]["status"] != "completed"],
        "source_digest": locked["source_digest"],
        "base_digest": locked["plan_digest"],
        "next_step_requires_independent_task_permit": bool(ready),
        "automatic_dispatch_enabled": False,
        "model_requests_executed_by_this_function": 0,
        "media_created": False, "human_approved": False,
    }
