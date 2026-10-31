"""Independent remediation diagnostics. Green means reproduction completed.

These are observations of remaining defects, not acceptance tests.
Only synthetic fixtures and a disposable PostgreSQL database are used.
"""
from __future__ import annotations
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "cra_recheck_existing_rules", ROOT / "tests/integration/test_rules.py"
)
_existing = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _existing
_spec.loader.exec_module(_existing)
engine = _existing.engine
queue = _existing.queue
session_factory = _existing.session_factory
settings = _existing.settings
services = _existing.services

from cra_app.documents.service import CreateDocumentCommand
from cra_app.rules.contracts import FactValue, RuleCondition, RuleException, RuleNode, RuleOperand, RuleSourceRef
from cra_app.rules.evaluator import evaluate_node
from cra_app.rules.service import ApplicableRuleQuery, CreateActivationCommand, ExtractRuleCommand
from cra_app.subjects.calendar import extract_date_interval_specs
from cra_app.subjects.service import SubjectService

def emit(case, original_finding, expected, observed, reproduced, evidence_kind):
    print("CRA_RECHECK_RESULT=" + json.dumps({
        "case": case, "original_finding": original_finding,
        "expected_correct_behavior": expected, "observed": observed,
        "finding_reproduced": bool(reproduced),
        "acceptance_passed": False,
        "evidence_kind": evidence_kind,
        "reviewed_source_commit": "5148684064a57e50077dd32d02e76b57b2221fc4",
    }, ensure_ascii=False, default=str))

def eq(key, value):
    return RuleCondition(op="eq",
        left=RuleOperand(kind="fact_ref", fact_key=key),
        right=RuleOperand(kind="literal", value=value))

def source_ref():
    return RuleSourceRef(anchor_key="review-synthetic", quote="Pure synthetic diagnostic rule.")

@pytest.mark.parametrize("gate_case", ["false_parent_precondition", "true_parent_exception"])
def test_nested_window_does_not_inherit_parent_gate(gate_case):
    child = RuleNode(
        node_key="R-RECHECK-CHILD", summary="Synthetic child visit window",
        trigger=RuleCondition(op="date_interval", anchor_fact_key="anchor_date",
                              fact_key="actual_date", min_days=0, max_days=2),
        source_refs=[source_ref()],
    )
    parent = RuleNode(
        node_key="R-RECHECK-PARENT", summary="Synthetic gated parent list",
        preconditions=[eq("needs_check", True)] if gate_case == "false_parent_precondition" else [],
        trigger=eq("ready", True),
        exceptions=[RuleException(
            exception_key="E1", description="Synthetic parent waiver",
            condition=eq("waiver", True), source_refs=[source_ref()],
        )] if gate_case == "true_parent_exception" else [],
        children=[child], source_refs=[source_ref()],
    )
    facts = {"ready": FactValue(value=True), "needs_check": FactValue(value=False),
             "waiver": FactValue(value=True), "anchor_date": FactValue(value="2021-01-01"),
             "actual_date": FactValue(value="2021-01-10")}
    parent_result = evaluate_node(parent, facts)
    specs = extract_date_interval_specs(parent)
    assert len(specs) == 1
    service = SubjectService.__new__(SubjectService)
    status, window = service._requirement_status(
        spec=specs[0],
        anchor=SimpleNamespace(value_type="date", value_raw="2021-01-01"),
        actual=SimpleNamespace(value_type="date", value_raw="2021-01-10"),
        active_decision=None, facts=facts,
    )
    reproduced = status == "out_of_window" and not specs[0].gate_conditions
    emit(gate_case, "CRA-REV-20261101-03",
         "The child obligation inherits the parent's false prerequisite or effective waiver.",
         {"parent_evaluation": parent_result.status,
          "child_gate_count": len(specs[0].gate_conditions),
          "child_window_status": status}, reproduced,
         "actual_calendar_and_requirement_components_plus_static_caller_trace")
    assert reproduced, "Diagnostic assumption changed; reassess rather than declaring this finding reproduced."

def _upload_activate(services, *, site_id, label, action):
    content = (
        f"Rule R-RECHECK-SCOPE-01: Synthetic {label} review instruction.\n"
        "Trigger: scope_ready = true\n"
        f"Branch A: WHEN scope_ready = true THEN {action}\n"
        "Required facts: scope_ready\n"
    ).encode()
    upload = services["documents"].create_document(
        services["admin"], services["study"],
        CreateDocumentCommand(
            expected_revision=0, idempotency_key=f"recheck-{label}-upload",
            site_id=site_id, title=f"Synthetic {label} document",
            document_type="protocol" if site_id is None else "sop",
            purpose="rule", version_label="v1",
        ), filename=f"synthetic_{label}.txt", content=content,
    )
    assert services["documents"].process_job(upload.job_id).status == "completed"
    extraction = services["rules"].extract_candidates(
        services["admin"], upload.document_version_id,
        ExtractRuleCommand(idempotency_key=f"recheck-{label}-extract"),
    )
    assert extraction.confirmed_count == 1
    services["rules"].create_activation(
        services["admin"],
        CreateActivationCommand(
            expected_revision=0, idempotency_key=f"recheck-{label}-activate",
            document_version_id=upload.document_version_id, site_id=site_id,
            starts_on=date(2021, 1, 1), reason="Synthetic independent document activation",
        ),
    )

def test_site_same_key_silently_removes_independent_project_rule(services):
    query = ApplicableRuleQuery(
        study_id=services["study"], site_id=services["site_a"],
        event_date=date(2021, 1, 2), facts={"scope_ready": FactValue(value=True)},
    )
    _upload_activate(services, site_id=None, label="project", action="require synthetic review")
    before = services["rules"].applicable_rules(services["admin"], query)
    project_ids = {str(item.rule.id) for item in before.rules}
    assert len(project_ids) == 1
    _upload_activate(services, site_id=services["site_a"], label="site", action="omit synthetic review")
    after = services["rules"].applicable_rules(services["admin"], query)
    visible_ids = {str(item.rule.id) for item in after.rules}
    reproduced = not (project_ids & visible_ids) and not after.envelope.conflicts
    emit("site_same_key_masks_project", "CRA-REV-20261101-04",
         "Independent project requirements remain or an explicit source conflict is raised; a site document cannot silently waive them.",
         {"project_rule_ids_before": sorted(project_ids),
          "visible_after": [{"id": str(item.rule.id), "layer": item.rule.policy_layer,
                             "summary": item.tree.summary} for item in after.rules],
          "conflicts": [item.model_dump(mode="json") for item in after.envelope.conflicts]},
         reproduced, "actual_document_extraction_activation_and_applicability_services_with_PostgreSQL")
    assert reproduced, "Diagnostic assumption changed; reassess rather than declaring this finding reproduced."
