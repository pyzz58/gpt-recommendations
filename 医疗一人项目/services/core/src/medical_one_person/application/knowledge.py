from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError, RevisionConflictError
from medical_one_person.application.tasks import invalidate_task_inputs
from medical_one_person.domain.knowledge.documents import IngestState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Citation,
    Claim,
    ClaimVersion,
    DocumentExtraction,
    EvidenceLink,
    ExtractionTable,
    ImpactReview,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    Library,
    Project,
    ProjectEvent,
    ProvenanceEdge,
    RetrievalSnapshot,
    SourcePassage,
    SourceReview,
    Task,
    User,
)

INDEX_VERSION = "lexical.v1"


@dataclass(frozen=True)
class IndexResult:
    version_id: UUID
    chunks: int
    state: str


@dataclass(frozen=True)
class SearchHit:
    chunk_id: UUID
    version_id: UUID
    document_id: UUID
    title: str
    locator: dict[str, Any]
    excerpt: str
    content_hash: str
    extraction_quality: dict[str, Any]
    score: float


@dataclass(frozen=True)
class SearchResult:
    snapshot_id: UUID
    query: str
    hits: list[SearchHit]
    permitted_version_ids: list[UUID]


@dataclass(frozen=True)
class CitationRecord:
    id: UUID
    chunk_id: UUID
    version_id: UUID
    locator: dict[str, Any]
    quoted_excerpt: str
    content_sha256: str
    review_status: str


@dataclass(frozen=True)
class ClaimRecord:
    id: UUID
    version_id: UUID
    revision: int
    statement: str
    status: str


@dataclass(frozen=True)
class ImpactResult:
    impact_review_id: UUID
    affected: list[dict[str, str]]


