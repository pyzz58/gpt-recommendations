from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.knowledge import (
    CitationService,
    ClaimService,
    KnowledgeIndexService,
    KnowledgeSearchService,
    KnowledgeVersionService,
)
from medical_one_person.application.knowledge_ingestion import KnowledgeIngestionService
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.tasks import TaskService
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Citation,
    ClaimVersion,
    EvidenceLink,
    ImpactReview,
    KnowledgeDocumentVersion,
    RetrievalSnapshot,
)
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser
from medical_one_person.infrastructure.knowledge.upload import UploadService


def _setup(session_factory: sessionmaker[Session], tmp_path: Path):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="检索证据项目",
        scope="W08词法检索、引用和版本影响测试。",
        idempotency_key="create-retrieval-project",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="evidence.review",
        purpose="w08-retrieval",
        assignee_role="A26",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:retrieval"],
        goal="核对合成研究资料。",
        deliverable_schema="audit_report.v1",
        acceptance_policy="independent_review.v1",
        mode="mock",
    )
    store = LocalArtifactStore(tmp_path / "objects")
    uploads = UploadService(
        session_factory,
        store,
        tmp_path / "staging",
        max_file_bytes=1024 * 1024,
        max_batch_bytes=2 * 1024 * 1024,
        chunk_size=64 * 1024,
    )
    uploads.ensure_private_library(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    return identity, project, task, store, uploads


def _upload(
    uploads: UploadService,
    identity,
    project,
    *,
    filename: str,
    content: bytes,
    document_id=None,
):
    upload = uploads.create_session(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        filename=filename,
        expected_bytes=len(content),
        media_type_hint="text/plain",
        expected_sha256=hashlib.sha256(content).hexdigest(),
        document_id=document_id,
    )
    uploads.put_part(
        session_id=upload.session_id,
        actor_user_id=identity.owner_user_id,
        offset=0,
        content=content,
        client_sha256=hashlib.sha256(content).hexdigest(),
    )
    return uploads.commit(
        session_id=upload.session_id,
        actor_user_id=identity.owner_user_id,
    )


def test_search_snapshot_citation_claim_and_version_impact(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    identity, project, task, store, uploads = _setup(session_factory, tmp_path)
    first_content = (
        "第一版：合成药物在犬模型中降低了疼痛评分。\n阴性结果：未观察到功能改善。\n"
    ).encode()
    first = _upload(
        uploads,
        identity,
        project,
        filename="synthetic-study.txt",
        content=first_content,
    )
    ingestion = KnowledgeIngestionService(session_factory, store, DocumentParser())
    ingestion.process(workspace_id=identity.workspace_id, job_id=first.job_id)
    indexer = KnowledgeIndexService(session_factory, chunk_chars=80, overlap_chars=10)
    indexed = indexer.index_version(
        workspace_id=identity.workspace_id,
        version_id=first.version_id,
    )
    assert indexed.chunks >= 1
    assert indexed.state == "ready"
    assert (
        indexer.index_version(
            workspace_id=identity.workspace_id,
            version_id=first.version_id,
        ).chunks
        == indexed.chunks
    )

    search = KnowledgeSearchService(session_factory)
    result = search.search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="犬模型 疼痛",
    )
    assert result.hits
    hit = result.hits[0]
    assert hit.locator["start_line"] == 1
    version_service = KnowledgeVersionService(session_factory)
    review_id = version_service.record_source_review(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        version_id=first.version_id,
        scope="synthetic citation check only",
        outcome="verified_scope",
        evidence_refs=[str(hit.chunk_id)],
    )
    assert review_id

    citations = CitationService(session_factory)
    citation = citations.create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        task_id=task.id,
        chunk_id=hit.chunk_id,
        quoted_excerpt=hit.excerpt,
    )
    assert citation.review_status == "unreviewed"
    with pytest.raises(ValueError, match="not present"):
        citations.create(
            workspace_id=identity.workspace_id,
            actor_user_id=identity.owner_user_id,
            task_id=task.id,
            chunk_id=hit.chunk_id,
            quoted_excerpt="不存在的引文",
        )

    claims = ClaimService(session_factory)
    claim = claims.create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        statement="合成药物可能降低犬疼痛评分。",
        species_or_population="犬",
        intervention="合成药物",
        comparator="对照",
        endpoint="疼痛评分",
        analysis_set="synthetic",
        sample_size=None,
        directness="direct",
    )
    claims.link_evidence(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        claim_version_id=claim.version_id,
        citation_id=citation.id,
        stance="supports",
    )

    second_content = "第二版：合成药物证据已更新，犬疼痛结论待复核。\n".encode()
    second = _upload(
        uploads,
        identity,
        project,
        filename="synthetic-study-v2.txt",
        content=second_content,
        document_id=first.document_id,
    )
    ingestion.process(workspace_id=identity.workspace_id, job_id=second.job_id)
    indexer.index_version(workspace_id=identity.workspace_id, version_id=second.version_id)
    impact = version_service.promote_current(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        document_id=first.document_id,
        version_id=second.version_id,
        expected_revision=1,
        reason="第二版更正了合成结论",
    )
    assert {"citation", "claim_version", "retrieval_snapshot", "task"}.issubset(
        {item["type"] for item in impact.affected}
    )

    current_results = search.search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="降低了疼痛评分",
    )
    assert current_results.hits == []
    historical_results = search.search(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        task_id=task.id,
        query="降低了疼痛评分",
        include_historical=True,
    )
    assert historical_results.hits
    assert historical_results.hits[0].version_id == first.version_id

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored_citation = session.get(Citation, citation.id)
        stored_claim = session.get(ClaimVersion, claim.version_id)
        snapshots = session.scalars(select(RetrievalSnapshot)).all()
        impact_rows = session.scalars(select(ImpactReview)).all()
        links = session.scalars(select(EvidenceLink)).all()
        versions = session.scalars(
            select(KnowledgeDocumentVersion).order_by(KnowledgeDocumentVersion.version_label)
        ).all()
    assert stored_citation is not None
    assert stored_claim is not None and stored_claim.status == "stale"
    assert len(snapshots) == 3
    assert len(impact_rows) == 1
    assert len(links) == 1
    assert [version.version_status for version in versions] == [
        "historical",
        "current",
    ]
