"""W20 reliability correlation and regression ledger

Revision ID: e3b8c4d5f601
Revises: d9a7e3f1b420
Create Date: 2026-11-01 14:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3b8c4d5f601"
down_revision: str | None = "d9a7e3f1b420"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tool_audit_events", sa.Column("task_id", sa.UUID()))
    op.add_column("tool_audit_events", sa.Column("job_id", sa.UUID()))
    op.add_column(
        "tool_audit_events", sa.Column("correlation_id", sa.UUID())
    )
    op.create_foreign_key(
        "tool_audit_same_task",
        "tool_audit_events",
        "tasks",
        ["workspace_id", "project_id", "task_id"],
        ["workspace_id", "project_id", "id"],
    )
    op.create_foreign_key(
        "tool_audit_same_job",
        "tool_audit_events",
        "jobs",
        ["workspace_id", "project_id", "job_id"],
        ["workspace_id", "project_id", "id"],
    )
    op.add_column("budget_reservations", sa.Column("task_id", sa.UUID()))
    op.add_column("budget_reservations", sa.Column("job_id", sa.UUID()))
    op.create_foreign_key(
        "budget_reservation_same_task",
        "budget_reservations",
        "tasks",
        ["workspace_id", "project_id", "task_id"],
        ["workspace_id", "project_id", "id"],
    )
    op.create_foreign_key(
        "budget_reservation_same_job",
        "budget_reservations",
        "jobs",
        ["workspace_id", "project_id", "job_id"],
        ["workspace_id", "project_id", "id"],
    )
    op.create_table(
        "reliability_evaluations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("policy_bundle_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("limitations", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('passed', 'blocked')",
            name=op.f("ck_reliability_evaluations_reliability_status"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="reliability_evaluation_same_project",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "policy_bundle_id"],
            ["policy_bundles.workspace_id", "policy_bundles.id"],
            name="reliability_evaluation_policy_bundle",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reliability_evaluations")),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_reliability_evaluations_workspace_project_id",
        ),
    )
    op.create_index(
        "ix_reliability_evaluations_project_created",
        "reliability_evaluations",
        ["project_id", "created_at"],
    )
    op.execute("ALTER TABLE reliability_evaluations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reliability_evaluations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY workspace_isolation ON reliability_evaluations
        USING (
          workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
        )
        WITH CHECK (
          workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workspace_isolation ON reliability_evaluations")
    op.execute("ALTER TABLE reliability_evaluations DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_reliability_evaluations_project_created",
        table_name="reliability_evaluations",
    )
    op.drop_table("reliability_evaluations")
    op.drop_constraint(
        "budget_reservation_same_job", "budget_reservations", type_="foreignkey"
    )
    op.drop_constraint(
        "budget_reservation_same_task", "budget_reservations", type_="foreignkey"
    )
    op.drop_column("budget_reservations", "job_id")
    op.drop_column("budget_reservations", "task_id")
    op.drop_constraint("tool_audit_same_job", "tool_audit_events", type_="foreignkey")
    op.drop_constraint("tool_audit_same_task", "tool_audit_events", type_="foreignkey")
    op.drop_column("tool_audit_events", "correlation_id")
    op.drop_column("tool_audit_events", "job_id")
    op.drop_column("tool_audit_events", "task_id")
