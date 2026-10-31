"""Create the minimal governance, audit and idempotency foundation.

Revision ID: 0001_governance
Revises:
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_governance"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "studies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_studies_revision_positive"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "code", name="uq_studies_tenant_code"
        ),
        sa.UniqueConstraint(
            "tenant_id", "id", name="uq_studies_tenant_id"
        ),
    )

    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_sites_revision_positive"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_sites_study_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "code", name="uq_sites_study_code"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_sites_study_scope_id",
        ),
    )

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("can_write", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('study_admin', 'cra', 'viewer')",
            name="ck_memberships_role",
        ),
        sa.CheckConstraint(
            "(role = 'study_admin' AND site_id IS NULL) OR "
            "(role IN ('cra', 'viewer'))",
            name="ck_memberships_role_scope",
        ),
        sa.CheckConstraint(
            "role <> 'viewer' OR can_write = false",
            name="ck_memberships_viewer_read_only",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_memberships_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_memberships_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_memberships_study_scope",
        "memberships",
        ["tenant_id", "study_id", "actor_id", "role"],
        unique=True,
        postgresql_where=sa.text("site_id IS NULL"),
    )
    op.create_index(
        "uq_memberships_site_scope",
        "memberships",
        ["tenant_id", "study_id", "actor_id", "role", "site_id"],
        unique=True,
        postgresql_where=sa.text("site_id IS NOT NULL"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_before", sa.Integer(), nullable=True),
        sa.Column("revision_after", sa.Integer(), nullable=False),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("command_name", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision_before IS NULL OR revision_before >= 1",
            name="ck_audit_events_revision_before",
        ),
        sa.CheckConstraint(
            "revision_after >= 1",
            name="ck_audit_events_revision_after",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_audit_events_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_audit_events_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_resource",
        "audit_events",
        [
            "tenant_id",
            "study_id",
            "resource_type",
            "resource_id",
            "created_at",
        ],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("command_name", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "response_resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("response_revision", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.CheckConstraint(
            "response_revision IS NULL OR response_revision >= 1",
            name="ck_idempotency_response_revision",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_idempotency_records_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_idempotency_records_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_id",
            "tenant_id",
            "scope_fingerprint",
            "command_name",
            "idempotency_key",
            name="uq_idempotency_command_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_index(
        "ix_audit_events_resource", table_name="audit_events"
    )
    op.drop_table("audit_events")
    op.drop_index(
        "uq_memberships_site_scope", table_name="memberships"
    )
    op.drop_index(
        "uq_memberships_study_scope", table_name="memberships"
    )
    op.drop_table("memberships")
    op.drop_table("sites")
    op.drop_table("studies")
