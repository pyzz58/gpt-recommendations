from __future__ import annotations

import csv
import io
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

import openpyxl
from docx import Document as load_docx
from openpyxl.utils import get_column_letter
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from medical_one_person.domain.knowledge.documents import (
    DocumentParseError,
    ExtractionResult,
    IngestState,
    ParsedPassage,
    ParsedTable,
)

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".eml",
    ".pptx",
}


class DocumentParser:
    extractor_version = "knowledge-parser.v1"

    def __init__(self, *, max_structured_cells: int = 200_000) -> None:
        self._max_structured_cells = max_structured_cells

    def parse(self, path: Path, *, filename: str, media_type: str) -> ExtractionResult:
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentParseError("UNSUPPORTED_FORMAT", "Unsupported document format")
        if extension == ".pdf":
            return self._pdf(path)
        if extension == ".docx":
            return self._docx(path)
        if extension == ".xlsx":
            return self._xlsx(path)
        if extension == ".csv":
            return self._csv(path)
        if extension in {".txt", ".md"}:
            return self._text(path, extension)
        if extension in {".png", ".jpg", ".jpeg"}:
            return self._image(path)
        if extension == ".eml":
            return self._eml(path, media_type)
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.PARTIAL,
            coverage={"content_not_extracted": True},
            quality_findings=[
                {
                    "code": "PPTX_PARSER_UNAVAILABLE",
                    "message": "PPTX stored; optional parser is not configured.",
                }
            ],
        )

    def _pdf(self, path: Path) -> ExtractionResult:
        try:
            reader = PdfReader(str(path))
        except Exception as exc:
            raise DocumentParseError("EXTRACTION_FAILED", "PDF could not be parsed") from exc
        if reader.is_encrypted:
            raise DocumentParseError("PASSWORD_REQUIRED", "Encrypted PDF requires an unlocked copy")
        passages: list[ParsedPassage] = []
        missing_pages: list[int] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                passages.append(
                    ParsedPassage(
                        locator={"page": page_number},
                        text=text,
                        quality={"text_extracted": True, "ocr": False},
                    )
                )
            else:
                missing_pages.append(page_number)
        if passages:
            state = IngestState.PARTIAL if missing_pages else IngestState.READY
            findings = (
                [
                    {
                        "code": "OCR_REQUIRED_FOR_PAGES",
                        "pages": missing_pages,
                    }
                ]
                if missing_pages
                else []
            )
            return ExtractionResult(
                extractor_version=self.extractor_version,
                state=state,
                passages=passages,
                coverage={
                    "pages_total": len(reader.pages),
                    "pages_with_text": len(passages),
                    "pages_missing_text": missing_pages,
                },
                quality_findings=findings,
            )
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.PARTIAL,
            coverage={
                "pages_total": len(reader.pages),
                "pages_with_text": 0,
                "pages_missing_text": missing_pages,
            },
            quality_findings=[
                {
                    "code": "OCR_REQUIRED",
                    "message": "No extractable PDF text; OCR is not configured.",
                }
            ],
        )

    def _docx(self, path: Path) -> ExtractionResult:
        try:
            document = load_docx(str(path))
        except Exception as exc:
            code = "PASSWORD_REQUIRED" if _is_encrypted_zip(path) else "EXTRACTION_FAILED"
            raise DocumentParseError(code, "DOCX could not be parsed") from exc
        passages: list[ParsedPassage] = []
        for index, paragraph in enumerate(document.paragraphs):
            text = paragraph.text.strip()
            if text:
                passages.append(
                    ParsedPassage(
                        locator={"paragraph_index": index},
                        text=text,
                        quality={"style": paragraph.style.name if paragraph.style else None},
                    )
                )
        tables: list[ParsedTable] = []
        for table_index, table in enumerate(document.tables):
            rows = [[cell.text for cell in row.cells] for row in table.rows]
            tables.append(
                ParsedTable(
                    locator={"table": table_index},
                    data={"rows": rows},
                )
            )
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.READY,
            passages=passages,
            tables=tables,
            coverage={
                "paragraphs_total": len(document.paragraphs),
                "passages": len(passages),
                "tables": len(tables),
                "headers_footers_extracted": False,
            },
        )

    def _xlsx(self, path: Path) -> ExtractionResult:
        try:
            formulas = openpyxl.load_workbook(path, data_only=False, read_only=True)
            cached = openpyxl.load_workbook(path, data_only=True, read_only=True)
        except Exception as exc:
            code = "PASSWORD_REQUIRED" if _is_encrypted_zip(path) else "EXTRACTION_FAILED"
            raise DocumentParseError(code, "XLSX could not be parsed") from exc
        tables: list[ParsedTable] = []
        cells_seen = 0
        for sheet_name in formulas.sheetnames:
            sheet_formula = formulas[sheet_name]
            sheet_cached = cached[sheet_name]
            rows: list[dict[str, object]] = []
            for row_number, (formula_row, cached_row) in enumerate(
                zip(sheet_formula.iter_rows(), sheet_cached.iter_rows(), strict=False),
                start=1,
            ):
                for formula_cell, cached_cell in zip(formula_row, cached_row, strict=False):
                    if formula_cell.value is None and cached_cell.value is None:
                        continue
                    if formula_cell.column is None:
                        continue
                    cells_seen += 1
                    if cells_seen > self._max_structured_cells:
                        raise DocumentParseError(
                            "EXTRACTION_FAILED",
                            "Workbook exceeds the structured extraction cell limit",
                        )
                    rows.append(
                        {
                            "row": row_number,
                            "column": get_column_letter(formula_cell.column),
                            "formula_or_raw": formula_cell.value,
                            "cached_value": cached_cell.value,
                            "data_type": formula_cell.data_type,
                        }
                    )
            tables.append(
                ParsedTable(
                    locator={"sheet": sheet_name},
                    data={
                        "hidden": sheet_formula.sheet_state != "visible",
                        "cells": rows,
                    },
                )
            )
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.READY,
            tables=tables,
            coverage={
                "sheets": len(tables),
                "cells": cells_seen,
                "formula_and_cached_values_separated": True,
            },
        )

    def _csv(self, path: Path) -> ExtractionResult:
        raw = path.read_bytes()
        encoding = "utf-8-sig"
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            encoding = "cp1252"
            text = raw.decode(encoding)
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return ExtractionResult(
                extractor_version=self.extractor_version,
                state=IngestState.PARTIAL,
                coverage={"rows": 0},
                quality_findings=[{"code": "EMPTY_TABLE"}],
            )
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.READY,
            tables=[
                ParsedTable(
                    locator={"table": 0, "encoding": encoding},
                    data={"rows": rows, "header": rows[0]},
                )
            ],
            coverage={"rows": len(rows), "encoding": encoding},
        )

    def _text(self, path: Path, extension: str) -> ExtractionResult:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
            encoding = "utf-8-replacement"
        passages: list[ParsedPassage] = []
        line_start = 1
        current: list[str] = []
        current_offset = 0
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip() and current:
                block = "\n".join(current)
                passages.append(
                    ParsedPassage(
                        locator={
                            "start_line": line_start,
                            "end_line": line_number - 1,
                            "start_char": current_offset,
                            "end_char": current_offset + len(block),
                        },
                        text=block,
                        quality={"encoding": encoding, "format": extension},
                    )
                )
                current_offset += len(block) + 1
                current = []
                line_start = line_number + 1
            else:
                if not current:
                    line_start = line_number
                current.append(line)
        if current:
            block = "\n".join(current)
            passages.append(
                ParsedPassage(
                    locator={
                        "start_line": line_start,
                        "end_line": line_start + len(current) - 1,
                        "start_char": current_offset,
                        "end_char": current_offset + len(block),
                    },
                    text=block,
                    quality={"encoding": encoding, "format": extension},
                )
            )
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.READY if passages else IngestState.PARTIAL,
            passages=passages,
            coverage={"encoding": encoding, "characters": len(text)},
            quality_findings=[] if encoding == "utf-8" else [{"code": "DECODE_REPLACEMENT"}],
        )

    def _image(self, path: Path) -> ExtractionResult:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                dimensions = {"width": image.width, "height": image.height}
                image_format = image.format
        except (UnidentifiedImageError, OSError) as exc:
            raise DocumentParseError("EXTRACTION_FAILED", "Image could not be parsed") from exc
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.PARTIAL,
            coverage={"image": dimensions, "format": image_format, "ocr": False},
            quality_findings=[
                {
                    "code": "OCR_UNAVAILABLE",
                    "message": "Image stored; OCR dependency is not configured.",
                }
            ],
        )

    def _eml(self, path: Path, media_type: str) -> ExtractionResult:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = message.get_body(preferencelist=("plain", "html"))
        text = body.get_content() if body is not None else ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        passages = (
            [
                ParsedPassage(
                    locator={"part": "body"},
                    text=str(text).strip(),
                    quality={"media_type": media_type},
                )
            ]
            if str(text).strip()
            else []
        )
        attachments = [
            {
                "filename": part.get_filename(),
                "content_type": part.get_content_type(),
                "size_bytes": len(part.get_payload(decode=True) or b""),
            }
            for part in message.iter_attachments()
        ]
        return ExtractionResult(
            extractor_version=self.extractor_version,
            state=IngestState.READY,
            passages=passages,
            tables=[
                ParsedTable(
                    locator={"part": "headers"},
                    data={
                        "from": str(message.get("From", "")),
                        "to": str(message.get("To", "")),
                        "subject": str(message.get("Subject", "")),
                        "message_id": message.get("Message-ID"),
                        "date": str(message.get("Date", "")),
                        "attachments": attachments,
                    },
                )
            ],
            coverage={"attachments_metadata": len(attachments)},
        )


def _is_encrypted_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return any(info.flag_bits & 0x1 for info in archive.infolist())
    except zipfile.BadZipFile:
        return False
