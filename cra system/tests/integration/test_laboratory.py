"""Real-PostgreSQL acceptance for CRA-W08 laboratory comparison."""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from cra_app.documents.service import DocumentService
from cra_app.documents.storage import build_private_storage
from cra_app.documents.models import DocumentVersion
from cra_app.documents.worker import build_worker_app
from cra_app.governance.models import AuditEvent
from cra_app.governance.identity import SyntheticIdentityProvider
from cra_app.governance.service import (
    CreateSite,
    CreateStudy,
    GrantMembership,
    GovernanceService,
    ScopeContext,
)
from cra_app.issues.service import IssueService
from cra_app.laboratory.comparison import (
    EdcValue,
    ObservationValue,
    compare_observation,
)
from cra_app.laboratory.recognition import extract_observations
from cra_app.laboratory.models import (
    LabComparison,
    LabObservation,
    LabRecognitionJob,
    LabReportVersion,
)
from cra_app.laboratory.service import LaboratoryService
from cra_app.main import create_app
from cra_app.platform.jobs import ProcrastinateQueue
from cra_app.providers.lab_ocr import RoutedLabProvider
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.subjects.contracts import CreateSubjectCommand
from cra_app.subjects.service import SubjectService

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LAB_PDF = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report.pdf"
LAB_PNG = FIXTURES / "labs" / "artifacts" / "synthetic_lab_report_eval.png"
ZH_CONTEXT_PDF = (
    FIXTURES / "labs" / "artifacts" / "synthetic_lab_report_zh_context.pdf"
)
EDC_XLSX = FIXTURES / "edc" / "artifacts" / "synthetic_edc_lab.xlsx"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W08 never falls back to SQLite"
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
                "TRUNCATE TABLE lab_comparison_issue_links, "
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
        CRA_SESSION_SECRET="synthetic-w08-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="local",
        CRA_PRIVATE_STORAGE_LOCAL_PATH=str(tmp_path / "private"),
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
            idempotency_key="w08-study",
            code="W08-SYN",
            title="W08 Synthetic Laboratory Comparison",
        ),
    )
    sites = {}
    for key, code in (("site_a", "S01"), ("site_b", "S02")):
        sites[key] = governance.create_site(
            admin,
            study.resource_id,
            CreateSite(
                expected_revision=0,
                idempotency_key=f"w08-{key}",
                code=code,
                name=f"Synthetic W08 {code}",
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
                idempotency_key=f"w08-grant-{actor}",
                actor_id=actor,
                role="cra",
                site_id=site_id,
                can_write=True,
            ),
        )
    documents = DocumentService(
        session_factory,
        storage=build_private_storage(settings),
        queue=queue,
        governance=governance,
    )
    subjects = SubjectService(session_factory, governance=governance)
    cra_a = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    for suffix in ("001", "002"):
        subjects.create_subject(
            cra_a,
            study.resource_id,
            CreateSubjectCommand(
                expected_revision=0,
                idempotency_key=f"w08-subject-{suffix}",
                site_id=sites["site_a"],
                external_id=f"SYN-EDC-{suffix}",
                identity_namespace="edc",
                deidentified_label=f"SYN-EDC-{suffix}",
            ),
        )
    issues = IssueService(
        session_factory,
        governance=governance,
        documents=documents,
    )
    return {
        "governance": governance,
        "study": study.resource_id,
        "sites": sites,
        "documents": documents,
        "subjects": subjects,
        "issues": issues,
    }


@pytest.fixture
def application(settings, session_factory, services):
    app = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
        document_service=services["documents"],
        subject_service=services["subjects"],
        issue_service=services["issues"],
    )
    app.state.laboratory_service = LaboratoryService(
        session_factory,
        documents=services["documents"],
        edc_imports=app.state.edc_import_service,
        issues=services["issues"],
        governance=services["governance"],
        provider=RoutedLabProvider(ocr_provider="disabled"),
    )
    return app


