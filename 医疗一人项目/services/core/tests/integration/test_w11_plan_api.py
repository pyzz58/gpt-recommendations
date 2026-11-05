from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_plan_api_dispatches_mock_executes_and_records_review(
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
            detail="W11 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w11-api-project"},
        json={
            "name": "W11 API项目",
            "scope": "验证计划API、派工、mock运行和审核记录。",
        },
    ).json()

    fixture = json.loads(
        (PROJECT_ROOT / "fixtures" / "opportunity-contract-examples.json").read_text(
            encoding="utf-8"
        )
    )
    opportunity = client.post(
        f"/api/v1/projects/{project['id']}/opportunities",
        json={"card": fixture["opportunities"][0]},
    ).json()
    selected = client.post(
        (f"/api/v1/projects/{project['id']}/opportunities/{opportunity['id']}/select"),
        headers={"Idempotency-Key": "w11-api-select"},
        json={
            "expected_revision": opportunity["revision"],
            "reason": "合成W11 API测试。",
            "scope": "不授权外部动作。",
            "evidence_version_ids": [],
        },
    )
    assert selected.status_code == 200, selected.text

    plan = client.post(
        f"/api/v1/projects/{project['id']}/plans",
        headers={"Idempotency-Key": "w11-api-plan"},
        json={
            "source_decision_id": selected.json()["decision_id"],
            "spec": {
                "title": "W11 API计划",
            "scientific_feedback": False,
                "objective": "只验证本地mock工作流。",
                "max_rework_rounds": 2,
                "nodes": [
                    {
                        "key": "research",
                        "task_type": "scientific.core_review",
                        "purpose": "w11-api",
                        "assignee_role": "A02",
                        "role_version": "1",
                        "input_version": "selection-v1",
                        "input_refs": ["fixture:w11-api"],
                        "goal": "生成合成科学核查草案。",
                        "deliverable_schema": "agent_delivery.v1",
                        "acceptance_policy": "independent_review.v1",
                    }
                ],
            },
        },
    )
    assert plan.status_code == 201, plan.text
    plan_body = plan.json()

    activated = client.post(
        f"/api/v1/projects/{project['id']}/plans/{plan_body['id']}/activate",
        json={"expected_revision": plan_body["revision"]},
    )
    assert activated.status_code == 200, activated.text

    dispatched = client.post(
        f"/api/v1/projects/{project['id']}/plans/{plan_body['id']}/dispatch",
        json={"expected_revision": activated.json()["revision"]},
    )
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["dispatched"][0]["node_key"] == "research"

    executed = client.post(
        f"/api/v1/projects/{project['id']}/plans/{plan_body['id']}/execute",
        json={"max_tasks": 1},
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["executed"][0]["task_state"] == "submitted"

    current = client.get(f"/api/v1/projects/{project['id']}/plans/{plan_body['id']}")
    assert current.status_code == 200
    node = current.json()["nodes"][0]
    reviewed = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{node['task_id']}/review",
        headers={"Idempotency-Key": "w11-api-review"},
        json={
            "plan_id": plan_body["id"],
            "expected_revision": node["task_revision"],
            "reviewer_role": "A25",
            "decision": "accepted",
            "summary": "合成mock审核通过，仅验证接口。",
            "findings": [],
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["task_state"] == "accepted"
    assert reviewed.json()["plan_status"] == "completed"
