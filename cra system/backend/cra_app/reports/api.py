"""HTTP contracts for letters, reports, immutable snapshots and exports."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict

from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.reports.service import (
    CreateDraftCommand,
    CreateExportCommand,
    CreateSnapshotCommand,
    CreateTemplateVersionCommand,
    DraftDetail,
    ExportDetail,
    ReportService,
    SnapshotDetail,
    TemplateVersionDetail,
    UpdateDraftTextCommand,
    RecordReportEventCommand,
)

router = APIRouter(prefix="/api/v1", tags=["reports"])


class TemplateVersionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    source_document_version_id: uuid.UUID
    title: str
    output_kind: str
    output_format: str
    mapping: dict[str, Any]
    supported_fields: list[str]
    required_variables: list[str]
    revision: int
    created_by: str
    created_at: datetime


class DraftHistoryView(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_id: str
    ordinal: int
    details: dict[str, Any]
    occurred_at: datetime


class ReportDraftView(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    monitoring_visit_id: uuid.UUID
    template_version_id: uuid.UUID
    output_kind: str
    title: str
    content: dict[str, Any]
    input_refs: dict[str, Any]
    unknowns: list[dict[str, Any]]
    not_checked: list[dict[str, Any]]
    missing_fields: list[str]
    user_text: dict[str, str]
    status: str
    revision: int
    generated_by: str
    generated_at: datetime
    updated_by: str
    updated_at: datetime
    history: list[DraftHistoryView]


class ReportEventView(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_id: str
    user_statement: str
    occurred_at: datetime


class ReportExportView(BaseModel):
    id: uuid.UUID
    snapshot_id: uuid.UUID
    template_version_id: uuid.UUID
    output_format: str
    filename: str
    sha256: str
    size_bytes: int
    row_refs: list[dict[str, Any]]
    generated_by: str
    created_at: datetime
    content_url: str
    actual_send_status: Literal["not_sent"] = "not_sent"


class ReportSnapshotView(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    draft_revision: int
    template_version_id: uuid.UUID
    snapshot_number: int
    status: str
    content: dict[str, Any]
    input_refs: dict[str, Any]
    content_hash: str
    missing_fields: list[str]
    unknown_acknowledged: bool
    issued_by: str | None
    issued_at: datetime | None
    user_statement: str | None
    created_by: str
    created_at: datetime
    exports: list[ReportExportView]
    events: list[ReportEventView]


def _service(request: Request) -> ReportService:
    return request.app.state.report_service


def _template_view(detail: TemplateVersionDetail) -> TemplateVersionView:
    item = detail.template
    return TemplateVersionView(
        id=item.id,
        study_id=item.study_id,
        site_id=item.site_id,
        source_document_version_id=item.source_document_version_id,
        title=item.title,
        output_kind=item.output_kind,
        output_format=item.output_format,
        mapping=item.mapping_json,
        supported_fields=item.supported_fields,
        required_variables=item.required_variables,
        revision=item.revision,
        created_by=item.created_by,
        created_at=item.created_at,
    )


def _draft_view(detail: DraftDetail) -> ReportDraftView:
    draft = detail.draft
    return ReportDraftView(
        id=draft.id,
        study_id=draft.study_id,
        site_id=draft.site_id,
        monitoring_visit_id=draft.monitoring_visit_id,
        template_version_id=draft.template_version_id,
        output_kind=draft.output_kind,
        title=draft.title,
        content=draft.content_json,
        input_refs=draft.input_refs,
        unknowns=draft.unknowns,
        not_checked=draft.not_checked,
        missing_fields=draft.missing_fields,
        user_text=draft.user_text,
        status=draft.status,
        revision=draft.revision,
        generated_by=draft.generated_by,
        generated_at=draft.generated_at,
        updated_by=draft.updated_by,
        updated_at=draft.updated_at,
        history=[
            DraftHistoryView(
                id=item.id,
                event_type=item.event_type,
                actor_id=item.actor_id,
                ordinal=item.ordinal,
                details=item.details,
                occurred_at=item.occurred_at,
            )
            for item in detail.history
        ],
    )


def _export_view(item: Any) -> ReportExportView:
    return ReportExportView(
        id=item.id,
        snapshot_id=item.snapshot_id,
        template_version_id=item.template_version_id,
        output_format=item.output_format,
        filename=item.filename,
        sha256=item.sha256,
        size_bytes=item.size_bytes,
        row_refs=item.row_refs,
        generated_by=item.generated_by,
        created_at=item.created_at,
        content_url=f"/api/v1/report-exports/{item.id}/content",
    )


def _snapshot_view(detail: SnapshotDetail) -> ReportSnapshotView:
    item = detail.snapshot
    return ReportSnapshotView(
        id=item.id,
        draft_id=item.draft_id,
        draft_revision=item.draft_revision,
        template_version_id=item.template_version_id,
        snapshot_number=item.snapshot_number,
        status=item.status,
        content=item.content_json,
        input_refs=item.input_refs,
        content_hash=item.content_hash,
        missing_fields=item.missing_fields,
        unknown_acknowledged=item.unknown_acknowledged,
        issued_by=item.issued_by,
        issued_at=item.issued_at,
        user_statement=item.user_statement,
        created_by=item.created_by,
        created_at=item.created_at,
        exports=[_export_view(export) for export in detail.exports],
        events=[
            ReportEventView(
                id=event.id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                user_statement=event.user_statement,
                occurred_at=event.occurred_at,
            )
            for event in detail.events
        ],
    )


@router.post(
    "/template-versions",
    response_model=TemplateVersionView,
    dependencies=[Depends(require_csrf)],
)
def create_template_version(
    command: CreateTemplateVersionCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> TemplateVersionView:
    return _template_view(
        _service(request).create_template_version(
            scope_from_identity(identity), command
        )
    )


@router.get(
    "/template-versions/{template_id}",
    response_model=TemplateVersionView,
)
def get_template_version(
    template_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> TemplateVersionView:
    return _template_view(
        _service(request).template_version(
            scope_from_identity(identity), template_id
        )
    )


@router.get(
    "/template-versions",
    response_model=list[TemplateVersionView],
)
def list_template_versions(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[TemplateVersionView]:
    return [
        _template_view(item)
        for item in _service(request).list_template_versions(
            scope_from_identity(identity), study_id, site_id
        )
    ]


@router.post(
    "/letters/draft",
    response_model=ReportDraftView,
    dependencies=[Depends(require_csrf)],
)
def create_letter_draft(
    command: CreateDraftCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportDraftView:
    return _draft_view(
        _service(request).create_draft(
            scope_from_identity(identity),
            command,
            output_kind="letter",
        )
    )


@router.post(
    "/reports/draft",
    response_model=ReportDraftView,
    dependencies=[Depends(require_csrf)],
)
def create_report_draft(
    command: CreateDraftCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportDraftView:
    return _draft_view(
        _service(request).create_draft(
            scope_from_identity(identity),
            command,
            output_kind="report",
        )
    )


@router.get(
    "/report-drafts/{draft_id}",
    response_model=ReportDraftView,
)
def get_report_draft(
    draft_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportDraftView:
    return _draft_view(
        _service(request).draft(scope_from_identity(identity), draft_id)
    )


@router.get(
    "/studies/{study_id}/report-drafts",
    response_model=list[ReportDraftView],
)
def list_report_drafts(
    request: Request,
    study_id: uuid.UUID,
    site_id: uuid.UUID = Query(...),
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[ReportDraftView]:
    return [
        _draft_view(item)
        for item in _service(request).list_drafts(
            scope_from_identity(identity), study_id, site_id
        )
    ]


@router.post(
    "/report-drafts/{draft_id}/text",
    response_model=ReportDraftView,
    dependencies=[Depends(require_csrf)],
)
def update_report_draft_text(
    draft_id: uuid.UUID,
    command: UpdateDraftTextCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportDraftView:
    return _draft_view(
        _service(request).update_text(
            scope_from_identity(identity), draft_id, command
        )
    )


@router.post(
    "/reports/{draft_id}/snapshot",
    response_model=ReportSnapshotView,
    dependencies=[Depends(require_csrf)],
)
def create_report_snapshot(
    draft_id: uuid.UUID,
    command: CreateSnapshotCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportSnapshotView:
    return _snapshot_view(
        _service(request).create_snapshot(
            scope_from_identity(identity), draft_id, command
        )
    )


@router.get(
    "/report-snapshots/{snapshot_id}",
    response_model=ReportSnapshotView,
)
def get_report_snapshot(
    snapshot_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportSnapshotView:
    return _snapshot_view(
        _service(request).snapshot(
            scope_from_identity(identity), snapshot_id
        )
    )


@router.post(
    "/exports",
    response_model=ReportExportView,
    dependencies=[Depends(require_csrf)],
)
def create_report_export(
    command: CreateExportCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportExportView:
    detail: ExportDetail = _service(request).create_export(
        scope_from_identity(identity), command
    )
    return _export_view(detail.export)


@router.get(
    "/report-exports/{export_id}",
    response_model=ReportExportView,
)
def get_report_export(
    export_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportExportView:
    return _export_view(
        _service(request).export(
            scope_from_identity(identity), export_id
        ).export
    )


@router.get("/report-exports/{export_id}/content")
def download_report_export(
    export_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> Response:
    content, media_type, filename = _service(request).export_content(
        scope_from_identity(identity), export_id
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/report-snapshots/{snapshot_id}/events",
    response_model=ReportSnapshotView,
    dependencies=[Depends(require_csrf)],
)
def record_report_event(
    snapshot_id: uuid.UUID,
    command: RecordReportEventCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReportSnapshotView:
    return _snapshot_view(
        _service(request).record_event(
            scope_from_identity(identity), snapshot_id, command
        )
    )
