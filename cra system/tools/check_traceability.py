"""Validate the CRA theory/technical baseline."""
import argparse
import os
from pathlib import Path
from traceability_lib import validate

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default=os.environ.get("CRA_BASE_SHA") or None)
    args = parser.parse_args()
    try:
        errors = validate(ROOT, args.base_ref)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("TRACEABILITY ERROR:", exc)
        return 1
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("PASS: theory, modules, tasks, scenarios, review fingerprints and generated views are synchronized.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
