from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.main import create_app


def test_w16_external_api_records_scope_and_professional_boundaries(
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
            detail="W16 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w16-api-project"},
        json={"name": "W16 API项目", "scope": "验证外部合作记录。"},
    ).json()
    project_id = project["id"]

    organization = client.post(
        f"/api/v1/projects/{project_id}/external/organizations",
        headers={"Idempotency-Key": "w16-api-org"},
        json={
            "name": "合成CRO",
            "provider_type": "cro",
            "capability_summary": "仅用于合成API合同测试。",
            "source_refs": ["fixture:w16-api-provider"],
            "verification_state": "verified",
        },
    )
    assert organization.status_code == 201, organization.text
    organization_id = organization.json()["id"]

    engagement = client.post(
        f"/api/v1/projects/{project_id}/external/engagements",
        headers={"Idempotency-Key": "w16-api-engagement"},
        json={
            "organization_id": organization_id,
            "title": "合成研究外包范围",
            "scope": {
                "scientific_question": "合成问题能否被测试回答？",
                "decision_impact": "决定是否继续准备验证。",
                "input_requirements": ["合成方案"],
                "deliverables": ["原始数据"],
                "method_and_quality": ["记录方法与偏差"],
                "rights_and_confidentiality": ["项目私有"],
                "acceptance_responsibility": "A25记录完整性",
                "target_start": "2026-11-01",
                "target_end": "2026-12-01",
                "budget_lower": "1000.00",
                "budget_upper": "2000.00",
                "currency": "CNY",
            },
        },
    )
    assert engagement.status_code == 201, engagement.text
    assert engagement.json()["state"] == "draft"

    regulatory = client.post(
        f"/api/v1/projects/{project_id}/external/professional-records",
        headers={"Idempotency-Key": "w16-api-regulatory"},
        json={
            "kind": "regulatory",
            "state": "official_confirmed",
            "title": "合成法规问题",
            "source_tier": "official",
            "source_title": "合成测试官方入口",
            "source_ref": "fixture:w16-api-regulatory",
            "checked_at": "2026-10-31",
            "market": "合成市场",
            "product_scope": "合成IVD",
            "facts": ["仅测试分类问题"],
            "limitations": ["不代表真实注册结论"],
            "metadata": {},
        },
    )
    assert regulatory.status_code == 201, regulatory.text
    assert regulatory.json()["market"] == "合成市场"

    commercial = client.post(
        f"/api/v1/projects/{project_id}/external/professional-records",
        headers={"Idempotency-Key": "w16-api-commercial"},
        json={
            "kind": "commercial",
            "title": "合成需求假说",
            "source_tier": "none",
            "commercial_evidence_type": "unknown",
            "facts": [],
            "limitations": ["尚无访谈"],
            "metadata": {},
        },
    )
    assert commercial.status_code == 201, commercial.text
    assert commercial.json()["commercial_evidence_type"] == "unknown"

    workspace = client.get(f"/api/v1/projects/{project_id}/external")
    assert workspace.status_code == 200, workspace.text
    body = workspace.json()
    assert len(body["organizations"]) == 1
    assert len(body["engagements"]) == 1
    assert len(body["professional_records"]) == 2