class KnowledgeIndexService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        chunk_chars: int = 1200,
        overlap_chars: int = 120,
    ) -> None:
        if chunk_chars <= overlap_chars or overlap_chars < 0:
            raise ValueError("Invalid chunk overlap configuration")
        self._session_factory = session_factory
        self._chunk_chars = chunk_chars
        self._overlap_chars = overlap_chars

    def index_version(self, *, workspace_id: UUID, version_id: UUID) -> IndexResult:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            version = session.get(KnowledgeDocumentVersion, version_id)
            if version is None:
                raise NotFoundError("Document version not found")
            return self._index_version(session, version)

    def rebuild_version(self, *, workspace_id: UUID, version_id: UUID) -> IndexResult:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            version = session.scalar(
                select(KnowledgeDocumentVersion)
                .where(KnowledgeDocumentVersion.id == version_id)
                .with_for_update()
            )
            if version is None:
                raise NotFoundError("Document version not found")
            citation_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(Citation)
                    .where(Citation.version_id == version.id)
                )
                or 0
            )
            if citation_count:
                raise ValueError(
                    "Index rebuild is blocked because immutable citations retain chunks: "
                    f"{citation_count}"
                )
            extraction = self._latest_extraction(session, version.id)
            session.execute(
                delete(KnowledgeChunk).where(
                    KnowledgeChunk.version_id == version.id,
                    KnowledgeChunk.extraction_id == extraction.id,
                    KnowledgeChunk.search_index_version == INDEX_VERSION,
                )
            )
            version.ingest_state = IngestState.INDEXING
            session.flush()
            return self._index_version(session, version)

    def _index_version(
        self,
        session: Session,
        version: KnowledgeDocumentVersion,
    ) -> IndexResult:
        extraction = self._latest_extraction(session, version.id)
        existing_count = int(
            session.scalar(
                select(func.count())
                .select_from(KnowledgeChunk)
                .where(
                    KnowledgeChunk.version_id == version.id,
                    KnowledgeChunk.extraction_id == extraction.id,
                    KnowledgeChunk.search_index_version == INDEX_VERSION,
                )
            )
            or 0
        )
        if existing_count:
            return IndexResult(
                version_id=version.id,
                chunks=existing_count,
                state=version.ingest_state,
            )
        passages = session.scalars(
            select(SourcePassage)
            .where(SourcePassage.extraction_id == extraction.id)
            .order_by(SourcePassage.id)
        ).all()
        chunk_index = 0
        for passage in passages:
            for part, locator in self._split(passage.text, passage.locator):
                session.add(
                    KnowledgeChunk(
                        id=uuid4(),
                        workspace_id=version.workspace_id,
                        library_id=version.library_id,
                        document_id=version.document_id,
                        project_id=_project_for_library(session, version.library_id),
                        version_id=version.id,
                        extraction_id=extraction.id,
                        chunk_index=chunk_index,
                        object_kind="passage",
                        object_id=passage.id,
                        locator=locator,
                        text=part,
                        content_hash=hashlib.sha256(part.encode()).hexdigest(),
                        extraction_quality=passage.extraction_quality,
                        search_index_version=INDEX_VERSION,
                    )
                )
                chunk_index += 1
        tables = session.scalars(
            select(ExtractionTable)
            .where(ExtractionTable.extraction_id == extraction.id)
            .order_by(ExtractionTable.id)
        ).all()
        for table in tables:
            table_text = json.dumps(table.table_data, ensure_ascii=False, sort_keys=True)
            for part, locator in self._split(table_text, table.locator):
                session.add(
                    KnowledgeChunk(
                        id=uuid4(),
                        workspace_id=version.workspace_id,
                        library_id=version.library_id,
                        document_id=version.document_id,
                        project_id=_project_for_library(session, version.library_id),
                        version_id=version.id,
                        extraction_id=extraction.id,
                        chunk_index=chunk_index,
                        object_kind="table",
                        object_id=table.id,
                        locator=locator,
                        text=part,
                        content_hash=hashlib.sha256(part.encode()).hexdigest(),
                        extraction_quality={"structured": True},
                        search_index_version=INDEX_VERSION,
                    )
                )
                chunk_index += 1
        state = IngestState.READY if extraction.state == "succeeded" else IngestState.PARTIAL
        version.ingest_state = state
        session.flush()
        return IndexResult(version_id=version.id, chunks=chunk_index, state=state)

    @staticmethod
    def _latest_extraction(
        session: Session,
        version_id: UUID,
    ) -> DocumentExtraction:
        extraction = session.scalar(
            select(DocumentExtraction)
            .where(
                DocumentExtraction.version_id == version_id,
                DocumentExtraction.state.in_(("succeeded", "partial")),
            )
            .order_by(DocumentExtraction.finished_at.desc())
            .limit(1)
        )
        if extraction is None:
            raise ValueError("No completed extraction is available for indexing")
        return extraction

    def _split(self, text: str, locator: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        if len(text) <= self._chunk_chars:
            return [(text, dict(locator))]
        chunks: list[tuple[str, dict[str, Any]]] = []
        start = 0
        while start < len(text):
            end = min(start + self._chunk_chars, len(text))
            chunks.append(
                (
                    text[start:end],
                    {**locator, "chunk_start_char": start, "chunk_end_char": end},
                )
            )
            if end == len(text):
                break
            start = end - self._overlap_chars
        return chunks


class KnowledgeSearchService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        task_id: UUID,
        query: str,
        top_k: int = 12,
        include_historical: bool = False,
    ) -> SearchResult:
        if not 1 <= top_k <= 40:
            raise ValueError("top_k must be between 1 and 40")
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query cannot be empty")
        terms = [
            term.lower() for term in re.split(r"[\s,，;；、]+", normalized_query) if term.strip()
        ]
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            task = session.scalar(
                select(Task).where(Task.id == task_id, Task.project_id == project_id)
            )
            if task is None:
                raise NotFoundError("Task not found")
            version_rows = session.execute(
                select(KnowledgeDocumentVersion, KnowledgeDocument, Library)
                .join(
                    KnowledgeDocument,
                    KnowledgeDocument.id == KnowledgeDocumentVersion.document_id,
                )
                .join(Library, Library.id == KnowledgeDocumentVersion.library_id)
                .where(
                    Library.project_id == project_id,
                    KnowledgeDocumentVersion.access_state == "active",
                )
            ).all()
            permitted = [
                (version, document)
                for version, document, _library in version_rows
                if include_historical or document.current_version_id == version.id
            ]
            permitted_ids = {version.id for version, _document in permitted}
            if not permitted_ids:
                snapshot = self._snapshot(
                    session,
                    project_id=project_id,
                    task_id=task.id,
                    query=normalized_query,
                    permitted_ids=[],
                    selected=[],
                    top_k=top_k,
                    include_historical=include_historical,
                )
                return SearchResult(snapshot.id, normalized_query, [], [])

            clauses = [KnowledgeChunk.text.ilike(f"%{term}%") for term in terms]
            candidate_rows = session.execute(
                select(KnowledgeChunk, KnowledgeDocument)
                .join(
                    KnowledgeDocument,
                    KnowledgeDocument.id == KnowledgeChunk.document_id,
                )
                .where(
                    KnowledgeChunk.project_id == project_id,
                    KnowledgeChunk.version_id.in_(permitted_ids),
                    KnowledgeChunk.search_index_version == INDEX_VERSION,
                    or_(
                        *clauses,
                        *[KnowledgeDocument.title.ilike(f"%{term}%") for term in terms],
                    ),
                )
                .limit(200)
            ).all()
            document_by_version = {version.id: document for version, document in permitted}
            scored: list[SearchHit] = []
            for chunk, candidate_document in candidate_rows:
                text_lower = chunk.text.lower()
                score = 3.0 if normalized_query.lower() in text_lower else 0.0
                score += sum(1.0 for term in terms if term in text_lower)
                if normalized_query.lower() in candidate_document.title.lower():
                    score += 2.0
                document = document_by_version[chunk.version_id]
                scored.append(
                    SearchHit(
                        chunk_id=chunk.id,
                        version_id=chunk.version_id,
                        document_id=chunk.document_id,
                        title=document.title,
                        locator=chunk.locator,
                        excerpt=chunk.text[:2000],
                        content_hash=chunk.content_hash,
                        extraction_quality=chunk.extraction_quality,
                        score=score,
                    )
                )
            scored.sort(key=lambda hit: (-hit.score, hit.title, str(hit.chunk_id)))
            selected = scored[:top_k]
            snapshot = self._snapshot(
                session,
                project_id=project_id,
                task_id=task.id,
                query=normalized_query,
                permitted_ids=sorted(permitted_ids, key=str),
                selected=selected,
                top_k=top_k,
                include_historical=include_historical,
            )
            return SearchResult(
                snapshot_id=snapshot.id,
                query=normalized_query,
                hits=selected,
                permitted_version_ids=sorted(permitted_ids, key=str),
            )

    @staticmethod
    def _snapshot(
        session: Session,
        *,
        project_id: UUID,
        task_id: UUID,
        query: str,
        permitted_ids: list[UUID],
        selected: list[SearchHit],
        top_k: int,
        include_historical: bool,
    ) -> RetrievalSnapshot:
        library_revision = (
            session.scalar(
                select(func.max(Library.acl_revision))
                .join(
                    KnowledgeDocumentVersion,
                    KnowledgeDocumentVersion.library_id == Library.id,
                )
                .where(Library.project_id == project_id)
            )
            or 1
        )
        snapshot = RetrievalSnapshot(
            id=uuid4(),
            workspace_id=session.scalar(
                select(Project.workspace_id).where(Project.id == project_id)
            ),
            project_id=project_id,
            task_id=task_id,
            query=query,
            filters={"include_historical": include_historical},
            permitted_version_ids=[str(item) for item in permitted_ids],
            selected_chunk_ids=[str(hit.chunk_id) for hit in selected],
            selected_content_hashes=[hit.content_hash for hit in selected],
            acl_revision=library_revision,
            top_k=top_k,
            created_at=datetime.now(UTC),
        )
        session.add(snapshot)
        session.flush()
        return snapshot


