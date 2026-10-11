#!/usr/bin/env python3
"""Runtime JSON Schema contract gate backed by upstream python-jsonschema.

Reuses mature MIT python-jsonschema Draft202012Validator instead of implementing
yet another JSON Schema parser. Fail CLOSED when missing. No network, no model
calls, no user text in exceptions or status. Schema supplied ONLY by trusted
role-contract code; do not permit arbitrary untrusted $ref / schemas.
"""
from __future__ import annotations

import json


class RoleSchemaError(ValueError):
    """Private-data-safe static error codes only."""


def validate_contract(schema, payload):
    """Validate exactly one trusted, local 2020-12 schema against parsed JSON.

    Schema validity is checked because bespoke program-generated schemas can
    contain accidental contradictions. ValidationErrors often quote user
    secrets/text: NEVER expose exception repr, .message, .path, or raw value.
    """
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError:
        raise RoleSchemaError("CREW_SCHEMA_RUNTIME_DEPENDENCY_MISSING") from None
    if not isinstance(schema, dict) or schema.get("$schema") != (
            "https://json-schema.org/draft/2020-12/schema"):
        raise RoleSchemaError("CREW_SCHEMA_UNTRUSTED_DRAFT")
    # Deny schema-level remote references even when the upstream library
    # supports resolution. All production contracts are local and bounded.
    def references_external(value):
        if isinstance(value, dict):
            if any(k in value for k in ("$ref", "$dynamicRef", "$recursiveRef")):
                return True
            return any(references_external(v) for v in value.values())
        if isinstance(value, list):
            return any(references_external(v) for v in value)
        return False
    if references_external(schema):
        raise RoleSchemaError("CREW_SCHEMA_REFERENCES_NOT_ALLOWED")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        raise RoleSchemaError("CREW_SCHEMA_CONTRACT_INVALID") from None
    # Do not stringify or serialize the payload for validation: it may
    # contain protected scripts, personal references and large model answers.
    try:
        valid = Draft202012Validator(schema).is_valid(payload)
    except Exception:
        raise RoleSchemaError("CREW_SCHEMA_VALIDATION_UNCERTAIN") from None
    if not valid:
        raise RoleSchemaError("CREW_SCHEMA_OUTPUT_REJECTED")
    return {"contract":"draft2020-12",
            "schema_enforced":True,
            "data_sent_to_network":False,
            "private_payload_logged":False}
