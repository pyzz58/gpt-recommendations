"""A deliberately small comparison example, not a validated clinical lab engine."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class LabRecord:
    site: str
    subject: str
    visit: str
    analyte: str
    specimen: str
    collected_at: str
    repeat_instance: str
    value: str
    unit: str
    report_revision: str | None = None
    source_state: str = "confirmed"

    @property
    def identity(self) -> tuple[str, ...]:
        return (self.site, self.subject, self.visit, self.analyte, self.specimen,
                self.collected_at, self.repeat_instance)


def candidate_matches(source: LabRecord, edc_rows: list[LabRecord]) -> dict:
    matches = [row for row in edc_rows if row.identity == source.identity]
    if not matches:
        return {"status": "not_seen_in_export", "count": 0}
    if len(matches) > 1:
        return {"status": "ambiguous", "count": len(matches)}
    return {"status": "single_candidate", "count": 1}


def compare_fields(source: LabRecord, edc: LabRecord | None, *, instance_confirmed: bool = False) -> dict:
    if source.source_state != "confirmed":
        return {"status": "unverified", "reason": source.source_state, "scope": []}
    if edc is None:
        return {"status": "not_seen_in_export", "scope": [], "reason": "This does not prove EDC omission."}
    if not all(source.identity) or not all(edc.identity):
        return {"status": "identity_review", "scope": []}
    if source.identity != edc.identity:
        return {"status": "not_comparable", "reason": "different_instance", "scope": []}
    if source.report_revision and edc.report_revision and source.report_revision != edc.report_revision:
        return {"status": "not_comparable", "reason": "different_report_revision", "scope": []}
    if (not source.report_revision or not edc.report_revision) and not instance_confirmed:
        return {"status": "identity_review", "reason": "report_revision_unconfirmed", "scope": []}
    if not source.unit or not edc.unit or source.unit != edc.unit:
        return {"status": "unit_review", "scope": []}
    try:
        left, right = Decimal(source.value), Decimal(edc.value)
    except InvalidOperation:
        return {"status": "not_comparable", "reason": "value_needs_interpretation", "scope": []}
    if not left.is_finite() or not right.is_finite():
        return {"status": "not_comparable", "reason": "non_finite_value", "scope": []}
    return {
        "status": "field_agreement" if left == right else "value_difference",
        "scope": ["value", "unit"],
        "source_value": source.value,
        "edc_value": edc.value,
        "unverified_dimensions": ["reference_range", "protocol_logic", "medical_assessment"],
    }