class CitationService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        task_id: UUID,
        chunk_id: UUID,
        quoted_excerpt: str,
    ) -> CitationRecord:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            chunk = session.get(KnowledgeChunk, chunk_id)
            task = session.get(Task, task_id)
            if (
                chunk is None
                or task is None
                or chunk.project_id != task.project_id
                or chunk.workspace_id != actor.workspace_id
            ):
                raise NotFoundError("Chunk or task not found")
            if not quoted_excerpt or quoted_excerpt not in chunk.text:
                raise ValueError("Quoted excerpt is not present in the indexed chunk")
            citation = Citation(
                id=uuid4(),
                workspace_id=chunk.workspace_id,
                library_id=chunk.library_id,
                document_id=chunk.document_id,
                project_id=chunk.project_id,
                version_id=chunk.version_id,
                extraction_id=chunk.extraction_id,
                chunk_id=chunk.id,
                task_id=task.id,
                locator=chunk.locator,
                quoted_excerpt=quoted_excerpt,
                content_sha256=hashlib.sha256(quoted_excerpt.encode()).hexdigest(),
                review_status="unreviewed",
                created_at=datetime.now(UTC),
            )
            session.add(citation)
            session.flush()
            return _citation_record(citation)


class ClaimService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        statement: str,
        species_or_population: str | None = None,
        intervention: str | None = None,
        comparator: str | None = None,
        endpoint: str | None = None,
        analysis_set: str | None = None,
        sample_size: int | None = None,
        directness: str = "unknown",
    ) -> ClaimRecord:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = session.get(Project, project_id)
            if project is None or project.workspace_id != actor.workspace_id:
                raise NotFoundError("Project not found")
            claim = Claim(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                current_version=1,
                created_by_user_id=actor.id,
                created_at=datetime.now(UTC),
            )
            session.add(claim)
            session.flush()
            version = ClaimVersion(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                claim_id=claim.id,
                revision=1,
                statement=statement,
                species_or_population=species_or_population,
                intervention=intervention,
                comparator=comparator,
                endpoint=endpoint,
                analysis_set=analysis_set,
                sample_size=sample_size,
                directness=directness,
                status="hypothesis",
                created_at=datetime.now(UTC),
            )
            session.add(version)
            session.flush()
            return _claim_record(version)

    def link_evidence(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        claim_version_id: UUID,
        citation_id: UUID,
        stance: str,
        note: str | None = None,
    ) -> None:
        if stance not in {"supports", "refutes", "context"}:
            raise ValueError("Unsupported evidence stance")
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            claim_version = session.get(ClaimVersion, claim_version_id)
            citation = session.get(Citation, citation_id)
            if (
                claim_version is None
                or citation is None
                or claim_version.project_id != citation.project_id
            ):
                raise NotFoundError("Claim or citation not found")
            session.add(
                EvidenceLink(
                    id=uuid4(),
                    workspace_id=claim_version.workspace_id,
                    project_id=claim_version.project_id,
                    claim_id=claim_version.claim_id,
                    claim_version_id=claim_version.id,
                    citation_id=citation.id,
                    stance=stance,
                    note=note,
                    created_at=datetime.now(UTC),
                )
            )


