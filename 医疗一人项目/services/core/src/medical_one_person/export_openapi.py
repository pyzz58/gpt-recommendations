from __future__ import annotations

import json
from pathlib import Path

from medical_one_person.main import app


def main() -> None:
    project_root = Path(__file__).resolve().parents[4]
    target = project_root / "schemas" / "openapi.v1.json"
    target.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(target)


if __name__ == "__main__":
    main()
