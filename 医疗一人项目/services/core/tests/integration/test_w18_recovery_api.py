from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app


def test_w18_offline_trash_rebuild_backup_and_restore_api(
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
        backup_root=tmp_path / "backups",
        restore_root=tmp_path / "restores",
    )
    app = create_app(
        database_checker=lambda: DependencyStatus(
            status="ready",
            detail="W18 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w18-api-project"},
        json={"name": "W18 API恢复项目", "scope": "验证回收站和加密恢复。"},
    ).json()
    project_id = project["id"]
    content = "W18 API合成原件：犬模型疼痛评分下降。\n".encode()
    digest = hashlib.sha256(content).hexdigest()
    upload = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads",
        json={
            "filename": "w18-api-study.txt",
            "expected_bytes": len(content),
            "media_type_hint": "text/plain",
            "expected_sha256": digest,
        },
    )
    assert upload.status_code == 201, upload.text
    upload_id = upload.json()["session_id"]
    part = client.put(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{upload_id}/parts/0",
        content=content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Part-SHA256": digest,
        },
    )
    assert part.status_code == 200, part.text
    committed = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{upload_id}/commit"
    )
    assert committed.status_code == 200, committed.text
    version_id = committed.json()["version_id"]
    document_id = committed.json()["document_id"]

    rebuild = client.post(
        f"/api/v1/projects/{project_id}/recovery/versions/{version_id}/rebuild-index"
    )
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["rebuilt"] is True
    assert rebuild.json()["chunks"] >= 1

    trashed = client.post(
        f"/api/v1/projects/{project_id}/recovery/trash/{document_id}",
        json={"reason": "W18 API合成回收站测试"},
    )
    assert trashed.status_code == 201, trashed.text
    assert trashed.json()["state"] == "trashed"
    documents = client.get(f"/api/v1/projects/{project_id}/knowledge/documents")
    assert documents.status_code == 200
    assert documents.json() == []
    recovery = client.get(f"/api/v1/projects/{project_id}/recovery")
    assert recovery.status_code == 200, recovery.text
    assert recovery.json()["trash"][0]["document_id"] == document_id

    restored = client.post(
        f"/api/v1/projects/{project_id}/recovery/trash/{document_id}/restore"
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["state"] == "restored"
    documents = client.get(f"/api/v1/projects/{project_id}/knowledge/documents")
    assert [item["id"] for item in documents.json()] == [document_id]

    passphrase = "synthetic-W18-API-passphrase"
    backup = client.post(
        f"/api/v1/projects/{project_id}/recovery/backups",
        headers={"Idempotency-Key": "w18-api-backup"},
        json={"passphrase": passphrase},
    )
    assert backup.status_code == 201, backup.text
    assert backup.json()["state"] == "completed"
    assert backup.json()["manifest"]["counts"]["knowledge_document_versions"] == 1
    assert passphrase not in backup.text
    check = client.post(
        (
            f"/api/v1/projects/{project_id}/recovery/backups/"
            f"{backup.json()['id']}/restore-check"
        ),
        json={"passphrase": passphrase},
    )
    assert check.status_code == 201, check.text
    assert check.json()["state"] == "verified"
    assert check.json()["detail"]["active_database_overwritten"] is False

    capabilities = client.get("/api/v1/system/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["dependencies"]["network"]["status"] == "ready"
    assert "Offline mode" in capabilities.json()["dependencies"]["network"]["detail"]
    assert (
        capabilities.json()["dependencies"]["recovery"]["status"] == "ready"
    )
