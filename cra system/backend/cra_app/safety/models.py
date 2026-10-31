"""Persistence for safety analysis, reviews and medical responses."""
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


class SafetyAssessment(Base):
    __tablename__ = "safety_assessments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_safety_assessments_site",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_safety_assessments_subject",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "lab_comparison_id"],
            [
                "lab_comparisons.tenant_id",
                "lab_comparisons.study_id",
                "lab_comparisons.id",
            ],
            name="fk_safety_assessments_lab_comparison",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "assessment_key",
            name="uq_safety_assessments_key",
        ),
        UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_safety_assessments_study_id",
        ),
        CheckConstraint(
            "status IN ('ready_to_review','limited','needs_clarification')",
            name="ck_safety_assessments_status",
        ),
        CheckConstraint(
            "provider_status IN ('completed','not_configured','rejected','failed')",
            name="ck_safety_assessments_provider_status",
        ),
        CheckConstraint(
            "event_type IN ('adverse_event','serious_event_review',"
            "'laboratory_logic','protocol_deviation','mixed')",
            name="ck_safety_assessments_event_type",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_safety_assessments_revision"
        ),
        Index(
            "ix_safety_assessments_subject_event",
            "tenant_id",
            "study_id",
            "site_id",
            "subject_id",
            "event_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    lab_comparison_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    assessment_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_dimensions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    rule_inputs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    deterministic_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_status: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    questions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    timely_alerts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    unknowns: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    output_envelope: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SafetyDimensionResult(Base):
    __tablename__ = "safety_dimension_results"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_dimension_results_assessment",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "assessment_id",
            "dimension",
            name="uq_safety_dimension_results_dimension",
        ),
        CheckConstraint(
            "dimension IN ('ae_collection','grade','seriousness',"
            "'relatedness','expectedness','aesi','dlt',"
            "'protocol_deviation','reporting_timeliness')",
            name="ck_safety_dimension_results_dimension",
        ),
        CheckConstraint(
            "status IN ('candidate','unknown','not_applicable',"
            "'not_checked_by_user','analysis_required')",
            name="ck_safety_dimension_results_status",
        ),
        Index(
            "ix_safety_dimension_results_assessment",
            "assessment_id",
            "dimension",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    candidate_values: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    uncertainties: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    rule_version_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SafetyCraReview(Base):
    __tablename__ = "safety_cra_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_cra_reviews_assessment",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "decision IN ('reviewed_candidate','needs_clarification',"
            "'not_checked_by_user')",
            name="ck_safety_cra_reviews_decision",
        ),
        Index(
            "ix_safety_cra_reviews_assessment",
            "assessment_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    dimensions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MedicalSafetyResponse(Base):
    __tablename__ = "medical_safety_responses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_medical_safety_responses_assessment",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "respondent_role IN ('investigator','medical_monitor',"
            "'medical_reviewer','other')",
            name="ck_medical_safety_responses_role",
        ),
        Index(
            "ix_medical_safety_responses_assessment",
            "assessment_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    respondent_role: Mapped[str] = mapped_column(String(32), nullable=False)
    respondent_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    dimension_responses: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SafetyIssueLink(Base):
    __tablename__ = "safety_issue_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "assessment_id"],
            [
                "safety_assessments.tenant_id",
                "safety_assessments.study_id",
                "safety_assessments.id",
            ],
            name="fk_safety_issue_links_assessment",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "issue_id"],
            ["issues.tenant_id", "issues.study_id", "issues.id"],
            name="fk_safety_issue_links_issue",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "assessment_id", name="uq_safety_issue_links_assessment"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dimensions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
