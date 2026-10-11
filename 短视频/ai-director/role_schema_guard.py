#!/usr/bin/env python3
"""Runtime JSON Schema contract gate backed by upstream python-jsonschema.

Reuses mature MIT python-jsonschema Draft202012Validator instead of implementing
yet another JSON Schema parser. Fail CLOSED when missing. No network, no model
calls, no user text in exceptions or status. Schema supplied ONLY by trusted
role-contract code; do not permit arbitrary untrusted $ref / schemas.
"""
from __future__ import annotations



class RoleSchemaError(ValueError):
    """Private-data-safe static error codes only."""


def preflight_schema(schema):
    """Validate the model-output schema BEFORE any paid transport/reservation.

    Do not pay for a response if a required runtime library is absent or our
    own generated schema is invalid. No network, private source or key read.
    """
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError:
        raise RoleSchemaError("CREW_SCHEMA_RUNTIME_DEPENDENCY_MISSING") from None
    if not isinstance(schema, dict) or schema.get("$schema") != (
            "https://json-schema.org/draft/2020-12/schema"):
        raise RoleSchemaError("CREW_SCHEMA_UNTRUSTED_DRAFT")

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
    return {"schema_verified": True, "network_calls": 0}


def validate_contract(schema, payload):
    """Validate a parsed response, never echo the invalid private data."""
    preflight_schema(schema)
    try:
        from jsonschema import Draft202012Validator
        valid = Draft202012Validator(schema).is_valid(payload)
    except Exception:
        raise RoleSchemaError("CREW_SCHEMA_VALIDATION_UNCERTAIN") from None
    if not valid:
        raise RoleSchemaError("CREW_SCHEMA_OUTPUT_REJECTED")
    return {"contract": "draft2020-12",
            "schema_enforced": True,
            "data_sent_to_network": False,
            "private_payload_logged": False}
