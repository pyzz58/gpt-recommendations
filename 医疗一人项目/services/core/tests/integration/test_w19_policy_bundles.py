from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import load_role_configs
from medical_one_person.agents.runner import AgentRunner
from medical_one_person.application.errors import RevisionConflictError
from medical_one_person.application.policy_bundles import (
    POLICY_SCHEMA_REVISION,
    PolicyBundleCandidate,
    PolicyBundleError,
    PolicyBundleService,
    _persist_candidate,
    _sha256,
)
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.scheduling import JobQueue, OutboxDispatcher
from medical_one_person.application.tasks import TaskService
from medical_one_person.domain.policy_bundles import (
    PolicyMigrationKind,
    PolicyMigrationState,
)
from medical_one_person.domain.tasks import TaskState
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    AgentRun,
    PolicyBundle,
    Task,
    TaskVersion,
    User,
)
from medical_one_person.providers import FakeModelProvider

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _project(session_factory: sessionmaker[Session], suffix: str):
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name=f"W19策略{suffix}",
        scope="验证不可变策略基线、影响范围与迁移账本。",
        idempotency_key=f"w19-project-{suffix}",
    )
    return identity, project


def _task(
    session_factory: sessionmaker[Session],
    identity,
    project,
    *,
    role_id: str,
    purpose: str,
):
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="policy.verification",
        purpose=purpose,
        assignee_role=role_id,
        role_version="1",
        input_version="v1",
        input_refs=[f"fixture:{purpose}"],
        goal="验证固定策略基线和影响门。",
        deliverable_schema="agent_delivery.v1",
        acceptance_policy="independent_review.v1",
    )
    return task


def _variant_bundle(
    session_factory: sessionmaker[Session],
    identity,
    base_bundle_id: str,
    *,
    role_id: str = "A02",
) -> str:
    with session_factory.begin() as session:
        actor = session.get(User, identity.owner_user_id)
        assert actor is not None
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        base = session.get(PolicyBundle, base_bundle_id)
        assert base is not None
        snapshot = copy.deepcopy(base.snapshot)
        components = snapshot["components"]
        role_rows = components["agents"]
        role = next(item for item in role_rows if item["role_id"] == role_id)
        role["tools_allow"] = role["tools_allow"][:-1]
        components["agents"] = role_rows
        component_hashes = {
            key: _sha256(value) for key, value in components.items()
        }
        snapshot["component_sha256"] = component_hashes
        content_sha256 = _sha256(snapshot)
        candidate = PolicyBundleCandidate(
            content_sha256=content_sha256,
            version_label=f"variant-{content_sha256[:12]}",
            theory_version=base.theory_version,
            theory_sha256=base.theory_sha256,
            component_sha256=component_hashes,
            snapshot=snapshot,
        )
        bundle = _persist_candidate(
            session,
            workspace_id=identity.workspace_id,
            actor_user_id=identity.owner_user_id,
            candidate=candidate,
            now=datetime.now(UTC),
        )
        return bundle.id


