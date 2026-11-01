"""Real-PostgreSQL acceptance for refresh/login/center continuity in W12."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

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
from cra_app.issues.service import IssueService
from cra_app.main import create_app
from cra_app.monitoring.service import MonitoringService
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.rules.common_policy import load_common_policy_set
from cra_app.rules.service import RuleService
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.subjects.contracts import (
    CheckDecisionCommand,
    CoverageBreakpointCommand,
    CreateSubjectCommand,
)
from cra_app.subjects.service import SubjectService

pytestmark = pytest.mark.postgres


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W12 never falls back to SQLite"
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
        CRA_SESSION_SECRET="synthetic-w12-session-secret",
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
def workspace(session_factory, settings, queue):
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
            idempotency_key="w12-study",
            code="W12-SYN",
            title="W12 Synthetic Continuity",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w12-site-a",
            code="A12",
            name="Synthetic W12 Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w12-site-b",
            code="B12",
            name="Synthetic W12 Site B",
        ),
    )
    for index, site in enumerate((site_a.resource_id, site_b.resource_id)):
        governance.grant_membership(
            admin,
            study.resource_id,
            GrantMembership(
                expected_revision=0,
                idempotency_key=f"w12-grant-a-{index}",
                actor_id="synthetic-cra-a",
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
    return {
        "governance": governance,
        "study": study.resource_id,
        "site_a": site_a.resource_id,
        "site_b": site_b.resource_id,
        "documents": documents,
        "rules": rules,
        "subjects": subjects,
        "issues": issues,
        "monitoring": monitoring,
        "settings": settings,
    }


def _client(workspace):
    settings = workspace["settings"]
    application = create_app(
        settings=settings,
        session_factory=workspace["monitoring"].session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
        document_service=workspace["documents"],
        rule_service=workspace["rules"],
        subject_service=workspace["subjects"],
        issue_service=workspace["issues"],
        monitoring_service=workspace["monitoring"],
    )
    return TestClient(application)


def _headers(api: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": api.cookies.get("cra_csrf")}


def _scope() -> ScopeContext:
    return ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )


def _issue(api: TestClient, workspace: dict, number: str):
    response = api.post(
        f"/api/v1/studies/{workspace['study']}/issues",
        json={
            "expected_revision": 0,
            "idempotency_key": f"w12-issue-{number}",
            "site_id": str(workspace["site_a"]),
            "issue_number": number,
            "original_finding": f"Synthetic continuity finding {number}",
            "location": f"Synthetic row {number}",
            "known_progress": "Open before this monitoring cycle.",
            "source_kind": "manual",
            "source_refs": [{"locator": f"Synthetic {number}"}],
            "actions": [
                {
                    "action_key": "PD",
                    "kind": "pd_reporting",
                    "requirement": "Confirm whether PD was reported.",
                },
                {
                    "action_key": "CORRECT",
                    "kind": "edc_correction",
                    "requirement": "Correct the synthetic EDC value.",
                },
            ],
        },
        headers=_headers(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_refresh_relogin_center_switch_and_second_visit_continue(
    workspace: dict,
):
    with _client(workspace) as first_client:
        assert first_client.post(
            "/api/v1/auth/synthetic/session"
        ).status_code == 200
        issues = [
            _issue(first_client, workspace, f"W12-{index:02d}")
            for index in range(1, 4)
        ]
        created = first_client.post(
            f"/api/v1/studies/{workspace['study']}/monitoring-visits",
            json={
                "expected_revision": 0,
                "idempotency_key": "w12-visit-one",
                "site_id": str(workspace["site_a"]),
                "stage": "previsit",
                "title": "Synthetic first continuous visit",
                "scope_note": "First synthetic monitoring cycle.",
            },
            headers=_headers(first_client),
        )
        assert created.status_code == 200, created.text
        first_visit = created.json()["visit"]
        selected_ids = [issues[0]["id"], issues[1]["id"]]
        selected = first_client.post(
            f"/api/v1/monitoring-visits/{first_visit['id']}/previsit-selection",
            json={
                "expected_revision": first_visit["revision"],
                "idempotency_key": "w12-select-two",
                "issue_ids": selected_ids,
            },
            headers=_headers(first_client),
        )
        assert selected.status_code == 200, selected.text
        first_visit = selected.json()["visit"]
        stage = first_client.post(
            f"/api/v1/monitoring-visits/{first_visit['id']}/stage",
            json={
                "expected_revision": first_visit["revision"],
                "idempotency_key": "w12-first-to-carryover",
                "stage": "carryover_review",
            },
            headers=_headers(first_client),
        )
        assert stage.status_code == 200, stage.text

        pd_action = next(
            action
            for action in issues[0]["actions"]
            if action["kind"] == "pd_reporting"
        )
        reported = first_client.post(
            f"/api/v1/actions/{pd_action['id']}/confirm-reported",
            json={
                "expected_revision": pd_action["revision"],
                "idempotency_key": "w12-pd-reported",
                "user_statement": "CRA confirms the synthetic PD was reported.",
            },
            headers=_headers(first_client),
        )
        assert reported.status_code == 200, reported.text

    with _client(workspace) as second_client:
        assert second_client.post(
            "/api/v1/auth/synthetic/session"
        ).status_code == 200
        visits = second_client.get(
            f"/api/v1/studies/{workspace['study']}/monitoring-visits"
            f"?site_id={workspace['site_a']}"
        )
        assert visits.status_code == 200, visits.text
        assert visits.json()[0]["id"] == first_visit["id"]
        journey = second_client.get(
            f"/api/v1/monitoring-visits/{first_visit['id']}/journey"
        )
        assert journey.status_code == 200, journey.text
        body = journey.json()
        assert body["visit"]["stage"] == "carryover_review"
        assert set(body["selected_issue_ids"]) == set(selected_ids)
        assert set(body["remaining_issue_numbers"]) == {
            "W12-01",
            "W12-02",
            "W12-03",
        }
        reported_issue = second_client.get(
            f"/api/v1/issues/{issues[0]['id']}"
        )
        assert reported_issue.status_code == 200
        assert next(
            action
            for action in reported_issue.json()["actions"]
            if action["kind"] == "pd_reporting"
        )["status"] == "completed"
        assert next(
            action
            for action in reported_issue.json()["actions"]
            if action["kind"] == "edc_correction"
        )["status"] == "open"

        subject = workspace["subjects"].create_subject(
            _scope(),
            workspace["study"],
            CreateSubjectCommand(
                expected_revision=0,
                idempotency_key="w12-subject",
                site_id=workspace["site_a"],
                external_id="W12-S001",
                identity_namespace="synthetic-edc",
                deidentified_label="Synthetic W12 Subject",
            ),
        )
        workspace["subjects"].save_coverage(
            _scope(),
            subject.id,
            CoverageBreakpointCommand(
                expected_revision=0,
                idempotency_key="w12-coverage",
                category="laboratory",
                scope_key="visit-1",
                status="in_progress",
                checked_through="visit-1",
                normal_scope_note="Synthetic normal range batch.",
                unverified_scope=["visit-2"],
            ),
        )
        decision = second_client.post(
            f"/api/v1/subjects/{subject.id}/check-decisions",
            json={
                "expected_revision": 0,
                "idempotency_key": "w12-skip",
                "category": "visit_window",
                "check_type": "visit_window",
                "reason": "declined_missing_data",
                "missing_keys": ["infusion_date"],
                "affected_paths": ["synthetic-visit-window"],
                "can_continue": ["laboratory_review"],
            },
            headers=_headers(second_client),
        )
        assert decision.status_code == 200, decision.text
        journey = second_client.get(
            f"/api/v1/monitoring-visits/{first_visit['id']}/journey"
        ).json()
        assert journey["subject_count"] == 1
        assert journey["coverage_count"] == 1
        assert journey["not_checked_count"] == 0
        assert journey["active_skip_count"] == 1

        resumed = second_client.post(
            f"/api/v1/subjects/{subject.id}/check-decisions/"
            f"{decision.json()['id']}/resume",
            json={
                "expected_revision": decision.json()["revision"],
                "idempotency_key": "w12-resume",
                "reason": "Synthetic missing data supplied.",
            },
            headers=_headers(second_client),
        )
        assert resumed.status_code == 200, resumed.text
        journey = second_client.get(
            f"/api/v1/monitoring-visits/{first_visit['id']}/journey"
        ).json()
        assert journey["active_skip_count"] == 0

        other_site = second_client.get(
            f"/api/v1/studies/{workspace['study']}/monitoring-visits"
            f"?site_id={workspace['site_b']}"
        )
        assert other_site.status_code == 200
        assert other_site.json() == []
        back = second_client.get(
            f"/api/v1/monitoring-visits/{first_visit['id']}/journey"
        )
        assert back.status_code == 200
        assert back.json()["visit"]["id"] == first_visit["id"]

        created_second = second_client.post(
            f"/api/v1/studies/{workspace['study']}/monitoring-visits",
            json={
                "expected_revision": 0,
                "idempotency_key": "w12-visit-two",
                "site_id": str(workspace["site_a"]),
                "stage": "carryover_review",
                "title": "Synthetic second continuous visit",
                "scope_note": "Continue unresolved items.",
            },
            headers=_headers(second_client),
        )
        assert created_second.status_code == 200, created_second.text
        second_body = created_second.json()
        assert {
            item["issue_number"] for item in second_body["carryover"]
        } == {"W12-01", "W12-02", "W12-03"}
        assert second_body["selected_issue_ids"] == []
