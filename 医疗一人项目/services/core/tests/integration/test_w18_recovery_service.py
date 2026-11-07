from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.application.knowledge import (
    CitationService,
    ClaimService,
    KnowledgeIndexService,
    KnowledgeSearchService,
    KnowledgeVersionService,
)
from medical_one_person.application.knowledge_browser import KnowledgeBrowser
from medical_one_person.application.knowledge_ingestion import KnowledgeIngestionService
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.recovery import RecoveryService
from medical_one_person.application.recovery_database import restore_manifest_rows
from medical_one_person.application.tasks import TaskService
from medical_one_person.domain.recovery import TrashState
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser
from medical_one_person.infrastructure.knowledge.upload import UploadService


def _setup(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W18恢复项目",
        scope="验证删除、索引重建与加密恢复。",
        idempotency_key="w18-project",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="evidence.review",
        purpose="w18-recovery",
        assignee_role="A26",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:w18"],
        goal="生成W18恢复测试引用。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
    )
    store = LocalArtifactStore(tmp_path / "objects")
    uploads = UploadService(
        session_factory,
        store,
        tmp_path / "staging",
        max_file_bytes=2 * 1024 * 1024,
        max_batch_bytes=4 * 1024 * 1024,
        chunk_size=64 * 1024,
    )
    uploads.ensure_private_library(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    content = (
        "W18合成研究：犬模型疼痛评分下降。\n"
        "阴性结果：功能改善未观察到。\n"
    ).encode()
    digest = hashlib.sha256(content).hexdigest()
    started = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="w18-recovery-study.txt",
        expected_bytes=len(content),
        media_type_hint="text/plain",
        expected_sha256=digest,
    )
    uploads.put_part(
        session_id=started.session_id,
        actor_user_id=identity.owner_user_id,
        offset=0,
        content=content,
        client_sha256=digest,
    )
    version = uploads.commit(
        session_id=started.session_id,
        actor_user_id=identity.owner_user_id,
    )
    KnowledgeIngestionService(session_factory, store, DocumentParser()).process(
        workspace_id=identity.workspace_id,
        job_id=version.job_id,
    )
    indexer = KnowledgeIndexService(
        session_factory,
        chunk_chars=80,
        overlap_chars=10,
    )
    indexer.index_version(
        workspace_id=identity.workspace_id,
        version_id=version.version_id,
    )
    recovery = RecoveryService(
        session_factory,
        store,
        indexer,
        backup_root=tmp_path / "backups",
        restore_root=tmp_path / "restore-checks",
    )
    return identity, project, task, store, uploads, indexer, recovery, version


def _citation(
    session_factory: sessionmaker[Session],
    identity,
    project,
    task,
    version,
):
    hit = KnowledgeSearchService(session_factory).search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="犬模型 疼痛",
    ).hits[0]
    KnowledgeVersionService(session_factory).record_source_review(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        version_id=version.version_id,
        scope="W18合成引文范围",
        outcome="verified_scope",
        evidence_refs=[str(hit.chunk_id)],
    )
    citation = CitationService(session_factory).create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
        chunk_id=hit.chunk_id,
        quoted_excerpt=hit.excerpt,
    )
    claim = ClaimService(session_factory).create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        statement="合成药物可能降低犬疼痛评分。",
        species_or_population="犬",
        directness="direct",
    )
    ClaimService(session_factory).link_evidence(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        claim_version_id=claim.version_id,
        citation_id=citation.id,
        stance="supports",
    )
    return citation, claim


def test_trash_restore_and_safe_index_rebuild(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity, project, task, _store, _uploads, indexer, recovery, version = _setup(
        session_factory,
        tmp_path,
    )
    rebuilt = indexer.rebuild_version(
        workspace_id=identity.workspace_id,
        version_id=version.version_id,
    )
    assert rebuilt.chunks >= 1
    assert rebuilt.state == "ready"

    citation, _claim = _citation(session_factory, identity, project, task, version)
    with pytest.raises(ValueError, match="immutable citations"):
        indexer.rebuild_version(
            workspace_id=identity.workspace_id,
            version_id=version.version_id,
        )

    trashed = recovery.trash_document(
        project_id=project.id,
        document_id=version.document_id,
        actor_user_id=identity.owner_user_id,
        reason="W18合成回收站测试",
    )
    assert trashed.state == TrashState.TRASHED
    assert trashed.reference_count == 1
    assert trashed.blocked_reason == "REFERENCED_BY_1_CITATIONS"
    assert KnowledgeBrowser(session_factory).list_documents(
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
    ) == []
    with pytest.raises(NotFoundError, match="Current document version"):
        KnowledgeBrowser(session_factory).get_document(
            actor_user_id=identity.owner_user_id,
            project_id=project.id,
            document_id=version.document_id,
        )
    hidden = KnowledgeSearchService(session_factory).search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="犬模型 疼痛",
    )
    assert hidden.hits == []
    workspace = recovery.workspace(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert workspace.trash[0].document_id == version.document_id
    assert workspace.trash[0].reference_count == 1

    restored = recovery.restore_document(
        project_id=project.id,
        document_id=version.document_id,
        actor_user_id=identity.owner_user_id,
    )
    assert restored.state == TrashState.RESTORED
    visible = KnowledgeBrowser(session_factory).list_documents(
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
    )
    assert [item.id for item in visible] == [version.document_id]
    result = KnowledgeSearchService(session_factory).search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="犬模型 疼痛",
    )
    assert result.hits
    assert any(hit.chunk_id == citation.chunk_id for hit in result.hits)


