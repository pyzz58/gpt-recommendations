"""Fail CI if the one production cron differs from canonical production_policy.json."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import re
from production_policy import POLICY, BEIJING


def list_workflow_crons():
    workflow=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text(encoding="utf-8")
    return re.findall(r"^    - cron: '([^']+)'$",workflow,re.M)


def verify():
    configured=POLICY["startup_cron_utc"]
    crons=list_workflow_crons()
    if crons != [configured]:
        raise AssertionError(f"Expected exactly one startup cron {configured!r}, found {crons!r}")
    minute,hour,_,_,_=configured.split()
    actual=(dt.datetime(2026,10,14,int(hour),int(minute),tzinfo=dt.timezone.utc)).astimezone(BEIJING)
    if (actual.hour,actual.minute)!=(0,1):
        raise AssertionError(f"Beijing startup must be 00:01, got {actual:%H:%M}")
    return True


if __name__=="__main__":
    verify()
    print("NEWSPAPER_SINGLE_SCHEDULE_OK policy=production_policy.json")
