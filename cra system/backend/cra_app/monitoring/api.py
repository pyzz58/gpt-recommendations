"""Monitoring-visit and carryover workbench HTTP contracts."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.issues.api import IssueView, issue_view
from cra_app.issues.contracts import (
    CreateMonitoringVisitCommand,
    SelectPrevisitIssuesCommand,
    UpdateMonitoringScopeCommand,
)
from cra_app.monitoring.service import MonitoringService, WorkbenchData
from cra_app.shared.output_contract import OutputEnvelope

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


class MonitoringVisitView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    stage: str
    title: str
    scope_note: str | None
    status: str
    revision: int
    created_by: str
    created_at: datetime


class DirectoryReferenceView(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID | None
    title: str
    original_filename: str | None
    document_type: str
    purpose: str
    parse_status: str | None
    mode: str


class WorkbenchView(BaseModel):
    visit: MonitoringVisitView
    stages: list[str]
    carryover: list[IssueView]
    selected_issue_ids: list[uuid.UUID]
    directory_references: list[DirectoryReferenceView]
    envelope: OutputEnvelope


def _service(request: Request) -> MonitoringService:
    return request.app.state.monitoring_service


def _workbench_view(data: WorkbenchData) -> WorkbenchView:
    visit = data.visit
    return WorkbenchView(
        visit=MonitoringVisitView(
            id=visit.id,
            study_id=visit.study_id,
            site_id=visit.site_id,
            stage=visit.stage,
            title=visit.title,
            scope_note=visit.scope_note,
            status=visit.status,
            revision=visit.revision,
            created_by=visit.created_by,
            created_at=visit.created_at,
        ),
        stages=[
            "previsit",
            "carryover_review",
            "subject_review",
            "closeout",
            "handover",
        ],
        carryover=[issue_view(item) for item in data.carryover],
        selected_issue_ids=list(data.selected_issue_ids),
        directory_references=[
            DirectoryReferenceView(
                document_id=item.document_id,
                document_version_id=item.document_version_id,
                title=item.title,
                original_filename=item.original_filename,
                document_type=item.document_type,
                purpose=item.purpose,
                parse_status=item.parse_status,
                mode=item.mode,
            )
            for item in data.directory_references
        ],
        envelope=data.envelope,
    )


@router.post(
    "/studies/{study_id}/monitoring-visits",
    response_model=WorkbenchView,
    dependencies=[Depends(require_csrf)],
)
def create_monitoring_visit(
    study_id: uuid.UUID,
    command: CreateMonitoringVisitCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> WorkbenchView:
    return _workbench_view(
        _service(request).create_visit(
            scope_from_identity(identity), study_id, command
        )
    )


@router.get(
    "/monitoring-visits/{visit_id}/workbench",
    response_model=WorkbenchView,
)
def workbench(
    visit_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> WorkbenchView:
    return _workbench_view(
        _service(request).workbench(
            scope_from_identity(identity), visit_id
        )
    )


@router.post(
    "/monitoring-visits/{visit_id}/scope",
    response_model=WorkbenchView,
    dependencies=[Depends(require_csrf)],
)
def update_monitoring_scope(
    visit_id: uuid.UUID,
    command: UpdateMonitoringScopeCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> WorkbenchView:
    return _workbench_view(
        _service(request).update_scope(
            scope_from_identity(identity), visit_id, command
        )
    )


@router.post(
    "/monitoring-visits/{visit_id}/previsit-selection",
    response_model=WorkbenchView,
    dependencies=[Depends(require_csrf)],
)
def select_previsit_issues(
    visit_id: uuid.UUID,
    command: SelectPrevisitIssuesCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> WorkbenchView:
    return _workbench_view(
        _service(request).select_previsit_issues(
            scope_from_identity(identity), visit_id, command
        )
    )
