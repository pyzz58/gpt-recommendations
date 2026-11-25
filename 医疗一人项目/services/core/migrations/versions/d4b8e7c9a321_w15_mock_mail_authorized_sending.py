"""W15 mock mail threads drafts authorized sending

Revision ID: d4b8e7c9a321
Revises: 6a2d9c4e8b71
Create Date: 2026-11-01 00:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4b8e7c9a321"
down_revision: str | None = "6a2d9c4e8b71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

W15_TABLES = (
    "mail_accounts",
    "mail_threads",
    "mail_messages",
    "mail_drafts",
    "mail_draft_attachments",
    "mail_send_authorizations",
    "mail_send_attempts",
)


def upgrade() -> None:
    op.create_table(
        "mail_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("provider_id", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=300), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("credential_ref", sa.String(length=300), nullable=True),
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
            "mode IN ('mock', 'live')",
            name=op.f("ck_mail_accounts_mail_account_mode"),
        ),
        sa.CheckConstraint(
            "state IN ('mock_ready', 'connected', 'unconfigured', 'disabled')",
            name=op.f("ck_mail_accounts_mail_account_state"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_accounts")),
        sa.UniqueConstraint(
            "workspace_id",
            "address",
            name="uq_mail_accounts_workspace_address",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "id",
            name="uq_mail_accounts_workspace_id",
        ),
    )
    op.create_index("ix_mail_accounts_workspace_id", "mail_accounts", ["workspace_id"])
    op.create_table(
        "mail_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("provider_thread_id", sa.String(length=300), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("link_state", sa.String(length=20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "link_state IN ('unlinked', 'linked')",
            name=op.f("ck_mail_threads_mail_thread_link_state"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_mail_threads_mail_thread_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "account_id"],
            ["mail_accounts.workspace_id", "mail_accounts.id"],
            name="mail_thread_same_account",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="mail_thread_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_threads")),
        sa.UniqueConstraint(
            "account_id",
            "provider_thread_id",
            name="uq_mail_threads_account_provider",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "account_id",
            "id",
            name="uq_mail_threads_workspace_account_id",
        ),
    )
    op.create_table(
        "mail_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=300), nullable=False),
        sa.Column("internet_message_id", sa.String(length=500), nullable=True),
        sa.Column("in_reply_to", sa.String(length=500), nullable=True),
        sa.Column("references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_sha256", sa.String(length=64), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("delivery_state", sa.String(length=30), nullable=False),
        sa.Column("raw_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name=op.f("ck_mail_messages_mail_message_direction"),
        ),
        sa.CheckConstraint(
            "delivery_state IN ('mock_received', 'mock_sent', 'received', 'sent')",
            name=op.f("ck_mail_messages_mail_message_delivery_state"),
        ),
        sa.CheckConstraint(
            "body_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_mail_messages_mail_message_body_sha"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "account_id", "thread_id"],
            ["mail_threads.workspace_id", "mail_threads.account_id", "mail_threads.id"],
            name="mail_message_same_thread",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_messages")),
        sa.UniqueConstraint(
            "account_id",
            "provider_message_id",
            name="uq_mail_messages_account_provider_message",
        ),
    )
    op.create_table(
        "mail_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
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
            "state IN ('draft', 'ready', 'sending', 'sent', 'outcome_unknown', "
            "'failed', 'cancelled')",
            name=op.f("ck_mail_drafts_mail_draft_state"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_mail_drafts_mail_draft_revision_positive"),
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_mail_drafts_mail_draft_content_sha"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "account_id"],
            ["mail_accounts.workspace_id", "mail_accounts.id"],
            name="mail_draft_same_account",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="mail_draft_same_project",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "account_id", "thread_id"],
            ["mail_threads.workspace_id", "mail_threads.account_id", "mail_threads.id"],
            name="mail_draft_same_thread",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_drafts")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_mail_drafts_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_mail_drafts_workspace_project_id",
        ),
    )
    op.create_index(
        "ix_mail_drafts_project_updated",
        "mail_drafts",
        ["project_id", "updated_at"],
    )
    op.create_table(
        "mail_draft_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("media_type", sa.String(length=200), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('artifact_version', 'knowledge_version')",
            name=op.f("ck_mail_draft_attachments_mail_attachment_source_type"),
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name=op.f("ck_mail_draft_attachments_mail_attachment_size_nonnegative"),
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_mail_draft_attachments_mail_attachment_sha"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "draft_id"],
            ["mail_drafts.workspace_id", "mail_drafts.project_id", "mail_drafts.id"],
            name="mail_attachment_same_draft",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_draft_attachments")),
        sa.UniqueConstraint(
            "draft_id",
            "source_type",
            "source_id",
            name="uq_mail_draft_attachments_source",
        ),
    )
    op.create_table(
        "mail_send_authorizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("granted_by_user_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "attachment_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("max_sends", sa.Integer(), nullable=False),
        sa.Column("used_sends", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('active', 'revoked', 'expired', 'exhausted')",
            name=op.f("ck_mail_send_authorizations_mail_authorization_state"),
        ),
        sa.CheckConstraint(
            "action = 'mail.send'",
            name=op.f("ck_mail_send_authorizations_mail_authorization_action"),
        ),
        sa.CheckConstraint(
            "max_sends >= 1 AND used_sends >= 0 AND used_sends <= max_sends",
            name=op.f("ck_mail_send_authorizations_mail_authorization_send_bounds"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_mail_send_authorizations_mail_authorization_revision_positive"),
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_mail_send_authorizations_mail_authorization_content_sha"),
        ),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "account_id"],
            ["mail_accounts.workspace_id", "mail_accounts.id"],
            name="mail_authorization_same_account",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "draft_id"],
            ["mail_drafts.workspace_id", "mail_drafts.project_id", "mail_drafts.id"],
            name="mail_authorization_same_draft",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_send_authorizations")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_mail_authorizations_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_mail_authorizations_workspace_project_id",
        ),
    )
    op.create_table(
        "mail_send_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("authorization_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("operation_key", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "attachment_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.String(length=300), nullable=True),
        sa.Column("provider_thread_id", sa.String(length=300), nullable=True),
        sa.Column("internet_message_id", sa.String(length=500), nullable=True),
        sa.Column("outcome_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('sending', 'sent', 'failed', 'outcome_unknown', 'not_sent')",
            name=op.f("ck_mail_send_attempts_mail_attempt_state"),
        ),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_mail_send_attempts_mail_attempt_request_hash"),
        ),
        sa.CheckConstraint(
            "body_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_mail_send_attempts_mail_attempt_body_sha"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "authorization_id"],
            [
                "mail_send_authorizations.workspace_id",
                "mail_send_authorizations.project_id",
                "mail_send_authorizations.id",
            ],
            name="mail_attempt_same_authorization",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "draft_id"],
            ["mail_drafts.workspace_id", "mail_drafts.project_id", "mail_drafts.id"],
            name="mail_attempt_same_draft",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mail_send_attempts")),
        sa.UniqueConstraint(
            "operation_key",
            name="uq_mail_attempts_operation_key",
        ),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_mail_attempts_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_mail_attempts_workspace_project_id",
        ),
    )
    op.create_index(
        "ix_mail_attempts_project_created",
        "mail_send_attempts",
        ["project_id", "created_at"],
    )
    for table in W15_TABLES:
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
    for table in reversed(W15_TABLES):
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_mail_attempts_project_created", table_name="mail_send_attempts")
    op.drop_table("mail_send_attempts")
    op.drop_table("mail_send_authorizations")
    op.drop_table("mail_draft_attachments")
    op.drop_index("ix_mail_drafts_project_updated", table_name="mail_drafts")
    op.drop_table("mail_drafts")
    op.drop_table("mail_messages")
    op.drop_table("mail_threads")
    op.drop_index("ix_mail_accounts_workspace_id", table_name="mail_accounts")
    op.drop_table("mail_accounts")
