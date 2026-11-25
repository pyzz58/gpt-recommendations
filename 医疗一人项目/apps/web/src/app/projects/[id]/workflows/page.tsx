"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  assessWorkflowStage,
  createWorkflowStagePlan,
  decideWorkflowStage,
  fetchOverview,
  fetchProjectWorkflows,
  fetchWorkflowAssessments,
  notifyProjectChanged,
} from "@/lib/api";
import type {
  CriterionResult,
  StageAssessmentView,
  WorkflowDescriptor,
  WorkflowStage,
} from "@/lib/api";

import {
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatDate,
  stateLabel,
  trackLabel,
} from "@/components/ui";

type CriterionDraft = {
  status: "met" | "unmet" | "unknown";
  refs: string;
  rationale: string;
};

export default function WorkflowsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [workflows, setWorkflows] = useState<WorkflowDescriptor[]>([]);
  const [assessments, setAssessments] = useState<StageAssessmentView[]>([]);
  const [selectedTrack, setSelectedTrack] = useState<
    "pet_repurposing" | "ivd" | "device"
  >("pet_repurposing");
  const [selectionDecisionId, setSelectionDecisionId] = useState<string | null>(
    null,
  );
  const [assessmentStage, setAssessmentStage] =
    useState<WorkflowStage | null>(null);
  const [drafts, setDrafts] = useState<Record<string, CriterionDraft>>({});
  const [assessmentRationale, setAssessmentRationale] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextWorkflows, nextAssessments, overview] = await Promise.all([
          fetchProjectWorkflows(projectId, signal),
          fetchWorkflowAssessments(projectId, undefined, signal),
          fetchOverview(projectId, signal),
        ]);
        setWorkflows(nextWorkflows);
        setAssessments(nextAssessments);
        setSelectionDecisionId(overview.current_selection_decision_id);
        if (overview.current_direction) {
          setSelectedTrack(
            overview.current_direction.track as
              | "pet_repurposing"
              | "ivd"
              | "device",
          );
        }
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取专业流程");
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

  const workflow = workflows.find(
    (item) => item.definition.track === selectedTrack,
  );
  const latestByStage = useMemo(() => {
    const result = new Map<string, StageAssessmentView>();
    for (const assessment of assessments) {
      if (
        assessment.workflow_track === selectedTrack &&
        !result.has(assessment.stage_id)
      ) {
        result.set(assessment.stage_id, assessment);
      }
    }
    return result;
  }, [assessments, selectedTrack]);

  function previousAccepted(stage: WorkflowStage): boolean {
    if (!workflow || stage.sequence === 1) return true;
    const previous = workflow.definition.stages[stage.sequence - 2];
    return latestByStage.get(previous.stage_id)?.decision === "accepted";
  }

  function defaultEvidenceRefs(stage: WorkflowStage): string {
    const refs = selectionDecisionId ? [selectionDecisionId] : [];
    if (stage.sequence > 1 && workflow) {
      const previous = workflow.definition.stages[stage.sequence - 2];
      const assessment = latestByStage.get(previous.stage_id);
      if (assessment) refs.push(assessment.id);
    }
    return refs.join(", ");
  }

  function openAssessment(stage: WorkflowStage) {
    setAssessmentStage(stage);
    setAssessmentRationale("");
    const refs = defaultEvidenceRefs(stage);
    setDrafts(
      Object.fromEntries(
        stage.criteria.map((criterion) => [
          criterion.id,
          {
            status: "unknown" as const,
            refs,
            rationale: "",
          },
        ]),
      ),
    );
  }

  async function submitAssessment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workflow || !assessmentStage || !assessmentRationale.trim()) return;
    const results: CriterionResult[] = assessmentStage.criteria.map(
      (criterion) => {
        const draft = drafts[criterion.id];
        return {
          criterion_id: criterion.id,
          status: draft?.status ?? "unknown",
          rationale: draft?.rationale.trim() || "用户未填写单独理由。",
          evidence_refs: (draft?.refs ?? "")
            .split(/[\s,，]+/)
            .map((item) => item.trim())
            .filter(Boolean),
        };
      },
    );
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const assessment = await assessWorkflowStage(
        projectId,
        workflow.definition.track,
        assessmentStage.stage_id,
        results,
        assessmentRationale.trim(),
      );
      setAssessmentStage(null);
      setNotice(
        `阶段评估已保存：${stateLabel(assessment.status)}，建议 ${recommendationLabel(
          assessment.recommendation,
        )}。`,
      );
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法保存阶段评估");
    } finally {
      setBusy(false);
    }
  }

  async function decide(
    assessment: StageAssessmentView,
    decision: "accepted" | "changes_requested",
  ) {
    const reason = window.prompt(
      decision === "accepted"
        ? "请输入接受阶段门的理由："
        : "请输入退回阶段门的理由：",
    );
    if (!reason?.trim()) return;
    setBusy(true);
    setError("");
    try {
      await decideWorkflowStage(
        projectId,
        assessment.id,
        decision,
        "A25",
        reason.trim(),
      );
      setNotice(
        decision === "accepted"
          ? "阶段门已记录为接受；这是用户决定，不是科学认证。"
          : "阶段门已退回，需修订或补充记录。",
      );
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法记录阶段门决定");
    } finally {
      setBusy(false);
    }
  }

  async function createPlan(stage: WorkflowStage) {
    if (!workflow || !selectionDecisionId) return;
    setBusy(true);
    setError("");
    try {
      await createWorkflowStagePlan(
        projectId,
        workflow.definition.track,
        stage.stage_id,
        selectionDecisionId,
        crypto.randomUUID(),
      );
      setNotice(`已生成“${stage.title}”阶段计划草案，请到任务页激活。`);
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法生成阶段计划");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingPanel label="正在读取专业流程…" />;
  if (error && workflows.length === 0) {
    return <ErrorPanel message={error} onRetry={() => void load()} />;
  }
  if (!workflow) return null;

  return (
    <div className="pageStack">
      <section className="workflowIntro">
        <div>
          <p className="eyebrow">DOMAIN WORKFLOW</p>
          <h2>专业流程不是同一模板换标题</h2>
          <p>
            宠物药、IVD和器械分别组织必要职责、阶段输出、证据判据、失败分支与现实前置条件。
            判据记录通过也不等于科学、监管或现实执行获得验证。
          </p>
        </div>
        <code title="工作流配置指纹">{workflow.sha256.slice(0, 12)}</code>
      </section>

      <div className="workflowTabs" role="tablist" aria-label="专业领域">
        {workflows.map((item) => (
          <button
            className={
              item.definition.track === selectedTrack
                ? "workflowTab active"
                : "workflowTab"
            }
            type="button"
            key={item.definition.track}
            onClick={() => setSelectedTrack(item.definition.track)}
          >
            <span>{trackLabel(item.definition.track)}</span>
            <small>
              {item.definition.workflow_id} · V{item.definition.version}
            </small>
          </button>
        ))}
      </div>

      {(error || notice) && (
        <div className={error ? "errorPanel" : "successPanel"}>
          {error || notice}
        </div>
      )}

      {!selectionDecisionId && (
        <div className="warningBanner">
          当前项目尚未选择研发方向。流程模板可查看，但不能建立阶段计划或正式记录阶段门。
        </div>
      )}

      <section className="surface workflowSummary">
        <SectionHeader
          eyebrow={`${workflow.definition.track.toUpperCase()} / ${workflow.definition.workflow_id}`}
          title={workflow.definition.title}
        />
        <p>{workflow.definition.purpose}</p>
        <div className="workflowMeta">
          <div>
            <strong>适用</strong>
            <ul>
              {workflow.definition.applicability.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <strong>不做什么</strong>
            <ul>
              {workflow.definition.non_goals.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <div className="stageStack">
        {workflow.definition.stages.map((stage) => {
          const latest = latestByStage.get(stage.stage_id);
          const unlocked = previousAccepted(stage);
          return (
            <article className="stageCard" key={stage.stage_id}>
              <div className="stageMarker">{stage.sequence}</div>
              <div className="stageBody">
                <div className="stageHeading">
                  <div>
                    <p className="eyebrow">STAGE {stage.sequence}</p>
                    <h3>{stage.title}</h3>
                  </div>
                  {latest ? (
                    <div className="stageStatuses">
                      <StatusPill value={latest.status} />
                      {latest.decision && <StatusPill value={latest.decision} />}
                    </div>
                  ) : (
                    <span className="mutedText">未评估</span>
                  )}
                </div>
                <p className="stagePurpose">{stage.purpose}</p>
                <div className="workflowMeta">
                  <div>
                    <strong>必要岗位</strong>
                    <div className="tagCloud">
                      {stage.required_roles.map((role) => (
                        <span key={role}>{role}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <strong>必要输出</strong>
                    <div className="tagCloud">
                      {stage.required_outputs.map((output) => (
                        <span key={output}>{output}</span>
                      ))}
                    </div>
                  </div>
                </div>
                <details className="criterionDetails">
                  <summary>查看判据与失败分支</summary>
                  <ul>
                    {stage.criteria.map((criterion) => (
                      <li key={criterion.id}>
                        <code>{criterion.kind}</code> {criterion.description}
                      </li>
                    ))}
                  </ul>
                  <p className="mutedText">
                    失败分支：
                    {Object.entries(stage.failure_routes)
                      .map(([condition, route]) => `${condition} → ${route}`)
                      .join("；")}
                  </p>
                </details>
                {stage.external_preconditions.length > 0 && (
                  <div className="externalGate">
                    <strong>现实前置条件 · W16前不可自证</strong>
                    {stage.external_preconditions.map((item) => (
                      <p key={item.id}>
                        {item.description} · {item.provider_type}
                      </p>
                    ))}
                  </div>
                )}
                <div className="stageActions">
                  <button
                    className="button secondary"
                    type="button"
                    onClick={() => openAssessment(stage)}
                    disabled={!selectionDecisionId || !unlocked || busy}
                  >
                    记录阶段评估
                  </button>
                  <button
                    className="button primary"
                    type="button"
                    onClick={() => void createPlan(stage)}
                    disabled={!selectionDecisionId || !unlocked || busy}
                  >
                    生成阶段计划
                  </button>
                  {latest?.status === "ready_for_review" && !latest.decision && (
                    <>
                      <button
                        className="button secondary"
                        type="button"
                        onClick={() => void decide(latest, "accepted")}
                        disabled={busy}
                      >
                        接受阶段门
                      </button>
                      <button
                        className="button danger"
                        type="button"
                        onClick={() => void decide(latest, "changes_requested")}
                        disabled={busy}
                      >
                        退回
                      </button>
                    </>
                  )}
                </div>
                {latest && (
                  <p className="stageAssessmentMeta">
                    V{latest.assessment_version} ·{" "}
                    {recommendationLabel(latest.recommendation)} ·{" "}
                    {formatDate(latest.created_at)}
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {assessmentStage && (
        <div className="dialogBackdrop">
          <section className="dialogCard wideDialog" role="dialog" aria-modal="true">
            <div className="dialogHeading">
              <div>
                <p className="eyebrow">STAGE EVIDENCE GATE</p>
                <h2>{assessmentStage.title}</h2>
              </div>
              <button
                className="iconButton"
                type="button"
                aria-label="关闭"
                onClick={() => setAssessmentStage(null)}
              >
                ×
              </button>
            </div>
            <form className="formStack" onSubmit={(event) => void submitAssessment(event)}>
              {assessmentStage.criteria.map((criterion) => {
                const draft = drafts[criterion.id];
                return (
                  <fieldset className="criterionEditor" key={criterion.id}>
                    <legend>{criterion.description}</legend>
                    <div className="criterionControls">
                      <select
                        value={draft?.status ?? "unknown"}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [criterion.id]: {
                              ...current[criterion.id],
                              status: event.target.value as CriterionDraft["status"],
                            },
                          }))
                        }
                      >
                        <option value="unknown">未知 / 待补证</option>
                        <option value="met">记录满足</option>
                        <option value="unmet">不满足</option>
                      </select>
                      <input
                        value={draft?.refs ?? ""}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [criterion.id]: {
                              ...current[criterion.id],
                              refs: event.target.value,
                            },
                          }))
                        }
                        placeholder="证据/决定/评估 UUID，逗号分隔"
                      />
                    </div>
                    <textarea
                      value={draft?.rationale ?? ""}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [criterion.id]: {
                            ...current[criterion.id],
                            rationale: event.target.value,
                          },
                        }))
                      }
                      rows={2}
                      placeholder="说明为何是 met/unmet/unknown，以及适用范围"
                    />
                  </fieldset>
                );
              })}
              <label>
                阶段总体理由
                <textarea
                  value={assessmentRationale}
                  onChange={(event) => setAssessmentRationale(event.target.value)}
                  rows={3}
                  required
                  placeholder="说明本阶段记录完整性、缺口和为何进入下一步或阻塞。"
                />
              </label>
              <div className="warningBanner">
                引用只验证对象属于本项目；“记录满足”不证明科学真实、监管路径或外部执行。
              </div>
              <button className="button primary" type="submit" disabled={busy}>
                {busy ? "正在保存…" : "保存阶段评估"}
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

function recommendationLabel(value: StageAssessmentView["recommendation"]): string {
  return (
    {
      continue_to_review: "进入阶段门审阅",
      gather_evidence: "补充证据",
      revise: "修订",
      wait_external: "等待真实现实前置条件",
      stop: "停止",
    }[value] ?? value
  );
}
