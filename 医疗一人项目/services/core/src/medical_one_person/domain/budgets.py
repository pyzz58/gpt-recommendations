from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ReservationState(StrEnum):
    RESERVED = "reserved"
    SETTLED = "settled"
    RELEASED = "released"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class BudgetSnapshot:
    id: UUID
    project_id: UUID
    currency: str
    limit_amount: Decimal
    reserved_amount: Decimal
    spent_amount: Decimal
    revision: int

    @property
    def available_amount(self) -> Decimal:
        return max(
            self.limit_amount - self.reserved_amount - self.spent_amount,
            Decimal("0"),
        )


@dataclass(frozen=True)
class ReservationRecord:
    id: UUID
    budget_id: UUID
    project_id: UUID
    operation_key: str
    amount: Decimal
    currency: str
    state: ReservationState
