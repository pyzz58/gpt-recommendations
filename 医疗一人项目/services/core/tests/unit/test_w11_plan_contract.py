from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from medical_one_person.domain.plans import PlanSpec


def _node(key: str, *, depends_on: list[str] | None = None) -> dict[str, object]:
    return {
        "key": key,
        "task_type": f"{key}.task",
        "purpose": key,
        "assignee_role": "A02",
        "role_version": "1",
        "input_version": "v1",
        "input_refs": [f"fixture:{key}"],
        "goal": f"完成{key}合成任务。",
        "deliverable_schema": "agent_delivery.v1",
        "acceptance_policy": "independent_review.v1",
        "depends_on": depends_on or [],
    }


def test_plan_contract_rejects_cycles_and_unknown_dependencies() -> None:
    cyclic = {
        "title": "循环计划",
        "objective": "验证环依赖拒绝。",
        "nodes": [
            _node("a", depends_on=["b"]),
            _node("b", depends_on=["a"]),
        ],
    }
    with pytest.raises(ValidationError, match="cycle"):
        PlanSpec.model_validate(cyclic)

    missing = {
        "title": "缺失依赖",
        "objective": "验证未知依赖拒绝。",
        "nodes": [_node("a", depends_on=["missing"])],
    }
    with pytest.raises(ValidationError, match="unknown dependencies"):
        PlanSpec.model_validate(missing)


def test_plan_contract_accepts_dependencies_declared_out_of_order() -> None:
    source = {
        "title": "乱序DAG",
        "objective": "验证拓扑排序输入。",
        "nodes": [
            _node("downstream", depends_on=["upstream"]),
            _node("upstream"),
        ],
    }
    plan = PlanSpec.model_validate(copy.deepcopy(source))
    assert [node.key for node in plan.nodes] == ["downstream", "upstream"]
