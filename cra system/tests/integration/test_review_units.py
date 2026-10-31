"""Application-level unit regressions for the 2026-11-01 review."""
from __future__ import annotations

from datetime import date

from cra_app.laboratory.comparison import (
    EdcValue,
    ObservationValue,
    compare_observation,
)
from cra_app.laboratory.recognition import extract_observations
from cra_app.providers.lab_ocr import (
    LabRecognitionResult,
    ProviderCell,
    ProviderLine,
    ProviderRow,
    ProviderTable,
)
from cra_app.providers.ports import ParsedAnchor
from cra_app.providers.rule_extraction import AnchoredRuleExtractor
from cra_app.rules.contracts import (
    FactValue,
    RuleCondition,
    RuleException,
    RuleNode,
    RuleOperand,
    RuleSourceRef,
)
from cra_app.rules.evaluator import evaluate_condition, evaluate_node


def _observation(
    *,
    value: str = "10",
    lower_limit: str | None = None,
    upper_limit: str | None = None,
) -> ObservationValue:
    return ObservationValue(
        id="source",
        subject_external_id="S1",
        visit_key="V1",
        analyte="Synthetic",
        specimen="Blood",
        collected_on=date(2026, 1, 1),
        collected_at=None,
        instance_type="initial",
        report_on=None,
        report_revision="FINAL",
        value_raw=value,
        unit="g/L",
        lower_limit=lower_limit,
        upper_limit=upper_limit,
    )


def _edc(
    source: ObservationValue,
    *,
    value: str = "10",
    lower_limit: str | None = None,
    upper_limit: str | None = None,
) -> EdcValue:
    return EdcValue(
        id="edc",
        subject_external_id="S1",
        subject_id="subject",
        visit_key="V1",
        analyte="Synthetic",
        specimen="Blood",
        collected_on=source.collected_on,
        collected_at=None,
        instance_type="initial",
        report_on=None,
        report_revision="FINAL",
        value_raw=value,
        unit="g/L",
        lower_limit=lower_limit,
        upper_limit=upper_limit,
    )


def test_reference_limits_are_compared_independently():
    source = _observation(lower_limit="0", upper_limit="20")
    edc = _edc(source, lower_limit="0", upper_limit="30")
    result = compare_observation(source, [edc])
    assert result.result_status == "logic_difference"
    assert "upper_limit_difference" in result.unknowns


def test_one_sided_reference_range_is_not_dropped():
    source = _observation()
    edc = _edc(source, lower_limit="0", upper_limit="20")
    result = compare_observation(source, [edc])
    assert result.result_status == "logic_difference"
    assert "lower_limit_difference" in result.unknowns
    assert "upper_limit_difference" in result.unknowns


def test_report_header_context_is_reused_without_patient_guess():
    table = ProviderTable(
        index=1,
        page=1,
        bbox=(0, 150, 500, 300),
        rows=(
            ProviderRow(
                (
                    ProviderCell("检验项目"),
                    ProviderCell("结果"),
                    ProviderCell("单位"),
                )
            ),
            ProviderRow(
                (
                    ProviderCell("葡萄糖"),
                    ProviderCell("5.1"),
                    ProviderCell("mmol/L"),
                )
            ),
        ),
    )
    result = LabRecognitionResult(
        provider_name="synthetic-provider",
        provider_version="1",
        model_version=None,
        file_format="clear_printed_image",
        tables=(table,),
        lines=(
            ProviderLine("受试者编号：SYN-001", 1, (0, 10, 200, 20)),
            ProviderLine("采样日期：2026-01-01", 1, (0, 25, 240, 35)),
            ProviderLine("初检复查：初检", 1, (0, 40, 200, 50)),
        ),
        warnings=(),
    )
    draft = extract_observations(result)
    assert draft.state == "recognized"
    assert draft.rows[0].subject_external_id == "SYN-001"
    assert draft.rows[0].collected_on.isoformat() == "2026-01-01"
    assert draft.rows[0].instance_type == "initial"
    assert (
        draft.rows[0].source_ref["cells"]["subject_external_id"]["kind"]
        == "report_context"
    )


def test_conflicting_row_and_report_identity_requires_review():
    table = ProviderTable(
        index=1,
        page=1,
        bbox=(0, 150, 500, 300),
        rows=(
            ProviderRow(
                (
                    ProviderCell("Subject ID"),
                    ProviderCell("Test"),
                    ProviderCell("Result"),
                    ProviderCell("Unit"),
                    ProviderCell("Collection Date"),
                    ProviderCell("Initial/Repeat"),
                )
            ),
            ProviderRow(
                (
                    ProviderCell("SYN-ROW-002"),
                    ProviderCell("Synthetic"),
                    ProviderCell("5.1"),
                    ProviderCell("mmol/L"),
                    ProviderCell("2026-01-02"),
                    ProviderCell("Initial"),
                )
            ),
        ),
    )
    result = LabRecognitionResult(
        provider_name="synthetic-provider",
        provider_version="1",
        model_version=None,
        file_format="clear_printed_image",
        tables=(table,),
        lines=(
            ProviderLine(
                "Subject ID: SYN-HEADER-001", 1, (0, 10, 200, 20)
            ),
            ProviderLine(
                "Collection Date: 2026-01-02", 1, (0, 25, 240, 35)
            ),
        ),
        warnings=(),
    )
    draft = extract_observations(result)
    assert draft.rows[0].subject_external_id == "SYN-ROW-002"
    assert draft.rows[0].validation_state == "needs_review"
    assert (
        "report_context_subject_external_id_conflict"
        in draft.rows[0].issues
    )


def _source_ref() -> RuleSourceRef:
    return RuleSourceRef(
        anchor_key="synthetic",
        quote="Synthetic source rule.",
        locator="synthetic",
    )


def test_unknown_exception_keeps_rule_unknown():
    node = RuleNode(
        node_key="R-UNKNOWN-EXCEPTION",
        summary="Synthetic exception rule",
        trigger=RuleCondition(
            op="eq",
            left=RuleOperand(kind="fact_ref", fact_key="triggered"),
            right=RuleOperand(kind="literal", value=True),
        ),
        exceptions=[
            RuleException(
                exception_key="EX1",
                description="Unknown exception",
                condition=RuleCondition(
                    op="eq",
                    left=RuleOperand(
                        kind="fact_ref", fact_key="exception_fact"
                    ),
                    right=RuleOperand(kind="literal", value=True),
                ),
                source_refs=[_source_ref()],
            )
        ],
        source_refs=[_source_ref()],
    )
    result = evaluate_node(node, {"triggered": FactValue(value=True)})
    assert result.status == "unknown"


def test_missing_dimensioned_unit_stays_unknown():
    condition = RuleCondition(
        op="ge",
        left=RuleOperand(kind="fact_ref", fact_key="value"),
        right=RuleOperand(kind="literal", value="10", unit="mg"),
    )
    result = evaluate_condition(
        condition, {"value": FactValue(value="11")}
    )
    assert result.result == "unknown"


def test_ordinary_chinese_requirement_is_preserved_for_review():
    anchor = ParsedAnchor(
        anchor_type="plain_text",
        logical_node_id="p1",
        text="严重不良事件必须在获知后24小时内完成上报。",
        ordinal=1,
    )
    result = AnchoredRuleExtractor().extract_rules(anchors=[anchor])
    assert len(result.rules) == 1
    rule = result.rules[0]
    assert rule.semantic_status == "analysis_required"
    assert "seriousness" in rule.purpose_tags
    assert "reporting_timeliness" in rule.purpose_tags
    assert result.coverage[0].status == "analysis_required"
