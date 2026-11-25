"""Link audit reviews to affected tasks

Revision ID: c8f1a6d3e720
Revises: b2e7d4a9c310
Create Date: 2026-11-01 06:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8f1a6d3e720"
down_revision: str | None = "b2e7d4a9c310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_runs", sa.Column("linked_task_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "audit_run_linked_task",
        "audit_runs",
        "tasks",
        ["workspace_id", "project_id", "linked_task_id"],
        ["workspace_id", "project_id", "id"],
    )


def downgrade() -> None:
    op.drop_constraint("audit_run_linked_task", "audit_runs", type_="foreignkey")
    op.drop_column("audit_runs", "linked_task_id")
