from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


class TableImportError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParsedTable:
    columns: list[str]
    rows: list[dict[str, Any]]
    quality_findings: list[dict[str, Any]]
    sheet_name: str | None


def parse_table(
    content: bytes,
    *,
    filename: str,
    media_type: str,
    sheet_name: str | None = None,
    max_rows: int = 10_000,
) -> ParsedTable:
    lowered = filename.lower()
    if lowered.endswith(".csv") or media_type in {"text/csv", "application/csv"}:
        return _parse_csv(content, max_rows=max_rows)
    if lowered.endswith(".xlsx") or "spreadsheetml" in media_type:
        return _parse_xlsx(
            content,
            sheet_name=sheet_name,
            max_rows=max_rows,
        )
    raise TableImportError(
        "UNSUPPORTED_TABLE_FORMAT",
        "Dataset import supports CSV and XLSX only",
    )


def _parse_csv(content: bytes, *, max_rows: int) -> ParsedTable:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TableImportError(
            "CSV_ENCODING_UNSUPPORTED",
            "CSV must be UTF-8 encoded",
        ) from exc
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise TableImportError("EMPTY_TABLE", "Dataset is empty") from exc
    columns = _validate_headers(headers)
    rows: list[dict[str, Any]] = []
    for raw_row in reader:
        if not any(value.strip() for value in raw_row):
            continue
        if len(raw_row) > len(columns):
            raise TableImportError(
                "ROW_WIDTH_MISMATCH",
                "CSV row contains more values than headers",
            )
        padded = raw_row + [""] * (len(columns) - len(raw_row))
        rows.append(
            {
                column: (value if value != "" else None)
                for column, value in zip(columns, padded, strict=True)
            }
        )
        if len(rows) > max_rows:
            raise TableImportError(
                "DATASET_TOO_LARGE",
                f"Dataset exceeds {max_rows} rows",
            )
    if not rows:
        raise TableImportError("EMPTY_TABLE", "Dataset has headers but no data rows")
    return ParsedTable(
        columns=columns,
        rows=rows,
        quality_findings=_missing_findings(columns, rows),
        sheet_name=None,
    )


def _parse_xlsx(
    content: bytes,
    *,
    sheet_name: str | None,
    max_rows: int,
) -> ParsedTable:
    try:
        workbook = load_workbook(
            io.BytesIO(content),
            read_only=True,
            data_only=False,
        )
    except (InvalidFileException, OSError, ValueError) as exc:
        raise TableImportError("XLSX_INVALID", "XLSX file cannot be opened") from exc
    try:
        if sheet_name is None:
            worksheet = workbook.active
        elif sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
        else:
            raise TableImportError("SHEET_NOT_FOUND", "Worksheet was not found")
        if worksheet is None or not hasattr(worksheet, "iter_rows"):
            raise TableImportError("WORKSHEET_INVALID", "Selected sheet is not a worksheet")
        row_iterator = worksheet.iter_rows(values_only=True)
        try:
            raw_headers = next(row_iterator)
        except StopIteration as exc:
            raise TableImportError("EMPTY_TABLE", "Worksheet is empty") from exc
        headers = ["" if value is None else str(value) for value in raw_headers]
        columns = _validate_headers(headers)
        rows: list[dict[str, Any]] = []
        for raw_row in row_iterator:
            if raw_row is None or not any(value is not None for value in raw_row):
                continue
            values = list(raw_row[: len(columns)])
            values.extend([None] * (len(columns) - len(values)))
            row: dict[str, Any] = {}
            for column, value in zip(columns, values, strict=True):
                if isinstance(value, str) and value.startswith("="):
                    raise TableImportError(
                        "FORMULA_NOT_EVALUATED",
                        f"Formula in column {column} has no independently evaluated value",
                    )
                row[column] = _json_cell(value)
            rows.append(row)
            if len(rows) > max_rows:
                raise TableImportError(
                    "DATASET_TOO_LARGE",
                    f"Dataset exceeds {max_rows} rows",
                )
        if not rows:
            raise TableImportError("EMPTY_TABLE", "Worksheet has no data rows")
        return ParsedTable(
            columns=columns,
            rows=rows,
            quality_findings=_missing_findings(columns, rows),
            sheet_name=worksheet.title,
        )
    finally:
        workbook.close()


def _validate_headers(raw_headers: list[Any]) -> list[str]:
    columns = [str(value).strip() if value is not None else "" for value in raw_headers]
    while columns and not columns[-1]:
        columns.pop()
    if not columns or all(not column for column in columns):
        raise TableImportError("EMPTY_HEADERS", "Dataset has no column headers")
    if any(not column for column in columns):
        raise TableImportError("EMPTY_HEADERS", "Dataset contains a blank header")
    if len(columns) != len(set(columns)):
        raise TableImportError("DUPLICATE_HEADERS", "Dataset headers must be unique")
    return columns


def _missing_findings(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for column in columns:
        missing = sum(row.get(column) is None for row in rows)
        if missing:
            findings.append(
                {
                    "code": "MISSING_VALUES",
                    "column": column,
                    "count": missing,
                    "scope": "raw_import",
                }
            )
    return findings


def _json_cell(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
