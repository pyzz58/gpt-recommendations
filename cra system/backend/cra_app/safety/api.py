"""HTTP contracts for evidence-grounded safety assessments and reviews."""
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
from cra_app.issues.api import IssueView, issue_view
from cra_app.safety.contracts import (
    CraSafetyReviewCommand,
    CreateSafetyAssessmentCommand,
    LinkSafetyIssuesCommand,
    MedicalSafetyResponseCommand,
)
from cra_app.safety.service import AssessmentDetail, SafetyService
from cra_app.shared.output_contract import OutputEnvelope

router = APIRouter(prefix="/api/v1", tags=["safety"])


class SafetyDimensionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    dimension: str
    status: str
    label: str
    candidate_values: list[str]
    rationale: str | None
    uncertainties: list[str]
    rule_version_ids: list[str]
    evidence_ids: list[str]
    source_refs: list[dict[str, Any]]


class SafetyQuestionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_key: str
    dimension: str
    question: str
    reason: str
    priority: str
    evidence_ids: list[str]


class TimelySafetyAlertView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_key: str
    title: str
    detail: str
    dimensions: list[str]
    evidence_ids: list[str]
    event_date: date
    awareness_date: date | None
    entry_date: date | None
    reported_date: date | None
    deadline_status: str
    not_a_final_reportability_decision: bool


class SafetyCraReviewView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    decision: str
    dimensions: list[str]
    note: str | None
    check_decision_id: uuid.UUID | None
    actor_id: str
    created_at: datetime


class MedicalSafetyResponseView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    respondent_role: str
    respondent_name: str | None
    response_text: str
    dimension_responses: dict[str, str]
    source_note: str | None
    actor_id: str
    created_at: datetime


class SafetyAssessmentSummaryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    subject_id: uuid.UUID
    event_type: str
    event_date: date
    status: str
    provider_status: str
    revision: int
    created_at: datetime


class SafetyAssessmentView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    subject_id: uuid.UUID
    lab_comparison_id: uuid.UUID | None
    event_type: str
    event_date: date
    requested_dimensions: list[str]
    context_snapshot: dict[str, Any]
    rule_inputs: list[dict[str, Any]]
    deterministic_summary: dict[str, Any]
    provider_name: str
    provider_version: str
    model_version: str | None
    provider_status: str
    provider_output: dict[str, Any]
    questions: list[SafetyQuestionView]
    timely_alerts: list[TimelySafetyAlertView]
    unknowns: list[dict[str, Any]]
    evidence_refs: list[dict[str, Any]]
    output_envelope: OutputEnvelope
    status: str
    revision: int
    created_by: str
    created_at: datetime
    dimensions: list[SafetyDimensionView]
    cra_reviews: list[SafetyCraReviewView]
    medical_responses: list[MedicalSafetyResponseView]
    issue_id: uuid.UUID | None
    replayed: bool


def _service(request: Request) -> SafetyService:
    return request.app.state.safety_service


def _summary(item) -> SafetyAssessmentSummaryView:
    return SafetyAssessmentSummaryView(
        id=item.id,
        study_id=item.study_id,
        site_id=item.site_id,
        subject_id=item.subject_id,
        event_type=item.event_type,
        event_date=item.event_date,
        status=item.status,
        provider_status=item.provider_status,
        revision=item.revision,
        created_at=item.created_at,
    )


