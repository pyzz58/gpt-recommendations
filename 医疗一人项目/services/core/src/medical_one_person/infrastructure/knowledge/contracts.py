from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


class KnowledgeContractValidator:
    def __init__(self, schema_path: Path) -> None:
        self._schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(self._schema)
        self._defs = self._schema["$defs"]
        for definition in self._defs.values():
            Draft202012Validator.check_schema(definition)

    def validate(self, contract: str, value: dict[str, Any]) -> None:
        if contract not in self._defs:
            raise KeyError(f"Unknown knowledge contract: {contract}")
        definition = dict(self._defs[contract])
        definition["$schema"] = self._schema["$schema"]
        definition["$defs"] = self._defs
        Draft202012Validator(definition).validate(value)

    def is_valid(self, contract: str, value: dict[str, Any]) -> bool:
        try:
            self.validate(contract, value)
            return True
        except ValidationError:
            return False
