from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from medical_one_person.domain.opportunities import Track


class CriterionKind(StrEnum):
    EVIDENCE = "evidence"
    PROFESSIONAL_JUDGMENT = "professional_judgment"
    DECISION = "decision"
    REVIEW = "review"


class CriterionResultStatus(StrEnum):
    MET = "met"
    UNMET = "unmet"
    UNKNOWN = "unknown"


class AssessmentStatus(StrEnum):
    NEEDS_EVIDENCE = "needs_evidence"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"
    READY_FOR_REVIEW = "ready_for_review"


class AssessmentRecommendation(StrEnum):
    CONTINUE_TO_REVIEW = "continue_to_review"
    GATHER_EVIDENCE = "gather_evidence"
    REVISE = "revise"
    WAIT_EXTERNAL = "wait_external"
    STOP = "stop"


class WorkflowCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: CriterionKind
    description: str = Field(min_length=1)
    required: bool = True
    requires_refs: bool = True


class ExternalPrecondition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    description: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    required: bool = True
    cannot_self_confirm: Literal[True] = True


class WorkflowPlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    task_type: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    assignee_role: str = Field(pattern=r"^A(0[1-9]|1[0-9]|2[0-6])$")
    goal: str = Field(min_length=1)
    input_refs: list[str] = Field(min_length=1)
    deliverable_schema: str = "agent_delivery.v1"
    acceptance_policy: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)


class WorkflowStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    sequence: int = Field(ge=1)
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    required_roles: list[str] = Field(min_length=1)
    criteria: list[WorkflowCriterion] = Field(min_length=1)
    required_inputs: list[str] = Field(min_length=1)
    required_outputs: list[str] = Field(min_length=1)
    review_policy: str = Field(min_length=1)
    failure_routes: dict[str, str] = Field(min_length=1)
    external_preconditions: list[ExternalPrecondition]
    theory_refs: list[str] = Field(min_length=1)
    plan_nodes: list[WorkflowPlanNode] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_nodes(self) -> WorkflowStage:
        keys = [node.key for node in self.plan_nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("Workflow stage plan node keys must be unique")
        known = set(keys)
        for node in self.plan_nodes:
            missing = set(node.depends_on) - known
            if missing:
                raise ValueError(
                    f"Workflow plan node {node.key} has unknown dependencies: {sorted(missing)}"
                )
            if node.key in node.depends_on:
                raise ValueError("Workflow plan node cannot depend on itself")
        if len(self.criteria) != len({item.id for item in self.criteria}):
            raise ValueError("Workflow criterion ids must be unique")
        if len(self.external_preconditions) != len(
            {item.id for item in self.external_preconditions}
        ):
            raise ValueError("External precondition ids must be unique")
        return self


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    workflow_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    version: int = Field(ge=1)
    track: Track
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    applicability: list[str] = Field(min_length=1)
    non_goals: list[str] = Field(min_length=1)
    stages: list[WorkflowStage] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_stages(self) -> WorkflowDefinition:
        stage_ids = [stage.stage_id for stage in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("Workflow stage ids must be unique")
        if [stage.sequence for stage in self.stages] != list(range(1, len(self.stages) + 1)):
            raise ValueError("Workflow stages must be sequential from 1")
        return self


class WorkflowCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    files: list[str] = Field(min_length=3, max_length=3)


class CriterionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str = Field(min_length=1)
    status: CriterionResultStatus
    rationale: str = Field(min_length=1, max_length=10_000)
    evidence_refs: list[str] = Field(default_factory=list)


class StageDecisionStatus(StrEnum):
    ACCEPTED = "accepted"
    CHANGES_REQUESTED = "changes_requested"
    BLOCKED = "blocked"