class KnowledgeVersionService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def promote_current(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        document_id: UUID,
        version_id: UUID,
        expected_revision: int,
        reason: str,
    ) -> ImpactResult:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            document = session.scalar(
                select(KnowledgeDocument)
                .where(KnowledgeDocument.id == document_id)
                .with_for_update()
            )
            if document is None:
                raise NotFoundError("Document not found")
            if document.revision != expected_revision:
                raise RevisionConflictError("Document revision conflict")
            changed = session.get(KnowledgeDocumentVersion, version_id)
            if changed is None or changed.document_id != document.id:
                raise NotFoundError("Document version not found")
            session.scalar(
                select(Project).where(Project.id == changed.project_id).with_for_update()
            )
            previous_id = document.current_version_id
            if previous_id is None:
                raise ValueError("Document has no current version")
            previous = session.get(KnowledgeDocumentVersion, previous_id)
            if previous is None:
                raise NotFoundError("Previous document version not found")
            previous.version_status = "historical"
            changed.version_status = "current"
            document.current_version_id = changed.id
            document.revision += 1
            affected: list[dict[str, str]] = []
            old_chunks = session.scalars(
                select(KnowledgeChunk.id).where(KnowledgeChunk.version_id == previous.id)
            ).all()
            citations = session.scalars(
                select(Citation).where(Citation.version_id == previous.id)
            ).all()
            for citation in citations:
                affected.append({"type": "citation", "id": str(citation.id), "state": "historical"})
            claim_versions: dict[UUID, ClaimVersion] = {}
            if citations:
                citation_ids = [citation.id for citation in citations]
                links = session.scalars(
                    select(EvidenceLink).where(EvidenceLink.citation_id.in_(citation_ids))
                ).all()
                for link in links:
                    claim_version = session.get(ClaimVersion, link.claim_version_id)
                    if claim_version is not None:
                        claim_version.status = "stale"
                        claim_versions[claim_version.id] = claim_version
            for claim_version in claim_versions.values():
                affected.append(
                    {
                        "type": "claim_version",
                        "id": str(claim_version.id),
                        "state": "stale",
                    }
                )
            snapshots = session.scalars(
                select(RetrievalSnapshot).where(RetrievalSnapshot.project_id == changed.project_id)
            ).all()
            old_chunk_ids = {str(chunk_id) for chunk_id in old_chunks}
            task_ids: set[UUID] = set()
            for snapshot in snapshots:
                if old_chunk_ids & set(snapshot.selected_chunk_ids):
                    task_ids.add(snapshot.task_id)
                    affected.append(
                        {
                            "type": "retrieval_snapshot",
                            "id": str(snapshot.id),
                            "state": "historical",
                        }
                    )
            invalidated_task_ids = invalidate_task_inputs(
                session,
                project_id=changed.project_id,
                task_ids=sorted(task_ids, key=str),
                actor_user_id=actor.id,
                reason=f"KNOWLEDGE_CURRENT_VERSION_CHANGED:{changed.id}",
                now=datetime.now(UTC),
            )
            for task_id in invalidated_task_ids:
                affected.append(
                    {
                        "type": "task",
                        "id": str(task_id),
                        "state": "needs_input",
                    }
                )
            impact = ImpactReview(
                id=uuid4(),
                workspace_id=document.workspace_id,
                library_id=document.library_id,
                document_id=document.id,
                previous_version_id=previous.id,
                changed_version_id=changed.id,
                affected_objects=affected,
                reason=reason,
                state="pending",
                created_at=datetime.now(UTC),
            )
            session.add(impact)
            session.flush()
            session.add(
                ProvenanceEdge(
                    id=uuid4(),
                    workspace_id=document.workspace_id,
                    project_id=changed.project_id,
                    from_type="document_version",
                    from_id=changed.id,
                    to_type="document_version",
                    to_id=previous.id,
                    relation="supersedes",
                    created_at=datetime.now(UTC),
                )
            )
            _append_version_event(session, document, changed, actor.id, reason)
            return ImpactResult(impact.id, affected)

    def record_source_review(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        version_id: UUID,
        scope: str,
        outcome: str,
        evidence_refs: list[str],
    ) -> UUID:
        if outcome not in {"verified_scope", "issues_found", "disputed"}:
            raise ValueError("Unsupported source review outcome")
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            version = session.get(KnowledgeDocumentVersion, version_id)
            if version is None or version.workspace_id != actor.workspace_id:
                raise NotFoundError("Document version not found")
            review = SourceReview(
                id=uuid4(),
                workspace_id=version.workspace_id,
                library_id=version.library_id,
                document_id=version.document_id,
                version_id=version.id,
                reviewer_user_id=actor.id,
                scope=scope,
                outcome=outcome,
                evidence_refs=evidence_refs,
                created_at=datetime.now(UTC),
            )
            session.add(review)
            version.evidence_status = {
                "verified_scope": "reviewed_for_scope",
                "issues_found": "needs_review",
                "disputed": "disputed",
            }[outcome]
            session.flush()
            return review.id


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    return actor


