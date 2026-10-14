"""Single authoritative production schedule for Newspaper (NOT neican).

GitHub cron entries have to be literal in YAML; contract tests check each one
against production_policy.json. All Python dates, windows and manifest stamps
are read from this file instead of repeating configuration strings.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

POLICY = json.loads(Path(__file__).with_name("production_policy.json").read_text(encoding="utf-8"))
if POLICY["schema"] != 1 or POLICY["timezone"] != "Asia/Shanghai":
    raise RuntimeError("Unsupported newspaper production policy")
BEIJING = ZoneInfo(POLICY["timezone"])
CUTOFF = dt.time.fromisoformat(POLICY["cutoff_bjt"])
REPORTING_SPAN = dt.timedelta(days=1)
PREPARATION_SPAN = dt.timedelta(days=1)  # same Beijing edition day

if CUTOFF != dt.time(0) or not POLICY["send_crons_utc"]:
    raise RuntimeError("Newspaper requires midnight cutoff and at least one startup cron")


def subject(edition: dt.date) -> str:
    return f"{POLICY['mail_subject_prefix']}｜{edition.isoformat()} {POLICY['cutoff_bjt']}截稿"


def edition_window(now: dt.datetime):
    if not isinstance(now, dt.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    local = now.astimezone(BEIJING)
    day = local.date() if local.time() >= CUTOFF else local.date()-dt.timedelta(days=1)
    end = dt.datetime.combine(day,CUTOFF,tzinfo=BEIJING)
    return end-REPORTING_SPAN,end,day


def check_preparation_window(now: dt.datetime,end: dt.datetime):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    local=now.astimezone(BEIJING)
    if not end <= local < end+PREPARATION_SPAN:
        raise RuntimeError("Outside same-day Beijing edition preparation window")


def check_send_window(now: dt.datetime, day: dt.date):
    """Allow immediate handoff whenever today's edition is ready."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    if now.astimezone(BEIJING).date() != day:
        raise RuntimeError("Refusing to send an edition on a different Beijing date")
