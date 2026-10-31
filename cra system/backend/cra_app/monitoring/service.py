"""Monitoring-visit workbench joining carryover, selection and source references."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.service import DocumentService
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.issues.contracts import (
    CreateMonitoringVisitCommand,
    SelectPrevisitIssuesCommand,
    UpdateMonitoringScopeCommand,
)
from cra_app.issues.models import (
    Issue,
    MonitoringVisit,
    MonitoringVisitSelection,
)
from cra_app.issues.service import (
    IssueDetail,
    IssueNotFound,
    IssueService,
    IssueValidationError,
    aggregate_action_status,
)
from cra_app.platform.jobs import digest_payload
from cra_app.shared.output_contract import OutputEnvelope


@dataclass(frozen=True)
class DirectoryReference:
    document_id: uuid.UUID
    document_version_id: uuid.UUID | None
    title: str
    original_filename: str | None
    document_type: str
    purpose: str
    parse_status: str | None
    mode: str = "reference_only"


@dataclass(frozen=True)
class WorkbenchData:
    visit: MonitoringVisit
    carryover: tuple[IssueDetail, ...]
    selected_issue_ids: tuple[uuid.UUID, ...]
    directory_references: tuple[DirectoryReference, ...]
    envelope: OutputEnvelope


class MonitoringService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        issues: IssueService,
        documents: DocumentService,
        governance: GovernanceService | None = None,
    ):
        self.session_factory = session_factory
        self.issues = issues
        self.documents = documents
        self.governance = governance or GovernanceService(session_factory)

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
        command,
        request_payload: dict | None = None,
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

    def _load_visit(
        self, scope: ScopeContext, visit_id: uuid.UUID
    ) -> MonitoringVisit:
        with self.session_factory() as session:
            visit = session.scalar(
                select(MonitoringVisit).where(
                    MonitoringVisit.id == visit_id,
                    MonitoringVisit.tenant_id == scope.tenant_id,
                )
            )
            if visit is None:
                raise IssueNotFound("monitoring visit was not found")
            return visit

    def _directory_references(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> tuple[DirectoryReference, ...]:
        documents = self.documents.list_documents(scope, study_id, site_id)
        references = []
        for document in documents:
            versions = self.documents.list_versions(scope, document.id)
            latest = versions[0] if versions else None
            references.append(
                DirectoryReference(
                    document_id=document.id,
                    document_version_id=latest.id if latest else None,
                    title=document.title,
                    original_filename=(
                        latest.original_filename if latest else None
                    ),
                    document_type=document.document_type,
                    purpose=document.purpose,
                    parse_status=latest.parse_status if latest else None,
                )
            )
        return tuple(references)

    def create_visit(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateMonitoringVisitCommand,
    ) -> WorkbenchData:
        self.governance.authorize(
            scope, "write_site", study_id, command.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=command.site_id,
                    command_name="monitoring.visits.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    visit = session.get(
                        MonitoringVisit, record.response_resource_id
                    )
                    if visit is None:
                        raise IssueNotFound(
                            "replayed monitoring visit was not found"
                        )
                else:
                    visit = MonitoringVisit(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        stage=command.stage,
                        title=command.title,
                        scope_note=command.scope_note,
                        status="draft",
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(visit)
                    session.flush()
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=command.site_id,
                            actor_id=scope.actor_id,
                            action="monitoring.visits.create",
                            resource_type="monitoring_visit",
                            resource_id=visit.id,
                            revision_before=None,
                            revision_after=visit.revision,
                            before_state=None,
                            after_state={
                                "stage": visit.stage,
                                "title": visit.title,
                                "scope_note": visit.scope_note,
                            },
                            command_name="monitoring.visits.create",
                            correlation_id=record.id,
                        )
                    )
                    self._complete(record, visit.id, visit.revision)
            return self._workbench_in_session(session, scope, visit)

    def visit(
        self, scope: ScopeContext, visit_id: uuid.UUID
    ) -> MonitoringVisit:
        visit = self._load_visit(scope, visit_id)
        self.governance.authorize(
            scope, "read_site", visit.study_id, visit.site_id
        )
        return visit

    def _selection_ids(
        self, session: Session, visit_id: uuid.UUID
    ) -> tuple[uuid.UUID, ...]:
        return tuple(
            session.scalars(
                select(MonitoringVisitSelection.issue_id)
                .where(MonitoringVisitSelection.monitoring_visit_id == visit_id)
                .order_by(MonitoringVisitSelection.selected_at)
            )
        )

    def _workbench_in_session(
        self, session: Session, scope: ScopeContext, visit: MonitoringVisit
    ) -> WorkbenchData:
        carryover = self.issues.list_issues(
            scope,
            visit.study_id,
            visit.site_id,
            remaining_only=True,
        )
        selected = self._selection_ids(session, visit.id)
        references = self._directory_references(
            scope, visit.study_id, visit.site_id
        )
        envelope = self.issues.carryover_envelope(
            scope,
            visit.study_id,
            visit.site_id,
            monitoring_visit_id=visit.id,
        )
        return WorkbenchData(
            visit=visit,
            carryover=tuple(carryover),
            selected_issue_ids=selected,
            directory_references=references,
            envelope=envelope,
        )

    def workbench(
        self, scope: ScopeContext, visit_id: uuid.UUID
    ) -> WorkbenchData:
        visit = self._load_visit(scope, visit_id)
        self.governance.authorize(
            scope, "read_site", visit.study_id, visit.site_id
        )
        with self.session_factory() as session:
            return self._workbench_in_session(session, scope, visit)

    def update_scope(
        self,
        scope: ScopeContext,
        visit_id: uuid.UUID,
        command: UpdateMonitoringScopeCommand,
    ) -> WorkbenchData:
        visit = self._load_visit(scope, visit_id)
        self.governance.authorize(
            scope, "write_site", visit.study_id, visit.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                visit = session.scalar(
                    select(MonitoringVisit)
                    .where(
                        MonitoringVisit.id == visit_id,
                        MonitoringVisit.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if visit is None:
                    raise IssueNotFound("monitoring visit was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=visit.study_id,
                    site_id=visit.site_id,
                    command_name="monitoring.visits.update_scope",
                    command=command,
                    request_payload={"visit_id": str(visit.id)},
                )
                if not replayed:
                    if visit.revision != command.expected_revision:
                        raise RevisionConflict(visit.revision)
                    visit.scope_note = command.scope_note
                    if command.status is not None:
                        visit.status = command.status
                    visit.revision += 1
                    visit.updated_by = scope.actor_id
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=visit.study_id,
                            site_id=visit.site_id,
                            actor_id=scope.actor_id,
                            action="monitoring.visits.update_scope",
                            resource_type="monitoring_visit",
                            resource_id=visit.id,
                            revision_before=command.expected_revision,
                            revision_after=visit.revision,
                            before_state=None,
                            after_state={
                                "scope_note": visit.scope_note,
                                "status": visit.status,
                            },
                            command_name="monitoring.visits.update_scope",
                            correlation_id=record.id,
                        )
                    )
                    self._complete(record, visit.id, visit.revision)
            return self._workbench_in_session(session, scope, visit)

    def select_previsit_issues(
        self,
        scope: ScopeContext,
        visit_id: uuid.UUID,
        command: SelectPrevisitIssuesCommand,
    ) -> WorkbenchData:
        visit = self._load_visit(scope, visit_id)
        self.governance.authorize(
            scope, "write_site", visit.study_id, visit.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                visit = session.scalar(
                    select(MonitoringVisit)
                    .where(
                        MonitoringVisit.id == visit_id,
                        MonitoringVisit.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if visit is None:
                    raise IssueNotFound("monitoring visit was not found")
                issues = list(
                    session.scalars(
                        select(Issue).where(
                            Issue.id.in_(command.issue_ids),
                            Issue.tenant_id == scope.tenant_id,
                            Issue.study_id == visit.study_id,
                            Issue.site_id == visit.site_id,
                        )
                    )
                )
                if len(issues) != len(command.issue_ids):
                    raise IssueValidationError(
                        "one or more selected issues are outside this site"
                    )
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=visit.study_id,
                    site_id=visit.site_id,
                    command_name="monitoring.visits.previsit_select",
                    command=command,
                    request_payload={"visit_id": str(visit.id)},
                )
                if not replayed:
                    if visit.revision != command.expected_revision:
                        raise RevisionConflict(visit.revision)
                    session.execute(
                        delete(MonitoringVisitSelection).where(
                            MonitoringVisitSelection.monitoring_visit_id
                            == visit.id
                        )
                    )
                    for issue_id in command.issue_ids:
                        session.add(
                            MonitoringVisitSelection(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=visit.study_id,
                                site_id=visit.site_id,
                                monitoring_visit_id=visit.id,
                                issue_id=issue_id,
                                selected_by=scope.actor_id,
                            )
                        )
                    visit.revision += 1
                    visit.updated_by = scope.actor_id
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=visit.study_id,
                            site_id=visit.site_id,
                            actor_id=scope.actor_id,
                            action="monitoring.visits.previsit_select",
                            resource_type="monitoring_visit",
                            resource_id=visit.id,
                            revision_before=command.expected_revision,
                            revision_after=visit.revision,
                            before_state=None,
                            after_state={
                                "selected_issue_ids": [
                                    str(item) for item in command.issue_ids
                                ],
                                "selection_does_not_delete_issues": True,
                            },
                            command_name="monitoring.visits.previsit_select",
                            correlation_id=record.id,
                        )
                    )
                    self._complete(record, visit.id, visit.revision)
                session.flush()
            return self._workbench_in_session(session, scope, visit)
