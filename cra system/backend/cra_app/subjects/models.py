"""PostgreSQL persistence for subject facts, visits and local check decisions."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_subjects_study_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_subjects_site_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_subjects_study_id",
        ),
        CheckConstraint("revision >= 1", name="ck_subjects_revision"),
        Index("ix_subjects_site_created", "tenant_id", "study_id", "site_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deidentified_label: Mapped[str] = mapped_column(String(128), nullable=False)
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


class SubjectIdentifier(Base):
    __tablename__ = "subject_identifiers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_subject_identifiers_subject",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "identity_namespace",
            "external_id",
            name="uq_subject_identifiers_source",
        ),
        CheckConstraint(
            "identity_namespace <> '' AND external_id <> ''",
            name="ck_subject_identifiers_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    identity_namespace: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClinicalFact(Base):
    __tablename__ = "clinical_facts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_clinical_facts_subject",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "supersedes_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_clinical_facts_supersedes",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "subject_id",
            "fact_key",
            "repeat_instance",
            "revision",
            name="uq_clinical_facts_revision",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_clinical_facts_study_id",
        ),
        CheckConstraint("revision >= 1", name="ck_clinical_facts_revision"),
        CheckConstraint(
            "value_type IN ('date','datetime','decimal','string','boolean','json')",
            name="ck_clinical_facts_value_type",
        ),
        CheckConstraint(
            "precision IN ('date','minute','second','unknown')",
            name="ck_clinical_facts_precision",
        ),
        CheckConstraint(
            "source_kind IN ('original_record','cra_confirmation',"
            "'other_response','model_suggestion')",
            name="ck_clinical_facts_source_kind",
        ),
        CheckConstraint(
            "verification_status IN ('original_record','cra_confirmed',"
            "'reported_by_other','model_candidate')",
            name="ck_clinical_facts_verification",
        ),
        CheckConstraint(
            "(observed_on IS NOT NULL)::int + (observed_at IS NOT NULL)::int = 1",
            name="ck_clinical_facts_one_observed_time",
        ),
        Index(
            "ix_clinical_facts_subject_key_revision",
            "tenant_id",
            "study_id",
            "subject_id",
            "fact_key",
            "repeat_instance",
            "revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(128), nullable=False)
    repeat_instance: Mapped[str] = mapped_column(
        String(128), nullable=False, default="_"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    value_raw: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    precision: Mapped[str] = mapped_column(String(16), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(24), nullable=False
    )
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    supersedes_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VisitInstance(Base):
    __tablename__ = "visit_instances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_visit_instances_subject",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "planned_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_visit_instances_planned_fact",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "actual_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_visit_instances_actual_fact",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "subject_id",
            "visit_key",
            "repeat_instance",
            "revision",
            name="uq_visit_instances_revision",
        ),
        CheckConstraint("revision >= 1", name="ck_visit_instances_revision"),
        CheckConstraint(
            "(planned_fact_id IS NOT NULL OR actual_fact_id IS NOT NULL)",
            name="ck_visit_instances_has_fact",
        ),
        Index(
            "ix_visit_instances_subject_order",
            "tenant_id",
            "study_id",
            "subject_id",
            "visit_key",
            "revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    visit_key: Mapped[str] = mapped_column(String(64), nullable=False)
    repeat_instance: Mapped[str] = mapped_column(
        String(128), nullable=False, default="_"
    )
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    planned_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actual_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    planned_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    precision: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VisitRequirement(Base):
    __tablename__ = "visit_requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_visit_requirements_subject",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_visit_requirements_rule_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "anchor_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_visit_requirements_anchor_fact",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "subject_id",
            "rule_version_id",
            "visit_key",
            "event_date",
            "content_hash",
            name="uq_visit_requirements_snapshot",
        ),
        CheckConstraint("min_days <= max_days", name="ck_visit_requirements_days"),
        CheckConstraint(
            "status IN ('ready','in_window','out_of_window',"
            "'unknown_anchor','unknown_actual','not_checked_by_user',"
            "'needs_review')",
            name="ck_visit_requirements_status",
        ),
        Index(
            "ix_visit_requirements_subject_event",
            "tenant_id",
            "study_id",
            "subject_id",
            "event_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    visit_key: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_fact_key: Mapped[str] = mapped_column(String(128), nullable=False)
    event_fact_key: Mapped[str] = mapped_column(String(128), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    anchor_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    anchor_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    min_days: Mapped[int] = mapped_column(Integer, nullable=False)
    max_days: Mapped[int] = mapped_column(Integer, nullable=False)
    inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    window_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    required_fact_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    allowed_sources: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    can_continue: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_fact_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_fact_revisions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)


class FactChangeImpact(Base):
    __tablename__ = "fact_change_impacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "old_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_fact_change_impacts_old_fact",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "new_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_fact_change_impacts_new_fact",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "dependent_type IN ('visit_requirement','coverage_breakpoint',"
            "'check_decision')",
            name="ck_fact_change_impacts_dependent_type",
        ),
        CheckConstraint(
            "status IN ('needs_review','reviewed')",
            name="ck_fact_change_impacts_status",
        ),
        Index(
            "ix_fact_change_impacts_subject",
            "tenant_id",
            "study_id",
            "subject_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    old_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    new_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dependent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dependent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CoverageBreakpoint(Base):
    __tablename__ = "coverage_breakpoints"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_coverage_breakpoints_subject",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "subject_id",
            "category",
            "scope_key",
            "revision",
            name="uq_coverage_breakpoint_revision",
        ),
        CheckConstraint(
            "category IN ('laboratory','documents','consent','medication',"
            "'safety','visit_window','other')",
            name="ck_coverage_breakpoints_category",
        ),
        CheckConstraint(
            "status IN ('in_progress','complete','not_checked')",
            name="ck_coverage_breakpoints_status",
        ),
        CheckConstraint("revision >= 1", name="ck_coverage_breakpoints_revision"),
        Index(
            "ix_coverage_breakpoints_subject",
            "tenant_id",
            "study_id",
            "subject_id",
            "category",
            "revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    checked_through: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    normal_scope_note: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    unverified_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    supersedes_breakpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CheckDecision(Base):
    __tablename__ = "check_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_check_decisions_subject",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_check_decisions_rule_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "category IN ('laboratory','documents','consent','medication',"
            "'safety','visit_window','other')",
            name="ck_check_decisions_category",
        ),
        CheckConstraint(
            "reason IN ('declined_missing_data','unreadable_skip')",
            name="ck_check_decisions_reason",
        ),
        CheckConstraint(
            "state IN ('active','resumed')",
            name="ck_check_decisions_state",
        ),
        CheckConstraint("revision >= 1", name="ck_check_decisions_revision"),
        CheckConstraint(
            "scope_end IS NULL OR scope_start IS NULL OR scope_end >= scope_start",
            name="ck_check_decisions_scope",
        ),
        Index(
            "ix_check_decisions_subject_state",
            "tenant_id",
            "study_id",
            "subject_id",
            "state",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    scope_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    missing_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    can_continue: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    rule_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recovery_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    recovery_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resumed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resume_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
