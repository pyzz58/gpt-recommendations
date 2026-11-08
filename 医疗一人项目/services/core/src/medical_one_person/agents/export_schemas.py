from __future__ import annotations

import json
from pathlib import Path

from medical_one_person.agents.config import AgentConfigCatalog
from medical_one_person.agents.contracts import AgentDelivery
from medical_one_person.domain.knowledge.sources import SourcePolicyCatalog
from medical_one_person.domain.skills import SkillCatalog
from medical_one_person.infrastructure.skills.contracts import (
    ArtifactHashInput,
    ArtifactHashOutput,
    NumericSummaryInput,
    NumericSummaryOutput,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[5]
    schemas = project_root / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    targets = {
        "agent-delivery.v1.schema.json": AgentDelivery.model_json_schema(),
        "agent-roles.v1.schema.json": AgentConfigCatalog.model_json_schema(),
        "skill-catalog.v1.schema.json": SkillCatalog.model_json_schema(),
        "source-policy.v1.schema.json": SourcePolicyCatalog.model_json_schema(),
        "numeric-summary.input.v1.schema.json": NumericSummaryInput.model_json_schema(),
        "numeric-summary.output.v1.schema.json": NumericSummaryOutput.model_json_schema(),
        "artifact-hash.input.v1.schema.json": ArtifactHashInput.model_json_schema(),
        "artifact-hash.output.v1.schema.json": ArtifactHashOutput.model_json_schema(),
    }
    for name, schema in targets.items():
        (schemas / name).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(schemas / name)


if __name__ == "__main__":
    main()
