"""Persistence for template mappings, drafts, immutable snapshots and exports."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cra_app.shared.db import Base

OUTPUT_KINDS = ("letter", "report", "track")
OUTPUT_FORMATS = ("docx", "xlsx")
DRAFT_STATUSES = ("draft", "ready")
SNAPSHOT_STATUSES = ("prepared", "issued")
REPORT_EVENT_TYPES = ("sent", "submitted", "archived")


class ReportTemplateVersion(Base):
    __tablename__ = "report_template_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_report_template_versions_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_report_template_versions_document",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "source_document_version_id",
            "output_kind",
            name="uq_report_template_version_kind",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_report_template_versions_study_id",
        ),
        CheckConstraint(
            "output_kind IN ('letter','report','track')",
            name="ck_report_template_versions_kind",
        ),
        CheckConstraint(
            "output_format IN ('docx','xlsx')",
            name="ck_report_template_versions_format",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_report_template_versions_revision",
        ),
        Index(
            "ix_report_template_versions_scope",
            "tenant_id",
            "study_id",
            "site_id",
            "output_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    output_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    output_format: Mapped[str] = mapped_column(String(16), nullable=False)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    supported_fields: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
    required_variables: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
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


class ReportDraft(Base):
    __tablename__ = "report_drafts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_report_drafts_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_report_drafts_visit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "template_version_id"],
            [
                "report_template_versions.tenant_id",
                "report_template_versions.study_id",
                "report_template_versions.id",
            ],
            name="fk_report_drafts_template",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_report_drafts_study_id",
        ),
        CheckConstraint(
            "output_kind IN ('letter','report')",
            name="ck_report_drafts_kind",
        ),
        CheckConstraint(
            "status IN ('draft','ready')",
            name="ck_report_drafts_status",
        ),
        CheckConstraint("revision >= 1", name="ck_report_drafts_revision"),
        Index(
            "ix_report_drafts_visit",
            "tenant_id",
            "study_id",
            "site_id",
            "monitoring_visit_id",
            "generated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    monitoring_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    output_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_refs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    unknowns: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    not_checked: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    missing_fields: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
    user_text: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReportDraftHistory(Base):
    __tablename__ = "report_draft_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "draft_id"],
            ["report_drafts.tenant_id", "report_drafts.study_id", "report_drafts.id"],
            name="fk_report_draft_history_draft",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "event_type IN ('generated','text_updated','marked_ready')",
            name="ck_report_draft_history_event",
        ),
        UniqueConstraint(
            "draft_id",
            "ordinal",
            name="uq_report_draft_history_ordinal",
        ),
        Index(
            "ix_report_draft_history_time",
            "tenant_id",
            "study_id",
            "draft_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "draft_id"],
            ["report_drafts.tenant_id", "report_drafts.study_id", "report_drafts.id"],
            name="fk_report_snapshots_draft",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "template_version_id"],
            [
                "report_template_versions.tenant_id",
                "report_template_versions.study_id",
                "report_template_versions.id",
            ],
            name="fk_report_snapshots_template",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "draft_id",
            "snapshot_number",
            name="uq_report_snapshots_number",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_report_snapshots_study_id",
        ),
        CheckConstraint(
            "status IN ('prepared','issued')",
            name="ck_report_snapshots_status",
        ),
        CheckConstraint(
            "status <> 'issued' OR "
            "(issued_by IS NOT NULL AND issued_at IS NOT NULL "
            "AND user_statement IS NOT NULL AND btrim(user_statement) <> '')",
            name="ck_report_snapshots_issued_evidence",
        ),
        CheckConstraint(
            "snapshot_number >= 1",
            name="ck_report_snapshots_number_positive",
        ),
        Index(
            "ix_report_snapshots_draft",
            "tenant_id",
            "study_id",
            "draft_id",
            "snapshot_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    snapshot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_refs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    missing_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    unknown_acknowledged: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    issued_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReportExport(Base):
    __tablename__ = "report_exports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "report_snapshots.tenant_id",
                "report_snapshots.study_id",
                "report_snapshots.id",
            ],
            name="fk_report_exports_snapshot",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "template_version_id"],
            [
                "report_template_versions.tenant_id",
                "report_template_versions.study_id",
                "report_template_versions.id",
            ],
            name="fk_report_exports_template",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("storage_key", name="uq_report_exports_storage_key"),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_report_exports_study_id",
        ),
        CheckConstraint(
            "output_format IN ('docx','xlsx')",
            name="ck_report_exports_format",
        ),
        CheckConstraint("size_bytes > 0", name="ck_report_exports_size"),
        Index(
            "ix_report_exports_snapshot",
            "tenant_id",
            "study_id",
            "snapshot_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    output_format: Mapped[str] = mapped_column(String(16), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    generated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReportEvent(Base):
    __tablename__ = "report_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "report_snapshots.tenant_id",
                "report_snapshots.study_id",
                "report_snapshots.id",
            ],
            name="fk_report_events_snapshot",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "event_type IN ('sent','submitted','archived')",
            name="ck_report_events_type",
        ),
        Index(
            "ix_report_events_snapshot",
            "tenant_id",
            "study_id",
            "snapshot_id",
            "occurred_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_statement: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
