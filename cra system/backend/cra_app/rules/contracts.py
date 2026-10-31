"""Provider-neutral rule tree and confirmation contracts."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ConditionOperator = Literal[
    "all",
    "any",
    "not",
    "present",
    "eq",
    "ne",
    "gt",
    "ge",
    "lt",
    "le",
    "in",
    "date_interval",
]
SemanticStatus = Literal["complete", "analysis_required"]
ExtractionCoverageStatus = Literal[
    "processed",
    "background",
    "analysis_required",
    "unsupported",
    "failed",
]
RelationType = Literal[
    "unchanged",
    "new",
    "supplement",
    "exception",
    "replaces",
    "withdraws",
    "restores",
    "conflict",
]


class RuleContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleOperand(RuleContract):
    kind: Literal["literal", "fact_ref"]
    value: str | int | Decimal | bool | None = None
    fact_key: str | None = Field(default=None, min_length=1, max_length=128)
    unit: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_kind(self) -> "RuleOperand":
        if self.kind == "literal" and self.fact_key is not None:
            raise ValueError("literal operands cannot contain fact_key")
        if self.kind == "fact_ref":
            if not self.fact_key:
                raise ValueError("fact_ref operands require fact_key")
            if self.value is not None:
                raise ValueError("fact_ref operands cannot contain a literal value")
        return self


class RuleCondition(RuleContract):
    op: ConditionOperator
    children: list["RuleCondition"] = Field(default_factory=list)
    child: "RuleCondition | None" = None
    left: RuleOperand | None = None
    right: RuleOperand | None = None
    values: list[RuleOperand] = Field(default_factory=list)
    fact_key: str | None = Field(default=None, min_length=1, max_length=128)
    anchor_fact_key: str | None = Field(
        default=None, min_length=1, max_length=128
    )
    min_days: int | None = None
    max_days: int | None = None
    inclusive: bool = True

    @model_validator(mode="after")
    def validate_shape(self) -> "RuleCondition":
        if self.op in {"all", "any"}:
            if len(self.children) < 2:
                raise ValueError(f"{self.op} requires at least two children")
        elif self.children:
            raise ValueError(f"{self.op} cannot contain children")
        if self.op == "not" and self.child is None:
            raise ValueError("not requires child")
        if self.op != "not" and self.child is not None:
            raise ValueError("only not may contain child")
        if self.op == "present" and not self.fact_key:
            raise ValueError("present requires fact_key")
        if self.op in {"eq", "ne", "gt", "ge", "lt", "le"}:
            if self.left is None or self.right is None:
                raise ValueError(f"{self.op} requires left and right operands")
        elif self.op != "in" and (
            self.left is not None or self.right is not None
        ):
            raise ValueError(f"{self.op} cannot contain comparison operands")
        if self.op == "in":
            if self.left is None or not self.values:
                raise ValueError("in requires left and at least one candidate")
            if self.right is not None:
                raise ValueError("in cannot contain a right operand")
        elif self.values:
            raise ValueError(f"{self.op} cannot contain candidate values")
        if self.op == "date_interval":
            if not self.fact_key or not self.anchor_fact_key:
                raise ValueError(
                    "date_interval requires fact_key and anchor_fact_key"
                )
            if self.min_days is None or self.max_days is None:
                raise ValueError("date_interval requires min_days and max_days")
            if self.min_days > self.max_days:
                raise ValueError("date_interval lower bound exceeds upper bound")
        elif self.anchor_fact_key is not None or any(
            value is not None for value in (self.min_days, self.max_days)
        ):
            raise ValueError(f"{self.op} cannot contain date interval fields")
        elif self.fact_key is not None and self.op != "present":
            raise ValueError(f"{self.op} cannot contain a present fact_key")
        return self


class RuleSourceRef(RuleContract):
    anchor_key: str = Field(min_length=1, max_length=512)
    quote: str = Field(min_length=1)
    locator: str | None = Field(default=None, max_length=512)
    anchor_id: uuid.UUID | None = None
    document_version_id: uuid.UUID | None = None


class RuleBranch(RuleContract):
    branch_key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    condition: RuleCondition
    target_node_ids: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    source_refs: list[RuleSourceRef] = Field(min_length=1)


class RuleException(RuleContract):
    exception_key: str = Field(min_length=1, max_length=96)
    description: str = Field(min_length=1)
    condition: RuleCondition | None = None
    source_refs: list[RuleSourceRef] = Field(min_length=1)


class RuleNode(RuleContract):
    node_key: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1)
    preconditions: list[RuleCondition] = Field(default_factory=list)
    trigger: RuleCondition | None = None
    branches: list[RuleBranch] = Field(default_factory=list)
    exceptions: list[RuleException] = Field(default_factory=list)
    follow_up: str | None = None
    completion: str | None = None
    required_facts: list[str] = Field(default_factory=list)
    children: list["RuleNode"] = Field(default_factory=list)
    source_refs: list[RuleSourceRef] = Field(min_length=1)
    semantic_status: SemanticStatus = "complete"
    unknowns: list[str] = Field(default_factory=list)


class ExtractionCoverage(RuleContract):
    unit_key: str = Field(min_length=1, max_length=512)
    status: ExtractionCoverageStatus
    reason: str | None = Field(default=None, max_length=500)
    anchor_key: str | None = Field(default=None, max_length=512)


class ExtractionRelation(RuleContract):
    rule_key: str = Field(min_length=1, max_length=128)
    relation_type: RelationType
    target_rule_key: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=1, max_length=500)
    source_refs: list[RuleSourceRef] = Field(default_factory=list)


class RuleExtractionResult(RuleContract):
    provider_name: str = Field(min_length=1, max_length=64)
    provider_version: str = Field(min_length=1, max_length=32)
    rules: list[RuleNode] = Field(default_factory=list)
    coverage: list[ExtractionCoverage] = Field(default_factory=list)
    relations: list[ExtractionRelation] = Field(default_factory=list)
    direct_accept: bool = False
    warnings: list[str] = Field(default_factory=list)


class ConfirmRuleCommand(RuleContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    base_version_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=500)
    operations: list["ConfirmationOperation"] = Field(min_length=1)


class ConfirmationOperation(RuleContract):
    op: Literal[
        "edit_fields",
        "add_child",
        "remove_child",
        "add_exception",
    ]
    summary: str | None = Field(default=None, min_length=1)
    preconditions: list[RuleCondition] | None = None
    trigger: RuleCondition | None = None
    has_trigger: bool | None = None
    follow_up: str | None = None
    completion: str | None = None
    required_facts: list[str] | None = None
    child: RuleNode | None = None
    child_key: str | None = Field(default=None, min_length=1, max_length=128)
    exception: RuleException | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> "ConfirmationOperation":
        if self.op == "edit_fields" and not any(
            value is not None
            for value in (
                self.summary,
                self.preconditions,
                self.triggers_requested,
                self.follow_up,
                self.completion,
                self.required_facts,
            )
        ):
            raise ValueError("edit_fields requires at least one changed field")
        if self.op == "add_child" and self.child is None:
            raise ValueError("add_child requires child")
        if self.op == "remove_child" and not self.child_key:
            raise ValueError("remove_child requires child_key")
        if self.op == "add_exception" and self.exception is None:
            raise ValueError("add_exception requires exception")
        return self

    @property
    def triggers_requested(self) -> bool:
        return self.has_trigger is True or self.trigger is not None


class FactValue(RuleContract):
    value: Any = None
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    precision: str | None = Field(default=None, max_length=32)


class EvaluationResult(RuleContract):
    result: Literal["true", "false", "unknown"]
    reasons: list[str] = Field(default_factory=list)


class BranchEvaluation(RuleContract):
    branch_key: str
    result: Literal["true", "false", "unknown"]
    actions: list[str]
    reasons: list[str] = Field(default_factory=list)


class NodeEvaluation(RuleContract):
    node_key: str
    status: Literal[
        "applicable",
        "not_applicable",
        "unknown",
        "exception",
        "analysis_required",
    ]
    preconditions: list[EvaluationResult] = Field(default_factory=list)
    trigger: EvaluationResult | None = None
    exceptions: list[EvaluationResult] = Field(default_factory=list)
    branches: list[BranchEvaluation] = Field(default_factory=list)
    selected_branch_keys: list[str] = Field(default_factory=list)
    unknown_branch_keys: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


RuleCondition.model_rebuild()
RuleNode.model_rebuild()
ConfirmRuleCommand.model_rebuild()
