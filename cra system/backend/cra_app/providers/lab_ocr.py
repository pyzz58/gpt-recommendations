"""Replaceable laboratory recognition adapters with source coordinates."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

import pdfplumber


class LabProviderUnavailable(Exception):
    """The requested source format has no enabled recognition provider."""


class LabProviderError(Exception):
    """A configured provider failed or returned an invalid response."""


@dataclass(frozen=True)
class ProviderCell:
    text: str
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class ProviderRow:
    cells: tuple[ProviderCell, ...]


@dataclass(frozen=True)
class ProviderTable:
    index: int
    page: int
    bbox: tuple[float, float, float, float] | None
    rows: tuple[ProviderRow, ...]


@dataclass(frozen=True)
class ProviderLine:
    text: str
    page: int
    bbox: tuple[float, float, float, float] | None


@dataclass(frozen=True)
class LabRecognitionResult:
    provider_name: str
    provider_version: str
    model_version: str | None
    file_format: str
    tables: tuple[ProviderTable, ...]
    lines: tuple[ProviderLine, ...]
    warnings: tuple[str, ...]
    elapsed_seconds: float | None = None
    max_rss_bytes: int | None = None


class LabRecognitionProvider(Protocol):
    @property
    def enabled(self) -> bool: ...

    def recognize(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
    ) -> LabRecognitionResult: ...


def _bbox(value: Any) -> tuple[float, float, float, float] | None:
    if value is None or len(value) != 4:
        return None
    try:
        return tuple(round(float(item), 3) for item in value)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


class TextPdfLabProvider:
    name = "pdfplumber-lab-table"
    version = "1"

    @property
    def enabled(self) -> bool:
        return True

    def recognize(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
    ) -> LabRecognitionResult:
        tables: list[ProviderTable] = []
        lines: list[ProviderLine] = []
        warnings: list[str] = []
        table_index = 0
        with pdfplumber.open(BytesIO(content)) as document:
            for page_number, page in enumerate(document.pages, start=1):
                found_tables = page.find_tables()
                table_boxes = [tuple(table.bbox) for table in found_tables]
                for table in found_tables:
                    table_index += 1
                    rows: list[ProviderRow] = []
                    for row in table.rows:
                        cells: list[ProviderCell] = []
                        for cell in row.cells:
                            if cell is None:
                                cells.append(ProviderCell(""))
                                continue
                            text = page.crop(cell).extract_text() or ""
                            cells.append(
                                ProviderCell(
                                    text=" ".join(text.split()),
                                    bbox=_bbox(cell),
                                )
                            )
                        if any(cell.text for cell in cells):
                            rows.append(ProviderRow(tuple(cells)))
                    tables.append(
                        ProviderTable(
                            index=table_index,
                            page=page_number,
                            bbox=_bbox(table.bbox),
                            rows=tuple(rows),
                        )
                    )
                words = page.extract_words()
                outside = []
                for word in words:
                    center_x = (word["x0"] + word["x1"]) / 2
                    center_y = (word["top"] + word["bottom"]) / 2
                    if any(
                        x0 <= center_x <= x1 and top <= center_y <= bottom
                        for x0, top, x1, bottom in table_boxes
                    ):
                        continue
                    outside.append(word)
                grouped: dict[float, list[dict[str, Any]]] = {}
                for word in outside:
                    grouped.setdefault(round(float(word["top"]), 1), []).append(
                        word
                    )
                for top in sorted(grouped):
                    row_words = sorted(
                        grouped[top], key=lambda item: float(item["x0"])
                    )
                    text = " ".join(str(item["text"]) for item in row_words)
                    if not text.strip():
                        continue
                    lines.append(
                        ProviderLine(
                            text=text,
                            page=page_number,
                            bbox=_bbox(
                                (
                                    min(float(item["x0"]) for item in row_words),
                                    min(float(item["top"]) for item in row_words),
                                    max(float(item["x1"]) for item in row_words),
                                    max(
                                        float(item["bottom"])
                                        for item in row_words
                                    ),
                                )
                            ),
                        )
                    )
        if not tables and not lines:
            warnings.append("no text or table structure was recovered")
        return LabRecognitionResult(
            provider_name=self.name,
            provider_version=self.version,
            model_version=None,
            file_format="text_pdf",
            tables=tuple(tables),
            lines=tuple(lines),
            warnings=tuple(warnings),
        )


class DoclingLabProvider:
    """Run Docling in an isolated process so the main runtime stays on 3.13."""

    name = "docling"
    version = "2.145.0"

    def __init__(
        self,
        *,
        enabled: bool,
        package_version: str = "2.145.0",
        timeout_seconds: int = 900,
        project_root: Path | None = None,
    ):
        self._enabled = enabled
        self.package_version = package_version
        self.timeout_seconds = timeout_seconds
        self.project_root = project_root or Path(__file__).resolve().parents[3]

    @property
    def enabled(self) -> bool:
        return self._enabled

    def recognize(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
    ) -> LabRecognitionResult:
        if not self.enabled:
            raise LabProviderUnavailable(
                "Docling image recognition is not configured"
            )
        uv = shutil.which("uv")
        if not uv:
            raise LabProviderError("uv executable is required for Docling")
        suffix = Path(filename).suffix.lower() or ".bin"
        with tempfile.TemporaryDirectory(prefix="cra-lab-provider-") as temporary:
            source = Path(temporary) / f"source{suffix}"
            source.write_bytes(content)
            command = [
                uv,
                "run",
                "--no-project",
                "--isolated",
                "--python",
                "3.12",
                "--with",
                f"docling=={self.package_version}",
                "python",
                "-m",
                "cra_app.providers.lab_worker",
                "--source",
                str(source),
            ]
            environment = os.environ.copy()
            backend = str(self.project_root / "backend")
            environment["PYTHONPATH"] = backend + (
                os.pathsep + environment["PYTHONPATH"]
                if environment.get("PYTHONPATH")
                else ""
            )
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.project_root,
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise LabProviderError("Docling recognition timed out") from exc
            if completed.returncode != 0:
                error = (completed.stderr or completed.stdout)[-2000:]
                raise LabProviderError(
                    "Docling recognition failed: " + error
                )
            marker = "CRA_LAB_RESULT="
            payload = next(
                (
                    line[len(marker) :]
                    for line in reversed(completed.stdout.splitlines())
                    if line.startswith(marker)
                ),
                None,
            )
            if payload is None:
                raise LabProviderError(
                    "Docling process returned no structured result"
                )
            try:
                result = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise LabProviderError(
                    "Docling process returned invalid JSON"
                ) from exc
        tables = tuple(
            ProviderTable(
                index=int(table["index"]),
                page=int(table.get("page") or 1),
                bbox=_bbox(table.get("bbox")),
                rows=tuple(
                    ProviderRow(
                        tuple(
                            ProviderCell(
                                text=str(cell.get("text") or ""),
                                bbox=_bbox(cell.get("bbox")),
                            )
                            for cell in row
                        )
                    )
                    for row in table.get("rows", [])
                    if row
                ),
            )
            for table in result.get("tables", [])
        )
        lines = tuple(
            ProviderLine(
                text=str(line.get("text") or ""),
                page=int(line.get("page") or 1),
                bbox=_bbox(line.get("bbox")),
            )
            for line in result.get("lines", [])
            if str(line.get("text") or "").strip()
        )
        return LabRecognitionResult(
            provider_name=self.name,
            provider_version=self.package_version,
            model_version=(
                str(result["model_version"])
                if result.get("model_version")
                else None
            ),
            file_format=(
                "scanned_pdf"
                if media_type == "application/pdf"
                else "clear_printed_image"
            ),
            tables=tables,
            lines=lines,
            warnings=tuple(str(item) for item in result.get("warnings", [])),
            elapsed_seconds=(
                float(result["elapsed_seconds"])
                if result.get("elapsed_seconds") is not None
                else None
            ),
            max_rss_bytes=(
                int(result["max_rss_bytes"])
                if result.get("max_rss_bytes") is not None
                else None
            ),
        )


class RoutedLabProvider:
    """Use direct PDF structure when available and Docling for images/scans."""

    def __init__(self, *, ocr_provider: str, project_root: Path | None = None):
        self.text_pdf = TextPdfLabProvider()
        self.docling = DoclingLabProvider(
            enabled=ocr_provider.strip().lower() in {"docling", "auto"},
            project_root=project_root,
        )

    def recognize(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
    ) -> LabRecognitionResult:
        suffix = Path(filename).suffix.lower()
        if media_type == "application/pdf":
            try:
                text_result = self.text_pdf.recognize(
                    content, filename=filename, media_type=media_type
                )
            except Exception as exc:
                raise LabProviderError(
                    f"text PDF recognition failed: {type(exc).__name__}"
                ) from exc
            if text_result.tables:
                return text_result
            if self.docling.enabled:
                return self.docling.recognize(
                    content, filename=filename, media_type=media_type
                )
            return text_result
        if media_type in {"image/png", "image/jpeg"} and suffix in {
            ".png",
            ".jpg",
            ".jpeg",
        }:
            if not self.docling.enabled:
                raise LabProviderUnavailable(
                    "image recognition requires CRA_OCR_PROVIDER=docling"
                )
            return self.docling.recognize(
                content, filename=filename, media_type=media_type
            )
        raise LabProviderUnavailable(
            f"unsupported laboratory source type: {media_type}"
        )
