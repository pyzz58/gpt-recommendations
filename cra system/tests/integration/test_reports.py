"""Real-PostgreSQL and actual Office-file acceptance for CRA-W11."""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from cra_app.documents.service import CreateDocumentCommand, DocumentService
from cra_app.documents.storage import build_private_storage
from cra_app.governance.identity import SyntheticIdentityProvider
from cra_app.governance.service import (
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.issues.service import IssueService
from cra_app.main import create_app
from cra_app.monitoring.service import MonitoringService
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.reports.docx_export import docx_text
from cra_app.rules.common_policy import load_common_policy_set
from cra_app.rules.service import RuleService
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.site_files.service import SiteFileService
from cra_app.subjects.contracts import (
    CoverageBreakpointCommand,
    CreateSubjectCommand,
)
from cra_app.subjects.service import SubjectService

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "reports"
ARTIFACTS = FIXTURES / "artifacts"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W11 never falls back to SQLite"
        )
    return value


@pytest.fixture(scope="session")
def engine():
    db_engine = build_engine(_database_url())
    with db_engine.connect() as connection:
        assert str(connection.scalar(text("SHOW server_version"))).startswith(
            "18."
        )
    yield db_engine
    db_engine.dispose()


@pytest.fixture(scope="session")
def queue():
    adapter = ProcrastinateQueue(_database_url())
    adapter.ensure_schema()
    return adapter


@pytest.fixture
def session_factory(engine, queue):
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE report_events, report_exports, "
                "report_snapshots, report_draft_history, report_drafts, "
                "report_template_versions, stage_checklist_history, "
                "stage_checklist_items, stage_checklists, site_file_history, "
                "site_file_items, site_directory_references, "
                "monitoring_visit_selections, monitoring_visits, query_links, "
                "issue_history, issue_actions, issues, "
                "fact_change_impacts, check_decisions, coverage_breakpoints, "
                "visit_requirements, visit_instances, clinical_facts, "
                "subject_identifiers, subjects, rule_relations, "
                "rule_source_refs, rule_extraction_coverage, "
                "version_activations, rule_versions, rules, rule_snapshots, "
                "outbox_events, business_jobs, parse_coverage, "
                "source_anchors, document_versions, source_documents, "
                "idempotency_records, audit_events, memberships, sites, "
                "studies CASCADE"
            )
        )
        connection.execute(
            text(
                "TRUNCATE TABLE procrastinate_events, procrastinate_jobs, "
                "procrastinate_workers, procrastinate_periodic_defers CASCADE"
            )
        )
    return build_session_factory(engine)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        CRA_ENV="test",
        CRA_DATABASE_URL=_database_url(),
        CRA_SESSION_SECRET="synthetic-w11-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
        CRA_COMMON_POLICY_PATH="tests/fixtures/rules/common_policy.json",
        CRA_MODEL_PROVIDER="disabled",
        CRA_OCR_PROVIDER="disabled",
        CRA_ANALYSIS_PROVIDER="disabled",
    )


@pytest.fixture
def services(session_factory, settings, queue):
    governance = GovernanceService(session_factory)
    admin = ScopeContext(
        actor_id="synthetic-admin",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
        platform_roles=frozenset({"platform_admin"}),
    )
    study = governance.create_study(
        admin,
        CreateStudy(
            expected_revision=0,
            idempotency_key="w11-study",
            code="W11-SYN",
            title="W11 Synthetic Reporting",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w11-site-a",
            code="A11",
            name="Synthetic W11 Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w11-site-b",
            code="B11",
            name="Synthetic W11 Site B",
        ),
    )
    for actor, site in (
        ("synthetic-cra-a", site_a.resource_id),
        ("synthetic-cra-b", site_b.resource_id),
    ):
        governance.grant_membership(
            admin,
            study.resource_id,
            GrantMembership(
                expected_revision=0,
                idempotency_key=f"w11-grant-{actor}",
                actor_id=actor,
                role="cra",
                site_id=site,
                can_write=True,
            ),
        )
    documents = DocumentService(
        session_factory,
        storage=build_private_storage(settings),
        queue=queue,
        governance=governance,
    )
    rules = RuleService(
        session_factory,
        governance=governance,
        common_policy_set=load_common_policy_set(
            settings.common_policy_path
        ),
    )
    subjects = SubjectService(
        session_factory, governance=governance, rules=rules
    )
    issues = IssueService(
        session_factory,
        governance=governance,
        documents=documents,
    )
    monitoring = MonitoringService(
        session_factory,
        issues=issues,
        documents=documents,
        governance=governance,
    )
    site_files = SiteFileService(
        session_factory,
        governance=governance,
        documents=documents,
        issues=issues,
        monitoring=monitoring,
    )
    return {
        "governance": governance,
        "admin": admin,
        "study": study.resource_id,
        "site_a": site_a.resource_id,
        "site_b": site_b.resource_id,
        "documents": documents,
        "rules": rules,
        "subjects": subjects,
        "issues": issues,
        "monitoring": monitoring,
        "site_files": site_files,
    }


