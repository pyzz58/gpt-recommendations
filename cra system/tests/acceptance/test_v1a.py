"""Negative and positive acceptance for the CRA V1A evidence ledger."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import build_validation_report as report  # noqa: E402

MANIFEST = json.loads(
    (ROOT / "validation/capability-manifest.json").read_text(
        encoding="utf-8"
    )
)


def test_current_manifest_has_all_40_scenarios_and_valid_evidence():
    scenarios = MANIFEST["scenarios"]
    assert len(scenarios) == 40
    assert {item["id"] for item in scenarios} == {
        f"CRA-S{index:02d}" for index in range(1, 41)
    }
    assert report.validate_manifest(ROOT, MANIFEST) == []


def test_report_check_entry_point_passes(capsys, monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["build_validation_report.py"]
    )
    assert report.main() == 0
    body = json.loads(capsys.readouterr().out)
    assert body["clinical_validation"] is False
    assert body["engineering_evidence"] is True
    assert body["release_assessment"]["authorized_trial_ready"] is False
    assert body["release_assessment"]["v1a_core_automation_met"] is False


def test_validated_capability_without_evidence_is_rejected():
    changed = copy.deepcopy(MANIFEST)
    capability = next(
        item
        for item in changed["capabilities"]
        if item["id"] == "lab_clear_image_png"
    )
    capability["evidence"] = []
    errors = report.validate_manifest(ROOT, changed)
    assert any(
        "lab_clear_image_png" in error and "evidence" in error
        for error in errors
    )


def test_scenario_cannot_be_called_validated_without_executed_evidence():
    changed = copy.deepcopy(MANIFEST)
    scenario = changed["scenarios"][0]
    scenario["status"] = "synthetic_validated"
    scenario["evidence"] = []
    errors = report.validate_manifest(ROOT, changed)
    assert any(
        scenario["id"] in error and "evidence" in error
        for error in errors
    )


def test_incomplete_scenario_must_state_its_uncovered_scope():
    changed = copy.deepcopy(MANIFEST)
    scenario = next(
        item
        for item in changed["scenarios"]
        if item["id"] == "CRA-S02"
    )
    scenario["status"] = "not_evaluated"
    scenario["uncovered"] = []
    errors = report.validate_manifest(ROOT, changed)
    assert any(
        "CRA-S02" in error and "uncovered" in error
        for error in errors
    )


def test_trial_ready_cannot_hide_missing_w15_and_authorization():
    changed = copy.deepcopy(MANIFEST)
    changed["release_assessment"]["authorized_trial_ready"] = True
    errors = report.validate_manifest(ROOT, changed)
    assert any("verified W15" in error for error in errors)
    assert any("trial evidence" in error for error in errors)


def test_synthetic_machine_time_cannot_become_a_savings_claim():
    changed = copy.deepcopy(MANIFEST)
    changed["time_study"]["time_saving_claim"] = True
    errors = report.validate_manifest(ROOT, changed)
    assert any("cannot claim savings" in error for error in errors)


def test_summary_keeps_synthetic_and_clinical_evidence_separate():
    summary = report.build_summary(MANIFEST)
    assert summary["clinical_validation"] is False
    assert summary["engineering_evidence"] is True
    assert summary["time_study"]["time_saving_claim"] is False
    assert "CRA-S34" in {
        item["scenario_id"] for item in summary["scenario_gaps"]
    }
    assert "human_workflow_total" in (
        summary["time_study"]["incomplete_measurements"]
    )


def test_automatic_completion_is_not_enabled():
    assert all(
        item["automatic_completion_allowed"] is False
        for item in MANIFEST["capabilities"]
    )


@pytest.mark.parametrize(
    "status",
    ["synthetic_validated", "engineering_verified", "not_evaluated", "unmet"],
)
def test_scenario_status_vocabulary_is_explicit(status):
    assert status in report.SCENARIO_STATUSES
