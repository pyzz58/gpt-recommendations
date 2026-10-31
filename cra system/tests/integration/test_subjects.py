"""Real PostgreSQL acceptance for CRA-W05 subject context and checkpoints."""
from __future__ import annotations

import json
import hashlib
import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
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
from cra_app.main import create_app
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.rules.common_policy import load_common_policy_set
from cra_app.rules.contracts import ConfirmationOperation
from cra_app.rules.service import (
    ConfirmRuleCommand,
    CreateActivationCommand,
    ExtractRuleCommand,
    RuleService,
)
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.subjects.context_import import parse_context_file
from cra_app.subjects.contracts import (
    CheckDecisionCommand,
    CoverageBreakpointCommand,
    FactImportRow,
    ImportFactsCommand,
    MapSubjectIdentifierCommand,
)
from cra_app.subjects.models import (
    CheckDecision,
    ClinicalFact,
    CoverageBreakpoint,
    FactChangeImpact,
    Subject,
    VisitRequirement,
)
from cra_app.subjects.service import SubjectService

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SUBJECT_FIXTURES = FIXTURES / "subjects" / "artifacts"
DOCUMENT_FIXTURES = FIXTURES / "documents" / "artifacts"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W05 never falls back to SQLite"
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
                "TRUNCATE TABLE fact_change_impacts, check_decisions, "
                "coverage_breakpoints, visit_requirements, visit_instances, "
                "clinical_facts, subject_identifiers, subjects, "
                "rule_relations, rule_source_refs, rule_extraction_coverage, "
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
        CRA_SESSION_SECRET="synthetic-w05-session-secret",
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
            idempotency_key="w05-study",
            code="W05-SYN",
            title="W05 Synthetic Subjects",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w05-site-a",
            code="A01",
            name="Synthetic Subject Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w05-site-b",
            code="B01",
            name="Synthetic Subject Site B",
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
                idempotency_key=f"w05-grant-{actor}",
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
        common_policy_set=load_common_policy_set(settings.common_policy_path),
    )
    subjects = SubjectService(
        session_factory, governance=governance, rules=rules
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
    )
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _upload_visit_rule(api: TestClient, services: dict) -> dict:
    content = (SUBJECT_FIXTURES / "synthetic_visit_rule.docx").read_bytes()
    upload = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={
            "file": (
                "synthetic_visit_rule.docx",
                content,
                "application/octet-stream",
            )
        },
        data={
            "title": "Synthetic W05 visit rule",
            "document_type": "protocol",
            "purpose": "rule",
            "version_label": "v1",
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={
            "Idempotency-Key": "w05-rule-upload",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert upload.status_code == 202, upload.text
    body = upload.json()
    assert services["documents"].process_job(
        uuid.UUID(body["job_id"])
    ).status == "completed"
    extracted = api.post(
        f"/api/v1/document-versions/{body['document_version_id']}"
        "/rule-candidates",
        json={"expected_revision": 0, "idempotency_key": "w05-rule-extract"},
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert extracted.status_code == 202, extracted.text
    rules = api.get(
        f"/api/v1/studies/{services['study']}/rules",
        params={"site_id": str(services["site_a"])},
    )
    assert rules.status_code == 200
    rule = next(
        item for item in rules.json() if item["rule_key"] == "R-INFUSION-01"
    )
    version = rule["current_version"]
    confirmed = api.post(
        f"/api/v1/rules/{rule['id']}/confirmation",
        json={
            "expected_revision": rule["revision"],
            "idempotency_key": "w05-rule-confirm",
            "base_version_id": version["id"],
            "reason": "Synthetic W05 rule confirmation",
            "operations": [
                {
                    "op": "edit_fields",
                    "summary": version["summary"],
                }
            ],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert confirmed.status_code == 200, confirmed.text
    activation = api.post(
        "/api/v1/version-activations",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-rule-activation",
            "document_version_id": body["document_version_id"],
            "starts_on": "2020-01-01",
            "reason": "Synthetic W05 rule activation",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert activation.status_code == 200, activation.text
    return {
        **body,
        "rule_id": rule["id"],
        "rule_version_id": confirmed.json()["rule_version_id"],
    }


def _context_rows(filename: str) -> list[FactImportRow]:
    return parse_context_file(
        filename, (SUBJECT_FIXTURES / filename).read_bytes()
    )


def _import_rows(
    services: dict,
    rows: list[FactImportRow],
    *,
    key: str,
    source_kind: str = "original_record",
):
    return services["subjects"].import_facts(
        ScopeContext(
            actor_id="synthetic-cra-a",
            tenant_id="synthetic-tenant",
            authentication_source="trusted-test",
        ),
        services["study"],
        ImportFactsCommand(
            idempotency_key=key,
            site_id=services["site_a"],
            identity_namespace="synthetic-edc",
            source_kind=source_kind,
            rows=rows,
        ),
    )


def _subjects(api: TestClient, services: dict) -> list[dict]:
    response = api.get(
        f"/api/v1/studies/{services['study']}/subjects",
        params={"site_id": str(services["site_a"])},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _subject_by_external(api: TestClient, services: dict, external_id: str):
    return next(
        item
        for item in _subjects(api, services)
        if any(
            identifier["external_id"] == external_id
            for identifier in item["identifiers"]
        )
    )


def _evaluate(api: TestClient, subject_id: str, event_date: str) -> dict:
    response = api.post(
        f"/api/v1/subjects/{subject_id}/visit-requirements",
        json={
            "event_date": event_date,
            "jurisdiction": "synthetic",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_structured_context_json_csv_and_xlsx_parse_same_subjects():
    manifest = json.loads(
        (SUBJECT_FIXTURES.parent / "manifest.json").read_text()
    )
    assert manifest["group"] == "development_and_independent_expectations"
    for artifact in manifest["artifacts"]:
        content = (SUBJECT_FIXTURES.parent / artifact["file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
    json_rows = _context_rows("synthetic_context.json")
    csv_rows = _context_rows("synthetic_context.csv")
    xlsx_rows = _context_rows("synthetic_context.xlsx")
    assert {row.subject_external_id for row in json_rows} == {
        "SYN-001",
        "SYN-002",
    }
    assert len(json_rows) == len(csv_rows) == len(xlsx_rows) == 8
    for parsed in (json_rows, csv_rows, xlsx_rows):
        treatment_due = next(
            row for row in parsed if row.fact_key == "treatment_due"
        )
        assert treatment_due.value_type == "boolean"
        assert treatment_due.precision == "date"


def test_context_file_endpoint_imports_structured_synthetic_csv(api, services):
    content = (SUBJECT_FIXTURES / "synthetic_context.csv").read_bytes()
    response = api.post(
        f"/api/v1/studies/{services['study']}/facts/import-file",
        files={"file": ("synthetic_context.csv", content, "text/csv")},
        data={
            "site_id": str(services["site_a"]),
            "identity_namespace": "synthetic-edc-file",
            "source_kind": "original_record",
        },
        headers={
            "Idempotency-Key": "w05-file-import",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["inserted_facts"] == 8
    assert len(body["subject_ids"]) == 2
    subjects = _subjects(api, services)
    assert {item["current_stage"] for item in subjects} == {"treatment"}


def test_import_reuse_identity_timeline_and_cross_site_isolation(
    api, services, session_factory
):
    rows = _context_rows("synthetic_context.json")
    imported = _import_rows(services, rows, key="w05-json-import")
    assert imported.inserted_facts == 8
    assert len(imported.subject_ids) == 2

    replay = _import_rows(
        services, rows, key="w05-json-import"
    )
    assert replay.replayed is True
    assert replay.inserted_facts == 0

    syn1 = _subject_by_external(api, services, "SYN-001")
    syn2 = _subject_by_external(api, services, "SYN-002")
    assert syn1["id"] != syn2["id"]
    assert syn1["current_stage"] == "treatment"
    timeline = api.get(f"/api/v1/subjects/{syn1['id']}/timeline")
    assert timeline.status_code == 200
    infusion = next(
        item for item in timeline.json() if item["fact_key"] == "infusion_date"
    )
    assert infusion["value"] == "2021-01-01"
    assert infusion["observed_on"] == "2021-01-01"
    assert infusion["observed_at"] is None
    assert infusion["precision"] == "date"
    assert infusion["source_kind"] == "original_record"

    mapped = api.post(
        f"/api/v1/subjects/{syn1['id']}/identifiers",
        json={
            "expected_revision": syn1["revision"],
            "idempotency_key": "w05-map-alt-id",
            "identity_namespace": "manual",
            "external_id": "SYN-001-ALT",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert mapped.status_code == 200, mapped.text
    alt_row = FactImportRow(
        subject_external_id="SYN-001-ALT",
        fact_key="consent_date",
        value_raw="2020-12-20",
        value_type="date",
        observed_on=date(2020, 12, 20),
        precision="date",
        source_kind="original_record",
        source_ref={
            "source_type": "record",
            "source_id": "synthetic-manual-map",
        },
    )
    services["subjects"].import_facts(
        ScopeContext(
            actor_id="synthetic-cra-a",
            tenant_id="synthetic-tenant",
            authentication_source="trusted-test",
        ),
        services["study"],
        ImportFactsCommand(
            idempotency_key="w05-map-import",
            site_id=services["site_a"],
            identity_namespace="manual",
            rows=[alt_row],
        ),
    )
    assert len(_subjects(api, services)) == 2

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Subject)) == 2


def test_rule_driven_window_dates_and_stage(
    api, services, session_factory
):
    rule = _upload_visit_rule(api, services)
    _import_rows(
        services,
        _context_rows("synthetic_context.json"),
        key="w05-window-context",
    )
    syn1 = _subject_by_external(api, services, "SYN-001")
    result = _evaluate(api, syn1["id"], "2021-01-02")
    assert result["envelope"]["purpose"] == "visit_window"
    assert {item["requirement"]["stage"] for item in result["requirements"]} == {
        "treatment"
    }
    statuses = {
        item["requirement"]["visit_key"]: item["requirement"]["status"]
        for item in result["requirements"]
    }
    assert statuses["R-INFUSION-01:branch:V"] == "in_window"
    assert statuses["R-INFUSION-01:branch:L"] == "out_of_window"
    in_window = next(
        item["requirement"]
        for item in result["requirements"]
        if item["requirement"]["visit_key"].endswith(":V")
    )
    assert in_window["anchor_fact_key"] == "infusion_date"
    assert in_window["anchor_date"] == "2021-01-01"
    assert in_window["actual_date"] == "2021-01-02"
    assert in_window["window_start"] == "2020-12-30"
    assert in_window["window_end"] == "2021-01-03"
    assert in_window["rule_version_id"] == rule["rule_version_id"]
    assert result["instances"]
    with session_factory() as session:
        requirements = list(session.scalars(select(VisitRequirement)))
        assert len(requirements) == 2
    with pytest.raises(SQLAlchemyError):
        with session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        "UPDATE clinical_facts SET value_raw = 'tampered' "
                        "WHERE fact_key = 'infusion_date'"
                    )
                )


def test_missing_anchor_skip_recovery_and_other_work_continues(
    api, services, session_factory
):
    rule = _upload_visit_rule(api, services)
    _import_rows(
        services,
        _context_rows("synthetic_context.json"),
        key="w05-skip-context",
    )
    syn1 = _subject_by_external(api, services, "SYN-001")
    syn2 = _subject_by_external(api, services, "SYN-002")
    before = _evaluate(api, syn2["id"], "2021-01-03")
    assert all(
        item["requirement"]["status"] == "unknown_anchor"
        for item in before["requirements"]
    )
    decision = api.post(
        f"/api/v1/subjects/{syn2['id']}/check-decisions",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-skip-missing-infusion",
            "category": "visit_window",
            "check_type": "visit_window",
            "reason": "declined_missing_data",
            "scope_start": "2021-01-01",
            "scope_end": "2021-01-31",
            "missing_keys": ["infusion_date"],
            "affected_paths": ["R-INFUSION-01:branch:V"],
            "can_continue": ["identified_subject_work", "laboratory_review"],
            "rule_version_id": rule["rule_version_id"],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert decision.status_code == 200, decision.text
    decision_body = decision.json()
    after = _evaluate(api, syn2["id"], "2021-01-03")
    assert all(
        item["requirement"]["status"] == "not_checked_by_user"
        for item in after["requirements"]
    )
    assert after["envelope"]["not_checked"]
    assert any(
        "laboratory_review" in item["requirement"]["can_continue"]
        or "known_subject_and_stage" in item["requirement"]["can_continue"]
        for item in after["requirements"]
    )
    syn1_after = _evaluate(api, syn1["id"], "2021-01-02")
    assert {
        item["requirement"]["status"] for item in syn1_after["requirements"]
    } == {"in_window", "out_of_window"}

    infusion = next(
        row
        for row in _context_rows("synthetic_context.json")
        if row.subject_external_id == "SYN-001"
        and row.fact_key == "infusion_date"
    ).model_copy(
        update={
            "subject_external_id": "SYN-002",
            "value_raw": "2021-01-03",
            "observed_on": date(2021, 1, 3),
        }
    )
    _import_rows(services, [infusion], key="w05-syn2-infusion")
    decisions = api.get(
        f"/api/v1/subjects/{syn2['id']}/check-decisions"
    )
    assert decisions.status_code == 200
    active = decisions.json()[0]
    assert active["recovery_available"] is True
    assert active["state"] == "active"
    still_skipped = _evaluate(api, syn2["id"], "2021-01-03")
    assert all(
        item["requirement"]["status"] == "not_checked_by_user"
        for item in still_skipped["requirements"]
    )
    resumed = api.post(
        f"/api/v1/subjects/{syn2['id']}/check-decisions/"
        f"{decision_body['id']}/resume",
        json={
            "expected_revision": active["revision"],
            "idempotency_key": "w05-resume-infusion",
            "reason": "Synthetic missing date supplied",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["state"] == "resumed"
    missing_actual = _evaluate(api, syn2["id"], "2021-01-03")
    assert all(
        item["requirement"]["status"] == "unknown_actual"
        for item in missing_actual["requirements"]
    )
    with session_factory() as session:
        stored = session.get(CheckDecision, uuid.UUID(decision_body["id"]))
        assert stored is not None and stored.state == "resumed"
        assert session.scalar(
            select(func.count()).select_from(FactChangeImpact)
        ) >= 2


def test_fact_revision_marks_requirements_stale_and_breakpoints_are_separate(
    api, services, session_factory
):
    rule = _upload_visit_rule(api, services)
    _import_rows(
        services,
        _context_rows("synthetic_context.json"),
        key="w05-revision-context",
    )
    subject = _subject_by_external(api, services, "SYN-001")
    other_subject = _subject_by_external(api, services, "SYN-002")
    first = _evaluate(api, subject["id"], "2021-01-02")
    first_requirement_id = next(
        item["requirement"]["id"]
        for item in first["requirements"]
        if item["requirement"]["visit_key"].endswith(":V")
    )
    old_infusion = next(
        row
        for row in _context_rows("synthetic_context.json")
        if row.subject_external_id == "SYN-001"
        and row.fact_key == "infusion_date"
    )
    corrected = old_infusion.model_copy(
        update={
            "value_raw": "2021-01-05",
            "observed_on": date(2021, 1, 5),
            "source_ref": old_infusion.source_ref.model_copy(
                update={"source_id": "synthetic-context:revision-2"}
            ),
        }
    )
    outcome = _import_rows(
        services, [corrected], key="w05-correct-infusion"
    )
    assert outcome.superseded_facts == 1
    with session_factory() as session:
        requirement = session.get(
            VisitRequirement, uuid.UUID(first_requirement_id)
        )
        assert requirement is not None
        assert requirement.status == "needs_review"
        facts = list(
            session.scalars(
                select(ClinicalFact)
                .where(
                    ClinicalFact.subject_id == uuid.UUID(subject["id"]),
                    ClinicalFact.fact_key == "infusion_date",
                )
                .order_by(ClinicalFact.revision)
            )
        )
        assert [(fact.revision, fact.value_raw) for fact in facts] == [
            (1, "2021-01-01"),
            (2, "2021-01-05"),
        ]
        assert session.scalar(
            select(func.count()).select_from(FactChangeImpact)
        ) >= 1
    revised = _evaluate(api, subject["id"], "2021-01-02")
    revised_window = next(
        item["requirement"]
        for item in revised["requirements"]
        if item["requirement"]["visit_key"].endswith(":V")
    )
    assert revised_window["anchor_date"] == "2021-01-05"
    assert revised_window["window_start"] == "2021-01-03"
    assert revised_window["window_end"] == "2021-01-07"
    assert revised_window["status"] == "out_of_window"

    lab = api.post(
        f"/api/v1/subjects/{subject['id']}/coverage",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-coverage-lab",
            "category": "laboratory",
            "scope_key": "screening",
            "status": "in_progress",
            "checked_through": "V3",
            "normal_scope_note": "Synthetic normal range reviewed",
            "unverified_scope": ["repeat chemistry"],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert lab.status_code == 200, lab.text
    documents = api.post(
        f"/api/v1/subjects/{subject['id']}/coverage",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-coverage-docs",
            "category": "documents",
            "scope_key": "screening",
            "status": "in_progress",
            "checked_through": "V2",
            "unverified_scope": ["training log"],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert documents.status_code == 200, documents.text
    lab_update = api.post(
        f"/api/v1/subjects/{subject['id']}/coverage",
        json={
            "expected_revision": 1,
            "idempotency_key": "w05-coverage-lab-v2",
            "category": "laboratory",
            "scope_key": "screening",
            "status": "complete",
            "checked_through": "V4",
            "normal_scope_note": "Synthetic normal range reviewed",
            "unverified_scope": [],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert lab_update.status_code == 200, lab_update.text
    coverage = api.get(f"/api/v1/subjects/{subject['id']}/coverage")
    by_category = {item["category"]: item for item in coverage.json()}
    assert by_category["laboratory"]["checked_through"] == "V4"
    assert by_category["documents"]["checked_through"] == "V2"
    assert by_category["laboratory"]["id"] != by_category["documents"]["id"]
    other_coverage = api.get(
        f"/api/v1/subjects/{other_subject['id']}/coverage"
    )
    assert other_coverage.status_code == 200
    assert other_coverage.json() == []
    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(CoverageBreakpoint)
        ) == 3
    with pytest.raises(SQLAlchemyError):
        with session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        "UPDATE coverage_breakpoints "
                        "SET checked_through = 'tampered' WHERE id = :id"
                    ),
                    {"id": by_category["laboratory"]["id"]},
                )


def test_cross_site_access_and_model_suggestion_not_used(
    api, services, settings, session_factory
):
    _import_rows(
        services,
        _context_rows("synthetic_context.json"),
        key="w05-model-context",
    )
    subject = _subject_by_external(api, services, "SYN-001")
    model_row = FactImportRow(
        subject_external_id="SYN-001",
        fact_key="study_phase",
        value_raw="follow-up",
        value_type="string",
        observed_on=date(2021, 1, 4),
        precision="date",
        source_kind="model_suggestion",
        source_ref={
            "source_type": "record",
            "source_id": "synthetic-model-suggestion",
        },
    )
    _import_rows(
        services,
        [model_row],
        key="w05-model-suggestion",
        source_kind="model_suggestion",
    )
    assert _subject_by_external(api, services, "SYN-001")[
        "current_stage"
    ] == "treatment"
    with session_factory() as session:
        assert session.scalar(
            select(func.count())
            .select_from(ClinicalFact)
            .where(ClinicalFact.verification_status == "model_candidate")
        ) == 1

    provider = SyntheticIdentityProvider(settings)
    identity = provider.create_identity(actor_id="synthetic-cra-b")
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=provider,
        document_service=services["documents"],
        rule_service=services["rules"],
        subject_service=services["subjects"],
    )
    with TestClient(application) as other:
        other.cookies.set("cra_session", provider.issue_session(identity))
        denied = other.get(f"/api/v1/subjects/{subject['id']}/timeline")
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "authorization_denied"
