from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.policies import AccessAction, SubjectContext
from medical_one_person.domain.recovery import NetworkMode
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    CommandReceipt,
    Project,
    ToolAuditEvent,
)
from medical_one_person.infrastructure.tool_gateway import (
    ToolDeniedError,
    ToolGateway,
    ToolResult,
    ToolSpec,
)


def test_postgres_rls_hides_other_workspace_and_resets_pooled_context(
    session_factory: sessionmaker[Session],
) -> None:
    first = bootstrap_local_owner(
        session_factory, workspace_name="隔离工作区 A", owner_name="负责人 A"
    )
    second = bootstrap_local_owner(
        session_factory, workspace_name="隔离工作区 B", owner_name="负责人 B"
    )
    service = ProjectService(session_factory)
    project_a = service.create_project(
        actor_user_id=first.owner_user_id,
        name="项目 A",
        scope="仅 A 工作区可见。",
        idempotency_key="create-rls-a",
    )
    project_b = service.create_project(
        actor_user_id=second.owner_user_id,
        name="项目 B",
        scope="仅 B 工作区可见。",
        idempotency_key="create-rls-b",
    )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=first.workspace_id,
            user_id=first.owner_user_id,
        )
        visible = session.scalars(select(Project).order_by(Project.name)).all()
        hidden = session.get(Project, project_b.id)
        receipt_count = session.scalar(select(func.count()).select_from(CommandReceipt))

    assert [project.id for project in visible] == [project_a.id]
    assert hidden is None
    assert receipt_count == 1

    with session_factory.begin() as session:
        visible_without_context = session.scalars(select(Project)).all()
        receipt_without_context = session.scalar(select(func.count()).select_from(CommandReceipt))
    assert visible_without_context == []
    assert receipt_without_context == 0


