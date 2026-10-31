import { type FormEvent, useState } from "react";

import type { RuleVersionDetailView } from "../../api/client";

type Props = {
  detail: RuleVersionDetailView;
  busy: boolean;
  onConfirm: (operations: Record<string, unknown>[]) => Promise<void>;
};

export function RuleConfirmation({ detail, busy, onConfirm }: Props) {
  const [summary, setSummary] = useState(detail.tree.summary);
  const [followUp, setFollowUp] = useState(detail.tree.follow_up ?? "");
  const [completion, setCompletion] = useState(detail.tree.completion ?? "");
  const [newChild, setNewChild] = useState("");
  const [newException, setNewException] = useState("");
  const [removedChildren, setRemovedChildren] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const isConfirmed = detail.version.state === "confirmed";
  const firstSource = detail.tree.source_refs[0];

  function toggleRemoval(nodeKey: string) {
    setRemovedChildren((current) =>
      current.includes(nodeKey)
        ? current.filter((key) => key !== nodeKey)
        : [...current, nodeKey]
    );
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const operations: Record<string, unknown>[] = [];
    if (
      summary !== detail.tree.summary ||
      followUp !== (detail.tree.follow_up ?? "") ||
      completion !== (detail.tree.completion ?? "")
    ) {
      operations.push({
        op: "edit_fields",
        summary: summary.trim(),
        follow_up: followUp.trim(),
        completion: completion.trim()
      });
    }
    if (newChild.trim()) {
      operations.push({
        op: "add_child",
        child: {
          node_key: `${detail.rule_key}-USER-${crypto.randomUUID().slice(0, 8)}`,
          summary: newChild.trim(),
          children: [],
          source_refs: [firstSource]
        }
      });
    }
    for (const childKey of removedChildren) {
      operations.push({ op: "remove_child", child_key: childKey });
    }
    if (newException.trim()) {
      operations.push({
        op: "add_exception",
        exception: {
          exception_key: `USER-${crypto.randomUUID().slice(0, 8)}`,
          description: newException.trim(),
          condition: null,
          source_refs: [firstSource]
        }
      });
    }
    if (operations.length === 0) {
      setError("没有实际修改。可修正字段、增加子项/例外，或勾选删除子项。");
      return;
    }
    try {
      await onConfirm(operations);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "规则确认失败");
    }
  }

  return (
    <form className="rule-confirmation" onSubmit={(event) => void submit(event)}>
      <div className="confirmation-heading">
        <div>
          <p className="eyebrow">用户确认增删改</p>
          <h4>{isConfirmed ? "继续修订" : "确认候选规则"}</h4>
        </div>
        <span className={`status-chip ${isConfirmed ? "" : "muted"}`}>
          {isConfirmed ? "当前已确认" : "尚未确认"}
        </span>
      </div>
      <p className="confirmation-note">
        每次确认生成新版本；原提取和旧版本保留。新子项和例外会绑定当前规则已有的原文依据，
        无依据内容不能伪装为确定性规则。
      </p>
      <label>
        关键要求摘要
        <textarea value={summary} onChange={(event) => setSummary(event.target.value)} />
      </label>
      <label>
        后续动作
        <textarea value={followUp} onChange={(event) => setFollowUp(event.target.value)} />
      </label>
      <label>
        完成方式
        <textarea
          value={completion}
          onChange={(event) => setCompletion(event.target.value)}
        />
      </label>
      <label>
        新增子项
        <input
          value={newChild}
          onChange={(event) => setNewChild(event.target.value)}
          placeholder="例如：核对签署日期与筛选日期"
        />
      </label>
      <label>
        新增例外
        <input
          value={newException}
          onChange={(event) => setNewException(event.target.value)}
          placeholder="仅保存为待人工分析，不自动推定适用"
        />
      </label>
      {(detail.tree.children ?? []).length > 0 && (
        <fieldset className="remove-children">
          <legend>移除本次任务中的子项（不删除原文条款）</legend>
          {(detail.tree.children ?? []).map((child) => (
            <label key={child.node_key}>
              <input
                type="checkbox"
                checked={removedChildren.includes(child.node_key)}
                onChange={() => toggleRemoval(child.node_key)}
              />
              {child.summary}
            </label>
          ))}
        </fieldset>
      )}
      {error && <p className="inline-error" role="alert">{error}</p>}
      <button className="primary-button" type="submit" disabled={busy}>
        {busy ? "正在保存新版本…" : "确认并生成新版本"}
      </button>
    </form>
  );
}
