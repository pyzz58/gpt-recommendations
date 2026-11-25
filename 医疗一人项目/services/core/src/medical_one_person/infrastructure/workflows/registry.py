from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.domain.opportunities import Track
from medical_one_person.domain.workflows import WorkflowCatalog, WorkflowDefinition


class WorkflowRegistry:
    def __init__(
        self,
        definitions: dict[Track, WorkflowDefinition],
        fingerprints: dict[Track, str],
    ) -> None:
        self._definitions = definitions
        self._fingerprints = fingerprints

    @classmethod
    def from_catalog(
        cls,
        catalog_path: Path,
        roles: dict[str, AgentRoleConfig],
    ) -> WorkflowRegistry:
        root = catalog_path.resolve().parent
        catalog = WorkflowCatalog.model_validate(
            yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        )
        definitions: dict[Track, WorkflowDefinition] = {}
        fingerprints: dict[Track, str] = {}
        for file_name in catalog.files:
            path = (root / file_name).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Workflow config escapes catalog directory")
            raw = path.read_bytes()
            definition = WorkflowDefinition.model_validate(yaml.safe_load(raw.decode("utf-8")))
            if definition.track in definitions:
                raise ValueError(f"Duplicate workflow track: {definition.track.value}")
            for stage in definition.stages:
                unknown_roles = set(stage.required_roles) - roles.keys()
                unknown_node_roles = {
                    node.assignee_role for node in stage.plan_nodes
                } - roles.keys()
                if unknown_roles or unknown_node_roles:
                    raise ValueError(
                        f"Workflow {definition.workflow_id} references unknown roles: "
                        f"{sorted(unknown_roles | unknown_node_roles)}"
                    )
            definitions[definition.track] = definition
            fingerprints[definition.track] = hashlib.sha256(raw).hexdigest()
        expected = set(Track)
        if set(definitions) != expected:
            raise ValueError(
                f"Workflow catalog must cover {sorted(item.value for item in expected)}"
            )
        return cls(definitions, fingerprints)

    def list(self) -> list[WorkflowDefinition]:
        return [
            self._definitions[track] for track in (Track.PET_REPURPOSING, Track.IVD, Track.DEVICE)
        ]

    def get(self, track: Track) -> WorkflowDefinition:
        return self._definitions[track]

    def fingerprint(self, track: Track) -> str:
        return self._fingerprints[track]
