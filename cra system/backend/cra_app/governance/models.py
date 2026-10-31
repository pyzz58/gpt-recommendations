"""Minimal governance persistence for CRA-W01."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cra_app.shared.db import Base


class Study(Base):
    __tablename__ = "studies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_studies_tenant_code"),
        UniqueConstraint("tenant_id", "id", name="uq_studies_tenant_id"),
        CheckConstraint("revision >= 1", name="ck_studies_revision_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_sites_study_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "study_id", "code", name="uq_sites_study_code"
        ),
        UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_sites_study_scope_id"
        ),
        CheckConstraint("revision >= 1", name="ck_sites_revision_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_memberships_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_memberships_site_scope",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "role IN ('study_admin', 'cra', 'viewer')",
            name="ck_memberships_role",
        ),
        CheckConstraint(
            "(role = 'study_admin' AND site_id IS NULL) OR "
            "(role IN ('cra', 'viewer'))",
            name="ck_memberships_role_scope",
        ),
        CheckConstraint(
            "role <> 'viewer' OR can_write = false",
            name="ck_memberships_viewer_read_only",
        ),
        Index(
            "uq_memberships_study_scope",
            "tenant_id",
            "study_id",
            "actor_id",
            "role",
            unique=True,
            postgresql_where=text("site_id IS NULL"),
        ),
        Index(
            "uq_memberships_site_scope",
            "tenant_id",
            "study_id",
            "actor_id",
            "role",
            "site_id",
            unique=True,
            postgresql_where=text("site_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    can_write: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_audit_events_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_audit_events_site_scope",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_audit_events_resource",
            "tenant_id",
            "study_id",
            "resource_type",
            "resource_id",
            "created_at",
        ),
        CheckConstraint(
            "revision_before IS NULL OR revision_before >= 1",
            name="ck_audit_events_revision_before",
        ),
        CheckConstraint(
            "revision_after >= 1", name="ck_audit_events_revision_after"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revision_after: Mapped[int] = mapped_column(Integer, nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    command_name: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_idempotency_records_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_idempotency_records_site_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "actor_id",
            "tenant_id",
            "scope_fingerprint",
            "command_name",
            "idempotency_key",
            name="uq_idempotency_command_key",
        ),
        CheckConstraint(
            "response_revision IS NULL OR response_revision >= 1",
            name="ck_idempotency_response_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    scope_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    command_name: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    response_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    response_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
