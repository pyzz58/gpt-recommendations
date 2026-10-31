"""Validate model explanations against registered facts, rules and outputs."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[./:-]\d+)*(?![A-Za-z])")
_BANNED_CONCLUSION = re.compile(
    r"\b(?:confirmed|definitive|diagnosis|diagnosed|caused by|proves|"
    r"clinical(?:ly)? safe|patient is safe|no adverse event|"
    r"definitely related|meets (?:the )?(?:sae|serious|severity|grade)|"
    r"meets .*\b(?:sae|seriousness|severity)\b|"
    r"classified as (?:a )?(?:serious|sae)|rules out)\b|"
    r"(?:已确认|确诊|诊断明确|肯定相关|因果关系成立|患者安全|"
    r"临床安全|无不良事件|无AE|满足SAE|符合严重性)",
    re.IGNORECASE,
)

EXPLANATION_TEMPLATES = {
    "candidate_review": (
        "The server-generated candidates require targeted CRA and "
        "investigator or medical review; this explanation does not make a "
        "medical or safety conclusion."
    ),
    "unknown_clarification": (
        "The server has retained unknown safety information and generated "
        "targeted clarification questions; no medical conclusion is made."
    ),
    "candidate_and_unknown_review": (
        "The server-generated candidates and unknown safety information "
        "require targeted CRA and investigator or medical review; no final "
        "medical conclusion is made."
    ),
    "general_review": (
        "The safety assessment remains subject to CRA and investigator or "
        "medical review; no medical conclusion is made."
    ),
}


@dataclass(frozen=True)
class GroundedExplanation:
    accepted: bool
    explanation: str | None
    evidence_ids: tuple[str, ...]
    errors: tuple[str, ...]


def _json_object(raw: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def validate_model_explanation(
    raw: str,
    *,
    allowed_evidence_ids: set[str],
    allowed_explanation_codes: set[str] | None = None,
) -> GroundedExplanation:
    payload = _json_object(raw)
    if payload is None:
        return GroundedExplanation(
            accepted=False,
            explanation=None,
            evidence_ids=(),
            errors=("provider_output_not_json_object",),
        )
    explanation_code = payload.get("explanation_code")
    evidence_ids = payload.get("evidence_ids")
    errors: list[str] = []
    if not isinstance(evidence_ids, list) or not evidence_ids or not all(
        isinstance(item, str) for item in evidence_ids
    ):
        errors.append("evidence_ids_missing_or_invalid")
        evidence_ids = []
    else:
        unknown = sorted(set(evidence_ids) - allowed_evidence_ids)
        if unknown:
            errors.append("unknown_evidence_ids:" + ",".join(unknown[:8]))

    explanation: str | None = None
    if explanation_code is not None:
        if set(payload) != {"explanation_code", "evidence_ids"}:
            errors.append("unexpected_output_keys")
        effective_codes = allowed_explanation_codes or set(
            EXPLANATION_TEMPLATES
        )
        if (
            not isinstance(explanation_code, str)
            or explanation_code not in effective_codes
            or explanation_code not in EXPLANATION_TEMPLATES
        ):
            errors.append("explanation_code_not_allowed")
        else:
            explanation = EXPLANATION_TEMPLATES[explanation_code]
    else:
        explanation = payload.get("explanation")
        if not isinstance(explanation, str) or len(explanation.strip()) < 20:
            errors.append("explanation_missing_or_too_short")
            explanation = None
        if explanation is not None:
            if len(explanation) > 800:
                errors.append("explanation_too_long")
            if _NUMBER.search(explanation):
                errors.append("unsupported_numeric_token")
            if _BANNED_CONCLUSION.search(explanation):
                errors.append("medical_or_safety_conclusion_outside_boundary")
            if not re.search(
                r"candidate|clarif|review|verif|uncertain|unknown|"
                r"候选|核实|复核|澄清|未知|待确认",
                explanation,
                re.IGNORECASE,
            ):
                errors.append("explanation_not_review_oriented")
    return GroundedExplanation(
        accepted=not errors,
        explanation=explanation if not errors else None,
        evidence_ids=tuple(dict.fromkeys(evidence_ids)) if not errors else (),
        errors=tuple(errors),
    )
