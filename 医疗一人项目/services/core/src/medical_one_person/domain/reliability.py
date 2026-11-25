from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReliabilityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: str
    object_type: str
    object_id: str
    detail: str


class ReliabilityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tasks: int
    open_tasks: int
    jobs: int
    running_jobs: int
    expired_leases: int
    attempts: int
    agent_runs: int
    succeeded_agent_runs: int
    skill_runs: int
    tool_audits: int
    unresolved_tool_audits: int
    policy_impact_count: int
    migrated_policy_count: int
    budget_reserved: str
    budget_spent: str
    uncertain_budget_reservations: int
    outcome_unknown_mail_attempts: int
    open_audit_findings: int
    task_list_p95_ms: float


class ReliabilityEvaluationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    policy_bundle_id: str | None
    status: str
    metrics: ReliabilityMetrics
    findings: list[ReliabilityFinding]
    limitations: list[str]
    created_at: datetime


class ReliabilityProjectView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    latest: ReliabilityEvaluationView | None
    evidence: dict[str, Any]
