"""Real-PostgreSQL acceptance for CRA-W09 safety analysis and boundaries."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from cra_app.governance.identity import SyntheticIdentityProvider
from cra_app.governance.service import (
    AuthorizationDenied,
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.main import create_app
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.providers.case_analysis import CaseModelResult
from cra_app.safety.contracts import CreateSafetyAssessmentCommand
from cra_app.safety.models import SafetyDimensionResult
from cra_app.safety.service import SafetyService
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.shared.output_contract import OutputEnvelope

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SAFETY_RULES = FIXTURES / "safety" / "rules.txt"
LAB_PDF = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report.pdf"
EDC_XLSX = FIXTURES / "edc" / "artifacts" / "synthetic_edc_lab.xlsx"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W09 never falls back to SQLite"
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
                "TRUNCATE TABLE safety_issue_links, medical_safety_responses, "
                "safety_cra_reviews, safety_dimension_results, "
                "safety_assessments, lab_comparison_issue_links, "
                "lab_comparison_fields, lab_comparisons, "
                "lab_observation_decisions, lab_observations, "
                "lab_report_versions, edc_lab_records, edc_snapshot_rows, "
                "edc_snapshots, edc_preview_cells, edc_preview_sheets, "
                "edc_import_previews, edc_import_mappings, "
                "carryover_candidates, carryover_imports, "
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
        CRA_SESSION_SECRET="synthetic-w09-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
        CRA_COMMON_POLICY_PATH=str(
            FIXTURES / "rules" / "common_policy.json"
        ),
        CRA_ANALYSIS_PROVIDER="disabled",
        CRA_OCR_PROVIDER="disabled",
    )


@pytest.fixture
def workspace(session_factory):
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
            idempotency_key="w09-study",
            code="W09-SYN",
            title="W09 Synthetic Safety Analysis",
        ),
    )
    sites = {}
    for key, code in (("site_a", "A01"), ("site_b", "B01")):
        sites[key] = governance.create_site(
            admin,
            study.resource_id,
            CreateSite(
                expected_revision=0,
                idempotency_key=f"w09-site-{key}",
                code=code,
                name=f"W09 Synthetic {code}",
            ),
        ).resource_id
    for actor, site_id in (
        ("synthetic-cra-a", sites["site_a"]),
        ("synthetic-cra-b", sites["site_b"]),
    ):
        governance.grant_membership(
            admin,
            study.resource_id,
            GrantMembership(
                expected_revision=0,
                idempotency_key=f"w09-grant-{actor}",
                actor_id=actor,
                role="cra",
                site_id=site_id,
                can_write=True,
            ),
        )
    return {
        "governance": governance,
        "study": study.resource_id,
        "site_a": sites["site_a"],
        "site_b": sites["site_b"],
    }


@pytest.fixture
def application(settings, session_factory, workspace):
    return create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
    )


@pytest.fixture
def api(application):
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _csrf(api: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": api.cookies.get("cra_csrf")}


def _scope_a() -> ScopeContext:
    return ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )


def _bootstrap_subject_and_rules(
    api: TestClient, application, workspace: dict
) -> tuple[str, str, str]:
    subject = api.post(
        f"/api/v1/studies/{workspace['study']}/subjects",
        json={
            "expected_revision": 0,
            "idempotency_key": "w09-subject",
            "site_id": str(workspace["site_a"]),
            "external_id": "SYN-EDC-001",
            "identity_namespace": "edc",
            "deidentified_label": "SYN-EDC-001",
        },
        headers=_csrf(api),
    )
    assert subject.status_code == 200, subject.text
    subject_id = subject.json()["id"]

    uploaded = api.post(
        f"/api/v1/studies/{workspace['study']}/documents",
        files={
            "file": (
                "synthetic_w09_safety_rules.txt",
                SAFETY_RULES.read_bytes(),
                "text/plain",
            )
        },
        data={
            "title": "Synthetic W09 safety rules",
            "document_type": "text",
            "purpose": "rule",
            "version_label": "v1",
            "expected_revision": "0",
            "site_id": str(workspace["site_a"]),
        },
        headers={**_csrf(api), "Idempotency-Key": "w09-rule-upload"},
    )
    assert uploaded.status_code == 202, uploaded.text
    upload_body = uploaded.json()
    assert application.state.document_service.process_job(
        uuid.UUID(upload_body["job_id"])
    ).status == "completed"

    extracted = api.post(
        f"/api/v1/document-versions/{upload_body['document_version_id']}"
        "/rule-candidates",
        json={
            "expected_revision": 0,
            "idempotency_key": "w09-rule-extract",
        },
        headers=_csrf(api),
    )
    assert extracted.status_code == 202, extracted.text
    extraction = extracted.json()
    assert (
        extraction["candidate_count"] + extraction["confirmed_count"] == 9
    )
    if extraction["candidate_count"]:
        listed = api.get(
            f"/api/v1/studies/{workspace['study']}/rules",
            params={"site_id": str(workspace["site_a"])},
        )
        assert listed.status_code == 200, listed.text
        rules = listed.json()
        assert len(rules) == 9
        for rule in rules:
            assert rule["current_version"] is not None
            confirmed = api.post(
                f"/api/v1/rules/{rule['id']}/confirmation",
                json={
                    "expected_revision": rule["revision"],
                    "idempotency_key": f"w09-confirm-{rule['rule_key']}",
                    "base_version_id": rule["current_version"]["id"],
                    "reason": "Synthetic CRA confirms the safety rule subset",
                    "operations": [
                        {
                            "op": "edit_fields",
                            "summary": rule["current_version"]["summary"],
                        }
                    ],
                },
                headers=_csrf(api),
            )
            assert confirmed.status_code == 200, confirmed.text

    activation = api.post(
        "/api/v1/version-activations",
        json={
            "expected_revision": 0,
            "idempotency_key": "w09-rule-activate",
            "document_version_id": upload_body["document_version_id"],
            "site_id": str(workspace["site_a"]),
            "starts_on": "2026-01-01",
            "reason": "Pure synthetic W09 event-time rule activation",
        },
        headers=_csrf(api),
    )
    assert activation.status_code == 200, activation.text
    return (
        subject_id,
        upload_body["document_version_id"],
        upload_body["document_id"],
    )


def _import_facts(
    api: TestClient,
    workspace: dict,
    *,
    facts: dict[str, object],
    key: str,
) -> None:
    rows = []
    for fact_key, value in facts.items():
        rows.append(
            {
                "subject_external_id": "SYN-EDC-001",
                "fact_key": fact_key,
                "value_raw": (
                    str(value).lower()
                    if isinstance(value, bool)
                    else str(value)
                ),
                "value_type": (
                    "boolean"
                    if isinstance(value, bool)
                    else "string"
                ),
                "observed_on": "2026-09-30",
                "source_kind": "original_record",
                "source_ref": {
                    "source_type": "record",
                    "source_id": f"SYNTHETIC-W09-{fact_key}",
                    "locator": f"synthetic/source/{fact_key}",
                    "quote": f"Pure synthetic value for {fact_key}",
                },
            }
        )
    imported = api.post(
        f"/api/v1/studies/{workspace['study']}/facts/import",
        json={
            "expected_revision": 0,
            "idempotency_key": key,
            "site_id": str(workspace["site_a"]),
            "identity_namespace": "edc",
            "source_kind": "original_record",
            "rows": rows,
        },
        headers=_csrf(api),
    )
    assert imported.status_code == 200, imported.text


def _assessment_command(
    workspace: dict,
    subject_id: str,
    *,
    key: str,
    event_type: str = "adverse_event",
    requested_dimensions: list[str] | None = None,
    lab_comparison_id: str | None = None,
    event_date: str = "2026-10-01",
) -> dict:
    return {
        "expected_revision": 0,
        "idempotency_key": key,
        "study_id": str(workspace["study"]),
        "site_id": str(workspace["site_a"]),
        "subject_id": subject_id,
        "event_type": event_type,
        "event_date": event_date,
        "requested_dimensions": requested_dimensions
        or [
            "ae_collection",
            "grade",
            "seriousness",
            "relatedness",
            "expectedness",
            "reporting_timeliness",
        ],
        "lab_comparison_id": lab_comparison_id,
        "note": "Pure synthetic W09 acceptance input",
    }


def _create_assessment(
    api: TestClient,
    workspace: dict,
    subject_id: str,
    *,
    key: str,
    event_type: str = "adverse_event",
    requested_dimensions: list[str] | None = None,
    lab_comparison_id: str | None = None,
) -> dict:
    response = api.post(
        "/api/v1/safety-assessments",
        json=_assessment_command(
            workspace,
            subject_id,
            key=key,
            event_type=event_type,
            requested_dimensions=requested_dimensions,
            lab_comparison_id=lab_comparison_id,
        ),
        headers=_csrf(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _dimension(body: dict, name: str) -> dict:
    return next(
        item for item in body["dimensions"] if item["dimension"] == name
    )


def test_dimensions_timely_alert_reviews_issue_and_immutability(
    api: TestClient,
    application,
    workspace: dict,
    session_factory,
):
    subject_id, _, _ = _bootstrap_subject_and_rules(
        api, application, workspace
    )
    _import_facts(
        api,
        workspace,
        facts={
            "ae_term": "synthetic headache",
            "grade_criteria_met": True,
        },
        key="w09-facts-ae-grade",
    )
    body = _create_assessment(
        api, workspace, subject_id, key="w09-assessment-ae-grade"
    )
    assert _dimension(body, "ae_collection")["status"] == "candidate"
    assert _dimension(body, "grade")["status"] == "candidate"
    assert _dimension(body, "seriousness")["status"] == "unknown"
    assert _dimension(body, "relatedness")["status"] == "unknown"
    assert _dimension(body, "expectedness")["status"] == "unknown"
    assert body["timely_alerts"] == []
    questions = " ".join(item["question"] for item in body["questions"])
    assert "SAE" in questions
    assert "相关性" in questions
    assert "参考安全性信息" in questions
    assert body["provider_status"] == "not_configured"
    assert body["replayed"] is False
    assert any(
        unknown["code"] == "provider:not_configured"
        for unknown in body["unknowns"]
    )
    fact_claims = [
        claim
        for claim in body["output_envelope"]["claims"]
        if claim["kind"] == "fact"
    ]
    assert fact_claims
    assert all(
        claim["verification_status"] != "auto_extracted"
        for claim in fact_claims
    )
    assert not any(
        claim["kind"] == "inference"
        for claim in body["output_envelope"]["claims"]
    )

    replay = _create_assessment(
        api, workspace, subject_id, key="w09-assessment-ae-grade"
    )
    assert replay["id"] == body["id"]
    assert replay["replayed"] is True

    reviewed = api.post(
        f"/api/v1/safety-assessments/{body['id']}/cra-review",
        json={
            "idempotency_key": "w09-cra-review",
            "decision": "reviewed_candidate",
            "dimensions": ["ae_collection", "grade"],
            "note": "Synthetic CRA checked candidate display only",
        },
        headers=_csrf(api),
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["cra_reviews"][0]["decision"] == (
        "reviewed_candidate"
    )

    medical = api.post(
        f"/api/v1/safety-assessments/{body['id']}/medical-response",
        json={
            "idempotency_key": "w09-medical-response",
            "respondent_role": "investigator",
            "respondent_name": "Synthetic Investigator",
            "response_text": (
                "Synthetic medical reply for review only; no clinical data."
            ),
            "dimension_responses": {
                "grade": "Synthetic investigator grade recorded separately."
            },
            "source_note": "Synthetic W09 response source",
        },
        headers=_csrf(api),
    )
    assert medical.status_code == 200, medical.text
    medical_body = medical.json()
    assert len(medical_body["cra_reviews"]) == 1
    assert len(medical_body["medical_responses"]) == 1
    assert _dimension(medical_body, "grade")["status"] == "candidate"

    issue = api.post(
        f"/api/v1/safety-assessments/{body['id']}/issues",
        json={
            "idempotency_key": "w09-link-issue",
            "dimensions": ["seriousness"],
            "action_kind": "medical_clarification",
            "requirement": "Confirm the synthetic SAE criterion.",
        },
        headers=_csrf(api),
    )
    assert issue.status_code == 200, issue.text
    issue_body = issue.json()
    assert issue_body["subject_id"] == subject_id
    assert issue_body["actions"][0]["kind"] == "medical_clarification"
    assert issue_body["actions"][0]["status"] == "open"
    repeated_issue = api.post(
        f"/api/v1/safety-assessments/{body['id']}/issues",
        json={
            "idempotency_key": "w09-link-issue-repeat",
            "dimensions": ["seriousness"],
            "action_kind": "medical_clarification",
            "requirement": "Confirm the synthetic SAE criterion.",
        },
        headers=_csrf(api),
    )
    assert repeated_issue.status_code == 200
    assert repeated_issue.json()["id"] == issue_body["id"]
    assert repeated_issue.json()["actions"][0]["status"] == "open"

    with session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(SafetyDimensionResult)
            .where(
                SafetyDimensionResult.assessment_id
                == uuid.UUID(body["id"])
            )
        ) == 6
        with pytest.raises(SQLAlchemyError):
            with session.begin():
                session.execute(
                    text(
                        "UPDATE safety_assessments SET event_type = 'mixed' "
                        "WHERE id = :id"
                    ),
                    {"id": body["id"]},
                )


def test_timely_alert_skip_scope_and_cross_site_denial(
    api: TestClient,
    application,
    workspace: dict,
):
    subject_id, _, _ = _bootstrap_subject_and_rules(
        api, application, workspace
    )
    _import_facts(
        api,
        workspace,
        facts={
            "ae_term": "synthetic hypersensitivity",
            "sae_criteria_met": True,
        },
        key="w09-facts-sae",
    )
    body = _create_assessment(
        api,
        workspace,
        subject_id,
        key="w09-assessment-sae",
        event_type="serious_event_review",
        requested_dimensions=[
            "seriousness",
            "relatedness",
            "reporting_timeliness",
        ],
    )
    assert _dimension(body, "seriousness")["status"] == "candidate"
    assert _dimension(body, "reporting_timeliness")["status"] == "candidate"
    assert len(body["timely_alerts"]) == 1
    alert = body["timely_alerts"][0]
    assert alert["event_date"] == "2026-10-01"
    assert alert["awareness_date"] is None
    assert alert["deadline_status"] == "awareness_time_missing"
    assert alert["not_a_final_reportability_decision"] is True
    assert body["questions"][0]["priority"] == "timely"
    assert "知悉" in body["questions"][0]["question"]
    assert "超期" in body["questions"][0]["question"]

    skipped_review = api.post(
        f"/api/v1/safety-assessments/{body['id']}/cra-review",
        json={
            "idempotency_key": "w09-skip-relatedness",
            "decision": "not_checked_by_user",
            "dimensions": ["relatedness"],
            "note": "Synthetic user declined this dependent safety path",
        },
        headers=_csrf(api),
    )
    assert skipped_review.status_code == 200, skipped_review.text
    derived = _create_assessment(
        api,
        workspace,
        subject_id,
        key="w09-assessment-after-skip",
        event_type="serious_event_review",
        requested_dimensions=[
            "seriousness",
            "relatedness",
            "reporting_timeliness",
        ],
    )
    assert derived["id"] != body["id"]
    assert _dimension(derived, "relatedness")["status"] == (
        "not_checked_by_user"
    )
    assert any(
        item["code"] == "not_checked:relatedness"
        for item in derived["output_envelope"]["not_checked"]
    )
    assert all(
        "normal" not in item["reason"].casefold()
        for item in derived["output_envelope"]["not_checked"]
    )

    command = CreateSafetyAssessmentCommand.model_validate(
        _assessment_command(
            workspace,
            subject_id,
            key="w09-cross-site",
            event_type="adverse_event",
            requested_dimensions=["ae_collection"],
        )
    )
    cross_site = command.model_copy(
        update={"site_id": workspace["site_b"]}
    )
    with pytest.raises(AuthorizationDenied):
        application.state.safety_service.create(_scope_a(), cross_site)

    scope_b = ScopeContext(
        actor_id="synthetic-cra-b",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    with pytest.raises(AuthorizationDenied):
        application.state.safety_service.detail(
            scope_b, uuid.UUID(body["id"])
        )


class _InvalidReferenceProvider:
    name = "invalid-test-provider"
    version = "1"

    def analyze_batch(self, requests):
        return [
            CaseModelResult(
                provider_name=self.name,
                provider_version=self.version,
                model_version="synthetic-invalid",
                status="completed",
                raw_output=json.dumps(
                    {
                        "explanation_code": "candidate_review",
                        "evidence_ids": ["RULE:NOT-SUPPLIED"],
                    }
                ),
            )
            for _ in requests
        ]


def test_invalid_provider_reference_is_rejected_without_decision(
    api: TestClient,
    application,
    workspace: dict,
    session_factory,
):
    subject_id, _, _ = _bootstrap_subject_and_rules(
        api, application, workspace
    )
    _import_facts(
        api,
        workspace,
        facts={
            "ae_term": "synthetic rash",
            "grade_criteria_met": True,
        },
        key="w09-facts-invalid-provider",
    )
    governed = application.state
    service = SafetyService(
        session_factory,
        governance=governed.governance_service,
        rules=governed.rule_service,
        subjects=governed.subject_service,
        issues=governed.issue_service,
        laboratory=governed.laboratory_service,
        provider=_InvalidReferenceProvider(),
    )
    detail = service.create(
        _scope_a(),
        CreateSafetyAssessmentCommand.model_validate(
            _assessment_command(
                workspace,
                subject_id,
                key="w09-invalid-provider",
                requested_dimensions=["grade", "seriousness"],
            )
        ),
    )
    assert detail.assessment.provider_status == "rejected"
    assert detail.assessment.provider_output["accepted"] is False
    assert any(
        "unknown_evidence_ids" in error
        for error in detail.assessment.provider_output["errors"]
    )
    envelope = OutputEnvelope.model_validate(
        detail.assessment.output_envelope
    )
    assert not any(claim.kind == "inference" for claim in envelope.claims)
    seriousness = next(
        item
        for item in detail.dimensions
        if item.dimension == "seriousness"
    )
    assert seriousness.status == "unknown"


def _edc_mapping() -> dict:
    columns = {
        "subject_external_id": "Subject ID",
        "visit_key": "Visit",
        "analyte": "Analyte",
        "value_raw": "Result",
        "unit": "Unit",
        "collected_on": "Collection Date",
        "collected_at": "Collection Time",
        "instance_type": "Instance",
        "repeat_instance": "Repeat No",
        "report_on": "Report Date",
        "specimen": "Specimen",
        "lower_limit": "LLN",
        "upper_limit": "ULN",
    }
    return {
        "sheets": {
            name: {
                "header_row": 1,
                "data_start_row": 2,
                "columns": columns,
                "included": True,
            }
            for name in ("Hematology", "Chemistry")
        }
    }


def test_laboratory_difference_generates_specific_question_not_safe_conclusion(
    api: TestClient,
    application,
    workspace: dict,
):
    subject_id, _, _ = _bootstrap_subject_and_rules(
        api, application, workspace
    )
    preview = api.post(
        f"/api/v1/studies/{workspace['study']}/edc-imports/preview",
        files={
            "file": (
                EDC_XLSX.name,
                EDC_XLSX.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "site_id": str(workspace["site_a"]),
            "title": "Synthetic W09 EDC export",
            "export_scope_json": json.dumps(
                {
                    "status": "declared",
                    "forms": ["Hematology", "Chemistry"],
                    "subjects": ["SYN-EDC-001"],
                    "sites": ["A01"],
                    "date_start": "2026-01-01",
                    "date_end": "2026-01-03",
                    "filters": {},
                    "declared_complete": False,
                    "note": "Pure synthetic filtered export.",
                }
            ),
            "included_sheets_json": json.dumps(
                ["Hematology", "Chemistry"]
            ),
            "identity_namespace": "edc",
        },
        headers={**_csrf(api), "Idempotency-Key": "w09-edc-preview"},
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    snapshot = api.post(
        f"/api/v1/edc-imports/{preview_body['id']}/confirm",
        json={
            "expected_revision": preview_body["revision"],
            "idempotency_key": "w09-edc-confirm",
            "mapping": _edc_mapping(),
            "identity_namespace": "edc",
        },
        headers=_csrf(api),
    )
    assert snapshot.status_code == 200, snapshot.text

    report = api.post(
        f"/api/v1/studies/{workspace['study']}/lab-reports",
        files={
            "file": (
                LAB_PDF.name,
                LAB_PDF.read_bytes(),
                "application/pdf",
            )
        },
        data={
            "site_id": str(workspace["site_a"]),
            "title": "Synthetic W09 laboratory report",
            "version_label": "v1",
        },
        headers={**_csrf(api), "Idempotency-Key": "w09-lab-report"},
    )
    assert report.status_code == 200, report.text
    comparison = api.post(
        "/api/v1/lab-comparisons",
        json={
            "expected_revision": 0,
            "idempotency_key": "w09-lab-comparison",
            "report_id": report.json()["id"],
            "edc_snapshot_id": snapshot.json()["id"],
        },
        headers=_csrf(api),
    )
    assert comparison.status_code == 200, comparison.text
    assert any(
        field["result_status"] != "agreement"
        for field in comparison.json()["fields"]
    )
    body = _create_assessment(
        api,
        workspace,
        subject_id,
        key="w09-lab-safety",
        event_type="laboratory_logic",
        requested_dimensions=["ae_collection"],
        lab_comparison_id=comparison.json()["id"],
    )
    assert any(
        "AE线索" in item["question"]
        and "数值一致或差异均不等于医学安全结论" in item["question"]
        for item in body["questions"]
    )
    serialized = json.dumps(body, ensure_ascii=False).casefold()
    assert "clinical_safe" not in serialized
    assert "completion_allowed\": true" not in serialized
