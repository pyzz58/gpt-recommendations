"""Deterministic schedule-phase selection; called by the production workflow.

Never silently treat an unrecognized cron string as a send request.
This module must work on Python's standard library before pip dependencies.
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
from production_policy import POLICY, BEIJING, SEND_START, SEND_END


def choose_phase(event: str, cron: str, dry_run: str, now: dt.datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    if event == "schedule":
        if cron in POLICY["prepare_crons_utc"]:
            planned = "prepare"
        elif cron in POLICY["send_crons_utc"]:
            planned = "send"
        else:
            raise RuntimeError("Unknown scheduled cron; refusing unexpected production run")
        local_time = now.astimezone(BEIJING).time()
        if local_time >= SEND_END:
            return "expired"
        if planned == "prepare" and local_time >= SEND_START:
            return "send"
        if planned == "send" and local_time < SEND_START:
            return "wait"
        return planned
    if event == "repository_dispatch":
        local_time = now.astimezone(BEIJING).time()
        if local_time >= SEND_END:
            return "expired"
        return "send" if local_time >= SEND_START else "prepare"
    if event == "workflow_dispatch" and dry_run == "false":
        local_time = now.astimezone(BEIJING).time()
        return "send" if SEND_START <= local_time < SEND_END else "expired"
    return "preview"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--cron", default="")
    parser.add_argument("--dry-run", default="true")
    args = parser.parse_args()
    phase = choose_phase(args.event, args.cron, args.dry_run,
                         dt.datetime.now(BEIJING))
    print(f"Newspaper policy {POLICY['version']}; phase={phase}")
    with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as output:
        output.write(f"phase={phase}\n")


if __name__ == "__main__":
    main()
