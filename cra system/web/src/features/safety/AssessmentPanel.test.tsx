import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AssessmentPanel } from "./AssessmentPanel";

describe("AssessmentPanel", () => {
  it("shows separate safety dimensions and an explicit non-conclusion boundary", () => {
    const markup = renderToStaticMarkup(
      <AssessmentPanel
        studyId="00000000-0000-0000-0000-000000000001"
        siteId="00000000-0000-0000-0000-000000000002"
      />
    );
    expect(markup).toContain("AE、SAE、PD及特殊标准分开核查");
    expect(markup).toContain("模型只可在允许模板和证据ID内解释");
    expect(markup).toContain("严重性/SAE");
    expect(markup).toContain("相关性");
    expect(markup).toContain("预期性");
    expect(markup).toContain("及时报告");
    expect(markup).not.toContain("clinical_safe=true");
  });
});