@pytest.fixture
def api(settings, session_factory, services):
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
        document_service=services["documents"],
        rule_service=services["rules"],
        subject_service=services["subjects"],
        issue_service=services["issues"],
        monitoring_service=services["monitoring"],
        site_file_service=services["site_files"],
    )
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _headers(api: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": api.cookies.get("cra_csrf")}


def _scope(services: dict) -> ScopeContext:
    return ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )


def _upload_template(
    services: dict,
    *,
    key: str,
    filename: str,
    content: bytes,
):
    return services["documents"].create_document(
        _scope(services),
        services["study"],
        CreateDocumentCommand(
            expected_revision=0,
            idempotency_key=f"w11-{key}",
            title=f"Synthetic template {key}",
            document_type="template",
            purpose="template",
            version_label="v1",
            site_id=services["site_a"],
        ),
        filename=filename,
        content=content,
    )


def _create_template(api: TestClient, services: dict, *, kind: str):
    artifact = {
        "letter": "synthetic_visit_letter.docx",
        "report": "synthetic_monitoring_report.docx",
        "track": "synthetic_track_template.xlsx",
    }[kind]
    upload = _upload_template(
        services,
        key=f"{kind}-template",
        filename=artifact,
        content=(ARTIFACTS / artifact).read_bytes(),
    )
    if kind == "track":
        mapping = {
            "output_kind": "track",
            "output_format": "xlsx",
            "xlsx": {
                "cells": {},
                "table": {
                    "sheet": "Track",
                    "start_row": 2,
                    "columns": {
                        "A": "issue_number",
                        "B": "section",
                        "C": "original_finding",
                        "D": "location",
                        "E": "recommendation",
                        "F": "status",
                        "G": "known_progress",
                        "H": "next_steps_text",
                        "I": "source_refs_text",
                    },
                },
                "required_variables": [],
            },
        }
    else:
        fields = {
            "study_code": "study_code",
            "site_code": "site_code",
            "site_name": "site_name",
            "visit_title": "visit_title",
            "generated_on": "generated_on",
            "visit_scope_note": "visit_scope_note",
            "coverage_summary": "coverage_summary",
            "not_checked_summary": "not_checked_summary",
            "next_steps_summary": "next_steps_summary",
            "user_summary": "user_summary",
            "user_conclusion": "user_conclusion",
        }
        loops = (
            {"letter_issues": "letter_issues"}
            if kind == "letter"
            else {
                "prior_issues": "prior_issues",
                "current_findings": "current_findings",
            }
        )
        mapping = {
            "output_kind": kind,
            "output_format": "docx",
            "docx": {
                "fields": fields,
                "loops": loops,
                "required_variables": (
                    ["study_code"]
                    if kind == "letter"
                    else ["study_code", "user_summary", "user_conclusion"]
                ),
            },
        }
    response = api.post(
        "/api/v1/template-versions",
        json={
            "expected_revision": 0,
            "idempotency_key": f"map-{kind}",
            "source_document_version_id": str(upload.document_version_id),
            "title": f"Synthetic {kind} template",
            "mapping": mapping,
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_issue(
    api: TestClient,
    services: dict,
    *,
    number: str,
    finding: str,
    location: str,
):
    response = api.post(
        f"/api/v1/studies/{services['study']}/issues",
        json={
            "expected_revision": 0,
            "idempotency_key": f"issue-{number}",
            "site_id": str(services["site_a"]),
            "issue_number": number,
            "original_finding": finding,
            "location": location,
            "recommendation": f"Correct {number}.",
            "recommendation_sources": [
                {"text": "Synthetic monitoring plan", "official_status": "unknown"}
            ],
            "known_progress": "Synthetic progress before visit.",
            "source_kind": "manual",
            "source_refs": [{"locator": f"Synthetic {number} row"}],
            "actions": [
                {
                    "action_key": "CORRECT",
                    "kind": "edc_correction",
                    "requirement": f"Correct the synthetic source for {number}.",
                }
            ],
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_visit(api: TestClient, services: dict):
    response = api.post(
        f"/api/v1/studies/{services['study']}/monitoring-visits",
        json={
            "expected_revision": 0,
            "idempotency_key": "w11-monitoring-visit",
            "site_id": str(services["site_a"]),
            "stage": "handover",
            "title": "Synthetic W11 monitoring visit",
            "scope_note": "Synthetic consent and laboratory partial review.",
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    return response.json()["visit"]


def _create_subject_and_coverage(services: dict):
    subject = services["subjects"].create_subject(
        _scope(services),
        services["study"],
        CreateSubjectCommand(
            expected_revision=0,
            idempotency_key="w11-subject",
            site_id=services["site_a"],
            external_id="W11-S001",
            identity_namespace="synthetic-edc",
            deidentified_label="Synthetic Subject 001",
        ),
    )
    coverage = services["subjects"].save_coverage(
        _scope(services),
        subject.id,
        CoverageBreakpointCommand(
            expected_revision=0,
            idempotency_key="w11-coverage",
            category="laboratory",
            scope_key="synthetic-visit-1",
            status="not_checked",
            unverified_scope=["Synthetic lab shift not reviewed"],
        ),
    )
    return subject, coverage


def test_letter_report_snapshot_and_track_are_consistent(
    api: TestClient, services: dict, engine
):
    letter_template = _create_template(api, services, kind="letter")
    report_template = _create_template(api, services, kind="report")
    track_template = _create_template(api, services, kind="track")

    prior = [
        _create_issue(
            api,
            services,
            number=f"W11-P0{index}",
            finding=f"Synthetic prior finding {index}",
            location=f"Synthetic row P0{index}",
        )
        for index in range(1, 4)
    ]
    visit = _create_visit(api, services)
    current = _create_issue(
        api,
        services,
        number="W11-C01",
        finding="Synthetic current finding",
        location="Synthetic row C01",
    )
    subject, coverage = _create_subject_and_coverage(services)
    assert coverage.status == "not_checked"

    letter_response = api.post(
        "/api/v1/letters/draft",
        json={
            "expected_revision": 0,
            "idempotency_key": "w11-letter-draft",
            "monitoring_visit_id": visit["id"],
            "template_version_id": letter_template["id"],
            "selected_issue_ids": [prior[0]["id"], prior[1]["id"]],
        },
        headers=_headers(api),
    )
    assert letter_response.status_code == 200, letter_response.text
    letter = letter_response.json()
    assert len(letter["content"]["letter_issues"]) == 2
    assert [
        item["issue_number"] for item in letter["content"]["letter_issues"]
    ] == ["W11-P01", "W11-P02"]
    full_list = api.get(
        f"/api/v1/studies/{services['study']}/issues?site_id={services['site_a']}"
    )
    assert full_list.status_code == 200
    assert len(full_list.json()) == 4

    report_response = api.post(
        "/api/v1/reports/draft",
        json={
            "expected_revision": 0,
            "idempotency_key": "w11-report-draft",
            "monitoring_visit_id": visit["id"],
            "template_version_id": report_template["id"],
        },
        headers=_headers(api),
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert report["missing_fields"] == ["user_summary", "user_conclusion"]
    assert [
        item["issue_number"] for item in report["content"]["prior_issues"]
    ] == ["W11-P01", "W11-P02", "W11-P03"]
    assert [
        item["issue_number"] for item in report["content"]["current_findings"]
    ] == ["W11-C01"]
    assert report["not_checked"][0]["subject_label"] == (
        "Synthetic Subject 001"
    )
    assert "全部正常" not in report["content"]["scope_notice"]
    assert "全中心无异常" not in report["content"]["scope_notice"]

    updated = api.post(
        f"/api/v1/report-drafts/{report['id']}/text",
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w11-report-text",
            "text_updates": {
                "summary": "CRA确认本次合成监查范围有限。",
                "conclusion": "未覆盖项目不形成正常结论。",
            },
            "status": "ready",
        },
        headers=_headers(api),
    )
    assert updated.status_code == 200, updated.text
    report = updated.json()
    assert report["missing_fields"] == []

    no_ack = api.post(
        f"/api/v1/reports/{report['id']}/snapshot",
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w11-report-snapshot-no-ack",
            "status": "issued",
            "user_statement": "CRA确认本合成报告已签发。",
        },
        headers=_headers(api),
    )
    assert no_ack.status_code == 422

    snapshot_response = api.post(
        f"/api/v1/reports/{report['id']}/snapshot",
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w11-report-snapshot",
            "status": "issued",
            "acknowledge_unknowns": True,
            "user_statement": "CRA确认本合成报告已签发。",
        },
        headers=_headers(api),
    )
    assert snapshot_response.status_code == 200, snapshot_response.text
    snapshot = snapshot_response.json()
    assert snapshot["status"] == "issued"
    assert snapshot["unknown_acknowledged"] is True
    submitted = api.post(
        f"/api/v1/report-snapshots/{snapshot['id']}/events",
        json={
            "expected_revision": 0,
            "idempotency_key": "w11-report-submitted",
            "event_type": "submitted",
            "user_statement": "CRA确认合成报告已按项目流程提交。",
        },
        headers=_headers(api),
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["events"][0]["event_type"] == "submitted"

    letter_snapshot = api.post(
        f"/api/v1/reports/{letter['id']}/snapshot",
        json={
            "expected_revision": letter["revision"],
            "idempotency_key": "w11-letter-snapshot",
            "status": "prepared",
            "acknowledge_unknowns": False,
        },
        headers=_headers(api),
    )
    assert letter_snapshot.status_code == 200, letter_snapshot.text

    exports = {}
    for key, snapshot_id, template_id in (
        ("report", snapshot["id"], report_template["id"]),
        ("track", snapshot["id"], track_template["id"]),
        (
            "letter",
            letter_snapshot.json()["id"],
            letter_template["id"],
        ),
    ):
        response = api.post(
            "/api/v1/exports",
            json={
                "expected_revision": 0,
                "idempotency_key": f"w11-export-{key}",
                "snapshot_id": snapshot_id,
                "template_version_id": template_id,
            },
            headers=_headers(api),
        )
        assert response.status_code == 200, response.text
        exports[key] = response.json()
        assert response.json()["actual_send_status"] == "not_sent"

    report_download = api.get(exports["report"]["content_url"])
    assert report_download.status_code == 200
    assert report_download.content.startswith(b"PK")
    report_text = docx_text(report_download.content)
    for issue_number in ("W11-P01", "W11-P02", "W11-P03", "W11-C01"):
        assert issue_number in report_text
    assert "CRA确认本次合成监查范围有限" in report_text
    assert "Synthetic lab shift not reviewed" in report_text

    letter_download = api.get(exports["letter"]["content_url"])
    letter_text = docx_text(letter_download.content)
    assert "W11-P01" in letter_text
    assert "W11-P02" in letter_text
    assert "W11-P03" not in letter_text
    assert "W11-C01" not in letter_text

    track_download = api.get(exports["track"]["content_url"])
    workbook = load_workbook(BytesIO(track_download.content), data_only=True)
    try:
        rows = list(workbook["Track"].iter_rows(min_row=2, values_only=True))
    finally:
        workbook.close()
    assert [row[0] for row in rows] == [
        "W11-P01",
        "W11-P02",
        "W11-P03",
        "W11-C01",
    ]
    assert all(row[5] == "open" for row in rows)
    assert len(exports["track"]["row_refs"]) == 4

    original_hash = snapshot["content_hash"]
    action = prior[0]["actions"][0]
    confirmed = api.post(
        "/api/v1/actions/confirm-corrected",
        json={
            "idempotency_key": "w11-confirm-prior-action",
            "actions": [
                {
                    "action_id": action["id"],
                    "expected_revision": action["revision"],
                }
            ],
            "optional_note": "Synthetic completion after report issue.",
        },
        headers=_headers(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    unchanged = api.get(f"/api/v1/report-snapshots/{snapshot['id']}")
    assert unchanged.status_code == 200
    assert unchanged.json()["content_hash"] == original_hash
    assert unchanged.json()["content"]["prior_issues"][0]["status"] == "open"

    new_report = api.post(
        "/api/v1/reports/draft",
        json={
            "expected_revision": 0,
            "idempotency_key": "w11-report-draft-after-change",
            "monitoring_visit_id": visit["id"],
            "template_version_id": report_template["id"],
        },
        headers=_headers(api),
    )
    assert new_report.status_code == 200, new_report.text
    new_report_body = new_report.json()
    assert new_report_body["content"]["prior_issues"][0]["status"] == (
        "completed"
    )
    new_snapshot = api.post(
        f"/api/v1/reports/{new_report_body['id']}/snapshot",
        json={
            "expected_revision": new_report_body["revision"],
            "idempotency_key": "w11-report-snapshot-after-change",
            "status": "prepared",
            "acknowledge_unknowns": False,
        },
        headers=_headers(api),
    )
    assert new_snapshot.status_code == 200, new_snapshot.text
    new_track = api.post(
        "/api/v1/exports",
        json={
            "expected_revision": 0,
            "idempotency_key": "w11-export-track-after-change",
            "snapshot_id": new_snapshot.json()["id"],
            "template_version_id": track_template["id"],
        },
        headers=_headers(api),
    )
    assert new_track.status_code == 200, new_track.text
    new_track_download = api.get(new_track.json()["content_url"])
    new_workbook = load_workbook(
        BytesIO(new_track_download.content), data_only=True
    )
    try:
        first_new_row = [
            cell.value
            for cell in new_workbook["Track"][2]
        ]
    finally:
        new_workbook.close()
    assert first_new_row[0] == "W11-P01"
    assert first_new_row[5] == "completed"

    with pytest.raises(SQLAlchemyError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE report_snapshots "
                    "SET content_hash = 'rewritten'"
                )
            )


def test_unsafe_docx_template_expression_is_rejected(
    api: TestClient, services: dict
):
    document = Document()
    document.add_paragraph("{{ __class__ }}")
    buffer = BytesIO()
    document.save(buffer)
    upload = _upload_template(
        services,
        key="unsafe-template",
        filename="unsafe.docx",
        content=buffer.getvalue(),
    )
    response = api.post(
        "/api/v1/template-versions",
        json={
            "expected_revision": 0,
            "idempotency_key": "unsafe-template-map",
            "source_document_version_id": str(upload.document_version_id),
            "title": "Unsafe synthetic template",
            "mapping": {
                "output_kind": "report",
                "output_format": "docx",
                "docx": {
                    "fields": {},
                    "loops": {},
                    "required_variables": [],
                },
            },
        },
        headers=_headers(api),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "report_validation_failed"


def test_report_routes_are_in_openapi(
    api: TestClient,
):
    schema = api.get("/api/v1/openapi.json").json()
    assert "/api/v1/letters/draft" in schema["paths"]
    assert "/api/v1/reports/draft" in schema["paths"]
    assert "/api/v1/exports" in schema["paths"]
    assert "/api/v1/report-exports/{export_id}/content" in schema["paths"]
