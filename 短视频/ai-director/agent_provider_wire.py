#!/usr/bin/env python3
"""DeepSeek Chat Completions wire protocol, WITHOUT ANY network transport.

Request preparation and response normalization only. This module cannot submit
an HTTP request, read credentials, retry, save private prompts or spend money.
Provider-reported usage is not an independently verified provider invoice.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_UP
import json

import agent_role_contracts as roles

MODEL_NAMES = frozenset({"deepseek-flash", "deepseek-v4-pro"})
ENDPOINT = "https://api.deepseek.com/chat/completions"
QUANT = Decimal("0.00000001")
MILLION = Decimal(1000000)
MAX_WIRE_BYTES = 1024 * 1024


class ProviderProtocolError(ValueError):
    """Malformed response. NEVER add response body or private data to message."""


def _int(value, name, *, allow_zero=True):
    if type(value) is not int or value < 0 or (not allow_zero and value == 0):
        raise ProviderProtocolError("INVALID_USAGE_" + name.upper())
    return value


def _money(value, name):
    if type(value) not in (str, int, float, Decimal):
        raise ProviderProtocolError("INVALID_PRICE_" + name.upper())
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProviderProtocolError("INVALID_PRICE_" + name.upper()) from None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000"):
        raise ProviderProtocolError("INVALID_PRICE_" + name.upper())
    return amount


def prepare_chat_request(messages, *, model, max_output_tokens):
    """Build a private HTTP POST *descriptor*, never perform the POST."""
    if model not in MODEL_NAMES:
        raise ProviderProtocolError("UNSUPPORTED_MODEL_NEEDS_REVIEW")
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 65536:
        raise ProviderProtocolError("INVALID_OUTPUT_LIMIT")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError("CHAT_REQUIRES_SYSTEM_AND_USER")
    if ([m.get("role") if isinstance(m, dict) else None for m in messages]
            != ["system", "user"] or
            any(set(m) != {"role", "content"} or
                not isinstance(m["content"], str) or not m["content"].strip()
                for m in messages)):
        raise ProviderProtocolError("INVALID_CHAT_MESSAGES")
    body = {"model": model, "messages": [dict(m) for m in messages],
            "response_format": {"type": "json_object"},
            "stream": False, "max_tokens": max_output_tokens}
    size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    if size > MAX_WIRE_BYTES:
        raise ProviderProtocolError("PRIVATE_CHAT_REQUEST_TOO_LARGE")
    return {"endpoint": ENDPOINT, "method": "POST", "body": body,
            "content_type": "application/json",
            "private_payload": True, "dispatch_authorized": False,
            "actual_network_requests": 0}


def _decode(raw):
    if isinstance(raw, dict):
        return raw
    if type(raw) is bytes:
        if len(raw) > MAX_WIRE_BYTES:
            raise ProviderProtocolError("RESPONSE_TOO_LARGE")
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ProviderProtocolError("INVALID_RESPONSE_ENCODING") from None
    if type(raw) is not str or len(raw.encode("utf-8")) > MAX_WIRE_BYTES:
        raise ProviderProtocolError("RESPONSE_TOO_LARGE_OR_NOT_TEXT")
    try:
        return roles.parse_strict_json(raw)
    except ValueError:
        raise ProviderProtocolError("INVALID_RESPONSE_JSON") from None


def normalize_usage(raw, *, hit_price_cny_m, miss_price_cny_m, output_price_cny_m):
    """Use returned provider counts; treat missing cache split as all miss.

    Never silently treat unknown cache tokens as cache hits. Estimates exclude
    other provider charges and cannot certify a bank or supplier invoice.
    """
    if not isinstance(raw, dict):
        raise ProviderProtocolError("MISSING_USAGE")
    prompt = _int(raw.get("prompt_tokens"), "prompt_tokens")
    completion = _int(raw.get("completion_tokens"), "completion_tokens")
    total = _int(raw.get("total_tokens"), "total_tokens")
    if prompt + completion != total:
        raise ProviderProtocolError("USAGE_TOTAL_MISMATCH")
    hit = raw.get("prompt_cache_hit_tokens")
    miss = raw.get("prompt_cache_miss_tokens")
    if hit is None and miss is None:
        hit, miss, cache_type = 0, prompt, "cache_split_absent_all_miss"
    elif hit is not None and miss is not None:
        hit = _int(hit, "prompt_cache_hit_tokens")
        miss = _int(miss, "prompt_cache_miss_tokens")
        if hit + miss != prompt:
            raise ProviderProtocolError("USAGE_CACHE_SPLIT_MISMATCH")
        cache_type = "provider_reported_split"
    else:
        raise ProviderProtocolError("USAGE_CACHE_SPLIT_PARTIAL")
    hit_price = _money(hit_price_cny_m, "cache_hit")
    miss_price = _money(miss_price_cny_m, "cache_miss")
    out_price = _money(output_price_cny_m, "output")
    computed = (
        Decimal(hit) * hit_price +
        Decimal(miss) * miss_price +
        Decimal(completion) * out_price
    ) / MILLION
    estimated = computed.quantize(QUANT, rounding=ROUND_UP)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "prompt_cache_hit_tokens": hit, "prompt_cache_miss_tokens": miss,
        "cache_breakdown": cache_type,
        "estimated_usage_cost_cny": str(estimated),
        "cost_basis": "caller-supplied CNY/1M prices; provider-reported token counters",
        "invoice_verified": False,
    }


def parse_chat_completion(raw, *, expected_model, max_output_tokens,
                          hit_price_cny_m, miss_price_cny_m,
                          output_price_cny_m):
    """Validate DeepSeek chat.completion and preserve strict JSON content only.

    No response body is ever included in exceptions. A reject may have been
    billed and must remain a spent/uncertain reservation in the durable ledger.
    """
    payload = _decode(raw)
    if not isinstance(payload, dict) or payload.get("object") != "chat.completion":
        raise ProviderProtocolError("NOT_CHAT_COMPLETION")
    if payload.get("model") != expected_model or expected_model not in MODEL_NAMES:
        raise ProviderProtocolError("MODEL_RESPONSE_MISMATCH")
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ProviderProtocolError("INVALID_CHOICE_COUNT")
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise ProviderProtocolError("NON_FINAL_OR_TRUNCATED_COMPLETION")
    message = choice.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        raise ProviderProtocolError("NO_ASSISTANT_MESSAGE")
    content = message.get("content")
    if type(content) is not str or not content.strip():
        raise ProviderProtocolError("EMPTY_ASSISTANT_CONTENT")
    if len(content) > roles.MAX_RESPONSE_CHARS:
        raise ProviderProtocolError("ROLE_CONTENT_TOO_LONG")
    usage = normalize_usage(
        payload.get("usage"),
        hit_price_cny_m=hit_price_cny_m,
        miss_price_cny_m=miss_price_cny_m,
        output_price_cny_m=output_price_cny_m,
    )
    if type(max_output_tokens) is not int or max_output_tokens < 1:
        raise ProviderProtocolError("INVALID_OUTPUT_LIMIT")
    if usage["completion_tokens"] > max_output_tokens:
        raise ProviderProtocolError("PROVIDER_OUTPUT_EXCEEDED_DECLARED_LIMIT")
    # The role contract verifies exact shot coverage, stage ownership, and
    # source fidelity later; don't reformat or "fix" model JSON here.
    try:
        roles.parse_strict_json(content)
    except ValueError:
        raise ProviderProtocolError("INVALID_ROLE_JSON_CONTENT") from None
    return {"content": content, "usage": usage,
            "protocol": "deepseek-chat-completions",
            "provider_response_checked": True,
            "actual_invoice_verified": False}
