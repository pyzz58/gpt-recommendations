"""HTTP endpoints for reusable template-driven monitoring review."""
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
from cra_app.monitoring.review_contracts import (
    BindReviewTemplateCommand,
    CreateReviewTemplateCommand,
    UpdateMonitoringReviewItemCommand,
)
from cra_app.monitoring.review_models import (
    MonitoringReviewBinding,
    MonitoringReviewHistory,
    MonitoringReviewItem,
    ReviewTemplateItem,
    ReviewTemplateVersion,
)
from cra_app.monitoring.review_service import (
    ReviewTemplateDetail,
    TemplateReviewService,
    VisitReviewBoard,
    VisitReviewItemDetail,
)

router = APIRouter(prefix="/api/v1", tags=["template-review"])


class ExtractedQuestionView(BaseModel):
    item_key: str
    section_key: str
    section_order: int
    section_title: str
    question_order: int
    question_text: str
    source_locator: str
    source_quote: str
    report_locator: str
    applicability: dict[str, Any]


class ReviewTemplatePreviewView(BaseModel):
    source_document_version_id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    title: str
    sections: list[dict[str, Any]]
    questions: list[ExtractedQuestionView]
    warnings: list[dict[str, Any]]


class ReviewTemplateItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_key: str
    section_key: str
    section_order: int
    section_title: str
    question_order: int
    question_text: str
    source_locator: str
    source_quote: str
    report_locator: str
    applicability: dict[str, Any]


