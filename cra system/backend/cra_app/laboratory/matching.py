"""Exact laboratory identity and repeat-instance matching."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cra_app.laboratory.comparison import EdcValue, ObservationValue

MatchStatus = Literal["unique_validated", "ambiguous", "unmatched"]

_UNIT_ALIASES = {
    "g/l": "g/L",
    "mmol/l": "mmol/L",
    "umol/l": "umol/L",
    "µmol/l": "umol/L",
    "μmol/l": "umol/L",
    "u/l": "U/L",
    "iu/l": "IU/L",
}
_ANALYTE_ALIASES = {
    "hb": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "血红蛋白": "hemoglobin",
    "alt": "alanine aminotransferase",
    "丙氨酸氨基转移酶": "alanine aminotransferase",
    "glucose": "glucose",
    "葡萄糖": "glucose",
    "creatinine": "creatinine",
    "肌酐": "creatinine",
}


def normalized_text(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(value.strip().split())
    return collapsed or None


def normalized_key(value: str | None) -> str | None:
    cleaned = normalized_text(value)
    return cleaned.casefold() if cleaned else None


def normalize_unit(value: str | None) -> str | None:
    cleaned = normalized_text(value)
    if cleaned is None:
        return None
    key = cleaned.replace(" ", "").casefold()
    return _UNIT_ALIASES.get(key, cleaned)


def normalize_analyte(value: str | None) -> str | None:
    key = normalized_key(value)
    if key is None:
        return None
    return _ANALYTE_ALIASES.get(key, key)


def normalize_instance(value: str | None) -> str | None:
    key = normalized_key(value)
    if key is None:
        return None
    aliases = {
        "initial": "initial",
        "first": "initial",
        "初检": "initial",
        "首次": "initial",
        "首次检验": "initial",
        "repeat": "repeat",
        "retest": "repeat",
        "复查": "repeat",
        "复测": "repeat",
        "重测": "repeat",
    }
    return aliases.get(key, re.sub(r"\s+", "_", key))


def _candidate_matches(source: ObservationValue, edc: EdcValue) -> bool:
    if edc.identity_status != "mapped" or edc.subject_id is None:
        return False
    if normalized_key(source.subject_external_id) != normalized_key(
        edc.subject_external_id
    ):
        return False
    if normalize_analyte(source.analyte) != normalize_analyte(edc.analyte):
        return False
    if source.collected_on is None or source.collected_on != edc.collected_on:
        return False
    if normalize_instance(source.instance_type) != normalize_instance(
        edc.instance_type
    ):
        return False
    if (
        source.visit_key
        and edc.visit_key
        and normalized_key(source.visit_key) != normalized_key(edc.visit_key)
    ):
        return False
    if (
        source.specimen
        and edc.specimen
        and normalized_key(source.specimen) != normalized_key(edc.specimen)
    ):
        return False
    if source.collected_at is not None and edc.collected_at is not None:
        if source.collected_at.replace(tzinfo=None) != edc.collected_at.replace(
            tzinfo=None
        ):
            return False
    return True


def _missing_identity_keys(source: ObservationValue) -> list[str]:
    missing = []
    for name, value in (
        ("subject_external_id", source.subject_external_id),
        ("analyte", source.analyte),
        ("collected_on", source.collected_on),
        ("instance_type", source.instance_type),
    ):
        if value is None or value == "":
            missing.append(name)
    return missing


def match_observation(
    source: ObservationValue,
    edc_records: list[EdcValue],
) -> tuple[MatchStatus, list[EdcValue], tuple[str, ...], str | None]:
    missing = _missing_identity_keys(source)
    if missing:
        return (
            "unmatched",
            [],
            tuple(f"missing:{key}" for key in missing),
            "身份、项目、采样日或初检/复查实例不完整，未执行对象匹配。",
        )
    candidates = [
        record for record in edc_records if _candidate_matches(source, record)
    ]
    if not candidates:
        return (
            "unmatched",
            [],
            ("not_seen_in_export",),
            "本次导出未见相同身份与实例；不能据此推断 EDC 漏录。",
        )
    revision_mismatches = [
        record
        for record in candidates
        if source.report_revision
        and record.report_revision
        and normalized_key(source.report_revision)
        != normalized_key(record.report_revision)
    ]
    if len(revision_mismatches) == len(candidates):
        return (
            "unmatched",
            [],
            ("report_revision_mismatch",),
            "同一对象存在报告修订差异，未把不同修订自动当作同一比较实例。",
        )
    if revision_mismatches:
        candidates = [
            record for record in candidates if record not in revision_mismatches
        ]
    revision_unknown = len(candidates) > 1 and any(
        source.report_revision is None or candidate.report_revision is None
        for candidate in candidates
    )
    if len(candidates) > 1:
        unknowns = ["multiple_edc_candidates"]
        if revision_unknown:
            unknowns.append("report_revision_unconfirmed")
        return (
            "ambiguous",
            candidates,
            tuple(unknowns),
            "存在多个同样符合条件的实例，未按数值接近度自动挑选。",
        )
    candidate = candidates[0]
    if candidate.validation_status != "ready_for_match":
        return (
            "unmatched",
            candidates,
            ("edc_candidate_needs_review",),
            "EDC 候选仍有来源或身份校验缺口。",
        )
    unknowns = (
        ("report_revision_missing_in_export",)
        if source.report_revision and candidate.report_revision is None
        else ()
    )
    return "unique_validated", candidates, unknowns, None
