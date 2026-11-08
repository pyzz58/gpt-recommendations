import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type DocumentVersionView,
  type DocumentView,
  type IssueView,
  type ReportDraftView,
  type ReportSnapshotView,
  type TemplateVersionView,
  createLetterDraft,
  createReportDraft,
  createReportExport,
  createReportSnapshot,
  createTemplateVersion,
  getDocumentVersions,
  getDocuments,
  getIssues,
  getReportDrafts,
  getTemplateVersions,
  recordReportEvent,
  updateReportDraftText
} from "../../api/client";

type Props = {
  studyId: string;
  siteId: string;
};

type TemplateCandidate = {
  document: DocumentView;
  version: DocumentVersionView;
};

export type TemplateKind = "letter" | "report" | "track";

export function defaultTemplateMapping(
  kind: TemplateKind
): Record<string, unknown> {
  if (kind === "track") {
    return {
      xlsx: {
        cells: {},
        table: {
          sheet: "Track",
          start_row: 2,
          columns: {
            A: "issue_number",
            B: "section",
            C: "original_finding",
            D: "location",
            E: "recommendation",
            F: "status",
            G: "known_progress",
            H: "next_steps_text",
            I: "source_refs_text"
          }
        },
        required_variables: []
      }
    };
  }
  return {
    docx: {
      fields: {
        study_code: "study_code",
        site_code: "site_code",
        site_name: "site_name",
        visit_title: "visit_title",
        generated_on: "generated_on",
        visit_scope_note: "visit_scope_note",
        coverage_summary: "coverage_summary",
        not_checked_summary: "not_checked_summary",
        next_steps_summary: "next_steps_summary",
        user_summary: "user_summary",
        user_conclusion: "user_conclusion"
      },
      loops:
        kind === "letter"
          ? { letter_issues: "letter_issues" }
          : {
              prior_issues: "prior_issues",
              current_findings: "current_findings"
            },
      required_variables:
        kind === "letter"
          ? ["study_code"]
          : ["study_code", "user_summary", "user_conclusion"]
    }
  };
}

export function snapshotStatusLabel(status: string): string {
  if (status === "issued") return "已签发";
  if (status === "prepared") return "已固定快照";
  return status;
}

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "报告操作失败";
}

function visitKey(studyId: string, siteId: string): string {
  return `cra.w06.visit.${studyId}.${siteId}`;
}

