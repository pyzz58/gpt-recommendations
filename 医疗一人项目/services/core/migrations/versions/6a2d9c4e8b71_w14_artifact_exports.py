"""W14 artifact exports and validation

Revision ID: 6a2d9c4e8b71
Revises: bee2b2f5fefa
Create Date: 2026-10-31 23:55:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6a2d9c4e8b71"
down_revision: str | None = "bee2b2f5fefa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_artifact_versions_project_id_id",
        "artifact_versions",
        ["project_id", "id"],
    )
    op.create_table(
        "artifact_exports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("artifact_version_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("media_type", sa.String(length=200), nullable=False),
        sa.Column("filename", sa.String(length=400), nullable=False),
        sa.Column("template_id", sa.String(length=100), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("data_origin", sa.String(length=20), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("validation_status", sa.String(length=30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "structured_content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "validation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("preview_pdf_object_key", sa.String(length=300), nullable=True),
        sa.Column("preview_pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("preview_pdf_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("preview_png_object_key", sa.String(length=300), nullable=True),
        sa.Column("preview_png_sha256", sa.String(length=64), nullable=True),
        sa.Column("preview_png_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "format IN ('docx', 'pptx', 'xlsx', 'pdf')",
            name=op.f("ck_artifact_exports_artifact_export_format"),
        ),
        sa.CheckConstraint(
            "state IN ('running', 'succeeded', 'failed')",
            name=op.f("ck_artifact_exports_artifact_export_state"),
        ),
        sa.CheckConstraint(
            "validation_status IN ('not_checked', 'passed', 'failed')",
            name=op.f("ck_artifact_exports_artifact_export_validation_status"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_artifact_exports_artifact_export_revision_positive"),
        ),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_exports_artifact_export_request_hash"),
        ),
        sa.CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_exports_artifact_export_input_sha256"),
        ),
        sa.CheckConstraint(
            "report_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_exports_artifact_export_report_sha256"),
        ),
        sa.CheckConstraint(
            "preview_pdf_sha256 IS NULL OR preview_pdf_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_exports_artifact_export_preview_pdf_sha256"),
        ),
        sa.CheckConstraint(
            "preview_png_sha256 IS NULL OR preview_png_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_exports_artifact_export_preview_png_sha256"),
        ),
        sa.CheckConstraint(
            "preview_pdf_size_bytes IS NULL OR preview_pdf_size_bytes >= 0",
            name=op.f("ck_artifact_exports_artifact_export_preview_pdf_size"),
        ),
        sa.CheckConstraint(
            "preview_png_size_bytes IS NULL OR preview_png_size_bytes >= 0",
            name=op.f("ck_artifact_exports_artifact_export_preview_png_size"),
        ),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count >= 1",
            name=op.f("ck_artifact_exports_artifact_export_page_count"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_artifact_exports_created_by_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "artifact_version_id"],
            ["artifact_versions.project_id", "artifact_versions.id"],
            name="artifact_export_same_version",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "analysis_id"],
            ["analysis_runs.workspace_id", "analysis_runs.project_id", "analysis_runs.id"],
            name="artifact_export_same_analysis",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="artifact_export_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_exports")),
        sa.UniqueConstraint(
            "artifact_version_id",
            name="uq_artifact_exports_artifact_version",
        ),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_artifact_exports_project_idempotency",
        ),
        sa.UniqueConstraint(
            "project_id",
            "id",
            name="uq_artifact_exports_project_id_id",
        ),
    )
    op.create_index(
        "ix_artifact_exports_analysis_created",
        "artifact_exports",
        ["analysis_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_artifact_exports_project_created",
        "artifact_exports",
        ["project_id", "created_at"],
        unique=False,
    )
    op.execute("ALTER TABLE artifact_exports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE artifact_exports FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY workspace_isolation ON artifact_exports
        USING (
          workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
        )
        WITH CHECK (
          workspace_id = NULLIF(current_setting('medical_one.workspace_id', true), '')::uuid
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workspace_isolation ON artifact_exports")
    op.execute("ALTER TABLE artifact_exports DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_artifact_exports_project_created",
        table_name="artifact_exports",
    )
    op.drop_index(
        "ix_artifact_exports_analysis_created",
        table_name="artifact_exports",
    )
    op.drop_table("artifact_exports")
    op.drop_constraint(
        "uq_artifact_versions_project_id_id",
        "artifact_versions",
        type_="unique",
    )
