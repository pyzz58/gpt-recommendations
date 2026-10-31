"""Date-precision-preserving visit-window calculations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Literal

from cra_app.rules.contracts import RuleCondition, RuleNode


@dataclass(frozen=True)
class DateWindow:
    anchor_date: date
    min_days: int
    max_days: int
    inclusive: bool = True

    @property
    def starts_on(self) -> date:
        return self.anchor_date + timedelta(days=self.min_days)

    @property
    def ends_on(self) -> date:
        return self.anchor_date + timedelta(days=self.max_days)

    def classify(self, actual_date: date | None) -> Literal[
        "in_window", "out_of_window", "unknown"
    ]:
        if actual_date is None:
            return "unknown"
        if self.inclusive:
            return (
                "in_window"
                if self.starts_on <= actual_date <= self.ends_on
                else "out_of_window"
            )
        return (
            "in_window"
            if self.starts_on < actual_date < self.ends_on
            else "out_of_window"
        )


@dataclass(frozen=True)
class DateIntervalSpec:
    node_key: str
    path: str
    anchor_fact_key: str
    event_fact_key: str
    min_days: int
    max_days: int
    inclusive: bool
    gate_conditions: tuple[RuleCondition, ...] = ()


def _date_interval(condition: RuleCondition | None) -> tuple[str, str, int, int, bool] | None:
    if condition is None or condition.op != "date_interval":
        return None
    assert condition.anchor_fact_key is not None
    assert condition.fact_key is not None
    assert condition.min_days is not None
    assert condition.max_days is not None
    return (
        condition.anchor_fact_key,
        condition.fact_key,
        condition.min_days,
        condition.max_days,
        condition.inclusive,
    )


def extract_date_interval_specs(node: RuleNode) -> list[DateIntervalSpec]:
    specs: list[DateIntervalSpec] = []

    def add(
        condition: RuleCondition | None,
        path: str,
        gate_conditions: tuple[RuleCondition, ...],
    ) -> None:
        parsed = _date_interval(condition)
        if parsed:
            anchor, event, minimum, maximum, inclusive = parsed
            specs.append(
                DateIntervalSpec(
                    node_key=node.node_key,
                    path=path,
                    anchor_fact_key=anchor,
                    event_fact_key=event,
                    min_days=minimum,
                    max_days=maximum,
                    inclusive=inclusive,
                    gate_conditions=gate_conditions,
                )
            )

    base_gates = tuple(node.preconditions) + tuple(
        RuleCondition(op="not", child=exception.condition)
        for exception in node.exceptions
        if exception.condition is not None
    )
    for index, precondition in enumerate(node.preconditions):
        gates = tuple(
            gate
            for gate_index, gate in enumerate(node.preconditions)
            if gate_index != index
        )
        add(precondition, f"precondition[{index}]", gates)
    add(node.trigger, "trigger", base_gates)
    branch_gates = (
        base_gates + (node.trigger,)
        if node.trigger is not None and node.trigger.op != "date_interval"
        else base_gates
    )
    for branch in node.branches:
        add(
            branch.condition,
            f"branch:{branch.branch_key}",
            branch_gates,
        )
    exception_gates = branch_gates
    for exception in node.exceptions:
        add(
            exception.condition,
            f"exception:{exception.exception_key}",
            exception_gates,
        )
    for child in node.children:
        specs.extend(
            DateIntervalSpec(
                node_key=spec.node_key,
                path=f"{child.node_key}:{spec.path}",
                anchor_fact_key=spec.anchor_fact_key,
                event_fact_key=spec.event_fact_key,
                min_days=spec.min_days,
                max_days=spec.max_days,
                inclusive=spec.inclusive,
                gate_conditions=spec.gate_conditions,
            )
            for spec in extract_date_interval_specs(child)
        )
    unique: list[DateIntervalSpec] = []
    seen: set[tuple[str, str, int, int, bool]] = set()
    for spec in specs:
        key = (
            spec.anchor_fact_key,
            spec.event_fact_key,
            spec.min_days,
            spec.max_days,
            spec.inclusive,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(spec)
    return unique


def current_stage(facts: dict[str, str]) -> str:
    for key in ("current_stage", "study_stage", "study_phase"):
        value = facts.get(key)
        if value:
            return value
    return "unknown"
