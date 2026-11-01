import { useEffect, useState } from "react";

import {
  type HandoverSummaryView,
  getHandoverSummary
} from "../api/client";
import { StageChecklist } from "../features/monitoring/StageChecklist";
import { ReportPreview } from "../features/reports/ReportPreview";

type Props = {
  studyId: string;
  siteId: string;
  visitId: string;
};

export function HandoverPage({ studyId, siteId, visitId }: Props) {
  const [summary, setSummary] = useState<HandoverSummaryView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHandoverSummary(visitId)
      .then(setSummary)
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "交接摘要读取失败")
      );
  }, [visitId]);

  return (
    <section className="workspace-module handover-page">
      <section className="handover-summary">
        <p className="eyebrow">简洁交接</p>
        <h2>无遗留简述；有遗留交代现状和后续</h2>
        {error && <div className="notice notice-error">{error}</div>}
        {summary ? (
          <>
            <p className="handover-copy">{summary.summary}</p>
            {summary.issues.length > 0 && (
              <ol>
                {summary.issues.map((issue) => (
                  <li key={issue.id}>
                    <strong>{issue.issue_number}</strong>
                    {" · "}
                    {issue.known_progress ?? "进展待复核"}
                    <small>后续：{issue.next_steps.join("；")}</small>
                  </li>
                ))}
              </ol>
            )}
            <p className="security-note">{summary.limitation}</p>
          </>
        ) : (
          !error && <p>正在读取原问题和阶段清单…</p>
        )}
      </section>
      <StageChecklist studyId={studyId} siteId={siteId} />
      <ReportPreview studyId={studyId} siteId={siteId} />
    </section>
  );
}
