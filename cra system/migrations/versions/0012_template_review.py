"""Add reusable report-template review configuration and visit records.

Revision ID: 0012_template_review
Revises: 0011_reports_outputs
Create Date: 2026-11-08
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_template_review"
down_revision: str | None = "0011_reports_outputs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _scope_columns() -> list[sa.Column]:
    return [
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "review_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        *_scope_columns(),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("structure_json", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_review_template_versions_site",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_review_template_versions_document",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "source_document_version_id",
            name="uq_review_template_versions_source",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_review_template_versions_study_id",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_review_template_versions_revision",
        ),
    )
    op.create_index(
        "ix_review_template_versions_scope",
        "review_template_versions",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "review_template_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        *_scope_columns(),
        sa.Column(
            "review_template_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("item_key", sa.String(96), nullable=False),
        sa.Column("section_key", sa.String(96), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(255), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.String(512), nullable=False),
        sa.Column("source_quote", sa.Text(), nullable=False),
        sa.Column("report_locator", sa.String(512), nullable=False),
        sa.Column("applicability", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "review_template_version_id"],
            [
                "review_template_versions.tenant_id",
                "review_template_versions.study_id",
                "review_template_versions.id",
            ],
            name="fk_review_template_items_template",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "review_template_version_id",
            "item_key",
            name="uq_review_template_items_key",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_review_template_items_study_id",
        ),
        sa.CheckConstraint(
            "section_order >= 0 AND question_order >= 0",
            name="ck_review_template_items_order",
        ),
    )
    op.create_index(
        "ix_review_template_items_template_order",
        "review_template_items",
        ["review_template_version_id", "section_order", "question_order"],
    )

    op.create_table(
        "monitoring_review_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        *_scope_columns(),
        sa.Column(
            "monitoring_visit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "review_template_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_monitoring_review_bindings_visit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "review_template_version_id"],
            [
                "review_template_versions.tenant_id",
                "review_template_versions.study_id",
                "review_template_versions.id",
            ],
            name="fk_monitoring_review_bindings_template",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "monitoring_visit_id",
            name="uq_monitoring_review_bindings_visit",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_monitoring_review_bindings_revision",
        ),
    )

    op.create_table(
        "monitoring_review_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        *_scope_columns(),
        sa.Column(
            "monitoring_visit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "review_template_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "linked_issue_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "linked_comparison_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("rule_version_ids", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("report_section", sa.String(512), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(128), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_monitoring_review_items_visit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "review_template_item_id"],
            [
                "review_template_items.tenant_id",
                "review_template_items.study_id",
                "review_template_items.id",
            ],
            name="fk_monitoring_review_items_template_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "monitoring_visit_id",
            "review_template_item_id",
            name="uq_monitoring_review_items_visit_template",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_monitoring_review_items_study_id",
        ),
        sa.CheckConstraint(
            "status IN ('not_checked','checked','needs_clarification',"
            "'not_applicable','skipped')",
            name="ck_monitoring_review_items_status",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_monitoring_review_items_revision",
        ),
    )
    op.create_index(
        "ix_monitoring_review_items_visit",
        "monitoring_review_items",
        ["tenant_id", "study_id", "monitoring_visit_id", "status"],
    )

    op.create_table(
        "monitoring_review_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        *_scope_columns(),
        sa.Column(
            "monitoring_review_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_review_item_id"],
            [
                "monitoring_review_items.tenant_id",
                "monitoring_review_items.study_id",
                "monitoring_review_items.id",
            ],
            name="fk_monitoring_review_history_item",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "monitoring_review_item_id",
            "ordinal",
            name="uq_monitoring_review_history_ordinal",
        ),
    )
    op.create_index(
        "ix_monitoring_review_history_time",
        "monitoring_review_history",
        ["tenant_id", "study_id", "monitoring_review_item_id", "ordinal"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_review_history_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'monitoring_review_history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER monitoring_review_history_no_update
        BEFORE UPDATE OR DELETE ON monitoring_review_history
        FOR EACH ROW EXECUTE FUNCTION cra_reject_review_history_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS monitoring_review_history_no_update "
        "ON monitoring_review_history"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cra_reject_review_history_mutation()"
    )
    op.drop_table("monitoring_review_history")
    op.drop_table("monitoring_review_items")
    op.drop_table("monitoring_review_bindings")
    op.drop_table("review_template_items")
    op.drop_table("review_template_versions")
