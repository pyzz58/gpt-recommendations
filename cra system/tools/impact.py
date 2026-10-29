"""List direct and dependent module candidates for a requirement update."""
import argparse
import json
from pathlib import Path
from traceability_lib import fingerprint, read_json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("requirement_ids", nargs="+")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reqs = {r["id"]: r for r in read_json(root, "theory/requirements.json")["requirements"]}
    modules = read_json(root, "traceability/modules.json")["modules"]
    missing = set(args.requirement_ids) - set(reqs)
    if missing:
        parser.error("unknown requirement IDs: " + ", ".join(sorted(missing)))
    direct = {mid for rid in args.requirement_ids for mid in reqs[rid]["modules"]}
    affected = set(direct)
    while True:
        expanded = affected | {m["id"] for m in modules if set(m["depends_on"]) & affected}
        if expanded == affected:
            break
        affected = expanded
    print(json.dumps({
        "direct_review_modules": sorted(direct),
        "dependent_review_candidates": sorted(affected - direct),
        "requirement_fingerprints": {rid: fingerprint(reqs[rid]) for rid in args.requirement_ids},
        "note": "Dependencies are review candidates, not an instruction to rewrite every module. Document actual impact."
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
