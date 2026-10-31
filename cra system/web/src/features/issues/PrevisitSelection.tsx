import { useEffect, useState } from "react";

import type { IssueView } from "../../api/client";

type Props = {
  issues: IssueView[];
  selectedIds: string[];
  busy: boolean;
  onSave: (issueIds: string[]) => Promise<void>;
};

export function toggleIssueSelection(
  current: string[],
  issueId: string
): string[] {
  return current.includes(issueId)
    ? current.filter((item) => item !== issueId)
    : [...current, issueId];
}

export function PrevisitSelection({
  issues,
  selectedIds,
  busy,
  onSave
}: Props) {
  const [localSelection, setLocalSelection] = useState<string[]>(selectedIds);

  useEffect(() => {
    setLocalSelection(selectedIds);
  }, [selectedIds]);

  function toggle(issueId: string) {
    setLocalSelection((current) => toggleIssueSelection(current, issueId));
  }

  return (
    <section className="previsit-selection" aria-labelledby="previsit-title">
      <div className="applicable-heading">
        <div>
          <p className="eyebrow">访前选择 · 不删问题</p>
          <h3 id="previsit-title">选择本次准备沟通的遗留</h3>
        </div>
        <span className="status-chip muted">
          已选 {localSelection.length} / {issues.length}
        </span>
      </div>
      <p>
        勾选只保存准备集合；全部遗留仍会保留在本次监查和后续跟进中。最终信件模板不在
        W06 生成。
      </p>
      <div className="previsit-options">
        {issues.map((issue) => (
          <label key={issue.id}>
            <input
              type="checkbox"
              checked={localSelection.includes(issue.id)}
              onChange={() => toggle(issue.id)}
              disabled={busy}
            />
            <span>
              <strong>{issue.issue_number}</strong>
              <small>
                {issue.aggregate_status} ·{" "}
                {issue.original_finding ?? "原问题未载明"}
              </small>
            </span>
          </label>
        ))}
      </div>
      <button
        className="secondary-button"
        type="button"
        disabled={busy}
        onClick={() => void onSave(localSelection)}
      >
        保存访前选择
      </button>
    </section>
  );
}
