from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.external import ExternalService
from medical_one_person.application.knowledge import ClaimService
from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.domain.external import (
    DeliverableKind,
    DeliverableSpec,
    EngagementScope,
    EngagementSpec,
    OrganizationSpec,
    ProviderType,
    VerificationState,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import ClaimVersion
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _analysis_target(client: TestClient, project_id: str) -> str:
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    upload = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads",
        json={
            "filename": "w17-api-synthetic.csv",
            "expected_bytes": len(content),
            "media_type_hint": "text/csv",
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
    imported = client.post(
        f"/api/v1/projects/{project_id}/datasets/import",
        headers={"Idempotency-Key": "w17-api-dataset-import"},
        json={
            "document_version_id": committed.json()["version_id"],
            "title": "W17 API合成统计",
            "source_label": "synthetic-w17-api",
            "synthetic": True,
            "sheet_name": None,
        },
    )
    assert imported.status_code == 201, imported.text
    derived = client.post(
        f"/api/v1/projects/{project_id}/datasets/{imported.json()['id']}/versions",
        headers={"Idempotency-Key": "w17-api-dataset-clean"},
        json={
            "parent_version_id": imported.json()["current_version"]["id"],
            "spec": {
                "select_columns": ["group", "score", "response"],
                "numeric_columns": ["score"],
                "rename_columns": {},
                "drop_missing_columns": ["score"],
                "rationale": "W17 API只使用主要终点完整的合成行。",
            },
        },
    )
    assert derived.status_code == 201, derived.text
    plan = client.post(
        (
            f"/api/v1/projects/{project_id}/dataset-versions/"
            f"{derived.json()['current_version']['id']}/statistical-plans"
        ),
        headers={"Idempotency-Key": "w17-api-stat-plan"},
        json={
            "spec": {
                "question": "W17 API合成两组均值差是多少？",
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
        f"/api/v1/projects/{project_id}/statistical-plans/{plan.json()['id']}/run",
        headers={"Idempotency-Key": "w17-api-stat-run"},
    )
    assert analysis.status_code == 201, analysis.text
    review = client.post(
        f"/api/v1/projects/{project_id}/analyses/{analysis.json()['id']}/review",
        headers={"Idempotency-Key": "w17-api-stat-review"},
        json={
            "reviewer_role": "A14",
            "decision": "accepted",
            "summary": "W17 API合成统计方法复核。",
            "findings": [],
        },
    )
    assert review.status_code == 200, review.text
    return str(analysis.json()["id"])


def test_w17_audit_api_creates_reviews_dispositions_and_evaluation(
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
            detail="W17 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    session = client.post("/api/v1/system/local-session")
    assert session.status_code == 200
    owner_user_id = session.json()["user_id"]
    workspace_id = session.json()["workspace_id"]
    project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w17-api-project"},
        json={"name": "W17 API审计项目", "scope": "验证审计API与阻断处置。"},
    ).json()
    other_project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w17-api-other-project"},
        json={"name": "W17 API隔离项目", "scope": "仅用于跨项目拒绝。"},
    ).json()
    project_id = project["id"]

    claim = ClaimService(session_factory).create(
        workspace_id=workspace_id,
        actor_user_id=owner_user_id,
        project_id=project_id,
        statement="W17 API无证据支持断言。",
        species_or_population="犬",
        directness="direct",
    )
    with session_factory.begin() as db:
        set_rls_context(
            db,
            workspace_id=workspace_id,
            user_id=owner_user_id,
        )
        row = db.get(ClaimVersion, claim.version_id)
        assert row is not None
        row.status = "supported"

    analysis_id = _analysis_target(client, project_id)
    external = ExternalService(session_factory)
    organization = external.create_organization(
        project_id=project_id,
        actor_user_id=owner_user_id,
        spec=OrganizationSpec(
            name="W17 API合成CRO",
            provider_type=ProviderType.CRO,
            capability_summary="仅用于合成API测试，未联系。",
            source_refs=["fixture:w17-api-provider"],
            verification_state=VerificationState.VERIFIED,
        ),
        idempotency_key="w17-api-org",
    )
    engagement = external.create_engagement(
        project_id=project_id,
        actor_user_id=owner_user_id,
        spec=EngagementSpec(
            organization_id=organization.id,
            title="W17 API合成工作包",
            scope=EngagementScope(
                scientific_question="合成问题",
                decision_impact="仅验证审计流程。",
                input_requirements=["合成方案"],
                deliverables=["合成报告"],
                method_and_quality=["记录方法"],
                rights_and_confidentiality=["项目私有"],
                acceptance_responsibility="A25记录",
            ),
        ),
        idempotency_key="w17-api-engagement",
    )
    deliverable = external.create_deliverable(
        project_id=project_id,
        actor_user_id=owner_user_id,
        spec=DeliverableSpec(
            engagement_id=engagement.id,
            title="W17 API预期交付",
            kind=DeliverableKind.REPORT,
            expected_items=["合成报告"],
        ),
        idempotency_key="w17-api-deliverable",
    )

    created = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers={"Idempotency-Key": "w17-api-claim-audit"},
        json={
            "target_type": "claim_version",
            "target_id": str(claim.version_id),
            "reviewer_role": "A25",
            "producer_role": "A02",
        },
    )
    assert created.status_code == 201, created.text
    audit = created.json()
    assert audit["state"] == "blocked"
    assert audit["downstream_blocked"] is True
    assert audit["reviewer_role"] == "A25"
    assert audit["producer_role"] == "A02"
    assert audit["findings"][0]["code"] == "CLAIM_MISSING_EVIDENCE"
    replay = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers={"Idempotency-Key": "w17-api-claim-audit"},
        json={
            "target_type": "claim_version",
            "target_id": str(claim.version_id),
            "reviewer_role": "A25",
            "producer_role": "A02",
        },
    )
    assert replay.status_code == 201
    assert replay.json() == audit
    conflict = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers={"Idempotency-Key": "w17-api-claim-audit"},
        json={
            "target_type": "claim_version",
            "target_id": str(claim.version_id),
            "reviewer_role": "A26",
            "producer_role": "A02",
        },
    )
    assert conflict.status_code == 409
    same_role = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers={"Idempotency-Key": "w17-api-self-review"},
        json={
            "target_type": "claim_version",
            "target_id": str(claim.version_id),
            "reviewer_role": "A25",
            "producer_role": "A25",
        },
    )
    assert same_role.status_code == 422
    cross_project = client.post(
        f"/api/v1/projects/{other_project['id']}/audits",
        headers={"Idempotency-Key": "w17-api-cross-project"},
        json={
            "target_type": "claim_version",
            "target_id": str(claim.version_id),
            "reviewer_role": "A25",
            "producer_role": "A02",
        },
    )
    assert cross_project.status_code == 404

    finding_id = audit["findings"][0]["id"]
    disposition = client.post(
        (
            f"/api/v1/projects/{project_id}/audits/{audit['id']}/findings/"
            f"{finding_id}/disposition"
        ),
        json={
            "status": "resolved",
            "resolution": "W17 API测试记录处置，不改变原审计结论。",
        },
    )
    assert disposition.status_code == 200, disposition.text
    assert disposition.json()["status"] == "resolved"
    rewrite = client.post(
        (
            f"/api/v1/projects/{project_id}/audits/{audit['id']}/findings/"
            f"{finding_id}/disposition"
        ),
        json={
            "status": "accepted_risk",
            "resolution": "尝试覆盖已解决处置。",
        },
    )
    assert rewrite.status_code == 409

    analysis_audit = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers={"Idempotency-Key": "w17-api-analysis-audit"},
        json={
            "target_type": "analysis_run",
            "target_id": analysis_id,
            "reviewer_role": "A25",
            "producer_role": "A15",
        },
    )
    assert analysis_audit.status_code == 201, analysis_audit.text
    assert analysis_audit.json()["state"] == "passed"

    deliverable_audit = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers={"Idempotency-Key": "w17-api-deliverable-audit"},
        json={
            "target_type": "external_deliverable",
            "target_id": str(deliverable.id),
            "reviewer_role": "A26",
            "producer_role": "A22",
        },
    )
    assert deliverable_audit.status_code == 201, deliverable_audit.text
    assert deliverable_audit.json()["state"] == "passed"

    workspace = client.get(f"/api/v1/projects/{project_id}/audits")
    assert workspace.status_code == 200, workspace.text
    body = workspace.json()
    assert {item["target_type"] for item in body["targets"]} == {
        "analysis_run",
        "claim_version",
        "external_deliverable",
    }
    assert len(body["reviews"]) == 3
    assert body["reviews"][0]["target_id"]
    assert body["limitations"]

    evaluation = client.post(f"/api/v1/projects/{project_id}/audits/evaluate")
    assert evaluation.status_code == 201, evaluation.text
    metrics = evaluation.json()["metrics"]
    assert metrics == {
        "cases": 7,
        "true_positives": 6,
        "false_positives": 0,
        "false_negatives": 0,
        "precision": 1.0,
        "recall": 1.0,
    }
    assert any("Synthetic" in item for item in evaluation.json()["limitations"])
