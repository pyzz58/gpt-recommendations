"""W18 pre-call capability, material-permission and budget gate.

All checks happen before an adapter is invoked. Budget reservations and
settlements are append-only archive events serialized by expected-current CAS.
This module does not authenticate external credentials or authorize a new paid
service; it only enforces recorded scopes and explicitly supplied synthetic or
approved quotas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .archive import Archive, ArchiveError, Conflict, canonical
from .contracts import (Contract, Digest, Identifier, MaterialUse, NonBlank, ObjectKind,
                        ReferenceUse, Representation, RightsGrant, SourceTimes,
                        StoredVersion, UseContext, VersionReference, VersionSubmission)
from .operations import (AdapterDescriptor, ObservationKind, OperationJournal, OperationKind,
                         OperationRequest, OperationRun)


class GatingError(ArchiveError):
    """A pre-call refusal or budget-account failure, never an external result."""


class AdmissionMode(str, Enum):
    APPROVED = "APPROVED"
    CONTROLLED_TRIAL = "CONTROLLED_TRIAL"


class BudgetEventKind(str, Enum):
    RESERVE = "RESERVE"
    SETTLE = "SETTLE"
    UNKNOWN = "UNKNOWN"
    RELEASE = "RELEASE"


class BudgetLine(Contract):
    metric: NonBlank
    amount: Decimal = Field(ge=0)


class BudgetEnvelope(Contract):
    schema_version: Literal[1] = 1
    budget_id: Identifier
    run_id: Identifier
    task_version_id: Identifier
    quotas: tuple[BudgetLine, ...]
    max_concurrent_reservations: int = Field(default=1, ge=1)
    valid_from: AwareDatetime
    valid_until: AwareDatetime
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.valid_until <= self.valid_from:
            raise ValueError("Budget validity must end after it begins")
        if not self.quotas:
            raise ValueError("Budget needs at least one approved quota")
        metrics = [item.metric.casefold() for item in self.quotas]
        if len(metrics) != len(set(metrics)):
            raise ValueError("Duplicate budget metric")
        return self


class CapabilityAdmission(Contract):
    schema_version: Literal[1] = 1
    admission_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    step_ids: tuple[Identifier, ...]
    provider_id: NonBlank
    tool_id: Identifier
    tool_version: NonBlank
    configuration_sha256: Digest
    operation_kinds: tuple[OperationKind, ...]
    material_uses: tuple[MaterialUse, ...]
    territory: NonBlank
    external_processing_allowed: bool
    budget_id: Identifier
    max_attempts: int = Field(ge=1)
    max_internal_retries: int = Field(ge=0)
    mode: AdmissionMode
    review_version_id: Identifier
    valid_from: AwareDatetime
    valid_until: AwareDatetime
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.valid_until <= self.valid_from:
            raise ValueError("Capability admission must end after it begins")
        groups = (
            ("step", self.step_ids),
            ("operation kind", self.operation_kinds),
            ("material use", self.material_uses),
        )
        for name, values in groups:
            if not values or len(values) != len(set(values)):
                raise ValueError(f"Capability {name} scope must be nonempty and unique")
        return self


class ReservationEstimate(Contract):
    schema_version: Literal[1] = 1
    operation_id: Identifier
    basis: ObservationKind
    lines: tuple[BudgetLine, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.basis is ObservationKind.UNKNOWN:
            raise ValueError("Unknown pre-call cost cannot reserve an unlimited amount")
        if not self.lines:
            raise ValueError("Pre-call reservation needs explicit budget lines")
        metrics = [item.metric.casefold() for item in self.lines]
        if len(metrics) != len(set(metrics)):
            raise ValueError("Duplicate reservation metric")
        return self


class BudgetEvent(Contract):
    schema_version: Literal[1] = 1
    event_id: Identifier
    budget_id: Identifier
    admission_id: Identifier
    operation_id: Identifier
    reservation_id: Identifier
    request_sha256: Digest
    kind: BudgetEventKind
    basis: ObservationKind | None = None
    lines: tuple[BudgetLine, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        metrics = [item.metric.casefold() for item in self.lines]
        if len(metrics) != len(set(metrics)):
            raise ValueError("Duplicate budget event metric")
        if self.kind is BudgetEventKind.RESERVE:
            if self.basis is ObservationKind.UNKNOWN or self.basis is None or not self.lines:
                raise ValueError("Reservation needs known/estimated lines")
        elif self.kind is BudgetEventKind.SETTLE:
            if self.basis not in (ObservationKind.ACTUAL, ObservationKind.ESTIMATED):
                raise ValueError("Known settlement needs actual or estimated basis")
            if not self.lines:
                raise ValueError("Known settlement needs actual/estimated lines")
        elif self.kind is BudgetEventKind.UNKNOWN:
            if self.basis is not ObservationKind.UNKNOWN or self.lines:
                raise ValueError("Unknown settlement has no known lines")
        elif self.basis is not None or self.lines:
            raise ValueError("A release carries no settlement lines")
        return self


@dataclass(frozen=True)
class BudgetReservation:
    budget_id: str
    admission_id: str
    operation_id: str
    reservation_id: str
    request_sha256: str
    basis: ObservationKind
    lines: tuple[BudgetLine, ...]
    event_version_id: str
    created_at: datetime


@dataclass(frozen=True)
class BudgetState:
    budget_id: str
    quotas: dict[str, Decimal]
    reserved: dict[str, Decimal]
    consumed: dict[str, Decimal]
    remaining: dict[str, Decimal]
    open_reservations: tuple[str, ...]
    unknown_reservations: tuple[str, ...]


@dataclass(frozen=True)
class GatedOperationRun:
    admission: CapabilityAdmission
    material_use: MaterialUse
    reservation: BudgetReservation
    settlement: BudgetEvent
    run: OperationRun
    manual_review_required: bool


def _digest(*values: str) -> str:
    return hashlib.sha256(canonical(list(values)).encode()).hexdigest()


class BudgetLedger:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("BudgetLedger requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("BudgetLedger requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _budget_object(budget_id: str) -> str:
        return "BUDGET-DEF-" + _digest(budget_id)[:32]

    @staticmethod
    def _budget_version(budget_id: str) -> str:
        return "BUDGET-" + _digest(budget_id)[:32]

    @staticmethod
    def _event_object(budget_id: str) -> str:
        return "BUDGET-LEDGER-" + _digest(budget_id)[:32]

    @staticmethod
    def _reservation_id(budget_id: str, operation_id: str) -> str:
        return "RES-" + _digest("reservation", budget_id, operation_id)[:32]

    @staticmethod
    def _event_id(budget_id: str, reservation_id: str, kind: BudgetEventKind) -> str:
        return "BEV-" + _digest(kind.value, budget_id, reservation_id)[:32]

    def create_budget(self, envelope: BudgetEnvelope) -> StoredVersion:
        if not isinstance(envelope, BudgetEnvelope):
            raise TypeError("create_budget requires a BudgetEnvelope")
        envelope = BudgetEnvelope.model_validate_json(
            envelope.model_dump_json(warnings=False))
        task = self.archive.get(envelope.task_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise GatingError("Budget owner is not a Task")
        submission = VersionSubmission(
            schema_version=2, object_id=self._budget_object(envelope.budget_id),
            kind=ObjectKind.BUDGET_ENVELOPE,
            version_id=self._budget_version(envelope.budget_id),
            title=f"{envelope.budget_id} approved budget",
            spec_sha256=task.submission.spec_sha256, created_at=envelope.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(VersionReference(target_version_id=envelope.task_version_id,
                use=ReferenceUse.BASIS, locator="budget task"),))
        return self.archive.append(
            submission, canonical(envelope.model_dump(mode="json")).encode())

    def load_budget(self, budget_id: str) -> BudgetEnvelope:
        stored = self.archive.get(self._budget_version(budget_id))
        if stored.submission.kind is not ObjectKind.BUDGET_ENVELOPE:
            raise GatingError("Requested version is not a budget envelope")
        envelope = BudgetEnvelope.model_validate_json(
            self.archive.read_body(self._budget_version(budget_id)))
        if envelope.budget_id != budget_id:
            raise GatingError("Budget identity mismatch")
        return envelope

    def _events(self, budget_id: str) -> tuple[StoredVersion, tuple[BudgetEvent, ...]]:
        history = self.archive.history(self._event_object(budget_id))
        events = tuple(BudgetEvent.model_validate_json(
            self.archive.read_body(item.submission.version_id)) for item in history)
        return history, events

    def state(self, budget_id: str) -> BudgetState:
        envelope = self.load_budget(budget_id)
        quotas = {item.metric.casefold(): item.amount for item in envelope.quotas}
        _, events = self._events(budget_id)
        reservations: dict[str, BudgetEvent] = {}
        unknown = set()
        consumed: dict[str, Decimal] = {}
        for event in events:
            key = event.reservation_id
            if event.kind is BudgetEventKind.RESERVE:
                reservations[key] = event
            elif event.kind in (BudgetEventKind.SETTLE, BudgetEventKind.RELEASE):
                reservations.pop(key, None)
                if event.kind is BudgetEventKind.SETTLE:
                    for line in event.lines:
                        metric = line.metric.casefold()
                        consumed[metric] = consumed.get(metric, Decimal("0")) + line.amount
            elif event.kind is BudgetEventKind.UNKNOWN:
                unknown.add(key)
        held: dict[str, Decimal] = {}
        for event in reservations.values():
            for line in event.lines:
                metric = line.metric.casefold()
                held[metric] = held.get(metric, Decimal("0")) + line.amount
        reserved = {metric: held.get(metric, Decimal("0")) for metric in quotas}
        final_consumed = {metric: consumed.get(metric, Decimal("0")) for metric in quotas}
        remaining = {
            metric: quotas[metric] - final_consumed[metric] - reserved[metric]
            for metric in quotas
        }
        return BudgetState(
            budget_id=budget_id, quotas=quotas, reserved=reserved,
            consumed=final_consumed, remaining=remaining,
            open_reservations=tuple(sorted(reservations)),
            unknown_reservations=tuple(sorted(unknown)))

    def reserve(self, budget_id: str, admission_id: str, request: OperationRequest,
                estimate: ReservationEstimate, at: datetime) -> BudgetReservation:
        if estimate.operation_id != request.operation_id:
            raise GatingError("Budget estimate targets a different operation")
        reservation_id = self._reservation_id(budget_id, request.operation_id)
        for _ in range(8):
            envelope = self.load_budget(budget_id)
            if not (envelope.valid_from <= at < envelope.valid_until):
                raise GatingError("Budget is not currently valid")
            history, events = self._events(budget_id)
            if any(item.reservation_id == reservation_id for item in events):
                raise Conflict("Operation already has a budget reservation")
            state = self.state(budget_id)
            if len(state.open_reservations) >= envelope.max_concurrent_reservations:
                raise GatingError("Budget concurrent reservation limit is already reached")
            estimate_metrics = {line.metric.casefold() for line in estimate.lines}
            if estimate_metrics != set(state.remaining):
                raise GatingError(
                    "Reservation must account for every approved budget metric")
            for line in estimate.lines:
                metric = line.metric.casefold()
                if metric not in state.remaining:
                    raise GatingError(f"Budget metric is not approved: {line.metric}")
                if line.amount > state.remaining[metric]:
                    raise GatingError(f"Insufficient approved budget for {line.metric}")
            event = BudgetEvent(
                event_id=self._event_id(
                    budget_id, reservation_id, BudgetEventKind.RESERVE),
                budget_id=budget_id, admission_id=admission_id,
                operation_id=request.operation_id, reservation_id=reservation_id,
                request_sha256=request.request_sha256,
                kind=BudgetEventKind.RESERVE, basis=estimate.basis,
                lines=estimate.lines, created_at=at)
            submission = VersionSubmission(
                schema_version=2, object_id=self._event_object(budget_id),
                kind=ObjectKind.BUDGET_EVENT, version_id=event.event_id,
                parent_version_id=(history[-1].submission.version_id if history else None),
                title=f"budget reservation {request.operation_id}",
                spec_sha256=self.archive.get(request.task_version_id).submission.spec_sha256,
                created_at=at, source_times=SourceTimes(), rights=self.rights,
                representation=Representation.FULL_BODY)
            try:
                stored = self.archive.append(
                    submission, canonical(event.model_dump(mode="json")).encode(),
                    expected_current={
                        self._event_object(budget_id):
                            history[-1].submission.version_id if history else None,
                    })
            except Conflict:
                continue
            return BudgetReservation(
                budget_id=budget_id, admission_id=admission_id,
                operation_id=request.operation_id, reservation_id=reservation_id,
                request_sha256=request.request_sha256,
                basis=estimate.basis, lines=estimate.lines,
                event_version_id=stored.submission.version_id, created_at=at)
        raise Conflict("Budget reservation changed concurrently; no external call was made")

    def _settle(self, reservation: BudgetReservation, kind: BudgetEventKind,
                basis: ObservationKind, lines: tuple[BudgetLine, ...],
                at: datetime) -> BudgetEvent:
        for _ in range(8):
            history, events = self._events(reservation.budget_id)
            reservation_events = [
                item for item in events
                if item.reservation_id == reservation.reservation_id]
            if not any(item.kind is BudgetEventKind.RESERVE for item in reservation_events):
                raise GatingError("Budget reservation does not exist")
            if any(item.kind is not BudgetEventKind.RESERVE for item in reservation_events):
                existing = next(
                    item for item in reversed(reservation_events)
                    if item.kind is not BudgetEventKind.RESERVE)
                return existing
            event = BudgetEvent(
                event_id=self._event_id(
                    reservation.budget_id, reservation.reservation_id, kind),
                budget_id=reservation.budget_id, admission_id=reservation.admission_id,
                operation_id=reservation.operation_id,
                reservation_id=reservation.reservation_id,
                request_sha256=reservation.request_sha256,
                kind=kind, basis=basis, lines=lines, created_at=at)
            submission = VersionSubmission(
                schema_version=2, object_id=self._event_object(reservation.budget_id),
                kind=ObjectKind.BUDGET_EVENT, version_id=event.event_id,
                parent_version_id=(history[-1].submission.version_id if history else None),
                title=f"budget {kind.value.lower()} {reservation.operation_id}",
                spec_sha256=self.archive.get(
                    self.load_budget(reservation.budget_id).task_version_id
                ).submission.spec_sha256,
                created_at=at, source_times=SourceTimes(), rights=self.rights,
                representation=Representation.FULL_BODY)
            try:
                self.archive.append(
                    submission, canonical(event.model_dump(mode="json")).encode(),
                    expected_current={
                        self._event_object(reservation.budget_id):
                            history[-1].submission.version_id if history else None,
                    })
            except Conflict:
                continue
            return event
        raise Conflict("Budget settlement changed concurrently")

    def settle(self, reservation: BudgetReservation, *,
               basis: ObservationKind, lines: tuple[BudgetLine, ...],
               at: datetime) -> BudgetEvent:
        if basis is ObservationKind.UNKNOWN:
            return self._settle(
                reservation, BudgetEventKind.UNKNOWN, basis, (), at)
        return self._settle(
            reservation, BudgetEventKind.SETTLE, basis, tuple(lines), at)

    def release(self, reservation: BudgetReservation, at: datetime) -> BudgetEvent:
        return self._settle(
            reservation, BudgetEventKind.RELEASE, ObservationKind.UNKNOWN, (), at)


class PreCallGate:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("PreCallGate requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("PreCallGate requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.ledger = BudgetLedger(archive, rights)
        self.journal = OperationJournal(archive, rights)

    @staticmethod
    def _admission_version(admission_id: str) -> str:
        return "ADMISSION-" + _digest(admission_id)[:32]

    def create_budget(self, envelope: BudgetEnvelope) -> StoredVersion:
        return self.ledger.create_budget(envelope)

    def load_budget(self, budget_id: str) -> BudgetEnvelope:
        return self.ledger.load_budget(budget_id)

    def append_admission(self, admission: CapabilityAdmission) -> StoredVersion:
        if not isinstance(admission, CapabilityAdmission):
            raise TypeError("append_admission requires CapabilityAdmission")
        admission = CapabilityAdmission.model_validate_json(
            admission.model_dump_json(warnings=False))
        task = self.archive.get(admission.task_version_id)
        if task.submission.kind is not ObjectKind.TASK:
            raise GatingError("Capability admission owner is not a Task")
        if task.submission.spec_sha256 != admission.spec_sha256:
            raise GatingError("Capability admission and Task use different specifications")
        budget = self.load_budget(admission.budget_id)
        if budget.task_version_id != admission.task_version_id:
            raise GatingError("Capability admission and budget bind different Tasks")
        review = self.archive.get(admission.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise GatingError("Capability admission needs an archived Review")
        if review.submission.spec_sha256 != admission.spec_sha256:
            raise GatingError("Capability Review uses a different specification")
        if review.body_retention_revoked:
            raise GatingError("Capability Review was withdrawn")
        if not any(item.target_version_id == admission.task_version_id
                   and item.use is ReferenceUse.REVIEW_OF
                   for item in review.submission.references):
            raise GatingError("Capability Review does not cover the exact Task")
        submission = VersionSubmission(
            schema_version=2,
            object_id="CAPABILITY-" + _digest(admission.admission_id)[:32],
            kind=ObjectKind.CAPABILITY_ADMISSION,
            version_id=self._admission_version(admission.admission_id),
            title=f"capability admission {admission.mode.value}",
            spec_sha256=admission.spec_sha256, created_at=admission.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=(
                VersionReference(target_version_id=admission.task_version_id,
                    use=ReferenceUse.BASIS, locator="admitted task"),
                VersionReference(target_version_id=admission.review_version_id,
                    use=ReferenceUse.REVIEW_OF, locator="capability Review"),
                VersionReference(target_version_id=self.ledger._budget_version(admission.budget_id),
                    use=ReferenceUse.BASIS, locator="approved budget"),
            ))
        return self.archive.append(
            submission, canonical(admission.model_dump(mode="json")).encode())

    def load_admission(self, admission_id: str) -> CapabilityAdmission:
        version_id = self._admission_version(admission_id)
        stored = self.archive.get(version_id)
        if stored.submission.kind is not ObjectKind.CAPABILITY_ADMISSION:
            raise GatingError("Requested version is not a capability admission")
        admission = CapabilityAdmission.model_validate_json(
            self.archive.read_body(version_id))
        if admission.admission_id != admission_id:
            raise GatingError("Capability admission identity mismatch")
        return admission

    @staticmethod
    def material_use_for(kind: OperationKind) -> MaterialUse:
        if kind is OperationKind.MODEL:
            return MaterialUse.MODEL_PROCESS
        if kind is OperationKind.TRANSLATE:
            return MaterialUse.TRANSLATE
        if kind is OperationKind.RENDER:
            return MaterialUse.PRIVATE_DELIVERY
        return MaterialUse.INDEX

    def _validate_scope(
            self, admission: CapabilityAdmission, request: OperationRequest,
            descriptor: AdapterDescriptor, now: datetime) -> MaterialUse:
        if not (admission.valid_from <= now < admission.valid_until):
            raise GatingError("Capability admission is not currently valid")
        if request.spec_sha256 != admission.spec_sha256:
            raise GatingError("Operation and capability admission use different specifications")
        if request.task_version_id != admission.task_version_id:
            raise GatingError("Capability admission does not cover the exact Task version")
        task = self.archive.get(request.task_version_id)
        if task.body_retention_revoked:
            raise GatingError("Admitted Task was withdrawn")
        latest = self.archive.latest(task.submission.object_id)
        if latest is None or latest.submission.version_id != request.task_version_id:
            raise GatingError("Capability admission targets a superseded Task version")
        budget = self.load_budget(admission.budget_id)
        if budget.task_version_id != request.task_version_id:
            raise GatingError("Budget does not cover the exact Task version")
        if budget.run_id != request.run_id:
            raise GatingError("Budget does not cover the operation run")
        review = self.archive.get(admission.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise GatingError("Capability admission Review is missing")
        if review.submission.spec_sha256 != admission.spec_sha256:
            raise GatingError("Capability admission Review uses another specification")
        if review.body_retention_revoked:
            raise GatingError("Capability admission Review was withdrawn")
        if request.step_id not in admission.step_ids:
            raise GatingError("Operation step is outside the admitted scope")
        if (request.provider_id != admission.provider_id
                or request.tool_id != admission.tool_id
                or request.tool_version != admission.tool_version
                or request.configuration_sha256 != admission.configuration_sha256):
            raise GatingError("Operation provider/tool/configuration is outside admission")
        if request.kind not in admission.operation_kinds:
            raise GatingError("Operation kind is outside the admitted scope")
        if not admission.external_processing_allowed:
            raise GatingError("Capability admission does not permit external processing")
        if request.max_attempts > admission.max_attempts:
            raise GatingError("Operation retry limit exceeds admission")
        if request.attempt_number > admission.max_attempts:
            raise GatingError("Operation attempt exceeds admission")
        if descriptor.max_internal_retries > admission.max_internal_retries:
            raise GatingError("Adapter internal retry limit exceeds admission")
        if request.kind is OperationKind.OTHER:
            if request.material_use is None:
                raise GatingError("OTHER operations need an explicit material use")
            material_use = request.material_use
        else:
            material_use = self.material_use_for(request.kind)
            if (request.material_use is not None
                    and request.material_use is not material_use):
                raise GatingError("Operation material use conflicts with its operation kind")
        if material_use not in admission.material_uses:
            raise GatingError("Operation material use is outside admission")
        return material_use

    @staticmethod
    def _settlement_lines(receipt) -> tuple[ObservationKind, tuple[BudgetLine, ...]]:
        if receipt.cost.kind is ObservationKind.UNKNOWN:
            return ObservationKind.UNKNOWN, ()
        lines = [BudgetLine(metric="calls", amount=Decimal("1"))]
        cost = receipt.cost
        if cost.amount is None or cost.currency is None:
            return ObservationKind.UNKNOWN, ()
        lines.append(BudgetLine(
            metric=f"cost:{cost.currency.upper()}", amount=cost.amount))
        usage: dict[str, Decimal] = {}
        for item in receipt.usage:
            metric = f"usage:{item.metric}:{item.unit}".casefold()
            usage[metric] = usage.get(metric, Decimal("0")) + item.quantity
        lines.extend(
            BudgetLine(metric=metric, amount=amount)
            for metric, amount in sorted(usage.items()))
        return cost.kind, tuple(lines)

    def execute(self, admission_id: str, request: OperationRequest,
                adapter, payload: bytes, estimate: ReservationEstimate) -> GatedOperationRun:
        if not isinstance(request, OperationRequest):
            raise TypeError("PreCallGate.execute requires an OperationRequest")
        request = OperationRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        if not isinstance(estimate, ReservationEstimate):
            raise TypeError("PreCallGate.execute requires a ReservationEstimate")
        estimate = ReservationEstimate.model_validate_json(
            estimate.model_dump_json(warnings=False))
        admission = self.load_admission(admission_id)
        now = datetime.now(timezone.utc)
        descriptor = adapter.descriptor()
        material_use = self._validate_scope(admission, request, descriptor, now)
        context = UseContext(
            at=now, provider=request.provider_id, territory=admission.territory)
        for version_id in request.input_version_ids:
            self.archive.check_version_use(version_id, material_use, context)
        reservation = self.ledger.reserve(
            admission.budget_id, admission.admission_id, request, estimate, now)
        try:
            run = self.journal._execute_adapter(request, adapter, payload)
        except BaseException:
            self.ledger.settle(
                reservation, basis=ObservationKind.UNKNOWN, lines=(),
                at=datetime.now(timezone.utc))
            raise
        receipt = self.journal.receipt(request.operation_id)
        if receipt is None:
            self.ledger.settle(
                reservation, basis=ObservationKind.UNKNOWN, lines=(),
                at=datetime.now(timezone.utc))
            raise GatingError("Adapter call has no persisted receipt")
        basis, lines = self._settlement_lines(receipt)
        settlement = self.ledger.settle(
            reservation, basis=basis, lines=lines,
            at=datetime.now(timezone.utc))
        return GatedOperationRun(
            admission=admission, material_use=material_use,
            reservation=reservation, settlement=settlement, run=run,
            manual_review_required=admission.mode is AdmissionMode.CONTROLLED_TRIAL)
