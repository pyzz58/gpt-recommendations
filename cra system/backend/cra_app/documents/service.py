"""Authorized immutable document upload and asynchronous parse orchestration."""
from __future__ import annotations

import hashlib
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import BytesIO

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import (
    DOCUMENT_PURPOSES,
    DOCUMENT_TYPES,
    DocumentVersion,
    ParseCoverage,
    SourceAnchor,
    SourceDocument,
)
from cra_app.documents.parsers import (
    DocxSourceParser,
    PdfSourceParser,
    TextSourceParser,
)
from cra_app.documents.storage import PrivateObjectStorage
from cra_app.governance.service import (
    AuthorizationDenied,
    GovernanceService,
    ScopeContext,
)
from cra_app.platform.jobs import (
    BusinessJob,
    OutboxEvent,
    ProcrastinateQueue,
    digest_payload,
    relay_pending_outbox,
)
from cra_app.providers.ports import (
    CoverageUnit,
    ParsedAnchor,
    ParseDocumentPort,
    ParseResult,
)


class DocumentError(Exception):
    pass


class DocumentValidationError(DocumentError):
    pass


class DocumentIdempotencyConflict(DocumentError):
    pass


class DocumentNotFound(DocumentError):
    pass


class DocumentJobConflict(DocumentError):
    pass


class _UploadCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    document_type: str
    purpose: str
    version_label: str = Field(min_length=1, max_length=64)
    published_on: date | None = None
    user_starts_on: date | None = None
    user_starts_note: str | None = Field(default=None, max_length=500)

    def validate_domain(self) -> None:
        if self.document_type not in DOCUMENT_TYPES:
            raise ValueError("unsupported document type")
        if self.purpose not in DOCUMENT_PURPOSES:
            raise ValueError("unsupported document purpose")


class CreateDocumentCommand(_UploadCommand):
    site_id: uuid.UUID | None = None

    def validate_domain(self) -> None:
        super().validate_domain()
        if self.expected_revision != 0:
            raise ValueError("create requires expected_revision=0")


class AddVersionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    version_label: str = Field(min_length=1, max_length=64)
    published_on: date | None = None
    user_starts_on: date | None = None
    user_starts_note: str | None = Field(default=None, max_length=500)

    def validate_domain(self) -> None:
        if self.expected_revision < 1:
            raise ValueError("new version requires expected_revision >= 1")


@dataclass(frozen=True)
class UploadResult:
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    job_id: uuid.UUID
    revision: int
    replayed: bool
    sha256: str


@dataclass(frozen=True)
class StoredContent:
    content: bytes
    media_type: str
    filename: str
    version: DocumentVersion


