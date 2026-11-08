from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Citation,
    ExtractionTable,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    Project,
    SourcePassage,
    User,
)


class KnowledgeDocumentSummary(BaseModel):
    id: UUID
    title: str
    document_kind: str
    revision: int
    current_version_id: UUID | None
    version_id: UUID | None
    version_label: str | None
    filename: str | None
    media_type: str | None
    size_bytes: int | None
    ingest_state: str
    evidence_status: str
    version_status: str
    access_state: str
    cloud_policy: str
    ingested_at: datetime | None
    created_at: datetime
    versions_count: int
    citations_count: int


class KnowledgeVersionSummary(BaseModel):
    id: UUID
    version_label: str
    filename: str
    media_type: str
    size_bytes: int
    content_hash: str
    ingest_state: str
    evidence_status: str
    version_status: str
    access_state: str
    cloud_policy: str
    ingested_at: datetime


class KnowledgePassageSummary(BaseModel):
    id: UUID
    version_id: UUID
    locator: dict[str, Any]
    text: str
    content_hash: str
    extraction_quality: dict[str, Any]


class KnowledgeDocumentDetail(BaseModel):
    document: KnowledgeDocumentSummary
    versions: list[KnowledgeVersionSummary]
    passages: list[KnowledgePassageSummary]
    tables_count: int


class KnowledgeBrowser:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_documents(
        self,
        *,
        actor_user_id: UUID,
        project_id: UUID,
        query: str | None = None,
        document_kind: str | None = None,
    ) -> list[KnowledgeDocumentSummary]:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            statement = (
                select(KnowledgeDocument, KnowledgeDocumentVersion)
                .join(
                    KnowledgeDocumentVersion,
                    (KnowledgeDocumentVersion.document_id == KnowledgeDocument.id)
                    & (KnowledgeDocumentVersion.id == KnowledgeDocument.current_version_id),
                )
                .where(
                    KnowledgeDocumentVersion.project_id == project_id,
                    KnowledgeDocumentVersion.access_state == "active",
                )
                .order_by(
                    KnowledgeDocumentVersion.ingested_at.desc(),
                    KnowledgeDocument.title,
                )
            )
            if query and query.strip():
                statement = statement.where(KnowledgeDocument.title.ilike(f"%{query.strip()}%"))
            if document_kind:
                statement = statement.where(KnowledgeDocument.document_kind == document_kind)
            rows = session.execute(statement).all()
            return [self._summary(session, document, version) for document, version in rows]

    def get_document(
        self,
        *,
        actor_user_id: UUID,
        project_id: UUID,
        document_id: UUID,
    ) -> KnowledgeDocumentDetail:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            _project(session, project_id, actor.workspace_id)
            document = session.scalar(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.library_id.in_(
                        select(KnowledgeDocumentVersion.library_id).where(
                            KnowledgeDocumentVersion.project_id == project_id,
                            KnowledgeDocumentVersion.document_id == document_id,
                        )
                    ),
                )
            )
            if document is None:
                raise NotFoundError("Knowledge document not found")
            versions = session.scalars(
                select(KnowledgeDocumentVersion)
                .where(
                    KnowledgeDocumentVersion.document_id == document.id,
                    KnowledgeDocumentVersion.project_id == project_id,
                )
                .order_by(KnowledgeDocumentVersion.ingested_at.desc())
            ).all()
            current = next(
                (item for item in versions if item.id == document.current_version_id),
                None,
            )
            if current is None or current.access_state != "active":
                raise NotFoundError("Current document version not found")
            passages = session.scalars(
                select(SourcePassage)
                .where(SourcePassage.version_id == current.id)
                .order_by(SourcePassage.id)
                .limit(100)
            ).all()
            tables_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(ExtractionTable)
                    .where(ExtractionTable.version_id == current.id)
                )
                or 0
            )
            return KnowledgeDocumentDetail(
                document=self._summary(session, document, current),
                versions=[
                    KnowledgeVersionSummary(
                        id=item.id,
                        version_label=item.version_label,
                        filename=item.filename,
                        media_type=item.media_type,
                        size_bytes=item.size_bytes,
                        content_hash=item.content_hash,
                        ingest_state=item.ingest_state,
                        evidence_status=item.evidence_status,
                        version_status=item.version_status,
                        access_state=item.access_state,
                        cloud_policy=item.cloud_policy,
                        ingested_at=item.ingested_at,
                    )
                    for item in versions
                ],
                passages=[
                    KnowledgePassageSummary(
                        id=item.id,
                        version_id=item.version_id,
                        locator=item.locator,
                        text=item.text,
                        content_hash=item.content_hash,
                        extraction_quality=item.extraction_quality,
                    )
                    for item in passages
                ],
                tables_count=tables_count,
            )

    @staticmethod
    def _summary(
        session: Session,
        document: KnowledgeDocument,
        version: KnowledgeDocumentVersion,
    ) -> KnowledgeDocumentSummary:
        versions_count = int(
            session.scalar(
                select(func.count())
                .select_from(KnowledgeDocumentVersion)
                .where(KnowledgeDocumentVersion.document_id == document.id)
            )
            or 0
        )
        citations_count = int(
            session.scalar(
                select(func.count()).select_from(Citation).where(Citation.version_id == version.id)
            )
            or 0
        )
        return KnowledgeDocumentSummary(
            id=document.id,
            title=document.title,
            document_kind=document.document_kind,
            revision=document.revision,
            current_version_id=document.current_version_id,
            version_id=version.id,
            version_label=version.version_label,
            filename=version.filename,
            media_type=version.media_type,
            size_bytes=version.size_bytes,
            ingest_state=version.ingest_state,
            evidence_status=version.evidence_status,
            version_status=version.version_status,
            access_state=version.access_state,
            cloud_policy=version.cloud_policy,
            ingested_at=version.ingested_at,
            created_at=document.created_at,
            versions_count=versions_count,
            citations_count=citations_count,
        )


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project
