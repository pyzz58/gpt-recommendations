from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.domain.skills import SkillCatalog, SkillDefinition, SkillState
from medical_one_person.infrastructure.skills.contracts import (
    ArtifactHashInput,
    ArtifactHashOutput,
    NumericSummaryInput,
    NumericSummaryOutput,
)


@dataclass(frozen=True)
class BuiltinExecutor:
    input_schema: str
    output_schema: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[[BaseModel], BaseModel]


@dataclass(frozen=True)
class RegisteredSkill:
    definition: SkillDefinition
    state: SkillState
    executor: BuiltinExecutor | None


class SkillRegistry:
    def __init__(self, definitions: list[SkillDefinition]) -> None:
        self._definitions = {definition.skill_id: definition for definition in definitions}
        if len(self._definitions) != len(definitions):
            raise ValueError("Duplicate skill identifiers")
        self._executors = _builtin_executors()
        self._skills: dict[str, RegisteredSkill] = {}
        for definition in definitions:
            executor = self._executors.get(definition.skill_id)
            state = _resolved_state(definition, executor)
            if definition.runtime_kind == "builtin" and executor is None:
                state = SkillState.DEPENDENCY_MISSING
            if executor is not None and (
                definition.input_schema != executor.input_schema
                or definition.output_schema != executor.output_schema
            ):
                state = SkillState.FAILED_VALIDATION
            self._skills[definition.skill_id] = RegisteredSkill(
                definition=definition,
                state=state,
                executor=executor,
            )

    @classmethod
    def from_catalog(cls, path: Path) -> SkillRegistry:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        catalog = SkillCatalog.model_validate(data)
        return cls(catalog.skills)

    def get(self, skill_id: str) -> RegisteredSkill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {skill_id}") from exc

    def list(self) -> list[RegisteredSkill]:
        return sorted(self._skills.values(), key=lambda item: item.definition.skill_id)

    def validate_against_roles(self, roles: dict[str, AgentRoleConfig]) -> None:
        for skill in self._skills.values():
            definition = skill.definition
            for role_id in definition.allowed_roles:
                role = roles.get(role_id)
                if role is None:
                    raise ValueError(f"{definition.skill_id} references unknown role {role_id}")
                missing_tools = set(definition.required_tools) - set(role.tools_allow)
                if missing_tools:
                    raise ValueError(
                        f"{definition.skill_id} requires tools absent from {role_id}: "
                        f"{sorted(missing_tools)}"
                    )


def _resolved_state(definition: SkillDefinition, executor: BuiltinExecutor | None) -> SkillState:
    if definition.declared_status in {
        SkillState.PLANNED,
        SkillState.DEPENDENCY_MISSING,
        SkillState.UNCONFIGURED,
        SkillState.DISABLED,
        SkillState.FAILED_VALIDATION,
    }:
        return definition.declared_status
    if definition.runtime_kind == "builtin" and executor is not None:
        return SkillState.READY
    if definition.runtime_kind == "container":
        return SkillState.UNCONFIGURED
    return SkillState.DEPENDENCY_MISSING


def _numeric_summary(value: BaseModel) -> BaseModel:
    data = NumericSummaryInput.model_validate(value)
    numbers = data.numbers
    return NumericSummaryOutput(
        count=len(numbers),
        sum=sum(numbers),
        mean=sum(numbers) / len(numbers),
        minimum=min(numbers),
        maximum=max(numbers),
        unit=data.unit,
        limitations=[
            "Deterministic arithmetic on caller-provided numbers only.",
            "No missing-data, study-design, or scientific-validity assessment.",
        ],
    )


def _artifact_hash(value: BaseModel) -> BaseModel:
    data = ArtifactHashInput.model_validate(value)
    content = data.content.encode("utf-8")
    return ArtifactHashOutput(
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        media_type=data.media_type,
        validation_status="schema_validated",
    )


def _builtin_executors() -> dict[str, BuiltinExecutor]:
    return {
        "data.numeric_summary": BuiltinExecutor(
            input_schema="numeric_summary.input.v1",
            output_schema="numeric_summary.output.v1",
            input_model=NumericSummaryInput,
            output_model=NumericSummaryOutput,
            handler=_numeric_summary,
        ),
        "artifact.hash": BuiltinExecutor(
            input_schema="artifact_hash.input.v1",
            output_schema="artifact_hash.output.v1",
            input_model=ArtifactHashInput,
            output_model=ArtifactHashOutput,
            handler=_artifact_hash,
        ),
    }


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
