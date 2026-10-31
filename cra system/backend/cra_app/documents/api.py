"""Authorized document upload, source access and parse-status endpoints."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict

from cra_app.documents.service import (
    AddVersionCommand,
    CreateDocumentCommand,
    DocumentService,
    UploadResult,
)
from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity

router = APIRouter(prefix="/api/v1", tags=["documents"])


class DocumentView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: str
    study_id: uuid.UUID
    site_id: uuid.UUID | None
    title: str
    document_type: str
    purpose: str
    revision: int
    created_by: str
    created_at: datetime


class VersionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    document_id: uuid.UUID
    version_label: str
    original_filename: str
    media_type: str
    sha256: str
    size_bytes: int
    published_on: date | None
    user_starts_on: date | None
    user_starts_note: str | None
    uploaded_at: datetime
    uploaded_by: str
    parse_status: str
    parser_name: str | None
    parser_version: str | None
    duplicate_of_version_id: uuid.UUID | None


class AnchorView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    document_version_id: uuid.UUID
    anchor_type: str
    logical_node_id: str
    section_path: list[str]
    text: str
    style: dict[str, Any]
    page_number: int | None
    bbox: list[float] | None
    table_index: int | None
    row_index: int | None
    column_index: int | None
    footnote_id: str | None
    ordinal: int


class CoverageView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    document_version_id: uuid.UUID
    unit_key: str
    unit_type: str
    status: str
    reason: str | None
    anchor_id: uuid.UUID | None
    metadata: dict[str, Any]


class JobView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    job_type: str
    input_version_id: uuid.UUID
    status: str
    attempts: int
    max_attempts: int
    error_code: str | None
    error_summary: str | None
    output: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    job_id: uuid.UUID
    revision: int
    replayed: bool
    sha256: str


class RetryResponse(BaseModel):
    job_id: uuid.UUID
    status: str


def _service(request: Request) -> DocumentService:
    return request.app.state.document_service


async def _read_upload(file: UploadFile, request: Request) -> bytes:
    maximum = request.app.state.settings.max_upload_bytes
    content = await file.read(maximum + 1)
    if len(content) > maximum:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "upload_too_large",
                "message": "Uploaded file exceeds the configured limit",
            },
        )
    return content


def _upload_response(result: UploadResult) -> UploadResponse:
    return UploadResponse(
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        job_id=result.job_id,
        revision=result.revision,
        replayed=result.replayed,
        sha256=result.sha256,
    )


@router.post(
    "/studies/{study_id}/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_document(
    study_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    document_type: str = Form(...),
    purpose: str = Form(...),
    version_label: str = Form(..., min_length=1, max_length=64),
    expected_revision: int = Form(0, ge=0),
    site_id: uuid.UUID | None = Form(None),
    published_on: date | None = Form(None),
    user_starts_on: date | None = Form(None),
    user_starts_note: str | None = Form(None, max_length=500),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> UploadResponse:
    content = await _read_upload(file, request)
    command = CreateDocumentCommand(
        expected_revision=expected_revision,
        idempotency_key=idempotency_key,
        site_id=site_id,
        title=title,
        document_type=document_type,
        purpose=purpose,
        version_label=version_label,
        published_on=published_on,
        user_starts_on=user_starts_on,
        user_starts_note=user_starts_note,
    )
    result = _service(request).create_document(
        scope_from_identity(identity),
        study_id,
        command,
        filename=file.filename or "unnamed",
        content=content,
    )
    return _upload_response(result)


@router.post(
    "/documents/{document_id}/versions",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def add_document_version(
    document_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    file: UploadFile = File(...),
    version_label: str = Form(..., min_length=1, max_length=64),
    expected_revision: int = Form(..., ge=1),
    published_on: date | None = Form(None),
    user_starts_on: date | None = Form(None),
    user_starts_note: str | None = Form(None, max_length=500),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> UploadResponse:
    content = await _read_upload(file, request)
    command = AddVersionCommand(
        expected_revision=expected_revision,
        idempotency_key=idempotency_key,
        version_label=version_label,
        published_on=published_on,
        user_starts_on=user_starts_on,
        user_starts_note=user_starts_note,
    )
    result = _service(request).add_version(
        scope_from_identity(identity),
        document_id,
        command,
        filename=file.filename or "unnamed",
        content=content,
    )
    return _upload_response(result)


@router.get(
    "/studies/{study_id}/documents",
    response_model=list[DocumentView],
)
def list_documents(
    study_id: uuid.UUID,
    request: Request,
    site_id: uuid.UUID | None = Query(None),
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[DocumentView]:
    documents = _service(request).list_documents(
        scope_from_identity(identity), study_id, site_id
    )
    return [
        DocumentView(
            id=document.id,
            tenant_id=document.tenant_id,
            study_id=document.study_id,
            site_id=document.site_id,
            title=document.title,
            document_type=document.document_type,
            purpose=document.purpose,
            revision=document.revision,
            created_by=document.created_by,
            created_at=document.created_at,
        )
        for document in documents
    ]


@router.get(
    "/documents/{document_id}/versions",
    response_model=list[VersionView],
)
def list_versions(
    document_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[VersionView]:
    versions = _service(request).list_versions(
        scope_from_identity(identity), document_id
    )
    return [_version_view(version) for version in versions]


@router.get(
    "/document-versions/{version_id}",
    response_model=VersionView,
)
def get_version(
    version_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> VersionView:
    return _version_view(
        _service(request).get_version(
            scope_from_identity(identity), version_id
        )
    )


@router.get(
    "/document-versions/{version_id}/anchors",
    response_model=list[AnchorView],
)
def list_anchors(
    version_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[AnchorView]:
    anchors = _service(request).anchors(
        scope_from_identity(identity), version_id
    )
    return [
        AnchorView(
            id=anchor.id,
            document_version_id=anchor.document_version_id,
            anchor_type=anchor.anchor_type,
            logical_node_id=anchor.logical_node_id,
            section_path=anchor.section_path,
            text=anchor.text,
            style=anchor.style,
            page_number=anchor.page_number,
            bbox=anchor.bbox,
            table_index=anchor.table_index,
            row_index=anchor.row_index,
            column_index=anchor.column_index,
            footnote_id=anchor.footnote_id,
            ordinal=anchor.ordinal,
        )
        for anchor in anchors
    ]


@router.get(
    "/document-versions/{version_id}/coverage",
    response_model=list[CoverageView],
)
def list_coverage(
    version_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[CoverageView]:
    coverage = _service(request).coverage(
        scope_from_identity(identity), version_id
    )
    return [
        CoverageView(
            id=unit.id,
            document_version_id=unit.document_version_id,
            unit_key=unit.unit_key,
            unit_type=unit.unit_type,
            status=unit.status,
            reason=unit.reason,
            anchor_id=unit.anchor_id,
            metadata=unit.metadata_json,
        )
        for unit in coverage
    ]


@router.get(
    "/document-versions/{version_id}/content",
    response_class=Response,
)
def get_content(
    version_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> Response:
    stored = _service(request).read_content(
        scope_from_identity(identity), version_id
    )
    disposition = "inline" if stored.media_type == "application/pdf" else "attachment"
    return Response(
        content=stored.content,
        media_type=stored.media_type,
        headers={
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{quote(stored.filename)}"
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/jobs/{job_id}", response_model=JobView)
def get_job(
    job_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> JobView:
    job = _service(request).job(scope_from_identity(identity), job_id)
    return _job_view(job)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=RetryResponse,
    dependencies=[Depends(require_csrf)],
)
def retry_job(
    job_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> RetryResponse:
    job = _service(request).retry_job(
        scope_from_identity(identity), job_id
    )
    return RetryResponse(job_id=job.id, status=job.status)


def _version_view(version) -> VersionView:
    return VersionView(
        id=version.id,
        document_id=version.document_id,
        version_label=version.version_label,
        original_filename=version.original_filename,
        media_type=version.media_type,
        sha256=version.sha256,
        size_bytes=version.size_bytes,
        published_on=version.published_on,
        user_starts_on=version.user_starts_on,
        user_starts_note=version.user_starts_note,
        uploaded_at=version.uploaded_at,
        uploaded_by=version.uploaded_by,
        parse_status=version.parse_status,
        parser_name=version.parser_name,
        parser_version=version.parser_version,
        duplicate_of_version_id=version.duplicate_of_version_id,
    )


def _job_view(job) -> JobView:
    return JobView(
        id=job.id,
        job_type=job.job_type,
        input_version_id=job.input_version_id,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        error_code=job.error_code,
        error_summary=job.error_summary,
        output=job.output,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
