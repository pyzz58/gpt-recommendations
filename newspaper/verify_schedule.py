"""Fail CI if actual GitHub cron differs from the single production policy."""
from __future__ import annotations
import datetime as dt
from pathlib import Path
import re
from production_policy import POLICY, BEIJING


def list_workflow_crons():
    workflow=(Path(__file__).resolve().parent.parent/".github/workflows/newspaper.yml").read_text(encoding="utf-8")
    return re.findall(r"^    - cron: '([0-9]+ [0-9]+ \* \* \*)'\s*$",workflow,re.M)


def verify():
    actual=list_workflow_crons()
    expected=POLICY["prepare_crons_utc"]+POLICY["send_crons_utc"]
    if actual != expected or len(actual)!=len(set(actual)):
        raise AssertionError(f"Newspaper YAML cron differs from production_policy.json: {actual!r} vs {expected!r}")
    for i,cron in enumerate(actual):
        minute,hour,_,_,_=cron.split()
        # Convert UTC cron wall-clock to Beijing clock, accounting for a date offset.
        local=(dt.datetime(2026,10,13,int(hour),int(minute),tzinfo=dt.timezone.utc)).astimezone(BEIJING)
        target=0 if i < len(POLICY["prepare_crons_utc"]) else 1
        if local.hour!=target:
            raise AssertionError(f"Expected Beijing {target:02}:xx, got {local:%H:%M}: {cron}")
    return True


if __name__=="__main__":
    verify()
    print("NEWSPAPER_SCHEDULE_CONTRACT_OK policy=production_policy.json")