export function ReportPreview({ studyId, siteId }: Props) {
  const [templates, setTemplates] = useState<TemplateVersionView[]>([]);
  const [candidates, setCandidates] = useState<TemplateCandidate[]>([]);
  const [drafts, setDrafts] = useState<ReportDraftView[]>([]);
  const [issues, setIssues] = useState<IssueView[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<ReportDraftView | null>(
    null
  );
  const [snapshot, setSnapshot] = useState<ReportSnapshotView | null>(null);
  const [letterIssueIds, setLetterIssueIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [nextTemplates, documents, nextDrafts, nextIssues] =
        await Promise.all([
          getTemplateVersions(studyId, siteId),
          getDocuments(studyId, siteId),
          getReportDrafts(studyId, siteId),
          getIssues(studyId, siteId)
        ]);
      const nextCandidates: TemplateCandidate[] = [];
      for (const document of documents.filter(
        (item) => item.purpose === "template"
      )) {
        const versions = await getDocumentVersions(document.id);
        if (versions[0]) {
          nextCandidates.push({ document, version: versions[0] });
        }
      }
      setTemplates(nextTemplates);
      setCandidates(nextCandidates);
      setDrafts(nextDrafts);
      setIssues(nextIssues);
      setSelectedDraft((current) => {
        if (!current) return nextDrafts[0] ?? null;
        return (
          nextDrafts.find((item) => item.id === current.id) ??
          nextDrafts[0] ??
          null
        );
      });
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [siteId, studyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function registerTemplate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const versionId = String(form.get("version_id") ?? "");
    const kind = String(form.get("output_kind") ?? "report") as TemplateKind;
    const candidate = candidates.find(
      (item) => item.version.id === versionId
    );
    if (!candidate) {
      setError("请选择已上传的模板版本。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createTemplateVersion({
        sourceDocumentVersionId: versionId,
        title: String(form.get("title") ?? candidate.document.title),
        outputKind: kind,
        mapping: defaultTemplateMapping(kind),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage("模板版本与受控字段/循环区映射已登记。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function templateFor(kind: TemplateKind): TemplateVersionView | undefined {
    return templates.find((item) => item.output_kind === kind);
  }

  function currentVisitId(): string | null {
    return window.localStorage.getItem(visitKey(studyId, siteId));
  }

  async function createLetter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const visitId = currentVisitId();
    const template = templateFor("letter");
    if (!visitId || !template) {
      setError("需要先建立中心监查，并登记 letter DOCX 模板。");
      return;
    }
    if (letterIssueIds.length === 0) {
      setError("访视信至少选择一项遗留。");
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const draft = await createLetterDraft({
        visitId,
        templateVersionId: template.id,
        selectedIssueIds: letterIssueIds,
        title: String(form.get("title") ?? ""),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setSelectedDraft(draft);
      setMessage("访视信草稿已生成；完整遗留清单未改变。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function createReport() {
    const visitId = currentVisitId();
    const template = templateFor("report");
    if (!visitId || !template) {
      setError("需要先建立中心监查，并登记 report DOCX 模板。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const draft = await createReportDraft({
        visitId,
        templateVersionId: template.id,
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setSelectedDraft(draft);
      setMessage("监查报告草稿已从同一问题、覆盖、事实和规则记录生成。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveText(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDraft) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const draft = await updateReportDraftText(selectedDraft, {
        textUpdates: {
          summary: String(form.get("summary") ?? ""),
          conclusion: String(form.get("conclusion") ?? ""),
          coverage_scope: String(form.get("coverage_scope") ?? "")
        },
        status: String(form.get("status") ?? "ready") as "draft" | "ready",
        idempotencyKey: crypto.randomUUID()
      });
      setSelectedDraft(draft);
      await load();
      setSelectedDraft(draft);
      setMessage("文字修改已单独保存；事实、规则和问题版本未改动。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function makeSnapshot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedDraft) return;
    const form = new FormData(event.currentTarget);
    const status = String(form.get("status") ?? "prepared") as
      | "prepared"
      | "issued";
    setBusy(true);
    setError(null);
    try {
      const result = await createReportSnapshot(selectedDraft, {
        status,
        acknowledgeUnknowns: form.get("acknowledge_unknowns") === "on",
        userStatement: String(form.get("user_statement") ?? ""),
        idempotencyKey: crypto.randomUUID()
      });
      setSnapshot(result);
      setMessage(
        status === "issued"
          ? "报告快照已按用户明确声明记录为已签发。"
          : "报告内容及输入版本已固定，尚未表示签发或发送。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function exportSnapshot(kind: TemplateKind) {
    if (!snapshot) return;
    const template = templateFor(kind);
    if (!template) {
      setError(`尚未登记 ${kind} 导出模板。`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const exported = await createReportExport({
        snapshotId: snapshot.id,
        templateVersionId: template.id,
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setSnapshot((current) =>
        current
          ? {
              ...current,
              exports: [...current.exports, exported]
            }
          : current
      );
      setMessage("实际 Office 文件已生成到私有存储；导出不代表已发送。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function markSubmitted(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!snapshot) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      setSnapshot(
        await recordReportEvent(snapshot, {
          eventType: "submitted",
          userStatement: String(form.get("statement") ?? ""),
          idempotencyKey: crypto.randomUUID()
        })
      );
      setMessage("实际提交记录已单独保存；报告内容未改写。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function toggleLetterIssue(id: string) {
    setLetterIssueIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  }

  const currentReport = selectedDraft;
  return (
    <section className="workspace-module reports-module" aria-labelledby="reports-title">
      <div className="module-heading">
        <div>
          <p className="eyebrow">W11 · LETTER / REPORT / TRACK</p>
          <h2 id="reports-title">同一记录生成多份材料</h2>
          <p>
            旧问题与本次发现分栏，访视信只选指定事项；生成、导出、签发和提交分别记录。
          </p>
        </div>
        <span className="status-chip muted">{drafts.length} 份草稿</span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <div className="report-template-grid">
        <form className="subject-import-form" onSubmit={(event) => void registerTemplate(event)}>
          <p className="eyebrow">模板版本</p>
          <h3>登记受控字段映射</h3>
          <label>
            模板文件
            <select name="version_id" required>
              <option value="">选择已上传模板</option>
              {candidates.map((item) => (
                <option key={item.version.id} value={item.version.id}>
                  {item.document.title} · {item.version.version_label}
                </option>
              ))}
            </select>
          </label>
          <label>
            输出类型
            <select name="output_kind" defaultValue="report">
              <option value="letter">访视信 DOCX</option>
              <option value="report">监查报告 DOCX</option>
              <option value="track">Excel Track</option>
            </select>
          </label>
          <label>
            映射名称
            <input name="title" placeholder="项目报告模板 v1" required />
          </label>
          <button className="secondary-button" type="submit" disabled={busy || candidates.length === 0}>
            登记标准映射
          </button>
          <p className="security-note">
            DOCX 仅接受声明的字段和循环标签；不执行任意 Jinja 表达式。
          </p>
        </form>

        <section className="source-reference">
          <p className="eyebrow">已登记模板</p>
          {templates.length === 0 ? (
            <p>尚无模板映射。</p>
          ) : (
            templates.map((template) => (
              <div key={template.id}>
                <strong>{template.title}</strong>
                <small>
                  {template.output_kind} · {template.output_format} ·{" "}
                  {template.supported_fields.length} 个受控字段
                </small>
              </div>
            ))
          )}
        </section>
      </div>

      <div className="report-create-grid">
        <form className="source-reference" onSubmit={(event) => void createLetter(event)}>
          <p className="eyebrow">访视信</p>
          <h3>只选需要沟通的事项</h3>
          <label>
            标题
            <input name="title" placeholder="访视前遗留确认" />
          </label>
          <div className="report-issue-checklist">
            {issues.map((issue) => (
              <label key={issue.id}>
                <input
                  type="checkbox"
                  checked={letterIssueIds.includes(issue.id)}
                  onChange={() => toggleLetterIssue(issue.id)}
                />
                {issue.issue_number} · {issue.original_finding ?? "unknown"}
              </label>
            ))}
          </div>
          <button className="secondary-button" type="submit" disabled={busy || !templateFor("letter")}>
            生成访视信草稿
          </button>
        </form>

        <section className="source-reference">
          <p className="eyebrow">监查报告</p>
          <h3>旧问题与本次发现分栏</h3>
          <p>
            报告复用当前监查中心的问题、核查覆盖、事实、规则和安全分析记录，不重新维护另一份状态。
          </p>
          <button className="primary-button compact" type="button" disabled={busy || !templateFor("report")} onClick={() => void createReport()}>
            生成监查报告草稿
          </button>
        </section>
      </div>

      <div className="report-draft-layout">
        <aside className="report-draft-list">
          <p className="eyebrow">草稿</p>
          {drafts.map((draft) => (
            <button
              key={draft.id}
              type="button"
              className={draft.id === currentReport?.id ? "active" : ""}
              onClick={() => {
                setSelectedDraft(draft);
                setSnapshot(null);
              }}
            >
              <strong>{draft.title}</strong>
              <small>
                {draft.output_kind} · {draft.status} · r{draft.revision}
              </small>
            </button>
          ))}
        </aside>

        <section className="report-preview">
          {!currentReport ? (
            <p>尚无报告草稿。</p>
          ) : (
            <>
              <header>
                <div>
                  <p className="eyebrow">草稿预览</p>
                  <h3>{currentReport.title}</h3>
                </div>
                <span className="status-chip">
                  {currentReport.output_kind} · r{currentReport.revision}
                </span>
              </header>
              <div className="report-warning-grid">
                <span>未知：{currentReport.unknowns.length}</span>
                <span>未核查：{currentReport.not_checked.length}</span>
                <span>缺失字段：{currentReport.missing_fields.join("、") || "无"}</span>
              </div>
              <p>{String(currentReport.content.scope_notice ?? "")}</p>
              <p>{String(currentReport.content.coverage_summary ?? "")}</p>
              <p>{String(currentReport.content.not_checked_summary ?? "")}</p>
              {Array.isArray(currentReport.content.review_sections) &&
                currentReport.content.review_sections.length > 0 && (
                  <section className="source-reference report-review-backfill">
                    <p className="eyebrow">模板核查回填</p>
                    {(currentReport.content.review_sections as Array<{
                      section_key: string;
                      section_title: string;
                      items: Array<{
                        item_key: string;
                        question: string;
                        status: string;
                        note: string;
                        source_locator: string;
                      }>;
                    }>).map((section) => (
                      <div key={section.section_key}>
                        <strong>{section.section_title}</strong>
                        <ul>
                          {section.items.map((item) => (
                            <li key={item.item_key}>
                              <strong>{item.item_key}</strong>{" "}
                              {item.question} · {item.status}
                              {item.note ? ` · ${item.note}` : ""}
                              <small>来源：{item.source_locator}</small>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </section>
                )}

              <form className="report-text-form" onSubmit={(event) => void saveText(event)}>
                <label>
                  CRA说明
                  <textarea
                    name="summary"
                    rows={3}
                    defaultValue={currentReport.user_text.summary ?? ""}
                  />
                </label>
                <label>
                  核查范围说明
                  <textarea
                    name="coverage_scope"
                    rows={3}
                    defaultValue={currentReport.user_text.coverage_scope ?? ""}
                  />
                </label>
                <label>
                  结论
                  <textarea
                    name="conclusion"
                    rows={3}
                    defaultValue={currentReport.user_text.conclusion ?? ""}
                  />
                </label>
                <button className="secondary-button" type="submit" disabled={busy}>
                  保存文案并标记可审阅
                </button>
              </form>

              <form className="report-snapshot-form" onSubmit={(event) => void makeSnapshot(event)}>
                <h4>固定快照</h4>
                <label>
                  状态
                  <select name="status" defaultValue="issued">
                    <option value="prepared">仅固定，未签发</option>
                    <option value="issued">用户确认已签发</option>
                  </select>
                </label>
                <label>
                  用户声明
                  <input name="user_statement" placeholder="例：本报告已按项目流程签发" />
                </label>
                <label className="checkbox-row">
                  <input name="acknowledge_unknowns" type="checkbox" />
                  已看到 unknown/未核查范围，不将其视为正常
                </label>
                <button className="primary-button compact" type="submit" disabled={busy}>
                  生成不可变快照
                </button>
              </form>
            </>
          )}

          {snapshot && (
            <section className="report-snapshot-result">
              <p className="eyebrow">不可变快照 r{snapshot.snapshot_number}</p>
              <h3>{snapshotStatusLabel(snapshot.status)}</h3>
              <small>内容摘要 {snapshot.content_hash.slice(0, 16)}…</small>
              <div className="action-buttons">
                {currentReport?.output_kind === "report" && (
                  <button className="secondary-button" type="button" disabled={busy} onClick={() => void exportSnapshot("report")}>
                    导出报告 DOCX
                  </button>
                )}
                {currentReport?.output_kind === "letter" && (
                  <button className="secondary-button" type="button" disabled={busy} onClick={() => void exportSnapshot("letter")}>
                    导出访视信 DOCX
                  </button>
                )}
                <button className="secondary-button" type="button" disabled={busy} onClick={() => void exportSnapshot("track")}>
                  导出 Excel Track
                </button>
              </div>
              {snapshot.exports.map((item) => (
                <a
                  key={item.id}
                  className="report-download"
                  href={item.content_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {item.filename} · {item.output_format.toUpperCase()}
                </a>
              ))}
              {snapshot.events.length > 0 && (
                <p>
                  实际提交/发送记录：
                  {snapshot.events
                    .map((event) => `${event.event_type} @ ${new Date(event.occurred_at).toLocaleString()}`)
                    .join("；")}
                </p>
              )}
              {snapshot.status === "issued" && (
                <form onSubmit={(event) => void markSubmitted(event)}>
                  <label>
                    记录实际提交
                    <input
                      name="statement"
                      placeholder="仅在实际提交后填写"
                      required
                    />
                  </label>
                  <button className="text-button" type="submit" disabled={busy}>
                    用户确认已提交
                  </button>
                </form>
              )}
            </section>
          )}
        </section>
      </div>
    </section>
  );
}
