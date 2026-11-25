from __future__ import annotations

from pathlib import Path

from medical_one_person.agents.config import load_role_configs
from medical_one_person.infrastructure.workflows import WorkflowRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_three_workflow_packages_load_with_distinct_professional_stages() -> None:
    roles = load_role_configs(PROJECT_ROOT / "config" / "agents" / "roles.yaml")
    workflows = WorkflowRegistry.from_catalog(
        PROJECT_ROOT / "config" / "workflows" / "catalog.yaml",
        roles,
    )
    definitions = workflows.list()
    assert {item.track.value for item in definitions} == {
        "pet_repurposing",
        "ivd",
        "device",
    }
    assert len({item.workflow_id for item in definitions}) == 3
    for definition in definitions:
        assert len(definition.stages) == 4
        assert all(stage.external_preconditions for stage in definition.stages[-1:])
        assert workflows.fingerprint(definition.track)
        stage_ids = {stage.stage_id for stage in definition.stages}
        assert len(stage_ids) == 4

    pet = workflows.get(definitions[0].track)
    ivd = workflows.get(definitions[1].track)
    device = workflows.get(definitions[2].track)
    assert pet.workflow_id != ivd.workflow_id != device.workflow_id
    assert {role for stage in pet.stages for role in stage.required_roles} != {
        role for stage in ivd.stages for role in stage.required_roles
    }
