from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app


def test_w19_policy_api_exposes_baseline_and_migration_ledger(
    session_factory: sessionmaker[Session],
    app_database_url: str,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_mode="mock",
        environment="development",
        database_url=app_database_url,
        artifact_root=tmp_path / "artifacts",
        knowledge_staging_root=tmp_path / "staging",
        run_root=tmp_path / "runs",
    )
    app = create_app(
        database_checker=lambda: DependencyStatus(
            status="ready",
            detail="W19 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    session = client.post("/api/v1/system/local-session")
    assert session.status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w19-api-project"},
        json={
            "name": "W19 API策略项目",
            "scope": "验证不可变策略基线与迁移API。",
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    policy = client.get(f"/api/v1/projects/{project_id}/policy")
    assert policy.status_code == 200, policy.text
    body = policy.json()
    assert body["project_bundle"]["id"] == project.json()["policy_bundle_id"]
    assert body["active_bundle"]["id"] == project.json()["policy_bundle_id"]
    bundle_id = body["project_bundle"]["id"]

    published = client.post(f"/api/v1/projects/{project_id}/policy/publish")
    assert published.status_code == 201, published.text
    assert published.json()["id"] == bundle_id

    activated = client.post(
        f"/api/v1/projects/{project_id}/policy/activate",
        json={
            "bundle_id": bundle_id,
            "expected_revision": project.json()["revision"],
        },
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["project_bundle"]["id"] == bundle_id

    dry_run = client.post(
        f"/api/v1/projects/{project_id}/policy/migrations/dry-run",
        json={
            "target_bundle_id": bundle_id,
            "kind": "config",
            "schema_revision": None,
            "backup_ref": None,
            "expected_project_revision": project.json()["revision"],
        },
    )
    assert dry_run.status_code == 201, dry_run.text
    assert dry_run.json()["state"] == "dry_run_passed"
    operation_id = UUID(dry_run.json()["id"])
    applied = client.post(
        f"/api/v1/projects/{project_id}/policy/migrations/{operation_id}/apply"
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["state"] == "succeeded"

    final = client.get(f"/api/v1/projects/{project_id}/policy")
    assert final.status_code == 200
    assert any(item["id"] == str(operation_id) for item in final.json()["migrations"])
