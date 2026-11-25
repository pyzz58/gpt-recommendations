from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderType(StrEnum):
    CDMO = "cdmo"
    CRO = "cro"
    SMO = "smo"
    CENTRAL_LAB = "central_lab"
    TESTING_LAB = "testing_lab"
    SAMPLE_PROVIDER = "sample_provider"
    PROTOTYPE_PROVIDER = "prototype_provider"
    REGULATORY = "regulatory"
    ETHICS = "ethics"
    OTHER = "other"


class VerificationState(StrEnum):
    CANDIDATE = "candidate"
    CONTACTED = "contacted"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ExpertState(StrEnum):
    CANDIDATE = "candidate"
    CONTACTED = "contacted"
    REPLIED = "replied"
    LIMITED_REVIEW = "limited_review"
    ENGAGED = "engaged"
    DECLINED = "declined"


class ExternalEngagementState(StrEnum):
    DRAFT = "draft"
    SCOPE_READY = "scope_ready"
    REQUESTED = "requested"
    QUOTED = "quoted"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    DELIVERED = "delivered"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class QuoteState(StrEnum):
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ContractState(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    AWAITING_SIGNATURE = "awaiting_signature"
    SIGNED = "signed"
    CANCELLED = "cancelled"


class DeliverableKind(StrEnum):
    REPORT = "report"
    RAW_DATA = "raw_data"
    PROTOTYPE = "prototype"
    SERVICE_RECORD = "service_record"
    APPROVAL_RECORD = "approval_record"


class DeliverableState(StrEnum):
    EXPECTED = "expected"
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProfessionalRecordKind(StrEnum):
    REGULATORY = "regulatory"
    PATENT = "patent"
    FINANCIAL = "financial"
    COMMERCIAL = "commercial"


class ProfessionalRecordState(StrEnum):
    DRAFT = "draft"
    INFORMATION_ONLY = "information_only"
    OFFICIAL_CONFIRMED = "official_confirmed"
    DISPUTED = "disputed"
    EXPIRED = "expired"


class SourceTier(StrEnum):
    OFFICIAL = "official"
    PRIMARY_PUBLICATION = "primary_publication"
    VENDOR = "vendor"
    USER_STATEMENT = "user_statement"
    NONE = "none"


class FinancialEventType(StrEnum):
    BUDGET = "budget"
    COMMITMENT = "commitment"
    PAYMENT = "payment"
    SPEND = "spend"


class CommercialEvidenceType(StrEnum):
    ASSUMPTION = "assumption"
    PUBLIC_CLAIM = "public_claim"
    VERIFIED_INTERVIEW = "verified_interview"
    MARKET_REPORT = "market_report"
    UNKNOWN = "unknown"


class PatentStatus(StrEnum):
    IDEA = "idea"
    SEARCH_ONLY = "search_only"
    PROVISIONAL = "provisional"
    PENDING = "pending"
    GRANTED = "granted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class ExternalAuthorizationState(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"


class OrganizationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=300)
    provider_type: ProviderType
    capability_summary: str = Field(min_length=1, max_length=10_000)
    source_refs: list[str] = Field(default_factory=list, max_length=20)
    verification_state: VerificationState = VerificationState.CANDIDATE

    @model_validator(mode="after")
    def verified_requires_source(self) -> OrganizationSpec:
        if self.verification_state == VerificationState.VERIFIED and not self.source_refs:
            raise ValueError("Verified organization requires source references")
        return self


class ContactSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    organization_id: UUID
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    source_refs: list[str] = Field(min_length=1, max_length=20)
    verification_state: VerificationState = VerificationState.CANDIDATE


class ExpertSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=200)
    expertise: str = Field(min_length=1, max_length=2_000)
    public_source_refs: list[str] = Field(min_length=1, max_length=20)
    contact_email: str | None = Field(default=None, max_length=320)
    conflict_notes: str = Field(default="未核查", max_length=5_000)
    state: ExpertState = ExpertState.CANDIDATE


class EngagementScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scientific_question: str = Field(min_length=1, max_length=5_000)
    decision_impact: str = Field(min_length=1, max_length=5_000)
    input_requirements: list[str] = Field(min_length=1, max_length=50)
    deliverables: list[str] = Field(min_length=1, max_length=50)
    method_and_quality: list[str] = Field(min_length=1, max_length=50)
    rights_and_confidentiality: list[str] = Field(min_length=1, max_length=50)
    acceptance_responsibility: str = Field(min_length=1, max_length=2_000)
    target_start: date | None = None
    target_end: date | None = None
    budget_lower: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    budget_upper: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str = Field(default="CNY", pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def validate_range(self) -> EngagementScope:
        if (
            self.budget_lower is not None
            and self.budget_upper is not None
            and self.budget_upper < self.budget_lower
        ):
            raise ValueError("Budget upper bound cannot be below lower bound")
        if self.target_start and self.target_end and self.target_end < self.target_start:
            raise ValueError("Target end cannot be before target start")
        return self


class EngagementSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    organization_id: UUID
    title: str = Field(min_length=1, max_length=300)
    scope: EngagementScope


class QuoteSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    engagement_id: UUID
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    tax_included: bool | None = None
    shipping_included: bool | None = None
    assumptions: list[str] = Field(default_factory=list, max_length=50)
    excluded_work: list[str] = Field(default_factory=list, max_length=50)
    valid_until: date | None = None
    document_version_id: UUID | None = None
    state: QuoteState = QuoteState.RECEIVED

    @model_validator(mode="after")
    def received_or_accepted_requires_document(self) -> QuoteSpec:
        if self.state in {QuoteState.RECEIVED, QuoteState.ACCEPTED} and not (
            self.document_version_id and self.amount is not None
        ):
            raise ValueError(
                "Received or accepted quote requires an original document and amount"
            )
        return self


class ContractSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    engagement_id: UUID
    quote_id: UUID | None = None
    title: str = Field(min_length=1, max_length=300)
    terms_summary: str = Field(min_length=1, max_length=20_000)
    document_version_id: UUID | None = None
    state: Literal[ContractState.DRAFT] = ContractState.DRAFT


class ContractTransitionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_revision: int = Field(ge=1)
    state: ContractState
    internal_signed: bool
    external_signed: bool
    document_version_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=5_000)

    @model_validator(mode="after")
    def signed_requires_both(self) -> ContractTransitionSpec:
        if self.state == ContractState.SIGNED and not (
            self.internal_signed and self.external_signed and self.document_version_id
        ):
            raise ValueError(
                "Signed contract requires both signatures and a signed document version"
            )
        return self


class DeliverableSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    engagement_id: UUID
    title: str = Field(min_length=1, max_length=300)
    kind: DeliverableKind
    expected_items: list[str] = Field(min_length=1, max_length=50)
    due_at: datetime | None = None


class DeliverableReceiptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_version_id: UUID
    manifest: dict[str, Any] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list, max_length=50)
    summary: str = Field(min_length=1, max_length=10_000)


class DeliverableReviewSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["accepted", "rejected"]
    reviewer_role: Literal["A25", "A26"]
    summary: str = Field(min_length=1, max_length=10_000)
    findings: list[str] = Field(default_factory=list, max_length=50)
    missing_items: list[str] = Field(default_factory=list, max_length=50)


class ProfessionalRecordSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ProfessionalRecordKind
    state: ProfessionalRecordState = ProfessionalRecordState.DRAFT
    title: str = Field(min_length=1, max_length=300)
    source_tier: SourceTier
    source_title: str | None = Field(default=None, max_length=500)
    source_ref: str | None = Field(default=None, max_length=2_000)
    checked_at: date | None = None
    market: str | None = Field(default=None, max_length=200)
    product_scope: str | None = Field(default=None, max_length=1_000)
    jurisdiction: str | None = Field(default=None, max_length=200)
    patent_status: PatentStatus | None = None
    application_number: str | None = Field(default=None, max_length=200)
    publication_number: str | None = Field(default=None, max_length=200)
    financial_event_type: FinancialEventType | None = None
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    commercial_evidence_type: CommercialEvidenceType | None = None
    facts: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> ProfessionalRecordSpec:
        if self.kind == ProfessionalRecordKind.REGULATORY:
            if not self.market or not self.product_scope or not self.checked_at:
                raise ValueError("Regulatory record requires market, product scope and checked_at")
            if self.state == ProfessionalRecordState.OFFICIAL_CONFIRMED and (
                self.source_tier != SourceTier.OFFICIAL or not self.source_ref
            ):
                raise ValueError("Official regulatory record requires an official source")
        if self.kind == ProfessionalRecordKind.PATENT and (
            not self.jurisdiction
            or self.patent_status is None
            or not self.checked_at
        ):
            raise ValueError("Patent record requires jurisdiction, status and checked_at")
        if self.kind == ProfessionalRecordKind.FINANCIAL:
            if self.financial_event_type is None or self.amount is None or not self.currency:
                raise ValueError("Financial record requires event type, amount and currency")
            if self.financial_event_type in {
                FinancialEventType.COMMITMENT,
                FinancialEventType.PAYMENT,
                FinancialEventType.SPEND,
            } and not self.source_ref:
                raise ValueError("Commitment/payment/spend requires a source reference")
        if self.kind == ProfessionalRecordKind.COMMERCIAL:
            if self.commercial_evidence_type is None:
                raise ValueError("Commercial record requires evidence type")
            if (
                self.commercial_evidence_type
                in {
                    CommercialEvidenceType.VERIFIED_INTERVIEW,
                    CommercialEvidenceType.MARKET_REPORT,
                }
                and not self.source_ref
            ):
                raise ValueError("Verified commercial evidence requires a source reference")
        return self


class ExternalAuthorizationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    engagement_id: UUID
    action_scope: str = Field(min_length=1, max_length=2_000)
    amount_max: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    expires_at: datetime
