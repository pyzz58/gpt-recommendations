from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    BudgetExceededError,
    ConflictingOperationError,
    NotFoundError,
)
from medical_one_person.domain.budgets import (
    BudgetSnapshot,
    ReservationRecord,
    ReservationState,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Budget,
    BudgetLedgerEntry,
    BudgetReservation,
    Project,
    User,
)


class BudgetService:
    """Atomic reservation and idempotent settlement for one project budget."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        name: str,
        currency: str,
        limit_amount: Decimal,
    ) -> BudgetSnapshot:
        _validate_positive_amount(limit_amount, "Budget limit")
        normalized_currency = _currency(currency)
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            project = self._project(session, project_id, actor.workspace_id)
            budget = session.scalar(
                select(Budget).where(
                    Budget.project_id == project.id,
                    Budget.name == name,
                )
            )
            if budget is None:
                budget = Budget(
                    id=uuid4(),
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    name=name,
                    currency=normalized_currency,
                    limit_amount=limit_amount,
                    reserved_amount=Decimal("0"),
                    spent_amount=Decimal("0"),
                    revision=1,
                    created_at=datetime.now(UTC),
                )
                session.add(budget)
                session.flush()
            return _budget_snapshot(budget)

    def reserve(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        budget_id: UUID,
        amount: Decimal,
        operation_key: str,
    ) -> ReservationRecord:
        _validate_positive_amount(amount, "Reservation amount")
        if not operation_key.strip():
            raise ValueError("Reservation operation key cannot be empty")
        try:
            return self._reserve_once(
                project_id=project_id,
                actor_user_id=actor_user_id,
                budget_id=budget_id,
                amount=amount,
                operation_key=operation_key,
            )
        except IntegrityError:
            with self._session_factory.begin() as session:
                actor = self._actor(session, actor_user_id)
                self._set_context(session, actor)
                existing = session.scalar(
                    select(BudgetReservation).where(
                        BudgetReservation.budget_id == budget_id,
                        BudgetReservation.operation_key == operation_key,
                    )
                )
                if existing is None:
                    raise
                if existing.amount != amount:
                    raise ConflictingOperationError(
                        "Reservation operation key was reused with a different amount"
                    ) from None
                return _reservation_record(existing)

    def _reserve_once(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        budget_id: UUID,
        amount: Decimal,
        operation_key: str,
    ) -> ReservationRecord:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            existing = session.scalar(
                select(BudgetReservation).where(
                    BudgetReservation.budget_id == budget_id,
                    BudgetReservation.operation_key == operation_key,
                )
            )
            if existing is not None:
                if existing.amount != amount:
                    raise ConflictingOperationError(
                        "Reservation operation key was reused with a different amount"
                    )
                return _reservation_record(existing)

            budget = session.scalar(
                select(Budget)
                .where(
                    Budget.id == budget_id,
                    Budget.project_id == project_id,
                    Budget.workspace_id == actor.workspace_id,
                )
                .with_for_update()
            )
            if budget is None:
                raise NotFoundError("Budget not found")
            if budget.reserved_amount + budget.spent_amount + amount > budget.limit_amount:
                raise BudgetExceededError("Budget authorization would be exceeded")

            now = datetime.now(UTC)
            budget.reserved_amount += amount
            budget.revision += 1
            reservation = BudgetReservation(
                id=uuid4(),
                workspace_id=budget.workspace_id,
                project_id=budget.project_id,
                budget_id=budget.id,
                operation_key=operation_key,
                amount=amount,
                currency=budget.currency,
                state=ReservationState.RESERVED.value,
                created_at=now,
            )
            session.add(reservation)
            session.flush()
            session.add(
                BudgetLedgerEntry(
                    id=uuid4(),
                    workspace_id=budget.workspace_id,
                    project_id=budget.project_id,
                    budget_id=budget.id,
                    reservation_id=reservation.id,
                    ledger_key=f"reserve:{operation_key}",
                    kind="reserve",
                    reserved_delta=amount,
                    spent_delta=Decimal("0"),
                    created_at=now,
                )
            )
            session.flush()
            return _reservation_record(reservation)

    def settle(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        reservation_id: UUID,
        actual_amount: Decimal,
        ledger_key: str,
    ) -> ReservationRecord:
        if not actual_amount.is_finite() or actual_amount < 0:
            raise ValueError("Actual amount must be finite and non-negative")
        if not ledger_key.strip():
            raise ValueError("Settlement ledger key cannot be empty")
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            reservation = session.scalar(
                select(BudgetReservation)
                .where(
                    BudgetReservation.id == reservation_id,
                    BudgetReservation.project_id == project_id,
                    BudgetReservation.workspace_id == actor.workspace_id,
                )
                .with_for_update()
            )
            if reservation is None:
                raise NotFoundError("Reservation not found")
            existing_ledger = session.scalar(
                select(BudgetLedgerEntry).where(
                    BudgetLedgerEntry.project_id == project_id,
                    BudgetLedgerEntry.ledger_key == ledger_key,
                )
            )
            if existing_ledger is not None:
                if (
                    existing_ledger.kind == "settle"
                    and existing_ledger.reservation_id == reservation.id
                    and existing_ledger.spent_delta == actual_amount
                ):
                    return _reservation_record(reservation)
                raise ConflictingOperationError(
                    "Settlement ledger key conflicts with an earlier operation"
                )
            if reservation.state == ReservationState.SETTLED.value:
                raise ConflictingOperationError("Reservation was already settled")
            if reservation.state not in {
                ReservationState.RESERVED.value,
                ReservationState.UNCERTAIN.value,
            }:
                raise ConflictingOperationError(
                    "Reservation cannot be settled in its current state"
                )

            budget = session.scalar(
                select(Budget).where(Budget.id == reservation.budget_id).with_for_update()
            )
            if budget is None:
                raise NotFoundError("Budget not found")
            now = datetime.now(UTC)
            budget.reserved_amount -= reservation.amount
            if budget.reserved_amount < 0:
                raise ConflictingOperationError("Budget reservation balance is inconsistent")
            budget.spent_amount += actual_amount
            budget.revision += 1
            reservation.state = ReservationState.SETTLED.value
            reservation.settled_at = now
            session.add(
                BudgetLedgerEntry(
                    id=uuid4(),
                    workspace_id=budget.workspace_id,
                    project_id=budget.project_id,
                    budget_id=budget.id,
                    reservation_id=reservation.id,
                    ledger_key=ledger_key,
                    kind="settle",
                    reserved_delta=-reservation.amount,
                    spent_delta=actual_amount,
                    created_at=now,
                )
            )
            session.flush()
            return _reservation_record(reservation)

    def release(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        reservation_id: UUID,
        ledger_key: str,
    ) -> ReservationRecord:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            reservation = session.scalar(
                select(BudgetReservation)
                .where(
                    BudgetReservation.id == reservation_id,
                    BudgetReservation.project_id == project_id,
                )
                .with_for_update()
            )
            if reservation is None:
                raise NotFoundError("Reservation not found")
            if reservation.state == ReservationState.RELEASED.value:
                return _reservation_record(reservation)
            if reservation.state != ReservationState.RESERVED.value:
                raise ConflictingOperationError("Only a reserved amount can be released")
            budget = session.scalar(
                select(Budget).where(Budget.id == reservation.budget_id).with_for_update()
            )
            if budget is None:
                raise NotFoundError("Budget not found")
            now = datetime.now(UTC)
            budget.reserved_amount -= reservation.amount
            if budget.reserved_amount < 0:
                raise ConflictingOperationError("Budget reservation balance is inconsistent")
            budget.revision += 1
            reservation.state = ReservationState.RELEASED.value
            reservation.settled_at = now
            session.add(
                BudgetLedgerEntry(
                    id=uuid4(),
                    workspace_id=budget.workspace_id,
                    project_id=budget.project_id,
                    budget_id=budget.id,
                    reservation_id=reservation.id,
                    ledger_key=ledger_key,
                    kind="release",
                    reserved_delta=-reservation.amount,
                    spent_delta=Decimal("0"),
                    created_at=now,
                )
            )
            session.flush()
            return _reservation_record(reservation)

    def mark_uncertain(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        reservation_id: UUID,
    ) -> ReservationRecord:
        with self._session_factory.begin() as session:
            actor = self._actor(session, actor_user_id)
            self._set_context(session, actor)
            reservation = session.scalar(
                select(BudgetReservation)
                .where(
                    BudgetReservation.id == reservation_id,
                    BudgetReservation.project_id == project_id,
                )
                .with_for_update()
            )
            if reservation is None:
                raise NotFoundError("Reservation not found")
            if reservation.state == ReservationState.RESERVED.value:
                reservation.state = ReservationState.UNCERTAIN.value
                session.flush()
            return _reservation_record(reservation)

    @staticmethod
    def _actor(session: Session, actor_user_id: UUID) -> User:
        actor = session.get(User, actor_user_id)
        if actor is None:
            raise NotFoundError("Project not found")
        return actor

    @staticmethod
    def _set_context(session: Session, actor: User) -> None:
        set_rls_context(
            session,
            workspace_id=actor.workspace_id,
            user_id=actor.id,
        )

    @staticmethod
    def _project(session: Session, project_id: UUID, workspace_id: UUID) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found")
        return project


def _validate_positive_amount(amount: Decimal, label: str) -> None:
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{label} must be finite and positive")


def _currency(value: str) -> str:
    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("Currency must be a three-letter ISO-style code")
    return currency


def _budget_snapshot(budget: Budget) -> BudgetSnapshot:
    return BudgetSnapshot(
        id=budget.id,
        project_id=budget.project_id,
        currency=budget.currency,
        limit_amount=budget.limit_amount,
        reserved_amount=budget.reserved_amount,
        spent_amount=budget.spent_amount,
        revision=budget.revision,
    )


def _reservation_record(reservation: BudgetReservation) -> ReservationRecord:
    return ReservationRecord(
        id=reservation.id,
        budget_id=reservation.budget_id,
        project_id=reservation.project_id,
        operation_key=reservation.operation_key,
        amount=reservation.amount,
        currency=reservation.currency,
        state=ReservationState(reservation.state),
    )
