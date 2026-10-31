from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.domain.knowledge.documents import IngestState
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    IngestJob,
    KnowledgeBlob,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    Library,
    Project,
    ProjectEvent,
    UploadPart,
    UploadSession,
    User,
)
from medical_one_person.infrastructure.knowledge.parsers import SUPPORTED_EXTENSIONS

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class KnowledgeUploadError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class UploadStatus:
    session_id: UUID
    filename: str
    expected_bytes: int
    received_bytes: int
    chunk_size: int
    received_ranges: list[tuple[int, int]]
    state: str
    expires_at: datetime


@dataclass(frozen=True)
class UploadCommit:
    session_id: UUID
    blob_id: UUID
    document_id: UUID
    version_id: UUID
    job_id: UUID
    ingest_state: str
    duplicate_document_ids: list[UUID]


class UploadService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: LocalArtifactStore,
        staging_root: Path,
        *,
        max_file_bytes: int,
        max_batch_bytes: int,
        chunk_size: int,
        expiry: timedelta = timedelta(hours=24),
    ) -> None:
        self._session_factory = session_factory
        self._store = store
        self._staging_root = staging_root.resolve()
        self._staging_root.mkdir(parents=True, exist_ok=True)
        self._max_file_bytes = max_file_bytes
        self._max_batch_bytes = max_batch_bytes
        self._chunk_size = chunk_size
        self._expiry = expiry

    def ensure_private_library(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        name: str = "项目资料",
    ) -> UUID:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = self._project(session, project_id, actor.workspace_id)
            library = session.scalar(
                select(Library).where(
                    Library.workspace_id == actor.workspace_id,
                    Library.project_id == project.id,
                    Library.scope == "project_private",
                    Library.name == name,
                )
            )
            if library is None:
                library = Library(
                    id=uuid4(),
                    workspace_id=actor.workspace_id,
                    project_id=project.id,
                    scope="project_private",
                    name=name,
                    acl_revision=1,
                    created_at=datetime.now(UTC),
                )
                session.add(library)
                session.flush()
            return library.id

    def create_session(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        filename: str,
        expected_bytes: int,
        media_type_hint: str | None,
        expected_sha256: str | None = None,
        batch_reserved_bytes: int | None = None,
        document_id: UUID | None = None,
    ) -> UploadStatus:
        safe_filename = Path(filename).name
        if safe_filename != filename or not safe_filename:
            raise KnowledgeUploadError("UNSUPPORTED_FORMAT", "Filename must not contain a path")
        if Path(safe_filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise KnowledgeUploadError("UNSUPPORTED_FORMAT", "Unsupported document format")
        if expected_bytes <= 0 or expected_bytes > self._max_file_bytes:
            raise KnowledgeUploadError("UPLOAD_TOO_LARGE", "File exceeds the configured limit")
        batch_total = batch_reserved_bytes if batch_reserved_bytes is not None else expected_bytes
        if batch_total > self._max_batch_bytes:
            raise KnowledgeUploadError("UPLOAD_TOO_LARGE", "Batch exceeds the configured limit")
        if expected_sha256 is not None and not _HASH_PATTERN.fullmatch(expected_sha256):
            raise KnowledgeUploadError("CHECKSUM_MISMATCH", "Expected SHA-256 is malformed")

        session_id = uuid4()
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = self._project(session, project_id, actor.workspace_id)
            library = session.scalar(
                select(Library).where(
                    Library.workspace_id == actor.workspace_id,
                    Library.project_id == project.id,
                    Library.scope == "project_private",
                )
            )
            if library is None:
                raise KnowledgeUploadError(
                    "DOCUMENT_RESTRICTED", "Project private library is not initialized"
                )
            if document_id is not None:
                document = session.scalar(
                    select(KnowledgeDocument).where(
                        KnowledgeDocument.id == document_id,
                        KnowledgeDocument.library_id == library.id,
                    )
                )
                if document is None:
                    raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Document not found")
            upload = UploadSession(
                id=session_id,
                workspace_id=actor.workspace_id,
                project_id=project.id,
                library_id=library.id,
                uploader_user_id=actor.id,
                filename=safe_filename,
                media_type_hint=media_type_hint,
                expected_bytes=expected_bytes,
                expected_sha256=expected_sha256,
                chunk_size=self._chunk_size,
                state="active",
                reserved_bytes=expected_bytes,
                document_id=document_id,
                created_at=now,
                expires_at=now + self._expiry,
            )
            session.add(upload)
            session.flush()
        (self._session_dir(session_id) / "parts").mkdir(parents=True, exist_ok=True)
        return UploadStatus(
            session_id=session_id,
            filename=safe_filename,
            expected_bytes=expected_bytes,
            received_bytes=0,
            chunk_size=self._chunk_size,
            received_ranges=[],
            state="active",
            expires_at=now + self._expiry,
        )

    def put_part(
        self,
        *,
        session_id: UUID,
        actor_user_id: UUID,
        offset: int,
        content: bytes,
        client_sha256: str,
    ) -> UploadStatus:
        if offset < 0 or not content:
            raise KnowledgeUploadError("VALIDATION_FAILED", "Part offset or content is invalid")
        if len(content) > self._chunk_size:
            raise KnowledgeUploadError("UPLOAD_TOO_LARGE", "Part exceeds the chunk size")
        if not _HASH_PATTERN.fullmatch(client_sha256):
            raise KnowledgeUploadError("CHECKSUM_MISMATCH", "Part SHA-256 is malformed")
        server_hash = hashlib.sha256(content).hexdigest()
        if server_hash != client_sha256:
            raise KnowledgeUploadError("CHECKSUM_MISMATCH", "Part SHA-256 does not match")
        end = offset + len(content)
        path = self._part_path(session_id, offset)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            upload = session.scalar(
                select(UploadSession)
                .where(
                    UploadSession.id == session_id,
                    UploadSession.uploader_user_id == actor.id,
                )
                .with_for_update()
            )
            if upload is None:
                raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Upload session not found")
            self._require_active(upload)
            if end > upload.expected_bytes:
                raise KnowledgeUploadError("VALIDATION_FAILED", "Part exceeds expected file size")
            exact = session.scalar(
                select(UploadPart).where(
                    UploadPart.session_id == upload.id,
                    UploadPart.offset == offset,
                )
            )
            if exact is not None:
                if exact.length == len(content) and exact.part_hash == server_hash:
                    return self._status(session, upload)
                raise KnowledgeUploadError("VERSION_CONFLICT", "Part range has different content")
            overlap = session.scalar(
                select(UploadPart).where(
                    UploadPart.session_id == upload.id,
                    and_(
                        UploadPart.offset < end,
                        UploadPart.offset + UploadPart.length > offset,
                    ),
                )
            )
            if overlap is not None:
                raise KnowledgeUploadError("VERSION_CONFLICT", "Part overlaps an existing range")

            _atomic_write(path, content)
            session.add(
                UploadPart(
                    id=uuid4(),
                    workspace_id=upload.workspace_id,
                    session_id=upload.id,
                    offset=offset,
                    length=len(content),
                    part_hash=server_hash,
                    staging_key=str(path.relative_to(self._session_dir(session_id))),
                    created_at=datetime.now(UTC),
                )
            )
            session.flush()
            return self._status(session, upload)

    def get_status(self, *, session_id: UUID, actor_user_id: UUID) -> UploadStatus:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            upload = session.scalar(
                select(UploadSession).where(
                    UploadSession.id == session_id,
                    UploadSession.uploader_user_id == actor.id,
                )
            )
            if upload is None:
                raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Upload session not found")
            return self._status(session, upload)

    def commit(
        self,
        *,
        session_id: UUID,
        actor_user_id: UUID,
    ) -> UploadCommit:
        full_path = self._session_dir(session_id) / "full.upload"
        cleanup_parts = False
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            upload = session.scalar(
                select(UploadSession)
                .where(
                    UploadSession.id == session_id,
                    UploadSession.uploader_user_id == actor.id,
                )
                .with_for_update()
            )
            if upload is None:
                raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Upload session not found")
            if upload.state == "committed":
                assert upload.committed_blob_id and upload.document_id
                assert upload.committed_version_id and upload.committed_job_id
                return UploadCommit(
                    session_id=upload.id,
                    blob_id=upload.committed_blob_id,
                    document_id=upload.document_id,
                    version_id=upload.committed_version_id,
                    job_id=upload.committed_job_id,
                    ingest_state=IngestState.QUEUED,
                    duplicate_document_ids=[],
                )
            self._require_active(upload)
            parts = session.scalars(
                select(UploadPart)
                .where(UploadPart.session_id == upload.id)
                .order_by(UploadPart.offset)
            ).all()
            self._validate_complete_ranges(upload, parts)

            digest = hashlib.sha256()
            size = 0
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with full_path.open("wb") as target:
                for part in parts:
                    part_path = self._session_dir(session_id) / part.staging_key
                    if not part_path.is_file():
                        raise KnowledgeUploadError("INCOMPLETE_UPLOAD", "A staged part is missing")
                    with part_path.open("rb") as source:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            digest.update(block)
                            target.write(block)
                            size += len(block)
                target.flush()
                os.fsync(target.fileno())
            content_hash = digest.hexdigest()
            if size != upload.expected_bytes:
                raise KnowledgeUploadError("INCOMPLETE_UPLOAD", "Uploaded size does not match")
            if upload.expected_sha256 and content_hash != upload.expected_sha256:
                raise KnowledgeUploadError("CHECKSUM_MISMATCH", "Full-file SHA-256 differs")
            media_type = detect_media_type(full_path, upload.filename)
            stored = self._store.put_path(full_path)

            now = datetime.now(UTC)
            blob = session.scalar(
                select(KnowledgeBlob).where(
                    KnowledgeBlob.workspace_id == actor.workspace_id,
                    KnowledgeBlob.content_hash == stored.sha256,
                )
            )
            if blob is None:
                blob = KnowledgeBlob(
                    id=uuid4(),
                    workspace_id=actor.workspace_id,
                    content_hash=stored.sha256,
                    size_bytes=stored.size_bytes,
                    media_type=media_type,
                    object_key=stored.object_key,
                    ref_count=0,
                    created_at=now,
                )
                session.add(blob)
                session.flush()
            duplicate_document_ids = list(
                session.scalars(
                    select(KnowledgeDocumentVersion.document_id)
                    .where(
                        KnowledgeDocumentVersion.library_id == upload.library_id,
                        KnowledgeDocumentVersion.content_hash == stored.sha256,
                    )
                    .distinct()
                ).all()
            )
            if upload.document_id is not None:
                document = session.get(KnowledgeDocument, upload.document_id)
                if document is None:
                    raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Document not found")
            else:
                document = KnowledgeDocument(
                    id=uuid4(),
                    workspace_id=upload.workspace_id,
                    library_id=upload.library_id,
                    title=upload.filename,
                    document_kind=Path(upload.filename).suffix.lower().lstrip("."),
                    revision=1,
                    created_at=now,
                )
                session.add(document)
                session.flush()
            version_number = (
                session.scalar(
                    select(func.count())
                    .select_from(KnowledgeDocumentVersion)
                    .where(KnowledgeDocumentVersion.document_id == document.id)
                )
                or 0
            ) + 1
            version = KnowledgeDocumentVersion(
                id=uuid4(),
                workspace_id=document.workspace_id,
                project_id=upload.project_id,
                library_id=document.library_id,
                document_id=document.id,
                blob_id=blob.id,
                version_label=f"v{version_number}",
                filename=upload.filename,
                media_type=media_type,
                size_bytes=stored.size_bytes,
                content_hash=stored.sha256,
                origin="user_upload",
                data_origin="user_provided",
                confidentiality="project_private",
                cloud_policy="local_only",
                source_at=None,
                ingested_at=now,
                ingest_state=IngestState.QUEUED,
                evidence_status="unreviewed",
                version_status="current" if document.current_version_id is None else "historical",
                access_state="active",
            )
            session.add(version)
            session.flush()
            if document.current_version_id is None:
                document.current_version_id = version.id
            blob.ref_count += 1
            ingest_job = IngestJob(
                id=uuid4(),
                workspace_id=document.workspace_id,
                library_id=document.library_id,
                document_id=document.id,
                version_id=version.id,
                state="pending",
                attempts=0,
                created_at=now,
            )
            session.add(ingest_job)
            session.flush()
            upload.state = "committed"
            upload.committed_blob_id = blob.id
            upload.document_id = document.id
            upload.committed_version_id = version.id
            upload.committed_job_id = ingest_job.id
            upload.committed_at = now
            self._append_project_event(
                session,
                workspace_id=document.workspace_id,
                project_id=upload.project_id,
                file_name=upload.filename,
                version_id=version.id,
                actor_user_id=actor.id,
                now=now,
            )
            cleanup_parts = True
            result = UploadCommit(
                session_id=upload.id,
                blob_id=blob.id,
                document_id=document.id,
                version_id=version.id,
                job_id=ingest_job.id,
                ingest_state=version.ingest_state,
                duplicate_document_ids=duplicate_document_ids,
            )
        if cleanup_parts:
            shutil.rmtree(self._session_dir(session_id), ignore_errors=True)
        return result

    def cancel(self, *, session_id: UUID, actor_user_id: UUID) -> None:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            upload = session.scalar(
                select(UploadSession)
                .where(
                    UploadSession.id == session_id,
                    UploadSession.uploader_user_id == actor.id,
                )
                .with_for_update()
            )
            if upload is None:
                raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Upload session not found")
            if upload.state == "committed":
                raise KnowledgeUploadError(
                    "VERSION_CONFLICT", "Committed upload cannot be cancelled"
                )
            upload.state = "cancelled"
        shutil.rmtree(self._session_dir(session_id), ignore_errors=True)

    @staticmethod
    def _actor(session: Session, actor_user_id: UUID) -> User:
        actor = session.get(User, actor_user_id)
        if actor is None:
            raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Uploader not found")
        return actor

    @staticmethod
    def _set_context(session: Session, actor: User) -> None:
        set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)

    @staticmethod
    def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.workspace_id != workspace_id:
            raise KnowledgeUploadError("DOCUMENT_RESTRICTED", "Project not found")
        return project

    @staticmethod
    def _require_active(upload: UploadSession) -> None:
        if upload.state == "expired" or upload.expires_at <= datetime.now(UTC):
            upload.state = "expired"
            raise KnowledgeUploadError("INCOMPLETE_UPLOAD", "Upload session expired")
        if upload.state != "active":
            raise KnowledgeUploadError("VERSION_CONFLICT", "Upload session is not active")

    def _session_dir(self, session_id: UUID) -> Path:
        path = (self._staging_root / str(session_id)).resolve()
        if not path.is_relative_to(self._staging_root):
            raise KnowledgeUploadError("VALIDATION_FAILED", "Invalid staging path")
        return path

    def _part_path(self, session_id: UUID, offset: int) -> Path:
        return self._session_dir(session_id) / "parts" / f"{offset:020d}.part"

    def _status(self, session: Session, upload: UploadSession) -> UploadStatus:
        parts = session.scalars(
            select(UploadPart).where(UploadPart.session_id == upload.id).order_by(UploadPart.offset)
        ).all()
        ranges = _merge_ranges(parts)
        return UploadStatus(
            session_id=upload.id,
            filename=upload.filename,
            expected_bytes=upload.expected_bytes,
            received_bytes=sum(part.length for part in parts),
            chunk_size=upload.chunk_size,
            received_ranges=ranges,
            state=upload.state,
            expires_at=upload.expires_at,
        )

    @staticmethod
    def _validate_complete_ranges(upload: UploadSession, parts: Sequence[UploadPart]) -> None:
        ranges = _merge_ranges(parts)
        if ranges != [(0, upload.expected_bytes)]:
            raise KnowledgeUploadError("INCOMPLETE_UPLOAD", "Upload ranges are not complete")

    @staticmethod
    def _append_project_event(
        session: Session,
        *,
        workspace_id: UUID,
        project_id: UUID,
        file_name: str,
        version_id: UUID,
        actor_user_id: UUID,
        now: datetime,
    ) -> None:
        session.scalar(select(Project).where(Project.id == project_id).with_for_update())
        last_sequence = session.scalar(
            select(ProjectEvent.project_seq)
            .where(ProjectEvent.project_id == project_id)
            .order_by(ProjectEvent.project_seq.desc())
            .limit(1)
        )
        session.add(
            ProjectEvent(
                id=uuid4(),
                workspace_id=workspace_id,
                project_id=project_id,
                project_seq=(last_sequence or 0) + 1,
                type="knowledge.version_stored",
                actor_user_id=actor_user_id,
                object_type="document_version",
                object_id=version_id,
                object_revision=1,
                payload={"filename": file_name, "ingest_state": IngestState.QUEUED},
                correlation_id=uuid4(),
                created_at=now,
            )
        )


