"""Reusable template-driven review configuration and monitoring records."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
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
from cra_app.issues.service import IssueService
from cra_app.laboratory.service import LaboratoryService
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
from cra_app.monitoring.service import MonitoringService
from cra_app.monitoring.template_review import (
    ReviewTemplateExtraction,
    extract_report_template,
)
from cra_app.platform.jobs import digest_payload
from cra_app.rules.models import RuleVersion
from cra_app.subjects.models import Subject


@dataclass(frozen=True)
class TemplatePreview:
    source_document_version_id: uuid.UUID
    study_id: uuid.UUID
    site_id: uuid.UUID
    title: str
    extraction: ReviewTemplateExtraction


@dataclass(frozen=True)
class ReviewTemplateDetail:
    template: ReviewTemplateVersion
    items: tuple[ReviewTemplateItem, ...]


@dataclass(frozen=True)
class VisitReviewItemDetail:
    item: MonitoringReviewItem
    template_item: ReviewTemplateItem
    history: tuple[MonitoringReviewHistory, ...]


@dataclass(frozen=True)
class VisitReviewBoard:
    binding: MonitoringReviewBinding | None
    template: ReviewTemplateVersion | None
    items: tuple[VisitReviewItemDetail, ...]


class ReviewNotFound(Exception):
    pass


class ReviewValidationError(Exception):
    pass


class ReviewConflict(Exception):
    pass


class TemplateReviewService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService,
        documents: DocumentService,
        monitoring: MonitoringService,
        subjects,
        issues: IssueService,
        laboratory: LaboratoryService,
    ):
        self.session_factory = session_factory
        self.governance = governance
        self.documents = documents
        self.monitoring = monitoring
        self.subjects = subjects
        self.issues = issues
        self.laboratory = laboratory

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
            raise RuntimeError("failed to reserve review idempotency key")
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

    def preview_template(
        self, scope: ScopeContext, version_id: uuid.UUID
    ) -> TemplatePreview:
        stored = self.documents.read_content(scope, version_id)
        version = stored.version
        documents = self.documents.list_documents(
            scope, version.study_id, version.site_id
        )
        document = next(
            (item for item in documents if item.id == version.document_id),
            None,
        )
        if document is None:
            raise ReviewNotFound("template document was not found")
        if document.purpose != "template" or document.document_type != "template":
            raise ReviewValidationError(
                "review configuration requires a template-purpose document"
            )
        if version.media_type not in {
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
            "application/msword",
        } and not version.original_filename.lower().endswith(".docx"):
            raise ReviewValidationError(
                "this review-template extractor accepts DOCX documents only"
            )
        try:
            extraction = extract_report_template(stored.content)
        except ValueError as exc:
            raise ReviewValidationError(str(exc)) from exc
        return TemplatePreview(
            source_document_version_id=version.id,
            study_id=version.study_id,
            site_id=version.site_id,
            title=document.title,
            extraction=extraction,
        )

    def create_template(
        self, scope: ScopeContext, command: CreateReviewTemplateCommand
    ) -> ReviewTemplateDetail:
        preview = self.preview_template(
            scope, command.source_document_version_id
        )
        self.governance.authorize(
            scope, "write_site", preview.study_id, preview.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=preview.study_id,
                    site_id=preview.site_id,
                    command_name="monitoring.review_template.create",
                    command=command,
                )
                if replayed:
                    assert record.response_resource_id is not None
                    template = session.get(
                        ReviewTemplateVersion, record.response_resource_id
                    )
                    if template is None:
                        raise ReviewNotFound(
                            "replayed review template was not found"
                        )
                else:
                    template = ReviewTemplateVersion(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=preview.study_id,
                        site_id=preview.site_id,
                        source_document_version_id=(
                            command.source_document_version_id
                        ),
                        title=command.title,
                        structure_json={
                            "sections": list(preview.extraction.sections),
                            "question_count": len(command.items),
                        },
                        warnings=command.warnings,
                        revision=1,
                        created_by=scope.actor_id,
                    )
                    session.add(template)
                    session.flush()
                    for item in command.items:
                        session.add(
                            ReviewTemplateItem(
                                id=uuid.uuid4(),
                                tenant_id=scope.tenant_id,
                                study_id=preview.study_id,
                                site_id=preview.site_id,
                                review_template_version_id=template.id,
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
                        )
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=preview.study_id,
                            site_id=preview.site_id,
                            actor_id=scope.actor_id,
                            action="monitoring.review_template.create",
                            resource_type="review_template_version",
                            resource_id=template.id,
                            revision_before=None,
                            revision_after=template.revision,
                            before_state=None,
                            after_state={
                                "title": template.title,
                                "source_document_version_id": str(
                                    template.source_document_version_id
                                ),
                                "question_count": len(command.items),
                            },
                            command_name="monitoring.review_template.create",
                            correlation_id=record.id,
                        )
                    )
                    self._complete(record, template.id, template.revision)
            items = tuple(
                session.scalars(
                    select(ReviewTemplateItem)
                    .where(
                        ReviewTemplateItem.review_template_version_id
                        == template.id
                    )
                    .order_by(
                        ReviewTemplateItem.section_order,
                        ReviewTemplateItem.question_order,
                    )
                )
            )
            return ReviewTemplateDetail(template=template, items=items)

    def list_templates(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> list[ReviewTemplateDetail]:
        self.governance.authorize(scope, "read_site", study_id, site_id)
        with self.session_factory() as session:
            templates = list(
                session.scalars(
                    select(ReviewTemplateVersion)
                    .where(
                        ReviewTemplateVersion.tenant_id == scope.tenant_id,
                        ReviewTemplateVersion.study_id == study_id,
                        ReviewTemplateVersion.site_id == site_id,
                    )
                    .order_by(ReviewTemplateVersion.created_at.desc())
                )
            )
            result = []
            for template in templates:
                items = tuple(
                    session.scalars(
                        select(ReviewTemplateItem)
                        .where(
                            ReviewTemplateItem.review_template_version_id
                            == template.id
                        )
                        .order_by(
                            ReviewTemplateItem.section_order,
                            ReviewTemplateItem.question_order,
                        )
                    )
                )
                result.append(
                    ReviewTemplateDetail(template=template, items=items)
                )
            return result

    def bind_visit(
        self,
        scope: ScopeContext,
        visit_id: uuid.UUID,
        command: BindReviewTemplateCommand,
    ) -> VisitReviewBoard:
        visit = self.monitoring.visit(scope, visit_id)
        self.governance.authorize(
            scope, "write_site", visit.study_id, visit.site_id
        )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                template = session.scalar(
                    select(ReviewTemplateVersion).where(
                        ReviewTemplateVersion.id
                        == command.review_template_version_id,
                        ReviewTemplateVersion.tenant_id == scope.tenant_id,
                        ReviewTemplateVersion.study_id == visit.study_id,
                        ReviewTemplateVersion.site_id == visit.site_id,
                    )
                )
                if template is None:
                    raise ReviewNotFound("review template was not found")
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=visit.study_id,
                    site_id=visit.site_id,
                    command_name="monitoring.review_template.bind",
                    command=command,
                    request_payload={"visit_id": str(visit_id)},
                )
                existing = session.scalar(
                    select(MonitoringReviewBinding).where(
                        MonitoringReviewBinding.monitoring_visit_id == visit.id
                    )
                )
                if existing is not None:
                    if (
                        existing.review_template_version_id
                        != template.id
                    ):
                        raise ReviewConflict(
                            "monitoring visit already uses another review template"
                        )
                    return self._board(session, scope, visit.id)
                binding = MonitoringReviewBinding(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=visit.study_id,
                    site_id=visit.site_id,
                    monitoring_visit_id=visit.id,
                    review_template_version_id=template.id,
                    revision=1,
                    created_by=scope.actor_id,
                )
                session.add(binding)
                session.flush()
                template_items = list(
                    session.scalars(
                        select(ReviewTemplateItem)
                        .where(
                            ReviewTemplateItem.review_template_version_id
                            == template.id
                        )
                        .order_by(
                            ReviewTemplateItem.section_order,
                            ReviewTemplateItem.question_order,
                        )
                    )
                )
                for template_item in template_items:
                    item = MonitoringReviewItem(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=visit.study_id,
                        site_id=visit.site_id,
                        monitoring_visit_id=visit.id,
                        review_template_item_id=template_item.id,
                        subject_id=None,
                        linked_issue_id=None,
                        linked_comparison_id=None,
                        rule_version_ids=[],
                        status="not_checked",
                        note=None,
                        report_section=template_item.report_locator,
                        revision=1,
                        created_by=scope.actor_id,
                        updated_by=scope.actor_id,
                    )
                    session.add(item)
                    session.flush()
                    session.add(
                        MonitoringReviewHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=visit.study_id,
                            site_id=visit.site_id,
                            monitoring_review_item_id=item.id,
                            ordinal=1,
                            actor_id=scope.actor_id,
                            details={
                                "event": "initialized",
                                "status": "not_checked",
                            },
                        )
                    )
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=visit.study_id,
                        site_id=visit.site_id,
                        actor_id=scope.actor_id,
                        action="monitoring.review_template.bind",
                        resource_type="monitoring_review_binding",
                        resource_id=binding.id,
                        revision_before=None,
                        revision_after=binding.revision,
                        before_state=None,
                        after_state={
                            "visit_id": str(visit.id),
                            "review_template_version_id": str(template.id),
                            "item_count": len(template_items),
                        },
                        command_name="monitoring.review_template.bind",
                        correlation_id=record.id,
                    )
                )
                self._complete(record, binding.id, binding.revision)
            return self._board(session, scope, visit.id)

    def _board(
        self,
        session: Session,
        scope: ScopeContext,
        visit_id: uuid.UUID,
    ) -> VisitReviewBoard:
        binding = session.scalar(
            select(MonitoringReviewBinding).where(
                MonitoringReviewBinding.monitoring_visit_id == visit_id,
                MonitoringReviewBinding.tenant_id == scope.tenant_id,
            )
        )
        if binding is None:
            return VisitReviewBoard(binding=None, template=None, items=())
        template = session.get(
            ReviewTemplateVersion, binding.review_template_version_id
        )
        rows = session.execute(
            select(MonitoringReviewItem, ReviewTemplateItem)
            .join(
                ReviewTemplateItem,
                ReviewTemplateItem.id
                == MonitoringReviewItem.review_template_item_id,
            )
            .where(
                MonitoringReviewItem.monitoring_visit_id == visit_id,
                MonitoringReviewItem.tenant_id == scope.tenant_id,
            )
            .order_by(
                ReviewTemplateItem.section_order,
                ReviewTemplateItem.question_order,
            )
        ).all()
        items = []
        for item, template_item in rows:
            history = tuple(
                session.scalars(
                    select(MonitoringReviewHistory)
                    .where(
                        MonitoringReviewHistory.monitoring_review_item_id
                        == item.id
                    )
                    .order_by(MonitoringReviewHistory.ordinal)
                )
            )
            items.append(
                VisitReviewItemDetail(
                    item=item,
                    template_item=template_item,
                    history=history,
                )
            )
        return VisitReviewBoard(
            binding=binding,
            template=template,
            items=tuple(items),
        )

    def board(
        self, scope: ScopeContext, visit_id: uuid.UUID
    ) -> VisitReviewBoard:
        visit = self.monitoring.visit(scope, visit_id)
        self.governance.authorize(
            scope, "read_site", visit.study_id, visit.site_id
        )
        with self.session_factory() as session:
            return self._board(session, scope, visit_id)

    def update_item(
        self,
        scope: ScopeContext,
        item_id: uuid.UUID,
        command: UpdateMonitoringReviewItemCommand,
    ) -> VisitReviewItemDetail:
        with self.session_factory() as session:
            session.expire_on_commit = False
            item = session.scalar(
                select(MonitoringReviewItem).where(
                    MonitoringReviewItem.id == item_id,
                    MonitoringReviewItem.tenant_id == scope.tenant_id,
                )
            )
            if item is None:
                raise ReviewNotFound("monitoring review item was not found")
            self.governance.authorize(
                scope, "write_site", item.study_id, item.site_id
            )
            if command.subject_id is not None:
                subject = session.scalar(
                    select(Subject).where(
                        Subject.id == command.subject_id,
                        Subject.tenant_id == scope.tenant_id,
                        Subject.study_id == item.study_id,
                        Subject.site_id == item.site_id,
                    )
                )
                if subject is None:
                    raise ReviewValidationError(
                        "selected subject is outside the current site"
                    )
            if command.linked_issue_id is not None:
                try:
                    self.issues.issue_detail(scope, command.linked_issue_id)
                except Exception as exc:
                    raise ReviewValidationError(
                        "linked issue is outside the current authorized scope"
                    ) from exc
            if command.linked_comparison_id is not None:
                try:
                    comparison = self.laboratory.comparison_detail(
                        scope, command.linked_comparison_id
                    )
                except Exception as exc:
                    raise ReviewValidationError(
                        "linked comparison is outside the current authorized scope"
                    ) from exc
                if (
                    comparison.comparison.study_id != item.study_id
                    or comparison.comparison.site_id != item.site_id
                ):
                    raise ReviewValidationError(
                        "linked comparison is outside the current site"
                    )
            rule_ids = [str(value) for value in command.rule_version_ids]
            if rule_ids:
                count = session.scalar(
                    select(func.count())
                    .select_from(RuleVersion)
                    .where(
                        RuleVersion.id.in_(command.rule_version_ids),
                        RuleVersion.tenant_id == scope.tenant_id,
                        RuleVersion.study_id == item.study_id,
                    )
                )
                if count != len(rule_ids):
                    raise ReviewValidationError(
                        "one or more rule versions are outside the current study"
                    )
            session.rollback()
            with session.begin():
                item = session.scalar(
                    select(MonitoringReviewItem)
                    .where(MonitoringReviewItem.id == item_id)
                    .with_for_update()
                )
                if item is None:
                    raise ReviewNotFound("monitoring review item was not found")
                if item.revision != command.expected_revision:
                    raise RevisionConflict(item.revision)
                record, replayed = self._reserve(
                    session,
                    scope=scope,
                    study_id=item.study_id,
                    site_id=item.site_id,
                    command_name="monitoring.review_item.update",
                    command=command,
                    request_payload={"item_id": str(item.id)},
                )
                if not replayed:
                    before = {
                        "status": item.status,
                        "note": item.note,
                        "revision": item.revision,
                    }
                    item.status = command.status
                    item.note = command.note
                    item.subject_id = command.subject_id
                    item.rule_version_ids = rule_ids
                    item.linked_issue_id = command.linked_issue_id
                    item.linked_comparison_id = command.linked_comparison_id
                    item.revision += 1
                    item.updated_by = scope.actor_id
                    session.flush()
                    ordinal = int(
                        session.scalar(
                            select(
                                func.coalesce(
                                    func.max(MonitoringReviewHistory.ordinal), 0
                                )
                            ).where(
                                MonitoringReviewHistory.monitoring_review_item_id
                                == item.id
                            )
                        )
                        or 0
                    ) + 1
                    session.add(
                        MonitoringReviewHistory(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=item.study_id,
                            site_id=item.site_id,
                            monitoring_review_item_id=item.id,
                            ordinal=ordinal,
                            actor_id=scope.actor_id,
                            details={
                                "event": "updated",
                                "before": before,
                                "after": {
                                    "status": item.status,
                                    "note": item.note,
                                    "subject_id": (
                                        str(item.subject_id)
                                        if item.subject_id
                                        else None
                                    ),
                                    "rule_version_ids": item.rule_version_ids,
                                    "linked_issue_id": (
                                        str(item.linked_issue_id)
                                        if item.linked_issue_id
                                        else None
                                    ),
                                    "linked_comparison_id": (
                                        str(item.linked_comparison_id)
                                        if item.linked_comparison_id
                                        else None
                                    ),
                                    "revision": item.revision,
                                },
                            },
                        )
                    )
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=item.study_id,
                            site_id=item.site_id,
                            actor_id=scope.actor_id,
                            action="monitoring.review_item.update",
                            resource_type="monitoring_review_item",
                            resource_id=item.id,
                            revision_before=before["revision"],
                            revision_after=item.revision,
                            before_state=before,
                            after_state={
                                "status": item.status,
                                "note": item.note,
                                "revision": item.revision,
                            },
                            command_name="monitoring.review_item.update",
                            correlation_id=record.id,
                        )
                    )
                    self._complete(record, item.id, item.revision)
            template_item = session.scalar(
                select(ReviewTemplateItem).where(
                    ReviewTemplateItem.id == item.review_template_item_id
                )
            )
            if template_item is None:
                raise ReviewNotFound("template item was not found")
            history = tuple(
                session.scalars(
                    select(MonitoringReviewHistory)
                    .where(
                        MonitoringReviewHistory.monitoring_review_item_id
                        == item.id
                    )
                    .order_by(MonitoringReviewHistory.ordinal)
                )
            )
            session.refresh(item)
            session.refresh(template_item)
            return VisitReviewItemDetail(
                item=item,
                template_item=template_item,
                history=history,
            )

    def report_sections(
        self, scope: ScopeContext, visit_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        board = self.board(scope, visit_id)
        grouped: dict[str, dict[str, Any]] = {}
        for detail in board.items:
            item = detail.item
            template_item = detail.template_item
            section = grouped.setdefault(
                template_item.section_key,
                {
                    "section_key": template_item.section_key,
                    "section_title": template_item.section_title,
                    "items": [],
                },
            )
            section["items"].append(
                {
                    "item_key": template_item.item_key,
                    "question": template_item.question_text,
                    "status": item.status,
                    "note": item.note or "",
                    "source_locator": template_item.source_locator,
                    "report_locator": template_item.report_locator,
                    "linked_issue_id": (
                        str(item.linked_issue_id)
                        if item.linked_issue_id
                        else None
                    ),
                    "linked_comparison_id": (
                        str(item.linked_comparison_id)
                        if item.linked_comparison_id
                        else None
                    ),
                }
            )
        return list(grouped.values())
