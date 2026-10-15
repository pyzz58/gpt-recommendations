"""Validate the single external scheduled startup contract against existing GitHub workflow.

No GitHub-native cron. ChatGPT's scheduled task updates only a dedicated
main-branch marker; GitHub push launches the existing production job.
"""
from __future__ import annotations

from pathlib import Path
import re
from production_policy import POLICY


def workflow_text() -> str:
    return (Path(__file__).resolve().parent.parent / ".github/workflows/newspaper.yml").read_text(encoding="utf-8")


def list_workflow_crons():
    return re.findall(r"^    - cron: '([^']+)'$", workflow_text(), re.M)


def verify() -> bool:
    text = workflow_text()
    if POLICY["startup_mode"] != "external-marker-push":
        raise AssertionError("Unknown external scheduler type")
    if POLICY["startup_branch"] != "main" or POLICY["startup_time_bjt"] != "00:01" or POLICY["startup_timezone"] != "Asia/Shanghai":
        raise AssertionError("External scheduled startup must be Beijing 00:01, main branch")
    if re.search(r"^  schedule:\s*$", text, re.M) or list_workflow_crons():
        raise AssertionError("Obsolete native GitHub cron exists")
    expected = (
        "  push:\n"
        "    branches: [main]\n"
        "    paths:\n"
        f"      - '{POLICY['startup_marker_path']}'\n"
    )
    if expected not in text:
        raise AssertionError("External scheduler push does not match the canonical marker path")
    if "python newspaper/digest.py --prepare" not in text or "python newspaper/prepared_delivery.py" not in text:
        raise AssertionError("Existing newspaper build/delivery pipeline was disconnected")
    return True


if __name__ == "__main__":
    verify()
    print("NEWSPAPER_EXTERNAL_STARTUP_OK policy=production_policy.json")
