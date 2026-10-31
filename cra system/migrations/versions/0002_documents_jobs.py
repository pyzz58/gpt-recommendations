"""Add private document versions, anchors, coverage and asynchronous jobs.

Revision ID: 0002_documents_jobs
Revises: 0001_governance
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_documents_jobs"
down_revision: str | None = "0001_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('rule','fact','carryover_report','track',"
            "'directory','template','other')",
            name="ck_source_documents_purpose",
        ),
        sa.CheckConstraint(
            "document_type IN ('protocol','ib','sop','monitoring_plan','qa',"
            "'manual','report','track','directory','template','text','other')",
            name="ck_source_documents_type",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_source_documents_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_source_documents_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_source_documents_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_source_documents_study_id",
        ),
    )
    op.create_index(
        "ix_source_documents_scope",
        "source_documents",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_label", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("user_starts_on", sa.Date(), nullable=True),
        sa.Column("user_starts_note", sa.String(length=500), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uploaded_by", sa.String(length=128), nullable=False),
        sa.Column("parse_status", sa.String(length=24), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column(
            "duplicate_of_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "revision >= 1", name="ck_document_versions_revision"
        ),
        sa.CheckConstraint(
            "size_bytes > 0", name="ck_document_versions_size"
        ),
        sa.CheckConstraint(
            "parse_status IN ('pending','running','completed','partial','failed')",
            name="ck_document_versions_parse_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_id"],
            [
                "source_documents.tenant_id",
                "source_documents.study_id",
                "source_documents.id",
            ],
            name="fk_document_versions_document_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "duplicate_of_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_document_versions_duplicate_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_document_versions_study_id",
        ),
        sa.UniqueConstraint(
            "document_id",
            "version_label",
            name="uq_document_versions_label",
        ),
        sa.UniqueConstraint(
            "storage_key", name="uq_document_versions_storage_key"
        ),
    )
    op.create_index(
        "ix_document_versions_scope_hash",
        "document_versions",
        ["tenant_id", "study_id", "sha256"],
    )

    op.create_table(
        "source_anchors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "document_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("anchor_type", sa.String(length=32), nullable=False),
        sa.Column("logical_node_id", sa.String(length=512), nullable=False),
        sa.Column(
            "section_path",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "style", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("table_index", sa.Integer(), nullable=True),
        sa.Column("row_index", sa.Integer(), nullable=True),
        sa.Column("column_index", sa.Integer(), nullable=True),
        sa.Column("footnote_id", sa.String(length=64), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "anchor_type IN ('paragraph','table_cell','footnote',"
            "'pdf_text','plain_text','header','footer','media')",
            name="ck_source_anchors_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_source_anchors_version_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "logical_node_id",
            name="uq_source_anchors_node",
        ),
    )
    op.create_index(
        "ix_source_anchors_version_order",
        "source_anchors",
        ["document_version_id", "ordinal"],
    )

    op.create_table(
        "parse_coverage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "document_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("unit_key", sa.String(length=512), nullable=False),
        sa.Column("unit_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("anchor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('processed','background','not_applicable',"
            "'unsupported','failed','pending')",
            name="ck_parse_coverage_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_parse_coverage_version_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["anchor_id"],
            ["source_anchors.id"],
            name="fk_parse_coverage_anchor",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "unit_key",
            name="uq_parse_coverage_unit",
        ),
    )
    op.create_index(
        "ix_parse_coverage_version_status",
        "parse_coverage",
        ["document_version_id", "status"],
    )

    op.create_table(
        "business_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "authentication_source", sa.String(length=128), nullable=False
        ),
        sa.Column(
            "platform_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("scope_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "input_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column(
            "lease_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.String(length=500), nullable=True),
        sa.Column(
            "output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            "job_type IN ('parse_document')", name="ck_business_jobs_type"
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled')",
            name="ck_business_jobs_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_business_jobs_attempts"
        ),
        sa.CheckConstraint(
            "max_attempts >= 1 AND attempts <= max_attempts",
            name="ck_business_jobs_max_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "input_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_business_jobs_input_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_id",
            "tenant_id",
            "scope_fingerprint",
            "job_type",
            "idempotency_key",
            name="uq_business_jobs_idempotency",
        ),
    )
    op.create_index(
        "ix_business_jobs_status_available",
        "business_jobs",
        ["status", "available_at"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dedup_key", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "published_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.CheckConstraint(
            "status IN ('pending','published','failed')",
            name="ck_outbox_events_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key", name="uq_outbox_events_dedup"),
    )
    op.create_index(
        "ix_outbox_events_status_created",
        "outbox_events",
        ["status", "created_at"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_document_version_source_update()
        RETURNS trigger AS $$
        BEGIN
          IF NEW.document_id IS DISTINCT FROM OLD.document_id
             OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
             OR NEW.study_id IS DISTINCT FROM OLD.study_id
             OR NEW.site_id IS DISTINCT FROM OLD.site_id
             OR NEW.version_label IS DISTINCT FROM OLD.version_label
             OR NEW.storage_key IS DISTINCT FROM OLD.storage_key
             OR NEW.original_filename IS DISTINCT FROM OLD.original_filename
             OR NEW.media_type IS DISTINCT FROM OLD.media_type
             OR NEW.sha256 IS DISTINCT FROM OLD.sha256
             OR NEW.size_bytes IS DISTINCT FROM OLD.size_bytes
             OR NEW.published_on IS DISTINCT FROM OLD.published_on
             OR NEW.user_starts_on IS DISTINCT FROM OLD.user_starts_on
             OR NEW.user_starts_note IS DISTINCT FROM OLD.user_starts_note
             OR NEW.uploaded_at IS DISTINCT FROM OLD.uploaded_at
             OR NEW.uploaded_by IS DISTINCT FROM OLD.uploaded_by THEN
            RAISE EXCEPTION 'document source version is immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_document_version_immutable
        BEFORE UPDATE ON document_versions
        FOR EACH ROW EXECUTE FUNCTION cra_reject_document_version_source_update()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER cra_document_version_immutable ON document_versions"
    )
    op.execute("DROP FUNCTION cra_reject_document_version_source_update()")
    op.drop_table("outbox_events")
    op.drop_table("business_jobs")
    op.drop_index(
        "ix_parse_coverage_version_status", table_name="parse_coverage"
    )
    op.drop_table("parse_coverage")
    op.drop_index(
        "ix_source_anchors_version_order", table_name="source_anchors"
    )
    op.drop_table("source_anchors")
    op.drop_index(
        "ix_document_versions_scope_hash", table_name="document_versions"
    )
    op.drop_table("document_versions")
    op.drop_index(
        "ix_source_documents_scope", table_name="source_documents"
    )
    op.drop_table("source_documents")
