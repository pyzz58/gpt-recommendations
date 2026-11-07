"""Check the CRA runtime candidate and authorized-trial evidence boundary.

Passing the static/deployment checks does not prove that an approved
environment, real clinical data or an authorized trial exists.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE = "deploy/compose.runtime.yml"
DEFAULT_SCHEMA = "deploy/env.schema.json"
DEFAULT_TRIAL_RECORD = "validation/AUTHORIZED_TRIAL.md"

PLACEHOLDERS = {"", "change_me", "changeme", "replace_me", "example"}


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"invalid environment assignment: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"invalid environment key: {key}")
        values[key] = value.strip()
    return values


def _redacted(value: str) -> str:
    if not value:
        return value
    parsed = urlsplit(value)
    if parsed.password:
        netloc = parsed.netloc.replace(parsed.password, "***")
        return parsed._replace(netloc=netloc).geturl()
    return value


def validate_environment(
    values: dict[str, str],
    *,
    allow_nonproduction: bool,
) -> list[str]:
    required = {
        "CRA_ENV",
        "CRA_DATABASE_URL",
        "CRA_SESSION_SECRET",
        "CRA_PUBLIC_BASE_URL",
        "CRA_OIDC_ISSUER",
        "CRA_OIDC_CLIENT_ID",
        "CRA_OIDC_CLIENT_SECRET",
        "CRA_STORAGE_BACKEND",
    }
    errors = [
        f"environment: missing {key}" for key in sorted(required - values.keys())
    ]
    if errors:
        return errors
    if values["CRA_ENV"] != "production" and not allow_nonproduction:
        errors.append("environment: approved deployment must use CRA_ENV=production")
    for key, value in values.items():
        if "CHANGE_ME" in value.upper():
            errors.append(f"environment: {key} still contains a template marker")
    if len(values["CRA_SESSION_SECRET"]) < 32:
        errors.append("environment: CRA_SESSION_SECRET must be at least 32 characters")
    if values.get("CRA_SESSION_COOKIE_SECURE", "true") != "true":
        errors.append("environment: CRA_SESSION_COOKIE_SECURE must be true")

    database_url = values["CRA_DATABASE_URL"]
    if not database_url.startswith("postgresql+psycopg://"):
        errors.append("environment: CRA_DATABASE_URL must use postgresql+psycopg")
    if values["CRA_ENV"] == "production":
        for key in ("CRA_PUBLIC_BASE_URL", "CRA_OIDC_ISSUER"):
            if urlsplit(values[key]).scheme != "https":
                errors.append(f"environment: {key} must use HTTPS")
        if values["CRA_STORAGE_BACKEND"] != "s3":
            errors.append(
                "environment: approved production must use private S3 storage"
            )
        for key in (
            "CRA_PRIVATE_STORAGE_ENDPOINT",
            "CRA_PRIVATE_STORAGE_ACCESS_KEY",
            "CRA_PRIVATE_STORAGE_SECRET_KEY",
            "CRA_PRIVATE_STORAGE_BUCKET",
        ):
            if not values.get(key):
                errors.append(f"environment: missing {key}")
        for key in ("CRA_API_IMAGE", "CRA_WEB_IMAGE"):
            if not re.search(r"@sha256:[0-9a-f]{64}$", values.get(key, "")):
                errors.append(
                    f"environment: {key} must use an immutable sha256 digest"
                )
    return errors


def validate_trial_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("trial evidence schema_version must be 1")
    if payload.get("status") != "complete":
        errors.append("trial evidence status must be complete")
    approval = payload.get("authorization")
    if not isinstance(approval, dict):
        errors.append("trial evidence authorization is required")
    else:
        if approval.get("approved_use") is not True:
            errors.append("trial evidence requires an approved use")
        if not approval.get("owner") or not approval.get("recorded_at"):
            errors.append("trial evidence authorization needs owner and date")
    environment = payload.get("environment")
    if not isinstance(environment, dict):
        errors.append("trial evidence environment is required")
    else:
        if environment.get("oidc_login_tested") is not True:
            errors.append("trial environment needs tested OIDC login")
        if environment.get("tls_verified") is not True:
            errors.append("trial environment needs verified TLS")
        if environment.get("private_storage_verified") is not True:
            errors.append("trial environment needs verified private storage")
        if environment.get("center_isolation_verified") is not True:
            errors.append("trial environment needs center-isolation evidence")
    restore = payload.get("restore")
    if not isinstance(restore, dict) or restore.get("status") != "passed":
        errors.append("trial evidence requires a passed restore exercise")
    trial = payload.get("trial")
    if not isinstance(trial, dict):
        errors.append("trial evidence operation record is required")
    else:
        if trial.get("sessions", 0) < 1:
            errors.append("trial evidence requires at least one real operation")
        if trial.get("critical_errors") is None:
            errors.append("trial evidence must record critical errors")
        if trial.get("total_seconds") is None:
            errors.append("trial evidence must record actual total time")
        if not isinstance(trial.get("device_scope"), list) or not trial[
            "device_scope"
        ]:
            errors.append("trial evidence must record tested device scope")
    feedback = payload.get("feedback")
    if not isinstance(feedback, list):
        errors.append("trial evidence feedback array is required")
    else:
        for index, item in enumerate(feedback):
            if not isinstance(item, dict):
                errors.append(f"feedback[{index}] must be an object")
                continue
            if not item.get("theory_id") or not item.get("module_id") or not item.get(
                "task_id"
            ):
                errors.append(
                    f"feedback[{index}] needs theory_id, module_id and task_id"
                )
            if item.get("classification") not in {
                "theory_change",
                "data_gap",
                "code_error",
                "presentation",
                "no_change",
            }:
                errors.append(f"feedback[{index}] has an invalid classification")
    return errors


def validate_compose(root: Path, compose_path: Path) -> list[str]:
    errors: list[str] = []
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    if compose.get("name") != "cra-runtime":
        errors.append("compose: name must be cra-runtime")
    services = compose.get("services")
    required = {"postgres", "migrate", "api", "worker", "web"}
    if not isinstance(services, dict) or set(services) != required:
        return errors + ["compose: expected postgres, migrate, api, worker and web"]
    postgres = services["postgres"]
    if "@sha256:" not in str(postgres.get("image", "")):
        errors.append("compose: PostgreSQL image must be digest-pinned")
    if postgres.get("ports"):
        errors.append("compose: PostgreSQL must not publish a host port")
    for name in ("migrate", "api", "worker", "web"):
        service = services[name]
        if service.get("privileged"):
            errors.append(f"compose: {name} must not be privileged")
        if service.get("read_only") is not True:
            errors.append(f"compose: {name} must use a read-only root filesystem")
        if "no-new-privileges:true" not in service.get("security_opt", []):
            errors.append(f"compose: {name} must set no-new-privileges")
    if not any(
        network.get("internal") is True
        for network in compose.get("networks", {}).values()
        if isinstance(network, dict)
    ):
        errors.append("compose: private backend network must be internal")
    web_ports = services["web"].get("ports", [])
    if not web_ports or "127.0.0.1:8080" not in str(web_ports[0]):
        errors.append("compose: web must bind to loopback by default")
    environment = services["api"].get("environment", {})
    if environment.get("CRA_ANALYSIS_PROVIDER") != "disabled":
        errors.append("compose: unapproved analysis providers must stay disabled")
    if environment.get("CRA_MODEL_PROVIDER") != "disabled":
        errors.append("compose: unapproved model providers must stay disabled")
    for relative in (
        "deploy/api.Dockerfile",
        "deploy/web.Dockerfile",
        "deploy/nginx.runtime.conf",
        "deploy/RUNBOOK.md",
        "deploy/restore-check.md",
    ):
        if not (root / relative).is_file():
            errors.append(f"deploy: missing {relative}")
    return errors


def trial_record_status(root: Path, relative: str) -> str:
    text = (root / relative).read_text(encoding="utf-8")
    match = re.search(r"^状态：(BLOCKED|COMPLETE)$", text, re.MULTILINE)
    if not match:
        raise ValueError("trial record must declare 状态：BLOCKED or 状态：COMPLETE")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--compose", default=DEFAULT_COMPOSE)
    parser.add_argument("--env-file")
    parser.add_argument("--allow-nonproduction", action="store_true")
    parser.add_argument("--trial-record", default=DEFAULT_TRIAL_RECORD)
    parser.add_argument("--trial-evidence")
    args = parser.parse_args()
    errors = validate_compose(ROOT, ROOT / args.compose)
    environment_summary: dict[str, Any] = {"checked": False}
    if args.env_file:
        values = read_env_file(ROOT / args.env_file)
        errors.extend(
            validate_environment(
                values, allow_nonproduction=args.allow_nonproduction
            )
        )
        environment_summary = {
            "checked": True,
            "environment": values.get("CRA_ENV"),
            "database_url": _redacted(values.get("CRA_DATABASE_URL", "")),
            "storage_backend": values.get("CRA_STORAGE_BACKEND"),
            "ocr_provider": values.get("CRA_OCR_PROVIDER", "disabled"),
        }
    status = trial_record_status(ROOT, args.trial_record)
    trial_errors: list[str] = []
    if args.trial_evidence:
        payload = json.loads((ROOT / args.trial_evidence).read_text(encoding="utf-8"))
        trial_errors = validate_trial_evidence(payload)
    blocked_reasons = [
        "approved deployment account and OIDC tenant are not configured",
        "approved private object storage and model/OCR runtime are not present",
        "backup has not been restored in an approved isolated environment",
        "no authorized real CRA operation, device test or timing record exists",
    ]
    payload = {
        "schema_version": 1,
        "deployment_candidate_checked": not errors,
        "environment": environment_summary,
        "authorized_trial_record_status": status,
        "authorized_trial_ready": (
            status == "COMPLETE" and not trial_errors
        ),
        "blocked_reasons": blocked_reasons if status == "BLOCKED" else [],
        "trial_evidence_errors": trial_errors,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.check and errors:
        return 1
    if args.trial_evidence and trial_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
