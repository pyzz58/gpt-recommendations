from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from medical_one_person.domain.phase_validation import (
    PilotCoverageEntry,
    PilotEvidenceLevel,
    PilotProcessStep,
    PilotReadinessInput,
    evaluate_pilot_readiness,
)

ROOT = Path(__file__).resolve().parents[4]


def baseline() -> PilotReadinessInput:
    return PilotReadinessInput.model_validate(
        json.loads((ROOT / "fixtures/w24-pilot-baseline.json").read_text())
    )


def test_baseline_pilot_is_prepared_and_never_complete() -> None:
    report = evaluate_pilot_readiness(baseline())

    assert report.status == "prepared_no_real_evidence"
    assert report.required_steps == len(PilotProcessStep)
    assert report.declared_steps == len(PilotProcessStep)
    assert report.missing_steps == []
    assert report.real_evidence_steps == []
    assert report.declared_coverage_complete is False
    assert report.phase_one_complete is False
    assert report.human_confirmation_required is True
    assert len(report.gaps) == len(PilotProcessStep)


def test_real_evidence_levels_require_specific_references() -> None:
    with pytest.raises(ValidationError, match="contacted requires real evidence"):
        PilotCoverageEntry(
            step=PilotProcessStep.PROVIDER_MATCHING,
            level=PilotEvidenceLevel.CONTACTED,
            owner_role="A22",
        )

    with pytest.raises(ValidationError, match="accepted requires acceptance"):
        PilotCoverageEntry(
            step=PilotProcessStep.RAW_DELIVERY,
            level=PilotEvidenceLevel.ACCEPTED,
            owner_role="A22",
            evidence_refs=["mail:1"],
            authorization_refs=["auth:1"],
            execution_refs=["run:1"],
            delivery_refs=["delivery:1"],
        )


def test_not_applicable_requires_reason_and_duplicate_steps_fail() -> None:
    with pytest.raises(ValidationError, match="concrete reason"):
        PilotCoverageEntry(
            step=PilotProcessStep.PROVIDER_MATCHING,
            level=PilotEvidenceLevel.NOT_APPLICABLE,
            owner_role="A22",
        )

    data = baseline().model_dump(mode="json")
    data["coverage"].append(data["coverage"][0])
    with pytest.raises(ValidationError, match="coverage steps must be unique"):
        PilotReadinessInput.model_validate(data)


def test_declared_complete_still_requires_human_confirmation() -> None:
    entries = []
    for step in PilotProcessStep:
        entries.append(
            PilotCoverageEntry(
                step=step,
                level=PilotEvidenceLevel.ACCEPTED,
                owner_role="A03",
                evidence_refs=[f"evidence:{step.value}"],
                authorization_refs=[f"authorization:{step.value}"],
                execution_refs=[f"execution:{step.value}"],
                delivery_refs=[f"delivery:{step.value}"],
                acceptance_refs=[f"acceptance:{step.value}"],
            )
        )
    report = evaluate_pilot_readiness(
        PilotReadinessInput(
            pilot_id="TEST",
            version=1,
            candidate_defined=True,
            charter_ref="fixture",
            coverage=entries,
        )
    )

    assert report.status == "declared_complete_pending_human_review"
    assert report.declared_coverage_complete is True
    assert report.phase_one_complete is False
    assert report.human_confirmation_required is True
