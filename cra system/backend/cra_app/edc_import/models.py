"""Persistence for reusable mappings, Excel previews and immutable lab snapshots."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cra_app.shared.db import Base


class EDCImportMapping(Base):
    __tablename__ = "edc_import_mappings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_edc_import_mappings_site",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "name",
            name="uq_edc_import_mappings_name",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_edc_import_mappings_study_id",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_edc_import_mappings_revision"
        ),
        Index(
            "ix_edc_import_mappings_signature",
            "tenant_id",
            "study_id",
            "site_id",
            "header_signature",
            "revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    header_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EDCImportPreview(Base):
    __tablename__ = "edc_import_previews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_edc_import_previews_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_edc_import_previews_source",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "mapping_profile_id"],
            [
                "edc_import_mappings.tenant_id",
                "edc_import_mappings.study_id",
                "edc_import_mappings.id",
            ],
            name="fk_edc_import_previews_mapping",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_edc_import_previews_study_id",
        ),
        CheckConstraint(
            "state IN ('preview','confirmed','failed')",
            name="ck_edc_import_previews_state",
        ),
        CheckConstraint(
            "scope_status IN ('declared','unknown')",
            name="ck_edc_import_previews_scope_status",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_edc_import_previews_revision"
        ),
        CheckConstraint(
            "export_completed_at IS NULL OR export_started_at IS NULL "
            "OR export_completed_at >= export_started_at",
            name="ck_edc_import_previews_export_window",
        ),
        Index(
            "ix_edc_import_previews_source",
            "tenant_id",
            "study_id",
            "site_id",
            "source_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    header_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    export_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scope_status: Mapped[str] = mapped_column(String(16), nullable=False)
    export_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    export_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    included_sheets: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    suggested_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    mapping_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    identity_namespace: Mapped[str] = mapped_column(
        String(64), nullable=False, default="edc"
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="preview"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EDCPreviewSheet(Base):
    __tablename__ = "edc_preview_sheets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "preview_id"],
            [
                "edc_import_previews.tenant_id",
                "edc_import_previews.study_id",
                "edc_import_previews.id",
            ],
            name="fk_edc_preview_sheets_preview",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "preview_id", "sheet_name", name="uq_edc_preview_sheets_name"
        ),
        CheckConstraint(
            "sheet_state IN ('visible','hidden','veryHidden')",
            name="ck_edc_preview_sheets_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_state: Mapped[str] = mapped_column(String(16), nullable=False)
    max_row: Mapped[int] = mapped_column(Integer, nullable=False)
    max_column: Mapped[int] = mapped_column(Integer, nullable=False)
    header_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headers: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    populated_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EDCPreviewCell(Base):
    __tablename__ = "edc_preview_cells"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "preview_id"],
            [
                "edc_import_previews.tenant_id",
                "edc_import_previews.study_id",
                "edc_import_previews.id",
            ],
            name="fk_edc_preview_cells_preview",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "preview_id",
            "sheet_name",
            "row_number",
            "column_number",
            name="uq_edc_preview_cell_coordinate",
        ),
        CheckConstraint(
            "row_number >= 1 AND column_number >= 1",
            name="ck_edc_preview_cells_coordinate",
        ),
        Index(
            "ix_edc_preview_cells_row",
            "preview_id",
            "sheet_name",
            "row_number",
            "column_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_number: Mapped[int] = mapped_column(Integer, nullable=False)
    coordinate: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cell_type: Mapped[str] = mapped_column(String(32), nullable=False)
    number_format: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EDCSnapshot(Base):
    __tablename__ = "edc_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_edc_snapshots_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "preview_id"],
            [
                "edc_import_previews.tenant_id",
                "edc_import_previews.study_id",
                "edc_import_previews.id",
            ],
            name="fk_edc_snapshots_preview",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_edc_snapshots_source",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "mapping_profile_id"],
            [
                "edc_import_mappings.tenant_id",
                "edc_import_mappings.study_id",
                "edc_import_mappings.id",
            ],
            name="fk_edc_snapshots_mapping",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "snapshot_key",
            name="uq_edc_snapshots_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_edc_snapshots_study_id",
        ),
        UniqueConstraint("preview_id", name="uq_edc_snapshots_preview"),
        CheckConstraint(
            "scope_status IN ('declared','unknown')",
            name="ck_edc_snapshots_scope_status",
        ),
        CheckConstraint(
            "absence_semantics = 'not_seen_in_export'",
            name="ck_edc_snapshots_absence_semantics",
        ),
        CheckConstraint(
            "row_count >= 0 AND record_count >= 0",
            name="ck_edc_snapshots_counts",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preview_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    mapping_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    mapping_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_key: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    export_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scope_status: Mapped[str] = mapped_column(String(16), nullable=False)
    export_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    export_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sheet_manifest: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    absence_semantics: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_seen_in_export"
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EDCSnapshotRow(Base):
    __tablename__ = "edc_snapshot_rows"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "edc_snapshots.tenant_id",
                "edc_snapshots.study_id",
                "edc_snapshots.id",
            ],
            name="fk_edc_snapshot_rows_snapshot",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "snapshot_id",
            "sheet_name",
            "row_number",
            name="uq_edc_snapshot_row",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_edc_snapshot_rows_study_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_anchor: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    formulas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    cached_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EDCLabRecord(Base):
    __tablename__ = "edc_lab_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "edc_snapshots.tenant_id",
                "edc_snapshots.study_id",
                "edc_snapshots.id",
            ],
            name="fk_edc_lab_records_snapshot",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_row_id"],
            [
                "edc_snapshot_rows.tenant_id",
                "edc_snapshot_rows.study_id",
                "edc_snapshot_rows.id",
            ],
            name="fk_edc_lab_records_row",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_edc_lab_records_subject",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "snapshot_id",
            "snapshot_row_id",
            "analyte",
            "instance_key",
            name="uq_edc_lab_records_instance",
        ),
        CheckConstraint(
            "identity_status IN ('mapped','unmatched','ambiguous')",
            name="ck_edc_lab_records_identity_status",
        ),
        CheckConstraint(
            "validation_status IN ('ready_for_match','needs_review')",
            name="ck_edc_lab_records_validation_status",
        ),
        CheckConstraint(
            "value_type IN ('exact','bound','text','unknown')",
            name="ck_edc_lab_records_value_type",
        ),
        CheckConstraint(
            "timezone_status IN ('unknown','explicit','date_only')",
            name="ck_edc_lab_records_timezone_status",
        ),
        Index(
            "ix_edc_lab_records_match",
            "tenant_id",
            "study_id",
            "site_id",
            "subject_external_id",
            "analyte",
            "collected_on",
            "instance_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    subject_external_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    visit_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    analyte: Mapped[str] = mapped_column(String(255), nullable=False)
    value_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(8), nullable=True)
    numeric_value: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 10), nullable=True
    )
    unit_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    collected_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    precision: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown"
    )
    timezone_status: Mapped[str] = mapped_column(String(16), nullable=False)
    instance_type_raw: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    instance_type: Mapped[str] = mapped_column(String(32), nullable=False)
    repeat_instance: Mapped[str] = mapped_column(String(128), nullable=False)
    instance_key: Mapped[str] = mapped_column(String(512), nullable=False)
    report_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_revision: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    specimen: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lower_limit: Mapped[str | None] = mapped_column(String(128), nullable=True)
    upper_limit: Mapped[str | None] = mapped_column(String(128), nullable=True)
    identity_status: Mapped[str] = mapped_column(String(16), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
