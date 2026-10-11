#!/usr/bin/env python3
"""Offline write-ahead, crash-safe reservation harness for prospective AI calls.

No HTTP, SDK, credentials or billable invocations. The only response adapter is
an exact synthetic OfflineResponseFrames object. Records contain no prompt,
private script, model response or API key. File-locking covers one journal.
Reserving MUST be durable before even mock delivery; interrupted attempts are
NEVER replayed automatically.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_UP
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

import agent_team as team
import agent_role_contracts as roles
import agent_provider_wire as wire

JOURNAL_VERSION = "crew-private-preflight-v1"
PER_MILLION = Decimal("1000000")
QUANT = Decimal("0.00000001")
BLOCKING_STATUSES = frozenset({"pending_uncertain", "timeout_unknown",
                               "transport_unknown", "usage_overrun_requires_review"})


class DurablePreflightError(ValueError):
    """No private text or raw provider data is added to errors."""


def _sha(data):
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _int(value, name, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise DurablePreflightError("INVALID_" + name.upper())
    return value


def policy(*, model, source_digest, base_digest, cap_cny,
           max_attempts, max_output_tokens,
           cache_hit_cny_m, cache_miss_cny_m, output_cny_m):
    """Explicit, synthetic or future-reviewed ceilings; not permission."""
    if model not in wire.MODEL_NAMES:
        raise DurablePreflightError("UNREVIEWED_MODEL")
    if not isinstance(source_digest, str) or len(source_digest) != 64 or any(
            c not in "0123456789abcdef" for c in source_digest):
        raise DurablePreflightError("MISSING_SOURCE_DIGEST")
    if not isinstance(base_digest, str) or len(base_digest) != 64 or any(
            c not in "0123456789abcdef" for c in base_digest):
        raise DurablePreflightError("MISSING_BASE_DIGEST")
    if wire._money(cache_hit_cny_m, "hit") > wire._money(cache_miss_cny_m, "miss"):
        raise DurablePreflightError("CACHE_HIT_CEILING_CANNOT_EXCEED_MISS_CEILING")
    p = {
        "version": JOURNAL_VERSION, "provider": "deepseek",
        "model": model, "source_digest": source_digest,
        "base_digest": base_digest,
        "cap_cny": str(wire._money(cap_cny, "cap")),
        "max_attempts": _int(max_attempts, "max_attempts", 1, 25),
        "max_output_tokens": _int(max_output_tokens, "max_output_tokens", 1, 65536),
        "cache_hit_cny_m": str(wire._money(cache_hit_cny_m, "hit")),
        "cache_miss_cny_m": str(wire._money(cache_miss_cny_m, "miss")),
        "output_cny_m": str(wire._money(output_cny_m, "output")),
        "actual_calls_authorized": False,
        "private_transfer_authorized": False,
    }
    return p


class PrivateReservationJournal:
    """Lock + atomic write-ahead record. Offline preflight, no payment bridge."""

    def __init__(self, directory, config):
        if not isinstance(config, dict):
            raise DurablePreflightError("INVALID_CONFIG")
        expected = policy(
            model=config.get("model"), source_digest=config.get("source_digest"),
            base_digest=config.get("base_digest"), cap_cny=config.get("cap_cny"),
            max_attempts=config.get("max_attempts"),
            max_output_tokens=config.get("max_output_tokens"),
            cache_hit_cny_m=config.get("cache_hit_cny_m"),
            cache_miss_cny_m=config.get("cache_miss_cny_m"),
            output_cny_m=config.get("output_cny_m"))
        if expected != config:
            raise DurablePreflightError("CONFIG_NOT_EXACTLY_OFFLINE")
        self.config = deepcopy(config)
        self.digest = _sha(self.config)
        self.folder = Path(directory)
        if self.folder.is_symlink():
            raise DurablePreflightError("JOURNAL_DIRECTORY_SYMLINK")
        self.folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.folder.is_dir():
            raise DurablePreflightError("JOURNAL_DIRECTORY_INVALID")
        self.path = self.folder / "crew_budget.journal.json"
        lock_path = self.folder / "crew_budget.journal.lock"
        if lock_path.is_symlink() or self.path.is_symlink():
            raise DurablePreflightError("JOURNAL_SYMLINK_NOT_ALLOWED")
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(lock_path, flags, 0o600)
        self._lock_fd = fd
        self.closed = False
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise DurablePreflightError("JOURNAL_ALREADY_LOCKED") from None
            os.fchmod(fd, 0o600)
            if self.path.exists():
                if not stat.S_ISREG(self.path.stat().st_mode):
                    raise DurablePreflightError("JOURNAL_NOT_REGULAR_FILE")
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("config_digest") != self.digest:
                    raise DurablePreflightError("JOURNAL_CONFIG_MISMATCH")
                if not isinstance(data.get("attempts"), list):
                    raise DurablePreflightError("JOURNAL_ATTEMPTS_INVALID")
                self.data = data
                self._validate_integrity()
            else:
                self.data = {
                    "version": JOURNAL_VERSION, "config_digest": self.digest,
                    "cap_cny": self.config["cap_cny"], "attempts": [],
                    "no_provider_calls_performed": True,
                }
                self._write()
        except Exception:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        if not getattr(self, "closed", True):
            self.closed = True
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            os.close(self._lock_fd)

    def _validate_integrity(self):
        if self.closed or _sha(self.config) != self.digest:
            raise DurablePreflightError("JOURNAL_CONFIG_MUTATED_OR_CLOSED")
        if self.data.get("version") != JOURNAL_VERSION or (
                self.data.get("no_provider_calls_performed") is not True):
            raise DurablePreflightError("JOURNAL_UNEXPECTED_VERSION")
        attempt_list = self.data.get("attempts")
        if not isinstance(attempt_list, list):
            raise DurablePreflightError("JOURNAL_ATTEMPTS_INVALID")
        if len(attempt_list) > self.config["max_attempts"]:
            raise DurablePreflightError("JOURNAL_EXCEEDS_ATTEMPT_LIMIT")
        seen = set()
        reserve_total = Decimal(0)
        for idx, record in enumerate(attempt_list, 1):
            if not isinstance(record, dict) or record.get("id") != idx or (
                    record.get("task_id") not in team.SPECS):
                raise DurablePreflightError("JOURNAL_RECORD_INVALID")
            key = (record["task_id"], record.get("revision"))
            if key in seen:
                raise DurablePreflightError("JOURNAL_DUPLICATE_TASK_REVISION")
            seen.add(key)
            val = wire._money(record.get("reserved_cny"), "reserve")
            if record.get("status") not in (
                    "pending_uncertain", "timeout_unknown", "transport_unknown",
                    "response_rejected", "response_accepted",
                    "usage_overrun_requires_review"):
                raise DurablePreflightError("JOURNAL_UNKNOWN_STATUS")
            reserve_total += val
        if reserve_total > Decimal(self.config["cap_cny"]):
            raise DurablePreflightError("JOURNAL_OVER_BUDGET")

    def _write(self):
        self._validate_integrity()
        # Write safely before a future request could ever be dispatched.
        raw = json.dumps(self.data, ensure_ascii=False, sort_keys=True,
                         indent=2, allow_nan=False).encode("utf-8") + b"\n"
        fd, tmp = tempfile.mkstemp(prefix=".crew_budget.", suffix=".tmp",
                                   dir=str(self.folder))
        try:
            with os.fdopen(fd, "wb") as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
            dfd = os.open(self.folder, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @property
    def reserved_cny(self):
        self._validate_integrity()
        return sum((Decimal(x["reserved_cny"]) for x in self.data["attempts"]),
                   Decimal("0"))

    def quote(self, messages):
        self._validate_integrity()
        if not isinstance(messages, list) or len(messages) != 2:
            raise DurablePreflightError("INVALID_MESSAGES")
        wire_request = wire.prepare_chat_request(
            messages, model=self.config["model"],
            max_output_tokens=self.config["max_output_tokens"])
        encoded = json.dumps(wire_request["body"], ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        input_proxy = len(encoded) + 1024
        reserve = (
            Decimal(input_proxy) * Decimal(self.config["cache_miss_cny_m"]) +
            Decimal(self.config["max_output_tokens"]) *
            Decimal(self.config["output_cny_m"])
        ) / PER_MILLION
        reserve = reserve.quantize(QUANT, rounding=ROUND_UP)
        return {"private_request_sha256": hashlib.sha256(encoded).hexdigest(),
                "input_proxy_tokens": input_proxy,
                "reserved_output_tokens": self.config["max_output_tokens"],
                "reserved_cny": str(reserve),
                "token_estimation_is_not_exact": True,
                "invoice_protection_guaranteed": False}

    def reserve(self, *, task_id, revision, messages):
        self._validate_integrity()
        if task_id not in team.SPECS:
            raise DurablePreflightError("UNKNOWN_TASK")
        _int(revision, "revision", 1, 1000000)
        if any(x["status"] in BLOCKING_STATUSES for x in self.data["attempts"]):
            raise DurablePreflightError("UNRECONCILED_ATTEMPT_BLOCKS_RESUME")
        if any(x["task_id"] == task_id and x["revision"] == revision
               for x in self.data["attempts"]):
            raise DurablePreflightError("DUPLICATE_TASK_REVISION_NO_RETRY")
        if len(self.data["attempts"]) >= self.config["max_attempts"]:
            raise DurablePreflightError("ATTEMPT_LIMIT_EXCEEDED")
        quote = self.quote(messages)
        if self.reserved_cny + Decimal(quote["reserved_cny"]) > Decimal(self.config["cap_cny"]):
            raise DurablePreflightError("CAP_PREVENTS_RESERVATION")
        record = {
            "id": len(self.data["attempts"]) + 1,
            "task_id": task_id, "revision": revision,
            **quote, "status": "pending_uncertain",
        }
        self.data["attempts"].append(record)
        try:
            self._write()
        except Exception:
            # Never dispatch without a proven write-ahead reservation.
            self.data["attempts"].pop()
            raise
        return record["id"]

    def finish(self, record_id, *, status, usage=None):
        self._validate_integrity()
        _int(record_id, "record_id", 1, len(self.data["attempts"]))
        if status not in ("response_accepted", "response_rejected",
                          "timeout_unknown", "transport_unknown",
                          "usage_overrun_requires_review"):
            raise DurablePreflightError("INVALID_FINISH_STATUS")
        record = self.data["attempts"][record_id - 1]
        if record["status"] != "pending_uncertain":
            raise DurablePreflightError("CANNOT_REFINISH_ATTEMPT")
        record["status"] = status
        if usage is not None:
            if not isinstance(usage, dict) or not set(
                    ("prompt_tokens", "completion_tokens", "total_tokens",
                     "estimated_usage_cost_cny")) <= set(usage):
                raise DurablePreflightError("INVALID_REPORTED_USAGE")
            record["provider_reported_usage"] = {
                key: usage[key] for key in (
                    "prompt_tokens", "completion_tokens", "total_tokens",
                    "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
                    "estimated_usage_cost_cny", "invoice_verified")
                if key in usage}
        self._write()

    def summary(self):
        self._validate_integrity()
        return {
            "mode": "offline_write_ahead_only",
            "record_count": len(self.data["attempts"]),
            "reserved_cny": str(self.reserved_cny),
            "cap_cny": self.config["cap_cny"],
            "unreconciled_count": sum(
                x["status"] in BLOCKING_STATUSES for x in self.data["attempts"]),
            "journal": deepcopy(self.data),
            "actual_network_calls": 0, "actual_billed_cny": "0",
            "human_approved": False, "invoice_verified": False,
        }


class OfflineResponseFrames:
    """Exact-class mock. No callback injection, no network, no subprocess."""

    def __init__(self, frames):
        if not isinstance(frames, dict):
            raise ValueError("frames must be a dictionary")
        self._frames = deepcopy(frames)

    def fetch(self, task_id, revision):
        data = self._frames.get(task_id, {})
        raw = data.get(str(revision), data.get(revision)) if isinstance(data, dict) else None
        if raw is None:
            raise KeyError("SYNTHETIC_FRAME_NOT_FOUND")
        if raw == "SIMULATE_TIMEOUT":
            raise TimeoutError("SIMULATED_TIMEOUT_CHARGE_UNKNOWN")
        if raw == "SIMULATE_TRANSPORT_FAILURE":
            raise ConnectionError("SIMULATED_TRANSPORT_CHARGE_UNKNOWN")
        if type(raw) not in (str, bytes, dict):
            raise ValueError("SYNTHETIC_FRAME_MUST_BE_JSON_RESPONSE")
        return deepcopy(raw)


def run_one_offline(base, state, journal, frames, task_id=None, *,
                    source_text=None, allow_mock_director_final=False):
    """True *offline* protocol path: reserve -> fake wire -> parse -> role submit."""
    if type(frames) is not OfflineResponseFrames or type(journal) is not PrivateReservationJournal:
        raise DurablePreflightError("LIVE_TRANSPORT_NOT_IMPLEMENTED_OR_AUTHORIZED")
    tasks = team.ready(state)
    tid = tasks[0] if task_id is None and tasks else task_id
    if tid not in tasks:
        raise DurablePreflightError("TASK_NOT_READY")
    if tid == "director_final" and not allow_mock_director_final:
        raise DurablePreflightError("DIRECTOR_FINAL_REQUIRES_EXPLICIT_MOCK_APPROVAL")
    if journal.config["base_digest"] != state["base_digest"] or (
            journal.config["source_digest"] != state["source_digest"]):
        raise DurablePreflightError("JOURNAL_SOURCE_MISMATCH")
    prompt = roles.build_role_messages(base, state, tid,
                                       source_text=source_text)
    request = wire.prepare_chat_request(
        prompt["messages"], model=journal.config["model"],
        max_output_tokens=journal.config["max_output_tokens"])
    revision = prompt["next_revision"]
    # Check fixture exists before reservation, analogous to an offline-only check.
    # This is not an authorization to send the private request object anywhere.
    if tid not in frames._frames or (
            str(revision) not in frames._frames[tid] and
            revision not in frames._frames[tid]):
        raise KeyError("SYNTHETIC_FRAME_NOT_FOUND")
    attempt_id = journal.reserve(
        task_id=tid, revision=revision, messages=request["body"]["messages"])
    try:
        response = frames.fetch(tid, revision)
    except TimeoutError:
        journal.finish(attempt_id, status="timeout_unknown")
        raise
    except ConnectionError:
        journal.finish(attempt_id, status="transport_unknown")
        raise
    try:
        parsed = wire.parse_chat_completion(
            response, expected_model=journal.config["model"],
            max_output_tokens=journal.config["max_output_tokens"],
            hit_price_cny_m=journal.config["cache_hit_cny_m"],
            miss_price_cny_m=journal.config["cache_miss_cny_m"],
            output_price_cny_m=journal.config["output_cny_m"])
        # The proxy does NOT guarantee enough reserve. If the provider-reported
        # token count implies more than our reservation, stop and require
        # manual reconciliation, rather than accept new downstream work.
        expected = Decimal(journal.data["attempts"][attempt_id - 1]["reserved_cny"])
        observed = Decimal(parsed["usage"]["estimated_usage_cost_cny"])
        if observed > expected:
            journal.finish(attempt_id, status="usage_overrun_requires_review",
                           usage=parsed["usage"])
            raise DurablePreflightError("PROVIDER_USAGE_ESTIMATE_EXCEEDS_RESERVATION")
        updated = roles.submit_role_output(
            base, state, tid, parsed["content"], source_text=source_text)
    except Exception:
        if journal.data["attempts"][attempt_id - 1]["status"] == "pending_uncertain":
            journal.finish(attempt_id, status="response_rejected",
                           usage=parsed["usage"] if "parsed" in locals() else None)
        raise
    journal.finish(attempt_id, status="response_accepted",
                   usage=parsed["usage"])
    return updated, {
        "mode": "offline_verified_provider_shape",
        "task_id": tid, "revision": revision,
        "estimated_usage_cny": parsed["usage"]["estimated_usage_cost_cny"],
        "reported_total_tokens": parsed["usage"]["total_tokens"],
        "actual_network_calls": 0, "actual_billed_cny": "0",
        "invoice_verified": False, "private_prompt_in_receipt": False,
        "human_approved": False,
    }