class ReviewTemplateView(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    source_document_version_id: uuid.UUID
    title: str
    structure: dict[str, Any]
    warnings: list[dict[str, Any]]
    revision: int
    created_by: str
    created_at: datetime
    items: list[ReviewTemplateItemView]


class ReviewHistoryView(BaseModel):
    id: uuid.UUID
    ordinal: int
    actor_id: str
    details: dict[str, Any]
    recorded_at: datetime


class MonitoringReviewItemView(BaseModel):
    id: uuid.UUID
    monitoring_visit_id: uuid.UUID
    template_item_id: uuid.UUID
    item_key: str
    section_key: str
    section_order: int
    section_title: str
    question_order: int
    question_text: str
    source_locator: str
    source_quote: str
    report_locator: str
    applicability: dict[str, Any]
    subject_id: uuid.UUID | None
    linked_issue_id: uuid.UUID | None
    linked_comparison_id: uuid.UUID | None
    rule_version_ids: list[str]
    status: str
    note: str | None
    report_section: str
    revision: int
    updated_by: str
    updated_at: datetime
    history: list[ReviewHistoryView]


class ReviewBindingView(BaseModel):
    id: uuid.UUID
    monitoring_visit_id: uuid.UUID
    review_template_version_id: uuid.UUID
    revision: int


class VisitReviewBoardView(BaseModel):
    binding: ReviewBindingView | None
    template: ReviewTemplateView | None
    items: list[MonitoringReviewItemView]


def _service(request: Request) -> TemplateReviewService:
    return request.app.state.template_review_service


def _template_view(detail: ReviewTemplateDetail) -> ReviewTemplateView:
    template = detail.template
    return ReviewTemplateView(
        id=template.id,
        study_id=template.study_id,
        site_id=template.site_id,
        source_document_version_id=template.source_document_version_id,
        title=template.title,
        structure=template.structure_json,
        warnings=template.warnings,
        revision=template.revision,
        created_by=template.created_by,
        created_at=template.created_at,
        items=[
            ReviewTemplateItemView.model_validate(item)
            for item in detail.items
        ],
    )


def _history_view(item: MonitoringReviewHistory) -> ReviewHistoryView:
    return ReviewHistoryView(
        id=item.id,
        ordinal=item.ordinal,
        actor_id=item.actor_id,
        details=item.details,
        recorded_at=item.recorded_at,
    )


def _visit_item_view(detail: VisitReviewItemDetail) -> MonitoringReviewItemView:
    item = detail.item
    template_item = detail.template_item
    return MonitoringReviewItemView(
        id=item.id,
        monitoring_visit_id=item.monitoring_visit_id,
        template_item_id=item.review_template_item_id,
        item_key=template_item.item_key,
        section_key=template_item.section_key,
        section_order=template_item.section_order,
        section_title=template_item.section_title,
        question_order=template_item.question_order,
        question_text=template_item.question_text,
        source_locator=template_item.source_locator,
        source_quote=template_item.source_quote,
        report_locator=template_item.report_locator,
        applicability=template_item.applicability,
        subject_id=item.subject_id,
        linked_issue_id=item.linked_issue_id,
        linked_comparison_id=item.linked_comparison_id,
        rule_version_ids=item.rule_version_ids,
        status=item.status,
        note=item.note,
        report_section=item.report_section,
        revision=item.revision,
        updated_by=item.updated_by,
        updated_at=item.updated_at,
        history=[_history_view(history) for history in detail.history],
    )


def _binding_view(item: MonitoringReviewBinding) -> ReviewBindingView:
    return ReviewBindingView(
        id=item.id,
        monitoring_visit_id=item.monitoring_visit_id,
        review_template_version_id=item.review_template_version_id,
        revision=item.revision,
    )


def _board_view(board: VisitReviewBoard) -> VisitReviewBoardView:
    return VisitReviewBoardView(
        binding=_binding_view(board.binding) if board.binding else None,
        template=(
            ReviewTemplateView(
                id=board.template.id,
                study_id=board.template.study_id,
                site_id=board.template.site_id,
                source_document_version_id=(
                    board.template.source_document_version_id
                ),
                title=board.template.title,
                structure=board.template.structure_json,
                warnings=board.template.warnings,
                revision=board.template.revision,
                created_by=board.template.created_by,
                created_at=board.template.created_at,
                items=[],
            )
            if board.template
            else None
        ),
        items=[_visit_item_view(item) for item in board.items],
    )


@router.post(
    "/document-versions/{version_id}/review-template-preview",
    response_model=ReviewTemplatePreviewView,
    dependencies=[Depends(require_csrf)],
)
def preview_review_template(
    version_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReviewTemplatePreviewView:
    preview = _service(request).preview_template(
        scope_from_identity(identity), version_id
    )
    return ReviewTemplatePreviewView(
        source_document_version_id=preview.source_document_version_id,
        study_id=preview.study_id,
        site_id=preview.site_id,
        title=preview.title,
        sections=list(preview.extraction.sections),
        questions=[
            ExtractedQuestionView(
                item_key=item.item_key,
                section_key=item.section_key,
                section_order=item.section_order,
                section_title=item.section_title,
                question_order=item.question_order,
                question_text=item.question_text,
                source_locator=item.source_locator,
                source_quote=item.source_quote,
                report_locator=item.report_locator,
                applicability=item.applicability,
            )
            for item in preview.extraction.questions
        ],
        warnings=list(preview.extraction.warnings),
    )


@router.post(
    "/review-templates",
    response_model=ReviewTemplateView,
    dependencies=[Depends(require_csrf)],
)
def create_review_template(
    command: CreateReviewTemplateCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ReviewTemplateView:
    return _template_view(
        _service(request).create_template(
            scope_from_identity(identity), command
        )
    )


@router.get(
    "/review-templates",
    response_model=list[ReviewTemplateView],
)
def list_review_templates(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[ReviewTemplateView]:
    return [
        _template_view(item)
        for item in _service(request).list_templates(
            scope_from_identity(identity), study_id, site_id
        )
    ]


@router.post(
    "/monitoring-visits/{visit_id}/review-template",
    response_model=VisitReviewBoardView,
    dependencies=[Depends(require_csrf)],
)
def bind_review_template(
    visit_id: uuid.UUID,
    command: BindReviewTemplateCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> VisitReviewBoardView:
    return _board_view(
        _service(request).bind_visit(
            scope_from_identity(identity), visit_id, command
        )
    )


@router.get(
    "/monitoring-visits/{visit_id}/review-items",
    response_model=VisitReviewBoardView,
)
def get_monitoring_review_items(
    visit_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> VisitReviewBoardView:
    return _board_view(
        _service(request).board(
            scope_from_identity(identity), visit_id
        )
    )


@router.patch(
    "/monitoring-review-items/{item_id}",
    response_model=MonitoringReviewItemView,
    dependencies=[Depends(require_csrf)],
)
def update_monitoring_review_item(
    item_id: uuid.UUID,
    command: UpdateMonitoringReviewItemCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> MonitoringReviewItemView:
    return _visit_item_view(
        _service(request).update_item(
            scope_from_identity(identity), item_id, command
        )
    )
