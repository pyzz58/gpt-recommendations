"""HTTP contracts for EDC XLSX preview, mapping confirmation and snapshots."""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict

from cra_app.edc_import.contracts import (
    ConfirmEDCImportCommand,
    EDCExportScope,
    EDCSnapshotLookupCommand,
    PreviewEDCImportCommand,
)
from cra_app.edc_import.service import (
    EDCImportService,
    PreviewDetail,
    SnapshotDetail,
)
from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity

router = APIRouter(prefix="/api/v1", tags=["edc-import"])


class EDCPreviewCellView(BaseModel):
    coordinate: str
    raw_text: str | None
    formula: str | None
    cached_text: str | None
    cell_type: str
    number_format: str | None


class EDCPreviewRowView(BaseModel):
    row_number: int
    anchor: str
    display_values: dict[str, str | None]
    raw_values: dict[str, str | None]
    formulas: dict[str, str]
    cached_values: dict[str, str | None]


class EDCPreviewSheetView(BaseModel):
    name: str
    ordinal: int
    state: str
    max_row: int
    max_column: int
    header_row: int | None
    headers: list[str]
    populated_rows: int
    previewed_rows: int
    preview_truncated: bool
    value_types: dict[str, int]
    warnings: list[str]
    rows: list[EDCPreviewRowView]
    formula_cells: list[EDCPreviewCellView]


class EDCMappingProfileView(BaseModel):
    id: uuid.UUID
    name: str
    header_signature: str
    mapping: dict[str, Any]
    revision: int
    updated_at: datetime


class EDCPreviewView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    source_document_version_id: uuid.UUID
    source_sha256: str
    parser_name: str
    parser_version: str
    header_signature: str
    export_scope: dict[str, Any]
    scope_status: Literal["declared", "unknown"]
    export_started_at: datetime | None
    export_completed_at: datetime | None
    included_sheets: list[str]
    suggested_mapping: dict[str, Any]
    mapping_profile_id: uuid.UUID | None
    identity_namespace: str
    state: str
    revision: int
    snapshot_id: uuid.UUID | None
    sheets: list[EDCPreviewSheetView]
    mapping_profiles: list[EDCMappingProfileView]
    replayed: bool


class EDCLabRecordView(BaseModel):
    id: uuid.UUID
    snapshot_row_id: uuid.UUID
    subject_id: uuid.UUID | None
    subject_external_id: str | None
    visit_key: str | None
    analyte: str
    value_raw: str | None
    value_type: str
    operator: str | None
    numeric_value: Decimal | None
    unit_raw: str | None
    collected_on: date | None
    collected_at: datetime | None
    precision: str
    timezone_status: str
    instance_type_raw: str | None
    instance_type: str
    repeat_instance: str
    instance_key: str
    report_on: date | None
    specimen: str | None
    lower_limit: str | None
    upper_limit: str | None
    identity_status: str
    validation_status: str
    issues: list[str]
    source_ref: dict[str, Any]


class EDCSnapshotRowView(BaseModel):
    id: uuid.UUID
    sheet_name: str
    row_number: int
    row_anchor: str
    raw_values: dict[str, Any]
    formulas: dict[str, Any]
    cached_values: dict[str, Any]
    row_hash: str


class EDCSnapshotView(BaseModel):
    id: uuid.UUID
    preview_id: uuid.UUID
    source_document_version_id: uuid.UUID
    source_sha256: str
    mapping_profile_id: uuid.UUID | None
    mapping_revision: int | None
    export_scope: dict[str, Any]
    scope_status: Literal["declared", "unknown"]
    export_started_at: datetime | None
    export_completed_at: datetime | None
    sheet_manifest: list[dict[str, Any]]
    row_count: int
    record_count: int
    absence_semantics: Literal["not_seen_in_export"] = "not_seen_in_export"
    rows: list[EDCSnapshotRowView]
    records: list[EDCLabRecordView]
    replayed: bool


class EDCSnapshotLookupView(BaseModel):
    snapshot_id: uuid.UUID
    status: Literal["seen_in_export", "not_seen_in_export"]
    scope_status: Literal["declared", "unknown"]
    absence_semantics: Literal["not_seen_in_export"] = "not_seen_in_export"
    edc_omission_inferred: Literal[False] = False
    record_ids: list[uuid.UUID]


def _service(request: Request) -> EDCImportService:
    return request.app.state.edc_import_service


def _parse_json_form(value: str | None, default: Any) -> Any:
    if value is None or not value.strip():
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "edc_import_json_invalid",
                "message": f"multipart JSON value is invalid: {exc.msg}",
            },
        ) from exc


