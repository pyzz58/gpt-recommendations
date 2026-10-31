"""Recognition acceptance over committed synthetic files, not answer JSON."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cra_app.laboratory.recognition import extract_observations
from cra_app.providers.lab_ocr import (
    LabProviderUnavailable,
    RoutedLabProvider,
    TextPdfLabProvider,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
PDF = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report.pdf"
PNG = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report_eval.png"


def test_text_pdf_is_read_from_file_with_table_coordinates():
    result = TextPdfLabProvider().recognize(
        PDF.read_bytes(),
        filename=PDF.name,
        media_type="application/pdf",
    )
    assert result.provider_name == "pdfplumber-lab-table"
    assert len(result.tables) == 1
    assert result.tables[0].page == 1
    assert result.tables[0].bbox is not None

    draft = extract_observations(result)
    assert draft.state == "recognized"
    assert draft.file_format == "text_pdf"
    assert len(draft.rows) == 5
    hemoglobin = [
        row for row in draft.rows if row.analyte_raw == "Hemoglobin"
    ]
    assert {row.instance_type for row in hemoglobin} == {"initial", "repeat"}
    assert len({row.collected_at for row in hemoglobin}) == 2
    assert all(
        row.source_ref["cells"]["analyte"]["bbox"] is not None
        for row in draft.rows
    )
    assert all(
        row.source_ref["cells"]["value_raw"]["text"]
        for row in draft.rows
    )


def test_ocr_disabled_still_reads_text_pdf_but_not_image():
    provider = RoutedLabProvider(ocr_provider="disabled")
    result = provider.recognize(
        PDF.read_bytes(),
        filename=PDF.name,
        media_type="application/pdf",
    )
    assert result.provider_name == "pdfplumber-lab-table"
    with pytest.raises(LabProviderUnavailable):
        provider.recognize(
            PNG.read_bytes(),
            filename=PNG.name,
            media_type="image/png",
        )


def test_laboratory_artifacts_are_marked_synthetic_and_hash_bound():
    manifest = json.loads(
        (FIXTURES / "manifest.json").read_text(encoding="utf-8")
    )
    artifacts = {
        item["artifact_id"]: item
        for item in manifest["artifacts"]
        if item.get("purpose") == "laboratory"
    }
    assert set(artifacts) == {
        "LAB-REPORT-PDF-DEV",
        "LAB-REPORT-PNG-EVAL",
    }
    assert "synthetic" in PDF.name
    assert "synthetic" in PNG.name
    for item in artifacts.values():
        content = (FIXTURES / item["file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        assert item["expected_file"] == "labs/evaluation_cases.json"