def _assessment_view(detail: AssessmentDetail) -> SafetyAssessmentView:
    item = detail.assessment
    return SafetyAssessmentView(
        id=item.id,
        study_id=item.study_id,
        site_id=item.site_id,
        subject_id=item.subject_id,
        lab_comparison_id=item.lab_comparison_id,
        event_type=item.event_type,
        event_date=item.event_date,
        requested_dimensions=item.requested_dimensions,
        context_snapshot=item.context_snapshot,
        rule_inputs=item.rule_inputs,
        deterministic_summary=item.deterministic_summary,
        provider_name=item.provider_name,
        provider_version=item.provider_version,
        model_version=item.model_version,
        provider_status=item.provider_status,
        provider_output=item.provider_output,
        questions=[
            SafetyQuestionView.model_validate(value)
            for value in item.questions
        ],
        timely_alerts=[
            TimelySafetyAlertView.model_validate(value)
            for value in item.timely_alerts
        ],
        unknowns=item.unknowns,
        evidence_refs=item.evidence_refs,
        output_envelope=OutputEnvelope.model_validate(item.output_envelope),
        status=item.status,
        revision=item.revision,
        created_by=item.created_by,
        created_at=item.created_at,
        dimensions=[
            SafetyDimensionView(
                id=value.id,
                dimension=value.dimension,
                status=value.status,
                label=value.label,
                candidate_values=value.candidate_values,
                rationale=value.rationale,
                uncertainties=value.uncertainties,
                rule_version_ids=value.rule_version_ids,
                evidence_ids=value.evidence_ids,
                source_refs=value.source_refs,
            )
            for value in detail.dimensions
        ],
        cra_reviews=[
            SafetyCraReviewView(
                id=value.id,
                decision=value.decision,
                dimensions=value.dimensions,
                note=value.note,
                check_decision_id=value.check_decision_id,
                actor_id=value.actor_id,
                created_at=value.created_at,
            )
            for value in detail.cra_reviews
        ],
        medical_responses=[
            MedicalSafetyResponseView(
                id=value.id,
                respondent_role=value.respondent_role,
                respondent_name=value.respondent_name,
                response_text=value.response_text,
                dimension_responses=value.dimension_responses,
                source_note=value.source_note,
                actor_id=value.actor_id,
                created_at=value.created_at,
            )
            for value in detail.medical_responses
        ],
        issue_id=detail.issue_link.issue_id if detail.issue_link else None,
        replayed=detail.replayed,
    )


@router.post(
    "/safety-assessments",
    response_model=SafetyAssessmentView,
    dependencies=[Depends(require_csrf)],
)
def create_safety_assessment(
    command: CreateSafetyAssessmentCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SafetyAssessmentView:
    return _assessment_view(
        _service(request).create(scope_from_identity(identity), command)
    )


@router.get(
    "/safety-assessments/{assessment_id}",
    response_model=SafetyAssessmentView,
)
def get_safety_assessment(
    assessment_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SafetyAssessmentView:
    return _assessment_view(
        _service(request).detail(
            scope_from_identity(identity), assessment_id
        )
    )


@router.get(
    "/studies/{study_id}/safety-assessments",
    response_model=list[SafetyAssessmentSummaryView],
)
def list_safety_assessments(
    study_id: uuid.UUID,
    request: Request,
    site_id: uuid.UUID = Query(...),
    subject_id: uuid.UUID = Query(...),
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[SafetyAssessmentSummaryView]:
    return [
        _summary(item)
        for item in _service(request).list_assessments(
            scope_from_identity(identity), study_id, site_id, subject_id
        )
    ]


@router.post(
    "/safety-assessments/{assessment_id}/cra-review",
    response_model=SafetyAssessmentView,
    dependencies=[Depends(require_csrf)],
)
def record_cra_safety_review(
    assessment_id: uuid.UUID,
    command: CraSafetyReviewCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SafetyAssessmentView:
    return _assessment_view(
        _service(request).record_cra_review(
            scope_from_identity(identity), assessment_id, command
        )
    )


@router.post(
    "/safety-assessments/{assessment_id}/medical-response",
    response_model=SafetyAssessmentView,
    dependencies=[Depends(require_csrf)],
)
def record_medical_safety_response(
    assessment_id: uuid.UUID,
    command: MedicalSafetyResponseCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> SafetyAssessmentView:
    return _assessment_view(
        _service(request).record_medical_response(
            scope_from_identity(identity), assessment_id, command
        )
    )


@router.post(
    "/safety-assessments/{assessment_id}/issues",
    response_model=IssueView,
    dependencies=[Depends(require_csrf)],
)
def link_safety_assessment_issue(
    assessment_id: uuid.UUID,
    command: LinkSafetyIssuesCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> IssueView:
    return issue_view(
        _service(request).link_issue(
            scope_from_identity(identity), assessment_id, command
        )
    )
