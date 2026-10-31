"""HTTP contracts for laboratory recognition, review and EDC comparison."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel, ConfigDict

from cra_app.documents.service import CreateDocumentCommand
from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.issues.api import issue_view
from cra_app.laboratory.contracts import (
    BatchConfirmLabObservationsCommand,
    CreateLabComparisonCommand,
    LinkLabIssuesCommand,
    ManualLabObservationCommand,
    ReviewLabObservationCommand,
)
from cra_app.laboratory.service import (
    ComparisonDetail,
    EffectiveObservation,
    IssueLinkResult,
    LaboratoryService,
    ReportDetail,
    effective_observations,
)

router = APIRouter(prefix="/api/v1", tags=["laboratory"])


class LabObservationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    ordinal: int
    subject_external_id: str | None
    visit_key: str | None
    analyte: str | None
    specimen: str | None
    collected_on: date | None
    collected_at: datetime | None
    precision: str
    timezone_status: str
    instance_type: str
    repeat_instance: str | None
    report_on: date | None
    report_revision: str | None
    value_raw: str | None
    value_type: str
    operator: str | None
    numeric_value: Decimal | None
    unit: str | None
    lower_limit: str | None
    upper_limit: str | None
    extraction_state: str
    validation_state: str
    issues: list[str]
    source_ref: dict[str, Any]
    provider_confidence: Decimal | None
    latest_decision: str | None
    latest_decision_at: datetime | None


class LabReportView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    source_document_version_id: uuid.UUID
    recognition_job_id: uuid.UUID
    source_sha256: str
    file_format: str
    provider_name: str
    provider_version: str
    model_version: str | None
    support_profile: dict[str, Any]
    warnings: list[str]
    state: str
    observations_count: int
    revision: int
    created_at: datetime
    observations: list[LabObservationView]
    replayed: bool


class LabComparisonFieldView(BaseModel):
    id: uuid.UUID
    observation_id: uuid.UUID
    edc_record_id: uuid.UUID | None
    ordinal: int
    match_status: str
    result_status: str
    matched_identity: dict[str, Any]
    candidate_record_ids: list[str]
    source_value: str | None
    edc_value: str | None
    source_unit: str | None
    edc_unit: str | None
    unknowns: list[str]
    reason: str | None
    field_results: list[dict[str, Any]]
    linked_issue_id: uuid.UUID | None
    stale: bool


class LabComparisonView(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    edc_snapshot_id: uuid.UUID
    report_revision: int
    report_current_revision: int
    snapshot_record_count: int
    state: str
    scope: dict[str, Any]
    unknowns: list[dict[str, Any]]
    input_digest: str
    revision: int
    created_at: datetime
    fields: list[LabComparisonFieldView]
    stale: bool
    stale_field_ids: list[uuid.UUID]
    replayed: bool


class LabIssueLinkView(BaseModel):
    comparison_id: uuid.UUID
    links: list[dict[str, uuid.UUID]]
    issues: list[dict[str, Any]]


def _service(request: Request) -> LaboratoryService:
    return request.app.state.laboratory_service


def _observation_view(effective: EffectiveObservation) -> LabObservationView:
    observation = effective.observation
    fields = effective.fields
    return LabObservationView(
        id=observation.id,
        ordinal=observation.ordinal,
        subject_external_id=fields.get("subject_external_id"),
        visit_key=fields.get("visit_key"),
        analyte=fields.get("analyte_raw"),
        specimen=fields.get("specimen"),
        collected_on=fields.get("collected_on"),
        collected_at=fields.get("collected_at"),
        precision=observation.precision,
        timezone_status=fields.get(
            "timezone_status", observation.timezone_status
        ),
        instance_type=fields.get("instance_type") or observation.instance_type,
        repeat_instance=fields.get(
            "instance_type_raw", observation.repeat_instance
        ),
        report_on=fields.get("report_on"),
        report_revision=fields.get("report_revision"),
        value_raw=fields.get("value_raw"),
        value_type=fields.get("value_type", observation.value_type),
        operator=fields.get("operator", observation.operator),
        numeric_value=fields.get(
            "numeric_value", observation.numeric_value
        ),
        unit=fields.get("unit_raw"),
        lower_limit=fields.get("lower_limit_raw"),
        upper_limit=fields.get("upper_limit_raw"),
        extraction_state=effective.extraction_state,
        validation_state=effective.validation_state,
        issues=list(effective.issues),
        source_ref=observation.source_ref,
        provider_confidence=observation.provider_confidence,
        latest_decision=(
            effective.decision.action if effective.decision else None
        ),
        latest_decision_at=(
            effective.decision.created_at if effective.decision else None
        ),
    )


def _report_view(detail: ReportDetail) -> LabReportView:
    report = detail.report
    effective = effective_observations(detail)
    return LabReportView(
        id=report.id,
        study_id=report.study_id,
        site_id=report.site_id,
        source_document_version_id=report.source_document_version_id,
        recognition_job_id=report.recognition_job_id,
        source_sha256=report.source_sha256,
        file_format=report.file_format,
        provider_name=report.provider_name,
        provider_version=report.provider_version,
        model_version=report.model_version,
        support_profile=report.support_profile,
        warnings=report.warnings,
        state=report.state,
        observations_count=report.observations_count,
        revision=report.revision,
        created_at=report.created_at,
        observations=[_observation_view(item) for item in effective],
        replayed=detail.replayed,
    )


def _comparison_view(detail: ComparisonDetail) -> LabComparisonView:
    comparison = detail.comparison
    links = {
        link.comparison_field_id: link.issue_id for link in detail.issue_links
    }
    return LabComparisonView(
        id=comparison.id,
        report_id=comparison.report_id,
        edc_snapshot_id=comparison.edc_snapshot_id,
        report_revision=comparison.report_revision,
        report_current_revision=detail.report_current_revision,
        snapshot_record_count=comparison.snapshot_record_count,
        state=comparison.state,
        scope=comparison.scope,
        unknowns=comparison.unknowns,
        input_digest=comparison.input_digest,
        revision=comparison.revision,
        created_at=comparison.created_at,
        fields=[
            LabComparisonFieldView(
                id=field.id,
                observation_id=field.observation_id,
                edc_record_id=field.edc_record_id,
                ordinal=field.ordinal,
                match_status=field.match_status,
                result_status=field.result_status,
                matched_identity=field.matched_identity,
                candidate_record_ids=field.candidate_record_ids,
                source_value=field.source_value,
                edc_value=field.edc_value,
                source_unit=field.source_unit,
                edc_unit=field.edc_unit,
                unknowns=field.unknowns,
                reason=field.reason,
                field_results=field.field_results,
                linked_issue_id=links.get(field.id),
                stale=field.id in detail.stale_field_ids,
            )
            for field in detail.fields
        ],
        stale=detail.stale,
        stale_field_ids=sorted(
            detail.stale_field_ids, key=lambda item: str(item)
        ),
        replayed=detail.replayed,
    )


@router.post(
    "/studies/{study_id}/lab-reports",
    response_model=LabReportView,
    dependencies=[Depends(require_csrf)],
)
async def create_lab_report(
    study_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    file: UploadFile = File(...),
    site_id: uuid.UUID = Form(...),
    title: str = Form(...),
    version_label: str = Form(default="v1"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> LabReportView:
    filename = file.filename or "synthetic-lab-report.pdf"
    content = await file.read()
    command = CreateDocumentCommand(
        expected_revision=0,
        idempotency_key=idempotency_key,
        title=title,
        document_type="report",
        purpose="fact",
        version_label=version_label,
        site_id=site_id,
    )
    detail = _service(request).create_and_recognize(
        scope_from_identity(identity),
        study_id,
        command,
        filename=filename,
        content=content,
    )
    return _report_view(detail)


@router.get(
    "/studies/{study_id}/lab-reports",
    response_model=list[LabReportView],
)
def list_lab_reports(
    study_id: uuid.UUID,
    site_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[LabReportView]:
    return [
        _report_view(
            _service(request).report_detail(
                scope_from_identity(identity), report.id
            )
        )
        for report in _service(request).list_reports(
            scope_from_identity(identity), study_id, site_id
        )
    ]


@router.get("/lab-reports/{report_id}", response_model=LabReportView)
def get_lab_report(
    report_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabReportView:
    return _report_view(
        _service(request).report_detail(
            scope_from_identity(identity), report_id
        )
    )


@router.post(
    "/lab-reports/{report_id}/observations/{observation_id}/decision",
    response_model=LabReportView,
    dependencies=[Depends(require_csrf)],
)
def review_lab_observation(
    report_id: uuid.UUID,
    observation_id: uuid.UUID,
    command: ReviewLabObservationCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabReportView:
    return _report_view(
        _service(request).review_observation(
            scope_from_identity(identity),
            report_id,
            observation_id,
            command,
        )
    )


@router.post(
    "/lab-reports/{report_id}/observations/batch-confirm",
    response_model=LabReportView,
    dependencies=[Depends(require_csrf)],
)
def batch_confirm_lab_observations(
    report_id: uuid.UUID,
    command: BatchConfirmLabObservationsCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabReportView:
    return _report_view(
        _service(request).batch_confirm(
            scope_from_identity(identity), report_id, command
        )
    )


@router.post(
    "/lab-reports/{report_id}/observations",
    response_model=LabReportView,
    dependencies=[Depends(require_csrf)],
)
def add_manual_lab_observation(
    report_id: uuid.UUID,
    command: ManualLabObservationCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabReportView:
    return _report_view(
        _service(request).add_manual_observation(
            scope_from_identity(identity), report_id, command
        )
    )


@router.post(
    "/lab-comparisons",
    response_model=LabComparisonView,
    dependencies=[Depends(require_csrf)],
)
def create_lab_comparison(
    command: CreateLabComparisonCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabComparisonView:
    return _comparison_view(
        _service(request).create_comparison(
            scope_from_identity(identity), command
        )
    )


@router.get(
    "/lab-comparisons/{comparison_id}",
    response_model=LabComparisonView,
)
def get_lab_comparison(
    comparison_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabComparisonView:
    return _comparison_view(
        _service(request).comparison_detail(
            scope_from_identity(identity), comparison_id
        )
    )


@router.post(
    "/lab-comparisons/{comparison_id}/issues",
    response_model=LabIssueLinkView,
    dependencies=[Depends(require_csrf)],
)
def link_lab_comparison_issues(
    comparison_id: uuid.UUID,
    command: LinkLabIssuesCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> LabIssueLinkView:
    result = _service(request).link_issues(
        scope_from_identity(identity), comparison_id, command
    )
    issues = [
        issue_view(
            _service(request).issues.issue_detail(
                scope_from_identity(identity), issue_id
            )
        )
        for _, issue_id in result.links
    ]
    return LabIssueLinkView(
        comparison_id=result.comparison_id,
        links=[
            {"field_id": field_id, "issue_id": issue_id}
            for field_id, issue_id in result.links
        ],
        issues=[
            issue.model_dump(mode="json") for issue in issues
        ],
    )