def test_encrypted_backup_and_isolated_restore_verification(
    session_factory: sessionmaker[Session],
    database_url: str,
    tmp_path: Path,
) -> None:
    identity, project, task, _store, _uploads, _indexer, recovery, version = _setup(
        session_factory,
        tmp_path,
    )
    _citation(session_factory, identity, project, task, version)
    passphrase = "synthetic-W18-passphrase"
    backup = recovery.create_backup(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        passphrase=passphrase,
        idempotency_key="w18-backup",
    )
    assert backup.state == "completed"
    assert backup.backup_sha256
    assert backup.encrypted_size_bytes > 0
    assert backup.manifest["counts"]["citations"] == 1
    assert backup.manifest["counts"]["evidence_links"] == 1
    backup_path = tmp_path / "backups" / str(project.id) / backup.file_name
    assert backup_path.is_file()
    assert b"W18" not in backup_path.read_bytes()
    replay = recovery.create_backup(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        passphrase=passphrase,
        idempotency_key="w18-backup",
    )
    assert replay == backup

    verified = recovery.restore_check(
        project_id=project.id,
        backup_id=backup.id,
        actor_user_id=identity.owner_user_id,
        passphrase=passphrase,
    )
    assert verified.state == "verified"
    assert verified.object_count >= 1
    assert verified.detail["database_json_validated"] is True
    assert verified.detail["isolated_database_restore_run"] is False
    assert verified.detail["active_database_overwritten"] is False
    restore_directory = Path(verified.detail["restore_directory"])
    assert (restore_directory / "manifest.json").is_file()
    assert list((restore_directory / "objects").rglob("*"))
    manifest = json.loads((restore_directory / "manifest.json").read_text())

    parsed = make_url(database_url)
    restore_database = f"medical_one_restore_{uuid4().hex[:10]}"
    admin_engine = create_engine(
        parsed.set(database="postgres").render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{restore_database}"'))
    restore_url = parsed.set(database=restore_database).render_as_string(
        hide_password=False
    )
    restore_engine = None
    try:
        core_root = Path(__file__).resolve().parents[2]
        config = Config(core_root / "alembic.ini")
        config.set_main_option("script_location", str(core_root / "migrations"))
        config.attributes["database_url"] = restore_url
        command.upgrade(config, "head")
        restore_engine = create_engine(restore_url)
        with sessionmaker(bind=restore_engine).begin() as restored_session:
            counts = restore_manifest_rows(restored_session, manifest)
        assert counts["workspaces"] == 1
        assert counts["projects"] == 1
        assert counts["tasks"] == 1
        assert counts["citations"] == 1
        assert counts["budget_ledger_entries"] == 0
    finally:
        if restore_engine is not None:
            restore_engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                text(f'DROP DATABASE IF EXISTS "{restore_database}" WITH (FORCE)')
            )
        admin_engine.dispose()

    failed = recovery.restore_check(
        project_id=project.id,
        backup_id=backup.id,
        actor_user_id=identity.owner_user_id,
        passphrase="wrong-synthetic-passphrase",
    )
    assert failed.state == "failed"
    assert "active_database_overwritten" in failed.detail

    with backup_path.open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ValueError, match="hash verification"):
        recovery.restore_check(
            project_id=project.id,
            backup_id=backup.id,
            actor_user_id=identity.owner_user_id,
            passphrase=passphrase,
        )


def test_w18_tables_are_forced_through_workspace_rls(database: Engine) -> None:
    with database.connect() as connection:
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
        tables = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN (
                    'trash_entries',
                    'backup_snapshots',
                    'restore_checks'
                  )
                ORDER BY c.relname
                """
            )
        ).all()
    assert policies == 84
    assert len(tables) == 3
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
