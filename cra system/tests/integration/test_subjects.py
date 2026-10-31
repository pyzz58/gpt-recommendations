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
from cra_app.rules.contracts import (
    ConfirmationOperation,
    FactValue,
    RuleCondition,
    RuleNode,
    RuleOperand,
    RuleSourceRef,
)
from cra_app.rules.evaluator import evaluate_condition
from cra_app.rules.service import (
    ConfirmRuleCommand,
    CreateActivationCommand,
    ExtractRuleCommand,
    RuleService,
)
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.subjects.context_import import parse_context_file
from cra_app.subjects.calendar import extract_date_interval_specs
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


def _upload_gated_text_window_rule(api: TestClient, services: dict) -> dict:
    content = (
        "Rule R-WINDOW-GATED-01: Synthetic gated visit window.\n"
        "Trigger: screening_active = true\n"
        "Branch V: WHEN visit_date within -2..2 days of infusion_date "
        "THEN review the synthetic visit window\n"
        "Required facts: screening_active, infusion_date, visit_date\n"
    ).encode()
    upload = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={
            "file": (
                "synthetic_gated_window_rule.txt",
                content,
                "text/plain",
            )
        },
        data={
            "title": "Synthetic gated visit window",
            "document_type": "text",
            "purpose": "rule",
            "version_label": "v1",
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={
            "Idempotency-Key": "w05-gated-rule-upload",
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
        json={"expected_revision": 0, "idempotency_key": "w05-gated-extract"},
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert extracted.status_code == 202, extracted.text
    activation = api.post(
        "/api/v1/version-activations",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-gated-activation",
            "document_version_id": body["document_version_id"],
            "starts_on": "2020-01-01",
            "reason": "Synthetic gated window activation",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert activation.status_code == 200, activation.text
    return body


def _confirm_nested_window_rule(api: TestClient, services: dict) -> None:
    rules = api.get(
        f"/api/v1/studies/{services['study']}/rules",
        params={"site_id": str(services["site_a"])},
    )
    assert rules.status_code == 200, rules.text
    item = next(
        rule
        for rule in rules.json()
        if rule["rule_key"] == "R-WINDOW-GATED-01"
    )
    version_id = item["current_version"]["id"]
    detail = api.get(f"/api/v1/rule-versions/{version_id}")
    assert detail.status_code == 200, detail.text
    source_ref = detail.json()["tree"]["source_refs"][0]
    interval = {
        "op": "date_interval",
        "fact_key": "visit_date",
        "anchor_fact_key": "infusion_date",
        "min_days": -2,
        "max_days": 2,
        "inclusive": True,
    }
    confirmed = api.post(
        f"/api/v1/rules/{item['id']}/confirmation",
        json={
            "expected_revision": item["revision"],
            "idempotency_key": "w05-nested-parent-confirmation",
            "base_version_id": version_id,
            "reason": "Add synthetic nested applicability boundary",
            "operations": [
                {
                    "op": "edit_fields",
                    "preconditions": [
                        {
                            "op": "eq",
                            "left": {
                                "kind": "fact_ref",
                                "fact_key": "gate_ok",
                            },
                            "right": {
                                "kind": "literal",
                                "value": True,
                            },
                        }
                    ],
                },
                {
                    "op": "add_exception",
                    "exception": {
                        "exception_key": "PARENT-WAIVER",
                        "description": "Synthetic parent waiver",
                        "condition": {
                            "op": "eq",
                            "left": {
                                "kind": "fact_ref",
                                "fact_key": "waiver",
                            },
                            "right": {
                                "kind": "literal",
                                "value": True,
                            },
                        },
                        "source_refs": [source_ref],
                    },
                },
                {
                    "op": "add_child",
                    "child": {
                        "node_key": "R-WINDOW-GATED-01-NESTED",
                        "summary": "Synthetic nested visit window",
                        "trigger": interval,
                        "required_facts": [
                            "infusion_date",
                            "visit_date",
                        ],
                        "source_refs": [source_ref],
                    },
                },
            ],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert confirmed.status_code == 200, confirmed.text


def _confirm_branch_linked_window(
    api: TestClient,
    services: dict,
    *,
    shape: str,
) -> None:
    _upload_gated_text_window_rule(api, services)
    listed = api.get(
        f"/api/v1/studies/{services['study']}/rules",
        params={"site_id": str(services["site_a"])},
    )
    assert listed.status_code == 200, listed.text
    item = next(
        rule
        for rule in listed.json()
        if rule["rule_key"] == "R-WINDOW-GATED-01"
    )
    version_id = item["current_version"]["id"]
    detail = api.get(f"/api/v1/rule-versions/{version_id}")
    assert detail.status_code == 200, detail.text
    source_refs = detail.json()["tree"]["source_refs"]
    interval = {
        "op": "date_interval",
        "fact_key": "visit_date",
        "anchor_fact_key": "infusion_date",
        "min_days": -2,
        "max_days": 2,
        "inclusive": True,
    }
    leaf = {
        "node_key": "RECHECK-BRANCH-WINDOW",
        "summary": "Pure synthetic branch-linked check",
        "trigger": interval,
        "required_facts": ["infusion_date", "visit_date"],
        "source_refs": source_refs,
    }
    target = (
        leaf
        if shape == "direct"
        else {
            "node_key": "RECHECK-BRANCH-CONTAINER",
            "summary": "Pure synthetic branch-selected child list",
            "children": [leaf],
            "source_refs": source_refs,
        }
    )
    group = {
        "node_key": "RECHECK-BRANCH-GROUP",
        "summary": "Pure synthetic conditional child list",
        "trigger": {
            "op": "eq",
            "left": {
                "kind": "fact_ref",
                "fact_key": "screening_active",
            },
            "right": {"kind": "literal", "value": True},
        },
        "branches": [
            {
                "branch_key": "RECHECK-SELECT",
                "label": "Synthetic eligible branch",
                "condition": {
                    "op": "eq",
                    "left": {
                        "kind": "fact_ref",
                        "fact_key": "gate_ok",
                    },
                    "right": {"kind": "literal", "value": True},
                },
                "target_node_ids": [target["node_key"]],
                "source_refs": source_refs,
            }
        ],
        "children": [target],
        "source_refs": source_refs,
    }
    confirmed = api.post(
        f"/api/v1/rules/{item['id']}/confirmation",
        json={
            "expected_revision": item["revision"],
            "idempotency_key": "w05-branch-linked-window-confirm",
            "base_version_id": version_id,
            "reason": "Pure synthetic branch selection and child window",
            "operations": [{"op": "add_child", "child": group}],
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert confirmed.status_code == 200, confirmed.text


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


def _record_no_protocol_waiver(
    services: dict, external_id: str, *, key: str, observed_on: date
):
    _import_rows(
        services,
        [
            FactImportRow(
                subject_external_id=external_id,
                fact_key="protocol_waiver",
                value_raw="false",
                value_type="boolean",
                observed_on=observed_on,
                source_ref={
                    "source_type": "record",
                    "source_id": f"synthetic-no-waiver:{external_id}",
                    "locator": "synthetic/waiver",
                    "quote": "Pure synthetic no-waiver fact",
                },
            )
        ],
        key=key,
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


def test_visit_window_respects_gate_unknown_date_and_auto_candidate_status(
    api, services
):
    _upload_gated_text_window_rule(api, services)
    ref = {
        "source_type": "record",
        "source_id": "synthetic-visit-window-source",
        "locator": "synthetic/window",
        "quote": "Pure synthetic visit-window facts",
    }
    rows = [
        FactImportRow(
            subject_external_id="SYN-GATE-FALSE",
            fact_key="screening_active",
            value_raw="false",
            value_type="boolean",
            observed_on=date(2026, 1, 1),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-GATE-FALSE",
            fact_key="infusion_date",
            value_raw="2026-01-01",
            value_type="date",
            observed_on=date(2026, 1, 1),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-GATE-FALSE",
            fact_key="visit_date",
            value_raw="2026-01-10",
            value_type="date",
            observed_on=date(2026, 1, 10),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-UNKNOWN-DATE",
            fact_key="screening_active",
            value_raw="true",
            value_type="boolean",
            observed_on=date(2026, 1, 1),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-UNKNOWN-DATE",
            fact_key="infusion_date",
            value_raw="2026-01-01",
            value_type="date",
            observed_on=date(2026, 1, 1),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-UNKNOWN-DATE",
            fact_key="visit_date",
            value_raw="date unavailable",
            value_type="string",
            observed_on=date(2026, 1, 10),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-UNKNOWN-GATE",
            fact_key="infusion_date",
            value_raw="2026-01-01",
            value_type="date",
            observed_on=date(2026, 1, 1),
            source_ref=ref,
        ),
        FactImportRow(
            subject_external_id="SYN-UNKNOWN-GATE",
            fact_key="visit_date",
            value_raw="2026-01-02",
            value_type="date",
            observed_on=date(2026, 1, 2),
            source_ref=ref,
        ),
    ]
    _import_rows(services, rows, key="w05-gated-window")
    false_subject = _subject_by_external(api, services, "SYN-GATE-FALSE")
    false_body = _evaluate(api, false_subject["id"], "2026-01-10")
    assert false_body["requirements"][0]["window_status"] == "not_applicable"
    assert false_body["requirements"][0]["requirement"]["window_start"] is None

    unknown_subject = _subject_by_external(
        api, services, "SYN-UNKNOWN-DATE"
    )
    unknown_body = _evaluate(api, unknown_subject["id"], "2026-01-10")
    assert unknown_body["requirements"][0]["window_status"] == "unknown_actual"
    assert any(
        item["code"] == "missing_actual_visit_date"
        for item in unknown_body["envelope"]["unknowns"]
    )
    window_claims = [
        claim
        for claim in unknown_body["envelope"]["claims"]
        if claim["kind"] == "auto_candidate"
    ]
    assert window_claims
    assert all(
        claim["verification_status"] == "needs_review"
        for claim in window_claims
    )

    unknown_gate_subject = _subject_by_external(
        api, services, "SYN-UNKNOWN-GATE"
    )
    unknown_gate_body = _evaluate(
        api, unknown_gate_subject["id"], "2026-01-10"
    )
    assert (
        unknown_gate_body["requirements"][0]["window_status"]
        == "unknown_applicability"
    )
    assert any(
        item["code"] == "unknown_visit_applicability"
        for item in unknown_gate_body["envelope"]["unknowns"]
    )


def test_nested_visit_windows_inherit_parent_gates_and_keep_out_of_window(
    api, services
):
    _upload_gated_text_window_rule(api, services)
    _confirm_nested_window_rule(api, services)
    ref = {
        "source_type": "record",
        "source_id": "synthetic-nested-parent-source",
        "locator": "synthetic/nested-parent",
        "quote": "Pure synthetic nested parent facts",
    }

    def fact(subject, key, value, value_type="boolean"):
        return FactImportRow(
            subject_external_id=subject,
            fact_key=key,
            value_raw=str(value),
            value_type=value_type,
            observed_on=date(2026, 1, 1),
            source_ref=ref,
        )

    rows = []
    for subject, gate_ok, waiver in (
        ("SYN-NESTED-PARENT-FALSE", False, False),
        ("SYN-NESTED-PARENT-WAIVED", True, True),
    ):
        rows.extend(
            [
                fact(subject, "screening_active", True),
                fact(subject, "gate_ok", gate_ok),
                fact(subject, "waiver", waiver),
                fact(subject, "infusion_date", "2026-01-01", "date"),
                fact(subject, "visit_date", "2026-01-10", "date"),
            ]
        )
    rows.extend(
        [
            fact("SYN-NESTED-PARENT-UNKNOWN", "screening_active", True),
            fact("SYN-NESTED-PARENT-UNKNOWN", "waiver", False),
            fact(
                "SYN-NESTED-PARENT-UNKNOWN",
                "infusion_date",
                "2026-01-01",
                "date",
            ),
            fact(
                "SYN-NESTED-PARENT-UNKNOWN",
                "visit_date",
                "2026-01-10",
                "date",
            ),
            fact("SYN-NESTED-OUT", "screening_active", True),
            fact("SYN-NESTED-OUT", "gate_ok", True),
            fact("SYN-NESTED-OUT", "waiver", False),
            fact("SYN-NESTED-OUT", "infusion_date", "2026-01-01", "date"),
            fact("SYN-NESTED-OUT", "visit_date", "2026-01-10", "date"),
        ]
    )
    _import_rows(services, rows, key="w05-nested-parent-window")

    expected = {
        "SYN-NESTED-PARENT-FALSE": "not_applicable",
        "SYN-NESTED-PARENT-WAIVED": "not_applicable",
        "SYN-NESTED-PARENT-UNKNOWN": "unknown_applicability",
        "SYN-NESTED-OUT": "out_of_window",
    }
    for external_id, status in expected.items():
        subject = _subject_by_external(api, services, external_id)
        body = _evaluate(api, subject["id"], "2026-01-10")
        nested = [
            item
            for item in body["requirements"]
            if "NESTED" in item["requirement"]["visit_key"]
        ]
        assert len(nested) == 1
        assert nested[0]["window_status"] == status


def test_sibling_equal_visit_windows_keep_distinct_condition_paths(
    api, services
):
    content = (
        "Rule R-WINDOW-SIBLINGS-01: Synthetic sibling paths.\n"
        "Trigger: screening_active = true\n"
        "Branch B1: WHEN visit_date within -2..2 days of infusion_date "
        "THEN review path B1\n"
        "Branch B2: WHEN visit_date within -2..2 days of infusion_date "
        "THEN review path B2\n"
        "Required facts: screening_active, infusion_date, visit_date\n"
    ).encode()
    upload = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={
            "file": (
                "synthetic_sibling_window_rule.txt",
                content,
                "text/plain",
            )
        },
        data={
            "title": "Synthetic sibling visit windows",
            "document_type": "text",
            "purpose": "rule",
            "version_label": "v1",
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={
            "Idempotency-Key": "w05-sibling-rule-upload",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert upload.status_code == 202, upload.text
    uploaded = upload.json()
    assert services["documents"].process_job(
        uuid.UUID(uploaded["job_id"])
    ).status == "completed"
    extracted = api.post(
        f"/api/v1/document-versions/{uploaded['document_version_id']}"
        "/rule-candidates",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-sibling-extract",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert extracted.status_code == 202, extracted.text
    activation = api.post(
        "/api/v1/version-activations",
        json={
            "expected_revision": 0,
            "idempotency_key": "w05-sibling-activation",
            "document_version_id": uploaded["document_version_id"],
            "starts_on": "2020-01-01",
            "reason": "Synthetic sibling branch activation",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert activation.status_code == 200, activation.text
    ref = {
        "source_type": "record",
        "source_id": "synthetic-sibling-window-source",
        "locator": "synthetic/siblings",
        "quote": "Pure synthetic sibling window facts",
    }
    _import_rows(
        services,
        [
            FactImportRow(
                subject_external_id="SYN-SIBLING-WINDOW",
                fact_key="screening_active",
                value_raw="true",
                value_type="boolean",
                observed_on=date(2026, 1, 1),
                source_ref=ref,
            ),
            FactImportRow(
                subject_external_id="SYN-SIBLING-WINDOW",
                fact_key="infusion_date",
                value_raw="2026-01-01",
                value_type="date",
                observed_on=date(2026, 1, 1),
                source_ref=ref,
            ),
            FactImportRow(
                subject_external_id="SYN-SIBLING-WINDOW",
                fact_key="visit_date",
                value_raw="2026-01-02",
                value_type="date",
                observed_on=date(2026, 1, 2),
                source_ref=ref,
            ),
        ],
        key="w05-sibling-window-facts",
    )
    subject = _subject_by_external(
        api, services, "SYN-SIBLING-WINDOW"
    )
    body = _evaluate(api, subject["id"], "2026-01-02")
    sibling_keys = {
        item["requirement"]["visit_key"]
        for item in body["requirements"]
        if "R-WINDOW-SIBLINGS-01" in item["requirement"]["visit_key"]
    }
    assert sibling_keys == {
        "R-WINDOW-SIBLINGS-01:branch:B1",
        "R-WINDOW-SIBLINGS-01:branch:B2",
    }


@pytest.mark.parametrize(
    "shape,gate,expected",
    [
        ("direct", True, "out_of_window"),
        ("container", False, "not_applicable"),
        ("container", None, "unknown_applicability"),
        ("container", True, "out_of_window"),
    ],
    ids=[
        "direct-selected-window",
        "container-false",
        "container-unknown",
        "container-true-control",
    ],
)
def test_branch_target_preserves_window_and_selection_context(
    api, services, shape, gate, expected
):
    _confirm_branch_linked_window(api, services, shape=shape)
    source = {
        "source_type": "record",
        "source_id": "synthetic-branch-linked-window-source",
        "locator": "synthetic/branch-linked-window",
        "quote": "Pure synthetic eligibility and date facts",
    }
    values = [
        ("screening_active", "true", "boolean"),
        ("infusion_date", "2026-01-01", "date"),
        ("visit_date", "2026-01-10", "date"),
    ]
    if gate is not None:
        values.append(("gate_ok", str(gate).lower(), "boolean"))
    _import_rows(
        services,
        [
            FactImportRow(
                subject_external_id="SYN-BRANCH-LINK",
                fact_key=key,
                value_raw=value,
                value_type=value_type,
                observed_on=date(2026, 1, 1),
                source_ref=source,
            )
            for key, value, value_type in values
        ],
        key="w05-branch-linked-window-facts",
    )
    subject = _subject_by_external(api, services, "SYN-BRANCH-LINK")
    body = _evaluate(api, subject["id"], "2026-01-10")
    selected = [
        item
        for item in body["requirements"]
        if "RECHECK-BRANCH-WINDOW" in item["requirement"]["visit_key"]
    ]
    assert len(selected) == 1
    assert selected[0]["window_status"] == expected


def test_multiple_branch_entries_to_one_target_use_or_semantics():
    source_ref = RuleSourceRef(
        anchor_key="synthetic-multi-entry",
        quote="Synthetic alternate branch target",
    )

    def eq(key: str) -> RuleCondition:
        return RuleCondition(
            op="eq",
            left=RuleOperand(kind="fact_ref", fact_key=key),
            right=RuleOperand(kind="literal", value=True),
        )

    leaf = RuleNode(
        node_key="synthetic-leaf",
        summary="Synthetic date obligation",
        trigger=RuleCondition(
            op="date_interval",
            anchor_fact_key="anchor_date",
            fact_key="actual_date",
            min_days=-2,
            max_days=2,
        ),
        source_refs=[source_ref],
    )
    container = RuleNode(
        node_key="synthetic-container",
        summary="Synthetic shared branch target",
        children=[leaf],
        source_refs=[source_ref],
    )
    group = RuleNode(
        node_key="synthetic-group",
        summary="Synthetic alternate entry group",
        trigger=eq("group_ready"),
        branches=[
            {
                "branch_key": "A",
                "label": "Entry A",
                "condition": eq("entry_a"),
                "target_node_ids": [container.node_key],
                "source_refs": [source_ref],
            },
            {
                "branch_key": "B",
                "label": "Entry B",
                "condition": eq("entry_b"),
                "target_node_ids": [container.node_key],
                "source_refs": [source_ref],
            },
        ],
        children=[container],
        source_refs=[source_ref],
    )
    specs = extract_date_interval_specs(group)
    assert len(specs) == 1
    alternatives = next(
        condition
        for condition in specs[0].gate_conditions
        if condition.op == "any"
    )
    assert len(alternatives.children) == 2
    assert evaluate_condition(
        alternatives,
        {"entry_a": FactValue(value=False)},
    ).result == "unknown"
    assert evaluate_condition(
        alternatives,
        {
            "entry_a": FactValue(value=True),
            "entry_b": FactValue(value=False),
        },
    ).result == "true"


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
    _record_no_protocol_waiver(
        services,
        "SYN-001",
        key="w05-window-no-waiver",
        observed_on=date(2021, 1, 1),
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
    _record_no_protocol_waiver(
        services,
        "SYN-002",
        key="w05-skip-no-waiver",
        observed_on=date(2021, 1, 3),
    )
    _record_no_protocol_waiver(
        services,
        "SYN-001",
        key="w05-other-subject-no-waiver",
        observed_on=date(2021, 1, 1),
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
    _record_no_protocol_waiver(
        services,
        "SYN-001",
        key="w05-revision-no-waiver",
        observed_on=date(2021, 1, 1),
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
