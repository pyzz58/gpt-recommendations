"""Authorized issue, action, Query and carryover workflow service."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import DocumentVersion, SourceAnchor
from cra_app.documents.service import DocumentService
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.issues.carryover_import import (
    CarryoverCandidateDraft,
    CarryoverPreview,
    preview_anchors,
    preview_text,
    preview_xlsx,
)
from cra_app.issues.contracts import (
    ActionCreate,
    AddActionCommand,
    ConfirmCarryoverImportCommand,
    ConfirmCorrectedCommand,
    ConfirmReportedCommand,
    CreateIssueCommand,
    CreateQueryLinkCommand,
    PreviewCarryoverDocumentCommand,
    PreviewCarryoverTextCommand,
    RecordReplyCommand,
    ReopenActionCommand,
)
from cra_app.issues.models import (
    ActionItem,
    CarryoverCandidate,
    CarryoverImport,
    Issue,
    IssueHistory,
    QueryLink,
)
from cra_app.platform.jobs import digest_payload
from cra_app.shared.output_contract import (
    Claim,
    InputRevision,
    NotCheckedItem,
    OutputCapability,
    OutputEnvelope,
    OutputScope,
    SourceRef,
    UnknownItem,
)


class IssueServiceError(Exception):
    pass


class IssueNotFound(IssueServiceError):
    pass


class IssueValidationError(IssueServiceError):
    pass


class IssueConflict(IssueServiceError):
    pass


@dataclass(frozen=True)
class IssueDetail:
    issue: Issue
    actions: tuple[ActionItem, ...]
    history: tuple[IssueHistory, ...]
    query_links: tuple[QueryLink, ...]


@dataclass(frozen=True)
class CarryoverImportDetail:
    import_record: CarryoverImport
    candidates: tuple[CarryoverCandidate, ...]
    replayed: bool


@dataclass(frozen=True)
class ConfirmationOutcome:
    actions: tuple[ActionItem, ...]
    replayed: bool


def _dedupe_json(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in items:
        marker = json.dumps(
            item, ensure_ascii=False, sort_keys=True, default=str
        )
        if marker not in seen:
            result.append(item)
            seen.add(marker)
    return result


def aggregate_action_status(actions: list[ActionItem] | tuple[ActionItem, ...]) -> str:
    if not actions:
        return "incomplete"
    statuses = {action.status for action in actions}
    if statuses == {"completed"}:
        return "completed"
    if "needs_correction" in statuses:
        return "needs_correction"
    if statuses & {"completed", "reported_done"}:
        return "in_progress"
    return "open"


class IssueService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService | None = None,
        documents: DocumentService | None = None,
    ):
        self.session_factory = session_factory
        self.governance = governance or GovernanceService(session_factory)
        self.documents = documents

    def _authorize_read(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "read_site", study_id, site_id)

    def _authorize_write(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "write_site", study_id, site_id)

    @staticmethod
    def _scope_fingerprint(
        scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> str:
        return digest_payload(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id),
                "site_id": str(site_id),
            }
        )

    def _reserve_idempotency(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        command_name: str,
        command: Any,
        request_payload: dict[str, Any] | None = None,
    ) -> tuple[IdempotencyRecord, bool]:
        scope_fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": scope_fingerprint,
                "command": command.model_dump(mode="json"),
                "request": request_payload or {},
            }
        )
        record_id = uuid.uuid4()
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=record_id,
                actor_id=scope.actor_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                scope_fingerprint=scope_fingerprint,
                command_name=command_name,
                idempotency_key=command.idempotency_key,
                request_digest=request_digest,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "actor_id",
                    "tenant_id",
                    "scope_fingerprint",
                    "command_name",
                    "idempotency_key",
                ]
            )
        )
        record = session.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == scope.actor_id,
                IdempotencyRecord.tenant_id == scope.tenant_id,
                IdempotencyRecord.scope_fingerprint == scope_fingerprint,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key == command.idempotency_key,
            )
            .with_for_update()
        )
        if record is None:
            raise RuntimeError("failed to reserve idempotency key")
        if record.request_digest != request_digest:
            raise IdempotencyConflict(
                "idempotency key was already used with different input"
            )
        return record, record.response_resource_id is not None

    @staticmethod
    def _complete_idempotency(
        record: IdempotencyRecord,
        resource_id: uuid.UUID,
        revision: int,
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    @staticmethod
    def _audit(
        session: Session,
        *,
        scope: ScopeContext,
        issue: Issue,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        revision_before: int | None,
        revision_after: int,
        after_state: dict[str, Any],
        command_name: str,
        correlation_id: uuid.UUID,
    ) -> None:
        session.add(
            AuditEvent(
                id=uuid.uuid4(),
                tenant_id=scope.tenant_id,
                study_id=issue.study_id,
                site_id=issue.site_id,
                actor_id=scope.actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                revision_before=revision_before,
                revision_after=revision_after,
                before_state=None,
                after_state=after_state,
                command_name=command_name,
                correlation_id=correlation_id,
            )
        )

    @staticmethod
    def _next_action_key(actions: list[ActionItem], preferred: str | None) -> str:
        used = {action.action_key for action in actions}
        if preferred and preferred not in used:
            return preferred
        index = 1
        while f"A{index}" in used:
            index += 1
        return f"A{index}"

    def _create_action(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        issue: Issue,
        draft: ActionCreate | CarryoverCandidateDraft,
        action_key: str,
    ) -> ActionItem:
        if isinstance(draft, ActionCreate):
            kind = draft.kind
            requirement = draft.requirement
            due_on = draft.due_on
            deadline_source = draft.deadline_source
            deadline_refs = draft.deadline_source_refs
        else:
            kind = draft.kind
            requirement = draft.requirement
            due_on = None
            deadline_source = None
            deadline_refs = []
        action = ActionItem(
            id=uuid.uuid4(),
            tenant_id=scope.tenant_id,
            study_id=issue.study_id,
            site_id=issue.site_id,
            issue_id=issue.id,
            action_key=action_key,
            kind=kind,
            requirement=requirement,
            status="open",
            completion_basis=None,
            completed_by=None,
            completed_at=None,
            completion_note=None,
            due_on=due_on,
            deadline_source=deadline_source,
            deadline_source_refs=deadline_refs,
            revision=1,
            created_by=scope.actor_id,
            updated_by=scope.actor_id,
        )
        session.add(action)
        session.flush()
        session.add(
            IssueHistory(
                id=uuid.uuid4(),
                tenant_id=scope.tenant_id,
                study_id=issue.study_id,
                site_id=issue.site_id,
                issue_id=issue.id,
                action_id=action.id,
                event_type="action_created",
                actor_id=scope.actor_id,
                details={
                    "action_key": action_key,
                    "kind": kind,
                    "requirement": requirement,
                    "deadline_source": deadline_source,
                },
            )
        )
        return action

    def _load_issue(self, scope: ScopeContext, issue_id: uuid.UUID) -> Issue:
        with self.session_factory() as session:
            issue = session.scalar(
                select(Issue).where(
                    Issue.id == issue_id,
                    Issue.tenant_id == scope.tenant_id,
                )
            )
            if issue is None:
                raise IssueNotFound("issue was not found")
            return issue

    def _load_action(
        self, scope: ScopeContext, action_id: uuid.UUID
    ) -> ActionItem:
        with self.session_factory() as session:
            action = session.scalar(
                select(ActionItem).where(
                    ActionItem.id == action_id,
                    ActionItem.tenant_id == scope.tenant_id,
                )
            )
            if action is None:
                raise IssueNotFound("action was not found")
            return action

    def _issue_detail_in_session(
        self, session: Session, issue: Issue
    ) -> IssueDetail:
        actions = tuple(
            session.scalars(
                select(ActionItem)
                .where(
                    ActionItem.tenant_id == issue.tenant_id,
                    ActionItem.study_id == issue.study_id,
                    ActionItem.issue_id == issue.id,
                )
                .order_by(ActionItem.action_key)
            )
        )
        history = tuple(
            session.scalars(
                select(IssueHistory)
                .where(
                    IssueHistory.tenant_id == issue.tenant_id,
                    IssueHistory.study_id == issue.study_id,
                    IssueHistory.issue_id == issue.id,
                )
                .order_by(IssueHistory.occurred_at, IssueHistory.id)
            )
        )
        query_links = tuple(
            session.scalars(
                select(QueryLink)
                .where(
                    QueryLink.tenant_id == issue.tenant_id,
                    QueryLink.study_id == issue.study_id,
                    QueryLink.issue_id == issue.id,
                )
                .order_by(QueryLink.created_at)
            )
        )
        return IssueDetail(
            issue=issue,
            actions=actions,
            history=history,
            query_links=query_links,
        )

    def issue_detail(
        self, scope: ScopeContext, issue_id: uuid.UUID
    ) -> IssueDetail:
        issue = self._load_issue(scope, issue_id)
        self._authorize_read(scope, issue.study_id, issue.site_id)
        with self.session_factory() as session:
            return self._issue_detail_in_session(session, issue)

    def list_issues(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        *,
        remaining_only: bool = False,
    ) -> list[IssueDetail]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            issues = list(
                session.scalars(
                    select(Issue)
                    .where(
                        Issue.tenant_id == scope.tenant_id,
                        Issue.study_id == study_id,
                        Issue.site_id == site_id,
                    )
                    .order_by(Issue.created_at, Issue.issue_number)
                )
            )
            details = [
                self._issue_detail_in_session(session, issue) for issue in issues
            ]
            if remaining_only:
                details = [
                    item
                    for item in details
                    if aggregate_action_status(item.actions) != "completed"
                ]
            return details

    def create_issue(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateIssueCommand,
    ) -> IssueDetail:
        self._authorize_write(scope, study_id, command.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=command.site_id,
                    command_name="issues.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    issue = session.get(Issue, record.response_resource_id)
                    if issue is None:
                        raise IssueNotFound("replayed issue was not found")
                    return self._issue_detail_in_session(session, issue)
                if command.subject_id is not None:
                    from cra_app.subjects.models import Subject

                    subject = session.scalar(
                        select(Subject).where(
                            Subject.id == command.subject_id,
                            Subject.tenant_id == scope.tenant_id,
                            Subject.study_id == study_id,
                            Subject.site_id == command.site_id,
                        )
                    )
                    if subject is None:
                        raise IssueValidationError(
                            "subject is outside the requested site"
                        )
                if command.source_document_version_id is not None:
                    version = session.scalar(
                        select(DocumentVersion).where(
                            DocumentVersion.id
                            == command.source_document_version_id,
                            DocumentVersion.tenant_id == scope.tenant_id,
                            DocumentVersion.study_id == study_id,
                        )
                    )
                    if version is None or version.site_id != command.site_id:
                        raise IssueValidationError(
                            "source document version is outside the issue site"
                        )
                if command.source_anchor_id is not None:
                    if command.source_document_version_id is None:
                        raise IssueValidationError(
                            "source anchor requires its document version"
                        )
                    anchor = session.scalar(
                        select(SourceAnchor).where(
                            SourceAnchor.id == command.source_anchor_id,
                            SourceAnchor.tenant_id == scope.tenant_id,
                            SourceAnchor.study_id == study_id,
                            SourceAnchor.document_version_id
                            == command.source_document_version_id,
                        )
                    )
                    if anchor is None:
                        raise IssueValidationError(
                            "source anchor does not belong to the source version"
                        )
                issue_number = (
                    command.issue_number.strip()
                    if command.issue_number
                    else f"ISS-{uuid.uuid4().hex[:12].upper()}"
                )
                duplicate = session.scalar(
                    select(Issue.id).where(
                        Issue.tenant_id == scope.tenant_id,
                        Issue.study_id == study_id,
                        Issue.site_id == command.site_id,
                        Issue.issue_number == issue_number,
                    )
                )
                if duplicate is not None:
                    raise IssueConflict(
                        "issue number already exists at this site"
                    )
                issue = Issue(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=study_id,
                    site_id=command.site_id,
                    subject_id=command.subject_id,
                    issue_number=issue_number,
                    original_finding=command.original_finding,
                    location=command.location,
                    recommendation=command.recommendation,
                    recommendation_sources=command.recommendation_sources,
                    reported_correction=command.reported_correction,
                    known_progress=command.known_progress,
                    source_kind=command.source_kind,
                    verification_status="user_reviewed",
                    source_document_version_id=command.source_document_version_id,
                    source_anchor_id=command.source_anchor_id,
                    source_original_key=command.source_original_key,
                    source_refs=command.source_refs,
                    revision=1,
                    created_by=scope.actor_id,
                    updated_by=scope.actor_id,
                )
                session.add(issue)
                session.flush()
                session.add(
                    IssueHistory(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        issue_id=issue.id,
                        action_id=None,
                        event_type="issue_created",
                        actor_id=scope.actor_id,
                        details={
                            "issue_number": issue_number,
                            "source_kind": command.source_kind,
                        },
                    )
                )
                actions: list[ActionItem] = []
                used_keys: set[str] = set()
                for index, action_command in enumerate(command.actions, start=1):
                    key = self._next_action_key(actions, action_command.action_key)
                    if action_command.action_key and action_command.action_key in used_keys:
                        raise IssueValidationError("action keys must be unique")
                    used_keys.add(key)
                    actions.append(
                        self._create_action(
                            session,
                            scope=scope,
                            issue=issue,
                            draft=action_command,
                            action_key=key,
                        )
                    )
                self._audit(
                    session,
                    scope=scope,
                    issue=issue,
                    action="issues.create",
                    resource_type="issue",
                    resource_id=issue.id,
                    revision_before=None,
                    revision_after=issue.revision,
                    after_state={
                        "issue_number": issue.issue_number,
                        "actions": [action.action_key for action in actions],
                    },
                    command_name="issues.create",
                    correlation_id=record.id,
                )
                self._complete_idempotency(
                    record, issue.id, issue.revision
                )
                return self._issue_detail_in_session(session, issue)

    def add_action(
        self,
        scope: ScopeContext,
        issue_id: uuid.UUID,
        command: AddActionCommand,
    ) -> IssueDetail:
        issue = self._load_issue(scope, issue_id)
        self._authorize_write(scope, issue.study_id, issue.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                issue = session.scalar(
                    select(Issue)
                    .where(
                        Issue.id == issue_id,
                        Issue.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if issue is None:
                    raise IssueNotFound("issue was not found")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=issue.study_id,
                    site_id=issue.site_id,
                    command_name="issues.actions.create",
                    command=command,
                )
                if replayed:
                    return self._issue_detail_in_session(session, issue)
                if issue.revision != command.expected_revision:
                    raise RevisionConflict(issue.revision)
                existing_actions = list(
                    session.scalars(
                        select(ActionItem).where(
                            ActionItem.issue_id == issue.id
                        )
                    )
                )
                key = self._next_action_key(
                    existing_actions, command.action.action_key
                )
                action = self._create_action(
                    session,
                    scope=scope,
                    issue=issue,
                    draft=command.action,
                    action_key=key,
                )
                issue.revision += 1
                issue.updated_by = scope.actor_id
                self._audit(
                    session,
                    scope=scope,
                    issue=issue,
                    action="issues.actions.create",
                    resource_type="issue_action",
                    resource_id=action.id,
                    revision_before=command.expected_revision,
                    revision_after=issue.revision,
                    after_state={
                        "issue_number": issue.issue_number,
                        "action_key": action.action_key,
                        "kind": action.kind,
                    },
                    command_name="issues.actions.create",
                    correlation_id=record.id,
                )
                self._complete_idempotency(
                    record, action.id, action.revision
                )
                return self._issue_detail_in_session(session, issue)

    def confirm_corrected(
        self,
        scope: ScopeContext,
        command: ConfirmCorrectedCommand,
    ) -> ConfirmationOutcome:
        first = self._load_action(scope, command.actions[0].action_id)
        self._authorize_write(scope, first.study_id, first.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                targets = {
                    item.action_id: item.expected_revision
                    for item in command.actions
                }
                actions = list(
                    session.scalars(
                        select(ActionItem)
                        .where(
                            ActionItem.id.in_(targets),
                            ActionItem.tenant_id == scope.tenant_id,
                        )
                        .order_by(ActionItem.id)
                        .with_for_update()
                    )
                )
                if len(actions) != len(targets):
                    raise IssueNotFound("one or more actions were not found")
                if any(
                    action.study_id != first.study_id
                    or action.site_id != first.site_id
                    for action in actions
                ):
                    raise IssueValidationError(
                        "a confirmation batch must stay within one site"
                    )
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=first.study_id,
                    site_id=first.site_id,
                    command_name="issues.actions.confirm_corrected",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    assert record.response_revision is not None
                    replay_actions = tuple(
                        session.scalars(
                            select(ActionItem).where(
                                ActionItem.id.in_(targets),
                                ActionItem.tenant_id == scope.tenant_id,
                            )
                        )
                    )
                    return ConfirmationOutcome(
                        actions=replay_actions, replayed=True
                    )
                for action in actions:
                    if action.revision != targets[action.id]:
                        raise RevisionConflict(action.revision)
                    if action.kind == "pd_reporting":
                        raise IssueValidationError(
                            "PD reporting requires explicit confirm-reported"
                        )
                now = datetime.now(UTC)
                issue_ids = {action.issue_id for action in actions}
                issues = {
                    issue.id: issue
                    for issue in session.scalars(
                        select(Issue)
                        .where(Issue.id.in_(issue_ids))
                        .with_for_update()
                    )
                }
                for action in actions:
                    issue = issues[action.issue_id]
                    before = action.status
                    action.status = "completed"
                    action.completion_basis = "user_confirmation"
                    action.completed_by = scope.actor_id
                    action.completed_at = now
                    action.completion_note = command.optional_note
                    action.updated_by = scope.actor_id
                    action.revision += 1
                    session.add(
                        IssueHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=issue.study_id,
                            site_id=issue.site_id,
                            issue_id=issue.id,
                            action_id=action.id,
                            event_type="action_confirmed",
                            actor_id=scope.actor_id,
                            details={
                                "completion_basis": "user_confirmation",
                                "confirmed_at": now.isoformat(),
                                "before_status": before,
                                "optional_note": command.optional_note,
                                "statement": "CRA confirmed the selected action",
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        issue=issue,
                        action="issues.actions.confirm_corrected",
                        resource_type="issue_action",
                        resource_id=action.id,
                        revision_before=targets[action.id],
                        revision_after=action.revision,
                        after_state={
                            "status": action.status,
                            "completion_basis": action.completion_basis,
                        },
                        command_name="issues.actions.confirm_corrected",
                        correlation_id=record.id,
                    )
                for issue in issues.values():
                    issue.revision += 1
                    issue.updated_by = scope.actor_id
                self._complete_idempotency(
                    record, actions[0].id, actions[0].revision
                )
                return ConfirmationOutcome(
                    actions=tuple(actions), replayed=False
                )

    def confirm_reported(
        self,
        scope: ScopeContext,
        action_id: uuid.UUID,
        command: ConfirmReportedCommand,
    ) -> ActionItem:
        action = self._load_action(scope, action_id)
        self._authorize_write(scope, action.study_id, action.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                action = session.scalar(
                    select(ActionItem)
                    .where(
                        ActionItem.id == action_id,
                        ActionItem.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if action is None:
                    raise IssueNotFound("action was not found")
                if action.kind != "pd_reporting":
                    raise IssueValidationError(
                        "confirm-reported is only valid for pd_reporting"
                    )
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=action.study_id,
                    site_id=action.site_id,
                    command_name="issues.actions.confirm_reported",
                    command=command,
                    request_payload={"action_id": str(action.id)},
                )
                if replayed:
                    return action
                if action.revision != command.expected_revision:
                    raise RevisionConflict(action.revision)
                issue = session.scalar(
                    select(Issue)
                    .where(Issue.id == action.issue_id)
                    .with_for_update()
                )
                assert issue is not None
                now = datetime.now(UTC)
                action.status = "completed"
                action.completion_basis = "user_confirmation"
                action.completed_by = scope.actor_id
                action.completed_at = now
                action.completion_note = (
                    command.optional_note
                    or command.user_statement
                )
                action.updated_by = scope.actor_id
                action.revision += 1
                issue.revision += 1
                issue.updated_by = scope.actor_id
                session.add(
                    IssueHistory(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=issue.study_id,
                        site_id=issue.site_id,
                        issue_id=issue.id,
                        action_id=action.id,
                        event_type="action_reported",
                        actor_id=scope.actor_id,
                        details={
                            "completion_basis": "user_confirmation",
                            "confirmed_at": now.isoformat(),
                            "user_statement": command.user_statement,
                            "optional_note": command.optional_note,
                        },
                    )
                )
                self._audit(
                    session,
                    scope=scope,
                    issue=issue,
                    action="issues.actions.confirm_reported",
                    resource_type="issue_action",
                    resource_id=action.id,
                    revision_before=command.expected_revision,
                    revision_after=action.revision,
                    after_state={
                        "kind": action.kind,
                        "status": action.status,
                        "completion_basis": action.completion_basis,
                    },
                    command_name="issues.actions.confirm_reported",
                    correlation_id=record.id,
                )
                self._complete_idempotency(
                    record, action.id, action.revision
                )
                return action

    def reopen_action(
        self,
        scope: ScopeContext,
        action_id: uuid.UUID,
        command: ReopenActionCommand,
    ) -> ActionItem:
        action = self._load_action(scope, action_id)
        self._authorize_write(scope, action.study_id, action.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                action = session.scalar(
                    select(ActionItem)
                    .where(
                        ActionItem.id == action_id,
                        ActionItem.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if action is None:
                    raise IssueNotFound("action was not found")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=action.study_id,
                    site_id=action.site_id,
                    command_name="issues.actions.reopen",
                    command=command,
                    request_payload={"action_id": str(action.id)},
                )
                if replayed:
                    return action
                if action.revision != command.expected_revision:
                    raise RevisionConflict(action.revision)
                issue = session.scalar(
                    select(Issue)
                    .where(Issue.id == action.issue_id)
                    .with_for_update()
                )
                assert issue is not None
                previous = action.status
                action.status = "open"
                action.completion_basis = None
                action.completed_by = None
                action.completed_at = None
                action.completion_note = None
                action.updated_by = scope.actor_id
                action.revision += 1
                issue.revision += 1
                issue.updated_by = scope.actor_id
                session.add(
                    IssueHistory(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=issue.study_id,
                        site_id=issue.site_id,
                        issue_id=issue.id,
                        action_id=action.id,
                        event_type="action_reopened",
                        actor_id=scope.actor_id,
                        details={
                            "reason": command.reason,
                            "previous_status": previous,
                            "status": "open",
                        },
                    )
                )
                self._audit(
                    session,
                    scope=scope,
                    issue=issue,
                    action="issues.actions.reopen",
                    resource_type="issue_action",
                    resource_id=action.id,
                    revision_before=command.expected_revision,
                    revision_after=action.revision,
                    after_state={
                        "status": action.status,
                        "reason": command.reason,
                    },
                    command_name="issues.actions.reopen",
                    correlation_id=record.id,
                )
                self._complete_idempotency(
                    record, action.id, action.revision
                )
                return action

    def record_reply(
        self,
        scope: ScopeContext,
        issue_id: uuid.UUID,
        command: RecordReplyCommand,
    ) -> IssueDetail:
        issue = self._load_issue(scope, issue_id)
        self._authorize_write(scope, issue.study_id, issue.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                issue = session.scalar(
                    select(Issue)
                    .where(
                        Issue.id == issue_id,
                        Issue.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if issue is None:
                    raise IssueNotFound("issue was not found")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=issue.study_id,
                    site_id=issue.site_id,
                    command_name="issues.reply.record",
                    command=command,
                )
                if replayed:
                    return self._issue_detail_in_session(session, issue)
                if issue.revision != command.expected_revision:
                    raise RevisionConflict(issue.revision)
                previous = issue.reported_correction
                issue.reported_correction = command.statement
                issue.revision += 1
                issue.updated_by = scope.actor_id
                session.add(
                    IssueHistory(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=issue.study_id,
                        site_id=issue.site_id,
                        issue_id=issue.id,
                        action_id=None,
                        event_type="reply_recorded",
                        actor_id=scope.actor_id,
                        details={
                            "previous_reported_correction": previous,
                            "statement": command.statement,
                            "does_not_complete_actions": True,
                        },
                    )
                )
                self._audit(
                    session,
                    scope=scope,
                    issue=issue,
                    action="issues.reply.record",
                    resource_type="issue",
                    resource_id=issue.id,
                    revision_before=command.expected_revision,
                    revision_after=issue.revision,
                    after_state={"reported_correction": command.statement},
                    command_name="issues.reply.record",
                    correlation_id=record.id,
                )
                self._complete_idempotency(
                    record, issue.id, issue.revision
                )
                return self._issue_detail_in_session(session, issue)

    def create_query_link(
        self,
        scope: ScopeContext,
        issue_id: uuid.UUID,
        command: CreateQueryLinkCommand,
    ) -> QueryLink:
        issue = self._load_issue(scope, issue_id)
        self._authorize_write(scope, issue.study_id, issue.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                issue = session.scalar(
                    select(Issue)
                    .where(
                        Issue.id == issue_id,
                        Issue.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if issue is None:
                    raise IssueNotFound("issue was not found")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=issue.study_id,
                    site_id=issue.site_id,
                    command_name="issues.query.create",
                    command=command,
                    request_payload={"issue_id": str(issue.id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    query = session.get(QueryLink, record.response_resource_id)
                    if query is None:
                        raise IssueNotFound("replayed Query was not found")
                    return query
                if issue.revision != command.expected_revision:
                    raise RevisionConflict(issue.revision)
                query = QueryLink(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=issue.study_id,
                    site_id=issue.site_id,
                    issue_id=issue.id,
                    query_state=command.query_state,
                    external_system=command.external_system,
                    external_query_number=command.external_query_number,
                    opened_on=command.opened_on,
                    due_on=command.due_on,
                    deadline_source=command.deadline_source,
                    deadline_source_refs=command.deadline_source_refs,
                    replied_on=command.replied_on,
                    reply_summary=command.reply_summary,
                    revision=1,
                    created_by=scope.actor_id,
                    updated_by=scope.actor_id,
                )
                session.add(query)
                session.flush()
                issue.revision += 1
                issue.updated_by = scope.actor_id
                session.add(
                    IssueHistory(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=issue.study_id,
                        site_id=issue.site_id,
                        issue_id=issue.id,
                        action_id=None,
                        event_type="query_linked",
                        actor_id=scope.actor_id,
                        details={
                            "query_id": str(query.id),
                            "query_state": query.query_state,
                            "external_query_number": query.external_query_number,
                            "opened_on": (
                                query.opened_on.isoformat()
                                if query.opened_on
                                else None
                            ),
                            "due_on": (
                                query.due_on.isoformat()
                                if query.due_on
                                else None
                            ),
                            "deadline_source": query.deadline_source,
                        },
                    )
                )
                self._audit(
                    session,
                    scope=scope,
                    issue=issue,
                    action="issues.query.create",
                    resource_type="query_link",
                    resource_id=query.id,
                    revision_before=command.expected_revision,
                    revision_after=issue.revision,
                    after_state={
                        "issue_number": issue.issue_number,
                        "query_state": query.query_state,
                        "external_query_number": query.external_query_number,
                        "deadline_source": query.deadline_source,
                    },
                    command_name="issues.query.create",
                    correlation_id=record.id,
                )
                self._complete_idempotency(record, query.id, query.revision)
                return query

    @staticmethod
    def _candidate_actions(
        candidate: CarryoverCandidate | CarryoverCandidateDraft,
        corrections: dict[str, Any] | None = None,
    ) -> list[ActionCreate]:
        corrections = corrections or {}
        if "actions" in corrections and corrections["actions"] is not None:
            raw_actions = corrections["actions"]
            return [
                item if isinstance(item, ActionCreate) else ActionCreate.model_validate(item)
                for item in raw_actions
            ]
        raw_actions = (
            candidate.actions
            if isinstance(candidate, CarryoverCandidateDraft)
            else candidate.actions
        )
        result = []
        for item in raw_actions:
            if isinstance(item, ActionCreate):
                result.append(item)
            elif hasattr(item, "kind"):
                result.append(
                    ActionCreate(
                        action_key=getattr(item, "action_key", None),
                        kind=item.kind,
                        requirement=getattr(item, "requirement", None),
                    )
                )
            else:
                result.append(ActionCreate.model_validate(item))
        return result

    @staticmethod
    def _source_kind_for_version(version: DocumentVersion) -> str:
        if version.original_filename.lower().endswith(".xlsx"):
            return "track"
        if version.media_type == "text/plain" or version.original_filename.lower().endswith(".txt"):
            return "text"
        return "monitoring_report"

    def _preview_for_document(
        self,
        scope: ScopeContext,
        version: DocumentVersion,
    ) -> CarryoverPreview:
        if self.documents is None:
            raise IssueValidationError("document source service is unavailable")
        stored = self.documents.read_content(scope, version.id)
        if version.original_filename.lower().endswith(".xlsx"):
            try:
                return preview_xlsx(
                    stored.content,
                    source_sha256=version.sha256,
                    filename=version.original_filename,
                )
            except Exception as exc:
                raise IssueValidationError(
                    f"XLSX carryover parsing failed: {type(exc).__name__}"
                ) from exc
        anchors = self.documents.anchors(scope, version.id)
        return preview_anchors(
            anchors=anchors,
            source_sha256=version.sha256,
        )

    def _store_preview(
        self,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        command: Any,
        command_name: str,
        source_kind: str,
        source_document_version_id: uuid.UUID | None,
        source_label: str,
        source_sha256: str,
        preview: CarryoverPreview,
        request_payload: dict[str, Any] | None = None,
    ) -> CarryoverImportDetail:
        self._authorize_write(scope, study_id, site_id)
        fingerprint = hashlib.sha256(
            (
                f"{source_sha256}|{preview.parser_name}|"
                f"{preview.parser_version}"
            ).encode("utf-8")
        ).hexdigest()
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=site_id,
                    command_name=command_name,
                    command=command,
                    request_payload=request_payload,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    import_record = session.get(
                        CarryoverImport, record.response_resource_id
                    )
                    if import_record is None:
                        raise IssueNotFound(
                            "replayed carryover import was not found"
                        )
                    candidates = tuple(
                        session.scalars(
                            select(CarryoverCandidate)
                            .where(
                                CarryoverCandidate.carryover_import_id
                                == import_record.id
                            )
                            .order_by(CarryoverCandidate.ordinal)
                        )
                    )
                    return CarryoverImportDetail(
                        import_record=import_record,
                        candidates=candidates,
                        replayed=True,
                    )
                import_record = session.scalar(
                    select(CarryoverImport).where(
                        CarryoverImport.tenant_id == scope.tenant_id,
                        CarryoverImport.study_id == study_id,
                        CarryoverImport.site_id == site_id,
                        CarryoverImport.source_fingerprint == fingerprint,
                    )
                )
                if import_record is not None:
                    self._complete_idempotency(
                        record, import_record.id, import_record.revision
                    )
                    candidates = tuple(
                        session.scalars(
                            select(CarryoverCandidate)
                            .where(
                                CarryoverCandidate.carryover_import_id
                                == import_record.id
                            )
                            .order_by(CarryoverCandidate.ordinal)
                        )
                    )
                    return CarryoverImportDetail(
                        import_record=import_record,
                        candidates=candidates,
                        replayed=True,
                    )
                import_record = CarryoverImport(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=study_id,
                    site_id=site_id,
                    source_kind=source_kind,
                    source_document_version_id=source_document_version_id,
                    source_label=source_label,
                    source_sha256=source_sha256,
                    source_fingerprint=fingerprint,
                    parser_name=preview.parser_name,
                    parser_version=preview.parser_version,
                    warnings=list(preview.warnings),
                    state="preview",
                    revision=1,
                    created_by=scope.actor_id,
                )
                session.add(import_record)
                session.flush()
                candidates = []
                for candidate in preview.candidates:
                    stored = CarryoverCandidate(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=site_id,
                        carryover_import_id=import_record.id,
                        candidate_key=candidate.candidate_key,
                        ordinal=candidate.ordinal,
                        original_issue_number=candidate.original_issue_number,
                        original_finding=candidate.original_finding,
                        location=candidate.location,
                        recommendation=candidate.recommendation,
                        recommendation_sources=list(
                            candidate.recommendation_sources
                        ),
                        known_progress=candidate.known_progress,
                        actions=[
                            {
                                "action_key": action.action_key,
                                "kind": action.kind,
                                "requirement": action.requirement,
                            }
                            for action in candidate.actions
                        ],
                        source_refs=list(candidate.source_refs),
                        unknown_fields=list(candidate.unknown_fields),
                        state="preview",
                        imported_issue_id=None,
                        user_corrections={},
                    )
                    session.add(stored)
                    candidates.append(stored)
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=site_id,
                        actor_id=scope.actor_id,
                        action=command_name,
                        resource_type="carryover_import",
                        resource_id=import_record.id,
                        revision_before=None,
                        revision_after=1,
                        before_state=None,
                        after_state={
                            "source_label": source_label,
                            "source_sha256": source_sha256,
                            "candidates": len(candidates),
                            "warnings": list(preview.warnings),
                        },
                        command_name=command_name,
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, import_record.id, import_record.revision
                )
                return CarryoverImportDetail(
                    import_record=import_record,
                    candidates=tuple(candidates),
                    replayed=False,
                )

    def preview_carryover_document(
        self,
        scope: ScopeContext,
        version_id: uuid.UUID,
        command: PreviewCarryoverDocumentCommand,
    ) -> CarryoverImportDetail:
        if self.documents is None:
            raise IssueValidationError("document source service is unavailable")
        version = self.documents.get_version(scope, version_id)
        if version.site_id != command.site_id:
            raise IssueValidationError(
                "document version is outside the selected site"
            )
        preview = self._preview_for_document(scope, version)
        return self._store_preview(
            scope=scope,
            study_id=version.study_id,
            site_id=command.site_id,
            command=command,
            command_name="issues.carryover.preview_document",
            source_kind="document",
            source_document_version_id=version.id,
            source_label=version.original_filename,
            source_sha256=version.sha256,
            preview=preview,
            request_payload={"document_version_id": str(version.id)},
        )

    def preview_carryover_text(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: PreviewCarryoverTextCommand,
    ) -> CarryoverImportDetail:
        source_sha256 = hashlib.sha256(command.text.encode("utf-8")).hexdigest()
        preview = preview_text(
            command.text,
            source_sha256=source_sha256,
            source_label=command.source_label,
        )
        return self._store_preview(
            scope=scope,
            study_id=study_id,
            site_id=command.site_id,
            command=command,
            command_name="issues.carryover.preview_text",
            source_kind="text",
            source_document_version_id=None,
            source_label=command.source_label,
            source_sha256=source_sha256,
            preview=preview,
        )

    def carryover_import_detail(
        self, scope: ScopeContext, import_id: uuid.UUID
    ) -> CarryoverImportDetail:
        with self.session_factory() as session:
            import_record = session.scalar(
                select(CarryoverImport).where(
                    CarryoverImport.id == import_id,
                    CarryoverImport.tenant_id == scope.tenant_id,
                )
            )
            if import_record is None:
                raise IssueNotFound("carryover import was not found")
            self._authorize_read(
                scope, import_record.study_id, import_record.site_id
            )
            candidates = tuple(
                session.scalars(
                    select(CarryoverCandidate)
                    .where(
                        CarryoverCandidate.carryover_import_id
                        == import_record.id
                    )
                    .order_by(CarryoverCandidate.ordinal)
                )
            )
            return CarryoverImportDetail(
                import_record=import_record,
                candidates=candidates,
                replayed=False,
            )

    def confirm_carryover(
        self,
        scope: ScopeContext,
        import_id: uuid.UUID,
        command: ConfirmCarryoverImportCommand,
    ) -> CarryoverImportDetail:
        import_record = self.carryover_import_detail(scope, import_id).import_record
        self._authorize_write(
            scope, import_record.study_id, import_record.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                import_record = session.scalar(
                    select(CarryoverImport)
                    .where(
                        CarryoverImport.id == import_id,
                        CarryoverImport.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if import_record is None:
                    raise IssueNotFound("carryover import was not found")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=import_record.study_id,
                    site_id=import_record.site_id,
                    command_name="issues.carryover.confirm",
                    command=command,
                    request_payload={"import_id": str(import_id)},
                )
                candidates = tuple(
                    session.scalars(
                        select(CarryoverCandidate)
                        .where(
                            CarryoverCandidate.carryover_import_id
                            == import_record.id
                        )
                        .order_by(CarryoverCandidate.ordinal)
                        .with_for_update()
                    )
                )
                if replayed:
                    return CarryoverImportDetail(
                        import_record=import_record,
                        candidates=candidates,
                        replayed=True,
                    )
                if import_record.revision != command.expected_revision:
                    raise RevisionConflict(import_record.revision)
                if import_record.state != "preview":
                    raise IssueConflict(
                        "only a preview carryover import can be confirmed"
                    )
                if not candidates:
                    raise IssueValidationError(
                        "carryover preview has no candidate issues to confirm"
                    )
                corrections = {
                    item.candidate_id: item for item in command.corrections
                }
                if set(corrections) - {candidate.id for candidate in candidates}:
                    raise IssueValidationError(
                        "a correction refers to another carryover import"
                    )
                now = datetime.now(UTC)
                version = None
                if import_record.source_document_version_id is not None:
                    version = session.get(
                        DocumentVersion,
                        import_record.source_document_version_id,
                    )
                for candidate in candidates:
                    correction = corrections.get(candidate.id)
                    if correction is not None and correction.skip:
                        candidate.state = "skipped"
                        candidate.user_corrections = correction.model_dump(
                            mode="json"
                        )
                        continue
                    issue_number = (
                        correction.issue_number
                        if correction and correction.issue_number
                        else candidate.original_issue_number
                    )
                    finding = (
                        correction.original_finding
                        if correction and correction.original_finding is not None
                        else candidate.original_finding
                    )
                    location_value = (
                        correction.location
                        if correction and correction.location is not None
                        else candidate.location
                    )
                    recommendation_value = (
                        correction.recommendation
                        if correction and correction.recommendation is not None
                        else candidate.recommendation
                    )
                    known_progress = (
                        correction.known_progress
                        if correction and correction.known_progress is not None
                        else candidate.known_progress
                    )
                    issue_number = (
                        issue_number.strip()
                        if issue_number and issue_number.strip()
                        else f"IMP-{candidate.candidate_key[:12].upper()}"
                    )
                    existing = session.scalar(
                        select(Issue)
                        .where(
                            Issue.tenant_id == scope.tenant_id,
                            Issue.study_id == import_record.study_id,
                            Issue.site_id == import_record.site_id,
                            Issue.issue_number == issue_number,
                        )
                        .with_for_update()
                    )
                    actions = self._candidate_actions(
                        candidate,
                        (
                            correction.model_dump(mode="json")
                            if correction
                            else {}
                        ),
                    )
                    if existing is None:
                        source_kind = (
                            self._source_kind_for_version(version)
                            if version is not None
                            else "text"
                        )
                        first_anchor = next(
                            (
                                ref.get("anchor_id")
                                for ref in candidate.source_refs
                                if ref.get("anchor_id")
                            ),
                            None,
                        )
                        try:
                            source_anchor_id = (
                                uuid.UUID(str(first_anchor))
                                if first_anchor
                                else None
                            )
                        except ValueError:
                            source_anchor_id = None
                        existing = Issue(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=import_record.study_id,
                            site_id=import_record.site_id,
                            subject_id=None,
                            issue_number=issue_number,
                            original_finding=finding,
                            location=location_value,
                            recommendation=recommendation_value,
                            recommendation_sources=list(
                                candidate.recommendation_sources
                            ),
                            reported_correction=None,
                            known_progress=known_progress,
                            source_kind=source_kind,
                            verification_status="user_reviewed",
                            source_document_version_id=(
                                import_record.source_document_version_id
                            ),
                            source_anchor_id=source_anchor_id,
                            source_original_key=candidate.candidate_key,
                            source_refs=list(candidate.source_refs),
                            revision=1,
                            created_by=scope.actor_id,
                            updated_by=scope.actor_id,
                        )
                        session.add(existing)
                        session.flush()
                        session.add(
                            IssueHistory(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=import_record.study_id,
                                site_id=import_record.site_id,
                                issue_id=existing.id,
                                action_id=None,
                                event_type="issue_created",
                                actor_id=scope.actor_id,
                                details={
                                    "issue_number": issue_number,
                                    "source": "carryover_import",
                                },
                            )
                        )
                        candidate.state = "imported"
                    else:
                        previous_known_progress = existing.known_progress
                        if known_progress is not None:
                            existing.known_progress = known_progress
                        if existing.original_finding is None and finding is not None:
                            existing.original_finding = finding
                        if existing.location is None and location_value is not None:
                            existing.location = location_value
                        if (
                            existing.recommendation is None
                            and recommendation_value is not None
                        ):
                            existing.recommendation = recommendation_value
                        existing.recommendation_sources = _dedupe_json(
                            [
                                *existing.recommendation_sources,
                                *candidate.recommendation_sources,
                            ]
                        )
                        existing.source_refs = _dedupe_json(
                            [*existing.source_refs, *candidate.source_refs]
                        )
                        existing.revision += 1
                        existing.updated_by = scope.actor_id
                        candidate.state = "reused"
                        session.add(
                            IssueHistory(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=import_record.study_id,
                                site_id=import_record.site_id,
                                issue_id=existing.id,
                                action_id=None,
                                event_type="carryover_imported",
                                actor_id=scope.actor_id,
                                details={
                                    "carryover_import_id": str(import_record.id),
                                    "candidate_id": str(candidate.id),
                                    "previous_known_progress": previous_known_progress,
                                    "source_refs": list(candidate.source_refs),
                                    "reused_existing_number": True,
                                },
                            )
                        )
                    candidate.imported_issue_id = existing.id
                    if candidate.state == "imported":
                        session.add(
                            IssueHistory(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=import_record.study_id,
                                site_id=import_record.site_id,
                                issue_id=existing.id,
                                action_id=None,
                                event_type="carryover_imported",
                                actor_id=scope.actor_id,
                                details={
                                    "carryover_import_id": str(import_record.id),
                                    "candidate_id": str(candidate.id),
                                    "source_refs": list(candidate.source_refs),
                                },
                            )
                        )
                    existing_actions = list(
                        session.scalars(
                            select(ActionItem).where(
                                ActionItem.issue_id == existing.id
                            )
                        )
                    )
                    for action_draft in actions:
                        preferred = action_draft.action_key
                        same_key = next(
                            (
                                item
                                for item in existing_actions
                                if item.action_key == preferred
                            ),
                            None,
                        )
                        if (
                            same_key is not None
                            and same_key.kind == action_draft.kind
                            and (
                                same_key.requirement == action_draft.requirement
                                or action_draft.requirement is None
                            )
                        ):
                            continue
                        action_key = self._next_action_key(
                            existing_actions, preferred
                        )
                        created_action = self._create_action(
                            session,
                            scope=scope,
                            issue=existing,
                            draft=action_draft,
                            action_key=action_key,
                        )
                        existing_actions.append(created_action)
                    candidate.user_corrections = (
                        correction.model_dump(mode="json")
                        if correction
                        else {}
                    )
                    self._audit(
                        session,
                        scope=scope,
                        issue=existing,
                        action="issues.carryover.confirm",
                        resource_type="issue",
                        resource_id=existing.id,
                        revision_before=None,
                        revision_after=existing.revision,
                        after_state={
                            "carryover_import_id": str(import_record.id),
                            "candidate_id": str(candidate.id),
                            "state": candidate.state,
                        },
                        command_name="issues.carryover.confirm",
                        correlation_id=record.id,
                    )
                import_record.state = "confirmed"
                import_record.revision += 1
                import_record.confirmed_by = scope.actor_id
                import_record.confirmed_at = now
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=import_record.study_id,
                        site_id=import_record.site_id,
                        actor_id=scope.actor_id,
                        action="issues.carryover.confirm",
                        resource_type="carryover_import",
                        resource_id=import_record.id,
                        revision_before=command.expected_revision,
                        revision_after=import_record.revision,
                        before_state=None,
                        after_state={
                            "state": import_record.state,
                            "candidates": len(candidates),
                        },
                        command_name="issues.carryover.confirm",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, import_record.id, import_record.revision
                )
                return CarryoverImportDetail(
                    import_record=import_record,
                    candidates=tuple(candidates),
                    replayed=False,
                )

    def carryover_envelope(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        *,
        monitoring_visit_id: uuid.UUID | None = None,
    ) -> OutputEnvelope:
        details = self.list_issues(
            scope, study_id, site_id, remaining_only=True
        )
        unresolved = [
            action
            for detail in details
            for action in detail.actions
            if action.status != "completed"
        ]
        claims = [
            Claim(
                claim_id=f"issue:{detail.issue.id}",
                kind="fact",
                label=detail.issue.issue_number,
                value={
                    "issue_id": str(detail.issue.id),
                    "aggregate_status": aggregate_action_status(detail.actions),
                    "original_finding": detail.issue.original_finding,
                    "known_progress": detail.issue.known_progress,
                    "actions": [
                        {
                            "id": str(action.id),
                            "kind": action.kind,
                            "status": action.status,
                        }
                        for action in detail.actions
                    ],
                },
                source_refs=[
                    SourceRef(
                        source_type="record",
                        source_id=str(detail.issue.id),
                        locator=detail.issue.source_original_key,
                    )
                ],
                verification_status="cra_confirmed",
            )
            for detail in details
        ]
        unknowns = [
            UnknownItem(
                code=f"{detail.issue.issue_number}.original_finding",
                reason="old source did not state the original finding",
                affected_scope=str(detail.issue.id),
            )
            for detail in details
            if not detail.issue.original_finding
        ]
        not_checked = [
            NotCheckedItem(
                code=f"{detail.issue.issue_number}.actions",
                scope=str(detail.issue.id),
                reason="issue has no defined action item",
            )
            for detail in details
            if not detail.actions
        ]
        return OutputEnvelope(
            output_id=uuid.uuid4(),
            purpose="carryover_reminder",
            scope=OutputScope(
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                subject_id=None,
            ),
            input_revisions=[
                InputRevision(
                    resource_type="issue",
                    resource_id=str(detail.issue.id),
                    revision=detail.issue.revision,
                )
                for detail in details
            ],
            claims=claims,
            evidence_refs=[
                SourceRef(
                    source_type="record",
                    source_id=str(history.id),
                    locator=history.event_type,
                    quote=(
                        f"monitoring_visit_id={monitoring_visit_id}"
                        if monitoring_visit_id
                        else None
                    ),
                )
                for detail in details
                for history in detail.history[-3:]
            ],
            unknowns=unknowns,
            not_checked=not_checked,
            capabilities=[
                OutputCapability(
                    capability_id="M05.carryover",
                    level="limited",
                    validated=False,
                    limitations=[
                        "carryover display is limited to recorded Issues",
                        "a partial import is not the complete monitoring history",
                    ],
                )
            ],
            status=(
                "limited" if unknowns or not_checked else "ready_to_review"
            ),
            generated_at=datetime.now(UTC),
            actor_id=scope.actor_id,
        )
