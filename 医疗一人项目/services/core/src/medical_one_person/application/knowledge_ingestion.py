from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.domain.knowledge.documents import (
    DocumentParseError,
    IngestState,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    DocumentExtraction,
    ExtractionTable,
    IngestJob,
    KnowledgeBlob,
    KnowledgeDocumentVersion,
    SourcePassage,
)
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser


@dataclass(frozen=True)
class IngestionResult:
    job_id: UUID
    version_id: UUID
    state: str
    passages: int
    tables: int
    error_code: str | None


class KnowledgeIngestionService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: LocalArtifactStore,
        parser: DocumentParser,
    ) -> None:
        self._session_factory = session_factory
        self._store = store
        self._parser = parser

    def process(self, *, workspace_id: UUID, job_id: UUID) -> IngestionResult:
        job, version, object_key, filename, media_type = self._start(workspace_id, job_id)
        try:
            parsed = self._parser.parse(
                self._store.trusted_path(object_key),
                filename=filename,
                media_type=media_type,
            )
        except DocumentParseError as exc:
            return self._fail(workspace_id, job_id, exc.code)
        except Exception:
            return self._fail(workspace_id, job_id, "EXTRACTION_FAILED")

        final_state = IngestState.INDEXING if parsed.state == IngestState.READY else parsed.state
        findings = list(parsed.quality_findings)
        if final_state == IngestState.INDEXING:
            findings.append(
                {
                    "code": "INDEX_NOT_BUILT",
                    "message": "Extraction completed; lexical index construction begins in W08.",
                }
            )
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            stored_job = session.get(IngestJob, job.id)
            stored_version = session.get(KnowledgeDocumentVersion, version.id)
            if stored_job is None or stored_version is None:
                raise RuntimeError("Ingestion records disappeared")
            config_hash = hashlib.sha256(
                json.dumps(
                    {"extractor": parsed.extractor_version, "config": "v1"},
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            extraction = session.scalar(
                select(DocumentExtraction).where(
                    DocumentExtraction.version_id == stored_version.id,
                    DocumentExtraction.extractor_version == parsed.extractor_version,
                    DocumentExtraction.config_hash == config_hash,
                )
            )
            if extraction is None:
                extraction = DocumentExtraction(
                    id=uuid4(),
                    workspace_id=stored_version.workspace_id,
                    library_id=stored_version.library_id,
                    document_id=stored_version.document_id,
                    version_id=stored_version.id,
                    extractor_version=parsed.extractor_version,
                    config_hash=config_hash,
                    state=("partial" if final_state == IngestState.PARTIAL else "succeeded"),
                    coverage=parsed.coverage,
                    quality_findings=findings,
                    started_at=now,
                    finished_at=now,
                )
                session.add(extraction)
                session.flush()
            for passage in parsed.passages:
                session.add(
                    SourcePassage(
                        id=uuid4(),
                        workspace_id=stored_version.workspace_id,
                        extraction_id=extraction.id,
                        version_id=stored_version.id,
                        locator=passage.locator,
                        text=passage.text,
                        content_hash=hashlib.sha256(passage.text.encode()).hexdigest(),
                        extraction_quality=passage.quality,
                    )
                )
            for table in parsed.tables:
                encoded = json.dumps(table.data, ensure_ascii=False, sort_keys=True).encode("utf-8")
                session.add(
                    ExtractionTable(
                        id=uuid4(),
                        workspace_id=stored_version.workspace_id,
                        extraction_id=extraction.id,
                        version_id=stored_version.id,
                        locator=table.locator,
                        table_data=table.data,
                        content_hash=hashlib.sha256(encoded).hexdigest(),
                    )
                )
            stored_version.ingest_state = final_state
            stored_job.state = "partial" if final_state == IngestState.PARTIAL else "succeeded"
            stored_job.finished_at = now
            stored_job.error_code = None
            session.flush()
        return IngestionResult(
            job_id=job.id,
            version_id=version.id,
            state=final_state,
            passages=len(parsed.passages),
            tables=len(parsed.tables),
            error_code=None,
        )

    def _start(
        self, workspace_id: UUID, job_id: UUID
    ) -> tuple[IngestJob, KnowledgeDocumentVersion, str, str, str]:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            job = session.scalar(
                select(IngestJob)
                .where(IngestJob.id == job_id, IngestJob.workspace_id == workspace_id)
                .with_for_update()
            )
            if job is None:
                raise LookupError("Ingest job not found")
            version = session.scalar(
                select(KnowledgeDocumentVersion)
                .where(KnowledgeDocumentVersion.id == job.version_id)
                .with_for_update()
            )
            if version is None:
                raise LookupError("Document version not found")
            if job.state in {"succeeded", "partial"}:
                raise RuntimeError("Ingest job was already completed")
            blob = session.get(KnowledgeBlob, version.blob_id)
            if blob is None:
                raise LookupError("Original blob not found")
            job.state = "running"
            job.attempts += 1
            job.started_at = now
            version.ingest_state = IngestState.EXTRACTING
            return (
                job,
                version,
                blob.object_key,
                version.filename,
                version.media_type,
            )

    def _fail(self, workspace_id: UUID, job_id: UUID, error_code: str) -> IngestionResult:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            job = session.get(IngestJob, job_id)
            if job is None:
                raise LookupError("Ingest job not found")
            version = session.get(KnowledgeDocumentVersion, job.version_id)
            if version is None:
                raise LookupError("Document version not found")
            job.state = "failed"
            job.error_code = error_code
            job.finished_at = now
            version.ingest_state = IngestState.FAILED
            return IngestionResult(
                job_id=job.id,
                version_id=version.id,
                state=IngestState.FAILED,
                passages=0,
                tables=0,
                error_code=error_code,
            )
