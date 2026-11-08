"""Deterministic extraction of report-template sections and review questions."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from docx import Document


@dataclass(frozen=True)
class ExtractedQuestion:
    item_key: str
    section_key: str
    section_order: int
    section_title: str
    question_order: int
    question_text: str
    source_locator: str
    source_quote: str
    report_locator: str
    applicability: dict[str, Any]


@dataclass(frozen=True)
class ReviewTemplateExtraction:
    sections: tuple[dict[str, Any], ...]
    questions: tuple[ExtractedQuestion, ...]
    warnings: tuple[dict[str, Any], ...]


def _is_heading(style_name: str | None) -> bool:
    if not style_name:
        return False
    normalized = style_name.strip().lower()
    return (
        normalized.startswith("heading")
        or normalized.startswith("标题")
        or normalized == "section heading"
    )


def _is_question(text: str) -> bool:
    value = text.strip()
    if not value:
        return False
    if value.endswith(("?", "？")):
        return True
    return any(
        value.startswith(prefix)
        for prefix in ("是否", "请核查", "请确认", "确认", "核对")
    )


def extract_report_template(content: bytes) -> ReviewTemplateExtraction:
    """Extract only explicit headings and question-like cells/paragraphs.

    This is intentionally deterministic. It does not infer missing questions
    from clinical knowledge or silently discard unparsed report content.
    """
    try:
        document = Document(BytesIO(content))
    except Exception as exc:
        raise ValueError("DOCX report template is not readable") from exc

    sections: list[dict[str, Any]] = []
    questions: list[ExtractedQuestion] = []
    warnings: list[dict[str, Any]] = []
    current_index = -1
    current_title = "未分类"
    current_key = "S00"
    section_question_count = 0

    def ensure_section() -> None:
        nonlocal current_index, current_title, current_key
        if current_index >= 0:
            return
        current_index = 0
        current_title = "未分类"
        current_key = "S01"
        sections.append(
            {
                "section_key": current_key,
                "section_order": 0,
                "title": current_title,
                "source_locator": "document start",
            }
        )

    def add_question(
        text: str,
        *,
        locator: str,
        kind: str,
    ) -> None:
        nonlocal section_question_count
        ensure_section()
        section_question_count += 1
        question_order = section_question_count - 1
        item_key = f"S{current_index + 1:02d}-Q{section_question_count:02d}"
        questions.append(
            ExtractedQuestion(
                item_key=item_key,
                section_key=current_key,
                section_order=current_index,
                section_title=current_title,
                question_order=question_order,
                question_text=text.strip(),
                source_locator=locator,
                source_quote=text.strip(),
                report_locator=locator,
                applicability={
                    "source": "report_template",
                    "source_kind": kind,
                    "requires_cra_confirmation": True,
                    "conditions": [],
                    "exceptions": [],
                },
            )
        )

    for paragraph_index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
        if _is_heading(paragraph.style.name if paragraph.style else None):
            current_index += 1
            current_title = text
            current_key = f"S{current_index + 1:02d}"
            section_question_count = 0
            sections.append(
                {
                    "section_key": current_key,
                    "section_order": current_index,
                    "title": current_title,
                    "source_locator": f"paragraph[{paragraph_index + 1}]",
                }
            )
            continue
        if _is_question(text):
            add_question(
                text,
                locator=f"paragraph[{paragraph_index + 1}]",
                kind="paragraph",
            )

    for table_index, table in enumerate(document.tables):
        for row_index, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if not cells:
                continue
            question = next((cell for cell in cells if _is_question(cell)), None)
            if question is None:
                continue
            add_question(
                question,
                locator=f"table[{table_index + 1}]/row[{row_index + 1}]",
                kind="table_cell",
            )

    for section in sections:
        count = sum(
            1
            for question in questions
            if question.section_key == section["section_key"]
        )
        if count == 0:
            warnings.append(
                {
                    "code": "section_without_explicit_question",
                    "section_key": section["section_key"],
                    "section_title": section["title"],
                    "source_locator": section["source_locator"],
                    "message": (
                        "该章节未找到明确问句；保留章节和来源，"
                        "未解析内容不能视为无核查要求。"
                    ),
                }
            )
    if not sections:
        warnings.append(
            {
                "code": "no_template_structure",
                "message": "DOCX中未找到明确的标题或问句，必须人工补充核查项。",
            }
        )
    return ReviewTemplateExtraction(
        sections=tuple(sections),
        questions=tuple(questions),
        warnings=tuple(warnings),
    )
