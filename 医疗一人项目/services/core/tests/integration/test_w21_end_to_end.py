from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.infrastructure.exports.renderer import OfficeRenderer
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _app(settings: Settings, session_factory: sessionmaker[Session]):
    return create_app(
        database_checker=lambda: DependencyStatus(
            status="ready",
            detail="W21 end-to-end integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )


def _client(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> TestClient:
    client = TestClient(_app(settings, session_factory), base_url="http://127.0.0.1:3000")
    response = client.post("/api/v1/system/local-session")
    assert response.status_code == 200, response.text
    return client


def _create_project(client: TestClient, *, suffix: str, key: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": key},
        json={
            "name": f"W21 {suffix}",
            "scope": f"仅用于W21双项目隔离与完整链路验证：{suffix}。",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _select_opportunity(
    client: TestClient,
    *,
    project_id: str,
    key: str,
) -> str:
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
    selected = client.post(
        f"/api/v1/projects/{project_id}/opportunities/{opportunity.json()['id']}/select",
        headers={"Idempotency-Key": key},
        json={
            "expected_revision": opportunity.json()["revision"],
            "reason": "W21双项目合成选择。",
            "scope": "仅本地mock，不授权现实动作。",
            "evidence_version_ids": [],
        },
    )
    assert selected.status_code == 200, selected.text
    return selected.json()["decision_id"]


def _create_plan(
    client: TestClient,
    *,
    project_id: str,
    decision_id: str,
    key: str,
    nodes: list[dict],
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/plans",
        headers={"Idempotency-Key": key},
        json={
            "source_decision_id": decision_id,
            "spec": {
                "title": f"W21计划-{key}",
            "scientific_feedback": False,
                "objective": "验证两个隔离项目中的完整mock研发协作链。",
                "max_rework_rounds": 2,
                "nodes": nodes,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _activate(
    client: TestClient,
    project_id: str,
    plan: dict,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/plans/{plan['id']}/activate",
        json={"expected_revision": plan["revision"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _dispatch(
    client: TestClient,
    project_id: str,
    plan_id: str,
    revision: int,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/plans/{plan_id}/dispatch",
        json={"expected_revision": revision},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _execute(
    client: TestClient,
    project_id: str,
    plan_id: str,
    *,
    max_tasks: int = 1,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/plans/{plan_id}/execute",
        json={"max_tasks": max_tasks},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _review(
    client: TestClient,
    *,
    project_id: str,
    plan_id: str,
    task_id: str,
    revision: int,
    decision: str,
    summary: str,
    key: str,
    findings: list[dict] | None = None,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/tasks/{task_id}/review",
        headers={"Idempotency-Key": key},
        json={
            "plan_id": plan_id,
            "expected_revision": revision,
            "reviewer_role": "A25",
            "decision": decision,
            "summary": summary,
            "findings": findings or [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _upload_raw_data(client: TestClient, project_id: str) -> str:
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    upload = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads",
        json={
            "filename": "w21-cro-raw-results.csv",
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
    return str(committed.json()["version_id"])


def _create_external_delivery(
    client: TestClient,
    *,
    project_id: str,
    raw_version_id: str,
) -> dict:
    def current_engagement(engagement_id: str) -> dict:
        workspace = client.get(f"/api/v1/projects/{project_id}/external")
        assert workspace.status_code == 200, workspace.text
        return next(
            item
            for item in workspace.json()["engagements"]
            if item["id"] == engagement_id
        )

    organization = client.post(
        f"/api/v1/projects/{project_id}/external/organizations",
        headers={"Idempotency-Key": "w21-org"},
        json={
            "name": "W21合成CRO",
            "provider_type": "cro",
            "capability_summary": "仅用于本地外包交付模拟，无现实联系。",
            "source_refs": ["fixture:w21-cro"],
            "verification_state": "verified",
        },
    )
    assert organization.status_code == 201, organization.text
    engagement = client.post(
        f"/api/v1/projects/{project_id}/external/engagements",
        headers={"Idempotency-Key": "w21-engagement"},
        json={
            "organization_id": organization.json()["id"],
            "title": "W21合成原始数据交付",
            "scope": {
                "scientific_question": "外包数据能否走完接收与验收？",
                "decision_impact": "仅验证软件交接链。",
                "input_requirements": ["合成方案"],
                "deliverables": ["原始数据"],
                "method_and_quality": ["记录方法与偏差"],
                "rights_and_confidentiality": ["项目私有"],
                "acceptance_responsibility": "A25检查完整性",
                "budget_lower": "0.00",
                "budget_upper": "0.00",
                "currency": "CNY",
            },
        },
    )
    assert engagement.status_code == 201, engagement.text
    for target_state in ("scope_ready", "requested"):
        transitioned = client.put(
            (
                f"/api/v1/projects/{project_id}/external/engagements/"
                f"{engagement.json()['id']}/state"
            ),
            json={
                "expected_revision": engagement.json()["revision"],
                "state": target_state,
            },
        )
        assert transitioned.status_code == 200, transitioned.text
        engagement = transitioned
    quote = client.post(
        f"/api/v1/projects/{project_id}/external/quotes",
        headers={"Idempotency-Key": "w21-quote"},
        json={
            "engagement_id": engagement.json()["id"],
            "amount": "0.00",
            "currency": "CNY",
            "tax_included": False,
            "shipping_included": None,
            "assumptions": ["仅本地合成模拟"],
            "excluded_work": ["现实执行与付款"],
            "document_version_id": raw_version_id,
            "state": "accepted",
        },
    )
    assert quote.status_code == 201, quote.text
    engagement = current_engagement(engagement.json()["id"])
    assert engagement["state"] == "quoted"
    contract = client.post(
        f"/api/v1/projects/{project_id}/external/contracts",
        headers={"Idempotency-Key": "w21-contract"},
        json={
            "engagement_id": engagement["id"],
            "quote_id": quote.json()["id"],
            "title": "W21合成合同",
            "terms_summary": "仅登记合成合同状态，不产生现实签署。",
            "document_version_id": raw_version_id,
        },
    )
    assert contract.status_code == 201, contract.text
    signed = client.put(
        f"/api/v1/projects/{project_id}/external/contracts/"
        f"{contract.json()['id']}/state",
        json={
            "expected_revision": contract.json()["revision"],
            "state": "signed",
            "internal_signed": True,
            "external_signed": True,
            "document_version_id": raw_version_id,
            "reason": "仅登记合成双方签署样本文档。",
        },
    )
    assert signed.status_code == 200, signed.text
    authorization = client.post(
        f"/api/v1/projects/{project_id}/external/authorizations",
        headers={"Idempotency-Key": "w21-external-auth"},
        json={
            "engagement_id": engagement["id"],
            "action_scope": "仅登记合成外部执行状态，不联系或付款。",
            "amount_max": "0.01",
            "currency": "CNY",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
    )
    assert authorization.status_code == 201, authorization.text
    engagement = current_engagement(engagement["id"])
    for target_state in ("authorized", "executing"):
        if engagement["state"] == target_state:
            continue
        transitioned = client.put(
            (
                f"/api/v1/projects/{project_id}/external/engagements/"
                f"{engagement['id']}/state"
            ),
            json={
                "expected_revision": engagement["revision"],
                "state": target_state,
            },
        )
        assert transitioned.status_code == 200, transitioned.text
        engagement = transitioned.json()
    deliverable = client.post(
        f"/api/v1/projects/{project_id}/external/deliverables",
        headers={"Idempotency-Key": "w21-deliverable"},
        json={
            "engagement_id": engagement["id"],
            "title": "W21合成原始数据包",
            "kind": "raw_data",
            "expected_items": ["原始数据", "方法记录"],
        },
    )
    assert deliverable.status_code == 201, deliverable.text
    received = client.post(
        (
            f"/api/v1/projects/{project_id}/external/deliverables/"
            f"{deliverable.json()['id']}/receive"
        ),
        json={
            "expected_revision": deliverable.json()["revision"],
            "knowledge_version_id": raw_version_id,
            "manifest": {"rows": 20, "source": "synthetic"},
            "missing_items": [],
            "summary": "收到合成CRO原始数据，不代表真实机构执行。",
        },
    )
    assert received.status_code == 200, received.text
    accepted = client.post(
        (
            f"/api/v1/projects/{project_id}/external/deliverables/"
            f"{deliverable.json()['id']}/review"
        ),
        json={
            "expected_revision": received.json()["revision"],
            "decision": "accepted",
            "reviewer_role": "A25",
            "summary": "合成原始数据、方法和缺件状态已核对。",
            "findings": [],
            "missing_items": [],
        },
    )
    assert accepted.status_code == 200, accepted.text
    return accepted.json()


def test_w21_two_isolated_projects_complete_chain_restart_and_stop(
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
    client = _client(settings, session_factory)
    project_a = _create_project(client, suffix="项目A", key="w21-project-a")
    project_b = _create_project(client, suffix="项目B", key="w21-project-b")
    decision_a = _select_opportunity(
        client,
        project_id=project_a["id"],
        key="w21-select-a",
    )
    decision_b = _select_opportunity(
        client,
        project_id=project_b["id"],
        key="w21-select-b",
    )
    nodes_a = [
        {
            "key": "research",
            "task_type": "scientific.core_review",
            "purpose": "w21-research",
            "assignee_role": "A02",
            "role_version": "1",
            "input_version": "selection-v1",
            "input_refs": ["fixture:w21-a"],
            "goal": "形成待退回重做的合成科学草案。",
            "deliverable_schema": "agent_delivery.v1",
            "acceptance_policy": "independent_review.v1",
        },
        {
            "key": "audit",
            "task_type": "scientific.audit",
            "purpose": "w21-audit",
            "assignee_role": "A26",
            "role_version": "1",
            "input_version": "selection-v1",
            "input_refs": ["fixture:w21-a"],
            "goal": "复核上游草案并保留反证。",
            "deliverable_schema": "agent_delivery.v1",
            "acceptance_policy": "independent_review.v1",
            "depends_on": ["research"],
        },
    ]
    nodes_b = [nodes_a[0] | {"purpose": "w21-b-research", "input_refs": ["fixture:w21-b"]}]
    plan_a = _create_plan(
        client,
        project_id=project_a["id"],
        decision_id=decision_a,
        key="w21-plan-a",
        nodes=nodes_a,
    )
    plan_b = _create_plan(
        client,
        project_id=project_b["id"],
        decision_id=decision_b,
        key="w21-plan-b",
        nodes=nodes_b,
    )
    plan_a = _activate(client, project_a["id"], plan_a)
    plan_b = _activate(client, project_b["id"], plan_b)
    dispatched_a = _dispatch(client, project_a["id"], plan_a["id"], plan_a["revision"])
    dispatched_b = _dispatch(client, project_b["id"], plan_b["id"], plan_b["revision"])
    assert dispatched_a["dispatched"][0]["node_key"] == "research"
    assert dispatched_b["dispatched"][0]["node_key"] == "research"
    executed_a = _execute(client, project_a["id"], plan_a["id"])
    executed_b = _execute(client, project_b["id"], plan_b["id"])
    assert executed_a["executed"][0]["task_state"] == "submitted"
    assert executed_b["executed"][0]["task_state"] == "submitted"

    current_a = client.get(f"/api/v1/projects/{project_a['id']}/plans/{plan_a['id']}").json()
    research = next(node for node in current_a["nodes"] if node["node_key"] == "research")
    reviewed = _review(
        client,
        project_id=project_a["id"],
        plan_id=plan_a["id"],
        task_id=research["task_id"],
        revision=research["task_revision"],
        decision="changes_requested",
        summary="补齐证据定位后重做。",
        findings=[
            {
                "code": "MISSING_LOCATOR",
                "severity": "major",
                "message": "缺少可核对定位。",
                "evidence_refs": [],
            }
        ],
        key="w21-review-rework",
    )
    assert reviewed["task_state"] == "rework"
    b_after_rework = client.get(f"/api/v1/projects/{project_b['id']}/plans/{plan_b['id']}").json()
    assert b_after_rework["nodes"][0]["task_state"] == "submitted"
    current_a = client.get(f"/api/v1/projects/{project_a['id']}/plans/{plan_a['id']}").json()
    _dispatch(client, project_a["id"], plan_a["id"], current_a["revision"])
    _execute(client, project_a["id"], plan_a["id"])
    current_a = client.get(f"/api/v1/projects/{project_a['id']}/plans/{plan_a['id']}").json()
    research = next(node for node in current_a["nodes"] if node["node_key"] == "research")
    accepted = _review(
        client,
        project_id=project_a["id"],
        plan_id=plan_a["id"],
        task_id=research["task_id"],
        revision=research["task_revision"],
        decision="accepted",
        summary="重做后通过。",
        key="w21-review-research-accepted",
    )
    assert accepted["task_state"] == "accepted"
    current_a = client.get(f"/api/v1/projects/{project_a['id']}/plans/{plan_a['id']}").json()
    audit_dispatch = _dispatch(
        client,
        project_a["id"],
        plan_a["id"],
        current_a["revision"],
    )
    assert audit_dispatch["dispatched"] == []
    audit_execution = _execute(client, project_a["id"], plan_a["id"])
    assert audit_execution["executed"][0]["task_state"] == "submitted"
    current_a = client.get(f"/api/v1/projects/{project_a['id']}/plans/{plan_a['id']}").json()
    audit = next(node for node in current_a["nodes"] if node["node_key"] == "audit")
    final_review = _review(
        client,
        project_id=project_a["id"],
        plan_id=plan_a["id"],
        task_id=audit["task_id"],
        revision=audit["task_revision"],
        decision="accepted",
        summary="下游独立复核通过。",
        key="w21-review-audit-accepted",
    )
    assert final_review["task_state"] == "accepted"
    raw_version = _upload_raw_data(client, project_a["id"])
    delivered = _create_external_delivery(
        client,
        project_id=project_a["id"],
        raw_version_id=raw_version,
    )
    assert delivered["state"] == "accepted"

    cross_project = client.get(
        f"/api/v1/projects/{project_b['id']}/plans/{plan_a['id']}"
    )
    assert cross_project.status_code == 404

    client.close()
    restarted = _client(settings, session_factory)
    restored_a = restarted.get(
        f"/api/v1/projects/{project_a['id']}/plans/{plan_a['id']}"
    )
    restored_b = restarted.get(
        f"/api/v1/projects/{project_b['id']}/plans/{plan_b['id']}"
    )
    assert restored_a.status_code == 200
    assert restored_a.json()["status"] == "completed"
    assert restored_b.status_code == 200
    assert restored_b.json()["nodes"][0]["task_state"] == "submitted"

    stop_plan = _create_plan(
        restarted,
        project_id=project_a["id"],
        decision_id=decision_a,
        key="w21-stop-plan",
        nodes=[nodes_a[0] | {"purpose": "w21-stop", "input_refs": ["fixture:w21-stop"]}],
    )
    stop_plan = _activate(restarted, project_a["id"], stop_plan)
    stop_plan_id = stop_plan["id"]
    stop_dispatch = _dispatch(
        restarted,
        project_a["id"],
        stop_plan_id,
        stop_plan["revision"],
    )
    stopped = restarted.post(
        f"/api/v1/projects/{project_a['id']}/plans/{stop_plan_id}/stop",
        json={
            "expected_revision": stop_dispatch["plan_revision"],
            "reason": "W21验证停止后不再产生新动作。",
        },
    )
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "stopped"
    assert stopped.json()["nodes"][0]["task_state"] == "cancelled"
    no_execution = restarted.post(
        f"/api/v1/projects/{project_a['id']}/plans/{stop_plan_id}/execute",
        json={"max_tasks": 1},
    )
    assert no_execution.status_code in {409, 422}
    restarted.close()


def _renderer() -> tuple[str, str]:
    soffice = os.getenv("MEDICAL_ONE_OFFICE_SOFFICE_PATH")
    pdftoppm = os.getenv("MEDICAL_ONE_OFFICE_PDFTOPPM_PATH")
    renderer = OfficeRenderer(soffice_path=soffice, pdftoppm_path=pdftoppm)
    if renderer.status().status != "ready":
        pytest.skip("LibreOffice and Poppler are required for W21 real-file verification")
    assert soffice is not None and pdftoppm is not None
    return soffice, pdftoppm


def _reviewed_analysis(client: TestClient, project_id: str) -> str:
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    upload = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads",
        json={
            "filename": "w21-export-dataset.csv",
            "expected_bytes": len(content),
            "media_type_hint": "text/csv",
            "expected_sha256": digest,
        },
    )
    assert upload.status_code == 201, upload.text
    session_id = upload.json()["session_id"]
    assert client.put(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{session_id}/parts/0",
        content=content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Part-SHA256": digest,
        },
    ).status_code == 200
    committed = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{session_id}/commit"
    )
    assert committed.status_code == 200, committed.text
    imported = client.post(
        f"/api/v1/projects/{project_id}/datasets/import",
        headers={"Idempotency-Key": "w21-export-dataset"},
        json={
            "document_version_id": committed.json()["version_id"],
            "title": "W21真实文件合成数据",
            "source_label": "synthetic-w21",
            "synthetic": True,
            "sheet_name": None,
        },
    )
    assert imported.status_code == 201, imported.text
    derived = client.post(
        f"/api/v1/projects/{project_id}/datasets/{imported.json()['id']}/versions",
        headers={"Idempotency-Key": "w21-export-clean"},
        json={
            "parent_version_id": imported.json()["current_version"]["id"],
            "spec": {
                "select_columns": ["group", "score", "response"],
                "numeric_columns": ["score"],
                "rename_columns": {},
                "drop_missing_columns": ["score"],
                "rationale": "W21真实文件导出使用完整主要终点。",
            },
        },
    )
    assert derived.status_code == 201, derived.text
    plan = client.post(
        f"/api/v1/projects/{project_id}/dataset-versions/"
        f"{derived.json()['current_version']['id']}/statistical-plans",
        headers={"Idempotency-Key": "w21-export-plan"},
        json={
            "spec": {
                "question": "W21两组均值差是多少？",
                "endpoint_column": "score",
                "method": "two_group_mean_difference",
                "group_column": "group",
                "analysis_set": "主要终点完整行",
                "missing_policy": "fail_if_missing",
                "unit": "score",
                "alpha": 0.05,
                "expected_groups": ["control", "treatment"],
                "limitations": ["合成数据"],
                "exploratory": False,
            }
        },
    )
    assert plan.status_code == 201, plan.text
    analysis = client.post(
        f"/api/v1/projects/{project_id}/statistical-plans/{plan.json()['id']}/run",
        headers={"Idempotency-Key": "w21-export-run"},
    )
    assert analysis.status_code == 201, analysis.text
    review = client.post(
        f"/api/v1/projects/{project_id}/analyses/{analysis.json()['id']}/review",
        headers={"Idempotency-Key": "w21-export-review"},
        json={
            "reviewer_role": "A14",
            "decision": "accepted",
            "summary": "W21真实文件分析复核。",
            "findings": [],
        },
    )
    assert review.status_code == 200, review.text
    return str(analysis.json()["id"])


def test_w21_real_file_export_survives_restart(
    session_factory: sessionmaker[Session],
    app_database_url: str,
    tmp_path: Path,
) -> None:
    soffice, pdftoppm = _renderer()
    settings = Settings(
        app_mode="mock",
        environment="development",
        database_url=app_database_url,
        artifact_root=tmp_path / "artifacts",
        knowledge_staging_root=tmp_path / "staging",
        run_root=tmp_path / "runs",
        office_soffice_path=soffice,
        office_pdftoppm_path=pdftoppm,
    )
    client = _client(settings, session_factory)
    project = _create_project(client, suffix="真实文件", key="w21-export-project")
    analysis_id = _reviewed_analysis(client, project["id"])
    exported = client.post(
        f"/api/v1/projects/{project['id']}/artifact-exports",
        headers={"Idempotency-Key": "w21-xlsx-export"},
        json={
            "analysis_id": analysis_id,
            "format": "xlsx",
            "title": "W21真实Excel报告",
        },
    )
    assert exported.status_code == 201, exported.text
    assert exported.json()["state"] == "succeeded"
    assert exported.json()["validation_status"] == "passed"
    download_before = client.get(
        f"/api/v1/projects/{project['id']}/artifact-exports/"
        f"{exported.json()['id']}/download"
    )
    assert download_before.status_code == 200
    digest = hashlib.sha256(download_before.content).hexdigest()
    client.close()

    restarted = _client(settings, session_factory)
    download_after = restarted.get(
        f"/api/v1/projects/{project['id']}/artifact-exports/"
        f"{exported.json()['id']}/download"
    )
    assert download_after.status_code == 200
    assert hashlib.sha256(download_after.content).hexdigest() == digest
    restarted.close()
