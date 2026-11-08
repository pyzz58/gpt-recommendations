from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    Query,
    Request,
    Response,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.application.knowledge import (
    IndexResult,
    KnowledgeIndexService,
    KnowledgeSearchService,
)
from medical_one_person.application.knowledge_browser import (
    KnowledgeBrowser,
    KnowledgeDocumentDetail,
    KnowledgeDocumentSummary,
)
from medical_one_person.application.knowledge_ingestion import (
    IngestionResult,
    KnowledgeIngestionService,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    IngestJob,
    KnowledgeBlob,
    KnowledgeDocumentVersion,
    Project,
    UploadSession,
    User,
)
from medical_one_person.infrastructure.knowledge.upload import (
    UploadService,
    UploadStatus,
)


class UploadStartRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=300)
    expected_bytes: int = Field(gt=0)
    media_type_hint: str | None = Field(default=None, max_length=200)
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    batch_reserved_bytes: int | None = Field(default=None, gt=0)
    document_id: UUID | None = None


class UploadStatusView(BaseModel):
    session_id: UUID
    filename: str
    expected_bytes: int
    received_bytes: int
    chunk_size: int
    received_ranges: list[tuple[int, int]]
    state: str
    expires_at: datetime


class UploadCommitView(BaseModel):
    session_id: UUID
    blob_id: UUID
    document_id: UUID
    version_id: UUID
    job_id: UUID
    ingest_state: str
    duplicate_document_ids: list[UUID]


class ProcessingView(BaseModel):
    job_id: UUID
    version_id: UUID
    state: str
    passages: int
    tables: int
    indexed_chunks: int
    error_code: str | None


class KnowledgeSearchRequest(BaseModel):
    task_id: UUID
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=12, ge=1, le=40)
    include_historical: bool = False


class SearchHitView(BaseModel):
    chunk_id: UUID
    version_id: UUID
    document_id: UUID
    title: str
    locator: dict[str, Any]
    excerpt: str
    content_hash: str
    extraction_quality: dict[str, Any]
    score: float


class KnowledgeSearchView(BaseModel):
    snapshot_id: UUID
    query: str
    hits: list[SearchHitView]
    permitted_version_ids: list[UUID]


