"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createAuditReview,
  fetchAuditWorkspace,
  notifyProjectChanged,
  resolveAuditFinding,
  runAuditEvaluation,
} from "@/lib/api";
import type {
  AuditEvaluationView,
  AuditFindingView,
  AuditRunView,
  AuditTargetType,
  AuditTargetView,
  AuditWorkspaceView,
} from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatDate,
} from "@/components/ui";

const targetLabels: Record<AuditTargetType, string> = {
  claim_version: "证据断言",
  analysis_run: "统计分析",
  external_deliverable: "外部交付",
};

const severityLabels: Record<AuditFindingView["severity"], string> = {
  critical: "严重 · 阻断",
  major: "主要 · 需修改",
  minor: "次要",
};

const producerRoles = Array.from({ length: 24 }, (_, index) =>
  `A${String(index + 1).padStart(2, "0")}`,
);

export default function AuditsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [workspace, setWorkspace] = useState<AuditWorkspaceView | null>(null);
  const [selectedTargetKey, setSelectedTargetKey] = useState("");
  const [reviewerRole, setReviewerRole] = useState<"A25" | "A26">("A25");
  const [producerRole, setProducerRole] = useState("A02");
  const [resolutionDrafts, setResolutionDrafts] = useState<Record<string, string>>(
    {},
  );
  const [latestEvaluation, setLatestEvaluation] =
    useState<AuditEvaluationView | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const next = await fetchAuditWorkspace(projectId, signal);
        setWorkspace(next);
        setLatestEvaluation(next.evaluations[0] ?? null);
        setSelectedTargetKey((current) => {
          if (
            current &&
            next.targets.some((target) => targetKey(target) === current)
          ) {
            return current;
          }
          const first = next.targets[0];
          return first ? targetKey(first) : "";
        });
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取独立审计");
        }
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [load]);

  const selectedTarget =
    workspace?.targets.find((target) => targetKey(target) === selectedTargetKey) ??
    null;

  async function runAction(action: () => Promise<unknown>, message: string, key: string) {
    setBusy(key);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "审计操作失败");
    } finally {
      setBusy("");
    }
  }

  async function startReview() {
    if (!selectedTarget) return;
    await runAction(
      () =>
        createAuditReview(
          projectId,
          {
            target_type: selectedTarget.target_type,
            target_id: selectedTarget.target_id,
            reviewer_role: reviewerRole,
            producer_role: producerRole || null,
          },
          crypto.randomUUID(),
        ),
      "审计结论和历史输入快照已保存。",
      "review",
    );
  }

  async function disposeFinding(
    review: AuditRunView,
    finding: AuditFindingView,
    status: "resolved" | "accepted_risk",
  ) {
    const resolution = (resolutionDrafts[finding.id] ?? "").trim();
    if (!resolution) {
      setError("记录 finding 处置前必须填写理由。");
      return;
    }
    await runAction(
      () =>
        resolveAuditFinding(projectId, review.id, finding.id, {
          status,
          resolution,
        }),
      status === "resolved" ? "finding 已标记为解决。" : "finding 已记录为接受风险。",
      finding.id,
    );
    setResolutionDrafts((current) => ({ ...current, [finding.id]: "" }));
  }

  async function evaluate() {
    setBusy("evaluation");
    setError("");
    setNotice("");
    try {
      const result = await runAuditEvaluation(projectId);
      setLatestEvaluation(result);
      setNotice("合成规则回归已运行并保存结果。");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "合成评测失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="pageStack">
      <section className="surface externalIntro">
        <div>
          <p className="eyebrow">W17 · INDEPENDENT REVIEW</p>
          <h2>独立审计与反证回流</h2>
          <p>
            A25 检查流程、引用与交付完整性；A26 单独核查反证、过度声明和方法边界。
            critical 或 major 会阻断下游，结论、输入快照和处置历史分别保留。
          </p>
        </div>
        <div className="warningBanner">
          确定性规则审计；不是真人专家、非 mock 独立 Agent 或完整科学验证。
        </div>
      </section>

      {loading && <LoadingPanel />}
      {!loading && error && (
        <ErrorPanel message={error} onRetry={() => void load()} />
      )}
      {!loading && notice && <p className="noticeBanner">{notice}</p>}

      {!loading && workspace && (
        <>
          <section className="surface">
            <SectionHeader
              eyebrow="AUDIT SCOPE"
              title="选择审计对象"
              aside={
                <span className="mutedText">
                  {workspace.targets.length} 个可审计对象
                </span>
              }
            />
            {workspace.targets.length === 0 ? (
              <EmptyState title="当前项目还没有可审计对象">
                <p>
                  先在证据、统计或外部合作页面形成断言、分析或交付记录，再运行独立审计。
                </p>
              </EmptyState>
            ) : (
              <div className="auditControlGrid">
                <label>
                  审计目标
                  <select
                    value={selectedTargetKey}
                    onChange={(event) => setSelectedTargetKey(event.target.value)}
                  >
                    {workspace.targets.map((target) => (
                      <option value={targetKey(target)} key={targetKey(target)}>
                        {targetLabels[target.target_type]} · {target.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  独立岗位
                  <select
                    value={reviewerRole}
                    onChange={(event) =>
                      setReviewerRole(event.target.value as "A25" | "A26")
                    }
                  >
                    <option value="A25">A25 · 质量与流程</option>
                    <option value="A26">A26 · 反证与科学审计</option>
                  </select>
                </label>
                <label>
                  原产出岗位
                  <select
                    value={producerRole}
                    onChange={(event) => setProducerRole(event.target.value)}
                  >
                    <option value="">未指定</option>
                    {producerRoles.map((role) => (
                      <option value={role} key={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )}
            {selectedTarget && (
              <div className="auditTargetCard">
                <div className="cardTopline">
                  <StatusPill value={selectedTarget.target_type} />
                  <span>{targetLabels[selectedTarget.target_type]}</span>
                </div>
                <h3>{selectedTarget.label}</h3>
                <p>{selectedTarget.detail}</p>
                <small>target_id · {selectedTarget.target_id}</small>
                <button
                  className="button primary"
                  disabled={busy !== ""}
                  onClick={() => void startReview()}
                  type="button"
                >
                  {busy === "review" ? "正在保存审计…" : `运行 ${reviewerRole} 审计`}
                </button>
              </div>
            )}
          </section>

          <section className="surface">
            <SectionHeader
              eyebrow="IMMUTABLE REVIEW HISTORY"
              title="审计结论与缺陷"
              aside={<span className="mutedText">处置不回写原结论</span>}
            />
            {workspace.reviews.length === 0 ? (
              <EmptyState title="还没有审计记录">
                <p>选择目标与独立岗位后运行审计。</p>
              </EmptyState>
            ) : (
              <div className="auditReviewList">
                {workspace.reviews.map((review) => (
                  <article className="externalRecordCard auditReviewCard" key={review.id}>
                    <div className="cardTopline">
                      <StatusPill value={review.state} />
                      <span>
                        {review.reviewer_role} · v{review.review_version}
                      </span>
                    </div>
                    <h3>{targetLabels[review.target_type]}</h3>
                    <p>{review.summary}</p>
                    <div className="auditHashBlock">
                      <span>目标 {shortHash(review.target_sha256)}</span>
                      <span>输入 {shortHash(review.input_sha256)}</span>
                      <span>产出 {review.producer_role ?? "未指定"}</span>
                      <span>{formatDate(review.created_at)}</span>
                    </div>
                    {review.downstream_blocked && (
                      <div className="auditBlocked">
                        下游已阻断。必须处理缺陷或保留新的复审记录。
                      </div>
                    )}
                    {review.findings.length === 0 ? (
                      <p className="auditPassed">未命中当前确定性规则。</p>
                    ) : (
                      <div className="auditFindingList">
                        {review.findings.map((finding) => (
                          <div
                            className={`auditFinding ${finding.severity}`}
                            key={finding.id}
                          >
                            <div className="cardTopline">
                              <strong>{finding.code}</strong>
                              <span>{severityLabels[finding.severity]}</span>
                            </div>
                            <p>{finding.message}</p>
                            {finding.evidence_refs.length > 0 && (
                              <small>
                                证据引用 · {finding.evidence_refs.join(" · ")}
                              </small>
                            )}
                            {finding.status === "open" ? (
                              <div className="auditDisposition">
                                <input
                                  aria-label={`${finding.code} 处置理由`}
                                  placeholder="说明补证、返工或接受风险的理由"
                                  value={resolutionDrafts[finding.id] ?? ""}
                                  onChange={(event) =>
                                    setResolutionDrafts((current) => ({
                                      ...current,
                                      [finding.id]: event.target.value,
                                    }))
                                  }
                                />
                                <button
                                  className="button secondary"
                                  disabled={busy !== ""}
                                  onClick={() =>
                                    void disposeFinding(review, finding, "resolved")
                                  }
                                  type="button"
                                >
                                  标记解决
                                </button>
                                <button
                                  className="button danger"
                                  disabled={busy !== ""}
                                  onClick={() =>
                                    void disposeFinding(
                                      review,
                                      finding,
                                      "accepted_risk",
                                    )
                                  }
                                  type="button"
                                >
                                  接受风险
                                </button>
                              </div>
                            ) : (
                              <div className="auditDispositionRecord">
                                <StatusPill value={finding.status} />
                                <span>{finding.resolution}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="surface">
            <SectionHeader
              eyebrow="SYNTHETIC REGRESSION"
              title="规则回归评测"
              aside={
                <button
                  className="button secondary"
                  disabled={busy !== ""}
                  onClick={() => void evaluate()}
                  type="button"
                >
                  {busy === "evaluation" ? "正在评测…" : "运行合成评测"}
                </button>
              }
            />
            {latestEvaluation ? (
              <EvaluationPanel evaluation={latestEvaluation} />
            ) : (
              <EmptyState title="尚未运行评测">
                <p>评测只验证 7 个合成规则案例，不代表医学或药学能力认证。</p>
              </EmptyState>
            )}
          </section>

          <section className="surface">
            <SectionHeader eyebrow="LIMITATIONS" title="当前能力边界" />
            <ul className="limitationList">
              {workspace.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
              <li>
                规则命中不等于科学结论正确；未命中也不能被表述为已完成专家审查。
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

function EvaluationPanel({ evaluation }: { evaluation: AuditEvaluationView }) {
  return (
    <div>
      <div className="metricGrid auditMetrics">
        <Metric label="案例" value={evaluation.metrics.cases} />
        <Metric label="TP" value={evaluation.metrics.true_positives} />
        <Metric label="FP" value={evaluation.metrics.false_positives} />
        <Metric label="FN" value={evaluation.metrics.false_negatives} />
        <Metric
          label="Precision"
          value={`${(evaluation.metrics.precision * 100).toFixed(1)}%`}
        />
        <Metric
          label="Recall"
          value={`${(evaluation.metrics.recall * 100).toFixed(1)}%`}
        />
      </div>
      <p className="auditFixtureMeta">
        {evaluation.fixture_name} · SHA {shortHash(evaluation.fixture_sha256)} ·{" "}
        {formatDate(evaluation.created_at)}
      </p>
      <div className="auditCaseList">
        {evaluation.case_results.map((item) => (
          <div className="auditCaseRow" key={item.case_id}>
            <strong>{item.case_id}</strong>
            <span>{item.reviewer_role}</span>
            <code>{item.predicted_codes.join(", ") || "no findings"}</code>
            <small>
              missed {item.missed_codes.join(", ") || "none"} · unexpected{" "}
              {item.unexpected_codes.join(", ") || "none"}
            </small>
          </div>
        ))}
      </div>
      <div className="warningBanner">
        {evaluation.limitations.join("；")}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function targetKey(target: AuditTargetView): string {
  return `${target.target_type}:${target.target_id}`;
}

function shortHash(value: string): string {
  return value.length > 16 ? `${value.slice(0, 10)}…${value.slice(-6)}` : value;
}
