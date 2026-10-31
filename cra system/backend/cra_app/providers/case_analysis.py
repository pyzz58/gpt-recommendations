"""Replaceable, isolated local-model adapter for safety explanations."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class CaseModelResult:
    provider_name: str
    provider_version: str
    model_version: str | None
    status: str
    raw_output: str | None
    error: str | None = None
    elapsed_seconds: float | None = None
    max_rss_bytes: int | None = None


class CaseAnalysisProvider(Protocol):
    def analyze_batch(
        self, requests: list[dict[str, Any]]
    ) -> list[CaseModelResult]: ...


class DisabledCaseAnalysisProvider:
    name = "disabled"
    version = "1"

    def analyze_batch(
        self, requests: list[dict[str, Any]]
    ) -> list[CaseModelResult]:
        return [
            CaseModelResult(
                provider_name=self.name,
                provider_version=self.version,
                model_version=None,
                status="unavailable",
                raw_output=None,
                error="analysis provider is not configured",
            )
            for _ in requests
        ]


class LocalTransformersCaseAnalysisProvider:
    """Run the pinned open-weight model in an isolated Python 3.12 process."""

    name = "local-transformers"
    version = "1"
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision = "7ae557604adf67be50417f59c2c2f167def9a775"

    def __init__(
        self,
        *,
        enabled: bool,
        timeout_seconds: int = 1200,
        project_root: Path | None = None,
    ):
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.project_root = project_root or Path(__file__).resolve().parents[3]

    def analyze_batch(
        self, requests: list[dict[str, Any]]
    ) -> list[CaseModelResult]:
        if not self.enabled:
            return DisabledCaseAnalysisProvider().analyze_batch(requests)
        if not requests:
            return []
        uv = shutil.which("uv")
        if not uv:
            return [
                CaseModelResult(
                    provider_name=self.name,
                    provider_version=self.version,
                    model_version=self.model_id,
                    status="failed",
                    raw_output=None,
                    error="uv executable is required",
                )
                for _ in requests
            ]
        with tempfile.TemporaryDirectory(
            prefix="cra-case-provider-"
        ) as temporary:
            input_path = Path(temporary) / "requests.json"
            input_path.write_text(
                json.dumps(requests, ensure_ascii=False), encoding="utf-8"
            )
            command = [
                uv,
                "run",
                "--no-project",
                "--isolated",
                "--python",
                "3.12",
                "--with",
                "transformers==4.57.1",
                "--with",
                "torch==2.7.1",
                "--with",
                "safetensors==0.5.3",
                "python",
                "-m",
                "cra_app.providers.case_worker",
                "--input",
                str(input_path),
            ]
            environment = os.environ.copy()
            backend = str(self.project_root / "backend")
            environment["PYTHONPATH"] = backend + (
                os.pathsep + environment["PYTHONPATH"]
                if environment.get("PYTHONPATH")
                else ""
            )
            environment["TOKENIZERS_PARALLELISM"] = "false"
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.project_root,
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                return [
                    CaseModelResult(
                        provider_name=self.name,
                        provider_version=self.version,
                        model_version=self.model_id,
                        status="failed",
                        raw_output=None,
                        error="local analysis model timed out",
                    )
                    for _ in requests
                ]
            if completed.returncode != 0:
                error = (completed.stderr or completed.stdout)[-2000:]
                return [
                    CaseModelResult(
                        provider_name=self.name,
                        provider_version=self.version,
                        model_version=self.model_id,
                        status="failed",
                        raw_output=None,
                        error=error,
                    )
                    for _ in requests
                ]
            marker = "CRA_CASE_RESULT="
            payload = next(
                (
                    line[len(marker) :]
                    for line in reversed(completed.stdout.splitlines())
                    if line.startswith(marker)
                ),
                None,
            )
            if payload is None:
                return [
                    CaseModelResult(
                        provider_name=self.name,
                        provider_version=self.version,
                        model_version=self.model_id,
                        status="failed",
                        raw_output=None,
                        error="local analysis model returned no structured result",
                    )
                    for _ in requests
                ]
            try:
                results = json.loads(payload)
            except json.JSONDecodeError:
                return [
                    CaseModelResult(
                        provider_name=self.name,
                        provider_version=self.version,
                        model_version=self.model_id,
                        status="failed",
                        raw_output=None,
                        error="local analysis model returned invalid JSON envelope",
                    )
                    for _ in requests
                ]
        by_id = {str(item["case_id"]): item for item in results}
        output: list[CaseModelResult] = []
        for request in requests:
            raw_result = by_id.get(str(request["case_id"]))
            if raw_result is None:
                output.append(
                    CaseModelResult(
                        provider_name=self.name,
                        provider_version=self.version,
                        model_version=self.model_id,
                        status="failed",
                        raw_output=None,
                        error="result missing for case",
                    )
                )
                continue
            output.append(
                CaseModelResult(
                    provider_name=self.name,
                    provider_version=self.version,
                    model_version=(
                        f"{self.model_id}@{self.model_revision}"
                    ),
                    status="completed",
                    raw_output=str(raw_result.get("raw_output") or ""),
                    error=raw_result.get("error"),
                    elapsed_seconds=raw_result.get("elapsed_seconds"),
                    max_rss_bytes=raw_result.get("max_rss_bytes"),
                )
            )
        return output


def build_case_analysis_provider(
    provider_name: str, *, project_root: Path | None = None
) -> CaseAnalysisProvider:
    if provider_name.strip().lower() in {
        "local-qwen2.5-0.5b",
        "local-transformers",
    }:
        return LocalTransformersCaseAnalysisProvider(
            enabled=True, project_root=project_root
        )
    return DisabledCaseAnalysisProvider()
