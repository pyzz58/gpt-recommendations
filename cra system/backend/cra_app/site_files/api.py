"""HTTP contracts for ISF/TMF references, status updates and stage lists."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.issues.service import aggregate_action_status
from cra_app.site_files.service import (
    AddDirectoryItemCommand,
    AddStageChecklistItemCommand,
    CreateDirectoryReferenceCommand,
    CreateStageChecklistCommand,
    DirectoryDetail,
    SiteFileService,
    StageChecklistDetail,
    VerifyFileCommand,
    VerifyStageItemCommand,
)

router = APIRouter(prefix="/api/v1", tags=["site-files"])


class DirectoryHistoryView(BaseModel):
    id: uuid.UUID
    site_file_item_id: uuid.UUID | None
    event_type: str
    actor_id: str
    details: dict[str, Any]
    occurred_at: datetime


class SiteFileItemView(BaseModel):
    id: uuid.UUID
    item_key: str
    title: str
    requirement: str | None
    applicability_status: str
    acquisition_status: str
    verification_status: str
    verification_note: str | None
    source_anchor_id: uuid.UUID | None
    source_refs: list[dict[str, Any]]
    linked_issue_id: uuid.UUID | None
    linked_action_id: uuid.UUID | None
    verified_by: str | None
    verified_at: datetime | None
    revision: int


class SiteDirectoryReferenceView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    source_document_version_id: uuid.UUID
    original_filename: str
    content_url: str
    directory_kind: str
    label: str
    mode: str
    annotations: list[dict[str, Any]]
    revision: int
    created_by: str
    created_at: datetime
    items: list[SiteFileItemView]
    history: list[DirectoryHistoryView]
    missing_item_keys: list[str]
    pending_verification_item_keys: list[str]
    coverage_note: str
    previous_reference_id: uuid.UUID | None
    change_status: str
    new_item_keys: list[str]
    removed_item_keys: list[str]
    changed_item_keys: list[str]


class StageChecklistHistoryView(BaseModel):
    id: uuid.UUID
    stage_checklist_item_id: uuid.UUID | None
    event_type: str
    actor_id: str
    details: dict[str, Any]
    occurred_at: datetime


class StageChecklistItemView(BaseModel):
    id: uuid.UUID
    item_key: str
    title: str
    requirement: str
    source_document_version_id: uuid.UUID
    source_anchor_id: uuid.UUID | None
    source_refs: list[dict[str, Any]]
    status: str
    completion_note: str | None
    completed_by: str | None
    completed_at: datetime | None
    revision: int


class StageChecklistView(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    stage: str
    title: str
    source_refs: list[dict[str, Any]]
    revision: int
    created_by: str
    created_at: datetime
    items: list[StageChecklistItemView]
    history: list[StageChecklistHistoryView]
    all_items_confirmed: bool
    center_close_approved: bool = False
    limitation: str


class HandoverActionView(BaseModel):
    id: uuid.UUID
    action_key: str
    kind: str
    status: str
    requirement: str | None


class HandoverIssueView(BaseModel):
    id: uuid.UUID
    issue_number: str
    original_finding: str | None
    location: str | None
    known_progress: str | None
    aggregate_status: str
    source_refs: list[dict[str, Any]]
    actions: list[HandoverActionView]
    next_steps: list[str]


class HandoverChecklistItemView(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    stage_checklist_id: uuid.UUID


class HandoverSummaryView(BaseModel):
    visit_id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    generated_at: datetime
    has_carryover: bool
    summary: str
    issues: list[HandoverIssueView]
    incomplete_checklist_items: list[HandoverChecklistItemView]
    center_close_approved: bool = False
    limitation: str


def _service(request: Request) -> SiteFileService:
    return request.app.state.site_file_service


def _directory_view(
    request: Request,
    identity: AuthenticatedIdentity,
    detail: DirectoryDetail,
    previous: DirectoryDetail | None = None,
) -> SiteDirectoryReferenceView:
    scope = scope_from_identity(identity)
    version = request.app.state.document_service.get_version(
        scope, detail.reference.source_document_version_id
    )
    missing = [
        item.item_key
        for item in detail.items
        if item.applicability_status == "required"
        and item.acquisition_status != "provided"
    ]
    pending = [
        item.item_key
        for item in detail.items
        if item.applicability_status == "required"
        and item.verification_status != "qualified"
    ]
    new_keys: list[str] = []
    removed_keys: list[str] = []
    changed_keys: list[str] = []
    if previous is None:
        change_status = "no_previous_reference"
    elif not previous.items or not detail.items:
        change_status = "comparison_unknown_without_structured_versions"
    else:
        previous_items = {item.item_key: item for item in previous.items}
        current_items = {item.item_key: item for item in detail.items}
        new_keys = sorted(set(current_items) - set(previous_items))
        removed_keys = sorted(set(previous_items) - set(current_items))
        for key in sorted(set(current_items) & set(previous_items)):
            before, after = previous_items[key], current_items[key]
            if (
                before.applicability_status,
                before.acquisition_status,
                before.verification_status,
            ) != (
                after.applicability_status,
                after.acquisition_status,
                after.verification_status,
            ):
                changed_keys.append(key)
        change_status = "compared"
    return SiteDirectoryReferenceView(
        id=detail.reference.id,
        study_id=detail.reference.study_id,
        site_id=detail.reference.site_id,
        source_document_version_id=detail.reference.source_document_version_id,
        original_filename=version.original_filename,
        content_url=(
            f"/api/v1/document-versions/{version.id}/content"
        ),
        directory_kind=detail.reference.directory_kind,
        label=detail.reference.label,
        mode=detail.reference.mode,
        annotations=detail.reference.annotations,
        revision=detail.reference.revision,
        created_by=detail.reference.created_by,
        created_at=detail.reference.created_at,
        items=[
            SiteFileItemView(
                id=item.id,
                item_key=item.item_key,
                title=item.title,
                requirement=item.requirement,
                applicability_status=item.applicability_status,
                acquisition_status=item.acquisition_status,
                verification_status=item.verification_status,
                verification_note=item.verification_note,
                source_anchor_id=item.source_anchor_id,
                source_refs=item.source_refs,
                linked_issue_id=item.linked_issue_id,
                linked_action_id=item.linked_action_id,
                verified_by=item.verified_by,
                verified_at=item.verified_at,
                revision=item.revision,
            )
            for item in detail.items
        ],
        history=[
            DirectoryHistoryView(
                id=event.id,
                site_file_item_id=event.site_file_item_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                details=event.details,
                occurred_at=event.occurred_at,
            )
            for event in detail.history
        ],
        missing_item_keys=missing,
        pending_verification_item_keys=pending,
        coverage_note=(
            "reference_only：原目录可直接对照，但尚未结构化，不能宣称全部核查合格。"
            if detail.reference.mode == "reference_only"
            else "structured_partial：仅对已建立条目显示状态；未列范围仍为unknown。"
        ),
        previous_reference_id=(
            previous.reference.id if previous is not None else None
        ),
        change_status=change_status,
        new_item_keys=new_keys,
        removed_item_keys=removed_keys,
        changed_item_keys=changed_keys,
    )


def _checklist_view(detail: StageChecklistDetail) -> StageChecklistView:
    required = [
        item for item in detail.items if item.status != "not_applicable"
    ]
    return StageChecklistView(
        id=detail.checklist.id,
        study_id=detail.checklist.study_id,
        site_id=detail.checklist.site_id,
        stage=detail.checklist.stage,
        title=detail.checklist.title,
        source_refs=detail.checklist.source_refs,
        revision=detail.checklist.revision,
        created_by=detail.checklist.created_by,
        created_at=detail.checklist.created_at,
        items=[
            StageChecklistItemView(
                id=item.id,
                item_key=item.item_key,
                title=item.title,
                requirement=item.requirement,
                source_document_version_id=item.source_document_version_id,
                source_anchor_id=item.source_anchor_id,
                source_refs=item.source_refs,
                status=item.status,
                completion_note=item.completion_note,
                completed_by=item.completed_by,
                completed_at=item.completed_at,
                revision=item.revision,
            )
            for item in detail.items
        ],
        history=[
            StageChecklistHistoryView(
                id=event.id,
                stage_checklist_item_id=event.stage_checklist_item_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                details=event.details,
                occurred_at=event.occurred_at,
            )
            for event in detail.history
        ],
        all_items_confirmed=bool(required)
        and all(item.status == "confirmed" for item in required),
        center_close_approved=False,
        limitation="清单完成不等于项目组批准中心关闭，也不会自动锁定数据库。",
    )


@router.post(
    "/document-directories",
    response_model=SiteDirectoryReferenceView,
    dependencies=[Depends(require_csrf)],
)
def create_directory_reference(
    command: CreateDirectoryReferenceCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SiteDirectoryReferenceView:
    return _directory_view(
        request,
        identity,
        _service(request).create_directory_reference(
            scope_from_identity(identity), command
        ),
    )


@router.get(
    "/directory-references/{reference_id}",
    response_model=SiteDirectoryReferenceView,
)
def directory_reference(
    reference_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SiteDirectoryReferenceView:
    return _directory_view(
        request,
        identity,
        _service(request).directory_detail(
            scope_from_identity(identity), reference_id
        ),
    )


@router.get(
    "/site-file-status",
    response_model=list[SiteDirectoryReferenceView],
)
def site_file_status(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[SiteDirectoryReferenceView]:
    details = _service(request).site_file_status(
        scope_from_identity(identity), study_id, site_id
    )
    previous_by_kind: dict[str, DirectoryDetail] = {}
    views = []
    for detail in details:
        previous = previous_by_kind.get(detail.reference.directory_kind)
        views.append(_directory_view(request, identity, detail, previous))
        previous_by_kind[detail.reference.directory_kind] = detail
    return views


@router.post(
    "/document-directories/{reference_id}/items",
    response_model=SiteDirectoryReferenceView,
    dependencies=[Depends(require_csrf)],
)
def add_directory_item(
    reference_id: uuid.UUID,
    command: AddDirectoryItemCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SiteDirectoryReferenceView:
    return _directory_view(
        request,
        identity,
        _service(request).add_directory_item(
            scope_from_identity(identity), reference_id, command
        ),
    )


@router.post(
    "/file-verifications",
    response_model=SiteDirectoryReferenceView,
    dependencies=[Depends(require_csrf)],
)
def verify_file(
    command: VerifyFileCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SiteDirectoryReferenceView:
    return _directory_view(
        request,
        identity,
        _service(request).verify_file(
            scope_from_identity(identity), command
        ),
    )


@router.post(
    "/studies/{study_id}/stage-checklists",
    response_model=StageChecklistView,
    dependencies=[Depends(require_csrf)],
)
def create_stage_checklist(
    study_id: uuid.UUID,
    command: CreateStageChecklistCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> StageChecklistView:
    return _checklist_view(
        _service(request).create_stage_checklist(
            scope_from_identity(identity), study_id, command
        )
    )


@router.get(
    "/stage-checklists",
    response_model=list[StageChecklistView],
)
def stage_checklists(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[StageChecklistView]:
    return [
        _checklist_view(detail)
        for detail in _service(request).stage_checklists(
            scope_from_identity(identity), study_id, site_id
        )
    ]


@router.post(
    "/stage-checklists/{checklist_id}/items",
    response_model=StageChecklistView,
    dependencies=[Depends(require_csrf)],
)
def add_stage_checklist_item(
    checklist_id: uuid.UUID,
    command: AddStageChecklistItemCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> StageChecklistView:
    return _checklist_view(
        _service(request).add_stage_item(
            scope_from_identity(identity), checklist_id, command
        )
    )


@router.post(
    "/stage-checklist-items/{item_id}/verification",
    response_model=StageChecklistView,
    dependencies=[Depends(require_csrf)],
)
def verify_stage_checklist_item(
    item_id: uuid.UUID,
    command: VerifyStageItemCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> StageChecklistView:
    return _checklist_view(
        _service(request).verify_stage_item(
            scope_from_identity(identity), item_id, command
        )
    )


@router.get(
    "/monitoring-visits/{visit_id}/handover-summary",
    response_model=HandoverSummaryView,
)
def handover_summary(
    visit_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> HandoverSummaryView:
    summary = _service(request).handover_summary(
        scope_from_identity(identity), visit_id
    )
    return HandoverSummaryView(
        visit_id=summary.visit_id,
        study_id=summary.study_id,
        site_id=summary.site_id,
        generated_at=summary.generated_at,
        has_carryover=summary.has_carryover,
        summary=summary.summary,
        issues=[
            HandoverIssueView(
                id=item.issue.issue.id,
                issue_number=item.issue.issue.issue_number,
                original_finding=item.issue.issue.original_finding,
                location=item.issue.issue.location,
                known_progress=item.issue.issue.known_progress,
                aggregate_status=aggregate_action_status(
                    item.issue.actions
                ),
                source_refs=item.issue.issue.source_refs,
                actions=[
                    HandoverActionView(
                        id=action.id,
                        action_key=action.action_key,
                        kind=action.kind,
                        status=action.status,
                        requirement=action.requirement,
                    )
                    for action in item.issue.actions
                ],
                next_steps=list(item.next_steps),
            )
            for item in summary.issues
        ],
        incomplete_checklist_items=[
            HandoverChecklistItemView(
                id=item.id,
                title=item.title,
                status=item.status,
                stage_checklist_id=item.stage_checklist_id,
            )
            for item in summary.incomplete_checklist_items
        ],
        center_close_approved=False,
        limitation="交接摘要来自原Issue和清单现状，不形成额外审批或中心关闭许可。",
    )
