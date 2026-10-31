"""Persistence model for private project documents and source anchors."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
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

DOCUMENT_PURPOSES = (
    "rule",
    "fact",
    "edc_export",
    "carryover_report",
    "track",
    "directory",
    "template",
    "other",
)
DOCUMENT_TYPES = (
    "protocol",
    "ib",
    "sop",
    "monitoring_plan",
    "qa",
    "manual",
    "report",
    "track",
    "edc_export",
    "directory",
    "template",
    "text",
    "other",
)


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_source_documents_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_source_documents_site_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_source_documents_study_id"
        ),
        CheckConstraint(
            "purpose IN ('rule','fact','edc_export','carryover_report','track',"
            "'directory','template','other')",
            name="ck_source_documents_purpose",
        ),
        CheckConstraint(
            "document_type IN ('protocol','ib','sop','monitoring_plan','qa',"
            "'manual','report','track','edc_export','directory','template',"
            "'text','other')",
            name="ck_source_documents_type",
        ),
        CheckConstraint("revision >= 1", name="ck_source_documents_revision"),
        Index(
            "ix_source_documents_scope",
            "tenant_id",
            "study_id",
            "site_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
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


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_id"],
            [
                "source_documents.tenant_id",
                "source_documents.study_id",
                "source_documents.id",
            ],
            name="fk_document_versions_document_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "duplicate_of_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_document_versions_duplicate_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_document_versions_study_id",
        ),
        UniqueConstraint(
            "document_id",
            "version_label",
            name="uq_document_versions_label",
        ),
        UniqueConstraint("storage_key", name="uq_document_versions_storage_key"),
        CheckConstraint("revision >= 1", name="ck_document_versions_revision"),
        CheckConstraint("size_bytes > 0", name="ck_document_versions_size"),
        CheckConstraint(
            "parse_status IN ('pending','running','completed','partial','failed')",
            name="ck_document_versions_parse_status",
        ),
        Index(
            "ix_document_versions_scope_hash",
            "tenant_id",
            "study_id",
            "sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    user_starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    user_starts_note: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    uploaded_by: Mapped[str] = mapped_column(String(128), nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending"
    )
    parser_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duplicate_of_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class SourceAnchor(Base):
    __tablename__ = "source_anchors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_source_anchors_version_scope",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "document_version_id",
            "logical_node_id",
            name="uq_source_anchors_node",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_source_anchors_scope_id",
        ),
        CheckConstraint(
            "anchor_type IN ('paragraph','table_cell','footnote',"
            "'pdf_text','plain_text','header','footer','media')",
            name="ck_source_anchors_type",
        ),
        Index(
            "ix_source_anchors_version_order",
            "document_version_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    anchor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    logical_node_id: Mapped[str] = mapped_column(String(512), nullable=False)
    section_path: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    table_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    footnote_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ParseCoverage(Base):
    __tablename__ = "parse_coverage"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_parse_coverage_version_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["anchor_id"],
            ["source_anchors.id"],
            name="fk_parse_coverage_anchor",
            ondelete="SET NULL",
        ),
        UniqueConstraint(
            "document_version_id",
            "unit_key",
            name="uq_parse_coverage_unit",
        ),
        CheckConstraint(
            "status IN ('processed','background','not_applicable',"
            "'unsupported','failed','pending')",
            name="ck_parse_coverage_status",
        ),
        Index(
            "ix_parse_coverage_version_status",
            "document_version_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    unit_key: Mapped[str] = mapped_column(String(512), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
