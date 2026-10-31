from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from medical_one_person.domain.opportunities import Track


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class ReviewDecision(StrEnum):
    ACCEPTED = "accepted"
    CHANGES_REQUESTED = "changes_requested"
    DISPUTED = "disputed"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=100)
    severity: FindingSeverity
    message: str = Field(min_length=1, max_length=4_000)
    evidence_refs: list[str] = Field(default_factory=list)


class PlanNodeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    task_type: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=200)
    assignee_role: str = Field(pattern=r"^A(0[1-9]|1[0-9]|2[0-6])$")
    role_version: str = Field(min_length=1, max_length=100)
    input_version: str = Field(min_length=1, max_length=100)
    input_refs: list[str] = Field(min_length=1)
    goal: str = Field(min_length=1, max_length=4_000)
    deliverable_schema: str = Field(min_length=1, max_length=100)
    acceptance_policy: str = Field(min_length=1, max_length=100)
    mode: Literal["mock"] = "mock"
    max_attempts: int = Field(default=3, ge=1, le=10)
    depends_on: list[str] = Field(default_factory=list)


class PlanSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=300)
    objective: str = Field(min_length=1, max_length=10_000)
    nodes: list[PlanNodeSpec] = Field(min_length=1, max_length=20)
    max_rework_rounds: int = Field(default=3, ge=0, le=10)
    workflow_track: Track | None = None
    workflow_id: str | None = None
    workflow_version: int | None = Field(default=None, ge=1)
    stage_id: str | None = None

    @model_validator(mode="after")
    def validate_dag(self) -> PlanSpec:
        workflow_fields = (
            self.workflow_track,
            self.workflow_id,
            self.workflow_version,
            self.stage_id,
        )
        if any(value is None for value in workflow_fields) and not all(
            value is None for value in workflow_fields
        ):
            raise ValueError("Workflow track, id, version and stage must be set together")
        keys = [node.key for node in self.nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("Plan node keys must be unique")
        known = set(keys)
        edges: dict[str, set[str]] = {}
        for node in self.nodes:
            if len(node.depends_on) != len(set(node.depends_on)):
                raise ValueError("Plan node dependencies must be unique")
            missing = set(node.depends_on) - known
            if missing:
                raise ValueError(
                    f"Plan node {node.key} has unknown dependencies: {sorted(missing)}"
                )
            if node.key in node.depends_on:
                raise ValueError("A plan node cannot depend on itself")
            edges[node.key] = set(node.depends_on)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_key: str) -> None:
            if node_key in visiting:
                raise ValueError("Plan dependencies must not contain a cycle")
            if node_key in visited:
                return
            visiting.add(node_key)
            for dependency in edges[node_key]:
                visit(dependency)
            visiting.remove(node_key)
            visited.add(node_key)

        for node_key in edges:
            visit(node_key)
        return self