def build_knowledge_router(
    session_factory: sessionmaker[Session],
    store: LocalArtifactStore,
    uploads: UploadService,
    ingestion: KnowledgeIngestionService,
    indexer: KnowledgeIndexService,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/projects/{project_id}/knowledge",
        tags=["knowledge"],
    )
    browser = KnowledgeBrowser(session_factory)
    search = KnowledgeSearchService(session_factory)

    @router.get("/documents", response_model=list[KnowledgeDocumentSummary])
    def list_documents(
        project_id: UUID,
        q: str | None = Query(default=None, max_length=300),
        document_kind: str | None = Query(default=None, max_length=100),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[KnowledgeDocumentSummary]:
        return browser.list_documents(
            actor_user_id=principal.user_id,
            project_id=project_id,
            query=q,
            document_kind=document_kind,
        )

    @router.get(
        "/documents/{document_id}",
        response_model=KnowledgeDocumentDetail,
    )
    def document_detail(
        project_id: UUID,
        document_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> KnowledgeDocumentDetail:
        return browser.get_document(
            actor_user_id=principal.user_id,
            project_id=project_id,
            document_id=document_id,
        )

    @router.post("/uploads", response_model=UploadStatusView, status_code=201)
    def start_upload(
        project_id: UUID,
        request: UploadStartRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> UploadStatusView:
        uploads.ensure_private_library(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )
        status = uploads.create_session(
            project_id=project_id,
            actor_user_id=principal.user_id,
            filename=request.filename,
            expected_bytes=request.expected_bytes,
            media_type_hint=request.media_type_hint,
            expected_sha256=request.expected_sha256,
            batch_reserved_bytes=request.batch_reserved_bytes,
            document_id=request.document_id,
        )
        return _upload_status(status)

    @router.get("/uploads/{upload_id}", response_model=UploadStatusView)
    def upload_status(
        project_id: UUID,
        upload_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> UploadStatusView:
        _verify_upload_project(
            session_factory,
            actor_user_id=principal.user_id,
            project_id=project_id,
            upload_id=upload_id,
        )
        return _upload_status(
            uploads.get_status(
                session_id=upload_id,
                actor_user_id=principal.user_id,
            )
        )

    @router.put("/uploads/{upload_id}/parts/{offset}", response_model=UploadStatusView)
    async def put_upload_part(
        project_id: UUID,
        upload_id: UUID,
        offset: int,
        request: Request,
        part_sha256: str = Header(alias="X-Part-SHA256", min_length=64, max_length=64),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> UploadStatusView:
        _verify_upload_project(
            session_factory,
            actor_user_id=principal.user_id,
            project_id=project_id,
            upload_id=upload_id,
        )
        content = await request.body()
        return _upload_status(
            uploads.put_part(
                session_id=upload_id,
                actor_user_id=principal.user_id,
                offset=offset,
                content=content,
                client_sha256=part_sha256,
            )
        )

    @router.post("/uploads/{upload_id}/commit", response_model=UploadCommitView)
    def commit_upload(
        project_id: UUID,
        upload_id: UUID,
        background_tasks: BackgroundTasks,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> UploadCommitView:
        _verify_upload_project(
            session_factory,
            actor_user_id=principal.user_id,
            project_id=project_id,
            upload_id=upload_id,
        )
        committed = uploads.commit(
            session_id=upload_id,
            actor_user_id=principal.user_id,
        )
        background_tasks.add_task(
            _process_ingest_job,
            session_factory,
            ingestion,
            indexer,
            principal=principal,
            project_id=project_id,
            job_id=committed.job_id,
        )
        return UploadCommitView(
            session_id=committed.session_id,
            blob_id=committed.blob_id,
            document_id=committed.document_id,
            version_id=committed.version_id,
            job_id=committed.job_id,
            ingest_state=committed.ingest_state,
            duplicate_document_ids=committed.duplicate_document_ids,
        )

    @router.post(
        "/ingest-jobs/{job_id}/process",
        response_model=ProcessingView,
    )
    def process_ingest_job(
        project_id: UUID,
        job_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ProcessingView:
        return _process_ingest_job(
            session_factory,
            ingestion,
            indexer,
            principal=principal,
            project_id=project_id,
            job_id=job_id,
        )

    @router.get("/versions/{version_id}/download")
    def download_version(
        project_id: UUID,
        version_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> Response:
        with session_factory.begin() as session:
            actor = _actor(session, principal.user_id)
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            row = session.execute(
                select(KnowledgeDocumentVersion, KnowledgeBlob)
                .join(
                    KnowledgeBlob,
                    KnowledgeBlob.id == KnowledgeDocumentVersion.blob_id,
                )
                .where(
                    KnowledgeDocumentVersion.id == version_id,
                    KnowledgeDocumentVersion.project_id == project_id,
                    KnowledgeDocumentVersion.access_state == "active",
                )
            ).one_or_none()
            if row is None:
                raise NotFoundError("Knowledge document version not found")
            version, blob = row
            content = store.read(blob.object_key, blob.content_hash)
            return Response(
                content=content,
                media_type=version.media_type,
                headers={
                    "Content-Disposition": (
                        "attachment; filename*=UTF-8''" + quote(version.filename, safe="")
                    ),
                    "Cache-Control": "private, no-store",
                },
            )

    @router.post("/search", response_model=KnowledgeSearchView)
    def search_knowledge(
        project_id: UUID,
        request: KnowledgeSearchRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> KnowledgeSearchView:
        result = search.search(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            project_id=project_id,
            task_id=request.task_id,
            query=request.query,
            top_k=request.top_k,
            include_historical=request.include_historical,
        )
        return KnowledgeSearchView(
            snapshot_id=result.snapshot_id,
            query=result.query,
            hits=[
                SearchHitView(
                    chunk_id=hit.chunk_id,
                    version_id=hit.version_id,
                    document_id=hit.document_id,
                    title=hit.title,
                    locator=hit.locator,
                    excerpt=hit.excerpt,
                    content_hash=hit.content_hash,
                    extraction_quality=hit.extraction_quality,
                    score=hit.score,
                )
                for hit in result.hits
            ],
            permitted_version_ids=result.permitted_version_ids,
        )

    return router


def _upload_status(status: UploadStatus) -> UploadStatusView:
    return UploadStatusView(
        session_id=status.session_id,
        filename=status.filename,
        expected_bytes=status.expected_bytes,
        received_bytes=status.received_bytes,
        chunk_size=status.chunk_size,
        received_ranges=status.received_ranges,
        state=status.state,
        expires_at=status.expires_at,
    )


def _verify_upload_project(
    session_factory: sessionmaker[Session],
    *,
    actor_user_id: UUID,
    project_id: UUID,
    upload_id: UUID,
) -> None:
    with session_factory.begin() as session:
        actor = _actor(session, actor_user_id)
        set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
        project = session.get(Project, project_id)
        if project is None or project.workspace_id != actor.workspace_id:
            raise NotFoundError("Project not found")
        upload = session.scalar(
            select(UploadSession.id)
            .where(
                UploadSession.id == upload_id,
                UploadSession.project_id == project_id,
                UploadSession.uploader_user_id == actor.id,
            )
            .limit(1)
        )
        if upload is None:
            raise NotFoundError("Upload session not found")


def _process_ingest_job(
    session_factory: sessionmaker[Session],
    ingestion: KnowledgeIngestionService,
    indexer: KnowledgeIndexService,
    *,
    principal: AuthenticatedPrincipal,
    project_id: UUID,
    job_id: UUID,
) -> ProcessingView:
    with session_factory.begin() as session:
        actor = _actor(session, principal.user_id)
        set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
        job = session.scalar(
            select(IngestJob)
            .join(
                KnowledgeDocumentVersion,
                KnowledgeDocumentVersion.id == IngestJob.version_id,
            )
            .where(
                IngestJob.id == job_id,
                KnowledgeDocumentVersion.project_id == project_id,
            )
        )
        if job is None:
            raise NotFoundError("Ingest job not found")
        if job.state in {"succeeded", "partial"}:
            raise ValueError("Ingest job has already completed")
    result: IngestionResult = ingestion.process(
        workspace_id=principal.workspace_id,
        job_id=job_id,
    )
    indexed: IndexResult | None = None
    if result.state == "indexing":
        indexed = indexer.index_version(
            workspace_id=principal.workspace_id,
            version_id=result.version_id,
        )
    return ProcessingView(
        job_id=result.job_id,
        version_id=result.version_id,
        state=indexed.state if indexed is not None else result.state,
        passages=result.passages,
        tables=result.tables,
        indexed_chunks=indexed.chunks if indexed is not None else 0,
        error_code=result.error_code,
    )


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    return actor
