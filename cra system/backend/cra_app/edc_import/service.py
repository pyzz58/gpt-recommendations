"""Authorized EDC Excel preview, mapping and immutable snapshot service."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import DocumentVersion
from cra_app.documents.service import (
    CreateDocumentCommand,
    DocumentService,
    DocumentValidationError,
    validate_upload,
)
from cra_app.edc_import.contracts import (
    ConfirmEDCImportCommand,
    EDCSnapshotLookupCommand,
    EDCWorkbookMapping,
    PreviewEDCImportCommand,
)
from cra_app.edc_import.excel import (
    ExcelImportError,
    WorkbookDraft,
    mapping_missing_required_fields,
    parse_workbook,
    value_type_summary,
)
from cra_app.edc_import.models import (
    EDCLabRecord,
    EDCPreviewCell,
    EDCImportMapping,
    EDCImportPreview,
    EDCPreviewSheet,
    EDCSnapshot,
    EDCSnapshotRow,
)
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.platform.jobs import digest_payload
from cra_app.subjects.models import SubjectIdentifier


class EDCImportError(Exception):
    pass


class EDCNotFound(EDCImportError):
    pass


class EDCValidationError(EDCImportError):
    pass


class EDCConflict(EDCImportError):
    pass


@dataclass(frozen=True)
class PreviewDetail:
    preview: EDCImportPreview
    sheets: tuple[EDCPreviewSheet, ...]
    cells: tuple[EDCPreviewCell, ...]
    mapping_profiles: tuple[EDCImportMapping, ...]
    replayed: bool = False


@dataclass(frozen=True)
class SnapshotDetail:
    snapshot: EDCSnapshot
    rows: tuple[EDCSnapshotRow, ...]
    records: tuple[EDCLabRecord, ...]
    replayed: bool = False


@dataclass(frozen=True)
class UploadOutcome:
    preview_id: uuid.UUID


def _digest_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    result = value.strip()
    return result or None


def _parse_date(value: str | None) -> date | None:
    cleaned = _text(value)
    if cleaned is None:
        return None
    try:
        return date.fromisoformat(cleaned[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(
                cleaned.replace("Z", "+00:00")
            ).date()
        except ValueError:
            return None


def _parse_datetime(
    value: str | None,
    *,
    date_hint: date | None = None,
) -> tuple[datetime | None, str]:
    cleaned = _text(value)
    if cleaned is None:
        return None, "unknown"
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed_time = time.fromisoformat(cleaned)
        except ValueError:
            return None, "unknown"
        if date_hint is None:
            return None, "unknown"
        return datetime.combine(date_hint, parsed_time), "unknown"
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None), "explicit"
    return parsed, "unknown"


def _parse_result(value: str | None) -> tuple[str, str | None, Decimal | None]:
    cleaned = _text(value)
    if cleaned is None:
        return "unknown", None, None
    match = re.fullmatch(
        r"(<=|>=|<|>)?\s*([-+]?\d+(?:\.\d+)?)", cleaned
    )
    if match is None:
        return "text", None, None
    try:
        number = Decimal(match.group(2))
    except InvalidOperation:
        return "text", None, None
    return (
        "bound" if match.group(1) else "exact",
        match.group(1),
        number,
    )


def _normalize_instance_type(value: str | None) -> str:
    cleaned = _text(value)
    if cleaned is None:
        return "unknown"
    normalized = cleaned.casefold()
    if normalized in {"initial", "first", "初检", "首次", "首次检验"}:
        return "initial"
    if normalized in {"repeat", "retest", "复查", "复测", "重测"}:
        return "repeat"
    return re.sub(r"\s+", "_", normalized)[:32]


class EDCImportService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        documents: DocumentService,
        governance: GovernanceService | None = None,
    ):
        self.session_factory = session_factory
        self.documents = documents
        self.governance = governance or GovernanceService(session_factory)

    def _authorize_read(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "read_site", study_id, site_id)

    def _authorize_write(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "write_site", study_id, site_id)

    @staticmethod
    def _scope_fingerprint(
        scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> str:
        return digest_payload(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id),
                "site_id": str(site_id),
            }
        )

    def _reserve(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        command_name: str,
        command,
        request_payload: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": fingerprint,
                "command": command.model_dump(mode="json"),
                "request": request_payload,
            }
        )
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=uuid.uuid4(),
                actor_id=scope.actor_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                scope_fingerprint=fingerprint,
                command_name=command_name,
                idempotency_key=command.idempotency_key,
                request_digest=request_digest,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "actor_id",
                    "tenant_id",
                    "scope_fingerprint",
                    "command_name",
                    "idempotency_key",
                ]
            )
        )
        record = session.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == scope.actor_id,
                IdempotencyRecord.tenant_id == scope.tenant_id,
                IdempotencyRecord.scope_fingerprint == fingerprint,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key == command.idempotency_key,
            )
            .with_for_update()
        )
        if record is None:
            raise RuntimeError("failed to reserve idempotency key")
        if record.request_digest != request_digest:
            raise IdempotencyConflict(
                "idempotency key was already used with different input"
            )
        return record, record.response_resource_id is not None

    @staticmethod
    def _complete(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    def _load_preview(
        self, scope: ScopeContext, preview_id: uuid.UUID
    ) -> EDCImportPreview:
        with self.session_factory() as session:
            preview = session.scalar(
                select(EDCImportPreview).where(
                    EDCImportPreview.id == preview_id,
                    EDCImportPreview.tenant_id == scope.tenant_id,
                )
            )
            if preview is None:
                raise EDCNotFound("EDC import preview was not found")
            return preview

    def _preview_detail_in_session(
        self,
        session: Session,
        preview: EDCImportPreview,
        *,
        replayed: bool = False,
    ) -> PreviewDetail:
        sheets = tuple(
            session.scalars(
                select(EDCPreviewSheet)
                .where(EDCPreviewSheet.preview_id == preview.id)
                .order_by(EDCPreviewSheet.ordinal)
            )
        )
        cells = tuple(
            session.scalars(
                select(EDCPreviewCell)
                .where(EDCPreviewCell.preview_id == preview.id)
                .order_by(
                    EDCPreviewCell.sheet_name,
                    EDCPreviewCell.row_number,
                    EDCPreviewCell.column_number,
                )
            )
        )
        profiles = tuple(
            session.scalars(
                select(EDCImportMapping)
                .where(
                    EDCImportMapping.tenant_id == preview.tenant_id,
                    EDCImportMapping.study_id == preview.study_id,
                    EDCImportMapping.site_id == preview.site_id,
                    EDCImportMapping.header_signature
                    == preview.header_signature,
                )
                .order_by(
                    EDCImportMapping.updated_at.desc(),
                    EDCImportMapping.name,
                )
            )
        )
        return PreviewDetail(
            preview=preview,
            sheets=sheets,
            cells=cells,
            mapping_profiles=profiles,
            replayed=replayed,
        )

    def preview_detail(
        self, scope: ScopeContext, preview_id: uuid.UUID
    ) -> PreviewDetail:
        preview = self._load_preview(scope, preview_id)
        self._authorize_read(scope, preview.study_id, preview.site_id)
        with self.session_factory() as session:
            return self._preview_detail_in_session(session, preview)

    def _find_source_version(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        sha256: str,
    ) -> DocumentVersion | None:
        with self.session_factory() as session:
            return session.scalar(
                select(DocumentVersion)
                .where(
                    DocumentVersion.tenant_id == scope.tenant_id,
                    DocumentVersion.study_id == study_id,
                    DocumentVersion.site_id == site_id,
                    DocumentVersion.sha256 == sha256,
                )
                .order_by(DocumentVersion.uploaded_at)
                .limit(1)
            )

    def _source_version(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: PreviewEDCImportCommand,
        *,
        filename: str,
        content: bytes,
        sha256: str,
    ) -> DocumentVersion:
        existing = self._find_source_version(
            scope, study_id, command.site_id, sha256
        )
        if existing is not None:
            return existing
        uploaded = self.documents.create_document(
            scope,
            study_id,
            CreateDocumentCommand(
                expected_revision=0,
                idempotency_key=("edc-source-" + command.idempotency_key)[:128],
                title=command.title,
                document_type="edc_export",
                purpose="edc_export",
                version_label=f"snapshot-{sha256[:12]}",
                published_on=(
                    command.export_completed_at.date()
                    if command.export_completed_at
                    else None
                ),
                user_starts_on=None,
                user_starts_note=None,
                site_id=command.site_id,
            ),
            filename=filename,
            content=content,
        )
        with self.session_factory() as session:
            version = session.get(DocumentVersion, uploaded.document_version_id)
            if version is None:
                raise EDCNotFound("uploaded EDC source version was not found")
            return version

    def preview_upload(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: PreviewEDCImportCommand,
        *,
        filename: str,
        content: bytes,
    ) -> PreviewDetail:
        self._authorize_write(scope, study_id, command.site_id)
        sha256 = hashlib.sha256(content).hexdigest()
        try:
            validate_upload(
                filename, content, self.documents.max_upload_bytes
            )
            parsed = parse_workbook(
                content,
                filename=filename,
                included_sheets=command.included_sheets or None,
            )
        except (ExcelImportError, DocumentValidationError) as exc:
            raise EDCValidationError(str(exc)) from exc
        profile = None
        if command.mapping_profile_id is not None:
            with self.session_factory() as session:
                profile = session.scalar(
                    select(EDCImportMapping).where(
                        EDCImportMapping.id == command.mapping_profile_id,
                        EDCImportMapping.tenant_id == scope.tenant_id,
                        EDCImportMapping.study_id == study_id,
                        EDCImportMapping.site_id == command.site_id,
                    )
                )
            if profile is None:
                raise EDCNotFound("EDC mapping profile was not found")
            if profile.header_signature != parsed.header_signature:
                raise EDCValidationError(
                    "mapping profile does not match workbook headers"
                )
        source = self._source_version(
            scope,
            study_id,
            command,
            filename=filename,
            content=content,
            sha256=sha256,
        )
        mapping_json = (
            profile.mapping_json
            if profile is not None
            else parsed.suggested_mapping.model_dump(mode="json")
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=command.site_id,
                    command_name="edc.imports.preview",
                    command=command,
                    request_payload={
                        "source_sha256": sha256,
                        "parser_name": parsed.parser_name,
                        "parser_version": parsed.parser_version,
                        "header_signature": parsed.header_signature,
                    },
                )
                if replayed:
                    assert record.response_resource_id is not None
                    preview = session.get(
                        EDCImportPreview, record.response_resource_id
                    )
                    if preview is None:
                        raise EDCNotFound(
                            "replayed EDC preview was not found"
                        )
                    return self._preview_detail_in_session(
                        session, preview, replayed=True
                    )
                preview = EDCImportPreview(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=study_id,
                    site_id=command.site_id,
                    source_document_version_id=source.id,
                    source_sha256=sha256,
                    parser_name=parsed.parser_name,
                    parser_version=parsed.parser_version,
                    header_signature=parsed.header_signature,
                    export_scope=command.export_scope.model_dump(mode="json"),
                    scope_status=command.export_scope.status,
                    export_started_at=command.export_started_at,
                    export_completed_at=command.export_completed_at,
                    included_sheets=list(parsed.included_sheets),
                    suggested_mapping=mapping_json,
                    mapping_profile_id=(
                        profile.id if profile is not None else None
                    ),
                    identity_namespace=command.identity_namespace,
                    state="preview",
                    revision=1,
                    snapshot_id=None,
                    created_by=scope.actor_id,
                    confirmed_by=None,
                    confirmed_at=None,
                )
                session.add(preview)
                session.flush()
                for sheet in parsed.sheets:
                    session.add(
                        EDCPreviewSheet(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=command.site_id,
                            preview_id=preview.id,
                            sheet_name=sheet.name,
                            ordinal=sheet.ordinal,
                            sheet_state=sheet.state,
                            max_row=sheet.max_row,
                            max_column=sheet.max_column,
                            header_row=sheet.header_row,
                            headers=list(sheet.headers),
                            populated_rows=sheet.populated_rows,
                            warnings=list(sheet.warnings),
                        )
                    )
                    for cell in sheet.cells:
                        session.add(
                            EDCPreviewCell(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=study_id,
                                site_id=command.site_id,
                                preview_id=preview.id,
                                sheet_name=sheet.name,
                                row_number=cell.row,
                                column_number=cell.column,
                                coordinate=cell.coordinate,
                                raw_text=cell.raw_text,
                                formula=cell.formula,
                                cached_text=cell.cached_text,
                                cell_type=cell.cell_type,
                                number_format=cell.number_format,
                            )
                        )
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        actor_id=scope.actor_id,
                        action="edc.imports.preview",
                        resource_type="edc_import_preview",
                        resource_id=preview.id,
                        revision_before=None,
                        revision_after=preview.revision,
                        before_state=None,
                        after_state={
                            "source_sha256": sha256,
                            "header_signature": parsed.header_signature,
                            "included_sheets": list(parsed.included_sheets),
                            "populated_cells": parsed.populated_cells,
                            "scope_status": preview.scope_status,
                        },
                        command_name="edc.imports.preview",
                        correlation_id=record.id,
                    )
                )
                session.flush()
                self._complete(record, preview.id, preview.revision)
                return self._preview_detail_in_session(session, preview)

    @staticmethod
    def _rows_from_cells(
        cells: list[EDCPreviewCell],
        sheet: EDCPreviewSheet,
        mapping,
    ) -> list[dict[str, Any]]:
        by_row: dict[int, list[EDCPreviewCell]] = defaultdict(list)
        for cell in cells:
            by_row[cell.row_number].append(cell)
        header_cells = {
            cell.column_number: cell
            for cell in by_row.get(mapping.header_row, [])
        }
        headers = {
            column: _text(cell.display_text if hasattr(cell, "display_text") else cell.cached_text if cell.formula else cell.raw_text)
            for column, cell in header_cells.items()
        }
        if not any(headers.values()):
            raise EDCValidationError(
                f"{sheet.sheet_name}: mapped header row is empty"
            )
        header_columns: dict[str, int] = {}
        for column, header in headers.items():
            if header:
                if header in header_columns:
                    raise EDCValidationError(
                        f"{sheet.sheet_name}: duplicate header {header!r}"
                    )
                header_columns[header] = column
        for field, header in mapping.columns.items():
            if header not in header_columns:
                raise EDCValidationError(
                    f"{sheet.sheet_name}: mapped {field} header "
                    f"{header!r} was not found"
                )
        rows = []
        for row_number in sorted(by_row):
            if row_number < mapping.data_start_row:
                continue
            row_cells = {
                cell.column_number: cell for cell in by_row[row_number]
            }
            if not row_cells:
                continue
            raw_values = {}
            display_values = {}
            formulas = {}
            cached_values = {}
            for header, column in header_columns.items():
                cell = row_cells.get(column)
                raw_values[header] = cell.raw_text if cell else None
                display_values[header] = (
                    cell.display_text
                    if cell is not None and hasattr(cell, "display_text")
                    else (
                        cell.cached_text
                        if cell is not None and cell.formula
                        else cell.raw_text
                        if cell is not None
                        else None
                    )
                )
                if cell is not None and cell.formula:
                    formulas[header] = cell.formula
                    cached_values[header] = cell.cached_text
            if not any(value is not None for value in display_values.values()):
                continue
            rows.append(
                {
                    "sheet": sheet.sheet_name,
                    "row_number": row_number,
                    "row_anchor": (
                        f"{sheet.sheet_name}!A{row_number}:"
                        f"{sheet.max_column}{row_number}"
                    ),
                    "raw_values": raw_values,
                    "display_values": display_values,
                    "formulas": formulas,
                    "cached_values": cached_values,
                }
            )
        return rows

    def _mapping_profile(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        preview: EDCImportPreview,
        command: ConfirmEDCImportCommand,
        mapping_digest: str,
    ) -> EDCImportMapping | None:
        selected = None
        if preview.mapping_profile_id is not None:
            selected = session.get(EDCImportMapping, preview.mapping_profile_id)
            if selected is not None:
                selected_mapping = EDCWorkbookMapping.model_validate(
                    selected.mapping_json
                )
                if _digest_json(selected_mapping.model_dump(mode="json")) != mapping_digest:
                    selected = None
        if command.save_mapping_name is None:
            return selected
        existing = session.scalar(
            select(EDCImportMapping).where(
                EDCImportMapping.tenant_id == scope.tenant_id,
                EDCImportMapping.study_id == preview.study_id,
                EDCImportMapping.site_id == preview.site_id,
                EDCImportMapping.name == command.save_mapping_name,
            )
        )
        if existing is not None:
            if (
                existing.header_signature == preview.header_signature
                and _digest_json(existing.mapping_json) == mapping_digest
            ):
                return existing
            raise EDCConflict(
                "mapping name already exists with another definition"
            )
        profile = EDCImportMapping(
            id=uuid.uuid4(),
            tenant_id=scope.tenant_id,
            study_id=preview.study_id,
            site_id=preview.site_id,
            name=command.save_mapping_name,
            header_signature=preview.header_signature,
            mapping_json=command.mapping.model_dump(mode="json"),
            revision=1,
            created_by=scope.actor_id,
            updated_by=scope.actor_id,
        )
        session.add(profile)
        session.flush()
        return profile

    def _standard_record(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        preview: EDCImportPreview,
        snapshot: EDCSnapshot,
        row: EDCSnapshotRow,
        mapping,
        display: dict[str, Any],
        formulas: dict[str, Any],
    ) -> EDCLabRecord:
        issues: list[str] = []

        def mapped_value(field: str) -> str | None:
            header = mapping.columns.get(field)
            if not header:
                return None
            return _text(display.get(header))

        subject_external_id = mapped_value("subject_external_id")
        analyte = mapped_value("analyte")
        value_raw = mapped_value("value_raw")
        value_header = mapping.columns.get("value_raw")
        if value_header and display.get(value_header) is None:
            issues.append("formula_cache_missing")
            value_raw = None
        if subject_external_id is None:
            issues.append("subject_external_id_missing")
        if analyte is None:
            issues.append("analyte_missing")
        if value_raw is None:
            issues.append("result_missing")

        collected_on = None
        collected_at = None
        timezone_status = "unknown"
        date_value = _parse_date(mapped_value("collected_on"))
        if "collected_at" in mapping.columns:
            collected_at, timezone_status = _parse_datetime(
                mapped_value("collected_at"),
                date_hint=date_value,
            )
            if collected_at is not None:
                collected_on = collected_at.date()
            else:
                collected_on = date_value
        elif "collected_on" in mapping.columns:
            collected_on = date_value
            timezone_status = "date_only"
        if collected_on is None:
            issues.append("collection_time_missing_or_invalid")

        instance_type_raw = mapped_value("instance_type")
        repeat_raw = mapped_value("repeat_instance")
        instance_type = _normalize_instance_type(instance_type_raw)
        if instance_type == "unknown" and repeat_raw:
            instance_type = _normalize_instance_type(repeat_raw)
        if instance_type == "unknown":
            issues.append("initial_repeat_instance_missing")
        repeat_instance = repeat_raw or instance_type

        subject_id = None
        identity_status = "unmatched"
        if subject_external_id:
            identifiers = list(
                session.scalars(
                    select(SubjectIdentifier).where(
                        SubjectIdentifier.tenant_id == scope.tenant_id,
                        SubjectIdentifier.study_id == preview.study_id,
                        SubjectIdentifier.site_id == preview.site_id,
                        SubjectIdentifier.identity_namespace
                        == preview.identity_namespace,
                        SubjectIdentifier.external_id == subject_external_id,
                    )
                )
            )
            if len(identifiers) == 1:
                subject_id = identifiers[0].subject_id
                identity_status = "mapped"
            elif len(identifiers) > 1:
                identity_status = "ambiguous"
                issues.append("subject_identifier_ambiguous")
            else:
                issues.append("subject_not_mapped")

        value_kind, operator, numeric = _parse_result(value_raw)
        validation_status = (
            "ready_for_match"
            if not issues and subject_id is not None
            else "needs_review"
        )
        instance_key = "|".join(
            [
                subject_external_id or "unknown-subject",
                analyte or "unknown-analyte",
                (
                    collected_at.isoformat()
                    if collected_at
                    else collected_on.isoformat()
                    if collected_on
                    else "unknown-time"
                ),
                repeat_instance,
            ]
        )
        record = EDCLabRecord(
            id=uuid.uuid4(),
            tenant_id=scope.tenant_id,
            study_id=preview.study_id,
            site_id=preview.site_id,
            snapshot_id=snapshot.id,
            snapshot_row_id=row.id,
            subject_id=subject_id,
            subject_external_id=subject_external_id,
            visit_key=mapped_value("visit_key"),
            analyte=analyte or "unknown_analyte",
            value_raw=value_raw,
            value_type=value_kind,
            operator=operator,
            numeric_value=numeric,
            unit_raw=mapped_value("unit"),
            collected_on=collected_on,
            collected_at=collected_at,
            precision=(
                mapped_value("precision")
                or (
                    "second"
                    if collected_at and collected_at.second
                    else "minute"
                    if collected_at
                    else "date"
                    if collected_on
                    else "unknown"
                )
            ),
            timezone_status=timezone_status,
            instance_type_raw=instance_type_raw or repeat_raw,
            instance_type=instance_type,
            repeat_instance=repeat_instance,
            instance_key=instance_key,
            report_on=_parse_date(mapped_value("report_on")),
            report_revision=mapped_value("report_revision"),
            specimen=mapped_value("specimen"),
            lower_limit=mapped_value("lower_limit"),
            upper_limit=mapped_value("upper_limit"),
            identity_status=identity_status,
            validation_status=validation_status,
            issues=issues,
            source_ref={
                "document_version_id": str(
                    preview.source_document_version_id
                ),
                "source_sha256": preview.source_sha256,
                "sheet": row.sheet_name,
                "row": row.row_number,
                "anchor": row.row_anchor,
                "formula_headers": sorted(
                    header for header in formulas if formulas[header]
                ),
            },
        )
        session.add(record)
        return record

    def confirm(
        self,
        scope: ScopeContext,
        preview_id: uuid.UUID,
        command: ConfirmEDCImportCommand,
    ) -> SnapshotDetail:
        preview = self._load_preview(scope, preview_id)
        self._authorize_write(scope, preview.study_id, preview.site_id)
        mapping_dump = command.mapping.model_dump(mode="json")
        mapping_digest = _digest_json(mapping_dump)
        scope_override = command.export_scope
        export_scope = (
            scope_override.model_dump(mode="json")
            if scope_override is not None
            else preview.export_scope
        )
        scope_status = (
            scope_override.status
            if scope_override is not None
            else preview.scope_status
        )
        scope_digest = _digest_json(export_scope)
        snapshot_key = hashlib.sha256(
            (
                f"{preview.source_sha256}|{mapping_digest}|"
                f"{scope_digest}|{','.join(sorted(command.mapping.sheets))}"
            ).encode("utf-8")
        ).hexdigest()
        missing = mapping_missing_required_fields(command.mapping)
        if missing:
            raise EDCValidationError(
                "mapping is missing required fields: " + "; ".join(missing)
            )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                preview = session.scalar(
                    select(EDCImportPreview)
                    .where(
                        EDCImportPreview.id == preview_id,
                        EDCImportPreview.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if preview is None:
                    raise EDCNotFound("EDC import preview was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=preview.study_id,
                    site_id=preview.site_id,
                    command_name="edc.imports.confirm",
                    command=command,
                    request_payload={
                        "preview_id": str(preview.id),
                        "snapshot_key": snapshot_key,
                    },
                )
                if replayed:
                    assert record.response_resource_id is not None
                    snapshot = session.get(
                        EDCSnapshot, record.response_resource_id
                    )
                    if snapshot is None:
                        raise EDCNotFound(
                            "replayed EDC snapshot was not found"
                        )
                    return self._snapshot_detail_in_session(
                        session, snapshot, replayed=True
                    )
                if preview.revision != command.expected_revision:
                    raise RevisionConflict(preview.revision)
                existing = session.scalar(
                    select(EDCSnapshot).where(
                        EDCSnapshot.tenant_id == preview.tenant_id,
                        EDCSnapshot.study_id == preview.study_id,
                        EDCSnapshot.site_id == preview.site_id,
                        EDCSnapshot.snapshot_key == snapshot_key,
                    )
                )
                if existing is not None:
                    self._complete(
                        record, existing.id, existing.row_count + 1
                    )
                    return self._snapshot_detail_in_session(
                        session, existing, replayed=True
                    )
                if preview.state != "preview":
                    raise EDCConflict(
                        "only a preview EDC import can be confirmed"
                    )
                profile = self._mapping_profile(
                    session,
                    scope=scope,
                    preview=preview,
                    command=command,
                    mapping_digest=mapping_digest,
                )
                sheets = {
                    sheet.sheet_name: sheet
                    for sheet in session.scalars(
                        select(EDCPreviewSheet)
                        .where(EDCPreviewSheet.preview_id == preview.id)
                        .order_by(EDCPreviewSheet.ordinal)
                    )
                }
                cells_by_sheet: dict[str, list[EDCPreviewCell]] = defaultdict(list)
                for cell in session.scalars(
                    select(EDCPreviewCell)
                    .where(EDCPreviewCell.preview_id == preview.id)
                    .order_by(
                        EDCPreviewCell.sheet_name,
                        EDCPreviewCell.row_number,
                        EDCPreviewCell.column_number,
                    )
                ):
                    cells_by_sheet[cell.sheet_name].append(cell)
                for sheet_name in command.mapping.sheets:
                    if sheet_name not in sheets:
                        raise EDCValidationError(
                            f"mapped sheet {sheet_name!r} is not in the workbook"
                        )
                manifest = []
                parsed_sheets = []
                for sheet_name, sheet in sheets.items():
                    mapping = command.mapping.sheets.get(sheet_name)
                    manifest.append(
                        {
                            "sheet": sheet_name,
                            "state": sheet.sheet_state,
                            "included": bool(mapping and mapping.included),
                            "headers": sheet.headers,
                            "header_row": (
                                mapping.header_row
                                if mapping
                                else sheet.header_row
                            ),
                            "warnings": sheet.warnings,
                        }
                    )
                    if mapping is None or not mapping.included:
                        continue
                    parsed_rows = self._rows_from_cells(
                        cells_by_sheet[sheet_name], sheet, mapping
                    )
                    parsed_sheets.append((sheet, mapping, parsed_rows))
                rows_created = sum(
                    len(parsed_rows)
                    for _, _, parsed_rows in parsed_sheets
                )
                snapshot = EDCSnapshot(
                    id=uuid.uuid4(),
                    tenant_id=preview.tenant_id,
                    study_id=preview.study_id,
                    site_id=preview.site_id,
                    preview_id=preview.id,
                    source_document_version_id=preview.source_document_version_id,
                    mapping_profile_id=profile.id if profile else None,
                    mapping_revision=profile.revision if profile else None,
                    source_sha256=preview.source_sha256,
                    mapping_digest=mapping_digest,
                    scope_digest=scope_digest,
                    snapshot_key=snapshot_key,
                    mapping_json=mapping_dump,
                    export_scope=export_scope,
                    scope_status=scope_status,
                    export_started_at=preview.export_started_at,
                    export_completed_at=preview.export_completed_at,
                    sheet_manifest=manifest,
                    row_count=rows_created,
                    record_count=rows_created,
                    absence_semantics="not_seen_in_export",
                    created_by=scope.actor_id,
                )
                session.add(snapshot)
                session.flush()
                for sheet, mapping, parsed_rows in parsed_sheets:
                    for parsed_row in parsed_rows:
                        row_hash = _digest_json(
                            {
                                "raw": parsed_row["raw_values"],
                                "formulas": parsed_row["formulas"],
                                "cached": parsed_row["cached_values"],
                            }
                        )
                        row = EDCSnapshotRow(
                            id=uuid.uuid4(),
                            tenant_id=preview.tenant_id,
                            study_id=preview.study_id,
                            site_id=preview.site_id,
                            snapshot_id=snapshot.id,
                            sheet_name=parsed_row["sheet"],
                            row_number=parsed_row["row_number"],
                            row_anchor=parsed_row["row_anchor"],
                            raw_values=parsed_row["raw_values"],
                            formulas=parsed_row["formulas"],
                            cached_values=parsed_row["cached_values"],
                            row_hash=row_hash,
                        )
                        session.add(row)
                        session.flush()
                        self._standard_record(
                            session,
                            scope=scope,
                            preview=preview,
                            snapshot=snapshot,
                            row=row,
                            mapping=mapping,
                            display=parsed_row["display_values"],
                            formulas=parsed_row["formulas"],
                        )
                session.flush()
                preview.state = "confirmed"
                preview.revision += 1
                preview.snapshot_id = snapshot.id
                preview.confirmed_by = scope.actor_id
                preview.confirmed_at = datetime.now(UTC)
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=preview.tenant_id,
                        study_id=preview.study_id,
                        site_id=preview.site_id,
                        actor_id=preview.confirmed_by,
                        action="edc.imports.confirm",
                        resource_type="edc_snapshot",
                        resource_id=snapshot.id,
                        revision_before=command.expected_revision,
                        revision_after=snapshot.row_count + 1,
                        before_state=None,
                        after_state={
                            "preview_id": str(preview.id),
                            "snapshot_key": snapshot_key,
                            "rows": snapshot.row_count,
                            "records": snapshot.record_count,
                            "scope_status": snapshot.scope_status,
                            "absence_semantics": snapshot.absence_semantics,
                        },
                        command_name="edc.imports.confirm",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, snapshot.id, snapshot.row_count + 1)
                return self._snapshot_detail_in_session(
                    session, snapshot, replayed=False
                )

    def _snapshot_detail_in_session(
        self,
        session: Session,
        snapshot: EDCSnapshot,
        *,
        replayed: bool = False,
    ) -> SnapshotDetail:
        rows = tuple(
            session.scalars(
                select(EDCSnapshotRow)
                .where(EDCSnapshotRow.snapshot_id == snapshot.id)
                .order_by(
                    EDCSnapshotRow.sheet_name, EDCSnapshotRow.row_number
                )
            )
        )
        records = tuple(
            session.scalars(
                select(EDCLabRecord)
                .where(EDCLabRecord.snapshot_id == snapshot.id)
                .order_by(
                    EDCLabRecord.subject_external_id,
                    EDCLabRecord.collected_on,
                    EDCLabRecord.analyte,
                    EDCLabRecord.instance_key,
                )
            )
        )
        return SnapshotDetail(
            snapshot=snapshot,
            rows=rows,
            records=records,
            replayed=replayed,
        )

    def snapshot_detail(
        self, scope: ScopeContext, snapshot_id: uuid.UUID
    ) -> SnapshotDetail:
        with self.session_factory() as session:
            snapshot = session.scalar(
                select(EDCSnapshot).where(
                    EDCSnapshot.id == snapshot_id,
                    EDCSnapshot.tenant_id == scope.tenant_id,
                )
            )
            if snapshot is None:
                raise EDCNotFound("EDC snapshot was not found")
            self._authorize_read(scope, snapshot.study_id, snapshot.site_id)
            return self._snapshot_detail_in_session(session, snapshot)

    def list_snapshots(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[EDCSnapshot]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(EDCSnapshot)
                    .where(
                        EDCSnapshot.tenant_id == scope.tenant_id,
                        EDCSnapshot.study_id == study_id,
                        EDCSnapshot.site_id == site_id,
                    )
                    .order_by(
                        EDCSnapshot.created_at.desc(), EDCSnapshot.id
                    )
                )
            )

    def lookup(
        self,
        scope: ScopeContext,
        snapshot_id: uuid.UUID,
        command: EDCSnapshotLookupCommand,
    ) -> dict[str, Any]:
        detail = self.snapshot_detail(scope, snapshot_id)
        matches = [
            record
            for record in detail.records
            if record.subject_external_id == command.subject_external_id
            and record.analyte.casefold() == command.analyte.casefold()
            and (
                command.collected_on is None
                or record.collected_on == command.collected_on
            )
            and (
                command.instance_type is None
                or record.instance_type
                == _normalize_instance_type(command.instance_type)
            )
        ]
        return {
            "snapshot_id": str(detail.snapshot.id),
            "status": "seen_in_export" if matches else "not_seen_in_export",
            "scope_status": detail.snapshot.scope_status,
            "absence_semantics": "not_seen_in_export",
            "edc_omission_inferred": False,
            "record_ids": [str(record.id) for record in matches],
        }

    def list_mappings(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        *,
        header_signature: str | None = None,
    ) -> list[EDCImportMapping]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            query = select(EDCImportMapping).where(
                EDCImportMapping.tenant_id == scope.tenant_id,
                EDCImportMapping.study_id == study_id,
                EDCImportMapping.site_id == site_id,
            )
            if header_signature:
                query = query.where(
                    EDCImportMapping.header_signature == header_signature
                )
            return list(
                session.scalars(
                    query.order_by(
                        EDCImportMapping.updated_at.desc(),
                        EDCImportMapping.name,
                    )
                )
            )