@pytest.fixture
def api(application):
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _csrf(api: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": api.cookies.get("cra_csrf")}


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


def _confirm_edc(api: TestClient, services: dict) -> dict:
    preview = api.post(
        f"/api/v1/studies/{services['study']}/edc-imports/preview",
        files={
            "file": (
                EDC_XLSX.name,
                EDC_XLSX.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "site_id": str(services["sites"]["site_a"]),
            "title": "Synthetic W08 EDC export",
            "export_scope_json": json.dumps(
                {
                    "status": "declared",
                    "forms": ["Hematology", "Chemistry"],
                    "subjects": ["SYN-EDC-001", "SYN-EDC-002"],
                    "sites": ["S01"],
                    "date_start": "2026-01-01",
                    "date_end": "2026-01-03",
                    "filters": {},
                    "declared_complete": False,
                    "note": "Synthetic filtered export.",
                }
            ),
            "included_sheets_json": json.dumps(["Hematology", "Chemistry"]),
            "identity_namespace": "edc",
        },
        headers={**_csrf(api), "Idempotency-Key": "w08-edc-preview"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    confirmed = api.post(
        f"/api/v1/edc-imports/{body['id']}/confirm",
        json={
            "expected_revision": body["revision"],
            "idempotency_key": "w08-edc-confirm",
            "mapping": _edc_mapping(),
            "identity_namespace": "edc",
        },
        headers=_csrf(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    listed = api.get(
        f"/api/v1/studies/{services['study']}/edc-snapshots"
        f"?site_id={services['sites']['site_a']}"
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["id"] == confirmed.json()["id"]
    return confirmed.json()


def _queue_lab(
    api: TestClient,
    services: dict,
    *,
    key: str = "w08-lab",
    title: str = "Synthetic W08 laboratory report",
) -> dict:
    response = api.post(
        f"/api/v1/studies/{services['study']}/lab-reports",
        files={"file": (LAB_PDF.name, LAB_PDF.read_bytes(), "application/pdf")},
        data={
            "site_id": str(services["sites"]["site_a"]),
            "title": title,
            "version_label": "v1",
        },
        headers={**_csrf(api), "Idempotency-Key": key},
    )
    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued["state"] == "pending"
    return queued


def _upload_lab(api: TestClient, services: dict, *, key: str = "w08-lab") -> dict:
    queued = _queue_lab(api, services, key=key)
    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    api.app.state.laboratory_service.process_recognition_job(
        scope,
        uuid.UUID(queued["recognition_job_id"]),
        worker_id="synthetic-test-worker",
    )
    completed = api.get(f"/api/v1/lab-reports/{queued['id']}")
    assert completed.status_code == 200, completed.text
    return completed.json()


def _create_comparison(
    api: TestClient,
    report_id: str,
    snapshot_id: str,
    *,
    key: str,
) -> dict:
    response = api.post(
        "/api/v1/lab-comparisons",
        json={
            "expected_revision": 0,
            "idempotency_key": key,
            "report_id": report_id,
            "edc_snapshot_id": snapshot_id,
        },
        headers=_csrf(api),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_text_pdf_initial_repeat_scope_and_issue_link(
    api: TestClient, services: dict, session_factory
):
    snapshot = _confirm_edc(api, services)
    report = _upload_lab(api, services)
    assert report["state"] == "recognized"
    assert report["provider_name"] == "pdfplumber-lab-table"
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob, uuid.UUID(report["recognition_job_id"])
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.output["observations"] == 5
        source = session.get(
            DocumentVersion, uuid.UUID(report["source_document_version_id"])
        )
        assert source is not None
        assert source.parse_status in {"pending", "completed"}
    assert report["observations_count"] == 5
    assert report["file_format"] == "text_pdf"
    assert report["support_profile"]["clinical_use_validated"] is False
    assert all(
        item["source_ref"]["page"] == 1
        and item["source_ref"]["cells"]["analyte"]["bbox"]
        for item in report["observations"]
    )
    ready_ids = [
        item["id"]
        for item in report["observations"]
        if item["validation_state"] == "ready_for_match"
    ]
    confirmed = api.post(
        f"/api/v1/lab-reports/{report['id']}/observations/batch-confirm",
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w08-batch-ready",
            "observation_ids": ready_ids,
            "note": "Synthetic normal-range batch confirmation",
        },
        headers=_csrf(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    report = confirmed.json()
    assert {
        item["extraction_state"]
        for item in report["observations"]
        if item["id"] in ready_ids
    } == {"user_confirmed"}

    comparison = _create_comparison(
        api, report["id"], snapshot["id"], key="w08-compare-basic"
    )
    assert comparison["state"] == "complete"
    assert comparison["scope"]["medical_safety_assessed"] is False
    assert comparison["scope"]["edc_absence_semantics"] == (
        "not_seen_in_export"
    )
    fields = comparison["fields"]
    hb_initial = next(
        field
        for field in fields
        if field["matched_identity"]["analyte"] == "Hemoglobin"
        and field["matched_identity"]["instance_type"] == "initial"
    )
    hb_repeat = next(
        field
        for field in fields
        if field["matched_identity"]["analyte"] == "Hemoglobin"
        and field["matched_identity"]["instance_type"] == "repeat"
    )
    assert hb_initial["match_status"] == "unique_validated"
    assert hb_initial["result_status"] == "agreement"
    assert hb_repeat["result_status"] == "agreement"
    assert hb_initial["edc_record_id"] != hb_repeat["edc_record_id"]

    glucose = next(
        field
        for field in fields
        if field["matched_identity"]["analyte"] == "Glucose"
    )
    assert glucose["result_status"] == "unit_review"
    assert "unit_missing" in glucose["unknowns"]

    alt = next(
        field
        for field in fields
        if field["matched_identity"]["analyte"] == "ALT"
    )
    assert alt["result_status"] == "not_seen_in_export"
    assert alt["match_status"] == "unmatched"

    linked = api.post(
        f"/api/v1/lab-comparisons/{comparison['id']}/issues",
        json={
            "idempotency_key": "w08-link-glucose",
            "field_ids": [glucose["id"]],
        },
        headers=_csrf(api),
    )
    assert linked.status_code == 200, linked.text
    issue = linked.json()["issues"][0]
    assert issue["actions"][0]["kind"] == "edc_correction"
    assert all(
        action["kind"] != "pd_reporting" for action in issue["actions"]
    )
    assert issue["subject_id"] is not None


def test_correction_recomputes_difference_without_overwriting_source(
    api: TestClient, services: dict, session_factory
):
    snapshot = _confirm_edc(api, services)
    report = _upload_lab(api, services, key="w08-lab-correction")
    observation = next(
        item
        for item in report["observations"]
        if item["analyte"] == "Hemoglobin"
        and item["instance_type"] == "initial"
    )
    original_comparison = _create_comparison(
        api,
        report["id"],
        snapshot["id"],
        key="w08-compare-before-correction",
    )
    assert original_comparison["stale"] is False
    corrected = api.post(
        (
            f"/api/v1/lab-reports/{report['id']}/observations/"
            f"{observation['id']}/decision"
        ),
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w08-correct-hb",
            "action": "correct",
            "corrected_fields": {"value_raw": "122"},
            "note": "Synthetic CRA correction for recomputation test",
        },
        headers=_csrf(api),
    )
    assert corrected.status_code == 200, corrected.text
    corrected_body = corrected.json()
    corrected_observation = next(
        item
        for item in corrected_body["observations"]
        if item["id"] == observation["id"]
    )
    assert corrected_observation["value_raw"] == "122"
    assert corrected_observation["extraction_state"] == "user_corrected"
    stale = api.get(f"/api/v1/lab-comparisons/{original_comparison['id']}")
    assert stale.status_code == 200
    assert stale.json()["stale"] is True
    assert stale.json()["report_current_revision"] == corrected_body["revision"]
    corrected_field = next(
        field
        for field in stale.json()["fields"]
        if field["observation_id"] == observation["id"]
    )
    assert corrected_field["stale"] is True
    assert len(stale.json()["stale_field_ids"]) == 1
    unaffected = next(
        field
        for field in stale.json()["fields"]
        if field["observation_id"] != observation["id"]
    )
    assert unaffected["stale"] is False
    stale_link = api.post(
        f"/api/v1/lab-comparisons/{original_comparison['id']}/issues",
        json={
            "idempotency_key": "w08-stale-link",
            "field_ids": [corrected_field["id"]],
        },
        headers=_csrf(api),
    )
    assert stale_link.status_code == 409

    comparison = _create_comparison(
        api,
        report["id"],
        snapshot["id"],
        key="w08-compare-corrected",
    )
    field = next(
        item
        for item in comparison["fields"]
        if item["observation_id"] == observation["id"]
    )
    assert field["result_status"] == "value_difference"
    with session_factory() as session:
        source = session.get(LabObservation, uuid.UUID(observation["id"]))
        assert source is not None
        assert source.value_raw == "121"
        with pytest.raises(SQLAlchemyError):
            with session.begin():
                session.execute(
                    text(
                        "UPDATE lab_observations SET value_raw = '999' "
                        "WHERE id = :id"
                    ),
                    {"id": source.id},
                )


def test_confirm_and_successive_corrections_keep_current_effective_value(
    api: TestClient, services: dict
):
    report = _upload_lab(api, services, key="w08-correction-chain")
    observation = next(
        item
        for item in report["observations"]
        if item["analyte"] == "Hemoglobin"
        and item["instance_type"] == "initial"
    )
    value_corrected = api.post(
        (
            f"/api/v1/lab-reports/{report['id']}/observations/"
            f"{observation['id']}/decision"
        ),
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w08-chain-value",
            "action": "correct",
            "corrected_fields": {"value_raw": "119"},
            "note": "Synthetic CRA value correction",
        },
        headers=_csrf(api),
    )
    assert value_corrected.status_code == 200, value_corrected.text
    corrected = value_corrected.json()
    confirmed = api.post(
        (
            f"/api/v1/lab-reports/{report['id']}/observations/"
            f"{observation['id']}/decision"
        ),
        json={
            "expected_revision": corrected["revision"],
            "idempotency_key": "w08-chain-confirm",
            "action": "confirm",
            "note": "Synthetic CRA confirms the current corrected value",
        },
        headers=_csrf(api),
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_body = confirmed.json()
    current = next(
        item
        for item in confirmed_body["observations"]
        if item["id"] == observation["id"]
    )
    assert current["value_raw"] == "119"
    assert current["extraction_state"] == "user_confirmed"

    unit_corrected = api.post(
        (
            f"/api/v1/lab-reports/{report['id']}/observations/"
            f"{observation['id']}/decision"
        ),
        json={
            "expected_revision": confirmed_body["revision"],
            "idempotency_key": "w08-chain-unit",
            "action": "correct",
            "corrected_fields": {"unit_raw": "g/L"},
            "note": "Synthetic CRA later corrects only the unit",
        },
        headers=_csrf(api),
    )
    assert unit_corrected.status_code == 200, unit_corrected.text
    latest = next(
        item
        for item in unit_corrected.json()["observations"]
        if item["id"] == observation["id"]
    )
    assert latest["value_raw"] == "119"
    assert latest["unit"] == "g/L"
    batch = api.post(
        f"/api/v1/lab-reports/{report['id']}/observations/batch-confirm",
        json={
            "expected_revision": unit_corrected.json()["revision"],
            "idempotency_key": "w08-chain-batch",
            "observation_ids": [observation["id"]],
            "note": "Synthetic batch confirmation of the current correction",
        },
        headers=_csrf(api),
    )
    assert batch.status_code == 200, batch.text
    after_batch = next(
        item
        for item in batch.json()["observations"]
        if item["id"] == observation["id"]
    )
    assert after_batch["value_raw"] == "119"
    assert after_batch["unit"] == "g/L"
    with api.app.state.session_factory() as session:
        candidates = list(
            session.scalars(
                select(LabObservation).where(
                    LabObservation.id == uuid.UUID(observation["id"])
                )
            )
        )
        assert candidates[0].value_raw == "121"


def test_skip_is_scope_limited_and_not_normal(api: TestClient, services: dict):
    snapshot = _confirm_edc(api, services)
    report = _upload_lab(api, services, key="w08-lab-skip")
    repeat = next(
        item
        for item in report["observations"]
        if item["analyte"] == "Hemoglobin"
        and item["instance_type"] == "repeat"
    )
    skipped = api.post(
        (
            f"/api/v1/lab-reports/{report['id']}/observations/"
            f"{repeat['id']}/decision"
        ),
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w08-skip-repeat",
            "action": "skip",
            "note": "Synthetic user does not need this repeat comparison",
        },
        headers=_csrf(api),
    )
    assert skipped.status_code == 200, skipped.text
    comparison = _create_comparison(
        api, report["id"], snapshot["id"], key="w08-compare-skip"
    )
    skipped_field = next(
        field
        for field in comparison["fields"]
        if field["observation_id"] == repeat["id"]
    )
    assert skipped_field["result_status"] == "not_checked_by_user"
    assert "user_skipped" in skipped_field["unknowns"]
    assert skipped_field["matched_identity"]["analyte"] == "Hemoglobin"
    other = next(
        field
        for field in comparison["fields"]
        if field["observation_id"]
        != repeat["id"]
        and field["result_status"] == "agreement"
    )
    assert other["result_status"] != "not_checked_by_user"


def test_comparison_is_idempotent_and_cross_site_is_denied(
    api: TestClient, services: dict
):
    snapshot = _confirm_edc(api, services)
    report = _upload_lab(api, services, key="w08-lab-auth")
    first = _create_comparison(
        api, report["id"], snapshot["id"], key="w08-compare-reuse"
    )
    second = _create_comparison(
        api, report["id"], snapshot["id"], key="w08-compare-reuse"
    )
    assert second["id"] == first["id"]
    assert second["replayed"] is True
    provider = SyntheticIdentityProvider(api.app.state.settings)
    identity = provider.create_identity(actor_id="synthetic-cra-b")
    api.cookies.clear()
    api.cookies.set("cra_session", provider.issue_session(identity), path="/")
    denied = api.get(f"/api/v1/lab-comparisons/{first['id']}")
    assert denied.status_code == 403


def test_comparator_bound_and_ambiguity_do_not_guess():
    source = ObservationValue(
        id="source",
        subject_external_id="SYN-EDC-001",
        visit_key="V1",
        analyte="Hemoglobin",
        specimen="Blood",
        collected_on=date(2026, 1, 2),
        collected_at=None,
        instance_type="initial",
        report_on=None,
        report_revision="FINAL",
        value_raw="<12",
        unit="g/L",
    )
    edc = EdcValue(
        id="edc-1",
        subject_external_id="SYN-EDC-001",
        subject_id="subject",
        visit_key="V1",
        analyte="Hemoglobin",
        specimen="Blood",
        collected_on=date(2026, 1, 2),
        collected_at=None,
        instance_type="initial",
        report_on=None,
        report_revision="FINAL",
        value_raw="12",
        unit="g/L",
    )
    outcome = compare_observation(source, [edc])
    assert outcome.result_status == "not_comparable"
    assert "bound_value_requires_review" in outcome.unknowns
    duplicate = EdcValue(**{**edc.__dict__, "id": "edc-2"})
    ambiguous = compare_observation(source, [edc, duplicate])
    assert ambiguous.match_status == "ambiguous"
    assert ambiguous.result_status == "not_comparable"
    revised = EdcValue(**{**edc.__dict__, "report_revision": "AMENDED"})
    revision_outcome = compare_observation(source, [revised])
    assert revision_outcome.result_status == "not_comparable"
    assert "report_revision_mismatch" in revision_outcome.unknowns
    exact_source = ObservationValue(
        **{
            **source.__dict__,
            "value_raw": "12",
            "lower_limit": "0",
            "upper_limit": "10",
        }
    )
    range_mismatch = EdcValue(
        **{
            **edc.__dict__,
            "value_raw": "12",
            "lower_limit": "0",
            "upper_limit": "20",
        }
    )
    logic = compare_observation(exact_source, [range_mismatch])
    assert logic.result_status == "logic_difference"
    assert "reference_range_flag_difference" in logic.unknowns


def test_ocr_disabled_preserves_file_and_allows_small_manual_fallback(
    api: TestClient, services: dict
):
    uploaded = api.post(
        f"/api/v1/studies/{services['study']}/lab-reports",
        files={"file": (LAB_PNG.name, LAB_PNG.read_bytes(), "image/png")},
        data={
            "site_id": str(services["sites"]["site_a"]),
            "title": "Synthetic image with OCR disabled",
            "version_label": "v1",
        },
        headers={**_csrf(api), "Idempotency-Key": "w08-image-disabled"},
    )
    assert uploaded.status_code == 202, uploaded.text
    queued = uploaded.json()
    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    api.app.state.laboratory_service.process_recognition_job(
        scope,
        uuid.UUID(queued["recognition_job_id"]),
        worker_id="synthetic-test-worker",
    )
    report = api.get(f"/api/v1/lab-reports/{queued['id']}").json()
    assert report["state"] == "provider_unavailable"
    assert report["observations_count"] == 0
    assert "OCR" in report["warnings"][0]

    manual = api.post(
        f"/api/v1/lab-reports/{report['id']}/observations",
        json={
            "expected_revision": report["revision"],
            "idempotency_key": "w08-manual-fallback",
            "subject_external_id": "SYN-EDC-001",
            "visit_key": "V1",
            "analyte_raw": "Glucose",
            "specimen": "Blood",
            "collected_on": "2026-01-02",
            "collected_at": "2026-01-02T09:15:00+00:00",
            "instance_type_raw": "Initial",
            "report_on": "2026-01-02",
            "report_revision": "FINAL",
            "value_raw": "5.1",
            "unit_raw": "mmol/L",
            "lower_limit_raw": "3.9",
            "upper_limit_raw": "5.5",
            "source_note": "Synthetic fallback for unavailable image OCR",
        },
        headers=_csrf(api),
    )
    assert manual.status_code == 200, manual.text
    body = manual.json()
    assert body["observations_count"] == 1
    assert body["observations"][0]["extraction_state"] == "manual"
    assert body["observations"][0]["source_ref"]["provider"] == "manual-entry"


def test_lab_upload_returns_queued_job_and_recovers_expired_lease(
    api: TestClient, services: dict, session_factory
):
    uploaded = api.post(
        f"/api/v1/studies/{services['study']}/lab-reports",
        files={"file": (LAB_PDF.name, LAB_PDF.read_bytes(), "application/pdf")},
        data={
            "site_id": str(services["sites"]["site_a"]),
            "title": "Synthetic queued laboratory report",
            "version_label": "v1",
        },
        headers={**_csrf(api), "Idempotency-Key": "w08-queued-lab"},
    )
    assert uploaded.status_code == 202, uploaded.text
    queued = uploaded.json()
    assert queued["state"] == "pending"
    assert queued["observations_count"] == 0
    with session_factory() as session:
        assert session.scalar(
            text(
                "SELECT count(*) FROM procrastinate_jobs "
                "WHERE task_name = 'cra.laboratory.recognize'"
            )
        ) == 1
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(queued["recognition_job_id"]),
        )
        assert job is not None and job.status == "queued"
        job.status = "running"
        job.attempts = 1
        job.lease_owner = "interrupted-worker"
        job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    recovered = api.app.state.laboratory_service.process_recognition_job(
        scope,
        uuid.UUID(queued["recognition_job_id"]),
        worker_id="recovery-worker",
    )
    assert recovered.report.state == "recognized"
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(queued["recognition_job_id"]),
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.attempts == 2
        assert job.lease_owner is None


def test_real_procrastinate_worker_processes_laboratory_job(
    api: TestClient, services: dict, settings: Settings, session_factory
):
    uploaded = api.post(
        f"/api/v1/studies/{services['study']}/lab-reports",
        files={"file": (LAB_PDF.name, LAB_PDF.read_bytes(), "application/pdf")},
        data={
            "site_id": str(services["sites"]["site_a"]),
            "title": "Synthetic worker laboratory report",
            "version_label": "v1",
        },
        headers={**_csrf(api), "Idempotency-Key": "w08-worker-lab"},
    )
    assert uploaded.status_code == 202, uploaded.text
    queued = uploaded.json()
    worker = build_worker_app(
        services["documents"],
        _database_url(),
        api.app.state.laboratory_service,
    )
    worker.run_worker(queues=["laboratory"], concurrency=1, wait=False)
    completed = api.get(f"/api/v1/lab-reports/{queued['id']}")
    assert completed.status_code == 200, completed.text
    assert completed.json()["state"] == "recognized"
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(queued["recognition_job_id"]),
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.attempts == 1


def test_succeeded_job_redelivery_is_noop_before_provider(
    api: TestClient, services: dict, session_factory
):
    report = _upload_lab(api, services, key="w08-redelivery-noop")
    service = api.app.state.laboratory_service
    real_provider = service.provider
    calls = []

    class CountingProvider:
        enabled = True
        name = "synthetic-counting-provider"
        version = "1"

        def recognize(self, content, *, filename, media_type):
            calls.append(1)
            return real_provider.recognize(
                content,
                filename=filename,
                media_type=media_type,
            )

    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    with session_factory() as session:
        audits_before = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.resource_id == uuid.UUID(report["id"]),
                AuditEvent.action == "laboratory.recognition.completed",
            )
        )
    service.provider = CountingProvider()
    try:
        worker = build_worker_app(
            services["documents"],
            _database_url(),
            service,
        )
        worker.run_worker(queues=["laboratory"], concurrency=1, wait=False)
    finally:
        service.provider = real_provider
    current = service.report_detail(scope, uuid.UUID(report["id"]))
    assert calls == []
    assert current.report.revision == report["revision"]
    assert len(current.observations) == report["observations_count"] == 5
    with session_factory() as session:
        audits_after = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.resource_id == uuid.UUID(report["id"]),
                AuditEvent.action == "laboratory.recognition.completed",
            )
        )
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(report["recognition_job_id"]),
        )
        assert job is not None and job.status == "succeeded"
        assert job.attempts == 1
    assert audits_after == audits_before == 1


def test_public_retry_recovers_expired_lease_but_protects_live_lease(
    api: TestClient, services: dict, session_factory
):
    expired = _queue_lab(
        api,
        services,
        key="w08-expired-public-retry",
        title="Synthetic expired public retry",
    )
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(expired["recognition_job_id"]),
        )
        assert job is not None
        job.status = "running"
        job.attempts = 1
        job.lease_owner = "synthetic-expired-worker"
        job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
    retried = api.post(
        f"/api/v1/lab-reports/{expired['id']}/retry-recognition",
        headers=_csrf(api),
    )
    assert retried.status_code == 202, retried.text
    assert retried.json()["state"] == "pending"
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(expired["recognition_job_id"]),
        )
        assert job is not None
        assert job.status == "queued"
        assert job.lease_owner is None
        assert job.lease_expires_at is None

    worker = build_worker_app(
        services["documents"],
        _database_url(),
        api.app.state.laboratory_service,
    )
    worker.run_worker(queues=["laboratory"], concurrency=1, wait=False)
    completed = api.get(f"/api/v1/lab-reports/{expired['id']}")
    assert completed.status_code == 200, completed.text
    assert completed.json()["state"] == "recognized"
    assert completed.json()["observations_count"] == 5

    live = _queue_lab(
        api,
        services,
        key="w08-live-public-retry",
        title="Synthetic live public retry",
    )
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(live["recognition_job_id"]),
        )
        assert job is not None
        job.status = "running"
        job.attempts = 1
        job.lease_owner = "synthetic-live-worker"
        job.lease_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        session.commit()
    denied = api.post(
        f"/api/v1/lab-reports/{live['id']}/retry-recognition",
        headers=_csrf(api),
    )
    assert denied.status_code == 409, denied.text
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(live["recognition_job_id"]),
        )
        assert job is not None
        assert job.status == "running"
        assert job.lease_owner == "synthetic-live-worker"


