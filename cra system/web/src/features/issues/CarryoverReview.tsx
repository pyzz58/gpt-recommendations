import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type CarryoverResponse,
  type IssueView,
  type WorkbenchView,
  confirmCarryoverImport,
  confirmCorrectedActions,
  confirmPdReported,
  createMonitoringVisit,
  createQueryLink,
  getMonitoringWorkbench,
  previewCarryoverDocument,
  previewCarryoverText,
  reopenIssueAction,
  selectPrevisitIssues,
  updateMonitoringScope
} from "../../api/client";
import { PrevisitSelection } from "./PrevisitSelection";

type Props = {
  studyId: string;
  siteId: string;
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "遗留事项操作失败";
}

function actionLabel(kind: string): string {
  switch (kind) {
    case "pd_reporting":
      return "PD上报";
    case "edc_correction":
      return "EDC/数据更正";
    case "document_supply":
      return "补件";
    case "medical_clarification":
      return "医学澄清";
    case "query_followup":
      return "Query跟进";
    default:
      return "其他行动";
  }
}

export function carryoverStatusLabel(status: string): string {
  switch (status) {
    case "completed":
      return "CRA确认完成";
    case "in_progress":
      return "部分完成";
    case "needs_correction":
      return "仍需整改";
    case "reported_done":
      return "中心已报告，待CRA确认";
    case "open":
      return "待跟进";
    case "incomplete":
      return "尚未定义行动";
    default:
      return status;
  }
}

function storageKey(studyId: string, siteId: string): string {
  return `cra.w06.visit.${studyId}.${siteId}`;
}

