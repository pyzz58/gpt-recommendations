from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from medical_one_person.agents.config import load_role_configs
from medical_one_person.domain.skills import SkillState
from medical_one_person.infrastructure.run_workspace import RunWorkspaceManager
from medical_one_person.infrastructure.skills.container import (
    ContainerSandboxPolicy,
    ContainerUnavailableError,
    require_container_runtime,
)
from medical_one_person.infrastructure.skills.registry import SkillRegistry


def _skill_catalog() -> Path:
    return Path(__file__).resolve().parents[4] / "config" / "skills" / "catalog.yaml"


def test_skill_registry_reports_only_implemented_skills_ready() -> None:
    registry = SkillRegistry.from_catalog(_skill_catalog())
    states = {item.definition.skill_id: item.state for item in registry.list()}

    assert states["data.numeric_summary"] == SkillState.READY
    assert states["artifact.hash"] == SkillState.READY
    assert states["literature.search"] == SkillState.DEPENDENCY_MISSING
    assert states["office.docx"] == SkillState.DEPENDENCY_MISSING
    assert states["stage.assess"] == SkillState.PLANNED
    assert sum(state == SkillState.READY for state in states.values()) == 2


def test_skill_permissions_match_professional_role_allowlists() -> None:
    root = Path(__file__).resolve().parents[4]
    roles = load_role_configs(root / "config" / "agents" / "roles.yaml")
    registry = SkillRegistry.from_catalog(_skill_catalog())

    registry.validate_against_roles(roles)


def test_container_policy_is_offline_read_only_unprivileged_and_bounded(tmp_path) -> None:
    workspace = RunWorkspaceManager(tmp_path / "runs").prepare(uuid4(), uuid4(), uuid4())
    registry = SkillRegistry.from_catalog(_skill_catalog())
    skill = registry.get("office.docx")
    assert skill.definition.runtime_image_digest is not None
    policy = ContainerSandboxPolicy(
        image_digest=skill.definition.runtime_image_digest,
        limits=skill.definition.resource_limits,
    )

    command = policy.command(workspace=workspace, argv=("python", "render.py"))
    rendered = " ".join(command)

    assert "--network none" in rendered
    assert "--read-only" in command
    assert "--cap-drop ALL" in rendered
    assert "--security-opt no-new-privileges" in rendered
    assert "--user 10001:10001" in rendered
    assert f"--pids-limit {skill.definition.resource_limits.max_processes}" in rendered
    assert f"--memory {skill.definition.resource_limits.memory_mb}m" in rendered
    assert "dst=/workspace/input,readonly" in rendered
    assert "docker.sock" not in rendered


def test_missing_container_runtime_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "medical_one_person.infrastructure.skills.container.which",
        lambda _: None,
    )
    with pytest.raises(ContainerUnavailableError, match="unavailable"):
        require_container_runtime()
