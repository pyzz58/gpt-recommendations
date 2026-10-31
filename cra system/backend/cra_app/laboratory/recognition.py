"""Convert provider table coordinates into validated laboratory observations."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from cra_app.laboratory.comparison import parse_value
from cra_app.laboratory.matching import (
    normalize_analyte,
    normalize_instance,
    normalize_unit,
    normalized_text,
)
from cra_app.providers.lab_ocr import (
    LabRecognitionResult,
    ProviderCell,
    ProviderTable,
)

SUPPORT_PROFILE_VERSION = "synthetic-lab-v1"
SUPPORT_PROFILE: dict[str, Any] = {
    "version": SUPPORT_PROFILE_VERSION,
    "validated_formats": [
        {
            "kind": "text_pdf",
            "condition": "selectable text and ruled table",
            "provider": "pdfplumber-lab-table",
        },
        {
            "kind": "clear_printed_image_png",
            "condition": "synthetic clear print, no rotation or blur",
            "provider": "docling",
        },
    ],
    "experimental_formats": [
        {
            "kind": "image_jpeg",
            "condition": "same clean-print route as PNG; format coverage not separately evaluated",
        },
        {
            "kind": "scanned_pdf",
            "condition": "Docling fallback only; not part of the T-above evaluation set",
        },
    ],
    "unsupported": [
        "handwriting",
        "severe blur or occlusion",
        "unruled arbitrary hospital layouts",
        "non-laboratory clinical documents",
    ],
    "clinical_use_validated": False,
    "evaluation_group": "pure_synthetic",
}

_FIELD_ALIASES = {
    "subject_external_id": {
        "subject id",
        "patient id",
        "subject",
        "患者编号",
        "受试者编号",
    },
    "visit_key": {"visit", "visit name", "visit number", "访视", "访视编号"},
    "analyte": {
        "analyte",
        "test",
        "test name",
        "lab test",
        "检验项目",
        "项目",
    },
    "value_raw": {
        "result",
        "value",
        "lab result",
        "结果",
        "检验结果",
    },
    "unit_raw": {"unit", "units", "单位"},
    "collected_on": {
        "collection date",
        "collected date",
        "sample date",
        "采样日期",
        "采集日期",
    },
    "collected_time": {
        "collection time",
        "collected time",
        "sample time",
        "采样时间",
        "采集时间",
    },
    "instance_type": {
        "instance",
        "initial repeat",
        "initial/repeat",
        "初检复查",
        "初检/复查",
    },
    "specimen": {
        "specimen",
        "specimen type",
        "sample type",
        "样本类型",
        "标本类型",
    },
    "report_on": {"report date", "报告日期"},
    "report_revision": {
        "report revision",
        "report version",
        "amend revision",
        "报告修订",
        "报告版本",
    },
    "lower_limit": {
        "lln",
        "lower limit",
        "reference low",
        "参考下限",
        "下限",
    },
    "upper_limit": {
        "uln",
        "upper limit",
        "reference high",
        "参考上限",
        "上限",
    },
}


def _normalized_header(value: str) -> str:
    return re.sub(r"[\s_/\-]+", " ", value.strip().casefold())


def _parse_date(value: str | None) -> date | None:
    cleaned = normalized_text(value)
    if cleaned is None:
        return None
    for parser in (
        lambda item: date.fromisoformat(item),
        lambda item: datetime.strptime(item, "%d/%m/%Y").date(),
        lambda item: datetime.strptime(item, "%d-%b-%Y").date(),
    ):
        try:
            return parser(cleaned)
        except ValueError:
            continue
    return None


def _parse_time(value: str | None) -> time | None:
    cleaned = normalized_text(value)
    if cleaned is None:
        return None
    for candidate in (cleaned, cleaned.upper()):
        try:
            return time.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _bbox(value: tuple[float, float, float, float] | None) -> list[float] | None:
    return list(value) if value is not None else None


@dataclass(frozen=True)
class LabRowDraft:
    ordinal: int
    subject_external_id: str | None
    visit_key: str | None
    analyte_raw: str | None
    analyte_normalized: str | None
    specimen: str | None
    collected_on: date | None
    collected_at: datetime | None
    precision: str
    timezone_status: str
    instance_type_raw: str | None
    instance_type: str
    repeat_instance: str | None
    report_on: date | None
    report_revision: str | None
    value_raw: str | None
    value_type: str
    operator: str | None
    numeric_value: Decimal | None
    unit_raw: str | None
    unit_normalized: str | None
    lower_limit_raw: str | None
    upper_limit_raw: str | None
    extraction_state: str
    validation_state: str
    issues: tuple[str, ...]
    source_ref: dict[str, Any]
    provider_confidence: Decimal | None = None


@dataclass(frozen=True)
class RecognitionDraft:
    provider_name: str
    provider_version: str
    model_version: str | None
    file_format: str
    support_profile: dict[str, Any]
    warnings: tuple[str, ...]
    rows: tuple[LabRowDraft, ...]
    state: str


def _field_for_header(value: str) -> str | None:
    normalized = _normalized_header(value)
    for field_name, aliases in _FIELD_ALIASES.items():
        if normalized in aliases:
            return field_name
    return None


def _header_mapping(table: ProviderTable) -> tuple[int, dict[int, str]] | None:
    for row_index, row in enumerate(table.rows):
        mapping = {
            cell_index: field_name
            for cell_index, cell in enumerate(row.cells)
            if (field_name := _field_for_header(cell.text)) is not None
        }
        if "analyte" in mapping.values() and "value_raw" in mapping.values():
            return row_index, mapping
    return None


def _cell_value(
    row: tuple[ProviderCell, ...],
    columns: dict[int, str],
    field_name: str,
) -> tuple[str | None, ProviderCell | None]:
    for index, name in columns.items():
        if name != field_name or index >= len(row):
            continue
        value = normalized_text(row[index].text)
        return value, row[index]
    return None, None


def _row_from_table(
    *,
    table: ProviderTable,
    columns: dict[int, str],
    row: tuple[ProviderCell, ...],
    row_index: int,
    ordinal: int,
    provider_name: str,
    provider_version: str,
) -> LabRowDraft | None:
    values: dict[str, str | None] = {}
    source_cells: dict[str, dict[str, Any]] = {}
    for field_name in _FIELD_ALIASES:
        value, cell = _cell_value(row, columns, field_name)
        values[field_name] = value
        if cell is not None:
            source_cells[field_name] = {
                "text": cell.text,
                "bbox": _bbox(cell.bbox),
            }
    if not values["analyte"] and not values["value_raw"]:
        return None
    issues: list[str] = []
    if not values["subject_external_id"]:
        issues.append("subject_external_id_missing")
    if not values["analyte"]:
        issues.append("analyte_missing")
    if not values["value_raw"]:
        issues.append("result_missing")
    if not values["unit_raw"]:
        issues.append("unit_missing")
    collected_on = _parse_date(values["collected_on"])
    if collected_on is None:
        issues.append("collection_date_missing_or_invalid")
    collected_time = _parse_time(values["collected_time"])
    collected_at = (
        datetime.combine(collected_on, collected_time)
        if collected_on and collected_time
        else None
    )
    if values["collected_time"] and collected_time is None:
        issues.append("collection_time_invalid")
    instance_raw = values["instance_type"]
    instance = normalize_instance(instance_raw) or "unknown"
    if instance == "unknown":
        issues.append("initial_repeat_instance_missing")
    parsed = parse_value(values["value_raw"])
    if parsed.value_type == "text":
        issues.append("numeric_value_requires_interpretation")
    if parsed.value_type == "unknown":
        issues.append("result_unreadable")
    validation_state = "needs_review" if issues else "ready_for_match"
    source_ref = {
        "provider": provider_name,
        "provider_version": provider_version,
        "page": table.page,
        "table_index": table.index,
        "row_index": row_index,
        "table_bbox": _bbox(table.bbox),
        "cells": source_cells,
        "anchor": f"page[{table.page}]/table[{table.index}]/row[{row_index}]",
    }
    return LabRowDraft(
        ordinal=ordinal,
        subject_external_id=values["subject_external_id"],
        visit_key=values["visit_key"],
        analyte_raw=values["analyte"],
        analyte_normalized=normalize_analyte(values["analyte"]),
        specimen=values["specimen"],
        collected_on=collected_on,
        collected_at=collected_at,
        precision=(
            "minute"
            if collected_at and not collected_at.second
            else "second"
            if collected_at
            else "date"
            if collected_on
            else "unknown"
        ),
        timezone_status="unknown" if collected_time else "date_only",
        instance_type_raw=instance_raw,
        instance_type=instance,
        repeat_instance=instance_raw,
        report_on=_parse_date(values["report_on"]),
        report_revision=values["report_revision"],
        value_raw=values["value_raw"],
        value_type=parsed.value_type,
        operator=parsed.operator,
        numeric_value=parsed.number,
        unit_raw=values["unit_raw"],
        unit_normalized=normalize_unit(values["unit_raw"]),
        lower_limit_raw=values["lower_limit"],
        upper_limit_raw=values["upper_limit"],
        extraction_state=(
            "auto_extracted"
            if validation_state == "ready_for_match"
            else "needs_review"
        ),
        validation_state=validation_state,
        issues=tuple(issues),
        source_ref=source_ref,
    )


def extract_observations(
    result: LabRecognitionResult,
) -> RecognitionDraft:
    rows: list[LabRowDraft] = []
    warnings = list(result.warnings)
    for table in result.tables:
        header = _header_mapping(table)
        if header is None:
            warnings.append(
                f"table {table.index} has no recognizable laboratory header"
            )
            continue
        header_index, columns = header
        for row_index, row in enumerate(
            table.rows[header_index + 1 :], start=header_index + 1
        ):
            draft = _row_from_table(
                table=table,
                columns=columns,
                row=row.cells,
                row_index=row_index,
                ordinal=len(rows) + 1,
                provider_name=result.provider_name,
                provider_version=result.provider_version,
            )
            if draft is not None:
                rows.append(draft)
    if result.tables and not rows:
        warnings.append("structured table was present but no data rows validated")
    if not result.tables:
        warnings.append("no routed table structure was returned")
    if rows and all(row.validation_state == "ready_for_match" for row in rows):
        state = "recognized"
    elif rows:
        state = "partial"
    else:
        state = "failed"
    return RecognitionDraft(
        provider_name=result.provider_name,
        provider_version=result.provider_version,
        model_version=result.model_version,
        file_format=result.file_format,
        support_profile=SUPPORT_PROFILE,
        warnings=tuple(dict.fromkeys(warnings)),
        rows=tuple(rows),
        state=state,
    )
