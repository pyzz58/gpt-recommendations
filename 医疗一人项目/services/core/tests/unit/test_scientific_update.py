from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import ValidationError

from medical_one_person.agents.contracts import ScientificUpdate
from medical_one_person.domain.plans import PlanSpec
from medical_one_person.infrastructure.db.engine import EXPECTED_DATABASE_REVISION


def test_continuation_requires_a_plan_and_wait_retains_unknowns():
    update = {
        "consumed_run_ids": [str(uuid4())],
        "answered_questions": ["synthetic"],
        "judgment_change": "unknown",
        "remaining_unknowns": ["source missing"],
        "action": "continue",
        "rationale": "needs evidence",
    }
    with pytest.raises(ValidationError, match="needs a plan"):
        ScientificUpdate.model_validate(update)
    update["action"] = "wait"
    assert ScientificUpdate.model_validate(update).next_plan is None


def test_startup_schema_gate_matches_the_actual_migration_head():
    core_root = Path(__file__).resolve().parents[2]
    config = Config(core_root / "alembic.ini")
    config.set_main_option("script_location", str(core_root / "migrations"))
    assert ScriptDirectory.from_config(config).get_heads() == [EXPECTED_DATABASE_REVISION]


def test_host_integration_task_cannot_be_inserted_as_an_ordinary_node():
    with pytest.raises(ValidationError, match="reserved"):
        PlanSpec.model_validate(
            {
                "title": "synthetic",
                "objective": "synthetic",
                "nodes": [
                    {
                        "key": "attempt",
                        "task_type": "scientific.integration",
                        "purpose": "attempt",
                        "assignee_role": "A02",
                        "role_version": "1",
                        "input_version": "v1",
                        "input_refs": ["fixture:attempt"],
                        "goal": "synthetic",
                        "deliverable_schema": "agent_delivery.v1",
                        "acceptance_policy": "review",
                    }
                ],
            }
        )
