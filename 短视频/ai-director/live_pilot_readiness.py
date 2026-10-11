#!/usr/bin/env python3
"""One cheap, no-network REAL-MODEL readiness check with a public fiction.

NOT a DeepSeek call, authorization, quoted provider invoice or synthetic
pretence of live results. Produces a pricing/source-locked dry-run estimate
for DIRECTOR_BRIEF only; script_edit request is unknown until director returns.
Does not read secrets/environment or accept private input on its CLI.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_UP
import hashlib
import json
from pathlib import Path
import sys

import article_intake as intake
import editorial_storyboard as creative
import agent_provider_wire as wire
import agent_live_pilot as pilot

MODEL = "deepseek-flash"
PRICE_OFFICIAL_URL = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
# Conservative 2026-10-11 verified peak prices, CNY per million tokens:
# cache hit 0.04; cache miss 2.00; output 8.00. Operator MUST reverify.
PEAK_CNY_PER_M = {"cache_hit": "0.04", "cache_miss": "2", "output": "8"}
SUGGESTED_TOTAL_CAP_CNY = "2"
MAX_OUTPUT_TOKENS_PER_ROLE = 8192

# Pure fiction written for this public rehearsal. No user-uploaded article,
# real person/identity, medical statistics or copyrighted third-party text.
PUBLIC_FICTION = """# 虚构一分钟悬念短片

### 1. 门后的信
- 说人话：傍晚，林禾独自回到公寓。她关门时，门内传来三下轻轻的敲击。她握着门把手，停了两秒。客厅灯还亮着，木桌上多了一封没有署名的信。信封上有一道崭新的折痕。她走近，指尖刚碰到封口，客厅的灯忽然熄灭。黑暗中又传来三下敲击。林禾没有拆信，把信放进口袋，缓缓转身望向紧闭的门。
- 备注：以上人物、故事和场景均完全虚构，无需医疗、新闻或法规查证。
"""


class RehearsalError(ValueError):
    pass


def price_director_request():
    """Inspect only the first prompt. Never turn this into a network call."""
    catalog = intake.episode_catalog(PUBLIC_FICTION)
    result = intake.prepare_episode(PUBLIC_FICTION, "EP01")
    if result["status"] != "editorial_review_required":
        raise RehearsalError("REHEARSAL_INTAKE_NOT_READY")
    episode_source = intake.episode_source_for_team(PUBLIC_FICTION, "EP01")
    request = creative.build_director_brief_request(result, episode_source)
    if request["external_model_call_authorized"] is not False:
        raise RehearsalError("REHEARSAL_UNEXPECTED_DISPATCH_FLAG")
    config = pilot.create_pilot_config(
        model=MODEL, source_digest=result["episode_source_sha256"],
        base_digest=result["team"]["base_digest"],
        cap_cny=SUGGESTED_TOTAL_CAP_CNY,
        max_output_tokens=MAX_OUTPUT_TOKENS_PER_ROLE,
        cache_hit_cny_m=PEAK_CNY_PER_M["cache_hit"],
        cache_miss_cny_m=PEAK_CNY_PER_M["cache_miss"],
        output_cny_m=PEAK_CNY_PER_M["output"],
        max_attempts=2)
    envelope = wire.prepare_chat_request(
        request["messages"], model=config["model"],
        max_output_tokens=config["max_output_tokens"])
    if envelope["dispatch_authorized"] is not False:
        raise RehearsalError("REHEARSAL_REQUEST_WAS_AUTHORIZED")
    payload = json.dumps(envelope["body"], ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    byte_proxy = len(payload) + 1024
    predicted_reserve = (
        Decimal(byte_proxy) * Decimal(config["cache_miss_cny_m"]) +
        Decimal(config["max_output_tokens"]) * Decimal(config["output_cny_m"])
    ) / Decimal(1000000)
    quoted = predicted_reserve.quantize(Decimal("0.00000001"),
                                        rounding=ROUND_UP)
    if quoted > Decimal(config["cap_cny"]):
        raise RehearsalError("REHEARSAL_FIRST_CALL_OVER_SUGGESTED_CAP")
    return {
        "kind": "public_fiction_deepseek_live_pilot_READINESS_NOT_EXECUTED",
        "model": MODEL, "pricing_checked_on": "2026-10-11",
        "model_version_label": "DeepSeek-V4.1-Flash",
        "official_pricing_url": PRICE_OFFICIAL_URL,
        "pricing_peak_cny_per_m": PEAK_CNY_PER_M,
        "planning_cap_cny": SUGGESTED_TOTAL_CAP_CNY,
        "cap_is_not_provider_invoice_limit": True,
        "max_output_tokens_per_role": MAX_OUTPUT_TOKENS_PER_ROLE,
        "fictional_source_sha256": hashlib.sha256(
            PUBLIC_FICTION.encode("utf-8")).hexdigest(),
        "episode_source_sha256": result["episode_source_sha256"],
        "base_plan_digest": result["team"]["base_digest"],
        "catalog_topics": catalog["section_count"],
        "source_shots": len(result["plan"]["shots"]),
        "first_task": "director_brief",
        "first_task_prompt_utf8_bytes": len(payload),
        "first_task_approx_input_token_proxy": byte_proxy,
        "first_task_estimated_max_reservation_cny": str(quoted),
        "second_task": "script_edit",
        "second_task_quote": "NOT_YET_KNOWN_NEEDS_DIRECTOR_OUTPUT",
        "document_is_user_private": False,
        "source_edits_require_author_approval": True,
        "run_preconditions": [
            "TRUSTED_PRIVATE_RUNTIME",
            "AUTHORIZED_DEEPSEEK_ACCOUNT_AND_SECRET_OUTSIDE_GITHUB",
            "PER_TASK_VERIFIED_USER_CONSENT_FOR_DATA_AND_COST",
            "REVERIFY_OFFICIAL_PRICES_BEFORE_EACH_REAL_CALL",
            "SUPPLIER_ACCOUNT_LEVEL_BILLING_LIMITS",
            "PERSIST_NEW_TEAM_STATE_PRIVATELY_BEFORE_SECOND_CALL",
        ],
        "missing_preconditions": [
            "NO_CONNECTED_DEEPSEEK_ACCOUNT_IN_THIS_CHAT",
            "NO_TRUSTED_PRIVATE_EXECUTOR_WITH_ACCOUNT_CREDENTIALS",
            "NO_AUTHENTICATED_PER_TASK_SPEND_PERMISSION",
            "NO_PROVIDER_INVOICE_VALIDATION",
        ],
        "external_network_requests": 0,
        "actual_provider_calls": 0,
        "actual_spend_cny": "0",
        "human_approved": False,
        "ready_for_live_dispatch": False,
        "ready_for_video_generation": False,
        "status": "OFFLINE_PREFLIGHT_ONLY_BLOCK_REAL_DISPATCH",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Price fictional director prompt without DeepSeek network")
    parser.add_argument("--public-fiction-only", action="store_true", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        output = Path(args.out)
        if output.exists() or output.is_symlink():
            raise RehearsalError("REHEARSAL_OUTPUT_EXISTS")
        report = price_director_request()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2, allow_nan=False)
            fp.write("\n")
        print("DEEPSEEK_REAL_PILOT_PREFLIGHT_OFFLINE: first_reserved_cny=%s; external_calls=0" %
              report["first_task_estimated_max_reservation_cny"])
        return 0
    except (OSError, KeyError, TypeError, ValueError):
        print("DEEPSEEK_REAL_PILOT_PREFLIGHT_FAILED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
