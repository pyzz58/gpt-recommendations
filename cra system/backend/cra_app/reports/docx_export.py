"""Controlled DOCX rendering and content inspection."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document

from cra_app.reports.template_mapping import (
    DocxTemplateMapping,
    render_docx as _render_docx,
)


def render_docx(
    template_bytes: bytes,
    mapping: DocxTemplateMapping,
    context: dict[str, Any],
) -> tuple[bytes, list[str]]:
    return _render_docx(template_bytes, mapping, context)


def docx_text(content: bytes) -> str:
    document = Document(BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            paragraphs.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(paragraphs)
