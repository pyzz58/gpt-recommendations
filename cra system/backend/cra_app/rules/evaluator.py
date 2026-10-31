"""Closed, non-eval condition evaluator preserving three-value uncertainty."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from cra_app.rules.contracts import (
    BranchEvaluation,
    EvaluationResult,
    FactValue,
    NodeEvaluation,
    RuleCondition,
    RuleNode,
    RuleOperand,
)


def _unknown(reason: str) -> EvaluationResult:
    return EvaluationResult(result="unknown", reasons=[reason])


def _fact_value(
    operand: RuleOperand, facts: dict[str, FactValue]
) -> tuple[Any, str | None] | None:
    if operand.kind == "literal":
        return operand.value, operand.unit
    assert operand.fact_key is not None
    fact = facts.get(operand.fact_key)
    if fact is None:
        return None
    return fact.value, fact.unit


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _compare(
    op: str,
    left: RuleOperand,
    right: RuleOperand,
    facts: dict[str, FactValue],
) -> EvaluationResult:
    left_value = _fact_value(left, facts)
    right_value = _fact_value(right, facts)
    if left_value is None or right_value is None:
        return _unknown("required fact is missing")
    left_raw, left_unit = left_value
    right_raw, right_unit = right_value
    if left_unit and right_unit and left_unit != right_unit:
        return _unknown(f"unit mismatch: {left_unit} != {right_unit}")

    left_decimal = _decimal(left_raw)
    right_decimal = _decimal(right_raw)
    if left_decimal is not None and right_decimal is not None:
        comparable_left: Any = left_decimal
        comparable_right: Any = right_decimal
    else:
        left_date = _date(left_raw)
        right_date = _date(right_raw)
        if left_date is not None and right_date is not None:
            comparable_left = left_date
            comparable_right = right_date
        elif type(left_raw) is type(right_raw) or {
            type(left_raw),
            type(right_raw),
        } <= {str, int, bool}:
            comparable_left = left_raw
            comparable_right = right_raw
        else:
            return _unknown("values have no safe common comparison type")

    operations = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: a > b,
        "ge": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "le": lambda a, b: a <= b,
    }
    try:
        result = operations[op](comparable_left, comparable_right)
    except TypeError:
        return _unknown("comparison types are incompatible")
    return EvaluationResult(result="true" if result else "false")


def evaluate_condition(
    condition: RuleCondition | None,
    facts: dict[str, FactValue],
) -> EvaluationResult:
    """Evaluate only the documented finite AST; no source code is executed."""
    if condition is None:
        return _unknown("condition is not structured and requires analysis")
    op = condition.op
    if op == "all":
        results = [evaluate_condition(child, facts) for child in condition.children]
        if any(item.result == "false" for item in results):
            return EvaluationResult(result="false")
        if any(item.result == "unknown" for item in results):
            return EvaluationResult(
                result="unknown",
                reasons=sorted({reason for item in results for reason in item.reasons}),
            )
        return EvaluationResult(result="true")
    if op == "any":
        results = [evaluate_condition(child, facts) for child in condition.children]
        if any(item.result == "true" for item in results):
            return EvaluationResult(result="true")
        if any(item.result == "unknown" for item in results):
            return EvaluationResult(
                result="unknown",
                reasons=sorted({reason for item in results for reason in item.reasons}),
            )
        return EvaluationResult(result="false")
    if op == "not":
        assert condition.child is not None
        result = evaluate_condition(condition.child, facts)
        if result.result == "unknown":
            return result
        return EvaluationResult(
            result="false" if result.result == "true" else "true"
        )
    if op == "present":
        assert condition.fact_key is not None
        fact = facts.get(condition.fact_key)
        if fact is None:
            return _unknown("required fact is missing")
        return EvaluationResult(
            result="true" if fact.value is not None else "false"
        )
    if op in {"eq", "ne", "gt", "ge", "lt", "le"}:
        assert condition.left is not None and condition.right is not None
        return _compare(op, condition.left, condition.right, facts)
    if op == "in":
        assert condition.left is not None
        actual = _fact_value(condition.left, facts)
        if actual is None:
            return _unknown("required fact is missing")
        actual_value, actual_unit = actual
        has_unknown = False
        for candidate in condition.values:
            candidate_value = _fact_value(candidate, facts)
            if candidate_value is None:
                has_unknown = True
                continue
            value, unit = candidate_value
            if actual_unit and unit and actual_unit != unit:
                has_unknown = True
                continue
            if actual_value == value:
                return EvaluationResult(result="true")
            left_decimal = _decimal(actual_value)
            right_decimal = _decimal(value)
            if (
                left_decimal is not None
                and right_decimal is not None
                and left_decimal == right_decimal
            ):
                return EvaluationResult(result="true")
        if has_unknown:
            return _unknown("one or more membership candidates are unresolved")
        return EvaluationResult(result="false")
    if op == "date_interval":
        assert condition.fact_key is not None
        assert condition.anchor_fact_key is not None
        assert condition.min_days is not None
        assert condition.max_days is not None
        event = facts.get(condition.fact_key)
        anchor = facts.get(condition.anchor_fact_key)
        if event is None or anchor is None:
            return _unknown("date interval requires event and anchor facts")
        event_date = _date(event.value)
        anchor_date = _date(anchor.value)
        if event_date is None or anchor_date is None:
            return _unknown("date interval facts require ISO date values")
        delta = (event_date - anchor_date).days
        lower_ok = (
            delta >= condition.min_days
            if condition.inclusive
            else delta > condition.min_days
        )
        upper_ok = (
            delta <= condition.max_days
            if condition.inclusive
            else delta < condition.max_days
        )
        return EvaluationResult(
            result="true" if lower_ok and upper_ok else "false"
        )
    return _unknown(f"unsupported condition operator: {op}")


def evaluate_node(node: RuleNode, facts: dict[str, FactValue]) -> NodeEvaluation:
    if node.semantic_status == "analysis_required":
        return NodeEvaluation(
            node_key=node.node_key,
            status="analysis_required",
            unknowns=node.unknowns or ["rule requires analysis"],
        )

    precondition_results = [
        evaluate_condition(condition, facts) for condition in node.preconditions
    ]
    trigger_result = evaluate_condition(node.trigger, facts)
    exception_results = [
        evaluate_condition(exception.condition, facts)
        for exception in node.exceptions
    ]
    branch_results = [
        BranchEvaluation(
            branch_key=branch.branch_key,
            result=(evaluation := evaluate_condition(branch.condition, facts)).result,
            actions=branch.actions,
            reasons=evaluation.reasons,
        )
        for branch in node.branches
    ]
    selected = [
        branch.branch_key for branch in branch_results if branch.result == "true"
    ]
    uncertain = [
        branch.branch_key for branch in branch_results if branch.result == "unknown"
    ]
    reasons = [
        reason
        for item in (*precondition_results, trigger_result, *exception_results)
        if item is not None
        for reason in item.reasons
    ]

    if any(item.result == "true" for item in exception_results):
        status = "exception"
    elif any(item.result == "false" for item in precondition_results):
        status = "not_applicable"
    elif any(item.result == "unknown" for item in precondition_results):
        status = "unknown"
    elif trigger_result is None or trigger_result.result == "unknown":
        status = "unknown"
    elif trigger_result.result == "false":
        status = "not_applicable"
    else:
        status = "applicable"

    return NodeEvaluation(
        node_key=node.node_key,
        status=status,
        preconditions=precondition_results,
        trigger=trigger_result,
        exceptions=exception_results,
        branches=branch_results,
        selected_branch_keys=selected,
        unknown_branch_keys=uncertain,
        unknowns=sorted(set(reasons)),
    )
