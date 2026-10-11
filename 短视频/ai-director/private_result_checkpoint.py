#!/usr/bin/env python3
"""Private, source-bound LLM result checkpoints -- NEVER public GitHub storage.

Implementation deliberately small: modeled after LangGraph's checkpoint /
pending-write distinction (MIT), but it does NOT import LangGraph or replay
external side effects. The spend journal owns the exclusive OS lock. Any LLM
network call must first reserve a journal attempt; the complete *validated*
team state must then be fsync'ed here BEFORE the journal is marked accepted.

A crash after the response but before this checkpoint is DURABLY SAVED is
inherently unrecoverable via local files: leave the billed status UNKNOWN and
require manual vendor reconciliation; DO NOT automatically re-send.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

import agent_live_pilot as pilot
import agent_team as team

VERSION = "private-result-checkpoint-v1"
MAX_BYTES = 16 * 1024 * 1024
RECOVER_CONSENT = "RECOVER_SAVED_RESULT_NO_API_CALL"


class CheckpointError(ValueError):
    """Static codes only; never echo model output or private script."""


def _require(ok, reason):
    if not ok:
        raise CheckpointError(reason)


def _hash(data):
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def _fsync_folder(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _secure_dir(path):
    _require(not path.is_symlink() and path.is_dir(),
             "CHECKPOINT_VAULT_DIRECTORY_UNTRUSTED")
    mode = path.stat().st_mode
    _require(stat.S_ISDIR(mode) and not (mode & 0o077),
             "CHECKPOINT_VAULT_DIRECTORY_PERMISSIONS")


def _atomic_create(path, value):
    """No overwrite under any circumstances; fsync bytes AND containing dir."""
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     indent=2, allow_nan=False).encode("utf-8") + b"\n"
    _require(len(raw) <= MAX_BYTES, "CHECKPOINT_TOO_LARGE")
    handle, tempname = tempfile.mkstemp(prefix=".private-result-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as fp:
            os.fchmod(fp.fileno(), 0o600)
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        # Atomic O_EXCL equivalent: linking fails if target exists, unlike
        # os.replace() which can overwrite paid responses.
        os.link(tempname, path, follow_symlinks=False)
        _fsync_folder(path.parent)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)


class PrivateResultVault:
    """Checkpoint store under same private/locked journal directory.

    Do NOT point this at a tracked repo, workspace artifacts folder, or a
    public CI cache. Caller is responsible for durable private host storage.
    """

    def __init__(self, journal):
        _require(type(journal) is pilot.PilotJournal and
                 not journal.closed and not journal.poisoned,
                 "CHECKPOINT_ACTIVE_JOURNAL_REQUIRED")
        journal._validate()
        self.journal = journal
        _secure_dir(journal.path)
        self.root = journal.path / "private-result-checkpoints"
        _require(not self.root.is_symlink(), "CHECKPOINT_VAULT_SYMLINK")
        self.root.mkdir(mode=0o700, exist_ok=True)
        _secure_dir(self.root)
        _require(not (self.root / ".git").exists(), "CHECKPOINT_VAULT_TRACKED")
        self.config_digest = journal.digest

    def _check(self):
        _require(type(self.journal) is pilot.PilotJournal and
                 not self.journal.closed and not self.journal.poisoned,
                 "CHECKPOINT_JOURNAL_NOT_ACTIVE")
        self.journal._validate()
        _secure_dir(self.root)
        _require(self.journal.digest == self.config_digest,
                 "CHECKPOINT_CONFIG_CHANGED")

    def _file(self, attempt_id):
        _require(type(attempt_id) is int and
                 1 <= attempt_id <= len(self.journal.records["attempts"]),
                 "CHECKPOINT_ATTEMPT_OUT_OF_RANGE")
        return self.root / ("attempt-%04d.json" % attempt_id)

    def _record(self, attempt_id):
        self._check()
        return self.journal.records["attempts"][attempt_id - 1]

    def _validate_state(self, state):
        _require(isinstance(state, dict), "CHECKPOINT_TEAM_STATE_MISSING")
        try:
            team._check_state(state)
        except (ValueError, KeyError, TypeError):
            raise CheckpointError("CHECKPOINT_TEAM_STATE_INVALID") from None
        _require(state.get("base_digest") == self.journal.config["base_digest"]
                 and state.get("source_digest") == self.journal.config["source_digest"],
                 "CHECKPOINT_SOURCE_OR_PLAN_DRIFT")

    def save(self, attempt_id, before, after, *, usage):
        """Write validated private source-bound result BEFORE finish(accepted)."""
        rec = self._record(attempt_id)
        _require(rec["status"] == "pending_uncertain",
                 "CHECKPOINT_ATTEMPT_ALREADY_FINISHED")
        self._validate_state(before)
        self._validate_state(after)
        _require(isinstance(usage, dict) and
                 type(usage.get("total_tokens")) is int and
                 isinstance(usage.get("estimated_usage_cost_cny"), str),
                 "CHECKPOINT_USAGE_REQUIRED")
        task_id = rec["task_id"]
        pre = before["tasks"].get(task_id)
        post = after["tasks"].get(task_id)
        _require(isinstance(pre, dict) and isinstance(post, dict) and
                 post.get("status") == "completed" and
                 post.get("revision") == rec["revision"] and
                 pre.get("revision") + 1 == post.get("revision"),
                 "CHECKPOINT_TASK_REVISION_DRIFT")
        out = {
            "version": VERSION, "attempt_id": attempt_id,
            "task_id": task_id, "revision": rec["revision"],
            "request_digest": rec["request_digest"],
            "config_digest": self.journal.digest,
            "source_digest": self.journal.config["source_digest"],
            "base_digest": self.journal.config["base_digest"],
            "before_state_digest": _hash(before),
            "after_state_digest": _hash(after),
            "usage": deepcopy(usage),
            "after_state": deepcopy(after),
            "source_and_output_are_private": True,
            "permission_to_reissue_model_request": False,
            "human_release_approved": False,
            "provider_invoice_verified": False,
        }
        file = self._file(attempt_id)
        _require(not file.exists() and not file.is_symlink(),
                 "CHECKPOINT_OVERWRITE_FORBIDDEN")
        try:
            _atomic_create(file, out)
        except FileExistsError:
            raise CheckpointError("CHECKPOINT_OVERWRITE_FORBIDDEN") from None
        return {"kind": VERSION, "attempt_id": attempt_id,
                "after_state_digest": out["after_state_digest"],
                "saved_durably": True, "provider_call_count": 0,
                "private_result_contents_in_receipt": False}

    def load(self, attempt_id, *, expected_before=None):
        """Validate hash/bindings before returning a private team snapshot."""
        rec = self._record(attempt_id)
        path = self._file(attempt_id)
        _require(not path.is_symlink() and path.is_file(),
                 "CHECKPOINT_MISSING_OR_UNTRUSTED")
        _require(path.stat().st_size <= MAX_BYTES and
                 not (path.stat().st_mode & 0o077),
                 "CHECKPOINT_FILE_PERMISSIONS_OR_SIZE")
        try:
            data = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError, UnicodeError):
            raise CheckpointError("CHECKPOINT_CORRUPTED") from None
        _require(isinstance(data, dict) and
                 data.get("version") == VERSION and
                 data.get("attempt_id") == attempt_id and
                 data.get("task_id") == rec["task_id"] and
                 data.get("revision") == rec["revision"] and
                 data.get("request_digest") == rec["request_digest"] and
                 data.get("config_digest") == self.journal.digest and
                 data.get("source_digest") == self.journal.config["source_digest"] and
                 data.get("base_digest") == self.journal.config["base_digest"] and
                 data.get("permission_to_reissue_model_request") is False,
                 "CHECKPOINT_BINDING_MISMATCH")
        out = data.get("after_state")
        self._validate_state(out)
        _require(_hash(out) == data.get("after_state_digest") and
                 out["tasks"][rec["task_id"]]["revision"] == rec["revision"] and
                 out["tasks"][rec["task_id"]]["status"] == "completed",
                 "CHECKPOINT_RESULT_INTEGRITY_FAILED")
        if expected_before is not None:
            self._validate_state(expected_before)
            _require(_hash(expected_before) == data.get("before_state_digest"),
                     "CHECKPOINT_PREVIOUS_STATE_MISMATCH")
        return {"team": deepcopy(out), "attempt_id": attempt_id,
                "usage": deepcopy(data["usage"]),
                "source_and_output_are_private": True,
                "eligible_to_reissue_request": False,
                "human_approved": False,
                "provider_invoice_verified": False}

    def assert_existing_accepted_checkpoint_chain(self, current_state):
        """Fail closed on stale/missing prior accepted paid results."""
        self._check()
        self._validate_state(current_state)
        accepted = [x for x in self.journal.records["attempts"]
                    if x["status"] == "response_accepted"]
        for record in accepted:
            self.load(record["id"])  # hash, request and source must be bound
        if accepted:
            last = self.load(accepted[-1]["id"])
            _require(_hash(last["team"]) == _hash(current_state),
                     "CHECKPOINT_CALLER_STATE_NOT_LATEST")
        # A pending provider side effect cannot be resolved by sending again.
        _require(not any(x["status"] in pilot.BLOCKED_STATES
                         for x in self.journal.records["attempts"]),
                 "CHECKPOINT_UNKNOWN_BILLING_BLOCKS_NEXT")
        return {"accepted_private_results": len(accepted),
                "new_provider_calls": 0, "caller_state_verified": True}

    def reconcile_saved_result(self, attempt_id, before, *, operator_acknowledgement):
        """Manual no-network resolution if result file was fsynced, ledger not.

        This is a recovery from our OWN local checkpoint, not proof of paid
        invoice. Never retries or replays a model request. Authenticated private
        UI must check who is authorizing the reconciliation.
        """
        _require(operator_acknowledgement == RECOVER_CONSENT,
                 "CHECKPOINT_MANUAL_RECONCILIATION_REQUIRED")
        rec = self._record(attempt_id)
        _require(rec["status"] in ("pending_uncertain","response_accepted"),
                 "CHECKPOINT_RECONCILIATION_STATUS_INVALID")
        result = self.load(attempt_id, expected_before=before)
        if rec["status"] == "pending_uncertain":
            self.journal.finish(attempt_id, "response_accepted",
                                usage=result["usage"])
        return {"kind":"manual_checkpoint_reconciliation",
                "after_state":result["team"],
                "attempt_id":attempt_id,
                "provider_calls":0,
                "provider_invoice_verified":False,
                "identity_cryptographically_verified":False,
                "permission_to_retry_spending":False,
                "human_release_approved":False}
