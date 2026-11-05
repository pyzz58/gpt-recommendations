"""Versioned scientific feedback and bounded follow-up plans.

Revision ID: f4a2c7d9e601
Revises: e3b8c4d5f601
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a2c7d9e601"
down_revision: str | None = "e3b8c4d5f601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing plans retain their historical semantics; new commands opt in by default.
    op.add_column(
        "plans",
        sa.Column("scientific_feedback", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "plans", sa.Column("max_followup_rounds", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "plans", sa.Column("feedback_round", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("plans", sa.Column("parent_plan_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "plan_parent_same_project",
        "plans",
        "plans",
        ["workspace_id", "project_id", "parent_plan_id"],
        ["workspace_id", "project_id", "id"],
    )
    op.create_check_constraint(
        "plan_feedback_round", "plans", "feedback_round >= 0 AND feedback_round <= 3"
    )
    op.create_check_constraint(
        "plan_followup_bound", "plans", "max_followup_rounds >= 0 AND max_followup_rounds <= 3"
    )


def downgrade() -> None:
    op.drop_constraint("ck_plans_plan_followup_bound", "plans", type_="check")
    op.drop_constraint("ck_plans_plan_feedback_round", "plans", type_="check")
    op.drop_constraint("plan_parent_same_project", "plans", type_="foreignkey")
    for name in ("parent_plan_id", "feedback_round", "max_followup_rounds", "scientific_feedback"):
        op.drop_column("plans", name)
