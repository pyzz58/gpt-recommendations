from __future__ import annotations

import math
import sys
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.properties import PageSetupProperties
from pptx import Presentation
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches
from pptx.util import Pt as PptxPt
from pypdf import PdfReader
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_LEFT  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import (  # type: ignore[import-untyped]
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from medical_one_person.domain.exports import ExportFormat, StructuredReport
from medical_one_person.infrastructure.exports.renderer import (
    OfficeRenderer,
    PdfPreview,
)


class ExportValidationError(Exception):
    pass


EXPORT_SENTINEL = "W14-EXPORT-CHECK"
OFFICE_FONT_NAME = "Arial Unicode MS" if sys.platform == "darwin" else "Noto Sans CJK SC"


@dataclass(frozen=True)
class GeneratedExport:
    file_path: Path
    preview: PdfPreview
    validation: dict[str, Any]


class OfficeExportEngine:
    def __init__(
        self,
        renderer: OfficeRenderer,
        *,
        pdf_font_path: Path | None = None,
    ) -> None:
        self._renderer = renderer
        self._pdf_font_path = pdf_font_path

    def generate(
        self,
        *,
        report: StructuredReport,
        rows: list[dict[str, Any]],
        export_format: ExportFormat,
        workdir: Path,
    ) -> GeneratedExport:
        workdir.mkdir(parents=True, exist_ok=True)
        output = workdir / f"report.{export_format.value}"
        checks: list[dict[str, Any]] = []

        if export_format == ExportFormat.DOCX:
            _write_docx(output, report)
            checks.extend(_validate_docx(output, report))
        elif export_format == ExportFormat.PPTX:
            _write_pptx(output, report)
            checks.extend(_validate_pptx(output, report))
        elif export_format == ExportFormat.XLSX:
            draft = workdir / "draft.xlsx"
            formulas = _write_xlsx(draft, report, rows)
            recalculated = self._renderer.recalculate_xlsx(draft, workdir / "recalc")
            output.write_bytes(recalculated.read_bytes())
            checks.extend(_validate_xlsx(output, report, formulas))
        elif export_format == ExportFormat.PDF:
            _write_pdf(output, report, font_path=self._pdf_font_path)
            checks.extend(_validate_pdf(output, report))
        else:
            raise ExportValidationError(f"Unsupported export format: {export_format}")

        failed = [check for check in checks if check["status"] != "passed"]
        if failed:
            raise ExportValidationError(
                "Structural validation failed: "
                + "; ".join(str(check["message"]) for check in failed)
            )
        preview = self._renderer.render_preview(
            output,
            workdir / "preview",
            expected_text=[EXPORT_SENTINEL],
        )
        runtime = self._renderer.status()
        validation = {
            "status": "passed",
            "scope": (
                "File openability, required text presence, rendered page non-blankness, "
                "shape bounds and independent formula comparison for this fixture"
            ),
            "checks": checks
            + [
                {
                    "code": "render.pages",
                    "status": "passed",
                    "message": "Preview PDF rendered to images without blank pages",
                    "page_count": preview.page_count,
                    "rendered_page_count": preview.rendered_page_count,
                    "minimum_content_ratio": preview.minimum_content_ratio,
                },
                {
                    "code": "render.required_text",
                    "status": "passed",
                    "message": "Rendered PDF contains title and required section text",
                    "extracted_characters": preview.extracted_characters,
                },
            ],
            "page_count": preview.page_count,
            "blank_pages": preview.blank_pages,
            "formula_checks": [
                check for check in checks if check["code"].startswith("formula.")
            ],
            "tool_versions": runtime.versions,
            "limitations": [
                "Automated rendering checks detect open failures and blank pages, not every "
                "font, clipping, typographic or semantic defect.",
                "Formula checks cover the explicit workbook reconciliation cells only.",
                "A generated document does not make its scientific interpretation valid.",
            ],
        }
        return GeneratedExport(file_path=output, preview=preview, validation=validation)


def _write_docx(path: Path, report: StructuredReport) -> None:
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(2.1)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    styles = document.styles
    styles["Normal"].font.name = OFFICE_FONT_NAME
    styles["Normal"].font.size = Pt(10.5)
    for style_name in ("Title", "Subtitle", "Heading 1", "Heading 2"):
        style = styles[style_name]
        style.font.name = OFFICE_FONT_NAME
        style.font.color.rgb = RGBColor(23, 79, 68)
    document.core_properties.title = report.title
    document.core_properties.subject = report.subtitle
    document.core_properties.author = "医疗一人项目"
    document.core_properties.comments = (
        "Generated from a versioned analysis and accepted owner-recorded review."
    )

    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.add_run(report.title)
    subtitle = document.add_paragraph(report.subtitle)
    subtitle.style = styles["Subtitle"]
    _add_docx_meta_table(document, report)
    document.add_paragraph(
        "说明：本文件是可追溯交付，不因文件生成成功而证明数据质量、研究设计或科学结论。"
    )
    document.add_page_break()  # type: ignore[no-untyped-call]

    for report_section in report.sections:
        document.add_heading(report_section.heading, level=1)
        for paragraph in report_section.paragraphs:
            document.add_paragraph(paragraph)
        for bullet in report_section.bullets:
            document.add_paragraph(bullet, style="List Bullet")
        if report_section.heading == "结果":
            _add_docx_result_table(document, report)

    document.add_heading("来源与版本", level=1)
    source_table = document.add_table(rows=1, cols=4)
    source_table.style = "Table Grid"
    for cell, label in zip(
        source_table.rows[0].cells,
        ("类别", "对象", "版本", "SHA-256"),
        strict=True,
    ):
        cell.text = label
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for source in report.sources:
        cells = source_table.add_row().cells
        values = (
            source.label,
            source.object_id,
            source.version,
            source.sha256 or "—",
        )
        for cell, value in zip(cells, values, strict=True):
            cell.text = value

    document.add_heading("关键限制", level=1)
    for limitation in report.limitations:
        document.add_paragraph(limitation, style="List Bullet")
    document.add_heading("复核记录", level=1)
    document.add_paragraph(
        f"{report.review.reviewer_role} 于 {report.review.reviewed_at.isoformat()} "
        f"记录决定 {report.review.decision}。"
    )
    document.add_paragraph(report.review.summary)
    footer = section.footer.paragraphs[0]
    footer.text = (
        f"医疗一人项目 · {EXPORT_SENTINEL} · "
        "来源与模板版本见文内 · 生成文件不等于科学验证"
    )
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.save(str(path))


def _add_docx_meta_table(document: Any, report: StructuredReport) -> None:
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Shading Accent 1"
    analysis_source = next(
        item for item in report.sources if item.kind == "analysis_run"
    )
    dataset_source = next(
        item for item in report.sources if item.kind == "dataset_version"
    )
    metadata = (
        (
            "数据来源",
            {
                "synthetic": "合成数据",
                "real": "已声明真实数据",
                "unknown": "来源性质未知",
            }[report.data_origin],
        ),
        ("运行模式", report.mode),
        ("分析方法", report.method),
        ("分析版本", analysis_source.version),
        ("数据行 SHA-256", dataset_source.sha256 or "—"),
        ("复核角色与决定", f"{report.review.reviewer_role} / {report.review.decision}"),
    )
    for label, value in metadata:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
        for run in cells[0].paragraphs[0].runs:
            run.bold = True


def _add_docx_result_table(document: Any, report: StructuredReport) -> None:
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, label in zip(table.rows[0].cells, ("指标", "结果", "说明"), strict=True):
        cell.text = label
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for label, value in report.result_summary:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
        cells[2].text = "来自版本化分析结果"


def _validate_docx(path: Path, report: StructuredReport) -> list[dict[str, Any]]:
    try:
        document = Document(str(path))
    except Exception as exc:
        raise ExportValidationError("Generated DOCX cannot be opened") from exc
    paragraphs = "\n".join(paragraph.text for paragraph in document.paragraphs)
    expected = [report.title, *(section.heading for section in report.sections)]
    missing = [value for value in expected if value not in paragraphs]
    return [
        {
            "code": "docx.open",
            "status": "passed",
            "message": "python-docx reopened the generated document",
            "paragraph_count": len(document.paragraphs),
            "table_count": len(document.tables),
        },
        {
            "code": "docx.required_text",
            "status": "passed" if not missing and document.tables else "failed",
            "message": (
                "Required report title, sections and result table are present"
                if not missing and document.tables
                else f"DOCX is missing required content: {missing}"
            ),
        },
    ]


def _write_pptx(path: Path, report: StructuredReport) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    presentation.core_properties.title = report.title
    presentation.core_properties.subject = report.subtitle

    cover = presentation.slides.add_slide(presentation.slide_layouts[6])
    _add_pptx_band(cover, presentation)
    _add_pptx_text(
        cover,
        report.title,
        Inches(0.85),
        Inches(1.35),
        Inches(11.6),
        Inches(1.5),
        30,
        bold=True,
    )
    _add_pptx_text(
        cover,
        report.subtitle,
        Inches(0.85),
        Inches(3.05),
        Inches(11.6),
        Inches(0.9),
        18,
    )
    _add_pptx_text(
        cover,
        (
            f"{report.method} · "
            f"{'合成数据' if report.data_origin == 'synthetic' else report.data_origin}"
            f" · {report.mode}"
        ),
        Inches(0.85),
        Inches(4.25),
        Inches(11.6),
        Inches(0.6),
        13,
        color="65727B",
    )
    _add_pptx_footer(cover, presentation, report)

    for report_section in report.sections:
        items = [*report_section.paragraphs, *report_section.bullets]
        chunks = _chunks(items, 6)
        for chunk_index, chunk in enumerate(chunks):
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            _add_pptx_text(
                slide,
                report_section.heading + ("（续）" if chunk_index else ""),
                Inches(0.75),
                Inches(0.45),
                Inches(11.8),
                Inches(0.8),
                24,
                bold=True,
                color="174F44",
            )
            for index, item in enumerate(chunk):
                top = 1.55 + index * 0.78
                shape = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE,
                    Inches(0.72),
                    Inches(top),
                    Inches(0.52),
                    Inches(0.52),
                )
                shape.fill.solid()
                shape.fill.fore_color.rgb = PptxRGBColor(  # type: ignore[no-untyped-call]
                    224,
                    238,
                    233,
                )
                shape.line.fill.background()
                _add_pptx_text(
                    slide,
                    str(index + chunk_index * 6 + 1),
                    Inches(0.72),
                    Inches(top + 0.07),
                    Inches(0.52),
                    Inches(0.3),
                    11,
                    bold=True,
                    color="174F44",
                    align=PP_ALIGN.CENTER,
                )
                _add_pptx_text(
                    slide,
                    item,
                    Inches(1.45),
                    Inches(top),
                    Inches(11.0),
                    Inches(0.66),
                    15,
                )
            if report_section.heading == "结果":
                _add_pptx_result_table(slide, report)
            _add_pptx_footer(slide, presentation, report)

    sources_slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _add_pptx_text(
        sources_slide,
        "来源、版本与复核",
        Inches(0.75),
        Inches(0.45),
        Inches(11.8),
        Inches(0.8),
        24,
        bold=True,
        color="174F44",
    )
    source_lines = [
        f"{source.label} · {source.version} · {(source.sha256 or '无哈希')[:16]}"
        for source in report.sources
    ]
    source_lines.append(
        f"复核：{report.review.reviewer_role} / {report.review.decision} · "
        f"{report.review.reviewed_at.date().isoformat()}"
    )
    for index, line in enumerate(source_lines[:8]):
        _add_pptx_text(
            sources_slide,
            line,
            Inches(0.9),
            Inches(1.45 + index * 0.6),
            Inches(11.6),
            Inches(0.45),
            12,
        )
    _add_pptx_footer(sources_slide, presentation, report)
    presentation.save(str(path))


