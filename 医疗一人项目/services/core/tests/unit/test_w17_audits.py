from __future__ import annotations

from pathlib import Path

from medical_one_person.application.audits import _review_packet
from medical_one_person.domain.audits import (
    AuditEvaluationFixture,
    AuditState,
    AuditTargetType,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _fixture() -> AuditEvaluationFixture:
    return AuditEvaluationFixture.model_validate_json(
        (PROJECT_ROOT / "fixtures" / "w17-audit-cases.json").read_text(
            encoding="utf-8"
        )
    )


def test_synthetic_w17_cases_hit_their_expected_rule_codes() -> None:
    fixture = _fixture()

    assert len(fixture.cases) == 7
    for case in fixture.cases:
        result = _review_packet(case.target_type, case.packet, case.reviewer_role)
        assert {finding.code for finding in result.findings} == set(
            case.expected_codes
        ), case.case_id


def test_a25_and_a26_apply_distinct_review_rules() -> None:
    fixture = _fixture()
    packet = next(
        case.packet for case in fixture.cases if case.case_id == "unreviewed-citation"
    )

    a25 = _review_packet(AuditTargetType.CLAIM_VERSION, packet, "A25")
    a26 = _review_packet(AuditTargetType.CLAIM_VERSION, packet, "A26")

    assert a25.state == AuditState.CHANGES_REQUESTED
    assert {item.code for item in a25.findings} == {"CITATION_UNREVIEWED"}
    assert a26.state == AuditState.PASSED
    assert a26.findings == []


def test_rule_fixture_detects_tampered_citation_hash_and_blocked_delivery() -> None:
    fixture = _fixture()
    clean = next(case.packet for case in fixture.cases if case.case_id == "clean-claim")
    tampered = {
        **clean,
        "evidence": [
            {
                **clean["evidence"][0],
                "citation_sha256": "0" * 64,
            }
        ],
    }
    claim = _review_packet(AuditTargetType.CLAIM_VERSION, tampered, "A25")
    assert claim.state == AuditState.BLOCKED
    assert {
        item.code for item in claim.findings
    } == {"CITATION_HASH_MISMATCH"}

    deliverable_case = next(
        case
        for case in fixture.cases
        if case.case_id == "accepted-without-raw-original"
    )
    deliverable = _review_packet(
        AuditTargetType.EXTERNAL_DELIVERABLE,
        {**deliverable_case.packet, "manifest": {}},
        "A26",
    )
    assert deliverable.state == AuditState.BLOCKED
    assert deliverable.downstream_blocked is True
    assert {item.code for item in deliverable.findings} == {
        "MANIFEST_HASH_MISSING",
        "RAW_DATA_HASH_MISSING",
        "RAW_ORIGINAL_MISSING",
    }
