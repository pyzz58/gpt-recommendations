"""W19 immutable policy bundles, impacts, and migration ledger

Revision ID: d9a7e3f1b420
Revises: c8f1a6d3e720
Create Date: 2026-11-01 13:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d9a7e3f1b420"
down_revision: str | None = "c8f1a6d3e720"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY_TABLES = (
    "policy_bundles",
    "policy_states",
    "policy_impacts",
    "policy_migration_operations",
)


def upgrade() -> None:
    op.create_table(
        "policy_bundles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("theory_version", sa.String(length=50), nullable=False),
        sa.Column("theory_sha256", sa.String(length=64), nullable=False),
        sa.Column("component_sha256", postgresql.JSONB(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('published', 'retired')",
            name=op.f("ck_policy_bundles_policy_bundle_state"),
        ),
        sa.CheckConstraint(
            "id ~ '^[0-9a-f]{64}$' AND content_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_policy_bundles_policy_bundle_hashes"),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_bundles")),
        sa.UniqueConstraint(
            "workspace_id", "id", name="uq_policy_bundles_workspace_id"
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "content_sha256",
            name="uq_policy_bundles_workspace_content",
        ),
    )
    op.create_table(
        "policy_states",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("active_bundle_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_policy_states_policy_state_revision_positive"),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "active_bundle_id"],
            ["policy_bundles.workspace_id", "policy_bundles.id"],
            name="policy_state_active_bundle",
        ),
        sa.PrimaryKeyConstraint("workspace_id", name=op.f("pk_policy_states")),
    )
    op.create_table(
        "policy_impacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("from_bundle_id", sa.String(length=64), nullable=True),
        sa.Column("to_bundle_id", sa.String(length=64), nullable=False),
        sa.Column("change_source", sa.String(length=300), nullable=False),
        sa.Column("changed_components", postgresql.JSONB(), nullable=False),
        sa.Column("affected_requirements", postgresql.JSONB(), nullable=False),
        sa.Column("affected_task_ids", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('recorded', 'applied')",
            name=op.f("ck_policy_impacts_policy_impact_status"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "from_bundle_id"],
            ["policy_bundles.workspace_id", "policy_bundles.id"],
            name="policy_impact_from_bundle",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "to_bundle_id"],
            ["policy_bundles.workspace_id", "policy_bundles.id"],
            name="policy_impact_to_bundle",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="policy_impact_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_impacts")),
        sa.UniqueConstraint(
            "project_id",
            "from_bundle_id",
            "to_bundle_id",
            name="uq_policy_impacts_transition",
        ),
    )
    op.create_table(
        "policy_migration_operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("from_bundle_id", sa.String(length=64), nullable=True),
        sa.Column("to_bundle_id", sa.String(length=64), nullable=False),
        sa.Column("expected_project_revision", sa.Integer(), nullable=False),
        sa.Column("schema_revision", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
        sa.Column("backup_ref", sa.String(length=300), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('config', 'database')",
            name=op.f("ck_policy_migration_operations_policy_migration_kind"),
        ),
        sa.CheckConstraint(
            "state IN ('dry_run_passed', 'dry_run_failed', 'applying', "
            "'succeeded', 'failed', 'rolled_back')",
            name=op.f("ck_policy_migration_operations_policy_migration_state"),
        ),
        sa.CheckConstraint(
            "expected_project_revision >= 1",
            name=op.f("ck_policy_migration_operations_policy_migration_revision"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "from_bundle_id"],
            ["policy_bundles.workspace_id", "policy_bundles.id"],
            name="policy_migration_from_bundle",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "to_bundle_id"],
            ["policy_bundles.workspace_id", "policy_bundles.id"],
            name="policy_migration_to_bundle",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="policy_migration_same_project",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_policy_migration_operations")
        ),
        sa.UniqueConstraint(
            "project_id",
            "to_bundle_id",
            "kind",
            "schema_revision",
            name="uq_policy_migrations_target",
        ),
    )

    op.add_column("plans", sa.Column("policy_bundle_id", sa.String(length=64)))
    op.add_column("tasks", sa.Column("policy_bundle_id", sa.String(length=64)))
    op.add_column(
        "task_versions", sa.Column("policy_bundle_id", sa.String(length=64))
    )
    op.add_column(
        "agent_runs", sa.Column("policy_bundle_id", sa.String(length=64))
    )
    op.add_column(
        "skill_runs", sa.Column("policy_bundle_id", sa.String(length=64))
    )
    op.create_foreign_key(
        "project_policy_bundle",
        "projects",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "project_version_policy_bundle",
        "project_versions",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "task_policy_bundle",
        "tasks",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "task_version_policy_bundle",
        "task_versions",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "plan_policy_bundle",
        "plans",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "agent_run_policy_bundle_id",
        "agent_runs",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )
    op.create_foreign_key(
        "skill_run_policy_bundle",
        "skill_runs",
        "policy_bundles",
        ["workspace_id", "policy_bundle_id"],
        ["workspace_id", "id"],
    )

    for table in POLICY_TABLES:
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
    for table in reversed(POLICY_TABLES):
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Policy references cannot survive removal of the immutable bundle table.
    # Clear them explicitly so a downgrade followed by upgrade is deterministic.
    op.execute("UPDATE projects SET policy_bundle_id = NULL")
    op.execute("UPDATE project_versions SET policy_bundle_id = NULL")
    op.drop_constraint("skill_run_policy_bundle", "skill_runs", type_="foreignkey")
    op.drop_constraint("agent_run_policy_bundle_id", "agent_runs", type_="foreignkey")
    op.drop_constraint("plan_policy_bundle", "plans", type_="foreignkey")
    op.drop_constraint(
        "task_version_policy_bundle", "task_versions", type_="foreignkey"
    )
    op.drop_constraint("task_policy_bundle", "tasks", type_="foreignkey")
    op.drop_constraint(
        "project_version_policy_bundle", "project_versions", type_="foreignkey"
    )
    op.drop_constraint("project_policy_bundle", "projects", type_="foreignkey")
    op.drop_column("agent_runs", "policy_bundle_id")
    op.drop_column("skill_runs", "policy_bundle_id")
    op.drop_column("tasks", "policy_bundle_id")
    op.drop_column("task_versions", "policy_bundle_id")
    op.drop_column("plans", "policy_bundle_id")

    op.drop_table("policy_migration_operations")
    op.drop_table("policy_impacts")
    op.drop_table("policy_states")
    op.drop_table("policy_bundles")
