from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.domain.policies import (
    AccessAction,
    PolicyDecision,
    PolicyEngine,
    PolicyRequest,
    SubjectContext,
)
from medical_one_person.domain.recovery import NetworkMode
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import ToolAuditEvent


class ToolGatewayError(Exception):
    pass


class ToolDeniedError(ToolGatewayError):
    pass


class UnknownToolError(ToolGatewayError):
    pass


@dataclass(frozen=True)
class ToolContext:
    subject: SubjectContext
    parameters_digest: str


@dataclass(frozen=True)
class ToolResult:
    summary: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    action: AccessAction
    handler: Callable[[ToolContext, Mapping[str, Any]], ToolResult]
    network_host: str | None = None
    has_external_side_effect: bool = False

    @property
    def requires_network(self) -> bool:
        return self.network_host is not None


class ToolGateway:
    """Executes registered tools only after policy, project, and audit checks."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        project_access_checker: Callable[[SubjectContext, UUID], bool],
        policy_engine: PolicyEngine | None = None,
        network_mode: NetworkMode = NetworkMode.OFFLINE,
    ) -> None:
        self._session_factory = session_factory
        self._project_access_checker = project_access_checker
        self._policy_engine = policy_engine or PolicyEngine()
        self._network_mode = network_mode
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.tool_id in self._tools:
            raise ValueError(f"Tool already registered: {spec.tool_id}")
        if spec.tool_id.strip() != spec.tool_id or not spec.tool_id:
            raise ValueError("Tool identifiers must be non-empty and trimmed")
        self._tools[spec.tool_id] = spec

    def execute(
        self,
        *,
        subject: SubjectContext,
        tool_id: str,
        requested_project_id: UUID,
        target: str,
        parameters: Mapping[str, Any],
    ) -> ToolResult:
        spec = self._tools.get(tool_id)
        if spec is None:
            raise UnknownToolError("Tool is not registered")

        parameters_digest = _digest_json(parameters)
        request = PolicyRequest(
            action=spec.action,
            tool_id=spec.tool_id,
            target=target,
            parameters_digest=parameters_digest,
            network_host=spec.network_host,
            has_external_side_effect=spec.has_external_side_effect,
        )
        decision = self._policy_engine.decide(subject, request)
        if spec.requires_network and self._network_mode == NetworkMode.OFFLINE:
            decision = PolicyDecision(
                allowed=False,
                reason_code="OFFLINE_MODE",
                explanation="Remote network tools are disabled in offline mode",
            )
        elif requested_project_id != subject.project_id:
            decision = PolicyDecision(
                allowed=False,
                reason_code="PROJECT_SCOPE_MISMATCH",
                explanation="The requested project differs from the server-resolved subject scope",
            )
        elif not self._project_access_checker(subject, requested_project_id):
            decision = PolicyDecision(
                allowed=False,
                reason_code="PROJECT_ACCESS_DENIED",
                explanation="The subject cannot access the requested project",
            )

        audit_id = uuid4()
        if not decision.allowed:
            self._write_denied_audit(audit_id, subject, SpecRequest(spec, request), decision)
            raise ToolDeniedError(decision.reason_code)

        self._write_authorized_audit(audit_id, subject, SpecRequest(spec, request))
        try:
            result = spec.handler(
                ToolContext(subject=subject, parameters_digest=parameters_digest),
                parameters,
            )
        except Exception:
            self._finish_audit(audit_id, subject, state="failed", reason_code="TOOL_FAILED")
            raise
        self._finish_audit(
            audit_id,
            subject,
            state="succeeded",
            reason_code="COMPLETED",
        )
        return result

    def _write_authorized_audit(
        self, audit_id: UUID, subject: SubjectContext, request: SpecRequest
    ) -> None:
        self._insert_audit(
            audit_id=audit_id,
            subject=subject,
            request=request,
            state="authorized",
            reason_code="ALLOWED",
        )

    def _write_denied_audit(
        self,
        audit_id: UUID,
        subject: SubjectContext,
        request: SpecRequest,
        decision: PolicyDecision,
    ) -> None:
        self._insert_audit(
            audit_id=audit_id,
            subject=subject,
            request=request,
            state="denied",
            reason_code=decision.reason_code,
        )

    def _insert_audit(
        self,
        *,
        audit_id: UUID,
        subject: SubjectContext,
        request: SpecRequest,
        state: str,
        reason_code: str,
    ) -> None:
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=subject.workspace_id,
                user_id=subject.user_id,
            )
            session.add(
                ToolAuditEvent(
                    id=audit_id,
                    workspace_id=subject.workspace_id,
                    project_id=subject.project_id,
                    actor_user_id=subject.user_id,
                    role_id=subject.role_id,
                    tool_id=request.spec.tool_id,
                    action=request.spec.action.value,
                    target_hash=_digest_text(request.policy.target),
                    parameters_hash=request.policy.parameters_digest,
                    state=state,
                    reason_code=reason_code,
                    created_at=now,
                    finished_at=now if state == "denied" else None,
                )
            )

    def _finish_audit(
        self,
        audit_id: UUID,
        subject: SubjectContext,
        *,
        state: str,
        reason_code: str,
    ) -> None:
        with self._session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=subject.workspace_id,
                user_id=subject.user_id,
            )
            audit = session.get(ToolAuditEvent, audit_id)
            if audit is None:
                raise ToolGatewayError("Tool audit record disappeared before completion")
            audit.state = state
            audit.reason_code = reason_code
            audit.finished_at = datetime.now(UTC)


@dataclass(frozen=True)
class SpecRequest:
    spec: ToolSpec
    policy: PolicyRequest


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_json(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _digest_text(canonical)
