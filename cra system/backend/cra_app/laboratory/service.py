"""Authorized laboratory recognition, review, matching and comparison."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import DocumentVersion
from cra_app.documents.service import (
    CreateDocumentCommand,
    DocumentError,
    DocumentService,
    StoredContent,
)
from cra_app.edc_import.models import EDCLabRecord
from cra_app.edc_import.service import EDCImportService, SnapshotDetail
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.issues.contracts import ActionCreate, CreateIssueCommand
from cra_app.issues.service import IssueDetail, IssueService
from cra_app.laboratory.comparison import (
    EdcValue,
    ObservationValue,
    compare_observation,
    parse_value,
)
from cra_app.laboratory.matching import (
    normalize_analyte,
    normalize_instance,
    normalize_unit,
    normalized_key,
    normalized_text,
)
from cra_app.laboratory.contracts import (
    BatchConfirmLabObservationsCommand,
    CreateLabComparisonCommand,
    LinkLabIssuesCommand,
    ManualLabObservationCommand,
    ReviewLabObservationCommand,
)
from cra_app.laboratory.models import (
    LabComparison,
    LabComparisonField,
    LabComparisonIssueLink,
    LabObservation,
    LabObservationDecision,
    LabRecognitionJob,
    LabReportVersion,
)
from cra_app.laboratory.recognition import (
    LabRowDraft,
    RecognitionDraft,
    SUPPORT_PROFILE,
    extract_observations,
)
from cra_app.platform.jobs import digest_payload
from cra_app.providers.lab_ocr import (
    LabProviderError,
    LabProviderUnavailable,
    LabRecognitionProvider,
    RoutedLabProvider,
)


class LaboratoryError(Exception):
    pass


class LaboratoryNotFound(LaboratoryError):
    pass


class LaboratoryValidationError(LaboratoryError):
    pass


class LaboratoryConflict(LaboratoryError):
    pass


@dataclass(frozen=True)
class ReportDetail:
    report: LabReportVersion
    observations: tuple[LabObservation, ...]
    decisions: tuple[LabObservationDecision, ...]
    replayed: bool = False


@dataclass(frozen=True)
class ComparisonDetail:
    comparison: LabComparison
    fields: tuple[LabComparisonField, ...]
    issue_links: tuple[LabComparisonIssueLink, ...]
    stale: bool = False
    stale_field_ids: frozenset[uuid.UUID] = frozenset()
    report_current_revision: int = 0
    replayed: bool = False


@dataclass(frozen=True)
class EffectiveObservation:
    observation: LabObservation
    decision: LabObservationDecision | None
    fields: dict[str, Any]
    extraction_state: str
    validation_state: str
    issues: tuple[str, ...]


@dataclass(frozen=True)
class IssueLinkResult:
    comparison_id: uuid.UUID
    links: tuple[tuple[uuid.UUID, uuid.UUID], ...]


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


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_datetime(value: Any, *, collection_date: date | None) -> tuple[datetime | None, str]:
    if value is None or value == "":
        return None, "date_only" if collection_date else "unknown"
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_time = time.fromisoformat(raw)
            except ValueError:
                return None, "unknown"
            if collection_date is None:
                return None, "unknown"
            parsed = datetime.combine(collection_date, parsed_time)
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None), "explicit"
    return parsed, "unknown"


def _latest_decisions(
    decisions: list[LabObservationDecision],
) -> dict[uuid.UUID, LabObservationDecision]:
    latest: dict[uuid.UUID, LabObservationDecision] = {}
    for decision in sorted(
        decisions, key=lambda item: (item.created_at, str(item.id))
    ):
        latest[decision.observation_id] = decision
    return latest


def _validate_fields(fields: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    issues: list[str] = []
    if not fields.get("subject_external_id"):
        issues.append("subject_external_id_missing")
    if not fields.get("analyte_raw"):
        issues.append("analyte_missing")
    if fields.get("collected_on") is None:
        issues.append("collection_date_missing_or_invalid")
    if not fields.get("instance_type_raw"):
        issues.append("initial_repeat_instance_missing")
    if not fields.get("value_raw"):
        issues.append("result_missing")
    if not fields.get("unit_raw"):
        issues.append("unit_missing")
    value = parse_value(fields.get("value_raw"))
    if value.value_type in {"text", "unknown"}:
        issues.append("numeric_value_requires_interpretation")
    return ("needs_review" if issues else "ready_for_match", tuple(issues))


def _fields_from_observation(observation: LabObservation) -> dict[str, Any]:
    return {
        "subject_external_id": observation.subject_external_id,
        "visit_key": observation.visit_key,
        "analyte_raw": observation.analyte_raw,
        "specimen": observation.specimen,
        "collected_on": observation.collected_on,
        "collected_at": observation.collected_at,
        "instance_type_raw": observation.instance_type_raw,
        "report_on": observation.report_on,
        "report_revision": observation.report_revision,
        "value_raw": observation.value_raw,
        "unit_raw": observation.unit_raw,
        "lower_limit_raw": observation.lower_limit_raw,
        "upper_limit_raw": observation.upper_limit_raw,
    }


def _effective_observation(
    observation: LabObservation,
    decision: LabObservationDecision | None,
) -> EffectiveObservation:
    fields = _fields_from_observation(observation)
    if decision is None:
        return EffectiveObservation(
            observation=observation,
            decision=None,
            fields=fields,
            extraction_state=observation.extraction_state,
            validation_state=observation.validation_state,
            issues=tuple(observation.issues),
        )
    if decision.action == "skip":
        return EffectiveObservation(
            observation=observation,
            decision=decision,
            fields=fields,
            extraction_state="user_skipped",
            validation_state="needs_review",
            issues=("user_skipped",),
        )
    if decision.action == "confirm":
        if observation.validation_state != "ready_for_match":
            raise LaboratoryValidationError(
                "only observations that passed structural validation can be "
                "bulk-confirmed"
            )
        return EffectiveObservation(
            observation=observation,
            decision=decision,
            fields=fields,
            extraction_state="user_confirmed",
            validation_state="ready_for_match",
            issues=tuple(observation.issues),
        )
    fields.update(decision.corrected_fields)
    fields["collected_on"] = _as_date(fields.get("collected_on"))
    collected_at, timezone_status = _as_datetime(
        fields.get("collected_at"),
        collection_date=fields.get("collected_on"),
    )
    fields["collected_at"] = collected_at
    fields["timezone_status"] = timezone_status
    fields["report_on"] = _as_date(fields.get("report_on"))
    fields["analyte_normalized"] = normalize_analyte(fields.get("analyte_raw"))
    fields["instance_type"] = (
        normalize_instance(fields.get("instance_type_raw")) or "unknown"
    )
    fields["unit_normalized"] = normalize_unit(fields.get("unit_raw"))
    parsed = parse_value(fields.get("value_raw"))
    fields["value_type"] = parsed.value_type
    fields["operator"] = parsed.operator
    fields["numeric_value"] = parsed.number
    validation_state, issues = _validate_fields(fields)
    return EffectiveObservation(
        observation=observation,
        decision=decision,
        fields=fields,
        extraction_state="user_corrected",
        validation_state=validation_state,
        issues=issues,
    )


def _observation_value(effective: EffectiveObservation) -> ObservationValue:
    fields = effective.fields
    return ObservationValue(
        id=str(effective.observation.id),
        subject_external_id=fields.get("subject_external_id"),
        visit_key=fields.get("visit_key"),
        analyte=fields.get("analyte_raw"),
        specimen=fields.get("specimen"),
        collected_on=fields.get("collected_on"),
        collected_at=fields.get("collected_at"),
        instance_type=fields.get("instance_type") or normalize_instance(
            fields.get("instance_type_raw")
        ),
        report_on=fields.get("report_on"),
        report_revision=fields.get("report_revision"),
        value_raw=fields.get("value_raw"),
        unit=fields.get("unit_raw"),
        lower_limit=fields.get("lower_limit_raw"),
        upper_limit=fields.get("upper_limit_raw"),
        validation_state=effective.validation_state,
        extraction_state=effective.extraction_state,
        issues=effective.issues,
    )


def _effective_signature(effective: EffectiveObservation) -> dict[str, Any]:
    fields = effective.fields
    signature = {
        "subject_external_id": fields.get("subject_external_id"),
        "visit_key": fields.get("visit_key"),
        "analyte_raw": fields.get("analyte_raw"),
        "specimen": fields.get("specimen"),
        "collected_on": fields.get("collected_on"),
        "collected_at": fields.get("collected_at"),
        "instance_type_raw": fields.get("instance_type_raw"),
        "report_on": fields.get("report_on"),
        "report_revision": fields.get("report_revision"),
        "value_raw": fields.get("value_raw"),
        "unit_raw": fields.get("unit_raw"),
        "lower_limit_raw": fields.get("lower_limit_raw"),
        "upper_limit_raw": fields.get("upper_limit_raw"),
        "review_state": (
            "skipped"
            if effective.extraction_state == "user_skipped"
            else "corrected"
            if effective.extraction_state == "user_corrected"
            else "base"
        ),
        "validation_state": effective.validation_state,
        "issues": list(effective.issues),
    }
    return json.loads(json.dumps(signature, ensure_ascii=False, default=str))


def effective_observations(
    detail: ReportDetail,
) -> tuple[EffectiveObservation, ...]:
    latest = _latest_decisions(list(detail.decisions))
    return tuple(
        _effective_observation(observation, latest.get(observation.id))
        for observation in detail.observations
    )


class LaboratoryService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        documents: DocumentService,
        edc_imports: EDCImportService,
        issues: IssueService,
        governance: GovernanceService | None = None,
        provider: LabRecognitionProvider | None = None,
    ):
        self.session_factory = session_factory
        self.documents = documents
        self.edc_imports = edc_imports
        self.issues = issues
        self.governance = governance or GovernanceService(session_factory)
        self.provider = provider or RoutedLabProvider(ocr_provider="disabled")

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

    def _reserve(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        command_name: str,
        idempotency_key: str,
        command: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": fingerprint,
                "command": command,
            }
        )
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=uuid.uuid4(),
                actor_id=scope.actor_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                scope_fingerprint=fingerprint,
                command_name=command_name,
                idempotency_key=idempotency_key,
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
                IdempotencyRecord.scope_fingerprint == fingerprint,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key == idempotency_key,
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
    def _complete(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    def _load_report(self, scope: ScopeContext, report_id: uuid.UUID) -> LabReportVersion:
        with self.session_factory() as session:
            report = session.scalar(
                select(LabReportVersion).where(
                    LabReportVersion.id == report_id,
                    LabReportVersion.tenant_id == scope.tenant_id,
                )
            )
            if report is None:
                raise LaboratoryNotFound("laboratory report was not found")
            self._authorize_read(scope, report.study_id, report.site_id)
            return report

    def report_detail(
        self, scope: ScopeContext, report_id: uuid.UUID
    ) -> ReportDetail:
        report = self._load_report(scope, report_id)
        with self.session_factory() as session:
            observations = tuple(
                session.scalars(
                    select(LabObservation)
                    .where(LabObservation.report_id == report_id)
                    .order_by(LabObservation.ordinal)
                )
            )
            decisions = tuple(
                session.scalars(
                    select(LabObservationDecision)
                    .where(LabObservationDecision.tenant_id == scope.tenant_id)
                    .join(
                        LabObservation,
                        LabObservation.id
                        == LabObservationDecision.observation_id,
                    )
                    .where(LabObservation.report_id == report_id)
                    .order_by(
                        LabObservationDecision.created_at,
                        LabObservationDecision.id,
                    )
                )
            )
            return ReportDetail(
                report=report,
                observations=observations,
                decisions=decisions,
            )

    def list_reports(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[LabReportVersion]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(LabReportVersion)
                    .where(
                        LabReportVersion.tenant_id == scope.tenant_id,
                        LabReportVersion.study_id == study_id,
                        LabReportVersion.site_id == site_id,
                    )
                    .order_by(
                        LabReportVersion.created_at.desc(),
                        LabReportVersion.id,
                    )
                )
            )

    def _observation_model(
        self,
        *,
        report: LabReportVersion,
        draft: LabRowDraft,
    ) -> LabObservation:
        return LabObservation(
            id=uuid.uuid4(),
            tenant_id=report.tenant_id,
            study_id=report.study_id,
            site_id=report.site_id,
            report_id=report.id,
            ordinal=draft.ordinal,
            subject_external_id=draft.subject_external_id,
            visit_key=draft.visit_key,
            analyte_raw=draft.analyte_raw,
            analyte_normalized=draft.analyte_normalized,
            specimen=draft.specimen,
            collected_on=draft.collected_on,
            collected_at=draft.collected_at,
            precision=draft.precision,
            timezone_status=draft.timezone_status,
            instance_type_raw=draft.instance_type_raw,
            instance_type=draft.instance_type,
            repeat_instance=draft.repeat_instance,
            report_on=draft.report_on,
            report_revision=draft.report_revision,
            value_raw=draft.value_raw,
            value_type=draft.value_type,
            operator=draft.operator,
            numeric_value=draft.numeric_value,
            unit_raw=draft.unit_raw,
            unit_normalized=draft.unit_normalized,
            lower_limit_raw=draft.lower_limit_raw,
            upper_limit_raw=draft.upper_limit_raw,
            extraction_state=draft.extraction_state,
            validation_state=draft.validation_state,
            issues=list(draft.issues),
            source_ref=draft.source_ref,
            provider_confidence=draft.provider_confidence,
        )

    def create_and_recognize(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateDocumentCommand,
        *,
        filename: str,
        content: bytes,
    ) -> ReportDetail:
        upload = self.documents.create_document(
            scope,
            study_id,
            command,
            filename=filename,
            content=content,
        )
        try:
            self.documents.process_job(
                upload.job_id, worker_id="laboratory-intake"
            )
        except DocumentError:
            # The generic W03 parser may not support an image even when the
            # laboratory provider does. The private source and lab job remain.
            pass
        with self.session_factory() as session:
            existing = session.scalar(
                select(LabReportVersion).where(
                    LabReportVersion.tenant_id == scope.tenant_id,
                    LabReportVersion.study_id == study_id,
                    LabReportVersion.source_document_version_id
                    == upload.document_version_id,
                )
            )
            if existing is not None:
                detail = self.report_detail(scope, existing.id)
                return ReportDetail(
                    report=detail.report,
                    observations=detail.observations,
                    decisions=detail.decisions,
                    replayed=True,
                )
            report = LabReportVersion(
                id=uuid.uuid4(),
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=command.site_id,
                source_document_version_id=upload.document_version_id,
                recognition_job_id=uuid.uuid4(),
                source_sha256=upload.sha256,
                file_format="pending",
                provider_name="pending",
                provider_version="pending",
                model_version=None,
                support_profile=SUPPORT_PROFILE,
                warnings=[],
                state="pending",
                observations_count=0,
                revision=1,
                created_by=scope.actor_id,
            )
            recognition_job = LabRecognitionJob(
                id=report.recognition_job_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=command.site_id,
                source_document_version_id=upload.document_version_id,
                actor_id=scope.actor_id,
                authentication_source=scope.authentication_source,
                platform_roles=sorted(scope.platform_roles),
                idempotency_key=command.idempotency_key,
                request_digest=digest_payload(
                    {
                        "source_document_version_id": str(
                            upload.document_version_id
                        ),
                        "source_sha256": upload.sha256,
                    }
                ),
                status="queued",
                attempts=0,
                output={},
            )
            session.add(recognition_job)
            session.flush()
            session.add(report)
            session.commit()
            report_id = report.id
            job_id = report.recognition_job_id
        self._mark_job_running(job_id)
        stored = self.documents.read_content(scope, upload.document_version_id)
        try:
            result = self.provider.recognize(
                stored.content,
                filename=stored.filename,
                media_type=stored.media_type,
            )
            draft = extract_observations(result)
        except LabProviderUnavailable as exc:
            return self._finish_unavailable_report(
                scope, report_id, provider_name="disabled", warning=str(exc)
            )
        except LabProviderError as exc:
            return self._finish_failed_report(
                scope,
                report_id,
                provider_name=getattr(self.provider, "name", "provider"),
                warning=f"provider_failed:{type(exc).__name__}",
            )
        return self._store_recognition(scope, report_id, draft)

    def _mark_job_running(self, job_id: uuid.UUID) -> None:
        with self.session_factory() as session:
            with session.begin():
                job = session.get(
                    LabRecognitionJob, job_id, with_for_update=True
                )
                if job is None:
                    raise LaboratoryNotFound("laboratory recognition job was not found")
                job.status = "running"
                job.attempts = 1

    def _finish_unavailable_report(
        self,
        scope: ScopeContext,
        report_id: uuid.UUID,
        *,
        provider_name: str,
        warning: str,
    ) -> ReportDetail:
        with self.session_factory() as session:
            with session.begin():
                report = session.get(
                    LabReportVersion, report_id, with_for_update=True
                )
                if report is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                report.provider_name = provider_name
                report.provider_version = "1"
                report.file_format = "unsupported_or_disabled"
                report.state = "provider_unavailable"
                report.warnings = [warning]
                report.revision += 1
                job = session.get(
                    LabRecognitionJob,
                    report.recognition_job_id,
                    with_for_update=True,
                )
                if job is not None:
                    job.status = "failed"
                    job.error_code = "provider_unavailable"
                    job.error_summary = warning[:500]
                    job.output = {"report_id": str(report.id)}
        return self.report_detail(scope, report_id)

    def _finish_failed_report(
        self,
        scope: ScopeContext,
        report_id: uuid.UUID,
        *,
        provider_name: str,
        warning: str,
    ) -> ReportDetail:
        with self.session_factory() as session:
            with session.begin():
                report = session.get(
                    LabReportVersion, report_id, with_for_update=True
                )
                if report is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                report.provider_name = provider_name
                report.provider_version = "unknown"
                report.file_format = "unknown"
                report.state = "failed"
                report.warnings = [warning]
                report.revision += 1
                job = session.get(
                    LabRecognitionJob,
                    report.recognition_job_id,
                    with_for_update=True,
                )
                if job is not None:
                    job.status = "failed"
                    job.error_code = "provider_failed"
                    job.error_summary = warning[:500]
                    job.output = {"report_id": str(report.id)}
        return self.report_detail(scope, report_id)

    def _store_recognition(
        self,
        scope: ScopeContext,
        report_id: uuid.UUID,
        draft: RecognitionDraft,
    ) -> ReportDetail:
        with self.session_factory() as session:
            with session.begin():
                report = session.get(
                    LabReportVersion, report_id, with_for_update=True
                )
                if report is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                for row in draft.rows:
                    session.add(
                        self._observation_model(report=report, draft=row)
                    )
                report.provider_name = draft.provider_name
                report.provider_version = draft.provider_version
                report.model_version = draft.model_version
                report.file_format = draft.file_format
                report.support_profile = draft.support_profile
                report.warnings = list(draft.warnings)
                report.state = draft.state
                report.observations_count = len(draft.rows)
                report.revision += 1
                job = session.get(
                    LabRecognitionJob,
                    report.recognition_job_id,
                    with_for_update=True,
                )
                if job is None:
                    raise LaboratoryNotFound(
                        "laboratory recognition job was not found"
                    )
                job.status = "succeeded"
                job.error_code = None
                job.error_summary = None
                job.output = {
                    "report_id": str(report.id),
                    "provider": report.provider_name,
                    "provider_version": report.provider_version,
                    "observations": report.observations_count,
                    "state": report.state,
                }
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=report.tenant_id,
                        study_id=report.study_id,
                        site_id=report.site_id,
                        actor_id=scope.actor_id,
                        action="laboratory.recognition.completed",
                        resource_type="lab_report_version",
                        resource_id=report.id,
                        revision_before=report.revision - 1,
                        revision_after=report.revision,
                        before_state=None,
                        after_state={
                            "state": report.state,
                            "provider": report.provider_name,
                            "provider_version": report.provider_version,
                            "observations": report.observations_count,
                            "warnings": report.warnings,
                        },
                        command_name="laboratory.recognize",
                        correlation_id=report.id,
                    )
                )
        return self.report_detail(scope, report_id)

    def review_observation(
        self,
        scope: ScopeContext,
        report_id: uuid.UUID,
        observation_id: uuid.UUID,
        command: ReviewLabObservationCommand,
    ) -> ReportDetail:
        report = self._load_report(scope, report_id)
        self._authorize_write(scope, report.study_id, report.site_id)
        with self.session_factory() as session:
            with session.begin():
                report = session.scalar(
                    select(LabReportVersion)
                    .where(
                        LabReportVersion.id == report_id,
                        LabReportVersion.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if report is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    command_name="laboratory.observation.review",
                    idempotency_key=command.idempotency_key,
                    command=command.model_dump(mode="json"),
                )
                if replayed:
                    return self.report_detail(scope, report_id)
                if report.revision != command.expected_revision:
                    raise RevisionConflict(report.revision)
                observation = session.scalar(
                    select(LabObservation).where(
                        LabObservation.id == observation_id,
                        LabObservation.report_id == report_id,
                    )
                )
                if observation is None:
                    raise LaboratoryNotFound("laboratory observation was not found")
                if (
                    command.action == "confirm"
                    and observation.validation_state != "ready_for_match"
                ):
                    raise LaboratoryValidationError(
                        "an observation with validation gaps cannot be "
                        "confirmed without correction"
                    )
                decision = LabObservationDecision(
                    id=uuid.uuid4(),
                    tenant_id=report.tenant_id,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    observation_id=observation.id,
                    action=command.action,
                    corrected_fields=command.corrected_fields,
                    note=command.note,
                    actor_id=scope.actor_id,
                )
                session.add(decision)
                report.revision += 1
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=report.tenant_id,
                        study_id=report.study_id,
                        site_id=report.site_id,
                        actor_id=scope.actor_id,
                        action=f"laboratory.observation.{command.action}",
                        resource_type="lab_observation",
                        resource_id=observation.id,
                        revision_before=report.revision - 1,
                        revision_after=report.revision,
                        before_state=None,
                        after_state={
                            "report_id": str(report.id),
                            "decision_id": str(decision.id),
                            "corrected_fields": command.corrected_fields,
                        },
                        command_name="laboratory.observation.review",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, report.id, report.revision)
        return self.report_detail(scope, report_id)

    def batch_confirm(
        self,
        scope: ScopeContext,
        report_id: uuid.UUID,
        command: BatchConfirmLabObservationsCommand,
    ) -> ReportDetail:
        report = self._load_report(scope, report_id)
        self._authorize_write(scope, report.study_id, report.site_id)
        with self.session_factory() as session:
            with session.begin():
                report = session.scalar(
                    select(LabReportVersion)
                    .where(
                        LabReportVersion.id == report_id,
                        LabReportVersion.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if report is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    command_name="laboratory.observation.batch_confirm",
                    idempotency_key=command.idempotency_key,
                    command=command.model_dump(mode="json"),
                )
                if replayed:
                    return self.report_detail(scope, report_id)
                if report.revision != command.expected_revision:
                    raise RevisionConflict(report.revision)
                observations = {
                    item.id: item
                    for item in session.scalars(
                        select(LabObservation).where(
                            LabObservation.report_id == report.id,
                            LabObservation.id.in_(command.observation_ids),
                        )
                    )
                }
                if len(observations) != len(command.observation_ids):
                    raise LaboratoryValidationError(
                        "one or more observations are outside this report"
                    )
                if any(
                    item.validation_state != "ready_for_match"
                    for item in observations.values()
                ):
                    raise LaboratoryValidationError(
                        "batch confirmation only accepts observations that "
                        "passed structural validation"
                    )
                latest = _latest_decisions(
                    list(
                        session.scalars(
                            select(LabObservationDecision).where(
                                LabObservationDecision.observation_id.in_(
                                    command.observation_ids
                                )
                            )
                        )
                    )
                )
                for observation_id in command.observation_ids:
                    if latest.get(observation_id) and latest[
                        observation_id
                    ].action == "skip":
                        continue
                    session.add(
                        LabObservationDecision(
                            id=uuid.uuid4(),
                            tenant_id=report.tenant_id,
                            study_id=report.study_id,
                            site_id=report.site_id,
                            observation_id=observation_id,
                            action="confirm",
                            corrected_fields={},
                            note=command.note,
                            actor_id=scope.actor_id,
                        )
                    )
                report.revision += 1
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=report.tenant_id,
                        study_id=report.study_id,
                        site_id=report.site_id,
                        actor_id=scope.actor_id,
                        action="laboratory.observation.batch_confirm",
                        resource_type="lab_report_version",
                        resource_id=report.id,
                        revision_before=report.revision - 1,
                        revision_after=report.revision,
                        before_state=None,
                        after_state={
                            "observation_ids": [
                                str(item) for item in command.observation_ids
                            ],
                            "note": command.note,
                        },
                        command_name="laboratory.observation.batch_confirm",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, report.id, report.revision)
        return self.report_detail(scope, report_id)

    def add_manual_observation(
        self,
        scope: ScopeContext,
        report_id: uuid.UUID,
        command: ManualLabObservationCommand,
    ) -> ReportDetail:
        report = self._load_report(scope, report_id)
        self._authorize_write(scope, report.study_id, report.site_id)
        collected_at, timezone_status = _as_datetime(
            command.collected_at,
            collection_date=command.collected_on,
        )
        fields = {
            "subject_external_id": command.subject_external_id.strip(),
            "visit_key": normalized_text(command.visit_key),
            "analyte_raw": command.analyte_raw.strip(),
            "specimen": normalized_text(command.specimen),
            "collected_on": command.collected_on,
            "collected_at": collected_at,
            "instance_type_raw": command.instance_type_raw.strip(),
            "report_on": command.report_on,
            "report_revision": normalized_text(command.report_revision),
            "value_raw": command.value_raw.strip(),
            "unit_raw": normalized_text(command.unit_raw),
            "lower_limit_raw": normalized_text(command.lower_limit_raw),
            "upper_limit_raw": normalized_text(command.upper_limit_raw),
        }
        validation_state, issues = _validate_fields(fields)
        parsed = parse_value(fields["value_raw"])
        instance = normalize_instance(fields["instance_type_raw"]) or "unknown"
        with self.session_factory() as session:
            with session.begin():
                report = session.scalar(
                    select(LabReportVersion)
                    .where(
                        LabReportVersion.id == report_id,
                        LabReportVersion.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if report is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    command_name="laboratory.observation.manual",
                    idempotency_key=command.idempotency_key,
                    command=command.model_dump(mode="json"),
                )
                if replayed:
                    return self.report_detail(scope, report_id)
                if report.revision != command.expected_revision:
                    raise RevisionConflict(report.revision)
                next_ordinal = (
                    session.scalar(
                        select(LabObservation.ordinal)
                        .where(LabObservation.report_id == report.id)
                        .order_by(LabObservation.ordinal.desc())
                        .limit(1)
                    )
                    or 0
                ) + 1
                observation = LabObservation(
                    id=uuid.uuid4(),
                    tenant_id=report.tenant_id,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    report_id=report.id,
                    ordinal=next_ordinal,
                    subject_external_id=fields["subject_external_id"],
                    visit_key=fields["visit_key"],
                    analyte_raw=fields["analyte_raw"],
                    analyte_normalized=normalize_analyte(fields["analyte_raw"]),
                    specimen=fields["specimen"],
                    collected_on=fields["collected_on"],
                    collected_at=collected_at,
                    precision=(
                        "minute"
                        if collected_at and not collected_at.second
                        else "second"
                        if collected_at
                        else "date"
                    ),
                    timezone_status=timezone_status,
                    instance_type_raw=fields["instance_type_raw"],
                    instance_type=instance,
                    repeat_instance=fields["instance_type_raw"],
                    report_on=fields["report_on"],
                    report_revision=fields["report_revision"],
                    value_raw=fields["value_raw"],
                    value_type=parsed.value_type,
                    operator=parsed.operator,
                    numeric_value=parsed.number,
                    unit_raw=fields["unit_raw"],
                    unit_normalized=normalize_unit(fields["unit_raw"]),
                    lower_limit_raw=fields["lower_limit_raw"],
                    upper_limit_raw=fields["upper_limit_raw"],
                    extraction_state="manual",
                    validation_state=validation_state,
                    issues=list(issues),
                    source_ref={
                        "provider": "manual-entry",
                        "note": command.source_note,
                        "anchor": "manual",
                    },
                )
                session.add(observation)
                report.observations_count += 1
                report.revision += 1
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=report.tenant_id,
                        study_id=report.study_id,
                        site_id=report.site_id,
                        actor_id=scope.actor_id,
                        action="laboratory.observation.manual",
                        resource_type="lab_observation",
                        resource_id=observation.id,
                        revision_before=report.revision - 1,
                        revision_after=report.revision,
                        before_state=None,
                        after_state={
                            "report_id": str(report.id),
                            "source_note": command.source_note,
                            "issues": list(issues),
                        },
                        command_name="laboratory.observation.manual",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, report.id, report.revision)
        return self.report_detail(scope, report_id)

    @staticmethod
    def _edc_values(detail: SnapshotDetail) -> list[EdcValue]:
        return [
            EdcValue(
                id=str(record.id),
                subject_external_id=record.subject_external_id,
                subject_id=str(record.subject_id) if record.subject_id else None,
                visit_key=record.visit_key,
                analyte=record.analyte,
                specimen=record.specimen,
                collected_on=record.collected_on,
                collected_at=record.collected_at,
                instance_type=record.instance_type,
                report_on=record.report_on,
                report_revision=record.report_revision,
                value_raw=record.value_raw,
                unit=record.unit_raw,
                lower_limit=record.lower_limit,
                upper_limit=record.upper_limit,
                identity_status=record.identity_status,
                validation_status=record.validation_status,
                issues=tuple(record.issues),
            )
            for record in detail.records
        ]

    def create_comparison(
        self,
        scope: ScopeContext,
        command: CreateLabComparisonCommand,
    ) -> ComparisonDetail:
        detail = self.report_detail(scope, command.report_id)
        report = detail.report
        self._authorize_write(scope, report.study_id, report.site_id)
        snapshot = self.edc_imports.snapshot_detail(
            scope, command.edc_snapshot_id
        )
        if (
            snapshot.snapshot.study_id != report.study_id
            or snapshot.snapshot.site_id != report.site_id
        ):
            raise LaboratoryValidationError(
                "laboratory report and EDC snapshot must use the same site"
            )
        effective = list(effective_observations(detail))
        edc_records = self._edc_values(snapshot)
        outcomes = [
            compare_observation(_observation_value(item), edc_records)
            for item in effective
        ]
        input_digest = _digest(
            {
                "report_id": str(report.id),
                "report_revision": report.revision,
                "snapshot_id": str(snapshot.snapshot.id),
                "decisions": [
                    str(item.decision.id) if item.decision else None
                    for item in effective
                ],
                "edc_records": [
                    {
                        "id": str(record.id),
                        "value": record.value_raw,
                        "unit": record.unit_raw,
                        "instance": record.instance_type,
                    }
                    for record in snapshot.records
                ],
            }
        )
        comparison_key = _digest(
            {
                "report_id": str(report.id),
                "snapshot_id": str(snapshot.snapshot.id),
                "input_digest": input_digest,
            }
        )
        state = (
            "no_eligible_observations"
            if not effective
            else "partial"
            if report.state in {"partial", "provider_unavailable", "failed"}
            else "complete"
        )
        unknowns = [
            {"observation_id": str(item.observation.id), "unknown": unknown}
            for item, outcome in zip(effective, outcomes, strict=True)
            for unknown in outcome.unknowns
        ]
        with self.session_factory() as session:
            with session.begin():
                report_locked = session.get(
                    LabReportVersion, report.id, with_for_update=True
                )
                if report_locked is None:
                    raise LaboratoryNotFound("laboratory report was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    command_name="laboratory.comparison.create",
                    idempotency_key=command.idempotency_key,
                    command={
                        **command.model_dump(mode="json"),
                        "comparison_key": comparison_key,
                    },
                )
                if replayed:
                    assert record.response_resource_id is not None
                    result = self.comparison_detail(
                        scope, record.response_resource_id
                    )
                    return ComparisonDetail(
                        comparison=result.comparison,
                        fields=result.fields,
                        issue_links=result.issue_links,
                        stale=result.stale,
                        stale_field_ids=result.stale_field_ids,
                        report_current_revision=result.report_current_revision,
                        replayed=True,
                    )
                existing = session.scalar(
                    select(LabComparison).where(
                        LabComparison.tenant_id == report.tenant_id,
                        LabComparison.study_id == report.study_id,
                        LabComparison.site_id == report.site_id,
                        LabComparison.comparison_key == comparison_key,
                    )
                )
                if existing is not None:
                    self._complete(record, existing.id, existing.revision)
                    result = self.comparison_detail(scope, existing.id)
                    return ComparisonDetail(
                        comparison=result.comparison,
                        fields=result.fields,
                        issue_links=result.issue_links,
                        stale=result.stale,
                        stale_field_ids=result.stale_field_ids,
                        report_current_revision=result.report_current_revision,
                        replayed=True,
                    )
                comparison = LabComparison(
                    id=uuid.uuid4(),
                    tenant_id=report.tenant_id,
                    study_id=report.study_id,
                    site_id=report.site_id,
                    report_id=report.id,
                    edc_snapshot_id=snapshot.snapshot.id,
                    comparison_key=comparison_key,
                    report_revision=report.revision,
                    snapshot_record_count=snapshot.snapshot.record_count,
                    state=state,
                    scope={
                        "report_id": str(report.id),
                        "report_revision": report.revision,
                        "edc_snapshot_id": str(snapshot.snapshot.id),
                        "edc_scope_status": snapshot.snapshot.scope_status,
                        "edc_absence_semantics": snapshot.snapshot.absence_semantics,
                        "observations": len(effective),
                        "edc_records": len(edc_records),
                        "fields_checked": [
                            "identity",
                            "analyte",
                            "collection_date",
                            "collection_time_when_available",
                            "initial_repeat_instance",
                            "Decimal_value",
                            "operator",
                            "unit",
                        ],
                        "medical_safety_assessed": False,
                    },
                    unknowns=unknowns,
                    input_digest=input_digest,
                    revision=1,
                    created_by=scope.actor_id,
                )
                session.add(comparison)
                session.flush()
                for ordinal, (item, outcome) in enumerate(
                    zip(effective, outcomes, strict=True), start=1
                ):
                    matched_identity = {
                        **outcome.matched_identity,
                        "source_ref": item.observation.source_ref,
                    }
                    session.add(
                        LabComparisonField(
                            id=uuid.uuid4(),
                            tenant_id=report.tenant_id,
                            study_id=report.study_id,
                            site_id=report.site_id,
                            comparison_id=comparison.id,
                            observation_id=item.observation.id,
                            edc_record_id=(
                                uuid.UUID(outcome.edc_record_id)
                                if outcome.edc_record_id
                                else None
                            ),
                            ordinal=ordinal,
                            match_status=outcome.match_status,
                            result_status=outcome.result_status,
                            matched_identity=matched_identity,
                            candidate_record_ids=list(
                                outcome.candidate_record_ids
                            ),
                            source_value=item.fields.get("value_raw"),
                            edc_value=next(
                                (
                                    record.value_raw
                                    for record in snapshot.records
                                    if str(record.id) == outcome.edc_record_id
                                ),
                                None,
                            ),
                            source_unit=item.fields.get("unit_raw"),
                            edc_unit=next(
                                (
                                    record.unit_raw
                                    for record in snapshot.records
                                    if str(record.id) == outcome.edc_record_id
                                ),
                                None,
                            ),
                            unknowns=list(outcome.unknowns),
                            reason=outcome.reason,
                            field_results=[
                                {
                                    "field": result.field,
                                    "status": result.status,
                                    "source": result.source,
                                    "edc": result.edc,
                                    "detail": result.detail,
                                }
                                for result in outcome.field_results
                            ],
                            source_state=_effective_signature(item),
                        )
                    )
                comparison_id = comparison.id
                self._complete(record, comparison.id, comparison.revision)
        result = self.comparison_detail(scope, comparison_id)
        return ComparisonDetail(
            comparison=result.comparison,
            fields=result.fields,
            issue_links=result.issue_links,
            stale=result.stale,
            stale_field_ids=result.stale_field_ids,
            report_current_revision=result.report_current_revision,
            replayed=False,
        )

    def comparison_detail(
        self, scope: ScopeContext, comparison_id: uuid.UUID
    ) -> ComparisonDetail:
        with self.session_factory() as session:
            comparison = session.scalar(
                select(LabComparison).where(
                    LabComparison.id == comparison_id,
                    LabComparison.tenant_id == scope.tenant_id,
                )
            )
            if comparison is None:
                raise LaboratoryNotFound("laboratory comparison was not found")
            self._authorize_read(
                scope, comparison.study_id, comparison.site_id
            )
            fields = tuple(
                session.scalars(
                    select(LabComparisonField)
                    .where(
                        LabComparisonField.comparison_id == comparison.id
                    )
                    .order_by(LabComparisonField.ordinal)
                )
            )
            links = tuple(
                session.scalars(
                    select(LabComparisonIssueLink).where(
                        LabComparisonIssueLink.comparison_field_id.in_(
                            [field.id for field in fields] or [uuid.uuid4()]
                        )
                    )
                )
            )
            report = session.get(LabReportVersion, comparison.report_id)
            if report is None:
                raise LaboratoryNotFound("laboratory report was not found")
            observations = tuple(
                session.scalars(
                    select(LabObservation)
                    .where(LabObservation.report_id == report.id)
                    .order_by(LabObservation.ordinal)
                )
            )
            decisions = tuple(
                session.scalars(
                    select(LabObservationDecision)
                    .where(LabObservationDecision.tenant_id == scope.tenant_id)
                    .join(
                        LabObservation,
                        LabObservation.id
                        == LabObservationDecision.observation_id,
                    )
                    .where(LabObservation.report_id == report.id)
                    .order_by(
                        LabObservationDecision.created_at,
                        LabObservationDecision.id,
                    )
                )
            )
            latest = _latest_decisions(list(decisions))
            current = {
                observation.id: _effective_signature(
                    _effective_observation(
                        observation, latest.get(observation.id)
                    )
                )
                for observation in observations
            }
            stale_field_ids = frozenset(
                field.id
                for field in fields
                if current.get(field.observation_id) != field.source_state
            )
            return ComparisonDetail(
                comparison=comparison,
                fields=fields,
                issue_links=links,
                stale=bool(stale_field_ids),
                stale_field_ids=stale_field_ids,
                report_current_revision=report.revision,
            )

    def link_issues(
        self,
        scope: ScopeContext,
        comparison_id: uuid.UUID,
        command: LinkLabIssuesCommand,
    ) -> IssueLinkResult:
        comparison_detail = self.comparison_detail(scope, comparison_id)
        comparison = comparison_detail.comparison
        self._authorize_write(scope, comparison.study_id, comparison.site_id)
        requested_stale = set(command.field_ids) & {
            field.id for field in comparison_detail.fields
            if field.id in comparison_detail.stale_field_ids
        }
        if requested_stale:
            raise LaboratoryConflict(
                "selected laboratory source fields changed after this "
                "comparison; rerun comparison before linking issues"
            )
        report = self._load_report(scope, comparison.report_id)
        fields = {field.id: field for field in comparison_detail.fields}
        if any(field_id not in fields for field_id in command.field_ids):
            raise LaboratoryValidationError(
                "one or more comparison fields are outside this comparison"
            )
        field_ids = set(command.field_ids)
        existing_links = {
            link.comparison_field_id: link.issue_id
            for link in comparison_detail.issue_links
            if link.comparison_field_id in field_ids
        }
        links: list[tuple[uuid.UUID, uuid.UUID]] = []
        for field_id in command.field_ids:
            if field_id in existing_links:
                links.append((field_id, existing_links[field_id]))
                continue
            field = fields[field_id]
            if field.result_status == "agreement":
                raise LaboratoryValidationError(
                    "agreement fields do not create corrective issues"
                )
            subject_id = None
            if field.edc_record_id:
                with self.session_factory() as session:
                    edc_record = session.get(EDCLabRecord, field.edc_record_id)
                    if edc_record is not None:
                        subject_id = edc_record.subject_id
            issue = self.issues.create_issue(
                scope,
                comparison.study_id,
                CreateIssueCommand(
                    idempotency_key=f"laboratory-field-issue:{field.id}",
                    site_id=comparison.site_id,
                    subject_id=subject_id,
                    issue_number=None,
                    original_finding=(
                        f"检验核对候选：{field.matched_identity.get('subject_external_id')} "
                        f"{field.matched_identity.get('analyte')} "
                        f"{field.matched_identity.get('instance_type')}；"
                        f"源结果 {field.source_value or '未识别'} "
                        f"{field.source_unit or ''}，EDC 结果 "
                        f"{field.edc_value or '未录'} {field.edc_unit or ''}。"
                    ),
                    location=(
                        (field.matched_identity.get("source_ref") or {}).get(
                            "anchor"
                        )
                    ),
                    recommendation=(
                        "请核实源检验报告与本次 EDC 导出；本项是自动比较候选，"
                        "不是 PD 或医学安全结论。"
                    ),
                    recommendation_sources=[
                        {
                            "kind": "laboratory_comparison",
                            "comparison_id": str(comparison.id),
                            "field_id": str(field.id),
                            "reason": field.reason,
                        }
                    ],
                    source_kind="other",
                    source_document_version_id=report.source_document_version_id,
                    source_refs=[
                        {
                            "source_type": "laboratory_comparison_field",
                            "source_id": str(field.id),
                            "locator": field.matched_identity.get("anchor"),
                            "field_results": field.field_results,
                        }
                    ],
                    actions=[
                        ActionCreate(
                            kind="edc_correction",
                            requirement=(
                                "核实检验结果/单位/实例，并按确认结果处理 EDC "
                                "更正；不得自动判定 PD。"
                            ),
                            deadline_source_refs=[],
                        )
                    ],
                ),
            )
            with self.session_factory() as session:
                with session.begin():
                    inserted = session.scalar(
                        select(LabComparisonIssueLink).where(
                            LabComparisonIssueLink.comparison_field_id
                            == field.id
                        )
                    )
                    if inserted is None:
                        inserted = LabComparisonIssueLink(
                            id=uuid.uuid4(),
                            tenant_id=comparison.tenant_id,
                            study_id=comparison.study_id,
                            site_id=comparison.site_id,
                            comparison_field_id=field.id,
                            issue_id=issue.issue.id,
                            created_by=scope.actor_id,
                        )
                        session.add(inserted)
            links.append((field.id, issue.issue.id))
        return IssueLinkResult(
            comparison_id=comparison.id, links=tuple(links)
        )
