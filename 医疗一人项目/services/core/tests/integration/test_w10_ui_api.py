from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from medical_one_person.api.session import SESSION_COOKIE_NAME
from medical_one_person.application.tasks import TaskService
from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _client(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
) -> TestClient:
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
            detail="integration test",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    return TestClient(app, base_url="http://127.0.0.1:3000")


def test_local_session_project_overview_opportunity_and_events(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    client = _client(session_factory, app_database_url, tmp_path)

    unauthorized = client.get("/api/v1/projects")
    assert unauthorized.status_code == 401

    blocked_origin = client.post(
        "/api/v1/system/local-session",
        headers={"Origin": "https://untrusted.example"},
    )
    assert blocked_origin.status_code == 403

    session_response = client.post("/api/v1/system/local-session")
    assert session_response.status_code == 200
    assert SESSION_COOKIE_NAME in session_response.cookies
    set_cookie = session_response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert session_response.json()["display_name"] == "发起人"

    created = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w10-project"},
        json={
            "name": "W10 页面集成项目",
            "scope": "验证本地会话、项目读取、岗位卡片和机会选择，不执行外部动作。",
        },
    )
    assert created.status_code == 201, created.text
    project = created.json()
    project_id = project["id"]

    listing = client.get("/api/v1/projects")
    assert listing.status_code == 200
    assert listing.json()[0]["project"]["id"] == project_id

    task_service = TaskService(session_factory)
    task = task_service.create_task(
        project_id=project_id,
        actor_user_id=session_response.json()["user_id"],
        task_type="evidence.review",
        purpose="w10-api",
        assignee_role="A26",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:synthetic"],
        goal="检查合成资料，不得声称真实科学结论。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
    )
    newer_task = task_service.create_task(
        project_id=project_id,
        actor_user_id=session_response.json()["user_id"],
        task_type="independent_audit",
        purpose="w10-api-newer",
        assignee_role="A26",
        role_version="1",
        input_version="v2",
        input_refs=["fixture:synthetic-v2"],
        goal="复核更新后的合成资料。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
    )

    agents = client.get(f"/api/v1/projects/{project_id}/agents")
    assert agents.status_code == 200
    assert len(agents.json()) == 26
    a26 = next(item for item in agents.json() if item["role_id"] == "A26")
    assert a26["latest_task_id"] == str(newer_task.id)
    assert a26["scene_state"] == "ready"

    tasks = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert tasks.status_code == 200
    assert tasks.json()[0]["id"] == str(newer_task.id)
    assert {item["id"] for item in tasks.json()} == {
        str(task.id),
        str(newer_task.id),
    }

    fixture = json.loads(
        (PROJECT_ROOT / "fixtures" / "opportunity-contract-examples.json").read_text(
            encoding="utf-8"
        )
    )
    opportunity = client.post(
        f"/api/v1/projects/{project_id}/opportunities",
        json={"card": fixture["opportunities"][0]},
    )
    assert opportunity.status_code == 201, opportunity.text
    opportunity_body = opportunity.json()
    selected = client.post(
        (f"/api/v1/projects/{project_id}/opportunities/{opportunity_body['id']}/select"),
        headers={"Idempotency-Key": "w10-selection"},
        json={
            "expected_revision": opportunity_body["revision"],
            "reason": "仅验证用户选择合同。",
            "scope": "不授权费用、外联或实验。",
            "evidence_version_ids": [],
        },
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["status"] == "selected"

    overview = client.get(f"/api/v1/projects/{project_id}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["counts"]["tasks"] == 2
    assert body["counts"]["open_tasks"] == 2
    assert body["current_direction"]["id"] == opportunity_body["id"]
    assert any(item["type"] == "opportunity.selected" for item in body["recent_events"])

    events = client.get(f"/api/v1/projects/{project_id}/events?after=0")
    assert events.status_code == 200
    assert [item["project_seq"] for item in events.json()] == sorted(
        item["project_seq"] for item in events.json()
    )


def test_knowledge_upload_processing_browsing_search_and_download(
    session_factory,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    client = _client(session_factory, app_database_url, tmp_path)
    session_response = client.post("/api/v1/system/local-session")
    assert session_response.status_code == 200
    project_response = client.post(
        "/api/v1/projects",
        headers={"Idempotency-key": "w10-knowledge-project"},
        json={
            "name": "W10 知识库项目",
            "scope": "验证上传、解析、索引、浏览与原文下载。",
        },
    )
    project_id = project_response.json()["id"]
    task = TaskService(session_factory).create_task(
        project_id=project_id,
        actor_user_id=session_response.json()["user_id"],
        task_type="evidence.review",
        purpose="w10-search",
        assignee_role="A26",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:w10"],
        goal="检索合成资料。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
    )

    content = "合成研究记录：犬模型疼痛评分下降。\n负面结果：功能改善未观察到。\n".encode()
    digest = hashlib.sha256(content).hexdigest()
    started = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads",
        json={
            "filename": "synthetic-w10.txt",
            "expected_bytes": len(content),
            "media_type_hint": "text/plain",
            "expected_sha256": digest,
        },
    )
    assert started.status_code == 201, started.text
    upload_id = started.json()["session_id"]

    part = client.put(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{upload_id}/parts/0",
        content=content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Part-SHA256": digest,
        },
    )
    assert part.status_code == 200, part.text
    assert part.json()["received_bytes"] == len(content)

    committed = client.post(f"/api/v1/projects/{project_id}/knowledge/uploads/{upload_id}/commit")
    assert committed.status_code == 200, committed.text
    version_id = committed.json()["version_id"]

    documents = client.get(f"/api/v1/projects/{project_id}/knowledge/documents")
    assert documents.status_code == 200, documents.text
    document = documents.json()[0]
    assert document["filename"] == "synthetic-w10.txt"
    assert document["ingest_state"] == "ready"

    detail = client.get(f"/api/v1/projects/{project_id}/knowledge/documents/{document['id']}")
    assert detail.status_code == 200
    assert any("犬模型" in passage["text"] for passage in detail.json()["passages"])

    search = client.post(
        f"/api/v1/projects/{project_id}/knowledge/search",
        json={
            "task_id": str(task.id),
            "query": "犬模型 疼痛",
        },
    )
    assert search.status_code == 200, search.text
    assert search.json()["hits"]
    assert search.json()["snapshot_id"]

    download = client.get(f"/api/v1/projects/{project_id}/knowledge/versions/{version_id}/download")
    assert download.status_code == 200
    assert download.content == content
    assert download.headers["cache-control"] == "private, no-store"
