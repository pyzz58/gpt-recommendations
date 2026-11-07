import { describe, expect, it } from "vitest";

import type { LabComparisonFieldView } from "../../api/client";
import {
  comparisonStatusLabel,
  imageHighlightStyle,
  isPdfFileFormat,
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

  it("renders scanned and text PDFs in the PDF source viewer", () => {
    expect(isPdfFileFormat("text_pdf")).toBe(true);
    expect(isPdfFileFormat("scanned_pdf")).toBe(true);
    expect(isPdfFileFormat("clear_printed_jpeg")).toBe(false);
  });

  it("keeps image field coordinates reviewable at display size", () => {
    expect(
      imageHighlightStyle([100, 50, 300, 150], {
        width: 1000,
        height: 500
      })
    ).toEqual({
      left: "10%",
      top: "10%",
      width: "20%",
      height: "20%"
    });
    expect(imageHighlightStyle([300, 50, 100, 150], null)).toBeNull();
  });
});
