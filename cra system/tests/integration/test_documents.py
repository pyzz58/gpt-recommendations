"""Real PostgreSQL and S3-compatible acceptance for CRA-W03."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

import pytest
from cra_app.documents.models import (
    DocumentVersion,
    SourceAnchor,
    SourceDocument,
)
from cra_app.documents.parsers.docx import DocxSourceParser
from cra_app.documents.parsers.pdf import PdfSourceParser
from cra_app.documents.service import (
    CreateDocumentCommand,
    DocumentService,
    DocumentValidationError,
)
from cra_app.documents.storage import build_private_storage
from cra_app.documents.worker import build_worker_app
from cra_app.governance.identity import SyntheticIdentityProvider
from cra_app.governance.service import (
    AuthorizationDenied,
    CreateSite,
    CreateStudy,
    GovernanceService,
    GrantMembership,
    ScopeContext,
)
from cra_app.main import create_app
from cra_app.platform.jobs import (
    BusinessJob,
    OutboxEvent,
    ProcrastinateQueue,
)
from cra_app.shared.config import Settings
from cra_app.shared.db import build_engine, build_session_factory
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

pytestmark = pytest.mark.postgres

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ARTIFACTS = FIXTURES / "documents" / "artifacts"


def _database_url() -> str:
    value = os.environ.get("CRA_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CRA_TEST_DATABASE_URL is required; W03 never falls back to SQLite"
        )
    return value


def _s3_endpoint() -> str:
    value = os.environ.get("CRA_TEST_S3_ENDPOINT", "").strip()
    if not value:
        raise RuntimeError("CRA_TEST_S3_ENDPOINT is required for W03")
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
            text("DROP FUNCTION IF EXISTS cra_w03_reject_outbox() CASCADE")
        )
        connection.execute(
            text(
                "TRUNCATE TABLE outbox_events, business_jobs, parse_coverage, "
                "source_anchors, document_versions, source_documents, "
                "idempotency_records, audit_events, memberships, sites, studies "
                "CASCADE"
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
def settings() -> Settings:
    return Settings(
        CRA_ENV="test",
        CRA_DATABASE_URL=_database_url(),
        CRA_SESSION_SECRET="synthetic-w03-session-secret",
        CRA_SESSION_COOKIE_SECURE=False,
        CRA_SYNTHETIC_ACTOR_ID="synthetic-cra-a",
        CRA_SYNTHETIC_TENANT_ID="synthetic-tenant",
        CRA_STORAGE_BACKEND="s3",
        CRA_PRIVATE_STORAGE_ENDPOINT=_s3_endpoint(),
        CRA_PRIVATE_STORAGE_ACCESS_KEY="synthetic",
        CRA_PRIVATE_STORAGE_SECRET_KEY="synthetic",
        CRA_PRIVATE_STORAGE_BUCKET="cra-w03-tests",
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
            idempotency_key="w03-study",
            code="W03-SYN",
            title="W03 Synthetic Document Study",
        ),
    )
    site_a = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w03-site-a",
            code="A01",
            name="Synthetic Documents Site A",
        ),
    )
    site_b = governance.create_site(
        admin,
        study.resource_id,
        CreateSite(
            expected_revision=0,
            idempotency_key="w03-site-b",
            code="B01",
            name="Synthetic Documents Site B",
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
                idempotency_key=f"w03-grant-{actor}",
                actor_id=actor,
                role="cra",
                site_id=site,
                can_write=True,
            ),
        )
    storage = build_private_storage(settings)
    document_service = DocumentService(
        session_factory,
        storage=storage,
        queue=queue,
        governance=governance,
    )
    return {
        "governance": governance,
        "admin": admin,
        "study": study.resource_id,
        "site_a": site_a.resource_id,
        "site_b": site_b.resource_id,
        "storage": storage,
        "documents": document_service,
    }


@pytest.fixture
def api(settings, session_factory, services):
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=SyntheticIdentityProvider(settings),
        document_service=services["documents"],
    )
    with TestClient(application) as client:
        login = client.post("/api/v1/auth/synthetic/session")
        assert login.status_code == 200
        yield client


def _upload(
    client: TestClient,
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    *,
    filename: str,
    content: bytes,
    idempotency_key: str,
    purpose: str = "rule",
    document_type: str = "protocol",
    version_label: str = "v1",
) -> dict:
    response = client.post(
        f"/api/v1/studies/{study_id}/documents",
        files={
            "file": (
                filename,
                content,
                "application/octet-stream",
            )
        },
        data={
            "title": "Synthetic source document",
            "document_type": document_type,
            "purpose": purpose,
            "version_label": version_label,
            "expected_revision": "0",
            "site_id": str(site_id),
            "published_on": "2026-10-01",
            "user_starts_on": "2026-10-02",
            "user_starts_note": "Synthetic user-managed use date",
        },
        headers={
            "Idempotency-Key": idempotency_key,
            "X-CSRF-Token": client.cookies.get("cra_csrf"),
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_synthetic_manifest_hashes_and_source_parsers():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    assert {item["group"] for item in manifest["artifacts"]} == {
        "development",
        "evaluation",
    }
    for item in manifest["artifacts"]:
        path = FIXTURES / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]

    docx_path = ARTIFACTS / "synthetic_rule_protocol.docx"
    docx = DocxSourceParser().parse(
        docx_path.read_bytes(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename=docx_path.name,
    )
    assert docx.status == "partial"
    assert any(anchor.anchor_type == "footnote" for anchor in docx.anchors)
    assert any(anchor.anchor_type == "media" for anchor in docx.anchors)
    assert any(
        anchor.style.get("grid_span", 1) > 1
        for anchor in docx.anchors
        if anchor.anchor_type == "table_cell"
    )
    paragraph = next(
        anchor for anchor in docx.anchors if "any study procedure" in anchor.text
    )
    assert any(
        run["text"] == "any study procedure" and run["bold"]
        for run in paragraph.style["runs"]
    )
    assert any(
        unit.status == "background" and "sdt[1]" in unit.unit_key
        for unit in docx.coverage
    )
    assert any(
        unit.status == "unsupported" and unit.unit_type == "embedded_media"
        for unit in docx.coverage
    )

    pdf_path = ARTIFACTS / "synthetic_monitoring_report.pdf"
    pdf = PdfSourceParser().parse(
        pdf_path.read_bytes(),
        media_type="application/pdf",
        filename=pdf_path.name,
    )
    assert pdf.status == "completed"
    assert any(
        anchor.anchor_type == "table_cell"
        and anchor.page_number == 1
        and anchor.bbox
        for anchor in pdf.anchors
    )
    assert any("SYN-001" in anchor.text for anchor in pdf.anchors)


def test_private_s3_storage_round_trip(settings):
    storage = build_private_storage(settings)
    key = f"synthetic/{uuid.uuid4()}.txt"
    storage.put(key, b"synthetic-private-content", "text/plain")
    assert storage.read(key) == b"synthetic-private-content"


def test_upload_idempotency_outbox_and_docx_source_locations(
    api, services, session_factory
):
    content = (ARTIFACTS / "synthetic_rule_protocol.docx").read_bytes()
    missing_csrf = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={"file": ("no-csrf.docx", content, "application/octet-stream")},
        data={
            "title": "Must not upload",
            "document_type": "protocol",
            "purpose": "rule",
            "version_label": "v1",
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={"Idempotency-Key": "missing-csrf"},
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "csrf_validation_failed"
    first = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="synthetic_rule_protocol.docx",
        content=content,
        idempotency_key="synthetic-docx-upload",
    )
    second = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="synthetic_rule_protocol.docx",
        content=content,
        idempotency_key="synthetic-docx-upload",
    )
    assert second["replayed"] is True
    assert first["document_version_id"] == second["document_version_id"]
    assert first["job_id"] == second["job_id"]

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DocumentVersion)) == 1
        assert session.scalar(select(func.count()).select_from(BusinessJob)) == 1
        assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 1
        outbox = session.scalar(select(OutboxEvent))
        assert outbox is not None and outbox.status == "published"
        queue_count = session.scalar(
            text(
                "SELECT count(*) FROM procrastinate_jobs "
                "WHERE args->>'job_id' = :job_id"
            ),
            {"job_id": first["job_id"]},
        )
        assert int(queue_count) == 1

    changed = api.post(
        f"/api/v1/studies/{services['study']}/documents",
        files={
            "file": (
                "changed.docx",
                content + b"synthetic-change",
                "application/octet-stream",
            )
        },
        data={
            "title": "Changed synthetic source",
            "document_type": "protocol",
            "purpose": "rule",
            "version_label": "v1-different",
            "expected_revision": "0",
            "site_id": str(services["site_a"]),
        },
        headers={
            "Idempotency-Key": "synthetic-docx-upload",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "document_idempotency_conflict"

    result = services["documents"].process_job(uuid.UUID(first["job_id"]))
    assert result.status == "partial"
    anchors = api.get(
        f"/api/v1/document-versions/{first['document_version_id']}/anchors"
    )
    assert anchors.status_code == 200
    anchor_body = anchors.json()
    assert any(anchor["anchor_type"] == "footnote" for anchor in anchor_body)
    assert any(anchor["anchor_type"] == "table_cell" for anchor in anchor_body)
    bold = next(
        anchor for anchor in anchor_body if "any study procedure" in anchor["text"]
    )
    assert any(run["bold"] for run in bold["style"]["runs"])
    coverage = api.get(
        f"/api/v1/document-versions/{first['document_version_id']}/coverage"
    )
    assert coverage.status_code == 200
    assert any(unit["status"] == "background" for unit in coverage.json())
    source = api.get(
        f"/api/v1/document-versions/{first['document_version_id']}/content"
    )
    assert source.status_code == 200
    assert source.content == content
    assert source.headers["cache-control"] == "private, no-store"


def test_version_immutability_duplicate_hash_and_append_revision(
    api, services, session_factory
):
    content = (ARTIFACTS / "synthetic_rule_text.txt").read_bytes()
    first = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="synthetic_rule_text.txt",
        content=content,
        idempotency_key="text-version-v1",
        purpose="rule",
        document_type="text",
        version_label="v1",
    )
    versions = api.get(
        f"/api/v1/documents/{first['document_id']}/versions"
    )
    assert versions.status_code == 200
    assert versions.json()[0]["user_starts_on"] == "2026-10-02"
    assert versions.json()[0]["published_on"] == "2026-10-01"

    added = api.post(
        f"/api/v1/documents/{first['document_id']}/versions",
        files={
            "file": (
                "synthetic_rule_text.txt",
                content,
                "application/octet-stream",
            )
        },
        data={
            "version_label": "v2-copy",
            "expected_revision": "1",
            "user_starts_on": "2026-11-01",
        },
        headers={
            "Idempotency-Key": "text-version-v2",
            "X-CSRF-Token": api.cookies.get("cra_csrf"),
        },
    )
    assert added.status_code == 202, added.text
    with session_factory() as session:
        version = session.get(
            DocumentVersion, uuid.UUID(added.json()["document_version_id"])
        )
        assert version is not None
        assert str(version.duplicate_of_version_id) == first["document_version_id"]
        document = session.get(SourceDocument, uuid.UUID(first["document_id"]))
        assert document is not None and document.revision == 2

    with pytest.raises(SQLAlchemyError):
        with session_factory() as session:
            with session.begin():
                session.execute(
                    text(
                        "UPDATE document_versions SET sha256 = :sha "
                        "WHERE id = :id"
                    ),
                    {
                        "sha": "0" * 64,
                        "id": first["document_version_id"],
                    },
                )


def test_pdf_coordinates_unsupported_excel_and_authorized_content(
    api, services
):
    pdf = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="synthetic_monitoring_report.pdf",
        content=(ARTIFACTS / "synthetic_monitoring_report.pdf").read_bytes(),
        idempotency_key="pdf-eval",
        purpose="carryover_report",
        document_type="report",
    )
    parsed = services["documents"].process_job(uuid.UUID(pdf["job_id"]))
    assert parsed.status == "completed"
    anchors = api.get(
        f"/api/v1/document-versions/{pdf['document_version_id']}/anchors"
    ).json()
    assert any(
        item["anchor_type"] == "table_cell"
        and item["page_number"] == 1
        and item["bbox"]
        for item in anchors
    )

    excel = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="synthetic_track.xlsx",
        content=(ARTIFACTS / "synthetic_track.xlsx").read_bytes(),
        idempotency_key="excel-private-only",
        purpose="track",
        document_type="track",
    )
    result = services["documents"].process_job(uuid.UUID(excel["job_id"]))
    assert result.status == "partial"
    coverage = api.get(
        f"/api/v1/document-versions/{excel['document_version_id']}/coverage"
    ).json()
    assert coverage[0]["status"] == "unsupported"
    assert "private source file" in coverage[0]["reason"]
    content = api.get(
        f"/api/v1/document-versions/{excel['document_version_id']}/content"
    )
    assert content.status_code == 200
    assert content.content == (ARTIFACTS / "synthetic_track.xlsx").read_bytes()


def test_cross_site_reads_and_worker_permission_recheck(
    api, services, settings, session_factory, queue
):
    uploaded = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="synthetic_rule_text.txt",
        content=(ARTIFACTS / "synthetic_rule_text.txt").read_bytes(),
        idempotency_key="permission-source",
    )

    provider = SyntheticIdentityProvider(settings)
    application = create_app(
        settings=settings,
        session_factory=session_factory,
        identity_provider=provider,
        document_service=services["documents"],
    )
    with TestClient(application) as other:
        identity = provider.create_identity(actor_id="synthetic-cra-b")
        other.cookies.set("cra_session", provider.issue_session(identity))
        denied = other.get(
            f"/api/v1/document-versions/{uploaded['document_version_id']}/content"
        )
        assert denied.status_code == 403

    with session_factory() as session:
        with session.begin():
            session.execute(
                text(
                    "DELETE FROM memberships WHERE actor_id = :actor "
                    "AND study_id = :study"
                ),
                {
                    "actor": "synthetic-cra-a",
                    "study": services["study"],
                },
            )
    with pytest.raises(AuthorizationDenied):
        services["documents"].process_job(uuid.UUID(uploaded["job_id"]))
    with session_factory() as session:
        job = session.get(BusinessJob, uuid.UUID(uploaded["job_id"]))
        assert job is not None
        assert job.status == "failed"
        assert job.error_code == "authorization_revoked"
        assert session.scalar(
            select(func.count())
            .select_from(SourceAnchor)
            .where(
                SourceAnchor.document_version_id
                == uuid.UUID(uploaded["document_version_id"])
            )
        ) == 0


def test_outbox_transaction_rollback_and_same_version_retry(
    api, services, engine, session_factory
):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE FUNCTION cra_w03_reject_outbox() RETURNS trigger AS $$
                BEGIN
                  RAISE EXCEPTION 'synthetic outbox failure';
                END;
                $$ LANGUAGE plpgsql
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TRIGGER cra_w03_reject_outbox
                BEFORE INSERT ON outbox_events
                FOR EACH ROW EXECUTE FUNCTION cra_w03_reject_outbox()
                """
            )
        )
    scope_a = ScopeContext(
        actor_id="synthetic-cra-a",
        tenant_id="synthetic-tenant",
        authentication_source="trusted-test",
    )
    with pytest.raises(SQLAlchemyError):
        services["documents"].create_document(
            scope_a,
            services["study"],
            CreateDocumentCommand(
                expected_revision=0,
                idempotency_key="outbox-rollback",
                site_id=services["site_a"],
                title="Synthetic rollback source",
                document_type="text",
                purpose="rule",
                version_label="v1",
            ),
            filename="rollback.txt",
            content=b"Synthetic rollback",
        )
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(SourceDocument)) == 0
        assert session.scalar(select(func.count()).select_from(DocumentVersion)) == 0
        assert session.scalar(select(func.count()).select_from(BusinessJob)) == 0
        assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 0
    with engine.begin() as connection:
        connection.execute(
            text("DROP TRIGGER cra_w03_reject_outbox ON outbox_events")
        )
        connection.execute(text("DROP FUNCTION cra_w03_reject_outbox()"))

    broken_pdf = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="broken.pdf",
        content=b"%PDF-1.7\nsynthetic-invalid-body",
        idempotency_key="broken-pdf",
        purpose="carryover_report",
        document_type="report",
    )
    with pytest.raises(DocumentValidationError):
        services["documents"].process_job(uuid.UUID(broken_pdf["job_id"]))
    with session_factory() as session:
        job = session.get(BusinessJob, uuid.UUID(broken_pdf["job_id"]))
        assert job is not None and job.status == "failed" and job.attempts == 1
        original_version = job.input_version_id
    services["documents"].retry_job(
        ScopeContext(
            actor_id="synthetic-cra-a",
            tenant_id="synthetic-tenant",
            authentication_source="trusted-test",
        ),
        uuid.UUID(broken_pdf["job_id"]),
    )
    with pytest.raises(DocumentValidationError):
        services["documents"].process_job(uuid.UUID(broken_pdf["job_id"]))
    with session_factory() as session:
        versions = session.scalars(
            select(DocumentVersion).where(
                DocumentVersion.document_id == uuid.UUID(broken_pdf["document_id"])
            )
        ).all()
        assert [version.id for version in versions] == [original_version]
        job = session.get(BusinessJob, uuid.UUID(broken_pdf["job_id"]))
        assert job is not None and job.attempts == 2 and job.status == "failed"


def test_real_procrastinate_worker_processes_queued_job(
    api, services, session_factory, queue
):
    uploaded = _upload(
        api,
        services["study"],
        services["site_a"],
        filename="worker.txt",
        content=b"Synthetic worker line\nCondition C -> path B\n",
        idempotency_key="worker-job",
    )
    worker = build_worker_app(services["documents"], _database_url())
    worker.run_worker(queues=["documents"], concurrency=1, wait=False)
    with session_factory() as session:
        job = session.get(BusinessJob, uuid.UUID(uploaded["job_id"]))
        assert job is not None
        assert job.status == "succeeded"
        assert job.attempts == 1
        assert session.scalar(
            select(func.count())
            .select_from(SourceAnchor)
            .where(
                SourceAnchor.document_version_id
                == uuid.UUID(uploaded["document_version_id"])
            )
        ) > 0
