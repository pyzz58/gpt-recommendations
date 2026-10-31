import { describe, expect, it } from "vitest";

import {
  acquisitionLabel,
  applicabilityLabel,
  verificationLabel
} from "./DirectoryReview";

describe("site-file status labels", () => {
  it("keeps applicability separate from possession and qualification", () => {
    expect(applicabilityLabel("required")).toBe("应有");
    expect(acquisitionLabel("not_seen")).toBe("未见");
    expect(verificationLabel("pending")).toBe("待核实");
    expect(verificationLabel("qualified")).toBe("已核实合格");
  });
});
