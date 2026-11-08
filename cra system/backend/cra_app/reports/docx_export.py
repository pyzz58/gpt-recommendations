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
    content, missing = _render_docx(template_bytes, mapping, context)
    review_sections = context.get("review_sections")
    if not isinstance(review_sections, list) or not review_sections:
        return content, missing
    document = Document(BytesIO(content))
    document.add_heading("报告模板核查记录", level=1)
    document.add_paragraph(
        "以下内容按确认的模板章节回填同源核查记录；未核查、"
        "待核实和跳过项不作为正常或已完成。"
    )
    for section in review_sections:
        document.add_heading(
            str(section.get("section_title", "未分类章节")), level=2
        )
        for item in section.get("items", []):
            paragraph = document.add_paragraph()
            paragraph.add_run(
                f"{item.get('item_key', '')} "
                f"{item.get('question', '')}\n"
            ).bold = True
            paragraph.add_run(
                f"状态：{item.get('status', 'not_checked')}；"
                f"记录：{item.get('note') or '未填写'}；"
                f"来源：{item.get('source_locator', 'unknown')}；"
                f"回填位置：{item.get('report_locator', 'unknown')}"
            )
    output = BytesIO()
    document.save(output)
    return output.getvalue(), missing


def docx_text(content: bytes) -> str:
    document = Document(BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            paragraphs.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(paragraphs)
