"""Read-only next work-package selector."""
import argparse
import json
from pathlib import Path
from execution_plan import next_task

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", choices=("v1a", "v1b", "deployment"), default="v1a")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / "plan/tasks.json").read_text(encoding="utf-8"))["tasks"]
    result = next_task(tasks, args.track)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
