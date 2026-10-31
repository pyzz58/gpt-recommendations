"""Deterministic, source-verifying rule extraction for the W04 authored subset.

This is an actual provider, not a canned result: it consumes parsed anchors,
parses a documented rule-statement grammar, creates a finite AST, and rejects
source or numeric evidence that cannot be found in the input. Free-form
clinical prose outside the subset remains analysis-required.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from cra_app.providers.ports import ParsedAnchor
from cra_app.rules.contracts import (
    ExtractionCoverage,
    ExtractionRelation,
    RuleBranch,
    RuleCondition,
    RuleException,
    RuleExtractionResult,
    RuleNode,
    RuleOperand,
    RuleSourceRef,
)
from cra_app.rules.evaluator import evaluate_condition
from cra_app.rules.contracts import FactValue

RULE_HEADING = re.compile(
    r"^\s*(?:Rule|规则)\s+([A-Za-z][A-Za-z0-9._-]{2,})\s*[:：]\s*(.+)$",
    re.IGNORECASE,
)
RULE_REFERENCE = re.compile(r"\bR-[A-Z0-9][A-Z0-9._-]*\b", re.IGNORECASE)
RELATION_DIRECTIVE = re.compile(
    r"^\s*(?:Relation|关系)\s*[:：]\s*"
    r"(?P<source>[A-Za-z][A-Za-z0-9._-]+)\s+"
    r"(?P<relation>replaces|withdraws|restores|supplements|补充|替代|撤销|恢复)\s+"
    r"(?P<target>[A-Za-z][A-Za-z0-9._-]+)\s*$",
    re.IGNORECASE,
)
FOOTNOTE_RULE = re.compile(
    r"^\s*(?:Footnote|脚注)\s+(?P<rule>R-[A-Z0-9._-]+)\s*[:：]\s*(?P<text>.+)$",
    re.IGNORECASE,
)
NUMBER = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])")
TOKEN = re.compile(
    r"""
    \s*(
      >=|<=|!=|==|=|>|<|\(|\)|,|
      "(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|
      [A-Za-z_][A-Za-z0-9_.-]*|
      [-+]?\d+(?:\.\d+)?|
      且|并且|或|非|不是
    )
    """,
    re.VERBOSE,
)


class RuleExtractionError(ValueError):
    pass


@dataclass
class _RuleBuilder:
    rule_key: str
    summary: str
    source_line: ParsedAnchor
    preconditions: list[tuple[RuleCondition, ParsedAnchor]] = field(default_factory=list)
    trigger: tuple[RuleCondition, ParsedAnchor] | None = None
    branches: list[RuleBranch] = field(default_factory=list)
    exceptions: list[RuleException] = field(default_factory=list)
    follow_up: str | None = None
    completion: str | None = None
    required_facts: list[str] = field(default_factory=list)
    children: list[RuleNode] = field(default_factory=list)
    source_anchors: list[ParsedAnchor] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    analysis_required: bool = False

    def add_source(self, anchor: ParsedAnchor) -> RuleSourceRef:
        if all(item.logical_node_id != anchor.logical_node_id for item in self.source_anchors):
            self.source_anchors.append(anchor)
        return _source_ref(anchor)


def _source_ref(anchor: ParsedAnchor) -> RuleSourceRef:
    locator = anchor.logical_node_id
    if anchor.page_number is not None:
        locator = f"page {anchor.page_number}: {locator}"
    return RuleSourceRef(
        anchor_key=anchor.logical_node_id,
        quote=anchor.text,
        locator=locator,
    )


def _fact_operand(token: str) -> RuleOperand:
    return RuleOperand(kind="fact_ref", fact_key=token)


def _literal_operand(token: str, unit: str | None = None) -> RuleOperand:
    lowered = token.lower()
    if lowered == "true":
        value: str | int | Decimal | bool = True
    elif lowered == "false":
        value = False
    elif lowered in {"null", "none"}:
        value = None
    elif re.fullmatch(r"[-+]?\d+(?:\.\d+)?", token):
        value = Decimal(token)
    elif token[:1] in {"'", '"'} and token[-1:] == token[:1]:
        value = token[1:-1]
    else:
        return _fact_operand(token)
    return RuleOperand(kind="literal", value=value, unit=unit)


class _ConditionParser:
    def __init__(self, source: str):
        self.tokens = [match.group(1) for match in TOKEN.finditer(source)]
        consumed = "".join(match.group(0) for match in TOKEN.finditer(source))
        if re.sub(r"\s+", "", consumed) != re.sub(r"\s+", "", source):
            raise RuleExtractionError("condition contains unsupported syntax")
        self.index = 0

    def _peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _take(self) -> str:
        token = self._peek()
        if token is None:
            raise RuleExtractionError("unexpected end of condition")
        self.index += 1
        return token

    def _accept(self, *values: str) -> str | None:
        token = self._peek()
        if token and token.upper() in {value.upper() for value in values}:
            self.index += 1
            return token
        return None

    def parse(self) -> RuleCondition:
        condition = self._parse_or()
        if self.index != len(self.tokens):
            raise RuleExtractionError(
                f"unexpected condition token: {self.tokens[self.index]}"
            )
        return condition

    def _parse_or(self) -> RuleCondition:
        children = [self._parse_and()]
        while self._accept("OR", "或"):
            children.append(self._parse_and())
        if len(children) == 1:
            return children[0]
        return RuleCondition(op="any", children=children)

    def _parse_and(self) -> RuleCondition:
        children = [self._parse_unary()]
        while self._accept("AND", "且", "并且"):
            children.append(self._parse_unary())
        if len(children) == 1:
            return children[0]
        return RuleCondition(op="all", children=children)

    def _parse_unary(self) -> RuleCondition:
        if self._accept("NOT", "非", "不是"):
            return RuleCondition(op="not", child=self._parse_unary())
        if self._accept("PRESENT", "存在"):
            operand = self._operand()
            if operand.kind != "fact_ref" or not operand.fact_key:
                raise RuleExtractionError("present requires a fact name")
            return RuleCondition(op="present", fact_key=operand.fact_key)
        if self._accept("(") is not None:
            result = self._parse_or()
            if self._accept(")") is None:
                raise RuleExtractionError("missing closing parenthesis")
            return result
        return self._parse_predicate()

    def _operand(self) -> RuleOperand:
        token = self._take()
        operand = _literal_operand(token)
        if operand.kind == "literal" and self._peek() and re.fullmatch(
            r"[A-Za-z%][A-Za-z0-9%/._-]*", self._peek() or ""
        ):
            if (self._peek() or "").upper() not in {
                "AND",
                "OR",
                "IN",
                "THEN",
            }:
                operand = operand.model_copy(update={"unit": self._take()})
        return operand

    def _parse_predicate(self) -> RuleCondition:
        left = self._operand()
        if self._accept("NOT") is not None and self._accept("IN") is not None:
            values = self._parse_in_values()
            return RuleCondition(
                op="not",
                child=RuleCondition(op="in", left=left, values=values),
            )
        if self._accept("IN") is not None:
            return RuleCondition(op="in", left=left, values=self._parse_in_values())
        operator = self._accept("=", "==", "!=", ">", ">=", "<", "<=")
        if operator is None:
            if left.kind != "fact_ref" or not left.fact_key:
                raise RuleExtractionError("a literal cannot be a standalone condition")
            return RuleCondition(op="present", fact_key=left.fact_key)
        right = self._operand()
        mapped = {
            "=": "eq",
            "==": "eq",
            "!=": "ne",
            ">": "gt",
            ">=": "ge",
            "<": "lt",
            "<=": "le",
        }[operator]
        return RuleCondition(op=mapped, left=left, right=right)

    def _parse_in_values(self) -> list[RuleOperand]:
        if self._accept("(") is None:
            raise RuleExtractionError("IN requires a parenthesized value list")
        values = [self._in_value()]
        while self._accept(",") is not None:
            values.append(self._in_value())
        if self._accept(")") is None:
            raise RuleExtractionError("IN value list is not closed")
        return values

    def _in_value(self) -> RuleOperand:
        token = self._take()
        if token[:1] in {"'", '"'} or token.lower() in {
            "true",
            "false",
            "null",
            "none",
        } or re.fullmatch(r"[-+]?\d+(?:\.\d+)?", token):
            return _literal_operand(token)
        return RuleOperand(kind="literal", value=token)


def parse_condition(source: str) -> RuleCondition:
    cleaned = source.strip().rstrip("。.;；")
    interval = re.fullmatch(
        r"(?P<event>[A-Za-z_][A-Za-z0-9_.-]*)\s+"
        r"(?:within|在)\s+(?P<lower>-?\d+)\s*\.\.\s*(?P<upper>-?\d+)\s+"
        r"(?:days?|天)\s+(?:of|相对)\s+"
        r"(?P<anchor>[A-Za-z_][A-Za-z0-9_.-]*)",
        cleaned,
        re.IGNORECASE,
    )
    if interval:
        return RuleCondition(
            op="date_interval",
            fact_key=interval.group("event"),
            anchor_fact_key=interval.group("anchor"),
            min_days=int(interval.group("lower")),
            max_days=int(interval.group("upper")),
        )
    return _ConditionParser(cleaned).parse()


def _strip_condition(value: str) -> str:
    return re.sub(
        r"^\s*(?:if|when|如果|当)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()


def _split_condition_action(value: str) -> tuple[str, str | None]:
    match = re.search(r"\s+(?:then|则|->)\s+", value, re.IGNORECASE)
    if not match:
        return _strip_condition(value), None
    return _strip_condition(value[: match.start()]), value[match.end() :].strip()


def _semantic_errors(node: RuleNode, source_text: str) -> list[str]:
    """Independent completeness checks for a real quote with a wrong AST."""
    lowered = source_text.casefold()
    condition_source = "\n".join(
        line
        for line in source_text.splitlines()
        if re.match(
            r"^\s*(Trigger|Precondition|Branch|Exception|触发|前提|分支|例外)\b",
            line,
            re.IGNORECASE,
        )
    ).upper()
    errors: list[str] = []
    if (
        any(
            marker in lowered
            for marker in ("precondition:", "前提：", "前提:")
        )
        and not node.preconditions
    ):
        errors.append("source precondition was not preserved")
    if (
        any(marker in lowered for marker in ("unless", "except", "例外"))
        and not node.exceptions
    ):
        errors.append("source condition has an exception that the candidate lost")
    if (
        any(marker in lowered for marker in ("must not", "may not", "不得", "禁止"))
        and not any(
            marker in node.summary.casefold()
            for marker in ("must not", "may not", "不得", "禁止")
        )
        and not re.search(r'"op"\s*:\s*"(?:not|ne)"', node.model_dump_json())
    ):
        errors.append("source negation was not preserved")
    if (
        any(marker in lowered for marker in ("both", "同时", "并且"))
        and " OR " in condition_source
    ):
        errors.append("source contains mixed conjunction/disjunction semantics")
    if (
        " AND " in condition_source
        and not any(
            item.op == "all"
            for item in (node.trigger, *node.preconditions)
            if item is not None
        )
    ):
        errors.append("source conjunction was not represented as all")
    if any(marker in lowered for marker in ("either", "任一", "之一")) and not any(
        child.op == "any"
        for child in [node.trigger]
        if child is not None
    ):
        errors.append("source disjunction was not represented as any")
    source_numbers = set(NUMBER.findall(source_text))
    tree_numbers = _candidate_numbers(node)
    if not tree_numbers <= source_numbers:
        errors.append("candidate contains a number absent from its source")
    return errors


def _candidate_numbers(node: RuleNode) -> set[str]:
    values: set[str] = set()
    for text in (
        node.node_key,
        node.summary,
        node.follow_up or "",
        node.completion or "",
        *(
            action
            for branch in node.branches
            for action in branch.actions
        ),
        *(exception.description for exception in node.exceptions),
    ):
        values.update(NUMBER.findall(text))
    conditions: list[RuleCondition] = [
        *node.preconditions,
        *[branch.condition for branch in node.branches],
        *[
            exception.condition
            for exception in node.exceptions
            if exception.condition is not None
        ],
    ]
    if node.trigger is not None:
        conditions.append(node.trigger)
    while conditions:
        condition = conditions.pop()
        if condition.fact_key:
            values.update(NUMBER.findall(condition.fact_key))
        if condition.anchor_fact_key:
            values.update(NUMBER.findall(condition.anchor_fact_key))
        for operand in (condition.left, condition.right, *condition.values):
            if operand is not None and operand.value is not None:
                values.update(NUMBER.findall(str(operand.value)))
        if condition.child is not None:
            conditions.append(condition.child)
        conditions.extend(condition.children)
    for child in node.children:
        values.update(_candidate_numbers(child))
    return values


def validate_candidate_semantics(
    node: RuleNode, quoted_source: str
) -> list[str]:
    """Public hook used by tests and extraction evaluation."""
    return _semantic_errors(node, quoted_source)


class AnchoredRuleExtractor:
    name = "anchored-rule-subset"
    version = "1"

    def extract_rules(self, *, anchors: list[ParsedAnchor]) -> RuleExtractionResult:
        builders: dict[str, _RuleBuilder] = {}
        current: _RuleBuilder | None = None
        footnotes: list[tuple[str, ParsedAnchor]] = []
        relations: list[ExtractionRelation] = []
        coverage: list[ExtractionCoverage] = []
        warnings: list[str] = []

        for anchor in sorted(anchors, key=lambda item: item.ordinal):
            tags = anchor.metadata.get("content_control_tags", [])
            text = anchor.text.strip()
            if not text:
                continue
            if any(
                "background" in str(tag).casefold() or "背景" in str(tag)
                for tag in tags
            ):
                coverage.append(
                    ExtractionCoverage(
                        unit_key=anchor.logical_node_id,
                        status="background",
                        reason="explicit background content control",
                        anchor_key=anchor.logical_node_id,
                    )
                )
                continue

            if anchor.style.get("heading_level"):
                current = None
                coverage.append(
                    ExtractionCoverage(
                        unit_key=anchor.logical_node_id,
                        status="processed",
                        reason="section heading",
                        anchor_key=anchor.logical_node_id,
                    )
                )
                continue

            heading = RULE_HEADING.match(text)
            if heading:
                rule_key = heading.group(1).upper()
                current = builders.get(rule_key)
                if current is None:
                    current = _RuleBuilder(
                        rule_key=rule_key,
                        summary=heading.group(2).strip().rstrip("。.;；"),
                        source_line=anchor,
                    )
                    builders[rule_key] = current
                current.add_source(anchor)
                coverage.append(
                    ExtractionCoverage(
                        unit_key=anchor.logical_node_id,
                        status="processed",
                        anchor_key=anchor.logical_node_id,
                    )
                )
                continue

            relation_match = RELATION_DIRECTIVE.match(text)
            if relation_match:
                relation_word = relation_match.group("relation").casefold()
                relation_type = {
                    "replaces": "replaces",
                    "替代": "replaces",
                    "withdraws": "withdraws",
                    "撤销": "withdraws",
                    "restores": "restores",
                    "恢复": "restores",
                    "supplements": "supplement",
                    "补充": "supplement",
                }[relation_word]
                relations.append(
                    ExtractionRelation(
                        rule_key=relation_match.group("source").upper(),
                        relation_type=relation_type,
                        target_rule_key=relation_match.group("target").upper(),
                        reason=f"explicit source relation: {text}",
                        source_refs=[_source_ref(anchor)],
                    )
                )
                coverage.append(
                    ExtractionCoverage(
                        unit_key=anchor.logical_node_id,
                        status="processed",
                        anchor_key=anchor.logical_node_id,
                    )
                )
                continue

            footnote_match = FOOTNOTE_RULE.match(text)
            if footnote_match:
                footnotes.append((footnote_match.group("rule").upper(), anchor))
                coverage.append(
                    ExtractionCoverage(
                        unit_key=anchor.logical_node_id,
                        status="processed",
                        anchor_key=anchor.logical_node_id,
                    )
                )
                continue

            if current is None:
                if re.search(
                    r"\b(?:shall|must|required)\b|应当|必须|要求",
                    text,
                    re.IGNORECASE,
                ):
                    warnings.append(
                        f"unbound requirement at {anchor.logical_node_id}"
                    )
                    coverage.append(
                        ExtractionCoverage(
                            unit_key=anchor.logical_node_id,
                            status="analysis_required",
                            reason="requirement has no stable Rule identifier",
                            anchor_key=anchor.logical_node_id,
                        )
                    )
                else:
                    coverage.append(
                        ExtractionCoverage(
                            unit_key=anchor.logical_node_id,
                            status="processed",
                            reason="non-rule context",
                            anchor_key=anchor.logical_node_id,
                        )
                    )
                continue

            matched = re.match(
                r"^\s*(Summary|Requirement|摘要|要求)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                current.summary = matched.group(2).strip().rstrip("。.;；")
                current.add_source(anchor)
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Precondition|前提)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                current.preconditions.append(
                    (parse_condition(matched.group(2)), anchor)
                )
                current.add_source(anchor)
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Trigger|触发)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                current.trigger = (parse_condition(matched.group(2)), anchor)
                current.add_source(anchor)
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Branch|分支)\s+([A-Za-z0-9._-]+)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                condition_text, action_text = _split_condition_action(
                    matched.group(3)
                )
                condition = parse_condition(condition_text)
                branch_key = matched.group(2).upper()
                action = (
                    action_text
                    or f"Follow source branch {branch_key}"
                ).strip()
                source_ref = current.add_source(anchor)
                current.branches.append(
                    RuleBranch(
                        branch_key=branch_key,
                        label=f"Branch {branch_key}",
                        condition=condition,
                        target_node_ids=[f"{current.rule_key}-{branch_key}"],
                        actions=[action],
                        source_refs=[source_ref],
                    )
                )
                current.children.append(
                    RuleNode(
                        node_key=f"{current.rule_key}-{branch_key}",
                        summary=action,
                        trigger=condition,
                        follow_up=action,
                        source_refs=[source_ref],
                    )
                )
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Exception|例外)\s+([A-Za-z0-9._-]+)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                condition_text, action_text = _split_condition_action(
                    matched.group(3)
                )
                try:
                    condition = parse_condition(condition_text)
                    description = (action_text or condition_text).strip()
                except RuleExtractionError:
                    condition = None
                    description = matched.group(3).strip()
                    current.analysis_required = True
                    current.unknowns.append(
                        f"exception {matched.group(2)} needs analysis"
                    )
                current.exceptions.append(
                    RuleException(
                        exception_key=matched.group(2).upper(),
                        description=description,
                        condition=condition,
                        source_refs=[current.add_source(anchor)],
                    )
                )
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Follow-up|Follow up|后续)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                current.follow_up = matched.group(2).strip()
                current.add_source(anchor)
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Completion|完成)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                current.completion = matched.group(2).strip()
                current.add_source(anchor)
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Required facts|所需事实)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                current.required_facts.extend(
                    item.strip()
                    for item in re.split(r"[,，;；]", matched.group(2))
                    if item.strip()
                )
                current.add_source(anchor)
                coverage.append(self._processed(anchor))
                continue

            matched = re.match(
                r"^\s*(Child|子项)\s+([A-Za-z0-9._-]+)\s*[:：]\s*(.+)$",
                text,
                re.IGNORECASE,
            )
            if matched:
                source_ref = current.add_source(anchor)
                current.children.append(
                    RuleNode(
                        node_key=f"{current.rule_key}-{matched.group(2).upper()}",
                        summary=matched.group(3).strip(),
                        source_refs=[source_ref],
                    )
                )
                coverage.append(self._processed(anchor))
                continue

            current.add_source(anchor)
            current.analysis_required = True
            current.unknowns.append(
                f"unstructured clause at {anchor.logical_node_id}"
            )
            coverage.append(
                ExtractionCoverage(
                    unit_key=anchor.logical_node_id,
                    status="analysis_required",
                    reason="clause is preserved but outside the finite AST subset",
                    anchor_key=anchor.logical_node_id,
                )
            )

        for rule_key, anchor in footnotes:
            if rule_key in builders:
                builders[rule_key].add_source(anchor)

        nodes: list[RuleNode] = []
        for builder in builders.values():
            all_facts = set(builder.required_facts)
            fields = [
                builder.trigger[0] if builder.trigger else None,
                *[condition for condition, _ in builder.preconditions],
                *[branch.condition for branch in builder.branches],
                *[
                    exception.condition
                    for exception in builder.exceptions
                    if exception.condition is not None
                ],
            ]
            for condition in fields:
                if condition is not None:
                    all_facts.update(_condition_facts(condition))
            node = RuleNode(
                node_key=builder.rule_key,
                summary=builder.summary,
                preconditions=[condition for condition, _ in builder.preconditions],
                trigger=builder.trigger[0] if builder.trigger else None,
                branches=builder.branches,
                exceptions=builder.exceptions,
                follow_up=builder.follow_up,
                completion=builder.completion,
                required_facts=sorted(all_facts),
                children=builder.children,
                source_refs=[
                    self._source_ref_for_builder(anchor)
                    for anchor in builder.source_anchors
                ],
                semantic_status=(
                    "analysis_required"
                    if builder.analysis_required
                    else "complete"
                ),
                unknowns=builder.unknowns,
            )
            quoted = "\n".join(ref.quote for ref in node.source_refs)
            semantic_errors = validate_candidate_semantics(node, quoted)
            if semantic_errors:
                node = node.model_copy(
                    update={
                        "semantic_status": "analysis_required",
                        "unknowns": sorted(
                            {*builder.unknowns, *semantic_errors}
                        ),
                    }
                )
            nodes.append(node)

        source_texts = [
            anchor.text for anchor in anchors if anchor.anchor_type == "plain_text"
        ]
        direct_accept = bool(
            nodes
            and source_texts
            and len(source_texts) == len(anchors)
            and all(node.semantic_status == "complete" for node in nodes)
        )
        return RuleExtractionResult(
            provider_name=self.name,
            provider_version=self.version,
            rules=nodes,
            coverage=coverage,
            relations=relations,
            direct_accept=direct_accept,
            warnings=warnings,
        )

    @staticmethod
    def _processed(anchor: ParsedAnchor) -> ExtractionCoverage:
        return ExtractionCoverage(
            unit_key=anchor.logical_node_id,
            status="processed",
            anchor_key=anchor.logical_node_id,
        )

    @staticmethod
    def _source_ref_for_builder(anchor: ParsedAnchor) -> RuleSourceRef:
        return _source_ref(anchor)


def _condition_facts(condition: RuleCondition) -> set[str]:
    values: set[str] = set()
    if condition.fact_key:
        values.add(condition.fact_key)
    if condition.anchor_fact_key:
        values.add(condition.anchor_fact_key)
    for operand in (condition.left, condition.right, *condition.values):
        if operand and operand.fact_key:
            values.add(operand.fact_key)
    if condition.child:
        values.update(_condition_facts(condition.child))
    for child in condition.children:
        values.update(_condition_facts(child))
    return values


def node_digest(node: RuleNode) -> str:
    raw = json.dumps(
        node.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compare_rule_semantics(
    previous: RuleNode,
    current: RuleNode,
    *,
    explicit_relation: str | None = None,
) -> tuple[str, str]:
    if explicit_relation:
        return explicit_relation, "explicit relation in the source version"

    def semantic_payload(node: RuleNode) -> dict[str, Any]:
        payload = node.model_dump(mode="json")
        payload.pop("source_refs", None)
        for branch in payload.get("branches", []):
            branch.pop("source_refs", None)
        for exception in payload.get("exceptions", []):
            exception.pop("source_refs", None)
        payload["children"] = [
            semantic_payload(RuleNode.model_validate(child))
            for child in payload.get("children", [])
        ]
        return payload

    previous_payload = semantic_payload(previous)
    current_payload = semantic_payload(current)
    if previous_payload == current_payload:
        return "unchanged", "same rule tree"
    previous_children = {child.node_key for child in previous.children}
    current_children = {child.node_key for child in current.children}
    previous_exceptions = {
        exception.exception_key for exception in previous.exceptions
    }
    current_exceptions = {
        exception.exception_key for exception in current.exceptions
    }
    base_same = semantic_payload(
        previous.model_copy(update={"children": [], "exceptions": []})
    ) == semantic_payload(
        current.model_copy(update={"children": [], "exceptions": []})
    )
    if base_same and current_children >= previous_children:
        if current_exceptions > previous_exceptions:
            return "exception", "new exception was added"
        return "supplement", "new child requirement was added"
    return (
        "conflict",
        "changed rule meaning needs explicit replacement/withdrawal evidence",
    )


def evaluate_extraction_cases(
    result: RuleExtractionResult,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    by_key = {rule.node_key: rule for rule in result.rules}
    failures: list[str] = []
    passed = 0
    for case in cases:
        rule = by_key.get(case["rule_key"])
        if rule is None:
            failures.append(f"missing extracted rule {case['rule_key']}")
            continue
        if rule.semantic_status != case.get("semantic_status", "complete"):
            failures.append(
                f"{case['rule_key']} semantic status {rule.semantic_status}"
            )
            continue
        if len(rule.exceptions) != int(case.get("exception_count", 0)):
            failures.append(f"{case['rule_key']} exception count mismatch")
            continue
        facts = {
            key: FactValue(value=value, unit=unit)
            for key, (value, unit) in case.get("facts", {}).items()
        }
        for expected in case.get("branch_expectations", []):
            branch = next(
                (
                    item
                    for item in rule.branches
                    if item.branch_key == expected["branch_key"]
                ),
                None,
            )
            if branch is None:
                failures.append(
                    f"{case['rule_key']} missing branch {expected['branch_key']}"
                )
                continue
            actual = evaluate_condition(branch.condition, facts).result
            if actual != expected["result"]:
                failures.append(
                    f"{case['rule_key']}/{expected['branch_key']} "
                    f"expected {expected['result']} got {actual}"
                )
                continue
            passed += 1
        source = "\n".join(ref.quote for ref in rule.source_refs)
        corrupted = rule.model_copy(
            update={
                "exceptions": [],
                "semantic_status": "complete",
            }
        )
        if "exception" in source.casefold() and not validate_candidate_semantics(
            corrupted, source
        ):
            failures.append(
                f"{case['rule_key']} lost exception was not detected"
            )
            continue
        passed += 1
    return {
        "provider": result.provider_name,
        "provider_version": result.provider_version,
        "rules_extracted": len(result.rules),
        "coverage_units": len(result.coverage),
        "checks_passed": passed,
        "failures": failures,
        "passed": not failures,
    }