def _preview_rows(
    detail: PreviewDetail,
    cells_by_sheet: dict[str, list],
    sheet_name: str,
    *,
    limit: int = 250,
) -> tuple[list[EDCPreviewRowView], bool]:
    sheet = next(item for item in detail.sheets if item.sheet_name == sheet_name)
    headers = list(sheet.headers)
    rows: dict[int, dict[int, Any]] = defaultdict(dict)
    for cell in cells_by_sheet[sheet_name]:
        rows[cell.row_number][cell.column_number] = cell
    data = []
    for row_number in sorted(rows):
        if sheet.header_row is not None and row_number <= sheet.header_row:
            continue
        values = rows[row_number]
        display_values = {}
        raw_values = {}
        formulas = {}
        cached_values = {}
        for column, header in enumerate(headers, start=1):
            if not header:
                continue
            cell = values.get(column)
            raw_values[header] = cell.raw_text if cell else None
            display_values[header] = (
                cell.cached_text
                if cell is not None and cell.formula
                else cell.raw_text
                if cell is not None
                else None
            )
            if cell is not None and cell.formula:
                formulas[header] = cell.formula
                cached_values[header] = cell.cached_text
        if not any(value is not None for value in display_values.values()):
            continue
        data.append(
            EDCPreviewRowView(
                row_number=row_number,
                anchor=f"{sheet_name}!A{row_number}:{sheet.max_column}{row_number}",
                display_values=display_values,
                raw_values=raw_values,
                formulas=formulas,
                cached_values=cached_values,
            )
        )
        if len(data) >= limit:
            break
    return data, len(rows) > limit


def _preview_view(detail: PreviewDetail, cells: list) -> EDCPreviewView:
    cells_by_sheet: dict[str, list] = defaultdict(list)
    for cell in cells:
        cells_by_sheet[cell.sheet_name].append(cell)
    sheets = []
    for sheet in detail.sheets:
        rows, truncated = _preview_rows(
            detail, cells_by_sheet, sheet.sheet_name
        )
        sheet_cells = cells_by_sheet[sheet.sheet_name]
        formula_cells = [
            EDCPreviewCellView(
                coordinate=cell.coordinate,
                raw_text=cell.raw_text,
                formula=cell.formula,
                cached_text=cell.cached_text,
                cell_type=cell.cell_type,
                number_format=cell.number_format,
            )
            for cell in sheet_cells
            if cell.formula
        ][:100]
        sheets.append(
            EDCPreviewSheetView(
                name=sheet.sheet_name,
                ordinal=sheet.ordinal,
                state=sheet.sheet_state,
                max_row=sheet.max_row,
                max_column=sheet.max_column,
                header_row=sheet.header_row,
                headers=sheet.headers,
                populated_rows=sheet.populated_rows,
                previewed_rows=len(rows),
                preview_truncated=truncated,
                value_types=dict(
                    sorted(
                        Counter(cell.cell_type for cell in sheet_cells).items()
                    )
                ),
                warnings=sheet.warnings,
                rows=rows,
                formula_cells=formula_cells,
            )
        )
    preview = detail.preview
    return EDCPreviewView(
        id=preview.id,
        source_document_version_id=preview.source_document_version_id,
        source_sha256=preview.source_sha256,
        parser_name=preview.parser_name,
        parser_version=preview.parser_version,
        header_signature=preview.header_signature,
        export_scope=preview.export_scope,
        scope_status=preview.scope_status,
        export_started_at=preview.export_started_at,
        export_completed_at=preview.export_completed_at,
        included_sheets=preview.included_sheets,
        suggested_mapping=preview.suggested_mapping,
        mapping_profile_id=preview.mapping_profile_id,
        identity_namespace=preview.identity_namespace,
        state=preview.state,
        revision=preview.revision,
        snapshot_id=preview.snapshot_id,
        sheets=sheets,
        mapping_profiles=[
            EDCMappingProfileView(
                id=profile.id,
                name=profile.name,
                header_signature=profile.header_signature,
                mapping=profile.mapping_json,
                revision=profile.revision,
                updated_at=profile.updated_at,
            )
            for profile in detail.mapping_profiles
        ],
        replayed=detail.replayed,
    )


def _snapshot_view(detail: SnapshotDetail) -> EDCSnapshotView:
    snapshot = detail.snapshot
    return EDCSnapshotView(
        id=snapshot.id,
        preview_id=snapshot.preview_id,
        source_document_version_id=snapshot.source_document_version_id,
        source_sha256=snapshot.source_sha256,
        mapping_profile_id=snapshot.mapping_profile_id,
        mapping_revision=snapshot.mapping_revision,
        export_scope=snapshot.export_scope,
        scope_status=snapshot.scope_status,
        export_started_at=snapshot.export_started_at,
        export_completed_at=snapshot.export_completed_at,
        sheet_manifest=snapshot.sheet_manifest,
        row_count=snapshot.row_count,
        record_count=snapshot.record_count,
        rows=[
            EDCSnapshotRowView(
                id=row.id,
                sheet_name=row.sheet_name,
                row_number=row.row_number,
                row_anchor=row.row_anchor,
                raw_values=row.raw_values,
                formulas=row.formulas,
                cached_values=row.cached_values,
                row_hash=row.row_hash,
            )
            for row in detail.rows
        ],
        records=[
            EDCLabRecordView(
                id=record.id,
                snapshot_row_id=record.snapshot_row_id,
                subject_id=record.subject_id,
                subject_external_id=record.subject_external_id,
                visit_key=record.visit_key,
                analyte=record.analyte,
                value_raw=record.value_raw,
                value_type=record.value_type,
                operator=record.operator,
                numeric_value=record.numeric_value,
                unit_raw=record.unit_raw,
                collected_on=record.collected_on,
                collected_at=record.collected_at,
                precision=record.precision,
                timezone_status=record.timezone_status,
                instance_type_raw=record.instance_type_raw,
                instance_type=record.instance_type,
                repeat_instance=record.repeat_instance,
                instance_key=record.instance_key,
                report_on=record.report_on,
                specimen=record.specimen,
                lower_limit=record.lower_limit,
                upper_limit=record.upper_limit,
                identity_status=record.identity_status,
                validation_status=record.validation_status,
                issues=record.issues,
                source_ref=record.source_ref,
            )
            for record in detail.records
        ],
        replayed=detail.replayed,
    )