def test_tool_gateway_denies_cross_project_role_and_network_escalation(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="工具隔离项目",
        scope="验证服务端授权交集和审计。",
        idempotency_key="create-tool-isolation-project",
    )

    calls: list[str] = []

    def safe_handler(context, parameters):  # type: ignore[no-untyped-def]
        calls.append("safe")
        return ToolResult(summary="safe", data={"parameters": context.parameters_digest})

    def network_handler(context, parameters):  # type: ignore[no-untyped-def]
        calls.append("network")
        return ToolResult(summary="network", data={})

    def project_access(subject: SubjectContext, project_id: UUID) -> bool:
        with session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=subject.workspace_id,
                user_id=subject.user_id,
            )
            return session.get(Project, project_id) is not None

    gateway = ToolGateway(
        session_factory,
        project_access_checker=project_access,
        network_mode=NetworkMode.ALLOWLISTED,
    )
    gateway.register(
        ToolSpec(
            tool_id="safe.echo",
            action=AccessAction.TOOL_EXECUTE,
            handler=safe_handler,
        )
    )
    gateway.register(
        ToolSpec(
            tool_id="network.fetch",
            action=AccessAction.TOOL_EXECUTE,
            handler=network_handler,
            network_host="example.com",
        )
    )

    base_actions = frozenset(
        {
            AccessAction.PROJECT_READ,
            AccessAction.TOOL_EXECUTE,
        }
    )
    subject = SubjectContext(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A24",
        user_actions=base_actions,
        project_actions=base_actions,
        role_capabilities=base_actions,
        skill_requirements=base_actions,
    )

    result = gateway.execute(
        subject=subject,
        tool_id="safe.echo",
        requested_project_id=project.id,
        target="synthetic-target",
        parameters={"record_id": "synthetic-1"},
    )
    assert result.summary == "safe"
    assert calls == ["safe"]

    with pytest.raises(ToolDeniedError, match="NETWORK_NOT_GRANTED"):
        gateway.execute(
            subject=subject,
            tool_id="network.fetch",
            requested_project_id=project.id,
            target="example.com",
            parameters={},
        )
    assert calls == ["safe"]

    with pytest.raises(ToolDeniedError, match="PROJECT_SCOPE_MISMATCH"):
        gateway.execute(
            subject=subject,
            tool_id="safe.echo",
            requested_project_id=UUID(int=999),
            target="other-project",
            parameters={},
        )

    no_tool_grant = SubjectContext(
        user_id=subject.user_id,
        workspace_id=subject.workspace_id,
        project_id=subject.project_id,
        role_id="A20",
        user_actions=base_actions,
        project_actions=base_actions,
        role_capabilities=frozenset({AccessAction.PROJECT_READ}),
        skill_requirements=base_actions,
    )
    with pytest.raises(ToolDeniedError, match="ACTION_NOT_GRANTED"):
        gateway.execute(
            subject=no_tool_grant,
            tool_id="safe.echo",
            requested_project_id=project.id,
            target="budget-only",
            parameters={},
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        audits = session.scalars(select(ToolAuditEvent).order_by(ToolAuditEvent.created_at)).all()
    assert [audit.state for audit in audits] == [
        "succeeded",
        "denied",
        "denied",
        "denied",
    ]
    assert [audit.tool_id for audit in audits] == [
        "safe.echo",
        "network.fetch",
        "safe.echo",
        "safe.echo",
    ]
    assert all(len(audit.parameters_hash) == 64 for audit in audits)
    assert "synthetic-1" not in repr([audit.parameters_hash for audit in audits])


def test_external_side_effect_requires_unexpired_authorization(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="外部动作项目",
        scope="不得无授权发送。",
        idempotency_key="create-external-project",
    )
    called = False

    def send_handler(context, parameters):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        return ToolResult(summary="sent", data={})

    def project_access(subject: SubjectContext, project_id: UUID) -> bool:
        return project_id == subject.project_id

    gateway = ToolGateway(session_factory, project_access_checker=project_access)
    gateway.register(
        ToolSpec(
            tool_id="mail.send",
            action=AccessAction.MAIL_SEND,
            handler=send_handler,
            has_external_side_effect=True,
        )
    )
    actions = frozenset({AccessAction.MAIL_SEND})
    expired = SubjectContext(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A23",
        user_actions=actions,
        project_actions=actions,
        role_capabilities=actions,
        skill_requirements=actions,
        external_authorized=True,
        external_authorization_expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    with pytest.raises(ToolDeniedError, match="EXTERNAL_AUTHORIZATION_EXPIRED"):
        gateway.execute(
            subject=expired,
            tool_id="mail.send",
            requested_project_id=project.id,
            target="synthetic-recipient",
            parameters={"draft": "synthetic"},
        )
    assert called is False
    authorized = SubjectContext(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A23",
        user_actions=actions,
        project_actions=actions,
        role_capabilities=actions,
        skill_requirements=actions,
        external_authorized=True,
        external_authorization_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    result = gateway.execute(
        subject=authorized,
        tool_id="mail.send",
        requested_project_id=project.id,
        target="synthetic-recipient",
        parameters={"draft": "synthetic"},
    )
    assert result.summary == "sent"
    assert called is True


def test_offline_mode_blocks_registered_network_tool_before_handler(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="离线模式项目",
        scope="验证断网时远程工具被拒绝。",
        idempotency_key="create-offline-project",
    )
    called = False

    def network_handler(context, parameters):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        return ToolResult(summary="network", data={})

    gateway = ToolGateway(
        session_factory,
        project_access_checker=lambda subject, project_id: project_id == subject.project_id,
    )
    gateway.register(
        ToolSpec(
            tool_id="network.fetch",
            action=AccessAction.TOOL_EXECUTE,
            handler=network_handler,
            network_host="example.com",
        )
    )
    actions = frozenset(
        {
            AccessAction.NETWORK_REQUEST,
            AccessAction.TOOL_EXECUTE,
        }
    )
    subject = SubjectContext(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A24",
        user_actions=actions,
        project_actions=actions,
        role_capabilities=actions,
        skill_requirements=actions,
        allowed_network_hosts=frozenset({"example.com"}),
    )

    with pytest.raises(ToolDeniedError, match="OFFLINE_MODE"):
        gateway.execute(
            subject=subject,
            tool_id="network.fetch",
            requested_project_id=project.id,
            target="example.com",
            parameters={"query": "synthetic"},
        )
    assert called is False