def _add_pptx_band(slide: Any, presentation: Any) -> None:
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        0,
        0,
        presentation.slide_width,
        Inches(0.32),
    )
    band.fill.solid()
    band.fill.fore_color.rgb = PptxRGBColor(  # type: ignore[no-untyped-call]
        23,
        79,
        68,
    )
    band.line.fill.background()


def _add_pptx_text(
    slide: Any,
    text: str,
    left: Any,
    top: Any,
    width: Any,
    height: Any,
    font_size: int,
    *,
    bold: bool = False,
    color: str = "18222A",
    align: PP_ALIGN = PP_ALIGN.LEFT,
) -> Any:
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = text
    run.font.name = OFFICE_FONT_NAME
    run.font.size = PptxPt(font_size)
    run.font.bold = bold
    run.font.color.rgb = PptxRGBColor(  # type: ignore[no-untyped-call]
        int(color[0:2], 16),
        int(color[2:4], 16),
        int(color[4:6], 16),
    )
    return box


def _add_pptx_result_table(slide: Any, report: StructuredReport) -> None:
    row_count = min(len(report.result_summary), 4)
    if row_count == 0:
        return
    table_shape = slide.shapes.add_table(
        row_count,
        2,
        Inches(0.88),
        Inches(5.94),
        Inches(11.55),
        Inches(0.12 + row_count * 0.27),
    )
    table = table_shape.table
    table.columns[0].width = Inches(2.6)
    table.columns[1].width = Inches(8.95)
    for row_index, (label, value) in enumerate(report.result_summary[:row_count]):
        for column_index, text in enumerate((label, value)):
            cell = table.cell(row_index, column_index)
            cell.text = text
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = PptxPt(9)
                paragraph.font.name = OFFICE_FONT_NAME


