"""Deterministic laboratory identity matching and Decimal field comparison."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from cra_app.laboratory.matching import (
    MatchStatus,
    match_observation,
    normalize_unit,
)

ResultStatus = Literal[
    "agreement",
    "value_difference",
    "logic_difference",
    "unit_review",
    "not_seen_in_export",
    "not_comparable",
    "unreadable",
    "not_checked_by_user",
]

_VALUE_PATTERN = re.compile(
    r"^\s*(<=|>=|<|>)?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*$"
)
@dataclass(frozen=True)
class ParsedValue:
    raw: str
    value_type: Literal["exact", "bound", "text", "unknown"]
    operator: str | None
    number: Decimal | None


def parse_value(value: str | None) -> ParsedValue:
    raw = "" if value is None else value
    match = _VALUE_PATTERN.fullmatch(raw)
    if match is None:
        return ParsedValue(
            raw=raw,
            value_type="unknown" if not raw.strip() else "text",
            operator=None,
            number=None,
        )
    try:
        number = Decimal(match.group(2))
    except InvalidOperation:
        return ParsedValue(raw, "text", None, None)
    if not number.is_finite():
        return ParsedValue(raw, "text", None, None)
    operator = match.group(1)
    return ParsedValue(
        raw=raw,
        value_type="bound" if operator else "exact",
        operator=operator,
        number=number,
    )


@dataclass(frozen=True)
class ObservationValue:
    id: str
    subject_external_id: str | None
    visit_key: str | None
    analyte: str | None
    specimen: str | None
    collected_on: date | None
    collected_at: datetime | None
    instance_type: str | None
    report_on: date | None
    report_revision: str | None
    value_raw: str | None
    unit: str | None
    lower_limit: str | None = None
    upper_limit: str | None = None
    validation_state: str = "ready_for_match"
    extraction_state: str = "auto_extracted"
    issues: tuple[str, ...] = ()

    @property
    def value(self) -> ParsedValue:
        return parse_value(self.value_raw)

    @property
    def unit_normalized(self) -> str | None:
        return normalize_unit(self.unit)


@dataclass(frozen=True)
class EdcValue:
    id: str
    subject_external_id: str | None
    subject_id: str | None
    visit_key: str | None
    analyte: str | None
    specimen: str | None
    collected_on: date | None
    collected_at: datetime | None
    instance_type: str | None
    report_on: date | None
    report_revision: str | None
    value_raw: str | None
    unit: str | None
    lower_limit: str | None = None
    upper_limit: str | None = None
    identity_status: str = "mapped"
    validation_status: str = "ready_for_match"
    issues: tuple[str, ...] = ()

    @property
    def value(self) -> ParsedValue:
        return parse_value(self.value_raw)

    @property
    def unit_normalized(self) -> str | None:
        return normalize_unit(self.unit)


@dataclass(frozen=True)
class FieldResult:
    field: str
    status: str
    source: Any = None
    edc: Any = None
    detail: str | None = None


@dataclass(frozen=True)
class ComparisonOutcome:
    match_status: MatchStatus
    result_status: ResultStatus
    matched_identity: dict[str, Any]
    candidate_record_ids: tuple[str, ...]
    unknowns: tuple[str, ...]
    reason: str | None
    field_results: tuple[FieldResult, ...] = field(default_factory=tuple)
    edc_record_id: str | None = None


def _reference_flag(
    value: ParsedValue,
    lower: str | None,
    upper: str | None,
) -> str:
    if value.value_type != "exact" or value.number is None:
        return "unknown"
    parsed_lower = parse_value(lower)
    parsed_upper = parse_value(upper)
    lower_number = (
        parsed_lower.number
        if parsed_lower.value_type == "exact"
        else None
    )
    upper_number = (
        parsed_upper.number
        if parsed_upper.value_type == "exact"
        else None
    )
    if lower_number is not None and value.number < lower_number:
        return "below_range"
    if upper_number is not None and value.number > upper_number:
        return "above_range"
    if lower_number is not None or upper_number is not None:
        return "within_reported_range"
    return "unknown"


def _matched_identity(source: ObservationValue) -> dict[str, Any]:
    return {
        "subject_external_id": source.subject_external_id,
        "visit_key": source.visit_key,
        "analyte": source.analyte,
        "collected_on": (
            source.collected_on.isoformat() if source.collected_on else None
        ),
        "collected_time": (
            source.collected_at.isoformat() if source.collected_at else None
        ),
        "instance_type": source.instance_type,
        "specimen": source.specimen,
        "report_revision": source.report_revision,
    }


def compare_observation(
    source: ObservationValue,
    edc_records: list[EdcValue],
) -> ComparisonOutcome:
    identity = _matched_identity(source)
    if source.extraction_state == "user_skipped":
        return ComparisonOutcome(
            match_status="unmatched",
            result_status="not_checked_by_user",
            matched_identity=identity,
            candidate_record_ids=(),
            unknowns=("user_skipped",),
            reason="CRA 已选择本局部不核查；不计正常。",
        )
    if source.validation_state != "ready_for_match":
        return ComparisonOutcome(
            match_status="unmatched",
            result_status="not_comparable",
            matched_identity=identity,
            candidate_record_ids=(),
            unknowns=("source_needs_review",),
            reason="来源字段仍需人工核实，当前不执行自动比较。",
            field_results=tuple(
                FieldResult("extraction", "needs_review", detail=issue)
                for issue in source.issues
            ),
        )

    match_status, candidates, match_unknowns, reason = match_observation(
        source, edc_records
    )
    matched_identity = identity
    if match_status == "unmatched":
        result_status: ResultStatus = (
            "not_seen_in_export"
            if candidates == [] and "not_seen_in_export" in match_unknowns
            else "not_comparable"
        )
        return ComparisonOutcome(
            match_status=match_status,
            result_status=result_status,
            matched_identity=matched_identity,
            candidate_record_ids=(),
            unknowns=match_unknowns,
            reason=reason,
        )
    candidate_ids = tuple(item.id for item in candidates)
    if match_status == "ambiguous":
        return ComparisonOutcome(
            match_status=match_status,
            result_status="not_comparable",
            matched_identity=matched_identity,
            candidate_record_ids=candidate_ids,
            unknowns=match_unknowns,
            reason=reason,
        )

    candidate = candidates[0]
    field_results: list[FieldResult] = [
        FieldResult(
            "identity",
            "agreement",
            source=source.subject_external_id,
            edc=candidate.subject_external_id,
        ),
        FieldResult(
            "analyte",
            "agreement",
            source=source.analyte,
            edc=candidate.analyte,
        ),
        FieldResult(
            "collection",
            "agreement",
            source=source.collected_on.isoformat(),
            edc=candidate.collected_on.isoformat() if candidate.collected_on else None,
        ),
        FieldResult(
            "instance",
            "agreement",
            source=source.instance_type,
            edc=candidate.instance_type,
        ),
    ]
    if source.collected_at is not None and candidate.collected_at is not None:
        field_results.append(
            FieldResult(
                "collection_time",
                "agreement",
                source=source.collected_at.isoformat(),
                edc=candidate.collected_at.isoformat(),
            )
        )
    else:
        field_results.append(
            FieldResult(
                "collection_time",
                "unknown",
                source=source.collected_at.isoformat()
                if source.collected_at
                else None,
                edc=candidate.collected_at.isoformat()
                if candidate.collected_at
                else None,
                detail="仅按日期和实例匹配；没有臆造缺失时刻。",
            )
        )

    source_value = source.value
    edc_value = candidate.value
    source_unit = source.unit_normalized
    edc_unit = candidate.unit_normalized
    if not source_unit or not edc_unit:
        field_results.append(
            FieldResult(
                "unit",
                "unknown",
                source=source.unit,
                edc=candidate.unit,
                detail="任一侧缺失单位，未猜换算。",
            )
        )
        return ComparisonOutcome(
            match_status=match_status,
            result_status="unit_review",
            matched_identity=matched_identity,
            candidate_record_ids=candidate_ids,
            unknowns=("unit_missing",),
            reason="单位缺失或未知，数值未作自动换算。",
            field_results=tuple(field_results),
            edc_record_id=candidate.id,
        )
    if source_unit != edc_unit:
        field_results.append(
            FieldResult(
                "unit",
                "difference",
                source=source.unit,
                edc=candidate.unit,
                detail="单位不同且没有已批准转换。",
            )
        )
        return ComparisonOutcome(
            match_status=match_status,
            result_status="unit_review",
            matched_identity=matched_identity,
            candidate_record_ids=candidate_ids,
            unknowns=("unit_conversion_unapproved",),
            reason="单位不同，未猜测换算关系。",
            field_results=tuple(field_results),
            edc_record_id=candidate.id,
        )
    field_results.append(
        FieldResult(
            "unit",
            "agreement",
            source=source.unit,
            edc=candidate.unit,
        )
    )

    value_result_status: ResultStatus
    value_unknowns: tuple[str, ...] = match_unknowns
    if source_value.value_type == "unknown" or edc_value.value_type == "unknown":
        value_result_status = "unreadable"
        value_unknowns = ("value_unreadable",)
        field_results.append(
            FieldResult(
                "value",
                "unknown",
                source=source_value.raw,
                edc=edc_value.raw,
            )
        )
    elif source_value.value_type == "text" or edc_value.value_type == "text":
        value_result_status = "not_comparable"
        value_unknowns = ("text_value_mapping_unapproved",)
        field_results.append(
            FieldResult(
                "value",
                "unknown",
                source=source_value.raw,
                edc=edc_value.raw,
                detail="文本结果没有已批准的同义/阴阳性映射。",
            )
        )
    elif (
        source_value.value_type == "bound"
        or edc_value.value_type == "bound"
    ):
        if (
            source_value.value_type == "bound"
            and edc_value.value_type == "bound"
            and source_value.operator == edc_value.operator
            and source_value.number == edc_value.number
        ):
            value_result_status = "agreement"
            field_results.append(
                FieldResult(
                    "value",
                    "agreement",
                    source=source_value.raw,
                    edc=edc_value.raw,
                    detail="比较符和界限值均一致。",
                )
            )
        else:
            value_result_status = "not_comparable"
            value_unknowns = ("bound_value_requires_review",)
            field_results.append(
                FieldResult(
                    "value",
                    "unknown",
                    source=source_value.raw,
                    edc=edc_value.raw,
                    detail="带比较符的结果未转换为精确值。",
                )
            )
    else:
        equal = source_value.number == edc_value.number
        value_result_status = "agreement" if equal else "value_difference"
        field_results.append(
            FieldResult(
                "value",
                "agreement" if equal else "difference",
                source=source_value.raw,
                edc=edc_value.raw,
            )
        )

    source_flag = _reference_flag(
        source_value, source.lower_limit, source.upper_limit
    )
    edc_flag = _reference_flag(
        edc_value, candidate.lower_limit, candidate.upper_limit
    )
    range_status = "unknown"
    if source_flag != "unknown" and edc_flag != "unknown":
        range_status = (
            "agreement" if source_flag == edc_flag else "difference"
        )
    field_results.append(
        FieldResult(
            "reference_range_flag",
            range_status,
            source=source_flag,
            edc=edc_flag,
            detail="仅描述报告范围标记；医学安全和异常结论属于 M09。",
        )
    )
    if (
        value_result_status == "agreement"
        and range_status == "difference"
    ):
        value_result_status = "logic_difference"
        value_unknowns = (
            *value_unknowns,
            "reference_range_flag_difference",
        )
    return ComparisonOutcome(
        match_status=match_status,
        result_status=value_result_status,
        matched_identity=matched_identity,
        candidate_record_ids=candidate_ids,
        unknowns=value_unknowns,
        reason=(
            "数值及单位一致；仅限本次字段。"
            if value_result_status == "agreement"
            else (
                "数值不一致。"
                if value_result_status == "value_difference"
                else None
            )
        ),
        field_results=tuple(field_results),
        edc_record_id=candidate.id,
    )
