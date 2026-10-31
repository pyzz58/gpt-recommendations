"""Deadline calculations that never invent a missing due date."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DeadlineState:
    status: str
    overdue_days: int | None
    days_remaining: int | None
    source: str | None


def assess_deadline(
    *,
    due_on: date | None,
    deadline_source: str | None,
    as_of: date,
    resolved_on: date | None = None,
) -> DeadlineState:
    if resolved_on is not None:
        return DeadlineState(
            status="resolved",
            overdue_days=None,
            days_remaining=None,
            source=deadline_source,
        )
    if due_on is None or deadline_source is None or not deadline_source.strip():
        return DeadlineState(
            status="due_date_unknown",
            overdue_days=None,
            days_remaining=None,
            source=deadline_source,
        )
    delta = (as_of - due_on).days
    if delta > 0:
        return DeadlineState(
            status="overdue",
            overdue_days=delta,
            days_remaining=None,
            source=deadline_source,
        )
    return DeadlineState(
        status="due_date_known",
        overdue_days=0,
        days_remaining=-delta,
        source=deadline_source,
    )