export function CarryoverReview({ studyId, siteId }: Props) {
  const [workbench, setWorkbench] = useState<WorkbenchView | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [preview, setPreview] = useState<CarryoverResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStoredVisit = useCallback(async () => {
    const stored = window.localStorage.getItem(storageKey(studyId, siteId));
    if (!stored) {
      setWorkbench(null);
      return;
    }
    try {
      setWorkbench(await getMonitoringWorkbench(stored));
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 404) {
        window.localStorage.removeItem(storageKey(studyId, siteId));
        setWorkbench(null);
        return;
      }
      throw reason;
    }
  }, [studyId, siteId]);

  useEffect(() => {
    setBusy(true);
    setError(null);
    loadStoredVisit()
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [loadStoredVisit]);

  function remember(next: WorkbenchView) {
    setWorkbench(next);
    window.localStorage.setItem(
      storageKey(studyId, siteId),
      next.visit.id
    );
  }

  async function startVisit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const next = await createMonitoringVisit({
        studyId,
        siteId,
        title: String(form.get("title") ?? "本次中心监查"),
        scopeNote: String(form.get("scope_note") ?? ""),
        stage: String(form.get("stage") ?? "carryover_review")
      });
      remember(next);
      setMessage("本次监查已建立，已带入当前中心全部未完遗留。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function refresh(visitId = workbench?.visit.id) {
    if (!visitId) {
      return;
    }
    const next = await getMonitoringWorkbench(visitId);
    remember(next);
  }

  async function selectForPrevisit(issueIds: string[]) {
    if (!workbench) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await selectPrevisitIssues(workbench.visit, issueIds);
      remember(next);
      setMessage(
        "访前选择已保存；未选遗留仍保留在完整清单和后续跟进中。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function confirmAction(issue: IssueView, actionId: string) {
    const action = issue.actions.find((item) => item.id === actionId);
    if (!action) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (action.kind === "pd_reporting") {
        await confirmPdReported(action, {
          statement: "CRA明确确认该项PD已上报",
          note: "CRA在工作台点击确认，未要求回执或附件。"
        });
      } else {
        await confirmCorrectedActions({ actions: [action] });
      }
      await refresh();
      setMessage(
        action.kind === "pd_reporting"
          ? "PD上报事项已记录为CRA确认已上报；其他行动保持不变。"
          : "所选行动已记录为“CRA确认已整改”；其他行动保持不变。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function reopen(issue: IssueView, actionId: string) {
    const action = issue.actions.find((item) => item.id === actionId);
    if (!action) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await reopenIssueAction(
        action,
        "CRA复核后确认该事项仍未完成，需要继续跟进。"
      );
      await refresh();
      setMessage("该行动已重新打开，原确认和历史记录均保留。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function linkQuery(
    event: FormEvent<HTMLFormElement>,
    issue: IssueView
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await createQueryLink(issue, {
        state: String(form.get("query_state") ?? "draft") as
          | "draft"
          | "formal",
        externalSystem: String(form.get("external_system") ?? ""),
        externalNumber: String(form.get("external_number") ?? ""),
        openedOn: String(form.get("opened_on") ?? ""),
        dueOn: String(form.get("due_on") ?? ""),
        deadlineSource: String(form.get("deadline_source") ?? "")
      });
      await refresh();
      setMessage("Query关联已保存；期限未知时不会生成超期天数。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function previewDocument(versionId: string) {
    setBusy(true);
    setError(null);
    try {
      setPreview(
        await previewCarryoverDocument({ versionId, siteId })
      );
      setMessage("已生成遗留候选预览，确认前没有创建问题。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function previewText(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = String(form.get("text") ?? "").trim();
    if (!text) {
      setError("请输入历史问题文字。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setPreview(
        await previewCarryoverText({
          studyId,
          siteId,
          label: String(form.get("label") ?? "历史问题文字"),
          text
        })
      );
      setMessage("已生成文字遗留候选预览，确认前不会创建问题。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function confirmPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preview) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const corrections = preview.candidates.map((candidate) => {
      const issueNumber = String(
        form.get(`issue_number_${candidate.id}`) ?? ""
      ).trim();
      const finding = String(
        form.get(`finding_${candidate.id}`) ?? ""
      ).trim();
      const location = String(
        form.get(`location_${candidate.id}`) ?? ""
      ).trim();
      const recommendation = String(
        form.get(`recommendation_${candidate.id}`) ?? ""
      ).trim();
      const skip = form.get(`skip_${candidate.id}`) === "on";
      return {
        candidate_id: candidate.id,
        issue_number: issueNumber || null,
        original_finding: finding || candidate.original_finding,
        location: location || candidate.location,
        recommendation: recommendation || candidate.recommendation,
        skip
      };
    });
    setBusy(true);
    setError(null);
    try {
      const result = await confirmCarryoverImport(preview, corrections);
      setPreview(result);
      await refresh();
      setMessage(
        `遗留导入已确认：${result.candidates.filter((item) => item.state === "imported").length} 项新建，${result.candidates.filter((item) => item.state === "reused").length} 项复用原编号。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function updateScope(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workbench) {
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const next = await updateMonitoringScope(workbench.visit, {
        scopeNote: String(form.get("scope_note") ?? ""),
        status: String(form.get("status") ?? "in_progress")
      });
      remember(next);
      setMessage("监查范围和阶段状态已保存。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="carryover-workspace" aria-labelledby="carryover-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M05/M06 · 遗留、行动与Query</p>
          <h2 id="carryover-title">本次监查与遗留复核</h2>
          <p>
            从历史资料进入本次提醒，按行动分别确认；访前勾选不会删除任何遗留。
          </p>
        </div>
        <span className="status-chip muted">
          {workbench ? `${workbench.carryover.length} 项未完` : "未开始"}
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      {!workbench ? (
        <div className="subject-input-grid">
          <form className="subject-import-form" onSubmit={(event) => void startVisit(event)}>
            <p className="eyebrow">先带入遗留</p>
            <h3>开始本次中心监查</h3>
            <label>
              监查标题
              <input
                name="title"
                defaultValue="本次中心监查"
                required
              />
            </label>
            <label>
              起始阶段
              <select name="stage" defaultValue="carryover_review">
                <option value="previsit">访前准备</option>
                <option value="carryover_review">现场遗留复核</option>
                <option value="subject_review">逐患者核查</option>
                <option value="closeout">中心关闭</option>
                <option value="handover">交接</option>
              </select>
            </label>
            <label>
              本次范围简记
              <textarea
                name="scope_note"
                rows={3}
                placeholder="例：上次遗留、本次患者范围及未核实事项"
              />
            </label>
            <button className="primary-button compact" type="submit" disabled={busy}>
              建立本次监查
            </button>
          </form>
        </div>
      ) : (
        <>
          <section className="monitoring-stage-strip" aria-label="监查阶段">
            {workbench.stages.map((stage, index) => (
              <span
                key={stage}
                className={stage === workbench.visit.stage ? "active" : ""}
              >
                {index + 1}.{" "}
                {{
                  previsit: "访前",
                  carryover_review: "遗留复核",
                  subject_review: "逐患者",
                  closeout: "关闭",
                  handover: "交接"
                }[stage] ?? stage}
              </span>
            ))}
          </section>

          <div className="carryover-layout">
            <div className="carryover-main">
              <PrevisitSelection
                issues={workbench.carryover}
                selectedIds={workbench.selected_issue_ids}
                busy={busy}
                onSave={selectForPrevisit}
              />

              <section className="carryover-list" aria-labelledby="carryover-list-title">
                <div className="applicable-heading">
                  <div>
                    <p className="eyebrow">完整遗留清单</p>
                    <h3 id="carryover-list-title">逐项展开，按行动完成</h3>
                  </div>
                  <span className="status-chip muted">
                    {workbench.carryover.length} 项
                  </span>
                </div>
                {workbench.carryover.length === 0 ? (
                  <p className="empty-documents">
                    当前没有已记录的未完遗留。历史未导入不等于曾经没有问题。
                  </p>
                ) : (
                  workbench.carryover.map((issue) => (
                    <article
                      className={`carryover-card ${
                        expanded === issue.id ? "expanded" : ""
                      }`}
                      key={issue.id}
                    >
                      <button
                        type="button"
                        className="carryover-summary"
                        onClick={() =>
                          setExpanded((current) =>
                            current === issue.id ? null : issue.id
                          )
                        }
                        aria-expanded={expanded === issue.id}
                      >
                        <span>
                          <strong>{issue.issue_number}</strong>
                          <small>
                            {issue.location ?? "位置未载明"} ·{" "}
                            {issue.source_kind}
                          </small>
                        </span>
                        <span className="status-chip">
                          {carryoverStatusLabel(issue.aggregate_status)}
                        </span>
                      </button>
                      {expanded === issue.id && (
                        <div className="carryover-detail">
                          <dl>
                            <div>
                              <dt>原问题</dt>
                              <dd>{issue.original_finding ?? "unknown"}</dd>
                            </div>
                            <div>
                              <dt>位置</dt>
                              <dd>{issue.location ?? "unknown"}</dd>
                            </div>
                            <div>
                              <dt>整改建议</dt>
                              <dd>{issue.recommendation ?? "unknown"}</dd>
                            </div>
                            <div>
                              <dt>已知进展</dt>
                              <dd>{issue.known_progress ?? "unknown"}</dd>
                            </div>
                            <div>
                              <dt>已有沟通</dt>
                              <dd>{issue.reported_correction ?? "未记录"}</dd>
                            </div>
                            <div>
                              <dt>建议来源</dt>
                              <dd>
                                {issue.recommendation_sources.length
                                  ? issue.recommendation_sources
                                      .map((source) =>
                                        typeof source === "string"
                                          ? source
                                          : String(
                                              (source as { text?: string })
                                                .text ?? "原记录"
                                            )
                                      )
                                      .join("、")
                                  : "unknown"}
                              </dd>
                            </div>
                          </dl>
                          {issue.source_refs.length > 0 && (
                            <details>
                              <summary>查看原问题来源位置</summary>
                              <ul>
                                {issue.source_refs.map((source, index) => (
                                  <li key={`${issue.id}-source-${index}`}>
                                    {String(
                                      source.locator ??
                                        source.sheet ??
                                        source.source_type ??
                                        "来源位置"
                                    )}
                                    {source.quote ? ` · ${String(source.quote)}` : ""}
                                  </li>
                                ))}
                              </ul>
                            </details>
                          )}
                          <div className="action-list">
                            <h4>分项行动</h4>
                            {issue.actions.length === 0 && (
                              <p>尚未定义行动，不能推断整项已完成。</p>
                            )}
                            {issue.actions.map((action) => (
                              <article
                                key={action.id}
                                className={action.status}
                              >
                                <div>
                                  <strong>
                                    {action.action_key} · {actionLabel(action.kind)}
                                  </strong>
                                  <span>{carryoverStatusLabel(action.status)}</span>
                                </div>
                                <p>{action.requirement ?? "行动要求未载明"}</p>
                                <small>
                                  {action.completed_at
                                    ? `由 ${action.completed_by ?? "未知操作者"} 于 ${new Date(action.completed_at).toLocaleString()} 确认`
                                    : action.deadline_status === "overdue"
                                      ? `已超期 ${action.overdue_days} 天`
                                      : action.due_on
                                        ? `期限 ${action.due_on}`
                                        : "期限未载明"}
                                </small>
                                <div className="action-buttons">
                                  {action.status !== "completed" && (
                                    <button
                                      className="secondary-button"
                                      type="button"
                                      disabled={busy}
                                      onClick={() =>
                                        void confirmAction(issue, action.id)
                                      }
                                    >
                                      {action.kind === "pd_reporting"
                                        ? "CRA确认PD已上报"
                                        : "CRA确认已整改"}
                                    </button>
                                  )}
                                  {action.status === "completed" && (
                                    <button
                                      className="text-button"
                                      type="button"
                                      disabled={busy}
                                      onClick={() =>
                                        void reopen(issue, action.id)
                                      }
                                    >
                                      仍未改好，重新打开
                                    </button>
                                  )}
                                </div>
                              </article>
                            ))}
                          </div>

                          <form
                            className="query-form"
                            onSubmit={(event) => void linkQuery(event, issue)}
                          >
                            <h4>Query 草稿 / 正式关联</h4>
                            <label>
                              状态
                              <select name="query_state" defaultValue="draft">
                                <option value="draft">草稿</option>
                                <option value="formal">正式EDC Query</option>
                              </select>
                            </label>
                            <label>
                              系统
                              <input name="external_system" placeholder="synthetic-edc" />
                            </label>
                            <label>
                              外部编号
                              <input name="external_number" />
                            </label>
                            <label>
                              实际创建日
                              <input name="opened_on" type="date" />
                            </label>
                            <label>
                              期限
                              <input name="due_on" type="date" />
                            </label>
                            <label>
                              期限依据
                              <input name="deadline_source" />
                            </label>
                            <button
                              className="secondary-button"
                              type="submit"
                              disabled={busy}
                            >
                              保存Query关联
                            </button>
                          </form>

                          {issue.query_links.length > 0 && (
                            <div className="query-list">
                              <h4>已关联Query</h4>
                              {issue.query_links.map((query) => (
                                <p key={query.id}>
                                  {query.query_state === "draft"
                                    ? "草稿"
                                    : `${query.external_query_number ?? "正式Query"}`}
                                  {" · "}
                                  {query.deadline_status === "due_date_unknown"
                                    ? "期限待明确"
                                    : query.overdue_days
                                      ? `超期 ${query.overdue_days} 天`
                                      : `剩余 ${query.days_remaining ?? 0} 天`}
                                </p>
                              ))}
                            </div>
                          )}

                          {issue.history.length > 0 && (
                            <details>
                              <summary>查看操作历史</summary>
                              <ol>
                                {issue.history.map((event) => (
                                  <li key={event.id}>
                                    <strong>{event.event_type}</strong>
                                    <small>
                                      {event.actor_id} ·{" "}
                                      {new Date(event.occurred_at).toLocaleString()}
                                    </small>
                                  </li>
                                ))}
                              </ol>
                            </details>
                          )}
                        </div>
                      )}
                    </article>
                  ))
                )}
              </section>
            </div>

            <aside className="carryover-side">
              <form className="side-card" onSubmit={(event) => void updateScope(event)}>
                <p className="eyebrow">本次范围</p>
                <h3>阶段状态</h3>
                <label>
                  范围简记
                  <textarea
                    name="scope_note"
                    rows={4}
                    defaultValue={workbench.visit.scope_note ?? ""}
                  />
                </label>
                <label>
                  状态
                  <select name="status" defaultValue={workbench.visit.status}>
                    <option value="draft">草稿</option>
                    <option value="in_progress">进行中</option>
                    <option value="completed">本次完成</option>
                  </select>
                </label>
                <button className="secondary-button" type="submit" disabled={busy}>
                  保存范围
                </button>
              </form>

              <section className="side-card">
                <p className="eyebrow">历史资料预览</p>
                <h3>从已上传资料整理遗留</h3>
                {workbench.directory_references.length === 0 ? (
                  <p>当前中心尚无可引用的历史资料。</p>
                ) : (
                  workbench.directory_references.map((reference) => (
                    <div key={reference.document_id} className="source-reference">
                      <strong>{reference.title}</strong>
                      <small>
                        {reference.original_filename ?? "无文件"} ·{" "}
                        {reference.parse_status ?? "未解析"} ·{" "}
                        {reference.mode}
                      </small>
                      {reference.document_version_id && (
                        <button
                          className="text-button"
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            void previewDocument(reference.document_version_id!)
                          }
                        >
                          预览遗留
                        </button>
                      )}
                    </div>
                  ))
                )}
                <form className="text-carryover-form" onSubmit={(event) => void previewText(event)}>
                  <label>
                    文字来源名称
                    <input name="label" defaultValue="历史问题文字" required />
                  </label>
                  <label>
                    问题文字
                    <textarea name="text" rows={5} required />
                  </label>
                  <button className="secondary-button" type="submit" disabled={busy}>
                    预览文字遗留
                  </button>
                </form>
              </section>
            </aside>
          </div>

          {preview && (
            <section className="carryover-preview" aria-labelledby="carryover-preview-title">
              <div className="applicable-heading">
                <div>
                  <p className="eyebrow">确认前预览 · 缺项保留unknown</p>
                  <h3 id="carryover-preview-title">
                    历史资料候选：{preview.import_record.source_label}
                  </h3>
                </div>
                <span className="status-chip">
                  {preview.import_record.state}
                </span>
              </div>
              {preview.import_record.warnings.length > 0 && (
                <p>{preview.import_record.warnings.join("、")}</p>
              )}
              <form onSubmit={(event) => void confirmPreview(event)}>
                {preview.candidates.map((candidate) => (
                  <article key={candidate.id} className="preview-candidate">
                    <div>
                      <strong>
                        {candidate.original_issue_number ?? "原编号未载明"}
                      </strong>
                      <span>
                        未知：{candidate.unknown_fields.join("、") || "无"}
                      </span>
                    </div>
                    <label>
                      原编号
                      <input
                        name={`issue_number_${candidate.id}`}
                        defaultValue={candidate.original_issue_number ?? ""}
                      />
                    </label>
                    <label>
                      原问题
                      <textarea
                        name={`finding_${candidate.id}`}
                        rows={3}
                        defaultValue={candidate.original_finding ?? ""}
                      />
                    </label>
                    <label>
                      位置
                      <input
                        name={`location_${candidate.id}`}
                        defaultValue={candidate.location ?? ""}
                      />
                    </label>
                    <label>
                      整改建议
                      <textarea
                        name={`recommendation_${candidate.id}`}
                        rows={3}
                        defaultValue={candidate.recommendation ?? ""}
                      />
                    </label>
                    <small>
                      来源{" "}
                      {candidate.source_refs
                        .map(
                          (source) =>
                            String(source.locator ?? source.row ?? "原文件")
                        )
                        .join("、")}
                    </small>
                    <label className="checkbox-line">
                      <input
                        type="checkbox"
                        name={`skip_${candidate.id}`}
                      />
                      本次不导入该项
                    </label>
                  </article>
                ))}
                <button
                  className="primary-button compact"
                  type="submit"
                  disabled={
                    busy ||
                    preview.import_record.state === "confirmed" ||
                    preview.candidates.length === 0
                  }
                >
                  确认预览并进入遗留
                </button>
              </form>
            </section>
          )}
        </>
      )}
    </section>
  );
}
