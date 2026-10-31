"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  activatePlan,
  dispatchPlan,
  executePlan,
  fetchPlans,
  fetchTasks,
  notifyProjectChanged,
  pausePlan,
  resumePlan,
  reviewTask,
  stopPlan,
} from "@/lib/api";
import type {
  PlanNodeView,
  PlanView,
  ReviewDecision,
  TaskView,
} from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatDate,
  stateLabel,
} from "@/components/ui";

const columns = [
  {
    key: "work",
    title: "工作队列",
    states: ["draft", "needs_input", "ready", "queued", "running"],
  },
  {
    key: "review",
    title: "待验收 / 重做",
    states: ["submitted", "rework"],
  },
  {
    key: "waiting",
    title: "等待与暂停",
    states: ["waiting_external", "paused"],
  },
  {
    key: "closed",
    title: "已接受 / 结束",
    states: ["accepted", "failed", "cancelled"],
  },
];

export default function TasksPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [tasks, setTasks] = useState<TaskView[]>([]);
  const [plans, setPlans] = useState<PlanView[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [reviewNode, setReviewNode] = useState<PlanNodeView | null>(null);
  const [reviewDecision, setReviewDecision] =
    useState<ReviewDecision>("accepted");
  const [reviewerRole, setReviewerRole] = useState("A25");
  const [reviewSummary, setReviewSummary] = useState("");
  const [criticalFinding, setCriticalFinding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextTasks, nextPlans] = await Promise.all([
          fetchTasks(projectId, signal),
          fetchPlans(projectId, signal),
        ]);
        setTasks(nextTasks);
        setPlans(nextPlans);
        setSelectedPlanId((current) => {
          if (current && nextPlans.some((plan) => plan.id === current)) {
            return current;
          }
          return (
            nextPlans.find((plan) =>
              ["active", "paused", "draft"].includes(plan.status),
            )?.id ??
            nextPlans[0]?.id ??
            null
          );
        });
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取任务");
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

  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? null;
  const selectedPlan = plans.find((plan) => plan.id === selectedPlanId) ?? null;
  const dependencyNames = useMemo(
    () =>
      new Map(
        tasks.map((task) => [
          task.id,
          `${task.assignee_role} · ${task.goal.slice(0, 28)}`,
        ]),
      ),
    [tasks],
  );

  async function perform(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "计划操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function activateCurrentPlan() {
    if (!selectedPlan) return;
    await perform(
      () =>
        activatePlan(projectId, selectedPlan.id, selectedPlan.revision),
      "计划已激活。下一步是派发就绪任务。",
    );
  }

  async function dispatchAndExecute() {
    if (!selectedPlan) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const dispatched = await dispatchPlan(
        projectId,
        selectedPlan.id,
        selectedPlan.revision,
      );
      const executed = await executePlan(projectId, selectedPlan.id);
      setNotice(
        dispatched.dispatched.length === 0 && executed.executed.length === 0
          ? "当前没有可派发或可运行的任务；审核通过后请再次派发。"
          : `已派发 ${dispatched.dispatched.length} 项，运行 ${executed.executed.length} 项 mock 任务。`,
      );
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "派工或运行失败");
    } finally {
      setBusy(false);
    }
  }

  async function pauseCurrentPlan() {
    if (!selectedPlan) return;
    const reason = window.prompt("请输入暂停原因：");
    if (!reason?.trim()) return;
    await perform(
      () =>
        pausePlan(
          projectId,
          selectedPlan.id,
          selectedPlan.revision,
          reason.trim(),
        ),
      "计划已暂停；未开始的队列被取消，已运行动作不会被假装撤回。",
    );
  }

  async function resumeCurrentPlan() {
    if (!selectedPlan) return;
    let additional = 0;
    if (selectedPlan.pause_reason === "iteration_limit") {
      const raw = window.prompt(
        `已达到返工上限。请输入明确增加的返工轮数（1–${10 - selectedPlan.max_rework_rounds}）：`,
      );
      if (raw === null) return;
      additional = Number(raw);
      if (!Number.isInteger(additional) || additional < 1) return;
    }
    await perform(
      () =>
        resumePlan(
          projectId,
          selectedPlan.id,
          selectedPlan.revision,
          additional,
        ),
      additional
        ? `计划已恢复，并显式增加 ${additional} 轮返工额度。`
        : "计划已恢复。",
    );
  }

  async function stopCurrentPlan() {
    if (!selectedPlan) return;
    const reason = window.prompt("请输入停止原因：");
    if (!reason?.trim()) return;
    await perform(
      () =>
        stopPlan(
          projectId,
          selectedPlan.id,
          selectedPlan.revision,
          reason.trim(),
        ),
      "计划已停止；未开始的工作被取消，历史记录保留。",
    );
  }

  function openReview(node: PlanNodeView) {
    setReviewNode(node);
    setReviewDecision("accepted");
    setReviewerRole(node.reviewer_roles[0] ?? "A25");
    setReviewSummary("");
    setCriticalFinding(false);
  }

  async function submitReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPlan || !reviewNode || !reviewSummary.trim()) return;
    const decision = criticalFinding ? "changes_requested" : reviewDecision;
    setBusy(true);
    setError("");
    try {
      const result = await reviewTask(
        projectId,
        reviewNode.task_id,
        {
          planId: selectedPlan.id,
          expectedRevision: reviewNode.task_revision,
          reviewerRole,
          decision,
          summary: reviewSummary.trim(),
          findings: criticalFinding
            ? [
                {
                  code: "REVIEW_CRITICAL",
                  severity: "critical",
                  message: reviewSummary.trim(),
                  evidence_refs: [],
                },
              ]
            : [],
        },
        crypto.randomUUID(),
      );
      setReviewNode(null);
      setNotice(
        `审核已记录为“${stateLabel(result.decision)}”；任务状态为“${stateLabel(
          result.task_state,
        )}”。`,
      );
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法保存审核");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingPanel />;
  if (error && tasks.length === 0 && plans.length === 0) {
    return <ErrorPanel message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="pageStack">
      <section className="taskIntro">
        <div>
          <p className="eyebrow">BOUNDED DELIVERY GRAPH</p>
          <h2>计划、依赖、执行与验收各自留痕</h2>
          <p>
            激活只确认有界结构；派发创建持久任务；mock运行由确定性AgentRunner完成；提交后仍需独立审核岗位合同记录通过。
          </p>
        </div>
        <span className="largeCount">{plans.length} 个计划版本</span>
      </section>

      {(error || notice) && (
        <div className={error ? "errorPanel" : "successPanel"}>
          {error || notice}
        </div>
      )}

      {plans.length === 0 ? (
        <EmptyState title="尚无计划">
          <p>
            先在机会比较页面选择方向，并生成首轮核查草案。计划不会自动获得外部执行授权。
          </p>
        </EmptyState>
      ) : (
        <>
          <div className="planSwitcher" role="tablist" aria-label="计划版本">
            {plans.map((plan) => (
              <button
                className={plan.id === selectedPlanId ? "planTab active" : "planTab"}
                type="button"
                key={plan.id}
                onClick={() => setSelectedPlanId(plan.id)}
              >
                <strong>V{plan.plan_version}</strong>
                <span>{stateLabel(plan.status)}</span>
              </button>
            ))}
          </div>

          {selectedPlan && (
            <section className="surface planPanel">
              <SectionHeader
                eyebrow={`PLAN V${selectedPlan.plan_version} / REV ${selectedPlan.revision}`}
                title={selectedPlan.title}
                aside={<StatusPill value={selectedPlan.status} />}
              />
              <p className="planObjective">{selectedPlan.objective}</p>
              {selectedPlan.workflow_id && (
                <p className="mutedText">
                  专业流程 {selectedPlan.workflow_id} V
                  {selectedPlan.workflow_version} · 阶段{" "}
                  {selectedPlan.stage_id} · 配置指纹{" "}
                  {selectedPlan.workflow_sha256?.slice(0, 12)}
                </p>
              )}
              {selectedPlan.pause_reason === "iteration_limit" && (
                <div className="warningBanner">
                  该计划因返工超过 {selectedPlan.max_rework_rounds} 轮而暂停。恢复必须明确增加额度。
                </div>
              )}

              <div className="planActions">
                {selectedPlan.status === "draft" && (
                  <button
                    className="button primary"
                    type="button"
                    disabled={busy}
                    onClick={() => void activateCurrentPlan()}
                  >
                    激活计划
                  </button>
                )}
                {selectedPlan.status === "active" && (
                  <>
                    <button
                      className="button primary"
                      type="button"
                      disabled={busy}
                      onClick={() => void dispatchAndExecute()}
                    >
                      派发并运行就绪任务
                    </button>
                    <button
                      className="button secondary"
                      type="button"
                      disabled={busy}
                      onClick={() => void pauseCurrentPlan()}
                    >
                      暂停
                    </button>
                  </>
                )}
                {selectedPlan.status === "paused" && (
                  <button
                    className="button primary"
                    type="button"
                    disabled={busy}
                    onClick={() => void resumeCurrentPlan()}
                  >
                    恢复计划
                  </button>
                )}
                {["draft", "active", "paused"].includes(selectedPlan.status) && (
                  <button
                    className="button danger"
                    type="button"
                    disabled={busy}
                    onClick={() => void stopCurrentPlan()}
                  >
                    停止
                  </button>
                )}
              </div>

              <div className="dagGrid">
                {selectedPlan.nodes.map((node) => (
                  <article className="dagNode" key={node.node_id}>
                    <div className="agentCardTop">
                      <span className="roleId">{node.assignee_role}</span>
                      <StatusPill value={node.task_state} />
                    </div>
                    <h3>{node.node_key}</h3>
                    <p>{node.goal}</p>
                    <div className="dagDependencies">
                      {node.dependencies.length === 0 ? (
                        <span>根节点</span>
                      ) : (
                        node.dependencies.map((dependency) => (
                          <span key={dependency}>依赖 {dependency}</span>
                        ))
                      )}
                    </div>
                    {node.task_state === "submitted" && (
                      <button
                        className="button secondary fullWidth"
                        type="button"
                        onClick={() => openReview(node)}
                      >
                        记录审核
                      </button>
                    )}
                  </article>
                ))}
              </div>

              <div className="reviewHistory">
                <h3>审核记录</h3>
                {selectedPlan.reviews.length === 0 ? (
                  <p className="mutedText">尚无审核记录。</p>
                ) : (
                  selectedPlan.reviews.map((review) => (
                    <article key={review.review_id}>
                      <div>
                        <strong>
                          #{review.review_round} · {review.reviewer_role}
                        </strong>
                        <StatusPill value={review.decision} />
                      </div>
                      <p>{review.summary}</p>
                      <small>{formatDate(review.created_at)}</small>
                    </article>
                  ))
                )}
              </div>
            </section>
          )}
        </>
      )}

      <section className="surface">
        <SectionHeader eyebrow="TASK BOARD" title="任务与依赖" />
        {tasks.length === 0 ? (
          <EmptyState title="尚无任务">
            <p>从已选择方向生成计划后，这里会显示真实任务状态。</p>
          </EmptyState>
        ) : (
          <div className="board">
            {columns.map((column) => {
              const items = tasks.filter((task) =>
                column.states.includes(task.state),
              );
              return (
                <div className="boardColumn" key={column.key}>
                  <div className="boardHeading">
                    <h3>{column.title}</h3>
                    <span>{items.length}</span>
                  </div>
                  <div className="boardStack">
                    {items.map((task) => (
                      <button
                        className={`taskCard ${
                          selectedTaskId === task.id ? "selected" : ""
                        }`}
                        type="button"
                        key={task.id}
                        onClick={() => setSelectedTaskId(task.id)}
                      >
                        <div className="taskCardTop">
                          <span className="roleId">{task.assignee_role}</span>
                          <StatusPill value={task.state} />
                        </div>
                        <strong>{task.goal}</strong>
                        <p>{task.task_type}</p>
                        <div className="taskCardFooter">
                          <span>{task.mode.toUpperCase()}</span>
                          <span>{task.dependencies.length} 依赖</span>
                        </div>
                      </button>
                    ))}
                    {items.length === 0 && <p className="columnEmpty">无任务</p>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {selectedTask && (
        <section className="surface detailSurface">
          <SectionHeader
            eyebrow={`${selectedTask.assignee_role} / ${selectedTask.task_type}`}
            title="任务详情"
            aside={<StatusPill value={selectedTask.state} />}
          />
          <div className="detailGrid">
            <div>
              <h3>目标</h3>
              <p>{selectedTask.goal}</p>
            </div>
            <div>
              <h3>输入版本</h3>
              <p>{selectedTask.input_version}</p>
              <div className="referenceList">
                {selectedTask.input_refs.map((item) => (
                  <code key={item}>{item}</code>
                ))}
              </div>
            </div>
            <div>
              <h3>交付合同</h3>
              <p>{selectedTask.deliverable_schema}</p>
              <p className="mutedText">{selectedTask.acceptance_policy}</p>
            </div>
            <div>
              <h3>依赖</h3>
              {selectedTask.dependencies.length === 0 ? (
                <p className="mutedText">无上游依赖</p>
              ) : (
                <ul>
                  {selectedTask.dependencies.map((dependency) => (
                    <li key={dependency}>
                      {dependencyNames.get(dependency) ?? dependency}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <footer className="detailFooter">
            <span>revision {selectedTask.revision}</span>
            <span>更新于 {formatDate(selectedTask.updated_at)}</span>
            <span>{stateLabel(selectedTask.state)}</span>
          </footer>
        </section>
      )}

      {reviewNode && selectedPlan && (
        <div className="dialogBackdrop">
          <section className="dialogCard" role="dialog" aria-modal="true">
            <div className="dialogHeading">
              <div>
                <p className="eyebrow">REVIEW CONTRACT</p>
                <h2>记录审核结论</h2>
              </div>
              <button
                className="iconButton"
                type="button"
                aria-label="关闭"
                onClick={() => setReviewNode(null)}
              >
                ×
              </button>
            </div>
            <p className="dialogLead">{reviewNode.goal}</p>
            <p className="formNote">
              此处记录本地用户代表指定审核岗位合同作出的结论，不冒充 W17 的独立 Agent 或真实专家审核。
            </p>
            <form className="formStack" onSubmit={(event) => void submitReview(event)}>
              <label>
                审核岗位
                <select
                  value={reviewerRole}
                  onChange={(event) => setReviewerRole(event.target.value)}
                >
                  {reviewNode.reviewer_roles.map((role) => (
                    <option value={role} key={role}>
                      {role}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                结论
                <select
                  value={reviewDecision}
                  disabled={criticalFinding}
                  onChange={(event) =>
                    setReviewDecision(event.target.value as ReviewDecision)
                  }
                >
                  <option value="accepted">通过</option>
                  <option value="changes_requested">要求重做</option>
                  <option value="disputed">保留争议</option>
                </select>
              </label>
              <label>
                审核摘要与依据
                <textarea
                  value={reviewSummary}
                  onChange={(event) => setReviewSummary(event.target.value)}
                  rows={4}
                  required
                  placeholder="说明检查了什么、发现什么，以及为什么接受或退回。"
                />
              </label>
              <label className="checkboxLabel">
                <input
                  type="checkbox"
                  checked={criticalFinding}
                  onChange={(event) => {
                    setCriticalFinding(event.target.checked);
                    if (event.target.checked) {
                      setReviewDecision("changes_requested");
                    }
                  }}
                />
                critical缺陷：必须重做并阻止下游推进
              </label>
              <button className="button primary" type="submit" disabled={busy}>
                {busy ? "正在保存…" : "保存审核记录"}
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
