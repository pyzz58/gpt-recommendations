"""Real-PostgreSQL acceptance for CRA-W10 site files and stage checklists."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
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
from cra_app.site_files.service import SiteFileService
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory

pytestmark = pytest.mark.postgres


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W10 never falls back to SQLite"
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
                "TRUNCATE TABLE stage_checklist_history, "
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
        CRA_SESSION_SECRET="synthetic-w10-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
        CRA_MODEL_PROVIDER="disabled",
        CRA_OCR_PROVIDER="disabled",
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
            idempotency_key="w10-study",
            code="W10-SYN",
            title="W10 Synthetic Site Files",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w10-site-a",
            code="A01",
            name="Synthetic W10 Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w10-site-b",
            code="B01",
            name="Synthetic W10 Site B",
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
                idempotency_key=f"w10-grant-{actor}",
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
        issue_service=services["issues"],
        monitoring_service=services["monitoring"],
        site_file_service=services["site_files"],
    )
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _headers(api: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": api.cookies.get("cra_csrf")}


def _source(
    services: dict,
    *,
    key: str,
    purpose: str,
    document_type: str,
    title: str,
    content: str,
):
    actor = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    return services["documents"].create_document(
        actor,
        services["study"],
        CreateDocumentCommand(
            expected_revision=0,
            idempotency_key=f"w10-{key}",
            title=title,
            document_type=document_type,
            purpose=purpose,
            version_label="v1",
            site_id=services["site_a"],
        ),
        filename=f"{key}.txt",
        content=content.encode(),
    )


def _create_issue(api: TestClient, services: dict, *, number: str):
    response = api.post(
        f"/api/v1/studies/{services['study']}/issues",
        json={
            "expected_revision": 0,
            "idempotency_key": f"w10-{number}",
            "site_id": str(services["site_a"]),
            "issue_number": number,
            "original_finding": "Synthetic ISF file was not present.",
            "known_progress": "Site reports a synthetic replacement is pending.",
            "source_kind": "manual",
            "source_refs": [{"locator": "Synthetic ISF row 8"}],
            "actions": [
                {
                    "action_key": "SUPPLY",
                    "kind": "document_supply",
                    "requirement": "Provide the synthetic ISF file.",
                }
            ],
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reference_only_then_incremental_file_status_preserves_history(
    api: TestClient, services: dict, engine
):
    upload = _source(
        services,
        key="isf-directory",
        purpose="directory",
        document_type="directory",
        title="Synthetic ISF Directory",
        content="Synthetic ISF directory\nRow 8: training record\n",
    )
    issue = _create_issue(api, services, number="W10-001")
    action = issue["actions"][0]
    response = api.post(
        "/api/v1/document-directories",
        json={
            "expected_revision": 0,
            "idempotency_key": "create-directory",
            "site_id": str(services["site_a"]),
            "source_document_version_id": str(upload.document_version_id),
            "directory_kind": "isf",
            "label": "Synthetic ISF v1",
            "annotations": [{"page": 1, "note": "Synthetic annotation"}],
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    reference = response.json()
    assert reference["mode"] == "reference_only"
    assert reference["items"] == []
    assert "不能宣称全部核查合格" in reference["coverage_note"]
    original = api.get(reference["content_url"])
    assert original.status_code == 200
    assert b"training record" in original.content

    added = api.post(
        f"/api/v1/document-directories/{reference['id']}/items",
        json={
            "expected_revision": reference["revision"],
            "idempotency_key": "add-training-file",
            "item_key": "A01",
            "title": "Synthetic training record",
            "requirement": "Current training record is expected.",
            "applicability_status": "required",
            "acquisition_status": "not_seen",
            "verification_status": "pending",
            "source_refs": [
                {
                    "source_type": "directory_reference",
                    "locator": "Synthetic ISF row 8",
                }
            ],
            "linked_issue_id": issue["id"],
            "linked_action_id": action["id"],
        },
        headers=_headers(api),
    )
    assert added.status_code == 200, added.text
    body = added.json()
    assert body["mode"] == "structured"
    assert body["missing_item_keys"] == ["A01"]
    assert body["items"][0]["acquisition_status"] == "not_seen"
    assert body["items"][0]["verification_status"] == "pending"

    verification_payload = {
        "expected_revision": body["items"][0]["revision"],
        "idempotency_key": "confirm-training-file",
        "site_file_item_id": body["items"][0]["id"],
        "applicability_status": "required",
        "acquisition_status": "provided",
        "verification_status": "qualified",
        "verification_note": "CRA saw the synthetic file and checked it.",
        "linked_issue_id": issue["id"],
        "linked_action_id": action["id"],
    }
    verified = api.post(
        "/api/v1/file-verifications",
        json=verification_payload,
        headers=_headers(api),
    )
    assert verified.status_code == 200, verified.text
    verified_body = verified.json()
    assert verified_body["missing_item_keys"] == []
    assert verified_body["items"][0]["acquisition_status"] == "provided"
    assert verified_body["items"][0]["verification_status"] == "qualified"
    assert [item["event_type"] for item in verified_body["history"]] == [
        "directory_reference_created",
        "item_created",
        "status_updated",
    ]
    replayed = api.post(
        "/api/v1/file-verifications",
        json=verification_payload,
        headers=_headers(api),
    )
    assert replayed.status_code == 200
    assert len(replayed.json()["history"]) == 3
    issue_after = api.get(f"/api/v1/issues/{issue['id']}")
    assert issue_after.status_code == 200
    assert issue_after.json()["issue_number"] == "W10-001"
    assert issue_after.json()["actions"][0]["status"] == "open"
    with pytest.raises(SQLAlchemyError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE site_file_history SET actor_id = 'rewritten'"
                )
            )

    stale = dict(verification_payload)
    stale["idempotency_key"] = "stale-directory-update"
    stale["verification_note"] = "Synthetic second update."
    conflict = api.post(
        "/api/v1/file-verifications",
        json=stale,
        headers=_headers(api),
    )
    assert conflict.status_code == 409


def test_qualified_requires_provided_file_and_non_directory_source_is_rejected(
    api: TestClient, services: dict
):
    directory = _source(
        services,
        key="tmf-directory-invalid-status",
        purpose="directory",
        document_type="directory",
        title="Synthetic TMF Directory",
        content="Synthetic TMF directory\n",
    )
    reference = api.post(
        "/api/v1/document-directories",
        json={
            "expected_revision": 0,
            "idempotency_key": "create-invalid-status-directory",
            "site_id": str(services["site_a"]),
            "source_document_version_id": str(directory.document_version_id),
            "directory_kind": "tmf",
            "label": "Synthetic TMF v1",
            "annotations": [],
        },
        headers=_headers(api),
    ).json()
    invalid = api.post(
        f"/api/v1/document-directories/{reference['id']}/items",
        json={
            "expected_revision": reference["revision"],
            "idempotency_key": "invalid-qualified-status",
            "item_key": "T01",
            "title": "Synthetic file",
            "requirement": "Synthetic requirement",
            "applicability_status": "required",
            "acquisition_status": "not_seen",
            "verification_status": "qualified",
            "source_refs": [{"locator": "Synthetic TMF row 1"}],
        },
        headers=_headers(api),
    )
    assert invalid.status_code == 422

    sop = _source(
        services,
        key="not-directory",
        purpose="rule",
        document_type="sop",
        title="Synthetic SOP",
        content="Synthetic SOP text\n",
    )
    rejected = api.post(
        "/api/v1/document-directories",
        json={
            "expected_revision": 0,
            "idempotency_key": "reject-non-directory",
            "site_id": str(services["site_a"]),
            "source_document_version_id": str(sop.document_version_id),
            "directory_kind": "isf",
            "label": "Wrong source",
            "annotations": [],
        },
        headers=_headers(api),
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "site_file_validation_failed"


def test_site_status_compares_previous_structured_missing_and_new_items(
    api: TestClient, services: dict
):
    def create_reference(key: str):
        upload = _source(
            services,
            key=key,
            purpose="directory",
            document_type="directory",
            title=f"Synthetic directory {key}",
            content=f"Synthetic directory {key}\n",
        )
        response = api.post(
            "/api/v1/document-directories",
            json={
                "expected_revision": 0,
                "idempotency_key": f"create-{key}",
                "site_id": str(services["site_a"]),
                "source_document_version_id": str(upload.document_version_id),
                "directory_kind": "isf",
                "label": f"Synthetic ISF {key}",
                "annotations": [],
            },
            headers=_headers(api),
        )
        assert response.status_code == 200, response.text
        return response.json()

    def add(reference, key: str, *, acquisition: str, verification: str):
        response = api.post(
            f"/api/v1/document-directories/{reference['id']}/items",
            json={
                "expected_revision": reference["revision"],
                "idempotency_key": f"add-{reference['id']}-{key}",
                "item_key": key,
                "title": f"Synthetic item {key}",
                "requirement": "Synthetic directory requirement.",
                "applicability_status": "required",
                "acquisition_status": acquisition,
                "verification_status": verification,
                "source_refs": [{"locator": f"Synthetic row {key}"}],
            },
            headers=_headers(api),
        )
        assert response.status_code == 200, response.text
        return response.json()

    v1 = create_reference("directory-v1")
    v1 = add(v1, "A01", acquisition="not_seen", verification="pending")
    v1 = add(v1, "B01", acquisition="provided", verification="pending")
    v2 = create_reference("directory-v2")
    v2 = add(v2, "A01", acquisition="provided", verification="qualified")
    add(v2, "C01", acquisition="not_seen", verification="pending")

    status = api.get(
        f"/api/v1/site-file-status?study_id={services['study']}&site_id={services['site_a']}"
    )
    assert status.status_code == 200, status.text
    latest = status.json()[-1]
    assert latest["change_status"] == "compared"
    assert latest["previous_reference_id"] == v1["id"]
    assert latest["new_item_keys"] == ["C01"]
    assert latest["removed_item_keys"] == ["B01"]
    assert latest["changed_item_keys"] == ["A01"]
    assert latest["missing_item_keys"] == ["C01"]


def test_stage_checklists_keep_sources_history_and_never_approve_center_close(
    api: TestClient, services: dict
):
    sop = _source(
        services,
        key="stage-sop",
        purpose="rule",
        document_type="monitoring_plan",
        title="Synthetic Monitoring Plan",
        content="Synthetic startup and closeout requirements\n",
    )
    source_item = {
        "item_key": "S01",
        "title": "Synthetic site initiation confirmation",
        "requirement": "Confirm the synthetic site initiation requirement.",
        "source_document_version_id": str(sop.document_version_id),
        "source_refs": [
            {
                "source_type": "project_document",
                "locator": "Synthetic section 2.1",
            }
        ],
    }
    created = api.post(
        f"/api/v1/studies/{services['study']}/stage-checklists",
        json={
            "expected_revision": 0,
            "idempotency_key": "create-startup-checklist",
            "site_id": str(services["site_a"]),
            "stage": "startup",
            "title": "Synthetic startup checklist",
            "source_refs": source_item["source_refs"],
            "items": [source_item],
        },
        headers=_headers(api),
    )
    assert created.status_code == 200, created.text
    checklist = created.json()
    assert checklist["items"][0]["source_document_version_id"] == str(
        sop.document_version_id
    )
    assert checklist["all_items_confirmed"] is False
    assert checklist["center_close_approved"] is False

    item = checklist["items"][0]
    confirmed = api.post(
        f"/api/v1/stage-checklist-items/{item['id']}/verification",
        json={
            "expected_revision": item["revision"],
            "idempotency_key": "confirm-startup-item",
            "status": "confirmed",
            "note": "CRA confirmed the synthetic requirement.",
        },
        headers=_headers(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_body = confirmed.json()
    assert confirmed_body["all_items_confirmed"] is True
    assert confirmed_body["center_close_approved"] is False
    assert "不等于项目组批准" in confirmed_body["limitation"]
    assert [event["event_type"] for event in confirmed_body["history"]] == [
        "checklist_created",
        "item_created",
        "status_updated",
    ]

    no_source = api.post(
        f"/api/v1/studies/{services['study']}/stage-checklists",
        json={
            "expected_revision": 0,
            "idempotency_key": "missing-stage-source",
            "site_id": str(services["site_a"]),
            "stage": "closeout",
            "title": "Unsourced checklist",
            "source_refs": [],
            "items": [{**source_item, "item_key": "C01", "source_refs": []}],
        },
        headers=_headers(api),
    )
    assert no_source.status_code == 422


def test_handover_reuses_issue_progress_and_incomplete_checklist(
    api: TestClient, services: dict
):
    issue = _create_issue(api, services, number="W10-HANDOVER")
    sop = _source(
        services,
        key="closeout-sop",
        purpose="rule",
        document_type="sop",
        title="Synthetic Closeout SOP",
        content="Synthetic closeout requirement\n",
    )
    closeout = api.post(
        f"/api/v1/studies/{services['study']}/stage-checklists",
        json={
            "expected_revision": 0,
            "idempotency_key": "create-closeout-checklist",
            "site_id": str(services["site_a"]),
            "stage": "closeout",
            "title": "Synthetic closeout checklist",
            "source_refs": [{"locator": "Synthetic closeout section"}],
            "items": [
                {
                    "item_key": "C01",
                    "title": "Synthetic archive confirmation",
                    "requirement": "Confirm the synthetic archive requirement.",
                    "source_document_version_id": str(sop.document_version_id),
                    "source_refs": [
                        {"locator": "Synthetic closeout section"}
                    ],
                }
            ],
        },
        headers=_headers(api),
    )
    assert closeout.status_code == 200, closeout.text
    visit = api.post(
        f"/api/v1/studies/{services['study']}/monitoring-visits",
        json={
            "expected_revision": 0,
            "idempotency_key": "w10-handover-visit",
            "site_id": str(services["site_a"]),
            "stage": "handover",
            "title": "Synthetic handover visit",
            "scope_note": "Synthetic W10 handover scope",
        },
        headers=_headers(api),
    )
    assert visit.status_code == 200, visit.text
    handover = api.get(
        f"/api/v1/monitoring-visits/{visit.json()['visit']['id']}/handover-summary"
    )
    assert handover.status_code == 200, handover.text
    body = handover.json()
    assert body["has_carryover"] is True
    assert body["center_close_approved"] is False
    assert "不形成额外审批" in body["limitation"]
    assert body["issues"][0]["id"] == issue["id"]
    assert body["issues"][0]["issue_number"] == "W10-HANDOVER"
    assert body["issues"][0]["known_progress"].startswith("Site reports")
    assert body["issues"][0]["next_steps"] == [
        "Provide the synthetic ISF file."
    ]
    assert body["incomplete_checklist_items"][0]["title"] == (
        "Synthetic archive confirmation"
    )
    assert "W10-HANDOVER" in body["summary"]


def test_site_file_endpoints_are_in_openapi(
    api: TestClient,
):
    schema = api.get("/api/v1/openapi.json").json()
    assert "/api/v1/site-file-status" in schema["paths"]
    assert "/api/v1/file-verifications" in schema["paths"]
    assert "/api/v1/monitoring-visits/{visit_id}/handover-summary" in (
        schema["paths"]
    )
