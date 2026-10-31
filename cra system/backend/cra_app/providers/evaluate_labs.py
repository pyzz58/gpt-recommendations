"""Evaluate actual laboratory recognition, matching and comparison on synthetics."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import date, datetime, time as clock_time
from pathlib import Path
from typing import Any

from cra_app.edc_import.excel import parse_workbook
from cra_app.laboratory.comparison import (
    EdcValue,
    ObservationValue,
    compare_observation,
)
from cra_app.laboratory.matching import normalize_instance, normalize_unit
from cra_app.laboratory.recognition import extract_observations
from cra_app.providers.lab_ocr import (
    LabProviderUnavailable,
    RoutedLabProvider,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _records_from_edc(path: Path) -> list[EdcValue]:
    parsed = parse_workbook(
        path.read_bytes(),
        filename=path.name,
        included_sheets=["Hematology", "Chemistry"],
    )
    records: list[EdcValue] = []
    for sheet in parsed.sheets:
        mapping = parsed.suggested_mapping.sheets.get(sheet.name)
        if mapping is None or not mapping.included:
            continue
        by_row: dict[int, dict[str, str | None]] = defaultdict(dict)
        for cell in sheet.cells:
            for field_name, header in mapping.columns.items():
                if header == sheet.headers[cell.column - 1]:
                    by_row[cell.row][field_name] = (
                        cell.cached_text if cell.formula else cell.raw_text
                    )
        for row_number, values in sorted(by_row.items()):
            if row_number <= mapping.header_row:
                continue
            subject = values.get("subject_external_id")
            analyte = values.get("analyte")
            if not subject or not analyte:
                continue
            collected_on = None
            collected_at = None
            if values.get("collected_at"):
                try:
                    parsed_time = clock_time.fromisoformat(
                        str(values["collected_at"])
                    )
                except ValueError:
                    parsed_time = None
                raw_date = values.get("collected_on")
                if raw_date:
                    try:
                        collected_on = datetime.fromisoformat(
                            str(raw_date)
                        ).date()
                    except ValueError:
                        collected_on = None
                if collected_on and parsed_time:
                    collected_at = datetime.combine(
                        collected_on, parsed_time
                    )
            report_revision = values.get("report_revision")
            records.append(
                EdcValue(
                    id=f"{sheet.name}:{row_number}",
                    subject_external_id=subject,
                    subject_id=f"synthetic-subject:{subject}",
                    visit_key=values.get("visit_key"),
                    analyte=analyte,
                    specimen=values.get("specimen"),
                    collected_on=collected_on,
                    collected_at=collected_at,
                    instance_type=normalize_instance(
                        values.get("instance_type")
                    ),
                    report_on=None,
                    report_revision=report_revision,
                    value_raw=values.get("value_raw"),
                    unit=values.get("unit"),
                    lower_limit=values.get("lower_limit"),
                    upper_limit=values.get("upper_limit"),
                    identity_status="mapped",
                    validation_status=(
                        "ready_for_match"
                        if values.get("value_raw") is not None
                        else "needs_review"
                    ),
                    issues=(
                        ()
                        if values.get("value_raw") is not None
                        else ("formula_cache_missing",)
                    ),
                )
            )
    return records


def _observation_value(draft) -> ObservationValue:
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


def _expected_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["subject_external_id"]),
        str(row["analyte"]).casefold(),
        str(row["collected_on"]),
        str(row["instance_type"]).casefold(),
    )


def _draft_key(draft) -> tuple[str, str, str, str]:
    return (
        str(draft.subject_external_id),
        str(draft.analyte_raw).casefold(),
        draft.collected_on.isoformat() if draft.collected_on else "",
        str(draft.instance_type),
    )


def _evaluate_artifact(
    root: Path,
    artifact: dict[str, Any],
    expected_rows: list[dict[str, Any]],
    edc_records: list[EdcValue],
) -> dict[str, Any]:
    path = root / "tests/fixtures" / artifact["file"]
    if "synthetic" not in path.name and "synthetic" not in str(path):
        raise ValueError("laboratory evaluation input is not marked synthetic")
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != artifact["sha256"]:
        raise ValueError(f"artifact hash changed: {artifact['artifact_id']}")
    started = time.perf_counter()
    provider = RoutedLabProvider(
        ocr_provider=(
            "docling"
            if artifact.get("format_kind") == "clear_printed_image"
            else "disabled"
        ),
        project_root=root,
    )
    result = provider.recognize(
        content,
        filename=path.name,
        media_type=(
            "application/pdf"
            if artifact["format"] == "pdf"
            else "image/png"
        ),
    )
    draft = extract_observations(result)
    outcomes = [
        compare_observation(_observation_value(row), edc_records)
        for row in draft.rows
    ]
    elapsed = time.perf_counter() - started
    found = {_draft_key(row): row for row in draft.rows}
    key_checks = []
    key_errors = []
    for expected in expected_rows:
        key = _expected_key(expected)
        actual = found.get(key)
        if actual is None:
            key_errors.append(
                {
                    "key": list(key),
                    "error": "row_not_recovered",
                }
            )
            continue
        checks = {
            "subject": actual.subject_external_id == expected["subject_external_id"],
            "visit": actual.visit_key == expected["visit_key"],
            "analyte": actual.analyte_raw == expected["analyte"],
            "value": actual.value_raw == expected["value_raw"],
            "unit": actual.unit_raw == expected["unit_raw"],
            "date": (
                actual.collected_on
                == date.fromisoformat(expected["collected_on"])
            ),
            "time": (
                actual.collected_at.strftime("%H:%M")
                if actual.collected_at
                else None
            )
            == expected["collected_time"],
            "instance": actual.instance_type == expected["instance_type"],
            "coordinates": bool(actual.source_ref.get("cells")),
        }
        key_checks.append(checks)
        for label, passed in checks.items():
            if not passed:
                key_errors.append(
                    {
                        "key": list(key),
                        "field": label,
                        "expected": expected.get(label),
                        "actual": {
                            "subject": actual.subject_external_id,
                            "visit": actual.visit_key,
                            "analyte": actual.analyte_raw,
                            "value": actual.value_raw,
                            "unit": actual.unit_raw,
                            "date": actual.collected_on.isoformat()
                            if actual.collected_on
                            else None,
                            "time": actual.collected_at.strftime("%H:%M")
                            if actual.collected_at
                            else None,
                            "instance": actual.instance_type,
                        }.get(label),
                    }
                )
    statuses = [outcome.result_status for outcome in outcomes]
    review_required = sum(status != "agreement" for status in statuses)
    manually_corrected_or_backfilled = sum(
        row.validation_state != "ready_for_match" for row in draft.rows
    )
    return {
        "artifact_id": artifact["artifact_id"],
        "group": artifact["group"],
        "format_kind": artifact["format_kind"],
        "provider": result.provider_name,
        "provider_version": result.provider_version,
        "input_sha256": digest,
        "expected_rows": len(expected_rows),
        "recognized_rows": len(draft.rows),
        "coordinates_present": all(
            bool(row.source_ref.get("cells")) for row in draft.rows
        ),
        "key_field_errors": key_errors,
        "comparison_statuses": statuses,
        "automatic_agreements": statuses.count("agreement"),
        "review_required": review_required,
        "automatic_usable_ratio": (
            round(
                sum(
                    row.validation_state == "ready_for_match"
                    for row in draft.rows
                )
                / len(draft.rows),
                4,
            )
            if draft.rows
            else None
        ),
        "manual_correction_or_backfill_count": manually_corrected_or_backfilled,
        "manual_correction_or_backfill_ratio": (
            round(manually_corrected_or_backfilled / len(draft.rows), 4)
            if draft.rows
            else None
        ),
        "manual_review_ratio": (
            round(review_required / len(statuses), 4) if statuses else None
        ),
        "elapsed_seconds": round(elapsed, 3),
        "provider_elapsed_seconds": result.elapsed_seconds,
        "provider_max_rss_bytes": result.max_rss_bytes,
        "warnings": list(draft.warnings),
        "status": (
            "passed"
            if (
                len(draft.rows) == len(expected_rows)
                and not key_errors
                and all(
                    row["coordinates"]
                    for row in key_checks
                )
            )
            else "failed"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    root = _project_root()
    dataset_path = (
        args.dataset if args.dataset.is_absolute() else root / args.dataset
    )
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    artifacts = [
        item for item in dataset["artifacts"] if item.get("purpose") == "laboratory"
    ]
    if not artifacts:
        raise ValueError("dataset has no laboratory artifacts")
    evaluation = json.loads(
        (dataset_path.parent / "labs/evaluation_cases.json").read_text(
            encoding="utf-8"
        )
    )
    edc_records = _records_from_edc(
        dataset_path.parent / evaluation["edc_artifact"]
    )
    results = [
        _evaluate_artifact(
            root,
            artifact,
            evaluation["rows"],
            edc_records,
        )
        for artifact in artifacts
    ]
    passed = all(result["status"] == "passed" for result in results)
    payload = {
        "schema_version": 1,
        "source": "pure_synthetic",
        "provider_validation": passed,
        "clinical_validation": False,
        "manual_workflow_time_comparison": None,
        "artifacts": results,
        "total_elapsed_seconds": round(
            sum(result["elapsed_seconds"] for result in results), 3
        ),
        "limitations": [
            "Only the committed clear-print synthetic fixtures were evaluated.",
            "Elapsed time measures recognition and comparison, not a CRA's full workflow.",
            "Image recognition requires the isolated Docling environment.",
            "No real clinical data, handwriting, blur or arbitrary hospital layout was used.",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
