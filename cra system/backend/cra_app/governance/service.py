"""Audited, scoped, idempotent governance commands."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from cra_app.governance.models import (
    AuditEvent,
    IdempotencyRecord,
    Membership,
    Site,
    Study,
)


class ScopeContext(BaseModel):
    """Trusted identity scope.

    Construct only after the identity adapter has authenticated the session.
    Browser payloads must never populate actor_id, tenant_id or platform_roles.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(min_length=1, max_length=128)
    authentication_source: str = Field(min_length=1, max_length=64)
    platform_roles: frozenset[Literal["platform_admin"]] = frozenset()


class _WriteCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class CreateStudy(_WriteCommand):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)


class UpdateStudy(_WriteCommand):
    title: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_existing_revision(self) -> "UpdateStudy":
        if self.expected_revision < 1:
            raise ValueError("updates require expected_revision >= 1")
        return self


class CreateSite(_WriteCommand):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)


class UpdateSite(_WriteCommand):
    name: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_existing_revision(self) -> "UpdateSite":
        if self.expected_revision < 1:
            raise ValueError("updates require expected_revision >= 1")
        return self


class GrantMembership(_WriteCommand):
    actor_id: str = Field(min_length=1, max_length=128)
    role: Literal["study_admin", "cra", "viewer"]
    site_id: uuid.UUID | None = None
    can_write: bool = False

    @model_validator(mode="after")
    def validate_role_scope(self) -> "GrantMembership":
        if self.role == "study_admin":
            if self.site_id is not None:
                raise ValueError("study_admin membership is study-wide")
            if not self.can_write:
                raise ValueError("study_admin membership must be writable")
        if self.role == "viewer" and self.can_write:
            raise ValueError("viewer membership cannot write")
        return self


@dataclass(frozen=True)
class CommandResult:
    resource_id: uuid.UUID
    revision: int
    replayed: bool


class GovernanceError(Exception):
    """Base class for expected governance failures."""


class AuthorizationDenied(GovernanceError):
    pass


class ResourceNotFound(GovernanceError):
    pass


class RevisionConflict(GovernanceError):
    def __init__(self, current_revision: int):
        super().__init__(f"revision conflict; current revision is {current_revision}")
        self.current_revision = current_revision


class IdempotencyConflict(GovernanceError):
    pass


class InvalidCommand(GovernanceError):
    pass


class ResourceAlreadyExists(GovernanceError):
    pass


