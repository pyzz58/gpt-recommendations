"""Add ISF/TMF directory status and source-backed stage checklists.

Revision ID: 0010_site_files
Revises: 0009_review_remediation
Create Date: 2026-11-01
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_site_files"
down_revision: str | None = "0009_review_remediation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_directory_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("directory_kind", sa.String(length=24), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column(
            "annotations",
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
            "directory_kind IN ('isf','tmf','combined','other')",
            name="ck_site_directory_references_kind",
        ),
        sa.CheckConstraint(
            "mode IN ('reference_only','structured')",
            name="ck_site_directory_references_mode",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_site_directory_references_revision",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_site_directory_references_site",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_site_directory_references_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "source_document_version_id",
            name="uq_site_directory_reference_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_site_directory_references_study_id",
        ),
    )
    op.create_index(
        "ix_site_directory_references_scope",
        "site_directory_references",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "site_file_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "directory_reference_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=True),
        sa.Column(
            "applicability_status", sa.String(length=24), nullable=False
        ),
        sa.Column(
            "acquisition_status", sa.String(length=24), nullable=False
        ),
        sa.Column(
            "verification_status", sa.String(length=24), nullable=False
        ),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column(
            "source_anchor_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "linked_issue_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "linked_action_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("verified_by", sa.String(length=128), nullable=True),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            "applicability_status IN ('required','not_required','unknown')",
            name="ck_site_file_items_applicability",
        ),
        sa.CheckConstraint(
            "acquisition_status IN ('not_seen','provided','unknown')",
            name="ck_site_file_items_acquisition",
        ),
        sa.CheckConstraint(
            "verification_status IN ('pending','qualified','unknown')",
            name="ck_site_file_items_verification",
        ),
        sa.CheckConstraint(
            "verification_status <> 'qualified' "
            "OR acquisition_status = 'provided'",
            name="ck_site_file_items_qualified_requires_file",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_site_file_items_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "directory_reference_id"],
            [
                "site_directory_references.tenant_id",
                "site_directory_references.study_id",
                "site_directory_references.id",
            ],
            name="fk_site_file_items_directory",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_site_file_items_anchor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "linked_issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_site_file_items_issue",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "linked_action_id"],
            [
                "issue_actions.tenant_id",
                "issue_actions.study_id",
                "issue_actions.id",
            ],
            name="fk_site_file_items_action",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "directory_reference_id",
            "item_key",
            name="uq_site_file_items_key",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_site_file_items_study_id",
        ),
    )
    op.create_index(
        "ix_site_file_items_directory_status",
        "site_file_items",
        [
            "directory_reference_id",
            "acquisition_status",
            "verification_status",
        ],
    )

    op.create_table(
        "site_file_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "directory_reference_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "site_file_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
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
            "event_type IN ('directory_reference_created','item_created',"
            "'status_updated')",
            name="ck_site_file_history_event",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "directory_reference_id"],
            [
                "site_directory_references.tenant_id",
                "site_directory_references.study_id",
                "site_directory_references.id",
            ],
            name="fk_site_file_history_directory",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_file_item_id"],
            [
                "site_file_items.tenant_id",
                "site_file_items.study_id",
                "site_file_items.id",
            ],
            name="fk_site_file_history_item",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "directory_reference_id",
            "ordinal",
            name="uq_site_file_history_ordinal",
        ),
    )
    op.create_index(
        "ix_site_file_history_reference_order",
        "site_file_history",
        [
            "tenant_id",
            "study_id",
            "directory_reference_id",
            "ordinal",
        ],
    )

    op.create_table(
        "stage_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "source_refs",
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
            "stage IN ('startup','closeout')",
            name="ck_stage_checklists_stage",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_stage_checklists_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_stage_checklists_site",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "stage",
            name="uq_stage_checklists_scope_stage",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_stage_checklists_study_id",
        ),
    )
    op.create_index(
        "ix_stage_checklists_scope",
        "stage_checklists",
        ["tenant_id", "study_id", "site_id", "stage"],
    )

    op.create_table(
        "stage_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "stage_checklist_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_anchor_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("completion_note", sa.Text(), nullable=True),
        sa.Column("completed_by", sa.String(length=128), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            "status IN ('open','confirmed','not_applicable','unknown')",
            name="ck_stage_checklist_items_status",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_stage_checklist_items_revision",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "stage_checklist_id"],
            [
                "stage_checklists.tenant_id",
                "stage_checklists.study_id",
                "stage_checklists.id",
            ],
            name="fk_stage_checklist_items_checklist",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_stage_checklist_items_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_stage_checklist_items_anchor",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stage_checklist_id",
            "item_key",
            name="uq_stage_checklist_items_key",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_stage_checklist_items_study_id",
        ),
    )
    op.create_index(
        "ix_stage_checklist_items_status",
        "stage_checklist_items",
        ["stage_checklist_id", "status"],
    )

    op.create_table(
        "stage_checklist_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "stage_checklist_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "stage_checklist_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
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
            "event_type IN ('checklist_created','item_created',"
            "'status_updated')",
            name="ck_stage_checklist_history_event",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "stage_checklist_id"],
            [
                "stage_checklists.tenant_id",
                "stage_checklists.study_id",
                "stage_checklists.id",
            ],
            name="fk_stage_checklist_history_checklist",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "stage_checklist_item_id"],
            [
                "stage_checklist_items.tenant_id",
                "stage_checklist_items.study_id",
                "stage_checklist_items.id",
            ],
            name="fk_stage_checklist_history_item",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stage_checklist_id",
            "ordinal",
            name="uq_stage_checklist_history_ordinal",
        ),
    )
    op.create_index(
        "ix_stage_checklist_history_order",
        "stage_checklist_history",
        ["tenant_id", "study_id", "stage_checklist_id", "ordinal"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_site_file_history_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'site file history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_site_file_history_immutable
        BEFORE UPDATE OR DELETE ON site_file_history
        FOR EACH ROW EXECUTE FUNCTION cra_reject_site_file_history_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cra_reject_stage_checklist_history_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'stage checklist history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_stage_checklist_history_immutable
        BEFORE UPDATE OR DELETE ON stage_checklist_history
        FOR EACH ROW EXECUTE FUNCTION cra_reject_stage_checklist_history_change()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS cra_stage_checklist_history_immutable "
        "ON stage_checklist_history"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cra_reject_stage_checklist_history_change()"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS cra_site_file_history_immutable "
        "ON site_file_history"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cra_reject_site_file_history_change()"
    )
    op.drop_index(
        "ix_stage_checklist_history_order",
        table_name="stage_checklist_history",
    )
    op.drop_table("stage_checklist_history")
    op.drop_index(
        "ix_stage_checklist_items_status",
        table_name="stage_checklist_items",
    )
    op.drop_table("stage_checklist_items")
    op.drop_index(
        "ix_stage_checklists_scope", table_name="stage_checklists"
    )
    op.drop_table("stage_checklists")
    op.drop_index(
        "ix_site_file_history_reference_order",
        table_name="site_file_history",
    )
    op.drop_table("site_file_history")
    op.drop_index(
        "ix_site_file_items_directory_status",
        table_name="site_file_items",
    )
    op.drop_table("site_file_items")
    op.drop_index(
        "ix_site_directory_references_scope",
        table_name="site_directory_references",
    )
    op.drop_table("site_directory_references")
