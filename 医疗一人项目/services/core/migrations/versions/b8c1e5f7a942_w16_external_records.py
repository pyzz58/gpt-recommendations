"""W16 experts engagements quotes contracts and external records

Revision ID: b8c1e5f7a942
Revises: d4b8e7c9a321
Create Date: 2026-11-01 01:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8c1e5f7a942"
down_revision: str | None = "d4b8e7c9a321"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

W16_TABLES = (
    "external_organizations",
    "external_contacts",
    "external_experts",
    "external_engagements",
    "external_quotes",
    "external_contracts",
    "external_deliverables",
    "professional_records",
    "external_authorizations",
)


def upgrade() -> None:
    op.create_table(
        "external_organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("provider_type", sa.String(length=40), nullable=False),
        sa.Column("capability_summary", sa.Text(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_state", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
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
            "provider_type IN ('cdmo', 'cro', 'smo', 'central_lab', 'testing_lab', "
            "'sample_provider', 'prototype_provider', 'regulatory', 'ethics', 'other')",
            name=op.f("ck_external_organizations_external_organization_provider_type"),
        ),
        sa.CheckConstraint(
            "verification_state IN ('candidate', 'contacted', 'verified', 'rejected')",
            name=op.f(
                "ck_external_organizations_external_organization_verification_state"
            ),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_organizations_external_organization_revision_positive"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="external_organization_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_organizations")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_organizations_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_organizations_workspace_project_id",
        ),
    )
    op.create_index(
        "ix_external_organizations_project_type",
        "external_organizations",
        ["project_id", "provider_type"],
    )
    op.create_table(
        "external_contacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_state", sa.String(length=30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verification_state IN ('candidate', 'contacted', 'verified', 'rejected')",
            name=op.f("ck_external_contacts_external_contact_verification_state"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_contacts_external_contact_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "organization_id"],
            [
                "external_organizations.workspace_id",
                "external_organizations.project_id",
                "external_organizations.id",
            ],
            name="external_contact_same_organization",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_contacts")),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_contacts_workspace_project_id",
        ),
    )
    op.create_table(
        "external_experts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("expertise", sa.Text(), nullable=False),
        sa.Column(
            "public_source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("conflict_notes", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('candidate', 'contacted', 'replied', 'limited_review', "
            "'engaged', 'declined')",
            name=op.f("ck_external_experts_external_expert_state"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_experts_external_expert_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="external_expert_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_experts")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_experts_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_experts_workspace_project_id",
        ),
    )
    op.create_table(
        "external_engagements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
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
            "state IN ('draft', 'scope_ready', 'requested', 'quoted', 'authorized', "
            "'executing', 'delivered', 'under_review', 'accepted', 'closed', 'cancelled')",
            name=op.f("ck_external_engagements_external_engagement_state"),
        ),
        sa.CheckConstraint(
            "scope_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_external_engagements_external_engagement_scope_sha"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_engagements_external_engagement_revision_positive"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "organization_id"],
            [
                "external_organizations.workspace_id",
                "external_organizations.project_id",
                "external_organizations.id",
            ],
            name="external_engagement_same_organization",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_engagements")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_engagements_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_engagements_workspace_project_id",
        ),
    )
    op.create_table(
        "external_quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("tax_included", sa.Boolean(), nullable=True),
        sa.Column("shipping_included", sa.Boolean(), nullable=True),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("excluded_work", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_version_id", sa.UUID(), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('received', 'accepted', 'rejected', 'expired')",
            name=op.f("ck_external_quotes_external_quote_state"),
        ),
        sa.CheckConstraint(
            "scope_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_external_quotes_external_quote_scope_sha"),
        ),
        sa.CheckConstraint(
            "amount IS NULL OR amount >= 0",
            name=op.f("ck_external_quotes_external_quote_amount_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "document_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="external_quote_same_document",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_quote_same_engagement",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_quotes")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_quotes_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_quotes_workspace_project_id",
        ),
    )
    op.create_table(
        "external_contracts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("terms_summary", sa.Text(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("internal_signed", sa.Boolean(), nullable=False),
        sa.Column("external_signed", sa.Boolean(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
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
            "state IN ('draft', 'under_review', 'awaiting_signature', 'signed', "
            "'cancelled')",
            name=op.f("ck_external_contracts_external_contract_state"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_contracts_external_contract_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "document_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="external_contract_same_document",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_contract_same_engagement",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "quote_id"],
            [
                "external_quotes.workspace_id",
                "external_quotes.project_id",
                "external_quotes.id",
            ],
            name="external_contract_same_quote",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_contracts")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_contracts_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_contracts_workspace_project_id",
        ),
    )
    op.create_table(
        "external_deliverables",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("expected_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("knowledge_version_id", sa.UUID(), nullable=True),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("receipt_summary", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_role", sa.String(length=3), nullable=True),
        sa.Column("review_summary", sa.Text(), nullable=True),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
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
            "kind IN ('report', 'raw_data', 'prototype', 'service_record', "
            "'approval_record')",
            name=op.f("ck_external_deliverables_external_deliverable_kind"),
        ),
        sa.CheckConstraint(
            "state IN ('expected', 'received', 'under_review', 'accepted', 'rejected')",
            name=op.f("ck_external_deliverables_external_deliverable_state"),
        ),
        sa.CheckConstraint(
            "reviewer_role IS NULL OR reviewer_role IN ('A25', 'A26')",
            name=op.f("ck_external_deliverables_external_deliverable_reviewer"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_deliverables_external_deliverable_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_deliverable_same_engagement",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "knowledge_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="external_deliverable_same_document",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_deliverables")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_deliverables_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_deliverables_workspace_project_id",
        ),
    )
    op.create_table(
        "professional_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source_tier", sa.String(length=30), nullable=False),
        sa.Column("source_title", sa.String(length=500), nullable=True),
        sa.Column("source_ref", sa.String(length=2000), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("market", sa.String(length=200), nullable=True),
        sa.Column("product_scope", sa.String(length=1000), nullable=True),
        sa.Column("jurisdiction", sa.String(length=200), nullable=True),
        sa.Column("patent_status", sa.String(length=30), nullable=True),
        sa.Column("application_number", sa.String(length=200), nullable=True),
        sa.Column("publication_number", sa.String(length=200), nullable=True),
        sa.Column("financial_event_type", sa.String(length=30), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("commercial_evidence_type", sa.String(length=30), nullable=True),
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('regulatory', 'patent', 'financial', 'commercial')",
            name=op.f("ck_professional_records_professional_record_kind"),
        ),
        sa.CheckConstraint(
            "state IN ('draft', 'information_only', 'official_confirmed', "
            "'disputed', 'expired')",
            name=op.f("ck_professional_records_professional_record_state"),
        ),
        sa.CheckConstraint(
            "source_tier IN ('official', 'primary_publication', 'vendor', "
            "'user_statement', 'none')",
            name=op.f("ck_professional_records_professional_record_source_tier"),
        ),
        sa.CheckConstraint(
            "patent_status IS NULL OR patent_status IN "
            "('idea', 'search_only', 'provisional', 'pending', 'granted', "
            "'rejected', 'expired', 'unknown')",
            name=op.f("ck_professional_records_professional_record_patent_status"),
        ),
        sa.CheckConstraint(
            "financial_event_type IS NULL OR financial_event_type IN "
            "('budget', 'commitment', 'payment', 'spend')",
            name=op.f("ck_professional_records_professional_record_financial_event"),
        ),
        sa.CheckConstraint(
            "commercial_evidence_type IS NULL OR commercial_evidence_type IN "
            "('assumption', 'public_claim', 'verified_interview', 'market_report', 'unknown')",
            name=op.f("ck_professional_records_professional_record_commercial_evidence"),
        ),
        sa.CheckConstraint(
            "amount IS NULL OR amount >= 0",
            name=op.f("ck_professional_records_professional_record_amount"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_professional_records_professional_record_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="professional_record_same_project",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professional_records")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_professional_records_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_professional_records_workspace_project_id",
        ),
    )
    op.create_table(
        "external_authorizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=False),
        sa.Column("action_scope", sa.Text(), nullable=False),
        sa.Column("scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("amount_max", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("granted_by_user_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('active', 'revoked', 'expired', 'exhausted')",
            name=op.f("ck_external_authorizations_external_authorization_state"),
        ),
        sa.CheckConstraint(
            "amount_max > 0",
            name=op.f("ck_external_authorizations_external_authorization_amount_positive"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_external_authorizations_external_authorization_revision_positive"),
        ),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_authorization_same_engagement",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_authorizations")),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_authorizations_project_idempotency",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_authorizations_workspace_project_id",
        ),
    )
    for table in W16_TABLES:
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
    for table in reversed(W16_TABLES):
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("external_authorizations")
    op.drop_table("professional_records")
    op.drop_table("external_deliverables")
    op.drop_table("external_contracts")
    op.drop_table("external_quotes")
    op.drop_table("external_engagements")
    op.drop_table("external_experts")
    op.drop_table("external_contacts")
    op.drop_index(
        "ix_external_organizations_project_type",
        table_name="external_organizations",
    )
    op.drop_table("external_organizations")
