"""Independent forward acceptance checks for branch-linked visit windows.

Assertions describe correct behavior, not successful reproduction of defects.
All inputs are synthetic; APIs use disposable PostgreSQL.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "cra_closure_existing_subjects", ROOT / "tests/integration/test_subjects.py"
)
_existing = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _existing
_spec.loader.exec_module(_existing)

engine = _existing.engine
queue = _existing.queue
session_factory = _existing.session_factory
settings = _existing.settings
services = _existing.services
api = _existing.api

from cra_app.subjects.contracts import FactImportRow

pytestmark = pytest.mark.postgres


def _eq(key, value):
    return {
        "op": "eq",
        "left": {"kind": "fact_ref", "fact_key": key},
        "right": {"kind": "literal", "value": value},
    }


def _confirm_branch_child(api, services, shape):
    _existing._upload_gated_text_window_rule(api, services)
    listed = api.get(
        f"/api/v1/studies/{services['study']}/rules",
        params={"site_id": str(services["site_a"])},
    )
    assert listed.status_code == 200, listed.text
    item = next(r for r in listed.json() if r["rule_key"] == "R-WINDOW-GATED-01")
    version_id = item["current_version"]["id"]
    detail = api.get(f"/api/v1/rule-versions/{version_id}")
    assert detail.status_code == 200, detail.text
    tree = detail.json()["tree"]
    source_refs = tree["source_refs"]
    interval = {
        "op": "date_interval",
        "fact_key": "visit_date",
        "anchor_fact_key": "infusion_date",
        "min_days": -2,
        "max_days": 2,
        "inclusive": True,
    }
    leaf = {
        "node_key": "RECHECK-BRANCH-WINDOW",
        "summary": "Pure synthetic branch-linked check",
        "trigger": interval,
        "required_facts": ["infusion_date", "visit_date"],
        "source_refs": source_refs,
    }
    if shape == "direct":
        target = leaf
    else:
        target = {
            "node_key": "RECHECK-BRANCH-CONTAINER",
            "summary": "Pure synthetic branch-selected child list",
            "children": [leaf],
            "source_refs": source_refs,
        }
    group = {
        "node_key": "RECHECK-BRANCH-GROUP",
        "summary": "Pure synthetic conditional child list",
        "trigger": _eq("screening_active", True),
        "branches": [{
            "branch_key": "RECHECK-SELECT",
            "label": "Synthetic eligible branch",
            "condition": _eq("gate_ok", True),
            "target_node_ids": [target["node_key"]],
            "source_refs": source_refs,
        }],
        "children": [target],
        "source_refs": source_refs,
    }
    confirmed = api.post(
        f"/api/v1/rules/{item['id']}/confirmation",
        json={
            "expected_revision": item["revision"],
            "idempotency_key": "closure-branch-link-confirm",
            "base_version_id": version_id,
            "reason": "Pure synthetic branch-selection and child-window acceptance",
            "operations": [{"op": "add_child", "child": group}],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert confirmed.status_code == 200, confirmed.text
    version = api.get(f"/api/v1/rule-versions/{confirmed.json()['rule_version_id']}")
    assert version.status_code == 200, version.text
    saved = next(c for c in version.json()["tree"]["children"]
                 if c["node_key"] == "RECHECK-BRANCH-GROUP")
    assert saved["branches"][0]["target_node_ids"] == [target["node_key"]]
    assert saved["children"][0]["node_key"] == target["node_key"]


@pytest.mark.parametrize(
    "shape,gate,expected",
    [
        ("direct", True, "out_of_window"),
        ("container", False, "not_applicable"),
        ("container", None, "unknown_applicability"),
        ("container", True, "out_of_window"),
    ],
    ids=["direct-selected-window", "container-false", "container-unknown", "container-true-control"],
)
def test_branch_target_keeps_its_window_and_selection_context(api, services, shape, gate, expected):
    _confirm_branch_child(api, services, shape)
    source = {
        "source_type": "record",
        "source_id": "pure-synthetic-branch-facts",
        "locator": "synthetic/branch-linked-window",
        "quote": "Pure synthetic eligibility and date facts",
    }
    values = [
        ("screening_active", "true", "boolean"),
        ("infusion_date", "2026-01-01", "date"),
        ("visit_date", "2026-01-10", "date"),
    ]
    if gate is not None:
        values.append(("gate_ok", str(gate).lower(), "boolean"))
    _existing._import_rows(
        services,
        [FactImportRow(
            subject_external_id="SYN-BRANCH-LINK",
            fact_key=key,
            value_raw=value,
            value_type=value_type,
            observed_on=date(2026, 1, 1),
            source_ref=source,
        ) for key, value, value_type in values],
        key="closure-branch-link-facts",
    )
    subject = _existing._subject_by_external(api, services, "SYN-BRANCH-LINK")
    body = _existing._evaluate(api, subject["id"], "2026-01-10")
    selected = [
        item for item in body["requirements"]
        if "RECHECK-BRANCH-WINDOW" in item["requirement"]["visit_key"]
    ]
    observed = [item["window_status"] for item in selected]
    passed = len(selected) == 1 and observed == [expected]
    print("CRA_CLOSURE_FORWARD_RESULT=" + json.dumps({
        "source_commit": "f66750c9fac58dbf2e03189582a3544fc039bfd4",
        "original_finding": "CRA-REV-20261101-03",
        "shape": shape,
        "branch_fact": gate,
        "expected": [expected],
        "observed": observed,
        "requirement_count": len(selected),
        "acceptance_passed": passed,
        "evidence_kind": "public_confirmation_and_visit_requirement_API_with_PostgreSQL",
    }, ensure_ascii=False))
    assert len(selected) == 1, "Selected child window must not disappear"
    assert observed == [expected], "Branch selection must reach its target descendants"
