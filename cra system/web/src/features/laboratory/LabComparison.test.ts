import { describe, expect, it } from "vitest";

import type { LabComparisonFieldView } from "../../api/client";
import {
  comparisonStatusLabel,
  reviewableFieldIds
} from "./review";

describe("laboratory comparison review", () => {
  it("keeps unknown and difference scopes explicit", () => {
    expect(comparisonStatusLabel("unit_review")).toBe("单位待核实");
    expect(comparisonStatusLabel("logic_difference")).toBe("范围逻辑差异");
    expect(comparisonStatusLabel("not_seen_in_export")).toBe(
      "本次导出未见"
    );
  });

  it("selects only non-agreement fields for corrective issues", () => {
    const fields = [
      { id: "agreement", result_status: "agreement" },
      { id: "difference", result_status: "value_difference" },
      { id: "unit", result_status: "unit_review" }
    ] as LabComparisonFieldView[];
    expect(reviewableFieldIds(fields)).toEqual(["difference", "unit"]);
  });
});