SUPPORTED_TYPES = {
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _extension(filename: str) -> str:
    lower = filename.lower()
    for extension in SUPPORTED_TYPES:
        if lower.endswith(extension):
            return extension
    return ""


def validate_upload(
    filename: str, content: bytes, max_bytes: int
) -> str:
    if not content:
        raise DocumentValidationError("empty file")
    if len(content) > max_bytes:
        raise DocumentValidationError("file exceeds upload size limit")
    extension = _extension(filename)
    if not extension:
        raise DocumentValidationError("unsupported file extension")
    media_type = SUPPORTED_TYPES[extension]
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise DocumentValidationError("file signature does not match PDF")
    if extension in {".docx", ".xlsx"}:
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
                marker = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
                if marker not in names or "[Content_Types].xml" not in names:
                    raise DocumentValidationError(
                        f"file signature does not match {extension[1:].upper()}"
                    )
                if any(
                    name.lower().endswith("vbaproject.bin") for name in names
                ):
                    raise DocumentValidationError("macro-enabled files are not accepted")
        except zipfile.BadZipFile as exc:
            raise DocumentValidationError("invalid OOXML archive") from exc
    if extension in {".png", ".jpg", ".jpeg"}:
        signature = content[:12]
        if extension == ".png" and not signature.startswith(b"\x89PNG\r\n\x1a\n"):
            raise DocumentValidationError("file signature does not match PNG")
        if extension in {".jpg", ".jpeg"} and not signature.startswith(b"\xff\xd8"):
            raise DocumentValidationError("file signature does not match JPEG")
    return media_type


class DocumentService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        storage: PrivateObjectStorage,
        queue: ProcrastinateQueue,
        governance: GovernanceService | None = None,
        max_upload_bytes: int = 20 * 1024 * 1024,
        parsers: list[ParseDocumentPort] | None = None,
    ):
        self.session_factory = session_factory
        self.storage = storage
        self.queue = queue
        self.governance = governance or GovernanceService(session_factory)
        self.max_upload_bytes = max_upload_bytes
        self.parsers = parsers or [
            DocxSourceParser(),
            PdfSourceParser(),
            TextSourceParser(),
        ]

    @staticmethod
    def _scope_fingerprint(
        scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID | None
    ) -> str:
        return digest_payload(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id),
                "site_id": str(site_id) if site_id else None,
            }
        )

    def _authorize_upload(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
    ) -> None:
        if site_id is None:
            self.governance.authorize(scope, "manage_study", study_id)
        else:
            self.governance.authorize(scope, "write_site", study_id, site_id)

    def _authorize_read(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
    ) -> None:
        if site_id is None:
            self.governance.authorize(scope, "read_study", study_id)
        else:
            self.governance.authorize(scope, "read_site", study_id, site_id)

    @staticmethod
    def _storage_key(
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
        version_id: uuid.UUID,
        filename: str,
    ) -> str:
        extension = _extension(filename) or ".bin"
        site = str(site_id) if site_id else "study"
        return (
            f"{scope.tenant_id}/{study_id}/{site}/{version_id}{extension}"
        )

    def _find_idempotent_job(
        self,
        session: Session,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
        idempotency_key: str,
        request_digest: str,
    ) -> BusinessJob | None:
        scope_fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        job = session.scalar(
            select(BusinessJob).where(
                BusinessJob.actor_id == scope.actor_id,
                BusinessJob.tenant_id == scope.tenant_id,
                BusinessJob.scope_fingerprint == scope_fingerprint,
                BusinessJob.job_type == "parse_document",
                BusinessJob.idempotency_key == idempotency_key,
            )
        )
        if job is None:
            return None
        if job.request_digest != request_digest:
            raise DocumentIdempotencyConflict(
                "idempotency key was already used with different document input"
            )
        return job

    @staticmethod
    def _upload_result(
        job: BusinessJob,
        document_id: uuid.UUID,
        sha256: str,
        *,
        replayed: bool,
    ) -> UploadResult:
        return UploadResult(
            document_id=document_id,
            document_version_id=job.input_version_id,
            job_id=job.id,
            revision=1,
            replayed=replayed,
            sha256=sha256,
        )

    def create_document(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateDocumentCommand,
        *,
        filename: str,
        content: bytes,
    ) -> UploadResult:
        try:
            command.validate_domain()
        except ValueError as exc:
            raise DocumentValidationError(str(exc)) from exc
        media_type = validate_upload(filename, content, self.max_upload_bytes)
        self._authorize_upload(scope, study_id, command.site_id)
        sha256 = hashlib.sha256(content).hexdigest()
        request_digest = digest_payload(
            {
                "command": command.model_dump(mode="json"),
                "filename": filename,
                "media_type": media_type,
                "sha256": sha256,
            }
        )
        scope_fingerprint = self._scope_fingerprint(
            scope, study_id, command.site_id
        )
        with self.session_factory() as session:
            existing = self._find_idempotent_job(
                session,
                scope,
                study_id,
                command.site_id,
                command.idempotency_key,
                request_digest,
            )
            if existing:
                version = session.get(DocumentVersion, existing.input_version_id)
                assert version is not None
                return self._upload_result(
                    existing,
                    version.document_id,
                    version.sha256,
                    replayed=True,
                )

        document_id = uuid.uuid4()
        version_id = uuid.uuid4()
        job_id = uuid.uuid4()
        storage_key = self._storage_key(
            scope,
            study_id,
            command.site_id,
            version_id,
            filename,
        )
        self.storage.put(storage_key, content, media_type)
        try:
            with self.session_factory() as session:
                with session.begin():
                    document = SourceDocument(
                        id=document_id,
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        title=command.title,
                        document_type=command.document_type,
                        purpose=command.purpose,
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(document)
                    session.flush()
                    duplicate_id = session.scalar(
                        select(DocumentVersion.id)
                        .where(
                            DocumentVersion.tenant_id == scope.tenant_id,
                            DocumentVersion.study_id == study_id,
                            DocumentVersion.site_id.is_not_distinct_from(
                                command.site_id
                            ),
                            DocumentVersion.sha256 == sha256,
                        )
                        .limit(1)
                    )
                    version = DocumentVersion(
                        id=version_id,
                        document_id=document_id,
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        version_label=command.version_label,
                        storage_key=storage_key,
                        original_filename=filename,
                        media_type=media_type,
                        sha256=sha256,
                        size_bytes=len(content),
                        published_on=command.published_on,
                        user_starts_on=command.user_starts_on,
                        user_starts_note=command.user_starts_note,
                        uploaded_by=scope.actor_id,
                        duplicate_of_version_id=duplicate_id,
                    )
                    session.add(version)
                    session.flush()
                    job = BusinessJob(
                        id=job_id,
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        actor_id=scope.actor_id,
                        authentication_source=scope.authentication_source,
                        platform_roles=sorted(scope.platform_roles),
                        scope_fingerprint=scope_fingerprint,
                        job_type="parse_document",
                        idempotency_key=command.idempotency_key,
                        request_digest=request_digest,
                        input_version_id=version_id,
                    )
                    session.add(job)
                    session.add(
                        OutboxEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=command.site_id,
                            event_type="document.parse.requested",
                            aggregate_type="document_version",
                            aggregate_id=version_id,
                            dedup_key=f"parse:{version_id}",
                            payload={"job_id": str(job_id)},
                        )
                    )
            result = UploadResult(
                document_id=document_id,
                document_version_id=version_id,
                job_id=job_id,
                revision=1,
                replayed=False,
                sha256=sha256,
            )
        except IntegrityError:
            with self.session_factory() as session:
                existing = self._find_idempotent_job(
                    session,
                    scope,
                    study_id,
                    command.site_id,
                    command.idempotency_key,
                    request_digest,
                )
                if existing is None:
                    raise
                version = session.get(DocumentVersion, existing.input_version_id)
                assert version is not None
                return self._upload_result(
                    existing,
                    version.document_id,
                    version.sha256,
                    replayed=True,
                )
        self.relay_outbox_safely()
        return result

    def add_version(
        self,
        scope: ScopeContext,
        document_id: uuid.UUID,
        command: AddVersionCommand,
        *,
        filename: str,
        content: bytes,
    ) -> UploadResult:
        try:
            command.validate_domain()
        except ValueError as exc:
            raise DocumentValidationError(str(exc)) from exc
        media_type = validate_upload(filename, content, self.max_upload_bytes)
        with self.session_factory() as session:
            document = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.id == document_id,
                    SourceDocument.tenant_id == scope.tenant_id,
                )
            )
            if document is None:
                raise DocumentNotFound("document was not found")
            study_id, site_id = document.study_id, document.site_id
        self._authorize_upload(scope, study_id, site_id)
        sha256 = hashlib.sha256(content).hexdigest()
        request_digest = digest_payload(
            {
                "document_id": str(document_id),
                "command": command.model_dump(mode="json"),
                "filename": filename,
                "media_type": media_type,
                "sha256": sha256,
            }
        )
        with self.session_factory() as session:
            existing = self._find_idempotent_job(
                session,
                scope,
                study_id,
                site_id,
                command.idempotency_key,
                request_digest,
            )
            if existing:
                version = session.get(DocumentVersion, existing.input_version_id)
                assert version is not None
                return self._upload_result(
                    existing,
                    version.document_id,
                    version.sha256,
                    replayed=True,
                )

        version_id = uuid.uuid4()
        job_id = uuid.uuid4()
        storage_key = self._storage_key(
            scope, study_id, site_id, version_id, filename
        )
        self.storage.put(storage_key, content, media_type)
        try:
            with self.session_factory() as session:
                with session.begin():
                    document = session.scalar(
                        select(SourceDocument)
                        .where(
                            SourceDocument.id == document_id,
                            SourceDocument.tenant_id == scope.tenant_id,
                            SourceDocument.study_id == study_id,
                        )
                        .with_for_update()
                    )
                    if document is None:
                        raise DocumentNotFound("document was not found")
                    if document.revision != command.expected_revision:
                        raise DocumentJobConflict(
                            f"document revision is {document.revision}"
                        )
                    duplicate_id = session.scalar(
                        select(DocumentVersion.id)
                        .where(
                            DocumentVersion.tenant_id == scope.tenant_id,
                            DocumentVersion.study_id == study_id,
                            DocumentVersion.site_id.is_not_distinct_from(site_id),
                            DocumentVersion.sha256 == sha256,
                        )
                        .limit(1)
                    )
                    version = DocumentVersion(
                        id=version_id,
                        document_id=document_id,
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=site_id,
                        version_label=command.version_label,
                        storage_key=storage_key,
                        original_filename=filename,
                        media_type=media_type,
                        sha256=sha256,
                        size_bytes=len(content),
                        published_on=command.published_on,
                        user_starts_on=command.user_starts_on,
                        user_starts_note=command.user_starts_note,
                        uploaded_by=scope.actor_id,
                        duplicate_of_version_id=duplicate_id,
                    )
                    session.add(version)
                    session.flush()
                    document.revision += 1
                    document.updated_by = scope.actor_id
                    job = BusinessJob(
                        id=job_id,
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=site_id,
                        actor_id=scope.actor_id,
                        authentication_source=scope.authentication_source,
                        platform_roles=sorted(scope.platform_roles),
                        scope_fingerprint=self._scope_fingerprint(
                            scope, study_id, site_id
                        ),
                        job_type="parse_document",
                        idempotency_key=command.idempotency_key,
                        request_digest=request_digest,
                        input_version_id=version_id,
                    )
                    session.add(job)
                    session.add(
                        OutboxEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=site_id,
                            event_type="document.parse.requested",
                            aggregate_type="document_version",
                            aggregate_id=version_id,
                            dedup_key=f"parse:{version_id}",
                            payload={"job_id": str(job_id)},
                        )
                    )
            result = UploadResult(
                document_id=document_id,
                document_version_id=version_id,
                job_id=job_id,
                revision=command.expected_revision + 1,
                replayed=False,
                sha256=sha256,
            )
        except IntegrityError:
            with self.session_factory() as session:
                existing = self._find_idempotent_job(
                    session,
                    scope,
                    study_id,
                    site_id,
                    command.idempotency_key,
                    request_digest,
                )
                if existing is None:
                    raise
                version = session.get(DocumentVersion, existing.input_version_id)
                assert version is not None
                return self._upload_result(
                    existing,
                    version.document_id,
                    version.sha256,
                    replayed=True,
                )
        self.relay_outbox_safely()
        return result

    def relay_outbox_safely(self) -> int:
        try:
            return relay_pending_outbox(self.session_factory, self.queue)
        except Exception:
            return 0

    def list_documents(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
    ) -> list[SourceDocument]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            if site_id is None:
                condition = SourceDocument.site_id.is_(None)
            else:
                self.governance.authorize(scope, "read_site", study_id, site_id)
                condition = SourceDocument.site_id == site_id
            return list(
                session.scalars(
                    select(SourceDocument)
                    .where(
                        SourceDocument.tenant_id == scope.tenant_id,
                        SourceDocument.study_id == study_id,
                        condition,
                    )
                    .order_by(SourceDocument.created_at.desc())
                )
            )

    def list_versions(
        self, scope: ScopeContext, document_id: uuid.UUID
    ) -> list[DocumentVersion]:
        document = self._get_document_for_read(scope, document_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(DocumentVersion)
                    .where(DocumentVersion.document_id == document.id)
                    .order_by(DocumentVersion.uploaded_at.desc())
                )
            )

    def _get_document_for_read(
        self, scope: ScopeContext, document_id: uuid.UUID
    ) -> SourceDocument:
        with self.session_factory() as session:
            document = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.id == document_id,
                    SourceDocument.tenant_id == scope.tenant_id,
                )
            )
            if document is None:
                raise DocumentNotFound("document was not found")
            self._authorize_read(scope, document.study_id, document.site_id)
            return document

    def _get_version_for_read(
        self, scope: ScopeContext, version_id: uuid.UUID
    ) -> DocumentVersion:
        with self.session_factory() as session:
            version = session.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.id == version_id,
                    DocumentVersion.tenant_id == scope.tenant_id,
                )
            )
            if version is None:
                raise DocumentNotFound("document version was not found")
            self._authorize_read(scope, version.study_id, version.site_id)
            return version

    def get_version(
        self, scope: ScopeContext, version_id: uuid.UUID
    ) -> DocumentVersion:
        return self._get_version_for_read(scope, version_id)

    def read_content(
        self, scope: ScopeContext, version_id: uuid.UUID
    ) -> StoredContent:
        version = self._get_version_for_read(scope, version_id)
        return StoredContent(
            content=self.storage.read(version.storage_key),
            media_type=version.media_type,
            filename=version.original_filename,
            version=version,
        )

    def anchors(
        self, scope: ScopeContext, version_id: uuid.UUID
    ) -> list[SourceAnchor]:
        self._get_version_for_read(scope, version_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(SourceAnchor)
                    .where(SourceAnchor.document_version_id == version_id)
                    .order_by(SourceAnchor.ordinal)
                )
            )

    def coverage(
        self, scope: ScopeContext, version_id: uuid.UUID
    ) -> list[ParseCoverage]:
        self._get_version_for_read(scope, version_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(ParseCoverage)
                    .where(ParseCoverage.document_version_id == version_id)
                    .order_by(ParseCoverage.created_at, ParseCoverage.unit_key)
                )
            )

    def job(self, scope: ScopeContext, job_id: uuid.UUID) -> BusinessJob:
        with self.session_factory() as session:
            job = session.scalar(
                select(BusinessJob).where(
                    BusinessJob.id == job_id,
                    BusinessJob.tenant_id == scope.tenant_id,
                )
            )
            if job is None:
                raise DocumentNotFound("job was not found")
            self._authorize_read(scope, job.study_id, job.site_id)
            return job

    @staticmethod
    def _scope_for_job(job: BusinessJob) -> ScopeContext:
        return ScopeContext(
            actor_id=job.actor_id,
            tenant_id=job.tenant_id,
            authentication_source=job.authentication_source,
            platform_roles=frozenset(job.platform_roles),
        )

    def process_job(
        self, job_id: uuid.UUID, *, worker_id: str = "synchronous-worker"
    ) -> ParseResult:
        now = datetime.now(UTC)
        with self.session_factory() as session:
            initial_job = session.get(BusinessJob, job_id)
            if initial_job is None:
                raise DocumentNotFound("job was not found")
            scope = self._scope_for_job(initial_job)
        try:
            self._authorize_read(scope, initial_job.study_id, initial_job.site_id)
        except AuthorizationDenied:
            with self.session_factory() as session:
                with session.begin():
                    job = session.get(BusinessJob, job_id, with_for_update=True)
                    assert job is not None
                    self._fail_job(
                        session,
                        job,
                        code="authorization_revoked",
                        summary="authorization changed before worker processing",
                    )
            raise

        with self.session_factory() as session:
            with session.begin():
                job = session.scalar(
                    select(BusinessJob)
                    .where(BusinessJob.id == job_id)
                    .with_for_update()
                )
                if job is None:
                    raise DocumentNotFound("job was not found")
                if job.status == "succeeded":
                    version = session.get(DocumentVersion, job.input_version_id)
                    assert version is not None
                    return self._load_parse_result(session, version)
                if job.status == "running" and (
                    job.lease_expires_at is None or job.lease_expires_at > now
                ):
                    raise DocumentJobConflict("job already has an active lease")
                if job.attempts >= job.max_attempts:
                    raise DocumentJobConflict("job retry budget exhausted")
                job.status = "running"
                job.attempts += 1
                job.lease_owner = worker_id
                job.lease_expires_at = now + timedelta(minutes=5)
                version = session.get(DocumentVersion, job.input_version_id)
                if version is None:
                    raise DocumentNotFound("input version was not found")
                version.parse_status = "running"
                version_id = version.id

        try:
            stored = self.read_content(scope, version_id)
            parser = next(
                (
                    candidate
                    for candidate in self.parsers
                    if candidate.supports(stored.media_type, stored.filename)
                ),
                None,
            )
            if parser is None:
                result = ParseResult(
                    parser_name="private-file-only",
                    parser_version="1",
                    anchors=(),
                    coverage=(
                        CoverageUnit(
                            unit_key="document",
                            unit_type="document",
                            status="unsupported",
                            reason=(
                                "This format is retained as a private source file; "
                                "structured parsing belongs to its owning task."
                            ),
                        ),
                    ),
                    status="partial",
                )
            else:
                result = parser.parse(
                    stored.content,
                    media_type=stored.media_type,
                    filename=stored.filename,
                )
        except Exception as exc:
            with self.session_factory() as session:
                with session.begin():
                    job = session.get(BusinessJob, job_id, with_for_update=True)
                    assert job is not None
                    version = session.get(DocumentVersion, job.input_version_id)
                    assert version is not None
                    version.parse_status = "failed"
                    self._fail_job(
                        session,
                        job,
                        code="parse_failed",
                        summary=f"{type(exc).__name__}: {exc}"[:500],
                    )
            raise

        with self.session_factory() as session:
            with session.begin():
                job = session.scalar(
                    select(BusinessJob)
                    .where(BusinessJob.id == job_id)
                    .with_for_update()
                )
                assert job is not None
                self._authorize_read(
                    self._scope_for_job(job), job.study_id, job.site_id
                )
                version = session.get(DocumentVersion, job.input_version_id)
                assert version is not None
                session.execute(
                    delete(ParseCoverage).where(
                        ParseCoverage.document_version_id == version.id
                    )
                )
                session.execute(
                    delete(SourceAnchor).where(
                        SourceAnchor.document_version_id == version.id
                    )
                )
                anchor_ids: dict[str, uuid.UUID] = {}
                for parsed in result.anchors:
                    anchor_id = uuid.uuid4()
                    anchor_ids[parsed.logical_node_id] = anchor_id
                    session.add(
                        SourceAnchor(
                            id=anchor_id,
                            tenant_id=version.tenant_id,
                            study_id=version.study_id,
                            site_id=version.site_id,
                            document_version_id=version.id,
                            anchor_type=parsed.anchor_type,
                            logical_node_id=parsed.logical_node_id,
                            section_path=parsed.section_path,
                            text=parsed.text,
                            style={**parsed.style, **parsed.metadata},
                            page_number=parsed.page_number,
                            bbox=parsed.bbox,
                            table_index=parsed.table_index,
                            row_index=parsed.row_index,
                            column_index=parsed.column_index,
                            footnote_id=parsed.footnote_id,
                            ordinal=parsed.ordinal,
                        )
                    )
                session.flush()
                for unit in result.coverage:
                    session.add(
                        ParseCoverage(
                            id=uuid.uuid4(),
                            tenant_id=version.tenant_id,
                            study_id=version.study_id,
                            site_id=version.site_id,
                            document_version_id=version.id,
                            unit_key=unit.unit_key,
                            unit_type=unit.unit_type,
                            status=unit.status,
                            reason=unit.reason,
                            anchor_id=(
                                anchor_ids.get(unit.anchor_key)
                                if unit.anchor_key
                                else None
                            ),
                            metadata_json=unit.metadata,
                        )
                    )
                version.parser_name = result.parser_name
                version.parser_version = result.parser_version
                if result.status == "failed":
                    version.parse_status = "failed"
                    self._fail_job(
                        session,
                        job,
                        code="parse_failed",
                        summary="parser reported failure",
                    )
                else:
                    version.parse_status = result.status
                    job.status = "succeeded"
                    job.error_code = None
                    job.error_summary = None
                    job.lease_owner = None
                    job.lease_expires_at = None
                    job.output = {
                        "parse_status": result.status,
                        "anchor_count": len(result.anchors),
                        "coverage_count": len(result.coverage),
                        "warnings": list(result.warnings)[:20],
                    }
                session.add(
                    OutboxEvent(
                        id=uuid.uuid4(),
                        tenant_id=version.tenant_id,
                        study_id=version.study_id,
                        site_id=version.site_id,
                        event_type=f"document.parse.{'completed' if job.status == 'succeeded' else 'failed'}",
                        aggregate_type="document_version",
                        aggregate_id=version.id,
                        dedup_key=(
                            f"parse-result:{job.id}:{job.attempts}:{result.status}"
                        ),
                        payload={"job_id": str(job.id)},
                    )
                )
        if result.status == "failed":
            raise DocumentValidationError("parser reported a failed document")
        return result

    @staticmethod
    def _fail_job(
        session: Session,
        job: BusinessJob,
        *,
        code: str,
        summary: str,
    ) -> None:
        job.status = "failed"
        job.error_code = code
        job.error_summary = summary
        job.lease_owner = None
        job.lease_expires_at = None

    @staticmethod
    def _load_parse_result(
        session: Session, version: DocumentVersion
    ) -> ParseResult:
        anchors = list(
            session.scalars(
                select(SourceAnchor)
                .where(SourceAnchor.document_version_id == version.id)
                .order_by(SourceAnchor.ordinal)
            )
        )
        coverage = list(
            session.scalars(
                select(ParseCoverage).where(
                    ParseCoverage.document_version_id == version.id
                )
            )
        )
        return ParseResult(
            parser_name=version.parser_name or "stored",
            parser_version=version.parser_version or "1",
            anchors=tuple(
                ParsedAnchor(
                    anchor_type=item.anchor_type,
                    logical_node_id=item.logical_node_id,
                    text=item.text,
                    ordinal=item.ordinal,
                    section_path=item.section_path,
                    style=item.style,
                    page_number=item.page_number,
                    bbox=item.bbox,
                    table_index=item.table_index,
                    row_index=item.row_index,
                    column_index=item.column_index,
                    footnote_id=item.footnote_id,
                )
                for item in anchors
            ),
            coverage=tuple(
                CoverageUnit(
                    unit_key=item.unit_key,
                    unit_type=item.unit_type,
                    status=item.status,
                    reason=item.reason,
                    metadata=item.metadata_json,
                )
                for item in coverage
            ),
            status=version.parse_status,
        )

    def retry_job(
        self, scope: ScopeContext, job_id: uuid.UUID
    ) -> BusinessJob:
        job = self.job(scope, job_id)
        self._authorize_upload(scope, job.study_id, job.site_id)
        if job.attempts >= job.max_attempts:
            raise DocumentJobConflict("job retry budget exhausted")
        if job.status not in {"failed", "queued"}:
            raise DocumentJobConflict("only failed or queued jobs can be retried")
        with self.session_factory() as session:
            with session.begin():
                row = session.get(BusinessJob, job_id, with_for_update=True)
                assert row is not None
                row.status = "queued"
                row.available_at = datetime.now(UTC)
                row.lease_owner = None
                row.lease_expires_at = None
                session.add(
                    OutboxEvent(
                        id=uuid.uuid4(),
                        tenant_id=row.tenant_id,
                        study_id=row.study_id,
                        site_id=row.site_id,
                        event_type="document.parse.requested",
                        aggregate_type="document_version",
                        aggregate_id=row.input_version_id,
                        dedup_key=f"parse-retry:{row.id}:{row.attempts}",
                        payload={"job_id": str(row.id)},
                    )
                )
        self.relay_outbox_safely()
        return self.job(scope, job_id)
