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
    ProviderLine,
    ProviderTable,
)

SUPPORT_PROFILE_VERSION = "synthetic-lab-v2"
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
        {
            "kind": "clear_printed_jpeg_mild_rotation",
            "condition": (
                "synthetic clear print with 0.5-degree rotation; "
                "declared independent evaluation sample"
            ),
            "provider": "docling",
        },
        {
            "kind": "scanned_pdf_multipage",
            "condition": (
                "image-only two-page report with one headerless continuation "
                "table; declared independent evaluation sample"
            ),
            "provider": "docling",
        },
    ],
    "experimental_formats": [
        {
            "kind": "scanned_pdf_more_than_two_pages",
            "condition": "route exists; no independent multi-page set above two pages",
        },
        {
            "kind": "unruled_table",
            "condition": "structure recovery is not accepted without review",
        },
    ],
    "unsupported": [
        "handwriting",
        "severe blur or occlusion",
        "unruled arbitrary hospital layouts",
        "multi-column interleaved continuation without stable column order",
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
class ReportContext:
    values: dict[str, str]
    sources: dict[str, dict[str, Any]]
    ambiguities: tuple[str, ...] = ()


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
    report_context: ReportContext


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


def _continuation_columns(
    table: ProviderTable,
    previous_columns: dict[int, str] | None,
) -> dict[int, str] | None:
    """Reuse the previous header only for a structurally compatible table."""
    if not previous_columns:
        return None
    required = {"analyte", "value_raw"}
    if not required.issubset(previous_columns.values()):
        return None
    highest_index = max(previous_columns)
    if not table.rows or any(
        len(row.cells) <= highest_index for row in table.rows
    ):
        return None
    return previous_columns


def _context_pairs(
    table: ProviderTable,
) -> list[tuple[str, str, ProviderCell]]:
    pairs: list[tuple[str, str, ProviderCell]] = []
    context_fields = {
        "subject_external_id",
        "visit_key",
        "collected_on",
        "collected_time",
        "instance_type",
        "specimen",
        "report_on",
        "report_revision",
    }
    for row in table.rows:
        cells = [
            cell for cell in row.cells if normalized_text(cell.text)
        ]
        if len(cells) != 2:
            continue
        field = _field_for_header(cells[0].text)
        if field in context_fields:
            pairs.append((field, cells[1].text.strip(), cells[1]))
    return pairs


def _extract_report_context(
    lines: tuple[ProviderLine, ...],
    tables: tuple[ProviderTable, ...] = (),
) -> ReportContext:
    candidates: dict[str, list[tuple[str, ProviderLine]]] = {}
    context_fields = {
        "subject_external_id",
        "visit_key",
        "collected_on",
        "collected_time",
        "instance_type",
        "specimen",
        "report_on",
        "report_revision",
    }
    for line in lines:
        text = normalized_text(line.text)
        if not text:
            continue
        for field, aliases in _FIELD_ALIASES.items():
            if field not in context_fields:
                continue
            for alias in aliases:
                matches = re.finditer(
                    rf"(?:^|\s){re.escape(alias)}\s*[:：]\s*"
                    rf"(.+?)(?=\s+[^:：\s]+\s*[:：]|$)",
                    text,
                    re.IGNORECASE,
                )
                for match in matches:
                    candidates.setdefault(field, []).append(
                        (match.group(1).strip(), line)
                    )
    table_sources: dict[str, dict[str, Any]] = {}
    for table in tables:
        for field, value, cell in _context_pairs(table):
            line = ProviderLine(
                text=value,
                page=table.page,
                bbox=cell.bbox or table.bbox,
            )
            candidates.setdefault(field, []).append((value, line))
            table_sources[field] = {
                "text": value,
                "page": table.page,
                "bbox": _bbox(cell.bbox or table.bbox),
                "kind": "report_context_table",
                "table_index": table.index,
            }
    values: dict[str, str] = {}
    sources: dict[str, dict[str, Any]] = {}
    ambiguities: list[str] = []
    for field, items in candidates.items():
        distinct = {
            _normalized_header(value)
            for value, _ in items
            if _normalized_header(value)
        }
        if len(distinct) != 1:
            ambiguities.append(f"report_context_{field}_ambiguous")
            continue
        value, line = items[0]
        values[field] = normalized_text(value)
        sources[field] = table_sources.get(
            field,
            {
                "text": line.text,
                "page": line.page,
                "bbox": _bbox(line.bbox),
                "kind": "report_context",
            },
        )
    return ReportContext(values, sources, tuple(ambiguities))


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
    report_context: ReportContext,
    header_table: ProviderTable | None = None,
) -> LabRowDraft | None:
    values: dict[str, str | None] = {}
    source_cells: dict[str, dict[str, Any]] = {}
    for field_name in _FIELD_ALIASES:
        value, cell = _cell_value(row, columns, field_name)
        if not value and field_name in report_context.values:
            value = report_context.values[field_name]
            source_cells[field_name] = report_context.sources[field_name]
        values[field_name] = value
        if cell is not None:
            source_cells[field_name] = {
                "text": cell.text,
                "bbox": _bbox(cell.bbox),
            }
    if not values["analyte"] and not values["value_raw"]:
        return None
    if (
        values["analyte"]
        and values["value_raw"]
        and _normalized_header(values["analyte"])
        == _normalized_header(values["value_raw"])
    ):
        # Image models can append a footnote as a structured one-cell row that
        # is stretched across the grid. Repeating caption text in the analyte
        # and result columns is not a laboratory observation.
        return None
    issues: list[str] = []
    for context_field in {
        "subject_external_id",
        "collected_on",
        "collected_time",
        "instance_type",
        "report_on",
        "report_revision",
    }:
        if (
            values[context_field]
            and context_field in report_context.values
            and _normalized_header(values[context_field] or "")
            != _normalized_header(report_context.values[context_field])
        ):
            issues.append(f"report_context_{context_field}_conflict")
    if not values["subject_external_id"]:
        issues.append("subject_external_id_missing")
    if not values["analyte"]:
        issues.append("analyte_missing")
    if not values["value_raw"]:
        issues.append("result_missing")
    if not values["unit_raw"]:
        issues.append("unit_missing")
    elif not re.search(r"[A-Za-z%µμ\u4e00-\u9fff]", values["unit_raw"]):
        issues.append("unit_unrecognized_or_inconsistent")
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
        "header_table_index": (
            header_table.index if header_table is not None else table.index
        ),
        "header_page": (
            header_table.page if header_table is not None else table.page
        ),
        "header_inherited": (
            header_table is not None and header_table.index != table.index
        ),
        "row_index": row_index,
        "table_bbox": _bbox(table.bbox),
        "cells": source_cells,
        "anchor": f"page[{table.page}]/table[{table.index}]/row[{row_index}]",
        "report_context": report_context.values,
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
    report_context = _extract_report_context(result.lines, result.tables)
    rows: list[LabRowDraft] = []
    warnings = list(result.warnings)
    previous_table: ProviderTable | None = None
    previous_columns: dict[int, str] | None = None
    for table in result.tables:
        if _context_pairs(table):
            continue
        header = _header_mapping(table)
        if header is not None:
            header_index, columns = header
            header_table = table
            row_start = header_index + 1
        else:
            inherited = _continuation_columns(table, previous_columns)
            if inherited is None:
                warnings.append(
                    f"table {table.index} has no recognizable laboratory header"
                )
                previous_table = table
                previous_columns = None
                continue
            columns = inherited
            header_table = previous_table
            row_start = 0
            warnings.append(
                f"table {table.index} reused the compatible header from "
                f"table {previous_table.index if previous_table else 'unknown'}"
            )
        for row_index, row in enumerate(
            table.rows[row_start:], start=row_start
        ):
            draft = _row_from_table(
                table=table,
                columns=columns,
                row=row.cells,
                row_index=row_index,
                ordinal=len(rows) + 1,
                provider_name=result.provider_name,
                provider_version=result.provider_version,
                report_context=report_context,
                header_table=header_table,
            )
            if draft is not None:
                rows.append(draft)
        previous_table = table
        previous_columns = columns
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
        support_profile={
            **SUPPORT_PROFILE,
            "report_context": report_context.values,
            "report_context_ambiguities": list(report_context.ambiguities),
            "model_sha256": result.model_sha256,
            "dependency_lock_sha256": result.dependency_lock_sha256,
        },
        warnings=tuple(
            dict.fromkeys([*warnings, *report_context.ambiguities])
        ),
        rows=tuple(rows),
        state=state,
        report_context=report_context,
    )