def _add_pptx_footer(slide: Any, presentation: Any, report: StructuredReport) -> None:
    _add_pptx_text(
        slide,
        (
            f"医疗一人项目 · {report.mode} · 输入 "
            f"{report.calculation.reported_n} 条 · {EXPORT_SENTINEL} · "
            "生成文件不等于科学验证"
        ),
        Inches(0.76),
        presentation.slide_height - Inches(0.38),
        Inches(11.8),
        Inches(0.24),
        8,
        color="7A858C",
    )


def _validate_pptx(path: Path, report: StructuredReport) -> list[dict[str, Any]]:
    try:
        presentation = Presentation(str(path))
    except Exception as exc:
        raise ExportValidationError("Generated PPTX cannot be opened") from exc
    width = int(presentation.slide_width or 0)
    height = int(presentation.slide_height or 0)
    out_of_bounds: list[str] = []
    texts: list[str] = []
    for slide_index, slide in enumerate(presentation.slides, start=1):
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texts.append(shape.text)
            left = int(shape.left or 0)
            top = int(shape.top or 0)
            right = left + int(shape.width or 0)
            bottom = top + int(shape.height or 0)
            if left < 0 or top < 0 or right > width + 1 or bottom > height + 1:
                out_of_bounds.append(f"slide {slide_index} shape {shape.shape_id}")
    expected = [report.title, *(section.heading for section in report.sections)]
    joined = "\n".join(texts)
    missing = [
        value
        for value in expected
        if value not in joined and f"{value}（续）" not in joined
    ]
    return [
        {
            "code": "pptx.open",
            "status": "passed",
            "message": "python-pptx reopened the generated presentation",
            "slide_count": len(presentation.slides),
        },
        {
            "code": "pptx.bounds",
            "status": "passed" if not out_of_bounds else "failed",
            "message": (
                "All slide shapes remain within slide bounds"
                if not out_of_bounds
                else f"Out-of-bounds shapes: {out_of_bounds}"
            ),
        },
        {
            "code": "pptx.required_text",
            "status": "passed" if not missing else "failed",
            "message": (
                "Required title and sections are present"
                if not missing
                else f"PPTX is missing required text: {missing}"
            ),
        },
    ]


