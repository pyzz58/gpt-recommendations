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

    def condition_signature(condition: RuleCondition) -> str:
        return condition.model_dump_json(exclude_none=True)

    def extract(
        current: RuleNode,
        *,
        inherited_gates: tuple[RuleCondition, ...],
        path_prefix: str,
        suppress_trigger: bool = False,
    ) -> None:
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
                        node_key=current.node_key,
                        path=f"{path_prefix}{path}",
                        anchor_fact_key=anchor,
                        event_fact_key=event,
                        min_days=minimum,
                        max_days=maximum,
                        inclusive=inclusive,
                        gate_conditions=gate_conditions,
                    )
                )

        precondition_gates = tuple(
            RuleCondition(op="not", child=exception.condition)
            for exception in current.exceptions
            if exception.condition is not None
        )
        trigger_gate = (
            (current.trigger,)
            if current.trigger is not None
            and current.trigger.op != "date_interval"
            else ()
        )
        base_gates = (
            inherited_gates
            + tuple(current.preconditions)
            + precondition_gates
        )
        branch_gates = base_gates + trigger_gate
        for index, precondition in enumerate(current.preconditions):
            add(
                precondition,
                f"precondition[{index}]",
                (
                    inherited_gates
                    + tuple(
                        gate
                        for gate_index, gate in enumerate(
                            current.preconditions
                        )
                        if gate_index != index
                    )
                    + precondition_gates
                    + trigger_gate
                ),
            )
        if not suppress_trigger:
            add(current.trigger, "trigger", base_gates)
        children_by_key = {
            child.node_key: child for child in current.children
        }
        target_entries: dict[str, list[RuleCondition]] = {}
        for branch in current.branches:
            add(
                branch.condition,
                f"branch:{branch.branch_key}",
                branch_gates,
            )
            for target in branch.target_node_ids:
                if target in children_by_key:
                    target_entries.setdefault(target, []).append(
                        branch.condition
                    )
        for exception in current.exceptions:
            add(
                exception.condition,
                f"exception:{exception.exception_key}",
                (
                    inherited_gates
                    + tuple(current.preconditions)
                    + trigger_gate
                    + tuple(
                        RuleCondition(op="not", child=other.condition)
                        for other in current.exceptions
                        if other.exception_key != exception.exception_key
                        and other.condition is not None
                    )
                ),
            )
        for child in current.children:
            selection_conditions = target_entries.get(child.node_key, [])
            has_duplicate_trigger_path = bool(
                child.trigger is not None
                and any(
                    condition_signature(condition)
                    == condition_signature(child.trigger)
                    for condition in selection_conditions
                )
            )
            distinct_selection_conditions = [
                condition
                for condition in selection_conditions
                if child.trigger is None
                or condition_signature(condition)
                != condition_signature(child.trigger)
            ]
            selection_gates: tuple[RuleCondition, ...] = ()
            if (
                not has_duplicate_trigger_path
                and len(distinct_selection_conditions) == 1
            ):
                selection_gates = (distinct_selection_conditions[0],)
            elif (
                not has_duplicate_trigger_path
                and len(distinct_selection_conditions) > 1
            ):
                selection_gates = (
                    RuleCondition(
                        op="any",
                        children=distinct_selection_conditions,
                    ),
                )
            extract(
                child,
                inherited_gates=branch_gates + selection_gates,
                path_prefix=f"{path_prefix}{child.node_key}:",
                suppress_trigger=has_duplicate_trigger_path,
            )

    extract(
        node,
        inherited_gates=(),
        path_prefix="",
    )
    unique: list[DateIntervalSpec] = []
    seen: set[
        tuple[
            str,
            str,
            str,
            str,
            int,
            int,
            bool,
            tuple[str, ...],
        ]
    ] = set()
    for spec in specs:
        key = (
            spec.node_key,
            spec.path,
            spec.anchor_fact_key,
            spec.event_fact_key,
            spec.min_days,
            spec.max_days,
            spec.inclusive,
            tuple(
                condition_signature(condition)
                for condition in spec.gate_conditions
            ),
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
