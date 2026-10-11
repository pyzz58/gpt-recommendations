"""Fail-closed, offline production readiness report.

Never performs media generation, networking, billing, image transfer or publishing.
Its JSON fields are informational. No paid execution can be authorized by a
self-attested JSON document, including a passing report from this module.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROUTES = {"ai_video", "static_post", "edit_composite", "live_action_insert", "post_production"}
VISUAL_ROUTES = {"ai_video", "static_post"}


def evaluate(package):
    """Inspect compiled director tasks without trusting their approval claims."""
    findings = []

    def issue(code, shot_id=None, detail=""):
        findings.append({"code": code, "severity": "blocker", "shot_id": shot_id,
                         "detail": detail})

    if not isinstance(package, dict):
        issue("INVALID_PACKAGE", detail="compiled package must be a JSON object")
        return _result(findings, 0)

    if package.get("not_generated_video") is not True or package.get("publishing_allowed") is not False:
        issue("INVALID_SAFETY_FLAGS", detail="draft outputs must explicitly deny generation and publication")
    shots = package.get("shots")
    if not isinstance(shots, list) or not shots:
        issue("INVALID_SHOTS", detail="nonempty compiled shots are required")
        return _result(findings, 0)

    report = package.get("reference_asset_preflight")
    reference_ok = (isinstance(report, dict) and
                    report.get("status") == "preflight_only" and
                    report.get("ready_for_reference_preflight") is True and
                    report.get("blockers") == 0 and report.get("missing") == 0 and
                    report.get("human_visual_consistency_verified") is False and
                    report.get("media_generated") is False)
    seen = set()
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            issue("INVALID_SHOT", detail=f"shot position {index} must be object")
            continue
        sid = shot.get("shot_id")
        if not isinstance(sid, str) or not sid or sid in seen:
            issue("INVALID_SHOT_ID", detail="empty or duplicate shot identifier")
            continue
        seen.add(sid)
        route = shot.get("execution_route")
        if not isinstance(route, str) or route not in ROUTES:
            issue("INVALID_EXECUTION_ROUTE", sid)
            continue
        if shot.get("human_review_required") is not True:
            issue("HUMAN_REVIEW_FLAG_MISSING", sid)
        direction = shot.get("direction")
        qa = direction.get("qa") if isinstance(direction, dict) else None
        if not isinstance(qa, dict) or qa.get("human_approved") is not True:
            issue("HUMAN_SHOT_REVIEW_PENDING", sid)
        if route in VISUAL_ROUTES:
            if not reference_ok or shot.get("reference_preflight_ready") is not True:
                issue("REFERENCES_NOT_VERIFIED", sid,
                      "approved asset catalog, verified bytes and rights evidence needed")
            if shot.get("reference_media_supplied") is not True:
                issue("REFERENCE_MEDIA_NOT_DELIVERED", sid,
                      "a planned reference binding is not a model-uploaded image")
        if route == "ai_video":
            prompts = shot.get("prompts")
            if not isinstance(prompts, dict) or not any(isinstance(x, str) and x.strip() for x in prompts.values()):
                issue("AI_PROMPT_MISSING", sid)
        else:
            if shot.get("prompts") != {}:
                issue("NON_VIDEO_HAS_VIDEO_PROMPTS", sid)
            if not isinstance(shot.get("postproduction_job"), dict):
                issue("POSTPRODUCTION_JOB_MISSING", sid)

    summary = package.get("production_summary")
    if not isinstance(summary, dict):
        issue("PRODUCTION_SUMMARY_MISSING")
    elif summary.get("ai_video_jobs") != sum(s.get("execution_route") == "ai_video" for s in shots if isinstance(s, dict)):
        issue("PRODUCTION_COUNT_MISMATCH")
    return _result(findings, len(seen))


def _result(findings, count):
    return {"version": 1, "status": "offline_review_only", "shot_count": count,
            "blocker_count": len(findings), "metadata_preflight_passed": not findings,
            "execution_authorized": False, "paid_api_enabled": False,
            "publishing_authorized": False,
            "reason": "Offline QA cannot authorize payment, media generation or publication; explicit operator approval and an independent future runtime gate are always required.",
            "findings": findings}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Read-only offline production gate; no API")
    parser.add_argument("--compiled", required=True)
    args = parser.parse_args(argv)
    try:
        package = json.loads(Path(args.compiled).read_text(encoding="utf-8"))
        result = evaluate(package)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result["blocker_count"] else 0
    except (ValueError, OSError, TypeError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