def _write_xlsx(
    path: Path,
    report: StructuredReport,
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], tuple[str, float]]:
    workbook = Workbook()
    summary = workbook.active
    assert summary is not None
    summary.title = "报告摘要"
    summary.sheet_view.showGridLines = False
    summary.column_dimensions["A"].width = 24
    summary.column_dimensions["B"].width = 78
    _xlsx_title(summary, "A1:B1", report.title)
    summary["A2"] = report.subtitle
    summary.merge_cells("A2:B2")
    summary["A2"].font = Font(name=OFFICE_FONT_NAME, size=12, color="65727B")
    fields = [
        ("数据来源", "合成数据" if report.data_origin == "synthetic" else report.data_origin),
        ("运行模式", report.mode),
        ("分析方法", report.method),
        ("研究问题", report.question),
        ("模板说明", "analysis-workbook.xlsx v1"),
        ("重要边界", "生成文件不等于数据质量或科学结论已验证"),
    ]
    for index, (label, value) in enumerate(fields, start=4):
        summary.cell(index, 1, label)
        summary.cell(index, 2, value)
        _xlsx_label(summary.cell(index, 1))
        summary.cell(index, 2).alignment = Alignment(wrap_text=True, vertical="top")
    summary.row_dimensions[4].height = 60
    summary.freeze_panes = "A4"

    results = workbook.create_sheet("统计结果")
    results.sheet_view.showGridLines = False
    results.column_dimensions["A"].width = 34
    results.column_dimensions["B"].width = 46
    results.column_dimensions["C"].width = 60
    _xlsx_title(results, "A1:C1", "版本化分析结果")
    headers = ("指标", "结果", "说明")
    for column, header in enumerate(headers, start=1):
        results.cell(3, column, header)
        _xlsx_header(results.cell(3, column))
    for row_index, (label, value) in enumerate(report.result_summary, start=4):
        results.cell(row_index, 1, label)
        results.cell(row_index, 2, value)
        results.cell(row_index, 3, "来自 AnalysisRun 的结构化结果")
        for column in range(1, 4):
            results.cell(row_index, column).alignment = Alignment(
                wrap_text=True,
                vertical="top",
            )
    results.freeze_panes = "A4"

    data = workbook.create_sheet("分析数据")
    data.sheet_view.showGridLines = False
    data.append(["行号", "组别", report.calculation.endpoint_column])
    for column in range(1, 4):
        _xlsx_header(data.cell(1, column))
    parsed_rows = _analysis_values(report, rows)
    for output_index, (group, numeric_value) in enumerate(parsed_rows, start=2):
        data.cell(output_index, 1, output_index - 1)
        data.cell(output_index, 2, group)
        data.cell(output_index, 3, numeric_value)
    data.column_dimensions["A"].width = 12
    data.column_dimensions["B"].width = 24
    data.column_dimensions["C"].width = 24
    data.freeze_panes = "A2"

    limitations = workbook.create_sheet("限制与复核")
    limitations.sheet_view.showGridLines = False
    limitations.column_dimensions["A"].width = 120
    _xlsx_title(limitations, "A1:A1", "限制、来源与复核")
    limitations["A3"] = "关键限制"
    _xlsx_header(limitations["A3"])
    current_row = 4
    for limitation in report.limitations:
        limitations.cell(current_row, 1, limitation)
        current_row += 1
    current_row += 1
    limitations.cell(current_row, 1, "来源与版本")
    _xlsx_header(limitations.cell(current_row, 1))
    current_row += 1
    for source in report.sources:
        limitations.cell(
            current_row,
            1,
            f"{source.label} | {source.version} | {source.sha256 or '无哈希'}",
        )
        current_row += 1
    current_row += 1
    limitations.cell(
        current_row,
        1,
        f"复核 {report.review.reviewer_role} / {report.review.decision}: "
        f"{report.review.summary}",
    )

    checks = workbook.create_sheet("导出核对")
    checks.sheet_view.showGridLines = False
    checks.column_dimensions["A"].width = 34
    checks.column_dimensions["B"].width = 42
    checks.column_dimensions["C"].width = 70
    _xlsx_title(checks, "A1:C1", "LibreOffice 重算与独立计算核对")
    for column, header in enumerate(("核对项", "公式结果", "公式原文"), start=1):
        checks.cell(3, column, header)
        _xlsx_header(checks.cell(3, column))

    formulas = _formula_expectations(report, parsed_rows)
    for row_index, ((sheet, _cell), (formula, _expected)) in enumerate(
        formulas.items(),
        start=4,
    ):
        checks.cell(row_index, 1, sheet)
        checks.cell(row_index, 2, f"={formula}")
        checks.cell(row_index, 3, formula)
        checks.cell(row_index, 1).alignment = Alignment(wrap_text=True)
        checks.cell(row_index, 3).alignment = Alignment(wrap_text=True)
    checks["A9"] = "说明"
    _xlsx_label(checks["A9"])
    checks["B9"] = (
        "公式仅覆盖下列明确核对单元格；缓存值由 LibreOffice 实际重算，"
        "并与 Python 对同一分析数据的独立计算结果比较。"
    )
    checks.merge_cells("B9:C10")
    checks["B9"].alignment = Alignment(wrap_text=True, vertical="top")
    for worksheet in workbook.worksheets:
        _configure_xlsx_print_layout(worksheet)
        _apply_xlsx_font(worksheet)
        page_footer = worksheet.oddFooter
        if page_footer is not None and page_footer.center is not None:
            page_footer.center.text = (
                f"医疗一人项目 · {EXPORT_SENTINEL} · 生成文件不等于科学验证"
            )
    workbook.save(path)
    return formulas


