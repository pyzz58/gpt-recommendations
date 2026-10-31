from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.application.errors import (
    NotFoundError,
    RevisionConflictError,
)
from medical_one_person.config import Settings, get_settings
from medical_one_person.domain.policy_bundles import (
    PolicyBundleState,
    PolicyBundleView,
    PolicyImpactStatus,
    PolicyImpactView,
    PolicyMigrationKind,
    PolicyMigrationState,
    PolicyMigrationView,
    PolicyProjectView,
)
from medical_one_person.domain.tasks import InputValidity, TaskState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.engine import EXPECTED_DATABASE_REVISION
from medical_one_person.infrastructure.db.models import (
    Job,
    Plan,
    PlanNode,
    PolicyBundle,
    PolicyImpact,
    PolicyMigrationOperation,
    PolicyState,
    Project,
    ProjectEvent,
    ProjectVersion,
    Task,
    TaskVersion,
    User,
)
from medical_one_person.infrastructure.skills.registry import SkillRegistry
from medical_one_person.infrastructure.sources import load_source_policies
from medical_one_person.infrastructure.workflows import WorkflowRegistry

POLICY_SCHEMA_REVISION = EXPECTED_DATABASE_REVISION
OPEN_POLICY_TASK_STATES = {
    TaskState.DRAFT.value,
    TaskState.NEEDS_INPUT.value,
    TaskState.READY.value,
    TaskState.QUEUED.value,
    TaskState.RUNNING.value,
    TaskState.SUBMITTED.value,
    TaskState.REWORK.value,
    TaskState.WAITING_EXTERNAL.value,
    TaskState.PAUSED.value,
}


class PolicyBundleError(ValueError):
    pass


@dataclass(frozen=True)
class PolicyBundleCandidate:
    content_sha256: str
    version_label: str
    theory_version: str
    theory_sha256: str
    component_sha256: dict[str, str]
    snapshot: dict[str, Any]


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _document_version(content: str) -> str:
    match = re.search(r"^版本：(\S+)", content, re.M)
    if match is None:
        raise PolicyBundleError("Policy source document has no version")
    return match.group(1)


def _detect_secret_fields(value: Any, path: str = "") -> list[str]:
    blocked = {"password", "passwd", "api_key", "apikey", "private_key", "token"}
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized in blocked:
                found.append(child_path)
            found.extend(_detect_secret_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_detect_secret_fields(child, f"{path}[{index}]"))
    return found


