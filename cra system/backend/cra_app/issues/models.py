"""Persistence for issues, per-action completion, Query links and carryover imports."""
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cra_app.shared.db import Base

ACTION_KINDS = (
    "pd_reporting",
    "edc_correction",
    "document_supply",
    "medical_clarification",
    "query_followup",
    "other",
)
ACTION_STATUSES = ("open", "reported_done", "completed", "needs_correction")
QUERY_STATES = ("draft", "formal")
MONITORING_STAGES = (
    "previsit",
    "carryover_review",
    "subject_review",
    "closeout",
    "handover",
)


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_issues_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_issues_site_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_issues_subject_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_issues_source_version_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_anchor_id"],
            [
                "source_anchors.tenant_id",
                "source_anchors.study_id",
                "source_anchors.id",
            ],
            name="fk_issues_source_anchor_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "issue_number",
            name="uq_issues_stable_number",
        ),
        UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_issues_study_id"
        ),
        CheckConstraint("revision >= 1", name="ck_issues_revision"),
        CheckConstraint(
            "btrim(issue_number) <> ''", name="ck_issues_number_nonempty"
        ),
        CheckConstraint(
            "source_kind IN ('manual','monitoring_report','track','text',"
            "'legacy','other')",
            name="ck_issues_source_kind",
        ),
        CheckConstraint(
            "verification_status IN ('source_recorded','user_reviewed')",
            name="ck_issues_verification_status",
        ),
        Index(
            "ix_issues_site_created",
            "tenant_id",
            "study_id",
            "site_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    issue_number: Mapped[str] = mapped_column(String(64), nullable=False)
    original_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_sources: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    reported_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_progress: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(24), nullable=False
    )
    source_document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_anchor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_original_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
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


class ActionItem(Base):
    __tablename__ = "issue_actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_issue_actions_issue_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "issue_id", "action_key", name="uq_issue_actions_stable_key"
        ),
        UniqueConstraint(
            "tenant_id", "study_id", "id", name="uq_issue_actions_study_id"
        ),
        CheckConstraint("revision >= 1", name="ck_issue_actions_revision"),
        CheckConstraint(
            "kind IN ('pd_reporting','edc_correction','document_supply',"
            "'medical_clarification','query_followup','other')",
            name="ck_issue_actions_kind",
        ),
        CheckConstraint(
            "status IN ('open','reported_done','completed','needs_correction')",
            name="ck_issue_actions_status",
        ),
        CheckConstraint(
            "completion_basis IS NULL OR completion_basis IN "
            "('user_confirmation','user_reported')",
            name="ck_issue_actions_completion_basis",
        ),
        CheckConstraint(
            "due_on IS NULL OR (deadline_source IS NOT NULL "
            "AND btrim(deadline_source) <> '')",
            name="ck_issue_actions_deadline_evidence",
        ),
        Index(
            "ix_issue_actions_issue_status",
            "tenant_id",
            "study_id",
            "issue_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action_key: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    completion_basis: Mapped[str | None] = mapped_column(
        String(24), nullable=True
    )
    completed_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_source: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    deadline_source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
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


