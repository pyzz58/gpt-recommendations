from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.knowledge_ingestion import KnowledgeIngestionService
from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.knowledge.documents import IngestState
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    IngestJob,
    KnowledgeBlob,
    KnowledgeDocumentVersion,
    SourcePassage,
)
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser
from medical_one_person.infrastructure.knowledge.upload import (
    KnowledgeUploadError,
    UploadService,
)


def _setup(session_factory: sessionmaker[Session], tmp_path: Path):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="知识库上传项目",
        scope="W07分片上传、原件和解析测试。",
        idempotency_key="create-knowledge-project",
    )
    store = LocalArtifactStore(tmp_path / "objects")
    uploads = UploadService(
        session_factory,
        store,
        tmp_path / "staging",
        max_file_bytes=1024,
        max_batch_bytes=2048,
        chunk_size=8,
    )
    library_id = uploads.ensure_private_library(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    return identity, project, library_id, store, uploads


def _put(uploads: UploadService, identity, session_id, offset: int, content: bytes):
    return uploads.put_part(
        session_id=session_id,
        actor_user_id=identity.owner_user_id,
        offset=offset,
        content=content,
        client_sha256=hashlib.sha256(content).hexdigest(),
    )


def _put_all(uploads: UploadService, identity, session_id, content: bytes) -> None:
    for offset in range(0, len(content), 8):
        _put(uploads, identity, session_id, offset, content[offset : offset + 8])


def test_chunked_upload_resume_idempotency_and_ingestion(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity, project, _, store, uploads = _setup(session_factory, tmp_path)
    content = "合成本地资料\n第二段\n".encode()
    status = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="synthetic.txt",
        expected_bytes=len(content),
        media_type_hint="text/plain",
        expected_sha256=hashlib.sha256(content).hexdigest(),
    )

    first = content[:8]
    _put_all(uploads, identity, status.session_id, content)
    replay = _put(uploads, identity, status.session_id, 0, first)
    assert replay.received_ranges == [(0, len(content))]

    with pytest.raises(KnowledgeUploadError, match="overlaps"):
        _put(uploads, identity, status.session_id, 4, b"changed")
    with pytest.raises(KnowledgeUploadError, match="different content"):
        _put(uploads, identity, status.session_id, 0, b"changed!")

    resumed = uploads.get_status(
        session_id=status.session_id,
        actor_user_id=identity.owner_user_id,
    )
    assert resumed.received_ranges == [(0, len(content))]
    assert resumed.received_bytes == len(content)

    committed = uploads.commit(
        session_id=status.session_id,
        actor_user_id=identity.owner_user_id,
    )
    replay_commit = uploads.commit(
        session_id=status.session_id,
        actor_user_id=identity.owner_user_id,
    )
    assert committed == replay_commit
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        version = session.get(KnowledgeDocumentVersion, committed.version_id)
        assert version is not None
        blob = session.get(KnowledgeBlob, version.blob_id)
        assert blob is not None
        assert store.read(blob.object_key, blob.content_hash) == content
        assert version.ingest_state == IngestState.QUEUED
        assert version.evidence_status == "unreviewed"
        assert version.version_status == "current"
        assert version.access_state == "active"
        assert session.scalar(select(func.count()).select_from(KnowledgeDocumentVersion)) == 1
        assert session.scalar(select(func.count()).select_from(IngestJob)) == 1

    second = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="synthetic-copy.txt",
        expected_bytes=len(content),
        media_type_hint="text/plain",
    )
    _put_all(uploads, identity, second.session_id, content)
    second_commit = uploads.commit(
        session_id=second.session_id,
        actor_user_id=identity.owner_user_id,
    )
    assert committed.document_id in second_commit.duplicate_document_ids
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        blob = session.get(KnowledgeBlob, committed.blob_id)
        assert blob is not None and blob.ref_count == 2

    ingestion = KnowledgeIngestionService(
        session_factory,
        store,
        DocumentParser(),
    )
    parsed = ingestion.process(
        workspace_id=identity.workspace_id,
        job_id=committed.job_id,
    )
    assert parsed.state == IngestState.INDEXING
    assert parsed.passages >= 1
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        version = session.get(KnowledgeDocumentVersion, committed.version_id)
        passages = session.scalars(
            select(SourcePassage).where(SourcePassage.version_id == committed.version_id)
        ).all()
    assert version is not None
    assert version.ingest_state == IngestState.INDEXING
    assert version.evidence_status == "unreviewed"
    assert passages[0].locator["start_line"] == 1


def test_upload_rejections_and_partial_image_parsing(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity, project, _, store, uploads = _setup(session_factory, tmp_path)

    with pytest.raises(KnowledgeUploadError, match="path"):
        uploads.create_session(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            filename="../escape.txt",
            expected_bytes=1,
            media_type_hint="text/plain",
        )
    with pytest.raises(KnowledgeUploadError, match="Unsupported"):
        uploads.create_session(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            filename="archive.zip",
            expected_bytes=1,
            media_type_hint="application/zip",
        )
    with pytest.raises(KnowledgeUploadError, match="limit"):
        uploads.create_session(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            filename="large.txt",
            expected_bytes=1025,
            media_type_hint="text/plain",
        )

    incomplete = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="incomplete.txt",
        expected_bytes=5,
        media_type_hint="text/plain",
    )
    _put(uploads, identity, incomplete.session_id, 0, b"abc")
    with pytest.raises(KnowledgeUploadError, match="not complete"):
        uploads.commit(
            session_id=incomplete.session_id,
            actor_user_id=identity.owner_user_id,
        )

    image_path = tmp_path / "scan.png"
    Image.new("RGB", (24, 12), "white").save(image_path)
    image_bytes = image_path.read_bytes()
    image_upload = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="scan.png",
        expected_bytes=len(image_bytes),
        media_type_hint="image/png",
    )
    _put_all(uploads, identity, image_upload.session_id, image_bytes)
    image_commit = uploads.commit(
        session_id=image_upload.session_id,
        actor_user_id=identity.owner_user_id,
    )
    parsed = KnowledgeIngestionService(session_factory, store, DocumentParser()).process(
        workspace_id=identity.workspace_id,
        job_id=image_commit.job_id,
    )
    assert parsed.state == IngestState.PARTIAL
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        version = session.get(KnowledgeDocumentVersion, image_commit.version_id)
        assert version is not None
        assert version.ingest_state == IngestState.PARTIAL

    bad = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename="fake.pdf",
        expected_bytes=8,
        media_type_hint="application/pdf",
    )
    _put(uploads, identity, bad.session_id, 0, b"not-pdf!")
    with pytest.raises(KnowledgeUploadError, match="does not match"):
        uploads.commit(
            session_id=bad.session_id,
            actor_user_id=identity.owner_user_id,
        )
