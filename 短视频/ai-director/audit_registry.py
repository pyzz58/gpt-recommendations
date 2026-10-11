#!/usr/bin/env python3
"""Fail-closed metadata gate for the AI Director's continuous audit registry.

The register MUST distinguish evidenced fixes, confirmed open problems,
investigations, and issues impossible to verify without real media/consent.
This script never reads private manuscripts, fetches external code, calls a
model, invokes GitHub APIs or creates new GitHub issues.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

DEFAULT = Path(__file__).with_name("AUDIT_FINDINGS.json")
STATUSES = frozenset({
    "fixed_regression_verified","open_confirmed",
    "investigate","blocked_real_media",
})
PRIORITIES = frozenset({"P0","P1","P2","P3"})
EVIDENCES = frozenset({
    "confirmed_code","confirmed_real_fiction_sample",
    "real_media_absent","code_review_only",
    "verified_one_paid_fiction_trial",
    "synthetic_only","upstream_license_verified",
    "coverage_baseline_pending",
})
FIELDS = frozenset({
    "id","priority","domain","status","evidence_type",
    "description","source","test_evidence","issue_url","fix_commit",
})


class AuditRegistryError(ValueError):
    pass


def validate_registry(data):
    if (not isinstance(data, dict) or
            data.get("registry_version") != "1.0" or
            data.get("no_paid_requests_by_audit") is not True or
            not isinstance(data.get("findings"), list) or
            len(data["findings"]) < 10):
        raise AuditRegistryError("AUDIT_INVALID_REGISTRY_ROOT")
    ids = set()
    for i, item in enumerate(data["findings"]):
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise AuditRegistryError("AUDIT_MISSING_OR_EXTRA_FIELDS")
        ident = item["id"]
        if (not isinstance(ident,str) or
                re.fullmatch(r"AUD-[0-9]{3}",ident) is None or
                ident in ids):
            raise AuditRegistryError("AUDIT_DUPLICATE_OR_BAD_ID")
        ids.add(ident)
        if (item["status"] not in STATUSES or
                item["priority"] not in PRIORITIES or
                item["evidence_type"] not in EVIDENCES or
                any(not isinstance(item[k],str) or not item[k].strip()
                    for k in ("domain","description","source"))):
            raise AuditRegistryError("AUDIT_INVALID_FACT_FIELDS")
        if item["status"] == "fixed_regression_verified" and (
                not item["test_evidence"] or
                re.fullmatch(r"[a-f0-9]{40}",item["fix_commit"]) is None):
            raise AuditRegistryError("AUDIT_FALSE_VERIFIED_COMPLETION")
        if (item["status"] == "open_confirmed" and
                item["priority"] in {"P0","P1"} and not item["issue_url"] and
                item["id"] in {"AUD-002","AUD-003","AUD-004","AUD-005"}):
            raise AuditRegistryError("AUDIT_OPEN_CRITICAL_ISSUE_UNTRACKED")
        link=item["issue_url"]
        if link and (not isinstance(link,str) or
                     re.fullmatch(
                         r"https://github[.]com/pyzz58/gpt-recommendations/issues/[0-9]+",
                         link) is None):
            raise AuditRegistryError("AUDIT_ISSUE_URL_OUT_OF_SCOPE")
        if item["status"] == "blocked_real_media" and (
                item["evidence_type"] != "real_media_absent"):
            raise AuditRegistryError("AUDIT_UNSUPPORTED_REAL_MEDIA_CLAIM")
    return {
        "registry_version":"1.0","findings_total":len(ids),
        "status_counts":dict(Counter(x["status"] for x in data["findings"])),
        "priority_counts":dict(Counter(x["priority"] for x in data["findings"])),
        "open_p0":[x["id"] for x in data["findings"]
                   if x["priority"]=="P0" and x["status"]!="fixed_regression_verified"],
        "real_model_calls_from_audit":0,
        "automated_artistic_quality_proven":False,
        "real_media_feasibility_proven":False,
        "private_source_exposed":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description="Validate offline issue/claim evidence")
    p.add_argument("--registry",default=str(DEFAULT))
    p.add_argument("--summary-out",default=None)
    args=p.parse_args(argv)
    try:
        source=Path(args.registry)
        report=validate_registry(json.loads(source.read_text("utf-8")))
        if args.summary_out:
            path=Path(args.summary_out)
            with path.open("x",encoding="utf-8") as f:
                json.dump(report,f,ensure_ascii=False,indent=2)
                f.write("\n")
        print("AI_DIRECTOR_AUDIT_REGISTRY_OK: issues=%d p0_open=%d paid_calls=0" %
              (report["findings_total"],len(report["open_p0"])))
        return 0
    except (OSError,ValueError,TypeError):
        print("AI_DIRECTOR_AUDIT_REGISTRY_FAILED",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
