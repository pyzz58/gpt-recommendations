from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app


def test_w15_mail_api_draft_authorization_send_and_reconcile_contract(
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
            detail="W15 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w15-api-project"},
        json={"name": "W15 API项目", "scope": "验证本地模拟邮件。"},
    ).json()
    project_id = project["id"]

    account = client.get(f"/api/v1/projects/{project_id}/mail/account")
    assert account.status_code == 200, account.text
    assert account.json()["mode"] == "mock"
    assert account.json()["state"] == "mock_ready"
    assert account.json()["external_send_enabled"] is False

    synced = client.post(f"/api/v1/projects/{project_id}/mail/inbox/sync-mock")
    assert synced.status_code == 200, synced.text
    thread = synced.json()[0]
    assert len(thread["messages"]) == 2
    assert all(message["synthetic"] for message in thread["messages"])

    linked = client.post(
        f"/api/v1/projects/{project_id}/mail/threads/{thread['id']}/link",
        headers={"X-Expected-Revision": str(thread["revision"])},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["link_state"] == "linked"
    assert linked.json()["project_id"] == project_id

    draft = client.post(
        f"/api/v1/projects/{project_id}/mail/drafts",
        headers={"Idempotency-Key": "w15-api-draft"},
        json={
            "to_addresses": ["expert@example.test"],
            "cc_addresses": [],
            "bcc_addresses": [],
            "subject": "合成专家问题",
            "body_text": "这是一个本地模拟邮件，不构成真实外联。",
            "attachments": [],
            "thread_id": None,
        },
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["state"] == "draft"
    draft_id = draft.json()["id"]

    authorization = client.post(
        f"/api/v1/projects/{project_id}/mail/drafts/{draft_id}/authorizations",
        headers={"Idempotency-Key": "w15-api-authorize"},
        json={"spec": {"expires_in_minutes": 10, "max_sends": 1}},
    )
    assert authorization.status_code == 201, authorization.text
    assert authorization.json()["action"] == "mail.send"
    assert authorization.json()["state"] == "active"
    authorization_id = authorization.json()["id"]

    sent = client.post(
        f"/api/v1/projects/{project_id}/mail/drafts/{draft_id}/send",
        headers={"Idempotency-Key": "w15-api-send"},
        json={"authorization_id": authorization_id},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["attempt"]["state"] == "sent"
    assert sent.json()["draft_state"] == "sent"
    assert sent.json()["attempt"]["provider_message_id"].startswith("mock-message-")

    replay = client.post(
        f"/api/v1/projects/{project_id}/mail/drafts/{draft_id}/send",
        headers={"Idempotency-Key": "w15-api-send"},
        json={"authorization_id": authorization_id},
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["attempt"]["id"] == sent.json()["attempt"]["id"]

    attempts = client.get(f"/api/v1/projects/{project_id}/mail/attempts")
    assert attempts.status_code == 200
    assert len(attempts.json()) == 1

    second_project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w15-api-second-project"},
        json={"name": "W15隔离项目", "scope": "不得读取其他项目邮件。"},
    ).json()
    cross_link = client.post(
        f"/api/v1/projects/{second_project['id']}/mail/threads/{thread['id']}/link",
        headers={"X-Expected-Revision": str(linked.json()["revision"])},
    )
    assert cross_link.status_code == 404

    revoked_project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w15-api-revoke-project"},
        json={"name": "W15授权撤回", "scope": "验证撤回后不能发送。"},
    ).json()
    revoked_id = revoked_project["id"]
    draft2 = client.post(
        f"/api/v1/projects/{revoked_id}/mail/drafts",
        headers={"Idempotency-Key": "w15-api-revoke-draft"},
        json={
            "to_addresses": ["expert@example.test"],
            "cc_addresses": [],
            "bcc_addresses": [],
            "subject": "撤回测试",
            "body_text": "撤回后不得发送。",
            "attachments": [],
            "thread_id": None,
        },
    ).json()
    auth2 = client.post(
        f"/api/v1/projects/{revoked_id}/mail/drafts/{draft2['id']}/authorizations",
        headers={"Idempotency-Key": "w15-api-revoke-authorize"},
        json={"spec": {"expires_in_minutes": 10, "max_sends": 1}},
    ).json()
    revoked = client.post(
        f"/api/v1/projects/{revoked_id}/mail/authorizations/{auth2['id']}/revoke"
    )
    assert revoked.status_code == 200
    rejected = client.post(
        f"/api/v1/projects/{revoked_id}/mail/drafts/{draft2['id']}/send",
        headers={"Idempotency-Key": "w15-api-revoke-send"},
        json={"authorization_id": auth2["id"]},
    )
    assert rejected.status_code == 403
