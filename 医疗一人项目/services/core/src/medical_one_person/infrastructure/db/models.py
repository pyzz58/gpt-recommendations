from __future__ import annotations

import decimal
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from medical_one_person.domain.audits import (
    AuditFindingStatus,
    AuditState,
    AuditTargetType,
)
from medical_one_person.domain.datasets import (
    AnalysisState,
    DatasetVersionKind,
    DatasetVersionState,
    StatisticalMethod,
)
from medical_one_person.domain.exports import ExportFormat, ExportState, ExportValidationStatus
from medical_one_person.domain.external import (
    CommercialEvidenceType,
    ContractState,
    DeliverableKind,
    DeliverableState,
    ExpertState,
    ExternalAuthorizationState,
    ExternalEngagementState,
    FinancialEventType,
    PatentStatus,
    ProfessionalRecordKind,
    ProfessionalRecordState,
    ProviderType,
    QuoteState,
    SourceTier,
    VerificationState,
)
from medical_one_person.domain.mail import (
    MailAccountState,
    MailAttemptState,
    MailAuthorizationState,
    MailDraftState,
    MailMode,
    MailThreadLinkState,
)
from medical_one_person.domain.opportunities import OpportunityStatus, Track
from medical_one_person.domain.plans import PlanStatus, ReviewDecision
from medical_one_person.domain.projects import ProjectStage, ProjectStatus
from medical_one_person.domain.workflows import (
    AssessmentRecommendation,
    AssessmentStatus,
    StageDecisionStatus,
)
from medical_one_person.infrastructure.db.base import Base

