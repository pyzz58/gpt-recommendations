"""Generate or verify the FastAPI OpenAPI contract."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# OpenAPI generation must not require a live database. A syntactically valid
# synthetic URL is supplied so importing the app never opens a connection.
os.environ.setdefault("CRA_ENV", "synthetic")
os.environ.setdefault(
    "CRA_DATABASE_URL",
    "postgresql+psycopg://synthetic:not-used@127.0.0.1:5432/cra_openapi",
)

from cra_app.main import app  # noqa: E402

CONTRACT_PATH = PROJECT_ROOT / "contracts" / "openapi.json"


def rendered_contract() -> str:
    schema = app.openapi()
    return json.dumps(
        schema,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = rendered_contract()
    if args.write:
        CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONTRACT_PATH.write_text(expected, encoding="utf-8")
        print(f"WROTE {CONTRACT_PATH.relative_to(PROJECT_ROOT)}")
        return 0
    if not CONTRACT_PATH.exists():
        print("OpenAPI contract is missing", file=sys.stderr)
        return 1
    actual = CONTRACT_PATH.read_text(encoding="utf-8")
    if actual != expected:
        print(
            "OpenAPI contract is stale; run tools/export_openapi.py --write",
            file=sys.stderr,
        )
        return 1
    print("OpenAPI contract is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
