import { describe, expect, it } from "vitest";

import { stageStatusLabel } from "./StageChecklist";

describe("stage checklist status", () => {
  it("does not turn unknown into confirmed", () => {
    expect(stageStatusLabel("unknown")).toBe("未知");
    expect(stageStatusLabel("confirmed")).toBe("已确认");
  });
});
