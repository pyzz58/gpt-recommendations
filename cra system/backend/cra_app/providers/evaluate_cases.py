"""Independent synthetic evaluation for deterministic safety reasoning + model use."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from cra_app.providers.case_analysis import (
    build_case_analysis_provider,
)
from cra_app.rules.contracts import FactValue, RuleNode
from cra_app.rules.evaluator import evaluate_node
from cra_app.safety.grounding import (
    validate_model_explanation,
)

ROOT = Path(__file__).resolve().parents[3]
SAFETY_FIXTURES = ROOT / "tests" / "fixtures" / "safety"
RULES_PATH = SAFETY_FIXTURES / "rules.json"
CASES_PATH = SAFETY_FIXTURES / "evaluation_cases.json"

RULE_DIMENSIONS = {
    "R-AE-COLLECTION-01": "ae_collection",
    "R-AE-GRADE-01": "grade",
    "R-AE-SERIOUSNESS-01": "seriousness",
    "R-AE-RELATEDNESS-01": "relatedness",
    "R-AE-EXPECTEDNESS-01": "expectedness",
    "R-AESI-01": "aesi",
    "R-DLT-01": "dlt",
    "R-PD-01": "protocol_deviation",
    "R-SAE-TIMELINESS-01": "reporting_timeliness",
}

QUESTIONS = {
    "ae_collection": (
        "Confirm the original event term, first occurrence and source record."
    ),
    "grade": (
        "Verify the investigator grade against the adopted toxicity criteria."
    ),
    "seriousness": (
        "Confirm whether any SAE seriousness criterion applies; grade alone "
        "cannot answer this question."
    ),
    "relatedness": (
        "Obtain the investigator's separate relatedness assessment and rationale."
    ),
    "expectedness": (
        "Confirm expectedness against the project-adopted reference safety "
        "information version."
    ),
    "aesi": "Confirm the applicable AESI list version and event term.",
    "dlt": "Confirm the DLT criteria and assessment window.",
    "protocol_deviation": (
        "Verify PD criteria, reporting and correction for the suspected deviation."
    ),
    "reporting_timeliness": (
        "Confirm the awareness time, entry time, actual report time and the "
        "project reporting rule; no deadline is inferred without them."
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dimension_results(
    rules: list[RuleNode],
    *,
    requested: list[str],
    facts: dict[str, FactValue],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_dimension: dict[str, list[RuleNode]] = {}
    for rule in rules:
        dimension = RULE_DIMENSIONS.get(rule.node_key)
        if dimension is not None:
            by_dimension.setdefault(dimension, []).append(rule)
    for dimension in requested:
        matched = by_dimension.get(dimension, [])
        if not matched:
            output.append(
                {
                    "dimension": dimension,
                    "status": "unknown",
                    "text": f"Applicable rule for {dimension} is missing.",
                    "evidence_ids": [],
                }
            )
            continue
        evaluations = [evaluate_node(rule, facts) for rule in matched]
        candidate_actions = [
            action
            for evaluation in evaluations
            for branch in evaluation.branches
            if branch.result == "true"
            for action in branch.actions
        ]
        if candidate_actions:
            status = "candidate"
            text = "; ".join(candidate_actions)
        elif any(
            evaluation.status in {"unknown", "analysis_required"}
            for evaluation in evaluations
        ):
            status = "unknown"
            text = "; ".join(
                reason
                for evaluation in evaluations
                for reason in evaluation.unknowns
            ) or "Required condition is unknown."
        else:
            status = "not_applicable"
            text = "Structured condition evaluated false for this event."
        output.append(
            {
                "dimension": dimension,
                "status": status,
                "text": text,
                "evidence_ids": [
                    f"RULE:{rule.node_key}" for rule in matched
                ],
            }
        )
    return output


def _questions(dimensions: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for item in dimensions:
        dimension = str(item["dimension"])
        if item["status"] in {"unknown", "analysis_required"}:
            result.append(QUESTIONS[dimension])
        elif item["status"] == "candidate":
            result.append(
                f"Review the server candidate for {dimension}; "
                + QUESTIONS[dimension]
                + " "
                + str(item["text"])
            )
    return result


def _explanation_codes(dimensions: list[dict[str, Any]]) -> list[str]:
    candidate = any(item["status"] == "candidate" for item in dimensions)
    unknown = any(
        item["status"] in {"unknown", "analysis_required"}
        for item in dimensions
    )
    if candidate and unknown:
        return ["candidate_and_unknown_review"]
    if candidate:
        return ["candidate_review"]
    if unknown:
        return ["unknown_clarification"]
    return ["general_review"]


def _rule_node(item: dict[str, Any]) -> RuleNode:
    source_ref = {
        "anchor_key": item["anchor_key"],
        "quote": item["quote"],
        "locator": item["anchor_key"],
    }
    return RuleNode.model_validate(
        {
            "node_key": item["rule_key"],
            "summary": item["summary"],
            "trigger": item["trigger"],
            "branches": [
                {
                    **branch,
                    "label": f"Branch {branch['branch_key']}",
                    "target_node_ids": [
                        f"{item['rule_key']}-{branch['branch_key']}"
                    ],
                    "source_refs": [source_ref],
                }
                for branch in item.get("branches", [])
            ],
            "required_facts": item.get("required_facts", []),
            "source_refs": [source_ref],
        }
    )


def _evidence(
    rules_by_key: dict[str, dict[str, Any]],
    dimensions: list[dict[str, Any]],
    facts: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for key, value in facts.items():
        evidence.append(
            {
                "evidence_id": f"FACT:{key}",
                "text": f"{key}={json.dumps(value, ensure_ascii=False)}",
                "kind": "fact",
            }
        )
    included = {
        evidence_id.removeprefix("RULE:")
        for item in dimensions
        for evidence_id in item["evidence_ids"]
    }
    for rule_key in sorted(included):
        rule = rules_by_key[rule_key]
        evidence.append(
            {
                "evidence_id": f"RULE:{rule_key}",
                "text": rule["quote"],
                "kind": "rule",
            }
        )
    return evidence


def _boundary_checks(evidence_ids: set[str]) -> dict[str, bool]:
    first_evidence = sorted(evidence_ids)[0]
    fake = validate_model_explanation(
        json.dumps(
            {
                "explanation_code": "candidate_review",
                "evidence_ids": ["RULE:DOES-NOT-EXIST"],
            }
        ),
        allowed_evidence_ids=evidence_ids,
        allowed_explanation_codes={"candidate_review"},
    )
    conclusion = validate_model_explanation(
        json.dumps(
            {
                "explanation": (
                    "Classified as serious after 2026-10-01 and clinical safe."
                ),
                "evidence_ids": [first_evidence],
            }
        ),
        allowed_evidence_ids=evidence_ids,
        allowed_explanation_codes={"candidate_review"},
    )
    return {
        "fabricated_reference_rejected": not fake.accepted,
        "medical_conclusion_rejected": not conclusion.accepted,
        "unsupported_number_or_date_rejected": any(
            "unsupported_numeric_token" in error
            for error in conclusion.errors
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--provider", default="local-qwen2.5-0.5b"
    )
    args = parser.parse_args()

    manifest = json.loads(args.dataset.read_text(encoding="utf-8"))
    if manifest.get("source") != "pure_synthetic":
        raise ValueError("W09 evaluation accepts only pure synthetic input")
    artifacts = {item["artifact_id"]: item for item in manifest["artifacts"]}
    for artifact_id, path, expected_hash in (
        ("SAFETY-RULES-DEV", RULES_PATH, None),
        ("SAFETY-CASES-EVAL", CASES_PATH, None),
    ):
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"manifest is missing {artifact_id}")
        if artifact.get("group") not in {"development", "evaluation"}:
            raise ValueError(f"{artifact_id} has no evaluation group")
        if expected_hash is not None and artifact.get("sha256") != expected_hash:
            raise ValueError(f"{artifact_id} hash mismatch")
        if _sha256(path) != artifact.get("sha256"):
            raise ValueError(f"{artifact_id} content changed after manifest")

    rules_payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    cases_payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if (
        rules_payload.get("source") != "pure_synthetic"
        or cases_payload.get("source") != "pure_synthetic"
        or cases_payload.get("evaluation_group") != "independent_synthetic"
    ):
        raise ValueError("W09 fixtures must be pure synthetic independent data")
    rules = [_rule_node(item) for item in rules_payload["rules"]]
    rules_by_key = {
        item["rule_key"]: item for item in rules_payload["rules"]
    }

    prepared: list[dict[str, Any]] = []
    expected_by_case: dict[str, dict[str, Any]] = {}
    allowed_ids: set[str] = set()
    for case in cases_payload["cases"]:
        facts = {
            key: FactValue(value=value)
            for key, value in case["facts"].items()
        }
        dimensions = _dimension_results(
            rules,
            requested=case["requested_dimensions"],
            facts=facts,
        )
        evidence = _evidence(
            rules_by_key, dimensions, case["facts"]
        )
        allowed_ids.update(item["evidence_id"] for item in evidence)
        prepared.append(
            {
                "case_id": case["case_id"],
                "source": "pure_synthetic",
                "facts": [
                    {
                        "evidence_id": f"FACT:{key}",
                        "fact_key": key,
                        "value": value,
                    }
                    for key, value in case["facts"].items()
                ],
                "dimensions": dimensions,
                "evidence": evidence,
                "allowed_explanation_codes": _explanation_codes(dimensions),
            }
        )
        expected_by_case[case["case_id"]] = case["expected"]

    started = time.perf_counter()
    provider = build_case_analysis_provider(args.provider, project_root=ROOT)
    results = provider.analyze_batch(prepared)
    elapsed = time.perf_counter() - started
    details: list[dict[str, Any]] = []
    for request, model_result in zip(prepared, results, strict=True):
        case_id = request["case_id"]
        expected = expected_by_case[case_id]
        dimensions = request["dimensions"]
        actual_candidates = {
            item["dimension"]
            for item in dimensions
            if item["status"] == "candidate"
        }
        actual_unknowns = {
            item["dimension"]
            for item in dimensions
            if item["status"] in {"unknown", "analysis_required"}
        }
        questions = _questions(dimensions)
        question_text = " ".join(questions).casefold()
        grounded = (
            validate_model_explanation(
                model_result.raw_output or "",
                allowed_evidence_ids={
                    item["evidence_id"] for item in request["evidence"]
                },
                allowed_explanation_codes=set(
                    request["allowed_explanation_codes"]
                ),
            )
            if model_result.status == "completed"
            else None
        )
        details.append(
            {
                "case_id": case_id,
                "dimensions": dimensions,
                "questions": questions,
                "candidate_dimension_match": actual_candidates
                == set(expected["candidate_dimensions"]),
                "unknown_dimension_match": actual_unknowns
                == set(expected["unknown_dimensions"]),
                "required_question_topics_match": all(
                    topic.casefold() in question_text
                    for topic in expected["required_question_topics"]
                ),
                "forbidden_assertions_absent": all(
                    assertion.casefold()
                    not in json.dumps(
                        {"dimensions": dimensions, "questions": questions},
                        ensure_ascii=False,
                    ).casefold()
                    for assertion in expected["must_not_assert"]
                ),
                "provider_status": model_result.status,
                "provider_grounding_accepted": bool(
                    grounded and grounded.accepted
                ),
                "provider_errors": list(grounded.errors)
                if grounded
                else [model_result.error or "provider unavailable"],
                "provider_raw_output": model_result.raw_output,
                "provider_elapsed_seconds": model_result.elapsed_seconds,
                "provider_max_rss_bytes": model_result.max_rss_bytes,
            }
        )

    boundary = _boundary_checks(allowed_ids)
    condition_control = not any(
        item["status"] == "candidate"
        for case in prepared
        if case["case_id"] == "SAFE-EVAL-001"
        for item in case["dimensions"]
        if item["dimension"] == "seriousness"
    )
    case_fields = (
        "candidate_dimension_match",
        "unknown_dimension_match",
        "required_question_topics_match",
        "forbidden_assertions_absent",
        "provider_grounding_accepted",
    )
    all_cases_pass = all(
        all(item[field] for field in case_fields) for item in details
    )
    provider_validation = bool(
        all_cases_pass
        and all(boundary.values())
        and condition_control
        and all(
            item["provider_status"] == "completed" for item in details
        )
    )
    output = {
        "schema_version": 1,
        "source": "pure_synthetic",
        "provider": provider.name,
        "provider_validation": provider_validation,
        "clinical_validation": False,
        "manual_workflow_time_comparison": None,
        "sample_count": len(details),
        "elapsed_seconds": round(elapsed, 3),
        "max_rss_bytes": max(
            (
                item["provider_max_rss_bytes"] or 0
                for item in details
            ),
            default=0,
        ),
        "dimension_matches": sum(
            item["candidate_dimension_match"]
            and item["unknown_dimension_match"]
            for item in details
        ),
        "question_topic_matches": sum(
            item["required_question_topics_match"] for item in details
        ),
        "grounded_outputs": sum(
            item["provider_grounding_accepted"] for item in details
        ),
        "boundary_checks": {
            **boundary,
            "grade_cannot_create_seriousness_candidate": condition_control,
        },
        "cases": details,
        "limitations": [
            "Three independent synthetic cases only.",
            "The local model selects grounded explanation templates; it does not decide dimensions.",
            "No clinical accuracy, real-data performance, or workflow time saving is established.",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if provider_validation else 1


if __name__ == "__main__":
    raise SystemExit(main())
