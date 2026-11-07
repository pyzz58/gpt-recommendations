from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from medical_one_person.domain.opportunities import (
    OpportunityCard,
    ScientificBrief,
    Track,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = PROJECT_ROOT / "fixtures" / "opportunity-contract-examples.json"


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _card(index: int) -> dict[str, Any]:
    return copy.deepcopy(_fixture()["opportunities"][index])


def _schema(name: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_synthetic_three_track_fixtures_match_contracts() -> None:
    fixture = _fixture()
    assert fixture["data_status"] == "synthetic_mock"
    assert "不是真实证据" in fixture["warning"]

    cards = [OpportunityCard.model_validate(card) for card in fixture["opportunities"]]
    assert {card.track for card in cards} == {
        Track.PET_REPURPOSING,
        Track.IVD,
        Track.DEVICE,
    }
    assert any(
        probability.method == "unknown" for card in cards for probability in card.probabilities
    )
    assert any(
        probability.method == "subjective_scenario"
        for card in cards
        for probability in card.probabilities
    )
    assert any(cost.total_range == (None, None) for card in cards for cost in card.costs)

    card_schema = _schema("opportunity-card.v1.schema.json")
    brief_schema = _schema("scientific-brief.v1.schema.json")
    Draft202012Validator.check_schema(card_schema)
    Draft202012Validator.check_schema(brief_schema)
    for raw_card in fixture["opportunities"]:
        Draft202012Validator(card_schema).validate(raw_card)
    brief = ScientificBrief.model_validate(fixture["scientific_brief"])
    assert any("不构成科学建议" in item for item in brief.limitations)
    Draft202012Validator(brief_schema).validate(fixture["scientific_brief"])


def test_fact_requires_evidence_reference() -> None:
    card = _card(0)
    card["mechanism_steps"][0]["evidence_refs"] = []
    with pytest.raises(ValidationError, match="mechanism fact requires"):
        OpportunityCard.model_validate(card)


def test_probability_requires_event_specific_evidence_and_bounds() -> None:
    unknown_numeric = _card(1)
    unknown_numeric["probabilities"][0]["lower"] = 0.2
    with pytest.raises(ValidationError, match="must not contain numeric bounds"):
        OpportunityCard.model_validate(unknown_numeric)

    reversed_bounds = _card(0)
    reversed_bounds["probabilities"][0]["lower"] = 0.8
    reversed_bounds["probabilities"][0]["upper"] = 0.2
    with pytest.raises(ValidationError, match="lower bound cannot exceed"):
        OpportunityCard.model_validate(reversed_bounds)

    ungrounded_empirical = _card(0)
    ungrounded_empirical["probabilities"][0]["method"] = "empirical"
    with pytest.raises(ValidationError, match="requires basis references"):
        OpportunityCard.model_validate(ungrounded_empirical)

    falsely_calibrated = _card(0)
    falsely_calibrated["probabilities"][0]["calibration_status"] = "calibrated"
    with pytest.raises(ValidationError, match="cannot be labelled calibrated"):
        OpportunityCard.model_validate(falsely_calibrated)


def test_unknown_and_sourced_costs_cannot_be_fabricated() -> None:
    unknown_with_number = _card(2)
    unknown_with_number["costs"][0]["line_items"][0]["quantity"] = 1
    with pytest.raises(ValidationError, match="must not contain numeric costs"):
        OpportunityCard.model_validate(unknown_with_number)

    sourced_without_reference = _card(0)
    line = sourced_without_reference["costs"][0]["line_items"][0]
    line["source_type"] = "quote"
    line["source_ref"] = None
    with pytest.raises(ValidationError, match="requires a source reference"):
        OpportunityCard.model_validate(sourced_without_reference)

    incomplete_total = _card(0)
    incomplete_total["costs"][0]["total_range"] = [2000, None]
    with pytest.raises(ValidationError, match="both bounds or neither"):
        OpportunityCard.model_validate(incomplete_total)
