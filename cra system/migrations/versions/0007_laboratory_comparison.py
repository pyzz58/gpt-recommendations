"""Add laboratory recognition, source decisions and EDC comparisons.

Revision ID: 0007_laboratory_comparison
Revises: 0006_edc_import
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_laboratory_comparison"
down_revision: str | None = "0006_edc_import"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "edc_lab_records",
        sa.Column("report_revision", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "lab_recognition_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("source_document_version_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("authentication_source", sa.String(length=128), nullable=False),
        sa.Column(
            "platform_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
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
            "status IN ('queued','running','succeeded','failed')",
            name="ck_lab_recognition_jobs_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_lab_recognition_jobs_attempts"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_lab_recognition_jobs_site",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_lab_recognition_jobs_source",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_id",
            "tenant_id",
            "study_id",
            "site_id",
            "idempotency_key",
            name="uq_lab_recognition_jobs_idempotency",
        ),
    )
    op.create_index(
        "ix_lab_recognition_jobs_status",
        "lab_recognition_jobs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_table(
        "lab_report_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("source_document_version_id", sa.UUID(), nullable=False),
        sa.Column("recognition_job_id", sa.UUID(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_format", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column(
            "support_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("observations_count", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('pending','recognized','partial',"
            "'provider_unavailable','failed')",
            name="ck_lab_report_versions_state",
        ),
        sa.CheckConstraint(
            "observations_count >= 0",
            name="ck_lab_report_versions_count",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_lab_report_versions_revision"
        ),
        sa.ForeignKeyConstraint(
            ["recognition_job_id"],
            ["lab_recognition_jobs.id"],
            name="fk_lab_report_versions_job",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_lab_report_versions_source",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_lab_report_versions_site",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_report_versions_study_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "source_document_version_id",
            name="uq_lab_report_versions_source",
        ),
    )
    op.create_index(
        "ix_lab_report_versions_scope",
        "lab_report_versions",
        ["tenant_id", "study_id", "site_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "lab_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "subject_external_id", sa.String(length=128), nullable=True
        ),
        sa.Column("visit_key", sa.String(length=128), nullable=True),
        sa.Column("analyte_raw", sa.String(length=255), nullable=True),
        sa.Column(
            "analyte_normalized", sa.String(length=255), nullable=True
        ),
        sa.Column("specimen", sa.String(length=128), nullable=True),
        sa.Column("collected_on", sa.Date(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("precision", sa.String(length=16), nullable=False),
        sa.Column("timezone_status", sa.String(length=16), nullable=False),
        sa.Column(
            "instance_type_raw", sa.String(length=128), nullable=True
        ),
        sa.Column("instance_type", sa.String(length=32), nullable=False),
        sa.Column(
            "repeat_instance", sa.String(length=128), nullable=True
        ),
        sa.Column("report_on", sa.Date(), nullable=True),
        sa.Column(
            "report_revision", sa.String(length=64), nullable=True
        ),
        sa.Column("value_raw", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=16), nullable=False),
        sa.Column("operator", sa.String(length=8), nullable=True),
        sa.Column(
            "numeric_value",
            sa.Numeric(precision=30, scale=10),
            nullable=True,
        ),
        sa.Column("unit_raw", sa.String(length=64), nullable=True),
        sa.Column("unit_normalized", sa.String(length=64), nullable=True),
        sa.Column(
            "lower_limit_raw", sa.String(length=128), nullable=True
        ),
        sa.Column(
            "upper_limit_raw", sa.String(length=128), nullable=True
        ),
        sa.Column("extraction_state", sa.String(length=24), nullable=False),
        sa.Column("validation_state", sa.String(length=24), nullable=False),
        sa.Column(
            "issues",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_ref",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "provider_confidence",
            sa.Numeric(precision=8, scale=6),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "value_type IN ('exact','bound','text','unknown')",
            name="ck_lab_observations_value_type",
        ),
        sa.CheckConstraint(
            "extraction_state IN ('auto_extracted','needs_review','manual')",
            name="ck_lab_observations_extraction_state",
        ),
        sa.CheckConstraint(
            "validation_state IN ('ready_for_match','needs_review')",
            name="ck_lab_observations_validation_state",
        ),
        sa.CheckConstraint(
            "timezone_status IN ('unknown','explicit','date_only')",
            name="ck_lab_observations_timezone_status",
        ),
        sa.CheckConstraint(
            "ordinal >= 1", name="ck_lab_observations_ordinal_positive"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "report_id"],
            [
                "lab_report_versions.tenant_id",
                "lab_report_versions.study_id",
                "lab_report_versions.id",
            ],
            name="fk_lab_observations_report",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id", "ordinal", name="uq_lab_observations_ordinal"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_observations_study_id",
        ),
    )
    op.create_index(
        "ix_lab_observations_match",
        "lab_observations",
        [
            "tenant_id",
            "study_id",
            "site_id",
            "subject_external_id",
            "analyte_normalized",
            "collected_on",
            "instance_type",
        ],
        unique=False,
    )

    op.create_table(
        "lab_observation_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column(
            "corrected_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('confirm','correct','skip')",
            name="ck_lab_observation_decisions_action",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "observation_id"],
            [
                "lab_observations.tenant_id",
                "lab_observations.study_id",
                "lab_observations.id",
            ],
            name="fk_lab_observation_decisions_observation",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lab_observation_decisions_latest",
        "lab_observation_decisions",
        ["observation_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "lab_comparisons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("edc_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("comparison_key", sa.String(length=64), nullable=False),
        sa.Column("report_revision", sa.Integer(), nullable=False),
        sa.Column("snapshot_record_count", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column(
            "scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unknowns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('complete','partial','no_eligible_observations')",
            name="ck_lab_comparisons_state",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_lab_comparisons_revision"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "edc_snapshot_id"],
            [
                "edc_snapshots.tenant_id",
                "edc_snapshots.study_id",
                "edc_snapshots.id",
            ],
            name="fk_lab_comparisons_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "report_id"],
            [
                "lab_report_versions.tenant_id",
                "lab_report_versions.study_id",
                "lab_report_versions.id",
            ],
            name="fk_lab_comparisons_report",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_lab_comparisons_site",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_comparisons_study_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "comparison_key",
            name="uq_lab_comparisons_key",
        ),
    )

    op.create_table(
        "lab_comparison_fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("comparison_id", sa.UUID(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("edc_record_id", sa.UUID(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("match_status", sa.String(length=24), nullable=False),
        sa.Column("result_status", sa.String(length=32), nullable=False),
        sa.Column(
            "matched_identity",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "candidate_record_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("source_value", sa.Text(), nullable=True),
        sa.Column("edc_value", sa.Text(), nullable=True),
        sa.Column("source_unit", sa.String(length=64), nullable=True),
        sa.Column("edc_unit", sa.String(length=64), nullable=True),
        sa.Column(
            "unknowns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "field_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_state",
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
            "match_status IN ('unique_validated','ambiguous','unmatched')",
            name="ck_lab_comparison_fields_match_status",
        ),
        sa.CheckConstraint(
            "result_status IN ('agreement','value_difference','logic_difference',"
            "'unit_review',"
            "'not_seen_in_export','not_comparable','unreadable',"
            "'not_checked_by_user')",
            name="ck_lab_comparison_fields_result_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "comparison_id"],
            [
                "lab_comparisons.tenant_id",
                "lab_comparisons.study_id",
                "lab_comparisons.id",
            ],
            name="fk_lab_comparison_fields_comparison",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "observation_id"],
            [
                "lab_observations.tenant_id",
                "lab_observations.study_id",
                "lab_observations.id",
            ],
            name="fk_lab_comparison_fields_observation",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_id",
            "observation_id",
            name="uq_lab_comparison_fields_observation",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_comparison_fields_study_id",
        ),
    )
    op.create_index(
        "ix_lab_comparison_fields_result",
        "lab_comparison_fields",
        ["comparison_id", "result_status"],
        unique=False,
    )

    op.create_table(
        "lab_comparison_issue_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("comparison_field_id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "comparison_field_id"],
            [
                "lab_comparison_fields.tenant_id",
                "lab_comparison_fields.study_id",
                "lab_comparison_fields.id",
            ],
            name="fk_lab_comparison_issue_links_field",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_lab_comparison_issue_links_issue",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_field_id",
            name="uq_lab_comparison_issue_links_field",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_lab_source_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'laboratory source candidates and comparisons are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in (
        "lab_observations",
        "lab_observation_decisions",
        "lab_comparisons",
        "lab_comparison_fields",
        "lab_comparison_issue_links",
    ):
        op.execute(
            f"""
            CREATE TRIGGER cra_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION cra_reject_lab_source_change()
            """
        )


def downgrade() -> None:
    for table_name in (
        "lab_observations",
        "lab_observation_decisions",
        "lab_comparisons",
        "lab_comparison_fields",
        "lab_comparison_issue_links",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS cra_{table_name}_immutable "
            f"ON {table_name}"
        )
    op.execute("DROP FUNCTION IF EXISTS cra_reject_lab_source_change()")
    op.drop_table("lab_comparison_issue_links")
    op.drop_index(
        "ix_lab_comparison_fields_result",
        table_name="lab_comparison_fields",
    )
    op.drop_table("lab_comparison_fields")
    op.drop_table("lab_comparisons")
    op.drop_index(
        "ix_lab_observation_decisions_latest",
        table_name="lab_observation_decisions",
    )
    op.drop_table("lab_observation_decisions")
    op.drop_index("ix_lab_observations_match", table_name="lab_observations")
    op.drop_table("lab_observations")
    op.drop_index(
        "ix_lab_report_versions_scope",
        table_name="lab_report_versions",
    )
    op.drop_table("lab_report_versions")
    op.drop_index(
        "ix_lab_recognition_jobs_status",
        table_name="lab_recognition_jobs",
    )
    op.drop_table("lab_recognition_jobs")
    op.drop_column("edc_lab_records", "report_revision")
