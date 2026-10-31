"""Persistence for site-file directory status and stage checklists."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
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

DIRECTORY_KINDS = ("isf", "tmf", "combined", "other")
DIRECTORY_MODES = ("reference_only", "structured")
APPLICABILITY_STATUSES = ("required", "not_required", "unknown")
ACQUISITION_STATUSES = ("not_seen", "provided", "unknown")
VERIFICATION_STATUSES = ("pending", "qualified", "unknown")
STAGE_KINDS = ("startup", "closeout")
STAGE_ITEM_STATUSES = ("open", "confirmed", "not_applicable", "unknown")


class SiteDirectoryReference(Base):
    __tablename__ = "site_directory_references"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_site_directory_references_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_site_directory_references_version",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "source_document_version_id",
            name="uq_site_directory_reference_version",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_site_directory_references_study_id",
        ),
        CheckConstraint(
            "directory_kind IN ('isf','tmf','combined','other')",
            name="ck_site_directory_references_kind",
        ),
        CheckConstraint(
            "mode IN ('reference_only','structured')",
            name="ck_site_directory_references_mode",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_site_directory_references_revision",
        ),
        Index(
            "ix_site_directory_references_scope",
            "tenant_id",
            "study_id",
            "site_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    directory_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(
        String(24), nullable=False, default="reference_only"
    )
    annotations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
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


class SiteFileItem(Base):
    __tablename__ = "site_file_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "directory_reference_id"],
            [
                "site_directory_references.tenant_id",
                "site_directory_references.study_id",
                "site_directory_references.id",
            ],
            name="fk_site_file_items_directory",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_site_file_items_anchor",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "linked_issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_site_file_items_issue",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "linked_action_id"],
            [
                "issue_actions.tenant_id",
                "issue_actions.study_id",
                "issue_actions.id",
            ],
            name="fk_site_file_items_action",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "directory_reference_id",
            "item_key",
            name="uq_site_file_items_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_site_file_items_study_id",
        ),
        CheckConstraint(
            "applicability_status IN ('required','not_required','unknown')",
            name="ck_site_file_items_applicability",
        ),
        CheckConstraint(
            "acquisition_status IN ('not_seen','provided','unknown')",
            name="ck_site_file_items_acquisition",
        ),
        CheckConstraint(
            "verification_status IN ('pending','qualified','unknown')",
            name="ck_site_file_items_verification",
        ),
        CheckConstraint(
            "verification_status <> 'qualified' "
            "OR acquisition_status = 'provided'",
            name="ck_site_file_items_qualified_requires_file",
        ),
        CheckConstraint("revision >= 1", name="ck_site_file_items_revision"),
        Index(
            "ix_site_file_items_directory_status",
            "directory_reference_id",
            "acquisition_status",
            "verification_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    directory_reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    applicability_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="required"
    )
    acquisition_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_seen"
    )
    verification_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending"
    )
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    linked_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    linked_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    verified_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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


class SiteFileHistory(Base):
    __tablename__ = "site_file_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "directory_reference_id"],
            [
                "site_directory_references.tenant_id",
                "site_directory_references.study_id",
                "site_directory_references.id",
            ],
            name="fk_site_file_history_directory",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_file_item_id"],
            [
                "site_file_items.tenant_id",
                "site_file_items.study_id",
                "site_file_items.id",
            ],
            name="fk_site_file_history_item",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "event_type IN ('directory_reference_created','item_created',"
            "'status_updated')",
            name="ck_site_file_history_event",
        ),
        UniqueConstraint(
            "directory_reference_id",
            "ordinal",
            name="uq_site_file_history_ordinal",
        ),
        Index(
            "ix_site_file_history_reference_order",
            "tenant_id",
            "study_id",
            "directory_reference_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    directory_reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    site_file_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StageChecklist(Base):
    __tablename__ = "stage_checklists"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_stage_checklists_site",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "stage",
            name="uq_stage_checklists_scope_stage",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_stage_checklists_study_id",
        ),
        CheckConstraint(
            "stage IN ('startup','closeout')",
            name="ck_stage_checklists_stage",
        ),
        CheckConstraint("revision >= 1", name="ck_stage_checklists_revision"),
        Index(
            "ix_stage_checklists_scope",
            "tenant_id",
            "study_id",
            "site_id",
            "stage",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
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


class StageChecklistItem(Base):
    __tablename__ = "stage_checklist_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "stage_checklist_id"],
            [
                "stage_checklists.tenant_id",
                "stage_checklists.study_id",
                "stage_checklists.id",
            ],
            name="fk_stage_checklist_items_checklist",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_stage_checklist_items_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_stage_checklist_items_anchor",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "stage_checklist_id",
            "item_key",
            name="uq_stage_checklist_items_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_stage_checklist_items_study_id",
        ),
        CheckConstraint(
            "status IN ('open','confirmed','not_applicable','unknown')",
            name="ck_stage_checklist_items_status",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_stage_checklist_items_revision",
        ),
        Index(
            "ix_stage_checklist_items_status",
            "stage_checklist_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage_checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    source_anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="open"
    )
    completion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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


class StageChecklistHistory(Base):
    __tablename__ = "stage_checklist_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "stage_checklist_id"],
            [
                "stage_checklists.tenant_id",
                "stage_checklists.study_id",
                "stage_checklists.id",
            ],
            name="fk_stage_checklist_history_checklist",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "stage_checklist_item_id"],
            [
                "stage_checklist_items.tenant_id",
                "stage_checklist_items.study_id",
                "stage_checklist_items.id",
            ],
            name="fk_stage_checklist_history_item",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "event_type IN ('checklist_created','item_created',"
            "'status_updated')",
            name="ck_stage_checklist_history_event",
        ),
        UniqueConstraint(
            "stage_checklist_id",
            "ordinal",
            name="uq_stage_checklist_history_ordinal",
        ),
        Index(
            "ix_stage_checklist_history_order",
            "tenant_id",
            "study_id",
            "stage_checklist_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage_checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    stage_checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
