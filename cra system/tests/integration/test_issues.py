"""Real-PostgreSQL acceptance for CRA-W06 issue and action workflows."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

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
from cra_app.issues.models import IssueHistory
from cra_app.issues.service import IssueService
from cra_app.main import create_app
from cra_app.monitoring.service import MonitoringService
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory

pytestmark = pytest.mark.postgres


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
        CRA_SESSION_SECRET="synthetic-w06-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
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
            idempotency_key="w06-study",
            code="W06-SYN",
            title="W06 Synthetic Monitoring",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w06-site-a",
            code="A01",
            name="Synthetic W06 Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w06-site-b",
            code="B01",
            name="Synthetic W06 Site B",
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
                idempotency_key=f"w06-grant-{actor}",
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
    return {
        "governance": governance,
        "admin": admin,
        "study": study.resource_id,
        "site_a": site_a.resource_id,
        "site_b": site_b.resource_id,
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


def _create_issue(
    api: TestClient,
    services: dict,
    *,
    number: str,
    actions: list[dict] | None = None,
    site: str | None = None,
):
    response = api.post(
        f"/api/v1/studies/{services['study']}/issues",
        json={
            "expected_revision": 0,
            "idempotency_key": f"create-{number}",
            "site_id": site or str(services["site_a"]),
            "issue_number": number,
            "original_finding": f"Synthetic finding for {number}",
            "location": "Synthetic source field",
            "recommendation": "Correct the synthetic source field.",
            "recommendation_sources": [
                {"text": "Synthetic monitoring SOP", "official_status": "unknown"}
            ],
            "known_progress": "Open at the previous synthetic visit.",
            "source_kind": "manual",
            "source_refs": [
                {
                    "source_type": "record",
                    "source_id": "synthetic-w06-record",
                    "locator": "demo field",
                }
            ],
            "actions": actions
            if actions is not None
            else [
                {
                    "action_key": "A1",
                    "kind": "edc_correction",
                    "requirement": "Correct the synthetic EDC field.",
                }
            ],
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_pd_and_correction_actions_complete_independently(
    api: TestClient, services: dict
):
    issue = _create_issue(
        api,
        services,
        number="CRA-SYN-201",
        actions=[
            {
                "action_key": "PD",
                "kind": "pd_reporting",
                "requirement": "Confirm synthetic PD reporting.",
            },
            {
                "action_key": "CORRECT",
                "kind": "edc_correction",
                "requirement": "Correct the synthetic EDC field.",
            },
        ],
    )
    pd_action = next(
        action for action in issue["actions"] if action["kind"] == "pd_reporting"
    )
    correction = next(
        action
        for action in issue["actions"]
        if action["kind"] == "edc_correction"
    )
    reported = api.post(
        f"/api/v1/actions/{pd_action['id']}/confirm-reported",
        json={
            "expected_revision": pd_action["revision"],
            "idempotency_key": "confirm-pd",
            "user_statement": "CRA states the synthetic PD report was submitted.",
            "optional_note": "",
        },
        headers=_headers(api),
    )
    assert reported.status_code == 200, reported.text
    body = reported.json()
    assert body["status"] == "completed"
    assert body["completion_basis"] == "user_confirmation"
    assert body["completed_by"] == "synthetic-cra-a"
    assert body["completed_at"]

    after_pd = api.get(f"/api/v1/issues/{issue['id']}").json()
    remaining = next(
        action
        for action in after_pd["actions"]
        if action["id"] == correction["id"]
    )
    assert remaining["status"] == "open"
    assert after_pd["aggregate_status"] == "in_progress"

    corrected = api.post(
        "/api/v1/actions/confirm-corrected",
        json={
            "idempotency_key": "confirm-correction",
            "actions": [
                {
                    "action_id": correction["id"],
                    "expected_revision": correction["revision"],
                }
            ],
            "optional_note": None,
        },
        headers=_headers(api),
    )
    assert corrected.status_code == 200, corrected.text
    completed_action = corrected.json()["actions"][0]
    assert completed_action["status"] == "completed"
    assert completed_action["completion_basis"] == "user_confirmation"
    # No reply, location, attachment or separate verification record was required.
    final = api.get(f"/api/v1/issues/{issue['id']}").json()
    assert final["aggregate_status"] == "completed"
    assert [item["event_type"] for item in final["history"]].count(
        "action_confirmed"
    ) >= 1
    assert any(
        item["event_type"] == "action_reported" for item in final["history"]
    )


def test_correction_can_be_reopened_without_losing_history(
    api: TestClient, services: dict
):
    issue = _create_issue(api, services, number="CRA-SYN-202")
    action = issue["actions"][0]
    confirmed = api.post(
        "/api/v1/actions/confirm-corrected",
        json={
            "idempotency_key": "reopen-confirm",
            "actions": [
                {
                    "action_id": action["id"],
                    "expected_revision": action["revision"],
                }
            ],
        },
        headers=_headers(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    completed = confirmed.json()["actions"][0]
    reopened = api.post(
        f"/api/v1/actions/{action['id']}/reopen",
        json={
            "expected_revision": completed["revision"],
            "idempotency_key": "reopen-action",
            "reason": "Synthetic CRA found the field was still incorrect.",
        },
        headers=_headers(api),
    )
    assert reopened.status_code == 200, reopened.text
    body = reopened.json()
    assert body["status"] == "open"
    assert body["completion_basis"] is None
    assert body["completed_by"] is None
    detail = api.get(f"/api/v1/issues/{issue['id']}").json()
    assert detail["issue_number"] == "CRA-SYN-202"
    assert detail["aggregate_status"] == "open"
    assert [
        event["event_type"]
        for event in detail["history"]
        if event["event_type"] in {"action_confirmed", "action_reopened"}
    ] == ["action_confirmed", "action_reopened"]


def test_previsit_selection_keeps_complete_carryover_across_visits(
    api: TestClient, services: dict
):
    issues = [
        _create_issue(api, services, number=f"CRA-SYN-30{index}")
        for index in range(1, 4)
    ]
    created = api.post(
        f"/api/v1/studies/{services['study']}/monitoring-visits",
        json={
            "expected_revision": 0,
            "idempotency_key": "visit-one",
            "site_id": str(services["site_a"]),
            "stage": "previsit",
            "title": "Synthetic monitoring visit 1",
            "scope_note": "Synthetic carryover and subject review.",
        },
        headers=_headers(api),
    )
    assert created.status_code == 200, created.text
    workbench = created.json()
    assert len(workbench["carryover"]) == 3
    selected_ids = [issues[0]["id"], issues[2]["id"]]
    selection = api.post(
        f"/api/v1/monitoring-visits/{workbench['visit']['id']}/previsit-selection",
        json={
            "expected_revision": workbench["visit"]["revision"],
            "idempotency_key": "select-two",
            "issue_ids": selected_ids,
        },
        headers=_headers(api),
    )
    assert selection.status_code == 200, selection.text
    selected = selection.json()
    assert set(selected["selected_issue_ids"]) == set(selected_ids)
    assert {item["issue_number"] for item in selected["carryover"]} == {
        "CRA-SYN-301",
        "CRA-SYN-302",
        "CRA-SYN-303",
    }
    assert selected["directory_references"] == []
    assert selected["envelope"]["purpose"] == "carryover_reminder"

    visit_three = api.post(
        f"/api/v1/studies/{services['study']}/monitoring-visits",
        json={
            "expected_revision": 0,
            "idempotency_key": "visit-three",
            "site_id": str(services["site_a"]),
            "stage": "carryover_review",
            "title": "Synthetic monitoring visit 3",
            "scope_note": "Third synthetic follow-up.",
        },
        headers=_headers(api),
    )
    assert visit_three.status_code == 200, visit_three.text
    third = visit_three.json()
    assert {item["issue_number"] for item in third["carryover"]} == {
        "CRA-SYN-301",
        "CRA-SYN-302",
        "CRA-SYN-303",
    }
    assert third["selected_issue_ids"] == []


def test_query_requires_actual_identity_and_deadline_source(
    api: TestClient, services: dict
):
    issue = _create_issue(api, services, number="CRA-SYN-401")
    draft = api.post(
        f"/api/v1/issues/{issue['id']}/query-links",
        json={
            "expected_revision": issue["revision"],
            "idempotency_key": "query-draft",
            "query_state": "draft",
            "external_system": "synthetic-edc",
            "deadline_source_refs": [],
        },
        headers=_headers(api),
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["deadline_status"] == "due_date_unknown"
    assert draft.json()["overdue_days"] is None

    current = api.get(f"/api/v1/issues/{issue['id']}").json()
    invalid_formal = api.post(
        f"/api/v1/issues/{issue['id']}/query-links",
        json={
            "expected_revision": current["revision"],
            "idempotency_key": "query-invalid",
            "query_state": "formal",
            "external_system": "synthetic-edc",
        },
        headers=_headers(api),
    )
    assert invalid_formal.status_code == 422

    formal = api.post(
        f"/api/v1/issues/{issue['id']}/query-links",
        json={
            "expected_revision": current["revision"],
            "idempotency_key": "query-formal",
            "query_state": "formal",
            "external_system": "synthetic-edc",
            "external_query_number": "SYN-Q-001",
            "opened_on": "2026-01-01",
            "due_on": "2026-01-05",
            "deadline_source": "Synthetic site SOP section 5.2",
            "deadline_source_refs": [
                {
                    "source_type": "record",
                    "source_id": "synthetic-sop",
                    "locator": "5.2",
                }
            ],
        },
        headers=_headers(api),
    )
    assert formal.status_code == 200, formal.text
    assert formal.json()["query_state"] == "formal"
    assert formal.json()["overdue_days"] >= 0

    current = api.get(f"/api/v1/issues/{issue['id']}").json()
    missing_source_action = api.post(
        f"/api/v1/issues/{issue['id']}/actions",
        json={
            "expected_revision": current["revision"],
            "idempotency_key": "action-with-invented-deadline",
            "action": {
                "kind": "document_supply",
                "requirement": "Supply a synthetic document.",
                "due_on": "2026-01-10",
            },
        },
        headers=_headers(api),
    )
    assert missing_source_action.status_code == 422


def test_cross_site_denial_and_append_only_history(
    api: TestClient, services: dict, session_factory
):
    issue = _create_issue(api, services, number="CRA-SYN-501")
    provider = SyntheticIdentityProvider(
        api.app.state.settings
    )
    identity = provider.create_identity(actor_id="synthetic-cra-b")
    api.cookies.clear()
    api.cookies.set("cra_session", provider.issue_session(identity), path="/")
    denied = api.get(f"/api/v1/issues/{issue['id']}")
    assert denied.status_code == 403

    with session_factory() as session:
        history_id = session.scalar(
            select(IssueHistory.id).where(IssueHistory.issue_id == issue["id"])
        )
        assert history_id is not None
    with pytest.raises(SQLAlchemyError):
        with session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        "UPDATE issue_history SET actor_id = 'rewritten' "
                        "WHERE id = :id"
                    ),
                    {"id": history_id},
                )
