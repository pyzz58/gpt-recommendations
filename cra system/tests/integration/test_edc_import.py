"""Real-PostgreSQL acceptance for CRA-W07 EDC Excel snapshot import."""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from cra_app.documents.models import DocumentVersion, SourceDocument
from cra_app.documents.service import DocumentService
from cra_app.documents.storage import build_private_storage
from cra_app.edc_import.excel import parse_workbook
from cra_app.edc_import.models import (
    EDCLabRecord,
    EDCImportPreview,
    EDCSnapshot,
    EDCSnapshotRow,
)
from cra_app.edc_import.service import EDCImportService
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
from cra_app.rules.service import RuleService
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from cra_app.subjects.contracts import CreateSubjectCommand
from cra_app.subjects.service import SubjectService

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ARTIFACT = FIXTURES / "edc" / "artifacts" / "synthetic_edc_lab.xlsx"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W07 never falls back to SQLite"
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
                "TRUNCATE TABLE edc_lab_records, edc_snapshot_rows, "
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
        CRA_SESSION_SECRET="synthetic-w07-session-secret",
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
            idempotency_key="w07-study",
            code="W07-SYN",
            title="W07 Synthetic EDC Import",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w07-site-a",
            code="S01",
            name="Synthetic EDC Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w07-site-b",
            code="S02",
            name="Synthetic EDC Site B",
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
                idempotency_key=f"w07-grant-{actor}",
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
    subject_a = subjects.create_subject(
        ScopeContext(
            actor_id="synthetic-cra-a",
            tenant_id="synthetic-tenant",
            authentication_source="trusted-test",
        ),
        study.resource_id,
        CreateSubjectCommand(
            expected_revision=0,
            idempotency_key="w07-subject-a",
            site_id=site_a.resource_id,
            external_id="SYN-EDC-001",
            identity_namespace="edc",
            deidentified_label="SYN-EDC-001",
        ),
    )
    edc = EDCImportService(
        session_factory,
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
        "subject_a": subject_a,
        "edc": edc,
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
        edc_import_service=services["edc"],
    )
    with TestClient(application) as client:
        assert client.post("/api/v1/auth/synthetic/session").status_code == 200
        yield client


def _headers(api: TestClient, key: str) -> dict[str, str]:
    return {
        "X-CSRF-Token": api.cookies.get("cra_csrf"),
        "Idempotency-Key": key,
    }


def _mapping() -> dict:
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
            "Hematology": {
                "header_row": 1,
                "data_start_row": 2,
                "columns": columns,
                "included": True,
            },
            "Chemistry": {
                "header_row": 1,
                "data_start_row": 2,
                "columns": columns,
                "included": True,
            },
        }
    }


