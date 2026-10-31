"""Isolated candidate process used only by the synthetic provider probe."""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path


def _result(
    engine: str,
    *,
    started: float,
    tokens: list[str],
    boxes: list[list[float]],
    markdown: str = "",
    pages: int = 1,
) -> dict:
    raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    max_rss_bytes = raw_rss if sys.platform == "darwin" else raw_rss * 1024
    return {
        "engine": engine,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "max_rss_bytes": max_rss_bytes,
        "tokens": tokens,
        "boxes": boxes,
        "markdown": markdown[:4000],
        "pages": pages,
    }


def paddle(image: Path) -> dict:
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from paddleocr import PaddleOCR

    started = time.perf_counter()
    engine = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    predictions = list(engine.predict(str(image)))
    tokens: list[str] = []
    boxes: list[list[float]] = []
    for prediction in predictions:
        payload = prediction.json["res"]
        tokens.extend(str(value) for value in payload.get("rec_texts", []))
        boxes.extend(
            [float(value) for value in box]
            for box in payload.get("rec_boxes", [])
        )
    return _result(
        "paddleocr",
        started=started,
        tokens=tokens,
        boxes=boxes,
        pages=max(1, len(predictions)),
    )


def docling(image: Path) -> dict:
    from docling.document_converter import DocumentConverter

    started = time.perf_counter()
    result = DocumentConverter().convert(image)
    tokens: list[str] = []
    boxes: list[list[float]] = []
    for item, _level in result.document.iterate_items():
        text = getattr(item, "text", None)
        if isinstance(text, str) and text.strip():
            tokens.append(text)
        provenance = getattr(item, "prov", None) or []
        for source in provenance:
            bbox = source.bbox
            boxes.append([bbox.l, bbox.t, bbox.r, bbox.b])
    markdown = result.document.export_to_markdown()
    return _result(
        "docling",
        started=started,
        tokens=tokens,
        boxes=boxes,
        markdown=markdown,
        pages=len(result.document.pages) or 1,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["paddleocr", "docling"], required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()
    result = paddle(args.image) if args.engine == "paddleocr" else docling(args.image)
    print("CRA_PROBE_RESULT=" + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
