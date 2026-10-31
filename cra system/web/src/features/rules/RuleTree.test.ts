import { describe, expect, it } from "vitest";

import type { RuleConditionView } from "../../api/client";
import { conditionLabel } from "./RuleTree";

describe("rule condition labels", () => {
  it("keeps conjunction and negation explicit", () => {
    const condition = {
      op: "all",
      children: [
        {
          op: "eq",
          left: { kind: "fact_ref", fact_key: "consent_given" },
          right: { kind: "literal", value: false }
        },
        {
          op: "not",
          child: {
            op: "present",
            fact_key: "waiver"
          }
        }
      ]
    } as RuleConditionView;
    expect(conditionLabel(condition)).toContain("且");
    expect(conditionLabel(condition)).toContain("非");
    expect(conditionLabel(condition)).toContain("consent_given");
  });

  it("renders date interval boundaries without guessing", () => {
    const condition = {
      op: "date_interval",
      fact_key: "visit_date",
      anchor_fact_key: "consent_date",
      min_days: -3,
      max_days: 3
    } as RuleConditionView;
    expect(conditionLabel(condition)).toContain("visit_date");
    expect(conditionLabel(condition)).toContain("-3…3");
  });

  it("keeps unstructured conditions analysis-required", () => {
    expect(conditionLabel(null)).toContain("人工分析");
  });
});
