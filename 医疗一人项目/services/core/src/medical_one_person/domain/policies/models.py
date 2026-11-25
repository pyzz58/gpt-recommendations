from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class AccessAction(StrEnum):
    PROJECT_READ = "project.read"
    PROJECT_WRITE = "project.write"
    ARTIFACT_READ = "artifact.read"
    ARTIFACT_WRITE = "artifact.write"
    TOOL_EXECUTE = "tool.execute"
    NETWORK_REQUEST = "network.request"
    MAIL_DRAFT = "mail.draft"
    MAIL_SEND = "mail.send"
    BUDGET_COMMIT = "budget.commit"


@dataclass(frozen=True)
class SubjectContext:
    """Server-resolved principal; never populated from model-provided role text."""

    user_id: UUID
    workspace_id: UUID
    project_id: UUID
    role_id: str
    user_actions: frozenset[AccessAction]
    project_actions: frozenset[AccessAction]
    role_capabilities: frozenset[AccessAction]
    skill_requirements: frozenset[AccessAction]
    allowed_network_hosts: frozenset[str] = frozenset()
    external_authorized: bool = False
    external_authorization_expires_at: datetime | None = None


@dataclass(frozen=True)
class PolicyRequest:
    action: AccessAction
    tool_id: str
    target: str
    parameters_digest: str
    network_host: str | None = None
    has_external_side_effect: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str
    explanation: str


class PolicyEngine:
    """Deterministic intersection of server-controlled capability sets."""

    def decide(self, subject: SubjectContext, request: PolicyRequest) -> PolicyDecision:
        intersection = (
            subject.user_actions
            & subject.project_actions
            & subject.role_capabilities
            & subject.skill_requirements
        )
        if request.action not in intersection:
            return PolicyDecision(
                allowed=False,
                reason_code="ACTION_NOT_GRANTED",
                explanation=(
                    "The requested action is outside the resolved authorization intersection"
                ),
            )
        if request.network_host:
            if AccessAction.NETWORK_REQUEST not in intersection:
                return PolicyDecision(
                    allowed=False,
                    reason_code="NETWORK_NOT_GRANTED",
                    explanation="Network permission is not in the authorization intersection",
                )
            if request.network_host not in subject.allowed_network_hosts:
                return PolicyDecision(
                    allowed=False,
                    reason_code="NETWORK_HOST_DENIED",
                    explanation="The target host is not in the server-provided allowlist",
                )
        if request.has_external_side_effect:
            if not subject.external_authorized:
                return PolicyDecision(
                    allowed=False,
                    reason_code="EXTERNAL_AUTHORIZATION_REQUIRED",
                    explanation="External side effects require an explicit unexpired authorization",
                )
            expires_at = subject.external_authorization_expires_at
            if expires_at is None or expires_at <= datetime.now(UTC):
                return PolicyDecision(
                    allowed=False,
                    reason_code="EXTERNAL_AUTHORIZATION_EXPIRED",
                    explanation="External authorization is missing or expired",
                )
        return PolicyDecision(True, "ALLOWED", "Request is within the authorization intersection")
