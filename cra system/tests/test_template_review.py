"""Deterministic report-template extraction regressions."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_two_report_templates_produce_distinct_sections_and_questions():
    from cra_app.monitoring.template_review import extract_report_template

    first = extract_report_template(
        (
            ROOT
            / "tests/fixtures/reviews/artifacts/"
            "synthetic_monitoring_review_v1.docx"
        ).read_bytes()
    )
    second = extract_report_template(
        (
            ROOT
            / "tests/fixtures/reviews/artifacts/"
            "synthetic_monitoring_review_v2.docx"
        ).read_bytes()
    )
    assert [section["title"] for section in first.sections] == [
        "1. 知情同意与受试者资格",
        "2. EDC与检验原始报告",
        "3. 安全事件、问题与后续",
    ]
    assert len(first.questions) == 7
    assert first.questions[0].source_locator.startswith("paragraph[")
    assert len(second.questions) == 6
    assert second.questions[0].question_text != first.questions[0].question_text
    assert second.sections[1]["title"] == "2. 数据一致性"


def test_section_without_question_is_preserved_as_coverage_gap():
    from docx import Document
    from io import BytesIO
    from cra_app.monitoring.template_review import extract_report_template

    document = Document()
    document.add_heading("1. 有问句的章节", level=1)
    document.add_paragraph("是否已核查？")
    document.add_heading("2. 只有说明", level=1)
    document.add_paragraph("此处只有背景说明。")
    content = BytesIO()
    document.save(content)
    result = extract_report_template(content.getvalue())
    assert len(result.sections) == 2
    assert len(result.questions) == 1
    assert result.warnings[0]["code"] == "section_without_explicit_question"
    assert result.warnings[0]["section_title"] == "2. 只有说明"
