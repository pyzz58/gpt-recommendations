"""W17 independent audit reviews and evaluation runs

Revision ID: e9f6a3c2d140
Revises: b8c1e5f7a942
Create Date: 2026-11-01 02:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e9f6a3c2d140"
down_revision: str | None = "b8c1e5f7a942"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

W17_TABLES = ("audit_runs", "audit_findings", "audit_evaluations")


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_claim_versions_claim_status"),
        "claim_versions",
        type_="check",
    )
    op.create_check_constraint(
        "claim_status",
        "claim_versions",
        "status IN ('hypothesis', 'inferred', 'supported', 'contradicted', "
        "'conflicted', 'unknown', 'stale', 'disputed')",
    )
    op.create_table(
        "audit_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("target_sha256", sa.String(length=64), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("reviewer_role", sa.String(length=3), nullable=False),
        sa.Column("producer_role", sa.String(length=3), nullable=True),
        sa.Column("method", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("downstream_blocked", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("review_version", sa.Integer(), nullable=False),
        sa.Column(
            "input_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_type IN ('claim_version', 'analysis_run', 'external_deliverable')",
            name=op.f("ck_audit_runs_audit_run_target_type"),
        ),
        sa.CheckConstraint(
            "state IN ('passed', 'changes_requested', 'blocked')",
            name=op.f("ck_audit_runs_audit_run_state"),
        ),
        sa.CheckConstraint(
            "reviewer_role IN ('A25', 'A26')",
            name=op.f("ck_audit_runs_audit_run_reviewer_role"),
        ),
        sa.CheckConstraint(
            "producer_role IS NULL OR producer_role ~ '^A(0[1-9]|1[0-9]|2[0-6])$'",
            name=op.f("ck_audit_runs_audit_run_producer_role"),
        ),
        sa.CheckConstraint(
            "target_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_audit_runs_audit_run_target_sha"),
        ),
        sa.CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_audit_runs_audit_run_input_sha"),
        ),
        sa.CheckConstraint(
            "review_version >= 1",
            name=op.f("ck_audit_runs_audit_run_review_version_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="audit_run_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_runs")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_audit_runs_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_audit_runs_workspace_project_id",
        ),
        sa.UniqueConstraint(
            "project_id",
            "target_type",
            "target_id",
            "reviewer_role",
            "review_version",
            name="uq_audit_runs_target_reviewer_version",
        ),
    )
    op.create_index("ix_audit_runs_project_created", "audit_runs", ["project_id", "created_at"])
    op.create_table(
        "audit_findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("audit_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "affected_objects",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'major', 'minor')",
            name=op.f("ck_audit_findings_audit_finding_severity"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'accepted_risk')",
            name=op.f("ck_audit_findings_audit_finding_status"),
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "audit_id"],
            ["audit_runs.workspace_id", "audit_runs.project_id", "audit_runs.id"],
            name="audit_finding_same_run",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_findings")),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_audit_findings_workspace_project_id",
        ),
    )
    op.create_table(
        "audit_evaluations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("fixture_name", sa.String(length=200), nullable=False),
        sa.Column("fixture_sha256", sa.String(length=64), nullable=False),
        sa.Column("cases", sa.Integer(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "case_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "fixture_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_audit_evaluations_audit_evaluation_fixture_sha"),
        ),
        sa.CheckConstraint(
            "cases >= 1",
            name=op.f("ck_audit_evaluations_audit_evaluation_cases_positive"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="audit_evaluation_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_evaluations")),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_audit_evaluations_workspace_project_id",
        ),
    )
    for table in W17_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY workspace_isolation ON {table}
            USING (
              workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
            )
            WITH CHECK (
              workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
            )
            """
        )


def downgrade() -> None:
    for table in reversed(W17_TABLES):
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("audit_evaluations")
    op.drop_table("audit_findings")
    op.drop_index("ix_audit_runs_project_created", table_name="audit_runs")
    op.drop_table("audit_runs")
    op.drop_constraint(
        op.f("ck_claim_versions_claim_status"),
        "claim_versions",
        type_="check",
    )
    op.create_check_constraint(
        "claim_status",
        "claim_versions",
        "status IN ('hypothesis', 'inferred', 'supported', 'contradicted', "
        "'conflicted', 'unknown', 'stale')",
    )
