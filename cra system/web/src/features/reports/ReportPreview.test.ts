import { describe, expect, it } from "vitest";

import {
  defaultTemplateMapping,
  snapshotStatusLabel
} from "./ReportPreview";

describe("report output contracts", () => {
  it("keeps letter selection separate from full report loops", () => {
    const letter = defaultTemplateMapping("letter") as {
      docx: { loops: Record<string, string> };
    };
    const report = defaultTemplateMapping("report") as {
      docx: { loops: Record<string, string> };
    };
    expect(letter.docx.loops).toEqual({ letter_issues: "letter_issues" });
    expect(report.docx.loops).toEqual({
      prior_issues: "prior_issues",
      current_findings: "current_findings"
    });
  });

  it("does not conflate snapshot, issuance and export", () => {
    expect(snapshotStatusLabel("prepared")).toBe("已固定快照");
    expect(snapshotStatusLabel("issued")).toBe("已签发");
  });
});
