from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
    PlanStateError,
)
from medical_one_person.application.readiness import require_no_active_audit_blockers
from medical_one_person.domain.external import (
    ContactSpec,
    ContractSpec,
    ContractState,
    ContractTransitionSpec,
    DeliverableKind,
    DeliverableReceiptSpec,
    DeliverableReviewSpec,
    DeliverableSpec,
    DeliverableState,
    EngagementScope,
    EngagementSpec,
    ExpertSpec,
    ExpertState,
    ExternalAuthorizationSpec,
    ExternalAuthorizationState,
    ExternalEngagementState,
    OrganizationSpec,
    ProfessionalRecordKind,
    ProfessionalRecordSpec,
    ProfessionalRecordState,
    ProviderType,
    QuoteSpec,
    QuoteState,
    VerificationState,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    ExternalAuthorization,
    ExternalContact,
    ExternalContract,
    ExternalDeliverable,
    ExternalEngagement,
    ExternalExpert,
    ExternalOrganization,
    ExternalQuote,
    KnowledgeDocumentVersion,
    ProfessionalRecord,
    Project,
    ProjectEvent,
    User,
)


class OrganizationView(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    provider_type: ProviderType
    capability_summary: str
    source_refs: list[str]
    verification_state: VerificationState
    revision: int


class ContactView(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    role: str
    email: str | None
    source_refs: list[str]
    verification_state: VerificationState
    revision: int


class ExpertView(BaseModel):
    id: UUID
    name: str
    expertise: str
    public_source_refs: list[str]
    contact_email: str | None
    conflict_notes: str
    state: ExpertState
    revision: int


class EngagementView(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    scope: EngagementScope
    scope_sha256: str
    state: ExternalEngagementState
    revision: int
    created_at: datetime
    updated_at: datetime


class QuoteView(BaseModel):
    id: UUID
    engagement_id: UUID
    amount: Decimal | None
    currency: str
    tax_included: bool | None
    shipping_included: bool | None
    assumptions: list[str]
    excluded_work: list[str]
    valid_until: datetime | None
    document_version_id: UUID | None
    state: QuoteState
    scope_sha256: str
    created_at: datetime


class ContractView(BaseModel):
    id: UUID
    engagement_id: UUID
    quote_id: UUID | None
    title: str
    terms_summary: str
    document_version_id: UUID | None
    state: ContractState
    internal_signed: bool
    external_signed: bool
    signed_at: datetime | None
    revision: int
    created_at: datetime
    updated_at: datetime


class DeliverableView(BaseModel):
    id: UUID
    engagement_id: UUID
    title: str
    kind: DeliverableKind
    expected_items: list[str]
    state: DeliverableState
    knowledge_version_id: UUID | None
    manifest: dict[str, Any]
    missing_items: list[str]
    receipt_summary: str | None
    received_at: datetime | None
    reviewer_role: str | None
    review_summary: str | None
    findings: list[str]
    due_at: datetime | None
    revision: int
    created_at: datetime
    updated_at: datetime


class ProfessionalRecordView(BaseModel):
    id: UUID
    kind: ProfessionalRecordKind
    state: ProfessionalRecordState
    title: str
    source_tier: str
    source_title: str | None
    source_ref: str | None
    checked_at: datetime | None
    market: str | None
    product_scope: str | None
    jurisdiction: str | None
    patent_status: str | None
    application_number: str | None
    publication_number: str | None
    financial_event_type: str | None
    amount: Decimal | None
    currency: str | None
    commercial_evidence_type: str | None
    facts: list[str]
    limitations: list[str]
    metadata: dict[str, Any]
    revision: int
    created_at: datetime


class ExternalAuthorizationView(BaseModel):
    id: UUID
    engagement_id: UUID
    action_scope: str
    scope_sha256: str
    amount_max: Decimal
    currency: str
    valid_from: datetime
    expires_at: datetime
    state: ExternalAuthorizationState
    revision: int
    created_at: datetime


class QuoteComparisonView(BaseModel):
    engagement_id: UUID
    scope_sha256: str
    comparable: list[QuoteView]
    excluded: list[QuoteView]
    warnings: list[str]


class ExternalWorkspaceView(BaseModel):
    organizations: list[OrganizationView]
    contacts: list[ContactView]
    experts: list[ExpertView]
    engagements: list[EngagementView]
    quotes: list[QuoteView]
    contracts: list[ContractView]
    deliverables: list[DeliverableView]
    professional_records: list[ProfessionalRecordView]
    authorizations: list[ExternalAuthorizationView]


class ExternalService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def workspace(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> ExternalWorkspaceView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            return ExternalWorkspaceView(
                organizations=[
                    _organization_view(item)
                    for item in session.scalars(
                        select(ExternalOrganization)
                        .where(ExternalOrganization.project_id == project.id)
                        .order_by(ExternalOrganization.created_at)
                    )
                ],
                contacts=[
                    _contact_view(item)
                    for item in session.scalars(
                        select(ExternalContact)
                        .where(ExternalContact.project_id == project.id)
                        .order_by(ExternalContact.created_at)
                    )
                ],
                experts=[
                    _expert_view(item)
                    for item in session.scalars(
                        select(ExternalExpert)
                        .where(ExternalExpert.project_id == project.id)
                        .order_by(ExternalExpert.created_at)
                    )
                ],
                engagements=[
                    _engagement_view(item)
                    for item in session.scalars(
                        select(ExternalEngagement)
                        .where(ExternalEngagement.project_id == project.id)
                        .order_by(ExternalEngagement.created_at.desc())
                    )
                ],
                quotes=[
                    _quote_view(item)
                    for item in session.scalars(
                        select(ExternalQuote)
                        .where(ExternalQuote.project_id == project.id)
                        .order_by(ExternalQuote.created_at.desc())
                    )
                ],
                contracts=[
                    _contract_view(item)
                    for item in session.scalars(
                        select(ExternalContract)
                        .where(ExternalContract.project_id == project.id)
                        .order_by(ExternalContract.created_at.desc())
                    )
                ],
                deliverables=[
                    _deliverable_view(item)
                    for item in session.scalars(
                        select(ExternalDeliverable)
                        .where(ExternalDeliverable.project_id == project.id)
                        .order_by(ExternalDeliverable.created_at.desc())
                    )
                ],
                professional_records=[
                    _professional_record_view(item)
                    for item in session.scalars(
                        select(ProfessionalRecord)
                        .where(ProfessionalRecord.project_id == project.id)
                        .order_by(ProfessionalRecord.created_at.desc())
                    )
                ],
                authorizations=[
                    _authorization_view(item)
                    for item in session.scalars(
                        select(ExternalAuthorization)
                        .where(ExternalAuthorization.project_id == project.id)
                        .order_by(ExternalAuthorization.created_at.desc())
                    )
                ],
            )

    def create_organization(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: OrganizationSpec,
        idempotency_key: str,
    ) -> OrganizationView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalOrganization)
                .where(
                    ExternalOrganization.project_id == project.id,
                    ExternalOrganization.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "organization")
                return _organization_view(existing)
            now = datetime.now(UTC)
            row = ExternalOrganization(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                name=spec.name,
                provider_type=spec.provider_type.value,
                capability_summary=spec.capability_summary,
                source_refs=spec.source_refs,
                verification_state=spec.verification_state.value,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                revision=1,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            _event(session, project, actor, "external.organization_created", row.id, 1, now)
            return _organization_view(row)

    def create_contact(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: ContactSpec,
    ) -> ContactView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            organization = _organization(session, project.id, spec.organization_id)
            if organization.verification_state == VerificationState.REJECTED.value:
                raise ValueError("Cannot add a contact to a rejected organization")
            now = datetime.now(UTC)
            row = ExternalContact(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                organization_id=organization.id,
                name=spec.name,
                role=spec.role,
                email=spec.email.lower() if spec.email else None,
                source_refs=spec.source_refs,
                verification_state=spec.verification_state.value,
                revision=1,
                created_at=now,
            )
            session.add(row)
            session.flush()
            _event(session, project, actor, "external.contact_created", row.id, 1, now)
            return _contact_view(row)

    def create_expert(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: ExpertSpec,
        idempotency_key: str,
    ) -> ExpertView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalExpert)
                .where(
                    ExternalExpert.project_id == project.id,
                    ExternalExpert.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "expert")
                return _expert_view(existing)
            now = datetime.now(UTC)
            row = ExternalExpert(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                name=spec.name,
                expertise=spec.expertise,
                public_source_refs=spec.public_source_refs,
                contact_email=spec.contact_email.lower() if spec.contact_email else None,
                conflict_notes=spec.conflict_notes,
                state=spec.state.value,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                revision=1,
                created_at=now,
            )
            session.add(row)
            session.flush()
            _event(session, project, actor, "external.expert_created", row.id, 1, now)
            return _expert_view(row)

    def update_expert_state(
        self,
        *,
        project_id: UUID,
        expert_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        state: ExpertState,
        note: str,
    ) -> ExpertView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = session.scalar(
                select(ExternalExpert)
                .where(
                    ExternalExpert.id == expert_id,
                    ExternalExpert.project_id == project.id,
                )
                .with_for_update()
            )
            if row is None:
                raise NotFoundError("Expert not found")
            if row.revision != expected_revision:
                raise ConflictingOperationError("Expert revision is stale")
            now = datetime.now(UTC)
            row.state = state.value
            row.conflict_notes = f"{row.conflict_notes}\n{note}".strip()
            row.revision += 1
            _event(
                session,
                project,
                actor,
                "external.expert_state_changed",
                row.id,
                row.revision,
                now,
            )
            return _expert_view(row)

    def create_engagement(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: EngagementSpec,
        idempotency_key: str,
    ) -> EngagementView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalEngagement)
                .where(
                    ExternalEngagement.project_id == project.id,
                    ExternalEngagement.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "engagement")
                return _engagement_view(existing)
            organization = _organization(session, project.id, spec.organization_id)
            if organization.verification_state != VerificationState.VERIFIED.value:
                raise ValueError("External engagement requires a verified organization")
            scope = spec.scope.model_dump(mode="json")
            now = datetime.now(UTC)
            row = ExternalEngagement(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                organization_id=organization.id,
                title=spec.title,
                scope=scope,
                scope_sha256=_digest(scope),
                state=ExternalEngagementState.DRAFT.value,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                revision=1,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            _event(session, project, actor, "external.engagement_created", row.id, 1, now)
            return _engagement_view(row)

    def transition_engagement(
        self,
        *,
        project_id: UUID,
        engagement_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        state: ExternalEngagementState,
    ) -> EngagementView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = session.scalar(
                select(ExternalEngagement)
                .where(
                    ExternalEngagement.id == engagement_id,
                    ExternalEngagement.project_id == project.id,
                )
                .with_for_update()
            )
            if row is None:
                raise NotFoundError("External engagement not found")
            if row.revision != expected_revision:
                raise ConflictingOperationError("External engagement revision is stale")
            _validate_engagement_transition(session, row, state)
            now = datetime.now(UTC)
            old = row.state
            row.state = state.value
            row.revision += 1
            row.updated_at = now
            _event(
                session,
                project,
                actor,
                "external.engagement_state_changed",
                row.id,
                row.revision,
                now,
                {"from": old, "to": state.value},
            )
            return _engagement_view(row)

    def create_quote(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: QuoteSpec,
        idempotency_key: str,
    ) -> QuoteView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalQuote)
                .where(
                    ExternalQuote.project_id == project.id,
                    ExternalQuote.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "quote")
                return _quote_view(existing)
            engagement = _engagement(session, project.id, spec.engagement_id)
            _document_version(
                session,
                project.id,
                spec.document_version_id,
            )
            now = datetime.now(UTC)
            row = ExternalQuote(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                engagement_id=engagement.id,
                amount=spec.amount,
                currency=spec.currency,
                tax_included=spec.tax_included,
                shipping_included=spec.shipping_included,
                assumptions=spec.assumptions,
                excluded_work=spec.excluded_work,
                valid_until=_date_end(spec.valid_until),
                document_version_id=spec.document_version_id,
                state=spec.state.value,
                scope_sha256=engagement.scope_sha256,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_at=now,
            )
            session.add(row)
            session.flush()
            if engagement.state in {
                ExternalEngagementState.DRAFT.value,
                ExternalEngagementState.SCOPE_READY.value,
                ExternalEngagementState.REQUESTED.value,
            }:
                engagement.state = ExternalEngagementState.QUOTED.value
                engagement.revision += 1
                engagement.updated_at = now
            _event(session, project, actor, "external.quote_recorded", row.id, 1, now)
            return _quote_view(row)

    def compare_quotes(
        self,
        *,
        project_id: UUID,
        engagement_id: UUID,
        actor_user_id: UUID,
    ) -> QuoteComparisonView:
        with self._session_factory.begin() as session:
            actor = _owner(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            engagement = _engagement(session, project.id, engagement_id)
            quotes = session.scalars(
                select(ExternalQuote)
                .where(
                    ExternalQuote.project_id == project.id,
                    ExternalQuote.engagement_id == engagement.id,
                )
                .order_by(ExternalQuote.created_at)
            ).all()
            comparable = [
                item
                for item in quotes
                if item.scope_sha256 == engagement.scope_sha256
                and item.amount is not None
                and item.state in {QuoteState.RECEIVED.value, QuoteState.ACCEPTED.value}
            ]
            excluded = [item for item in quotes if item not in comparable]
            warnings: list[str] = []
            currencies = {item.currency for item in comparable}
            if len(currencies) > 1:
                warnings.append("Quotes use different currencies and cannot be summed")
            if any(item.tax_included is None for item in comparable):
                warnings.append("One or more quotes have unknown tax treatment")
            if any(item.shipping_included is None for item in comparable):
                warnings.append("One or more quotes have unknown shipping treatment")
            if any(item.assumptions or item.excluded_work for item in comparable):
                warnings.append("Quote assumptions or exclusions must be reviewed")
            return QuoteComparisonView(
                engagement_id=engagement.id,
                scope_sha256=engagement.scope_sha256,
                comparable=[_quote_view(item) for item in comparable],
                excluded=[_quote_view(item) for item in excluded],
                warnings=warnings,
            )

    def create_contract(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: ContractSpec,
        idempotency_key: str,
    ) -> ContractView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalContract)
                .where(
                    ExternalContract.project_id == project.id,
                    ExternalContract.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "contract")
                return _contract_view(existing)
            engagement = _engagement(session, project.id, spec.engagement_id)
            if spec.quote_id is not None:
                quote = _quote(session, project.id, spec.quote_id)
                if quote.engagement_id != engagement.id:
                    raise ValueError("Contract quote belongs to another engagement")
            _document_version(session, project.id, spec.document_version_id)
            now = datetime.now(UTC)
            row = ExternalContract(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                engagement_id=engagement.id,
                quote_id=spec.quote_id,
                title=spec.title,
                terms_summary=spec.terms_summary,
                document_version_id=spec.document_version_id,
                state=ContractState.DRAFT.value,
                internal_signed=False,
                external_signed=False,
                revision=1,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            _event(session, project, actor, "external.contract_drafted", row.id, 1, now)
            return _contract_view(row)

    def transition_contract(
        self,
        *,
        project_id: UUID,
        contract_id: UUID,
        actor_user_id: UUID,
        spec: ContractTransitionSpec,
    ) -> ContractView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = session.scalar(
                select(ExternalContract)
                .where(
                    ExternalContract.id == contract_id,
                    ExternalContract.project_id == project.id,
                )
                .with_for_update()
            )
            if row is None:
                raise NotFoundError("External contract not found")
            if row.revision != spec.expected_revision:
                raise ConflictingOperationError("Contract revision is stale")
            _document_version(session, project.id, spec.document_version_id)
            now = datetime.now(UTC)
            row.state = spec.state.value
            row.internal_signed = spec.internal_signed
            row.external_signed = spec.external_signed
            if spec.document_version_id is not None:
                row.document_version_id = spec.document_version_id
            row.signed_at = (
                now if spec.state == ContractState.SIGNED else row.signed_at
            )
            row.revision += 1
            row.updated_at = now
            _event(
                session,
                project,
                actor,
                "external.contract_state_changed",
                row.id,
                row.revision,
                now,
                {"state": spec.state.value, "reason": spec.reason},
            )
            return _contract_view(row)

    def create_deliverable(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: DeliverableSpec,
        idempotency_key: str,
    ) -> DeliverableView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalDeliverable)
                .where(
                    ExternalDeliverable.project_id == project.id,
                    ExternalDeliverable.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "deliverable")
                return _deliverable_view(existing)
            engagement = _engagement(session, project.id, spec.engagement_id)
            now = datetime.now(UTC)
            row = ExternalDeliverable(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                engagement_id=engagement.id,
                title=spec.title,
                kind=spec.kind.value,
                expected_items=spec.expected_items,
                state=DeliverableState.EXPECTED.value,
                knowledge_version_id=None,
                manifest={},
                missing_items=[],
                reviewer_role=None,
                findings=[],
                due_at=spec.due_at,
                revision=1,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            _event(session, project, actor, "external.deliverable_expected", row.id, 1, now)
            return _deliverable_view(row)

    def receive_deliverable(
        self,
        *,
        project_id: UUID,
        deliverable_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        spec: DeliverableReceiptSpec,
    ) -> DeliverableView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = session.scalar(
                select(ExternalDeliverable)
                .where(
                    ExternalDeliverable.id == deliverable_id,
                    ExternalDeliverable.project_id == project.id,
                )
                .with_for_update()
            )
            if row is None:
                raise NotFoundError("External deliverable not found")
            if row.revision != expected_revision:
                raise ConflictingOperationError("Deliverable revision is stale")
            engagement = _engagement(session, project.id, row.engagement_id)
            if engagement.state != ExternalEngagementState.EXECUTING.value:
                raise PlanStateError("Deliverable can only be received while engagement executes")
            document = _document_version(
                session,
                project.id,
                spec.knowledge_version_id,
                required=True,
            )
            assert document is not None
            now = datetime.now(UTC)
            row.knowledge_version_id = document.id
            row.manifest = {
                **spec.manifest,
                "filename": document.filename,
                "content_sha256": document.content_hash,
                "size_bytes": document.size_bytes,
            }
            row.missing_items = spec.missing_items
            row.receipt_summary = spec.summary
            row.received_at = now
            row.state = DeliverableState.RECEIVED.value
            row.revision += 1
            row.updated_at = now
            engagement.state = ExternalEngagementState.DELIVERED.value
            engagement.revision += 1
            engagement.updated_at = now
            _event(
                session,
                project,
                actor,
                "external.deliverable_received",
                row.id,
                row.revision,
                now,
                {"knowledge_version_id": str(document.id)},
            )
            return _deliverable_view(row)

    def review_deliverable(
        self,
        *,
        project_id: UUID,
        deliverable_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        spec: DeliverableReviewSpec,
    ) -> DeliverableView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = session.scalar(
                select(ExternalDeliverable)
                .where(
                    ExternalDeliverable.id == deliverable_id,
                    ExternalDeliverable.project_id == project.id,
                )
                .with_for_update()
            )
            if row is None:
                raise NotFoundError("External deliverable not found")
            if row.revision != expected_revision:
                raise ConflictingOperationError("Deliverable revision is stale")
            if row.state not in {
                DeliverableState.RECEIVED.value,
                DeliverableState.UNDER_REVIEW.value,
                DeliverableState.REJECTED.value,
            }:
                raise PlanStateError("Deliverable has not been received")
            if not row.knowledge_version_id:
                raise ValueError("Cannot review a deliverable without an original version")
            if spec.decision == "accepted" and spec.missing_items:
                raise ValueError("A deliverable with missing items cannot be accepted")
            if spec.decision == "accepted":
                require_no_active_audit_blockers(
                    session,
                    project_id=project.id,
                    target_ids={row.id},
                )
            if (
                row.kind == DeliverableKind.RAW_DATA.value
                and not row.knowledge_version_id
            ):
                raise ValueError("Raw data acceptance requires the raw data original")
            now = datetime.now(UTC)
            row.state = (
                DeliverableState.ACCEPTED.value
                if spec.decision == "accepted"
                else DeliverableState.REJECTED.value
            )
            row.reviewer_role = spec.reviewer_role
            row.review_summary = spec.summary
            row.findings = spec.findings
            row.missing_items = spec.missing_items
            row.revision += 1
            row.updated_at = now
            engagement = _engagement(session, project.id, row.engagement_id)
            engagement.state = ExternalEngagementState.UNDER_REVIEW.value
            engagement.revision += 1
            engagement.updated_at = now
            _event(
                session,
                project,
                actor,
                "external.deliverable_reviewed",
                row.id,
                row.revision,
                now,
                {"decision": spec.decision, "reviewer_role": spec.reviewer_role},
            )
            return _deliverable_view(row)

    def create_professional_record(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: ProfessionalRecordSpec,
        idempotency_key: str,
    ) -> ProfessionalRecordView:
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ProfessionalRecord)
                .where(
                    ProfessionalRecord.project_id == project.id,
                    ProfessionalRecord.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "professional record")
                return _professional_record_view(existing)
            now = datetime.now(UTC)
            row = ProfessionalRecord(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                kind=spec.kind.value,
                state=spec.state.value,
                title=spec.title,
                source_tier=spec.source_tier.value,
                source_title=spec.source_title,
                source_ref=spec.source_ref,
                checked_at=_date_end(spec.checked_at),
                market=spec.market,
                product_scope=spec.product_scope,
                jurisdiction=spec.jurisdiction,
                patent_status=spec.patent_status.value if spec.patent_status else None,
                application_number=spec.application_number,
                publication_number=spec.publication_number,
                financial_event_type=(
                    spec.financial_event_type.value
                    if spec.financial_event_type
                    else None
                ),
                amount=spec.amount,
                currency=spec.currency,
                commercial_evidence_type=(
                    spec.commercial_evidence_type.value
                    if spec.commercial_evidence_type
                    else None
                ),
                facts=spec.facts,
                limitations=spec.limitations,
                record_metadata=spec.metadata,
                revision=1,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_at=now,
            )
            session.add(row)
            session.flush()
            _event(
                session,
                project,
                actor,
                "external.professional_record_created",
                row.id,
                1,
                now,
                {"kind": row.kind, "state": row.state},
            )
            return _professional_record_view(row)

    def create_authorization(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        spec: ExternalAuthorizationSpec,
        idempotency_key: str,
    ) -> ExternalAuthorizationView:
        if spec.expires_at <= datetime.now(UTC):
            raise ValueError("External authorization must expire in the future")
        request_hash = _digest(spec.model_dump(mode="json"))
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            existing = session.scalar(
                select(ExternalAuthorization)
                .where(
                    ExternalAuthorization.project_id == project.id,
                    ExternalAuthorization.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                _same_request(existing.request_hash, request_hash, "external authorization")
                return _authorization_view(existing)
            engagement = _engagement(session, project.id, spec.engagement_id)
            now = datetime.now(UTC)
            row = ExternalAuthorization(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                engagement_id=engagement.id,
                action_scope=spec.action_scope,
                scope_sha256=engagement.scope_sha256,
                amount_max=spec.amount_max,
                currency=spec.currency,
                valid_from=now,
                expires_at=spec.expires_at,
                state=ExternalAuthorizationState.ACTIVE.value,
                granted_by_user_id=actor.id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                revision=1,
                created_at=now,
            )
            session.add(row)
            session.flush()
            if engagement.state == ExternalEngagementState.QUOTED.value:
                engagement.state = ExternalEngagementState.AUTHORIZED.value
                engagement.revision += 1
                engagement.updated_at = now
            _event(
                session,
                project,
                actor,
                "external.authorization_granted",
                row.id,
                1,
                now,
                {"engagement_id": str(engagement.id)},
            )
            return _authorization_view(row)

    def revoke_authorization(
        self,
        *,
        project_id: UUID,
        authorization_id: UUID,
        actor_user_id: UUID,
    ) -> ExternalAuthorizationView:
        with self._session_factory.begin() as session:
            actor, project = _context(session, project_id, actor_user_id)
            row = session.scalar(
                select(ExternalAuthorization)
                .where(
                    ExternalAuthorization.id == authorization_id,
                    ExternalAuthorization.project_id == project.id,
                )
                .with_for_update()
            )
            if row is None:
                raise NotFoundError("External authorization not found")
            if row.state == ExternalAuthorizationState.ACTIVE.value:
                row.state = ExternalAuthorizationState.REVOKED.value
                row.revision += 1
                _event(
                    session,
                    project,
                    actor,
                    "external.authorization_revoked",
                    row.id,
                    row.revision,
                    datetime.now(UTC),
                )
            return _authorization_view(row)


def _context(
    session: Session,
    project_id: UUID,
    actor_user_id: UUID,
) -> tuple[User, Project]:
    actor = _owner(session, actor_user_id)
    set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
    return actor, _project(session, project_id, actor.workspace_id)


def _owner(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage external records")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _organization(
    session: Session,
    project_id: UUID,
    organization_id: UUID,
) -> ExternalOrganization:
    row = session.scalar(
        select(ExternalOrganization).where(
            ExternalOrganization.id == organization_id,
            ExternalOrganization.project_id == project_id,
        )
    )
    if row is None:
        raise NotFoundError("External organization not found")
    return row


def _engagement(session: Session, project_id: UUID, engagement_id: UUID) -> ExternalEngagement:
    row = session.scalar(
        select(ExternalEngagement).where(
            ExternalEngagement.id == engagement_id,
            ExternalEngagement.project_id == project_id,
        )
    )
    if row is None:
        raise NotFoundError("External engagement not found")
    return row


def _quote(session: Session, project_id: UUID, quote_id: UUID) -> ExternalQuote:
    row = session.scalar(
        select(ExternalQuote).where(
            ExternalQuote.id == quote_id,
            ExternalQuote.project_id == project_id,
        )
    )
    if row is None:
        raise NotFoundError("External quote not found")
    return row


def _document_version(
    session: Session,
    project_id: UUID,
    version_id: UUID | None,
    *,
    required: bool = False,
) -> KnowledgeDocumentVersion | None:
    if version_id is None:
        if required:
            raise ValueError("A project knowledge document version is required")
        return None
    document = session.scalar(
        select(KnowledgeDocumentVersion).where(
            KnowledgeDocumentVersion.id == version_id,
            KnowledgeDocumentVersion.project_id == project_id,
            KnowledgeDocumentVersion.access_state == "active",
        )
    )
    if document is None:
        raise NotFoundError("Knowledge document version not found")
    return document


def _validate_engagement_transition(
    session: Session,
    engagement: ExternalEngagement,
    target: ExternalEngagementState,
) -> None:
    allowed = {
        ExternalEngagementState.DRAFT: {ExternalEngagementState.SCOPE_READY},
        ExternalEngagementState.SCOPE_READY: {ExternalEngagementState.REQUESTED},
        ExternalEngagementState.REQUESTED: {ExternalEngagementState.QUOTED},
        ExternalEngagementState.QUOTED: {ExternalEngagementState.AUTHORIZED},
        ExternalEngagementState.AUTHORIZED: {ExternalEngagementState.EXECUTING},
        ExternalEngagementState.EXECUTING: {ExternalEngagementState.DELIVERED},
        ExternalEngagementState.DELIVERED: {ExternalEngagementState.UNDER_REVIEW},
        ExternalEngagementState.UNDER_REVIEW: {ExternalEngagementState.ACCEPTED},
        ExternalEngagementState.ACCEPTED: {ExternalEngagementState.CLOSED},
    }
    current = ExternalEngagementState(engagement.state)
    if target == ExternalEngagementState.CANCELLED:
        if current in {ExternalEngagementState.CLOSED, ExternalEngagementState.CANCELLED}:
            raise PlanStateError("Closed engagement cannot be cancelled")
        return
    if target not in allowed.get(current, set()):
        raise PlanStateError(f"Invalid external engagement transition {current}->{target}")
    organization = session.get(ExternalOrganization, engagement.organization_id)
    if organization is None:
        raise NotFoundError("External organization not found")
    if target == ExternalEngagementState.REQUESTED and (
        organization.verification_state != VerificationState.VERIFIED.value
    ):
        raise PlanStateError("A verified organization is required before requesting work")
    quotes = session.scalars(
        select(ExternalQuote).where(
            ExternalQuote.engagement_id == engagement.id,
            ExternalQuote.project_id == engagement.project_id,
        )
    ).all()
    if target == ExternalEngagementState.QUOTED and not quotes:
        raise PlanStateError("At least one quote record is required")
    authorizations = session.scalars(
        select(ExternalAuthorization).where(
            ExternalAuthorization.engagement_id == engagement.id,
            ExternalAuthorization.project_id == engagement.project_id,
        )
    ).all()
    now = datetime.now(UTC)
    active_authorization = any(
        item.state == ExternalAuthorizationState.ACTIVE.value
        and item.expires_at > now
        and item.scope_sha256 == engagement.scope_sha256
        for item in authorizations
    )
    if target in {
        ExternalEngagementState.AUTHORIZED,
        ExternalEngagementState.EXECUTING,
    } and not active_authorization:
        raise PlanStateError("Active external authorization is required")
    contracts = session.scalars(
        select(ExternalContract).where(
            ExternalContract.engagement_id == engagement.id,
            ExternalContract.project_id == engagement.project_id,
        )
    ).all()
    if target == ExternalEngagementState.EXECUTING:
        accepted_quote = any(item.state == QuoteState.ACCEPTED.value for item in quotes)
        signed_contract = any(
            item.state == ContractState.SIGNED.value
            and item.internal_signed
            and item.external_signed
            and item.document_version_id is not None
            for item in contracts
        )
        if not accepted_quote or not signed_contract:
            raise PlanStateError(
                "Execution requires an accepted quote and signed external contract"
            )
    if target == ExternalEngagementState.ACCEPTED:
        deliverables = session.scalars(
            select(ExternalDeliverable).where(
                ExternalDeliverable.engagement_id == engagement.id,
                ExternalDeliverable.project_id == engagement.project_id,
            )
        ).all()
        if not deliverables or any(
            item.state != DeliverableState.ACCEPTED.value for item in deliverables
        ):
            raise PlanStateError("All deliverables must be accepted before engagement acceptance")


def _same_request(actual: str, provided: str, label: str) -> None:
    if actual != provided:
        raise ConflictingOperationError(
            f"{label} idempotency key was reused with different parameters"
        )


def _date_end(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.max, tzinfo=UTC)


def _event(
    session: Session,
    project: Project,
    actor: User,
    event_type: str,
    object_id: UUID,
    object_revision: int,
    now: datetime,
    payload: dict[str, Any] | None = None,
) -> None:
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == project.id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=project.workspace_id,
            project_id=project.id,
            project_seq=(last_sequence or 0) + 1,
            type=event_type,
            actor_user_id=actor.id,
            object_type="external_record",
            object_id=object_id,
            object_revision=object_revision,
            payload=payload or {},
            correlation_id=uuid4(),
            created_at=now,
        )
    )


def _organization_view(row: ExternalOrganization) -> OrganizationView:
    return OrganizationView(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        provider_type=ProviderType(row.provider_type),
        capability_summary=row.capability_summary,
        source_refs=row.source_refs,
        verification_state=VerificationState(row.verification_state),
        revision=row.revision,
    )


def _contact_view(row: ExternalContact) -> ContactView:
    return ContactView(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        role=row.role,
        email=row.email,
        source_refs=row.source_refs,
        verification_state=VerificationState(row.verification_state),
        revision=row.revision,
    )


def _expert_view(row: ExternalExpert) -> ExpertView:
    return ExpertView(
        id=row.id,
        name=row.name,
        expertise=row.expertise,
        public_source_refs=row.public_source_refs,
        contact_email=row.contact_email,
        conflict_notes=row.conflict_notes,
        state=ExpertState(row.state),
        revision=row.revision,
    )


def _engagement_view(row: ExternalEngagement) -> EngagementView:
    return EngagementView(
        id=row.id,
        organization_id=row.organization_id,
        title=row.title,
        scope=EngagementScope.model_validate(row.scope),
        scope_sha256=row.scope_sha256,
        state=ExternalEngagementState(row.state),
        revision=row.revision,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _quote_view(row: ExternalQuote) -> QuoteView:
    return QuoteView(
        id=row.id,
        engagement_id=row.engagement_id,
        amount=row.amount,
        currency=row.currency,
        tax_included=row.tax_included,
        shipping_included=row.shipping_included,
        assumptions=row.assumptions,
        excluded_work=row.excluded_work,
        valid_until=row.valid_until,
        document_version_id=row.document_version_id,
        state=QuoteState(row.state),
        scope_sha256=row.scope_sha256,
        created_at=row.created_at,
    )


def _contract_view(row: ExternalContract) -> ContractView:
    return ContractView(
        id=row.id,
        engagement_id=row.engagement_id,
        quote_id=row.quote_id,
        title=row.title,
        terms_summary=row.terms_summary,
        document_version_id=row.document_version_id,
        state=ContractState(row.state),
        internal_signed=row.internal_signed,
        external_signed=row.external_signed,
        signed_at=row.signed_at,
        revision=row.revision,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _deliverable_view(row: ExternalDeliverable) -> DeliverableView:
    return DeliverableView(
        id=row.id,
        engagement_id=row.engagement_id,
        title=row.title,
        kind=DeliverableKind(row.kind),
        expected_items=row.expected_items,
        state=DeliverableState(row.state),
        knowledge_version_id=row.knowledge_version_id,
        manifest=row.manifest,
        missing_items=row.missing_items,
        receipt_summary=row.receipt_summary,
        received_at=row.received_at,
        reviewer_role=row.reviewer_role,
        review_summary=row.review_summary,
        findings=row.findings,
        due_at=row.due_at,
        revision=row.revision,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _professional_record_view(row: ProfessionalRecord) -> ProfessionalRecordView:
    return ProfessionalRecordView(
        id=row.id,
        kind=ProfessionalRecordKind(row.kind),
        state=ProfessionalRecordState(row.state),
        title=row.title,
        source_tier=row.source_tier,
        source_title=row.source_title,
        source_ref=row.source_ref,
        checked_at=row.checked_at,
        market=row.market,
        product_scope=row.product_scope,
        jurisdiction=row.jurisdiction,
        patent_status=row.patent_status,
        application_number=row.application_number,
        publication_number=row.publication_number,
        financial_event_type=row.financial_event_type,
        amount=row.amount,
        currency=row.currency,
        commercial_evidence_type=row.commercial_evidence_type,
        facts=row.facts,
        limitations=row.limitations,
        metadata=row.record_metadata,
        revision=row.revision,
        created_at=row.created_at,
    )


def _authorization_view(row: ExternalAuthorization) -> ExternalAuthorizationView:
    state = ExternalAuthorizationState(row.state)
    if state == ExternalAuthorizationState.ACTIVE and row.expires_at <= datetime.now(UTC):
        state = ExternalAuthorizationState.EXPIRED
    return ExternalAuthorizationView(
        id=row.id,
        engagement_id=row.engagement_id,
        action_scope=row.action_scope,
        scope_sha256=row.scope_sha256,
        amount_max=row.amount_max,
        currency=row.currency,
        valid_from=row.valid_from,
        expires_at=row.expires_at,
        state=state,
        revision=row.revision,
        created_at=row.created_at,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
