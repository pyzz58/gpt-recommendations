#!/usr/bin/env python3
"""GitHub Actions-only synthetic vertical slice. NEVER use real documents.

Run only on the repository's invented letter story from test fixtures:
long article -> episode intake -> editor & director synthetic pitches ->
unapproved structural planning lock -> ten simulated DeepSeek-format role
responses -> independent QA -> production_delivery real work-order compiler.

This does not authenticate users, call a provider or generate video. Exports
public TEST FIXTURE artifacts, not trustworthy filmmaking recommendations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))

import agent_team as team
import agent_live_pilot as pilot
import agent_handoff_audit as handoff
import agent_creative_review as craft
import editorial_review_lock as reviews
import production_delivery as delivery
import test_agent_live_crew as synthetic


def run_synthetic_only(output_dir):
    """Writes public synthetic only to a NEW, empty destination folder."""
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("DEMO_OUTPUT_DIRECTORY_MUST_BE_EMPTY")
    if output_dir.is_symlink():
        raise ValueError("DEMO_OUTPUT_SYMLINK_BLOCKED")
    fixture = synthetic.LockedCrewPilotTests(
        methodName="test_full_chain_exports_real_video_model_work_orders_not_only_team_flags")
    fixture.setUp()
    try:
        # Fake credentials/permission intents inside the test fixture are NOT
        # evidence of the author's informed consent or identity validation.
        with tempfile.TemporaryDirectory(prefix="ai-director-synthetic-ledger-") as tmp:
            with pilot.PilotJournal(tmp, fixture.config) as budget:
                state = fixture.state
                mock_receipts = []
                for stage in team.SPECS:
                    state, receipt = fixture._step(budget, state, stage)
                    if receipt["network_attempted"] or receipt["transport"] != "synthetic_fixture":
                        raise ValueError("DEMO_NON_SYNTHETIC_TRANSPORT_BLOCKED")
                    mock_receipts.append({
                        "task_id": stage, "revision": receipt["revision"],
                        "source": "PREWRITTEN_SYNTHETIC_JSON_NOT_AI",
                    })
                if team.ready(state):
                    raise ValueError("DEMO_CREW_NOT_COMPLETE")
                qa = handoff.audit_handoffs(state, fixture.plan)
                review = craft.review_team(state, fixture.plan)
                package = delivery.build_locked_crew_delivery(
                    fixture.snapshot, fixture.original, state)
                markdown = delivery.render_operator_markdown(package)
                counts = package["production_counts"]
                summary = {
                    "kind": "PUBLIC_SYNTHETIC_VERTICAL_DEMO_NOT_REAL_AI",
                    "synthetic_source_id": "SYNTHETIC_ENVELOPE_STORY_ONLY",
                    "source_digest": hashlib.sha256(
                        fixture.original.encode("utf-8")).hexdigest(),
                    "locked_plan_digest": fixture.snapshot["plan_digest"],
                    "ten_roles_executed_as": "PREWRITTEN_OFFLINE_FIXTURE_RESPONSES",
                    "stages": mock_receipts,
                    "roles_count": len(mock_receipts),
                    "shots_count": package["project"]["total_shots"],
                    "runtime_s": package["project"]["duration_s"],
                    "video_prompt_jobs": counts["ai_video_jobs"],
                    "postproduction_jobs": counts["non_video_jobs"],
                    "handoff_audit_status": qa["status"],
                    "creative_review_status": review["status"],
                    "team_workbook_gate": package["full_workbook_review"]["team_delivery_gate"],
                    "media_generated": False,
                    "human_identity_or_approval_verified": False,
                    "real_deepseek_calls": 0,
                    "real_video_calls": 0,
                    "paid_model_authorized": False,
                    "source_facts_verified": False,
                    "ready_for_publication": False,
                }
        output_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "SYNTHETIC_DEMO_NOT_REAL_AI.json": json.dumps(
                package, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            "SYNTHETIC_DEMO_NOT_REAL_AI.md": markdown + "\n",
            "SYNTHETIC_DEMO_EXECUTION_EVIDENCE.json": json.dumps(
                summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            "README.txt": (
                "PUBLIC SYNTHETIC TEST FIXTURE — NOT REAL AI OUTPUT.\n"
                "All creative responses are prewritten synthetic JSON from "
                "test fixtures, NOT genuine DeepSeek creative work.\n"
                "No private/user-uploaded article, actual AI video, API calls, "
                "payment authorization, validated author review or medical "
                "fact verification exists in this archive.\n"
                "Read the Markdown per-shot work orders and execution evidence "
                "to assess the pipeline's shape, not artistic quality.\n"),
        }
        for name, content in files.items():
            with (output_dir / name).open("x", encoding="utf-8") as f:
                f.write(content)
        print("SYNTHETIC_VERTICAL_DEMO_OK: roles=%d shots=%d AI_video=%d post=%d external_calls=0" %
              (len(mock_receipts), summary["shots_count"],
               summary["video_prompt_jobs"], summary["postproduction_jobs"]))
        return summary
    finally:
        fixture.doCleanups()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Public synthetic demo, no network")
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        run_synthetic_only(args.output_dir)
        return 0
    except Exception:
        # Never print user-provided path, unknown content or a raw traceback.
        print("SYNTHETIC_VERTICAL_DEMO_FAILED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