@router.post(
    "/studies/{study_id}/edc-imports/preview",
    response_model=EDCPreviewView,
    dependencies=[Depends(require_csrf)],
)
async def preview_edc_import(
    study_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    file: UploadFile = File(...),
    site_id: uuid.UUID = Form(...),
    title: str = Form(...),
    export_started_at: str | None = Form(default=None),
    export_completed_at: str | None = Form(default=None),
    export_scope_json: str = Form(default="{}"),
    included_sheets_json: str = Form(default="[]"),
    mapping_profile_id: uuid.UUID | None = Form(default=None),
    identity_namespace: str = Form(default="edc"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> EDCPreviewView:
    filename = file.filename or "edc-export.xlsx"
    content = await file.read()
    export_scope = EDCExportScope.model_validate(
        _parse_json_form(export_scope_json, {})
    )
    included_sheets = _parse_json_form(included_sheets_json, [])
    if not isinstance(included_sheets, list) or not all(
        isinstance(item, str) for item in included_sheets
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "edc_import_sheets_invalid",
                "message": "included_sheets_json must be a JSON string array",
            },
        )
    try:
        command = PreviewEDCImportCommand(
            idempotency_key=idempotency_key,
            site_id=site_id,
            title=title,
            export_started_at=export_started_at or None,
            export_completed_at=export_completed_at or None,
            export_scope=export_scope,
            included_sheets=included_sheets,
            mapping_profile_id=mapping_profile_id,
            identity_namespace=identity_namespace,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "edc_import_metadata_invalid",
                "message": str(exc),
            },
        ) from exc
    detail = _service(request).preview_upload(
        scope_from_identity(identity),
        study_id,
        command,
        filename=filename,
        content=content,
    )
    return _preview_view(detail, list(detail.cells))


@router.get(
    "/edc-imports/{preview_id}",
    response_model=EDCPreviewView,
)
def get_edc_preview(
    preview_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> EDCPreviewView:
    detail = _service(request).preview_detail(
        scope_from_identity(identity), preview_id
    )
    return _preview_view(detail, list(detail.cells))


@router.post(
    "/edc-imports/{preview_id}/confirm",
    response_model=EDCSnapshotView,
    dependencies=[Depends(require_csrf)],
)
def confirm_edc_import(
    preview_id: uuid.UUID,
    command: ConfirmEDCImportCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> EDCSnapshotView:
    return _snapshot_view(
        _service(request).confirm(
            scope_from_identity(identity), preview_id, command
        )
    )


@router.get(
    "/edc-snapshots/{snapshot_id}",
    response_model=EDCSnapshotView,
)
def get_edc_snapshot(
    snapshot_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> EDCSnapshotView:
    return _snapshot_view(
        _service(request).snapshot_detail(
            scope_from_identity(identity), snapshot_id
        )
    )


@router.post(
    "/edc-snapshots/{snapshot_id}/lookup",
    response_model=EDCSnapshotLookupView,
)
def lookup_edc_snapshot(
    snapshot_id: uuid.UUID,
    command: EDCSnapshotLookupCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> EDCSnapshotLookupView:
    return EDCSnapshotLookupView.model_validate(
        _service(request).lookup(
            scope_from_identity(identity), snapshot_id, command
        )
    )


@router.get(
    "/studies/{study_id}/edc-import-mappings",
    response_model=list[EDCMappingProfileView],
)
def list_edc_mappings(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    header_signature: str | None = Query(default=None, max_length=64),
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[EDCMappingProfileView]:
    return [
        EDCMappingProfileView(
            id=profile.id,
            name=profile.name,
            header_signature=profile.header_signature,
            mapping=profile.mapping_json,
            revision=profile.revision,
            updated_at=profile.updated_at,
        )
        for profile in _service(request).list_mappings(
            scope_from_identity(identity),
            study_id,
            site_id,
            header_signature=header_signature,
        )
    ]
