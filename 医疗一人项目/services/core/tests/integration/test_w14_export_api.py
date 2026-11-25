from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.config import Settings
from medical_one_person.contracts import DependencyStatus
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    ArtifactExport,
    ArtifactVersion,
)
from medical_one_person.infrastructure.exports.renderer import OfficeRenderer
from medical_one_person.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _require_renderer() -> tuple[str, str]:
    soffice = os.getenv("MEDICAL_ONE_OFFICE_SOFFICE_PATH")
    pdftoppm = os.getenv("MEDICAL_ONE_OFFICE_PDFTOPPM_PATH")
    renderer = OfficeRenderer(soffice_path=soffice, pdftoppm_path=pdftoppm)
    if renderer.status().status != "ready":
        pytest.skip("LibreOffice and Poppler are required for W14 API acceptance")
    assert soffice is not None
    assert pdftoppm is not None
    return soffice, pdftoppm


def _create_reviewed_analysis(client: TestClient, project_id: str) -> str:
    content = (PROJECT_ROOT / "fixtures" / "dataset-study-example.csv").read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    upload = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads",
        json={
            "filename": "w14-synthetic-dataset.csv",
            "expected_bytes": len(content),
            "media_type_hint": "text/csv",
            "expected_sha256": digest,
        },
    )
    assert upload.status_code == 201, upload.text
    session_id = upload.json()["session_id"]
    part = client.put(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{session_id}/parts/0",
        content=content,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Part-SHA256": digest,
        },
    )
    assert part.status_code == 200, part.text
    committed = client.post(
        f"/api/v1/projects/{project_id}/knowledge/uploads/{session_id}/commit"
    )
    assert committed.status_code == 200, committed.text
    imported = client.post(
        f"/api/v1/projects/{project_id}/datasets/import",
        headers={"Idempotency-Key": "w14-dataset-import"},
        json={
            "document_version_id": committed.json()["version_id"],
            "title": "W14 API合成数据",
            "source_label": "synthetic-w14",
            "synthetic": True,
            "sheet_name": None,
        },
    )
    assert imported.status_code == 201, imported.text
    derived = client.post(
        f"/api/v1/projects/{project_id}/datasets/{imported.json()['id']}/versions",
        headers={"Idempotency-Key": "w14-dataset-clean"},
        json={
            "parent_version_id": imported.json()["current_version"]["id"],
            "spec": {
                "select_columns": ["group", "score", "response"],
                "numeric_columns": ["score"],
                "rename_columns": {},
                "drop_missing_columns": ["score"],
                "rationale": "W14导出测试使用主要终点完整行。",
            },
        },
    )
    assert derived.status_code == 201, derived.text
    version_id = derived.json()["current_version"]["id"]
    plan = client.post(
        f"/api/v1/projects/{project_id}/dataset-versions/{version_id}/statistical-plans",
        headers={"Idempotency-Key": "w14-stat-plan"},
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
        f"/api/v1/projects/{project_id}/statistical-plans/{plan.json()['id']}/run",
        headers={"Idempotency-Key": "w14-stat-run"},
    )
    assert analysis.status_code == 201, analysis.text
    assert analysis.json()["result"]["difference"] == -5
    review = client.post(
        f"/api/v1/projects/{project_id}/analyses/{analysis.json()['id']}/review",
        headers={"Idempotency-Key": "w14-stat-review"},
        json={
            "reviewer_role": "A14",
            "decision": "accepted",
            "summary": "合成W14统计报告复核记录。",
            "findings": [],
        },
    )
    assert review.status_code == 200, review.text
    return str(analysis.json()["id"])


