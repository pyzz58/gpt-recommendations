"""Add evidence-grounded safety assessments and medical responses.

Revision ID: 0008_safety_assessment
Revises: 0007_laboratory_comparison
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_safety_assessment"
down_revision: str | None = "0007_laboratory_comparison"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "safety_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("lab_comparison_id", sa.UUID(), nullable=True),
        sa.Column("assessment_key", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column(
            "requested_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "context_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "rule_inputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "deterministic_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("provider_status", sa.String(length=24), nullable=False),
        sa.Column(
            "provider_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "timely_alerts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unknowns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "output_envelope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ready_to_review','limited','needs_clarification')",
            name="ck_safety_assessments_status",
        ),
        sa.CheckConstraint(
            "provider_status IN ('completed','not_configured','rejected','failed')",
            name="ck_safety_assessments_provider_status",
        ),
        sa.CheckConstraint(
            "event_type IN ('adverse_event','serious_event_review',"
            "'laboratory_logic','protocol_deviation','mixed')",
            name="ck_safety_assessments_event_type",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_safety_assessments_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "lab_comparison_id"],
            [
                "lab_comparisons.tenant_id",
                "lab_comparisons.study_id",
                "lab_comparisons.id",
            ],
            name="fk_safety_assessments_lab_comparison",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_safety_assessments_site",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_safety_assessments_subject",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_safety_assessments_study_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "assessment_key",
            name="uq_safety_assessments_key",
        ),
    )
    op.create_index(
        "ix_safety_assessments_subject_event",
        "safety_assessments",
        ["tenant_id", "study_id", "site_id", "subject_id", "event_date"],
        unique=False,
    )

    op.create_table(
        "safety_dimension_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column(
            "candidate_values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "uncertainties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "rule_version_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_refs",
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
            "dimension IN ('ae_collection','grade','seriousness',"
            "'relatedness','expectedness','aesi','dlt',"
            "'protocol_deviation','reporting_timeliness')",
            name="ck_safety_dimension_results_dimension",
        ),
        sa.CheckConstraint(
            "status IN ('candidate','unknown','not_applicable',"
            "'not_checked_by_user','analysis_required')",
            name="ck_safety_dimension_results_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_dimension_results_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "dimension",
            name="uq_safety_dimension_results_dimension",
        ),
    )
    op.create_index(
        "ix_safety_dimension_results_assessment",
        "safety_dimension_results",
        ["assessment_id", "dimension"],
        unique=False,
    )

    op.create_table(
        "safety_cra_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("check_decision_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('reviewed_candidate','needs_clarification',"
            "'not_checked_by_user')",
            name="ck_safety_cra_reviews_decision",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_cra_reviews_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_safety_cra_reviews_assessment",
        "safety_cra_reviews",
        ["assessment_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "medical_safety_responses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("respondent_role", sa.String(length=32), nullable=False),
        sa.Column("respondent_name", sa.String(length=255), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column(
            "dimension_responses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "respondent_role IN ('investigator','medical_monitor',"
            "'medical_reviewer','other')",
            name="ck_medical_safety_responses_role",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_medical_safety_responses_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_medical_safety_responses_assessment",
        "medical_safety_responses",
        ["assessment_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "safety_issue_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_issue_links_assessment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_safety_issue_links_issue",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id", name="uq_safety_issue_links_assessment"
        ),
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_safety_analysis_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'safety analysis records are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in (
        "safety_assessments",
        "safety_dimension_results",
        "safety_cra_reviews",
        "medical_safety_responses",
        "safety_issue_links",
    ):
        op.execute(
            f"""
            CREATE TRIGGER cra_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION cra_reject_safety_analysis_change()
            """
        )


def downgrade() -> None:
    for table_name in (
        "safety_assessments",
        "safety_dimension_results",
        "safety_cra_reviews",
        "medical_safety_responses",
        "safety_issue_links",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS cra_{table_name}_immutable "
            f"ON {table_name}"
        )
    op.execute("DROP FUNCTION IF EXISTS cra_reject_safety_analysis_change()")
    op.drop_table("safety_issue_links")
    op.drop_index(
        "ix_medical_safety_responses_assessment",
        table_name="medical_safety_responses",
    )
    op.drop_table("medical_safety_responses")
    op.drop_index(
        "ix_safety_cra_reviews_assessment",
        table_name="safety_cra_reviews",
    )
    op.drop_table("safety_cra_reviews")
    op.drop_index(
        "ix_safety_dimension_results_assessment",
        table_name="safety_dimension_results",
    )
    op.drop_table("safety_dimension_results")
    op.drop_index(
        "ix_safety_assessments_subject_event",
        table_name="safety_assessments",
    )
    op.drop_table("safety_assessments")
