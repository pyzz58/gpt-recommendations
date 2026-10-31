import { describe, expect, it } from "vitest";

import { carryoverStatusLabel } from "./CarryoverReview";
import { toggleIssueSelection } from "./PrevisitSelection";

describe("carryover workbench semantics", () => {
  it("adds and removes a previsit selection without changing the full list", () => {
    const allIssueIds = ["issue-1", "issue-2", "issue-3"];
    const selected = toggleIssueSelection(
      toggleIssueSelection([], "issue-1"),
      "issue-3"
    );
    expect(selected).toEqual(["issue-1", "issue-3"]);
    expect(allIssueIds).toEqual(["issue-1", "issue-2", "issue-3"]);
    expect(toggleIssueSelection(selected, "issue-1")).toEqual(["issue-3"]);
  });

  it("distinguishes partial completion from a completed issue", () => {
    expect(carryoverStatusLabel("in_progress")).toBe("部分完成");
    expect(carryoverStatusLabel("completed")).toBe("CRA确认完成");
    expect(carryoverStatusLabel("incomplete")).toBe("尚未定义行动");
  });
});
