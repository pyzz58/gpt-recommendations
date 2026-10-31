"""Authorized incremental ISF/TMF review and source-backed stage checklists."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.documents.models import DocumentVersion, SourceAnchor, SourceDocument
from cra_app.documents.service import DocumentNotFound, DocumentService
from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.issues.models import Issue
from cra_app.issues.service import (
    IssueDetail,
    IssueNotFound,
    IssueService,
    IssueValidationError,
    aggregate_action_status,
)
from cra_app.monitoring.service import MonitoringService
from cra_app.monitoring.stages import (
    concise_handover_summary,
    incomplete_checklist_items,
)
from cra_app.platform.jobs import digest_payload
from cra_app.site_files.models import (
    StageChecklist,
    StageChecklistHistory,
    StageChecklistItem,
    SiteDirectoryReference,
    SiteFileHistory,
    SiteFileItem,
)

DirectoryKind = Literal["isf", "tmf", "combined", "other"]
ApplicabilityStatus = Literal["required", "not_required", "unknown"]
AcquisitionStatus = Literal["not_seen", "provided", "unknown"]
VerificationStatus = Literal["pending", "qualified", "unknown"]
StageKind = Literal["startup", "closeout"]
StageItemStatus = Literal["open", "confirmed", "not_applicable", "unknown"]


class SiteFileContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StatusState(SiteFileContract):
    applicability_status: ApplicabilityStatus = "required"
    acquisition_status: AcquisitionStatus = "not_seen"
    verification_status: VerificationStatus = "pending"

    @model_validator(mode="after")
    def validate_qualified_file(self) -> "StatusState":
        if (
            self.verification_status == "qualified"
            and self.acquisition_status != "provided"
        ):
            raise ValueError(
                "qualified verification requires an acquired/provided file"
            )
        return self


class CreateDirectoryReferenceCommand(SiteFileContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    source_document_version_id: uuid.UUID
    directory_kind: DirectoryKind
    label: str = Field(min_length=1, max_length=255)
    annotations: list[dict[str, Any]] = Field(
        default_factory=list, max_length=200
    )


class AddDirectoryItemCommand(StatusState):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    item_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    title: str = Field(min_length=1, max_length=255)
    requirement: str | None = Field(default=None, max_length=10000)
    verification_note: str | None = Field(default=None, max_length=4000)
    source_anchor_id: uuid.UUID | None = None
    source_refs: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    linked_issue_id: uuid.UUID | None = None
    linked_action_id: uuid.UUID | None = None


class VerifyFileCommand(StatusState):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_file_item_id: uuid.UUID
    verification_note: str | None = Field(default=None, max_length=4000)
    linked_issue_id: uuid.UUID | None = None
    linked_action_id: uuid.UUID | None = None


class StageChecklistItemInput(SiteFileContract):
    item_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    title: str = Field(min_length=1, max_length=255)
    requirement: str = Field(min_length=1, max_length=10000)
    source_document_version_id: uuid.UUID
    source_anchor_id: uuid.UUID | None = None
    source_refs: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class CreateStageChecklistCommand(SiteFileContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    site_id: uuid.UUID
    stage: StageKind
    title: str = Field(min_length=1, max_length=255)
    source_refs: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    items: list[StageChecklistItemInput] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_item_keys(self) -> "CreateStageChecklistCommand":
        keys = [item.item_key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("stage checklist item keys must be unique")
        return self


class AddStageChecklistItemCommand(SiteFileContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    item: StageChecklistItemInput


class VerifyStageItemCommand(SiteFileContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    status: StageItemStatus
    note: str | None = Field(default=None, max_length=4000)


@dataclass(frozen=True)
class DirectoryDetail:
    reference: SiteDirectoryReference
    items: tuple[SiteFileItem, ...]
    history: tuple[SiteFileHistory, ...]


@dataclass(frozen=True)
class StageChecklistDetail:
    checklist: StageChecklist
    items: tuple[StageChecklistItem, ...]
    history: tuple[StageChecklistHistory, ...]


@dataclass(frozen=True)
class HandoverIssue:
    issue: IssueDetail
    next_steps: tuple[str, ...]


@dataclass(frozen=True)
class HandoverSummary:
    visit_id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    generated_at: datetime
    has_carryover: bool
    summary: str
    issues: tuple[HandoverIssue, ...]
    incomplete_checklist_items: tuple[StageChecklistItem, ...]
    center_close_approved: Literal[False] = False


class SiteFileError(Exception):
    pass


class SiteFileNotFound(SiteFileError):
    pass


class SiteFileValidationError(SiteFileError):
    pass


class SiteFileConflict(SiteFileError):
    pass


class SiteFileService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService | None = None,
        documents: DocumentService,
        issues: IssueService,
        monitoring: MonitoringService,
    ):
        self.session_factory = session_factory
        self.governance = governance or GovernanceService(session_factory)
        self.documents = documents
        self.issues = issues
        self.monitoring = monitoring

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

    def _load_reference(
        self, session: Session, scope: ScopeContext, reference_id: uuid.UUID
    ) -> SiteDirectoryReference:
        reference = session.scalar(
            select(SiteDirectoryReference).where(
                SiteDirectoryReference.id == reference_id,
                SiteDirectoryReference.tenant_id == scope.tenant_id,
            )
        )
        if reference is None:
            raise SiteFileNotFound("directory reference was not found")
        return reference

    def _load_checklist(
        self, session: Session, scope: ScopeContext, checklist_id: uuid.UUID
    ) -> StageChecklist:
        checklist = session.scalar(
            select(StageChecklist).where(
                StageChecklist.id == checklist_id,
                StageChecklist.tenant_id == scope.tenant_id,
            )
        )
        if checklist is None:
            raise SiteFileNotFound("stage checklist was not found")
        return checklist

    def _document_version(
        self,
        session: Session,
        scope: ScopeContext,
        version_id: uuid.UUID,
    ) -> tuple[DocumentVersion, SourceDocument]:
        try:
            version = self.documents.get_version(scope, version_id)
        except DocumentNotFound as exc:
            raise SiteFileValidationError(
                "source document version was not found"
            ) from exc
        document = session.scalar(
            select(SourceDocument).where(
                SourceDocument.id == version.document_id,
                SourceDocument.tenant_id == scope.tenant_id,
                SourceDocument.study_id == version.study_id,
            )
        )
        if document is None:
            raise SiteFileValidationError("source document was not found")
        return version, document

    def _validate_anchor(
        self,
        session: Session,
        scope: ScopeContext,
        *,
        version: DocumentVersion,
        anchor_id: uuid.UUID | None,
    ) -> None:
        if anchor_id is None:
            return
        anchor = session.scalar(
            select(SourceAnchor).where(
                SourceAnchor.id == anchor_id,
                SourceAnchor.tenant_id == scope.tenant_id,
                SourceAnchor.study_id == version.study_id,
                SourceAnchor.document_version_id == version.id,
            )
        )
        if anchor is None:
            raise SiteFileValidationError(
                "source anchor does not belong to the selected document version"
            )

    def _validate_directory_version(
        self,
        session: Session,
        scope: ScopeContext,
        command: CreateDirectoryReferenceCommand,
    ) -> DocumentVersion:
        version, document = self._document_version(
            session, scope, command.source_document_version_id
        )
        if (
            document.purpose != "directory"
            or document.document_type != "directory"
        ):
            raise SiteFileValidationError(
                "directory reference requires a directory-purpose M02 version"
            )
        if version.study_id != document.study_id:
            raise SiteFileValidationError("document version scope mismatch")
        if document.site_id != command.site_id:
            raise SiteFileValidationError(
                "directory source does not belong to this site"
            )
        return version

    def _validate_stage_source(
        self,
        session: Session,
        scope: ScopeContext,
        *,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        item: StageChecklistItemInput,
    ) -> None:
        version, document = self._document_version(
            session, scope, item.source_document_version_id
        )
        if version.study_id != study_id:
            raise SiteFileValidationError("stage source belongs to another study")
        if document.site_id not in {None, site_id}:
            raise SiteFileValidationError("stage source belongs to another site")
        if document.purpose not in {
            "rule",
            "directory",
            "template",
            "other",
        }:
            raise SiteFileValidationError(
                "stage checklist source is not a project-requirement document"
            )
        self._validate_anchor(
            session,
            scope,
            version=version,
            anchor_id=item.source_anchor_id,
        )

    def _validated_issue_link(
        self,
        scope: ScopeContext,
        *,
        site_id: uuid.UUID,
        issue_id: uuid.UUID | None,
        action_id: uuid.UUID | None,
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        if issue_id is None and action_id is None:
            return None, None
        if issue_id is None:
            raise SiteFileValidationError(
                "a linked M06 action also requires its issue_id"
            )
        try:
            detail = self.issues.issue_detail(scope, issue_id)
        except (IssueNotFound, IssueValidationError) as exc:
            raise SiteFileValidationError("linked M06 issue was not found") from exc
        if detail.issue.site_id != site_id:
            raise SiteFileValidationError(
                "linked issue does not belong to this site"
            )
        if action_id is not None and not any(
            action.id == action_id for action in detail.actions
        ):
            raise SiteFileValidationError(
                "linked action does not belong to this issue"
            )
        return issue_id, action_id

    def _detail_in_session(
        self, session: Session, reference: SiteDirectoryReference
    ) -> DirectoryDetail:
        items = tuple(
            session.scalars(
                select(SiteFileItem)
                .where(
                    SiteFileItem.tenant_id == reference.tenant_id,
                    SiteFileItem.study_id == reference.study_id,
                    SiteFileItem.directory_reference_id == reference.id,
                )
                .order_by(SiteFileItem.item_key)
            )
        )
        history = tuple(
            session.scalars(
                select(SiteFileHistory)
                .where(
                    SiteFileHistory.tenant_id == reference.tenant_id,
                    SiteFileHistory.study_id == reference.study_id,
                    SiteFileHistory.directory_reference_id == reference.id,
                )
                .order_by(SiteFileHistory.ordinal)
            )
        )
        return DirectoryDetail(reference=reference, items=items, history=history)

    @staticmethod
    def _next_history_ordinal(
        session: Session,
        model: type[SiteFileHistory] | type[StageChecklistHistory],
        *,
        parent_id: uuid.UUID,
    ) -> int:
        column = (
            SiteFileHistory.directory_reference_id
            if model is SiteFileHistory
            else StageChecklistHistory.stage_checklist_id
        )
        current = session.scalar(
            select(func.max(model.ordinal)).where(column == parent_id)
        )
        return (current or 0) + 1

    def create_directory_reference(
        self,
        scope: ScopeContext,
        command: CreateDirectoryReferenceCommand,
    ) -> DirectoryDetail:
        with self.session_factory() as session:
            version = self._validate_directory_version(
                session, scope, command
            )
            study_id, site_id = version.study_id, command.site_id
        self.governance.authorize(scope, "write_site", study_id, site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=site_id,
                    command_name="site_files.directory.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    reference = self._load_reference(
                        session, scope, record.response_resource_id
                    )
                else:
                    existing = session.scalar(
                        select(SiteDirectoryReference).where(
                            SiteDirectoryReference.tenant_id
                            == scope.tenant_id,
                            SiteDirectoryReference.study_id == study_id,
                            SiteDirectoryReference.site_id == site_id,
                            SiteDirectoryReference.source_document_version_id
                            == command.source_document_version_id,
                        )
                    )
                    if existing is not None:
                        raise SiteFileConflict(
                            "this directory version is already referenced"
                        )
                    reference = SiteDirectoryReference(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=site_id,
                        source_document_version_id=(
                            command.source_document_version_id
                        ),
                        directory_kind=command.directory_kind,
                        label=command.label,
                        mode="reference_only",
                        annotations=command.annotations,
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(reference)
                    session.flush()
                    session.add(
                        SiteFileHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=site_id,
                            directory_reference_id=reference.id,
                            site_file_item_id=None,
                            event_type="directory_reference_created",
                            actor_id=scope.actor_id,
                            ordinal=1,
                            details={
                                "mode": "reference_only",
                                "source_document_version_id": str(
                                    command.source_document_version_id
                                ),
                                "directory_kind": command.directory_kind,
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=study_id,
                        site_id=site_id,
                        action="site_files.directory.create",
                        resource_type="site_directory_reference",
                        resource_id=reference.id,
                        revision_before=None,
                        revision_after=reference.revision,
                        after_state={
                            "mode": reference.mode,
                            "directory_kind": reference.directory_kind,
                        },
                        command_name="site_files.directory.create",
                        correlation_id=record.id,
                    )
                    self._complete(record, reference.id, reference.revision)
            return self._detail_in_session(session, reference)

    def directory_detail(
        self, scope: ScopeContext, reference_id: uuid.UUID
    ) -> DirectoryDetail:
        with self.session_factory() as session:
            reference = self._load_reference(session, scope, reference_id)
            self.governance.authorize(
                scope,
                "read_site",
                reference.study_id,
                reference.site_id,
            )
            return self._detail_in_session(session, reference)

    def site_file_status(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[DirectoryDetail]:
        self.governance.authorize(scope, "read_site", study_id, site_id)
        with self.session_factory() as session:
            references = list(
                session.scalars(
                    select(SiteDirectoryReference)
                    .where(
                        SiteDirectoryReference.tenant_id == scope.tenant_id,
                        SiteDirectoryReference.study_id == study_id,
                        SiteDirectoryReference.site_id == site_id,
                    )
                    .order_by(
                        SiteDirectoryReference.created_at,
                        SiteDirectoryReference.id,
                    )
                )
            )
            return [
                self._detail_in_session(session, reference)
                for reference in references
            ]

    def add_directory_item(
        self,
        scope: ScopeContext,
        reference_id: uuid.UUID,
        command: AddDirectoryItemCommand,
    ) -> DirectoryDetail:
        with self.session_factory() as session:
            reference = self._load_reference(session, scope, reference_id)
            self.governance.authorize(
                scope,
                "write_site",
                reference.study_id,
                reference.site_id,
            )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                reference = session.scalar(
                    select(SiteDirectoryReference)
                    .where(
                        SiteDirectoryReference.id == reference_id,
                        SiteDirectoryReference.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if reference is None:
                    raise SiteFileNotFound("directory reference was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=reference.study_id,
                    site_id=reference.site_id,
                    command_name="site_files.directory.item.add",
                    command=command,
                    request_payload={"reference_id": str(reference_id)},
                )
                if not replayed:
                    if reference.revision != command.expected_revision:
                        raise RevisionConflict(reference.revision)
                    version, _ = self._document_version(
                        session,
                        scope,
                        reference.source_document_version_id,
                    )
                    self._validate_anchor(
                        session,
                        scope,
                        version=version,
                        anchor_id=command.source_anchor_id,
                    )
                    issue_id, action_id = self._validated_issue_link(
                        scope,
                        site_id=reference.site_id,
                        issue_id=command.linked_issue_id,
                        action_id=command.linked_action_id,
                    )
                    duplicate = session.scalar(
                        select(SiteFileItem.id).where(
                            SiteFileItem.directory_reference_id
                            == reference.id,
                            SiteFileItem.item_key == command.item_key,
                        )
                    )
                    if duplicate is not None:
                        raise SiteFileConflict(
                            "directory item_key already exists in this reference"
                        )
                    item = SiteFileItem(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=reference.study_id,
                        site_id=reference.site_id,
                        directory_reference_id=reference.id,
                        item_key=command.item_key,
                        title=command.title,
                        requirement=command.requirement,
                        applicability_status=command.applicability_status,
                        acquisition_status=command.acquisition_status,
                        verification_status=command.verification_status,
                        verification_note=command.verification_note,
                        source_anchor_id=command.source_anchor_id,
                        source_refs=command.source_refs,
                        linked_issue_id=issue_id,
                        linked_action_id=action_id,
                        verified_by=None,
                        verified_at=None,
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(item)
                    session.flush()
                    reference.mode = "structured"
                    reference.revision += 1
                    reference.updated_by = scope.actor_id
                    session.add(
                        SiteFileHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=reference.study_id,
                            site_id=reference.site_id,
                            directory_reference_id=reference.id,
                            site_file_item_id=item.id,
                            event_type="item_created",
                            actor_id=scope.actor_id,
                            ordinal=self._next_history_ordinal(
                                session,
                                SiteFileHistory,
                                parent_id=reference.id,
                            ),
                            details={
                                "item_key": item.item_key,
                                "applicability_status": (
                                    item.applicability_status
                                ),
                                "acquisition_status": item.acquisition_status,
                                "verification_status": item.verification_status,
                                "linked_issue_id": (
                                    str(item.linked_issue_id)
                                    if item.linked_issue_id
                                    else None
                                ),
                                "linked_action_id": (
                                    str(item.linked_action_id)
                                    if item.linked_action_id
                                    else None
                                ),
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=reference.study_id,
                        site_id=reference.site_id,
                        action="site_files.directory.item.add",
                        resource_type="site_file_item",
                        resource_id=item.id,
                        revision_before=None,
                        revision_after=item.revision,
                        after_state={
                            "item_key": item.item_key,
                            "applicability_status": (
                                item.applicability_status
                            ),
                            "acquisition_status": item.acquisition_status,
                            "verification_status": item.verification_status,
                        },
                        command_name="site_files.directory.item.add",
                        correlation_id=record.id,
                    )
                    self._complete(record, item.id, item.revision)
            return self._detail_in_session(session, reference)

    def verify_file(
        self, scope: ScopeContext, command: VerifyFileCommand
    ) -> DirectoryDetail:
        with self.session_factory() as session:
            item = session.scalar(
                select(SiteFileItem).where(
                    SiteFileItem.id == command.site_file_item_id,
                    SiteFileItem.tenant_id == scope.tenant_id,
                )
            )
            if item is None:
                raise SiteFileNotFound("site file item was not found")
            study_id, site_id = item.study_id, item.site_id
            reference_id = item.directory_reference_id
        self.governance.authorize(scope, "write_site", study_id, site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                reference = session.scalar(
                    select(SiteDirectoryReference)
                    .where(
                        SiteDirectoryReference.id == reference_id,
                        SiteDirectoryReference.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                item = session.scalar(
                    select(SiteFileItem)
                    .where(
                        SiteFileItem.id == command.site_file_item_id,
                        SiteFileItem.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if reference is None or item is None:
                    raise SiteFileNotFound("site file item was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=site_id,
                    command_name="site_files.file.verify",
                    command=command,
                )
                if not replayed:
                    if item.revision != command.expected_revision:
                        raise RevisionConflict(item.revision)
                    issue_id, action_id = self._validated_issue_link(
                        scope,
                        site_id=site_id,
                        issue_id=command.linked_issue_id,
                        action_id=command.linked_action_id,
                    )
                    before = {
                        "applicability_status": item.applicability_status,
                        "acquisition_status": item.acquisition_status,
                        "verification_status": item.verification_status,
                        "linked_issue_id": (
                            str(item.linked_issue_id)
                            if item.linked_issue_id
                            else None
                        ),
                        "linked_action_id": (
                            str(item.linked_action_id)
                            if item.linked_action_id
                            else None
                        ),
                    }
                    item.applicability_status = command.applicability_status
                    item.acquisition_status = command.acquisition_status
                    item.verification_status = command.verification_status
                    item.verification_note = command.verification_note
                    item.linked_issue_id = issue_id
                    item.linked_action_id = action_id
                    item.verified_by = scope.actor_id
                    item.verified_at = datetime.now(UTC)
                    item.updated_by = scope.actor_id
                    item.revision += 1
                    session.add(
                        SiteFileHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=site_id,
                            directory_reference_id=reference.id,
                            site_file_item_id=item.id,
                            event_type="status_updated",
                            actor_id=scope.actor_id,
                            ordinal=self._next_history_ordinal(
                                session,
                                SiteFileHistory,
                                parent_id=reference.id,
                            ),
                            details={
                                "before": before,
                                "after": {
                                    "applicability_status": (
                                        item.applicability_status
                                    ),
                                    "acquisition_status": (
                                        item.acquisition_status
                                    ),
                                    "verification_status": (
                                        item.verification_status
                                    ),
                                    "verification_note": (
                                        item.verification_note
                                    ),
                                },
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=study_id,
                        site_id=site_id,
                        action="site_files.file.verify",
                        resource_type="site_file_item",
                        resource_id=item.id,
                        revision_before=command.expected_revision,
                        revision_after=item.revision,
                        after_state={
                            "applicability_status": (
                                item.applicability_status
                            ),
                            "acquisition_status": item.acquisition_status,
                            "verification_status": item.verification_status,
                        },
                        command_name="site_files.file.verify",
                        correlation_id=record.id,
                    )
                    self._complete(record, item.id, item.revision)
            return self._detail_in_session(session, reference)

    def _checklist_detail_in_session(
        self, session: Session, checklist: StageChecklist
    ) -> StageChecklistDetail:
        items = tuple(
            session.scalars(
                select(StageChecklistItem)
                .where(
                    StageChecklistItem.tenant_id == checklist.tenant_id,
                    StageChecklistItem.study_id == checklist.study_id,
                    StageChecklistItem.stage_checklist_id == checklist.id,
                )
                .order_by(StageChecklistItem.item_key)
            )
        )
        history = tuple(
            session.scalars(
                select(StageChecklistHistory)
                .where(
                    StageChecklistHistory.tenant_id == checklist.tenant_id,
                    StageChecklistHistory.study_id == checklist.study_id,
                    StageChecklistHistory.stage_checklist_id == checklist.id,
                )
                .order_by(StageChecklistHistory.ordinal)
            )
        )
        return StageChecklistDetail(
            checklist=checklist, items=items, history=history
        )

    def create_stage_checklist(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateStageChecklistCommand,
    ) -> StageChecklistDetail:
        first = command.items[0]
        with self.session_factory() as session:
            version, _ = self._document_version(
                session, scope, first.source_document_version_id
            )
        if version.study_id != study_id:
            raise SiteFileValidationError(
                "stage checklist source belongs to another study"
            )
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
                    command_name="monitoring.stage_checklist.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    checklist = self._load_checklist(
                        session, scope, record.response_resource_id
                    )
                else:
                    duplicate = session.scalar(
                        select(StageChecklist.id).where(
                            StageChecklist.tenant_id == scope.tenant_id,
                            StageChecklist.study_id == study_id,
                            StageChecklist.site_id == command.site_id,
                            StageChecklist.stage == command.stage,
                        )
                    )
                    if duplicate is not None:
                        raise SiteFileConflict(
                            "a checklist already exists for this site/stage"
                        )
                    checklist = StageChecklist(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        stage=command.stage,
                        title=command.title,
                        source_refs=command.source_refs,
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(checklist)
                    session.flush()
                    session.add(
                        StageChecklistHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=command.site_id,
                            stage_checklist_id=checklist.id,
                            stage_checklist_item_id=None,
                            event_type="checklist_created",
                            actor_id=scope.actor_id,
                            ordinal=1,
                            details={
                                "stage": checklist.stage,
                                "source_refs": command.source_refs,
                                "adds_close_approval": False,
                            },
                        )
                    )
                    history_ordinal = 2
                    for draft in command.items:
                        self._validate_stage_source(
                            session,
                            scope,
                            study_id=study_id,
                            site_id=command.site_id,
                            item=draft,
                        )
                        item = StageChecklistItem(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=command.site_id,
                            stage_checklist_id=checklist.id,
                            item_key=draft.item_key,
                            title=draft.title,
                            requirement=draft.requirement,
                            source_document_version_id=(
                                draft.source_document_version_id
                            ),
                            source_anchor_id=draft.source_anchor_id,
                            source_refs=draft.source_refs,
                            status="open",
                            completion_note=None,
                            completed_by=None,
                            completed_at=None,
                            revision=1,
                            created_by=scope.actor_id,
                            updated_by=scope.actor_id,
                        )
                        session.add(item)
                        session.flush()
                        session.add(
                            StageChecklistHistory(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=study_id,
                                site_id=command.site_id,
                                stage_checklist_id=checklist.id,
                                stage_checklist_item_id=item.id,
                                event_type="item_created",
                                actor_id=scope.actor_id,
                                ordinal=history_ordinal,
                                details={
                                    "item_key": item.item_key,
                                    "source_document_version_id": str(
                                        item.source_document_version_id
                                    ),
                                    "source_anchor_id": (
                                        str(item.source_anchor_id)
                                        if item.source_anchor_id
                                        else None
                                    ),
                                    "status": item.status,
                                },
                            )
                        )
                        history_ordinal += 1
                    self._audit(
                        session,
                        scope=scope,
                        study_id=study_id,
                        site_id=command.site_id,
                        action="monitoring.stage_checklist.create",
                        resource_type="stage_checklist",
                        resource_id=checklist.id,
                        revision_before=None,
                        revision_after=checklist.revision,
                        after_state={
                            "stage": checklist.stage,
                            "item_count": len(command.items),
                            "center_close_approved": False,
                        },
                        command_name="monitoring.stage_checklist.create",
                        correlation_id=record.id,
                    )
                    self._complete(record, checklist.id, checklist.revision)
            return self._checklist_detail_in_session(session, checklist)

    def stage_checklists(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[StageChecklistDetail]:
        self.governance.authorize(scope, "read_site", study_id, site_id)
        with self.session_factory() as session:
            checklists = list(
                session.scalars(
                    select(StageChecklist)
                    .where(
                        StageChecklist.tenant_id == scope.tenant_id,
                        StageChecklist.study_id == study_id,
                        StageChecklist.site_id == site_id,
                    )
                    .order_by(StageChecklist.stage)
                )
            )
            return [
                self._checklist_detail_in_session(session, checklist)
                for checklist in checklists
            ]

    def add_stage_item(
        self,
        scope: ScopeContext,
        checklist_id: uuid.UUID,
        command: AddStageChecklistItemCommand,
    ) -> StageChecklistDetail:
        with self.session_factory() as session:
            checklist = self._load_checklist(
                session, scope, checklist_id
            )
            self.governance.authorize(
                scope,
                "write_site",
                checklist.study_id,
                checklist.site_id,
            )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                checklist = session.scalar(
                    select(StageChecklist)
                    .where(
                        StageChecklist.id == checklist_id,
                        StageChecklist.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if checklist is None:
                    raise SiteFileNotFound("stage checklist was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=checklist.study_id,
                    site_id=checklist.site_id,
                    command_name="monitoring.stage_checklist.item.add",
                    command=command,
                    request_payload={"checklist_id": str(checklist_id)},
                )
                if not replayed:
                    if checklist.revision != command.expected_revision:
                        raise RevisionConflict(checklist.revision)
                    self._validate_stage_source(
                        session,
                        scope,
                        study_id=checklist.study_id,
                        site_id=checklist.site_id,
                        item=command.item,
                    )
                    duplicate = session.scalar(
                        select(StageChecklistItem.id).where(
                            StageChecklistItem.stage_checklist_id
                            == checklist.id,
                            StageChecklistItem.item_key
                            == command.item.item_key,
                        )
                    )
                    if duplicate is not None:
                        raise SiteFileConflict(
                            "stage checklist item_key already exists"
                        )
                    item = StageChecklistItem(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=checklist.study_id,
                        site_id=checklist.site_id,
                        stage_checklist_id=checklist.id,
                        item_key=command.item.item_key,
                        title=command.item.title,
                        requirement=command.item.requirement,
                        source_document_version_id=(
                            command.item.source_document_version_id
                        ),
                        source_anchor_id=command.item.source_anchor_id,
                        source_refs=command.item.source_refs,
                        status="open",
                        completion_note=None,
                        completed_by=None,
                        completed_at=None,
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(item)
                    session.flush()
                    checklist.revision += 1
                    checklist.updated_by = scope.actor_id
                    session.add(
                        StageChecklistHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=checklist.study_id,
                            site_id=checklist.site_id,
                            stage_checklist_id=checklist.id,
                            stage_checklist_item_id=item.id,
                            event_type="item_created",
                            actor_id=scope.actor_id,
                            ordinal=self._next_history_ordinal(
                                session,
                                StageChecklistHistory,
                                parent_id=checklist.id,
                            ),
                            details={"item_key": item.item_key},
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=checklist.study_id,
                        site_id=checklist.site_id,
                        action="monitoring.stage_checklist.item.add",
                        resource_type="stage_checklist_item",
                        resource_id=item.id,
                        revision_before=None,
                        revision_after=item.revision,
                        after_state={"item_key": item.item_key},
                        command_name="monitoring.stage_checklist.item.add",
                        correlation_id=record.id,
                    )
                    self._complete(record, checklist.id, checklist.revision)
            return self._checklist_detail_in_session(session, checklist)

    def verify_stage_item(
        self,
        scope: ScopeContext,
        item_id: uuid.UUID,
        command: VerifyStageItemCommand,
    ) -> StageChecklistDetail:
        with self.session_factory() as session:
            item = session.scalar(
                select(StageChecklistItem).where(
                    StageChecklistItem.id == item_id,
                    StageChecklistItem.tenant_id == scope.tenant_id,
                )
            )
            if item is None:
                raise SiteFileNotFound("stage checklist item was not found")
            checklist_id = item.stage_checklist_id
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                checklist = session.scalar(
                    select(StageChecklist)
                    .where(
                        StageChecklist.id == checklist_id,
                        StageChecklist.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                item = session.scalar(
                    select(StageChecklistItem)
                    .where(
                        StageChecklistItem.id == item_id,
                        StageChecklistItem.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if checklist is None or item is None:
                    raise SiteFileNotFound("stage checklist item was not found")
                self.governance.authorize(
                    scope,
                    "write_site",
                    checklist.study_id,
                    checklist.site_id,
                )
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=checklist.study_id,
                    site_id=checklist.site_id,
                    command_name="monitoring.stage_checklist.item.verify",
                    command=command,
                    request_payload={"item_id": str(item_id)},
                )
                if not replayed:
                    if item.revision != command.expected_revision:
                        raise RevisionConflict(item.revision)
                    before = item.status
                    item.status = command.status
                    item.completion_note = command.note
                    item.completed_by = scope.actor_id
                    item.completed_at = datetime.now(UTC)
                    item.updated_by = scope.actor_id
                    item.revision += 1
                    checklist.revision += 1
                    checklist.updated_by = scope.actor_id
                    session.add(
                        StageChecklistHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=checklist.study_id,
                            site_id=checklist.site_id,
                            stage_checklist_id=checklist.id,
                            stage_checklist_item_id=item.id,
                            event_type="status_updated",
                            actor_id=scope.actor_id,
                            ordinal=self._next_history_ordinal(
                                session,
                                StageChecklistHistory,
                                parent_id=checklist.id,
                            ),
                            details={
                                "before": before,
                                "after": item.status,
                                "note": item.completion_note,
                                "center_close_approved": False,
                            },
                        )
                    )
                    self._audit(
                        session,
                        scope=scope,
                        study_id=checklist.study_id,
                        site_id=checklist.site_id,
                        action="monitoring.stage_checklist.item.verify",
                        resource_type="stage_checklist_item",
                        resource_id=item.id,
                        revision_before=command.expected_revision,
                        revision_after=item.revision,
                        after_state={
                            "status": item.status,
                            "center_close_approved": False,
                        },
                        command_name="monitoring.stage_checklist.item.verify",
                        correlation_id=record.id,
                    )
                    self._complete(record, checklist.id, checklist.revision)
            return self._checklist_detail_in_session(session, checklist)

    def handover_summary(
        self, scope: ScopeContext, visit_id: uuid.UUID
    ) -> HandoverSummary:
        visit = self.monitoring.visit(scope, visit_id)
        issue_details = self.issues.list_issues(
            scope, visit.study_id, visit.site_id
        )
        remaining = [
            detail
            for detail in issue_details
            if aggregate_action_status(detail.actions) != "completed"
        ]
        handover_issues = tuple(
            HandoverIssue(
                issue=detail,
                next_steps=tuple(
                    action.requirement
                    or f"继续跟进行动 {action.action_key}"
                    for action in detail.actions
                    if action.status not in {"completed", "reported_done"}
                )
                or ("复核原问题、当前进展及后续工作",),
            )
            for detail in remaining
        )
        checklist_items = [
            item
            for detail in self.stage_checklists(
                scope, visit.study_id, visit.site_id
            )
            for item in incomplete_checklist_items(detail.items)
        ]
        progress = [
            f"{detail.issue.issue_number}："
            f"{(detail.issue.known_progress or '进展待复核').strip()}"
            for detail in remaining
        ]
        summary = concise_handover_summary(
            len(remaining),
            progress,
            [item.title for item in checklist_items],
        )
        return HandoverSummary(
            visit_id=visit.id,
            study_id=visit.study_id,
            site_id=visit.site_id,
            generated_at=datetime.now(UTC),
            has_carryover=bool(remaining or checklist_items),
            summary=summary,
            issues=handover_issues,
            incomplete_checklist_items=tuple(checklist_items),
            center_close_approved=False,
        )
