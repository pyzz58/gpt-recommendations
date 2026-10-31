"""Isolated Docling process for synthetic or authorized laboratory sources."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any


def _bbox(value: Any) -> list[float] | None:
    if value is None:
        return None
    try:
        return [
            round(float(value.l), 3),
            round(float(value.t), 3),
            round(float(value.r), 3),
            round(float(value.b), 3),
        ]
    except (AttributeError, TypeError, ValueError):
        return None


def _page(item: Any) -> int:
    provenance = getattr(item, "prov", None) or []
    if provenance:
        return int(getattr(provenance[0], "page_no", 1) or 1)
    return 1


def _cell_text(cell: Any) -> str:
    for attribute in ("text", "start_text", "start", "content"):
        value = getattr(cell, attribute, None)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    content = getattr(cell, "content", None)
    if content is not None:
        for attribute in ("text", "start_text"):
            value = getattr(content, attribute, None)
            if isinstance(value, str) and value.strip():
                return " ".join(value.split())
    return ""


def _cell_bbox(cell: Any, fallback: list[float] | None) -> list[float] | None:
    for attribute in ("bbox", "prov"):
        value = getattr(cell, attribute, None)
        if attribute == "prov" and value:
            value = getattr(value[0], "bbox", None)
        parsed = _bbox(value)
        if parsed is not None:
            return parsed
    return fallback


def _table_rows(item: Any, fallback_bbox: list[float] | None) -> list[list[dict]]:
    data = getattr(item, "data", None)
    grid = getattr(data, "grid", None)
    rows: list[list[dict]] = []
    if grid:
        for raw_row in grid:
            row = []
            for cell in raw_row:
                row.append(
                    {
                        "text": _cell_text(cell),
                        "bbox": _cell_bbox(cell, fallback_bbox),
                    }
                )
            if any(cell["text"] for cell in row):
                rows.append(row)
    if rows:
        return rows
    try:
        markdown = item.export_to_markdown()
    except Exception:
        return []
    for line in str(markdown).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= {"|", "-", ":", " "}:
            continue
        cells = [
            value.strip()
            for value in stripped.strip("|").split("|")
        ]
        rows.append(
            [
                {"text": value, "bbox": fallback_bbox}
                for value in cells
            ]
        )
    return rows


def recognize(source: Path) -> dict:
    from docling.document_converter import DocumentConverter

    started = time.perf_counter()
    result = DocumentConverter().convert(source)
    lines = []
    tables = []
    warnings = []
    table_index = 0
    for item, _level in result.document.iterate_items():
        text = getattr(item, "text", None)
        provenance = getattr(item, "prov", None) or []
        fallback_bbox = _bbox(
            getattr(provenance[0], "bbox", None) if provenance else None
        )
        page = _page(item)
        if isinstance(text, str) and text.strip():
            lines.append(
                {
                    "text": " ".join(text.split()),
                    "page": page,
                    "bbox": fallback_bbox,
                }
            )
        data = getattr(item, "data", None)
        if data is not None and hasattr(data, "grid"):
            table_index += 1
            rows = _table_rows(item, fallback_bbox)
            if rows:
                tables.append(
                    {
                        "index": table_index,
                        "page": page,
                        "bbox": fallback_bbox,
                        "rows": rows,
                    }
                )
    if not tables:
        warnings.append("Docling did not emit a structured table")
    raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    max_rss_bytes = raw_rss if sys.platform == "darwin" else raw_rss * 1024
    return {
        "provider": "docling",
        "model_version": "layout-default-ocr-default",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "max_rss_bytes": max_rss_bytes,
        "pages": len(result.document.pages) or 1,
        "tables": tables,
        "lines": lines,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    payload = recognize(args.source)
    print("CRA_LAB_RESULT=" + json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
