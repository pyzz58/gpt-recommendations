#!/usr/bin/env python3
"""Validate W24 pilot coverage declarations without external actions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from medical_one_person.domain.phase_validation import (
    PilotReadinessInput,
    evaluate_pilot_readiness,
)

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "fixtures" / "w24-pilot-baseline.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    raw = json.loads(args.input.read_text(encoding="utf-8"))
    report = evaluate_pilot_readiness(PilotReadinessInput.model_validate(raw))
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
