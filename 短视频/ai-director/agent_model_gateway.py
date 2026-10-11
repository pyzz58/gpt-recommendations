#!/usr/bin/env python3
"""Provider-neutral model request preparation and *offline-only* budget simulation.

A model profile is a future routing declaration, NOT permission to contact an
API. Only an exact OfflineMockTransport is executable here. No HTTP, SDK,
environment keys, subprocesses, user filesystem writes or model calls.

The budget estimate is deliberately a proxy; it cannot guarantee a provider
invoice or provider tokenizer count. Failed/uncertain attempts are never
automatically retried or refunded by this module.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_UP
import hashlib
import json

import agent_team as team
import agent_role_contracts as roles

VERSION = "offline-model-routing-v1"
PER_MILLION = Decimal("1000000")
QUANTUM = Decimal("0.00000001")
MAX_BYTES = 1024 * 1024


class ModelBudgetError(ValueError):
    pass


class MockResponseMissing(LookupError):
    pass


def _amount(value, name, *, allow_zero=False):
    if type(value) not in (str, int, float, Decimal):
        raise ModelBudgetError(name + ": invalid monetary value")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ModelBudgetError(name + ": invalid monetary value") from None
    if not amount.is_finite() or amount < 0 or (amount == 0 and not allow_zero):
        raise ModelBudgetError(name + ": must be finite and positive")
    if amount > Decimal("1000000000"):
        raise ModelBudgetError(name + ": exceeds supported accounting range")
    return amount


def _integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(name + ": invalid integer bound")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(name + ": invalid non-empty identifier")
    return value.strip()


def configure_profiles(profiles, routing, *, cap_cny, max_attempts):
    """Validate an explicit future model map, with zero billing assumptions.

    profiles={"model-key": {"provider": "deepseek", "model": "model-id",
      "max_input_tokens": 16384, "max_output_tokens": 2048,
      "input_cny_per_m": "8", "output_cny_per_m": "28"}}
    routing={"director_brief": "model-key", ... } optional default via "*".
    Prices are merely caller-declared ceilings and MUST be independently
    verified and explicitly authorized before any future actual use.
    """
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("nonempty explicit model profiles required")
    if not isinstance(routing, dict) or not routing:
        raise ValueError("nonempty task routing required")
    catalog = {}
    for name, raw in profiles.items():
        key = _text(name, "profile")
        if not isinstance(raw, dict) or set(raw) != {
            "provider", "model", "max_input_tokens", "max_output_tokens",
            "input_cny_per_m", "output_cny_per_m"}:
            raise ValueError("model profile needs exact declared fields")
        input_price = _amount(raw["input_cny_per_m"], "input price")
        output_price = _amount(raw["output_cny_per_m"], "output price")
        catalog[key] = {
            "provider": _text(raw["provider"], "provider"),
            "model": _text(raw["model"], "model"),
            "max_input_tokens": _integer(
                raw["max_input_tokens"], "max_input_tokens", 256, 2_000_000),
            "max_output_tokens": _integer(
                raw["max_output_tokens"], "max_output_tokens", 1, 65536),
            "input_cny_per_m": str(input_price),
            "output_cny_per_m": str(output_price),
        }
    resolved = {}
    if not set(routing) <= set(team.SPECS) | {"*"}:
        raise ValueError("routing references unknown crew task")
    for task_id in team.SPECS:
        profile = routing.get(task_id, routing.get("*"))
        if profile not in catalog:
            raise ValueError("no declared model profile for task " + task_id)
        resolved[task_id] = profile
    return {"version": VERSION, "profiles": catalog,
            "routes": resolved, "cap_cny": str(_amount(cap_cny, "cap_cny")),
            "max_attempts": _integer(max_attempts, "max_attempts", 1, 25),
            "live_calls_authorized": False,
            "private_data_transfer_authorized": False,
            "paid_media_authorized": False}


def _plan_fingerprint(config):
    return hashlib.sha256(json.dumps(
        config, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


class OfflineBudgetBook:
    """In-memory mock reservation ledger, with no real cost or refund claims.

    No public persistence: once genuine private calls are approved, use a
    separately reviewed durable atomic, crash-safe, process-locked ledger.
    """

    def __init__(self, config):
        if not isinstance(config, dict) or config.get("version") != VERSION or (
                config.get("live_calls_authorized") is not False) or (
                config.get("private_data_transfer_authorized") is not False):
            raise ModelBudgetError("untrusted or live-enabled budget configuration")
        # Revalidate to prevent forged/edited configurations from bypassing prices.
        checked = configure_profiles(
            config.get("profiles"), config.get("routes"),
            cap_cny=config.get("cap_cny"), max_attempts=config.get("max_attempts"))
        if checked != config:
            raise ModelBudgetError("budget config must match strict offline canonical form")
        self.config = deepcopy(config)
        self.config_digest = _plan_fingerprint(self.config)
        self.attempts = []

    @property
    def total_reserved_cny(self):
        return sum((Decimal(x["reserved_cny"]) for x in self.attempts),
                   Decimal("0"))

    def quote(self, task_id, messages):
        if task_id not in team.SPECS:
            raise ModelBudgetError("unknown task for model quote")
        if not isinstance(messages, list) or not messages or any(
                not isinstance(m, dict) or m.get("role") not in ("system", "user")
                or not isinstance(m.get("content"), str) for m in messages):
            raise ModelBudgetError("malformed model message envelope")
        raw = json.dumps(messages, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise ModelBudgetError("private prompt too large for offline quote")
        model_key = self.config["routes"][task_id]
        profile = self.config["profiles"][model_key]
        input_proxy = len(raw) + 1024  # proxy only, NOT tokenizer proof.
        if input_proxy > profile["max_input_tokens"]:
            raise ModelBudgetError("prompt proxy exceeds configured model context cap")
        output_cap = profile["max_output_tokens"]
        reserve = (Decimal(input_proxy) *
                   Decimal(profile["input_cny_per_m"]) / PER_MILLION +
                   Decimal(output_cap) *
                   Decimal(profile["output_cny_per_m"]) / PER_MILLION)
        reserve = reserve.quantize(QUANTUM, rounding=ROUND_UP)
        return {"task_id": task_id, "model_key": model_key,
                "provider": profile["provider"], "model": profile["model"],
                "input_proxy_tokens": input_proxy,
                "reserved_output_tokens": output_cap,
                "reserved_cny": str(reserve),
                "method": "utf8-byte-plus-overhead proxy, not provider bill",
                "live_calls_authorized": False}

    def reserve(self, quote, *, revision):
        """Reserve BEFORE mock delivery and count rejected responses as attempts."""
        if not isinstance(quote, dict) or quote.get("task_id") not in team.SPECS:
            raise ModelBudgetError("invalid quote")
        _integer(revision, "revision", 1, 1000000)
        task_id = quote["task_id"]
        model_key = self.config["routes"][task_id]
        profile = self.config["profiles"][model_key]
        input_proxy = _integer(quote.get("input_proxy_tokens"),
                               "input proxy", 1, 2_000_000)
        output_tokens = _integer(quote.get("reserved_output_tokens"),
                                 "output tokens", 1, 65536)
        if input_proxy > profile["max_input_tokens"] or (
                output_tokens != profile["max_output_tokens"]):
            raise ModelBudgetError("quote exceeds or mismatches selected token bounds")
        expected_cost = (Decimal(input_proxy) *
                         Decimal(profile["input_cny_per_m"]) / PER_MILLION +
                         Decimal(output_tokens) *
                         Decimal(profile["output_cny_per_m"]) / PER_MILLION
                         ).quantize(QUANTUM, rounding=ROUND_UP)
        if (quote.get("model_key") != model_key or
                quote.get("provider") != profile["provider"] or
                quote.get("model") != profile["model"] or
                quote.get("reserved_cny") != str(expected_cost) or
                quote.get("live_calls_authorized") is not False):
            raise ModelBudgetError("quote does not match declared model and budget")
        if len(self.attempts) >= self.config["max_attempts"]:
            raise ModelBudgetError("max model attempts reached")
        predicted = self.total_reserved_cny + expected_cost
        if predicted > Decimal(self.config["cap_cny"]):
            raise ModelBudgetError("offline budget cap exceeded before attempt")
        record = {
            "task_id": quote["task_id"], "revision": revision,
            "model_key": quote["model_key"], "provider": quote["provider"],
            "input_proxy_tokens": quote["input_proxy_tokens"],
            "reserved_output_tokens": quote["reserved_output_tokens"],
            "reserved_cny": quote["reserved_cny"],
            "status": "reserved_offline_no_external_call",
            "actual_provider_calls": 0, "actual_billed_cny": "0",
        }
        self.attempts.append(record)
        return record

    def safe_summary(self):
        return {"mode": "offline_mock_only", "config_digest": self.config_digest,
                "cap_cny": self.config["cap_cny"],
                "reserved_cny": str(self.total_reserved_cny),
                "attempts_used": len(self.attempts),
                "max_attempts": self.config["max_attempts"],
                "attempts": deepcopy(self.attempts),
                "actual_provider_calls": 0, "actual_billed_cny": "0",
                "source_text_included": False,
                "live_calls_authorized": False, "human_approved": False}


class OfflineMockTransport:
    """Only allowed response source: in-memory synthetically authored JSON.

    response = {"director_brief": {"1": "<JSON string>"}, ...}
    Never invokes a function/callback, provider SDK, network, subprocess or key.
    """

    def __init__(self, responses):
        if not isinstance(responses, dict):
            raise ValueError("mock responses must be dict")
        self._responses = deepcopy(responses)

    def complete(self, request):
        key = request["task_id"]
        rev = request["revision"]
        task_map = self._responses.get(key)
        if not isinstance(task_map, dict):
            raise MockResponseMissing("no offline response for " + key)
        content = task_map.get(str(rev), task_map.get(rev))
        if content is None:
            raise MockResponseMissing("no offline response for " + key)
        if not isinstance(content, str):
            raise ValueError("mock response must be a raw JSON string")
        return content


def prepare_request(base, state, task_id, book, *, source_text=None):
    """Build a private future provider request in memory, without dispatch."""
    if type(book) is not OfflineBudgetBook:
        raise ModelBudgetError("requires exact offline budget book")
    prompt = roles.build_role_messages(base, state, task_id,
                                       source_text=source_text)
    quote = book.quote(task_id, prompt["messages"])
    return {"kind": "private_offline_provider_envelope",
            "task_id": task_id, "revision": prompt["next_revision"],
            "provider": quote["provider"], "model": quote["model"],
            "messages": prompt["messages"],
            "output_json_schema": prompt["output_json_schema"],
            "max_output_tokens": quote["reserved_output_tokens"],
            "quote": quote, "contains_private_material": True,
            "live_calls_authorized": False,
            "external_requests_executed": 0}


def simulate_one(base, state, book, transport, task_id=None, *,
                 source_text=None, allow_mock_director_final=False):
    """Perform ONE mocked model response and professional strict output check.

    Updates only supplied in-memory budget object; creates a NEW crew ledger.
    A failure still reserves mock budget, but no currency is actually spent.
    """
    if type(transport) is not OfflineMockTransport:
        raise ValueError("LIVE_MODEL_TRANSPORT_DISABLED: only offline mock transport")
    if type(book) is not OfflineBudgetBook:
        raise ModelBudgetError("live budget adapters not allowed")
    ready_tasks = team.ready(state)
    if not ready_tasks:
        raise ValueError("no ready task")
    target = task_id if task_id is not None else ready_tasks[0]
    if target not in ready_tasks:
        raise ValueError("target task not ready")
    if target == "director_final" and not allow_mock_director_final:
        raise ValueError("mock director final requires explicit permission")
    request = prepare_request(base, state, target, book,
                              source_text=source_text)
    # Missing mock materials do not consume an attempt, as no call can occur.
    raw = transport.complete(request)
    record = book.reserve(request["quote"], revision=request["revision"])
    try:
        new_state = roles.submit_role_output(
            base, state, target, raw, source_text=source_text)
    except Exception:
        record["status"] = "rejected_mock_response_reserved"
        raise
    record["status"] = "accepted_mock_response_reserved"
    receipt = {
        "task_id": target, "revision": request["revision"],
        "model_key": request["quote"]["model_key"],
        "reserved_cny": request["quote"]["reserved_cny"],
        "status": "simulated_professional_output_accepted",
        "simulated_reserved_cny": request["quote"]["reserved_cny"],
        "actual_billed_cny": "0", "actual_provider_calls": 0,
        "contains_private_material": False, "human_approved": False,
    }
    return new_state, receipt


def simulate_until_pause(base, state, book, transport, *, source_text=None,
                         max_steps=10, allow_mock_director_final=False):
    """Offline, serial DAG simulation; no automatic rework, API retry or writes."""
    _integer(max_steps, "max_steps", 1, 50)
    if type(transport) is not OfflineMockTransport or type(book) is not OfflineBudgetBook:
        raise ValueError("only exact offline model simulator is permitted")
    current = deepcopy(state)
    receipts = []
    reason = "step_limit_reached"
    for _ in range(max_steps):
        pending = team.ready(current)
        if not pending:
            reason = "no_ready_tasks"
            break
        tid = pending[0]
        if tid == "director_final" and not allow_mock_director_final:
            reason = "director_final_requires_explicit_mock_permission"
            break
        try:
            current, receipt = simulate_one(
                base, current, book, transport, tid, source_text=source_text,
                allow_mock_director_final=allow_mock_director_final)
        except MockResponseMissing:
            reason = "mock_response_missing"
            break
        receipts.append(receipt)
    if reason == "step_limit_reached" and not team.ready(current):
        reason = "no_ready_tasks"
    return current, {"mode": VERSION, "status": reason,
                     "processed_count": len(receipts),
                     "processed": receipts, "ready_tasks": team.ready(current),
                     "budget": book.safe_summary(),
                     "actual_provider_calls": 0, "actual_billed_cny": "0",
                     "source_text_included": False,
                     "human_approved": False, "paid_media_generated": False}