def test_obsolete_attempt_cannot_overwrite_new_result_or_cra_correction(
    api: TestClient, services: dict, session_factory
):
    queued = _queue_lab(
        api,
        services,
        key="w08-stale-attempt-fence",
        title="Synthetic stale attempt fence",
    )
    service = api.app.state.laboratory_service
    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    old_claim = service._claim_job(
        scope,
        uuid.UUID(queued["recognition_job_id"]),
        worker_id="synthetic-obsolete-worker",
    )
    stored = services["documents"].read_content(
        scope,
        uuid.UUID(queued["source_document_version_id"]),
    )
    old_result = service.provider.recognize(
        stored.content,
        filename=stored.filename,
        media_type=stored.media_type,
    )
    old_draft = extract_observations(old_result)
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(queued["recognition_job_id"]),
        )
        assert job is not None
        job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
    retried = api.post(
        f"/api/v1/lab-reports/{queued['id']}/retry-recognition",
        headers=_csrf(api),
    )
    assert retried.status_code == 202, retried.text
    completed = service.process_recognition_job(
        scope,
        uuid.UUID(queued["recognition_job_id"]),
        worker_id="synthetic-new-worker",
    )
    assert completed.report.state == "recognized"
    hemoglobin = next(
        row
        for row in completed.observations
        if row.analyte_raw == "Hemoglobin"
        and row.instance_type == "initial"
    )
    corrected = api.post(
        (
            f"/api/v1/lab-reports/{queued['id']}/observations/"
            f"{hemoglobin.id}/decision"
        ),
        json={
            "expected_revision": completed.report.revision,
            "idempotency_key": "w08-stale-attempt-correction",
            "action": "correct",
            "corrected_fields": {"value_raw": "119"},
            "note": "Synthetic CRA correction before obsolete result arrives",
        },
        headers=_csrf(api),
    )
    assert corrected.status_code == 200, corrected.text
    corrected_body = corrected.json()
    stale = service._store_recognition(
        scope,
        uuid.UUID(queued["id"]),
        claim=old_claim,
        draft=old_draft,
    )
    current_report = api.get(f"/api/v1/lab-reports/{queued['id']}")
    assert current_report.status_code == 200, current_report.text
    current = next(
        row
        for row in current_report.json()["observations"]
        if row["id"] == str(hemoglobin.id)
    )
    assert current["value_raw"] == "119"
    assert current["extraction_state"] == "user_corrected"
    assert stale.report.revision == corrected_body["revision"]
    assert len(stale.observations) == 5
    with session_factory() as session:
        job = session.get(
            LabRecognitionJob,
            uuid.UUID(queued["recognition_job_id"]),
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.attempts == 2


def test_chinese_report_identity_and_date_are_bound_once_for_all_rows(
    api: TestClient, services: dict
):
    uploaded = api.post(
        f"/api/v1/studies/{services['study']}/lab-reports",
        files={
            "file": (
                ZH_CONTEXT_PDF.name,
                ZH_CONTEXT_PDF.read_bytes(),
                "application/pdf",
            )
        },
        data={
            "site_id": str(services["sites"]["site_a"]),
            "title": "Synthetic Chinese report context",
            "version_label": "v1",
        },
        headers={**_csrf(api), "Idempotency-Key": "w08-zh-context-lab"},
    )
    assert uploaded.status_code == 202, uploaded.text
    scope = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    queued = uploaded.json()
    api.app.state.laboratory_service.process_recognition_job(
        scope,
        uuid.UUID(queued["recognition_job_id"]),
        worker_id="synthetic-zh-context-worker",
    )
    report = api.get(f"/api/v1/lab-reports/{queued['id']}").json()
    assert report["state"] == "recognized"
    assert report["support_profile"]["report_context"] == {
        "subject_external_id": "SYN-ZH-001",
        "collected_on": "2026-01-02",
        "instance_type": "初检",
        "report_revision": "FINAL",
    }
    assert {
        item["subject_external_id"] for item in report["observations"]
    } == {"SYN-ZH-001"}
    assert {
        item["instance_type"] for item in report["observations"]
    } == {"initial"}
