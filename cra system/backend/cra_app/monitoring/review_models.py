"""Template-driven monitoring review configuration and visit records."""
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

REVIEW_ITEM_STATUSES = (
    "not_checked",
    "checked",
    "needs_clarification",
    "not_applicable",
    "skipped",
)


class ReviewTemplateVersion(Base):
    __tablename__ = "review_template_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_review_template_versions_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_review_template_versions_document",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "source_document_version_id",
            name="uq_review_template_versions_source",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_review_template_versions_study_id",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_review_template_versions_revision",
        ),
        Index(
            "ix_review_template_versions_scope",
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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    structure_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewTemplateItem(Base):
    __tablename__ = "review_template_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "review_template_version_id"],
            [
                "review_template_versions.tenant_id",
                "review_template_versions.study_id",
                "review_template_versions.id",
            ],
            name="fk_review_template_items_template",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "review_template_version_id",
            "item_key",
            name="uq_review_template_items_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_review_template_items_study_id",
        ),
        CheckConstraint(
            "section_order >= 0 AND question_order >= 0",
            name="ck_review_template_items_order",
        ),
        Index(
            "ix_review_template_items_template_order",
            "review_template_version_id",
            "section_order",
            "question_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    review_template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    item_key: Mapped[str] = mapped_column(String(96), nullable=False)
    section_key: Mapped[str] = mapped_column(String(96), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str] = mapped_column(String(255), nullable=False)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(String(512), nullable=False)
    source_quote: Mapped[str] = mapped_column(Text, nullable=False)
    report_locator: Mapped[str] = mapped_column(String(512), nullable=False)
    applicability: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MonitoringReviewBinding(Base):
    __tablename__ = "monitoring_review_bindings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_monitoring_review_bindings_visit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "review_template_version_id"],
            [
                "review_template_versions.tenant_id",
                "review_template_versions.study_id",
                "review_template_versions.id",
            ],
            name="fk_monitoring_review_bindings_template",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "monitoring_visit_id",
            name="uq_monitoring_review_bindings_visit",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_monitoring_review_bindings_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    monitoring_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    review_template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MonitoringReviewItem(Base):
    __tablename__ = "monitoring_review_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_monitoring_review_items_visit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "review_template_item_id"],
            [
                "review_template_items.tenant_id",
                "review_template_items.study_id",
                "review_template_items.id",
            ],
            name="fk_monitoring_review_items_template_item",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "monitoring_visit_id",
            "review_template_item_id",
            name="uq_monitoring_review_items_visit_template",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_monitoring_review_items_study_id",
        ),
        CheckConstraint(
            "status IN ('not_checked','checked','needs_clarification',"
            "'not_applicable','skipped')",
            name="ck_monitoring_review_items_status",
        ),
        CheckConstraint(
            "revision >= 1",
            name="ck_monitoring_review_items_revision",
        ),
        Index(
            "ix_monitoring_review_items_visit",
            "tenant_id",
            "study_id",
            "monitoring_visit_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    monitoring_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    review_template_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    linked_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    linked_comparison_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    rule_version_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_checked"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_section: Mapped[str] = mapped_column(String(512), nullable=False)
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


class MonitoringReviewHistory(Base):
    __tablename__ = "monitoring_review_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_review_item_id"],
            [
                "monitoring_review_items.tenant_id",
                "monitoring_review_items.study_id",
                "monitoring_review_items.id",
            ],
            name="fk_monitoring_review_history_item",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "monitoring_review_item_id",
            "ordinal",
            name="uq_monitoring_review_history_ordinal",
        ),
        Index(
            "ix_monitoring_review_history_time",
            "tenant_id",
            "study_id",
            "monitoring_review_item_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    monitoring_review_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
