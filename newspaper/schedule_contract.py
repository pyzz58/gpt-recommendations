"""Deterministic schedule-phase selection; called by the production workflow.

Never silently treat an unrecognized cron string as a send request.
This module must work on Python's standard library before pip dependencies.
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
from production_policy import POLICY, BEIJING


def choose_phase(event: str, cron: str, dry_run: str, now: dt.datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware clock required")
    if event == "push":
        return "send"  # Dedicated marker-path push only; workflow restricts paths.
    if event == "schedule":
        if cron not in POLICY["send_crons_utc"]:
            raise RuntimeError("Unknown scheduled cron; refusing unexpected production run")
        return "send"
    if event == "workflow_dispatch" and dry_run == "false":
        return "send"
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