def _apply_xlsx_font(sheet: Any) -> None:
    for row in sheet.iter_rows():
        for cell in row:
            font = copy(cell.font)
            font.name = OFFICE_FONT_NAME
            cell.font = font


def _configure_xlsx_print_layout(sheet: Any) -> None:
    sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_setup.paperSize = 9
    sheet.page_margins.left = 0.3
    sheet.page_margins.right = 0.3
    sheet.page_margins.top = 0.45
    sheet.page_margins.bottom = 0.55
    sheet.print_area = f"A1:{sheet.cell(sheet.max_row, sheet.max_column).coordinate}"


def _validate_xlsx(
    path: Path,
    report: StructuredReport,
    formulas: dict[tuple[str, str], tuple[str, float]],
) -> list[dict[str, Any]]:
    try:
        formula_workbook = load_workbook(path, data_only=False, read_only=False)
        value_workbook = load_workbook(path, data_only=True, read_only=False)
    except Exception as exc:
        raise ExportValidationError("Recalculated XLSX cannot be opened") from exc
    checks: list[dict[str, Any]] = [
        {
            "code": "xlsx.open",
            "status": "passed",
            "message": "openpyxl reopened the recalculated workbook",
            "sheet_count": len(formula_workbook.sheetnames),
        }
    ]
    independent = _independent_calculation(report, value_workbook["分析数据"])
    checks.append(
        {
            "code": "xlsx.independent_calculation",
            "status": (
                "passed"
                if math.isclose(
                    independent,
                    report.calculation.reported_value,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
                else "failed"
            ),
            "message": (
                "Python calculation from export rows matches the W13 reported value"
                if math.isclose(
                    independent,
                    report.calculation.reported_value,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
                else (
                    f"Independent value {independent} differs from reported "
                    f"{report.calculation.reported_value}"
                )
            ),
            "independent_value": independent,
            "reported_value": report.calculation.reported_value,
        }
    )
    for (sheet_name, cell), (expected_formula, expected) in formulas.items():
        formula_cell = formula_workbook[sheet_name][cell]
        cached_cell = value_workbook[sheet_name][cell]
        formula_value = formula_cell.value
        cached_value = cached_cell.value
        formula_preserved = isinstance(formula_value, str) and formula_value.startswith("=")
        cached_numeric = isinstance(cached_value, int | float)
        matches = cached_numeric and math.isclose(
            float(cached_value),
            expected,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
        checks.append(
            {
                "code": "formula.cached_value",
                "status": "passed" if formula_preserved and matches else "failed",
                "message": (
                    f"{sheet_name}!{cell} retains a formula and cached value matches "
                    "the independent calculation"
                    if formula_preserved and matches
                    else (
                        f"{sheet_name}!{cell} formula={formula_value!r}, "
                        f"cached={cached_value!r}, expected={expected!r}"
                    )
                ),
                "sheet": sheet_name,
                "cell": cell,
                "formula": formula_value,
                "cached_value": cached_value,
                "expected": expected,
                "expected_formula": expected_formula,
            }
        )
    return checks


def _xlsx_title(sheet: Any, target: str, text: str) -> None:
    if ":" in target and target.split(":", 1)[0] != target.split(":", 1)[1]:
        sheet.merge_cells(target)
    cell = sheet[target.split(":")[0]]
    cell.value = text
    cell.font = Font(name=OFFICE_FONT_NAME, size=20, bold=True, color="174F44")
    cell.alignment = Alignment(vertical="center")
    sheet.row_dimensions[cell.row].height = 34


def _xlsx_label(cell: Any) -> None:
    cell.font = Font(name=OFFICE_FONT_NAME, bold=True, color="174F44")
    cell.fill = PatternFill("solid", fgColor="E0EEE9")
    cell.alignment = Alignment(vertical="top", wrap_text=True)


def _xlsx_header(cell: Any) -> None:
    cell.font = Font(name=OFFICE_FONT_NAME, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="174F44")
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    thin = Side(style="thin", color="DCE2DF")
    cell.border = Border(bottom=thin)


def _formula_expectations(
    report: StructuredReport,
    rows: list[tuple[str, float]],
) -> dict[tuple[str, str], tuple[str, float]]:
    last_row = len(rows) + 1
    count_formula = f"COUNTA('分析数据'!C2:C{last_row})"
    calculation = report.calculation
    if calculation.method == "two_group_mean_difference":
        if len(calculation.expected_groups) != 2:
            raise ExportValidationError("Two-group export needs exactly two expected groups")
        first, second = calculation.expected_groups
        first_literal = _excel_string(first)
        second_literal = _excel_string(second)
        value_formula = (
            f"AVERAGEIF('分析数据'!B2:B{last_row},{first_literal},"
            f"'分析数据'!C2:C{last_row})-AVERAGEIF("
            f"'分析数据'!B2:B{last_row},{second_literal},"
            f"'分析数据'!C2:C{last_row})"
        )
        independent = _group_difference(rows, first, second)
    else:
        value_formula = f"AVERAGE('分析数据'!C2:C{last_row})"
        independent = sum(value for _, value in rows) / len(rows)
    if not rows:
        raise ExportValidationError("Cannot create formula checks without analysis rows")
    return {
        ("导出核对", "B4"): (count_formula, float(len(rows))),
        ("导出核对", "B5"): (value_formula, independent),
    }


def _independent_calculation(report: StructuredReport, sheet: Any) -> float:
    rows: list[tuple[str, float]] = []
    for row_index in range(2, sheet.max_row + 1):
        group = sheet.cell(row_index, 2).value
        value = sheet.cell(row_index, 3).value
        if isinstance(value, int | float):
            rows.append((str(group), float(value)))
    if report.calculation.method == "two_group_mean_difference":
        if len(report.calculation.expected_groups) != 2:
            raise ExportValidationError("Two-group export needs exactly two expected groups")
        return _group_difference(
            rows,
            report.calculation.expected_groups[0],
            report.calculation.expected_groups[1],
        )
    return sum(value for _, value in rows) / len(rows)


def _analysis_values(
    report: StructuredReport,
    rows: list[dict[str, Any]],
) -> list[tuple[str, float]]:
    values: list[tuple[str, float]] = []
    endpoint = report.calculation.endpoint_column
    method = report.calculation.method
    for row in rows:
        raw = row.get(endpoint)
        if raw is None:
            continue
        number = (
            _binary_number(raw)
            if method == "proportion_wilson"
            else _numeric_number(raw)
        )
        group = (
            str(row.get(report.calculation.group_column))
            if report.calculation.group_column
            else "全部"
        )
        values.append((group, number))
    if not values:
        raise ExportValidationError("No numeric analysis values remain for XLSX export")
    if len(values) != report.calculation.reported_n:
        raise ExportValidationError("Export rows do not match the analysis sample count")
    if method == "two_group_mean_difference":
        groups = set(report.calculation.expected_groups)
        if any(group not in groups for group, _ in values):
            raise ExportValidationError("Export rows contain an unexpected analysis group")
    return values


def _group_difference(
    rows: list[tuple[str, float]],
    first: str,
    second: str,
) -> float:
    first_values = [value for group, value in rows if group == first]
    second_values = [value for group, value in rows if group == second]
    if not first_values or not second_values:
        raise ExportValidationError("Formula validation group has no observations")
    return sum(first_values) / len(first_values) - sum(second_values) / len(second_values)


def _numeric_number(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ExportValidationError("Analysis data contains a non-finite number")
    return number


def _binary_number(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "positive", "是", "阳性"}:
        return 1.0
    if normalized in {"0", "false", "no", "negative", "否", "阴性"}:
        return 0.0
    number = float(normalized)
    if number not in {0.0, 1.0}:
        raise ExportValidationError("Proportion data must be binary")
    return number


def _excel_string(value: str) -> str:
    if any(character in value for character in ("\x00", "\n", "\r")):
        raise ExportValidationError("Analysis group contains unsupported control characters")
    return '"' + value.replace('"', '""') + '"'


def _write_pdf(
    path: Path,
    report: StructuredReport,
    *,
    font_path: Path | None = None,
) -> None:
    font_name = _register_pdf_font(font_path)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=25,
        leading=34,
        textColor=colors.HexColor("#174F44"),
        alignment=TA_LEFT,
        spaceAfter=12 * mm,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=12,
        leading=19,
        textColor=colors.HexColor("#65727B"),
        spaceAfter=8 * mm,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=17,
        leading=23,
        textColor=colors.HexColor("#174F44"),
        spaceBefore=7 * mm,
        spaceAfter=4 * mm,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=16,
        spaceAfter=2.5 * mm,
    )
    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=body_style,
        leftIndent=5 * mm,
        firstLineIndent=-3 * mm,
        bulletIndent=0,
    )
    small_style = ParagraphStyle(
        "ReportSmall",
        parent=body_style,
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor("#65727B"),
    )
    story: list[Any] = [
        Paragraph(escape(report.title), title_style),
        Paragraph(escape(report.subtitle), subtitle_style),
    ]
    meta_rows = [
        ["数据来源", "合成数据" if report.data_origin == "synthetic" else report.data_origin],
        ["运行模式", report.mode],
        ["分析方法", report.method],
        [f"复核（{report.review.reviewer_role}）", report.review.decision],
    ]
    meta_table = Table(meta_rows, colWidths=[38 * mm, 125 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E0EEE9")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#174F44")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DCE2DF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            meta_table,
            Spacer(1, 7 * mm),
            Paragraph(
                escape(
                    "说明：本文件是可追溯交付，不因文件生成成功而证明数据质量、"
                    "研究设计或科学结论。"
                ),
                subtitle_style,
            ),
            Spacer(1, 10 * mm),
        ]
    )
    for report_section in report.sections:
        story.append(Paragraph(escape(report_section.heading), heading_style))
        for paragraph in report_section.paragraphs:
            story.append(Paragraph(escape(paragraph), body_style))
        for bullet in report_section.bullets:
            story.append(Paragraph(f"• {escape(bullet)}", bullet_style))
        if report_section.heading == "结果":
            data = [["指标", "结果", "说明"]]
            data.extend(
                [[label, value, "来自版本化分析结果"] for label, value in report.result_summary]
            )
            table = Table(data, colWidths=[38 * mm, 42 * mm, 83 * mm], repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174F44")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C5D0CB")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.extend([Spacer(1, 2 * mm), table, Spacer(1, 4 * mm)])

    story.append(Paragraph("来源与版本", heading_style))
    for source in report.sources:
        story.append(
            Paragraph(
                escape(
                    f"{source.label} · {source.object_id} · {source.version} · "
                    f"{source.sha256 or '无哈希'}"
                ),
                small_style,
            )
        )
    story.append(Paragraph("关键限制", heading_style))
    for limitation in report.limitations:
        story.append(Paragraph(f"• {escape(limitation)}", bullet_style))
    story.append(Paragraph("复核记录", heading_style))
    story.append(Paragraph(escape(report.review.summary), body_style))

    def add_page_number(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#65727B"))
        canvas.drawString(22 * mm, 12 * mm, "医疗一人项目 · 生成文件不等于科学验证")
        canvas.drawString(22 * mm, 17 * mm, EXPORT_SENTINEL)
        canvas.drawRightString(
            A4[0] - 22 * mm,
            12 * mm,
            f"第 {document.page} 页",
        )
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=report.title,
        author="医疗一人项目",
        subject=report.subtitle,
    )
    document.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)


def _register_pdf_font(configured_path: Path | None) -> str:
    candidates = [
        configured_path,
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            try:
                pdfmetrics.registerFont(TTFont("ReportCJK", str(candidate)))
                return "ReportCJK"
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _validate_pdf(path: Path, report: StructuredReport) -> list[dict[str, Any]]:
    try:
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ExportValidationError("Generated PDF cannot be opened") from exc
    normalized = "".join(text.split())
    required = [EXPORT_SENTINEL]
    missing = [value for value in required if value not in normalized]
    return [
        {
            "code": "pdf.open",
            "status": "passed",
            "message": "pypdf reopened the generated PDF",
            "page_count": len(reader.pages),
        },
        {
            "code": "pdf.required_text",
            "status": "passed" if not missing else "failed",
            "message": (
                "Required export sentinel can be extracted from the PDF"
                if not missing
                else f"PDF is missing the export sentinel: {missing}"
            ),
        },
    ]


def _chunks(values: list[str], size: int) -> list[list[str]]:
    if not values:
        return [["本部分无额外说明。"]]
    return [values[index : index + size] for index in range(0, len(values), size)]