def test_w14_export_api_persists_versions_and_verified_files(
    session_factory: sessionmaker[Session],
    app_database_url: str,
    tmp_path: Path,
) -> None:
    soffice, pdftoppm = _require_renderer()
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
    app = create_app(
        database_checker=lambda: DependencyStatus(
            status="ready",
            detail="W14 API integration",
        ),
        settings_override=settings,
        session_factory_override=session_factory,
    )
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    assert client.post("/api/v1/system/local-session").status_code == 200
    principal = client.get("/api/v1/system/session").json()
    project_response = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w14-api-project"},
        json={"name": "W14 API项目", "scope": "验证Office与PDF导出合同。"},
    )
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]
    analysis_id = _create_reviewed_analysis(client, project_id)

    runtime = client.get(
        f"/api/v1/projects/{project_id}/artifact-exports/runtime"
    )
    assert runtime.status_code == 200, runtime.text
    assert runtime.json()["status"] == "ready"
    assert {item["format"] for item in runtime.json()["templates"]} == {
        "docx",
        "pptx",
        "xlsx",
        "pdf",
    }

    payload = {
        "analysis_id": analysis_id,
        "format": "xlsx",
        "title": "W14 API 分析报告",
    }
    first = client.post(
        f"/api/v1/projects/{project_id}/artifact-exports",
        headers={"Idempotency-Key": "w14-xlsx-export"},
        json=payload,
    )
    assert first.status_code == 201, first.text
    exported = first.json()
    assert exported["state"] == "succeeded"
    assert exported["validation_status"] == "passed"
    assert exported["data_origin"] == "synthetic"
    assert exported["artifact_version_id"]
    assert exported["page_count"] == 5
    formula_checks = exported["validation"]["formula_checks"]
    assert len(formula_checks) == 2
    assert all(item["status"] == "passed" for item in formula_checks)

    replay = client.post(
        f"/api/v1/projects/{project_id}/artifact-exports",
        headers={"Idempotency-Key": "w14-xlsx-export"},
        json=payload,
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == exported["id"]
    assert replay.json()["art_sha256"] == exported["art_sha256"]

    conflict = client.post(
        f"/api/v1/projects/{project_id}/artifact-exports",
        headers={"Idempotency-Key": "w14-xlsx-export"},
        json={**payload, "format": "pdf"},
    )
    assert conflict.status_code == 409

    download = client.get(
        f"/api/v1/projects/{project_id}/artifact-exports/{exported['id']}/download"
    )
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert download.headers["cache-control"] == "private, no-store"
    workbook_path = tmp_path / "downloaded.xlsx"
    workbook_path.write_bytes(download.content)
    value_workbook = load_workbook(workbook_path, data_only=True)
    assert value_workbook["导出核对"]["B5"].value == pytest.approx(-5)

    preview = client.get(
        f"/api/v1/projects/{project_id}/artifact-exports/{exported['id']}/preview.png"
    )
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.content.startswith(b"\x89PNG\r\n\x1a\n")

    pdf_export = client.post(
        f"/api/v1/projects/{project_id}/artifact-exports",
        headers={"Idempotency-Key": "w14-pdf-export"},
        json={**payload, "format": "pdf"},
    )
    assert pdf_export.status_code == 201, pdf_export.text
    assert pdf_export.json()["state"] == "succeeded"
    pdf_preview = client.get(
        f"/api/v1/projects/{project_id}/artifact-exports/"
        f"{pdf_export.json()['id']}/preview.pdf"
    )
    assert pdf_preview.status_code == 200
    assert pdf_preview.content.startswith(b"%PDF-")

    other_project = client.post(
        "/api/v1/projects",
        headers={"Idempotency-Key": "w14-other-project"},
        json={"name": "W14隔离项目", "scope": "验证导出不能跨项目读取。"},
    )
    assert other_project.status_code == 201, other_project.text
    other_project_id = other_project.json()["id"]
    assert client.get(
        f"/api/v1/projects/{other_project_id}/artifact-exports"
    ).json() == []
    cross_project_download = client.get(
        f"/api/v1/projects/{other_project_id}/artifact-exports/"
        f"{exported['id']}/download"
    )
    assert cross_project_download.status_code == 404

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=principal["workspace_id"],
            user_id=principal["user_id"],
        )
        assert session.scalar(select(func.count()).select_from(ArtifactExport)) == 2
        assert session.scalar(select(func.count()).select_from(ArtifactVersion)) == 2


def test_w14_artifact_exports_use_forced_rls(database: Engine) -> None:
    with database.connect() as connection:
        state = connection.execute(
            text(
                """
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = 'artifact_exports'
                """
            )
        ).one()
        policy_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'artifact_exports'
                """
            )
        )
    assert state.relrowsecurity is True
    assert state.relforcerowsecurity is True
    assert policy_count == 1
