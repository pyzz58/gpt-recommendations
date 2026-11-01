from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
)
from medical_one_person.application.knowledge import (
    INDEX_VERSION,
    KnowledgeIndexService,
)
from medical_one_person.domain.recovery import (
    BackupView,
    IndexRebuildView,
    RecoveryWorkspaceView,
    RestoreCheckView,
    TrashEntryView,
    TrashState,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.engine import EXPECTED_DATABASE_REVISION
from medical_one_person.infrastructure.db.models import (
    AgentRun,
    AnalysisReview,
    AnalysisRun,
    Artifact,
    ArtifactExport,
    ArtifactVersion,
    AuditEvaluation,
    AuditFinding,
    AuditRun,
    BackupSnapshot,
    Budget,
    BudgetLedgerEntry,
    BudgetReservation,
    Citation,
    Claim,
    ClaimVersion,
    Dataset,
    DatasetRow,
    DatasetVersion,
    Decision,
    DocumentExtraction,
    EvidenceLink,
    ExtractionTable,
    ImpactReview,
    KnowledgeBlob,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    Library,
    Opportunity,
    OpportunityVersion,
    Plan,
    PlanNode,
    PolicyBundle,
    PolicyImpact,
    PolicyMigrationOperation,
    PolicyState,
    Project,
    ProjectEvent,
    ProjectVersion,
    ProvenanceEdge,
    ReliabilityEvaluation,
    RestoreCheck,
    RetrievalSnapshot,
    SourcePassage,
    SourceReview,
    StatisticalPlan,
    Task,
    TaskDependency,
    TaskReview,
    TaskVersion,
    TrashEntry,
    User,
    Workspace,
)

BACKUP_FORMAT = "medical-one-encrypted-backup.v1"
BACKUP_MAGIC = b"M1BKUP01"
KDF_NAME = "scrypt"
KDF_N = 2**14
KDF_R = 8
KDF_P = 1
TRASH_RETENTION_DAYS = 30


class RecoveryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        artifact_store: LocalArtifactStore,
        indexer: KnowledgeIndexService,
        *,
        backup_root: Path,
        restore_root: Path,
    ) -> None:
        self._session_factory = session_factory
        self._artifact_store = artifact_store
        self._indexer = indexer
        self._backup_root = backup_root.resolve()
        self._restore_root = restore_root.resolve()
        self._backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._restore_root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def workspace(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> RecoveryWorkspaceView:
        with self._session_factory.begin() as session:
            _owner(session, actor_user_id)
            with _rls_context(session, actor_user_id):
                project = _project(session, project_id, actor_user_id)
                trash_rows = session.scalars(
                    select(TrashEntry)
                    .where(
                        TrashEntry.project_id == project.id,
                        TrashEntry.state == TrashState.TRASHED.value,
                    )
                    .order_by(TrashEntry.deleted_at.desc())
                ).all()
                titles = {
                    item.id: item.title
                    for item in session.scalars(
                        select(KnowledgeDocument).where(
                            KnowledgeDocument.id.in_(
                                [item.document_id for item in trash_rows]
                            )
                        )
                    ).all()
                }
                backups = session.scalars(
                    select(BackupSnapshot)
                    .where(BackupSnapshot.project_id == project.id)
                    .order_by(BackupSnapshot.created_at.desc())
                ).all()
                checks = session.scalars(
                    select(RestoreCheck)
                    .where(RestoreCheck.project_id == project.id)
                    .order_by(RestoreCheck.created_at.desc())
                ).all()
                return RecoveryWorkspaceView(
                    trash=[
                        _trash_view(item, titles.get(item.document_id, "unknown"))
                        for item in trash_rows
                    ],
                    backups=[_backup_view(item) for item in backups],
                    restore_checks=[_restore_check_view(item) for item in checks],
                    limitations=[
                        "Restore checks validate an encrypted archive in an isolated "
                        "directory; they do not overwrite the active database.",
                        "The passphrase is used only in memory and is never persisted.",
                        "Offline mode blocks remote tools but does not mean cached "
                        "regulatory, patent or literature material is current.",
                    ],
                )

    def trash_document(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
        actor_user_id: UUID,
        reason: str,
    ) -> TrashEntryView:
        if len(reason.strip()) < 3:
            raise ValueError("Trash reason is required")
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            with _rls_context(session, actor_user_id):
                project = _project(session, project_id, actor_user_id)
                _lock_project(session, project.id)
                document, versions = _document_versions(
                    session,
                    project.id,
                    document_id,
                )
                reference_count = int(
                    session.scalar(
                        select(func.count())
                        .select_from(Citation)
                        .where(
                            Citation.project_id == project.id,
                            Citation.version_id.in_([item.id for item in versions]),
                        )
                    )
                    or 0
                )
                entry = session.scalar(
                    select(TrashEntry)
                    .where(
                        TrashEntry.project_id == project.id,
                        TrashEntry.document_id == document.id,
                    )
                    .with_for_update()
                )
                if entry is not None and entry.state == TrashState.TRASHED.value:
                    return _trash_view(entry, document.title)
                previous_states = {str(item.id): item.access_state for item in versions}
                blocked_reason = (
                    f"REFERENCED_BY_{reference_count}_CITATIONS"
                    if reference_count
                    else None
                )
                for version in versions:
                    version.access_state = "trashed"
                if entry is None:
                    entry = TrashEntry(
                        id=uuid4(),
                        workspace_id=project.workspace_id,
                        project_id=project.id,
                        document_id=document.id,
                        previous_access_states=previous_states,
                        reference_count=reference_count,
                        blocked_reason=blocked_reason,
                        reason=reason.strip(),
                        state=TrashState.TRASHED.value,
                        purge_after=now + timedelta(days=TRASH_RETENTION_DAYS),
                        deleted_by_user_id=actor.id,
                        deleted_at=now,
                        restored_at=None,
                    )
                    session.add(entry)
                else:
                    entry.previous_access_states = previous_states
                    entry.reference_count = reference_count
                    entry.blocked_reason = blocked_reason
                    entry.reason = reason.strip()
                    entry.state = TrashState.TRASHED.value
                    entry.purge_after = now + timedelta(days=TRASH_RETENTION_DAYS)
                    entry.deleted_by_user_id = actor.id
                    entry.deleted_at = now
                    entry.restored_at = None
                _event(
                    session,
                    project=project,
                    actor=actor,
                    event_type="knowledge.document_trashed",
                    object_id=document.id,
                    payload={
                        "reason": reason.strip(),
                        "reference_count": reference_count,
                        "blocked_reason": blocked_reason,
                    },
                    now=now,
                )
                session.flush()
                return _trash_view(entry, document.title)

    def rebuild_index(
        self,
        *,
        project_id: UUID,
        version_id: UUID,
        actor_user_id: UUID,
    ) -> IndexRebuildView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            with _rls_context(session, actor_user_id):
                project = _project(session, project_id, actor_user_id)
                version = session.scalar(
                    select(KnowledgeDocumentVersion).where(
                        KnowledgeDocumentVersion.id == version_id,
                        KnowledgeDocumentVersion.project_id == project.id,
                    )
                )
                if version is None:
                    raise NotFoundError("Knowledge document version not found")
                workspace_id = actor.workspace_id
        result = self._indexer.rebuild_version(
            workspace_id=workspace_id,
            version_id=version_id,
        )
        return IndexRebuildView(
            version_id=result.version_id,
            chunks=result.chunks,
            state=result.state,
            index_version=INDEX_VERSION,
            rebuilt=True,
        )

    def restore_document(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
        actor_user_id: UUID,
    ) -> TrashEntryView:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            with _rls_context(session, actor_user_id):
                project = _project(session, project_id, actor_user_id)
                _lock_project(session, project.id)
                entry = session.scalar(
                    select(TrashEntry)
                    .where(
                        TrashEntry.project_id == project.id,
                        TrashEntry.document_id == document_id,
                    )
                    .with_for_update()
                )
                if entry is None:
                    raise NotFoundError("Trash entry not found")
                document, versions = _document_versions(
                    session,
                    project.id,
                    document_id,
                )
                if entry.state == TrashState.RESTORED.value:
                    return _trash_view(entry, document.title)
                for version in versions:
                    version.access_state = entry.previous_access_states.get(
                        str(version.id),
                        "active",
                    )
                entry.state = TrashState.RESTORED.value
                entry.restored_at = now
                _event(
                    session,
                    project=project,
                    actor=actor,
                    event_type="knowledge.document_restored",
                    object_id=document.id,
                    payload={"reason": entry.reason},
                    now=now,
                )
                return _trash_view(entry, document.title)

    def create_backup(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        passphrase: str,
        idempotency_key: str,
    ) -> BackupView:
        _validate_passphrase(passphrase)
        request_hash = _digest({"project_id": str(project_id), "format": BACKUP_FORMAT})
        with self._session_factory.begin() as session:
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            actor = _owner(session, actor_user_id)
            with _rls_context(session, actor_user_id):
                project = _project(session, project_id, actor_user_id)
                existing = session.scalar(
                    select(BackupSnapshot).where(
                        BackupSnapshot.project_id == project.id,
                        BackupSnapshot.idempotency_key == idempotency_key,
                    )
                )
                if existing is not None:
                    if existing.request_hash != request_hash:
                        raise ConflictingOperationError(
                            "Backup idempotency key was reused with different parameters"
                        )
                    return _backup_view(existing)
                backup_id = uuid4()
                backup_dir = self._backup_root / str(project.id)
                backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                file_name = f"{backup_id}.m1backup"
                destination = backup_dir / file_name
                with tempfile.TemporaryDirectory(
                    dir=self._backup_root,
                    prefix="w18-build-",
                ) as temporary:
                    archive = Path(temporary) / "snapshot.zip"
                    manifest, plaintext_sha256 = self._write_archive(
                        session,
                        project=project,
                        archive=archive,
                    )
                    salt, nonce, kdf = _encrypt_archive(
                        archive,
                        destination,
                        passphrase,
                    )
                backup_sha256, encrypted_size = _file_digest(destination)
                row = BackupSnapshot(
                    id=backup_id,
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    format=BACKUP_FORMAT,
                    file_name=file_name,
                    state="completed",
                    backup_sha256=backup_sha256,
                    plaintext_sha256=plaintext_sha256,
                    encrypted_size_bytes=encrypted_size,
                    manifest=manifest,
                    kdf={
                        **kdf,
                        "salt_hex": salt.hex(),
                        "nonce_hex": nonce.hex(),
                    },
                    error_code=None,
                    created_by_user_id=actor.id,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    created_at=datetime.now(UTC),
                )
                try:
                    session.add(row)
                    session.flush()
                except Exception:
                    destination.unlink(missing_ok=True)
                    raise
                return _backup_view(row)

    def restore_check(
        self,
        *,
        project_id: UUID,
        backup_id: UUID,
        actor_user_id: UUID,
        passphrase: str,
    ) -> RestoreCheckView:
        _validate_passphrase(passphrase)
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            with _rls_context(session, actor_user_id):
                project = _project(session, project_id, actor_user_id)
                backup = session.scalar(
                    select(BackupSnapshot).where(
                        BackupSnapshot.id == backup_id,
                        BackupSnapshot.project_id == project.id,
                    )
                )
                if backup is None or backup.state != "completed":
                    raise NotFoundError("Completed backup not found")
                source = self._backup_root / str(project.id) / backup.file_name
                if not source.is_file():
                    raise NotFoundError("Backup file not found")
                actual_sha, _size = _file_digest(source)
                if actual_sha != backup.backup_sha256:
                    raise ValueError("Backup file hash verification failed")
                destination = (
                    self._restore_root
                    / str(project.id)
                    / f"{backup.id}-{uuid4().hex[:12]}"
                )
                destination.mkdir(parents=True, exist_ok=False, mode=0o700)
                try:
                    plaintext_sha256, object_count = _decrypt_and_verify(
                        source,
                        destination,
                        passphrase,
                        backup,
                    )
                    check = RestoreCheck(
                        id=uuid4(),
                        workspace_id=project.workspace_id,
                        project_id=project.id,
                        backup_id=backup.id,
                        state="verified",
                        object_count=object_count,
                        table_counts=backup.manifest["counts"],
                        detail={
                            "plaintext_sha256": plaintext_sha256,
                            "backup_sha256": actual_sha,
                            "restore_directory": str(destination),
                            "database_json_validated": True,
                            "isolated_database_restore_run": False,
                            "active_database_overwritten": False,
                        },
                        created_by_user_id=actor.id,
                        created_at=datetime.now(UTC),
                    )
                except (InvalidTag, ValueError, zipfile.BadZipFile) as exc:
                    shutil.rmtree(destination, ignore_errors=True)
                    check = RestoreCheck(
                        id=uuid4(),
                        workspace_id=project.workspace_id,
                        project_id=project.id,
                        backup_id=backup.id,
                        state="failed",
                        object_count=0,
                        table_counts={},
                        detail={
                            "error": str(exc),
                            "restore_directory": str(destination),
                            "active_database_overwritten": False,
                        },
                        created_by_user_id=actor.id,
                        created_at=datetime.now(UTC),
                    )
                    session.add(check)
                    session.flush()
                    return _restore_check_view(check)
                session.add(check)
                session.flush()
                return _restore_check_view(check)

    def _write_archive(
        self,
        session: Session,
        *,
        project: Project,
        archive: Path,
    ) -> tuple[dict[str, Any], str]:
        libraries = session.scalars(
            select(Library).where(Library.project_id == project.id)
        ).all()
        library_ids = [item.id for item in libraries]
        documents = session.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.library_id.in_(library_ids)
            )
        ).all()
        document_ids = [item.id for item in documents]
        versions = session.scalars(
            select(KnowledgeDocumentVersion).where(
                KnowledgeDocumentVersion.project_id == project.id
            )
        ).all()
        version_ids = [item.id for item in versions]
        blob_ids = sorted({item.blob_id for item in versions})
        blobs = session.scalars(
            select(KnowledgeBlob).where(KnowledgeBlob.id.in_(blob_ids))
        ).all()
        tables: dict[str, list[dict[str, Any]]] = {
            "workspaces": [
                _model_row(
                    session.get(Workspace, project.workspace_id)
                )
            ],
            "users": [
                _model_row(item)
                for item in session.scalars(
                    select(User).where(User.workspace_id == project.workspace_id)
                ).all()
            ],
            "projects": [_model_row(project)],
            "policy_states": [
                _model_row(item)
                for item in session.scalars(
                    select(PolicyState).where(
                        PolicyState.workspace_id == project.workspace_id
                    )
                ).all()
            ],
            "policy_bundles": [
                _model_row(item)
                for item in session.scalars(
                    select(PolicyBundle)
                    .where(PolicyBundle.workspace_id == project.workspace_id)
                    .order_by(PolicyBundle.id)
                ).all()
            ],
            "policy_impacts": [
                _model_row(item)
                for item in session.scalars(
                    select(PolicyImpact)
                    .where(PolicyImpact.project_id == project.id)
                    .order_by(PolicyImpact.id)
                ).all()
            ],
            "policy_migration_operations": [
                _model_row(item)
                for item in session.scalars(
                    select(PolicyMigrationOperation)
                    .where(PolicyMigrationOperation.project_id == project.id)
                    .order_by(PolicyMigrationOperation.id)
                ).all()
            ],
            "project_versions": [
                _model_row(item)
                for item in session.scalars(
                    select(ProjectVersion).where(ProjectVersion.project_id == project.id)
                ).all()
            ],
            "libraries": [_model_row(item) for item in libraries],
            "knowledge_documents": [_model_row(item) for item in documents],
            "knowledge_document_versions": [_model_row(item) for item in versions],
            "knowledge_blobs": [_model_row(item) for item in blobs],
        }
        for model in _PROJECT_TABLES:
            rows = session.scalars(
                select(model)
                .where(model.project_id == project.id)
                .order_by(model.id)
            ).all()
            tables[model.__tablename__] = [_model_row(item) for item in rows]
        for model in _VERSION_TABLES:
            rows = session.scalars(
                select(model)
                .where(model.version_id.in_(version_ids))
                .order_by(model.id)
            ).all()
            tables[model.__tablename__] = [_model_row(item) for item in rows]
        for model in _DOCUMENT_TABLES:
            rows = session.scalars(
                select(model)
                .where(model.document_id.in_(document_ids))
                .order_by(model.id)
            ).all()
            tables[model.__tablename__] = [_model_row(item) for item in rows]

        object_rows = [
            {
                "object_key": item.object_key,
                "sha256": item.content_hash,
                "size_bytes": item.size_bytes,
                "source": "knowledge_blob",
            }
            for item in blobs
        ]
        artifact_versions = session.scalars(
            select(ArtifactVersion).where(ArtifactVersion.project_id == project.id)
        ).all()
        object_rows.extend(
            {
                "object_key": item.object_key,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "source": "artifact_version",
            }
            for item in artifact_versions
        )
        objects: list[dict[str, Any]] = list(
            {item["object_key"]: item for item in object_rows}.values()
        )
        manifest = {
            "schema_version": 1,
            "format": BACKUP_FORMAT,
            "created_at": datetime.now(UTC).isoformat(),
            "database_revision": EXPECTED_DATABASE_REVISION,
            "project_id": str(project.id),
            "workspace_id": str(project.workspace_id),
            "counts": {name: len(rows) for name, rows in tables.items()},
            "objects": objects,
            "tables": tables,
            "limitations": [
                "Database JSON is validated during restore-check but is not reinserted "
                "into the active database.",
                "The archive contains project-scoped objects only.",
            ],
        }
        manifest_bytes = json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        with zipfile.ZipFile(
            archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as handle:
            handle.writestr("manifest.json", manifest_bytes)
            for item in objects:
                path = self._artifact_store.trusted_path(item["object_key"])
                actual_sha, actual_size = _file_digest(path)
                if actual_sha != item["sha256"] or actual_size != item["size_bytes"]:
                    raise ValueError("An object failed hash verification before backup")
                handle.write(path, f"objects/{item['object_key']}")
        return manifest, hashlib.sha256(manifest_bytes).hexdigest()


_PROJECT_TABLES: tuple[type[Any], ...] = (
    AgentRun,
    Budget,
    BudgetReservation,
    BudgetLedgerEntry,
    Decision,
    Opportunity,
    OpportunityVersion,
    Plan,
    PlanNode,
    Task,
    TaskVersion,
    TaskDependency,
    TaskReview,
    KnowledgeChunk,
    Citation,
    RetrievalSnapshot,
    Claim,
    ClaimVersion,
    EvidenceLink,
    ProvenanceEdge,
    Artifact,
    ArtifactVersion,
    ArtifactExport,
    Dataset,
    DatasetVersion,
    DatasetRow,
    StatisticalPlan,
    AnalysisRun,
    AnalysisReview,
    AuditRun,
    AuditFinding,
    AuditEvaluation,
    ReliabilityEvaluation,
    TrashEntry,
)

_VERSION_TABLES: tuple[type[Any], ...] = (
    DocumentExtraction,
    SourcePassage,
    ExtractionTable,
    SourceReview,
)

_DOCUMENT_TABLES: tuple[type[Any], ...] = (ImpactReview,)


def _encrypt_archive(
    source: Path,
    destination: Path,
    passphrase: str,
) -> tuple[bytes, bytes, dict[str, Any]]:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=KDF_N,
        r=KDF_R,
        p=KDF_P,
        dklen=32,
    )
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    temporary = destination.with_suffix(".tmp")
    with source.open("rb") as input_handle, temporary.open("wb") as output_handle:
        output_handle.write(BACKUP_MAGIC)
        output_handle.write(salt)
        output_handle.write(nonce)
        for block in iter(lambda: input_handle.read(1024 * 1024), b""):
            output_handle.write(encryptor.update(block))
        output_handle.write(encryptor.finalize())
        output_handle.write(encryptor.tag)
        output_handle.flush()
        os.fsync(output_handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)
    return salt, nonce, {
        "name": KDF_NAME,
        "n": KDF_N,
        "r": KDF_R,
        "p": KDF_P,
        "cipher": "AES-256-GCM",
    }


