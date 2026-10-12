"""Fail-closed conservative per-request DeepSeek RMB cost guard.

Provider may update pricing without notice. Peak 2026-10-12 posted CNY
per million tokens; assume ALL tokens are cache misses and peak-priced.
This is an upper-bound estimate, not an account-side spending lock.
"""
from __future__ import annotations
from decimal import Decimal
import json

MAX_RMB = Decimal("0.20")
OPERATIONAL_RMB = Decimal("0.18")
PEAK_CNY_PER_MILLION = {
    "deepseek-flash": (Decimal("2"), Decimal("8")),
    "deepseek-v4-pro": (Decimal("9"), Decimal("27")),
}
DEFAULT_MODEL = "deepseek-flash"
MAX_OUTPUT_TOKENS = 2400
OVERHEAD_TOKENS = 1024


def conservative_input_tokens(messages: list[dict]) -> int:
    """UTF-8 bytes plus overhead conservatively overstate BPE token use."""
    return len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + OVERHEAD_TOKENS


def estimate_peak_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    if model not in PEAK_CNY_PER_MILLION:
        raise ValueError("Unknown model cannot be used under the cost guard")
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Invalid token count")
    input_rate, output_rate = PEAK_CNY_PER_MILLION[model]
    return (
        input_rate * Decimal(input_tokens)
        + output_rate * Decimal(output_tokens)
    ) / Decimal(1000000)


def preflight(messages: list[dict], model: str = DEFAULT_MODEL,
              output_limit: int = MAX_OUTPUT_TOKENS) -> tuple[int, Decimal]:
    if output_limit <= 0 or output_limit > MAX_OUTPUT_TOKENS:
        raise ValueError("Requested output exceeds the fixed token ceiling")
    tokens = conservative_input_tokens(messages)
    estimate = estimate_peak_cost(model, tokens, output_limit)
    if estimate >= OPERATIONAL_RMB or estimate >= MAX_RMB:
        raise ValueError(
            "DeepSeek request blocked: peak-price cost estimate exceeds "
            "the 0.18 CNY operating limit (0.20 CNY absolute budget)."
        )
    return tokens, estimate


def actual_cost_ceiling(model: str, usage: dict) -> Decimal:
    if not isinstance(usage, dict):
        raise ValueError("Missing DeepSeek usage object")
    # Ignore cache discounts, count all reported input as peak-priced.
    return estimate_peak_cost(
        model, int(usage.get("prompt_tokens", -1)),
        int(usage.get("completion_tokens", -1)),
    )
