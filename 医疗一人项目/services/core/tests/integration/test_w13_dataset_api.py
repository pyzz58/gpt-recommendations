from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_dataset_api_import_clean_plan_run_and_review(
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
            detail="W13 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w13-api-project"},
        json={"name": "W13 API项目", "scope": "验证数据集与统计API。"},
    ).json()
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    upload = client.post(
        f"/api/v1/projects/{project['id']}/knowledge/uploads",
        json={
            "filename": "synthetic-dataset.csv",
            "expected_bytes": len(content),
            "media_type_hint": "text/csv",
            "expected_sha256": digest,
        },
    ).json()
    part = client.put(
        (f"/api/v1/projects/{project['id']}/knowledge/uploads/{upload['session_id']}/parts/0"),
        content=content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Part-SHA256": digest,
        },
    )
    assert part.status_code == 200, part.text
    committed = client.post(
        f"/api/v1/projects/{project['id']}/knowledge/uploads/{upload['session_id']}/commit"
    )
    assert committed.status_code == 200, committed.text

    imported = client.post(
        f"/api/v1/projects/{project['id']}/datasets/import",
        headers={"Idempotency-Key": "w13-api-import"},
        json={
            "document_version_id": committed.json()["version_id"],
            "title": "API合成数据",
            "source_label": "synthetic-api",
            "synthetic": True,
            "sheet_name": None,
        },
    )
    assert imported.status_code == 201, imported.text
    raw = imported.json()

    derived = client.post(
        f"/api/v1/projects/{project['id']}/datasets/{raw['id']}/versions",
        headers={"Idempotency-Key": "w13-api-clean"},
        json={
            "parent_version_id": raw["current_version"]["id"],
            "spec": {
                "select_columns": ["group", "score", "response"],
                "numeric_columns": ["score"],
                "rename_columns": {},
                "drop_missing_columns": ["score"],
                "rationale": "删除缺少主要终点的行。",
            },
        },
    )
    assert derived.status_code == 201, derived.text
    cleaned = derived.json()

    plan = client.post(
        (
            f"/api/v1/projects/{project['id']}/dataset-versions/"
            f"{cleaned['current_version']['id']}/statistical-plans"
        ),
        headers={"Idempotency-Key": "w13-api-plan"},
        json={
            "spec": {
                "question": "两组均值差是多少？",
                "endpoint_column": "score",
                "method": "two_group_mean_difference",
                "group_column": "group",
                "analysis_set": "主要终点完整行",
                "missing_policy": "fail_if_missing",
                "unit": "score",
                "alpha": 0.05,
                "expected_groups": ["control", "treatment"],
                "limitations": ["未计算p值", "合成数据"],
                "exploratory": False,
            }
        },
    )
    assert plan.status_code == 201, plan.text

    analysis = client.post(
        (f"/api/v1/projects/{project['id']}/statistical-plans/{plan.json()['id']}/run"),
        headers={"Idempotency-Key": "w13-api-run"},
    )
    assert analysis.status_code == 201, analysis.text
    assert analysis.json()["result"]["difference"] == -5

    review = client.post(
        (f"/api/v1/projects/{project['id']}/analyses/{analysis.json()['id']}/review"),
        headers={"Idempotency-Key": "w13-api-review"},
        json={
            "reviewer_role": "A14",
            "decision": "accepted",
            "summary": "合成API统计记录已检查。",
            "findings": [],
        },
    )
    assert review.status_code == 200, review.text
    assert review.json()["decision"] == "accepted"
