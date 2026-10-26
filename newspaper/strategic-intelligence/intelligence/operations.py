"""W17 replaceable tool invocation journal and operation identity.

The adapter performs the external action and reports its own observed result.
The controller records that result, but does not authenticate credentials,
approve a call, allocate budget or judge content. W18 supplies the pre-call gate;
W31/W48 later verify semantic review and production recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
from typing import Literal, Protocol

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, Conflict, canonical
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank, ObjectKind,
                        ReferenceUse, Representation, RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)


class OperationKind(str, Enum):
    SEARCH = "SEARCH"
    DOWNLOAD = "DOWNLOAD"
    MODEL = "MODEL"
    TRANSLATE = "TRANSLATE"
    CALCULATE = "CALCULATE"
    RENDER = "RENDER"
    OTHER = "OTHER"


class OperationStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ObservationKind(str, Enum):
    ACTUAL = "ACTUAL"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class CostObservation(Contract):
    kind: ObservationKind = ObservationKind.UNKNOWN
    amount: Decimal | None = Field(default=None, ge=0)
    currency: NonBlank | None = None
    basis: NonBlank

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.kind is ObservationKind.UNKNOWN:
            if self.amount is not None or self.currency is not None:
                raise ValueError("Unknown cost cannot carry an amount or currency")
        elif self.amount is None or self.currency is None:
            raise ValueError("Observed cost needs amount and currency")
        return self


class UsageObservation(Contract):
    metric: NonBlank
    quantity: Decimal = Field(ge=0)
    unit: NonBlank


class OperationRequest(Contract):
    schema_version: int = Field(default=2, ge=1, le=2)
    operation_id: Identifier
    idempotency_key: Identifier
    run_id: Identifier
    task_version_id: Identifier
    step_id: Identifier
    spec_sha256: Digest
    kind: OperationKind
    tool_id: Identifier
    tool_version: NonBlank
    provider_id: NonBlank
    configuration_sha256: Digest
    request_sha256: Digest
    material_use: MaterialUse | None = None
    input_version_ids: tuple[Identifier, ...] = ()
    attempt_number: int = Field(default=1, ge=1)
    max_attempts: int = Field(default=1, ge=1)
    retry_of_operation_id: Identifier | None = None
    expected_previous_operation_id: Identifier | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def retry_binding(self) -> Self:
        if len(self.input_version_ids) != len(set(self.input_version_ids)):
            raise ValueError("Duplicate operation input")
        if self.attempt_number > self.max_attempts:
            raise ValueError("Operation attempt exceeds its declared limit")
        if self.attempt_number == 1:
            if self.retry_of_operation_id is not None or self.expected_previous_operation_id is not None:
                raise ValueError("First attempt cannot claim a prior operation")
        elif (self.retry_of_operation_id is None
                or self.retry_of_operation_id != self.expected_previous_operation_id):
            raise ValueError("Retry must bind the exact previous operation")
        return self


class AdapterDescriptor(Contract):
    tool_id: Identifier
    tool_version: NonBlank
    provider_id: NonBlank
    max_internal_retries: int = Field(default=0, ge=0)


class ToolResponse(Contract):
    schema_version: int = Field(default=2, ge=1, le=2)
    status: OperationStatus
    observed_status: OperationStatus | None = None
    provider_request_id: NonBlank | None = None
    result_sha256: Digest | None = None
    observed_result_sha256: Digest | None = None
    result_adopted: bool = True
    adapter_violation: NonBlank | None = None
    usage: tuple[UsageObservation, ...] = ()
    cost: CostObservation
    error_code: NonBlank | None = None
    error_message: NonBlank | None = None
    observed_internal_retries: int = Field(default=0, ge=0)
    started_at: AwareDatetime
    ended_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("Tool response ends before it starts")
        if self.result_adopted:
            if self.adapter_violation is not None:
                raise ValueError("Adopted response cannot carry an adapter violation")
            if self.status is OperationStatus.SUCCEEDED:
                if self.error_code is not None:
                    raise ValueError("Successful response cannot carry an error code")
                if self.result_sha256 is None:
                    raise ValueError("Successful response needs an actual result digest")
        else:
            if self.status is not OperationStatus.UNKNOWN:
                raise ValueError("A non-adopted adapter result must remain UNKNOWN")
            if self.observed_status is None or self.adapter_violation is None:
                raise ValueError("A non-adopted result needs observed status and violation")
            if self.result_sha256 is not None:
                raise ValueError("A non-adopted result cannot claim an adopted result digest")
        if self.status is OperationStatus.FAILED and self.result_sha256 is not None:
            raise ValueError("Failed response cannot claim a result body")
        if self.status is OperationStatus.UNKNOWN and self.result_sha256 is not None:
            raise ValueError("Unknown response cannot claim a result body")
        return self


class OperationReceipt(Contract):
    schema_version: int = Field(default=2, ge=1, le=2)
    operation_id: Identifier
    status: OperationStatus
    observed_status: OperationStatus | None = None
    provider_request_id: NonBlank | None = None
    original_provider_request_id: NonBlank | None = None
    result_sha256: Digest | None = None
    observed_result_sha256: Digest | None = None
    result_adopted: bool = True
    adapter_violation: NonBlank | None = None
    usage: tuple[UsageObservation, ...] = ()
    cost: CostObservation
    error_code: NonBlank | None = None
    error_message: NonBlank | None = None
    observed_internal_retries: int = Field(default=0, ge=0)
    evidence_refs: tuple[Identifier, ...] = ()
    started_at: AwareDatetime
    ended_at: AwareDatetime
    recorded_at: AwareDatetime
    source: ObservationSource
    reconciled_from_receipt_id: Identifier | None = None
    provider_mapping_id: Identifier | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("Operation timestamps are out of order")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("Duplicate receipt evidence")
        if self.result_adopted:
            if self.adapter_violation is not None:
                raise ValueError("Adopted receipt cannot carry an adapter violation")
            if self.status is OperationStatus.SUCCEEDED:
                if self.result_sha256 is None or self.error_code is not None:
                    raise ValueError("Successful receipt needs a result and no error code")
            elif self.result_sha256 is not None:
                raise ValueError("Non-successful receipt cannot claim a result body")
        else:
            if self.status is not OperationStatus.UNKNOWN:
                raise ValueError("A non-adopted receipt must remain UNKNOWN")
            if self.observed_status is None or self.adapter_violation is None:
                raise ValueError("A non-adopted receipt needs observed status and violation")
            if self.result_sha256 is not None:
                raise ValueError("A non-adopted receipt cannot claim an adopted result digest")
        return self


class ObservationSource(str, Enum):
    ADAPTER = "ADAPTER"
    PROVIDER_RECONCILIATION = "PROVIDER_RECONCILIATION"


class ProviderRequestMapping(Contract):
    schema_version: Literal[1] = 1
    mapping_id: Identifier
    operation_id: Identifier
    expected_receipt_version_id: Identifier
    original_provider_request_id: NonBlank
    query_provider_request_id: NonBlank
    evidence_version_ids: tuple[Identifier, ...]
    reason: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.original_provider_request_id == self.query_provider_request_id:
            raise ValueError("A provider request mapping must change the query identity")
        if not self.evidence_version_ids:
            raise ValueError("Provider request mapping needs query evidence")
        if len(self.evidence_version_ids) != len(set(self.evidence_version_ids)):
            raise ValueError("Duplicate provider mapping evidence")
        return self


@dataclass(frozen=True)
class AdapterReturn:
    status: OperationStatus
    provider_request_id: str | None
    response_body: bytes | None
    usage: tuple[UsageObservation, ...]
    cost: CostObservation
    error_code: str | None
    error_message: str | None
    observed_internal_retries: int
    started_at: datetime
    ended_at: datetime


class OperationAdapter(Protocol):
    def descriptor(self) -> AdapterDescriptor: ...

    def invoke(self, operation: OperationRequest, payload: bytes) -> AdapterReturn: ...


class ToolAdapterError(Exception):
    """Adapter exception with an optional provider-side identity."""

    def __init__(self, message: str, *, provider_request_id: str | None = None,
                 outcome_unknown: bool = True):
        super().__init__(message)
        self.provider_request_id = provider_request_id
        self.outcome_unknown = outcome_unknown


class OperationError(ArchiveError):
    """A local operation identity/journal failure."""


@dataclass(frozen=True)
class OperationRun:
    request: StoredVersion
    receipt: StoredVersion
    response_body: bytes | None


@dataclass(frozen=True)
class OperationSummary:
    idempotency_key: str
    operation_ids: tuple[str, ...]
    statuses: tuple[OperationStatus, ...]
    actual_cost_by_currency: dict[str, Decimal]
    estimated_cost_by_currency: dict[str, Decimal]
    unknown_cost_attempts: int
    elapsed_seconds: Decimal


class OperationJournal:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("OperationJournal requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("OperationJournal requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _operation_object(key: str) -> str:
        return f"OP-{key}"

    @staticmethod
    def _receipt_object(operation_id: str) -> str:
        return f"RECEIPT-{operation_id}"

    def _load_receipt_record(
            self, operation_id: str) -> tuple[StoredVersion, OperationReceipt] | None:
        stored = self.archive.latest(self._receipt_object(operation_id))
        if stored is None:
            return None
        if stored.submission.kind is not ObjectKind.OPERATION_RECEIPT:
            raise OperationError("Operation receipt has the wrong object kind")
        receipt = OperationReceipt.model_validate_json(self.archive.read_body(stored.submission.version_id))
        if receipt.operation_id != operation_id:
            raise OperationError("Operation receipt identity mismatch")
        return stored, receipt

    def _load_receipt(self, operation_id: str) -> OperationReceipt | None:
        record = self._load_receipt_record(operation_id)
        return None if record is None else record[1]

    def _query_evidence(self, operation_id: str,
                        evidence_version_ids: tuple[str, ...]) -> None:
        if not evidence_version_ids or len(evidence_version_ids) != len(set(evidence_version_ids)):
            raise OperationError("Reconciliation needs at least one unique evidence version")
        for version_id in evidence_version_ids:
            stored = self.archive.get(version_id)
            if stored.submission.kind is not ObjectKind.EVIDENCE:
                raise OperationError("Reconciliation evidence must be an Evidence version")
            if stored.body_retention_revoked:
                raise OperationError("Reconciliation evidence was withdrawn")
            if not any(
                    item.target_version_id == operation_id
                    and item.use is ReferenceUse.REVIEW_OF
                    for item in stored.submission.references):
                raise OperationError(
                    "Reconciliation evidence does not reference the exact operation")

    def append_provider_mapping(
            self, mapping: ProviderRequestMapping) -> StoredVersion:
        if not isinstance(mapping, ProviderRequestMapping):
            raise TypeError("append_provider_mapping requires ProviderRequestMapping")
        mapping = ProviderRequestMapping.model_validate_json(
            mapping.model_dump_json(warnings=False))
        record = self._load_receipt_record(mapping.operation_id)
        if record is None:
            raise OperationError("Provider mapping has no original receipt")
        stored, receipt = record
        if stored.submission.version_id != mapping.expected_receipt_version_id:
            raise Conflict("Provider mapping targets a stale UNKNOWN receipt")
        if receipt.status is not OperationStatus.UNKNOWN:
            raise OperationError("Provider mapping requires a current UNKNOWN receipt")
        if receipt.provider_request_id != mapping.original_provider_request_id:
            raise OperationError("Provider mapping changes the original provider request ID")
        self._query_evidence(mapping.operation_id, mapping.evidence_version_ids)
        operation = self.archive.get(mapping.operation_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise OperationError("Provider mapping target is not an operation request")
        references = [
            VersionReference(target_version_id=mapping.operation_id,
                             use=ReferenceUse.REVIEW_OF, locator="exact operation attempt"),
            VersionReference(target_version_id=stored.submission.version_id,
                             use=ReferenceUse.BASIS, locator="expected UNKNOWN receipt"),
            *(
                VersionReference(target_version_id=version_id,
                                 use=ReferenceUse.SUPPORT,
                                 locator=f"mapping evidence {index}")
                for index, version_id in enumerate(mapping.evidence_version_ids)
            ),
        ]
        submission = VersionSubmission(
            schema_version=2, object_id=f"PROVIDER-MAP-{mapping.mapping_id}",
            kind=ObjectKind.PROVIDER_REQUEST_MAPPING, version_id=mapping.mapping_id,
            title=f"provider request mapping {mapping.operation_id}",
            spec_sha256=operation.submission.spec_sha256, created_at=mapping.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        return self.archive.append(
            submission, canonical(mapping.model_dump(mode="json")).encode())

    def load_provider_mapping(self, mapping_id: str) -> ProviderRequestMapping:
        stored = self.archive.get(mapping_id)
        if stored.submission.kind is not ObjectKind.PROVIDER_REQUEST_MAPPING:
            raise OperationError("Requested version is not a provider request mapping")
        mapping = ProviderRequestMapping.model_validate_json(
            self.archive.read_body(mapping_id))
        if mapping.mapping_id != mapping_id:
            raise OperationError("Provider request mapping identity mismatch")
        return mapping

    def begin(self, request: OperationRequest) -> StoredVersion:
        if not isinstance(request, OperationRequest):
            raise TypeError("begin requires an OperationRequest")
        request = OperationRequest.model_validate_json(request.model_dump_json(warnings=False))
        self.archive.get(request.task_version_id)
        for version_id in request.input_version_ids:
            self.archive.get(version_id)
        latest = self.archive.latest(self._operation_object(request.idempotency_key))
        if latest is None:
            if request.attempt_number != 1:
                raise OperationError("A first logical operation must start at attempt 1")
        else:
            previous_id = latest.submission.version_id
            if request.expected_previous_operation_id != previous_id:
                raise OperationError("Retry does not bind the current previous operation")
            previous_receipt = self._load_receipt(previous_id)
            if previous_receipt is None:
                raise OperationError("Previous operation has no confirmed receipt")
            if previous_receipt.status is OperationStatus.UNKNOWN:
                raise OperationError("Unknown prior outcome must be reconciled before retry")
            if previous_receipt.status is not OperationStatus.FAILED:
                raise OperationError("Only a failed operation can be retried")
            previous_request = OperationRequest.model_validate_json(
                self.archive.read_body(previous_id))
            if (previous_request.kind is not request.kind
                    or previous_request.task_version_id != request.task_version_id
                    or previous_request.step_id != request.step_id
                    or previous_request.spec_sha256 != request.spec_sha256
                    or previous_request.tool_id != request.tool_id
                    or previous_request.tool_version != request.tool_version
                    or previous_request.provider_id != request.provider_id
                    or previous_request.configuration_sha256 != request.configuration_sha256
                    or previous_request.request_sha256 != request.request_sha256
                    or previous_request.max_attempts != request.max_attempts):
                raise OperationError("Retry changed the logical operation or its declared limit")
            if previous_request.attempt_number + 1 != request.attempt_number:
                raise OperationError("Retry attempt number is not consecutive")
        references = (
            VersionReference(target_version_id=request.task_version_id,
                             use=ReferenceUse.BASIS, locator="operation task"),
            *(
                VersionReference(target_version_id=version_id, use=ReferenceUse.SUPPORT,
                                 locator=f"operation input {index}")
                for index, version_id in enumerate(request.input_version_ids)
            ),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=self._operation_object(request.idempotency_key),
            kind=ObjectKind.OPERATION_REQUEST, version_id=request.operation_id,
            parent_version_id=latest.submission.version_id if latest else None,
            title=f"{request.kind.value} operation {request.step_id}",
            spec_sha256=request.spec_sha256, created_at=request.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=references)
        return self.archive.append(submission, canonical(request.model_dump(mode="json")).encode())

    def record_receipt(self, response: ToolResponse, *, operation_id: str,
                       recorded_at: datetime) -> StoredVersion:
        if not isinstance(response, ToolResponse):
            raise TypeError("record_receipt requires a ToolResponse")
        response = ToolResponse.model_validate_json(response.model_dump_json(warnings=False))
        operation = self.archive.get(operation_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise OperationError("Receipt target is not an operation request")
        if self._load_receipt(operation_id) is not None:
            raise Conflict("Operation already has a receipt; reconcile instead of overwriting")
        receipt = OperationReceipt(
            operation_id=operation_id, status=response.status,
            observed_status=response.observed_status,
            provider_request_id=response.provider_request_id,
            original_provider_request_id=response.provider_request_id,
            result_sha256=response.result_sha256, usage=response.usage, cost=response.cost,
            observed_result_sha256=response.observed_result_sha256,
            result_adopted=response.result_adopted,
            adapter_violation=response.adapter_violation,
            error_code=response.error_code, error_message=response.error_message,
            observed_internal_retries=response.observed_internal_retries,
            evidence_refs=(),
            started_at=response.started_at, ended_at=response.ended_at,
            recorded_at=recorded_at, source=ObservationSource.ADAPTER)
        submission = VersionSubmission(
            schema_version=2, object_id=self._receipt_object(operation_id),
            kind=ObjectKind.OPERATION_RECEIPT, version_id=f"RESULT-{operation_id}",
            title=f"operation receipt {operation_id}", spec_sha256=operation.submission.spec_sha256,
            created_at=recorded_at, source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(VersionReference(target_version_id=operation_id,
                                          use=ReferenceUse.REVIEW_OF,
                                          locator="exact operation attempt"),))
        return self.archive.append(
            submission, canonical(receipt.model_dump(mode="json")).encode(),
            expected_current={self._receipt_object(operation_id): None})

    def receipt(self, operation_id: str) -> OperationReceipt | None:
        return self._load_receipt(operation_id)

    def summary(self, idempotency_key: str) -> OperationSummary:
        history = self.archive.history(self._operation_object(idempotency_key))
        requests = tuple(OperationRequest.model_validate_json(
            self.archive.read_body(item.submission.version_id)) for item in history)
        receipts = []
        for request in requests:
            receipt = self._load_receipt(request.operation_id)
            if receipt is None:
                raise OperationError("Logical operation contains an attempt without receipt")
            receipts.append(receipt)
        actual: dict[str, Decimal] = {}
        estimated: dict[str, Decimal] = {}
        unknown = 0
        elapsed = Decimal("0")
        for receipt in receipts:
            elapsed += Decimal(str((receipt.ended_at-receipt.started_at).total_seconds()))
            if receipt.cost.kind is ObservationKind.UNKNOWN:
                unknown += 1
            elif receipt.cost.amount is not None and receipt.cost.currency is not None:
                target = actual if receipt.cost.kind is ObservationKind.ACTUAL else estimated
                currency = receipt.cost.currency.upper()
                target[currency] = target.get(currency, Decimal("0")) + receipt.cost.amount
        return OperationSummary(
            idempotency_key=idempotency_key,
            operation_ids=tuple(request.operation_id for request in requests),
            statuses=tuple(receipt.status for receipt in receipts),
            actual_cost_by_currency=actual, estimated_cost_by_currency=estimated,
            unknown_cost_attempts=unknown, elapsed_seconds=elapsed)

    def reconcile_unknown(self, operation_id: str, response: ToolResponse, *,
                          reconciliation_id: Identifier,
                          evidence_version_ids: tuple[Identifier, ...],
                          recorded_at: datetime,
                          provider_mapping_id: Identifier | None = None) -> StoredVersion:
        """Append provider-query evidence resolving or preserving an UNKNOWN result."""
        if not isinstance(response, ToolResponse):
            raise TypeError("reconcile_unknown requires a ToolResponse")
        response = ToolResponse.model_validate_json(
            response.model_dump_json(warnings=False))
        record = self._load_receipt_record(operation_id)
        if record is None:
            raise OperationError("Only an UNKNOWN operation can be reconciled")
        previous_stored, previous = record
        if previous is None or previous.status is not OperationStatus.UNKNOWN:
            raise OperationError("Only an UNKNOWN operation can be reconciled")
        if not previous.provider_request_id:
            raise OperationError("UNKNOWN receipt has no known original provider request ID")
        if not response.provider_request_id:
            raise OperationError("Reconciliation response has no provider request ID")
        self._query_evidence(operation_id, evidence_version_ids)
        operation = self.archive.get(operation_id)
        mapping = None
        if response.provider_request_id == previous.provider_request_id:
            if provider_mapping_id is not None:
                raise OperationError("A mapping is not needed when provider request IDs match")
        else:
            if provider_mapping_id is None:
                raise OperationError("Different provider request IDs need an explicit checked mapping")
            mapping = self.load_provider_mapping(provider_mapping_id)
            if (mapping.operation_id != operation_id
                    or mapping.expected_receipt_version_id
                    != previous_stored.submission.version_id
                    or mapping.original_provider_request_id
                    != previous.provider_request_id
                    or mapping.query_provider_request_id
                    != response.provider_request_id):
                raise OperationError("Provider request mapping does not bind this reconciliation")
            if not set(mapping.evidence_version_ids) <= set(evidence_version_ids):
                raise OperationError("Reconciliation must carry the mapping's query evidence")
        receipt = OperationReceipt(
            operation_id=operation_id, status=response.status,
            observed_status=response.observed_status,
            provider_request_id=response.provider_request_id,
            original_provider_request_id=previous.provider_request_id,
            result_sha256=response.result_sha256, usage=response.usage, cost=response.cost,
            observed_result_sha256=response.observed_result_sha256,
            result_adopted=response.result_adopted,
            adapter_violation=response.adapter_violation,
            error_code=response.error_code, error_message=response.error_message,
            observed_internal_retries=response.observed_internal_retries,
            evidence_refs=evidence_version_ids, started_at=response.started_at,
            ended_at=response.ended_at, recorded_at=recorded_at,
            source=ObservationSource.PROVIDER_RECONCILIATION,
            reconciled_from_receipt_id=previous_stored.submission.version_id,
            provider_mapping_id=provider_mapping_id)
        references = [
            VersionReference(target_version_id=operation_id, use=ReferenceUse.REVIEW_OF,
                             locator="exact operation attempt"),
            *(VersionReference(target_version_id=version_id, use=ReferenceUse.SUPPORT,
                               locator=f"reconciliation evidence {index}")
              for index, version_id in enumerate(evidence_version_ids)),
        ]
        if provider_mapping_id is not None:
            references.append(VersionReference(
                target_version_id=provider_mapping_id,
                use=ReferenceUse.SUPPORT, locator="checked provider request mapping"))
        submission = VersionSubmission(
            schema_version=2, object_id=self._receipt_object(operation_id),
            kind=ObjectKind.OPERATION_RECEIPT, version_id=reconciliation_id,
            parent_version_id=previous_stored.submission.version_id,
            title=f"operation reconciliation {operation_id}",
            spec_sha256=operation.submission.spec_sha256, created_at=recorded_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        return self.archive.append(
            submission, canonical(receipt.model_dump(mode="json")).encode(),
            expected_current={
                self._receipt_object(operation_id):
                    previous_stored.submission.version_id,
            })

    def _execute_adapter(self, request: OperationRequest, adapter: OperationAdapter,
                         payload: bytes) -> OperationRun:
        """Low-level adapter execution; production callers use PreCallGate."""
        if not isinstance(payload, bytes):
            raise TypeError("Tool payload must be exact bytes")
        if hashlib.sha256(payload).hexdigest() != request.request_sha256:
            raise OperationError("Payload does not match the declared request digest")
        descriptor = adapter.descriptor()
        if (descriptor.tool_id != request.tool_id
                or descriptor.tool_version != request.tool_version
                or descriptor.provider_id != request.provider_id):
            raise OperationError("Adapter identity differs from the operation request")
        stored_request = self.begin(request)
        started_fallback = datetime.now(timezone.utc)
        try:
            returned = adapter.invoke(request, payload)
            if not isinstance(returned, AdapterReturn):
                raise OperationError("Adapter returned no typed invocation record")
            violations = []
            if returned.observed_internal_retries > descriptor.max_internal_retries:
                violations.append("Adapter exceeded its declared internal retry limit")
            if returned.status is OperationStatus.SUCCEEDED:
                if returned.response_body is None:
                    violations.append("Successful adapter return is missing exact response bytes")
                if returned.error_code is not None:
                    violations.append("Successful adapter return carries an error code")
            else:
                if returned.response_body is not None:
                    violations.append("Failed or unknown adapter return carries a result body")
            observed_result_sha256 = (
                hashlib.sha256(returned.response_body).hexdigest()
                if returned.response_body is not None else None)
            if violations:
                response = ToolResponse(
                    status=OperationStatus.UNKNOWN,
                    observed_status=returned.status,
                    provider_request_id=returned.provider_request_id,
                    result_sha256=None,
                    observed_result_sha256=observed_result_sha256,
                    result_adopted=False,
                    adapter_violation="; ".join(violations),
                    usage=returned.usage,
                    cost=returned.cost,
                    error_code=returned.error_code,
                    error_message=returned.error_message,
                    observed_internal_retries=returned.observed_internal_retries,
                    started_at=returned.started_at,
                    ended_at=returned.ended_at)
                response_body = None
            else:
                result_sha256 = (
                    hashlib.sha256(returned.response_body).hexdigest()
                    if returned.status is OperationStatus.SUCCEEDED else None)
                response = ToolResponse(
                    status=returned.status,
                    observed_status=returned.status,
                    provider_request_id=returned.provider_request_id,
                    result_sha256=result_sha256,
                    observed_result_sha256=observed_result_sha256,
                    result_adopted=True,
                    usage=returned.usage,
                    cost=returned.cost,
                    error_code=returned.error_code,
                    error_message=returned.error_message,
                    observed_internal_retries=returned.observed_internal_retries,
                    started_at=returned.started_at,
                    ended_at=returned.ended_at)
                response_body = returned.response_body
        except Exception as exc:
            now = datetime.now(timezone.utc)
            provider_request_id = getattr(exc, "provider_request_id", None)
            outcome_unknown = getattr(exc, "outcome_unknown", True)
            response = ToolResponse(status=OperationStatus.UNKNOWN if outcome_unknown else OperationStatus.FAILED,
                provider_request_id=provider_request_id,
                cost=CostObservation(kind=ObservationKind.UNKNOWN,
                                     basis="Adapter exception did not return a billable usage record"),
                error_code=type(exc).__name__, error_message=str(exc),
                started_at=started_fallback, ended_at=now)
            response_body = None
        stored_receipt = self.record_receipt(response, operation_id=request.operation_id,
                                             recorded_at=datetime.now(timezone.utc))
        return OperationRun(request=stored_request, receipt=stored_receipt,
                            response_body=response_body)