class GovernanceService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    @staticmethod
    def _digest(value: dict[str, Any]) -> str:
        raw = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _scope_fingerprint(
        scope: ScopeContext,
        study_id: uuid.UUID | None,
        site_id: uuid.UUID | None,
    ) -> str:
        return GovernanceService._digest(
            {
                "tenant_id": scope.tenant_id,
                "study_id": str(study_id) if study_id else None,
                "site_id": str(site_id) if site_id else None,
            }
        )

    @staticmethod
    def _study_state(study: Study) -> dict[str, Any]:
        return {"code": study.code, "title": study.title}

    @staticmethod
    def _site_state(site: Site) -> dict[str, Any]:
        return {"code": site.code, "name": site.name}

    @staticmethod
    def _is_platform_admin(scope: ScopeContext) -> bool:
        return "platform_admin" in scope.platform_roles

    def _require_platform_admin(self, scope: ScopeContext) -> None:
        if not self._is_platform_admin(scope):
            raise AuthorizationDenied("tenant platform administration is required")

    def _has_study_membership(
        self, session: Session, scope: ScopeContext, study_id: uuid.UUID
    ) -> bool:
        return bool(
            session.scalar(
                select(
                    exists().where(
                        Membership.tenant_id == scope.tenant_id,
                        Membership.study_id == study_id,
                        Membership.actor_id == scope.actor_id,
                    )
                )
            )
        )

    def _require_read_study(
        self, session: Session, scope: ScopeContext, study_id: uuid.UUID
    ) -> None:
        if self._is_platform_admin(scope) or self._has_study_membership(
            session, scope, study_id
        ):
            return
        raise AuthorizationDenied("study is outside the authorized scope")

    def _require_manage_study(
        self, session: Session, scope: ScopeContext, study_id: uuid.UUID
    ) -> None:
        if self._is_platform_admin(scope):
            return
        allowed = session.scalar(
            select(
                exists().where(
                    Membership.tenant_id == scope.tenant_id,
                    Membership.study_id == study_id,
                    Membership.actor_id == scope.actor_id,
                    Membership.role == "study_admin",
                    Membership.site_id.is_(None),
                    Membership.can_write.is_(True),
                )
            )
        )
        if not allowed:
            raise AuthorizationDenied("study administration is required")

    def _require_read_site(
        self,
        session: Session,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> None:
        if self._is_platform_admin(scope):
            return
        allowed = session.scalar(
            select(
                exists().where(
                    Membership.tenant_id == scope.tenant_id,
                    Membership.study_id == study_id,
                    Membership.actor_id == scope.actor_id,
                    or_(
                        Membership.site_id.is_(None),
                        Membership.site_id == site_id,
                    ),
                )
            )
        )
        if not allowed:
            raise AuthorizationDenied("site is outside the authorized scope")

    def _require_write_site(
        self,
        session: Session,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> None:
        if self._is_platform_admin(scope):
            return
        allowed = session.scalar(
            select(
                exists().where(
                    Membership.tenant_id == scope.tenant_id,
                    Membership.study_id == study_id,
                    Membership.actor_id == scope.actor_id,
                    Membership.can_write.is_(True),
                    or_(
                        Membership.site_id.is_(None),
                        Membership.site_id == site_id,
                    ),
                )
            )
        )
        if not allowed:
            raise AuthorizationDenied("site write access is required")

    def _reserve_idempotency(
        self,
        session: Session,
        *,
        scope: ScopeContext,
        study_id: uuid.UUID | None,
        site_id: uuid.UUID | None,
        command_name: str,
        command: _WriteCommand,
        request_payload: dict[str, Any],
    ) -> tuple[IdempotencyRecord, bool]:
        scope_fingerprint = self._scope_fingerprint(scope, study_id, site_id)
        request_digest = self._digest(
            {
                "command_name": command_name,
                "scope_fingerprint": scope_fingerprint,
                "command": command.model_dump(mode="json"),
                "request": request_payload,
            }
        )
        record_id = uuid.uuid4()
        insert_statement = (
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
        session.execute(insert_statement)
        record = session.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == scope.actor_id,
                IdempotencyRecord.tenant_id == scope.tenant_id,
                IdempotencyRecord.scope_fingerprint == scope_fingerprint,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key
                == command.idempotency_key,
            )
            .with_for_update()
        )
        if record is None:
            raise RuntimeError("failed to reserve idempotency key")
        if record.request_digest != request_digest:
            raise IdempotencyConflict(
                "idempotency key was already used with different input"
            )
        if record.response_resource_id is not None:
            if record.response_revision is None:
                raise RuntimeError("incomplete idempotency response")
            return record, True
        return record, False

    @staticmethod
    def _complete_idempotency(
        record: IdempotencyRecord, resource_id: uuid.UUID, revision: int
    ) -> None:
        record.response_resource_id = resource_id
        record.response_revision = revision
        record.completed_at = datetime.now(UTC)

    @staticmethod
    def _result(record: IdempotencyRecord, *, replayed: bool) -> CommandResult:
        if record.response_resource_id is None or record.response_revision is None:
            raise RuntimeError("idempotency result is not complete")
        return CommandResult(
            resource_id=record.response_resource_id,
            revision=record.response_revision,
            replayed=replayed,
        )

    @staticmethod
    def _require_create_revision(command: _WriteCommand) -> None:
        if command.expected_revision != 0:
            raise InvalidCommand("create commands require expected_revision=0")

    def create_study(
        self, scope: ScopeContext, command: CreateStudy
    ) -> CommandResult:
        self._require_platform_admin(scope)
        self._require_create_revision(command)
        with self._session_factory() as session:
            with session.begin():
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=None,
                    site_id=None,
                    command_name="study.create",
                    command=command,
                    request_payload={},
                )
                if replayed:
                    return self._result(record, replayed=True)

                study = Study(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    code=command.code,
                    title=command.title,
                    revision=1,
                    created_by=scope.actor_id,
                    updated_by=scope.actor_id,
                )
                session.add(study)
                try:
                    session.flush()
                except Exception as exc:
                    if "uq_studies_tenant_code" in str(exc):
                        raise ResourceAlreadyExists(
                            "study code already exists in this tenant"
                        ) from exc
                    raise
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=study.tenant_id,
                        study_id=study.id,
                        site_id=None,
                        actor_id=scope.actor_id,
                        action="study.create",
                        resource_type="study",
                        resource_id=study.id,
                        revision_before=None,
                        revision_after=study.revision,
                        before_state=None,
                        after_state=self._study_state(study),
                        command_name="study.create",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, study.id, study.revision)
                return self._result(record, replayed=False)

    def create_site(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: CreateSite,
    ) -> CommandResult:
        self._require_create_revision(command)
        with self._session_factory() as session:
            with session.begin():
                self._require_manage_study(session, scope, study_id)
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=None,
                    command_name="site.create",
                    command=command,
                    request_payload={},
                )
                if replayed:
                    return self._result(record, replayed=True)

                site = Site(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=study_id,
                    code=command.code,
                    name=command.name,
                    revision=1,
                    created_by=scope.actor_id,
                    updated_by=scope.actor_id,
                )
                session.add(site)
                try:
                    session.flush()
                except Exception as exc:
                    if "uq_sites_study_code" in str(exc):
                        raise ResourceAlreadyExists(
                            "site code already exists in this study"
                        ) from exc
                    raise
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=site.tenant_id,
                        study_id=site.study_id,
                        site_id=site.id,
                        actor_id=scope.actor_id,
                        action="site.create",
                        resource_type="site",
                        resource_id=site.id,
                        revision_before=None,
                        revision_after=site.revision,
                        before_state=None,
                        after_state=self._site_state(site),
                        command_name="site.create",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, site.id, site.revision)
                return self._result(record, replayed=False)

    def grant_membership(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: GrantMembership,
    ) -> CommandResult:
        self._require_create_revision(command)
        with self._session_factory() as session:
            with session.begin():
                self._require_manage_study(session, scope, study_id)
                if command.site_id is not None:
                    target_site = session.scalar(
                        select(Site).where(
                            Site.id == command.site_id,
                            Site.tenant_id == scope.tenant_id,
                            Site.study_id == study_id,
                        )
                    )
                    if target_site is None:
                        raise ResourceNotFound("target site was not found in study")
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=None,
                    command_name="membership.grant",
                    command=command,
                    request_payload={},
                )
                if replayed:
                    return self._result(record, replayed=True)

                membership = Membership(
                    id=uuid.uuid4(),
                    tenant_id=scope.tenant_id,
                    study_id=study_id,
                    site_id=command.site_id,
                    actor_id=command.actor_id,
                    role=command.role,
                    can_write=command.can_write,
                    created_by=scope.actor_id,
                )
                session.add(membership)
                try:
                    session.flush()
                except Exception as exc:
                    if "uq_memberships_" in str(exc):
                        raise ResourceAlreadyExists(
                            "membership already exists"
                        ) from exc
                    raise
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=membership.tenant_id,
                        study_id=membership.study_id,
                        site_id=membership.site_id,
                        actor_id=scope.actor_id,
                        action="membership.grant",
                        resource_type="membership",
                        resource_id=membership.id,
                        revision_before=None,
                        revision_after=1,
                        before_state=None,
                        after_state={
                            "actor_id": membership.actor_id,
                            "role": membership.role,
                            "site_id": (
                                str(membership.site_id)
                                if membership.site_id
                                else None
                            ),
                            "can_write": membership.can_write,
                        },
                        command_name="membership.grant",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, membership.id, 1)
                return self._result(record, replayed=False)

    def update_study(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        command: UpdateStudy,
    ) -> CommandResult:
        with self._session_factory() as session:
            with session.begin():
                self._require_manage_study(session, scope, study_id)
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=None,
                    command_name="study.update",
                    command=command,
                    request_payload={"study_id": str(study_id)},
                )
                if replayed:
                    return self._result(record, replayed=True)

                study = session.scalar(
                    select(Study)
                    .where(
                        Study.id == study_id,
                        Study.tenant_id == scope.tenant_id,
                    )
                    .with_for_update()
                )
                if study is None:
                    raise ResourceNotFound("study was not found")
                if study.revision != command.expected_revision:
                    raise RevisionConflict(study.revision)
                before = self._study_state(study)
                before_revision = study.revision
                study.title = command.title
                study.revision += 1
                study.updated_by = scope.actor_id
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=study.tenant_id,
                        study_id=study.id,
                        site_id=None,
                        actor_id=scope.actor_id,
                        action="study.update",
                        resource_type="study",
                        resource_id=study.id,
                        revision_before=before_revision,
                        revision_after=study.revision,
                        before_state=before,
                        after_state=self._study_state(study),
                        command_name="study.update",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, study.id, study.revision)
                return self._result(record, replayed=False)

    def update_site(
        self,
        scope: ScopeContext,
        study_id: uuid.UUID,
        site_id: uuid.UUID,
        command: UpdateSite,
    ) -> CommandResult:
        with self._session_factory() as session:
            with session.begin():
                self._require_write_site(session, scope, study_id, site_id)
                record, replayed = self._reserve_idempotency(
                    session,
                    scope=scope,
                    study_id=study_id,
                    site_id=site_id,
                    command_name="site.update",
                    command=command,
                    request_payload={
                        "study_id": str(study_id),
                        "site_id": str(site_id),
                    },
                )
                if replayed:
                    return self._result(record, replayed=True)

                site = session.scalar(
                    select(Site)
                    .where(
                        Site.id == site_id,
                        Site.tenant_id == scope.tenant_id,
                        Site.study_id == study_id,
                    )
                    .with_for_update()
                )
                if site is None:
                    raise ResourceNotFound("site was not found")
                if site.revision != command.expected_revision:
                    raise RevisionConflict(site.revision)
                before = self._site_state(site)
                before_revision = site.revision
                site.name = command.name
                site.revision += 1
                site.updated_by = scope.actor_id
                session.flush()
                session.add(
                    AuditEvent(
                        id=uuid.uuid4(),
                        tenant_id=site.tenant_id,
                        study_id=site.study_id,
                        site_id=site.id,
                        actor_id=scope.actor_id,
                        action="site.update",
                        resource_type="site",
                        resource_id=site.id,
                        revision_before=before_revision,
                        revision_after=site.revision,
                        before_state=before,
                        after_state=self._site_state(site),
                        command_name="site.update",
                        correlation_id=record.id,
                    )
                )
                self._complete_idempotency(record, site.id, site.revision)
                return self._result(record, replayed=False)

    def get_study(
        self, scope: ScopeContext, study_id: uuid.UUID
    ) -> Study:
        with self._session_factory() as session:
            self._require_read_study(session, scope, study_id)
            study = session.scalar(
                select(Study).where(
                    Study.id == study_id,
                    Study.tenant_id == scope.tenant_id,
                )
            )
            if study is None:
                raise ResourceNotFound("study was not found")
            return study

    def get_site(
        self, scope: ScopeContext, study_id: uuid.UUID, site_id: uuid.UUID
    ) -> Site:
        with self._session_factory() as session:
            self._require_read_site(session, scope, study_id, site_id)
            site = session.scalar(
                select(Site).where(
                    Site.id == site_id,
                    Site.tenant_id == scope.tenant_id,
                    Site.study_id == study_id,
                )
            )
            if site is None:
                raise ResourceNotFound("site was not found")
            return site

    def list_sites(
        self, scope: ScopeContext, study_id: uuid.UUID
    ) -> list[Site]:
        with self._session_factory() as session:
            self._require_read_study(session, scope, study_id)
            if self._is_platform_admin(scope):
                return list(
                    session.scalars(
                        select(Site)
                        .where(
                            Site.tenant_id == scope.tenant_id,
                            Site.study_id == study_id,
                        )
                        .order_by(Site.code)
                    )
                )
            study_wide = session.scalar(
                select(
                    exists().where(
                        Membership.tenant_id == scope.tenant_id,
                        Membership.study_id == study_id,
                        Membership.actor_id == scope.actor_id,
                        Membership.site_id.is_(None),
                    )
                )
            )
            if study_wide:
                return list(
                    session.scalars(
                        select(Site)
                        .where(
                            Site.tenant_id == scope.tenant_id,
                            Site.study_id == study_id,
                        )
                        .order_by(Site.code)
                    )
                )
            allowed_site_ids = select(Membership.site_id).where(
                Membership.tenant_id == scope.tenant_id,
                Membership.study_id == study_id,
                Membership.actor_id == scope.actor_id,
                Membership.site_id.is_not(None),
            )
            return list(
                session.scalars(
                    select(Site)
                    .where(
                        Site.tenant_id == scope.tenant_id,
                        Site.study_id == study_id,
                        Site.id.in_(allowed_site_ids),
                    )
                    .order_by(Site.code)
                )
            )

    def authorize(
        self,
        scope: ScopeContext,
        action: Literal[
            "read_study",
            "manage_study",
            "read_site",
            "write_site",
        ],
        study_id: uuid.UUID,
        site_id: uuid.UUID | None = None,
    ) -> ScopeContext:
        """Authorize a resource action and return the trusted scope.

        Other modules consume this method instead of reading Membership tables.
        """
        with self._session_factory() as session:
            if action == "read_study":
                self._require_read_study(session, scope, study_id)
            elif action == "manage_study":
                self._require_manage_study(session, scope, study_id)
            elif action == "read_site":
                if site_id is None:
                    raise InvalidCommand("site_id is required for read_site")
                self._require_read_site(session, scope, study_id, site_id)
            elif action == "write_site":
                if site_id is None:
                    raise InvalidCommand("site_id is required for write_site")
                self._require_write_site(session, scope, study_id, site_id)
            else:
                raise InvalidCommand("unknown authorization action")
        return scope
