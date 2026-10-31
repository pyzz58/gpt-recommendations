from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.domain.policies import AccessAction, SubjectContext
from medical_one_person.domain.skills import SkillState
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import SkillRun, Task
from medical_one_person.infrastructure.skills.registry import (
    RegisteredSkill,
    SkillRegistry,
    canonical_json,
)
from medical_one_person.infrastructure.tool_gateway import (
    ToolDeniedError,
    ToolGateway,
    ToolResult,
    ToolSpec,
)


class SkillUnavailableError(Exception):
    pass


class SkillDeniedError(Exception):
    pass


class SkillOutputValidationError(Exception):
    pass


TOOL_ACTIONS = {
    "artifact.read": AccessAction.ARTIFACT_READ,
    "artifact.write": AccessAction.ARTIFACT_WRITE,
    "evidence.propose": AccessAction.TOOL_EXECUTE,
    "task.request": AccessAction.TOOL_EXECUTE,
    "source.search": AccessAction.NETWORK_REQUEST,
    "source.read": AccessAction.ARTIFACT_READ,
    "mail.draft": AccessAction.MAIL_DRAFT,
    "budget.read": AccessAction.PROJECT_READ,
}


@dataclass(frozen=True)
class ExistingSkillRun:
    id: UUID
    state: str
    output: dict[str, Any] | None


class SkillRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        registry: SkillRegistry,
        gateway: ToolGateway,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry
        self._gateway = gateway
        for registered in registry.list():
            if registered.state == SkillState.READY:
                self._register_skill(registered)

    def execute(
        self,
        *,
        subject: SubjectContext,
        skill_id: str,
        task_id: UUID,
        parameters: dict[str, Any],
    ) -> BaseModel:
        registered = self._registry.get(skill_id)
        definition = registered.definition
        input_bytes = canonical_json(parameters).encode("utf-8")
        if len(input_bytes) > definition.resource_limits.max_input_bytes:
            raise ValueError("Skill input exceeds configured size limit")
        input_hash = hashlib.sha256(input_bytes).hexdigest()
        run_key = hashlib.sha256(
            f"{subject.project_id}:{task_id}:{skill_id}:{definition.version}:{input_hash}".encode()
        ).hexdigest()

        existing = self._existing_run(subject, task_id, run_key, registered)
        if existing is not None and existing.state == "succeeded" and existing.output:
            assert registered.executor is not None
            return registered.executor.output_model.model_validate(existing.output)

        run_id = self._start_run(
            subject=subject,
            task_id=task_id,
            registered=registered,
            run_key=run_key,
            input_hash=input_hash,
            existing=existing,
        )
        if registered.state != SkillState.READY:
            self._finish_run(
                run_id,
                subject.workspace_id,
                state="unavailable",
                error_code=registered.state.value.upper(),
            )
            raise SkillUnavailableError(f"Skill state is {registered.state.value}, not ready")
        if subject.role_id not in definition.allowed_roles:
            self._finish_run(
                run_id,
                subject.workspace_id,
                state="denied",
                error_code="ROLE_NOT_ALLOWED",
            )
            raise SkillDeniedError("Role is not allowed to run this skill")
        available_actions = (
            subject.user_actions
            & subject.project_actions
            & subject.role_capabilities
            & subject.skill_requirements
        )
        for tool_name in definition.required_tools:
            action = TOOL_ACTIONS.get(tool_name)
            if action is None or action not in available_actions:
                self._finish_run(
                    run_id,
                    subject.workspace_id,
                    state="denied",
                    error_code="REQUIRED_TOOL_NOT_AUTHORIZED",
                )
                raise SkillDeniedError(f"Required tool is not authorized: {tool_name}")

        try:
            result = self._gateway.execute(
                subject=subject,
                tool_id=skill_id,
                requested_project_id=subject.project_id,
                target=f"skill:{skill_id}",
                parameters=parameters,
            )
            assert registered.executor is not None
            output = registered.executor.output_model.model_validate(result.data)
            output_bytes = canonical_json(output.model_dump(mode="json")).encode("utf-8")
            if len(output_bytes) > definition.resource_limits.max_output_bytes:
                raise SkillOutputValidationError("Skill output exceeds configured size limit")
        except ToolDeniedError as exc:
            self._finish_run(
                run_id,
                subject.workspace_id,
                state="denied",
                error_code="GATEWAY_DENIED",
            )
            raise SkillDeniedError("Tool gateway denied skill execution") from exc
        except (ValidationError, SkillOutputValidationError) as exc:
            self._finish_run(
                run_id,
                subject.workspace_id,
                state="failed",
                error_code="OUTPUT_SCHEMA_INVALID",
            )
            raise SkillOutputValidationError("Skill output failed schema validation") from exc
        except Exception:
            self._finish_run(
                run_id,
                subject.workspace_id,
                state="failed",
                error_code="SKILL_EXECUTION_FAILED",
            )
            raise

        self._finish_run(
            run_id,
            subject.workspace_id,
            state="succeeded",
            output=output.model_dump(mode="json"),
            error_code=None,
        )
        return output

    def _register_skill(self, registered: RegisteredSkill) -> None:
        executor = registered.executor
        if executor is None:
            return

        def handler(context, parameters):  # type: ignore[no-untyped-def]
            validated = executor.input_model.model_validate(parameters)
            output = executor.handler(validated)
            validated_output = executor.output_model.model_validate(output)
            return ToolResult(
                summary=f"{registered.definition.skill_id} completed",
                data=validated_output.model_dump(mode="json"),
            )

        self._gateway.register(
            ToolSpec(
                tool_id=registered.definition.skill_id,
                action=AccessAction.TOOL_EXECUTE,
                handler=handler,
                network_host=(
                    registered.definition.allowed_network_hosts[0]
                    if registered.definition.network_policy == "allowlisted"
                    and registered.definition.allowed_network_hosts
                    else None
                ),
                has_external_side_effect=(registered.definition.side_effect_class == "external"),
            )
        )

    def _existing_run(
        self,
        subject: SubjectContext,
        task_id: UUID,
        run_key: str,
        registered: RegisteredSkill,
    ) -> ExistingSkillRun | None:
        with self._session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=subject.workspace_id,
                user_id=subject.user_id,
            )
            run = session.scalar(
                select(SkillRun).where(
                    SkillRun.project_id == subject.project_id,
                    SkillRun.task_id == task_id,
                    SkillRun.skill_id == registered.definition.skill_id,
                    SkillRun.run_key == run_key,
                )
            )
            if run is None:
                return None
            return ExistingSkillRun(id=run.id, state=run.state, output=run.output)

    def _start_run(
        self,
        *,
        subject: SubjectContext,
        task_id: UUID,
        registered: RegisteredSkill,
        run_key: str,
        input_hash: str,
        existing: ExistingSkillRun | None,
    ) -> UUID:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=subject.workspace_id,
                user_id=subject.user_id,
            )
            task = session.get(Task, task_id)
            if task is None or task.project_id != subject.project_id:
                raise SkillUnavailableError("Task not found in project")
            if existing is None:
                run = SkillRun(
                    id=uuid4(),
                    workspace_id=task.workspace_id,
                    project_id=task.project_id,
                    task_id=task.id,
                    skill_id=registered.definition.skill_id,
                    skill_version=registered.definition.version,
                    run_key=run_key,
                    mode="mock",
                    input_schema=registered.definition.input_schema,
                    output_schema=registered.definition.output_schema,
                    input_sha256=input_hash,
                    state="running",
                    artifact_manifest=[],
                    created_at=now,
                    started_at=now,
                )
                session.add(run)
                session.flush()
                return run.id
            persisted = session.get(SkillRun, existing.id)
            if persisted is None:
                raise SkillUnavailableError("Existing skill run disappeared")
            persisted.state = "running"
            persisted.error_code = None
            persisted.started_at = now
            persisted.ended_at = None
            return persisted.id

    def _finish_run(
        self,
        run_id: UUID,
        workspace_id: UUID,
        *,
        state: str,
        output: dict[str, Any] | None = None,
        error_code: str | None,
    ) -> None:
        with self._session_factory.begin() as session:
            set_rls_context(session, workspace_id=workspace_id, user_id=None)
            run = session.get(SkillRun, run_id)
            if run is None:
                raise SkillUnavailableError("Skill run disappeared")
            run.state = state
            run.output = output
            run.error_code = error_code
            run.ended_at = datetime.now(UTC)
