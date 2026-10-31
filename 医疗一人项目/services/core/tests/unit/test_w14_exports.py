from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader

from medical_one_person.domain.exports import (
    ExportFormat,
    ReportCalculation,
    ReportReview,
    ReportSection,
    ReportSource,
    ReportTable,
    StructuredReport,
)
from medical_one_person.infrastructure.exports.engine import (
    EXPORT_SENTINEL,
    OfficeExportEngine,
)
from medical_one_person.infrastructure.exports.renderer import (
    OfficeRenderer,
    OfficeRendererUnavailable,
)
from medical_one_person.infrastructure.exports.templates import load_export_templates

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _report() -> StructuredReport:
    return StructuredReport(
        title="合成数据统计报告",
        subtitle="W14真实文件与重算测试",
        data_origin="synthetic",
        mode="mock",
        created_at=datetime.now(UTC),
        question="两组得分差异是多少？",
        method="两组均值差（正态近似区间）",
        result_summary=[
            ("组间均值差", "-5 score"),
            ("样本量", "6"),
        ],
        chart={"kind": "group_means"},
        sections=[
            ReportSection(heading="研究问题", paragraphs=["两组得分差异是多少？"]),
            ReportSection(
                heading="方法与来源",
                paragraphs=["使用合成样例和预设统计计划，不事后选择终点。"],
            ),
            ReportSection(
                heading="结果",
                paragraphs=["版本化分析记录的组间均值差为 -5 score。"],
            ),
            ReportSection(
                heading="复核与限制",
                paragraphs=["A14 的 owner 代表岗位合同记录为 accepted。"],
                bullets=["合成文件不构成科学结论。"],
            ),
        ],
        tables=[
            ReportTable(
                title="统计结果",
                columns=["指标", "结果"],
                rows=[["组间均值差", "-5 score"]],
            )
        ],
        sources=[
            ReportSource(
                kind="dataset_version",
                object_id="dataset-version-1",
                label="不可变数据版本",
                version="v1",
                sha256="1" * 64,
            ),
            ReportSource(
                kind="analysis_run",
                object_id="analysis-1",
                label="确定性分析运行",
                version="v1",
                sha256="2" * 64,
            ),
        ],
        limitations=["合成数据，不构成研究结论。"],
        review=ReportReview(
            review_id="review-1",
            reviewer_role="A14",
            decision="accepted",
            summary="合成样例复核记录。",
            reviewed_at=datetime.now(UTC),
        ),
        calculation=ReportCalculation(
            method="two_group_mean_difference",
            endpoint_column="score",
            group_column="group",
            expected_groups=["control", "treatment"],
            reported_value=-5.0,
            reported_n=6,
            unit="score",
        ),
    )


def _rows() -> list[dict[str, object]]:
    return [
        {"group": "control", "score": 12},
        {"group": "control", "score": 13},
        {"group": "control", "score": 14},
        {"group": "treatment", "score": 17},
        {"group": "treatment", "score": 18},
        {"group": "treatment", "score": 19},
    ]


def _renderer() -> OfficeRenderer:
    soffice = os.getenv("MEDICAL_ONE_OFFICE_SOFFICE_PATH")
    pdftoppm = os.getenv("MEDICAL_ONE_OFFICE_PDFTOPPM_PATH")
    renderer = OfficeRenderer(
        soffice_path=soffice,
        pdftoppm_path=pdftoppm,
    )
    status = renderer.status()
    if status.status != "ready":
        pytest.skip("LibreOffice and Poppler are required for W14 file acceptance")
    assert "cjk-font" in status.versions
    return renderer


def test_w14_template_catalog_covers_all_formats() -> None:
    templates = load_export_templates(
        PROJECT_ROOT / "config" / "templates" / "catalog.yaml"
    )
    assert {template.format for template in templates.templates} == set(ExportFormat)
    assert all(template.version == 1 for template in templates.templates)


def test_w14_generates_openable_office_pdf_and_recalculated_xlsx(tmp_path: Path) -> None:
    engine = OfficeExportEngine(_renderer())
    report = _report()
    outputs: dict[ExportFormat, Path] = {}
    for export_format in ExportFormat:
        generated = engine.generate(
            report=report,
            rows=_rows(),
            export_format=export_format,
            workdir=tmp_path / export_format.value,
        )
        assert generated.preview.page_count >= 1
        assert generated.preview.blank_pages == []
        assert generated.validation["status"] == "passed"
        outputs[export_format] = generated.file_path

    document = Document(str(outputs[ExportFormat.DOCX]))
    assert report.title in "\n".join(item.text for item in document.paragraphs)
    assert document.tables

    presentation = Presentation(str(outputs[ExportFormat.PPTX]))
    assert len(presentation.slides) >= 4

    formula_workbook = load_workbook(outputs[ExportFormat.XLSX], data_only=False)
    value_workbook = load_workbook(outputs[ExportFormat.XLSX], data_only=True)
    assert formula_workbook["导出核对"]["B5"].value
    assert str(formula_workbook["导出核对"]["B5"].value).startswith("=")
    assert value_workbook["导出核对"]["B5"].value == pytest.approx(-5)

    pdf_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs[ExportFormat.PDF]).pages
    )
    assert EXPORT_SENTINEL in "".join(pdf_text.split())


def test_w14_missing_renderer_is_explicit(tmp_path: Path) -> None:
    renderer = OfficeRenderer(
        soffice_path="/definitely/missing/soffice",
        pdftoppm_path="/definitely/missing/pdftoppm",
    )
    assert renderer.status().status == "unavailable"
    with pytest.raises(OfficeRendererUnavailable):
        OfficeExportEngine(renderer).generate(
            report=_report(),
            rows=_rows(),
            export_format=ExportFormat.PDF,
            workdir=tmp_path,
        )
