"""Real-PostgreSQL acceptance for file/text-based carryover import previews."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from cra_app.documents.service import DocumentService
from cra_app.documents.storage import build_private_storage
from cra_app.governance.identity import SyntheticIdentityProvider
from cra_app.governance.service import (
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.issues.models import CarryoverImport, Issue, IssueHistory
from cra_app.issues.service import IssueService
from cra_app.main import create_app
from cra_app.monitoring.service import MonitoringService
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ISSUE_FIXTURES = FIXTURES / "issues" / "artifacts"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W06 never falls back to SQLite"
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
                "TRUNCATE TABLE carryover_candidates, carryover_imports, "
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
        CRA_SESSION_SECRET="synthetic-w06-carryover-session",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
        CRA_COMMON_POLICY_PATH=str(
            FIXTURES / "rules" / "common_policy.json"
        ),
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
            idempotency_key="w06-carry-study",
            code="W06-CARRY",
            title="W06 Synthetic Carryover",
        ),
    )
    site = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w06-carry-site",
            code="A01",
            name="Synthetic Carryover Site",
        ),
    )
    governance.grant_membership(
        admin,
        study.resource_id,
        GrantMembership(
            expected_revision=0,
            idempotency_key="w06-carry-grant",
            actor_id="synthetic-cra-a",
            role="cra",
            site_id=site.resource_id,
            can_write=True,
        ),
    )
    documents = DocumentService(
        session_factory,
        storage=build_private_storage(settings),
        queue=queue,
        governance=governance,
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
    return {
        "governance": governance,
        "study": study.resource_id,
        "site": site.resource_id,
        "documents": documents,
        "issues": issues,
        "monitoring": monitoring,
    }


@pytest.fixture
def api(settings, session_factory, services):
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
        document_service=services["documents"],
        issue_service=services["issues"],
        monitoring_service=services["monitoring"],
    )
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _headers(api: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": api.cookies.get("cra_csrf")}


def _upload(
    api: TestClient,
    services: dict,
    *,
    filename: str,
    purpose: str,
    document_type: str,
    key: str,
) -> dict:
    response = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={
            "file": (
                filename,
                (ISSUE_FIXTURES / filename).read_bytes(),
                "application/octet-stream",
            )
        },
        data={
            "title": f"Synthetic {filename}",
            "document_type": document_type,
            "purpose": purpose,
            "version_label": "v1",
            "expected_revision": "0",
            "site_id": str(services["site"]),
        },
        headers={
            "Idempotency-Key": key,
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert response.status_code == 202, response.text
    body = response.json()
    services["documents"].process_job(uuid.UUID(body["job_id"]))
    return body


def _preview_document(
    api: TestClient,
    services: dict,
    version_id: str,
    key: str,
):
    return api.post(
        f"/api/v1/document-versions/{version_id}/carryover-imports/preview",
        json={
            "expected_revision": 0,
            "idempotency_key": key,
            "site_id": str(services["site"]),
        },
        headers=_headers(api),
    )


def test_docx_preview_confirmation_replay_and_preserved_source(
    api: TestClient, services: dict, session_factory
):
    uploaded = _upload(
        api,
        services,
        filename="synthetic_carryover_report.docx",
        purpose="carryover_report",
        document_type="report",
        key="carryover-docx-upload",
    )
    preview = _preview_document(
        api, services, uploaded["document_version_id"], "carryover-docx-preview"
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["import_record"]["source_kind"] == "document"
    assert body["import_record"]["state"] == "preview"
    assert [item["original_issue_number"] for item in body["candidates"]] == [
        "CRA-SYN-101",
        "CRA-SYN-102",
    ]
    first, second = body["candidates"]
    assert first["location"] == "Consent form, signature date"
    assert first["source_refs"]
    assert first["actions"][0]["kind"] == "edc_correction"
    assert {"location", "recommendation"}.issubset(second["unknown_fields"])

    confirmed = api.post(
        f"/api/v1/carryover-imports/{body['import_record']['id']}/confirm",
        json={
            "expected_revision": body["import_record"]["revision"],
            "idempotency_key": "carryover-docx-confirm",
            "corrections": [
                {
                    "candidate_id": second["id"],
                    "location": "Synthetic safety report",
                    "recommendation": (
                        "Clarify the synthetic reporting status before assuming "
                        "completion."
                    ),
                }
            ],
        },
        headers=_headers(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_body = confirmed.json()
    assert confirmed_body["import_record"]["state"] == "confirmed"
    assert {item["state"] for item in confirmed_body["candidates"]} == {
        "imported"
    }
    issue_list = api.get(
        f"/api/v1/studies/{services['study']}/issues",
        params={"site_id": str(services["site"])},
    )
    assert issue_list.status_code == 200, issue_list.text
    issues = issue_list.json()
    assert {item["issue_number"] for item in issues} == {
        "CRA-SYN-101",
        "CRA-SYN-102",
    }
    synth_102 = next(
        item for item in issues if item["issue_number"] == "CRA-SYN-102"
    )
    assert synth_102["location"] == "Synthetic safety report"
    assert "synthetic reporting status" in synth_102["recommendation"]
    assert synth_102["source_document_version_id"] == uploaded[
        "document_version_id"
    ]

    replay_preview = _preview_document(
        api, services, uploaded["document_version_id"], "carryover-docx-again"
    )
    assert replay_preview.status_code == 200, replay_preview.text
    assert replay_preview.json()["replayed"] is True
    assert replay_preview.json()["import_record"]["id"] == body["import_record"]["id"]

    replay_confirm = api.post(
        f"/api/v1/carryover-imports/{body['import_record']['id']}/confirm",
        json={
            "expected_revision": body["import_record"]["revision"],
            "idempotency_key": "carryover-docx-confirm",
            "corrections": [
                {
                    "candidate_id": second["id"],
                    "location": "Synthetic safety report",
                    "recommendation": (
                        "Clarify the synthetic reporting status before assuming "
                        "completion."
                    ),
                }
            ],
        },
        headers=_headers(api),
    )
    assert replay_confirm.status_code == 200, replay_confirm.text
    assert replay_confirm.json()["replayed"] is True
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Issue)) == 2
        assert (
            session.scalar(select(func.count()).select_from(CarryoverImport))
            == 1
        )


def test_xlsx_track_reuses_exact_number_and_keeps_unknowns(
    api: TestClient, services: dict, session_factory
):
    docx = _upload(
        api,
        services,
        filename="synthetic_carryover_report.docx",
        purpose="carryover_report",
        document_type="report",
        key="xlsx-reuse-docx-upload",
    )
    preview_docx = _preview_document(
        api, services, docx["document_version_id"], "xlsx-reuse-docx-preview"
    ).json()
    assert api.post(
        f"/api/v1/carryover-imports/{preview_docx['import_record']['id']}/confirm",
        json={
            "expected_revision": preview_docx["import_record"]["revision"],
            "idempotency_key": "xlsx-reuse-docx-confirm",
            "corrections": [],
        },
        headers=_headers(api),
    ).status_code == 200

    xlsx = _upload(
        api,
        services,
        filename="synthetic_carryover_track.xlsx",
        purpose="track",
        document_type="track",
        key="carryover-xlsx-upload",
    )
    preview = _preview_document(
        api, services, xlsx["document_version_id"], "carryover-xlsx-preview"
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    candidates = {
        item["original_issue_number"]: item for item in body["candidates"]
    }
    assert set(candidates) == {"CRA-SYN-101", "CRA-SYN-103"}
    assert {"location", "recommendation"}.issubset(
        candidates["CRA-SYN-103"]["unknown_fields"]
    )
    assert any(
        ref["source_type"] == "xlsx_cell"
        and ref["sheet"] == "Carryover"
        for ref in candidates["CRA-SYN-103"]["source_refs"]
    )
    confirmed = api.post(
        f"/api/v1/carryover-imports/{body['import_record']['id']}/confirm",
        json={
            "expected_revision": body["import_record"]["revision"],
            "idempotency_key": "carryover-xlsx-confirm",
            "corrections": [
                {
                    "candidate_id": candidates["CRA-SYN-103"]["id"],
                    "location": "Synthetic training folder",
                    "recommendation": (
                        "Supply the synthetic training record if the current "
                        "project requirement applies."
                    ),
                }
            ],
        },
        headers=_headers(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    states = {
        item["original_issue_number"]: item["state"]
        for item in confirmed.json()["candidates"]
    }
    assert states == {"CRA-SYN-101": "reused", "CRA-SYN-103": "imported"}
    issues = api.get(
        f"/api/v1/studies/{services['study']}/issues",
        params={"site_id": str(services["site"])},
    ).json()
    by_number = {item["issue_number"]: item for item in issues}
    assert set(by_number) == {"CRA-SYN-101", "CRA-SYN-102", "CRA-SYN-103"}
    reused = by_number["CRA-SYN-101"]
    assert sum(
        event["event_type"] == "carryover_imported"
        for event in reused["history"]
    ) >= 2
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Issue)) == 3
        history_count = session.scalar(
            select(func.count())
            .select_from(IssueHistory)
            .where(IssueHistory.issue_id == uuid.UUID(reused["id"]))
        )
        assert history_count and history_count >= 2


def test_text_preview_requires_user_correction_and_does_not_invent_fields(
    api: TestClient, services: dict
):
    text_source = (
        "Issue ID: CRA-SYN-104\n"
        "Finding: Synthetic source note lacks recommendation and action.\n"
        "Known Progress: No prior action recorded.\n"
    )
    preview = api.post(
        f"/api/v1/studies/{services['study']}/carryover-imports/preview-text",
        json={
            "expected_revision": 0,
            "idempotency_key": "carryover-text-preview",
            "site_id": str(services["site"]),
            "source_label": "synthetic issue note",
            "text": text_source,
        },
        headers=_headers(api),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    candidate = body["candidates"][0]
    assert candidate["original_issue_number"] == "CRA-SYN-104"
    assert candidate["location"] is None
    assert candidate["recommendation"] is None
    assert {"location", "recommendation", "actions"}.issubset(
        candidate["unknown_fields"]
    )
    assert candidate["source_refs"][0]["source_type"] == "document_anchor"
    confirmed = api.post(
        f"/api/v1/carryover-imports/{body['import_record']['id']}/confirm",
        json={
            "expected_revision": body["import_record"]["revision"],
            "idempotency_key": "carryover-text-confirm",
            "corrections": [
                {
                    "candidate_id": candidate["id"],
                    "location": "Synthetic note row 2",
                    "recommendation": (
                        "Clarify the synthetic source requirement with the CRA."
                    ),
                    "actions": [
                        {
                            "action_key": "A1",
                            "kind": "medical_clarification",
                            "requirement": "Resolve the synthetic ambiguity.",
                        }
                    ],
                }
            ],
        },
        headers=_headers(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    issues = api.get(
        f"/api/v1/studies/{services['study']}/issues",
        params={"site_id": str(services["site"])},
    ).json()
    issue = next(
        item for item in issues if item["issue_number"] == "CRA-SYN-104"
    )
    assert issue["source_kind"] == "text"
    assert issue["actions"][0]["kind"] == "medical_clarification"
    assert issue["source_refs"][0]["locator"].startswith(
        "synthetic issue note:line["
    )
