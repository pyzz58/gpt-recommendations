"""W22 external source snapshots

Revision ID: b7d1e4a9c260
Revises: a1c9e7f2d304
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d1e4a9c260"
down_revision: str | None = "a1c9e7f2d304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_source_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.String(length=100), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("adapter_ids", postgresql.JSONB(), nullable=False),
        sa.Column("records", postgresql.JSONB(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("query_sha256", sa.String(length=64), nullable=False),
        sa.Column("result_sha256", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "record_count >= 0",
            name=op.f("ck_external_source_snapshots_external_source_snapshot_count"),
        ),
        sa.CheckConstraint(
            "query_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_external_source_snapshots_external_source_snapshot_query_hash"),
        ),
        sa.CheckConstraint(
            "result_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_external_source_snapshots_external_source_snapshot_result_hash"),
        ),
        sa.CheckConstraint(
            "mode IN ('mock', 'live')",
            name=op.f("ck_external_source_snapshots_external_source_snapshot_mode"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="external_source_snapshot_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_source_snapshots")),
        sa.UniqueConstraint("workspace_id", "project_id", "id"),
    )
    op.create_index(
        "ix_external_source_snapshots_project_created",
        "external_source_snapshots",
        ["project_id", "created_at"],
    )
    op.execute("ALTER TABLE external_source_snapshots ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE external_source_snapshots FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY workspace_isolation ON external_source_snapshots
        USING (
          workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
        )
        WITH CHECK (
          workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workspace_isolation ON external_source_snapshots")
    op.execute("ALTER TABLE external_source_snapshots DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_external_source_snapshots_project_created",
        table_name="external_source_snapshots",
    )
    op.drop_table("external_source_snapshots")
