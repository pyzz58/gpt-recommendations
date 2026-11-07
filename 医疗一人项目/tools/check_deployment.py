#!/usr/bin/env python3
"""Static safety checks for the W23 deployment package; no Docker runtime is inferred."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_RUNTIME_FILES = (
    "最高思想.md",
    "技术路线与实施路径.md",
    "traceability/manifest.json",
    "config/agents/roles.yaml",
    "config/skills/catalog.yaml",
    "config/source_policies/catalog.yaml",
    "config/workflows/catalog.yaml",
    "config/templates/catalog.yaml",
    "fixtures/w17-audit-cases.json",
    "schemas/openapi.v1.json",
    "services/core/requirements.lock",
    "services/core/Dockerfile",
    "apps/web/Dockerfile",
    "deploy/compose.yaml",
    "scripts/medical-one.sh",
)

REQUIRED_COMPONENT_ENV = (
    ("workflow", "MEDICAL_ONE_WORKFLOW_CATALOG_PATH", "/app/config/workflows/catalog.yaml"),
    ("template", "MEDICAL_ONE_EXPORT_TEMPLATE_PATH", "/app/config/templates/catalog.yaml"),
    ("audit fixture", "MEDICAL_ONE_AUDIT_FIXTURE_PATH", "/app/fixtures/w17-audit-cases.json"),
    ("backup", "MEDICAL_ONE_BACKUP_ROOT", "/var/lib/medical-one/backups"),
    ("restore", "MEDICAL_ONE_RESTORE_ROOT", "/var/lib/medical-one/restore-checks"),
)

REQUIRED_DOCKER_COPIES = (
    "COPY --chown=app:app config /app/config",
    "COPY --chown=app:app schemas /app/schemas",
    "COPY --chown=app:app traceability/manifest.json /app/traceability/manifest.json",
    "COPY --chown=app:app fixtures/w17-audit-cases.json /app/fixtures/w17-audit-cases.json",
    "COPY --chown=app:app 技术路线与实施路径.md /app/技术路线与实施路径.md",
)


def validate(root: Path = DEFAULT_ROOT) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_RUNTIME_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing runtime file: {relative}")

    compose_path = root / "deploy" / "compose.yaml"
    core_dockerfile = root / "services" / "core" / "Dockerfile"
    if not compose_path.is_file() or not core_dockerfile.is_file():
        return errors
    compose: dict[str, Any] = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = compose.get("services", {})
    expected_services = {"postgres", "migrate", "api", "worker", "web"}
    if set(services) != expected_services:
        errors.append(
            "compose services differ: expected "
            + ", ".join(sorted(expected_services))
            + "; got "
            + ", ".join(sorted(services))
        )
        return errors

    postgres = services["postgres"]
    healthcheck = " ".join(postgres.get("healthcheck", {}).get("test", []))
    if "medical_one_migrator" not in healthcheck:
        errors.append("PostgreSQL healthcheck does not use the configured admin role")
    if "medical_one -d medical_one" in healthcheck:
        errors.append("PostgreSQL healthcheck uses the removed generic medical_one role")

    volumes = compose.get("volumes", {})
    for volume in ("backups", "restore-checks"):
        if volume not in volumes:
            errors.append(f"compose named volume is missing: {volume}")

    for service_name in ("api", "worker"):
        service = services[service_name]
        environment = service.get("environment", {})
        for label, key, expected in REQUIRED_COMPONENT_ENV:
            if environment.get(key) != expected:
                errors.append(
                    f"{service_name} {label} path must be {expected}"
                )
        mounts = {
            str(item).split(":", 1)[0]
            for item in service.get("volumes", [])
        }
        for volume in ("backups", "restore-checks"):
            if volume not in mounts:
                errors.append(f"{service_name} does not persist the {volume} volume")

    for service_name in ("migrate", "api", "worker"):
        image = services[service_name].get("image", "")
        if not image.endswith(":w23"):
            errors.append(f"{service_name} image tag is not W23-specific")
    if not services["web"].get("image", "").endswith(":w23"):
        errors.append("web image tag is not W23-specific")

    for service in services.values():
        for port in service.get("ports", []):
            if not str(port).startswith("127.0.0.1:"):
                errors.append(f"published port is not loopback-only: {port}")

    dockerfile = core_dockerfile.read_text(encoding="utf-8")
    for expected in REQUIRED_DOCKER_COPIES:
        if expected not in dockerfile:
            errors.append(f"core Dockerfile missing runtime copy: {expected}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    for error in errors:
        print("FAIL:", error)
    if errors:
        raise SystemExit(1)
    print(
        "PASS: deployment files contain the W23 runtime payload and loopback "
        "Compose structure; Docker execution is not implied."
    )


if __name__ == "__main__":
    main()
