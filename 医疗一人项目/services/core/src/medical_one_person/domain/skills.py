from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillState(StrEnum):
    PLANNED = "planned"
    INSTALLED = "installed"
    DEPENDENCY_MISSING = "dependency_missing"
    UNCONFIGURED = "unconfigured"
    READY = "ready"
    DISABLED = "disabled"
    FAILED_VALIDATION = "failed_validation"


class ResourceLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_count: float = Field(gt=0, le=8)
    memory_mb: int = Field(ge=64, le=32768)
    timeout_seconds: int = Field(ge=1, le=3600)
    max_input_bytes: int = Field(ge=1, le=100 * 1024 * 1024)
    max_output_bytes: int = Field(ge=1, le=100 * 1024 * 1024)
    max_processes: int = Field(ge=1, le=512)


class SkillDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,80}$")
    version: int = Field(ge=1)
    description: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    theory_refs: list[str] = Field(min_length=1)
    required_tools: list[str]
    source_scopes: list[str]
    secret_scopes: list[str]
    network_policy: Literal["disabled", "allowlisted"]
    allowed_network_hosts: list[str]
    runtime_kind: Literal["builtin", "container", "disabled"]
    runtime_image_digest: str | None
    resource_limits: ResourceLimits
    side_effect_class: Literal["none", "internal_write", "external"]
    license_ref: str
    validation_suite: str = Field(min_length=1)
    declared_status: SkillState
    allowed_roles: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_security_fields(self) -> SkillDefinition:
        if self.network_policy == "disabled" and self.allowed_network_hosts:
            raise ValueError("Disabled network policy cannot have allowed hosts")
        if self.runtime_kind == "container" and not self.runtime_image_digest:
            raise ValueError("Container skills require an image digest")
        if self.runtime_kind != "container" and self.runtime_image_digest:
            raise ValueError("Only container skills may declare an image digest")
        if any(not role.startswith("A") for role in self.allowed_roles):
            raise ValueError("Skill role scopes must use Axx identifiers")
        return self


class SkillCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    skills: list[SkillDefinition]
