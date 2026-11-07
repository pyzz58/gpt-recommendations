"""Recognition acceptance over committed synthetic files, not answer JSON."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from cra_app.laboratory.recognition import extract_observations
from cra_app.laboratory.comparison import (
    EdcValue,
    ObservationValue,
    compare_observation,
)
from cra_app.providers.lab_ocr import (
    LabRecognitionResult,
    LabProviderUnavailable,
    ProviderCell,
    ProviderRow,
    ProviderTable,
    RoutedLabProvider,
    TextPdfLabProvider,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
PDF = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report.pdf"
PNG = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report_eval.png"
ZH_CONTEXT_PDF = (
    FIXTURES / "labs" / "artifacts" / "synthetic_lab_report_zh_context.pdf"
)


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
        "LAB-REPORT-ZH-CONTEXT-EVAL",
    }
    assert "synthetic" in PDF.name
    assert "synthetic" in PNG.name
    for item in artifacts.values():
        content = (FIXTURES / item["file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        assert item["expected_file"] in {
            "labs/evaluation_cases.json",
            "labs/evaluation_cases_zh_context.json",
        }


def test_chinese_report_context_is_bound_once_and_reused_by_rows():
    result = TextPdfLabProvider().recognize(
        ZH_CONTEXT_PDF.read_bytes(),
        filename=ZH_CONTEXT_PDF.name,
        media_type="application/pdf",
    )
    draft = extract_observations(result)
    assert draft.state == "recognized"
    assert len(draft.rows) == 2
    assert draft.report_context.values["subject_external_id"] == "SYN-ZH-001"
    assert draft.report_context.values["collected_on"] == "2026-01-02"
    assert draft.report_context.values["instance_type"] == "初检"
    assert {row.subject_external_id for row in draft.rows} == {"SYN-ZH-001"}
    assert {row.instance_type for row in draft.rows} == {"initial"}
    assert all(
        row.source_ref["cells"]["subject_external_id"]["kind"]
        == "report_context"
        for row in draft.rows
    )


def _complex_result(
    first_rows: tuple[tuple[str, ...], ...],
    continuation_rows: tuple[tuple[str, ...], ...],
) -> LabRecognitionResult:
    header = (
        "Subject ID",
        "Analyte",
        "Result",
        "Unit",
        "Collection Date",
        "Instance",
    )

    def table(
        index: int, page: int, rows: tuple[tuple[str, ...], ...]
    ) -> ProviderTable:
        return ProviderTable(
            index=index,
            page=page,
            bbox=(10.0, 10.0, 500.0, 300.0),
            rows=tuple(
                ProviderRow(
                    tuple(ProviderCell(value) for value in row)
                )
                for row in rows
            ),
        )

    return LabRecognitionResult(
        provider_name="synthetic-complex-provider",
        provider_version="2",
        model_version="synthetic-test",
        file_format="scanned_pdf",
        tables=(
            table(1, 1, (header, *first_rows)),
            table(2, 2, continuation_rows),
        ),
        lines=(),
        warnings=(),
    )


def test_headerless_continuation_reuses_compatible_previous_header():
    result = _complex_result(
        (
            (
                "SYN-W14-001",
                "Hemoglobin",
                "112",
                "g/L",
                "2026-03-04",
                "Initial",
            ),
        ),
        (
            (
                "SYN-W14-001",
                "Glucose",
                "5,1",
                "mmol/L",
                "2026-03-04",
                "Initial",
            ),
        ),
    )
    draft = extract_observations(result)
    assert [row.analyte_raw for row in draft.rows] == [
        "Hemoglobin",
        "Glucose",
    ]
    continuation = draft.rows[1]
    assert continuation.source_ref["header_inherited"] is True
    assert continuation.source_ref["header_table_index"] == 1
    assert continuation.source_ref["header_page"] == 1
    assert "table 2 reused the compatible header from table 1" in draft.warnings


def test_incompatible_continuation_is_not_guessed():
    result = _complex_result(
        (
            (
                "SYN-W14-001",
                "Hemoglobin",
                "112",
                "g/L",
                "2026-03-04",
                "Initial",
            ),
        ),
        (("Caption only",),),
    )
    draft = extract_observations(result)
    assert [row.analyte_raw for row in draft.rows] == ["Hemoglobin"]
    assert "table 2 has no recognizable laboratory header" in draft.warnings


def test_caption_rows_are_removed_and_suspicious_units_need_review():
    result = _complex_result(
        (
            (
                "SYN-W14-001",
                "ALT",
                "<12",
                "7/",
                "2026-03-04",
                "Initial",
            ),
            (
                "The comma is reproduced as printed.",
                "The comma is reproduced as printed.",
                "The comma is reproduced as printed.",
                "",
                "",
                "",
            ),
        ),
        (),
    )
    draft = extract_observations(result)
    assert len(draft.rows) == 1
    row = draft.rows[0]
    assert row.value_raw == "<12"
    assert row.operator == "<"
    assert "unit_unrecognized_or_inconsistent" in row.issues
    assert row.validation_state == "needs_review"


def test_w14_complex_fixtures_are_hash_bound_and_independent():
    manifest = json.loads(
        (
            ROOT / "tests/w14_fixtures/manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["source"] == "pure_synthetic"
    assert {
        item["format_kind"] for item in manifest["artifacts"]
    } == {
        "scanned_pdf_multipage_continuation",
        "clear_printed_jpeg_mild_rotation",
    }
    for item in manifest["artifacts"]:
        path = ROOT / "tests/w14_fixtures" / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        assert item["evaluation_group"] == "independent_synthetic"


def test_non_laboratory_source_format_is_explicitly_rejected():
    provider = RoutedLabProvider(ocr_provider="disabled")
    with pytest.raises(LabProviderUnavailable, match="supported routes"):
        provider.recognize(
            b"synthetic",
            filename="synthetic_lab_report.tiff",
            media_type="image/tiff",
        )


def test_complex_candidates_use_the_existing_comparison_service():
    result = _complex_result(
        (
            (
                "SYN-W14-001",
                "Hemoglobin",
                "112",
                "g/L",
                "2026-03-04",
                "Initial",
            ),
            (
                "SYN-W14-001",
                "Glucose",
                "5,1",
                "mmol/L",
                "2026-03-04",
                "Initial",
            ),
        ),
        (),
    )
    draft = extract_observations(result)
    normal, ambiguous = draft.rows
    source = ObservationValue(
        id="normal",
        subject_external_id=normal.subject_external_id,
        visit_key=None,
        analyte=normal.analyte_raw,
        specimen=normal.specimen,
        collected_on=normal.collected_on,
        collected_at=normal.collected_at,
        instance_type=normal.instance_type,
        report_on=normal.report_on,
        report_revision=normal.report_revision,
        value_raw=normal.value_raw,
        unit=normal.unit_raw,
        lower_limit=normal.lower_limit_raw,
        upper_limit=normal.upper_limit_raw,
        validation_state=normal.validation_state,
        issues=normal.issues,
    )
    edc = EdcValue(
        id="existing-edc-row",
        subject_external_id="SYN-W14-001",
        subject_id="synthetic-subject",
        visit_key=None,
        analyte="Hemoglobin",
        specimen="Blood",
        collected_on=date(2026, 3, 4),
        collected_at=datetime(2026, 3, 4, 8, 10),
        instance_type="initial",
        report_on=None,
        report_revision=None,
        value_raw="112",
        unit="g/L",
        lower_limit=None,
        upper_limit=None,
    )
    outcome = compare_observation(source, [edc])
    assert outcome.result_status == "agreement"
    assert outcome.edc_record_id == edc.id
    assert "clinical_safe" not in {
        result.field
        for result in outcome.field_results
    }
    assert ambiguous.validation_state == "needs_review"
    ambiguous_source = source.__class__(
        **{
            **source.__dict__,
            "id": "ambiguous",
            "analyte": ambiguous.analyte_raw,
            "value_raw": ambiguous.value_raw,
            "unit": ambiguous.unit_raw,
            "validation_state": ambiguous.validation_state,
            "issues": ambiguous.issues,
        }
    )
    ambiguous_outcome = compare_observation(ambiguous_source, [edc])
    assert ambiguous_outcome.result_status == "not_comparable"
    assert "source_needs_review" in ambiguous_outcome.unknowns
