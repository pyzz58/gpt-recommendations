import { useState } from "react";

import { ImportPreview } from "../features/edc/ImportPreview";
import { LabComparison } from "../features/laboratory/LabComparison";
import { RecognitionReview } from "../features/laboratory/RecognitionReview";
import { AssessmentPanel } from "../features/safety/AssessmentPanel";
import { SubjectTimeline } from "../features/subjects/SubjectTimeline";

type Props = {
  studyId: string;
  siteId: string;
};

type Tab = "subject" | "edc" | "lab" | "compare" | "safety";

const TABS: { key: Tab; label: string }[] = [
  { key: "subject", label: "患者与分层list" },
  { key: "edc", label: "EDC检验快照" },
  { key: "lab", label: "源检验读取" },
  { key: "compare", label: "核对与异常" },
  { key: "safety", label: "安全跟进" }
];

export function SubjectReviewPage({ studyId, siteId }: Props) {
  const [tab, setTab] = useState<Tab>("subject");
  return (
    <section className="workspace-module subject-review-page">
      <div className="module-heading">
        <div>
          <p className="eyebrow">逐患者核查</p>
          <h2>分层list、源文件与EDC在同一患者上下文接续</h2>
          <p>正常范围可按批简记；低可信、异常、跳过和安全问题集中展开。</p>
        </div>
      </div>
      <nav className="subject-review-tabs" aria-label="患者核查类别">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={item.key === tab ? "active" : ""}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      {tab === "subject" && (
        <SubjectTimeline studyId={studyId} siteId={siteId} />
      )}
      {tab === "edc" && (
        <ImportPreview studyId={studyId} siteId={siteId} />
      )}
      {tab === "lab" && (
        <RecognitionReview studyId={studyId} siteId={siteId} />
      )}
      {tab === "compare" && (
        <LabComparison studyId={studyId} siteId={siteId} />
      )}
      {tab === "safety" && (
        <AssessmentPanel studyId={studyId} siteId={siteId} />
      )}
    </section>
  );
}
