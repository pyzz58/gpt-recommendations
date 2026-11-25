from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from medical_one_person.agents.config import AgentRoleConfig, load_role_configs
from medical_one_person.agents.contracts import AgentDelivery
from medical_one_person.providers.base import StructuredGenerationRequest
from medical_one_person.providers.fake import FakeModelProvider


def _catalog_path() -> Path:
    return Path(__file__).resolve().parents[4] / "config" / "agents" / "roles.yaml"


def test_catalog_contains_all_26_complete_role_contracts() -> None:
    roles = load_role_configs(_catalog_path())

    assert set(roles) == {f"A{index:02d}" for index in range(1, 27)}
    assert all(role.output_schema == "agent_delivery.v1" for role in roles.values())
    assert all(len(role.acceptance_cases) >= 3 for role in roles.values())
    assert {role_id for role_id, role in roles.items() if role.independent_context} == {
        "A25",
        "A26",
    }


def test_role_config_rejects_tool_escalation_and_missing_cases() -> None:
    roles = load_role_configs(_catalog_path())
    data = roles["A20"].model_dump(mode="json")
    data["tools_deny"].append(data["tools_allow"][0])
    with pytest.raises(ValidationError, match="must not overlap"):
        AgentRoleConfig.model_validate(data)

    data = roles["A20"].model_dump(mode="json")
    data["acceptance_cases"] = data["acceptance_cases"][:2]
    with pytest.raises(ValidationError):
        AgentRoleConfig.model_validate(data)


def test_fake_provider_can_emit_valid_mock_delivery_for_every_role() -> None:
    roles = load_role_configs(_catalog_path())
    provider = FakeModelProvider()
    project_id = uuid4()
    task_id = uuid4()

    for role in roles.values():
        request = StructuredGenerationRequest(
            role_id=role.role_id,
            role_version=role.version,
            project_id=project_id,
            task_id=task_id,
            goal="合成岗位合同测试",
            input_refs=["fixture:w05"],
            context_sections={"synthetic": "data only"},
            system_instructions="Role contract",
            output_schema=role.output_schema,
            delivery_type=role.deliverable_types[0],
            independent_context=role.independent_context,
        )
        response = provider.generate_structured(request)
        delivery = AgentDelivery.model_validate(response.output)

        assert response.mode == "mock"
        assert delivery.role_id == role.role_id
        assert delivery.independent_review is role.independent_context
        assert delivery.limitations[0] == "MOCK mode only."
