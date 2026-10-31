import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type DocumentVersionView,
  type DocumentView,
  type HandoverSummaryView,
  type StageChecklistItemView,
  type StageChecklistView,
  addStageChecklistItem,
  createStageChecklist,
  getDocumentVersions,
  getDocuments,
  getHandoverSummary,
  getStageChecklists,
  verifyStageChecklistItem
} from "../../api/client";

type Props = {
  studyId: string;
  siteId: string;
};

type SourceCandidate = {
  document: DocumentView;
  version: DocumentVersionView;
};

export function stageStatusLabel(status: string): string {
  if (status === "confirmed") return "已确认";
  if (status === "not_applicable") return "不适用";
  if (status === "unknown") return "未知";
  return "待核查";
}

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "阶段清单操作失败";
}

function storedVisitKey(studyId: string, siteId: string): string {
  return `cra.w06.visit.${studyId}.${siteId}`;
}

export function StageChecklist({ studyId, siteId }: Props) {
  const [checklists, setChecklists] = useState<StageChecklistView[]>([]);
  const [sources, setSources] = useState<SourceCandidate[]>([]);
  const [handover, setHandover] = useState<HandoverSummaryView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [nextChecklists, documents] = await Promise.all([
        getStageChecklists(studyId, siteId),
        getDocuments(studyId, siteId)
      ]);
      const nextSources: SourceCandidate[] = [];
      for (const document of documents.filter((item) =>
        ["rule", "directory", "template", "other"].includes(item.purpose)
      )) {
        const versions = await getDocumentVersions(document.id);
        if (versions[0]) {
          nextSources.push({ document, version: versions[0] });
        }
      }
      setChecklists(nextChecklists);
      setSources(nextSources);
      const visitId = window.localStorage.getItem(
        storedVisitKey(studyId, siteId)
      );
      if (visitId) {
        try {
          setHandover(await getHandoverSummary(visitId));
        } catch (reason) {
          if (reason instanceof ApiError && reason.status === 404) {
            window.localStorage.removeItem(storedVisitKey(studyId, siteId));
            setHandover(null);
          } else {
            throw reason;
          }
        }
      } else {
        setHandover(null);
      }
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [siteId, studyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createChecklist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await createStageChecklist({
        studyId,
        siteId,
        stage: String(form.get("stage") ?? "startup") as
          | "startup"
          | "closeout",
        title: String(form.get("title") ?? ""),
        sourceDocumentVersionId: String(
          form.get("source_document_version_id") ?? ""
        ),
        itemKey: String(form.get("item_key") ?? ""),
        itemTitle: String(form.get("item_title") ?? ""),
        requirement: String(form.get("requirement") ?? ""),
        sourceLocator: String(form.get("source_locator") ?? ""),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage(
        "阶段清单已按项目资料建立；每项保留来源，完成清单不等于中心获批关闭。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function addItem(
    event: FormEvent<HTMLFormElement>,
    checklist: StageChecklistView
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await addStageChecklistItem(checklist, {
        sourceDocumentVersionId: String(
          form.get("source_document_version_id") ?? ""
        ),
        itemKey: String(form.get("item_key") ?? ""),
        itemTitle: String(form.get("item_title") ?? ""),
        requirement: String(form.get("requirement") ?? ""),
        sourceLocator: String(form.get("source_locator") ?? ""),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage("已从项目资料增加阶段要求，并保留具体来源。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function verifyItem(
    event: FormEvent<HTMLFormElement>,
    item: StageChecklistItemView
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await verifyStageChecklistItem(item, {
        status: String(form.get("status") ?? item.status),
        note: String(form.get("note") ?? ""),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage("清单项状态已保存；系统未生成中心关闭批准。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const existingStages = new Set(checklists.map((item) => item.stage));

  return (
    <section className="workspace-module stage-checklist-module" aria-labelledby="stage-checklist-title">
      <div className="module-heading">
        <div>
          <p className="eyebrow">W10 · STARTUP / CLOSEOUT</p>
          <h2 id="stage-checklist-title">项目阶段清单与简洁交接</h2>
          <p>
            启动和关闭要求来自项目资料并保留具体来源；清单完成只代表已记录核查状态。
          </p>
        </div>
        <span className="status-chip muted">{checklists.length} 份清单</span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      {checklists.length < 2 && (
        <form
          className="subject-import-form stage-checklist-create"
          onSubmit={(event) => void createChecklist(event)}
        >
          <p className="eyebrow">项目资料配置</p>
          <h3>建立启动或关闭清单</h3>
          <label>
            阶段
            <select name="stage" defaultValue={existingStages.has("startup") ? "closeout" : "startup"}>
              {!existingStages.has("startup") && <option value="startup">中心启动</option>}
              {!existingStages.has("closeout") && <option value="closeout">中心关闭</option>}
            </select>
          </label>
          <label>
            清单名称
            <input name="title" defaultValue="项目阶段核查清单" required />
          </label>
          <label>
            项目资料版本
            <select name="source_document_version_id" required>
              <option value="">选择方案/SOP/手册等</option>
              {sources.map((item) => (
                <option key={item.version.id} value={item.version.id}>
                  {item.document.title} · {item.version.version_label}
                </option>
              ))}
            </select>
          </label>
          <label>
            首项编号
            <input name="item_key" defaultValue="S01" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,63}" required />
          </label>
          <label>
            首项名称
            <input name="item_title" required />
          </label>
          <label>
            具体要求
            <textarea name="requirement" rows={2} required />
          </label>
          <label>
            原文位置
            <input name="source_locator" placeholder="第4.2节 / 表格第3行" required />
          </label>
          <button className="primary-button compact" type="submit" disabled={busy || sources.length === 0}>
            建立清单
          </button>
        </form>
      )}

      <div className="stage-checklist-list">
        {checklists.map((checklist) => (
          <article className="stage-checklist-card" key={checklist.id}>
            <header>
              <div>
                <p className="eyebrow">
                  {checklist.stage === "startup" ? "STARTUP" : "CLOSEOUT"}
                </p>
                <h3>{checklist.title}</h3>
                <small>
                  {checklist.items.length} 项 · revision {checklist.revision}
                </small>
              </div>
              <span className="status-chip">
                {checklist.all_items_confirmed ? "清单项已确认" : "仍有待核查项"}
              </span>
            </header>
            <p className="directory-coverage">{checklist.limitation}</p>

            <div className="stage-checklist-items">
              {checklist.items.map((item) => (
                <article key={item.id} className={`stage-checklist-item ${item.status}`}>
                  <div>
                    <strong>{item.item_key} · {item.title}</strong>
                    <span>{stageStatusLabel(item.status)}</span>
                    <p>{item.requirement}</p>
                    <details>
                      <summary>查看来源</summary>
                      <ul>
                        {item.source_refs.map((source, index) => (
                          <li key={`${item.id}-source-${index}`}>
                            {String(source.locator ?? source.source_type ?? "项目资料")}
                            {" · "}
                            {item.source_document_version_id}
                          </li>
                        ))}
                      </ul>
                    </details>
                    {item.completed_at && (
                      <small>
                        {item.completed_by} · {new Date(item.completed_at).toLocaleString()}
                      </small>
                    )}
                  </div>
                  <form onSubmit={(event) => void verifyItem(event, item)}>
                    <label>
                      状态
                      <select name="status" defaultValue={item.status}>
                        <option value="open">待核查</option>
                        <option value="confirmed">已确认</option>
                        <option value="not_applicable">不适用</option>
                        <option value="unknown">未知</option>
                      </select>
                    </label>
                    <label>
                      说明
                      <input name="note" defaultValue={item.completion_note ?? ""} />
                    </label>
                    <button className="secondary-button" type="submit" disabled={busy}>
                      保存清单项
                    </button>
                  </form>
                </article>
              ))}
            </div>

            <form
              className="stage-checklist-add"
              onSubmit={(event) => void addItem(event, checklist)}
            >
              <h4>从项目资料补一项</h4>
              <label>
                编号
                <input name="item_key" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,63}" required />
              </label>
              <label>
                名称
                <input name="item_title" required />
              </label>
              <label>
                要求
                <textarea name="requirement" rows={2} required />
              </label>
              <label>
                资料版本
                <select name="source_document_version_id" required>
                  {sources.map((item) => (
                    <option key={item.version.id} value={item.version.id}>
                      {item.document.title} · {item.version.version_label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                原文位置
                <input name="source_locator" required />
              </label>
              <button className="secondary-button" type="submit" disabled={busy || sources.length === 0}>
                增加清单项
              </button>
            </form>
          </article>
        ))}
      </div>

      <section className="handover-summary">
        <div>
          <p className="eyebrow">简洁交接 · 复用原记录</p>
          <h3>无遗留时简述；有遗留时交代现状与后续</h3>
        </div>
        {!handover ? (
          <p>先建立或打开本次中心监查，系统将从原 Issue 与清单生成交接摘要。</p>
        ) : (
          <>
            <p className="handover-copy">{handover.summary}</p>
            {handover.issues.length > 0 && (
              <ol>
                {handover.issues.map((issue) => (
                  <li key={issue.id}>
                    <strong>{issue.issue_number}</strong> · {issue.known_progress ?? "进展待复核"}
                    <small>后续：{issue.next_steps.join("；")}</small>
                  </li>
                ))}
              </ol>
            )}
            {handover.incomplete_checklist_items.length > 0 && (
              <p>
                未完清单项：
                {handover.incomplete_checklist_items
                  .map((item) => `${item.title}（${stageStatusLabel(item.status)}）`)
                  .join("、")}
              </p>
            )}
            <p className="security-note">{handover.limitation}</p>
          </>
        )}
      </section>
    </section>
  );
}
