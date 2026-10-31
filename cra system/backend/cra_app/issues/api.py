"""HTTP contracts for issues, actions, Queries and carryover imports."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.issues.contracts import (
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
from cra_app.issues.deadlines import assess_deadline
from cra_app.issues.service import (
    CarryoverImportDetail,
    IssueDetail,
    IssueService,
    aggregate_action_status,
)

router = APIRouter(prefix="/api/v1", tags=["issues"])


class ActionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    action_key: str
    kind: str
    requirement: str | None
    status: str
    completion_basis: str | None
    completed_by: str | None
    completed_at: datetime | None
    completion_note: str | None
    due_on: date | None
    deadline_source: str | None
    deadline_source_refs: list[dict[str, Any]]
    deadline_status: str
    overdue_days: int | None
    days_remaining: int | None
    revision: int


class IssueHistoryView(BaseModel):
    id: uuid.UUID
    action_id: uuid.UUID | None
    event_type: str
    actor_id: str
    details: dict[str, Any]
    occurred_at: datetime


class QueryLinkView(BaseModel):
    id: uuid.UUID
    query_state: str
    external_system: str | None
    external_query_number: str | None
    opened_on: date | None
    due_on: date | None
    deadline_source: str | None
    deadline_source_refs: list[dict[str, Any]]
    deadline_status: str
    overdue_days: int | None
    days_remaining: int | None
    replied_on: date | None
    reply_summary: str | None
    revision: int


class IssueView(BaseModel):
    id: uuid.UUID
    issue_number: str
    study_id: uuid.UUID
    site_id: uuid.UUID
    subject_id: uuid.UUID | None
    original_finding: str | None
    location: str | None
    recommendation: str | None
    recommendation_sources: list[Any]
    reported_correction: str | None
    known_progress: str | None
    source_kind: str
    verification_status: str
    source_document_version_id: uuid.UUID | None
    source_anchor_id: uuid.UUID | None
    source_original_key: str | None
    source_refs: list[dict[str, Any]]
    aggregate_status: str
    revision: int
    actions: list[ActionView]
    history: list[IssueHistoryView]
    query_links: list[QueryLinkView]


class ActionConfirmationResponse(BaseModel):
    actions: list[ActionView]
    replayed: bool


class CarryoverCandidateView(BaseModel):
    id: uuid.UUID
    candidate_key: str
    ordinal: int
    original_issue_number: str | None
    original_finding: str | None
    location: str | None
    recommendation: str | None
    recommendation_sources: list[Any]
    known_progress: str | None
    actions: list[dict[str, Any]]
    source_refs: list[dict[str, Any]]
    unknown_fields: list[str]
    state: str
    imported_issue_id: uuid.UUID | None


class CarryoverImportView(BaseModel):
    id: uuid.UUID
    source_kind: str
    source_document_version_id: uuid.UUID | None
    source_label: str
    source_sha256: str
    parser_name: str
    parser_version: str
    warnings: list[str]
    state: str
    revision: int
    confirmed_by: str | None
    confirmed_at: datetime | None


class CarryoverResponse(BaseModel):
    import_record: CarryoverImportView
    candidates: list[CarryoverCandidateView]
    replayed: bool


def _service(request: Request) -> IssueService:
    return request.app.state.issue_service


def action_view(
    action,
    *,
    as_of: date | None = None,
) -> ActionView:
    deadline = assess_deadline(
        due_on=action.due_on,
        deadline_source=action.deadline_source,
        as_of=as_of or date.today(),
        resolved_on=(
            action.completed_at.date()
            if action.completed_at is not None
            else None
        ),
    )
    return ActionView(
        id=action.id,
        action_key=action.action_key,
        kind=action.kind,
        requirement=action.requirement,
        status=action.status,
        completion_basis=action.completion_basis,
        completed_by=action.completed_by,
        completed_at=action.completed_at,
        completion_note=action.completion_note,
        due_on=action.due_on,
        deadline_source=action.deadline_source,
        deadline_source_refs=action.deadline_source_refs,
        deadline_status=deadline.status,
        overdue_days=deadline.overdue_days,
        days_remaining=deadline.days_remaining,
        revision=action.revision,
    )


def issue_view(detail: IssueDetail, *, as_of: date | None = None) -> IssueView:
    issue = detail.issue
    return IssueView(
        id=issue.id,
        issue_number=issue.issue_number,
        study_id=issue.study_id,
        site_id=issue.site_id,
        subject_id=issue.subject_id,
        original_finding=issue.original_finding,
        location=issue.location,
        recommendation=issue.recommendation,
        recommendation_sources=issue.recommendation_sources,
        reported_correction=issue.reported_correction,
        known_progress=issue.known_progress,
        source_kind=issue.source_kind,
        verification_status=issue.verification_status,
        source_document_version_id=issue.source_document_version_id,
        source_anchor_id=issue.source_anchor_id,
        source_original_key=issue.source_original_key,
        source_refs=issue.source_refs,
        aggregate_status=aggregate_action_status(detail.actions),
        revision=issue.revision,
        actions=[action_view(action, as_of=as_of) for action in detail.actions],
        history=[
            IssueHistoryView(
                id=history.id,
                action_id=history.action_id,
                event_type=history.event_type,
                actor_id=history.actor_id,
                details=history.details,
                occurred_at=history.occurred_at,
            )
            for history in detail.history
        ],
        query_links=[
            QueryLinkView(
                id=query.id,
                query_state=query.query_state,
                external_system=query.external_system,
                external_query_number=query.external_query_number,
                opened_on=query.opened_on,
                due_on=query.due_on,
                deadline_source=query.deadline_source,
                deadline_source_refs=query.deadline_source_refs,
                deadline_status=assess_deadline(
                    due_on=query.due_on,
                    deadline_source=query.deadline_source,
                    as_of=as_of or date.today(),
                    resolved_on=query.replied_on,
                ).status,
                overdue_days=assess_deadline(
                    due_on=query.due_on,
                    deadline_source=query.deadline_source,
                    as_of=as_of or date.today(),
                    resolved_on=query.replied_on,
                ).overdue_days,
                days_remaining=assess_deadline(
                    due_on=query.due_on,
                    deadline_source=query.deadline_source,
                    as_of=as_of or date.today(),
                    resolved_on=query.replied_on,
                ).days_remaining,
                replied_on=query.replied_on,
                reply_summary=query.reply_summary,
                revision=query.revision,
            )
            for query in detail.query_links
        ],
    )


def _carryover_view(detail: CarryoverImportDetail) -> CarryoverResponse:
    import_record = detail.import_record
    return CarryoverResponse(
        import_record=CarryoverImportView(
            id=import_record.id,
            source_kind=import_record.source_kind,
            source_document_version_id=import_record.source_document_version_id,
            source_label=import_record.source_label,
            source_sha256=import_record.source_sha256,
            parser_name=import_record.parser_name,
            parser_version=import_record.parser_version,
            warnings=import_record.warnings,
            state=import_record.state,
            revision=import_record.revision,
            confirmed_by=import_record.confirmed_by,
            confirmed_at=import_record.confirmed_at,
        ),
        candidates=[
            CarryoverCandidateView(
                id=candidate.id,
                candidate_key=candidate.candidate_key,
                ordinal=candidate.ordinal,
                original_issue_number=candidate.original_issue_number,
                original_finding=candidate.original_finding,
                location=candidate.location,
                recommendation=candidate.recommendation,
                recommendation_sources=candidate.recommendation_sources,
                known_progress=candidate.known_progress,
                actions=candidate.actions,
                source_refs=candidate.source_refs,
                unknown_fields=candidate.unknown_fields,
                state=candidate.state,
                imported_issue_id=candidate.imported_issue_id,
            )
            for candidate in detail.candidates
        ],
        replayed=detail.replayed,
    )


@router.get(
    "/studies/{study_id}/issues",
    response_model=list[IssueView],
)
def list_issues(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    remaining_only: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[IssueView]:
    return [
        issue_view(item)
        for item in _service(request).list_issues(
            scope_from_identity(identity),
            study_id,
            site_id,
            remaining_only=remaining_only,
        )
    ]


@router.get("/issues/{issue_id}", response_model=IssueView)
def get_issue(
    issue_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> IssueView:
    return issue_view(
        _service(request).issue_detail(
            scope_from_identity(identity), issue_id
        )
    )


@router.post(
    "/studies/{study_id}/issues",
    response_model=IssueView,
    dependencies=[Depends(require_csrf)],
)
def create_issue(
    study_id: uuid.UUID,
    command: CreateIssueCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> IssueView:
    return issue_view(
        _service(request).create_issue(
            scope_from_identity(identity), study_id, command
        )
    )


@router.post(
    "/issues/{issue_id}/actions",
    response_model=IssueView,
    dependencies=[Depends(require_csrf)],
)
def add_action(
    issue_id: uuid.UUID,
    command: AddActionCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> IssueView:
    return issue_view(
        _service(request).add_action(
            scope_from_identity(identity), issue_id, command
        )
    )


@router.post(
    "/actions/confirm-corrected",
    response_model=ActionConfirmationResponse,
    dependencies=[Depends(require_csrf)],
)
def confirm_corrected(
    command: ConfirmCorrectedCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ActionConfirmationResponse:
    outcome = _service(request).confirm_corrected(
        scope_from_identity(identity), command
    )
    return ActionConfirmationResponse(
        actions=[action_view(action) for action in outcome.actions],
        replayed=outcome.replayed,
    )


@router.post(
    "/actions/{action_id}/confirm-reported",
    response_model=ActionView,
    dependencies=[Depends(require_csrf)],
)
def confirm_reported(
    action_id: uuid.UUID,
    command: ConfirmReportedCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ActionView:
    return action_view(
        _service(request).confirm_reported(
            scope_from_identity(identity), action_id, command
        )
    )


@router.post(
    "/actions/{action_id}/reopen",
    response_model=ActionView,
    dependencies=[Depends(require_csrf)],
)
def reopen_action(
    action_id: uuid.UUID,
    command: ReopenActionCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ActionView:
    return action_view(
        _service(request).reopen_action(
            scope_from_identity(identity), action_id, command
        )
    )


@router.post(
    "/issues/{issue_id}/replies",
    response_model=IssueView,
    dependencies=[Depends(require_csrf)],
)
def record_reply(
    issue_id: uuid.UUID,
    command: RecordReplyCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> IssueView:
    return issue_view(
        _service(request).record_reply(
            scope_from_identity(identity), issue_id, command
        )
    )


@router.post(
    "/issues/{issue_id}/query-links",
    response_model=QueryLinkView,
    dependencies=[Depends(require_csrf)],
)
def create_query_link(
    issue_id: uuid.UUID,
    command: CreateQueryLinkCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> QueryLinkView:
    query = _service(request).create_query_link(
        scope_from_identity(identity), issue_id, command
    )
    deadline = assess_deadline(
        due_on=query.due_on,
        deadline_source=query.deadline_source,
        as_of=date.today(),
        resolved_on=query.replied_on,
    )
    return QueryLinkView(
        id=query.id,
        query_state=query.query_state,
        external_system=query.external_system,
        external_query_number=query.external_query_number,
        opened_on=query.opened_on,
        due_on=query.due_on,
        deadline_source=query.deadline_source,
        deadline_source_refs=query.deadline_source_refs,
        deadline_status=deadline.status,
        overdue_days=deadline.overdue_days,
        days_remaining=deadline.days_remaining,
        replied_on=query.replied_on,
        reply_summary=query.reply_summary,
        revision=query.revision,
    )


@router.post(
    "/document-versions/{version_id}/carryover-imports/preview",
    response_model=CarryoverResponse,
    dependencies=[Depends(require_csrf)],
)
def preview_carryover_document(
    version_id: uuid.UUID,
    command: PreviewCarryoverDocumentCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CarryoverResponse:
    return _carryover_view(
        _service(request).preview_carryover_document(
            scope_from_identity(identity), version_id, command
        )
    )


@router.post(
    "/studies/{study_id}/carryover-imports/preview-text",
    response_model=CarryoverResponse,
    dependencies=[Depends(require_csrf)],
)
def preview_carryover_text(
    study_id: uuid.UUID,
    command: PreviewCarryoverTextCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CarryoverResponse:
    return _carryover_view(
        _service(request).preview_carryover_text(
            scope_from_identity(identity), study_id, command
        )
    )


@router.get(
    "/carryover-imports/{import_id}",
    response_model=CarryoverResponse,
)
def get_carryover_import(
    import_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CarryoverResponse:
    return _carryover_view(
        _service(request).carryover_import_detail(
            scope_from_identity(identity), import_id
        )
    )


@router.post(
    "/carryover-imports/{import_id}/confirm",
    response_model=CarryoverResponse,
    dependencies=[Depends(require_csrf)],
)
def confirm_carryover_import(
    import_id: uuid.UUID,
    command: ConfirmCarryoverImportCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CarryoverResponse:
    return _carryover_view(
        _service(request).confirm_carryover(
            scope_from_identity(identity), import_id, command
        )
    )
