"""Run isolated, synthetic-only feasibility probes for OCR candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_TOKENS = ("SYNTH-Hb", "121", "g/L")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _artifact_path(root: Path) -> Path:
    overridden = os.environ.get("CRA_PROBE_IMAGE")
    if overridden:
        return Path(overridden).resolve()
    return (
        root
        / "tests/fixtures/documents/artifacts/synthetic_lab_report.png"
    )


def _run_candidate(
    *,
    root: Path,
    engine: str,
    image: Path,
) -> dict:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv executable is required for isolated provider probe")
    packages = {
        "paddleocr": ["paddleocr==3.7.0", "paddlepaddle==3.3.1"],
        "docling": ["docling==2.145.0"],
    }[engine]
    command = [
        uv,
        "run",
        "--no-project",
        "--isolated",
        "--python",
        "3.12",
    ]
    for package in packages:
        command.extend(["--with", package])
    command.extend(
        [
            "python",
            "-m",
            "cra_app.providers.probe_worker",
            "--engine",
            engine,
            "--image",
            str(image),
        ]
    )
    environment = os.environ.copy()
    backend = str(root / "backend")
    environment["PYTHONPATH"] = backend + (
        os.pathsep + environment["PYTHONPATH"]
        if environment.get("PYTHONPATH")
        else ""
    )
    environment.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=1200,
    )
    if completed.returncode != 0:
        return {
            "engine": engine,
            "status": "failed",
            "returncode": completed.returncode,
            "error": (completed.stderr or completed.stdout)[-2000:],
        }
    marker = "CRA_PROBE_RESULT="
    payload = next(
        (
            line[len(marker) :]
            for line in reversed(completed.stdout.splitlines())
            if line.startswith(marker)
        ),
        None,
    )
    if payload is None:
        return {
            "engine": engine,
            "status": "failed",
            "error": "candidate process did not return structured output",
        }
    result = json.loads(payload)
    joined = "\n".join(result.get("tokens", [])) + "\n" + result.get(
        "markdown", ""
    )
    matched = [token for token in EXPECTED_TOKENS if token in joined]
    result.update(
        {
            "status": "passed" if len(matched) == len(EXPECTED_TOKENS) else "failed",
            "expected_tokens": list(EXPECTED_TOKENS),
            "matched_tokens": matched,
            "coordinate_count": len(result.get("boxes", [])),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.parse_args()
    root = _project_root()
    image = _artifact_path(root)
    if not image.is_file():
        print(f"Synthetic probe image is missing: {image}", file=sys.stderr)
        return 2
    if "synthetic" not in image.read_text(errors="ignore") and "synthetic" not in str(
        image
    ).lower():
        print("Probe input path is not marked synthetic", file=sys.stderr)
        return 2
    results = [
        _run_candidate(root=root, engine=engine, image=image)
        for engine in ("paddleocr", "docling")
    ]
    successful = [
        result
        for result in results
        if result.get("status") == "passed" and result.get("coordinate_count", 0) > 0
    ]
    selected = (
        min(successful, key=lambda item: item["elapsed_seconds"])
        if successful
        else None
    )
    report = {
        "input": image.relative_to(root).as_posix(),
        "input_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "source": "pure_synthetic",
        "python": "3.12",
        "results": results,
        "selected": selected["engine"] if selected else None,
        "selection_basis": (
            "expected token coverage plus coordinates, then lower first-run latency"
        ),
        "clinical_validation": False,
        "limitations": [
            "One synthetic image cannot establish format coverage or clinical accuracy.",
            "Numeric, unit, row/column, date and identity matching remain W08 work.",
            "Model downloads occur from official sources and need mirror/offline approval "
            "for an isolated provider runtime.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
