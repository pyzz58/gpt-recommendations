"use client";

import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  fetchOpportunities,
  fetchOverview,
  fetchPlans,
  fetchProjectWorkflows,
  notifyProjectChanged,
  selectOpportunity,
  createWorkflowStagePlan,
} from "@/lib/api";
import type { WorkflowDescriptor } from "@/lib/api";
import type { OpportunityView } from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  StatusPill,
  formatDate,
  trackLabel,
} from "@/components/ui";

const gapLabels: Record<string, string> = {
  science: "科学",
  regulatory: "注册",
  ip: "专利",
  manufacturing: "制造",
  commercial: "商业",
};

export default function OpportunitiesPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const [opportunities, setOpportunities] = useState<OpportunityView[]>([]);
  const [selectionDecisionId, setSelectionDecisionId] = useState<string | null>(
    null,
  );
  const [hasPlan, setHasPlan] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowDescriptor[]>([]);
  const [selectedForDecision, setSelectedForDecision] =
    useState<OpportunityView | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("");
  const [scope, setScope] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [creatingPlan, setCreatingPlan] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [nextOpportunities, overview, plans, nextWorkflows] = await Promise.all([
        fetchOpportunities(projectId, signal),
        fetchOverview(projectId, signal),
        fetchPlans(projectId, signal),
        fetchProjectWorkflows(projectId, signal),
      ]);
      setOpportunities(nextOpportunities);
      setWorkflows(nextWorkflows);
      setSelectionDecisionId(overview.current_selection_decision_id);
      setHasPlan(
        Boolean(
          overview.current_selection_decision_id &&
            plans.some(
              (plan) =>
                plan.source_decision_id ===
                overview.current_selection_decision_id,
            ),
        ),
      );
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取候选方向");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [load]);

  async function confirmSelection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedForDecision || !reason.trim() || !scope.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await selectOpportunity(
        projectId,
        selectedForDecision.id,
        selectedForDecision.revision,
        reason.trim(),
        scope.trim(),
        crypto.randomUUID(),
      );
      setSelectedForDecision(null);
      setReason("");
      setScope("");
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法保存选择");
    } finally {
      setSubmitting(false);
    }
  }

  async function createStarterPlan() {
    const selected = opportunities.find((item) => item.status === "selected");
    if (!selected || !selectionDecisionId) return;
    const workflow = workflows.find(
      (item) => item.definition.track === selected.card.track,
    );
    const firstStage = workflow?.definition.stages[0];
    if (!workflow || !firstStage) {
      setError("当前方向没有可加载的专业流程模板");
      return;
    }
    setCreatingPlan(true);
    setError("");
    try {
      await createWorkflowStagePlan(
        projectId,
        workflow.definition.track,
        firstStage.stage_id,
        selectionDecisionId,
        crypto.randomUUID(),
      );
      notifyProjectChanged();
      router.push(`/projects/${projectId}/tasks`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法生成计划草案");
      setCreatingPlan(false);
    }
  }

  if (loading) return <LoadingPanel />;
  if (error && opportunities.length === 0) {
    return <ErrorPanel message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="pageStack">
      <section className="comparisonIntro">
        <div>
          <p className="eyebrow">OPPORTUNITY COMPARISON</p>
          <h2>分维度比较，不生成隐藏的总分</h2>
          <p>
            科学、注册、专利、制造和商业缺口分别呈现。主观概率与未知金额保持醒目标记，
            不能作为经验成功率或真实报价。
          </p>
        </div>
        <div className="introActions">
          <span className="largeCount">{opportunities.length} 个候选</span>
          {selectionDecisionId && !hasPlan && (
            <button
              type="button"
              className="button primary"
              onClick={() => void createStarterPlan()}
              disabled={creatingPlan}
            >
              {creatingPlan ? "正在生成…" : "生成首轮核查草案"}
            </button>
          )}
        </div>
      </section>

      {error && <ErrorPanel message={error} />}

      {opportunities.length === 0 ? (
        <EmptyState title="尚无候选方向">
          <p>
            当前界面不会自动生成示例候选。候选卡必须由后续有据可查的岗位交付创建。
          </p>
        </EmptyState>
      ) : (
        <section className="opportunityGrid">
          {opportunities.map((opportunity) => {
            const expandedCard = expanded === opportunity.id;
            return (
              <article
                className={`opportunityCard ${
                  opportunity.status === "selected" ? "chosen" : ""
                }`}
                key={opportunity.id}
              >
                <div className="opportunityTop">
                  <span className="trackLabel">
                    {trackLabel(opportunity.card.track)}
                  </span>
                  <StatusPill value={opportunity.status} />
                </div>
                <h3>{opportunity.title}</h3>
                <p className="useCase">{opportunity.card.proposed_use}</p>

                <div className="dimensionGrid">
                  {Object.entries(gapLabels).map(([key, label]) => {
                    const gaps = opportunity.card.gaps[key] ?? [];
                    return (
                      <div key={key}>
                        <span>{label}</span>
                        <p>{gaps[0] ?? "未记录明确缺口"}</p>
                      </div>
                    );
                  })}
                </div>

                <div className="estimateRow">
                  <div>
                    <span>下一验证概率</span>
                    <strong>
                      {formatProbability(opportunity.card.probabilities[0])}
                    </strong>
                    <small>
                      {probabilityMethodLabel(
                        opportunity.card.probabilities[0]?.method,
                      )}
                    </small>
                  </div>
                  <div>
                    <span>阶段成本</span>
                    <strong>{formatCost(opportunity.card.costs[0])}</strong>
                    <small>
                      {opportunity.card.costs[0]?.line_items[0]?.source_type ??
                        "unknown"}
                    </small>
                  </div>
                </div>

                <p className="changeTrigger">
                  <strong>重评条件：</strong> {opportunity.card.change_trigger}
                </p>

                {expandedCard && (
                  <div className="opportunityDetail">
                    <h4>下一项验证</h4>
                    <p>{opportunity.card.next_validation.objective}</p>
                    <h4>关键限制</h4>
                    <ul>
                      {opportunity.card.limitations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                    <p className="mutedText">
                      证据截止 {formatDate(opportunity.card.evidence_cutoff)} ·
                      版本 V{opportunity.current_version}
                    </p>
                  </div>
                )}

                <div className="cardActions">
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() =>
                      setExpanded(expandedCard ? null : opportunity.id)
                    }
                  >
                    {expandedCard ? "收起详情" : "查看限制与验证"}
                  </button>
                  {opportunity.status !== "selected" && (
                    <button
                      type="button"
                      className="button primary"
                      onClick={() => setSelectedForDecision(opportunity)}
                    >
                      选择此方向
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      )}

      <p className="boundaryNote">
        选择操作只保存用户决定和项目事件，不会自动创建计划、派工、发送邮件、采购或委托实验。
      </p>

      {selectedForDecision && (
        <div className="dialogBackdrop">
          <section className="dialogCard" role="dialog" aria-modal="true">
            <div className="dialogHeading">
              <div>
                <p className="eyebrow">USER DECISION</p>
                <h2>选择研发方向</h2>
              </div>
              <button
                className="iconButton"
                type="button"
                aria-label="关闭"
                onClick={() => setSelectedForDecision(null)}
              >
                ×
              </button>
            </div>
            <p className="dialogLead">{selectedForDecision.title}</p>
            <form
              className="formStack"
              onSubmit={(event) => void confirmSelection(event)}
            >
              <label>
                选择理由
                <textarea
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  rows={3}
                  required
                  placeholder="说明哪项证据或资源约束改变了判断。"
                />
              </label>
              <label>
                本次选择范围
                <textarea
                  value={scope}
                  onChange={(event) => setScope(event.target.value)}
                  rows={3}
                  required
                  placeholder="例如：只做桌面补证，不授权外部费用。"
                />
              </label>
              <div className="warningBanner">
                当前对话框未附加证据版本。若没有已保存证据，选择理由必须明确说明限制。
              </div>
              <button className="button primary" type="submit" disabled={submitting}>
                {submitting ? "正在保存决定…" : "确认并记录选择"}
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

function formatProbability(
  value: OpportunityView["card"]["probabilities"][number] | undefined,
): string {
  if (!value || value.method === "unknown") return "暂不可估计";
  if (value.lower === null || value.upper === null) return "未知";
  return `${Math.round(value.lower * 100)}–${Math.round(value.upper * 100)}%`;
}

function probabilityMethodLabel(method: string | undefined): string {
  return (
    {
      empirical: "经验区间（须核查基准）",
      validated_model: "经验证模型",
      subjective_scenario: "主观情景，未校准",
      unknown: "证据不足",
    }[method ?? "unknown"] ?? "未知"
  );
}

function formatCost(
  value: OpportunityView["card"]["costs"][number] | undefined,
): string {
  if (!value) return "未知";
  const [lower, upper] = value.total_range;
  if (lower === null || upper === null) return "金额未知";
  return `${value.currency} ${lower.toLocaleString("zh-CN")}–${upper.toLocaleString(
    "zh-CN",
  )}`;
}
