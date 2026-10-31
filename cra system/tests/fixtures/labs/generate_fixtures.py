"""Generate deterministic synthetic laboratory reports for CRA-W08.

The generated text PDF and image contain only fictional identifiers and values.
Expected answers live in ``evaluation_cases.json`` and are never passed to a
recognition provider.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
MANIFEST = ROOT / "manifest.json"

HEADERS = (
    "Subject ID",
    "Visit",
    "Analyte",
    "Result",
    "Unit",
    "Collection Date",
    "Collection Time",
    "Instance",
    "Specimen",
    "Report Revision",
    "LLN",
    "ULN",
)

ROWS = (
    (
        "SYN-EDC-001",
        "V1",
        "Hemoglobin",
        "121",
        "g/L",
        "2026-01-02",
        "09:15",
        "Initial",
        "Blood",
        "FINAL",
        "110",
        "160",
    ),
    (
        "SYN-EDC-001",
        "V1",
        "Hemoglobin",
        "119",
        "g/L",
        "2026-01-02",
        "09:45",
        "Repeat",
        "Blood",
        "FINAL",
        "110",
        "160",
    ),
    (
        "SYN-EDC-001",
        "V1",
        "Glucose",
        "5.1",
        "mmol/L",
        "2026-01-02",
        "09:15",
        "Initial",
        "Blood",
        "FINAL",
        "3.9",
        "5.5",
    ),
    (
        "SYN-EDC-001",
        "V1",
        "ALT",
        "32",
        "U/L",
        "2026-01-02",
        "09:15",
        "Initial",
        "Blood",
        "FINAL",
        "0",
        "40",
    ),
    (
        "SYN-EDC-002",
        "V2",
        "Creatinine",
        "88",
        "umol/L",
        "2026-01-02",
        "09:15",
        "Initial",
        "Blood",
        "FINAL",
        "50",
        "110",
    ),
)

WIDTHS = (70, 34, 72, 42, 46, 74, 68, 48, 48, 58, 32, 32)


def _draw_pdf_row(
    drawing,
    *,
    x_positions: list[float],
    y: float,
    row_height: float,
    values: tuple[str, ...],
    font_size: float = 6.7,
) -> None:
    for index, value in enumerate(values):
        x = x_positions[index]
        width = x_positions[index + 1] - x
        text_width = stringWidth(value, "Helvetica", font_size)
        drawing.drawString(x + max(2, (width - text_width) / 2), y + 7, value)
    drawing.line(x_positions[0], y, x_positions[-1], y)


def create_pdf(path: Path) -> None:
    page_width, page_height = landscape((297 * mm, 210 * mm))
    drawing = canvas.Canvas(
        str(path),
        pagesize=(page_width, page_height),
        pageCompression=1,
        invariant=1,
    )
    drawing.setTitle("Synthetic Laboratory Report - No Clinical Data")
    drawing.setAuthor("CRA synthetic fixture generator")
    drawing.setSubject("Pure synthetic W08 laboratory comparison fixture")
    drawing.setCreator("cra-system")
    drawing.setFont("Helvetica-Bold", 14)
    drawing.drawString(35, page_height - 42, "SYNTHETIC LABORATORY REPORT")
    drawing.setFont("Helvetica", 8)
    drawing.drawString(
        35,
        page_height - 57,
        "Fictional data for engineering validation only. Not a clinical record.",
    )

    x_positions = [35.0]
    for width in WIDTHS:
        x_positions.append(x_positions[-1] + width)
    row_height = 28.0
    top = page_height - 92
    bottom = top - row_height * (len(ROWS) + 1)
    for x in x_positions:
        drawing.line(x, top, x, bottom)
    drawing.setFont("Helvetica-Bold", 6.7)
    _draw_pdf_row(
        drawing,
        x_positions=x_positions,
        y=top - row_height,
        row_height=row_height,
        values=HEADERS,
    )
    drawing.setFont("Helvetica", 6.7)
    for index, row in enumerate(ROWS, start=1):
        _draw_pdf_row(
            drawing,
            x_positions=x_positions,
            y=top - row_height * (index + 1),
            row_height=row_height,
            values=row,
        )
    drawing.line(x_positions[0], top, x_positions[-1], top)
    drawing.setFont("Helvetica", 7)
    drawing.drawString(
        35,
        bottom - 24,
        "Batch: SYN-W08-001    Revision reason: synthetic baseline",
    )
    drawing.showPage()
    drawing.save()


def create_image(path: Path, *, evaluation: bool) -> None:
    width, height = 3200, 1800
    image = Image.new("RGB", (width, height), "white")
    drawing = ImageDraw.Draw(image)
    font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    if font_path.exists():
        title_font = ImageFont.truetype(str(font_path), 48)
        font = ImageFont.truetype(str(font_path), 28)
        header_font = ImageFont.truetype(str(font_path), 27)
    else:
        title_font = ImageFont.load_default(size=48)
        font = ImageFont.load_default(size=28)
        header_font = ImageFont.load_default(size=27)
    drawing.text(
        (70, 50),
        "SYNTHETIC LABORATORY REPORT",
        fill="black",
        font=title_font,
    )
    drawing.text(
        (70, 112),
        (
            "Fictional evaluation image only. Not a clinical record."
            if evaluation
            else "Fictional data for engineering validation only."
        ),
        fill="black",
        font=font,
    )

    x_positions = [70]
    for source_width in WIDTHS:
        x_positions.append(x_positions[-1] + source_width * 4.2)
    table_top = 230
    row_height = 170
    table_bottom = table_top + row_height * (len(ROWS) + 1)
    for x in x_positions:
        drawing.line((x, table_top, x, table_bottom), fill="black", width=3)
    for index in range(len(ROWS) + 2):
        y = table_top + index * row_height
        drawing.line((x_positions[0], y, x_positions[-1], y), fill="black", width=3)
    for row_index, values in enumerate((HEADERS, *ROWS)):
        y = table_top + row_index * row_height + 68
        for column_index, value in enumerate(values):
            x = x_positions[column_index] + 10
            drawing.text(
                (x, y),
                value,
                fill="black",
                font=header_font if row_index == 0 else font,
            )
    drawing.text(
        (70, table_bottom + 45),
        "Batch: SYN-W08-EVAL",
        fill="black",
        font=font,
    )
    image.save(path, format="PNG", optimize=False, compress_level=9)


def create_expected() -> dict:
    expected_rows = [
        {
            "subject_external_id": row[0],
            "visit_key": row[1],
            "analyte": row[2],
            "value_raw": row[3],
            "unit_raw": row[4],
            "collected_on": row[5],
            "collected_time": row[6],
            "instance_type": row[7].lower(),
            "specimen": row[8],
            "report_revision": row[9],
            "lower_limit": row[10],
            "upper_limit": row[11],
        }
        for row in ROWS
    ]
    return {
        "schema_version": 1,
        "source": "pure_synthetic",
        "provider_input": "No expected values are supplied to the provider.",
        "edc_artifact": "edc/artifacts/synthetic_edc_lab.xlsx",
        "rows": expected_rows,
        "required_key_checks": [
            "subject",
            "visit",
            "analyte",
            "collection day and time",
            "initial versus repeat",
            "numeric Decimal and operator",
            "unit",
        ],
    }


def create_artifact_manifest() -> dict:
    def sha(relative: str) -> str:
        return hashlib.sha256((ROOT.parent / relative).read_bytes()).hexdigest()

    return {
        "schema_version": 1,
        "generated_on": "2026-10-31",
        "source": "pure_synthetic",
        "artifacts": [
            {
                "artifact_id": "LAB-REPORT-PDF-DEV",
                "file": "labs/artifacts/synthetic_lab_report.pdf",
                "format": "pdf",
                "format_kind": "text_pdf",
                "purpose": "laboratory",
                "group": "development",
                "expected_file": "labs/evaluation_cases.json",
                "sha256": sha("labs/artifacts/synthetic_lab_report.pdf"),
                "expected": {
                    "row_count": 5,
                    "contains": [
                        "SYN-EDC-001",
                        "Hemoglobin",
                        "Glucose",
                        "Initial",
                        "Repeat",
                    ],
                    "coordinates_present": True,
                },
            },
            {
                "artifact_id": "LAB-REPORT-PNG-EVAL",
                "file": "labs/artifacts/synthetic_lab_report_eval.png",
                "format": "png",
                "format_kind": "clear_printed_image",
                "purpose": "laboratory",
                "group": "evaluation",
                "expected_file": "labs/evaluation_cases.json",
                "sha256": sha(
                    "labs/artifacts/synthetic_lab_report_eval.png"
                ),
                "expected": {
                    "row_count": 5,
                    "contains": [
                        "SYN-EDC-001",
                        "Hemoglobin",
                        "Glucose",
                        "Initial",
                        "Repeat",
                    ],
                    "coordinates_present": True,
                },
            },
        ],
    }


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    create_pdf(ARTIFACTS / "synthetic_lab_report.pdf")
    create_image(
        ARTIFACTS / "synthetic_lab_report_eval.png",
        evaluation=True,
    )
    (ROOT / "evaluation_cases.json").write_text(
        json.dumps(create_expected(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MANIFEST.write_text(
        json.dumps(create_artifact_manifest(), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