def detect_media_type(path: Path, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    with path.open("rb") as handle:
        prefix = handle.read(512)
    if extension == ".pdf" and prefix.startswith(b"%PDF-"):
        return "application/pdf"
    if extension == ".png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if extension in {".jpg", ".jpeg"} and prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if extension in {".docx", ".xlsx", ".pptx"}:
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
            expected_prefix = {
                ".docx": "word/",
                ".xlsx": "xl/",
                ".pptx": "ppt/",
            }[extension]
            if "[Content_Types].xml" in names and any(
                name.startswith(expected_prefix) for name in names
            ):
                ooxml_types = {
                    ".docx": (
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ),
                    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    ".pptx": (
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    ),
                }
                return ooxml_types[extension]
        except zipfile.BadZipFile as exc:
            raise KnowledgeUploadError("UNSUPPORTED_FORMAT", "Invalid OOXML file") from exc
    if extension in {".txt", ".md", ".csv", ".eml"}:
        with contextlib.suppress(UnicodeDecodeError):
            prefix.decode("utf-8")
        return {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".eml": "message/rfc822",
        }[extension]
    raise KnowledgeUploadError(
        "UNSUPPORTED_FORMAT", "File content does not match its declared format"
    )


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _merge_ranges(parts: Sequence[UploadPart]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for part in sorted(parts, key=lambda item: item.offset):
        start = part.offset
        end = part.offset + part.length
        if ranges and start == ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], end)
        else:
            ranges.append((start, end))
    return ranges