def _decrypt_and_verify(
    source: Path,
    destination: Path,
    passphrase: str,
    backup: BackupSnapshot,
) -> tuple[str, int]:
    with source.open("rb") as handle:
        if handle.read(len(BACKUP_MAGIC)) != BACKUP_MAGIC:
            raise ValueError("Unsupported backup format")
        salt = handle.read(16)
        nonce = handle.read(12)
        if len(salt) != 16 or len(nonce) != 12:
            raise ValueError("Backup header is incomplete")
        handle.seek(0, os.SEEK_END)
        total = handle.tell()
        payload_size = total - len(BACKUP_MAGIC) - 16 - 12 - 16
        if payload_size < 0:
            raise ValueError("Backup file is truncated")
        handle.seek(len(BACKUP_MAGIC) + 16 + 12)
        key = hashlib.scrypt(
            passphrase.encode("utf-8"),
            salt=salt,
            n=KDF_N,
            r=KDF_R,
            p=KDF_P,
            dklen=32,
        )
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).decryptor()
        archive = destination / "snapshot.zip"
        remaining = payload_size
        with archive.open("wb") as output:
            while remaining:
                block = handle.read(min(1024 * 1024, remaining))
                if not block:
                    raise ValueError("Backup ciphertext is truncated")
                output.write(decryptor.update(block))
                remaining -= len(block)
            tag = handle.read(16)
            if len(tag) != 16:
                raise ValueError("Backup authentication tag is missing")
            output.write(decryptor.finalize_with_tag(tag))
    manifest_path = destination / "manifest.json"
    objects_root = destination / "objects"
    objects_root.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as handle:
        names = set(handle.namelist())
        if "manifest.json" not in names:
            raise ValueError("Backup manifest is missing")
        handle.extract("manifest.json", destination)
        manifest_bytes = manifest_path.read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != backup.plaintext_sha256:
            raise ValueError("Backup manifest hash does not match the recorded snapshot")
        manifest = json.loads(manifest_bytes)
        _validate_manifest(manifest, backup)
        for item in manifest["objects"]:
            member = f"objects/{item['object_key']}"
            if member not in names:
                raise ValueError("Backup object is missing")
            extracted = _safe_member(destination, member)
            extracted.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(member) as input_handle, extracted.open("wb") as output:
                shutil.copyfileobj(input_handle, output, length=1024 * 1024)
            os.chmod(extracted, 0o600)
            actual_sha, actual_size = _file_digest(extracted)
            if actual_sha != item["sha256"] or actual_size != item["size_bytes"]:
                raise ValueError("Restored object failed hash verification")
        extra_objects = {
            name
            for name in names
            if name != "manifest.json" and not name.startswith("objects/")
        }
        if extra_objects:
            raise ValueError("Backup contains unsupported archive members")
        expected_members = {
            "manifest.json",
            *{f"objects/{item['object_key']}" for item in manifest["objects"]},
        }
        if names != expected_members:
            raise ValueError("Backup archive member manifest is inconsistent")
    archive.unlink()
    os.chmod(manifest_path, 0o600)
    return hashlib.sha256(manifest_bytes).hexdigest(), len(manifest["objects"])


