"""PostgreSQL persistence for rule snapshots, versions and activation windows."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cra_app.shared.db import Base


class RuleSnapshot(Base):
    __tablename__ = "rule_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_rule_snapshots_document_version",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_rule_snapshots_scope_id",
        ),
        UniqueConstraint(
            "source_document_version_id",
            name="uq_rule_snapshots_source_version",
        ),
        CheckConstraint(
            "status IN ('ready','needs_review','invalid')",
            name="ck_rule_snapshots_status",
        ),
        CheckConstraint("revision >= 1", name="ck_rule_snapshots_revision"),
        Index(
            "ix_rule_snapshots_scope_created",
            "tenant_id",
            "study_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    prior_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_rules_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_rules_site_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_rules_study_id",
        ),
        CheckConstraint(
            "policy_layer IN ('common','study','site')",
            name="ck_rules_policy_layer",
        ),
        CheckConstraint(
            "status IN ('candidate','active','withdrawn')",
            name="ck_rules_status",
        ),
        CheckConstraint(
            "(policy_layer = 'site') = (site_id IS NOT NULL)",
            name="ck_rules_layer_site",
        ),
        CheckConstraint("revision >= 1", name="ck_rules_revision"),
        Index(
            "uq_rules_study_wide_key",
            "tenant_id",
            "study_id",
            "policy_layer",
            "rule_key",
            unique=True,
            postgresql_where=text("site_id IS NULL"),
        ),
        Index(
            "uq_rules_site_key",
            "tenant_id",
            "study_id",
            "site_id",
            "policy_layer",
            "rule_key",
            unique=True,
            postgresql_where=text("site_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    policy_layer: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_id"],
            ["rules.tenant_id", "rules.study_id", "rules.id"],
            name="fk_rule_versions_rule_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "rule_snapshots.tenant_id",
                "rule_snapshots.study_id",
                "rule_snapshots.id",
            ],
            name="fk_rule_versions_snapshot_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_rule_versions_source_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "inherited_from_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_versions_inherited_from",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "rule_id",
            "version_no",
            name="uq_rule_versions_rule_number",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_rule_versions_study_id",
        ),
        CheckConstraint("version_no >= 1", name="ck_rule_versions_number"),
        CheckConstraint(
            "state IN ('candidate','confirmed','withdrawn')",
            name="ck_rule_versions_state",
        ),
        CheckConstraint(
            "confirmation_basis IN ('candidate','user_confirmation',"
            "'direct_rule_text','unchanged_inheritance','manual_add')",
            name="ck_rule_versions_confirmation_basis",
        ),
        CheckConstraint(
            "semantic_status IN ('complete','analysis_required')",
            name="ck_rule_versions_semantic_status",
        ),
        Index(
            "ix_rule_versions_snapshot_state",
            "snapshot_id",
            "state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    inherited_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    confirmation_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    semantic_status: Mapped[str] = mapped_column(String(24), nullable=False)
    tree: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RuleSourceRef(Base):
    __tablename__ = "rule_source_refs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_source_refs_version",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_rule_source_refs_anchor",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "rule_version_id",
            "anchor_id",
            "quote_digest",
            name="uq_rule_source_ref_anchor_quote",
        ),
        CheckConstraint(
            "quote_digest ~ '^[0-9a-f]{64}$'",
            name="ck_rule_source_ref_quote_digest",
        ),
        Index(
            "ix_rule_source_refs_version",
            "rule_version_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    anchor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    quote_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    locator: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RuleRelation(Base):
    __tablename__ = "rule_relations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "from_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_relations_from",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "to_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_rule_relations_to",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "from_version_id",
            "to_version_id",
            "rule_key",
            "relation_type",
            name="uq_rule_relation_edge",
        ),
        CheckConstraint(
            "relation_type IN ('unchanged','new','supplement','exception',"
            "'replaces','withdraws','restores','conflict')",
            name="ck_rule_relations_type",
        ),
        Index(
            "ix_rule_relations_to",
            "to_version_id",
            "relation_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    to_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    rule_key: Mapped[str] = mapped_column(String(128), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RuleExtractionCoverage(Base):
    __tablename__ = "rule_extraction_coverage"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "rule_snapshots.tenant_id",
                "rule_snapshots.study_id",
                "rule_snapshots.id",
            ],
            name="fk_rule_extraction_coverage_snapshot",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_rule_extraction_coverage_anchor",
            ondelete="SET NULL",
        ),
        UniqueConstraint(
            "snapshot_id",
            "unit_key",
            name="uq_rule_extraction_coverage_unit",
        ),
        CheckConstraint(
            "status IN ('processed','background','analysis_required',"
            "'unsupported','failed')",
            name="ck_rule_extraction_coverage_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    unit_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )


class VersionActivation(Base):
    __tablename__ = "version_activations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "snapshot_id"],
            [
                "rule_snapshots.tenant_id",
                "rule_snapshots.study_id",
                "rule_snapshots.id",
            ],
            name="fk_version_activations_snapshot",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_version_activations_document_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "supersedes_activation_id"],
            [
                "version_activations.tenant_id",
                "version_activations.study_id",
                "version_activations.id",
            ],
            name="fk_version_activations_supersedes",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_version_activations_scope_id",
        ),
        CheckConstraint(
            "ends_before IS NULL OR ends_before > starts_on",
            name="ck_version_activations_interval",
        ),
        CheckConstraint(
            "status IN ('active','superseded')",
            name="ck_version_activations_status",
        ),
        CheckConstraint("revision >= 1", name="ck_version_activations_revision"),
        Index(
            "ix_version_activations_event_lookup",
            "tenant_id",
            "study_id",
            "site_id",
            "starts_on",
            "ends_before",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_before: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes_activation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
