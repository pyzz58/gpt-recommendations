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
SEND_START = dt.time.fromisoformat(POLICY["allowed_delivery_start_bjt"])
SEND_END = dt.time.fromisoformat(POLICY["allowed_delivery_end_bjt"])
REPORTING_SPAN = dt.timedelta(days=1)
PREPARATION_SPAN = dt.timedelta(hours=2)  # midnight to 02:00 BJT, includes fallback

if not (CUTOFF == dt.time(0) and SEND_START == dt.time(1) and SEND_END == dt.time(2)):
    raise RuntimeError("Newspaper requires 00:00 cutoff and 01:00–02:00 delivery")
if len(POLICY["prepare_crons_utc"]) < 2 or len(POLICY["send_crons_utc"]) < 3:
    raise RuntimeError("Missing newspaper recovery cron entries")


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
        raise RuntimeError("Outside 00:00–02:00 Beijing preparation window")


def check_send_window(now: dt.datetime,day: dt.date):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    local=now.astimezone(BEIJING)
    start=dt.datetime.combine(day,SEND_START,tzinfo=BEIJING)
    end=dt.datetime.combine(day,SEND_END,tzinfo=BEIJING)
    if not start <= local < end:
        raise RuntimeError("Outside same-day Beijing 01:00–02:00 SMTP window")
