from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_workflow_api_assesses_gate_and_creates_domain_plan(
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
            detail="W12 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w12-api-project"},
        json={
            "name": "W12 API项目",
            "scope": "验证专业流程、阶段门和领域计划API。",
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
        headers={"Idempotency-Key": "w12-api-select"},
        json={
            "expected_revision": opportunity["revision"],
            "reason": "W12 API合成选择。",
            "scope": "不授权外部动作。",
            "evidence_version_ids": [],
        },
    )
    assert selected.status_code == 200, selected.text
    decision_id = selected.json()["decision_id"]

    workflows = client.get(f"/api/v1/projects/{project['id']}/workflows")
    assert workflows.status_code == 200, workflows.text
    assert len(workflows.json()) == 3
    pet = next(
        item for item in workflows.json() if item["definition"]["track"] == "pet_repurposing"
    )
    first_stage, second_stage = pet["definition"]["stages"][:2]
    results = [
        {
            "criterion_id": criterion["id"],
            "status": "met",
            "rationale": "合成API判据记录。",
            "evidence_refs": [decision_id],
        }
        for criterion in first_stage["criteria"]
    ]
    assessed = client.post(
        (
            f"/api/v1/projects/{project['id']}/workflows/pet_repurposing/"
            f"stages/{first_stage['stage_id']}/assessments"
        ),
        json={
            "criterion_results": results,
            "rationale": "仅验证阶段门API，不代表科学或监管成立。",
        },
    )
    assert assessed.status_code == 201, assessed.text
    assert assessed.json()["status"] == "ready_for_review"

    decided = client.post(
        (f"/api/v1/projects/{project['id']}/workflow-assessments/{assessed.json()['id']}/decision"),
        json={
            "decision": "accepted",
            "reviewer_role": "A25",
            "reason": "用户接受合成阶段记录。",
        },
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["decision"] == "accepted"

    plan = client.post(
        (
            f"/api/v1/projects/{project['id']}/workflows/pet_repurposing/"
            f"stages/{second_stage['stage_id']}/plans"
        ),
        headers={"Idempotency-Key": "w12-api-stage2-plan"},
        json={"source_decision_id": decision_id},
    )
    assert plan.status_code == 201, plan.text
    assert plan.json()["workflow_id"] == pet["definition"]["workflow_id"]
    assert plan.json()["stage_id"] == second_stage["stage_id"]
    assert plan.json()["workflow_sha256"] == pet["sha256"]
