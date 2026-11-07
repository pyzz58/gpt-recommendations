from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ArchivedProjectError,
    IdempotencyConflictError,
    NotFoundError,
    RevisionConflictError,
)
from medical_one_person.application.policy_bundles import (
    ensure_active_bundle_in_session,
)
from medical_one_person.domain.projects import ProjectSnapshot, ProjectStage, ProjectStatus
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    CommandReceipt,
    Project,
    ProjectEvent,
    ProjectVersion,
    User,
)


class ProjectReceiptPayload(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    scope: str
    stage: ProjectStage
    status: ProjectStatus
    revision: int
    created_at: datetime
    updated_at: datetime
    policy_bundle_id: str | None = None


class ProjectService:
    """Commands that atomically preserve project versions and project events."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_project(
        self,
        *,
        actor_user_id: UUID,
        name: str,
        scope: str,
        idempotency_key: str,
    ) -> ProjectSnapshot:
        if not name.strip() or not scope.strip():
            raise ValueError("Project name and scope cannot be empty")
        if not idempotency_key.strip():
            raise ValueError("Idempotency key cannot be empty")
        request_payload = {"name": name, "scope": scope}
        request_hash = _hash_payload(request_payload)
        route = "projects.create"
        try:
            return self._create_project_once(
                actor_user_id=actor_user_id,
                name=name,
                scope=scope,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                route=route,
            )
        except IntegrityError:
            receipt = self._find_receipt(actor_user_id, route, idempotency_key)
            if receipt is None:
                raise
            return self._replay_receipt(receipt, request_hash)

    def _create_project_once(
        self,
        *,
        actor_user_id: UUID,
        name: str,
        scope: str,
        idempotency_key: str,
        request_hash: str,
        route: str,
    ) -> ProjectSnapshot:
        with self._session_factory.begin() as session:
            actor = session.get(User, actor_user_id)
            if actor is None:
                raise NotFoundError("Actor not found")
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            receipt = _find_receipt(session, actor_user_id, route, idempotency_key)
            if receipt is not None:
                return self._replay_receipt(receipt, request_hash)

            now = datetime.now(UTC)
            policy_bundle_id = ensure_active_bundle_in_session(
                session,
                workspace_id=actor.workspace_id,
                actor_user_id=actor.id,
                now=now,
            )
            project = Project(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                name=name,
                scope=scope,
                stage=ProjectStage.DRAFT.value,
                status=ProjectStatus.DRAFT.value,
                policy_bundle_id=policy_bundle_id,
                revision=1,
                created_by_user_id=actor.id,
                created_at=now,
                updated_at=now,
            )
            session.add(project)
            session.flush()
            self._append_version(session, project, actor.id, now)
            self._append_event(
                session,
                project,
                actor.id,
                event_type="project.created",
                payload={"name": project.name, "scope": project.scope},
                now=now,
            )
            session.add(
                CommandReceipt(
                    id=uuid4(),
                    actor_user_id=actor.id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_payload=_receipt_payload(project),
                    resource_id=project.id,
                    created_at=now,
                )
            )
            session.flush()
            return _snapshot(project)

    def rename_project(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        expected_revision: int,
        name: str,
        idempotency_key: str,
    ) -> ProjectSnapshot:
        if not name.strip():
            raise ValueError("Project name cannot be empty")
        if not idempotency_key.strip():
            raise ValueError("Idempotency key cannot be empty")
        request_hash = _hash_payload(
            {
                "project_id": str(project_id),
                "expected_revision": expected_revision,
                "name": name,
            }
        )
        route = "projects.rename"
        with self._session_factory.begin() as session:
            actor = session.get(User, actor_user_id)
            if actor is None:
                raise NotFoundError("Project not found")
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            receipt = _find_receipt(session, actor_user_id, route, idempotency_key)
            if receipt is not None:
                return self._replay_receipt(receipt, request_hash)

            project = session.scalar(
                select(Project).where(Project.id == project_id).with_for_update()
            )
            if project is None:
                raise NotFoundError("Project not found")
            receipt = _find_receipt(session, actor_user_id, route, idempotency_key)
            if receipt is not None:
                return self._replay_receipt(receipt, request_hash)
            if project.archived_at is not None or project.status == ProjectStatus.ARCHIVED:
                raise ArchivedProjectError("Archived projects cannot be renamed")
            if project.revision != expected_revision:
                raise RevisionConflictError(
                    f"Expected revision {expected_revision}, current revision {project.revision}"
                )

            if actor.workspace_id != project.workspace_id:
                raise NotFoundError("Project not found")

            now = datetime.now(UTC)
            project.name = name
            project.revision += 1
            project.updated_at = now
            session.flush()
            self._append_version(session, project, actor.id, now)
            self._append_event(
                session,
                project,
                actor.id,
                event_type="project.renamed",
                payload={"name": name, "previous_revision": expected_revision},
                now=now,
            )
            session.add(
                CommandReceipt(
                    id=uuid4(),
                    actor_user_id=actor.id,
                    route=route,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_payload=_receipt_payload(project),
                    resource_id=project.id,
                    created_at=now,
                )
            )
            session.flush()
            return _snapshot(project)

    def list_projects(self, workspace_id: UUID) -> list[ProjectSnapshot]:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            projects = session.scalars(
                select(Project)
                .where(Project.workspace_id == workspace_id)
                .order_by(Project.created_at, Project.id)
            )
            return [_snapshot(project) for project in projects]

    def _find_receipt(
        self, actor_user_id: UUID, route: str, idempotency_key: str
    ) -> CommandReceipt | None:
        with self._session_factory() as session:
            return _find_receipt(session, actor_user_id, route, idempotency_key)

    def _replay_receipt(self, receipt: CommandReceipt, request_hash: str) -> ProjectSnapshot:
        if receipt.request_hash != request_hash:
            raise IdempotencyConflictError(
                "Idempotency key was already used with a different request"
            )
        payload = ProjectReceiptPayload.model_validate(receipt.response_payload)
        return ProjectSnapshot(
            id=payload.id,
            workspace_id=payload.workspace_id,
            name=payload.name,
            scope=payload.scope,
            stage=payload.stage,
            status=payload.status,
            revision=payload.revision,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            policy_bundle_id=payload.policy_bundle_id,
        )

    @staticmethod
    def _append_version(
        session: Session, project: Project, actor_user_id: UUID, now: datetime
    ) -> None:
        session.add(
            ProjectVersion(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                project_revision=project.revision,
                name=project.name,
                scope=project.scope,
                stage=project.stage,
                status=project.status,
                charter_version=project.charter_version,
                policy_bundle_id=project.policy_bundle_id,
                changed_by_user_id=actor_user_id,
                created_at=now,
            )
        )

    @staticmethod
    def _append_event(
        session: Session,
        project: Project,
        actor_user_id: UUID,
        *,
        event_type: str,
        payload: dict[str, object],
        now: datetime,
    ) -> None:
        last_sequence = session.scalar(
            select(ProjectEvent.project_seq)
            .where(ProjectEvent.project_id == project.id)
            .order_by(ProjectEvent.project_seq.desc())
            .limit(1)
        )
        session.add(
            ProjectEvent(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                project_seq=(last_sequence or 0) + 1,
                type=event_type,
                actor_user_id=actor_user_id,
                object_type="project",
                object_id=project.id,
                object_revision=project.revision,
                payload=payload,
                correlation_id=uuid4(),
                created_at=now,
            )
        )


def _receipt_query(actor_user_id: UUID, route: str, idempotency_key: str) -> Select[CommandReceipt]:
    return select(CommandReceipt).where(
        CommandReceipt.actor_user_id == actor_user_id,
        CommandReceipt.route == route,
        CommandReceipt.idempotency_key == idempotency_key,
    )


def _find_receipt(
    session: Session, actor_user_id: UUID, route: str, idempotency_key: str
) -> CommandReceipt | None:
    return session.execute(
        _receipt_query(actor_user_id, route, idempotency_key)
    ).scalar_one_or_none()


def _hash_payload(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _snapshot(project: Project) -> ProjectSnapshot:
    return ProjectSnapshot(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        scope=project.scope,
        stage=ProjectStage(project.stage),
        status=ProjectStatus(project.status),
        revision=project.revision,
        created_at=project.created_at,
        updated_at=project.updated_at,
        policy_bundle_id=project.policy_bundle_id,
    )


def _receipt_payload(project: Project) -> dict[str, object]:
    return ProjectReceiptPayload(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        scope=project.scope,
        stage=ProjectStage(project.stage),
        status=ProjectStatus(project.status),
        revision=project.revision,
        created_at=project.created_at,
        updated_at=project.updated_at,
        policy_bundle_id=project.policy_bundle_id,
    ).model_dump(mode="json")
