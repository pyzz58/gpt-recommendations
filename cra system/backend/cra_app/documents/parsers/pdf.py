"""Machine-readable PDF parser retaining page coordinates and table cells."""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO

import pdfplumber

from cra_app.providers.ports import CoverageUnit, ParsedAnchor, ParseResult


def _bbox(value) -> list[float]:
    return [round(float(item), 3) for item in value]


class PdfSourceParser:
    name = "pdfplumber-text"
    version = "1"

    def supports(self, media_type: str, filename: str) -> bool:
        return media_type == "application/pdf" or filename.lower().endswith(".pdf")

    def parse(
        self, content: bytes, *, media_type: str, filename: str
    ) -> ParseResult:
        anchors: list[ParsedAnchor] = []
        coverage: list[CoverageUnit] = []
        warnings: list[str] = []
        ordinal = 0
        try:
            with pdfplumber.open(BytesIO(content)) as document:
                if not document.pages:
                    return ParseResult(
                        parser_name=self.name,
                        parser_version=self.version,
                        anchors=(),
                        coverage=(
                            CoverageUnit(
                                unit_key="pages",
                                unit_type="document",
                                status="failed",
                                reason="PDF contains no pages",
                            ),
                        ),
                        status="failed",
                    )
                for page_index, page in enumerate(document.pages, start=1):
                    try:
                        table_boxes: list[tuple[float, float, float, float]] = []
                        tables = page.find_tables()
                        for table_index, table in enumerate(tables, start=1):
                            table_boxes.append(tuple(table.bbox))
                            rows = table.rows
                            for row_index, row in enumerate(rows, start=1):
                                for column_index, cell in enumerate(row.cells, start=1):
                                    if cell is None:
                                        coverage.append(
                                            CoverageUnit(
                                                unit_key=(
                                                    f"page[{page_index}]/table[{table_index}]"
                                                    f"/r[{row_index}]/c[{column_index}]:coverage"
                                                ),
                                                unit_type="table_cell",
                                                status="not_applicable",
                                                reason="table cell geometry is absent",
                                            )
                                        )
                                        continue
                                    x0, top, x1, bottom = cell
                                    text = page.crop(cell).extract_text() or ""
                                    if not text.strip():
                                        coverage.append(
                                            CoverageUnit(
                                                unit_key=(
                                                    f"page[{page_index}]/table[{table_index}]"
                                                    f"/r[{row_index}]/c[{column_index}]:coverage"
                                                ),
                                                unit_type="table_cell",
                                                status="not_applicable",
                                                reason="empty table cell",
                                            )
                                        )
                                        continue
                                    anchor_key = (
                                        f"page[{page_index}]/table[{table_index}]"
                                        f"/r[{row_index}]/c[{column_index}]"
                                    )
                                    anchors.append(
                                        ParsedAnchor(
                                            anchor_type="table_cell",
                                            logical_node_id=anchor_key,
                                            text=text,
                                            ordinal=ordinal,
                                            page_number=page_index,
                                            bbox=_bbox((x0, top, x1, bottom)),
                                            table_index=table_index,
                                            row_index=row_index,
                                            column_index=column_index,
                                        )
                                    )
                                    ordinal += 1
                                    coverage.append(
                                        CoverageUnit(
                                            unit_key=f"{anchor_key}:coverage",
                                            unit_type="table_cell",
                                            status="processed",
                                            anchor_key=anchor_key,
                                        )
                                    )

                        words = page.extract_words(
                            keep_blank_chars=False,
                            use_text_flow=False,
                            extra_attrs=["size"],
                        )
                        outside = []
                        for word in words:
                            center_x = (word["x0"] + word["x1"]) / 2
                            center_y = (word["top"] + word["bottom"]) / 2
                            inside = any(
                                x0 <= center_x <= x1 and top <= center_y <= bottom
                                for x0, top, x1, bottom in table_boxes
                            )
                            if not inside:
                                outside.append(word)
                        lines: dict[float, list[dict]] = defaultdict(list)
                        for word in outside:
                            lines[round(float(word["top"]), 1)].append(word)
                        for line_index, top in enumerate(sorted(lines), start=1):
                            line_words = sorted(lines[top], key=lambda item: item["x0"])
                            text = " ".join(str(word["text"]) for word in line_words)
                            if not text.strip():
                                continue
                            anchor_key = f"page[{page_index}]/line[{line_index}]"
                            bbox = (
                                min(float(word["x0"]) for word in line_words),
                                min(float(word["top"]) for word in line_words),
                                max(float(word["x1"]) for word in line_words),
                                max(float(word["bottom"]) for word in line_words),
                            )
                            anchors.append(
                                ParsedAnchor(
                                    anchor_type="pdf_text",
                                    logical_node_id=anchor_key,
                                    text=text,
                                    ordinal=ordinal,
                                    page_number=page_index,
                                    bbox=_bbox(bbox),
                                    style={
                                        "font_sizes": sorted(
                                            {
                                                round(float(word.get("size", 0)), 2)
                                                for word in line_words
                                            }
                                        )
                                    },
                                )
                            )
                            ordinal += 1
                            coverage.append(
                                CoverageUnit(
                                    unit_key=f"{anchor_key}:coverage",
                                    unit_type="pdf_line",
                                    status="processed",
                                    anchor_key=anchor_key,
                                )
                            )
                        coverage.append(
                            CoverageUnit(
                                unit_key=f"page[{page_index}]:coverage",
                                unit_type="page",
                                status="processed",
                                metadata={
                                    "tables": len(tables),
                                    "words": len(words),
                                },
                            )
                        )
                    except Exception as exc:
                        coverage.append(
                            CoverageUnit(
                                unit_key=f"page[{page_index}]:coverage",
                                unit_type="page",
                                status="failed",
                                reason=f"{type(exc).__name__}: {exc}"[:500],
                            )
                        )
                        warnings.append(f"page {page_index} failed")
                failed_pages = any(unit.status == "failed" for unit in coverage)
                status = (
                    "failed"
                    if failed_pages and not anchors
                    else "partial"
                    if failed_pages
                    else "completed"
                )
                return ParseResult(
                    parser_name=self.name,
                    parser_version=self.version,
                    anchors=tuple(anchors),
                    coverage=tuple(coverage),
                    status=status,
                    warnings=tuple(warnings),
                )
        except Exception as exc:
            return ParseResult(
                parser_name=self.name,
                parser_version=self.version,
                anchors=(),
                coverage=(
                    CoverageUnit(
                        unit_key="document",
                        unit_type="document",
                        status="failed",
                        reason=f"{type(exc).__name__}: {exc}"[:500],
                    ),
                ),
                status="failed",
                warnings=("PDF parsing failed",),
            )