def _project_for_library(session: Session, library_id: UUID) -> UUID:
    project_id = session.scalar(select(Library.project_id).where(Library.id == library_id))
    if project_id is None:
        raise ValueError("Project-scoped knowledge indexing requires a project library")
    return project_id


def _citation_record(citation: Citation) -> CitationRecord:
    return CitationRecord(
        id=citation.id,
        chunk_id=citation.chunk_id,
        version_id=citation.version_id,
        locator=citation.locator,
        quoted_excerpt=citation.quoted_excerpt,
        content_sha256=citation.content_sha256,
        review_status=citation.review_status,
    )


def _claim_record(version: ClaimVersion) -> ClaimRecord:
    return ClaimRecord(
        id=version.claim_id,
        version_id=version.id,
        revision=version.revision,
        statement=version.statement,
        status=version.status,
    )


def _append_version_event(
    session: Session,
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
    actor_user_id: UUID,
    reason: str,
) -> None:
    session.scalar(select(Project).where(Project.id == version.project_id).with_for_update())
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == version.project_id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=document.workspace_id,
            project_id=version.project_id,
            project_seq=(last_sequence or 0) + 1,
            type="knowledge.current_version_changed",
            actor_user_id=actor_user_id,
            object_type="document",
            object_id=document.id,
            object_revision=document.revision,
            payload={"version_id": str(version.id), "reason": reason},
            correlation_id=uuid4(),
            created_at=datetime.now(UTC),
        )
    )
