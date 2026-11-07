"""Generate synthetic multi-page and mild-rotation laboratory fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"

WIDTH = 3200
HEIGHT = 2200
HEADERS = (
    "Analyte",
    "Result",
    "Unit",
    "LLN",
    "ULN",
    "Collection Time",
    "Specimen",
)
CONTINUATION_ROWS = (
    ("Glucose", "5,1", "mmol/L", "3.9", "5.5", "08:10", "Blood"),
    ("Creatinine", "0.88", "mg/dL", "0.6", "1.2", "08:10", "Blood"),
)
FIRST_PAGE_ROWS = (
    ("Hemoglobin", "112", "g/L", "110", "160", "08:10", "Blood"),
    ("ALT", "<12", "U/L", "0", "40", "08:10", "Blood"),
)
JPEG_HEADERS = (
    "Subject ID",
    "Visit",
    "Analyte",
    "Result",
    "Unit",
    "Collection Date",
    "Collection Time",
    "Instance",
    "Specimen",
    "LLN",
    "ULN",
)
JPEG_ROWS = (
    (
        "SYN-W14-002",
        "V4",
        "Glucose",
        "92",
        "mg/dL",
        "2026-03-05",
        "09:00",
        "Initial",
        "Blood",
        "70",
        "110",
    ),
    (
        "SYN-W14-002",
        "V4",
        "Creatinine",
        "1.41",
        "mg/dL",
        "2026-03-05",
        "09:00",
        "Initial",
        "Blood",
        "0.6",
        "1.2",
    ),
)


def _fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    candidates = (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for path in candidates:
        if path.is_file():
            return (
                ImageFont.truetype(str(path), 48),
                ImageFont.truetype(str(path), 34),
            )
    return ImageFont.load_default(size=48), ImageFont.load_default(size=34)


def _columns(
    count: int, *, left: int = 70, right: int = WIDTH - 70
) -> list[int]:
    step = (right - left) / count
    return [round(left + step * index) for index in range(count + 1)]


def _table(
    drawing: ImageDraw.ImageDraw,
    *,
    left: int,
    top: int,
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    header_font: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
) -> int:
    columns = _columns(len(headers), left=left, right=WIDTH - 70)
    row_height = 145
    for x in columns:
        drawing.line(
            (x, top, x, top + row_height * (len(rows) + 1)),
            fill="black",
            width=3,
        )
    for row_index, values in enumerate((headers, *rows)):
        y = top + row_index * row_height
        drawing.line(
            (columns[0], y, columns[-1], y), fill="black", width=3
        )
        for column_index, value in enumerate(values):
            drawing.text(
                (columns[column_index] + 10, y + 47),
                value,
                fill="black",
                font=header_font if row_index == 0 else body_font,
            )
    drawing.line(
        (columns[0], top + row_height * (len(rows) + 1), columns[-1],
         top + row_height * (len(rows) + 1)),
        fill="black",
        width=3,
    )
    return top + row_height * (len(rows) + 1)


def _context_table(
    drawing: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
) -> int:
    values = (
        ("Subject ID", "SYN-W14-001"),
        ("Visit", "V3"),
        ("Collection Date", "2026-03-04"),
        ("Collection Time", "08:10"),
        ("Instance", "Initial"),
        ("Report Revision", "FINAL"),
    )
    left = 70
    width = 900
    top = 330
    row_height = 62
    drawing.rectangle(
        (left, top, left + width, top + row_height * len(values)),
        outline="black",
        width=2,
    )
    drawing.line(
        (left + 330, top, left + 330, top + row_height * len(values)),
        fill="black",
        width=2,
    )
    for index, (label, value) in enumerate(values):
        y = top + index * row_height
        if index:
            drawing.line((left, y, left + width, y), fill="black", width=2)
        drawing.text((left + 8, y + 12), label, fill="black", font=font)
        drawing.text((left + 340, y + 12), value, fill="black", font=font)
    return top + row_height * len(values)


def _multipage_images() -> tuple[Image.Image, Image.Image]:
    header_font, body_font = _fonts()
    first = Image.new("RGB", (WIDTH, HEIGHT), "white")
    first_draw = ImageDraw.Draw(first)
    first_draw.text(
        (70, 55),
        "SYNTHETIC COMPLEX LABORATORY REPORT",
        fill="black",
        font=header_font,
    )
    first_draw.text(
        (70, 120),
        "Fictional data for engineering validation only.",
        fill="black",
        font=body_font,
    )
    first_draw.text(
        (70, 190), "Subject ID: SYN-W14-001    Visit: V3", font=body_font
    )
    first_draw.text(
        (70, 240),
        "Collection Date: 2026-03-04    Instance: Initial",
        font=body_font,
    )
    first_draw.text(
        (70, 290), "Report Revision: FINAL", font=body_font
    )
    context_bottom = _context_table(first_draw, body_font)
    _table(
        first_draw,
        left=70,
        top=context_bottom + 45,
        headers=HEADERS,
        rows=FIRST_PAGE_ROWS,
        header_font=body_font,
        body_font=body_font,
    )
    first_draw.text(
        (70, 880),
        "Results continue on the next page without repeating the header.",
        fill="black",
        font=body_font,
    )

    second = Image.new("RGB", (WIDTH, HEIGHT), "white")
    second_draw = ImageDraw.Draw(second)
    second_draw.text(
        (70, 55),
        "SYNTHETIC COMPLEX LABORATORY REPORT - CONTINUED",
        fill="black",
        font=header_font,
    )
    second_draw.text(
        (70, 130),
        (
            "Same report and collection context; this page uses a "
            "continuation table without a header."
        ),
        fill="black",
        font=body_font,
    )
    _table(
        second_draw,
        left=70,
        top=250,
        headers=HEADERS,
        rows=CONTINUATION_ROWS,
        header_font=body_font,
        body_font=body_font,
    )
    second_draw.text(
        (70, 650),
        "The comma in Glucose is reproduced as printed and must be reviewed.",
        fill="black",
        font=body_font,
    )
    return first, second


def _jpeg_image() -> Image.Image:
    header_font, body_font = _fonts()
    image = Image.new("RGB", (WIDTH, HEIGHT), (249, 249, 249))
    drawing = ImageDraw.Draw(image)
    drawing.text(
        (70, 55),
        "SYNTHETIC MILD-ROTATION LABORATORY JPEG",
        fill="black",
        font=header_font,
    )
    drawing.text(
        (70, 115),
        "Fictional evaluation image only; not a clinical record.",
        fill="black",
        font=body_font,
    )
    columns = _columns(len(JPEG_HEADERS))
    top = 210
    row_height = 220
    for x in columns:
        drawing.line(
            (x, top, x, top + row_height * (len(JPEG_ROWS) + 1)),
            fill="black",
            width=2,
        )
    for row_index, values in enumerate((JPEG_HEADERS, *JPEG_ROWS)):
        y = top + row_index * row_height
        drawing.line(
            (columns[0], y, columns[-1], y), fill="black", width=2
        )
        for column_index, value in enumerate(values):
            drawing.text(
                (columns[column_index] + 8, y + 84),
                value,
                fill="black",
                font=body_font,
            )
    drawing.line(
        (columns[0], top + row_height * (len(JPEG_ROWS) + 1),
         columns[-1], top + row_height * (len(JPEG_ROWS) + 1)),
        fill="black",
        width=2,
    )
    return image.rotate(
        0.5, resample=Image.Resampling.BICUBIC, expand=True, fillcolor="white"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(
    subject: str,
    visit: str,
    analyte: str,
    value: str,
    unit: str,
    collected_on: str,
    collected_time: str,
    instance: str,
    specimen: str,
    lower: str,
    upper: str,
    report_revision: str | None = None,
) -> dict[str, str]:
    return {
        "subject_external_id": subject,
        "visit_key": visit,
        "analyte": analyte,
        "value_raw": value,
        "unit_raw": unit,
        "collected_on": collected_on,
        "collected_time": collected_time,
        "instance_type": instance,
        "specimen": specimen,
        "lower_limit": lower,
        "upper_limit": upper,
        "report_revision": report_revision,
    }


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    first, second = _multipage_images()
    pdf_path = ARTIFACTS / "synthetic_lab_multipage_scan.pdf"
    first.save(
        pdf_path,
        "PDF",
        resolution=180,
        save_all=True,
        append_images=[second],
        title="Synthetic two-page laboratory scan",
    )

    jpeg_path = ARTIFACTS / "synthetic_lab_mild_rotation_eval.jpeg"
    _jpeg_image().save(
        jpeg_path, "JPEG", quality=94, subsampling=0, optimize=False
    )

    scan_rows = [
        _row(
            "SYN-W14-001",
            "V3",
            analyte,
            value,
            unit,
            "2026-03-04",
            "08:10",
            "initial",
            specimen,
            lower,
            upper,
            "FINAL",
        )
        for analyte, value, unit, lower, upper, _, specimen in (
            *FIRST_PAGE_ROWS,
            *CONTINUATION_ROWS,
        )
    ]
    jpeg_rows = [_row(*values) for values in JPEG_ROWS]
    manifest = {
        "schema_version": 1,
        "source": "pure_synthetic",
        "provider_input": "Expected values are never supplied to the provider.",
        "artifacts": [
            {
                "artifact_id": "LAB-W14-MULTIPAGE-SCAN-EVAL",
                "file": "artifacts/synthetic_lab_multipage_scan.pdf",
                "format": "pdf",
                "format_kind": "scanned_pdf_multipage_continuation",
                "evaluation_group": "independent_synthetic",
                "sha256": _sha256(pdf_path),
                "expected_row_count": 4,
                "expected_rows": scan_rows,
                "expected_review_issues": {
                    "Glucose": ["numeric_value_requires_interpretation"],
                },
            },
            {
                "artifact_id": "LAB-W14-MILD-ROTATION-JPEG-EVAL",
                "file": "artifacts/synthetic_lab_mild_rotation_eval.jpeg",
                "format": "jpeg",
                "format_kind": "clear_printed_jpeg_mild_rotation",
                "evaluation_group": "independent_synthetic",
                "sha256": _sha256(jpeg_path),
                "expected_row_count": 2,
                "expected_rows": jpeg_rows,
                "expected_review_issues": {},
            },
        ],
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
