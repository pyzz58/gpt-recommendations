import {
  type FormEvent,
  type MouseEvent,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  ApiError,
  type IssueView,
  type LabComparisonView,
  type MonitoringReviewItemView,
  type ReviewTemplateView,
  type RuleListItemView,
  type SubjectView,
  type VisitReviewBoardView,
  createIssue,
  bindReviewTemplate,
  getIssues,
  getReviewTemplates,
  getRules,
  getSubjects,
  getVisitReviewItems,
  updateMonitoringReviewItem
} from "../../api/client";
import { ImportPreview } from "../edc/ImportPreview";
import { LabComparison } from "../laboratory/LabComparison";
import { RecognitionReview } from "../laboratory/RecognitionReview";

type Props = {
  studyId: string;
  siteId: string;
  visitId: string;
  onChanged?: () => void;
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "逐项核查失败";
}

function statusLabel(status: string): string {
  switch (status) {
    case "checked":
      return "已核查";
    case "needs_clarification":
      return "待核实";
    case "not_applicable":
      return "不适用";
    case "skipped":
      return "已跳过";
    default:
      return "未核查";
  }
}

export function TemplateReviewWorkspace({
  studyId,
  siteId,
  visitId,
  onChanged
}: Props) {
  const [board, setBoard] = useState<VisitReviewBoardView | null>(null);
  const [templates, setTemplates] = useState<ReviewTemplateView[]>([]);
  const [subjects, setSubjects] = useState<SubjectView[]>([]);
  const [rules, setRules] = useState<RuleListItemView[]>([]);
  const [issues, setIssues] = useState<IssueView[]>([]);
  const [comparisonByItem, setComparisonByItem] = useState<
    Record<string, string>
  >({});
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [evidenceItem, setEvidenceItem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [
        nextBoard,
        nextTemplates,
        nextSubjects,
        nextRules,
        nextIssues
      ] =
        await Promise.all([
          getVisitReviewItems(visitId),
          getReviewTemplates(studyId, siteId),
          getSubjects(studyId, siteId),
          getRules(studyId, siteId),
          getIssues(studyId, siteId)
        ]);
      setBoard(nextBoard);
      setTemplates(nextTemplates);
      setSubjects(nextSubjects);
      setRules(nextRules);
      setIssues(nextIssues);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [siteId, studyId, visitId]);

  useEffect(() => {
    void load();
  }, [load]);

  const sections = useMemo(() => {
    const grouped = new Map<
      string,
      { title: string; order: number; items: MonitoringReviewItemView[] }
    >();
    for (const item of board?.items ?? []) {
      const current = grouped.get(item.section_key);
      if (current) {
        current.items.push(item);
      } else {
        grouped.set(item.section_key, {
          title: item.section_title,
          order: item.section_order,
          items: [item]
        });
      }
    }
    return [...grouped.entries()]
      .sort((left, right) => left[1].order - right[1].order)
      .map(([key, value]) => ({ key, ...value }));
  }, [board?.items]);

  const activeRules = rules.filter((rule) => rule.current_version);

  async function bind(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const templateId = String(form.get("template_id") ?? "");
    if (!templateId) {
      setError("请选择已确认的核查模板。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setBoard(await bindReviewTemplate(visitId, templateId));
      setMessage("本次监查已绑定模板核查项。");
      onChanged?.();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveItem(
    event: FormEvent<HTMLFormElement>,
    item: MonitoringReviewItemView
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await updateMonitoringReviewItem(item, {
        status: String(form.get("status") ?? item.status),
        note: String(form.get("note") ?? ""),
        subjectId: String(form.get("subject_id") ?? "") || null,
        ruleVersionIds: form
          .getAll("rule_version_ids")
          .map((value) => String(value)),
        linkedIssueId:
          String(form.get("linked_issue_id") ?? "") || null,
        linkedComparisonId:
          String(form.get("linked_comparison_id") ?? "") || null
      });
      await load();
      setMessage(`${item.item_key} 的核查记录已保存。`);
      onChanged?.();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function createIssueFromItem(
    event: MouseEvent<HTMLButtonElement>,
    item: MonitoringReviewItemView
  ) {
    const form = event.currentTarget.form;
    if (!form) {
      return;
    }
    const data = new FormData(form);
    const actionKind = String(
      data.get("new_issue_action") ?? "edc_correction"
    );
    setBusy(true);
    setError(null);
    try {
      const issue = await createIssue(studyId, {
        siteId,
        finding: `${item.question_text} ${item.note || ""}`.trim(),
        location: `${item.source_locator} · ${item.item_key}`,
        recommendation:
          "按已记录核查范围补充来源、更正或医学澄清。",
        knownProgress: "本次模板逐项核查发现，尚未确认整改完成。",
        actions: [
          {
            kind: actionKind,
            requirement: item.question_text
          }
        ]
      });
      setIssues((current) => [issue, ...current]);
      if (form.elements.namedItem("linked_issue_id") instanceof HTMLSelectElement) {
        const selector = form.elements.namedItem(
          "linked_issue_id"
        ) as HTMLSelectElement;
        selector.value = issue.id;
      }
      setMessage(
        `已创建 ${issue.issue_number}；保存本项后会把待办关联到当前核查项。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="workspace-module template-review-workspace"
      aria-labelledby="template-review-title"
    >
      <div className="module-heading">
        <div>
          <p className="eyebrow">本次监查 · 模板逐项核查</p>
          <h2 id="template-review-title">按报告章节与问句记录实际核查</h2>
          <p>
            模板问句只是待核查项；状态、依据、受试者和后续问题由 CRA 明确记录。
          </p>
        </div>
        <span className="status-chip muted">
          {board?.items.filter((item) => item.status !== "not_checked").length ??
            0}
          /{board?.items.length ?? 0} 已记录
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      {board && !board.binding && (
        <form className="source-reference" onSubmit={(event) => void bind(event)}>
          <p className="eyebrow">复用已确认配置</p>
          <h3>为本次监查选择核查模板</h3>
          {templates.length === 0 ? (
            <p>
              尚无模板核查配置。请先在“资料与模板”上传报告模板并完成集中配置。
            </p>
          ) : (
            <>
              <label>
                核查模板
                <select name="template_id" required>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.title} · {template.items.length} 项
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="primary-button compact"
                type="submit"
                disabled={busy}
              >
                用于本次监查
              </button>
            </>
          )}
        </form>
      )}

      {board?.binding && (
        <section className="template-bound-heading source-reference">
          <p className="eyebrow">当前模板</p>
          <strong>{board.template?.title}</strong>
          <span>
            {sections.length} 章节 · {board.items.length} 个核查项
          </span>
        </section>
      )}

      {sections.map((section) => (
        <section className="template-review-section" key={section.key}>
          <header>
            <div>
              <p className="eyebrow">模板章节</p>
              <h3>{section.title}</h3>
            </div>
            <span className="status-chip muted">
              {
                section.items.filter(
                  (item) => item.status !== "not_checked"
                ).length
              }
              /{section.items.length}
            </span>
          </header>

          {section.items.map((item) => {
            const selectedRules = activeRules.filter(
              (rule) =>
                rule.current_version &&
                item.rule_version_ids.includes(rule.current_version.id)
            );
            const conditions = Array.isArray(
              item.applicability.reviewer_conditions
            )
              ? (item.applicability.reviewer_conditions as string[])
              : [];
            const exceptions = Array.isArray(
              item.applicability.reviewer_exceptions
            )
              ? (item.applicability.reviewer_exceptions as string[])
              : [];
            return (
              <article
                className={`template-review-item ${
                  expandedItem === item.id ? "expanded" : ""
                }`}
                key={item.id}
                data-testid={`review-item-${item.item_key}`}
              >
                <button
                  className="review-item-toggle"
                  type="button"
                  aria-expanded={expandedItem === item.id}
                  onClick={() =>
                    setExpandedItem((current) =>
                      current === item.id ? null : item.id
                    )
                  }
                >
                  <span className="item-key">{item.item_key}</span>
                  <strong>{item.question_text}</strong>
                  <span
                    className={`status-chip ${
                      item.status === "checked" ? "" : "muted"
                    }`}
                  >
                    {statusLabel(item.status)}
                  </span>
                </button>
                {expandedItem === item.id && (
                <div className="template-review-item-body">
                  <div className="source-reference">
                    <p className="eyebrow">模板依据</p>
                    <p>{item.source_quote}</p>
                    <small>
                      {item.source_locator} · 报告回填位置{" "}
                      {item.report_locator}
                    </small>
                    {conditions.length ? (
                      <p>
                        条件：{conditions.join("；")}
                      </p>
                    ) : null}
                    {exceptions.length ? (
                      <p>
                        例外：{exceptions.join("；")}
                      </p>
                    ) : null}
                  </div>

                  <form onSubmit={(event) => void saveItem(event, item)}>
                    <div className="review-record-grid">
                      <label>
                        核查状态
                        <select name="status" defaultValue={item.status}>
                          <option value="not_checked">未核查</option>
                          <option value="checked">已核查</option>
                          <option value="needs_clarification">待核实</option>
                          <option value="not_applicable">不适用</option>
                          <option value="skipped">已跳过</option>
                        </select>
                      </label>
                      <label>
                        受试者
                        <select
                          name="subject_id"
                          defaultValue={item.subject_id ?? ""}
                        >
                          <option value="">不限定受试者</option>
                          {subjects.map((subject) => (
                            <option key={subject.id} value={subject.id}>
                              {subject.deidentified_label} ·{" "}
                              {subject.identifiers[0]?.external_id ?? "unknown"}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        关联问题
                        <select
                          name="linked_issue_id"
                          defaultValue={item.linked_issue_id ?? ""}
                        >
                          <option value="">不关联问题</option>
                          {issues.map((issue) => (
                            <option key={issue.id} value={issue.id}>
                              {issue.issue_number} ·{" "}
                              {issue.original_finding ?? "unknown"}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <input
                      type="hidden"
                      name="linked_comparison_id"
                      value={
                        comparisonByItem[item.id] ??
                        item.linked_comparison_id ??
                        ""
                      }
                    />
                    <label>
                      CRA 核查记录
                      <textarea
                        name="note"
                        rows={3}
                        defaultValue={item.note ?? ""}
                        placeholder="记录核查范围、差异或待核实原因；不要把未知写成正常。"
                      />
                    </label>
                    <fieldset className="rule-reference-picker">
                      <legend>关联项目依据</legend>
                      {activeRules.length === 0 ? (
                        <p>当前中心尚无已确认规则。</p>
                      ) : (
                        activeRules.map((rule) => (
                          <label key={rule.id}>
                            <input
                              name="rule_version_ids"
                              type="checkbox"
                              value={rule.current_version?.id}
                              defaultChecked={
                                rule.current_version
                                  ? item.rule_version_ids.includes(
                                      rule.current_version.id
                                    )
                                  : false
                              }
                            />
                            <span>
                              <strong>{rule.rule_key}</strong>{" "}
                              {rule.current_version?.summary}
                            </span>
                          </label>
                        ))
                      )}
                    </fieldset>
                    {selectedRules.length > 0 && (
                      <p className="security-note">
                        已关联 {selectedRules.length} 条规则；完整条件、例外和
                        原文可在“资料与模板”的规则底稿中展开核对。
                      </p>
                    )}
                    <div className="action-buttons">
                      <button
                        className="primary-button compact"
                        type="submit"
                        disabled={busy}
                      >
                        保存本项核查记录
                      </button>
                      <label>
                        新待办动作
                        <select
                          name="new_issue_action"
                          defaultValue="edc_correction"
                        >
                          <option value="edc_correction">EDC/数据更正</option>
                          <option value="document_supply">补充文件</option>
                          <option value="medical_clarification">
                            医学澄清
                          </option>
                          <option value="query_followup">Query跟进</option>
                          <option value="pd_reporting">PD上报</option>
                        </select>
                      </label>
                      <button
                        className="secondary-button"
                        type="button"
                        disabled={busy}
                        onClick={(event) =>
                          void createIssueFromItem(event, item)
                        }
                      >
                        从本项创建问题待办
                      </button>
                    </div>
                  </form>

                  <button
                    className="secondary-button item-evidence-toggle"
                    type="button"
                    onClick={() =>
                      setEvidenceItem((current) =>
                        current === item.id ? null : item.id
                      )
                    }
                  >
                    {evidenceItem === item.id
                      ? "收起 EDC/原始报告证据工具"
                      : "在当前核查项中打开 EDC/原始报告证据工具"}
                  </button>
                  {evidenceItem === item.id && (
                    <div className="item-evidence-tools">
                      <ImportPreview studyId={studyId} siteId={siteId} />
                      <RecognitionReview studyId={studyId} siteId={siteId} />
                      <LabComparison
                        studyId={studyId}
                        siteId={siteId}
                        onCompared={(comparison: LabComparisonView) =>
                          setComparisonByItem((current) => ({
                            ...current,
                            [item.id]: comparison.id
                          }))
                        }
                      />
                    </div>
                  )}
                </div>
                )}
              </article>
            );
          })}
        </section>
      ))}
    </section>
  );
}
