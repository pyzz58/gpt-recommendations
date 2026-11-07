from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values

CONFIG_PATH_ENV = "MEDICAL_ONE_CONFIG_FILE"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / ".env"


def resolve_config_path(
    value: str | Path | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> Path:
    raw = value if value is not None else os.getenv(CONFIG_PATH_ENV)
    if raw is None or str(raw).strip() == "":
        return (project_root / ".env").resolve()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def load_config_values(
    path: Path | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> tuple[Path, dict[str, str]]:
    resolved = resolve_config_path(path, project_root=project_root)
    if not resolved.exists():
        return resolved, {}
    parsed = dotenv_values(resolved, encoding="utf-8", interpolate=False)
    values: dict[str, str] = {}
    for key, value in parsed.items():
        if value is None:
            continue
        if not key.startswith("MEDICAL_ONE_") and key not in {
            "POSTGRES_APP_PASSWORD",
            "POSTGRES_MIGRATOR_PASSWORD",
            "NEXT_PUBLIC_API_BASE_URL",
        }:
            raise ValueError(f"Unsupported configuration key in {resolved}: {key}")
        values[key] = value
    return resolved, values


def environment_with_config_file(
    values: Mapping[str, str],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if environ is None else environ
    effective = {
        key: value
        for key, value in values.items()
        if key not in source
    }
    if CONFIG_PATH_ENV in source:
        effective[CONFIG_PATH_ENV] = source[CONFIG_PATH_ENV]
    return effective


def write_shell_exports(path: Path) -> None:
    resolved, values = load_config_values(path)
    effective = environment_with_config_file(values)
    effective[CONFIG_PATH_ENV] = str(resolved)
    for key, value in sorted(effective.items()):
        if "\0" in key or "\0" in value:
            raise ValueError("Configuration keys and values cannot contain NUL")
        sys.stdout.buffer.write(f"{key}={value}".encode() + b"\0")


def safe_summary(path: Path) -> dict[str, str | bool]:
    resolved, values = load_config_values(path)
    safe: dict[str, str | bool] = {
        "config_file": str(resolved),
        "config_file_exists": resolved.is_file(),
    }
    secret_fragments = (
        "PASSWORD",
        "TOKEN",
        "SECRET",
        "PRIVATE_KEY",
        "DATABASE_URL",
    )
    for key, value in sorted(values.items()):
        safe[key.lower()] = (
            "[redacted]"
            if key.endswith("KEY")
            or any(fragment in key for fragment in secret_fragments)
            else value
        )
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the project's single dotenv source")
    parser.add_argument("--path", type=Path, help="Explicit configuration file")
    parser.add_argument(
        "command",
        choices=["shell-export", "summary"],
        nargs="?",
        default="summary",
    )
    args = parser.parse_args()
    resolved = resolve_config_path(args.path)
    if args.command == "shell-export":
        write_shell_exports(resolved)
    else:
        print(json.dumps(safe_summary(resolved), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