def _validate_manifest(manifest: dict[str, Any], backup: BackupSnapshot) -> None:
    if manifest.get("format") != BACKUP_FORMAT:
        raise ValueError("Unsupported backup manifest format")
    if manifest.get("project_id") != str(backup.project_id):
        raise ValueError("Backup project does not match the recorded snapshot")
    counts = manifest.get("counts")
    tables = manifest.get("tables")
    if not isinstance(counts, dict) or not isinstance(tables, dict):
        raise ValueError("Backup manifest counts or tables are missing")
    if any(len(tables[name]) != count for name, count in counts.items()):
        raise ValueError("Backup table count verification failed")
    chunk_ids = {row["id"] for row in tables.get("knowledge_chunks", [])}
    citation_ids = {row["id"] for row in tables.get("citations", [])}
    for row in tables.get("citations", []):
        if row["chunk_id"] not in chunk_ids:
            raise ValueError("Backup citation references a missing chunk")
    for row in tables.get("evidence_links", []):
        if row["citation_id"] not in citation_ids:
            raise ValueError("Backup evidence link references a missing citation")


def _model_row(model: Any) -> dict[str, Any]:
    return {
        column.key: _jsonable(getattr(model, column.key))
        for column in model.__table__.columns
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _safe_member(root: Path, member: str) -> Path:
    target = (root / member).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Backup archive path escapes the restore directory")
    return target


def _validate_passphrase(passphrase: str) -> None:
    if len(passphrase) < 12:
        raise ValueError("Backup passphrase must contain at least 12 characters")


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage recovery")
    return actor


class _RLSContext:
    def __init__(self, session: Session, actor: User) -> None:
        self._session = session
        self._actor = actor

    def __enter__(self) -> None:
        set_rls_context(
            self._session,
            workspace_id=self._actor.workspace_id,
            user_id=self._actor.id,
        )

    def __exit__(self, *_args: object) -> None:
        return None


def _rls_context(session: Session, actor_user_id: UUID) -> _RLSContext:
    actor = _owner(session, actor_user_id)
    return _RLSContext(session, actor)


def _project(session: Session, project_id: UUID, actor_user_id: UUID) -> Project:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != actor.workspace_id:
        raise NotFoundError("Project not found")
    return project


def _lock_project(session: Session, project_id: UUID) -> None:
    project = session.scalar(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    if project is None:
        raise NotFoundError("Project not found")


def _document_versions(
    session: Session,
    project_id: UUID,
    document_id: UUID,
) -> tuple[KnowledgeDocument, Sequence[KnowledgeDocumentVersion]]:
    versions = session.scalars(
        select(KnowledgeDocumentVersion)
        .where(
            KnowledgeDocumentVersion.project_id == project_id,
            KnowledgeDocumentVersion.document_id == document_id,
        )
        .with_for_update()
    ).all()
    if not versions:
        raise NotFoundError("Knowledge document not found")
    document = session.get(KnowledgeDocument, document_id)
    if document is None:
        raise NotFoundError("Knowledge document not found")
    return document, versions


def _event(
    session: Session,
    *,
    project: Project,
    actor: User,
    event_type: str,
    object_id: UUID,
    payload: dict[str, Any],
    now: datetime,
) -> None:
    last = session.scalar(
        select(func.max(ProjectEvent.project_seq)).where(
            ProjectEvent.project_id == project.id
        )
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=project.workspace_id,
            project_id=project.id,
            project_seq=(last or 0) + 1,
            type=event_type,
            actor_user_id=actor.id,
            object_type="knowledge_document",
            object_id=object_id,
            object_revision=1,
            payload=payload,
            correlation_id=uuid4(),
            created_at=now,
        )
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _trash_view(row: TrashEntry, title: str) -> TrashEntryView:
    return TrashEntryView(
        id=row.id,
        document_id=row.document_id,
        title=title,
        reference_count=row.reference_count,
        blocked_reason=row.blocked_reason,
        reason=row.reason,
        state=TrashState(row.state),
        purge_after=row.purge_after.astimezone(UTC),
        deleted_at=row.deleted_at.astimezone(UTC),
        restored_at=row.restored_at.astimezone(UTC) if row.restored_at else None,
    )


def _backup_view(row: BackupSnapshot) -> BackupView:
    return BackupView(
        id=row.id,
        project_id=row.project_id,
        format=row.format,
        file_name=row.file_name,
        state=cast(Literal["completed", "failed"], row.state),
        backup_sha256=row.backup_sha256,
        plaintext_sha256=row.plaintext_sha256,
        encrypted_size_bytes=row.encrypted_size_bytes,
        manifest=row.manifest,
        error_code=row.error_code,
        created_at=row.created_at.astimezone(UTC),
    )


def _restore_check_view(row: RestoreCheck) -> RestoreCheckView:
    return RestoreCheckView(
        id=row.id,
        backup_id=row.backup_id,
        state=cast(Literal["verified", "failed"], row.state),
        object_count=row.object_count,
        table_counts=row.table_counts,
        detail=row.detail,
        created_at=row.created_at.astimezone(UTC),
    )
