"""Persistence for laboratory recognition, field decisions and comparisons."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cra_app.shared.db import Base


class LabRecognitionJob(Base):
    __tablename__ = "lab_recognition_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_lab_recognition_jobs_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_lab_recognition_jobs_source",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "actor_id",
            "tenant_id",
            "study_id",
            "site_id",
            "idempotency_key",
            name="uq_lab_recognition_jobs_idempotency",
        ),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')",
            name="ck_lab_recognition_jobs_status",
        ),
        CheckConstraint(
            "attempts >= 0", name="ck_lab_recognition_jobs_attempts"
        ),
        Index(
            "ix_lab_recognition_jobs_status",
            "status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authentication_source: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    platform_roles: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LabReportVersion(Base):
    __tablename__ = "lab_report_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_lab_report_versions_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "source_document_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_lab_report_versions_source",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["recognition_job_id"],
            ["lab_recognition_jobs.id"],
            name="fk_lab_report_versions_job",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "source_document_version_id",
            name="uq_lab_report_versions_source",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_report_versions_study_id",
        ),
        CheckConstraint(
            "state IN ('pending','recognized','partial','provider_unavailable',"
            "'failed')",
            name="ck_lab_report_versions_state",
        ),
        CheckConstraint(
            "observations_count >= 0",
            name="ck_lab_report_versions_count",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_lab_report_versions_revision"
        ),
        Index(
            "ix_lab_report_versions_scope",
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
    source_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    recognition_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_format: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    support_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    observations_count: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LabObservation(Base):
    __tablename__ = "lab_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "report_id"],
            [
                "lab_report_versions.tenant_id",
                "lab_report_versions.study_id",
                "lab_report_versions.id",
            ],
            name="fk_lab_observations_report",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "report_id", "ordinal", name="uq_lab_observations_ordinal"
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_observations_study_id",
        ),
        CheckConstraint(
            "value_type IN ('exact','bound','text','unknown')",
            name="ck_lab_observations_value_type",
        ),
        CheckConstraint(
            "extraction_state IN ('auto_extracted','needs_review','manual')",
            name="ck_lab_observations_extraction_state",
        ),
        CheckConstraint(
            "validation_state IN ('ready_for_match','needs_review')",
            name="ck_lab_observations_validation_state",
        ),
        CheckConstraint(
            "timezone_status IN ('unknown','explicit','date_only')",
            name="ck_lab_observations_timezone_status",
        ),
        CheckConstraint(
            "ordinal >= 1", name="ck_lab_observations_ordinal_positive"
        ),
        Index(
            "ix_lab_observations_match",
            "tenant_id",
            "study_id",
            "site_id",
            "subject_external_id",
            "analyte_normalized",
            "collected_on",
            "instance_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_external_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    visit_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    analyte_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analyte_normalized: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    specimen: Mapped[str | None] = mapped_column(String(128), nullable=True)
    collected_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    precision: Mapped[str] = mapped_column(String(16), nullable=False)
    timezone_status: Mapped[str] = mapped_column(String(16), nullable=False)
    instance_type_raw: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    instance_type: Mapped[str] = mapped_column(String(32), nullable=False)
    repeat_instance: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    report_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    report_revision: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    value_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(8), nullable=True)
    numeric_value: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 10), nullable=True
    )
    unit_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_normalized: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    lower_limit_raw: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    upper_limit_raw: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    extraction_state: Mapped[str] = mapped_column(String(24), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(24), nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provider_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LabObservationDecision(Base):
    __tablename__ = "lab_observation_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "observation_id"],
            [
                "lab_observations.tenant_id",
                "lab_observations.study_id",
                "lab_observations.id",
            ],
            name="fk_lab_observation_decisions_observation",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "action IN ('confirm','correct','skip')",
            name="ck_lab_observation_decisions_action",
        ),
        Index(
            "ix_lab_observation_decisions_latest",
            "observation_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    corrected_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LabComparison(Base):
    __tablename__ = "lab_comparisons"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_lab_comparisons_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "report_id"],
            [
                "lab_report_versions.tenant_id",
                "lab_report_versions.study_id",
                "lab_report_versions.id",
            ],
            name="fk_lab_comparisons_report",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "edc_snapshot_id"],
            [
                "edc_snapshots.tenant_id",
                "edc_snapshots.study_id",
                "edc_snapshots.id",
            ],
            name="fk_lab_comparisons_snapshot",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "comparison_key",
            name="uq_lab_comparisons_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_comparisons_study_id",
        ),
        CheckConstraint(
            "state IN ('complete','partial','no_eligible_observations')",
            name="ck_lab_comparisons_state",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_lab_comparisons_revision"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    edc_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    comparison_key: Mapped[str] = mapped_column(String(64), nullable=False)
    report_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    unknowns: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LabComparisonField(Base):
    __tablename__ = "lab_comparison_fields"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "comparison_id"],
            [
                "lab_comparisons.tenant_id",
                "lab_comparisons.study_id",
                "lab_comparisons.id",
            ],
            name="fk_lab_comparison_fields_comparison",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "observation_id"],
            [
                "lab_observations.tenant_id",
                "lab_observations.study_id",
                "lab_observations.id",
            ],
            name="fk_lab_comparison_fields_observation",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "comparison_id",
            "observation_id",
            name="uq_lab_comparison_fields_observation",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_lab_comparison_fields_study_id",
        ),
        CheckConstraint(
            "match_status IN ('unique_validated','ambiguous','unmatched')",
            name="ck_lab_comparison_fields_match_status",
        ),
        CheckConstraint(
            "result_status IN ('agreement','value_difference','logic_difference',"
            "'unit_review',"
            "'not_seen_in_export','not_comparable','unreadable',"
            "'not_checked_by_user')",
            name="ck_lab_comparison_fields_result_status",
        ),
        Index(
            "ix_lab_comparison_fields_result",
            "comparison_id",
            "result_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comparison_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    edc_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    match_status: Mapped[str] = mapped_column(String(24), nullable=False)
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_identity: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    candidate_record_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
    source_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    edc_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    edc_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    field_results: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    source_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LabComparisonIssueLink(Base):
    __tablename__ = "lab_comparison_issue_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "comparison_field_id"],
            [
                "lab_comparison_fields.tenant_id",
                "lab_comparison_fields.study_id",
                "lab_comparison_fields.id",
            ],
            name="fk_lab_comparison_issue_links_field",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_lab_comparison_issue_links_issue",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "comparison_field_id",
            name="uq_lab_comparison_issue_links_field",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comparison_field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
