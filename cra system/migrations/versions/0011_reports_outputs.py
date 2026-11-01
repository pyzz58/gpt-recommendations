"""Add template mappings, drafts, immutable snapshots and report exports.

Revision ID: 0011_reports_outputs
Revises: 0010_site_files
Create Date: 2026-11-01
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_reports_outputs"
down_revision: str | None = "0010_site_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("output_kind", sa.String(length=24), nullable=False),
        sa.Column("output_format", sa.String(length=16), nullable=False),
        sa.Column(
            "mapping_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "supported_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "required_variables",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            "output_kind IN ('letter','report','track')",
            name="ck_report_template_versions_kind",
        ),
        sa.CheckConstraint(
            "output_format IN ('docx','xlsx')",
            name="ck_report_template_versions_format",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_report_template_versions_revision",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_report_template_versions_site",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_report_template_versions_document",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "source_document_version_id",
            "output_kind",
            name="uq_report_template_version_kind",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_report_template_versions_study_id",
        ),
    )
    op.create_index(
        "ix_report_template_versions_scope",
        "report_template_versions",
        ["tenant_id", "study_id", "site_id", "output_kind"],
    )

    op.create_table(
        "report_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "monitoring_visit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("output_kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "content_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "input_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unknowns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "not_checked",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "missing_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "user_text",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("generated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "generated_at",
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
            "output_kind IN ('letter','report')",
            name="ck_report_drafts_kind",
        ),
        sa.CheckConstraint(
            "status IN ('draft','ready')",
            name="ck_report_drafts_status",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_report_drafts_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_report_drafts_site",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_report_drafts_visit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "template_version_id"],
            [
                "report_template_versions.tenant_id",
                "report_template_versions.study_id",
                "report_template_versions.id",
            ],
            name="fk_report_drafts_template",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_report_drafts_study_id"
        ),
    )
    op.create_index(
        "ix_report_drafts_visit",
        "report_drafts",
        [
            "tenant_id",
            "study_id",
            "site_id",
            "monitoring_visit_id",
            "generated_at",
        ],
    )

    op.create_table(
        "report_draft_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('generated','text_updated','marked_ready')",
            name="ck_report_draft_history_event",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "draft_id"],
            [
                "report_drafts.tenant_id",
                "report_drafts.study_id",
                "report_drafts.id",
            ],
            name="fk_report_draft_history_draft",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "draft_id",
            "ordinal",
            name="uq_report_draft_history_ordinal",
        ),
    )
    op.create_index(
        "ix_report_draft_history_time",
        "report_draft_history",
        ["tenant_id", "study_id", "draft_id", "ordinal"],
    )

    op.create_table(
        "report_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("snapshot_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "content_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "input_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "missing_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unknown_acknowledged", sa.Boolean(), nullable=False
        ),
        sa.Column("issued_by", sa.String(length=128), nullable=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("user_statement", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('prepared','issued')",
            name="ck_report_snapshots_status",
        ),
        sa.CheckConstraint(
            "status <> 'issued' OR "
            "(issued_by IS NOT NULL AND issued_at IS NOT NULL "
            "AND user_statement IS NOT NULL AND btrim(user_statement) <> '')",
            name="ck_report_snapshots_issued_evidence",
        ),
        sa.CheckConstraint(
            "snapshot_number >= 1",
            name="ck_report_snapshots_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "draft_id"],
            [
                "report_drafts.tenant_id",
                "report_drafts.study_id",
                "report_drafts.id",
            ],
            name="fk_report_snapshots_draft",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "template_version_id"],
            [
                "report_template_versions.tenant_id",
                "report_template_versions.study_id",
                "report_template_versions.id",
            ],
            name="fk_report_snapshots_template",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "draft_id",
            "snapshot_number",
            name="uq_report_snapshots_number",
        ),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_report_snapshots_study_id"
        ),
    )
    op.create_index(
        "ix_report_snapshots_draft",
        "report_snapshots",
        ["tenant_id", "study_id", "draft_id", "snapshot_number"],
    )

    op.create_table(
        "report_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("output_format", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "row_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("generated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "output_format IN ('docx','xlsx')",
            name="ck_report_exports_format",
        ),
        sa.CheckConstraint(
            "size_bytes > 0", name="ck_report_exports_size"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "report_snapshots.tenant_id",
                "report_snapshots.study_id",
                "report_snapshots.id",
            ],
            name="fk_report_exports_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "template_version_id"],
            [
                "report_template_versions.tenant_id",
                "report_template_versions.study_id",
                "report_template_versions.id",
            ],
            name="fk_report_exports_template",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_report_exports_storage_key"),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_report_exports_study_id"
        ),
    )
    op.create_index(
        "ix_report_exports_snapshot",
        "report_exports",
        ["tenant_id", "study_id", "snapshot_id", "created_at"],
    )

    op.create_table(
        "report_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("user_statement", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('sent','submitted','archived')",
            name="ck_report_events_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "report_snapshots.tenant_id",
                "report_snapshots.study_id",
                "report_snapshots.id",
            ],
            name="fk_report_events_snapshot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_report_events_snapshot",
        "report_events",
        ["tenant_id", "study_id", "snapshot_id", "occurred_at"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_report_draft_history_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'report draft history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_report_draft_history_immutable
        BEFORE UPDATE OR DELETE ON report_draft_history
        FOR EACH ROW EXECUTE FUNCTION cra_reject_report_draft_history_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cra_reject_report_snapshot_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'report snapshots are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_report_snapshot_immutable
        BEFORE UPDATE OR DELETE ON report_snapshots
        FOR EACH ROW EXECUTE FUNCTION cra_reject_report_snapshot_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cra_reject_report_export_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'report exports are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_report_export_immutable
        BEFORE UPDATE OR DELETE ON report_exports
        FOR EACH ROW EXECUTE FUNCTION cra_reject_report_export_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cra_reject_report_event_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'report events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_report_event_immutable
        BEFORE UPDATE OR DELETE ON report_events
        FOR EACH ROW EXECUTE FUNCTION cra_reject_report_event_change()
        """
    )


def downgrade() -> None:
    for trigger, table, function in (
        (
            "cra_report_event_immutable",
            "report_events",
            "cra_reject_report_event_change",
        ),
        (
            "cra_report_export_immutable",
            "report_exports",
            "cra_reject_report_export_change",
        ),
        (
            "cra_report_snapshot_immutable",
            "report_snapshots",
            "cra_reject_report_snapshot_change",
        ),
        (
            "cra_report_draft_history_immutable",
            "report_draft_history",
            "cra_reject_report_draft_history_change",
        ),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
        op.execute(f"DROP FUNCTION IF EXISTS {function}()")
    op.drop_index(
        "ix_report_events_snapshot", table_name="report_events"
    )
    op.drop_table("report_events")
    op.drop_index(
        "ix_report_exports_snapshot", table_name="report_exports"
    )
    op.drop_table("report_exports")
    op.drop_index(
        "ix_report_snapshots_draft", table_name="report_snapshots"
    )
    op.drop_table("report_snapshots")
    op.drop_index(
        "ix_report_draft_history_time", table_name="report_draft_history"
    )
    op.drop_table("report_draft_history")
    op.drop_index("ix_report_drafts_visit", table_name="report_drafts")
    op.drop_table("report_drafts")
    op.drop_index(
        "ix_report_template_versions_scope",
        table_name="report_template_versions",
    )
    op.drop_table("report_template_versions")
