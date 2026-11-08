"""Separate task lifecycle from input validity

Revision ID: b2e7d4a9c310
Revises: a7c4e2f9b610
Create Date: 2026-11-01 05:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2e7d4a9c310"
down_revision: str | None = "a7c4e2f9b610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    constraint_names = {
        "tasks": "task_input_validity",
        "task_versions": "task_version_input_validity",
    }
    for table, constraint_name in constraint_names.items():
        op.add_column(
            table,
            sa.Column(
                "input_validity",
                sa.String(length=20),
                server_default="current",
                nullable=False,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "input_snapshot",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
        op.add_column(table, sa.Column("input_snapshot_sha256", sa.String(length=64)))
        op.add_column(
            table,
            sa.Column("input_invalidated_at", sa.DateTime(timezone=True)),
        )
        op.add_column(table, sa.Column("input_invalidated_reason", sa.Text()))
        op.add_column(
            table,
            sa.Column(
                "input_invalidated_by",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )
        refs_expression = "input_refs" if table == "tasks" else "'[]'::jsonb"
        op.execute(
            f"""
            UPDATE {table}
            SET input_snapshot = jsonb_build_object(
                'input_version', input_version,
                'refs', {refs_expression},
                'legacy_backfill', true
            )
            """
        )
        op.alter_column(table, "input_snapshot", nullable=False)
        op.create_check_constraint(
            constraint_name,
            table,
            "input_validity IN ('current', 'stale', 'under_review')",
        )
    op.create_index("ix_tasks_project_input_validity", "tasks", ["project_id", "input_validity"])


def downgrade() -> None:
    op.drop_index("ix_tasks_project_input_validity", table_name="tasks")
    constraint_names = {
        "tasks": "task_input_validity",
        "task_versions": "task_version_input_validity",
    }
    for table, constraint_name in reversed(constraint_names.items()):
        op.drop_constraint(
            op.f(f"ck_{table}_{constraint_name}"),
            table,
            type_="check",
        )
        for column in (
            "input_invalidated_by",
            "input_invalidated_reason",
            "input_invalidated_at",
            "input_snapshot_sha256",
            "input_snapshot",
            "input_validity",
        ):
            op.drop_column(table, column)
