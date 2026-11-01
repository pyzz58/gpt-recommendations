"""Existing-template Excel track rendering and inspection."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from cra_app.reports.template_mapping import (
    XlsxTemplateMapping,
    render_xlsx as _render_xlsx,
)


def render_xlsx(
    template_bytes: bytes,
    mapping: XlsxTemplateMapping,
    context: dict[str, Any],
) -> tuple[bytes, list[str], list[dict[str, Any]]]:
    return _render_xlsx(template_bytes, mapping, context)


def workbook_rows(
    content: bytes, sheet_name: str
) -> list[list[Any]]:
    workbook = load_workbook(BytesIO(content), data_only=True)
    try:
        worksheet = workbook[sheet_name]
        return [
            [cell.value for cell in row]
            for row in worksheet.iter_rows()
        ]
    finally:
        workbook.close()
