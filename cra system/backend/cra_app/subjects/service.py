"""Authorized subject facts, visit windows, coverage and local skips."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, exists, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.governance.models import AuditEvent, IdempotencyRecord
from cra_app.governance.service import (
    GovernanceService,
    IdempotencyConflict,
    RevisionConflict,
    ScopeContext,
)
from cra_app.platform.jobs import digest_payload
from cra_app.rules.contracts import FactValue
from cra_app.rules.service import (
    ApplicableRuleQuery,
    RuleService,
)
from cra_app.shared.output_contract import (
    Claim,
    ConflictItem,
    InputRevision,
    NotCheckedItem,
    OutputCapability,
    OutputEnvelope,
    OutputScope,
    SourceRef,
    UnknownItem,
)
from cra_app.subjects.calendar import (
    DateIntervalSpec,
    DateWindow,
    current_stage,
    extract_date_interval_specs,
)
from cra_app.subjects.contracts import (
    CheckDecisionCommand,
    ConfirmFactCommand,
    CoverageBreakpointCommand,
    CreateSubjectCommand,
    FactImportRow,
    FactSourceKind,
    ImportFactsCommand,
    MapSubjectIdentifierCommand,
    NormalizedFactValue,
    ResumeCheckDecisionCommand,
)
from cra_app.subjects.models import (
    CheckDecision,
    ClinicalFact,
    CoverageBreakpoint,
    FactChangeImpact,
    Subject,
    SubjectIdentifier,
    VisitInstance,
    VisitRequirement,
)


class SubjectServiceError(Exception):
    pass


class SubjectNotFound(SubjectServiceError):
    pass


class SubjectValidationError(SubjectServiceError):
    pass


class SubjectConflict(SubjectServiceError):
    pass


class EvaluateVisitRequirementsCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_date: date
    jurisdiction: str = Field(default="synthetic", min_length=1, max_length=64)


@dataclass(frozen=True)
class ImportOutcome:
    subject_ids: tuple[uuid.UUID, ...]
    inserted_facts: int
    superseded_facts: int
    replayed: bool


@dataclass(frozen=True)
class SubjectSummary:
    subject: Subject
    current_stage: str
    identifiers: tuple[SubjectIdentifier, ...]


@dataclass(frozen=True)
class TimelineItem:
    fact: ClinicalFact
    is_current: bool


@dataclass(frozen=True)
class RequirementItem:
    requirement: VisitRequirement
    rule_summary: str
    window_status: str


@dataclass(frozen=True)
class VisitRequirementOutcome:
    envelope: OutputEnvelope
    requirements: tuple[RequirementItem, ...]
    instances: tuple[VisitInstance, ...]


def _json_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_status(source_kind: str) -> str:
    return {
        "original_record": "original_record",
        "cra_confirmation": "cra_confirmed",
        "other_response": "reported_by_other",
        "model_suggestion": "model_candidate",
    }[source_kind]


def _normalize_value(row: FactImportRow) -> NormalizedFactValue:
    raw = row.value_raw.strip()
    value_type = row.value_type
    if value_type is None:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            value_type = "date"
        elif re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?"
            r"(?:Z|[+-]\d{2}:\d{2})",
            raw,
        ):
            value_type = "datetime"
        elif raw.casefold() in {"true", "false"}:
            value_type = "boolean"
        elif re.fullmatch(r"[-+]?\d+(?:\.\d+)?", raw):
            value_type = "decimal"
        elif raw[:1] in {"{", "["}:
            try:
                json.loads(raw)
                value_type = "json"
            except json.JSONDecodeError:
                value_type = "string"
        else:
            value_type = "string"

    if value_type == "date":
        try:
            parsed_date = date.fromisoformat(raw)
        except ValueError as exc:
            raise SubjectValidationError("date value must use YYYY-MM-DD") from exc
        value: Any = parsed_date.isoformat()
        precision = row.precision or "date"
    elif value_type == "datetime":
        try:
            parsed_datetime = datetime.fromisoformat(
                raw.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise SubjectValidationError("datetime value is not ISO 8601") from exc
        if parsed_datetime.tzinfo is None:
            raise SubjectValidationError(
                "datetime values require an explicit UTC offset"
            )
        value = parsed_datetime.isoformat()
        precision = row.precision or (
            "second" if parsed_datetime.second else "minute"
        )
    elif value_type == "decimal":
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise SubjectValidationError("decimal value is invalid") from exc
        value = format(number, "f")
        precision = row.precision or "unknown"
    elif value_type == "boolean":
        if raw.casefold() not in {"true", "false"}:
            raise SubjectValidationError("boolean values must be true or false")
        value = raw.casefold() == "true"
        precision = row.precision or "unknown"
    elif value_type == "json":
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SubjectValidationError("JSON fact value is invalid") from exc
        precision = row.precision or "unknown"
    else:
        value = raw
        precision = row.precision or "unknown"
    return NormalizedFactValue(
        value_type=value_type,
        value=value,
        precision=precision,
    )


def _date_from_fact(fact: ClinicalFact | None) -> date | None:
    if fact is None:
        return None
    if fact.value_type == "date":
        return date.fromisoformat(fact.value_raw)
    if fact.value_type == "datetime":
        return datetime.fromisoformat(fact.value_raw).date()
    return None


class SubjectService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        governance: GovernanceService | None = None,
        rules: RuleService | None = None,
    ):
        self.session_factory = session_factory
        self.governance = governance or GovernanceService(session_factory)
        self.rules = rules or RuleService(
            session_factory, governance=self.governance
        )

    def _authorize_write(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(
            scope, "write_site", study_id, site_id
        )

    def _authorize_read(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> None:
        self.governance.authorize(scope, "read_site", study_id, site_id)

    def _scope_fingerprint(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID | None
    ) -> str:
        return digest_payload(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id),
                "site_id": str(site_id) if site_id else None,
            }
        )

    def _reserve_idempotency(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID | None,
        command_name: str,
        command: BaseModel,
        request_payload: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        scope_fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = digest_payload(
            {
                "command_name": command_name,
                "scope_fingerprint": scope_fingerprint,
                "command": command.model_dump(mode="json"),
                "request": request_payload,
            }
        )
        record_id = uuid.uuid4()
        session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                id=record_id,
                actor_id=scope.actor_id,
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                scope_fingerprint=scope_fingerprint,
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
                IdempotencyRecord.scope_fingerprint == scope_fingerprint,
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
    def _complete_idempotency(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    def _load_subject(
        self, scope: ScopeContext, subject_id: uuid.UUID
    ) -> Subject:
        with self.session_factory() as session:
            subject = session.scalar(
                select(Subject).where(
                    Subject.id == subject_id,
                    Subject.tenant_id == scope.tenant_id,
                )
            )
            if subject is None:
                raise SubjectNotFound("subject was not found")
            return subject

    def _subject_identifiers(
        self, session: Session, subject_id: uuid.UUID
    ) -> list[SubjectIdentifier]:
        return list(
            session.scalars(
                select(SubjectIdentifier)
                .where(SubjectIdentifier.subject_id == subject_id)
                .order_by(
                    SubjectIdentifier.identity_namespace,
                    SubjectIdentifier.external_id,
                )
            )
        )

    def list_subjects(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> list[SubjectSummary]:
        self._authorize_read(scope, study_id, site_id)
        with self.session_factory() as session:
            subjects = list(
                session.scalars(
                    select(Subject)
                    .where(
                        Subject.tenant_id == scope.tenant_id,
                        Subject.study_id == study_id,
                        Subject.site_id == site_id,
                    )
                    .order_by(Subject.deidentified_label)
                )
            )
            result = []
            for subject in subjects:
                facts = self._eligible_singleton_facts(session, subject.id)
                stage = current_stage(
                    {
                        key: str(fact.value_raw)
                        for key, fact in facts.items()
                    }
                )
                result.append(
                    SubjectSummary(
                        subject=subject,
                        current_stage=stage,
                        identifiers=tuple(
                            self._subject_identifiers(session, subject.id)
                        ),
                    )
                )
            return result

    def create_subject(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateSubjectCommand,
    ) -> Subject:
        self._authorize_write(scope, study_id, command.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=command.site_id,
                    command_name="subjects.create",
                    command=command,
                    request_payload={},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    subject = session.get(Subject, record.response_resource_id)
                    assert subject is not None
                    return subject
                existing = session.scalar(
                    select(SubjectIdentifier).where(
                        SubjectIdentifier.tenant_id == scope.tenant_id,
                        SubjectIdentifier.study_id == study_id,
                        SubjectIdentifier.site_id == command.site_id,
                        SubjectIdentifier.identity_namespace
                        == command.identity_namespace,
                        SubjectIdentifier.external_id == command.external_id,
                    )
                )
                if existing is not None:
                    raise SubjectConflict(
                        "subject identifier already exists"
                    )
                subject = Subject(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=study_id,
                    site_id=command.site_id,
                    deidentified_label=(
                        command.deidentified_label or command.external_id
                    ),
                    revision=1,
                    created_by=scope.actor_id,
                    updated_by=scope.actor_id,
                )
                session.add(subject)
                session.flush()
                session.add(
                    SubjectIdentifier(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        subject_id=subject.id,
                        identity_namespace=command.identity_namespace,
                        external_id=command.external_id,
                        created_by=scope.actor_id,
                    )
                )
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        actor_id=scope.actor_id,
                        action="subjects.create",
                        resource_type="subject",
                        resource_id=subject.id,
                        revision_before=None,
                        revision_after=1,
                        before_state=None,
                        after_state={
                            "identity_namespace": command.identity_namespace,
                            "external_id": command.external_id,
                            "deidentified_label": subject.deidentified_label,
                        },
                        command_name="subjects.create",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, subject.id, subject.revision)
                return subject

    def map_identifier(
        self,
        scope: ScopeContext,
        subject_id: uuid.UUID,
        command: MapSubjectIdentifierCommand,
    ) -> SubjectIdentifier:
        subject = self._load_subject(scope, subject_id)
        self._authorize_write(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                current_subject = session.scalar(
                    select(Subject)
                    .where(
                        Subject.id == subject_id,
                        Subject.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if current_subject is None:
                    raise SubjectNotFound("subject was not found")
                if current_subject.revision != command.expected_revision:
                    raise RevisionConflict(current_subject.revision)
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    command_name="subjects.identifier.map",
                    command=command,
                    request_payload={"subject_id": str(subject_id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    identifier = session.get(
                        SubjectIdentifier, record.response_resource_id
                    )
                    assert identifier is not None
                    return identifier
                duplicate = session.scalar(
                    select(SubjectIdentifier).where(
                        SubjectIdentifier.tenant_id == scope.tenant_id,
                        SubjectIdentifier.study_id == subject.study_id,
                        SubjectIdentifier.site_id == subject.site_id,
                        SubjectIdentifier.identity_namespace
                        == command.identity_namespace,
                        SubjectIdentifier.external_id == command.external_id,
                    )
                )
                if duplicate is not None:
                    raise SubjectConflict("subject identifier already mapped")
                identifier = SubjectIdentifier(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    subject_id=subject.id,
                    identity_namespace=command.identity_namespace,
                    external_id=command.external_id,
                    created_by=scope.actor_id,
                )
                session.add(identifier)
                current_subject.revision += 1
                current_subject.updated_by = scope.actor_id
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=subject.study_id,
                        site_id=subject.site_id,
                        actor_id=scope.actor_id,
                        action="subjects.identifier.map",
                        resource_type="subject",
                        resource_id=subject.id,
                        revision_before=command.expected_revision,
                        revision_after=current_subject.revision,
                        before_state=None,
                        after_state={
                            "identity_namespace": command.identity_namespace,
                            "external_id": command.external_id,
                        },
                        command_name="subjects.identifier.map",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, identifier.id, current_subject.revision
                )
                return identifier

    def _find_or_create_subject(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        namespace: str,
        external_id: str,
        deidentified_label: str | None = None,
    ) -> Subject:
        identifier = session.scalar(
            select(SubjectIdentifier).where(
                SubjectIdentifier.tenant_id == scope.tenant_id,
                SubjectIdentifier.study_id == study_id,
                SubjectIdentifier.site_id == site_id,
                SubjectIdentifier.identity_namespace == namespace,
                SubjectIdentifier.external_id == external_id,
            )
        )
        if identifier is not None:
            subject = session.get(Subject, identifier.subject_id)
            assert subject is not None
            return subject
        subject = Subject(
            id=uuid.uuid4(),
            tenant_id=scope.tenant_id,
            study_id=study_id,
            site_id=site_id,
            deidentified_label=deidentified_label or external_id,
            revision=1,
            created_by=scope.actor_id,
            updated_by=scope.actor_id,
        )
        session.add(subject)
        session.flush()
        session.add(
            SubjectIdentifier(
                id=uuid.uuid4(),
                tenant_id=scope.tenant_id,
                study_id=study_id,
                site_id=site_id,
                subject_id=subject.id,
                identity_namespace=namespace,
                external_id=external_id,
                created_by=scope.actor_id,
            )
        )
        return subject

    def _mark_fact_dependents_for_review(
        self,
        session: Session,
        *,
        subject: Subject,
        fact_key: str,
        old_fact: ClinicalFact | None,
        new_fact: ClinicalFact,
    ) -> int:
        requirements = list(
            session.scalars(
                select(VisitRequirement).where(
                    VisitRequirement.tenant_id == subject.tenant_id,
                    VisitRequirement.study_id == subject.study_id,
                    VisitRequirement.subject_id == subject.id,
                    VisitRequirement.input_fact_keys.contains([fact_key]),
                )
            )
        )
        for requirement in requirements:
            requirement.status = "needs_review"
            session.add(
                FactChangeImpact(
                    id=uuid.uuid4(),
                    tenant_id=subject.tenant_id,
                    study_id=subject.study_id,
                    subject_id=subject.id,
                    old_fact_id=old_fact.id if old_fact else None,
                    new_fact_id=new_fact.id,
                    dependent_type="visit_requirement",
                    dependent_id=requirement.id,
                    status="needs_review",
                    reason=f"fact {fact_key} received a new revision",
                )
            )
        decisions = list(
            session.scalars(
                select(CheckDecision).where(
                    CheckDecision.tenant_id == subject.tenant_id,
                    CheckDecision.study_id == subject.study_id,
                    CheckDecision.subject_id == subject.id,
                    CheckDecision.state == "active",
                    CheckDecision.missing_keys.contains([fact_key]),
                )
            )
        )
        fact_event_date = (
            _date_from_fact(new_fact)
            or new_fact.observed_on
            or (new_fact.observed_at.date() if new_fact.observed_at else None)
        )
        for decision in decisions:
            if (
                fact_event_date is not None
                and decision.scope_start is not None
                and fact_event_date < decision.scope_start
            ):
                continue
            if (
                fact_event_date is not None
                and decision.scope_end is not None
                and fact_event_date > decision.scope_end
            ):
                continue
            decision.recovery_available = True
            decision.recovery_detected_at = datetime.now(UTC)
            session.add(
                FactChangeImpact(
                    id=uuid.uuid4(),
                    tenant_id=subject.tenant_id,
                    study_id=subject.study_id,
                    subject_id=subject.id,
                    old_fact_id=old_fact.id if old_fact else None,
                    new_fact_id=new_fact.id,
                    dependent_type="check_decision",
                    dependent_id=decision.id,
                    status="needs_review",
                    reason=(
                        f"missing fact {fact_key} is now available; user "
                        "decision remains active until explicit resume"
                    ),
                )
            )
        return len(requirements) + len(decisions)

    def _sync_visit_instance(
        self,
        session: Session,
        *,
        subject: Subject,
        fact: ClinicalFact,
        row: FactImportRow,
    ) -> None:
        if fact.fact_key not in {"visit_date", "planned_visit_date"}:
            return
        visit_key = row.visit_key or row.repeat_instance or "_"
        repeat_instance = row.repeat_instance or "_"
        current = session.scalar(
            select(VisitInstance)
            .where(
                VisitInstance.tenant_id == subject.tenant_id,
                VisitInstance.study_id == subject.study_id,
                VisitInstance.subject_id == subject.id,
                VisitInstance.visit_key == visit_key,
                VisitInstance.repeat_instance == repeat_instance,
            )
            .order_by(VisitInstance.revision.desc())
            .limit(1)
        )
        revision = (current.revision + 1) if current else 1
        actual_fact_id = (
            fact.id
            if fact.fact_key == "visit_date"
            else (current.actual_fact_id if current else None)
        )
        planned_fact_id = (
            fact.id
            if fact.fact_key == "planned_visit_date"
            else (current.planned_fact_id if current else None)
        )
        actual_on = (
            _date_from_fact(fact)
            if fact.fact_key == "visit_date"
            else (current.actual_on if current else None)
        )
        planned_on = (
            _date_from_fact(fact)
            if fact.fact_key == "planned_visit_date"
            else (current.planned_on if current else None)
        )
        session.add(
            VisitInstance(
                id=uuid.uuid4(),
                tenant_id=subject.tenant_id,
                study_id=subject.study_id,
                site_id=subject.site_id,
                subject_id=subject.id,
                visit_key=visit_key,
                repeat_instance=repeat_instance,
                stage=None,
                planned_fact_id=planned_fact_id,
                actual_fact_id=actual_fact_id,
                planned_on=planned_on,
                actual_on=actual_on,
                precision=fact.precision,
                revision=revision,
                supersedes_visit_id=current.id if current else None,
                created_by=fact.created_by,
            )
        )

    def import_facts(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: ImportFactsCommand,
    ) -> ImportOutcome:
        self._authorize_write(scope, study_id, command.site_id)
        inserted = superseded = 0
        subject_ids: set[uuid.UUID] = set()
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=command.site_id,
                    command_name="facts.import",
                    command=command,
                    request_payload={},
                )
                if replayed:
                    identifiers = list(
                        session.scalars(
                            select(SubjectIdentifier).where(
                                SubjectIdentifier.tenant_id == scope.tenant_id,
                                SubjectIdentifier.study_id == study_id,
                                SubjectIdentifier.site_id == command.site_id,
                                SubjectIdentifier.identity_namespace
                                == command.identity_namespace,
                                SubjectIdentifier.external_id.in_(
                                    {
                                        row.subject_external_id
                                        for row in command.rows
                                    }
                                ),
                            )
                        )
                    )
                    return ImportOutcome(
                        subject_ids=tuple(
                            sorted({item.subject_id for item in identifiers})
                        ),
                        inserted_facts=0,
                        superseded_facts=0,
                        replayed=True,
                    )
                for row in command.rows:
                    effective_source: FactSourceKind = (
                        command.source_kind
                        if command.source_kind != "original_record"
                        else row.source_kind
                    )
                    verification_status = _source_status(effective_source)
                    normalized = _normalize_value(row)
                    subject = self._find_or_create_subject(
                        session,
                        scope=scope,
                        study_id=study_id,
                        site_id=command.site_id,
                        namespace=command.identity_namespace,
                        external_id=row.subject_external_id,
                    )
                    subject_ids.add(subject.id)
                    repeat_instance = row.repeat_instance or "_"
                    old_fact = session.scalar(
                        select(ClinicalFact)
                        .where(
                            ClinicalFact.tenant_id == scope.tenant_id,
                            ClinicalFact.study_id == study_id,
                            ClinicalFact.subject_id == subject.id,
                            ClinicalFact.fact_key == row.fact_key,
                            ClinicalFact.repeat_instance == repeat_instance,
                        )
                        .order_by(ClinicalFact.revision.desc())
                        .limit(1)
                    )
                    if (
                        old_fact is not None
                        and old_fact.value_raw == row.value_raw
                        and old_fact.observed_on == row.observed_on
                        and old_fact.observed_at == row.observed_at
                        and old_fact.source_kind == effective_source
                        and old_fact.verification_status == verification_status
                    ):
                        continue
                    revision = (old_fact.revision + 1) if old_fact else 1
                    fact = ClinicalFact(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=study_id,
                        site_id=command.site_id,
                        subject_id=subject.id,
                        fact_key=row.fact_key,
                        repeat_instance=repeat_instance,
                        revision=revision,
                        value_type=normalized.value_type,
                        value_json=normalized.value,
                        value_raw=row.value_raw,
                        unit=row.unit,
                        observed_on=row.observed_on,
                        observed_at=row.observed_at,
                        precision=(
                            row.precision
                            or normalized.precision
                        ),
                        source_kind=effective_source,
                        verification_status=verification_status,
                        source_ref=row.source_ref.model_dump(
                            mode="json", exclude_none=True
                        ),
                        supersedes_fact_id=old_fact.id if old_fact else None,
                        created_by=scope.actor_id,
                    )
                    session.add(fact)
                    session.flush()
                    inserted += 1
                    if old_fact is not None:
                        superseded += 1
                    affected = (
                        self._mark_fact_dependents_for_review(
                            session,
                            subject=subject,
                            fact_key=fact.fact_key,
                            old_fact=old_fact,
                            new_fact=fact,
                        )
                        if fact.verification_status
                        in {"original_record", "cra_confirmed"}
                        else 0
                    )
                    self._sync_visit_instance(
                        session, subject=subject, fact=fact, row=row
                    )
                    session.add(
                        AuditEvent(
                            id=uuid.uuid4(),
                            tenant_id=scope.tenant_id,
                            study_id=study_id,
                            site_id=command.site_id,
                            actor_id=scope.actor_id,
                            action="facts.import",
                            resource_type="clinical_fact",
                            resource_id=fact.id,
                            revision_before=(
                                old_fact.revision if old_fact else None
                            ),
                            revision_after=fact.revision,
                            before_state=(
                                {
                                    "fact_id": str(old_fact.id),
                                    "value_raw": old_fact.value_raw,
                                }
                                if old_fact
                                else None
                            ),
                            after_state={
                                "subject_id": str(subject.id),
                                "fact_key": fact.fact_key,
                                "repeat_instance": fact.repeat_instance,
                                "value_raw": fact.value_raw,
                                "value_type": fact.value_type,
                                "precision": fact.precision,
                                "source_kind": fact.source_kind,
                                "affected_dependents": affected,
                            },
                            command_name="facts.import",
                            correlation_id=record.id,
                        )
                    )
                if not subject_ids:
                    raise SubjectValidationError("import contained no new facts")
                first_subject = sorted(subject_ids)[0]
                self._complete_idempotency(record, first_subject, 1)
        return ImportOutcome(
            subject_ids=tuple(sorted(subject_ids)),
            inserted_facts=inserted,
            superseded_facts=superseded,
            replayed=False,
        )

    def _current_facts(
        self, session: Session, subject_id: uuid.UUID
    ) -> dict[tuple[str, str], ClinicalFact]:
        facts = list(
            session.scalars(
                select(ClinicalFact)
                .where(ClinicalFact.subject_id == subject_id)
                .order_by(
                    ClinicalFact.fact_key,
                    ClinicalFact.repeat_instance,
                    ClinicalFact.revision.desc(),
                )
            )
        )
        current: dict[tuple[str, str], ClinicalFact] = {}
        for fact in facts:
            current.setdefault((fact.fact_key, fact.repeat_instance), fact)
        return current

    def timeline(
        self, scope: ScopeContext, subject_id: uuid.UUID
    ) -> list[TimelineItem]:
        subject = self._load_subject(scope, subject_id)
        self._authorize_read(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            facts = list(
                session.scalars(
                    select(ClinicalFact)
                    .where(
                        ClinicalFact.tenant_id == scope.tenant_id,
                        ClinicalFact.study_id == subject.study_id,
                        ClinicalFact.subject_id == subject.id,
                    )
                    .order_by(
                        ClinicalFact.observed_on.asc().nulls_last(),
                        ClinicalFact.observed_at.asc().nulls_last(),
                        ClinicalFact.fact_key,
                        ClinicalFact.revision.desc(),
                    )
                )
            )
            current = self._current_facts(session, subject.id)
            current_ids = {fact.id for fact in current.values()}
            return [
                TimelineItem(fact=fact, is_current=fact.id in current_ids)
                for fact in facts
            ]

    def confirm_fact(
        self,
        scope: ScopeContext,
        fact_id: uuid.UUID,
        command: ConfirmFactCommand,
    ) -> ClinicalFact:
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                source_fact = session.scalar(
                    select(ClinicalFact)
                    .where(
                        ClinicalFact.id == fact_id,
                        ClinicalFact.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if source_fact is None:
                    raise SubjectNotFound("clinical fact was not found")
                subject = session.get(Subject, source_fact.subject_id)
                assert subject is not None
                self._authorize_write(scope, subject.study_id, subject.site_id)
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    command_name="facts.confirm",
                    command=command,
                    request_payload={"fact_id": str(fact_id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    existing_fact = session.get(
                        ClinicalFact, record.response_resource_id
                    )
                    assert existing_fact is not None
                    return existing_fact
                current = session.scalar(
                    select(ClinicalFact)
                    .where(
                        ClinicalFact.subject_id == subject.id,
                        ClinicalFact.fact_key == source_fact.fact_key,
                        ClinicalFact.repeat_instance
                        == source_fact.repeat_instance,
                    )
                    .order_by(ClinicalFact.revision.desc())
                    .limit(1)
                )
                if current is not None and current.revision != command.expected_revision:
                    raise RevisionConflict(current.revision)
                if (
                    current is not None
                    and current.verification_status == "cra_confirmed"
                ):
                    self._complete_idempotency(
                        record, current.id, current.revision
                    )
                    return current
                revision = (current.revision + 1) if current else 1
                confirmed = ClinicalFact(
                    id=uuid.uuid4(),
                    tenant_id=source_fact.tenant_id,
                    study_id=source_fact.study_id,
                    site_id=source_fact.site_id,
                    subject_id=source_fact.subject_id,
                    fact_key=source_fact.fact_key,
                    repeat_instance=source_fact.repeat_instance,
                    revision=revision,
                    value_type=source_fact.value_type,
                    value_json=source_fact.value_json,
                    value_raw=source_fact.value_raw,
                    unit=source_fact.unit,
                    observed_on=source_fact.observed_on,
                    observed_at=source_fact.observed_at,
                    precision=source_fact.precision,
                    source_kind="cra_confirmation",
                    verification_status="cra_confirmed",
                    source_ref={
                        "source_type": "user_action",
                        "source_id": str(source_fact.id),
                        "locator": command.note,
                    },
                    supersedes_fact_id=current.id if current else None,
                    created_by=scope.actor_id,
                )
                session.add(confirmed)
                session.flush()
                self._mark_fact_dependents_for_review(
                    session,
                    subject=subject,
                    fact_key=confirmed.fact_key,
                    old_fact=current,
                    new_fact=confirmed,
                )
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=subject.study_id,
                        site_id=subject.site_id,
                        actor_id=scope.actor_id,
                        action="facts.confirm",
                        resource_type="clinical_fact",
                        resource_id=confirmed.id,
                        revision_before=(
                            current.revision if current else None
                        ),
                        revision_after=confirmed.revision,
                        before_state=(
                            {"fact_id": str(current.id)}
                            if current
                            else None
                        ),
                        after_state={
                            "source_fact_id": str(source_fact.id),
                            "fact_key": confirmed.fact_key,
                            "verification_status": "cra_confirmed",
                            "note": command.note,
                        },
                        command_name="facts.confirm",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, confirmed.id, confirmed.revision
                )
                return confirmed

    def _latest_coverage(
        self,
        session: Session,
        *,
        subject_id: uuid.UUID,
        category: str,
        scope_key: str,
    ) -> CoverageBreakpoint | None:
        return session.scalar(
            select(CoverageBreakpoint)
            .where(
                CoverageBreakpoint.subject_id == subject_id,
                CoverageBreakpoint.category == category,
                CoverageBreakpoint.scope_key == scope_key,
            )
            .order_by(CoverageBreakpoint.revision.desc())
            .limit(1)
        )

    def save_coverage(
        self,
        scope: ScopeContext,
        subject_id: uuid.UUID,
        command: CoverageBreakpointCommand,
    ) -> CoverageBreakpoint:
        subject = self._load_subject(scope, subject_id)
        self._authorize_write(scope, subject.study_id, subject.site_id)
        if command.status == "complete" and command.unverified_scope:
            raise SubjectValidationError(
                "complete coverage cannot contain unverified scope"
            )
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    command_name="coverage.save",
                    command=command,
                    request_payload={"subject_id": str(subject_id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    coverage = session.get(
                        CoverageBreakpoint, record.response_resource_id
                    )
                    assert coverage is not None
                    return coverage
                latest = self._latest_coverage(
                    session,
                    subject_id=subject_id,
                    category=command.category,
                    scope_key=command.scope_key,
                )
                actual_revision = latest.revision if latest else 0
                if actual_revision != command.expected_revision:
                    raise RevisionConflict(actual_revision)
                coverage = CoverageBreakpoint(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    subject_id=subject_id,
                    category=command.category,
                    scope_key=command.scope_key,
                    revision=actual_revision + 1,
                    status=command.status,
                    checked_through=command.checked_through,
                    normal_scope_note=command.normal_scope_note,
                    unverified_scope=command.unverified_scope,
                    supersedes_breakpoint_id=latest.id if latest else None,
                    created_by=scope.actor_id,
                )
                session.add(coverage)
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=subject.study_id,
                        site_id=subject.site_id,
                        actor_id=scope.actor_id,
                        action="coverage.save",
                        resource_type="coverage_breakpoint",
                        resource_id=coverage.id,
                        revision_before=actual_revision or None,
                        revision_after=coverage.revision,
                        before_state=(
                            {
                                "coverage_id": str(latest.id),
                                "category": latest.category,
                                "scope_key": latest.scope_key,
                                "status": latest.status,
                            }
                            if latest
                            else None
                        ),
                        after_state={
                            "subject_id": str(subject_id),
                            "category": coverage.category,
                            "scope_key": coverage.scope_key,
                            "status": coverage.status,
                            "checked_through": coverage.checked_through,
                        },
                        command_name="coverage.save",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, coverage.id, coverage.revision
                )
                return coverage

    def list_coverage(
        self, scope: ScopeContext, subject_id: uuid.UUID
    ) -> list[CoverageBreakpoint]:
        subject = self._load_subject(scope, subject_id)
        self._authorize_read(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(CoverageBreakpoint)
                    .where(
                        CoverageBreakpoint.tenant_id == scope.tenant_id,
                        CoverageBreakpoint.study_id == subject.study_id,
                        CoverageBreakpoint.subject_id == subject.id,
                    )
                    .order_by(
                        CoverageBreakpoint.category,
                        CoverageBreakpoint.scope_key,
                        CoverageBreakpoint.revision.desc(),
                    )
                )
            )
            result = []
            seen: set[tuple[str, str]] = set()
            for row in rows:
                key = (row.category, row.scope_key)
                if key in seen:
                    continue
                seen.add(key)
                result.append(row)
            return result

    def decide_not_checked(
        self,
        scope: ScopeContext,
        subject_id: uuid.UUID,
        command: CheckDecisionCommand,
    ) -> CheckDecision:
        subject = self._load_subject(scope, subject_id)
        self._authorize_write(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    command_name="check_decisions.create",
                    command=command,
                    request_payload={"subject_id": str(subject_id)},
                )
                if replayed:
                    assert record.response_resource_id is not None
                    decision = session.get(CheckDecision, record.response_resource_id)
                    assert decision is not None
                    return decision
                existing_decisions = list(
                    session.scalars(
                        select(CheckDecision).where(
                            CheckDecision.tenant_id == scope.tenant_id,
                            CheckDecision.study_id == subject.study_id,
                            CheckDecision.subject_id == subject.id,
                            CheckDecision.category == command.category,
                            CheckDecision.check_type == command.check_type,
                            CheckDecision.state == "active",
                        )
                    )
                )
                for existing in existing_decisions:
                    same_scope = (
                        existing.scope_start == command.scope_start
                        and existing.scope_end == command.scope_end
                    )
                    same_rule = (
                        existing.rule_version_id == command.rule_version_id
                    )
                    if (
                        same_scope
                        and same_rule
                        and set(existing.missing_keys)
                        == set(command.missing_keys)
                        and existing.reason == command.reason
                    ):
                        self._complete_idempotency(
                            record, existing.id, existing.revision
                        )
                        return existing
                decision = CheckDecision(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    subject_id=subject.id,
                    category=command.category,
                    check_type=command.check_type,
                    reason=command.reason,
                    scope_start=command.scope_start,
                    scope_end=command.scope_end,
                    missing_keys=command.missing_keys,
                    affected_paths=command.affected_paths,
                    can_continue=command.can_continue,
                    rule_version_id=command.rule_version_id,
                    state="active",
                    revision=1,
                    recovery_available=False,
                    created_by=scope.actor_id,
                )
                session.add(decision)
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=subject.study_id,
                        site_id=subject.site_id,
                        actor_id=scope.actor_id,
                        action="check_decisions.create",
                        resource_type="check_decision",
                        resource_id=decision.id,
                        revision_before=None,
                        revision_after=1,
                        before_state=None,
                        after_state={
                            "category": decision.category,
                            "check_type": decision.check_type,
                            "reason": decision.reason,
                            "missing_keys": decision.missing_keys,
                            "affected_paths": decision.affected_paths,
                            "scope_start": (
                                decision.scope_start.isoformat()
                                if decision.scope_start
                                else None
                            ),
                            "scope_end": (
                                decision.scope_end.isoformat()
                                if decision.scope_end
                                else None
                            ),
                        },
                        command_name="check_decisions.create",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, decision.id, decision.revision)
                return decision

    def resume_check_decision(
        self,
        scope: ScopeContext,
        subject_id: uuid.UUID,
        decision_id: uuid.UUID,
        command: ResumeCheckDecisionCommand,
    ) -> CheckDecision:
        subject = self._load_subject(scope, subject_id)
        self._authorize_write(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                decision = session.scalar(
                    select(CheckDecision)
                    .where(
                        CheckDecision.id == decision_id,
                        CheckDecision.subject_id == subject.id,
                        CheckDecision.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if decision is None:
                    raise SubjectNotFound("check decision was not found")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    command_name="check_decisions.resume",
                    command=command,
                    request_payload={
                        "subject_id": str(subject_id),
                        "decision_id": str(decision_id),
                    },
                )
                if replayed:
                    assert record.response_resource_id is not None
                    return decision
                if decision.revision != command.expected_revision:
                    raise RevisionConflict(decision.revision)
                if decision.state == "resumed":
                    self._complete_idempotency(
                        record, decision.id, decision.revision
                    )
                    return decision
                decision.state = "resumed"
                decision.revision += 1
                decision.resumed_by = scope.actor_id
                decision.resumed_at = datetime.now(UTC)
                decision.resume_reason = command.reason
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=scope.tenant_id,
                        study_id=subject.study_id,
                        site_id=subject.site_id,
                        actor_id=scope.actor_id,
                        action="check_decisions.resume",
                        resource_type="check_decision",
                        resource_id=decision.id,
                        revision_before=command.expected_revision,
                        revision_after=decision.revision,
                        before_state={"state": "active"},
                        after_state={
                            "state": "resumed",
                            "reason": command.reason,
                        },
                        command_name="check_decisions.resume",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(
                    record, decision.id, decision.revision
                )
                return decision

    def list_check_decisions(
        self, scope: ScopeContext, subject_id: uuid.UUID
    ) -> list[CheckDecision]:
        subject = self._load_subject(scope, subject_id)
        self._authorize_read(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(CheckDecision)
                    .where(
                        CheckDecision.tenant_id == scope.tenant_id,
                        CheckDecision.study_id == subject.study_id,
                        CheckDecision.subject_id == subject.id,
                    )
                    .order_by(CheckDecision.created_at.desc())
                )
            )

    def _eligible_singleton_facts(
        self, session: Session, subject_id: uuid.UUID
    ) -> dict[str, ClinicalFact]:
        facts = list(
            session.scalars(
                select(ClinicalFact)
                .where(
                    ClinicalFact.subject_id == subject_id,
                    ClinicalFact.repeat_instance == "_",
                    ClinicalFact.verification_status.in_(
                        ("original_record", "cra_confirmed")
                    ),
                )
                .order_by(
                    ClinicalFact.fact_key,
                    ClinicalFact.revision.desc(),
                )
            )
        )
        current: dict[str, ClinicalFact] = {}
        for fact in facts:
            current.setdefault(fact.fact_key, fact)
        return current

    @staticmethod
    def _fact_value_map(
        facts: dict[str, ClinicalFact],
    ) -> dict[str, FactValue]:
        return {
            key: FactValue(value=fact.value_json, unit=fact.unit)
            for key, fact in facts.items()
        }

    def _active_decision_for(
        self,
        session: Session,
        *,
        subject: Subject,
        rule_version_id: uuid.UUID,
        missing_key: str,
        event_date: date,
    ) -> CheckDecision | None:
        decisions = session.scalars(
            select(CheckDecision).where(
                CheckDecision.tenant_id == subject.tenant_id,
                CheckDecision.study_id == subject.study_id,
                CheckDecision.subject_id == subject.id,
                CheckDecision.state == "active",
                CheckDecision.category == "visit_window",
                CheckDecision.check_type == "visit_window",
                or_(
                    CheckDecision.rule_version_id == rule_version_id,
                    CheckDecision.rule_version_id.is_(None),
                ),
                CheckDecision.missing_keys.contains([missing_key]),
            )
        )
        for decision in decisions:
            if (
                decision.scope_start is not None
                and event_date < decision.scope_start
            ):
                continue
            if decision.scope_end is not None and event_date > decision.scope_end:
                continue
            return decision
        return None

    @staticmethod
    def _fact_source_ref(fact: ClinicalFact) -> SourceRef:
        ref = fact.source_ref
        return SourceRef(
            source_type=(
                ref.get("source_type")
                if ref.get("source_type")
                in {
                    "document",
                    "document_anchor",
                    "edc_row",
                    "image_region",
                    "user_action",
                    "record",
                    "external_query",
                }
                else "record"
            ),
            source_id=str(ref.get("source_id", fact.id)),
            version=f"fact-r{fact.revision}",
            locator=ref.get("locator"),
            quote=ref.get("quote"),
        )

    def _requirement_status(
        self,
        *,
        spec: DateIntervalSpec,
        anchor: ClinicalFact | None,
        actual: ClinicalFact | None,
        active_decision: CheckDecision | None,
    ) -> tuple[str, DateWindow | None]:
        if active_decision is not None:
            return "not_checked_by_user", None
        if anchor is None:
            return "unknown_anchor", None
        anchor_date = _date_from_fact(anchor)
        if anchor_date is None:
            return "unknown_anchor", None
        window = DateWindow(
            anchor_date=anchor_date,
            min_days=spec.min_days,
            max_days=spec.max_days,
            inclusive=spec.inclusive,
        )
        if actual is None:
            return "unknown_actual", window
        classification = window.classify(_date_from_fact(actual))
        return (
            "in_window" if classification == "in_window" else "out_of_window",
            window,
        )

    def evaluate_visit_requirements(
        self,
        scope: ScopeContext,
        subject_id: uuid.UUID,
        command: EvaluateVisitRequirementsCommand,
    ) -> VisitRequirementOutcome:
        subject = self._load_subject(scope, subject_id)
        self._authorize_read(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            session.expire_on_commit = False
            with session.begin():
                return self._evaluate_visit_requirements_in_session(
                    session,
                    scope,
                    subject,
                    command,
                )

    def _evaluate_visit_requirements_in_session(
        self,
        session: Session,
        scope: ScopeContext,
        subject: Subject,
        command: EvaluateVisitRequirementsCommand,
    ) -> VisitRequirementOutcome:
            facts = self._eligible_singleton_facts(session, subject.id)
            fact_map = self._fact_value_map(facts)
            stage = current_stage(
                {key: fact.value_raw for key, fact in facts.items()}
            )
            rule_outcome = self.rules.applicable_rules(
                scope,
                ApplicableRuleQuery(
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    event_date=command.event_date,
                    jurisdiction=command.jurisdiction,
                    facts=fact_map,
                ),
            )
            requirements: list[RequirementItem] = []
            claims: list[Claim] = []
            unknowns: list[UnknownItem] = []
            not_checked: list[NotCheckedItem] = []
            evidence_refs: list[SourceRef] = []
            capabilities: list[OutputCapability] = []
            input_revisions: list[InputRevision] = [
                InputRevision(
                    resource_type="clinical_fact",
                    resource_id=str(fact.id),
                    revision=fact.revision,
                    digest=_json_digest(
                        {
                            "fact_key": fact.fact_key,
                            "value_raw": fact.value_raw,
                            "source_ref": fact.source_ref,
                        }
                    ),
                )
                for fact in facts.values()
            ]
            allowed_sources = [
                "authorized_record",
                "cra_confirmation",
            ]
            for applicable in rule_outcome.rules:
                specs = extract_date_interval_specs(applicable.tree)
                for spec in specs:
                    anchor = facts.get(spec.anchor_fact_key)
                    actual = facts.get(spec.event_fact_key)
                    decision = self._active_decision_for(
                        session,
                        subject=subject,
                        rule_version_id=applicable.version.id,
                        missing_key=spec.anchor_fact_key,
                        event_date=command.event_date,
                    )
                    status, window = self._requirement_status(
                        spec=spec,
                        anchor=anchor,
                        actual=actual,
                        active_decision=decision,
                    )
                    input_facts = [
                        fact
                        for fact in (anchor, actual)
                        if fact is not None
                    ]
                    input_keys = sorted(
                        {
                            spec.anchor_fact_key,
                            spec.event_fact_key,
                            *applicable.tree.required_facts,
                        }
                    )
                    required_keys = sorted(
                        {
                            spec.anchor_fact_key,
                            *applicable.tree.required_facts,
                        }
                    )
                    can_continue = [
                        "known_subject_and_stage",
                        "other_category_review",
                    ]
                    if "subject_external_id" in facts:
                        can_continue.append("identified_subject_work")
                    visit_key = (
                        f"{applicable.rule.rule_key}:{spec.path}"
                    )
                    content = {
                        "subject_id": str(subject.id),
                        "rule_version_id": str(applicable.version.id),
                        "visit_key": visit_key,
                        "event_date": command.event_date.isoformat(),
                        "anchor_fact_id": str(anchor.id) if anchor else None,
                        "actual_fact_id": str(actual.id) if actual else None,
                        "decision_id": str(decision.id) if decision else None,
                        "status": status,
                    }
                    content_hash = _json_digest(content)
                    requirement = session.scalar(
                        select(VisitRequirement).where(
                            VisitRequirement.subject_id == subject.id,
                            VisitRequirement.rule_version_id
                            == applicable.version.id,
                            VisitRequirement.visit_key == visit_key,
                            VisitRequirement.event_date == command.event_date,
                            VisitRequirement.content_hash == content_hash,
                        )
                    )
                    if requirement is None:
                        requirement = VisitRequirement(
                            id=uuid.uuid4(),
                            tenant_id=subject.tenant_id,
                            study_id=subject.study_id,
                            site_id=subject.site_id,
                            subject_id=subject.id,
                            rule_version_id=applicable.version.id,
                            visit_key=visit_key,
                            stage=stage,
                            anchor_fact_key=spec.anchor_fact_key,
                            event_fact_key=spec.event_fact_key,
                            event_date=command.event_date,
                            anchor_fact_id=anchor.id if anchor else None,
                            anchor_date=_date_from_fact(anchor),
                            actual_date=_date_from_fact(actual),
                            min_days=spec.min_days,
                            max_days=spec.max_days,
                            inclusive=spec.inclusive,
                            window_start=window.starts_on if window else None,
                            window_end=window.ends_on if window else None,
                            status=status,
                            required_fact_keys=required_keys,
                            allowed_sources=allowed_sources,
                            affected_paths=[
                                f"{applicable.rule.rule_key}:{spec.path}"
                            ],
                            can_continue=can_continue,
                            input_fact_keys=input_keys,
                            input_fact_revisions={
                                str(fact.id): fact.revision
                                for fact in input_facts
                            },
                            content_hash=content_hash,
                            created_by=scope.actor_id,
                        )
                        session.add(requirement)
                        session.flush()
                    if requirement.status == "needs_review":
                        requirement.status = status
                    requirements.append(
                        RequirementItem(
                            requirement=requirement,
                            rule_summary=applicable.tree.summary,
                            window_status=status,
                        )
                    )
                    claims.append(
                        Claim(
                            claim_id=f"visit-window:{requirement.id}",
                            kind=(
                                "fact"
                                if status in {"in_window", "out_of_window"}
                                else "inference"
                            ),
                            label=(
                                f"{applicable.rule.rule_key} {spec.path} "
                                f"{status}"
                            ),
                            value={
                                "visit_key": visit_key,
                                "stage": stage,
                                "anchor_fact_key": spec.anchor_fact_key,
                                "anchor_date": (
                                    requirement.anchor_date.isoformat()
                                    if requirement.anchor_date
                                    else None
                                ),
                                "actual_date": (
                                    requirement.actual_date.isoformat()
                                    if requirement.actual_date
                                    else None
                                ),
                                "window_start": (
                                    requirement.window_start.isoformat()
                                    if requirement.window_start
                                    else None
                                ),
                                "window_end": (
                                    requirement.window_end.isoformat()
                                    if requirement.window_end
                                    else None
                                ),
                                "min_days": spec.min_days,
                                "max_days": spec.max_days,
                                "inclusive": spec.inclusive,
                                "rule_version_id": str(applicable.version.id),
                            },
                            verification_status=(
                                "cra_confirmed"
                                if status in {"in_window", "out_of_window"}
                                else "needs_review"
                            ),
                            source_refs=[
                                self._fact_source_ref(fact)
                                for fact in input_facts
                            ],
                            calculation=(
                                "window = anchor + "
                                f"[{spec.min_days}, {spec.max_days}] days"
                            ),
                        )
                    )
                    evidence_refs.extend(
                        self._fact_source_ref(fact) for fact in input_facts
                    )
                    rule_refs = [
                        SourceRef(
                            source_type="document_anchor",
                            source_id=str(ref.anchor_id or ref.anchor_key),
                            version=(
                                str(ref.document_version_id)
                                if ref.document_version_id
                                else None
                            ),
                            locator=ref.locator,
                            quote=ref.quote,
                        )
                        for ref in applicable.tree.source_refs
                    ]
                    evidence_refs.extend(rule_refs)
                    claims[-1].source_refs.extend(rule_refs)
                    if status == "unknown_anchor":
                        unknowns.append(
                            UnknownItem(
                                code="missing_visit_anchor",
                                reason=(
                                    f"{spec.anchor_fact_key} is required for "
                                    f"{visit_key}"
                                ),
                                affected_scope=visit_key,
                            )
                        )
                    elif status == "unknown_actual":
                        unknowns.append(
                            UnknownItem(
                                code="missing_actual_visit_date",
                                reason=(
                                    f"{spec.event_fact_key} is required to "
                                    f"classify {visit_key}"
                                ),
                                affected_scope=visit_key,
                            )
                        )
                    elif status == "not_checked_by_user":
                        assert decision is not None
                        not_checked.append(
                            NotCheckedItem(
                                code="not_checked_by_user",
                                scope=visit_key,
                                reason=decision.reason,
                                decision_ref=str(decision.id),
                            )
                        )
                capabilities.append(
                    OutputCapability(
                        capability_id="rule-driven-visit-window",
                        level="limited",
                        validated=True,
                        limitations=[
                            "uses the finite W04 date-interval rules only",
                            "not a complete protocol schedule",
                        ],
                    )
                )
            if not requirements:
                unknowns.append(
                    UnknownItem(
                        code="no_visit_rules",
                        reason="no applicable confirmed date-interval rule",
                        affected_scope=f"{subject.deidentified_label}@{command.event_date.isoformat()}",
                    )
                )
            envelope = OutputEnvelope(
                output_id=uuid.uuid4(),
                purpose="visit_window",
                scope=OutputScope(
                    tenant_id=subject.tenant_id,
                    study_id=subject.study_id,
                    site_id=subject.site_id,
                    subject_id=str(subject.id),
                ),
                input_revisions=input_revisions,
                policy_versions=rule_outcome.envelope.policy_versions,
                claims=claims,
                evidence_refs=evidence_refs,
                unknowns=unknowns,
                conflicts=rule_outcome.envelope.conflicts,
                not_checked=not_checked,
                capabilities=capabilities,
                status=(
                    "needs_clarification"
                    if rule_outcome.envelope.conflicts
                    else "limited"
                    if unknowns or not_checked
                    else "ready_to_review"
                ),
                generated_at=datetime.now(UTC),
                actor_id=scope.actor_id,
            )
            instances = list(
                session.scalars(
                    select(VisitInstance)
                    .where(
                        VisitInstance.tenant_id == subject.tenant_id,
                        VisitInstance.study_id == subject.study_id,
                        VisitInstance.subject_id == subject.id,
                    )
                    .order_by(
                        VisitInstance.visit_key,
                        VisitInstance.repeat_instance,
                        VisitInstance.revision.desc(),
                    )
                )
            )
            current_instances: dict[tuple[str, str], VisitInstance] = {}
            for instance in instances:
                current_instances.setdefault(
                    (instance.visit_key, instance.repeat_instance), instance
                )
            return VisitRequirementOutcome(
                envelope=envelope,
                requirements=tuple(requirements),
                instances=tuple(current_instances.values()),
            )

    def list_visit_requirements(
        self,
        scope: ScopeContext,
        subject_id: uuid.UUID,
        *,
        event_date: date,
    ) -> list[VisitRequirement]:
        subject = self._load_subject(scope, subject_id)
        self._authorize_read(scope, subject.study_id, subject.site_id)
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(VisitRequirement)
                    .where(
                        VisitRequirement.tenant_id == scope.tenant_id,
                        VisitRequirement.study_id == subject.study_id,
                        VisitRequirement.subject_id == subject.id,
                        VisitRequirement.event_date == event_date,
                    )
                    .order_by(
                        VisitRequirement.visit_key,
                        VisitRequirement.computed_at.desc(),
                    )
                )
            )
            latest: dict[str, VisitRequirement] = {}
            for row in rows:
                latest.setdefault(row.visit_key, row)
            return list(latest.values())
