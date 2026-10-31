"""Add rule snapshots, immutable rule versions and activation windows.

Revision ID: 0003_rules_versions
Revises: 0002_documents_jobs
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_rules_versions"
down_revision: str | None = "0002_documents_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_source_anchors_scope_id",
        "source_anchors",
        ["tenant_id", "study_id", "id"],
    )

    op.create_table(
        "rule_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("prior_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("provider_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "validation_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ready','needs_review','invalid')",
            name="ck_rule_snapshots_status",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_rule_snapshots_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_rule_snapshots_document_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_rule_snapshots_scope_id",
        ),
        sa.UniqueConstraint(
            "source_document_version_id",
            name="uq_rule_snapshots_source_version",
        ),
    )
    op.create_index(
        "ix_rule_snapshots_scope_created",
        "rule_snapshots",
        ["tenant_id", "study_id", "created_at"],
    )

    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_layer", sa.String(length=16), nullable=False),
        sa.Column("rule_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "current_version_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "policy_layer IN ('common','study','site')",
            name="ck_rules_policy_layer",
        ),
        sa.CheckConstraint(
            "status IN ('candidate','active','withdrawn')",
            name="ck_rules_status",
        ),
        sa.CheckConstraint(
            "(policy_layer = 'site') = (site_id IS NOT NULL)",
            name="ck_rules_layer_site",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_rules_revision"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_rules_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_rules_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_rules_study_id"
        ),
    )
    op.create_index(
        "uq_rules_study_wide_key",
        "rules",
        ["tenant_id", "study_id", "policy_layer", "rule_key"],
        unique=True,
        postgresql_where=sa.text("site_id IS NULL"),
    )
    op.create_index(
        "uq_rules_site_key",
        "rules",
        ["tenant_id", "study_id", "site_id", "policy_layer", "rule_key"],
        unique=True,
        postgresql_where=sa.text("site_id IS NOT NULL"),
    )

    op.create_table(
        "rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "inherited_from_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("confirmation_basis", sa.String(length=32), nullable=False),
        sa.Column("semantic_status", sa.String(length=24), nullable=False),
        sa.Column(
            "tree", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "unknowns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_by", sa.String(length=128), nullable=True),
        sa.Column(
            "confirmed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.CheckConstraint(
            "version_no >= 1", name="ck_rule_versions_number"
        ),
        sa.CheckConstraint(
            "state IN ('candidate','confirmed','withdrawn')",
            name="ck_rule_versions_state",
        ),
        sa.CheckConstraint(
            "confirmation_basis IN ('candidate','user_confirmation',"
            "'direct_rule_text','unchanged_inheritance','manual_add')",
            name="ck_rule_versions_confirmation_basis",
        ),
        sa.CheckConstraint(
            "semantic_status IN ('complete','analysis_required')",
            name="ck_rule_versions_semantic_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_id"],
            ["rules.tenant_id", "rules.study_id", "rules.id"],
            name="fk_rule_versions_rule_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "rule_snapshots.tenant_id",
                "rule_snapshots.study_id",
                "rule_snapshots.id",
            ],
            name="fk_rule_versions_snapshot_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_rule_versions_source_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "inherited_from_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_versions_inherited_from",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id",
            "version_no",
            name="uq_rule_versions_rule_number",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_rule_versions_study_id",
        ),
    )
    op.create_index(
        "ix_rule_versions_snapshot_state",
        "rule_versions",
        ["snapshot_id", "state"],
    )

    op.create_table(
        "rule_source_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anchor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("quote_digest", sa.String(length=64), nullable=False),
        sa.Column("locator", sa.String(length=512), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quote_digest ~ '^[0-9a-f]{64}$'",
            name="ck_rule_source_ref_quote_digest",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_source_refs_version",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_rule_source_refs_anchor",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_version_id",
            "anchor_id",
            "quote_digest",
            name="uq_rule_source_ref_anchor_quote",
        ),
    )
    op.create_index(
        "ix_rule_source_refs_version",
        "rule_source_refs",
        ["rule_version_id", "ordinal"],
    )

    op.create_table(
        "rule_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_key", sa.String(length=128), nullable=False),
        sa.Column("relation_type", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relation_type IN ('unchanged','new','supplement','exception',"
            "'replaces','withdraws','restores','conflict')",
            name="ck_rule_relations_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "from_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_relations_from",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "to_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_relations_to",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_version_id",
            "to_version_id",
            "rule_key",
            "relation_type",
            name="uq_rule_relation_edge",
        ),
    )
    op.create_index(
        "ix_rule_relations_to",
        "rule_relations",
        ["to_version_id", "relation_type"],
    )

    op.create_table(
        "rule_extraction_coverage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("anchor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processed','background','analysis_required',"
            "'unsupported','failed')",
            name="ck_rule_extraction_coverage_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "rule_snapshots.tenant_id",
                "rule_snapshots.study_id",
                "rule_snapshots.id",
            ],
            name="fk_rule_extraction_coverage_snapshot",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_rule_extraction_coverage_anchor",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "unit_key",
            name="uq_rule_extraction_coverage_unit",
        ),
    )

    op.create_table(
        "version_activations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_before", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "supersedes_activation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ends_before IS NULL OR ends_before > starts_on",
            name="ck_version_activations_interval",
        ),
        sa.CheckConstraint(
            "status IN ('active','superseded')",
            name="ck_version_activations_status",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_version_activations_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "rule_snapshots.tenant_id",
                "rule_snapshots.study_id",
                "rule_snapshots.id",
            ],
            name="fk_version_activations_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_version_activations_document_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "supersedes_activation_id"],
            [
                "version_activations.tenant_id",
                "version_activations.study_id",
                "version_activations.id",
            ],
            name="fk_version_activations_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_version_activations_scope_id",
        ),
    )
    op.create_index(
        "ix_version_activations_event_lookup",
        "version_activations",
        ["tenant_id", "study_id", "site_id", "starts_on", "ends_before"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_rule_version_update()
        RETURNS trigger AS $$
        BEGIN
          IF NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'rule version is immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_rule_version_immutable
        BEFORE UPDATE ON rule_versions
        FOR EACH ROW EXECUTE FUNCTION cra_reject_rule_version_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cra_reject_rule_version_delete()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'rule version history cannot be deleted';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_rule_version_no_delete
        BEFORE DELETE ON rule_versions
        FOR EACH ROW EXECUTE FUNCTION cra_reject_rule_version_delete()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER cra_rule_version_no_delete ON rule_versions"
    )
    op.execute("DROP FUNCTION cra_reject_rule_version_delete()")
    op.execute(
        "DROP TRIGGER cra_rule_version_immutable ON rule_versions"
    )
    op.execute("DROP FUNCTION cra_reject_rule_version_update()")
    op.drop_index(
        "ix_version_activations_event_lookup",
        table_name="version_activations",
    )
    op.drop_table("version_activations")
    op.drop_table("rule_extraction_coverage")
    op.drop_index("ix_rule_relations_to", table_name="rule_relations")
    op.drop_table("rule_relations")
    op.drop_index(
        "ix_rule_source_refs_version", table_name="rule_source_refs"
    )
    op.drop_table("rule_source_refs")
    op.drop_index(
        "ix_rule_versions_snapshot_state", table_name="rule_versions"
    )
    op.drop_table("rule_versions")
    op.drop_index("uq_rules_site_key", table_name="rules")
    op.drop_index("uq_rules_study_wide_key", table_name="rules")
    op.drop_table("rules")
    op.drop_index(
        "ix_rule_snapshots_scope_created", table_name="rule_snapshots"
    )
    op.drop_table("rule_snapshots")
    op.drop_constraint(
        "uq_source_anchors_scope_id",
        "source_anchors",
        type_="unique",
    )
