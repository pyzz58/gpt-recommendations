"""Explicit HTTPS adapters for W17/W18; no SDK retries or implicit credentials.

The JSON chat wire format is deliberately limited to chat/completions. Model
pricing is operator supplied and reported as ESTIMATED, never a provider bill.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import ipaddress
import json
import os
from typing import Literal, Self
from urllib import error, request
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .archive import canonical
from .contracts import Contract, Identifier, NonBlank
from .operations import (AdapterDescriptor, AdapterReturn, CostObservation,
                         ObservationKind, OperationKind, OperationStatus,
                         ToolAdapterError, UsageObservation)


def https_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError("Adapter URLs require HTTPS, port 443 and no embedded credentials")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise ValueError("Private network destinations are not source/provider endpoints")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Private network destinations are not source/provider endpoints")
    return host


class HttpAdapterConfig(Contract):
    tool_id: Identifier
    provider_id: NonBlank
    kind: Literal["CHAT", "FETCH"]
    endpoint: NonBlank
    model: NonBlank | None = None
    api_key_env: Identifier | None = None
    timeout_seconds: int = Field(default=90, ge=1, le=600)
    max_response_bytes: int = Field(default=2_000_000, ge=1024, le=20_000_000)
    max_request_bytes: int = Field(default=2_000_000, ge=1024, le=20_000_000)
    max_output_tokens: int = Field(default=8000, ge=64, le=64000)
    input_price_per_million: Decimal | None = Field(default=None, ge=0)
    output_price_per_million: Decimal | None = Field(default=None, ge=0)
    currency: NonBlank = "USD"
    fetch_estimated_cost: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        https_url(self.endpoint)
        if self.kind == "CHAT" and (not self.model or not self.api_key_env):
            raise ValueError("CHAT needs an explicit model and credential environment name")
        if self.kind == "FETCH" and (self.model or self.api_key_env):
            raise ValueError("Public FETCH must not carry model credentials")
        if (self.input_price_per_million is None) != (self.output_price_per_million is None):
            raise ValueError("Configure both token prices or retain UNKNOWN cost")
        return self

    @property
    def sha256(self) -> str:
        return hashlib.sha256(canonical(self.model_dump(mode="json")).encode()).hexdigest()


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _send(url: str, method: str, headers: dict, body: bytes | None,
          timeout: int, limit: int) -> tuple[int, dict, bytes]:
    # No environment proxy, credential forwarding or hidden redirect/retry.
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        response = opener.open(req, timeout=timeout)
    except error.HTTPError as exc:
        with exc:
            return exc.code, dict(exc.headers.items()), b""
    with response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ToolAdapterError("Response exceeds the configured byte limit")
        return response.status, dict(response.headers.items()), data


class HttpsAdapter:
    VERSION = "1"

    def __init__(self, config: HttpAdapterConfig, *, transport=None):
        self.config = HttpAdapterConfig.model_validate_json(config.model_dump_json())
        self._transport = transport or _send

    def descriptor(self) -> AdapterDescriptor:
        return AdapterDescriptor(tool_id=self.config.tool_id, tool_version=self.VERSION,
            provider_id=self.config.provider_id, max_internal_retries=0)

    def preflight(self) -> None:
        if self.config.kind == "CHAT":
            key = os.environ.get(self.config.api_key_env, "")
            if not key or any(c in key for c in "\r\n"):
                raise ValueError("Configured model credential is absent or invalid")

    def invoke(self, operation, payload: bytes) -> AdapterReturn:
        self.preflight()
        if operation.configuration_sha256 != self.config.sha256:
            raise ValueError("Operation does not bind the actual HTTP configuration")
        if len(payload) > self.config.max_request_bytes:
            raise ValueError("Request exceeds the configured byte limit")
        data = json.loads(payload)
        headers = {"Accept": "application/json", "User-Agent": "SI-Controlled-Pilot/1"}
        if self.config.kind == "CHAT":
            if operation.kind not in (OperationKind.MODEL, OperationKind.TRANSLATE):
                raise ValueError("CHAT adapter cannot execute this operation kind")
            if (set(data) != {"model", "messages", "max_tokens"}
                    or data["model"] != self.config.model
                    or data["max_tokens"] != self.config.max_output_tokens):
                raise ValueError("Payload differs from the configured bounded chat protocol")
            if (not isinstance(data["messages"], list) or not data["messages"]
                    or any(set(m) != {"role", "content"}
                           or m["role"] not in ("system", "user")
                           or not isinstance(m["content"], str) for m in data["messages"])):
                raise ValueError("Invalid chat messages")
            headers["Authorization"] = "Bearer " + os.environ[self.config.api_key_env]
            headers["Content-Type"] = "application/json"
            method, body = "POST", payload
        else:
            if operation.kind is not OperationKind.DOWNLOAD or data != {"url": self.config.endpoint}:
                raise ValueError("FETCH must bind its exact approved URL")
            headers["Accept"] = "text/html, application/json, text/plain, application/pdf"
            method, body = "GET", None
        started = datetime.now(timezone.utc)
        try:
            status, response_headers, raw = self._transport(self.config.endpoint, method,
                headers, body, self.config.timeout_seconds, self.config.max_response_bytes)
        except Exception:
            # Never include credentials, request bodies or exception URLs in logs.
            raise ToolAdapterError("HTTP transport did not produce a confirmed response") from None
        ended = datetime.now(timezone.utc)
        if len(raw) > self.config.max_response_bytes:
            raise ToolAdapterError("Response exceeds the configured byte limit")
        lower = {k.lower(): v for k, v in response_headers.items()}
        provider_request_id = lower.get("x-request-id") or lower.get("request-id")
        usage = ()
        cost = CostObservation(kind=ObservationKind.UNKNOWN,
            basis="No provider billing amount was returned")
        if self.config.kind == "FETCH" and self.config.fetch_estimated_cost is not None:
            cost = CostObservation(kind=ObservationKind.ESTIMATED,
                amount=self.config.fetch_estimated_cost, currency=self.config.currency,
                basis="Operator-configured source request estimate; not a bill")
        if 200 <= status < 300 and self.config.kind == "CHAT":
            try:
                response = json.loads(raw)
                provider_request_id = provider_request_id or response.get("id")
                counts = response.get("usage", {})
                input_count, output_count = counts.get("prompt_tokens"), counts.get("completion_tokens")
                if (type(input_count) is int and type(output_count) is int
                        and input_count >= 0 and output_count >= 0):
                    usage = (UsageObservation(metric="input_tokens", quantity=Decimal(input_count), unit="token"),
                             UsageObservation(metric="output_tokens", quantity=Decimal(output_count), unit="token"))
                    if self.config.input_price_per_million is not None:
                        amount = (input_count * self.config.input_price_per_million
                                  + output_count * self.config.output_price_per_million) / Decimal(1_000_000)
                        cost = CostObservation(kind=ObservationKind.ESTIMATED, amount=amount,
                            currency=self.config.currency,
                            basis="Provider token counts multiplied by operator-configured rates; not a bill")
            except (ValueError, TypeError, AttributeError):
                pass
        return AdapterReturn(status=OperationStatus.SUCCEEDED if 200 <= status < 300 else OperationStatus.FAILED,
            provider_request_id=provider_request_id, response_body=raw if 200 <= status < 300 else None,
            usage=usage, cost=cost, error_code=None if 200 <= status < 300 else f"HTTP_{status}",
            error_message=None if 200 <= status < 300 else "Endpoint rejected the request; response body omitted",
            observed_internal_retries=0, started_at=started, ended_at=ended)
