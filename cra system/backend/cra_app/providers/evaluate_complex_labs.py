"""Evaluate the W14 complex-format laboratory routes on synthetic samples."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, time as clock_time
from pathlib import Path
from typing import Any

from cra_app.laboratory.comparison import (
    EdcValue,
    ObservationValue,
    compare_observation,
)
from cra_app.laboratory.matching import normalize_instance
from cra_app.laboratory.recognition import extract_observations
from cra_app.providers.lab_ocr import RoutedLabProvider


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _value(draft) -> ObservationValue:
    return ObservationValue(
        id=str(draft.ordinal),
        subject_external_id=draft.subject_external_id,
        visit_key=draft.visit_key,
        analyte=draft.analyte_raw,
        specimen=draft.specimen,
        collected_on=draft.collected_on,
        collected_at=draft.collected_at,
        instance_type=draft.instance_type,
        report_on=draft.report_on,
        report_revision=draft.report_revision,
        value_raw=draft.value_raw,
        unit=draft.unit_raw,
        lower_limit=draft.lower_limit_raw,
        upper_limit=draft.upper_limit_raw,
        validation_state=draft.validation_state,
        extraction_state=draft.extraction_state,
        issues=draft.issues,
    )


def _edc_value(expected: dict[str, Any]) -> EdcValue:
    collected_on = date.fromisoformat(expected["collected_on"])
    collected_time = clock_time.fromisoformat(expected["collected_time"])
    return EdcValue(
        id=f"w14-edc-{expected['analyte']}",
        subject_external_id=expected["subject_external_id"],
        subject_id=f"w14-subject:{expected['subject_external_id']}",
        visit_key=expected["visit_key"],
        analyte=expected["analyte"],
        specimen=expected["specimen"],
        collected_on=collected_on,
        collected_at=datetime.combine(collected_on, collected_time),
        instance_type=normalize_instance(expected["instance_type"]),
        report_on=collected_on,
        report_revision=expected["report_revision"],
        value_raw=expected["value_raw"],
        unit=expected["unit_raw"],
        lower_limit=expected["lower_limit"],
        upper_limit=expected["upper_limit"],
        identity_status="mapped",
        validation_status="ready_for_match",
    )


def _actual_value(draft) -> dict[str, Any]:
    return {
        "subject_external_id": draft.subject_external_id,
        "visit_key": draft.visit_key,
        "analyte": draft.analyte_raw,
        "value_raw": draft.value_raw,
        "unit_raw": draft.unit_raw,
        "collected_on": (
            draft.collected_on.isoformat() if draft.collected_on else None
        ),
        "collected_time": (
            draft.collected_at.strftime("%H:%M")
            if draft.collected_at
            else None
        ),
        "instance_type": draft.instance_type,
        "specimen": draft.specimen,
        "lower_limit": draft.lower_limit_raw,
        "upper_limit": draft.upper_limit_raw,
        "report_revision": draft.report_revision,
    }


def _field_errors(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for field in (
        "subject_external_id",
        "visit_key",
        "analyte",
        "value_raw",
        "unit_raw",
        "collected_on",
        "collected_time",
        "specimen",
        "lower_limit",
        "upper_limit",
        "report_revision",
    ):
        expected_value = expected[field]
        actual_value = actual[field]
        if (
            field == "instance_type"
            or field == "analyte"
            or field == "specimen"
        ):
            equal = str(expected_value).casefold() == str(
                actual_value
            ).casefold()
        else:
            equal = expected_value == actual_value
        if not equal:
            errors.append(
                {
                    "field": field,
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )
    if normalize_instance(expected["instance_type"]) != actual["instance_type"]:
        errors.append(
            {
                "field": "instance_type",
                "expected": expected["instance_type"],
                "actual": actual["instance_type"],
            }
        )
    return errors


def _evaluate_artifact(
    root: Path,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    path = root / "tests/w14_fixtures" / artifact["file"]
    if "synthetic" not in path.name:
        raise ValueError("W14 evaluation input must be synthetic")
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != artifact["sha256"]:
        raise ValueError(f"artifact hash changed: {artifact['artifact_id']}")
    media_type = (
        "application/pdf"
        if artifact["format"] == "pdf"
        else "image/jpeg"
    )
    started = time.perf_counter()
    result = RoutedLabProvider(
        ocr_provider="docling", project_root=root
    ).recognize(
        content,
        filename=path.name,
        media_type=media_type,
    )
    draft = extract_observations(result)
    elapsed = time.perf_counter() - started
    actual_by_analyte = {
        str(row.analyte_raw).casefold(): row for row in draft.rows
    }
    expected_by_analyte = {
        row["analyte"].casefold(): row
        for row in artifact["expected_rows"]
    }
    missing = sorted(set(expected_by_analyte) - set(actual_by_analyte))
    extra = sorted(set(actual_by_analyte) - set(expected_by_analyte))
    field_errors: list[dict[str, Any]] = []
    issue_errors: list[dict[str, Any]] = []
    comparison_statuses: list[str] = []
    for analyte, expected in expected_by_analyte.items():
        draft_row = actual_by_analyte.get(analyte)
        if draft_row is None:
            continue
        actual = _actual_value(draft_row)
        for error in _field_errors(expected, actual):
            field_errors.append({"analyte": analyte, **error})
        expected_issues = artifact.get("expected_review_issues", {}).get(
            expected["analyte"], []
        )
        missing_issues = [
            issue for issue in expected_issues if issue not in draft_row.issues
        ]
        if missing_issues:
            issue_errors.append(
                {
                    "analyte": analyte,
                    "missing_issues": missing_issues,
                    "actual_issues": list(draft_row.issues),
                }
            )
        comparison_statuses.append(
            compare_observation(
                _value(draft_row), [_edc_value(expected)]
            ).result_status
        )
    ready_rows = sum(
        row.validation_state == "ready_for_match" for row in draft.rows
    )
    passed = (
        len(draft.rows) == artifact["expected_row_count"]
        and not missing
        and not extra
        and not field_errors
        and not issue_errors
        and draft.file_format
        == (
            "scanned_pdf"
            if artifact["format"] == "pdf"
            else "clear_printed_jpeg"
        )
    )
    return {
        "artifact_id": artifact["artifact_id"],
        "evaluation_group": artifact["evaluation_group"],
        "format_kind": artifact["format_kind"],
        "input_sha256": digest,
        "provider": result.provider_name,
        "provider_version": result.provider_version,
        "model_version": result.model_version,
        "model_sha256": result.model_sha256,
        "dependency_lock_sha256": result.dependency_lock_sha256,
        "pages": len({table.page for table in result.tables}),
        "tables": len(result.tables),
        "expected_rows": artifact["expected_row_count"],
        "recognized_rows": len(draft.rows),
        "missing_analytes": missing,
        "unexpected_analytes": extra,
        "field_errors": field_errors,
        "issue_errors": issue_errors,
        "coordinates_present": all(
            bool(row.source_ref.get("cells")) for row in draft.rows
        ),
        "automatic_usable_rows": ready_rows,
        "automatic_usable_ratio": round(
            ready_rows / len(draft.rows), 4
        )
        if draft.rows
        else None,
        "focused_review_rows": len(draft.rows) - ready_rows,
        "manual_correction_or_backfill": 0,
        "manual_correction_or_backfill_ratio": 0.0,
        "comparison_statuses": comparison_statuses,
        "elapsed_seconds": round(elapsed, 3),
        "provider_elapsed_seconds": result.elapsed_seconds,
        "provider_max_rss_bytes": result.max_rss_bytes,
        "warnings": list(draft.warnings),
        "status": "passed" if passed else "failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("tests/w14_fixtures/manifest.json"),
    )
    args = parser.parse_args()
    root = _project_root()
    dataset_path = args.dataset if args.dataset.is_absolute() else root / args.dataset
    manifest = json.loads(dataset_path.read_text(encoding="utf-8"))
    if manifest.get("source") != "pure_synthetic":
        raise ValueError("W14 evaluation accepts pure synthetic input only")
    artifacts = [
        _evaluate_artifact(root, artifact)
        for artifact in manifest["artifacts"]
    ]
    passed = all(item["status"] == "passed" for item in artifacts)
    payload = {
        "schema_version": 1,
        "source": "pure_synthetic",
        "provider_validation": passed,
        "clinical_validation": False,
        "manual_workflow_time_comparison": None,
        "artifacts": artifacts,
        "total_elapsed_seconds": round(
            sum(item["elapsed_seconds"] for item in artifacts), 3
        ),
        "limitations": [
            "Two synthetic samples do not represent hospital format distribution.",
            "Mild rotation and one continuation table do not cover blur or perspective distortion.",
            "Elapsed time is provider time, not CRA total review time.",
            "No real clinical data or clinical safety conclusion was evaluated.",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
