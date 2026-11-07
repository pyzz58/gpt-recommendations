"""W03 RLS tool audit

Revision ID: 7994d0dd6e2c
Revises: 12ee06c30409
Create Date: 2026-10-31 19:55:13.267457
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7994d0dd6e2c"
down_revision: str | None = "12ee06c30409"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "medical_one_app"
WORKSPACE_POLICY_TABLES = (
    "projects",
    "project_versions",
    "conversations",
    "artifacts",
    "events",
    "tool_audit_events",
)


def upgrade() -> None:
    op.create_table(
        "tool_audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.String(length=20), nullable=False),
        sa.Column("tool_id", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_hash", sa.String(length=64), nullable=False),
        sa.Column("parameters_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('authorized', 'succeeded', 'failed', 'denied')",
            name=op.f("ck_tool_audit_events_tool_audit_state"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_tool_audit_events_actor_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="tool_audit_same_workspace",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_audit_events")),
    )
    op.create_index(
        "ix_tool_audit_project_created",
        "tool_audit_events",
        ["project_id", "created_at"],
        unique=False,
    )

    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
            CREATE ROLE {APP_ROLE} LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS;
          ELSE
            ALTER ROLE {APP_ROLE} NOINHERIT NOSUPERUSER NOBYPASSRLS;
          END IF;
        END
        $$;
        """
    )
    op.execute(
        f"""
        DO $$
        BEGIN
          EXECUTE format('GRANT CONNECT ON DATABASE %I TO {APP_ROLE}', current_database());
        END
        $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}")
    op.execute(
        f"""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}
        """
    )

    for table in WORKSPACE_POLICY_TABLES:
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

    for table in ("messages", "artifact_versions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY workspace_isolation ON {table}
            USING (
              EXISTS (
                SELECT 1 FROM projects p
                WHERE p.id = {table}.project_id
                  AND p.workspace_id =
                    NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
              )
            )
            WITH CHECK (
              EXISTS (
                SELECT 1 FROM projects p
                WHERE p.id = {table}.project_id
                  AND p.workspace_id =
                    NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
              )
            )
            """
        )

    op.execute("ALTER TABLE command_receipts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE command_receipts FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY actor_isolation ON command_receipts
        USING (
          actor_user_id =
            NULLIF(current_setting('medical_one.user_id', true), '')::uuid
        )
        WITH CHECK (
          actor_user_id =
            NULLIF(current_setting('medical_one.user_id', true), '')::uuid
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS actor_isolation ON command_receipts")
    op.execute("ALTER TABLE command_receipts DISABLE ROW LEVEL SECURITY")
    for table in ("messages", "artifact_versions", *WORKSPACE_POLICY_TABLES):
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute(
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM {APP_ROLE}"
    )
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    op.execute(
        f"""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {APP_ROLE}
        """
    )
    op.drop_index("ix_tool_audit_project_created", table_name="tool_audit_events")
    op.drop_table("tool_audit_events")
