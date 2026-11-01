from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.projects import ProjectService
from medical_one_person.application.skills import (
    SkillDeniedError,
    SkillOutputValidationError,
    SkillRunner,
    SkillUnavailableError,
)
from medical_one_person.application.tasks import TaskService
from medical_one_person.domain.policies import AccessAction, SubjectContext
from medical_one_person.infrastructure.bootstrap import bootstrap_local_owner
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Project,
    SkillRun,
    ToolAuditEvent,
)
from medical_one_person.infrastructure.skills.registry import SkillRegistry
from medical_one_person.infrastructure.tool_gateway import ToolGateway


def _catalog() -> Path:
    return Path(__file__).resolve().parents[4] / "config" / "skills" / "catalog.yaml"


def _subject(
    *,
    user_id: UUID,
    workspace_id: UUID,
    project_id: UUID,
    role_id: str,
    actions: set[AccessAction],
) -> SubjectContext:
    capabilities = frozenset(actions)
    return SubjectContext(
        user_id=user_id,
        workspace_id=workspace_id,
        project_id=project_id,
        role_id=role_id,
        user_actions=capabilities,
        project_actions=capabilities,
        role_capabilities=capabilities,
        skill_requirements=capabilities,
    )


def test_builtin_skill_is_authorized_schema_validated_audited_and_idempotent(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="技能执行项目",
        scope="验证数值技能授权、输出和审计。",
        idempotency_key="create-skill-project",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="statistics.summary",
        purpose="numeric-summary",
        assignee_role="A14",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:numbers"],
        goal="计算合成数值描述统计。",
        deliverable_schema="numeric_summary.output.v1",
        acceptance_policy="statistics_review.v1",
        mode="mock",
    )

    def project_access(subject: SubjectContext, project_id: UUID) -> bool:
        with session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=subject.workspace_id,
                user_id=subject.user_id,
            )
            return session.get(Project, project_id) is not None

    gateway = ToolGateway(session_factory, project_access_checker=project_access)
    runner = SkillRunner(
        session_factory,
        SkillRegistry.from_catalog(_catalog()),
        gateway,
    )
    actions = {AccessAction.TOOL_EXECUTE}
    subject = _subject(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A14",
        actions=actions,
    )
    parameters = {"numbers": [1, 2, 3, 4], "unit": "synthetic"}

    output = runner.execute(
        subject=subject,
        skill_id="data.numeric_summary",
        task_id=task.id,
        parameters=parameters,
    )
    replay = runner.execute(
        subject=subject,
        skill_id="data.numeric_summary",
        task_id=task.id,
        parameters=parameters,
    )

    assert output.model_dump() == replay.model_dump()
    assert output.count == 4
    assert output.mean == 2.5
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        runs = session.scalars(select(SkillRun)).all()
        audits = session.scalars(select(ToolAuditEvent)).all()
    assert len(runs) == 1
    assert runs[0].state == "succeeded"
    assert runs[0].output is not None
    assert len(audits) == 1
    assert audits[0].state == "succeeded"
    assert audits[0].task_id == task.id
    assert audits[0].correlation_id == runs[0].id


def test_skill_denials_and_missing_dependency_are_recorded(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="技能拒绝项目",
        scope="验证角色、工具和依赖拒绝。",
        idempotency_key="create-skill-denial-project",
    )

    def project_access(subject: SubjectContext, project_id: UUID) -> bool:
        return project_id == subject.project_id

    gateway = ToolGateway(session_factory, project_access_checker=project_access)
    runner = SkillRunner(
        session_factory,
        SkillRegistry.from_catalog(_catalog()),
        gateway,
    )
    task_service = TaskService(session_factory)
    hash_task = task_service.create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="artifact.hash",
        purpose="hash",
        assignee_role="A15",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:artifact"],
        goal="计算合成文本哈希。",
        deliverable_schema="artifact_hash.output.v1",
        acceptance_policy="quality_review.v1",
        mode="mock",
    )
    wrong_role = _subject(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A20",
        actions={AccessAction.TOOL_EXECUTE, AccessAction.ARTIFACT_WRITE},
    )
    with pytest.raises(SkillDeniedError, match="Role"):
        runner.execute(
            subject=wrong_role,
            skill_id="artifact.hash",
            task_id=hash_task.id,
            parameters={"content": "synthetic"},
        )

    missing_tool = _subject(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A15",
        actions={AccessAction.TOOL_EXECUTE},
    )
    with pytest.raises(SkillDeniedError, match="Required tool"):
        runner.execute(
            subject=missing_tool,
            skill_id="artifact.hash",
            task_id=hash_task.id,
            parameters={"content": "synthetic-other"},
        )

    literature_task = task_service.create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="literature.search",
        purpose="missing-search-adapter",
        assignee_role="A04",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:search"],
        goal="请求未配置的专业检索。",
        deliverable_schema="literature_search.output.v1",
        acceptance_policy="evidence_review.v1",
        mode="mock",
    )
    unavailable = _subject(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A04",
        actions={
            AccessAction.TOOL_EXECUTE,
            AccessAction.NETWORK_REQUEST,
            AccessAction.ARTIFACT_READ,
        },
    )
    with pytest.raises(SkillUnavailableError):
        runner.execute(
            subject=unavailable,
            skill_id="literature.search",
            task_id=literature_task.id,
            parameters={"query": "synthetic"},
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        runs = session.scalars(select(SkillRun).order_by(SkillRun.created_at)).all()
    assert [run.state for run in runs] == ["denied", "denied", "unavailable"]


def test_invalid_skill_input_fails_schema_and_audit(
    session_factory: sessionmaker[Session],
) -> None:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="技能输入失败项目",
        scope="验证输入错误可追踪。",
        idempotency_key="create-skill-invalid-project",
    )
    task = TaskService(session_factory).create_task(
        project_id=project.id,
        actor_user_id=identity.owner_user_id,
        task_type="statistics.summary",
        purpose="invalid",
        assignee_role="A14",
        role_version="1",
        input_version="v1",
        input_refs=["fixture:invalid"],
        goal="验证错误输入。",
        deliverable_schema="numeric_summary.output.v1",
        acceptance_policy="statistics_review.v1",
        mode="mock",
    )

    def project_access(subject: SubjectContext, project_id: UUID) -> bool:
        return project_id == subject.project_id

    gateway = ToolGateway(session_factory, project_access_checker=project_access)
    runner = SkillRunner(
        session_factory,
        SkillRegistry.from_catalog(_catalog()),
        gateway,
    )
    subject = _subject(
        user_id=identity.owner_user_id,
        workspace_id=identity.workspace_id,
        project_id=project.id,
        role_id="A14",
        actions={AccessAction.TOOL_EXECUTE},
    )
    with pytest.raises(SkillOutputValidationError):
        runner.execute(
            subject=subject,
            skill_id="data.numeric_summary",
            task_id=task.id,
            parameters={"numbers": [], "unit": "synthetic"},
        )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        run = session.scalar(select(SkillRun))
        audit = session.scalar(select(ToolAuditEvent))
        count = session.scalar(select(func.count()).select_from(SkillRun))
    assert count == 1
    assert run is not None and run.state == "failed"
    assert audit is not None and audit.state == "failed"
