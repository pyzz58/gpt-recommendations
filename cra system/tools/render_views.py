"""Render readable views from the versioned JSON source; never silently change requirements."""
import argparse
from pathlib import Path
from traceability_lib import render_views

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    changed = 0
    for relative, text in render_views(root).items():
        path = root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            changed += 1
            print(("WRITE " if args.write else "STALE ") + relative)
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    return 0 if args.write or not changed else 1

if __name__ == "__main__":
    raise SystemExit(main())
