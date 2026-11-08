"""Static contracts for the loopback-only synthetic Mac experience."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import local_experience  # noqa: E402


def test_local_services_bind_loopback_and_keep_w15_blocked():
    assert local_experience.WEB_URL == "http://127.0.0.1:15173"
    assert local_experience.API_URL == "http://127.0.0.1:18000"
    assert local_experience.POSTGRES_PORT == 55432
    assert local_experience._database_env()["CRA_OCR_PROVIDER"] == "docling"
    trial = (ROOT / "validation/AUTHORIZED_TRIAL.md").read_text(
        encoding="utf-8"
    )
    assert "状态：BLOCKED" in trial


def test_local_manifest_is_complete_and_pure_synthetic():
    manifest = json.loads(
        (ROOT / "synthetic_experience/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["source"] == "pure_synthetic"
    assert manifest["not_clinical_validation"] is True
    assert manifest["w15_status"] == "blocked"
    assert {
        item["purpose"] for item in manifest["files"]
    } >= {
        "rule",
        "carryover",
        "laboratory_text_pdf",
        "edc_export",
        "report_template",
    }
    for item in manifest["files"]:
        assert (ROOT / item["path"]).is_file()


def test_local_capabilities_match_declared_synthetic_provider_scope():
    manifest = json.loads(
        (ROOT / "synthetic_experience/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert "text_pdf_laboratory_reading" in manifest[
        "enabled_capabilities"
    ]
    assert "clear_image_laboratory_ocr" in manifest[
        "enabled_capabilities"
    ]
    assert "safety_analysis_model" in manifest["disabled_capabilities"]
    assert manifest["seeded_expectations"]["active_safety_rules"] == 9
    assert manifest["seeded_expectations"]["safety_question_count"] > 0
    assert manifest["seeded_expectations"]["review_template_sections"] == 3
    assert manifest["seeded_expectations"]["review_template_questions"] == 7
    assert "template_driven_review" in manifest["enabled_capabilities"]
