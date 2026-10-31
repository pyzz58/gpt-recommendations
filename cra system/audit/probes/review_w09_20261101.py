"""W09 synthetic component probes against the pinned in-progress df6f04b snapshot.

No model, OCR, network, database or real clinical data is used.
A successful diagnostic run is not business acceptance.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import uuid
from datetime import date
from types import SimpleNamespace
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source_root / "backend"))

from cra_app.governance.service import ScopeContext
from cra_app.laboratory.comparison import ObservationValue, EdcValue, compare_observation
from cra_app.rules.contracts import RuleNode, RuleSourceRef
from cra_app.safety.contracts import CreateSafetyAssessmentCommand
from cra_app.safety.service import SafetyService, _rule_matches_dimension

study_id = uuid.UUID("00000000-0000-0000-0000-000000000011")
site_id = uuid.UUID("00000000-0000-0000-0000-000000000012")
subject_id = uuid.UUID("00000000-0000-0000-0000-000000000013")
comparison_id = uuid.UUID("00000000-0000-0000-0000-000000000014")
field_id = uuid.UUID("00000000-0000-0000-0000-000000000015")
scope = ScopeContext(actor_id="synthetic-reviewer", tenant_id="synthetic",
                     authentication_source="synthetic-review")
command = CreateSafetyAssessmentCommand(
    idempotency_key="review-w09", study_id=study_id, site_id=site_id,
    subject_id=subject_id, event_type="laboratory_logic", event_date=date(2021, 1, 1),
    requested_dimensions=["ae_collection"], lab_comparison_id=comparison_id,
)
summary = SimpleNamespace(identifiers=[
    SimpleNamespace(external_id="SYNTH-SAFETY-REVIEW")
])

common = dict(subject_external_id="SYNTH-SAFETY-REVIEW", visit_key="V1",
              analyte="Synthetic", specimen="serum", collected_on=date(2021, 1, 1),
              collected_at=None, instance_type="initial", report_on=date(2021, 1, 1),
              report_revision="1", value_raw="99", unit="synthetic/unit",
              lower_limit="1", upper_limit="20")
source = ObservationValue(id="source", **common)
edc = EdcValue(id="edc", subject_id=str(subject_id), **common)
outcome = compare_observation(source, [edc])
field = SimpleNamespace(
    id=field_id, result_status=outcome.result_status,
    matched_identity=outcome.matched_identity, source_value="99",
    source_unit="synthetic/unit", edc_value="99", edc_unit="synthetic/unit",
    field_results=outcome.field_results, reason=outcome.reason,
)
detail = SimpleNamespace(
    comparison=SimpleNamespace(id=comparison_id, study_id=study_id,
                               site_id=site_id, revision=1),
    fields=[field], stale=False, stale_field_ids=(),
)
service = SafetyService.__new__(SafetyService)
service.laboratory = SimpleNamespace(comparison_detail=lambda *_: detail)
observations = []

def record(case, finding, expected, observed, reproduced):
    observations.append({
        "case": case, "finding": finding, "expected_correct_behavior": expected,
        "observed": observed, "finding_reproduced": bool(reproduced),
        "evidence_kind": "actual_component_call_with_synthetic_comparison_service_port",
    })

_, questions, evidence, _ = service._lab_questions(scope, command, summary)
flag = next(f.source for f in outcome.field_results if f.field == "reference_range_flag")
record(
    "consistent_but_abnormal_lab_handoff", "CRA-REV-20261101-11",
    "A consistent abnormal result remains available to the scoped safety review.",
    {"comparison_status": outcome.result_status, "source_range_flag": flag,
     "safety_questions": len(questions), "lab_evidence": len(evidence)},
    outcome.result_status == "agreement" and flag == "above_range"
    and not questions and not evidence,
)
field.result_status = "not_checked_by_user"
_, questions, evidence, _ = service._lab_questions(scope, command, summary)
record(
    "skipped_lab_path_generates_safety_question", "CRA-REV-20261101-11",
    "A local user skip remains skipped and does not itself regenerate this dependent prompt.",
    {"comparison_status": field.result_status, "questions": [q.question for q in questions]},
    bool(questions),
)
field.result_status = "value_difference"
detail.stale = True
detail.stale_field_ids = (field_id,)
_, questions, evidence, _ = service._lab_questions(scope, command, summary)
record(
    "stale_comparison_consumed_for_new_safety_question", "CRA-REV-20261101-11",
    "A stale field is identified as stale and not used as a fresh safety fact.",
    {"input_stale": detail.stale, "questions": [q.question for q in questions],
     "lab_evidence": len(evidence)},
    bool(questions) and bool(evidence),
)

node = RuleNode(
    node_key="R-REVIEW-012", summary="严重不良事件判断",
    source_refs=[RuleSourceRef(anchor_key="review-w09-1", quote="纯合成审查标题")],
)
matched = _rule_matches_dimension("R-REVIEW-012", "严重不良事件判断", node, "seriousness")
record(
    "chinese_safety_dimension_without_english_id_token", "CRA-REV-20261101-05",
    "A confirmed rule's safety dimension is explicit metadata independent of English ID spelling.",
    {"rule_title": node.summary, "seriousness_rule_recognized": matched}, not matched,
)
print(json.dumps({
    "schema_version": 1,
    "reviewed_source_commit": "df6f04b4c321f133f80dff07afa24c0974266927",
    "execution_commit": os.environ.get("GITHUB_SHA"),
    "scope": "W09 in-progress component boundary probes, no model inference or end-to-end clinical validation",
    "diagnostic_completed": True,
    "acceptance_passed": False,
    "meaning_of_successful_process": "diagnostics executed; reproduced findings remain OPEN",
    "observations": observations,
    "cases": len(observations),
    "findings_reproduced": sum(o["finding_reproduced"] for o in observations),
}, ensure_ascii=False, indent=2, default=str))