class IssueHistory(Base):
    __tablename__ = "issue_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_issue_history_issue_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "action_id"],
            [
                "issue_actions.tenant_id",
                "issue_actions.study_id",
                "issue_actions.id",
            ],
            name="fk_issue_history_action_scope",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_issue_history_issue_time",
            "tenant_id",
            "study_id",
            "issue_id",
            "occurred_at",
        ),
        CheckConstraint(
            "event_type IN ('issue_created','action_created',"
            "'action_reported','action_confirmed','action_reopened',"
            "'reply_recorded','carryover_imported','query_linked')",
            name="ck_issue_history_event_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QueryLink(Base):
    __tablename__ = "query_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_query_links_issue_scope",
            ondelete="RESTRICT",
        ),
        CheckConstraint("revision >= 1", name="ck_query_links_revision"),
        CheckConstraint(
            "query_state IN ('draft','formal')",
            name="ck_query_links_state",
        ),
        CheckConstraint(
            "query_state = 'draft' OR "
            "(external_query_number IS NOT NULL "
            "AND btrim(external_query_number) <> '' AND opened_on IS NOT NULL)",
            name="ck_query_links_formal_evidence",
        ),
        CheckConstraint(
            "due_on IS NULL OR "
            "(deadline_source IS NOT NULL AND btrim(deadline_source) <> '')",
            name="ck_query_links_deadline_evidence",
        ),
        CheckConstraint(
            "replied_on IS NULL OR opened_on IS NULL OR replied_on >= opened_on",
            name="ck_query_links_reply_after_open",
        ),
        Index(
            "ix_query_links_issue_state",
            "tenant_id",
            "study_id",
            "issue_id",
            "query_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    query_state: Mapped[str] = mapped_column(String(16), nullable=False)
    external_system: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    external_query_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    opened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_source: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    deadline_source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    replied_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    reply_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class MonitoringVisit(Base):
    __tablename__ = "monitoring_visits"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_monitoring_visits_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_monitoring_visits_site_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_monitoring_visits_study_id",
        ),
        CheckConstraint("revision >= 1", name="ck_monitoring_visits_revision"),
        CheckConstraint(
            "stage IN ('previsit','carryover_review','subject_review',"
            "'closeout','handover')",
            name="ck_monitoring_visits_stage",
        ),
        CheckConstraint(
            "status IN ('draft','in_progress','completed')",
            name="ck_monitoring_visits_status",
        ),
        Index(
            "ix_monitoring_visits_site_created",
            "tenant_id",
            "study_id",
            "site_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft"
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


class MonitoringVisitSelection(Base):
    __tablename__ = "monitoring_visit_selections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "monitoring_visit_id"],
            [
                "monitoring_visits.tenant_id",
                "monitoring_visits.study_id",
                "monitoring_visits.id",
            ],
            name="fk_monitoring_visit_selections_visit",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_monitoring_visit_selections_issue",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "monitoring_visit_id",
            "issue_id",
            name="uq_monitoring_visit_selection",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    monitoring_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    selected_by: Mapped[str] = mapped_column(String(128), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CarryoverImport(Base):
    __tablename__ = "carryover_imports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_carryover_imports_site_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_carryover_imports_source_version",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "source_fingerprint",
            name="uq_carryover_import_source",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_carryover_imports_study_id",
        ),
        CheckConstraint("revision >= 1", name="ck_carryover_imports_revision"),
        CheckConstraint(
            "source_kind IN ('document','text')",
            name="ck_carryover_imports_source_kind",
        ),
        CheckConstraint(
            "state IN ('preview','confirmed','failed')",
            name="ck_carryover_imports_state",
        ),
        Index(
            "ix_carryover_imports_scope",
            "tenant_id",
            "study_id",
            "site_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="preview"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CarryoverCandidate(Base):
    __tablename__ = "carryover_candidates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "carryover_import_id"],
            [
                "carryover_imports.tenant_id",
                "carryover_imports.study_id",
                "carryover_imports.id",
            ],
            name="fk_carryover_candidates_import",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "imported_issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_carryover_candidates_issue",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "carryover_import_id",
            "candidate_key",
            name="uq_carryover_candidate_key",
        ),
        CheckConstraint(
            "state IN ('preview','imported','reused','skipped')",
            name="ck_carryover_candidates_state",
        ),
        CheckConstraint(
            "state NOT IN ('imported','reused') "
            "OR imported_issue_id IS NOT NULL",
            name="ck_carryover_candidates_imported_issue",
        ),
        Index(
            "ix_carryover_candidates_import_order",
            "carryover_import_id",
            "ordinal",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    carryover_import_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    original_issue_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    original_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_sources: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    known_progress: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    unknown_fields: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="preview"
    )
    imported_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    user_corrections: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