PROJECT_STAGE_VALUES = ", ".join(f"'{value.value}'" for value in ProjectStage)
PROJECT_STATUS_VALUES = ", ".join(f"'{value.value}'" for value in ProjectStatus)
OPPORTUNITY_TRACK_VALUES = ", ".join(f"'{value.value}'" for value in Track)
OPPORTUNITY_STATUS_VALUES = ", ".join(f"'{value.value}'" for value in OpportunityStatus)
PLAN_STATUS_VALUES = ", ".join(f"'{value.value}'" for value in PlanStatus)
REVIEW_DECISION_VALUES = ", ".join(f"'{value.value}'" for value in ReviewDecision)
ASSESSMENT_STATUS_VALUES = ", ".join(f"'{value.value}'" for value in AssessmentStatus)
ASSESSMENT_RECOMMENDATION_VALUES = ", ".join(
    f"'{value.value}'" for value in AssessmentRecommendation
)
STAGE_DECISION_VALUES = ", ".join(f"'{value.value}'" for value in StageDecisionStatus)
DATASET_VERSION_KIND_VALUES = ", ".join(f"'{value.value}'" for value in DatasetVersionKind)
DATASET_VERSION_STATE_VALUES = ", ".join(f"'{value.value}'" for value in DatasetVersionState)
STATISTICAL_METHOD_VALUES = ", ".join(f"'{value.value}'" for value in StatisticalMethod)
ANALYSIS_STATE_VALUES = ", ".join(f"'{value.value}'" for value in AnalysisState)
EXPORT_FORMAT_VALUES = ", ".join(f"'{value.value}'" for value in ExportFormat)
EXPORT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in ExportState)
EXPORT_VALIDATION_VALUES = ", ".join(
    f"'{value.value}'" for value in ExportValidationStatus
)
MAIL_MODE_VALUES = ", ".join(f"'{value.value}'" for value in MailMode)
MAIL_ACCOUNT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in MailAccountState)
MAIL_THREAD_LINK_VALUES = ", ".join(f"'{value.value}'" for value in MailThreadLinkState)
MAIL_DRAFT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in MailDraftState)
MAIL_AUTHORIZATION_STATE_VALUES = ", ".join(
    f"'{value.value}'" for value in MailAuthorizationState
)
MAIL_ATTEMPT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in MailAttemptState)
PROVIDER_TYPE_VALUES = ", ".join(f"'{value.value}'" for value in ProviderType)
VERIFICATION_STATE_VALUES = ", ".join(f"'{value.value}'" for value in VerificationState)
EXPERT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in ExpertState)
ENGAGEMENT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in ExternalEngagementState)
QUOTE_STATE_VALUES = ", ".join(f"'{value.value}'" for value in QuoteState)
CONTRACT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in ContractState)
DELIVERABLE_KIND_VALUES = ", ".join(f"'{value.value}'" for value in DeliverableKind)
DELIVERABLE_STATE_VALUES = ", ".join(f"'{value.value}'" for value in DeliverableState)
PROFESSIONAL_RECORD_KIND_VALUES = ", ".join(
    f"'{value.value}'" for value in ProfessionalRecordKind
)
PROFESSIONAL_RECORD_STATE_VALUES = ", ".join(
    f"'{value.value}'" for value in ProfessionalRecordState
)
SOURCE_TIER_VALUES = ", ".join(f"'{value.value}'" for value in SourceTier)
FINANCIAL_EVENT_VALUES = ", ".join(f"'{value.value}'" for value in FinancialEventType)
COMMERCIAL_EVIDENCE_VALUES = ", ".join(
    f"'{value.value}'" for value in CommercialEvidenceType
)
PATENT_STATUS_VALUES = ", ".join(f"'{value.value}'" for value in PatentStatus)
EXTERNAL_AUTHORIZATION_STATE_VALUES = ", ".join(
    f"'{value.value}'" for value in ExternalAuthorizationState
)
AUDIT_TARGET_TYPE_VALUES = ", ".join(f"'{value.value}'" for value in AuditTargetType)
AUDIT_STATE_VALUES = ", ".join(f"'{value.value}'" for value in AuditState)
AUDIT_FINDING_STATUS_VALUES = ", ".join(
    f"'{value.value}'" for value in AuditFindingStatus
)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("workspace_id", "display_name"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    session_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_projects_workspace_id"),
        ForeignKeyConstraint(
            ["workspace_id", "parent_project_id"],
            ["projects.workspace_id", "projects.id"],
            name="parent_project_same_workspace",
        ),
        CheckConstraint(f"stage IN ({PROJECT_STAGE_VALUES})", name="project_stage"),
        CheckConstraint(f"status IN ({PROJECT_STATUS_VALUES})", name="project_status"),
        CheckConstraint("revision >= 1", name="project_revision_positive"),
        Index("ix_projects_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default=ProjectStage.DRAFT.value)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProjectStatus.DRAFT.value
    )
    parent_project_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    charter_version: Mapped[str | None] = mapped_column(String(100))
    policy_bundle_id: Mapped[str | None] = mapped_column(String(100))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectVersion(Base):
    __tablename__ = "project_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "project_revision"),
        CheckConstraint("project_revision >= 1", name="project_version_positive"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="project_version_same_workspace",
        ),
        Index("ix_project_versions_project_revision", "project_id", "project_revision"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    charter_version: Mapped[str | None] = mapped_column(String(100))
    policy_bundle_id: Mapped[str | None] = mapped_column(String(100))
    changed_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "id",
            name="uq_artifact_versions_project_id_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="conversation_same_workspace",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "conversation_id"],
            ["conversations.project_id", "conversations.id"],
            name="message_same_project",
        ),
        CheckConstraint("speaker IN ('user', 'agent', 'system')", name="message_speaker"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="artifact_same_workspace",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"
    __table_args__ = (
        UniqueConstraint("artifact_id", "version"),
        UniqueConstraint("project_id", "id"),
        ForeignKeyConstraint(
            ["project_id", "artifact_id"],
            ["artifacts.project_id", "artifacts.id"],
            name="artifact_version_same_project",
        ),
        CheckConstraint("version >= 1", name="artifact_version_positive"),
        CheckConstraint("size_bytes >= 0", name="artifact_size_nonnegative"),
        CheckConstraint("mode IN ('mock', 'live')", name="artifact_mode"),
        CheckConstraint("raw_or_derived IN ('raw', 'derived')", name="artifact_origin"),
        Index("ix_artifact_versions_project_created", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    artifact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    object_key: Mapped[str] = mapped_column(String(200), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    raw_or_derived: Mapped[str] = mapped_column(String(10), nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="not_checked"
    )
    producer: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArtifactExport(Base):
    __tablename__ = "artifact_exports"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_artifact_exports_project_idempotency",
        ),
        UniqueConstraint(
            "project_id",
            "id",
            name="uq_artifact_exports_project_id_id",
        ),
        UniqueConstraint(
            "artifact_version_id",
            name="uq_artifact_exports_artifact_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="artifact_export_same_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "analysis_id"],
            [
                "analysis_runs.workspace_id",
                "analysis_runs.project_id",
                "analysis_runs.id",
            ],
            name="artifact_export_same_analysis",
        ),
        ForeignKeyConstraint(
            ["project_id", "artifact_version_id"],
            ["artifact_versions.project_id", "artifact_versions.id"],
            name="artifact_export_same_version",
        ),
        CheckConstraint(f"format IN ({EXPORT_FORMAT_VALUES})", name="artifact_export_format"),
        CheckConstraint(f"state IN ({EXPORT_STATE_VALUES})", name="artifact_export_state"),
        CheckConstraint(
            f"validation_status IN ({EXPORT_VALIDATION_VALUES})",
            name="artifact_export_validation_status",
        ),
        CheckConstraint("revision >= 1", name="artifact_export_revision_positive"),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="artifact_export_request_hash",
        ),
        CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name="artifact_export_input_sha256",
        ),
        CheckConstraint(
            "report_sha256 ~ '^[0-9a-f]{64}$'",
            name="artifact_export_report_sha256",
        ),
        CheckConstraint(
            "preview_pdf_sha256 IS NULL OR preview_pdf_sha256 ~ '^[0-9a-f]{64}$'",
            name="artifact_export_preview_pdf_sha256",
        ),
        CheckConstraint(
            "preview_png_sha256 IS NULL OR preview_png_sha256 ~ '^[0-9a-f]{64}$'",
            name="artifact_export_preview_png_sha256",
        ),
        CheckConstraint(
            "preview_pdf_size_bytes IS NULL OR preview_pdf_size_bytes >= 0",
            name="artifact_export_preview_pdf_size",
        ),
        CheckConstraint(
            "preview_png_size_bytes IS NULL OR preview_png_size_bytes >= 0",
            name="artifact_export_preview_png_size",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 1",
            name="artifact_export_page_count",
        ),
        Index("ix_artifact_exports_project_created", "project_id", "created_at"),
        Index("ix_artifact_exports_analysis_created", "analysis_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    analysis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    artifact_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(400), nullable=False)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    structured_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preview_pdf_object_key: Mapped[str | None] = mapped_column(String(300))
    preview_pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    preview_pdf_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    preview_png_object_key: Mapped[str | None] = mapped_column(String(300))
    preview_png_sha256: Mapped[str | None] = mapped_column(String(64))
    preview_png_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    page_count: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_artifact_exports_created_by_user_id_users",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MailAccount(Base):
    __tablename__ = "mail_accounts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "address", name="uq_mail_accounts_workspace_address"),
        UniqueConstraint("workspace_id", "id", name="uq_mail_accounts_workspace_id"),
        CheckConstraint(f"mode IN ({MAIL_MODE_VALUES})", name="mail_account_mode"),
        CheckConstraint(
            f"state IN ({MAIL_ACCOUNT_STATE_VALUES})",
            name="mail_account_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MailThread(Base):
    __tablename__ = "mail_threads"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "provider_thread_id",
            name="uq_mail_threads_account_provider",
        ),
        UniqueConstraint(
            "workspace_id",
            "account_id",
            "id",
            name="uq_mail_threads_workspace_account_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "account_id"],
            ["mail_accounts.workspace_id", "mail_accounts.id"],
            name="mail_thread_same_account",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="mail_thread_same_project",
        ),
        CheckConstraint(
            f"link_state IN ({MAIL_THREAD_LINK_VALUES})",
            name="mail_thread_link_state",
        ),
        CheckConstraint("revision >= 1", name="mail_thread_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    provider_thread_id: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    link_state: Mapped[str] = mapped_column(String(20), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MailMessage(Base):
    __tablename__ = "mail_messages"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "provider_message_id",
            name="uq_mail_messages_account_provider_message",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "account_id", "thread_id"],
            ["mail_threads.workspace_id", "mail_threads.account_id", "mail_threads.id"],
            name="mail_message_same_thread",
        ),
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="mail_message_direction",
        ),
        CheckConstraint(
            "delivery_state IN ('mock_received', 'mock_sent', 'received', 'sent')",
            name="mail_message_delivery_state",
        ),
        CheckConstraint("body_sha256 ~ '^[0-9a-f]{64}$'", name="mail_message_body_sha"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    thread_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(300), nullable=False)
    internet_message_id: Mapped[str | None] = mapped_column(String(500))
    in_reply_to: Mapped[str | None] = mapped_column(String(500))
    references: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    recipients: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    delivery_state: Mapped[str] = mapped_column(String(30), nullable=False)
    raw_headers: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MailDraft(Base):
    __tablename__ = "mail_drafts"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_mail_drafts_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_mail_drafts_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "account_id"],
            ["mail_accounts.workspace_id", "mail_accounts.id"],
            name="mail_draft_same_account",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="mail_draft_same_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "account_id", "thread_id"],
            ["mail_threads.workspace_id", "mail_threads.account_id", "mail_threads.id"],
            name="mail_draft_same_thread",
        ),
        CheckConstraint(f"state IN ({MAIL_DRAFT_STATE_VALUES})", name="mail_draft_state"),
        CheckConstraint("revision >= 1", name="mail_draft_revision_positive"),
        CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="mail_draft_content_sha"),
        Index("ix_mail_drafts_project_updated", "project_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    thread_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    recipients: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MailDraftAttachment(Base):
    __tablename__ = "mail_draft_attachments"
    __table_args__ = (
        UniqueConstraint(
            "draft_id",
            "source_type",
            "source_id",
            name="uq_mail_draft_attachments_source",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "draft_id"],
            ["mail_drafts.workspace_id", "mail_drafts.project_id", "mail_drafts.id"],
            name="mail_attachment_same_draft",
        ),
        CheckConstraint(
            "source_type IN ('artifact_version', 'knowledge_version')",
            name="mail_attachment_source_type",
        ),
        CheckConstraint("size_bytes >= 0", name="mail_attachment_size_nonnegative"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="mail_attachment_sha"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    draft_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MailSendAuthorization(Base):
    __tablename__ = "mail_send_authorizations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_mail_authorizations_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_mail_authorizations_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "draft_id"],
            ["mail_drafts.workspace_id", "mail_drafts.project_id", "mail_drafts.id"],
            name="mail_authorization_same_draft",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "account_id"],
            ["mail_accounts.workspace_id", "mail_accounts.id"],
            name="mail_authorization_same_account",
        ),
        CheckConstraint(
            f"state IN ({MAIL_AUTHORIZATION_STATE_VALUES})",
            name="mail_authorization_state",
        ),
        CheckConstraint("action = 'mail.send'", name="mail_authorization_action"),
        CheckConstraint(
            "max_sends >= 1 AND used_sends >= 0 AND used_sends <= max_sends",
            name="mail_authorization_send_bounds",
        ),
        CheckConstraint("revision >= 1", name="mail_authorization_revision_positive"),
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="mail_authorization_content_sha",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    draft_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    granted_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    recipients: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    attachment_hashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    max_sends: Mapped[int] = mapped_column(Integer, nullable=False)
    used_sends: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MailSendAttempt(Base):
    __tablename__ = "mail_send_attempts"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_mail_attempts_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_mail_attempts_workspace_project_id",
        ),
        UniqueConstraint("operation_key", name="uq_mail_attempts_operation_key"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "draft_id"],
            ["mail_drafts.workspace_id", "mail_drafts.project_id", "mail_drafts.id"],
            name="mail_attempt_same_draft",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "authorization_id"],
            [
                "mail_send_authorizations.workspace_id",
                "mail_send_authorizations.project_id",
                "mail_send_authorizations.id",
            ],
            name="mail_attempt_same_authorization",
        ),
        CheckConstraint(f"state IN ({MAIL_ATTEMPT_STATE_VALUES})", name="mail_attempt_state"),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="mail_attempt_request_hash"),
        CheckConstraint("body_sha256 ~ '^[0-9a-f]{64}$'", name="mail_attempt_body_sha"),
        Index("ix_mail_attempts_project_created", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    draft_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    authorization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_key: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    recipients: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    attachment_manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(300))
    provider_thread_id: Mapped[str | None] = mapped_column(String(300))
    internet_message_id: Mapped[str | None] = mapped_column(String(500))
    outcome_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExternalOrganization(Base):
    __tablename__ = "external_organizations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_organizations_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_organizations_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="external_organization_same_project",
        ),
        CheckConstraint(
            f"provider_type IN ({PROVIDER_TYPE_VALUES})",
            name="external_organization_provider_type",
        ),
        CheckConstraint(
            f"verification_state IN ({VERIFICATION_STATE_VALUES})",
            name="external_organization_verification_state",
        ),
        CheckConstraint("revision >= 1", name="external_organization_revision_positive"),
        Index("ix_external_organizations_project_type", "project_id", "provider_type"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(40), nullable=False)
    capability_summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    verification_state: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExternalContact(Base):
    __tablename__ = "external_contacts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_contacts_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "organization_id"],
            [
                "external_organizations.workspace_id",
                "external_organizations.project_id",
                "external_organizations.id",
            ],
            name="external_contact_same_organization",
        ),
        CheckConstraint(
            f"verification_state IN ({VERIFICATION_STATE_VALUES})",
            name="external_contact_verification_state",
        ),
        CheckConstraint("revision >= 1", name="external_contact_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    source_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    verification_state: Mapped[str] = mapped_column(String(30), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExternalExpert(Base):
    __tablename__ = "external_experts"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_experts_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_experts_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="external_expert_same_project",
        ),
        CheckConstraint(f"state IN ({EXPERT_STATE_VALUES})", name="external_expert_state"),
        CheckConstraint("revision >= 1", name="external_expert_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    expertise: Mapped[str] = mapped_column(Text, nullable=False)
    public_source_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320))
    conflict_notes: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExternalEngagement(Base):
    __tablename__ = "external_engagements"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_engagements_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_engagements_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "organization_id"],
            [
                "external_organizations.workspace_id",
                "external_organizations.project_id",
                "external_organizations.id",
            ],
            name="external_engagement_same_organization",
        ),
        CheckConstraint(
            f"state IN ({ENGAGEMENT_STATE_VALUES})",
            name="external_engagement_state",
        ),
        CheckConstraint(
            "scope_sha256 ~ '^[0-9a-f]{64}$'",
            name="external_engagement_scope_sha",
        ),
        CheckConstraint("revision >= 1", name="external_engagement_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExternalQuote(Base):
    __tablename__ = "external_quotes"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_quotes_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_quotes_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_quote_same_engagement",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "document_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="external_quote_same_document",
        ),
        CheckConstraint(f"state IN ({QUOTE_STATE_VALUES})", name="external_quote_state"),
        CheckConstraint(
            "scope_sha256 ~ '^[0-9a-f]{64}$'",
            name="external_quote_scope_sha",
        ),
        CheckConstraint(
            "amount IS NULL OR amount >= 0",
            name="external_quote_amount_nonnegative",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    engagement_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    amount: Mapped[decimal.Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    tax_included: Mapped[bool | None] = mapped_column(Boolean)
    shipping_included: Mapped[bool | None] = mapped_column(Boolean)
    assumptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    excluded_work: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExternalContract(Base):
    __tablename__ = "external_contracts"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_contracts_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_contracts_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_contract_same_engagement",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "quote_id"],
            [
                "external_quotes.workspace_id",
                "external_quotes.project_id",
                "external_quotes.id",
            ],
            name="external_contract_same_quote",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "document_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="external_contract_same_document",
        ),
        CheckConstraint(f"state IN ({CONTRACT_STATE_VALUES})", name="external_contract_state"),
        CheckConstraint("revision >= 1", name="external_contract_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    engagement_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    quote_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    terms_summary: Mapped[str] = mapped_column(Text, nullable=False)
    document_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    internal_signed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    external_signed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExternalDeliverable(Base):
    __tablename__ = "external_deliverables"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_deliverables_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_deliverables_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_deliverable_same_engagement",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "knowledge_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="external_deliverable_same_document",
        ),
        CheckConstraint(
            f"kind IN ({DELIVERABLE_KIND_VALUES})",
            name="external_deliverable_kind",
        ),
        CheckConstraint(
            f"state IN ({DELIVERABLE_STATE_VALUES})",
            name="external_deliverable_state",
        ),
        CheckConstraint(
            "reviewer_role IS NULL OR reviewer_role IN ('A25', 'A26')",
            name="external_deliverable_reviewer",
        ),
        CheckConstraint("revision >= 1", name="external_deliverable_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    engagement_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    expected_items: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    knowledge_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    missing_items: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    receipt_summary: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_role: Mapped[str | None] = mapped_column(String(3))
    review_summary: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProfessionalRecord(Base):
    __tablename__ = "professional_records"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_professional_records_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_professional_records_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="professional_record_same_project",
        ),
        CheckConstraint(
            f"kind IN ({PROFESSIONAL_RECORD_KIND_VALUES})",
            name="professional_record_kind",
        ),
        CheckConstraint(
            f"state IN ({PROFESSIONAL_RECORD_STATE_VALUES})",
            name="professional_record_state",
        ),
        CheckConstraint(
            f"source_tier IN ({SOURCE_TIER_VALUES})",
            name="professional_record_source_tier",
        ),
        CheckConstraint(
            "patent_status IS NULL OR patent_status IN "
            f"({PATENT_STATUS_VALUES})",
            name="professional_record_patent_status",
        ),
        CheckConstraint(
            "financial_event_type IS NULL OR financial_event_type IN "
            f"({FINANCIAL_EVENT_VALUES})",
            name="professional_record_financial_event",
        ),
        CheckConstraint(
            "commercial_evidence_type IS NULL OR commercial_evidence_type IN "
            f"({COMMERCIAL_EVIDENCE_VALUES})",
            name="professional_record_commercial_evidence",
        ),
        CheckConstraint("amount IS NULL OR amount >= 0", name="professional_record_amount"),
        CheckConstraint("revision >= 1", name="professional_record_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source_tier: Mapped[str] = mapped_column(String(30), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(500))
    source_ref: Mapped[str | None] = mapped_column(String(2000))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    market: Mapped[str | None] = mapped_column(String(200))
    product_scope: Mapped[str | None] = mapped_column(String(1000))
    jurisdiction: Mapped[str | None] = mapped_column(String(200))
    patent_status: Mapped[str | None] = mapped_column(String(30))
    application_number: Mapped[str | None] = mapped_column(String(200))
    publication_number: Mapped[str | None] = mapped_column(String(200))
    financial_event_type: Mapped[str | None] = mapped_column(String(30))
    amount: Mapped[decimal.Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    commercial_evidence_type: Mapped[str | None] = mapped_column(String(30))
    facts: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    record_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExternalAuthorization(Base):
    __tablename__ = "external_authorizations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_external_authorizations_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_external_authorizations_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "engagement_id"],
            [
                "external_engagements.workspace_id",
                "external_engagements.project_id",
                "external_engagements.id",
            ],
            name="external_authorization_same_engagement",
        ),
        CheckConstraint(
            f"state IN ({EXTERNAL_AUTHORIZATION_STATE_VALUES})",
            name="external_authorization_state",
        ),
        CheckConstraint("amount_max > 0", name="external_authorization_amount_positive"),
        CheckConstraint("revision >= 1", name="external_authorization_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    engagement_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action_scope: Mapped[str] = mapped_column(Text, nullable=False)
    scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_max: Mapped[decimal.Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    granted_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditRun(Base):
    __tablename__ = "audit_runs"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_audit_runs_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_audit_runs_workspace_project_id",
        ),
        UniqueConstraint(
            "project_id",
            "target_type",
            "target_id",
            "reviewer_role",
            "review_version",
            name="uq_audit_runs_target_reviewer_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="audit_run_same_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "linked_task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="audit_run_linked_task",
        ),
        CheckConstraint(
            f"target_type IN ({AUDIT_TARGET_TYPE_VALUES})",
            name="audit_run_target_type",
        ),
        CheckConstraint(f"state IN ({AUDIT_STATE_VALUES})", name="audit_run_state"),
        CheckConstraint("reviewer_role IN ('A25', 'A26')", name="audit_run_reviewer_role"),
        CheckConstraint(
            "producer_role IS NULL OR producer_role ~ '^A(0[1-9]|1[0-9]|2[0-6])$'",
            name="audit_run_producer_role",
        ),
        CheckConstraint(
            "target_sha256 ~ '^[0-9a-f]{64}$'",
            name="audit_run_target_sha",
        ),
        CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name="audit_run_input_sha",
        ),
        CheckConstraint("review_version >= 1", name="audit_run_review_version_positive"),
        Index("ix_audit_runs_project_created", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    linked_task_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    target_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(3), nullable=False)
    producer_role: Mapped[str | None] = mapped_column(String(3))
    method: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    downstream_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    review_version: Mapped[int] = mapped_column(Integer, nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditFinding(Base):
    __tablename__ = "audit_findings"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_audit_findings_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "audit_id"],
            ["audit_runs.workspace_id", "audit_runs.project_id", "audit_runs.id"],
            name="audit_finding_same_run",
        ),
        CheckConstraint(
            "severity IN ('critical', 'major', 'minor')",
            name="audit_finding_severity",
        ),
        CheckConstraint(
            f"status IN ({AUDIT_FINDING_STATUS_VALUES})",
            name="audit_finding_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    audit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_objects: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvaluation(Base):
    __tablename__ = "audit_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_audit_evaluations_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="audit_evaluation_same_project",
        ),
        CheckConstraint(
            "fixture_sha256 ~ '^[0-9a-f]{64}$'",
            name="audit_evaluation_fixture_sha",
        ),
        CheckConstraint("cases >= 1", name="audit_evaluation_cases_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    fixture_name: Mapped[str] = mapped_column(String(200), nullable=False)
    fixture_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    cases: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    case_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


TRASH_STATE_VALUES = "'trashed', 'restored', 'purged'"
BACKUP_STATE_VALUES = "'completed', 'failed'"
RESTORE_STATE_VALUES = "'verified', 'failed'"


class TrashEntry(Base):
    __tablename__ = "trash_entries"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "document_id",
            name="uq_trash_entries_project_document",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_trash_entries_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="trash_entry_same_project",
        ),
        CheckConstraint(
            f"state IN ({TRASH_STATE_VALUES})",
            name="trash_entry_state",
        ),
        CheckConstraint("reference_count >= 0", name="trash_entry_reference_count"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id"),
        nullable=False,
    )
    previous_access_states: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    reference_count: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    purge_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackupSnapshot(Base):
    __tablename__ = "backup_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_backup_snapshots_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_backup_snapshots_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="backup_snapshot_same_project",
        ),
        CheckConstraint(
            f"state IN ({BACKUP_STATE_VALUES})",
            name="backup_snapshot_state",
        ),
        CheckConstraint(
            "backup_sha256 IS NULL OR backup_sha256 ~ '^[0-9a-f]{64}$'",
            name="backup_snapshot_backup_sha",
        ),
        CheckConstraint(
            "plaintext_sha256 IS NULL OR plaintext_sha256 ~ '^[0-9a-f]{64}$'",
            name="backup_snapshot_plaintext_sha",
        ),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="backup_snapshot_request_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    backup_sha256: Mapped[str | None] = mapped_column(String(64))
    plaintext_sha256: Mapped[str | None] = mapped_column(String(64))
    encrypted_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    kdf: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class RestoreCheck(Base):
    __tablename__ = "restore_checks"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_restore_checks_workspace_project_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "backup_id"],
            [
                "backup_snapshots.workspace_id",
                "backup_snapshots.project_id",
                "backup_snapshots.id",
            ],
            name="restore_check_same_backup",
        ),
        CheckConstraint(
            f"state IN ({RESTORE_STATE_VALUES})",
            name="restore_check_state",
        ),
        CheckConstraint("object_count >= 0", name="restore_check_object_count"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    backup_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    object_count: Mapped[int] = mapped_column(Integer, nullable=False)
    table_counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ProjectEvent(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("project_id", "project_seq"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="event_same_workspace",
        ),
        CheckConstraint("project_seq >= 1", name="event_sequence_positive"),
        Index("ix_events_project_sequence", "project_id", "project_seq"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    object_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CommandReceipt(Base):
    __tablename__ = "command_receipts"
    __table_args__ = (
        UniqueConstraint("actor_user_id", "route", "idempotency_key"),
        Index("ix_command_receipts_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    actor_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    route: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ToolAuditEvent(Base):
    __tablename__ = "tool_audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="tool_audit_same_workspace",
        ),
        CheckConstraint(
            "state IN ('authorized', 'succeeded', 'failed', 'denied')",
            name="tool_audit_state",
        ),
        Index("ix_tool_audit_project_created", "project_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(String(20), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


TASK_STATES = (
    "draft",
    "needs_input",
    "ready",
    "queued",
    "running",
    "submitted",
    "accepted",
    "rework",
    "waiting_external",
    "paused",
    "failed",
    "cancelled",
)
TASK_STATE_VALUES = ", ".join(f"'{value}'" for value in TASK_STATES)
INPUT_VALIDITY_VALUES = "'current', 'stale', 'under_review'"
JOB_STATE_VALUES = "'pending', 'queued', 'running', 'succeeded', 'failed', 'dead', 'cancelled'"
ATTEMPT_STATE_VALUES = "'running', 'succeeded', 'failed', 'interrupted'"
RESERVATION_STATE_VALUES = "'reserved', 'settled', 'released', 'uncertain'"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "dedupe_key"),
        UniqueConstraint("workspace_id", "project_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="task_same_workspace",
        ),
        CheckConstraint(f"state IN ({TASK_STATE_VALUES})", name="task_state"),
        CheckConstraint(
            f"input_validity IN ({INPUT_VALIDITY_VALUES})",
            name="task_input_validity",
        ),
        CheckConstraint("mode IN ('mock', 'live')", name="task_mode"),
        CheckConstraint("revision >= 1", name="task_revision_positive"),
        CheckConstraint("max_attempts >= 1", name="task_max_attempts_positive"),
        Index("ix_tasks_project_state", "project_id", "state"),
        Index("ix_tasks_assignee_state", "assignee_role", "state"),
        Index("ix_tasks_project_input_validity", "project_id", "input_validity"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    assignee_role: Mapped[str] = mapped_column(String(20), nullable=False)
    role_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_validity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="current",
        server_default="current",
    )
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_snapshot_sha256: Mapped[str | None] = mapped_column(String(64))
    input_invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_invalidated_reason: Mapped[str | None] = mapped_column(Text)
    input_invalidated_by: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    deliverable_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    acceptance_policy: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False, default="mock")
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TaskVersion(Base):
    __tablename__ = "task_versions"
    __table_args__ = (
        UniqueConstraint("task_id", "task_revision"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "task_id",
            "task_revision",
            name="uq_task_versions_workspace_project_task_revision",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "task_id",
            "id",
            name="uq_task_versions_workspace_project_task_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="task_version_same_task",
        ),
        CheckConstraint(
            f"input_validity IN ({INPUT_VALIDITY_VALUES})",
            name="task_version_input_validity",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    input_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_validity: Mapped[str] = mapped_column(String(20), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_snapshot_sha256: Mapped[str | None] = mapped_column(String(64))
    input_invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_invalidated_reason: Mapped[str | None] = mapped_column(Text)
    input_invalidated_by: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    role_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="dependent_task_same_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "depends_on_task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="upstream_task_same_project",
        ),
        CheckConstraint("task_id <> depends_on_task_id", name="task_no_self_dependency"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    depends_on_task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("project_id", "name"),
        UniqueConstraint("workspace_id", "project_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="budget_same_workspace",
        ),
        CheckConstraint("limit_amount >= 0", name="budget_limit_nonnegative"),
        CheckConstraint("reserved_amount >= 0", name="budget_reserved_nonnegative"),
        CheckConstraint("spent_amount >= 0", name="budget_spent_nonnegative"),
        CheckConstraint("revision >= 1", name="budget_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    limit_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reserved_amount: Mapped[decimal.Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=decimal.Decimal("0")
    )
    spent_amount: Mapped[decimal.Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=decimal.Decimal("0")
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BudgetReservation(Base):
    __tablename__ = "budget_reservations"
    __table_args__ = (
        UniqueConstraint("budget_id", "operation_key"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="budget_reservation_same_workspace",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "budget_id"],
            ["budgets.workspace_id", "budgets.project_id", "budgets.id"],
            name="budget_reservation_same_budget",
        ),
        CheckConstraint("amount > 0", name="reservation_amount_positive"),
        CheckConstraint(
            f"state IN ({RESERVATION_STATE_VALUES})",
            name="reservation_state",
        ),
        UniqueConstraint("workspace_id", "project_id", "budget_id", "id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    budget_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[decimal.Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BudgetLedgerEntry(Base):
    __tablename__ = "budget_ledger_entries"
    __table_args__ = (
        UniqueConstraint("project_id", "ledger_key"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "budget_id", "reservation_id"],
            [
                "budget_reservations.workspace_id",
                "budget_reservations.project_id",
                "budget_reservations.budget_id",
                "budget_reservations.id",
            ],
            name="ledger_same_reservation",
        ),
        CheckConstraint(
            "kind IN ('reserve', 'settle', 'release')",
            name="ledger_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    budget_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    reservation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    ledger_key: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    reserved_delta: Mapped[decimal.Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    spent_delta: Mapped[decimal.Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxMessage(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        UniqueConstraint("project_id", "unique_key"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="outbox_same_task",
        ),
        CheckConstraint(
            "state IN ('pending', 'dispatched', 'failed')",
            name="outbox_state",
        ),
        Index("ix_outbox_pending_available", "state", "available_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    unique_key: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("project_id", "job_key"),
        UniqueConstraint("workspace_id", "project_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="job_same_task",
        ),
        CheckConstraint(f"state IN ({JOB_STATE_VALUES})", name="job_state"),
        CheckConstraint("fence_token >= 0", name="job_fence_nonnegative"),
        CheckConstraint("attempts >= 0", name="job_attempts_nonnegative"),
        CheckConstraint("max_attempts >= 1", name="job_max_attempts_positive"),
        Index("ix_jobs_claim", "state", "available_at", "priority", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    job_key: Mapped[str] = mapped_column(String(200), nullable=False)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    lease_owner: Mapped[str | None] = mapped_column(String(200))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fence_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskAttempt(Base):
    __tablename__ = "task_attempts"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="attempt_same_task",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "job_id"],
            ["jobs.workspace_id", "jobs.project_id", "jobs.id"],
            name="attempt_same_job",
        ),
        CheckConstraint(f"state IN ({ATTEMPT_STATE_VALUES})", name="attempt_state"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[str] = mapped_column(String(200), nullable=False)
    fence_token: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentInstance(Base):
    __tablename__ = "agent_instances"
    __table_args__ = (
        UniqueConstraint("project_id", "role_id", "role_version"),
        UniqueConstraint("workspace_id", "project_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="agent_instance_same_workspace",
        ),
        CheckConstraint(
            "status IN ('inactive', 'active', 'disabled')",
            name="agent_instance_status",
        ),
        CheckConstraint("role_version >= 1", name="agent_role_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    role_id: Mapped[str] = mapped_column(String(3), nullable=False)
    role_version: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_scope: Mapped[str] = mapped_column(String(50), nullable=False)
    context_namespace: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("project_id", "run_key"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="agent_run_same_task",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "job_id"],
            ["jobs.workspace_id", "jobs.project_id", "jobs.id"],
            name="agent_run_same_job",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "agent_instance_id"],
            [
                "agent_instances.workspace_id",
                "agent_instances.project_id",
                "agent_instances.id",
            ],
            name="agent_run_same_instance",
        ),
        UniqueConstraint("workspace_id", "project_id", "agent_instance_id", "id"),
        CheckConstraint("mode IN ('mock', 'live')", name="agent_run_mode"),
        CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="agent_run_state",
        ),
        Index("ix_agent_runs_task_created", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_instance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_key: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    role_id: Mapped[str] = mapped_column(String(3), nullable=False)
    role_version: Mapped[int] = mapped_column(Integer, nullable=False)
    theory_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_bundle: Mapped[str] = mapped_column(String(100), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    output_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    independent_context: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SkillRun(Base):
    __tablename__ = "skill_runs"
    __table_args__ = (
        UniqueConstraint("project_id", "run_key"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="skill_run_same_task",
        ),
        CheckConstraint("mode IN ('mock', 'live')", name="skill_run_mode"),
        CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'failed', 'denied', 'unavailable')",
            name="skill_run_state",
        ),
        Index("ix_skill_runs_task_created", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_version: Mapped[int] = mapped_column(Integer, nullable=False)
    run_key: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    input_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    output_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    artifact_manifest: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Library(Base):
    __tablename__ = "libraries"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_libraries_workspace_library"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_libraries_workspace_project_library",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "scope",
            "name",
            name="uq_libraries_workspace_project_scope_name",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="library_same_project",
        ),
        CheckConstraint(
            "scope IN ('project_private', 'workspace_shared', 'public_reference')",
            name="library_scope",
        ),
        CheckConstraint(
            "(scope <> 'project_private') OR project_id IS NOT NULL",
            name="private_library_project_required",
        ),
        CheckConstraint("acl_revision >= 1", name="library_acl_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    acl_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LibraryGrant(Base):
    __tablename__ = "library_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "library_id"],
            ["libraries.workspace_id", "libraries.id"],
            name="grant_same_library",
        ),
        UniqueConstraint("library_id", "grantee_project_id", "grantee_role"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    grantee_project_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    grantee_role: Mapped[str | None] = mapped_column(String(20))
    actions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UploadSession(Base):
    __tablename__ = "upload_sessions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_upload_sessions_workspace_session"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "library_id"],
            ["libraries.workspace_id", "libraries.project_id", "libraries.id"],
            name="upload_session_same_library",
        ),
        CheckConstraint(
            "state IN ('active', 'committed', 'cancelled', 'expired')",
            name="upload_session_state",
        ),
        CheckConstraint("expected_bytes > 0", name="upload_expected_bytes_positive"),
        CheckConstraint("chunk_size > 0", name="upload_chunk_size_positive"),
        Index("ix_upload_sessions_expiry", "state", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    uploader_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    media_type_hint: Mapped[str | None] = mapped_column(String(200))
    expected_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_sha256: Mapped[str | None] = mapped_column(String(64))
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reserved_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    committed_blob_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    committed_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    committed_job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UploadPart(Base):
    __tablename__ = "upload_parts"
    __table_args__ = (
        UniqueConstraint("session_id", "offset"),
        ForeignKeyConstraint(
            ["workspace_id", "session_id"],
            ["upload_sessions.workspace_id", "upload_sessions.id"],
            name="upload_part_same_session",
        ),
        CheckConstraint('"offset" >= 0', name="upload_part_offset_nonnegative"),
        CheckConstraint("length > 0", name="upload_part_length_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    offset: Mapped[int] = mapped_column(BigInteger, nullable=False)
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    part_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    staging_key: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeBlob(Base):
    __tablename__ = "knowledge_blobs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_knowledge_blobs_workspace_blob"),
        UniqueConstraint("workspace_id", "content_hash"),
        CheckConstraint("size_bytes >= 0", name="knowledge_blob_size_nonnegative"),
        CheckConstraint("ref_count >= 0", name="knowledge_blob_refs_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    object_key: Mapped[str] = mapped_column(String(300), nullable=False)
    ref_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "library_id"],
            ["libraries.workspace_id", "libraries.id"],
            name="document_same_library",
        ),
        UniqueConstraint("workspace_id", "library_id", "id"),
        CheckConstraint("revision >= 1", name="document_revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeDocumentVersion(Base):
    __tablename__ = "knowledge_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_label"),
        UniqueConstraint("workspace_id", "library_id", "document_id", "id"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_document_versions_workspace_project_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id"],
            [
                "knowledge_documents.workspace_id",
                "knowledge_documents.library_id",
                "knowledge_documents.id",
            ],
            name="version_same_document",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "blob_id"],
            ["knowledge_blobs.workspace_id", "knowledge_blobs.id"],
            name="version_same_blob",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="version_same_project",
        ),
        CheckConstraint(
            "ingest_state IN ('stored', 'queued', 'extracting', 'indexing', "
            "'ready', 'partial', 'failed')",
            name="ingest_state",
        ),
        CheckConstraint(
            "evidence_status IN ('unreviewed', 'needs_review', 'reviewed_for_scope', 'disputed')",
            name="evidence_status",
        ),
        CheckConstraint(
            "version_status IN ('current', 'historical', 'withdrawn')",
            name="version_status",
        ),
        CheckConstraint(
            "access_state IN ('active', 'quarantined', 'trashed', 'purged')",
            name="access_state",
        ),
        CheckConstraint(
            "cloud_policy IN ('local_only', 'approved_cloud')",
            name="cloud_policy",
        ),
        Index(
            "ix_document_versions_project_current",
            "project_id",
            "version_status",
        ),
        Index("ix_document_versions_ingest", "library_id", "ingest_state"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    blob_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    origin: Mapped[str] = mapped_column(String(100), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(100), nullable=False)
    confidentiality: Mapped[str] = mapped_column(String(50), nullable=False)
    cloud_policy: Mapped[str] = mapped_column(String(30), nullable=False)
    source_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingest_state: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False)
    version_status: Mapped[str] = mapped_column(String(20), nullable=False)
    access_state: Mapped[str] = mapped_column(String(20), nullable=False)


class IngestJob(Base):
    __tablename__ = "ingest_jobs"
    __table_args__ = (
        UniqueConstraint("version_id"),
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id", "version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.library_id",
                "knowledge_document_versions.document_id",
                "knowledge_document_versions.id",
            ],
            name="ingest_job_same_version",
        ),
        CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'partial', 'failed')",
            name="ingest_job_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_document_extractions_workspace_extraction"),
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id", "version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.library_id",
                "knowledge_document_versions.document_id",
                "knowledge_document_versions.id",
            ],
            name="extraction_same_version",
        ),
        UniqueConstraint("version_id", "extractor_version", "config_hash"),
        CheckConstraint(
            "state IN ('running', 'succeeded', 'partial', 'failed')",
            name="extraction_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(100), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    coverage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quality_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourcePassage(Base):
    __tablename__ = "source_passages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "extraction_id"],
            ["document_extractions.workspace_id", "document_extractions.id"],
            name="passage_same_extraction",
        ),
        Index("ix_source_passages_extraction", "extraction_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    extraction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_quality: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ExtractionTable(Base):
    __tablename__ = "extraction_tables"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "extraction_id"],
            ["document_extractions.workspace_id", "document_extractions.id"],
            name="table_same_extraction",
        ),
        Index("ix_extraction_tables_extraction", "extraction_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    extraction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    table_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id", "version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.library_id",
                "knowledge_document_versions.document_id",
                "knowledge_document_versions.id",
            ],
            name="chunk_same_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "extraction_id"],
            ["document_extractions.workspace_id", "document_extractions.id"],
            name="chunk_same_extraction",
        ),
        UniqueConstraint("version_id", "extraction_id", "chunk_index"),
        CheckConstraint("chunk_index >= 0", name="chunk_index_nonnegative"),
        Index("ix_knowledge_chunks_version", "version_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    extraction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    object_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    object_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_quality: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    search_index_version: Mapped[str] = mapped_column(String(50), nullable=False)


class Citation(Base):
    __tablename__ = "citations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id", "version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.library_id",
                "knowledge_document_versions.document_id",
                "knowledge_document_versions.id",
            ],
            name="citation_same_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "chunk_id"],
            ["knowledge_chunks.workspace_id", "knowledge_chunks.id"],
            name="citation_same_chunk",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="citation_same_task",
        ),
        CheckConstraint(
            "review_status IN ('unreviewed', 'verified', 'disputed', 'invalid')",
            name="citation_review_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    extraction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quoted_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RetrievalSnapshot(Base):
    __tablename__ = "retrieval_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="snapshot_same_task",
        ),
        CheckConstraint("top_k >= 1 AND top_k <= 40", name="snapshot_top_k"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    permitted_version_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    selected_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    selected_content_hashes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    acl_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("workspace_id", "project_id", "id"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="claim_same_project",
        ),
        CheckConstraint("current_version >= 1", name="claim_current_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClaimVersion(Base):
    __tablename__ = "claim_versions"
    __table_args__ = (
        UniqueConstraint("claim_id", "revision"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "claim_id"],
            ["claims.workspace_id", "claims.project_id", "claims.id"],
            name="claim_version_same_claim",
        ),
        CheckConstraint("revision >= 1", name="claim_revision_positive"),
        CheckConstraint(
            "status IN ('hypothesis', 'inferred', 'supported', 'contradicted', "
            "'conflicted', 'unknown', 'stale', 'disputed')",
            name="claim_status",
        ),
        UniqueConstraint("workspace_id", "project_id", "claim_id", "id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    claim_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    species_or_population: Mapped[str | None] = mapped_column(String(300))
    intervention: Mapped[str | None] = mapped_column(Text)
    comparator: Mapped[str | None] = mapped_column(Text)
    endpoint: Mapped[str | None] = mapped_column(Text)
    analysis_set: Mapped[str | None] = mapped_column(String(200))
    sample_size: Mapped[int | None] = mapped_column(Integer)
    directness: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "claim_id", "claim_version_id"],
            [
                "claim_versions.workspace_id",
                "claim_versions.project_id",
                "claim_versions.claim_id",
                "claim_versions.id",
            ],
            name="evidence_link_same_claim_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "citation_id"],
            ["citations.workspace_id", "citations.id"],
            name="evidence_link_same_citation",
        ),
        CheckConstraint(
            "stance IN ('supports', 'refutes', 'context')",
            name="evidence_link_stance",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    claim_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    claim_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    citation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    stance: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SourceReview(Base):
    __tablename__ = "source_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id", "version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.library_id",
                "knowledge_document_versions.document_id",
                "knowledge_document_versions.id",
            ],
            name="source_review_same_version",
        ),
        CheckConstraint(
            "outcome IN ('verified_scope', 'issues_found', 'disputed')",
            name="source_review_outcome",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(300), nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ImpactReview(Base):
    __tablename__ = "impact_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "library_id", "document_id"],
            [
                "knowledge_documents.workspace_id",
                "knowledge_documents.library_id",
                "knowledge_documents.id",
            ],
            name="impact_same_document",
        ),
        CheckConstraint(
            "state IN ('pending', 'resolved', 'dismissed')",
            name="impact_review_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    library_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    previous_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    changed_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    affected_objects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProvenanceEdge(Base):
    __tablename__ = "provenance_edges"
    __table_args__ = (
        CheckConstraint(
            "relation IN ('supports', 'refutes', 'derived_from', 'used_by', "
            "'supersedes', 'version_of')",
            name="provenance_relation",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    from_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    to_type: Mapped[str] = mapped_column(String(50), nullable=False)
    to_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    relation: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ScientificBriefRecord(Base):
    __tablename__ = "scientific_briefs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "brief_version",
            name="uq_scientific_briefs_workspace_project_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="brief_same_project",
        ),
        CheckConstraint("brief_version >= 1", name="brief_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    brief_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_scientific_briefs_created_by_user_id_users",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="opportunity_same_project",
        ),
        CheckConstraint(
            f"status IN ({OPPORTUNITY_STATUS_VALUES})",
            name="opportunity_status",
        ),
        CheckConstraint(
            f"track IN ({OPPORTUNITY_TRACK_VALUES})",
            name="opportunity_track",
        ),
        CheckConstraint("current_version >= 1", name="opportunity_current_version_positive"),
        CheckConstraint("revision >= 1", name="opportunity_revision_positive"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_opportunities_workspace_project_opportunity",
        ),
        Index("ix_opportunities_project_status", "project_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    track: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_opportunities_created_by_user_id_users",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OpportunityVersion(Base):
    __tablename__ = "opportunity_versions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "opportunity_id",
            "version",
            name="uq_opportunity_versions_workspace_project_opportunity_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "opportunity_id"],
            ["opportunities.workspace_id", "opportunities.project_id", "opportunities.id"],
            name="opportunity_version_same_opportunity",
        ),
        CheckConstraint("version >= 1", name="opportunity_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    opportunity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    card: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="decision_same_project",
        ),
        ForeignKeyConstraint(
            [
                "workspace_id",
                "project_id",
                "selected_opportunity_id",
                "selected_opportunity_version",
            ],
            [
                "opportunity_versions.workspace_id",
                "opportunity_versions.project_id",
                "opportunity_versions.opportunity_id",
                "opportunity_versions.version",
            ],
            name="decision_selected_same_opportunity_version",
        ),
        CheckConstraint(
            "kind IN ('opportunity_selection', 'continue', 'revise', 'pause', 'stop')",
            name="decision_kind",
        ),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="decision_request_hash_sha256",
        ),
        UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_decisions_project_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_decisions_workspace_project_decision",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    selected: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    selected_opportunity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    selected_opportunity_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_version_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_decisions_actor_user_id_users",
        ),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "plan_version",
            name="uq_plans_workspace_project_version",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_plans_workspace_project_plan",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="plan_same_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "source_decision_id"],
            ["decisions.workspace_id", "decisions.project_id", "decisions.id"],
            name="plan_source_same_decision",
        ),
        CheckConstraint(f"status IN ({PLAN_STATUS_VALUES})", name="plan_status"),
        CheckConstraint("plan_version >= 1", name="plan_version_positive"),
        CheckConstraint("revision >= 1", name="plan_revision_positive"),
        CheckConstraint("max_nodes >= 1 AND max_nodes <= 20", name="plan_max_nodes"),
        CheckConstraint(
            "max_rework_rounds >= 0 AND max_rework_rounds <= 10",
            name="plan_max_rework_rounds",
        ),
        CheckConstraint(
            "(workflow_id IS NULL AND workflow_version IS NULL "
            "AND workflow_track IS NULL AND workflow_sha256 IS NULL "
            "AND stage_id IS NULL) OR "
            "(workflow_id IS NOT NULL AND workflow_version IS NOT NULL "
            "AND workflow_track IS NOT NULL AND workflow_sha256 IS NOT NULL "
            "AND stage_id IS NOT NULL)",
            name="plan_workflow_fields_together",
        ),
        CheckConstraint(
            f"workflow_track IS NULL OR workflow_track IN ({OPPORTUNITY_TRACK_VALUES})",
            name="plan_workflow_track",
        ),
        CheckConstraint(
            "workflow_version IS NULL OR workflow_version >= 1",
            name="plan_workflow_version_positive",
        ),
        Index("ix_plans_project_created", "project_id", "created_at"),
        Index(
            "uq_plans_project_active",
            "project_id",
            unique=True,
            postgresql_where=text("status IN ('active', 'paused')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    source_decision_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    workflow_track: Mapped[str | None] = mapped_column(String(30))
    workflow_id: Mapped[str | None] = mapped_column(String(64))
    workflow_version: Mapped[int | None] = mapped_column(Integer)
    workflow_sha256: Mapped[str | None] = mapped_column(String(64))
    stage_id: Mapped[str | None] = mapped_column(String(64))
    pause_reason: Mapped[str | None] = mapped_column(String(100))
    max_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_rework_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_plans_created_by_user_id_users"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlanNode(Base):
    __tablename__ = "plan_nodes"
    __table_args__ = (
        UniqueConstraint("plan_id", "node_key", name="uq_plan_nodes_plan_key"),
        UniqueConstraint("plan_id", "task_id", name="uq_plan_nodes_plan_task"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_plan_nodes_workspace_project_node",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "plan_id"],
            ["plans.workspace_id", "plans.project_id", "plans.id"],
            name="plan_node_same_plan",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "task_id"],
            ["tasks.workspace_id", "tasks.project_id", "tasks.id"],
            name="plan_node_same_task",
        ),
        CheckConstraint("order_index >= 0", name="plan_node_order_nonnegative"),
        Index("ix_plan_nodes_plan_order", "plan_id", "order_index"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    node_key: Mapped[str] = mapped_column(String(64), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TaskReview(Base):
    __tablename__ = "task_reviews"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "idempotency_key",
            name="uq_task_reviews_plan_idempotency",
        ),
        UniqueConstraint(
            "plan_id",
            "task_id",
            "review_round",
            name="uq_task_reviews_plan_task_round",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "plan_id"],
            ["plans.workspace_id", "plans.project_id", "plans.id"],
            name="task_review_same_plan",
        ),
        ForeignKeyConstraint(
            [
                "workspace_id",
                "project_id",
                "task_id",
                "task_version_id",
            ],
            [
                "task_versions.workspace_id",
                "task_versions.project_id",
                "task_versions.task_id",
                "task_versions.id",
            ],
            name="task_review_same_task_version",
        ),
        CheckConstraint(
            f"decision IN ({REVIEW_DECISION_VALUES})",
            name="task_review_decision",
        ),
        CheckConstraint(
            "reviewer_role IN ('A25', 'A26')",
            name="task_review_independent_role",
        ),
        CheckConstraint("review_round >= 1", name="task_review_round_positive"),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="task_review_request_hash_sha256",
        ),
        Index("ix_task_reviews_task_created", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    task_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_task_reviews_reviewer_user_id_users"),
        nullable=False,
    )
    reviewer_role: Mapped[str] = mapped_column(String(3), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    review_round: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StageAssessment(Base):
    __tablename__ = "stage_assessments"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_stage_assessments_workspace_project_assessment",
        ),
        UniqueConstraint(
            "project_id",
            "workflow_track",
            "stage_id",
            "assessment_version",
            name="uq_stage_assessments_project_stage_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="stage_assessment_same_project",
        ),
        CheckConstraint(
            f"workflow_track IN ({OPPORTUNITY_TRACK_VALUES})",
            name="stage_assessment_track",
        ),
        CheckConstraint(
            f"status IN ({ASSESSMENT_STATUS_VALUES})",
            name="stage_assessment_status",
        ),
        CheckConstraint(
            f"recommendation IN ({ASSESSMENT_RECOMMENDATION_VALUES})",
            name="stage_assessment_recommendation",
        ),
        CheckConstraint("workflow_version >= 1", name="stage_assessment_workflow_version_positive"),
        CheckConstraint(
            "assessment_version >= 1",
            name="stage_assessment_version_positive",
        ),
        Index(
            "ix_stage_assessments_project_track_stage",
            "project_id",
            "workflow_track",
            "stage_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    workflow_track: Mapped[str] = mapped_column(String(30), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assessment_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(30), nullable=False)
    criterion_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    external_preconditions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_stage_assessments_created_by_user_id_users"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StageDecision(Base):
    __tablename__ = "stage_decisions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_stage_decisions_workspace_project_decision",
        ),
        UniqueConstraint("assessment_id", name="uq_stage_decisions_assessment"),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "assessment_id"],
            [
                "stage_assessments.workspace_id",
                "stage_assessments.project_id",
                "stage_assessments.id",
            ],
            name="stage_decision_same_assessment",
        ),
        CheckConstraint(
            f"decision IN ({STAGE_DECISION_VALUES})",
            name="stage_decision_value",
        ),
        CheckConstraint(
            "reviewer_role IN ('A25', 'A26')",
            name="stage_decision_reviewer_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_stage_decisions_reviewer_user_id_users"),
        nullable=False,
    )
    reviewer_role: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_datasets_workspace_project_dataset",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["projects.workspace_id", "projects.id"],
            name="dataset_same_project",
        ),
        CheckConstraint("revision >= 1", name="dataset_revision_positive"),
        Index("ix_datasets_project_updated", "project_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_datasets_created_by_user_id_users"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "version_number",
            name="uq_dataset_versions_dataset_version",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_dataset_versions_workspace_project_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "dataset_id"],
            ["datasets.workspace_id", "datasets.project_id", "datasets.id"],
            name="dataset_version_same_dataset",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "parent_version_id"],
            [
                "dataset_versions.workspace_id",
                "dataset_versions.project_id",
                "dataset_versions.id",
            ],
            name="dataset_version_same_parent",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "source_document_version_id"],
            [
                "knowledge_document_versions.workspace_id",
                "knowledge_document_versions.project_id",
                "knowledge_document_versions.id",
            ],
            name="dataset_version_same_source",
        ),
        CheckConstraint(
            f"kind IN ({DATASET_VERSION_KIND_VALUES})",
            name="dataset_version_kind",
        ),
        CheckConstraint(
            f"state IN ({DATASET_VERSION_STATE_VALUES})",
            name="dataset_version_state",
        ),
        CheckConstraint("version_number >= 1", name="dataset_version_number_positive"),
        CheckConstraint("row_count >= 0", name="dataset_version_row_count_nonnegative"),
        CheckConstraint(
            "rows_sha256 ~ '^[0-9a-f]{64}$'",
            name="dataset_version_rows_sha256",
        ),
        CheckConstraint(
            "(kind = 'raw' AND source_document_version_id IS NOT NULL "
            "AND parent_version_id IS NULL) OR "
            "(kind = 'derived' AND parent_version_id IS NOT NULL "
            "AND source_document_version_id IS NULL)",
            name="dataset_version_origin",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "dataset_id",
            "id",
            name="uq_dataset_versions_same_dataset_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    source_document_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    parent_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    transformation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rows_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    columns: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    quality_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_dataset_versions_created_by_user_id_users",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DatasetRow(Base):
    __tablename__ = "dataset_rows"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id",
            "row_index",
            name="uq_dataset_rows_version_row",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "dataset_version_id"],
            [
                "dataset_versions.workspace_id",
                "dataset_versions.project_id",
                "dataset_versions.id",
            ],
            name="dataset_row_same_version",
        ),
        CheckConstraint("row_index >= 0", name="dataset_row_index_nonnegative"),
        Index("ix_dataset_rows_version_index", "dataset_version_id", "row_index"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dataset_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class StatisticalPlan(Base):
    __tablename__ = "statistical_plans"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id",
            "plan_version",
            name="uq_statistical_plans_version_plan",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_statistical_plans_workspace_project_plan",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "dataset_version_id"],
            [
                "dataset_versions.workspace_id",
                "dataset_versions.project_id",
                "dataset_versions.id",
            ],
            name="statistical_plan_same_dataset_version",
        ),
        CheckConstraint(
            f"method IN ({STATISTICAL_METHOD_VALUES})",
            name="statistical_plan_method",
        ),
        CheckConstraint("plan_version >= 1", name="statistical_plan_version_positive"),
        CheckConstraint("alpha > 0 AND alpha < 1", name="statistical_plan_alpha"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dataset_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint_column: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    group_column: Mapped[str | None] = mapped_column(String(200))
    analysis_set: Mapped[str] = mapped_column(String(300), nullable=False)
    missing_policy: Mapped[str] = mapped_column(String(50), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(100))
    alpha: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    expected_groups: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    exploratory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_statistical_plans_created_by_user_id_users",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "analysis_version",
            name="uq_analysis_runs_plan_version",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_analysis_runs_workspace_project_run",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "dataset_version_id"],
            [
                "dataset_versions.workspace_id",
                "dataset_versions.project_id",
                "dataset_versions.id",
            ],
            name="analysis_run_same_dataset_version",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "plan_id"],
            [
                "statistical_plans.workspace_id",
                "statistical_plans.project_id",
                "statistical_plans.id",
            ],
            name="analysis_run_same_plan",
        ),
        CheckConstraint(
            f"state IN ({ANALYSIS_STATE_VALUES})",
            name="analysis_run_state",
        ),
        CheckConstraint("analysis_version >= 1", name="analysis_run_version_positive"),
        CheckConstraint("code_sha256 ~ '^[0-9a-f]{64}$'", name="analysis_run_code_sha256"),
        CheckConstraint("input_sha256 ~ '^[0-9a-f]{64}$'", name="analysis_run_input_sha256"),
        CheckConstraint("output_sha256 ~ '^[0-9a-f]{64}$'", name="analysis_run_output_sha256"),
        Index("ix_analysis_runs_plan_created", "plan_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dataset_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    code_version: Mapped[str] = mapped_column(String(100), nullable=False)
    code_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    chart_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    output_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_analysis_runs_created_by_user_id_users"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalysisReview(Base):
    __tablename__ = "analysis_reviews"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "idempotency_key",
            name="uq_analysis_reviews_analysis_idempotency",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "id",
            name="uq_analysis_reviews_workspace_project_review",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id", "analysis_id"],
            [
                "analysis_runs.workspace_id",
                "analysis_runs.project_id",
                "analysis_runs.id",
            ],
            name="analysis_review_same_analysis",
        ),
        CheckConstraint(
            f"decision IN ({REVIEW_DECISION_VALUES})",
            name="analysis_review_decision",
        ),
        CheckConstraint(
            "reviewer_role IN ('A14', 'A25', 'A26')",
            name="analysis_review_role",
        ),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'",
            name="analysis_review_request_hash",
        ),
        CheckConstraint(
            "result_sha256 ~ '^[0-9a-f]{64}$'",
            name="analysis_review_result_sha256",
        ),
        Index("ix_analysis_reviews_analysis_created", "analysis_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    analysis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_analysis_reviews_reviewer_user_id_users"),
        nullable=False,
    )
    reviewer_role: Mapped[str] = mapped_column(String(3), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    result_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
