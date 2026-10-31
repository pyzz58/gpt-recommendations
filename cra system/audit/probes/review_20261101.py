"""Synthetic reviewer counterexamples against CRA source snapshot 1ff52eb.

This script records defective or limited behavior; exit zero means the diagnostic
completed, never that a clinical feature passed. It performs no DB, OCR, model,
network, patient-data, or production operation.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from cra_app.governance.service import ScopeContext
from cra_app.laboratory.comparison import ObservationValue, EdcValue, compare_observation
from cra_app.laboratory.recognition import extract_observations
from cra_app.laboratory.service import _effective_observation
from cra_app.providers.lab_ocr import (
    LabRecognitionResult, ProviderCell, ProviderLine, ProviderRow, ProviderTable,
)
from cra_app.providers.ports import ParsedAnchor
from cra_app.providers.rule_extraction import AnchoredRuleExtractor
from cra_app.rules.contracts import (
    FactValue, RuleCondition, RuleException, RuleNode, RuleOperand, RuleSourceRef,
)
from cra_app.rules.evaluator import evaluate_condition, evaluate_node
from cra_app.rules.service import (
    CreateActivationCommand, RuleService, RuleValidationError,
)
from cra_app.subjects.calendar import extract_date_interval_specs
from cra_app.subjects.service import SubjectService

OBSERVATIONS = []

def record(case, finding, expected, observed, reproduced, evidence_kind="actual_component_call"):
    OBSERVATIONS.append({
        "case": case, "finding": finding, "expected_correct_behavior": expected,
        "observed": observed, "finding_reproduced": bool(reproduced),
        "evidence_kind": evidence_kind,
    })

def ref():
    return RuleSourceRef(anchor_key="review-synthetic-1", quote="Pure synthetic reviewer example.")

def operand(key):
    return RuleOperand(kind="fact_ref", fact_key=key)

def literal(value, unit=None):
    return RuleOperand(kind="literal", value=value, unit=unit)

def equals(key, value):
    return RuleCondition(op="eq", left=operand(key), right=literal(value))

def fact_date(value):
    return SimpleNamespace(value_type="date", value_raw=value)

def source_observation():
    return SimpleNamespace(
        subject_external_id="SYNTH-REVIEW-001", visit_key="V1", analyte_raw="Synthetic",
        specimen="serum", collected_on=date(2021, 1, 1), collected_at=None,
        instance_type_raw="initial", report_on=date(2021, 1, 1), report_revision="1",
        value_raw="121", unit_raw="g/L", lower_limit_raw="100", upper_limit_raw="150",
        extraction_state="auto_extracted", validation_state="ready_for_match", issues=[],
    )

base = source_observation()
corrected = _effective_observation(
    base, SimpleNamespace(action="correct", corrected_fields={"value_raw": "119"})
)
confirmed = _effective_observation(
    base, SimpleNamespace(action="confirm", corrected_fields={})
)
record(
    "correct_then_confirm", "CRA-REV-20261101-01",
    "A later confirmation retains the current corrected value 119.",
    {"after_correction": corrected.fields["value_raw"],
     "after_later_confirmation": confirmed.fields["value_raw"]},
    corrected.fields["value_raw"] == "119" and confirmed.fields["value_raw"] == "121",
)
second_patch = _effective_observation(
    base, SimpleNamespace(action="correct", corrected_fields={"unit_raw": "synthetic/unit"})
)
record(
    "successive_partial_corrections", "CRA-REV-20261101-01",
    "Correcting a different field retains an earlier value correction.",
    {"earlier_value": corrected.fields["value_raw"],
     "value_after_latest_partial_patch": second_patch.fields["value_raw"]},
    second_patch.fields["value_raw"] == "121",
)

node = RuleNode(
    node_key="R-REVIEW-EXCEPTION", summary="Synthetic conditional task",
    trigger=equals("base_ready", True),
    exceptions=[RuleException(exception_key="E1", description="Synthetic exception",
                              condition=equals("exception_flag", True), source_refs=[ref()])],
    source_refs=[ref()],
)
result = evaluate_node(node, {"base_ready": FactValue(value=True)})
record(
    "unknown_exception_fact", "CRA-REV-20261101-02",
    "Unknown exception applicability stays unknown or requires clarification.",
    result.model_dump(mode="json"),
    result.status == "applicable" and any(e.result == "unknown" for e in result.exceptions),
)
unit_result = evaluate_condition(
    RuleCondition(op="gt", left=operand("synthetic_measurement"),
                  right=literal("7", "synthetic/unit")),
    {"synthetic_measurement": FactValue(value="9", unit=None)},
)
record(
    "missing_unit_in_dimensioned_comparison", "CRA-REV-20261101-02",
    "An unresolved required measurement unit returns unknown.",
    unit_result.model_dump(mode="json"), unit_result.result == "true",
)

window_node = RuleNode(
    node_key="R-REVIEW-WINDOW", summary="Synthetic gated date window",
    preconditions=[equals("needs_extra_check", True)],
    trigger=RuleCondition(op="date_interval", anchor_fact_key="anchor_date",
                          fact_key="actual_date", min_days=0, max_days=2),
    source_refs=[ref()],
)
window_eval = evaluate_node(window_node, {
    "needs_extra_check": FactValue(value=False),
    "anchor_date": FactValue(value="2021-01-01"),
    "actual_date": FactValue(value="2021-01-06"),
})
spec = extract_date_interval_specs(window_node)[0]
subject_service = SubjectService.__new__(SubjectService)
ungated_status, _ = subject_service._requirement_status(
    spec=spec, anchor=fact_date("2021-01-01"), actual=fact_date("2021-01-06"),
    active_decision=None,
)
record(
    "inapplicable_rule_window_path", "CRA-REV-20261101-03",
    "A false prerequisite prevents an active visit-window obligation.",
    {"rule_evaluation": window_eval.status, "specs_emitted": 1,
     "ungated_window_classification": ungated_status,
     "caller_reference": "subjects/service.py:1690-1707 ignores applicability evaluation"},
    window_eval.status == "not_applicable" and ungated_status == "out_of_window",
    "actual_component_calls_plus_static_caller_trace",
)
unknown_status, _ = subject_service._requirement_status(
    spec=spec, anchor=fact_date("2021-01-01"),
    actual=SimpleNamespace(value_type="string", value_raw="unknown"),
    active_decision=None,
)
record(
    "unknown_actual_date", "CRA-REV-20261101-03",
    "An actual date that cannot be determined remains unknown_actual.",
    {"classification": unknown_status}, unknown_status == "out_of_window",
)

study_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
site_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
version_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
rule_service = RuleService.__new__(RuleService)
rule_service._load_document_version = lambda scope, version: (
    SimpleNamespace(study_id=study_id, site_id=None),
    SimpleNamespace(site_id=None),
)
rule_service._authorize_write = lambda *args: None
rejection = None
try:
    rule_service.create_activation(
        ScopeContext(actor_id="reviewer-synthetic", tenant_id="synthetic"),
        CreateActivationCommand(idempotency_key="review-site-activation",
                                document_version_id=version_id, site_id=site_id,
                                starts_on=date(2021, 1, 1), reason="Synthetic site adoption"),
    )
except RuleValidationError as exc:
    rejection = str(exc)
record(
    "site_activation_of_shared_protocol", "CRA-REV-20261101-04",
    "An authorized shared project document can have an explicit site adoption date.",
    {"validation_rejection": rejection},
    rejection == "a study-wide document cannot be activated for one site",
    "actual_command_guard_with_stubbed_authorized_source",
)

extraction = AnchoredRuleExtractor().extract_rules(anchors=[
    ParsedAnchor(anchor_type="plain_text", logical_node_id="review-plain-rule",
                 text="每次访视应核对指定资料，无法完成时记录原因。", ordinal=1),
])
record(
    "ordinary_chinese_rule_prose", "CRA-REV-20261101-05",
    "Ordinary rule-purpose prose produces reviewable candidates or explicit semantic gaps.",
    {"rules": len(extraction.rules),
     "coverage": [item.model_dump(mode="json") for item in extraction.coverage],
     "warnings": extraction.warnings},
    len(extraction.rules) == 0
    and all(item.status == "processed" for item in extraction.coverage),
)

common = dict(subject_external_id="SYNTH-REVIEW-001", visit_key="V1", analyte="Synthetic",
              specimen="serum", collected_on=date(2021, 1, 1), collected_at=None,
              instance_type="initial", report_on=date(2021, 1, 1), report_revision="1",
              value_raw="10", unit="g/L", lower_limit="1")
source = ObservationValue(id="source-review", upper_limit="20", **common)
edc = EdcValue(id="edc-review", subject_id="synthetic-subject", upper_limit="30", **common)
comparison = compare_observation(source, [edc])
record(
    "different_reference_limits_same_range_flag", "CRA-REV-20261101-06",
    "Different reference bounds are retained as a reference-range discrepancy.",
    {"result_status": comparison.result_status,
     "source_upper_limit": "20", "edc_upper_limit": "30",
     "fields": [{"field": f.field, "status": f.status,
                 "source": f.source, "edc": f.edc} for f in comparison.field_results]},
    comparison.result_status == "agreement",
)

def row(*values):
    return ProviderRow(cells=tuple(ProviderCell(v, (1.0, 2.0, 30.0, 12.0)) for v in values))

header_result = LabRecognitionResult(
    provider_name="reviewer-structured-input", provider_version="1", model_version=None,
    file_format="text_pdf",
    tables=(ProviderTable(
        index=1, page=1, bbox=(0.0, 50.0, 500.0, 200.0),
        rows=(row("Analyte", "Result", "Unit", "LLN", "ULN"),
              row("Hemoglobin", "121", "g/L", "100", "150")),
    ),),
    lines=(
        ProviderLine("Subject ID: SYNTH-REVIEW-001", 1, (0.0, 0.0, 300.0, 12.0)),
        ProviderLine("Collection Date: 2021-01-01", 1, (0.0, 14.0, 300.0, 26.0)),
        ProviderLine("Instance: Initial", 1, (0.0, 28.0, 300.0, 40.0)),
    ),
    warnings=(),
)
header_draft = extract_observations(header_result)
record(
    "report_header_context_outside_result_rows", "CRA-REV-20261101-07",
    "Recognized report-level identity/date/instance can be bound once and reused across rows.",
    {"rows": len(header_draft.rows), "state": header_draft.state,
     "row_issues": [list(r.issues) for r in header_draft.rows]},
    bool(header_draft.rows)
    and all(r.validation_state == "needs_review" for r in header_draft.rows),
    "actual_field_extractor_call_with_synthetic_parsed_provider_output_no_OCR_run",
)

payload = {
    "schema_version": 1,
    "reviewed_source_commit": "1ff52eb1c91ccc312cc03aab9700d00fb378b217",
    "execution_commit": os.environ.get("GITHUB_SHA"),
    "scope": "synthetic component counterexamples, not clinical or complete API validation",
    "diagnostic_completed": True,
    "acceptance_passed": False,
    "meaning_of_successful_process": "diagnostics executed; reproduced findings remain OPEN",
    "observations": OBSERVATIONS,
    "cases": len(OBSERVATIONS),
    "findings_reproduced": sum(item["finding_reproduced"] for item in OBSERVATIONS),
}
print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
