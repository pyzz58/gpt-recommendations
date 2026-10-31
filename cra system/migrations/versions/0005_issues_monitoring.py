"""Add issue actions, Query links, carryover imports and monitoring visits.

Revision ID: 0005_issues_monitoring
Revises: 0004_subjects_coverage
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_issues_monitoring"
down_revision: str | None = "0004_subjects_coverage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issue_number", sa.String(length=64), nullable=False),
        sa.Column("original_finding", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column(
            "recommendation_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("reported_correction", sa.Text(), nullable=True),
        sa.Column("known_progress", sa.Text(), nullable=True),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "verification_status", sa.String(length=24), nullable=False
        ),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "source_anchor_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "source_original_key", sa.String(length=512), nullable=True
        ),
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
        sa.CheckConstraint("revision >= 1", name="ck_issues_revision"),
        sa.CheckConstraint(
            "btrim(issue_number) <> ''", name="ck_issues_number_nonempty"
        ),
        sa.CheckConstraint(
            "source_kind IN ('manual','monitoring_report','track','text',"
            "'legacy','other')",
            name="ck_issues_source_kind",
        ),
        sa.CheckConstraint(
            "verification_status IN ('source_recorded','user_reviewed')",
            name="ck_issues_verification_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_issues_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_issues_site_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_issues_subject_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_issues_source_version_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_issues_source_anchor_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "issue_number",
            name="uq_issues_stable_number",
        ),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_issues_study_id"
        ),
    )
    op.create_index(
        "ix_issues_site_created",
        "issues",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "issue_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "completion_basis", sa.String(length=24), nullable=True
        ),
        sa.Column("completed_by", sa.String(length=128), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("completion_note", sa.Text(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("deadline_source", sa.String(length=500), nullable=True),
        sa.Column(
            "deadline_source_refs",
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
        sa.CheckConstraint("revision >= 1", name="ck_issue_actions_revision"),
        sa.CheckConstraint(
            "kind IN ('pd_reporting','edc_correction','document_supply',"
            "'medical_clarification','query_followup','other')",
            name="ck_issue_actions_kind",
        ),
        sa.CheckConstraint(
            "status IN ('open','reported_done','completed','needs_correction')",
            name="ck_issue_actions_status",
        ),
        sa.CheckConstraint(
            "completion_basis IS NULL OR completion_basis IN "
            "('user_confirmation','user_reported')",
            name="ck_issue_actions_completion_basis",
        ),
        sa.CheckConstraint(
            "due_on IS NULL OR (deadline_source IS NOT NULL "
            "AND btrim(deadline_source) <> '')",
            name="ck_issue_actions_deadline_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_issue_actions_issue_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "issue_id", "action_key", name="uq_issue_actions_stable_key"
        ),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_issue_actions_study_id"
        ),
    )
    op.create_index(
        "ix_issue_actions_issue_status",
        "issue_actions",
        ["tenant_id", "study_id", "issue_id", "status"],
    )

    op.create_table(
        "issue_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
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
            "event_type IN ('issue_created','action_created',"
            "'action_reported','action_confirmed','action_reopened',"
            "'reply_recorded','carryover_imported','query_linked')",
            name="ck_issue_history_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_issue_history_issue_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "action_id"],
            [
                "issue_actions.tenant_id",
                "issue_actions.study_id",
                "issue_actions.id",
            ],
            name="fk_issue_history_action_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_issue_history_issue_time",
        "issue_history",
        ["tenant_id", "study_id", "issue_id", "occurred_at"],
    )

    op.create_table(
        "query_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_state", sa.String(length=16), nullable=False),
        sa.Column("external_system", sa.String(length=64), nullable=True),
        sa.Column(
            "external_query_number", sa.String(length=128), nullable=True
        ),
        sa.Column("opened_on", sa.Date(), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("deadline_source", sa.String(length=500), nullable=True),
        sa.Column(
            "deadline_source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("replied_on", sa.Date(), nullable=True),
        sa.Column("reply_summary", sa.Text(), nullable=True),
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
        sa.CheckConstraint("revision >= 1", name="ck_query_links_revision"),
        sa.CheckConstraint(
            "query_state IN ('draft','formal')",
            name="ck_query_links_state",
        ),
        sa.CheckConstraint(
            "query_state = 'draft' OR "
            "(external_query_number IS NOT NULL "
            "AND btrim(external_query_number) <> '' AND opened_on IS NOT NULL)",
            name="ck_query_links_formal_evidence",
        ),
        sa.CheckConstraint(
            "due_on IS NULL OR "
            "(deadline_source IS NOT NULL AND btrim(deadline_source) <> '')",
            name="ck_query_links_deadline_evidence",
        ),
        sa.CheckConstraint(
            "replied_on IS NULL OR opened_on IS NULL OR replied_on >= opened_on",
            name="ck_query_links_reply_after_open",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_query_links_issue_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_query_links_issue_state",
        "query_links",
        ["tenant_id", "study_id", "issue_id", "query_state"],
    )

    op.create_table(
        "monitoring_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
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
            "revision >= 1", name="ck_monitoring_visits_revision"
        ),
        sa.CheckConstraint(
            "stage IN ('previsit','carryover_review','subject_review',"
            "'closeout','handover')",
            name="ck_monitoring_visits_stage",
        ),
        sa.CheckConstraint(
            "status IN ('draft','in_progress','completed')",
            name="ck_monitoring_visits_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_monitoring_visits_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_monitoring_visits_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_monitoring_visits_study_id",
        ),
    )
    op.create_index(
        "ix_monitoring_visits_site_created",
        "monitoring_visits",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "monitoring_visit_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "monitoring_visit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_by", sa.String(length=128), nullable=False),
        sa.Column(
            "selected_at",
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
            name="fk_monitoring_visit_selections_visit",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_monitoring_visit_selections_issue",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "monitoring_visit_id",
            "issue_id",
            name="uq_monitoring_visit_selection",
        ),
    )

    op.create_table(
        "carryover_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "source_fingerprint", sa.String(length=64), nullable=False
        ),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_by", sa.String(length=128), nullable=True),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_carryover_imports_revision"
        ),
        sa.CheckConstraint(
            "source_kind IN ('document','text')",
            name="ck_carryover_imports_source_kind",
        ),
        sa.CheckConstraint(
            "state IN ('preview','confirmed','failed')",
            name="ck_carryover_imports_state",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_carryover_imports_site_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_carryover_imports_source_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "source_fingerprint",
            name="uq_carryover_import_source",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_carryover_imports_study_id",
        ),
    )
    op.create_index(
        "ix_carryover_imports_scope",
        "carryover_imports",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "carryover_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "carryover_import_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("candidate_key", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "original_issue_number", sa.String(length=64), nullable=True
        ),
        sa.Column("original_finding", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column(
            "recommendation_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("known_progress", sa.Text(), nullable=True),
        sa.Column(
            "actions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unknown_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column(
            "imported_issue_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "user_corrections",
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
            "state IN ('preview','imported','reused','skipped')",
            name="ck_carryover_candidates_state",
        ),
        sa.CheckConstraint(
            "state NOT IN ('imported','reused') "
            "OR imported_issue_id IS NOT NULL",
            name="ck_carryover_candidates_imported_issue",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "carryover_import_id"],
            [
                "carryover_imports.tenant_id",
                "carryover_imports.study_id",
                "carryover_imports.id",
            ],
            name="fk_carryover_candidates_import",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "imported_issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_carryover_candidates_issue",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "carryover_import_id",
            "candidate_key",
            name="uq_carryover_candidate_key",
        ),
    )
    op.create_index(
        "ix_carryover_candidates_import_order",
        "carryover_candidates",
        ["carryover_import_id", "ordinal"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_issue_history_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'issue history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_issue_history_immutable
        BEFORE UPDATE OR DELETE ON issue_history
        FOR EACH ROW EXECUTE FUNCTION cra_reject_issue_history_change()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS cra_issue_history_immutable ON issue_history"
    )
    op.execute("DROP FUNCTION IF EXISTS cra_reject_issue_history_change()")
    op.drop_index(
        "ix_carryover_candidates_import_order",
        table_name="carryover_candidates",
    )
    op.drop_table("carryover_candidates")
    op.drop_index(
        "ix_carryover_imports_scope", table_name="carryover_imports"
    )
    op.drop_table("carryover_imports")
    op.drop_table("monitoring_visit_selections")
    op.drop_index(
        "ix_monitoring_visits_site_created", table_name="monitoring_visits"
    )
    op.drop_table("monitoring_visits")
    op.drop_index("ix_query_links_issue_state", table_name="query_links")
    op.drop_table("query_links")
    op.drop_index("ix_issue_history_issue_time", table_name="issue_history")
    op.drop_table("issue_history")
    op.drop_index(
        "ix_issue_actions_issue_status", table_name="issue_actions"
    )
    op.drop_table("issue_actions")
    op.drop_index("ix_issues_site_created", table_name="issues")
    op.drop_table("issues")
