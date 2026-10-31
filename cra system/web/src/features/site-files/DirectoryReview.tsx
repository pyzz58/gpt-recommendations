import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type DirectoryReferenceView,
  type DocumentVersionView,
  type DocumentView,
  type SiteFileItemView,
  addDirectoryItem,
  createDirectoryReference,
  documentContentUrl,
  getDocumentVersions,
  getDocuments,
  getSiteFileStatus,
  verifySiteFile
} from "../../api/client";

type Props = {
  studyId: string;
  siteId: string;
};

type DirectoryCandidate = {
  document: DocumentView;
  version: DocumentVersionView;
};

export function applicabilityLabel(value: string): string {
  if (value === "required") return "应有";
  if (value === "not_required") return "不适用";
  return "适用性未知";
}

export function acquisitionLabel(value: string): string {
  if (value === "provided") return "已取得";
  if (value === "not_seen") return "未见";
  return "取得情况未知";
}

export function verificationLabel(value: string): string {
  if (value === "qualified") return "已核实合格";
  if (value === "pending") return "待核实";
  return "核实情况未知";
}

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "目录操作失败";
}

export function DirectoryReview({ studyId, siteId }: Props) {
  const [references, setReferences] = useState<DirectoryReferenceView[]>([]);
  const [candidates, setCandidates] = useState<DirectoryCandidate[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [nextReferences, documents] = await Promise.all([
        getSiteFileStatus(studyId, siteId),
        getDocuments(studyId, siteId)
      ]);
      const nextCandidates: DirectoryCandidate[] = [];
      for (const document of documents.filter(
        (item) => item.purpose === "directory"
      )) {
        const versions = await getDocumentVersions(document.id);
        if (versions[0]) {
          nextCandidates.push({ document, version: versions[0] });
        }
      }
      setReferences(nextReferences);
      setCandidates(nextCandidates);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [siteId, studyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createReference(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const candidate = candidates.find(
      (item) => item.version.id === String(form.get("version_id") ?? "")
    );
    if (!candidate) {
      setError("请先选择已上传的 ISF/TMF 目录版本。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createDirectoryReference({
        siteId,
        sourceDocumentVersionId: candidate.version.id,
        directoryKind: String(form.get("directory_kind") ?? "isf"),
        label: String(form.get("label") ?? candidate.document.title),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage(
        "原目录已建立 reference_only 对照；未结构化范围不会显示为全部合格。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function addItem(
    event: FormEvent<HTMLFormElement>,
    reference: DirectoryReferenceView
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await addDirectoryItem(reference, {
        itemKey: String(form.get("item_key") ?? ""),
        title: String(form.get("title") ?? ""),
        requirement: String(form.get("requirement") ?? ""),
        applicabilityStatus: String(
          form.get("applicability_status") ?? "required"
        ),
        acquisitionStatus: String(
          form.get("acquisition_status") ?? "not_seen"
        ),
        verificationStatus: String(
          form.get("verification_status") ?? "pending"
        ),
        sourceLocator: String(form.get("source_locator") ?? ""),
        issueId: String(form.get("issue_id") ?? "").trim(),
        actionId: String(form.get("action_id") ?? "").trim(),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage("已增量建立目录条目；未录入的目录范围仍保留为 unknown。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function verifyItem(
    event: FormEvent<HTMLFormElement>,
    item: SiteFileItemView
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await verifySiteFile(item, {
        applicabilityStatus: String(
          form.get("applicability_status") ?? item.applicability_status
        ),
        acquisitionStatus: String(
          form.get("acquisition_status") ?? item.acquisition_status
        ),
        verificationStatus: String(
          form.get("verification_status") ?? item.verification_status
        ),
        note: String(form.get("note") ?? ""),
        issueId: String(form.get("issue_id") ?? "").trim(),
        actionId: String(form.get("action_id") ?? "").trim(),
        idempotencyKey: crypto.randomUUID()
      });
      await load();
      setMessage(
        "文件状态已更新并保留上一条历史；M06 原问题与行动状态未被改写。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="workspace-module site-files-module" aria-labelledby="directory-title">
      <div className="module-heading">
        <div>
          <p className="eyebrow">W10 · ISF/TMF DIRECTORY</p>
          <h2 id="directory-title">原目录直接对照与缺件进展</h2>
          <p>
            原文件可作为对照底稿，条目按需逐步建立；应有、已取得和已核实合格分别记录。
          </p>
        </div>
        <span className="status-chip muted">{references.length} 个目录版本</span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <div className="site-files-grid">
        <form className="subject-import-form" onSubmit={(event) => void createReference(event)}>
          <p className="eyebrow">从 M02 原文件开始</p>
          <h3>建立目录参照</h3>
          <label>
            原目录版本
            <select name="version_id" required disabled={busy}>
              <option value="">选择已上传目录</option>
              {candidates.map((item) => (
                <option key={item.version.id} value={item.version.id}>
                  {item.document.title} · {item.version.version_label}
                </option>
              ))}
            </select>
          </label>
          <label>
            目录类型
            <select name="directory_kind" defaultValue="isf">
              <option value="isf">ISF</option>
              <option value="tmf">TMF</option>
              <option value="combined">ISF/TMF 合并</option>
              <option value="other">其他</option>
            </select>
          </label>
          <label>
            显示名称
            <input name="label" placeholder="例：项目 ISF 目录 v1" required />
          </label>
          <button className="primary-button compact" type="submit" disabled={busy || candidates.length === 0}>
            直接使用原目录对照
          </button>
          {candidates.length === 0 && (
            <p className="security-note">
              当前中心没有 purpose=directory 的已上传文件；先到资料模块上传合成目录。
            </p>
          )}
        </form>

        <section className="source-reference site-file-summary">
          <p className="eyebrow">当前状态</p>
          <h3>缺件与待核实分别显示</h3>
          <p>
            未见文件不等于内容不合格；文件已取得也不自动等于已核实合格。
          </p>
          <span className="status-chip">
            {references.reduce(
              (total, item) => total + item.missing_item_keys.length,
              0
            )}{" "}
            个未见适用条目
          </span>
        </section>
      </div>

      {references.map((reference) => (
        <article className="site-directory-card" key={reference.id}>
          <header>
            <div>
              <p className="eyebrow">
                {reference.directory_kind.toUpperCase()} · {reference.mode}
              </p>
              <h3>{reference.label}</h3>
              <small>
                {reference.original_filename} · revision {reference.revision}
              </small>
            </div>
            <a
              className="secondary-button link-button"
              href={documentContentUrl(reference.source_document_version_id)}
              target="_blank"
              rel="noreferrer"
            >
              打开原目录
            </a>
          </header>
          <p className="directory-coverage">{reference.coverage_note}</p>
          <p className="directory-change-summary">
            {reference.change_status === "compared"
              ? `与上一版本比较：新增 ${reference.new_item_keys.join("、") || "无"}；不再列出 ${
                  reference.removed_item_keys.join("、") || "无"
                }；状态变化 ${reference.changed_item_keys.join("、") || "无"}。`
              : reference.change_status ===
                  "comparison_unknown_without_structured_versions"
                ? "上一版本或当前版本尚未结构化，不能生成完整新增/缺件变化。"
                : "当前目录类型尚无上一版本可比较。"}
          </p>
          <div className="directory-status-line">
            <span>未见：{reference.missing_item_keys.join("、") || "无已识别项"}</span>
            <span>
              待核实：{reference.pending_verification_item_keys.join("、") || "无已识别项"}
            </span>
          </div>

          {reference.items.length > 0 ? (
            <div className="directory-item-list">
              {reference.items.map((item) => (
                <article className="directory-item" key={item.id}>
                  <div>
                    <strong>{item.item_key} · {item.title}</strong>
                    <small>
                      {applicabilityLabel(item.applicability_status)} ·{" "}
                      {acquisitionLabel(item.acquisition_status)} ·{" "}
                      {verificationLabel(item.verification_status)}
                    </small>
                    {item.requirement && <p>{item.requirement}</p>}
                    {item.source_refs.length > 0 && (
                      <details>
                        <summary>查看目录来源</summary>
                        <ul>
                          {item.source_refs.map((source, index) => (
                            <li key={`${item.id}-source-${index}`}>
                              {String(source.locator ?? source.source_type ?? "原目录")}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                  <form
                    className="directory-status-form"
                    onSubmit={(event) => void verifyItem(event, item)}
                  >
                    <label>
                      应有
                      <select name="applicability_status" defaultValue={item.applicability_status}>
                        <option value="required">应有</option>
                        <option value="not_required">不适用</option>
                        <option value="unknown">未知</option>
                      </select>
                    </label>
                    <label>
                      取得
                      <select name="acquisition_status" defaultValue={item.acquisition_status}>
                        <option value="not_seen">未见</option>
                        <option value="provided">已取得</option>
                        <option value="unknown">未知</option>
                      </select>
                    </label>
                    <label>
                      核实
                      <select name="verification_status" defaultValue={item.verification_status}>
                        <option value="pending">待核实</option>
                        <option value="qualified">已核实合格</option>
                        <option value="unknown">未知</option>
                      </select>
                    </label>
                    <label>
                      说明
                      <input name="note" defaultValue={item.verification_note ?? ""} />
                    </label>
                    <label>
                      Issue ID
                      <input name="issue_id" defaultValue={item.linked_issue_id ?? ""} />
                    </label>
                    <label>
                      Action ID
                      <input name="action_id" defaultValue={item.linked_action_id ?? ""} />
                    </label>
                    <button className="secondary-button" type="submit" disabled={busy}>
                      CRA确认并保存状态
                    </button>
                  </form>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-documents">
              reference_only：可直接打开原目录对照，当前未建立结构化条目。
            </p>
          )}

          <form
            className="directory-add-form"
            onSubmit={(event) => void addItem(event, reference)}
          >
            <h4>增量建立条目</h4>
            <label>
              编号
              <input name="item_key" placeholder="A01" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,63}" required />
            </label>
            <label>
              条目
              <input name="title" placeholder="合成文件名称" required />
            </label>
            <label>
              要求
              <textarea name="requirement" rows={2} />
            </label>
            <label>
              原目录位置
              <input name="source_locator" placeholder="第2页 / 第8行" />
            </label>
            <label>
              应有
              <select name="applicability_status" defaultValue="required">
                <option value="required">应有</option>
                <option value="not_required">不适用</option>
                <option value="unknown">未知</option>
              </select>
            </label>
            <label>
              取得
              <select name="acquisition_status" defaultValue="not_seen">
                <option value="not_seen">未见</option>
                <option value="provided">已取得</option>
                <option value="unknown">未知</option>
              </select>
            </label>
            <label>
              核实
              <select name="verification_status" defaultValue="pending">
                <option value="pending">待核实</option>
                <option value="qualified">已核实合格</option>
                <option value="unknown">未知</option>
              </select>
            </label>
            <label>
              关联 Issue ID（可选）
              <input name="issue_id" />
            </label>
            <label>
              关联 Action ID（可选）
              <input name="action_id" />
            </label>
            <button className="secondary-button" type="submit" disabled={busy}>
              增加条目
            </button>
          </form>
        </article>
      ))}
    </section>
  );
}
