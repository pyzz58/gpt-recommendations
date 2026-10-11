#!/usr/bin/env python3
"""DENY-BY-DEFAULT DeepSeek pilot: one authorized creative department per call.

Unlike agent_durable_preflight (which is *strictly offline*), this module has a
real HTTPS transport. It is NEVER imported or used by the existing offline
executor. No CLI/autostart, no reading env/keys, no retries, no media jobs.
A private authenticated app must secure actual per-task user consent BEFORE
creating a permit or dispatching a message. This module cannot authenticate
user identities or confirm vendor pricing; it must not claim it can.

GITHUB CI tests use only StaticHTTPSFrame (network_calls=0).
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_UP
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import ssl
import stat
import tempfile

import agent_team as team
import agent_role_contracts as roles
import agent_provider_wire as wire
import role_schema_guard as schema_guard
import editorial_storyboard as creative

VERSION = "deepseek-single-task-pilot-v1"
MAX_RESPONSE_BYTES = wire.MAX_WIRE_BYTES
QUANT = Decimal("0.00000001")
MILLION = Decimal(1000000)
CREATIVE_TASKS = frozenset({"director_brief", "script_edit"})
# Additional downstream roles are dispatched ONLY from a source-locked team;
# do not route them through the original unapproved creative-intake entrypoint.
PILOT_TASKS = frozenset(team.SPECS)
BLOCKED_STATES = frozenset({
    "pending_uncertain", "timeout_unknown", "transport_unknown",
    "usage_overrun_requires_review",
})
FINAL_STATES = frozenset({"response_rejected", "response_accepted"}) | BLOCKED_STATES
CONSENT_TEXT = "AUTHORIZE_ONE_PRIVATE_DEEPSEEK_TEXT_CALL"


class PilotError(ValueError):
    """Privacy-safe errors contain only fixed identifiers."""


def _fingerprint(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def _check(cond, message):
    if not cond:
        raise PilotError(message)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _amount(value, label):
    try:
        result = Decimal(str(value))
    except Exception:
        raise PilotError("PILOT_INVALID_" + label) from None
    _check(result.is_finite() and result > 0 and result <= Decimal("1000000"),
           "PILOT_INVALID_" + label)
    return result


def create_pilot_config(*, model, source_digest, base_digest, cap_cny,
                        max_output_tokens, cache_hit_cny_m,
                        cache_miss_cny_m, output_cny_m, max_attempts=2):
    """Explicit ceilings, NOT spend permission. Pricing is operator-supplied."""
    _check(model in wire.MODEL_NAMES, "PILOT_MODEL_NOT_VERIFIED")
    for name, digest in (("source", source_digest), ("base", base_digest)):
        _check(isinstance(digest, str) and len(digest) == 64 and
               all(x in "0123456789abcdef" for x in digest),
               "PILOT_INVALID_" + name.upper() + "_DIGEST")
    _check(type(max_output_tokens) is int and
           1 <= max_output_tokens <= 65536, "PILOT_OUTPUT_TOKEN_LIMIT")
    _check(type(max_attempts) is int and
           1 <= max_attempts <= 10, "PILOT_ATTEMPT_LIMIT")
    hit = _amount(cache_hit_cny_m, "CACHE_HIT_PRICE")
    miss = _amount(cache_miss_cny_m, "CACHE_MISS_PRICE")
    output = _amount(output_cny_m, "OUTPUT_PRICE")
    _check(hit <= miss, "PILOT_CACHE_PRICING_INCONSISTENT")
    return {
        "version": VERSION, "provider": "deepseek",
        "model": model, "source_digest": source_digest,
        "base_digest": base_digest, "cap_cny": str(_amount(cap_cny, "CAP")),
        "cache_hit_cny_m": str(hit), "cache_miss_cny_m": str(miss),
        "output_cny_m": str(output), "max_output_tokens": max_output_tokens,
        "max_attempts": max_attempts, "private_data_in_config": False,
        "authorization_in_config": False,
    }


def explicit_pilot_permit(config, *, task_id, acknowledgement,
                          privacy_consent, spending_consent, revision=1):
    """One-task intent evidence only; NOT identity verification or signature.

    Must be created only by a trusted, authenticated private user interface
    *after* disclosing endpoint, transfer content and maximum reserved charge.
    Never derive it from the user's generic 'continue' message.
    """
    _check(isinstance(config, dict) and config.get("version") == VERSION,
           "PILOT_CONFIG_REQUIRED")
    _check(task_id in PILOT_TASKS, "PILOT_ROLE_OUT_OF_SCOPE")
    _check(type(revision) is int and 1 <= revision <= 1000000,
           "PILOT_PERMIT_REVISION_INVALID")
    _check(acknowledgement == CONSENT_TEXT and
           privacy_consent is True and spending_consent is True,
           "PILOT_EXPLICIT_CONSENT_MISSING")
    return {
        "kind": "per_task_operator_consent", "version": VERSION,
        "task_id": task_id, "revision": revision,
        "config_digest": _fingerprint(config),
        "source_digest": config["source_digest"],
        "base_digest": config["base_digest"],
        "model": config["model"], "max_reserved_cny": config["cap_cny"],
        "private_transfer_consent": True, "spending_consent": True,
        "one_task_only": True,
        "identity_cryptographically_verified": False,
    }


class PilotJournal:
    """Separate live-capable durable ledger, NOT the offline journal.

    The attempt is fsync'ed BEFORE network send. Closed/unknown attempts are
    not auto-refunded, resent or replayed. A network timeout may have billed.
    Its on-disk records contain only hashes, usage counters and prices.
    """

    def __init__(self, directory, config):
        _check(isinstance(config, dict), "PILOT_INVALID_CONFIG")
        checked = create_pilot_config(
            model=config.get("model"), source_digest=config.get("source_digest"),
            base_digest=config.get("base_digest"), cap_cny=config.get("cap_cny"),
            cache_hit_cny_m=config.get("cache_hit_cny_m"),
            cache_miss_cny_m=config.get("cache_miss_cny_m"),
            output_cny_m=config.get("output_cny_m"),
            max_output_tokens=config.get("max_output_tokens"),
            max_attempts=config.get("max_attempts"))
        _check(config == checked, "PILOT_CONFIG_NOT_CANONICAL")
        self.config = deepcopy(checked)
        self.digest = _fingerprint(checked)
        self.path = Path(directory)
        _check(not self.path.is_symlink(), "PILOT_JOURNAL_SYMLINK")
        self.path.mkdir(mode=0o700, parents=True, exist_ok=True)
        _check(self.path.is_dir(), "PILOT_JOURNAL_DIR_INVALID")
        self.journal = self.path / "crew_live_pilot.journal.json"
        lock_path = self.path / "crew_live_pilot.journal.lock"
        _check(not self.journal.is_symlink() and not lock_path.is_symlink(),
               "PILOT_JOURNAL_SYMLINK")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        self.fd = os.open(lock_path, flags, 0o600)
        self.closed = False
        self.poisoned = False
        try:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise PilotError("PILOT_JOURNAL_ALREADY_LOCKED") from None
            os.fchmod(self.fd, 0o600)
            if self.journal.exists():
                _check(stat.S_ISREG(self.journal.stat().st_mode),
                       "PILOT_JOURNAL_NOT_REGULAR")
                try:
                    self.records = json.loads(self.journal.read_text("utf-8"))
                except (ValueError, OSError):
                    raise PilotError("PILOT_JOURNAL_CORRUPTED") from None
            else:
                self.records = {
                    "version": VERSION, "config_digest": self.digest,
                    "attempts": [], "live_capable": True,
                    "prompt_text_recorded": False,
                    "provider_billing_not_verified": True,
                }
                self._save()
            self._validate()
        except Exception:
            self.close()
            raise

    def close(self):
        if not self.closed:
            self.closed = True
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, exctype, exc, traceback):
        self.close()

    def _validate(self):
        _check(not self.closed and not self.poisoned and
               self.digest == _fingerprint(self.config),
               "PILOT_LEDGER_CLOSED_OR_MODIFIED")
        data = self.records
        _check(isinstance(data, dict) and
               data.get("version") == VERSION and
               data.get("config_digest") == self.digest and
               data.get("live_capable") is True and
               data.get("prompt_text_recorded") is False and
               isinstance(data.get("attempts"), list),
               "PILOT_LEDGER_INTEGRITY")
        seen, spent = set(), Decimal(0)
        attempts = data["attempts"]
        _check(len(attempts) <= self.config["max_attempts"],
               "PILOT_LEDGER_TOO_MANY_ATTEMPTS")
        for idx, rec in enumerate(attempts, 1):
            _check(isinstance(rec, dict) and rec.get("id") == idx
                   and rec.get("task_id") in PILOT_TASKS
                   and type(rec.get("revision")) is int
                   and rec["revision"] >= 1
                   and rec.get("status") in (FINAL_STATES | {"pending_uncertain"})
                   and isinstance(rec.get("request_digest"), str)
                   and len(rec["request_digest"]) == 64,
                   "PILOT_LEDGER_INVALID_RECORD")
            t = (rec["task_id"], rec["revision"])
            _check(t not in seen, "PILOT_DUPLICATE_ROLE_REVISION")
            seen.add(t)
            spent += _amount(rec.get("reserved_cny"), "RECORDED_RESERVATION")
        _check(spent <= Decimal(self.config["cap_cny"]),
               "PILOT_LEDGER_OVER_CAP")

    def _save(self):
        self._validate()
        raw = json.dumps(self.records, sort_keys=True, ensure_ascii=False,
                         allow_nan=False, indent=2).encode("utf-8") + b"\n"
        handle, name = tempfile.mkstemp(prefix=".crew_live_pilot.",
                                         suffix=".tmp", dir=self.path)
        try:
            with os.fdopen(handle, "wb") as fp:
                os.fchmod(fp.fileno(), 0o600)
                fp.write(raw)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(name, self.journal)
            df = os.open(self.path, os.O_RDONLY)
            try:
                os.fsync(df)
            finally:
                os.close(df)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _quote(self, request):
        body = json.dumps(request["body"], ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
        # UTF-8 bytes + overhead is a conservative PROXY, not the provider
        # tokenizer. Underestimation is caught only AFTER provider responds.
        input_proxy = len(body) + 1024
        estimate = (
            Decimal(input_proxy) * Decimal(self.config["cache_miss_cny_m"]) +
            Decimal(self.config["max_output_tokens"]) *
            Decimal(self.config["output_cny_m"])) / MILLION
        amount = estimate.quantize(QUANT, rounding=ROUND_UP)
        return {
            "request_digest": hashlib.sha256(body).hexdigest(),
            "estimated_input_tokens_proxy": input_proxy,
            "reserved_cny": str(amount),
            "reservation_not_invoice": True,
        }

    def reserve(self, task_id, revision, request):
        self._validate()
        _check(task_id in PILOT_TASKS and
               type(revision) is int and revision >= 1,
               "PILOT_INVALID_TASK_OR_REVISION")
        _check(request.get("body", {}).get("model") == self.config["model"],
               "PILOT_MODEL_DRIFT")
        _check(not any(x["status"] in BLOCKED_STATES
                       for x in self.records["attempts"]),
               "PILOT_UNKNOWN_ATTEMPT_BLOCKS_NEXT")
        _check(not any(x["task_id"] == task_id and x["revision"] == revision
                       for x in self.records["attempts"]),
               "PILOT_NO_AUTOMATIC_RETRY")
        _check(len(self.records["attempts"]) < self.config["max_attempts"],
               "PILOT_TOO_MANY_ATTEMPTS")
        quote = self._quote(request)
        spent = sum((Decimal(x["reserved_cny"])
                     for x in self.records["attempts"]), Decimal("0"))
        _check(spent + Decimal(quote["reserved_cny"]) <=
               Decimal(self.config["cap_cny"]), "PILOT_CAP_BEFORE_SEND")
        record = {
            "id": len(self.records["attempts"]) + 1,
            "task_id": task_id, "revision": revision, **quote,
            "status": "pending_uncertain",
        }
        self.records["attempts"].append(record)
        try:
            self._save()
        except Exception:
            self.records["attempts"].pop()
            raise
        return record["id"]

    def finish(self, record_id, status, usage=None):
        self._validate()
        _check(type(record_id) is int and 1 <= record_id <=
               len(self.records["attempts"]), "PILOT_RECORD_NOT_FOUND")
        _check(status in FINAL_STATES, "PILOT_INVALID_FINISH_STATUS")
        rec = self.records["attempts"][record_id - 1]
        _check(rec["status"] == "pending_uncertain",
               "PILOT_ATTEMPT_ALREADY_FINISHED")
        # Verify all caller-supplied usage BEFORE altering the ledger.
        # If durable commit fails, forbid further attempts with this journal
        # instance: the disk rename might have succeeded before fsync failed.
        if usage is not None:
            _check(isinstance(usage, dict) and
                   type(usage.get("total_tokens")) is int and
                   usage["total_tokens"] >= 0 and
                   isinstance(usage.get("estimated_usage_cost_cny"), str),
                   "PILOT_USAGE_INVALID")
            try:
                actual = Decimal(usage["estimated_usage_cost_cny"])
            except Exception:
                raise PilotError("PILOT_USAGE_INVALID") from None
            _check(actual.is_finite() and actual >= 0,
                   "PILOT_USAGE_INVALID")
        original = deepcopy(rec)
        rec["status"] = status
        if usage is not None:
            rec["reported_tokens"] = usage["total_tokens"]
            rec["usage_estimate_cny"] = usage["estimated_usage_cost_cny"]
        try:
            self._save()
        except Exception:
            # A failed _save is not proof that the provider wasn't billed,
            # and the filesystem rename might have already happened.
            # Refuse any additional operation until manually reconciled.
            self.records["attempts"][record_id - 1] = original
            self.poisoned = True
            raise

    def summary(self):
        self._validate()
        return {
            "mode": VERSION, "config_digest": self.digest,
            "attempts": deepcopy(self.records["attempts"]),
            "reserved_cny": str(sum((
                Decimal(r["reserved_cny"]) for r in self.records["attempts"]),
                Decimal(0))), "cap_cny": self.config["cap_cny"],
            "invoice_verified": False,
            "private_prompts_in_ledger": False,
            "human_identity_verified": False,
        }


class DeepSeekHTTPSClient:
    """One strict HTTPS POST to a fixed DeepSeek host. No redirects/retries.

    Reads a secret supplied by a trusted private caller only. No environment
    auto-discovery, arbitrary URL, hooks or recursive HTTP retries.
    """

    def __init__(self, *, timeout_s=45):
        _check(type(timeout_s) is int and 5 <= timeout_s <= 120,
               "PILOT_INVALID_TIMEOUT")
        self.timeout_s = timeout_s

    def complete(self, request, api_key):
        _check(type(api_key) is str and api_key.strip() and
               "\r" not in api_key and "\n" not in api_key,
               "PILOT_PRIVATE_API_KEY_MISSING")
        _check(request.get("endpoint") == wire.ENDPOINT and
               request.get("method") == "POST" and
               request.get("body", {}).get("model") in wire.MODEL_NAMES,
               "PILOT_INVALID_DESTINATION")
        payload = json.dumps(request["body"], ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        _check(len(payload) <= wire.MAX_WIRE_BYTES,
               "PILOT_REQUEST_TOO_LARGE")
        # Fixed host and path; http.client does not follow HTTP redirects.
        connection = http.client.HTTPSConnection(
            "api.deepseek.com", port=443, timeout=self.timeout_s,
            context=ssl.create_default_context())
        try:
            connection.request(
                "POST", "/chat/completions", body=payload,
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "ai-director-private-pilot/1",
                })
            response = connection.getresponse()
            if response.status != 200:
                # Don't read/print provider errors: may echo private prompts.
                raise PilotError("PILOT_PROVIDER_NON_200")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            _check(len(body) <= MAX_RESPONSE_BYTES,
                   "PILOT_RESPONSE_TOO_LARGE")
            return body
        finally:
            connection.close()


class StaticHTTPSFrame:
    """Exact-class offline fake, never opens a connection. For CI only."""

    def __init__(self, frame):
        self.frame = deepcopy(frame)
        self.calls = 0

    def complete(self, request, api_key):
        _check(api_key is None, "PILOT_FAKE_MUST_NOT_RECEIVE_KEY")
        self.calls += 1
        if self.frame == "TIMEOUT":
            raise TimeoutError("PILOT_SIMULATED_TIMEOUT")
        if self.frame == "CONNECTION":
            raise ConnectionError("PILOT_SIMULATED_NETWORK_UNCERTAINTY")
        return deepcopy(self.frame)


def run_one_creative_task(intake, state, episode_source, journal,
                          permit=None, client=None, *, api_key=None,
                          task_id=None, result_vault=None):
    """Perform at most ONE request, returning new state + nonprivate receipt.

    Call ONLY after private app verifies specific human consent, provider,
    costs, source transfer and budget. Not an autonomous 10-agent executor.
    Never auto-resume or retry if response is bad or transport uncertain.
    """
    _check(type(journal) is PilotJournal, "PILOT_DURABLE_JOURNAL_REQUIRED")
    _check(type(client) in (DeepSeekHTTPSClient, StaticHTTPSFrame),
           "PILOT_TRANSPORT_NOT_ALLOWED")
    _check(isinstance(permit, dict) and permit.get("kind") ==
           "per_task_operator_consent" and permit.get("version") == VERSION and
           permit.get("config_digest") == journal.digest and
           permit.get("private_transfer_consent") is True and
           permit.get("spending_consent") is True and
           permit.get("one_task_only") is True,
           "PILOT_EXPLICIT_CONSENT_MISSING")
    config = journal.config
    _check(permit.get("source_digest") == config["source_digest"] and
           permit.get("base_digest") == config["base_digest"] and
           permit.get("model") == config["model"] and
           permit.get("max_reserved_cny") == config["cap_cny"],
           "PILOT_PERMIT_WRONG_SCOPE")
    _check(type(episode_source) is str and
           _sha(episode_source) == config["source_digest"],
           "PILOT_BASE_OR_SOURCE_CHANGED")
    try:
        plan, original = creative._ensure_source(intake, episode_source)
    except (KeyError, TypeError, ValueError):
        raise PilotError("PILOT_INTAKE_SOURCE_OR_VERSION_INVALID") from None
    _check(team.fingerprint(plan) == config["base_digest"],
           "PILOT_BASE_OR_SOURCE_CHANGED")
    _check(isinstance(state, dict) and
           state.get("base_digest") == config["base_digest"] and
           state.get("source_digest") == config["source_digest"],
           "PILOT_TEAM_VERSION_CHANGED")
    available = team.ready(state)
    target = available[0] if task_id is None and available else task_id
    _check(target in CREATIVE_TASKS and target in available and
           permit.get("task_id") == target,
           "PILOT_TASK_NOT_ALLOWED")
    if target == "director_brief":
        req = creative.build_director_brief_request(intake, episode_source)
    else:
        req = creative.build_script_editor_request(intake, state, episode_source)
    _check(permit.get("revision") == req["next_revision"],
           "PILOT_PERMIT_WRONG_REVISION")
    envelope = wire.prepare_chat_request(
        req["messages"], model=config["model"],
        max_output_tokens=config["max_output_tokens"])
    # Validate the EXACT prompt-declared JSON Schema before any billable
    # request. The extended script_editor storyboard schema is not merely
    # advisory: it is enforced again on the received reply below.
    try:
        schema_guard.preflight_schema(req["output_json_schema"])
    except ValueError:
        raise PilotError("PILOT_SCHEMA_PREFLIGHT_REJECTED_BEFORE_SEND") from None
    # Even for a synthetic frame, require an explicit separate one-call
    # consent permit. A missing key is only allowed for offline CI frames.
    if type(client) is DeepSeekHTTPSClient:
        _check(type(api_key) is str and api_key.strip(),
               "PILOT_PRIVATE_API_KEY_MISSING")
    else:
        _check(api_key is None, "PILOT_NO_SECRETS_IN_FIXTURE")
    # Real paid responses must be recoverable from PRIVATE durable storage.
    # LangGraph's checkpoint / pending-write separation is the inspiration,
    # not a new dependency or automatic network replay.
    if type(client) is DeepSeekHTTPSClient or result_vault is not None:
        from private_result_checkpoint import PrivateResultVault
        _check(type(result_vault) is PrivateResultVault and
               result_vault.journal is journal,
               "PILOT_PRIVATE_RESULT_VAULT_REQUIRED")
        try:
            result_vault.assert_existing_accepted_checkpoint_chain(state)
        except Exception:
            raise PilotError("PILOT_PRIVATE_RESULT_CHAIN_NOT_SAFE") from None
    record_id = journal.reserve(target, req["next_revision"], envelope)
    parsed = None
    try:
        raw = client.complete(envelope, api_key)
    except TimeoutError:
        journal.finish(record_id, "timeout_unknown")
        raise PilotError("PILOT_TIMEOUT_CHARGE_UNKNOWN") from None
    except Exception:
        journal.finish(record_id, "transport_unknown")
        raise PilotError("PILOT_NETWORK_OR_PROVIDER_STATUS_UNKNOWN") from None
    try:
        parsed = wire.parse_chat_completion(
            raw, expected_model=config["model"],
            max_output_tokens=config["max_output_tokens"],
            hit_price_cny_m=config["cache_hit_cny_m"],
            miss_price_cny_m=config["cache_miss_cny_m"],
            output_price_cny_m=config["output_cny_m"])
        schema_guard.validate_contract(
            req["output_json_schema"],
            roles.parse_strict_json(parsed["content"]))
        cost = Decimal(parsed["usage"]["estimated_usage_cost_cny"])
        reserve = Decimal(journal.records["attempts"][record_id-1]["reserved_cny"])
        if cost > reserve:
            journal.finish(record_id, "usage_overrun_requires_review",
                           usage=parsed["usage"])
            raise PilotError("PILOT_USAGE_OVERRUN_NEEDS_RECONCILIATION")
        if target == "director_brief":
            updated = creative.submit_director_brief(
                intake, episode_source, parsed["content"])
        else:
            updated = creative.submit_creative_script_edit(
                intake, state, episode_source, parsed["content"])
    except Exception:
        if journal.records["attempts"][record_id - 1]["status"] == "pending_uncertain":
            journal.finish(record_id, "response_rejected",
                           usage=parsed["usage"] if parsed is not None else None)
        raise PilotError("PILOT_RESPONSE_REJECTED_NO_RETRY") from None
    # Checkpoint the *whole* validated state BEFORE marking the model call
    # accepted in the billing journal; network is NEVER automatically retried.
    if result_vault is not None:
        try:
            result_vault.save(record_id, state, updated, usage=parsed["usage"])
        except Exception:
            raise PilotError("PILOT_RESULT_CHECKPOINT_UNCERTAIN_NO_RETRY") from None
    try:
        journal.finish(record_id, "response_accepted", usage=parsed["usage"])
    except Exception:
        raise PilotError("PILOT_LEDGER_COMMIT_UNCERTAIN_RECOVERY_REQUIRED") from None
    return updated, {
        "kind": VERSION, "task_id": target, "revision": req["next_revision"],
        "model": config["model"], "provider": "deepseek",
        "transport": "real_https" if type(client) is DeepSeekHTTPSClient else "synthetic_fixture",
        "network_attempted": type(client) is DeepSeekHTTPSClient,
        "reported_total_tokens": parsed["usage"]["total_tokens"],
        "estimated_usage_cny": parsed["usage"]["estimated_usage_cost_cny"],
        "provider_invoice_verified": False,
        "source_or_response_in_receipt": False,
        "paid_media_generated": False,
        "publisher_approved": False,
        "human_identity_cryptographically_verified": False,
    }
