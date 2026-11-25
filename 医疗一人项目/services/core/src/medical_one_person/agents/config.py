from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AcceptanceCaseConfig(BaseModel):
    kind: Literal["positive", "missing_input", "unauthorized"]
    description: str = Field(min_length=1)


class AgentRoleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role_id: str = Field(pattern=r"^A\d{2}$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1)
    reports_to: list[str] = Field(min_length=1)
    responsibilities: list[str] = Field(min_length=1)
    not_responsibilities: list[str] = Field(min_length=1)
    input_schema: str = Field(min_length=1)
    output_schema: Literal["agent_delivery.v1"]
    deliverable_types: list[str] = Field(min_length=1)
    source_policy: str = Field(min_length=1)
    skills: list[str] = Field(min_length=1)
    tools_allow: list[str] = Field(min_length=1)
    tools_deny: list[str] = Field(min_length=1)
    memory_scope: Literal["project_and_role"]
    reviewers: list[str] = Field(min_length=1)
    model_profile: str = Field(min_length=1)
    limits_profile: str = Field(min_length=1)
    theory_refs: list[str] = Field(min_length=1)
    independent_context: bool
    acceptance_cases: list[AcceptanceCaseConfig] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_permissions_and_cases(self) -> AgentRoleConfig:
        if set(self.tools_allow) & set(self.tools_deny):
            raise ValueError("Allowed and denied tools must not overlap")
        if {case.kind for case in self.acceptance_cases} != {
            "positive",
            "missing_input",
            "unauthorized",
        }:
            raise ValueError("Each role needs positive, missing_input, and unauthorized cases")
        if self.role_id in self.reports_to or self.role_id in self.reviewers:
            raise ValueError("Role cannot report to or review itself")
        return self


class AgentConfigCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    roles: list[AgentRoleConfig]


def load_role_configs(path: Path) -> dict[str, AgentRoleConfig]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = AgentConfigCatalog.model_validate(data)
    roles = {role.role_id: role for role in catalog.roles}
    expected = {f"A{index:02d}" for index in range(1, 27)}
    if set(roles) != expected:
        missing = sorted(expected - set(roles))
        extra = sorted(set(roles) - expected)
        raise ValueError(f"Agent catalog must contain A01-A26; missing={missing}, extra={extra}")
    if len(roles) != len(catalog.roles):
        raise ValueError("Duplicate role identifiers are not allowed")
    all_ids = set(roles)
    for role in roles.values():
        invalid_targets = (set(role.reports_to) | set(role.reviewers)) - all_ids
        if invalid_targets:
            raise ValueError(f"{role.role_id} references unknown roles: {sorted(invalid_targets)}")
    return roles
