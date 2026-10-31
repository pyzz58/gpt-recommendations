"""Evaluate the actual anchored rule extractor on an independent synthetic set."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from cra_app.documents.parsers import DocxSourceParser, TextSourceParser
from cra_app.providers.rule_extraction import (
    AnchoredRuleExtractor,
    evaluate_extraction_cases,
    validate_candidate_semantics,
)
from cra_app.rules.contracts import RuleNode


def _parser_for(filename: str):
    if filename.endswith(".txt"):
        return TextSourceParser()
    return DocxSourceParser()


def evaluate(manifest_path: Path) -> dict[str, Any]:
    fixture_root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = next(
        (
            item
            for item in manifest["artifacts"]
            if item["artifact_id"] == "RULE-DOCX-EVAL"
        ),
        None,
    )
    if artifact is None:
        raise ValueError("RULE-DOCX-EVAL is missing from the fixture manifest")
    path = fixture_root / artifact["file"]
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != artifact["sha256"]:
        raise ValueError("evaluation fixture hash does not match the manifest")
    parser = _parser_for(path.name)
    parsed = parser.parse(
        content,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename=path.name,
    )
    result = AnchoredRuleExtractor().extract_rules(anchors=list(parsed.anchors))
    expected = artifact["expected"]
    actual_keys = sorted(rule.node_key for rule in result.rules)
    if actual_keys != sorted(expected["rule_keys"]):
        raise AssertionError(
            f"independent rule keys differ: expected {expected['rule_keys']}, "
            f"got {actual_keys}"
        )
    cases_path = fixture_root / expected["evaluation_cases"]
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    summary = evaluate_extraction_cases(result, cases)
    if not summary["passed"]:
        raise AssertionError("; ".join(summary["failures"]))

    by_key = {rule.node_key: rule for rule in result.rules}
    safety = by_key["R-SAFETY-01"]
    source = "\n".join(ref.quote for ref in safety.source_refs)
    corruption_checks = {
        "lost_exception": bool(
            validate_candidate_semantics(
                safety.model_copy(update={"exceptions": []}), source
            )
        ),
        "lost_negation": bool(
            validate_candidate_semantics(
                safety.model_copy(
                    update={
                        "summary": (
                            "Investigators may record relatedness without a "
                            "documented rationale."
                        )
                    }
                ),
                source,
            )
        ),
        "and_changed_to_or": bool(
            validate_candidate_semantics(
                by_key["R-LAB-01"].model_copy(
                    update={
                        "trigger": by_key["R-LAB-01"].trigger.model_copy(
                            update={"op": "any"}
                        )
                        if by_key["R-LAB-01"].trigger
                        else None
                    }
                ),
                "\n".join(
                    ref.quote for ref in by_key["R-LAB-01"].source_refs
                ),
            )
        ),
    }
    return {
        **summary,
        "artifact_id": artifact["artifact_id"],
        "artifact_sha256": digest,
        "parser": parsed.parser_name,
        "parser_status": parsed.status,
        "evaluation_group": artifact["group"],
        "corruption_checks": corruption_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to the synthetic fixture manifest",
    )
    args = parser.parse_args()
    try:
        result = evaluate(args.dataset)
        if not all(result["corruption_checks"].values()):
            raise AssertionError("semantic corruption checks did not all pass")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
