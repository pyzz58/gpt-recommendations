from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.artifacts import ArtifactService
from medical_one_person.application.conversations import ConversationService
from medical_one_person.application.errors import (
    IdempotencyConflictError,
    NotFoundError,
    RevisionConflictError,
)
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.sessions import SessionService
from medical_one_person.domain.artifacts import ArtifactMode, ArtifactOrigin
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.engine import database_status
from medical_one_person.infrastructure.db.models import (
    ProjectEvent,
    ProjectVersion,
)
from medical_one_person.infrastructure.db.models import (
    Session as DatabaseSession,
)


def test_project_creation_versions_events_and_restart_recovery(
    database: Engine,
    app_database_url: str,
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    service = ProjectService(session_factory)

    project = service.create_project(
        actor_user_id=identity.owner_user_id,
        name="合成项目",
        scope="验证项目创建、版本和事件持久化。",
        idempotency_key="create-project-1",
    )
    replay = service.create_project(
        actor_user_id=identity.owner_user_id,
        name="合成项目",
        scope="验证项目创建、版本和事件持久化。",
        idempotency_key="create-project-1",
    )

    assert replay == project
    assert database_status(database).status == "ready"
    with pytest.raises(IdempotencyConflictError):
        service.create_project(
            actor_user_id=identity.owner_user_id,
            name="不同请求",
            scope="同一个幂等键不能复用为不同参数。",
            idempotency_key="create-project-1",
        )

    restarted_engine = create_engine(app_database_url)
    restarted_factory = sessionmaker(bind=restarted_engine, expire_on_commit=False)
    try:
        restarted_service = ProjectService(restarted_factory)
        projects = restarted_service.list_projects(identity.workspace_id)
        assert [item.id for item in projects] == [project.id]
        with restarted_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=identity.workspace_id,
                user_id=identity.owner_user_id,
            )
            assert session.scalar(select(func.count()).select_from(ProjectVersion)) == 1
            event = session.scalar(select(ProjectEvent))
            assert event is not None
            assert event.project_seq == 1
            assert event.type == "project.created"
    finally:
        restarted_engine.dispose()


def test_project_revision_conflict_preserves_history(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    service = ProjectService(session_factory)
    project = service.create_project(
        actor_user_id=identity.owner_user_id,
        name="版本测试",
        scope="检查乐观版本和不可变版本记录。",
        idempotency_key="create-versioned-project",
    )

    updated = service.rename_project(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=1,
        name="版本测试 V2",
        idempotency_key="rename-project-1",
    )
    assert updated.revision == 2
    original_replay = service.create_project(
        actor_user_id=identity.owner_user_id,
        name="版本测试",
        scope="检查乐观版本和不可变版本记录。",
        idempotency_key="create-versioned-project",
    )
    assert original_replay.name == "版本测试"
    assert original_replay.revision == 1

    with pytest.raises(RevisionConflictError):
        service.rename_project(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            expected_revision=1,
            name="过期写入",
            idempotency_key="rename-project-stale",
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        versions = session.scalars(
            select(ProjectVersion).order_by(ProjectVersion.project_revision)
        ).all()
        events = session.scalars(select(ProjectEvent).order_by(ProjectEvent.project_seq)).all()
    assert [version.name for version in versions] == ["版本测试", "版本测试 V2"]
    assert [event.project_seq for event in events] == [1, 2]


def test_opaque_sessions_persist_and_revoke(
    app_database_url: str,
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    service = SessionService(session_factory)
    issued = service.issue(user_id=identity.owner_user_id)

    with session_factory() as session:
        stored = session.scalar(select(DatabaseSession))
        assert stored is not None
        assert stored.session_hash != issued.token
        assert len(stored.session_hash) == 64

    restarted_engine = create_engine(app_database_url)
    try:
        restarted_service = SessionService(
            sessionmaker(bind=restarted_engine, expire_on_commit=False)
        )
        principal = restarted_service.authenticate(issued.token)
        assert principal is not None
        assert principal.user_id == identity.owner_user_id

        restarted_service.revoke(issued.session_id)
        assert restarted_service.authenticate(issued.token) is None
    finally:
        restarted_engine.dispose()

    expired = service.issue(user_id=identity.owner_user_id, ttl=timedelta(seconds=-1))
    assert service.authenticate(expired.token) is None


def test_content_addressed_artifacts_and_conversation_events(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="资料与对话",
        scope="验证本地原件和项目事件。",
        idempotency_key="create-artifact-project",
    )
    store = LocalArtifactStore(tmp_path / "objects")
    artifacts = ArtifactService(session_factory, store)
    content = "合成研究资料\n".encode()

    first = artifacts.create_version(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        title="合成研究资料.txt",
        media_type="text/plain",
        content=content,
        mode=ArtifactMode.MOCK,
        origin=ArtifactOrigin.RAW,
        producer="w02-integration-test",
    )
    second = artifacts.create_version(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        title="合成研究资料.txt",
        media_type="text/plain",
        content=content,
        mode=ArtifactMode.MOCK,
        origin=ArtifactOrigin.RAW,
        producer="w02-integration-test",
    )
    assert first.object_key == second.object_key
    assert (first.version, second.version) == (1, 2)
    assert store.read(first.object_key, first.sha256) == content

    conversations = ConversationService(session_factory)
    conversation = conversations.create(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        title="合成对话",
    )
    message = conversations.append_message(
        project_id=project.id,
        conversation_id=conversation.id,
        actor_user_id=identity.owner_user_id,
        speaker="user",
        content="这是模拟输入，不是科学结论。",
        source_kind="user_input",
    )
    assert message.project_id == project.id

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        event_types = session.scalars(
            select(ProjectEvent.type).order_by(ProjectEvent.project_seq)
        ).all()
    assert event_types == [
        "project.created",
        "artifact.version_created",
        "artifact.version_created",
        "conversation.message_created",
    ]


def test_cross_workspace_actor_cannot_attach_artifact(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    first = bootstrap_local_owner(session_factory, workspace_name="项目 A", owner_name="负责人 A")
    second = bootstrap_local_owner(session_factory, workspace_name="项目 B", owner_name="负责人 B")
    project = ProjectService(session_factory).create_project(
        actor_user_id=first.owner_user_id,
        name="隔离项目",
        scope="检查跨工作区拒绝。",
        idempotency_key="create-isolation-project",
    )

    object_root = tmp_path / "objects"
    service = ArtifactService(session_factory, LocalArtifactStore(object_root))
    with pytest.raises(NotFoundError):
        service.create_version(
            project_id=project.id,
            actor_user_id=second.owner_user_id,
            title="不应写入.txt",
            media_type="text/plain",
            content=b"not allowed",
            mode=ArtifactMode.MOCK,
            origin=ArtifactOrigin.RAW,
            producer="test",
        )
    assert not list(object_root.rglob("*.*"))
