"""W15 deployment prechecks and explicit authorized-trial blockers."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import check_deployment  # noqa: E402


def _production_env() -> dict[str, str]:
    return {
        "CRA_ENV": "production",
        "CRA_DATABASE_URL": (
            "postgresql+psycopg://cra:managed-password@postgres:5432/cra"
        ),
        "CRA_SESSION_SECRET": "x" * 48,
        "CRA_SESSION_COOKIE_SECURE": "true",
        "CRA_PUBLIC_BASE_URL": "https://cra.example.test",
        "CRA_OIDC_ISSUER": "https://id.example.test",
        "CRA_OIDC_CLIENT_ID": "cra-client",
        "CRA_OIDC_CLIENT_SECRET": "managed-client-secret",
        "CRA_STORAGE_BACKEND": "s3",
        "CRA_PRIVATE_STORAGE_ENDPOINT": "http://private-store:9000",
        "CRA_PRIVATE_STORAGE_ACCESS_KEY": "managed-access",
        "CRA_PRIVATE_STORAGE_SECRET_KEY": "managed-secret",
        "CRA_PRIVATE_STORAGE_BUCKET": "cra-private",
        "CRA_API_IMAGE": "registry.example.test/cra-api@sha256:" + "a" * 64,
        "CRA_WEB_IMAGE": "registry.example.test/cra-web@sha256:" + "b" * 64,
        "CRA_OCR_PROVIDER": "docling",
    }


def _trial_evidence() -> dict:
    return {
        "schema_version": 1,
        "status": "complete",
        "authorization": {
            "approved_use": True,
            "owner": "authorized-owner",
            "recorded_at": "2026-11-07",
        },
        "environment": {
            "oidc_login_tested": True,
            "tls_verified": True,
            "private_storage_verified": True,
            "center_isolation_verified": True,
        },
        "restore": {"status": "passed"},
        "trial": {
            "sessions": 1,
            "critical_errors": 0,
            "total_seconds": 600,
            "device_scope": ["desktop"],
        },
        "feedback": [
            {
                "theory_id": "CRA-R044",
                "module_id": "M14",
                "task_id": "CRA-W15",
                "classification": "presentation",
            }
        ],
    }


def test_runtime_compose_is_locked_and_does_not_publish_database():
    assert check_deployment.validate_compose(
        ROOT, ROOT / "deploy/compose.runtime.yml"
    ) == []


def test_ci_environment_is_explicitly_nonproduction():
    values = check_deployment.read_env_file(
        ROOT / "deploy/runtime.check.env"
    )
    assert values["CRA_ENV"] == "test"
    assert check_deployment.validate_environment(
        values, allow_nonproduction=True
    ) == []
    assert check_deployment.validate_environment(
        values, allow_nonproduction=False
    )


def test_approved_production_requires_tls_s3_and_digest_images():
    values = _production_env()
    assert check_deployment.validate_environment(
        values, allow_nonproduction=False
    ) == []
    changed = copy.deepcopy(values)
    changed["CRA_PUBLIC_BASE_URL"] = "http://cra.example.test"
    changed["CRA_STORAGE_BACKEND"] = "local"
    changed["CRA_API_IMAGE"] = "cra-api:latest"
    errors = check_deployment.validate_environment(
        changed, allow_nonproduction=False
    )
    assert any("HTTPS" in error for error in errors)
    assert any("S3" in error for error in errors)
    assert any("immutable sha256" in error for error in errors)


def test_synthetic_identity_and_template_secrets_are_not_production_ready():
    values = _production_env()
    values["CRA_ENV"] = "test"
    values["CRA_SESSION_SECRET"] = "CHANGE_ME"
    errors = check_deployment.validate_environment(
        values, allow_nonproduction=False
    )
    assert any("CRA_ENV=production" in error for error in errors)
    assert any("template marker" in error for error in errors)


def test_authorized_trial_cannot_be_claimed_without_real_evidence():
    assert check_deployment.validate_trial_evidence(_trial_evidence()) == []
    incomplete = copy.deepcopy(_trial_evidence())
    incomplete["trial"]["sessions"] = 0
    incomplete["restore"]["status"] = "not_run"
    errors = check_deployment.validate_trial_evidence(incomplete)
    assert any("restore exercise" in error for error in errors)
    assert any("real operation" in error for error in errors)


def test_current_trial_record_is_blocked_not_complete():
    assert (
        check_deployment.trial_record_status(
            ROOT, "validation/AUTHORIZED_TRIAL.md"
        )
        == "BLOCKED"
    )


def test_deployment_contract_contains_no_real_secret_values():
    text = (ROOT / "deploy/runtime.env.example").read_text(encoding="utf-8")
    assert "CHANGE_ME" in text
    assert "synthetic-only" not in text
    schema = json.loads(
        (ROOT / "deploy/env.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["CRA_ENV"]["const"] == "production"
    assert schema["properties"]["CRA_STORAGE_BACKEND"]["const"] == "s3"


@pytest.mark.parametrize(
    "classification",
    [
        "theory_change",
        "data_gap",
        "code_error",
        "presentation",
        "no_change",
    ],
)
def test_feedback_classifications_are_explicit(classification):
    evidence = _trial_evidence()
    evidence["feedback"][0]["classification"] = classification
    assert check_deployment.validate_trial_evidence(evidence) == []