def _preview(
    api: TestClient,
    services: dict,
    *,
    key: str,
    mapping_profile_id: str | None = None,
    filename: str | None = None,
    content: bytes | None = None,
):
    data = {
        "site_id": str(services["site_a"]),
        "title": "Synthetic EDC laboratory export",
        "export_started_at": "2026-01-03T08:00:00+00:00",
        "export_completed_at": "2026-01-03T08:05:00+00:00",
        "export_scope_json": json.dumps(
            {
                "status": "declared",
                "forms": ["Hematology", "Chemistry"],
                "subjects": ["SYN-EDC-001", "SYN-EDC-002"],
                "sites": ["S01"],
                "date_start": "2026-01-01",
                "date_end": "2026-01-03",
                "filters": {"export_type": "filtered_by_subject_list"},
                "declared_complete": False,
                "note": "Synthetic filtered EDC export.",
            }
        ),
        "included_sheets_json": json.dumps(["Hematology", "Chemistry"]),
        "identity_namespace": "edc",
    }
    if mapping_profile_id:
        data["mapping_profile_id"] = mapping_profile_id
    return api.post(
        f"/api/v1/studies/{services['study']}/edc-imports/preview",
        files={
            "file": (
                filename or ARTIFACT.name,
                content if content is not None else ARTIFACT.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data=data,
        headers=_headers(api, key),
    )


def test_parser_preserves_multiple_sheets_and_formula_cache():
    parsed = parse_workbook(
        ARTIFACT.read_bytes(),
        filename=ARTIFACT.name,
        included_sheets=["Hematology", "Chemistry"],
    )
    assert [sheet.name for sheet in parsed.sheets] == [
        "Hematology",
        "Chemistry",
        "Internal Notes",
    ]
    assert parsed.sheets[2].state == "hidden"
    hem = parsed.sheets[0]
    formula = next(cell for cell in hem.cells if cell.coordinate == "D3")
    assert formula.formula == "=IF(1=1,119,0)"
    assert formula.cached_text == "119"
    chem = parsed.sheets[1]
    no_cache = next(cell for cell in chem.cells if cell.coordinate == "D2")
    assert no_cache.formula == "=16*2"
    assert no_cache.cached_text is None


def test_preview_confirm_scope_instances_and_source_positions(
    api: TestClient, services: dict, session_factory
):
    preview = _preview(api, services, key="w07-preview")
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["export_scope"]["status"] == "declared"
    assert body["export_scope"]["declared_complete"] is False
    assert [sheet["name"] for sheet in body["sheets"]] == [
        "Hematology",
        "Chemistry",
        "Internal Notes",
    ]
    hem_preview = body["sheets"][0]
    formula = next(
        cell
        for cell in hem_preview["formula_cells"]
        if cell["coordinate"] == "D3"
    )
    assert formula["raw_text"] == "=IF(1=1,119,0)"
    assert formula["cached_text"] == "119"
    repeat_row = next(
        row
        for row in hem_preview["rows"]
        if row["display_values"]["Instance"] == "Repeat"
    )
    assert repeat_row["display_values"]["Result"] == "119"
    assert repeat_row["formulas"]["Result"] == "=IF(1=1,119,0)"
    assert "Internal Notes" not in body["included_sheets"]

    confirmed = api.post(
        f"/api/v1/edc-imports/{body['id']}/confirm",
        json={
            "expected_revision": body["revision"],
            "idempotency_key": "w07-confirm",
            "mapping": _mapping(),
            "identity_namespace": "edc",
            "save_mapping_name": "Synthetic EDC Lab Mapping",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert confirmed.status_code == 200, confirmed.text
    snapshot = confirmed.json()
    assert snapshot["row_count"] == 5
    assert snapshot["record_count"] == 5
    assert snapshot["scope_status"] == "declared"
    assert snapshot["absence_semantics"] == "not_seen_in_export"
    assert datetime.fromisoformat(
        snapshot["export_started_at"]
    ).astimezone(UTC) == datetime(2026, 1, 3, 8, 0, tzinfo=UTC)
    assert datetime.fromisoformat(
        snapshot["export_completed_at"]
    ).astimezone(UTC) == datetime(2026, 1, 3, 8, 5, tzinfo=UTC)

    hemoglobin = [
        record
        for record in snapshot["records"]
        if record["subject_external_id"] == "SYN-EDC-001"
        and record["analyte"] == "Hemoglobin"
    ]
    assert {record["instance_type"] for record in hemoglobin} == {
        "initial",
        "repeat",
    }
    assert len({record["instance_key"] for record in hemoglobin}) == 2
    repeat = next(
        record for record in hemoglobin if record["instance_type"] == "repeat"
    )
    assert repeat["value_raw"] == "119"
    assert repeat["subject_id"] == str(services["subject_a"].id)
    assert repeat["identity_status"] == "mapped"
    assert repeat["validation_status"] == "ready_for_match"
    assert repeat["source_ref"]["sheet"] == "Hematology"
    assert repeat["source_ref"]["row"] == 3
    assert "Result" in repeat["source_ref"]["formula_headers"]

    alt = next(
        record for record in snapshot["records"] if record["analyte"] == "ALT"
    )
    assert alt["value_raw"] is None
    assert "formula_cache_missing" in alt["issues"]
    assert alt["validation_status"] == "needs_review"
    analytes = [record["analyte"] for record in snapshot["records"]]
    assert "Glucose" in analytes, snapshot["records"]
    glucose = next(record for record in snapshot["records"] if record["analyte"] == "Glucose")
    assert glucose["unit_raw"] is None
    assert glucose["identity_status"] == "mapped"

    lookup = api.post(
        f"/api/v1/edc-snapshots/{snapshot['id']}/lookup",
        json={
            "subject_external_id": "SYN-EDC-001",
            "analyte": "Not in this export",
            "collected_on": "2026-01-02",
            "instance_type": "Initial",
        },
    )
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()["status"] == "not_seen_in_export"
    assert lookup.json()["edc_omission_inferred"] is False

    with session_factory() as session:
        snapshot_db = session.get(EDCSnapshot, uuid.UUID(snapshot["id"]))
        assert snapshot_db is not None
        source_document = session.get(
            SourceDocument,
            session.scalar(
                select(SourceDocument.id)
                .join(
                    DocumentVersion,
                    (
                        DocumentVersion.tenant_id
                        == SourceDocument.tenant_id
                    )
                    & (
                        DocumentVersion.study_id
                        == SourceDocument.study_id
                    )
                    & (
                        DocumentVersion.document_id
                        == SourceDocument.id
                    ),
                )
                .where(
                    DocumentVersion.id
                    == snapshot_db.source_document_version_id
                )
            ),
        )
        assert source_document is not None
        assert source_document.purpose == "edc_export"
        assert source_document.document_type == "edc_export"
        row_id = session.scalar(
            select(EDCSnapshotRow.id).where(
                EDCSnapshotRow.snapshot_id == snapshot_db.id
            )
        )
        record_id = session.scalar(
            select(EDCLabRecord.id).where(
                EDCLabRecord.snapshot_id == snapshot_db.id
            )
        )
    for table, row_id in (
        ("edc_snapshots", snapshot["id"]),
        ("edc_snapshot_rows", str(row_id)),
        ("edc_lab_records", str(record_id)),
    ):
        with pytest.raises(SQLAlchemyError):
            with session_factory() as session:
                with session.begin():
                    session.execute(
                        text(
                            f"UPDATE {table} SET created_at = now() "
                            "WHERE id = :id"
                        ),
                        {"id": row_id},
                    )


def test_mapping_reuse_and_duplicate_confirm_do_not_copy_snapshot(
    api: TestClient, services: dict, session_factory
):
    first = _preview(api, services, key="w07-reuse-first")
    assert first.status_code == 200, first.text
    first_body = first.json()
    snapshot = api.post(
        f"/api/v1/edc-imports/{first_body['id']}/confirm",
        json={
            "expected_revision": first_body["revision"],
            "idempotency_key": "w07-reuse-confirm",
            "mapping": _mapping(),
            "identity_namespace": "edc",
            "save_mapping_name": "W07 Reusable Mapping",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert snapshot.status_code == 200, snapshot.text
    profile_id = snapshot.json()["mapping_profile_id"]
    assert profile_id

    second = _preview(
        api,
        services,
        key="w07-reuse-second",
        mapping_profile_id=profile_id,
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["mapping_profile_id"] == profile_id
    assert second_body["suggested_mapping"] == _mapping()
    repeated = api.post(
        f"/api/v1/edc-imports/{second_body['id']}/confirm",
        json={
            "expected_revision": second_body["revision"],
            "idempotency_key": "w07-reuse-second-confirm",
            "mapping": _mapping(),
            "identity_namespace": "edc",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["replayed"] is True
    assert repeated.json()["id"] == snapshot.json()["id"]
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(EDCSnapshot)) == 1
        assert session.scalar(select(func.count()).select_from(EDCSnapshotRow)) == 5
        assert session.scalar(select(func.count()).select_from(EDCLabRecord)) == 5
        assert (
            session.scalar(select(func.count()).select_from(EDCImportPreview))
            == 2
        )


def test_cross_site_preview_access_is_denied(
    api: TestClient, services: dict
):
    preview = _preview(api, services, key="w07-cross-site-preview")
    assert preview.status_code == 200, preview.text
    preview_id = preview.json()["id"]
    provider = SyntheticIdentityProvider(api.app.state.settings)
    identity = provider.create_identity(actor_id="synthetic-cra-b")
    api.cookies.clear()
    api.cookies.set("cra_session", provider.issue_session(identity), path="/")
    denied = api.get(f"/api/v1/edc-imports/{preview_id}")
    assert denied.status_code == 403


def test_corrected_export_creates_a_new_immutable_snapshot(
    api: TestClient, services: dict, session_factory
):
    first = _preview(api, services, key="w07-correction-first")
    assert first.status_code == 200, first.text
    first_body = first.json()
    first_snapshot = api.post(
        f"/api/v1/edc-imports/{first_body['id']}/confirm",
        json={
            "expected_revision": first_body["revision"],
            "idempotency_key": "w07-correction-first-confirm",
            "mapping": _mapping(),
            "identity_namespace": "edc",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert first_snapshot.status_code == 200, first_snapshot.text

    workbook = load_workbook(BytesIO(ARTIFACT.read_bytes()))
    workbook["Hematology"]["D2"] = 122
    corrected_content = BytesIO()
    workbook.save(corrected_content)
    workbook.close()
    second = _preview(
        api,
        services,
        key="w07-correction-second",
        filename="synthetic_edc_lab_corrected.xlsx",
        content=corrected_content.getvalue(),
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    second_snapshot = api.post(
        f"/api/v1/edc-imports/{second_body['id']}/confirm",
        json={
            "expected_revision": second_body["revision"],
            "idempotency_key": "w07-correction-second-confirm",
            "mapping": _mapping(),
            "identity_namespace": "edc",
        },
        headers={"X-CSRF-Token": api.cookies.get("cra_csrf")},
    )
    assert second_snapshot.status_code == 200, second_snapshot.text
    assert second_snapshot.json()["id"] != first_snapshot.json()["id"]
    assert second_snapshot.json()["source_sha256"] != first_snapshot.json()[
        "source_sha256"
    ]
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(EDCSnapshot)) == 2
