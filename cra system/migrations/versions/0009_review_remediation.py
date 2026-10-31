"""Add review remediation context, event binding and worker leases.

Revision ID: 0009_review_remediation
Revises: 0008_safety_assessment
Create Date: 2026-11-01
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_review_remediation"
down_revision: str | None = "0008_safety_assessment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "studies",
        sa.Column(
            "jurisdiction",
            sa.String(length=64),
            server_default="synthetic",
            nullable=False,
        ),
    )
    op.add_column(
        "safety_assessments",
        sa.Column("event_fact_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "safety_assessments",
        sa.Column(
            "fact_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_safety_assessments_event_fact",
        "safety_assessments",
        "clinical_facts",
        ["tenant_id", "study_id", "event_fact_id"],
        ["tenant_id", "study_id", "id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "ck_safety_assessments_provider_status",
        "safety_assessments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_safety_assessments_provider_status",
        "safety_assessments",
        "provider_status IN ('queued','completed','not_configured',"
        "'rejected','failed')",
    )
    op.drop_constraint(
        "ck_visit_requirements_status",
        "visit_requirements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_visit_requirements_status",
        "visit_requirements",
        "status IN ('ready','in_window','out_of_window',"
        "'unknown_anchor','unknown_actual','unknown_applicability',"
        "'not_applicable','not_checked_by_user','needs_review')",
    )
    op.add_column(
        "lab_recognition_jobs",
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
    )
    op.add_column(
        "lab_recognition_jobs",
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "lab_recognition_jobs",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_lab_recognition_jobs_max_attempts",
        "lab_recognition_jobs",
        "max_attempts >= 1 AND attempts <= max_attempts",
    )
    op.create_table(
        "safety_provider_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "authentication_source", sa.String(length=128), nullable=False
        ),
        sa.Column(
            "platform_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "request_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("model_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "dependency_lock_sha256", sa.String(length=64), nullable=True
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "errors",
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
            "status IN ('queued','running','completed','rejected','failed')",
            name="ck_safety_provider_runs_status",
        ),
        sa.CheckConstraint(
            "max_attempts >= 1 AND attempts <= max_attempts",
            name="ck_safety_provider_runs_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_provider_runs_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id", name="uq_safety_provider_runs_assessment"
        ),
    )


def downgrade() -> None:
    op.drop_table("safety_provider_runs")
    op.drop_constraint(
        "ck_lab_recognition_jobs_max_attempts",
        "lab_recognition_jobs",
        type_="check",
    )
    op.drop_column("lab_recognition_jobs", "lease_expires_at")
    op.drop_column("lab_recognition_jobs", "lease_owner")
    op.drop_column("lab_recognition_jobs", "max_attempts")
    op.drop_constraint(
        "ck_visit_requirements_status",
        "visit_requirements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_visit_requirements_status",
        "visit_requirements",
        "status IN ('ready','in_window','out_of_window',"
        "'unknown_anchor','unknown_actual','not_checked_by_user',"
        "'needs_review')",
    )
    op.drop_constraint(
        "ck_safety_assessments_provider_status",
        "safety_assessments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_safety_assessments_provider_status",
        "safety_assessments",
        "provider_status IN ('completed','not_configured','rejected','failed')",
    )
    op.drop_constraint(
        "fk_safety_assessments_event_fact",
        "safety_assessments",
        type_="foreignkey",
    )
    op.drop_column("safety_assessments", "fact_scope")
    op.drop_column("safety_assessments", "event_fact_id")
    op.drop_column("studies", "jurisdiction")