def test_policy_bundle_publish_is_immutable_and_idempotent(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(session_factory, "发布")
    assert project.policy_bundle_id is not None
    service = PolicyBundleService(session_factory)
    first = service.publish_from_config(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
    )
    replay = service.publish_from_config(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
    )
    assert first == replay
    assert first.id == project.policy_bundle_id
    assert first.theory_version == "V0.10"
    assert set(first.component_sha256) >= {
        "theory",
        "roadmap",
        "agents",
        "skills",
        "workflows",
        "source_policies",
        "schemas",
        "requirements",
    }
    view = service.project_view(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert view.active_bundle is not None
    assert view.project_bundle is not None
    assert view.project_bundle.id == first.id


def test_policy_activation_only_invalidates_affected_tasks_and_preserves_run_basis(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(session_factory, "影响")
    old_bundle_id = project.policy_bundle_id
    assert old_bundle_id is not None
    affected = _task(
        session_factory,
        identity,
        project,
        role_id="A02",
        purpose="affected-role",
    )
    unaffected = _task(
        session_factory,
        identity,
        project,
        role_id="A03",
        purpose="unaffected-role",
    )

    tasks = TaskService(session_factory)
    tasks.enqueue(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=affected.id,
    )
    OutboxDispatcher(session_factory).dispatch_once(workspace_id=identity.workspace_id)
    queue = JobQueue(session_factory)
    claim = queue.claim(
        workspace_id=identity.workspace_id,
        worker_id="w19-policy",
    )
    assert claim is not None
    runner = AgentRunner(
        session_factory,
        FakeModelProvider(),
        load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml"),
        theory_hash="0" * 64,
        job_queue=queue,
    )
    runner.run_claim(claim)

    new_bundle_id = _variant_bundle(
        session_factory,
        identity,
        old_bundle_id,
    )
    service = PolicyBundleService(session_factory)
    activated = service.activate_project_bundle(
        project_id=project.id,
        bundle_id=new_bundle_id,
        actor_user_id=identity.owner_user_id,
        expected_revision=project.revision,
    )
    assert activated.project_bundle is not None
    assert activated.project_bundle.id == new_bundle_id
    assert activated.impacts[0].changed_components == ["agents"]

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        affected_row = session.get(Task, affected.id)
        unaffected_row = session.get(Task, unaffected.id)
        old_run = session.scalar(
            select(AgentRun).where(AgentRun.task_id == affected.id)
        )
    assert affected_row is not None
    assert affected_row.state == TaskState.NEEDS_INPUT.value
    assert affected_row.input_validity == "under_review"
    assert affected_row.policy_bundle_id == old_bundle_id
    assert unaffected_row is not None
    assert unaffected_row.state == TaskState.READY.value
    assert unaffected_row.policy_bundle_id == old_bundle_id
    assert old_run is not None
    assert old_run.policy_bundle_id == old_bundle_id
    assert old_run.theory_hash != "0" * 64

    revised = tasks.revise_inputs(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_id=affected.id,
        expected_revision=affected_row.revision,
        input_version="v2",
        input_refs=["fixture:affected-role-v2"],
    )
    assert revised.policy_bundle_id == new_bundle_id
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        versions = session.scalars(
            select(TaskVersion)
            .where(TaskVersion.task_id == affected.id)
            .order_by(TaskVersion.task_revision)
        ).all()
    assert versions[0].policy_bundle_id == old_bundle_id
    assert versions[-1].policy_bundle_id == new_bundle_id


def test_policy_migration_dry_run_apply_and_rollback_keep_history(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(session_factory, "迁移")
    old_bundle_id = project.policy_bundle_id
    assert old_bundle_id is not None
    target_bundle_id = _variant_bundle(
        session_factory,
        identity,
        old_bundle_id,
    )
    service = PolicyBundleService(session_factory)
    dry_run = service.dry_run_migration(
        project_id=project.id,
        target_bundle_id=target_bundle_id,
        kind=PolicyMigrationKind.CONFIG,
        schema_revision=None,
        backup_ref=None,
        expected_project_revision=project.revision,
        actor_user_id=identity.owner_user_id,
    )
    assert dry_run.state == PolicyMigrationState.DRY_RUN_PASSED
    project_before_apply = service.project_view(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert project_before_apply.project_bundle is not None
    assert project_before_apply.project_bundle.id == old_bundle_id

    applied = service.apply_migration(
        project_id=project.id,
        operation_id=UUID(dry_run.id),
        actor_user_id=identity.owner_user_id,
    )
    assert applied.state == PolicyMigrationState.SUCCEEDED
    replay = service.apply_migration(
        project_id=project.id,
        operation_id=UUID(dry_run.id),
        actor_user_id=identity.owner_user_id,
    )
    assert replay.state == PolicyMigrationState.SUCCEEDED
    project_after_apply = service.project_view(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert project_after_apply.project_bundle is not None
    assert project_after_apply.project_bundle.id == target_bundle_id

    rolled_back = service.rollback_migration(
        project_id=project.id,
        operation_id=UUID(applied.id),
        actor_user_id=identity.owner_user_id,
    )
    assert rolled_back.state == PolicyMigrationState.ROLLED_BACK
    project_after_rollback = service.project_view(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
    )
    assert project_after_rollback.project_bundle is not None
    assert project_after_rollback.project_bundle.id == old_bundle_id
    assert project_after_rollback.impacts


def test_database_migration_requires_schema_and_backup(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(session_factory, "数据库门")
    assert project.policy_bundle_id is not None
    target_bundle_id = _variant_bundle(
        session_factory,
        identity,
        project.policy_bundle_id,
        role_id="A04",
    )
    service = PolicyBundleService(session_factory)
    failed = service.dry_run_migration(
        project_id=project.id,
        target_bundle_id=target_bundle_id,
        kind=PolicyMigrationKind.DATABASE,
        schema_revision="wrong-revision",
        backup_ref=None,
        expected_project_revision=project.revision,
        actor_user_id=identity.owner_user_id,
    )
    assert failed.state == PolicyMigrationState.DRY_RUN_FAILED
    assert cast_report(failed.report)["problems"] == [
        "DATABASE_SCHEMA_NOT_READY",
        "BACKUP_REFERENCE_REQUIRED",
    ]
    with pytest.raises(PolicyBundleError, match="passed dry-run"):
        service.apply_migration(
            project_id=project.id,
            operation_id=UUID(failed.id),
            actor_user_id=identity.owner_user_id,
        )

    passed = service.dry_run_migration(
        project_id=project.id,
        target_bundle_id=target_bundle_id,
        kind=PolicyMigrationKind.DATABASE,
        schema_revision=POLICY_SCHEMA_REVISION,
        backup_ref="fixture:w19-backup",
        expected_project_revision=project.revision,
        actor_user_id=identity.owner_user_id,
    )
    assert passed.state == PolicyMigrationState.DRY_RUN_PASSED


def test_stale_expected_revision_rejects_policy_activation(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project = _project(session_factory, "并发")
    assert project.policy_bundle_id is not None
    target_bundle_id = _variant_bundle(
        session_factory,
        identity,
        project.policy_bundle_id,
    )
    with pytest.raises(RevisionConflictError):
        PolicyBundleService(session_factory).activate_project_bundle(
            project_id=project.id,
            bundle_id=target_bundle_id,
            actor_user_id=identity.owner_user_id,
            expected_revision=project.revision + 1,
        )
def cast_report(value):
    assert isinstance(value, dict)
    return value
