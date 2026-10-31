"""Authorized subject facts, timeline, visit-window and checkpoint endpoints."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict

from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.shared.output_contract import OutputEnvelope
from cra_app.subjects.context_import import (
    ContextImportError,
    parse_context_file,
)
from cra_app.subjects.contracts import (
    CheckDecisionCommand,
    ConfirmFactCommand,
    CoverageBreakpointCommand,
    CreateSubjectCommand,
    FactImportRow,
    ImportFactsCommand,
    MapSubjectIdentifierCommand,
    ResumeCheckDecisionCommand,
)
from cra_app.subjects.service import (
    EvaluateVisitRequirementsCommand,
    SubjectService,
)

router = APIRouter(prefix="/api/v1", tags=["subjects"])


class SubjectIdentifierView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    identity_namespace: str
    external_id: str


class SubjectView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    deidentified_label: str
    revision: int
    current_stage: str
    identifiers: list[SubjectIdentifierView]


class CreateSubjectResponse(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    deidentified_label: str
    revision: int


class MapIdentifierResponse(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    identity_namespace: str
    external_id: str


class ImportFactsRequest(ImportFactsCommand):
    pass


class ImportFactsResponse(BaseModel):
    subject_ids: list[uuid.UUID]
    inserted_facts: int
    superseded_facts: int
    replayed: bool


class ClinicalFactView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    subject_id: uuid.UUID
    fact_key: str
    repeat_instance: str
    revision: int
    value_type: str
    value: Any
    value_raw: str
    unit: str | None
    observed_on: date | None
    observed_at: datetime | None
    precision: str
    source_kind: str
    verification_status: str
    source_ref: dict[str, Any]
    supersedes_fact_id: uuid.UUID | None
    is_current: bool
    created_by: str
    created_at: datetime


class ConfirmFactRequestBody(ConfirmFactCommand):
    pass


class VisitRequirementView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    visit_key: str
    stage: str
    status: Literal[
        "ready",
        "in_window",
        "out_of_window",
        "unknown_anchor",
        "unknown_actual",
        "not_checked_by_user",
        "needs_review",
    ]
    anchor_fact_key: str
    anchor_date: date | None
    event_fact_key: str
    actual_date: date | None
    event_date: date
    window_start: date | None
    window_end: date | None
    min_days: int
    max_days: int
    inclusive: bool
    required_fact_keys: list[str]
    allowed_sources: list[str]
    affected_paths: list[str]
    can_continue: list[str]
    rule_version_id: uuid.UUID


class VisitRequirementResult(BaseModel):
    requirement: VisitRequirementView
    rule_summary: str
    window_status: str


class VisitInstanceView(BaseModel):
    id: uuid.UUID
    visit_key: str
    repeat_instance: str
    revision: int
    stage: str | None
    planned_on: date | None
    actual_on: date | None
    precision: str


class EvaluateVisitRequirementsResponse(BaseModel):
    envelope: OutputEnvelope
    requirements: list[VisitRequirementResult]
    instances: list[VisitInstanceView]


class CoverageBreakpointRequest(CoverageBreakpointCommand):
    pass


class CoverageBreakpointView(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    category: str
    scope_key: str
    revision: int
    status: str
    checked_through: str | None
    normal_scope_note: str | None
    unverified_scope: list[str]
    created_by: str
    created_at: datetime


class CheckDecisionRequest(CheckDecisionCommand):
    pass


class ResumeCheckDecisionRequest(ResumeCheckDecisionCommand):
    pass


class CheckDecisionView(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    category: str
    check_type: str
    reason: str
    scope_start: date | None
    scope_end: date | None
    missing_keys: list[str]
    affected_paths: list[str]
    can_continue: list[str]
    rule_version_id: uuid.UUID | None
    state: str
    revision: int
    recovery_available: bool
    created_by: str
    created_at: datetime
    resumed_by: str | None
    resumed_at: datetime | None


def _service(request: Request) -> SubjectService:
    return request.app.state.subject_service


def _subject_view(item: Any) -> SubjectView:
    return SubjectView(
        id=item.subject.id,
        study_id=item.subject.study_id,
        site_id=item.subject.site_id,
        deidentified_label=item.subject.deidentified_label,
        revision=item.subject.revision,
        current_stage=item.current_stage,
        identifiers=[
            SubjectIdentifierView(
                id=identifier.id,
                identity_namespace=identifier.identity_namespace,
                external_id=identifier.external_id,
            )
            for identifier in item.identifiers
        ],
    )


def _fact_view(item: Any) -> ClinicalFactView:
    fact = item.fact
    return ClinicalFactView(
        id=fact.id,
        subject_id=fact.subject_id,
        fact_key=fact.fact_key,
        repeat_instance=fact.repeat_instance,
        revision=fact.revision,
        value_type=fact.value_type,
        value=fact.value_json,
        value_raw=fact.value_raw,
        unit=fact.unit,
        observed_on=fact.observed_on,
        observed_at=fact.observed_at,
        precision=fact.precision,
        source_kind=fact.source_kind,
        verification_status=fact.verification_status,
        source_ref=fact.source_ref,
        supersedes_fact_id=fact.supersedes_fact_id,
        is_current=item.is_current,
        created_by=fact.created_by,
        created_at=fact.created_at,
    )


def _coverage_view(item: Any) -> CoverageBreakpointView:
    return CoverageBreakpointView(
        id=item.id,
        subject_id=item.subject_id,
        category=item.category,
        scope_key=item.scope_key,
        revision=item.revision,
        status=item.status,
        checked_through=item.checked_through,
        normal_scope_note=item.normal_scope_note,
        unverified_scope=item.unverified_scope,
        created_by=item.created_by,
        created_at=item.created_at,
    )


def _decision_view(item: Any) -> CheckDecisionView:
    return CheckDecisionView(
        id=item.id,
        subject_id=item.subject_id,
        category=item.category,
        check_type=item.check_type,
        reason=item.reason,
        scope_start=item.scope_start,
        scope_end=item.scope_end,
        missing_keys=item.missing_keys,
        affected_paths=item.affected_paths,
        can_continue=item.can_continue,
        rule_version_id=item.rule_version_id,
        state=item.state,
        revision=item.revision,
        recovery_available=item.recovery_available,
        created_by=item.created_by,
        created_at=item.created_at,
        resumed_by=item.resumed_by,
        resumed_at=item.resumed_at,
    )


@router.get(
    "/studies/{study_id}/subjects",
    response_model=list[SubjectView],
)
def list_subjects(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[SubjectView]:
    return [
        _subject_view(item)
        for item in _service(request).list_subjects(
            scope_from_identity(identity), study_id, site_id
        )
    ]


@router.post(
    "/studies/{study_id}/subjects",
    response_model=CreateSubjectResponse,
    dependencies=[Depends(require_csrf)],
)
def create_subject(
    study_id: uuid.UUID,
    command: CreateSubjectCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CreateSubjectResponse:
    subject = _service(request).create_subject(
        scope_from_identity(identity), study_id, command
    )
    return CreateSubjectResponse(
        id=subject.id,
        study_id=subject.study_id,
        site_id=subject.site_id,
        deidentified_label=subject.deidentified_label,
        revision=subject.revision,
    )


@router.post(
    "/subjects/{subject_id}/identifiers",
    response_model=MapIdentifierResponse,
    dependencies=[Depends(require_csrf)],
)
def map_subject_identifier(
    subject_id: uuid.UUID,
    command: MapSubjectIdentifierCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> MapIdentifierResponse:
    identifier = _service(request).map_identifier(
        scope_from_identity(identity), subject_id, command
    )
    return MapIdentifierResponse(
        id=identifier.id,
        subject_id=identifier.subject_id,
        identity_namespace=identifier.identity_namespace,
        external_id=identifier.external_id,
    )


@router.post(
    "/studies/{study_id}/facts/import",
    response_model=ImportFactsResponse,
    dependencies=[Depends(require_csrf)],
)
def import_facts(
    study_id: uuid.UUID,
    command: ImportFactsRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ImportFactsResponse:
    outcome = _service(request).import_facts(
        scope_from_identity(identity), study_id, command
    )
    return ImportFactsResponse(
        subject_ids=list(outcome.subject_ids),
        inserted_facts=outcome.inserted_facts,
        superseded_facts=outcome.superseded_facts,
        replayed=outcome.replayed,
    )


@router.post(
    "/studies/{study_id}/facts/import-file",
    response_model=ImportFactsResponse,
    dependencies=[Depends(require_csrf)],
)
async def import_fact_file(
    study_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    file: UploadFile = File(...),
    site_id: uuid.UUID = Form(...),
    identity_namespace: str = Form(...),
    source_kind: str = Form("original_record"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> ImportFactsResponse:
    try:
        rows = parse_context_file(
            file.filename or "context.json", await file.read()
        )
        command = ImportFactsCommand(
            idempotency_key=idempotency_key,
            site_id=site_id,
            identity_namespace=identity_namespace,
            source_kind=source_kind,
            rows=[
                row.model_copy(
                    update={"subject_external_id": row.subject_external_id}
                )
                for row in rows
            ],
        )
    except (ContextImportError, ValueError) as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "context_import_invalid",
                "message": str(exc),
            },
        ) from exc
    outcome = _service(request).import_facts(
        scope_from_identity(identity), study_id, command
    )
    return ImportFactsResponse(
        subject_ids=list(outcome.subject_ids),
        inserted_facts=outcome.inserted_facts,
        superseded_facts=outcome.superseded_facts,
        replayed=outcome.replayed,
    )


@router.get(
    "/subjects/{subject_id}/timeline",
    response_model=list[ClinicalFactView],
)
def subject_timeline(
    subject_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[ClinicalFactView]:
    return [
        _fact_view(item)
        for item in _service(request).timeline(
            scope_from_identity(identity), subject_id
        )
    ]


@router.post(
    "/facts/{fact_id}/confirm",
    response_model=ClinicalFactView,
    dependencies=[Depends(require_csrf)],
)
def confirm_fact(
    fact_id: uuid.UUID,
    command: ConfirmFactRequestBody,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ClinicalFactView:
    fact = _service(request).confirm_fact(
        scope_from_identity(identity), fact_id, command
    )
    from cra_app.subjects.service import TimelineItem

    return _fact_view(TimelineItem(fact=fact, is_current=True))


@router.post(
    "/subjects/{subject_id}/visit-requirements",
    response_model=EvaluateVisitRequirementsResponse,
    dependencies=[Depends(require_csrf)],
)
def evaluate_visit_requirements(
    subject_id: uuid.UUID,
    command: EvaluateVisitRequirementsCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> EvaluateVisitRequirementsResponse:
    outcome = _service(request).evaluate_visit_requirements(
        scope_from_identity(identity), subject_id, command
    )
    return EvaluateVisitRequirementsResponse(
        envelope=outcome.envelope,
        requirements=[
            VisitRequirementResult(
                requirement=VisitRequirementView(
                    id=item.requirement.id,
                    visit_key=item.requirement.visit_key,
                    stage=item.requirement.stage,
                    status=item.requirement.status,
                    anchor_fact_key=item.requirement.anchor_fact_key,
                    anchor_date=item.requirement.anchor_date,
                    event_fact_key=item.requirement.event_fact_key,
                    actual_date=item.requirement.actual_date,
                    event_date=item.requirement.event_date,
                    window_start=item.requirement.window_start,
                    window_end=item.requirement.window_end,
                    min_days=item.requirement.min_days,
                    max_days=item.requirement.max_days,
                    inclusive=item.requirement.inclusive,
                    required_fact_keys=item.requirement.required_fact_keys,
                    allowed_sources=item.requirement.allowed_sources,
                    affected_paths=item.requirement.affected_paths,
                    can_continue=item.requirement.can_continue,
                    rule_version_id=item.requirement.rule_version_id,
                ),
                rule_summary=item.rule_summary,
                window_status=item.window_status,
            )
            for item in outcome.requirements
        ],
        instances=[
            VisitInstanceView(
                id=instance.id,
                visit_key=instance.visit_key,
                repeat_instance=instance.repeat_instance,
                revision=instance.revision,
                stage=instance.stage,
                planned_on=instance.planned_on,
                actual_on=instance.actual_on,
                precision=instance.precision,
            )
            for instance in outcome.instances
        ],
    )


@router.get(
    "/subjects/{subject_id}/visit-requirements",
    response_model=list[VisitRequirementView],
)
def list_visit_requirements(
    subject_id: uuid.UUID,
    event_date: date,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[VisitRequirementView]:
    return [
        VisitRequirementView(
            id=item.id,
            visit_key=item.visit_key,
            stage=item.stage,
            status=item.status,
            anchor_fact_key=item.anchor_fact_key,
            anchor_date=item.anchor_date,
            event_fact_key=item.event_fact_key,
            actual_date=item.actual_date,
            event_date=item.event_date,
            window_start=item.window_start,
            window_end=item.window_end,
            min_days=item.min_days,
            max_days=item.max_days,
            inclusive=item.inclusive,
            required_fact_keys=item.required_fact_keys,
            allowed_sources=item.allowed_sources,
            affected_paths=item.affected_paths,
            can_continue=item.can_continue,
            rule_version_id=item.rule_version_id,
        )
        for item in _service(request).list_visit_requirements(
            scope_from_identity(identity), subject_id, event_date=event_date
        )
    ]


@router.post(
    "/subjects/{subject_id}/coverage",
    response_model=CoverageBreakpointView,
    dependencies=[Depends(require_csrf)],
)
def save_coverage(
    subject_id: uuid.UUID,
    command: CoverageBreakpointRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CoverageBreakpointView:
    return _coverage_view(
        _service(request).save_coverage(
            scope_from_identity(identity), subject_id, command
        )
    )


@router.get(
    "/subjects/{subject_id}/coverage",
    response_model=list[CoverageBreakpointView],
)
def list_coverage(
    subject_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[CoverageBreakpointView]:
    return [
        _coverage_view(item)
        for item in _service(request).list_coverage(
            scope_from_identity(identity), subject_id
        )
    ]


@router.post(
    "/subjects/{subject_id}/check-decisions",
    response_model=CheckDecisionView,
    dependencies=[Depends(require_csrf)],
)
def create_check_decision(
    subject_id: uuid.UUID,
    command: CheckDecisionRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CheckDecisionView:
    return _decision_view(
        _service(request).decide_not_checked(
            scope_from_identity(identity), subject_id, command
        )
    )


@router.post(
    "/subjects/{subject_id}/check-decisions/{decision_id}/resume",
    response_model=CheckDecisionView,
    dependencies=[Depends(require_csrf)],
)
def resume_check_decision(
    subject_id: uuid.UUID,
    decision_id: uuid.UUID,
    command: ResumeCheckDecisionRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> CheckDecisionView:
    return _decision_view(
        _service(request).resume_check_decision(
            scope_from_identity(identity),
            subject_id,
            decision_id,
            command,
        )
    )


@router.get(
    "/subjects/{subject_id}/check-decisions",
    response_model=list[CheckDecisionView],
)
def list_check_decisions(
    subject_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[CheckDecisionView]:
    return [
        _decision_view(item)
        for item in _service(request).list_check_decisions(
            scope_from_identity(identity), subject_id
        )
    ]