class PolicyBundleSnapshotBuilder:
    """Builds a deterministic, reconstructable policy snapshot from project sources."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build(self) -> PolicyBundleCandidate:
        root = self._settings.theory_path.resolve().parent
        theory_bytes = self._settings.theory_path.read_bytes()
        roadmap_path = root / "技术路线与实施路径.md"
        roadmap_bytes = roadmap_path.read_bytes()
        manifest_path = root / "traceability" / "manifest.json"

        roles = load_role_configs(self._settings.agent_config_path)
        skills = SkillRegistry.from_catalog(self._settings.skill_config_path)
        skills.validate_against_roles(roles)
        sources = load_source_policies(self._settings.source_policy_path)
        workflows = WorkflowRegistry.from_catalog(
            self._settings.workflow_catalog_path,
            roles,
        )
        schema_root = root / "schemas"
        schemas = {
            str(path.relative_to(root)): {
                "sha256": _sha256(path.read_bytes()),
                "document": json.loads(path.read_text(encoding="utf-8")),
            }
            for path in sorted(schema_root.glob("*.json"))
        }
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        requirements = [
            {
                "id": item["id"],
                "technical_refs": item.get("technical_refs", []),
                "work_packages": item.get("work_packages", []),
                "acceptance_refs": item.get("acceptance_refs", []),
            }
            for item in manifest.get("requirements", [])
        ]
        components: dict[str, Any] = {
            "theory": {
                "version": _document_version(theory_bytes.decode("utf-8")),
                "sha256": _sha256(theory_bytes),
                "content": theory_bytes.decode("utf-8"),
            },
            "roadmap": {
                "version": _document_version(roadmap_bytes.decode("utf-8")),
                "sha256": _sha256(roadmap_bytes),
                "content": roadmap_bytes.decode("utf-8"),
            },
            "agents": [
                role.model_dump(mode="json")
                for role in sorted(roles.values(), key=lambda x: x.role_id)
            ],
            "skills": [
                skill.definition.model_dump(mode="json") for skill in skills.list()
            ],
            "workflows": [
                {
                    "track": definition.track.value,
                    "sha256": workflows.fingerprint(definition.track),
                    "definition": definition.model_dump(mode="json"),
                }
                for definition in workflows.list()
            ],
            "source_policies": [
                source.model_dump(mode="json")
                for source in sorted(sources.values(), key=lambda x: x.policy_id)
            ],
            "schemas": schemas,
            "requirements": requirements,
        }
        config_files = {}
        for path in sorted((root / "config").rglob("*")):
            if path.is_file() and path.suffix in {".yaml", ".yml", ".json"}:
                config_files[str(path.relative_to(root))] = _sha256(
                    path.read_bytes()
                )
        components["config_files"] = config_files
        secrets = _detect_secret_fields(components)
        if secrets:
            raise PolicyBundleError(
                "Policy bundle would contain secret-like fields: "
                + ", ".join(sorted(secrets))
            )
        component_hashes = {
            key: _sha256(value) for key, value in components.items()
        }
        snapshot = {
            "schema_version": 1,
            "components": components,
            "component_sha256": component_hashes,
            "runtime": {
                "policy_schema_revision": POLICY_SCHEMA_REVISION,
                "output_schemas": sorted(
                    {
                        role.output_schema for role in roles.values()
                    }
                    | {
                        skill.definition.output_schema for skill in skills.list()
                    }
                ),
            },
        }
        content_sha256 = _sha256(snapshot)
        theory_version = str(components["theory"]["version"])
        return PolicyBundleCandidate(
            content_sha256=content_sha256,
            version_label=f"{theory_version}-{content_sha256[:12]}",
            theory_version=theory_version,
            theory_sha256=str(components["theory"]["sha256"]),
            component_sha256=component_hashes,
            snapshot=snapshot,
        )


@lru_cache(maxsize=1)
def _default_builder() -> PolicyBundleSnapshotBuilder:
    return PolicyBundleSnapshotBuilder(get_settings())


@lru_cache(maxsize=1)
def _default_candidate() -> PolicyBundleCandidate:
    return _default_builder().build()


def _actor(session: Session, actor_user_id: UUID) -> User:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise NotFoundError("Actor not found")
    if not actor.is_owner:
        raise PermissionError("Only the verified workspace owner can manage policy bundles")
    set_rls_context(session, workspace_id=actor.workspace_id, user_id=actor.id)
    return actor


def _bundle_view(bundle: PolicyBundle) -> PolicyBundleView:
    return PolicyBundleView(
        id=bundle.id,
        workspace_id=str(bundle.workspace_id),
        version_label=bundle.version_label,
        content_sha256=bundle.content_sha256,
        theory_version=bundle.theory_version,
        theory_sha256=bundle.theory_sha256,
        component_sha256=bundle.component_sha256,
        state=PolicyBundleState(bundle.state),
        created_at=bundle.created_at,
    )


def _impact_view(impact: PolicyImpact) -> PolicyImpactView:
    return PolicyImpactView(
        id=str(impact.id),
        project_id=str(impact.project_id),
        from_bundle_id=impact.from_bundle_id,
        to_bundle_id=impact.to_bundle_id,
        changed_components=list(impact.changed_components),
        affected_requirements=list(impact.affected_requirements),
        affected_task_ids=list(impact.affected_task_ids),
        status=PolicyImpactStatus(impact.status),
        created_at=impact.created_at,
    )


def _migration_view(operation: PolicyMigrationOperation) -> PolicyMigrationView:
    return PolicyMigrationView(
        id=str(operation.id),
        project_id=str(operation.project_id),
        kind=PolicyMigrationKind(operation.kind),
        from_bundle_id=operation.from_bundle_id,
        to_bundle_id=operation.to_bundle_id,
        expected_project_revision=operation.expected_project_revision,
        schema_revision=operation.schema_revision,
        state=PolicyMigrationState(operation.state),
        report=dict(operation.report),
        backup_ref=operation.backup_ref,
        error_code=operation.error_code,
        created_at=operation.created_at,
        finished_at=operation.finished_at,
    )


def _persist_candidate(
    session: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    candidate: PolicyBundleCandidate,
    now: datetime,
) -> PolicyBundle:
    existing = session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.workspace_id == workspace_id,
            PolicyBundle.content_sha256 == candidate.content_sha256,
        )
    )
    if existing is not None:
        return existing
    bundle_id = _sha256(
        {
            "workspace_id": str(workspace_id),
            "content_sha256": candidate.content_sha256,
        }
    )
    bundle = PolicyBundle(
        id=bundle_id,
        workspace_id=workspace_id,
        version_label=candidate.version_label,
        content_sha256=candidate.content_sha256,
        theory_version=candidate.theory_version,
        theory_sha256=candidate.theory_sha256,
        component_sha256=candidate.component_sha256,
        snapshot=candidate.snapshot,
        state=PolicyBundleState.PUBLISHED.value,
        created_by_user_id=actor_user_id,
        created_at=now,
    )
    session.add(bundle)
    session.flush()
    return bundle


def ensure_active_bundle_in_session(
    session: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    now: datetime,
    builder: PolicyBundleSnapshotBuilder | None = None,
) -> str:
    state = session.get(PolicyState, workspace_id, with_for_update=True)
    if state is not None:
        return state.active_bundle_id
    candidate = builder.build() if builder is not None else _default_candidate()
    bundle = _persist_candidate(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        candidate=candidate,
        now=now,
    )
    session.add(
        PolicyState(
            workspace_id=workspace_id,
            active_bundle_id=bundle.id,
            revision=1,
            updated_by_user_id=actor_user_id,
            updated_at=now,
        )
    )
    session.flush()
    return bundle.id


class PolicyBundleService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._builder = PolicyBundleSnapshotBuilder(settings or get_settings())

    def publish_from_config(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> PolicyBundleView:
        candidate = self._builder.build()
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            if actor.workspace_id != workspace_id:
                raise PolicyBundleError("Workspace does not match actor")
            bundle = _persist_candidate(
                session,
                workspace_id=workspace_id,
                actor_user_id=actor.id,
                candidate=candidate,
                now=now,
            )
            state = session.get(PolicyState, workspace_id, with_for_update=True)
            if state is None:
                session.add(
                    PolicyState(
                        workspace_id=workspace_id,
                        active_bundle_id=bundle.id,
                        revision=1,
                        updated_by_user_id=actor.id,
                        updated_at=now,
                    )
                )
            session.flush()
            return _bundle_view(bundle)

    def ensure_active_bundle(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> PolicyBundleView:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            bundle_id = ensure_active_bundle_in_session(
                session,
                workspace_id=workspace_id,
                actor_user_id=actor.id,
                now=datetime.now(UTC),
                builder=self._builder,
            )
            bundle = session.get(PolicyBundle, bundle_id)
            if bundle is None:
                raise NotFoundError("Active policy bundle not found")
            return _bundle_view(bundle)

    def require_runtime_ready(self, *, workspace_id: UUID) -> PolicyBundleView:
        with self._session_factory.begin() as session:
            owner = session.scalar(
                select(User).where(
                    User.workspace_id == workspace_id,
                    User.is_owner.is_(True),
                )
            )
            if owner is None:
                raise PolicyBundleError("Workspace owner is required")
            set_rls_context(
                session,
                workspace_id=workspace_id,
                user_id=owner.id,
            )
            if self._database_revision(session) != POLICY_SCHEMA_REVISION:
                raise PolicyBundleError(
                    "Database schema is not ready for the current policy runtime"
                )
            bundle_id = ensure_active_bundle_in_session(
                session,
                workspace_id=workspace_id,
                actor_user_id=owner.id,
                now=datetime.now(UTC),
                builder=self._builder,
            )
            bundle = session.get(PolicyBundle, bundle_id)
            if bundle is None:
                raise PolicyBundleError("Active policy bundle is missing")
            return _bundle_view(bundle)

    def activate_project_bundle(
        self,
        *,
        project_id: UUID,
        bundle_id: str,
        actor_user_id: UUID,
        expected_revision: int,
        change_source: str = "project.activate",
    ) -> PolicyProjectView:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            project = self._locked_project(session, project_id, actor.workspace_id)
            bundle = session.get(PolicyBundle, bundle_id)
            if bundle is None or bundle.workspace_id != actor.workspace_id:
                raise NotFoundError("Policy bundle not found")
            self._activate_in_session(
                session,
                actor=actor,
                project=project,
                bundle=bundle,
                expected_revision=expected_revision,
                change_source=change_source,
                now=datetime.now(UTC),
            )
            return self._project_view(session, project)

    def project_view(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> PolicyProjectView:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            project = self._project(session, project_id, actor.workspace_id)
            return self._project_view(session, project)

    def dry_run_migration(
        self,
        *,
        project_id: UUID,
        target_bundle_id: str,
        kind: PolicyMigrationKind,
        schema_revision: str | None,
        backup_ref: str | None,
        expected_project_revision: int,
        actor_user_id: UUID,
    ) -> PolicyMigrationView:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            project = self._locked_project(session, project_id, actor.workspace_id)
            target = session.get(PolicyBundle, target_bundle_id)
            if target is None or target.workspace_id != actor.workspace_id:
                raise NotFoundError("Target policy bundle not found")
            current_schema = self._database_revision(session)
            existing = session.scalar(
                select(PolicyMigrationOperation).where(
                    PolicyMigrationOperation.project_id == project.id,
                    PolicyMigrationOperation.to_bundle_id == target.id,
                    PolicyMigrationOperation.kind == kind.value,
                    PolicyMigrationOperation.schema_revision == schema_revision,
                )
            )
            if existing is not None:
                return _migration_view(existing)
            problems: list[str] = []
            if project.revision != expected_project_revision:
                problems.append("PROJECT_REVISION_CONFLICT")
            if kind == PolicyMigrationKind.DATABASE:
                if not schema_revision:
                    problems.append("SCHEMA_REVISION_REQUIRED")
                elif current_schema != schema_revision:
                    problems.append("DATABASE_SCHEMA_NOT_READY")
                if not backup_ref:
                    problems.append("BACKUP_REFERENCE_REQUIRED")
            operation = PolicyMigrationOperation(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                kind=kind.value,
                from_bundle_id=project.policy_bundle_id,
                to_bundle_id=target.id,
                expected_project_revision=expected_project_revision,
                schema_revision=schema_revision,
                state=(
                    PolicyMigrationState.DRY_RUN_FAILED.value
                    if problems
                    else PolicyMigrationState.DRY_RUN_PASSED.value
                ),
                report={
                    "problems": problems,
                    "current_schema_revision": current_schema,
                    "target_schema_revision": schema_revision,
                    "dry_run": True,
                    "business_state_changed": False,
                },
                backup_ref=backup_ref,
                error_code=problems[0] if problems else None,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(operation)
            session.flush()
            return _migration_view(operation)

    def apply_migration(
        self,
        *,
        project_id: UUID,
        operation_id: UUID,
        actor_user_id: UUID,
    ) -> PolicyMigrationView:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            operation = session.scalar(
                select(PolicyMigrationOperation)
                .where(
                    PolicyMigrationOperation.id == operation_id,
                    PolicyMigrationOperation.project_id == project_id,
                    PolicyMigrationOperation.workspace_id == actor.workspace_id,
                )
                .with_for_update()
            )
            if operation is None:
                raise NotFoundError("Policy migration operation not found")
            if operation.state in {
                PolicyMigrationState.SUCCEEDED.value,
                PolicyMigrationState.ROLLED_BACK.value,
            }:
                return _migration_view(operation)
            if operation.state not in {
                PolicyMigrationState.DRY_RUN_PASSED.value,
                PolicyMigrationState.APPLYING.value,
            }:
                raise PolicyBundleError("Only a passed dry-run can be applied")
            project = self._locked_project(session, project_id, actor.workspace_id)
            if (
                operation.state == PolicyMigrationState.APPLYING.value
                and project.policy_bundle_id == operation.to_bundle_id
                and project.revision == operation.expected_project_revision + 1
            ):
                operation.state = PolicyMigrationState.SUCCEEDED.value
                operation.finished_at = datetime.now(UTC)
                return _migration_view(operation)
            if project.revision != operation.expected_project_revision:
                operation.state = PolicyMigrationState.FAILED.value
                operation.error_code = "PROJECT_REVISION_CONFLICT"
                operation.finished_at = datetime.now(UTC)
                return _migration_view(operation)
            if (
                operation.kind == PolicyMigrationKind.DATABASE.value
                and self._database_revision(session) != operation.schema_revision
            ):
                raise PolicyBundleError(
                    "Database schema is not at the requested revision"
                )
            operation.state = PolicyMigrationState.APPLYING.value
            operation.applied_at = datetime.now(UTC)
            operation.report = {
                **operation.report,
                "apply_started": True,
            }
        try:
            target = self._bundle_by_id(
                operation.to_bundle_id,
                workspace_id=actor.workspace_id,
                actor_user_id=actor.id,
            )
            self.activate_project_bundle(
                project_id=project_id,
                bundle_id=target.id,
                actor_user_id=actor_user_id,
                expected_revision=operation.expected_project_revision,
                change_source=f"policy.migration:{operation.id}",
            )
        except Exception as exc:
            with self._session_factory.begin() as session:
                set_rls_context(
                    session,
                    workspace_id=actor.workspace_id,
                    user_id=actor.id,
                )
                failed = session.get(PolicyMigrationOperation, operation_id)
                if failed is not None:
                    failed.state = PolicyMigrationState.FAILED.value
                    failed.error_code = type(exc).__name__.upper()[:100]
                    failed.report = {**failed.report, "error": str(exc)[:2000]}
                    failed.finished_at = datetime.now(UTC)
            raise
        with self._session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            succeeded = session.get(PolicyMigrationOperation, operation_id)
            assert succeeded is not None
            succeeded.state = PolicyMigrationState.SUCCEEDED.value
            succeeded.finished_at = datetime.now(UTC)
            return _migration_view(succeeded)

    def rollback_migration(
        self,
        *,
        project_id: UUID,
        operation_id: UUID,
        actor_user_id: UUID,
    ) -> PolicyMigrationView:
        with self._session_factory.begin() as session:
            actor = _actor(session, actor_user_id)
            operation = session.scalar(
                select(PolicyMigrationOperation)
                .where(
                    PolicyMigrationOperation.id == operation_id,
                    PolicyMigrationOperation.project_id == project_id,
                    PolicyMigrationOperation.workspace_id == actor.workspace_id,
                )
                .with_for_update()
            )
            if operation is None:
                raise NotFoundError("Policy migration operation not found")
            if operation.state == PolicyMigrationState.ROLLED_BACK.value:
                return _migration_view(operation)
            if operation.state != PolicyMigrationState.SUCCEEDED.value:
                raise PolicyBundleError("Only a successful migration can be rolled back")
            if operation.from_bundle_id is None:
                raise PolicyBundleError("Initial bundle activation has no previous bundle")
            project = self._locked_project(session, project_id, actor.workspace_id)
            previous = session.get(PolicyBundle, operation.from_bundle_id)
            if previous is None:
                raise NotFoundError("Previous policy bundle not found")
            self._activate_in_session(
                session,
                actor=actor,
                project=project,
                bundle=previous,
                expected_revision=project.revision,
                change_source=f"policy.rollback:{operation.id}",
                now=datetime.now(UTC),
            )
            operation.state = PolicyMigrationState.ROLLED_BACK.value
            operation.rolled_back_at = datetime.now(UTC)
            operation.finished_at = datetime.now(UTC)
            return _migration_view(operation)

    def _bundle_by_id(
        self,
        bundle_id: str,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
    ) -> PolicyBundle:
        with self._session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=workspace_id,
                user_id=actor_user_id,
            )
            bundle = session.get(PolicyBundle, bundle_id)
            if bundle is None or bundle.workspace_id != workspace_id:
                raise NotFoundError("Policy bundle not found")
            return bundle

    @staticmethod
    def _database_revision(session: Session) -> str | None:
        return session.scalar(text("SELECT version_num FROM alembic_version"))

    @staticmethod
    def _actor(session: Session, actor_user_id: UUID) -> User:
        return _actor(session, actor_user_id)

    @staticmethod
    def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
        project = session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        if project is None:
            raise NotFoundError("Project not found")
        return project

    @staticmethod
    def _locked_project(
        session: Session, project_id: UUID, workspace_id: UUID
    ) -> Project:
        project = session.scalar(
            select(Project)
            .where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        if project is None:
            raise NotFoundError("Project not found")
        return project

    def _activate_in_session(
        self,
        session: Session,
        *,
        actor: User,
        project: Project,
        bundle: PolicyBundle,
        expected_revision: int,
        change_source: str,
        now: datetime,
    ) -> None:
        if project.revision != expected_revision:
            raise RevisionConflictError("Project revision conflict")
        old_bundle_id = project.policy_bundle_id
        if old_bundle_id == bundle.id:
            return
        old_bundle = session.get(PolicyBundle, old_bundle_id) if old_bundle_id else None
        old_snapshot = old_bundle.snapshot if old_bundle is not None else {}
        changed_components, affected_requirements, affected_roles, changed_tracks = (
            self._impact_scope(old_snapshot, bundle.snapshot)
        )
        affected_tasks = self._affected_tasks(
            session,
            project=project,
            old_bundle_id=old_bundle_id,
            affected_roles=affected_roles,
            changed_tracks=changed_tracks,
            global_change=bool(
                set(changed_components)
                & {"theory", "roadmap", "requirements", "schemas", "config_files"}
            ),
        )
        impact = session.scalar(
            select(PolicyImpact).where(
                PolicyImpact.project_id == project.id,
                PolicyImpact.from_bundle_id == old_bundle_id,
                PolicyImpact.to_bundle_id == bundle.id,
            )
        )
        if impact is None:
            impact = PolicyImpact(
                id=uuid4(),
                workspace_id=actor.workspace_id,
                project_id=project.id,
                from_bundle_id=old_bundle_id,
                to_bundle_id=bundle.id,
                change_source=change_source,
                changed_components=changed_components,
                affected_requirements=affected_requirements,
                affected_task_ids=sorted(str(task.id) for task in affected_tasks),
                status=PolicyImpactStatus.RECORDED.value,
                created_by_user_id=actor.id,
                created_at=now,
            )
            session.add(impact)
        if impact.status != PolicyImpactStatus.APPLIED.value:
            for task in affected_tasks:
                self._invalidate_task(
                    session,
                    task,
                    old_bundle_id=old_bundle_id,
                    new_bundle_id=bundle.id,
                    now=now,
                )
            impact.status = PolicyImpactStatus.APPLIED.value
            impact.applied_at = now

        project.policy_bundle_id = bundle.id
        project.revision += 1
        project.updated_at = now
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
                changed_by_user_id=actor.id,
                created_at=now,
            )
        )
        plans = session.scalars(
            select(Plan)
            .where(
                Plan.project_id == project.id,
                Plan.status.in_(["draft", "active", "paused"]),
            )
            .with_for_update()
        ).all()
        for plan in plans:
            plan.policy_bundle_id = bundle.id
            plan.revision += 1
            plan.updated_at = now
        self._append_project_event(
            session,
            project=project,
            actor_user_id=actor.id,
            event_type="policy.bundle_activated",
            object_id=impact.id,
            payload={
                "from_bundle_id": old_bundle_id,
                "to_bundle_id": bundle.id,
                "impact_id": str(impact.id),
                "changed_components": changed_components,
                "affected_requirements": affected_requirements,
                "affected_task_ids": [str(task.id) for task in affected_tasks],
            },
            now=now,
        )
        session.flush()

    @staticmethod
    def _impact_scope(
        old_snapshot: dict[str, Any],
        new_snapshot: dict[str, Any],
    ) -> tuple[list[str], list[str], set[str], set[str]]:
        old_components = old_snapshot.get("components", {})
        new_components = new_snapshot.get("components", {})
        old_hashes = old_snapshot.get("component_sha256", {})
        new_hashes = new_snapshot.get("component_sha256", {})
        changed = sorted(
            key
            for key in old_hashes.keys() | new_hashes.keys()
            if old_hashes.get(key) != new_hashes.get(key)
        )
        if not old_hashes:
            changed = sorted(new_hashes)
        affected_roles: set[str] = set()
        affected_requirements: set[str] = set()
        changed_tracks: set[str] = set()
        requirement_mapping = {
            "theory": {"RQ-001", "RQ-030", "RQ-032"},
            "roadmap": {"RQ-001", "RQ-030", "RQ-032"},
            "agents": {"RQ-004", "RQ-005", "RQ-006"},
            "skills": {"RQ-013", "RQ-025", "RQ-032"},
            "workflows": {"RQ-003", "RQ-018", "RQ-031"},
            "source_policies": {"RQ-011", "RQ-026", "RQ-034"},
            "schemas": {"RQ-001", "RQ-032"},
            "requirements": {"RQ-001", "RQ-030", "RQ-032"},
            "config_files": {"RQ-001", "RQ-030", "RQ-032"},
        }
        for component in changed:
            affected_requirements.update(requirement_mapping.get(component, {"RQ-030"}))
        old_roles = {
            item["role_id"]: item
            for item in old_components.get("agents", [])
            if isinstance(item, dict)
        }
        new_roles = {
            item["role_id"]: item
            for item in new_components.get("agents", [])
            if isinstance(item, dict)
        }
        if "agents" in changed:
            affected_roles.update(
                role_id
                for role_id in old_roles.keys() | new_roles.keys()
                if old_roles.get(role_id) != new_roles.get(role_id)
            )
        if "skills" in changed:
            old_skills = {
                item["skill_id"]: item
                for item in old_components.get("skills", [])
                if isinstance(item, dict)
            }
            new_skills = {
                item["skill_id"]: item
                for item in new_components.get("skills", [])
                if isinstance(item, dict)
            }
            for skill_id in old_skills.keys() | new_skills.keys():
                if old_skills.get(skill_id) != new_skills.get(skill_id):
                    affected_roles.update(
                        (old_skills.get(skill_id) or {}).get("allowed_roles", [])
                    )
                    affected_roles.update(
                        (new_skills.get(skill_id) or {}).get("allowed_roles", [])
                    )
        if "source_policies" in changed:
            old_sources = {
                item["policy_id"]: item
                for item in old_components.get("source_policies", [])
                if isinstance(item, dict)
            }
            new_sources = {
                item["policy_id"]: item
                for item in new_components.get("source_policies", [])
                if isinstance(item, dict)
            }
            changed_policy_ids = {
                policy_id
                for policy_id in old_sources.keys() | new_sources.keys()
                if old_sources.get(policy_id) != new_sources.get(policy_id)
            }
            affected_roles.update(
                role_id
                for role_id, role in new_roles.items()
                if role.get("source_policy") in changed_policy_ids
            )
        if "workflows" in changed:
            old_workflows = {
                item["track"]: item
                for item in old_components.get("workflows", [])
                if isinstance(item, dict)
            }
            new_workflows = {
                item["track"]: item
                for item in new_components.get("workflows", [])
                if isinstance(item, dict)
            }
            changed_tracks = {
                track
                for track in old_workflows.keys() | new_workflows.keys()
                if old_workflows.get(track) != new_workflows.get(track)
            }
        return (
            changed,
            sorted(affected_requirements),
            affected_roles,
            changed_tracks,
        )

    @staticmethod
    def _affected_tasks(
        session: Session,
        *,
        project: Project,
        old_bundle_id: str | None,
        affected_roles: set[str],
        changed_tracks: set[str],
        global_change: bool,
    ) -> list[Task]:
        tasks = session.scalars(
            select(Task)
            .where(
                Task.project_id == project.id,
                Task.state.in_(OPEN_POLICY_TASK_STATES),
            )
            .with_for_update()
        ).all()
        candidates = [
            task
            for task in tasks
            if task.policy_bundle_id == old_bundle_id or old_bundle_id is None
        ]
        if global_change:
            return candidates
        selected = {
            task.id for task in candidates if task.assignee_role in affected_roles
        }
        if changed_tracks:
            plan_tasks = session.scalars(
                select(Task.id)
                .join(PlanNode, PlanNode.task_id == Task.id)
                .join(Plan, Plan.id == PlanNode.plan_id)
                .where(
                    Task.project_id == project.id,
                    Plan.workflow_track.in_(changed_tracks),
                )
            ).all()
            selected.update(plan_tasks)
        return [task for task in candidates if task.id in selected]

    @staticmethod
    def _invalidate_task(
        session: Session,
        task: Task,
        *,
        old_bundle_id: str | None,
        new_bundle_id: str,
        now: datetime,
    ) -> None:
        task.state = (
            TaskState.PAUSED.value
            if task.state in {TaskState.RUNNING.value, TaskState.WAITING_EXTERNAL.value}
            else TaskState.NEEDS_INPUT.value
        )
        task.input_validity = InputValidity.UNDER_REVIEW.value
        task.input_invalidated_at = now
        task.input_invalidated_reason = f"POLICY_BUNDLE_CHANGED:{new_bundle_id}"
        task.input_invalidated_by = [
            value for value in (old_bundle_id, new_bundle_id) if value
        ]
        task.revision += 1
        task.updated_at = now
        session.add(
            TaskVersion(
                id=uuid4(),
                workspace_id=task.workspace_id,
                project_id=task.project_id,
                task_id=task.id,
                task_revision=task.revision,
                state=task.state,
                input_version=task.input_version,
                input_validity=task.input_validity,
                input_snapshot=task.input_snapshot,
                input_snapshot_sha256=task.input_snapshot_sha256,
                input_invalidated_at=task.input_invalidated_at,
                input_invalidated_reason=task.input_invalidated_reason,
                input_invalidated_by=task.input_invalidated_by,
                role_version=task.role_version,
                policy_bundle_id=task.policy_bundle_id,
                created_at=now,
            )
        )
        jobs = session.scalars(
            select(Job)
            .where(
                Job.task_id == task.id,
                Job.state.in_(["queued", "pending"]),
            )
            .with_for_update()
        ).all()
        for job in jobs:
            job.state = "cancelled"
            job.last_error_code = "POLICY_BUNDLE_CHANGED"
            job.finished_at = now
            job.updated_at = now

    @staticmethod
    def _append_project_event(
        session: Session,
        *,
        project: Project,
        actor_user_id: UUID,
        event_type: str,
        object_id: UUID,
        payload: dict[str, Any],
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
                object_type="policy_bundle",
                object_id=object_id,
                object_revision=project.revision,
                payload=payload,
                correlation_id=uuid4(),
                created_at=now,
            )
        )

    def _project_view(self, session: Session, project: Project) -> PolicyProjectView:
        active_state = session.get(PolicyState, project.workspace_id)
        active = (
            session.get(PolicyBundle, active_state.active_bundle_id)
            if active_state is not None
            else None
        )
        current = (
            session.get(PolicyBundle, project.policy_bundle_id)
            if project.policy_bundle_id
            else None
        )
        impacts = session.scalars(
            select(PolicyImpact)
            .where(PolicyImpact.project_id == project.id)
            .order_by(PolicyImpact.created_at.desc())
        ).all()
        migrations = session.scalars(
            select(PolicyMigrationOperation)
            .where(PolicyMigrationOperation.project_id == project.id)
            .order_by(PolicyMigrationOperation.created_at.desc())
        ).all()
        return PolicyProjectView(
            project_id=str(project.id),
            project_revision=project.revision,
            active_bundle=_bundle_view(active) if active is not None else None,
            project_bundle=_bundle_view(current) if current is not None else None,
            impacts=[_impact_view(item) for item in impacts],
            migrations=[_migration_view(item) for item in migrations],
            limitations=[
                "Policy bundles bind configuration provenance; they do not prove "
                "clinical or scientific validity.",
                "Database migration operations verify revision gates but do not "
                "perform live external side effects.",
                "Previously accepted outputs and real external facts remain historical evidence.",
            ],
        )
