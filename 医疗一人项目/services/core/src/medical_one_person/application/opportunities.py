from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
    RevisionConflictError,
)
from medical_one_person.domain.opportunities import (
    OpportunityCard,
    OpportunityStatus,
    ScientificBrief,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    ClaimVersion,
    Decision,
    KnowledgeDocumentVersion,
    Opportunity,
    OpportunityVersion,
    Project,
    ProjectEvent,
    ScientificBriefRecord,
    User,
)


@dataclass(frozen=True)
class OpportunityRecord:
    id: UUID
    project_id: UUID
    title: str
    status: OpportunityStatus
    current_version: int
    revision: int
    card: OpportunityCard


@dataclass(frozen=True)
class SelectionResult:
    decision_id: UUID
    opportunity_id: UUID
    opportunity_version: int
    status: OpportunityStatus


class OpportunityService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        card: OpportunityCard,
    ) -> OpportunityRecord:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            opportunity = Opportunity(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                title=card.title,
                track=card.track.value,
                status=OpportunityStatus.PROPOSED.value,
                current_version=1,
                revision=1,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(opportunity)
            session.flush()
            session.add(
                OpportunityVersion(
                    id=uuid4(),
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    opportunity_id=opportunity.id,
                    version=1,
                    card=card.model_dump(mode="json"),
                    created_at=now,
                )
            )
            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="opportunity.created",
                object_type="opportunity",
                object_id=opportunity.id,
                object_revision=1,
                actor_user_id=actor.id,
                payload={"title": card.title, "track": card.track.value},
            )
            return _opportunity_record(opportunity, card)

    def revise(
        self,
        *,
        opportunity_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        card: OpportunityCard,
        status: OpportunityStatus,
    ) -> OpportunityRecord:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project_id = session.scalar(
                select(Opportunity.project_id).where(Opportunity.id == opportunity_id)
            )
            if project_id is None:
                raise NotFoundError("Opportunity not found")
            _locked_project(session, project_id, actor.workspace_id)
            opportunity = session.scalar(
                select(Opportunity)
                .where(
                    Opportunity.id == opportunity_id,
                    Opportunity.project_id == project_id,
                )
                .with_for_update()
            )
            if opportunity is None:
                raise NotFoundError("Opportunity not found")
            if opportunity.revision != expected_revision:
                raise RevisionConflictError("Opportunity revision conflict")
            opportunity.current_version += 1
            opportunity.revision += 1
            opportunity.title = card.title
            opportunity.track = card.track.value
            opportunity.status = status.value
            opportunity.updated_at = datetime.now(UTC)
            session.add(
                OpportunityVersion(
                    id=uuid4(),
                    workspace_id=opportunity.workspace_id,
                    project_id=opportunity.project_id,
                    opportunity_id=opportunity.id,
                    version=opportunity.current_version,
                    card=card.model_dump(mode="json"),
                    created_at=datetime.now(UTC),
                )
            )
            _append_event(
                session,
                project_id=opportunity.project_id,
                workspace_id=opportunity.workspace_id,
                event_type="opportunity.revised",
                object_type="opportunity",
                object_id=opportunity.id,
                object_revision=opportunity.revision,
                actor_user_id=actor.id,
                payload={"version": opportunity.current_version, "status": status.value},
            )
            return _opportunity_record(opportunity, card)

    def compare(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
    ) -> list[OpportunityRecord]:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            if actor.workspace_id != workspace_id:
                raise PermissionError("Actor does not belong to the requested workspace")
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _project(session, project_id, actor.workspace_id)
            rows = session.execute(
                select(Opportunity, OpportunityVersion)
                .join(
                    OpportunityVersion,
                    (OpportunityVersion.opportunity_id == Opportunity.id)
                    & (OpportunityVersion.version == Opportunity.current_version),
                )
                .where(Opportunity.project_id == project.id)
                .order_by(Opportunity.track, Opportunity.title)
            ).all()
            return [
                _opportunity_record(
                    opportunity,
                    OpportunityCard.model_validate(version.card),
                )
                for opportunity, version in rows
            ]

    def select_opportunity(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        opportunity_id: UUID,
        expected_revision: int,
        reason: str,
        scope: str,
        evidence_version_ids: list[str],
        idempotency_key: str,
    ) -> SelectionResult:
        if not reason.strip() or not scope.strip() or not idempotency_key.strip():
            raise ValueError("Selection reason, scope, and idempotency key are required")
        evidence_version_ids = _normalize_evidence_ids(evidence_version_ids)
        request_hash = _digest(
            {
                "opportunity_id": str(opportunity_id),
                "expected_revision": expected_revision,
                "reason": reason,
                "scope": scope,
                "evidence_version_ids": evidence_version_ids,
            }
        )
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            if actor.workspace_id != workspace_id or not actor.is_owner:
                raise PermissionError("Only the verified workspace owner can select opportunities")
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            existing = session.scalar(
                select(Decision).where(
                    Decision.project_id == project.id,
                    Decision.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise ConflictingOperationError(
                        "Selection idempotency key was reused with different parameters"
                    )
                return SelectionResult(
                    decision_id=existing.id,
                    opportunity_id=existing.selected_opportunity_id,
                    opportunity_version=existing.selected_opportunity_version,
                    status=OpportunityStatus.SELECTED,
                )
            _validate_evidence_versions(
                session,
                project_id=project.id,
                evidence_version_ids=evidence_version_ids,
            )
            opportunity = session.scalar(
                select(Opportunity)
                .where(
                    Opportunity.id == opportunity_id,
                    Opportunity.project_id == project.id,
                )
                .with_for_update()
            )
            if opportunity is None:
                raise NotFoundError("Opportunity not found")
            if opportunity.revision != expected_revision:
                raise RevisionConflictError("Opportunity revision conflict")
            options = [
                {
                    "opportunity_id": str(candidate.id),
                    "title": candidate.title,
                    "track": candidate.track,
                    "version": candidate.current_version,
                    "status": candidate.status,
                }
                for candidate in session.scalars(
                    select(Opportunity)
                    .where(Opportunity.project_id == project.id)
                    .order_by(Opportunity.created_at)
                )
            ]
            now = datetime.now(UTC)
            decision = Decision(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                kind="opportunity_selection",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                options=options,
                selected={
                    "opportunity_id": str(opportunity.id),
                    "title": opportunity.title,
                    "version": opportunity.current_version,
                },
                selected_opportunity_id=opportunity.id,
                selected_opportunity_version=opportunity.current_version,
                reason=reason,
                evidence_version_ids=evidence_version_ids,
                actor_user_id=actor.id,
                scope=scope,
                effective_at=now,
                created_at=now,
            )
            session.add(decision)
            opportunity.status = OpportunityStatus.SELECTED.value
            opportunity.revision += 1
            opportunity.updated_at = now
            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="opportunity.selected",
                object_type="decision",
                object_id=decision.id,
                object_revision=1,
                actor_user_id=actor.id,
                payload={
                    "opportunity_id": str(opportunity.id),
                    "version": opportunity.current_version,
                },
            )
            session.flush()
            return SelectionResult(
                decision_id=decision.id,
                opportunity_id=opportunity.id,
                opportunity_version=opportunity.current_version,
                status=OpportunityStatus.SELECTED,
            )

    def create_scientific_brief(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        project_id: UUID,
        brief: ScientificBrief,
    ) -> UUID:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
            project = _locked_project(session, project_id, actor.workspace_id)
            current = session.scalar(
                select(func.max(ScientificBriefRecord.brief_version)).where(
                    ScientificBriefRecord.project_id == project.id
                )
            )
            record = ScientificBriefRecord(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                brief_version=(current or 0) + 1,
                content=brief.model_dump(mode="json"),
                created_by_user_id=actor.id,
                created_at=datetime.now(UTC),
            )
            session.add(record)
            session.flush()
            _append_event(
                session,
                project_id=project.id,
                workspace_id=project.workspace_id,
                event_type="scientific_brief.created",
                object_type="scientific_brief",
                object_id=record.id,
                object_revision=record.brief_version,
                actor_user_id=actor.id,
                payload={"brief_version": record.brief_version},
            )
            return record.id


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("User not found")
    return actor


def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace_id:
        raise NotFoundError("Project not found")
    return project


def _locked_project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
    project = session.scalar(
        select(Project)
        .where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    if project is None:
        raise NotFoundError("Project not found")
    return project


def _normalize_evidence_ids(values: list[str]) -> list[str]:
    try:
        parsed = [UUID(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("Evidence version IDs must be UUIDs") from exc
    if len(parsed) != len(set(parsed)):
        raise ValueError("Evidence version IDs must be unique")
    return sorted(str(value) for value in parsed)


def _validate_evidence_versions(
    session: Session,
    *,
    project_id: UUID,
    evidence_version_ids: list[str],
) -> None:
    if not evidence_version_ids:
        return
    requested = {UUID(value) for value in evidence_version_ids}
    claim_ids = set(
        session.scalars(
            select(ClaimVersion.id).where(
                ClaimVersion.project_id == project_id,
                ClaimVersion.id.in_(requested),
            )
        )
    )
    document_version_ids = set(
        session.scalars(
            select(KnowledgeDocumentVersion.id).where(
                KnowledgeDocumentVersion.project_id == project_id,
                KnowledgeDocumentVersion.id.in_(requested),
            )
        )
    )
    if requested - claim_ids - document_version_ids:
        raise NotFoundError("Evidence version not found in project")


def _opportunity_record(opportunity: Opportunity, card: OpportunityCard) -> OpportunityRecord:
    return OpportunityRecord(
        id=opportunity.id,
        project_id=opportunity.project_id,
        title=opportunity.title,
        status=OpportunityStatus(opportunity.status),
        current_version=opportunity.current_version,
        revision=opportunity.revision,
        card=card,
    )


def _digest(value: dict[str, object]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _append_event(
    session: Session,
    *,
    project_id: UUID,
    workspace_id: UUID,
    event_type: str,
    object_type: str,
    object_id: UUID,
    object_revision: int,
    actor_user_id: UUID,
    payload: dict[str, object],
) -> None:
    last_sequence = session.scalar(
        select(ProjectEvent.project_seq)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.project_seq.desc())
        .limit(1)
    )
    session.add(
        ProjectEvent(
            id=uuid4(),
            workspace_id=workspace_id,
            project_id=project_id,
            project_seq=(last_sequence or 0) + 1,
            type=event_type,
            actor_user_id=actor_user_id,
            object_type=object_type,
            object_id=object_id,
            object_revision=object_revision,
            payload=payload,
            correlation_id=uuid4(),
            created_at=datetime.now(UTC),
        )
    )
