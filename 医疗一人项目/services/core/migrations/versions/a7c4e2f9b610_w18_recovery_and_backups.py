"""W18 knowledge recovery, index rebuild and encrypted backups

Revision ID: a7c4e2f9b610
Revises: e9f6a3c2d140
Create Date: 2026-11-01 03:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7c4e2f9b610"
down_revision: str | None = "e9f6a3c2d140"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

W18_TABLES = ("trash_entries", "backup_snapshots", "restore_checks")


def upgrade() -> None:
    op.create_table(
        "trash_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column(
            "previous_access_states",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("reference_count", sa.Integer(), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_by_user_id", sa.UUID(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('trashed', 'restored', 'purged')",
            name=op.f("ck_trash_entries_trash_entry_state"),
        ),
        sa.CheckConstraint(
            "reference_count >= 0",
            name=op.f("ck_trash_entries_trash_entry_reference_count"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
        sa.ForeignKeyConstraint(["deleted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="trash_entry_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trash_entries")),
        sa.UniqueConstraint(
            "project_id",
            "document_id",
            name="uq_trash_entries_project_document",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_trash_entries_workspace_project_id",
        ),
    )
    op.create_table(
        "backup_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("format", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=300), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("backup_sha256", sa.String(length=64), nullable=True),
        sa.Column("plaintext_sha256", sa.String(length=64), nullable=True),
        sa.Column("encrypted_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("kdf", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('completed', 'failed')",
            name=op.f("ck_backup_snapshots_backup_snapshot_state"),
        ),
        sa.CheckConstraint(
            "backup_sha256 IS NULL OR backup_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_backup_snapshots_backup_snapshot_backup_sha"),
        ),
        sa.CheckConstraint(
            "plaintext_sha256 IS NULL OR plaintext_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_backup_snapshots_backup_snapshot_plaintext_sha"),
        ),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_backup_snapshots_backup_snapshot_request_hash"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="backup_snapshot_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backup_snapshots")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_backup_snapshots_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_backup_snapshots_workspace_project_id",
        ),
    )
    op.create_table(
        "restore_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("backup_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("object_count", sa.Integer(), nullable=False),
        sa.Column("table_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('verified', 'failed')",
            name=op.f("ck_restore_checks_restore_check_state"),
        ),
        sa.CheckConstraint(
            "object_count >= 0",
            name=op.f("ck_restore_checks_restore_check_object_count"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "backup_id"],
            [
                "backup_snapshots.workspace_id",
                "backup_snapshots.project_id",
                "backup_snapshots.id",
            ],
            name="restore_check_same_backup",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restore_checks")),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_restore_checks_workspace_project_id",
        ),
    )
    for table in W18_TABLES:
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
    for table in reversed(W18_TABLES):
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("restore_checks")
    op.drop_table("backup_snapshots")
    op.drop_table("trash_entries")
