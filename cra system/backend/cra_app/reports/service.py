"""Authorized template mapping, drafts, immutable snapshots and file exports."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import DocumentVersion, SourceDocument
from cra_app.documents.service import DocumentNotFound, DocumentService
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.issues.models import Issue
from cra_app.issues.service import IssueService, aggregate_action_status
from cra_app.monitoring.service import MonitoringService
from cra_app.platform.jobs import digest_payload
from cra_app.reports.docx_export import render_docx
from cra_app.reports.models import (
    ReportDraft,
    ReportDraftHistory,
    ReportEvent,
    ReportExport,
    ReportSnapshot,
    ReportTemplateVersion,
)
from cra_app.reports.template_mapping import (
    DocxTemplateMapping,
    TemplateMappingSpec,
    XlsxTemplateMapping,
    render_xlsx,
)
from cra_app.rules.service import RuleService
from cra_app.safety.service import SafetyService
from cra_app.site_files.service import SiteFileService
from cra_app.subjects.service import SubjectService

DraftKind = Literal["letter", "report"]
SnapshotStatus = Literal["prepared", "issued"]
ReportEventType = Literal["sent", "submitted", "archived"]
USER_TEXT_KEYS = ("summary", "coverage_scope", "conclusion")


class ReportContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CreateTemplateVersionCommand(ReportContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    source_document_version_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    mapping: TemplateMappingSpec


class CreateDraftCommand(ReportContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    monitoring_visit_id: uuid.UUID
    template_version_id: uuid.UUID
    title: str | None = Field(default=None, max_length=255)
    selected_issue_ids: list[uuid.UUID] = Field(
        default_factory=list, max_length=500
    )

    @model_validator(mode="after")
    def validate_selected(self) -> "CreateDraftCommand":
        if len(self.selected_issue_ids) != len(set(self.selected_issue_ids)):
            raise ValueError("selected_issue_ids must be unique")
        return self


class UpdateDraftTextCommand(ReportContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    text_updates: dict[str, str] = Field(min_length=1, max_length=10)
    status: Literal["draft", "ready"] | None = None

    @model_validator(mode="after")
    def validate_text(self) -> "UpdateDraftTextCommand":
        unsupported = set(self.text_updates) - set(USER_TEXT_KEYS)
        if unsupported:
            raise ValueError(
                "unsupported user text fields: "
                + ", ".join(sorted(unsupported))
            )
        if any(len(value) > 10000 for value in self.text_updates.values()):
            raise ValueError("user text cannot exceed 10000 characters")
        return self


class CreateSnapshotCommand(ReportContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    status: SnapshotStatus
    acknowledge_unknowns: bool = False
    user_statement: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_issue_statement(self) -> "CreateSnapshotCommand":
        if self.status == "issued" and not (
            self.user_statement and self.user_statement.strip()
        ):
            raise ValueError(
                "issued snapshot requires the user's actual issuance statement"
            )
        return self


class CreateExportCommand(ReportContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    snapshot_id: uuid.UUID
    template_version_id: uuid.UUID


class RecordReportEventCommand(ReportContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    event_type: ReportEventType
    user_statement: str = Field(min_length=1, max_length=4000)


@dataclass(frozen=True)
class TemplateVersionDetail:
    template: ReportTemplateVersion


@dataclass(frozen=True)
class DraftDetail:
    draft: ReportDraft
    history: tuple[ReportDraftHistory, ...]


@dataclass(frozen=True)
class SnapshotDetail:
    snapshot: ReportSnapshot
    exports: tuple[ReportExport, ...]
    events: tuple[ReportEvent, ...]


@dataclass(frozen=True)
class ExportDetail:
    export: ReportExport


class ReportError(Exception):
    pass


class ReportNotFound(ReportError):
    pass


class ReportValidationError(ReportError):
    pass


class ReportConflict(ReportError):
    pass


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _source_text(source_refs: list[dict[str, Any]]) -> str:
    values = []
    for source in source_refs:
        value = (
            source.get("locator")
            or source.get("source_original_key")
            or source.get("source_type")
        )
        if value:
            values.append(str(value))
    return "；".join(values) if values else "来源位置unknown"


class ReportService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService | None = None,
        documents: DocumentService,
        issues: IssueService,
        monitoring: MonitoringService,
        subjects: SubjectService,
        rules: RuleService,
        safety: SafetyService,
        site_files: SiteFileService,
    ):
        self.session_factory = session_factory
        self.governance = governance or GovernanceService(session_factory)
        self.documents = documents
        self.issues = issues
        self.monitoring = monitoring
        self.subjects = subjects
        self.rules = rules
        self.safety = safety
        self.site_files = site_files

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
        command: BaseModel,
        request_payload: dict[str, Any] | None = None,
    ) -> tuple[IdempotencyRecord, bool]:
        fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": fingerprint,
                "command": command.model_dump(mode="json"),
                "request": request_payload or {},
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
                IdempotencyRecord.scope_fingerprint == fingerprint,
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
    def _complete(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    @staticmethod
    def _audit(
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
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
                study_id=study_id,
                site_id=site_id,
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
    def _next_draft_history_ordinal(
        session: Session, draft_id: uuid.UUID
    ) -> int:
        current = session.scalar(
            select(func.max(ReportDraftHistory.ordinal)).where(
                ReportDraftHistory.draft_id == draft_id
            )
        )
        return (current or 0) + 1

    def _load_template(
        self, session: Session, scope: ScopeContext, template_id: uuid.UUID
    ) -> ReportTemplateVersion:
        template = session.scalar(
            select(ReportTemplateVersion).where(
                ReportTemplateVersion.id == template_id,
                ReportTemplateVersion.tenant_id == scope.tenant_id,
            )
        )
        if template is None:
            raise ReportNotFound("template version was not found")
        return template

    def _load_draft(
        self, session: Session, scope: ScopeContext, draft_id: uuid.UUID
    ) -> ReportDraft:
        draft = session.scalar(
            select(ReportDraft).where(
                ReportDraft.id == draft_id,
                ReportDraft.tenant_id == scope.tenant_id,
            )
        )
        if draft is None:
            raise ReportNotFound("report draft was not found")
        return draft

    def _load_snapshot(
        self, session: Session, scope: ScopeContext, snapshot_id: uuid.UUID
    ) -> ReportSnapshot:
        snapshot = session.scalar(
            select(ReportSnapshot).where(
                ReportSnapshot.id == snapshot_id,
                ReportSnapshot.tenant_id == scope.tenant_id,
            )
        )
        if snapshot is None:
            raise ReportNotFound("report snapshot was not found")
        return snapshot

    @staticmethod
    def _template_detail(
        template: ReportTemplateVersion,
    ) -> TemplateVersionDetail:
        return TemplateVersionDetail(template=template)

    def _draft_detail_in_session(
        self, session: Session, draft: ReportDraft
    ) -> DraftDetail:
        history = tuple(
            session.scalars(
                select(ReportDraftHistory)
                .where(
                    ReportDraftHistory.tenant_id == draft.tenant_id,
                    ReportDraftHistory.study_id == draft.study_id,
                    ReportDraftHistory.draft_id == draft.id,
                )
                .order_by(ReportDraftHistory.ordinal)
            )
        )
        return DraftDetail(draft=draft, history=history)

    def _snapshot_detail_in_session(
        self, session: Session, snapshot: ReportSnapshot
    ) -> SnapshotDetail:
        exports = tuple(
            session.scalars(
                select(ReportExport)
                .where(
                    ReportExport.tenant_id == snapshot.tenant_id,
                    ReportExport.study_id == snapshot.study_id,
                    ReportExport.snapshot_id == snapshot.id,
                )
                .order_by(ReportExport.created_at)
            )
        )
        events = tuple(
            session.scalars(
                select(ReportEvent)
                .where(
                    ReportEvent.tenant_id == snapshot.tenant_id,
                    ReportEvent.study_id == snapshot.study_id,
                    ReportEvent.snapshot_id == snapshot.id,
                )
                .order_by(ReportEvent.occurred_at)
            )
        )
        return SnapshotDetail(
            snapshot=snapshot, exports=exports, events=events
        )

    @staticmethod
    def _mapping(
        template: ReportTemplateVersion,
    ) -> TemplateMappingSpec:
        return TemplateMappingSpec.model_validate(template.mapping_json)

    def create_template_version(
        self, scope: ScopeContext, command: CreateTemplateVersionCommand
    ) -> TemplateVersionDetail:
        stored = self.documents.read_content(
            scope, command.source_document_version_id
        )
        with self.session_factory() as session:
            document = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.id == stored.version.document_id,
                    SourceDocument.tenant_id == scope.tenant_id,
                    SourceDocument.study_id == stored.version.study_id,
                )
            )
            if document is None:
                raise ReportValidationError("template document was not found")
            if (
                document.purpose != "template"
                or document.document_type != "template"
            ):
                raise ReportValidationError(
                    "template version requires an M02 template-purpose file"
                )
            if document.site_id is None:
                raise ReportValidationError(
                    "report templates must belong to a site"
                )
            study_id, site_id = document.study_id, document.site_id
        self.governance.authorize(scope, "write_site", study_id, site_id)
        try:
            if command.mapping.docx is not None:
                if stored.media_type != (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ):
                    raise ReportValidationError(
                        "DOCX mapping requires a DOCX template"
                    )
                from cra_app.reports.template_mapping import (
                    validate_docx_template,
                )

                validate_docx_template(
                    stored.content, command.mapping.docx
                )
            if command.mapping.xlsx is not None:
                if stored.media_type != (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ):
                    raise ReportValidationError(
                        "XLSX mapping requires an XLSX template"
                    )
                from cra_app.reports.template_mapping import (
                    validate_xlsx_template,
                )

                validate_xlsx_template(
                    stored.content, command.mapping.xlsx
                )
        except ValueError as exc:
            raise ReportValidationError(str(exc)) from exc
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=site_id,
                    command_name="reports.template.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    template = self._load_template(
                        session, scope, record.response_resource_id
                    )
                else:
                    duplicate = session.scalar(
                        select(ReportTemplateVersion.id).where(
                            ReportTemplateVersion.tenant_id
                            == scope.tenant_id,
                            ReportTemplateVersion.study_id == study_id,
                            ReportTemplateVersion.source_document_version_id
                            == command.source_document_version_id,
                            ReportTemplateVersion.output_kind
                            == command.mapping.output_kind,
                        )
                    )
                    if duplicate is not None:
                        raise ReportConflict(
                            "this source version already has the same "
                            "template output mapping"
                        )
                    template = ReportTemplateVersion(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=site_id,
                        source_document_version_id=(
                            command.source_document_version_id
                        ),
                        title=command.title,
                        output_kind=command.mapping.output_kind,
                        output_format=command.mapping.output_format,
                        mapping_json=command.mapping.model_dump(mode="json"),
                        supported_fields=command.mapping.supported_fields(),
                        required_variables=command.mapping.required_variables(),
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(template)
                    session.flush()
                    self._audit(
                        session,
                        scope=scope,
                        study_id=study_id,
                        site_id=site_id,
                        action="reports.template.create",
                        resource_type="report_template_version",
                        resource_id=template.id,
                        revision_before=None,
                        revision_after=template.revision,
                        after_state={
                            "output_kind": template.output_kind,
                            "output_format": template.output_format,
                            "source_document_version_id": str(
                                template.source_document_version_id
                            ),
                        },
                        command_name="reports.template.create",
                        correlation_id=record.id,
                    )
                    self._complete(record, template.id, template.revision)
            return self._template_detail(template)

    def template_version(
        self, scope: ScopeContext, template_id: uuid.UUID
    ) -> TemplateVersionDetail:
        with self.session_factory() as session:
            template = self._load_template(session, scope, template_id)
            self.governance.authorize(
                scope, "read_site", template.study_id, template.site_id
            )
            return self._template_detail(template)

    def list_template_versions(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[TemplateVersionDetail]:
        self.governance.authorize(scope, "read_site", study_id, site_id)
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(ReportTemplateVersion)
                    .where(
                        ReportTemplateVersion.tenant_id == scope.tenant_id,
                        ReportTemplateVersion.study_id == study_id,
                        ReportTemplateVersion.site_id == site_id,
                    )
                    .order_by(
                        ReportTemplateVersion.output_kind,
                        ReportTemplateVersion.created_at,
                    )
                )
            )
            return [self._template_detail(row) for row in rows]

    def _issue_context(
        self, issue_detail: Any, section: str
    ) -> dict[str, Any]:
        issue = issue_detail.issue
        actions = issue_detail.actions
        next_steps = [
            action.requirement or f"继续跟进行动 {action.action_key}"
            for action in actions
            if action.status not in {"completed", "reported_done"}
        ]
        return {
            "id": str(issue.id),
            "issue_number": issue.issue_number,
            "section": section,
            "original_finding": issue.original_finding or "unknown",
            "location": issue.location or "unknown",
            "recommendation": issue.recommendation or "unknown",
            "known_progress": issue.known_progress or "unknown",
            "status": aggregate_action_status(actions),
            "revision": issue.revision,
            "next_steps_text": "；".join(next_steps) or "无已记录后续行动",
            "source_refs_text": _source_text(issue.source_refs),
            "source_refs": issue.source_refs,
        }

    def _compose_context(
        self,
        scope: ScopeContext,
        *,
        visit_id: uuid.UUID,
        output_kind: DraftKind,
        selected_issue_ids: list[uuid.UUID],
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        workbench = self.monitoring.workbench(scope, visit_id)
        visit = workbench.visit
        study = self.governance.get_study(scope, visit.study_id)
        site = self.governance.get_site(
            scope, visit.study_id, visit.site_id
        )
        issue_details = self.issues.list_issues(
            scope, visit.study_id, visit.site_id
        )
        issue_by_id = {item.issue.id: item for item in issue_details}
        if selected_issue_ids:
            missing = set(selected_issue_ids) - set(issue_by_id)
            if missing:
                raise ReportValidationError(
                    "one or more selected issues are outside this site"
                )
            letter_ids = list(selected_issue_ids)
        else:
            letter_ids = list(workbench.selected_issue_ids)
        if output_kind == "letter" and not letter_ids:
            raise ReportValidationError(
                "a letter requires at least one selected prior issue"
            )
        prior, current = [], []
        for detail in issue_details:
            section = (
                "prior_issue"
                if detail.issue.created_at < visit.created_at
                else "current_finding"
            )
            target = prior if section == "prior_issue" else current
            target.append(self._issue_context(detail, section))
        letter_issues = [
            self._issue_context(issue_by_id[issue_id], "letter_selection")
            for issue_id in letter_ids
        ]

        subjects = self.subjects.list_subjects(
            scope, visit.study_id, visit.site_id
        )
        coverage_records: list[dict[str, Any]] = []
        facts: list[dict[str, Any]] = []
        safety_assessments: list[dict[str, Any]] = []
        not_checked: list[dict[str, Any]] = []
        unknowns: list[dict[str, Any]] = []
        coverage_refs = []
        fact_refs = []
        assessment_refs = []
        for summary in subjects:
            label = summary.subject.deidentified_label
            for coverage in self.subjects.list_coverage(
                scope, summary.subject.id
            ):
                record = {
                    "coverage_id": str(coverage.id),
                    "subject_label": label,
                    "category": coverage.category,
                    "scope_key": coverage.scope_key,
                    "status": coverage.status,
                    "checked_through": coverage.checked_through or "unknown",
                    "unverified_scope": coverage.unverified_scope,
                    "unverified_scope_text": (
                        "；".join(coverage.unverified_scope)
                        if coverage.unverified_scope
                        else "未记录"
                    ),
                    "normal_scope_note": (
                        coverage.normal_scope_note or "未记录"
                    ),
                    "revision": coverage.revision,
                }
                coverage_records.append(record)
                coverage_refs.append(
                    {
                        "coverage_id": str(coverage.id),
                        "revision": coverage.revision,
                    }
                )
                if (
                    coverage.status == "not_checked"
                    or coverage.unverified_scope
                ):
                    not_checked.append(
                        {
                            "subject_label": label,
                            "category": coverage.category,
                            "scope_key": coverage.scope_key,
                            "unverified_scope": coverage.unverified_scope,
                        }
                    )
            timeline = self.subjects.timeline(scope, summary.subject.id)
            for item in timeline:
                if not item.is_current:
                    continue
                fact = item.fact
                facts.append(
                    {
                        "subject_label": label,
                        "fact_key": fact.fact_key,
                        "repeat_instance": fact.repeat_instance,
                        "value_raw": fact.value_raw,
                        "unit": fact.unit,
                        "precision": fact.precision,
                        "verification_status": fact.verification_status,
                    }
                )
                fact_refs.append(
                    {
                        "fact_id": str(fact.id),
                        "revision": fact.revision,
                    }
                )
            decisions = self.subjects.list_check_decisions(
                scope, summary.subject.id
            )
            for decision in decisions:
                if decision.state != "active":
                    continue
                not_checked.append(
                    {
                        "subject_label": label,
                        "category": decision.category,
                        "check_type": decision.check_type,
                        "reason": decision.reason,
                        "missing_keys": decision.missing_keys,
                        "affected_paths": decision.affected_paths,
                    }
                )
            for assessment in self.safety.list_assessments(
                scope, visit.study_id, visit.site_id, summary.subject.id
            ):
                record = {
                    "id": str(assessment.id),
                    "subject_label": label,
                    "event_type": assessment.event_type,
                    "event_date": assessment.event_date.isoformat(),
                    "status": assessment.status,
                    "questions_text": "；".join(
                        str(item.get("question", item))
                        for item in assessment.questions
                    )
                    or "无已记录问题",
                    "unknowns_text": "；".join(
                        str(item.get("summary", item))
                        for item in assessment.unknowns
                    )
                    or "无已记录unknown",
                }
                safety_assessments.append(record)
                assessment_refs.append(
                    {"assessment_id": str(assessment.id)}
                )
                for item in assessment.unknowns:
                    unknowns.append(
                        {
                            "source": "safety_assessment",
                            "assessment_id": str(assessment.id),
                            "detail": item,
                        }
                    )
        rule_refs = []
        rule_context = []
        for item in self.rules.list_rules(
            scope, visit.study_id, visit.site_id
        ):
            if item.current_version is None:
                continue
            rule_context.append(
                {
                    "rule_key": item.rule.rule_key,
                    "summary": item.current_version.summary,
                    "version_id": str(item.current_version.id),
                    "version_no": item.current_version.version_no,
                }
            )
            rule_refs.append(
                {
                    "rule_version_id": str(item.current_version.id),
                    "version_no": item.current_version.version_no,
                }
            )
        directory_refs = self.site_files.site_file_status(
            scope, visit.study_id, visit.site_id
        )
        directory_summary = [
            {
                "reference_id": str(item.reference.id),
                "directory_kind": item.reference.directory_kind,
                "mode": item.reference.mode,
                "missing_item_keys": [
                    file.item_key
                    for file in item.items
                    if file.applicability_status == "required"
                    and file.acquisition_status != "provided"
                ],
            }
            for item in directory_refs
        ]
        for item in directory_summary:
            if item["missing_item_keys"]:
                unknowns.append(
                    {
                        "source": "directory",
                        "reference_id": item["reference_id"],
                        "missing_item_keys": item["missing_item_keys"],
                    }
                )
        action_scope_ids = (
            set(letter_ids)
            if output_kind == "letter"
            else {detail.issue.id for detail in issue_details}
        )
        next_steps = [
            {
                "issue_number": detail.issue.issue_number,
                "action_key": action.action_key,
                "kind": action.kind,
                "status": action.status,
                "requirement": (
                    action.requirement
                    or f"继续跟进行动 {action.action_key}"
                ),
            }
            for detail in issue_details
            for action in detail.actions
            if detail.issue.id in action_scope_ids
            if action.status not in {"completed", "reported_done"}
        ]
        coverage_summary = (
            f"已记录{len(coverage_records)}项核查覆盖；"
            f"未核查/未覆盖{len(not_checked)}项。"
            "本报告不据此声明全中心所有数据无异常。"
        )
        not_checked_summary = (
            "；".join(
                f"{item.get('subject_label', '')} "
                f"{item.get('category', '')}: "
                f"{item.get('unverified_scope', item.get('missing_keys', []))}"
                for item in not_checked
            )
            or "未记录明确跳过或未核查范围；仍不代表全中心无异常。"
        )
        unknown_summary = (
            "；".join(
                str(item.get("summary", item.get("detail", item)))
                for item in unknowns
            )
            or "未记录unknown项；报告范围仍以覆盖记录为限。"
        )
        next_steps_summary = (
            "；".join(
                f"{item['issue_number']} {item['action_key']}: "
                f"{item['requirement']}"
                for item in next_steps
            )
            or "未记录未完成后续行动。"
        )
        track_rows = [
            {
                **issue,
                "next_steps_text": issue["next_steps_text"],
            }
            for issue in prior + current
        ]
        context = {
            "title": (
                "访视信"
                if output_kind == "letter"
                else "监查报告"
            ),
            "study_code": study.code,
            "site_code": site.code,
            "site_name": site.name,
            "visit_title": visit.title,
            "visit_stage": visit.stage,
            "visit_scope_note": visit.scope_note or "未记录本次范围",
            "generated_on": date.today().isoformat(),
            "prior_issue_count": str(len(prior)),
            "current_finding_count": str(len(current)),
            "selected_issue_count": str(len(letter_issues)),
            "coverage_summary": coverage_summary,
            "unknown_summary": unknown_summary,
            "not_checked_summary": not_checked_summary,
            "next_steps_summary": next_steps_summary,
            "user_summary": "",
            "user_conclusion": "",
            "letter_issues": letter_issues,
            "prior_issues": prior,
            "current_findings": current,
            "coverage_records": coverage_records,
            "facts": facts,
            "rules": rule_context,
            "safety_assessments": safety_assessments,
            "directory_summary": directory_summary,
            "next_steps": next_steps,
            "track_rows": track_rows,
            "scope_notice": (
                "报告仅覆盖已记录范围；未核查、跳过和unknown项不作为正常。"
            ),
        }
        input_refs = {
            "monitoring_visit": {
                "id": str(visit.id),
                "revision": visit.revision,
            },
            "issues": [
                {
                    "id": str(detail.issue.id),
                    "revision": detail.issue.revision,
                }
                for detail in issue_details
            ],
            "coverage": coverage_refs,
            "facts": fact_refs,
            "rules": rule_refs,
            "safety_assessments": assessment_refs,
            "directory_references": [
                {
                    "id": str(item.reference.id),
                    "revision": item.reference.revision,
                }
                for item in directory_refs
            ],
            "selected_issue_ids": [str(item) for item in letter_ids],
        }
        return context, input_refs, unknowns, not_checked

    def _missing_required(
        self,
        template: ReportTemplateVersion,
        context: dict[str, Any],
    ) -> list[str]:
        mapping = self._mapping(template)
        missing: list[str] = []
        if mapping.docx is not None:
            for variable in mapping.docx.required_variables:
                source = mapping.docx.fields[variable]
                value = context.get(source)
                if value is None or value == "":
                    missing.append(variable)
        if mapping.xlsx is not None:
            for coordinate in mapping.xlsx.required_variables:
                source_path = mapping.xlsx.cells[coordinate]
                value = context.get(source_path)
                if value is None or value == "":
                    missing.append(coordinate)
        return missing

    def create_draft(
        self,
        scope: ScopeContext,
        command: CreateDraftCommand,
        *,
        output_kind: DraftKind,
    ) -> DraftDetail:
        workbench = self.monitoring.workbench(
            scope, command.monitoring_visit_id
        )
        visit = workbench.visit
        self.governance.authorize(
            scope, "write_site", visit.study_id, visit.site_id
        )
        with self.session_factory() as session:
            template = self._load_template(
                session, scope, command.template_version_id
            )
            if (
                template.study_id != visit.study_id
                or template.site_id != visit.site_id
            ):
                raise ReportValidationError(
                    "template belongs to another site"
                )
            if template.output_kind != output_kind:
                raise ReportValidationError(
                    f"{output_kind} draft requires a {output_kind} template"
                )
        context, input_refs, unknowns, not_checked = self._compose_context(
            scope,
            visit_id=command.monitoring_visit_id,
            output_kind=output_kind,
            selected_issue_ids=command.selected_issue_ids,
        )
        missing_fields = self._missing_required(template, context)
        title = command.title or (
            f"{visit.title}访视信"
            if output_kind == "letter"
            else f"{visit.title}监查报告"
        )
        context["title"] = title
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=visit.study_id,
                    site_id=visit.site_id,
                    command_name=f"reports.{output_kind}.draft",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    draft = self._load_draft(
                        session, scope, record.response_resource_id
                    )
                else:
                    draft = ReportDraft(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=visit.study_id,
                        site_id=visit.site_id,
                        monitoring_visit_id=visit.id,
                        template_version_id=template.id,
                        output_kind=output_kind,
                        title=title,
                        content_json=context,
                        input_refs=input_refs,
                        unknowns=unknowns,
                        not_checked=not_checked,
                        missing_fields=missing_fields,
                        user_text={},
                        status="draft",
                        revision=1,
                        generated_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(draft)
                    session.flush()
                    session.add(
                        ReportDraftHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=visit.study_id,
                            site_id=visit.site_id,
                            draft_id=draft.id,
                            event_type="generated",
                            actor_id=scope.actor_id,
                            ordinal=1,
                            details={
                                "output_kind": output_kind,
                                "template_version_id": str(template.id),
                                "missing_fields": missing_fields,
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=visit.study_id,
                        site_id=visit.site_id,
                        action=f"reports.{output_kind}.draft",
                        resource_type="report_draft",
                        resource_id=draft.id,
                        revision_before=None,
                        revision_after=draft.revision,
                        after_state={
                            "output_kind": output_kind,
                            "missing_fields": missing_fields,
                            "send_status": "not_sent",
                        },
                        command_name=f"reports.{output_kind}.draft",
                        correlation_id=record.id,
                    )
                    self._complete(record, draft.id, draft.revision)
            return self._draft_detail_in_session(session, draft)

    def draft(self, scope: ScopeContext, draft_id: uuid.UUID) -> DraftDetail:
        with self.session_factory() as session:
            draft = self._load_draft(session, scope, draft_id)
            self.governance.authorize(
                scope, "read_site", draft.study_id, draft.site_id
            )
            return self._draft_detail_in_session(session, draft)

    def list_drafts(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[DraftDetail]:
        self.governance.authorize(scope, "read_site", study_id, site_id)
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(ReportDraft)
                    .where(
                        ReportDraft.tenant_id == scope.tenant_id,
                        ReportDraft.study_id == study_id,
                        ReportDraft.site_id == site_id,
                    )
                    .order_by(ReportDraft.generated_at.desc())
                )
            )
            return [self._draft_detail_in_session(session, row) for row in rows]

    def update_text(
        self,
        scope: ScopeContext,
        draft_id: uuid.UUID,
        command: UpdateDraftTextCommand,
    ) -> DraftDetail:
        draft = self._load_draft_for_scope(scope, draft_id)
        self.governance.authorize(
            scope, "write_site", draft.study_id, draft.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                draft = session.scalar(
                    select(ReportDraft)
                    .where(
                        ReportDraft.id == draft_id,
                        ReportDraft.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if draft is None:
                    raise ReportNotFound("report draft was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=draft.study_id,
                    site_id=draft.site_id,
                    command_name="reports.draft.update_text",
                    command=command,
                    request_payload={"draft_id": str(draft.id)},
                )
                if not replayed:
                    if draft.revision != command.expected_revision:
                        raise RevisionConflict(draft.revision)
                    template = self._load_template(
                        session, scope, draft.template_version_id
                    )
                    user_text = dict(draft.user_text)
                    user_text.update(command.text_updates)
                    draft.user_text = user_text
                    recalculated = dict(draft.content_json)
                    recalculated["user_summary"] = user_text.get(
                        "summary", ""
                    )
                    recalculated["coverage_scope"] = user_text.get(
                        "coverage_scope", ""
                    )
                    recalculated["user_conclusion"] = user_text.get(
                        "conclusion", ""
                    )
                    draft.missing_fields = self._missing_required(
                        template, recalculated
                    )
                    draft.status = command.status or draft.status
                    draft.updated_by = scope.actor_id
                    draft.updated_at = datetime.now(UTC)
                    draft.revision += 1
                    event_type = (
                        "marked_ready"
                        if command.status == "ready"
                        else "text_updated"
                    )
                    session.add(
                        ReportDraftHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=draft.study_id,
                            site_id=draft.site_id,
                            draft_id=draft.id,
                            event_type=event_type,
                            actor_id=scope.actor_id,
                            ordinal=self._next_draft_history_ordinal(
                                session, draft.id
                            ),
                            details={
                                "changed_text_keys": sorted(
                                    command.text_updates
                                ),
                                "status": draft.status,
                                "facts_modified": False,
                                "missing_fields": draft.missing_fields,
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=draft.study_id,
                        site_id=draft.site_id,
                        action="reports.draft.update_text",
                        resource_type="report_draft",
                        resource_id=draft.id,
                        revision_before=command.expected_revision,
                        revision_after=draft.revision,
                        after_state={
                            "changed_text_keys": sorted(
                                command.text_updates
                            ),
                            "status": draft.status,
                            "facts_modified": False,
                            "missing_fields": draft.missing_fields,
                        },
                        command_name="reports.draft.update_text",
                        correlation_id=record.id,
                    )
                    self._complete(record, draft.id, draft.revision)
            return self._draft_detail_in_session(session, draft)

    def _load_draft_for_scope(
        self, scope: ScopeContext, draft_id: uuid.UUID
    ) -> ReportDraft:
        with self.session_factory() as session:
            draft = self._load_draft(session, scope, draft_id)
            self.governance.authorize(
                scope, "read_site", draft.study_id, draft.site_id
            )
            return draft

    def create_snapshot(
        self,
        scope: ScopeContext,
        draft_id: uuid.UUID,
        command: CreateSnapshotCommand,
    ) -> SnapshotDetail:
        draft = self._load_draft_for_scope(scope, draft_id)
        self.governance.authorize(
            scope, "write_site", draft.study_id, draft.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                draft = session.scalar(
                    select(ReportDraft)
                    .where(
                        ReportDraft.id == draft_id,
                        ReportDraft.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if draft is None:
                    raise ReportNotFound("report draft was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=draft.study_id,
                    site_id=draft.site_id,
                    command_name="reports.snapshot.create",
                    command=command,
                    request_payload={"draft_id": str(draft.id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    snapshot = self._load_snapshot(
                        session, scope, record.response_resource_id
                    )
                else:
                    if draft.revision != command.expected_revision:
                        raise RevisionConflict(draft.revision)
                    significant_unknowns = bool(
                        draft.missing_fields
                        or draft.unknowns
                        or draft.not_checked
                    )
                    if (
                        command.status == "issued"
                        and significant_unknowns
                        and not command.acknowledge_unknowns
                    ):
                        raise ReportValidationError(
                            "issued report with missing/unknown/not-checked "
                            "scope requires explicit unknown acknowledgement"
                        )
                    content = dict(draft.content_json)
                    content["user_summary"] = draft.user_text.get(
                        "summary", ""
                    )
                    content["coverage_scope"] = draft.user_text.get(
                        "coverage_scope", ""
                    )
                    content["user_conclusion"] = draft.user_text.get(
                        "conclusion", ""
                    )
                    content["user_text"] = dict(draft.user_text)
                    issued_at = (
                        datetime.now(UTC)
                        if command.status == "issued"
                        else None
                    )
                    snapshot_number = (
                        session.scalar(
                            select(
                                func.max(ReportSnapshot.snapshot_number)
                            ).where(
                                ReportSnapshot.draft_id == draft.id
                            )
                        )
                        or 0
                    ) + 1
                    snapshot = ReportSnapshot(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=draft.study_id,
                        site_id=draft.site_id,
                        draft_id=draft.id,
                        draft_revision=draft.revision,
                        template_version_id=draft.template_version_id,
                        snapshot_number=snapshot_number,
                        status=command.status,
                        content_json=content,
                        input_refs=draft.input_refs,
                        content_hash=_canonical_hash(content),
                        missing_fields=draft.missing_fields,
                        unknown_acknowledged=significant_unknowns,
                        issued_by=(
                            scope.actor_id
                            if command.status == "issued"
                            else None
                        ),
                        issued_at=issued_at,
                        user_statement=command.user_statement,
                        created_by=scope.actor_id,
                    )
                    session.add(snapshot)
                    session.flush()
                    self._audit(
                        session,
                        scope=scope,
                        study_id=draft.study_id,
                        site_id=draft.site_id,
                        action="reports.snapshot.create",
                        resource_type="report_snapshot",
                        resource_id=snapshot.id,
                        revision_before=None,
                        revision_after=snapshot.snapshot_number,
                        after_state={
                            "draft_id": str(draft.id),
                            "draft_revision": draft.revision,
                            "status": snapshot.status,
                            "content_hash": snapshot.content_hash,
                            "unknown_acknowledged": (
                                snapshot.unknown_acknowledged
                            ),
                        },
                        command_name="reports.snapshot.create",
                        correlation_id=record.id,
                    )
                    self._complete(
                        record, snapshot.id, snapshot.snapshot_number
                    )
            return self._snapshot_detail_in_session(session, snapshot)

    def snapshot(
        self, scope: ScopeContext, snapshot_id: uuid.UUID
    ) -> SnapshotDetail:
        with self.session_factory() as session:
            snapshot = self._load_snapshot(
                session, scope, snapshot_id
            )
            self.governance.authorize(
                scope, "read_site", snapshot.study_id, snapshot.site_id
            )
            return self._snapshot_detail_in_session(session, snapshot)

    def list_snapshots(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[ReportSnapshot]:
        self.governance.authorize(scope, "read_site", study_id, site_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(ReportSnapshot)
                    .where(
                        ReportSnapshot.tenant_id == scope.tenant_id,
                        ReportSnapshot.study_id == study_id,
                        ReportSnapshot.site_id == site_id,
                    )
                    .order_by(
                        ReportSnapshot.created_at.desc(),
                        ReportSnapshot.id,
                    )
                )
            )

    @staticmethod
    def _safe_filename(value: str, extension: str) -> str:
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
        return (stem or "cra-report") + "." + extension

    def create_export(
        self, scope: ScopeContext, command: CreateExportCommand
    ) -> ExportDetail:
        with self.session_factory() as session:
            snapshot = self._load_snapshot(
                session, scope, command.snapshot_id
            )
            draft = self._load_draft(session, scope, snapshot.draft_id)
            template = self._load_template(
                session, scope, command.template_version_id
            )
            if (
                template.study_id != snapshot.study_id
                or template.site_id != snapshot.site_id
            ):
                raise ReportValidationError(
                    "export template belongs to another site"
                )
            if (
                template.output_kind != "track"
                and template.output_kind != draft.output_kind
            ):
                raise ReportValidationError(
                    "export template output kind does not match draft"
                )
        self.governance.authorize(
            scope, "write_site", snapshot.study_id, snapshot.site_id
        )
        stored = self.documents.read_content(
            scope, template.source_document_version_id
        )
        mapping = self._mapping(template)
        if mapping.docx is not None:
            content, missing = render_docx(
                stored.content, mapping.docx, snapshot.content_json
            )
            row_refs: list[dict[str, Any]] = []
            media_type = (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            )
        else:
            assert mapping.xlsx is not None
            content, missing, row_refs = render_xlsx(
                stored.content, mapping.xlsx, snapshot.content_json
            )
            media_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        if any(name not in snapshot.missing_fields for name in missing):
            raise ReportValidationError(
                "export uncovered undeclared missing template fields: "
                + ", ".join(missing)
            )
        export_id = uuid.uuid4()
        filename = self._safe_filename(
            f"{draft.title}-snapshot-{snapshot.snapshot_number}",
            template.output_format,
        )
        storage_key = (
            f"{scope.tenant_id}/{snapshot.study_id}/{snapshot.site_id}/"
            f"reports/{snapshot.id}/{export_id}.{template.output_format}"
        )
        self.documents.storage.put(storage_key, content, media_type)
        digest = hashlib.sha256(content).hexdigest()
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=snapshot.study_id,
                    site_id=snapshot.site_id,
                    command_name="reports.export.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    export = session.get(
                        ReportExport, record.response_resource_id
                    )
                    if export is None:
                        raise ReportNotFound("replayed export was not found")
                else:
                    export = ReportExport(
                        id=export_id,
                        tenant_id=scope.tenant_id,
                        study_id=snapshot.study_id,
                        site_id=snapshot.site_id,
                        snapshot_id=snapshot.id,
                        template_version_id=template.id,
                        output_format=template.output_format,
                        filename=filename,
                        storage_key=storage_key,
                        sha256=digest,
                        size_bytes=len(content),
                        row_refs=row_refs,
                        generated_by=scope.actor_id,
                    )
                    session.add(export)
                    session.flush()
                    self._audit(
                        session,
                        scope=scope,
                        study_id=snapshot.study_id,
                        site_id=snapshot.site_id,
                        action="reports.export.create",
                        resource_type="report_export",
                        resource_id=export.id,
                        revision_before=None,
                        revision_after=1,
                        after_state={
                            "snapshot_id": str(snapshot.id),
                            "format": export.output_format,
                            "sha256": export.sha256,
                            "actual_send_status": "not_sent",
                        },
                        command_name="reports.export.create",
                        correlation_id=record.id,
                    )
                    self._complete(record, export.id, 1)
            return ExportDetail(export=export)

    def export(
        self, scope: ScopeContext, export_id: uuid.UUID
    ) -> ExportDetail:
        with self.session_factory() as session:
            export = session.scalar(
                select(ReportExport).where(
                    ReportExport.id == export_id,
                    ReportExport.tenant_id == scope.tenant_id,
                )
            )
            if export is None:
                raise ReportNotFound("report export was not found")
            self.governance.authorize(
                scope, "read_site", export.study_id, export.site_id
            )
            return ExportDetail(export=export)

    def export_content(
        self, scope: ScopeContext, export_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        detail = self.export(scope, export_id)
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            + (
                "wordprocessingml.document"
                if detail.export.output_format == "docx"
                else "spreadsheetml.sheet"
            )
        )
        return (
            self.documents.storage.read(detail.export.storage_key),
            media_type,
            detail.export.filename,
        )

    def record_event(
        self,
        scope: ScopeContext,
        snapshot_id: uuid.UUID,
        command: RecordReportEventCommand,
    ) -> SnapshotDetail:
        snapshot = self.snapshot(scope, snapshot_id).snapshot
        self.governance.authorize(
            scope, "write_site", snapshot.study_id, snapshot.site_id
        )
        if command.event_type in {"sent", "submitted"} and (
            snapshot.status != "issued"
        ):
            raise ReportValidationError(
                "sent/submitted events require an issued snapshot"
            )
        with self.session_factory() as session:
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=snapshot.study_id,
                    site_id=snapshot.site_id,
                    command_name="reports.event.record",
                    command=command,
                    request_payload={"snapshot_id": str(snapshot.id)},
                )
                if not replayed:
                    event = ReportEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=snapshot.study_id,
                        site_id=snapshot.site_id,
                        snapshot_id=snapshot.id,
                        event_type=command.event_type,
                        actor_id=scope.actor_id,
                        user_statement=command.user_statement,
                    )
                    session.add(event)
                    session.flush()
                    self._audit(
                        session,
                        scope=scope,
                        study_id=snapshot.study_id,
                        site_id=snapshot.site_id,
                        action="reports.event.record",
                        resource_type="report_event",
                        resource_id=event.id,
                        revision_before=None,
                        revision_after=1,
                        after_state={
                            "snapshot_id": str(snapshot.id),
                            "event_type": command.event_type,
                        },
                        command_name="reports.event.record",
                        correlation_id=record.id,
                    )
                    self._complete(record, event.id, 1)
        return self.snapshot(scope, snapshot.id)
