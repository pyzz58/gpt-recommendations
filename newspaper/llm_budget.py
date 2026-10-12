"""Fail-closed conservative per-request DeepSeek RMB cost guard.

Provider may update pricing without notice. Peak 2026-10-12 posted CNY
per million tokens; assume ALL tokens are cache misses and peak-priced.
This is an upper-bound estimate, not an account-side spending lock.
"""
from __future__ import annotations
from decimal import Decimal
import json
import datetime as dt
from zoneinfo import ZoneInfo

MAX_RMB = Decimal("0.20")
OPERATIONAL_RMB = Decimal("0.18")
PEAK_CNY_PER_MILLION = {
    "deepseek-flash": (Decimal("2"), Decimal("8")),
    "deepseek-v4-pro": (Decimal("9"), Decimal("27")),
}
OFFPEAK_CNY_PER_MILLION = {
    "deepseek-flash": (Decimal("1"), Decimal("4")),
    "deepseek-v4-pro": (Decimal("4.5"), Decimal("13.5")),
}
DEFAULT_MODEL = "deepseek-flash"
MAX_OUTPUT_TOKENS = 3400
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


def beijing_offpeak(at: dt.datetime | None = None) -> bool:
    """Official off-peak outside weekdays 09–12 / 14–18 Beijing time.

    Chinese public holidays count as off-peak too; conservatively treat them as
    ordinary weekdays when no holiday calendar is available. Friday/Saturday/
    Sunday schedule classifications are independent of GitHub queue delay.
    """
    local=(at or dt.datetime.now(ZoneInfo("Asia/Shanghai"))).astimezone(
        ZoneInfo("Asia/Shanghai")
    )
    if local.weekday() >= 5:
        return True
    minute=local.hour*60+local.minute
    return not (540<=minute<720 or 840<=minute<1080)


def estimate_window_cost(
        model: str, input_tokens: int, output_tokens: int,
        at: dt.datetime | None = None) -> Decimal:
    prices=OFFPEAK_CNY_PER_MILLION if beijing_offpeak(at) else PEAK_CNY_PER_MILLION
    if model not in prices or input_tokens<0 or output_tokens<0:
        raise ValueError("Unsupported model or negative token count")
    cin,cout=prices[model]
    return (cin*Decimal(input_tokens)+cout*Decimal(output_tokens))/Decimal(1000000)


def preflight(messages: list[dict], model: str = DEFAULT_MODEL,
              output_limit: int = MAX_OUTPUT_TOKENS,
              at: dt.datetime | None = None) -> tuple[int, Decimal]:
    if output_limit <= 0 or output_limit > MAX_OUTPUT_TOKENS:
        raise ValueError("Requested output exceeds the fixed token ceiling")
    tokens = conservative_input_tokens(messages)
    estimate = estimate_window_cost(model, tokens, output_limit, at=at)
    if estimate >= OPERATIONAL_RMB or estimate >= MAX_RMB:
        raise ValueError(
            "DeepSeek request blocked: time-window pricing estimate exceeds "
            "0.18 CNY operational cap (0.20 CNY budget)."
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

def actual_window_estimate(model:str,usage:dict,at:dt.datetime|None=None)->Decimal:
    if not isinstance(usage,dict):
        raise ValueError("Missing usage object")
    return estimate_window_cost(
        model,int(usage.get("prompt_tokens",-1)),
        int(usage.get("completion_tokens",-1)),at=at
    )
