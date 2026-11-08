from __future__ import annotations

from pathlib import Path

import yaml

from medical_one_person.domain.knowledge import SourcePolicy
from medical_one_person.domain.knowledge.sources import SourcePolicyCatalog


def load_source_policies(path: Path) -> dict[str, SourcePolicy]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = SourcePolicyCatalog.model_validate(data)
    policies = {policy.policy_id: policy for policy in catalog.policies}
    if len(policies) != len(catalog.policies):
        raise ValueError("Duplicate source policy identifiers")
    return policies
