import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  ApiError,
  type DocumentVersionView,
  type DocumentView,
  type JobView,
  type ParseCoverageView,
  type SourceAnchorView,
  documentContentUrl,
  getDocumentVersions,
  getDocuments,
  getJob,
  getVersionAnchors,
  getVersionCoverage,
  retryJob,
  uploadDocument
} from "../../api/client";
import { SourcePdfViewer } from "../../components/SourcePdfViewer";

type Props = {
  studyId: string;
  siteId: string;
};

const STATUS_LABEL: Record<string, string> = {
  pending: "等待处理",
  running: "正在解析",
  completed: "解析完成",
  partial: "部分解析",
  failed: "解析失败",
  queued: "已排队",
  succeeded: "已完成"
};

function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status;
}

export function DocumentWorkspace({ studyId, siteId }: Props) {
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  );
  const [versions, setVersions] = useState<DocumentVersionView[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    null
  );
  const [anchors, setAnchors] = useState<SourceAnchorView[]>([]);
  const [coverage, setCoverage] = useState<ParseCoverageView[]>([]);
  const [selectedAnchorId, setSelectedAnchorId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<JobView | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId]
  );
  const selectedVersion = useMemo(
    () => versions.find((version) => version.id === selectedVersionId) ?? null,
    [versions, selectedVersionId]
  );
  const selectedAnchor = useMemo(
    () => anchors.find((anchor) => anchor.id === selectedAnchorId) ?? null,
    [anchors, selectedAnchorId]
  );
  const coverageCounts = useMemo(() => {
    return coverage.reduce<Record<string, number>>((counts, unit) => {
      counts[unit.status] = (counts[unit.status] ?? 0) + 1;
      return counts;
    }, {});
  }, [coverage]);

  const loadDocuments = useCallback(async () => {
    setError(null);
    try {
      const next = await getDocuments(studyId, siteId);
      setDocuments(next);
      setSelectedDocumentId((current) =>
        current && next.some((document) => document.id === current)
          ? current
          : next[0]?.id ?? null
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "资料列表加载失败");
    }
  }, [studyId, siteId]);

  const loadVersion = useCallback(async (versionId: string) => {
    setSelectedVersionId(versionId);
    setError(null);
    try {
      const [nextAnchors, nextCoverage] = await Promise.all([
        getVersionAnchors(versionId),
        getVersionCoverage(versionId)
      ]);
      setAnchors(nextAnchors);
      setCoverage(nextCoverage);
      setSelectedAnchorId(nextAnchors[0]?.id ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "来源定位加载失败");
    }
  }, []);

  const loadVersions = useCallback(
    async (documentId: string) => {
      try {
        const next = await getDocumentVersions(documentId);
        setVersions(next);
        if (next[0]) {
          await loadVersion(next[0].id);
        } else {
          setSelectedVersionId(null);
          setAnchors([]);
          setCoverage([]);
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "版本加载失败");
      }
    },
    [loadVersion]
  );

  useEffect(() => {
    setDocuments([]);
    setVersions([]);
    setAnchors([]);
    setCoverage([]);
    setActiveJob(null);
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (selectedDocumentId) {
      void loadVersions(selectedDocumentId);
    }
  }, [loadVersions, selectedDocumentId]);

  useEffect(() => {
    if (!activeJob || !["queued", "running"].includes(activeJob.status)) {
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const next = await getJob(activeJob.id);
        setActiveJob(next);
        if (["succeeded", "failed"].includes(next.status)) {
          await loadDocuments();
          if (selectedDocumentId) {
            await loadVersions(selectedDocumentId);
          }
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "作业状态读取失败");
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [
    activeJob,
    loadDocuments,
    loadVersions,
    selectedDocumentId
  ]);

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("file");
    if (!(file instanceof File) || !file.name) {
      setError("请选择合成资料文件。");
      setBusy(false);
      return;
    }
    try {
      const uploaded = await uploadDocument(studyId, siteId, {
        title: String(form.get("title") ?? ""),
        documentType: String(form.get("document_type") ?? "protocol"),
        purpose: String(form.get("purpose") ?? "rule"),
        versionLabel: String(form.get("version_label") ?? "v1"),
        publishedOn: String(form.get("published_on") ?? ""),
        userStartsOn: String(form.get("user_starts_on") ?? ""),
        file,
        idempotencyKey: crypto.randomUUID()
      });
      setMessage(
        uploaded.replayed
          ? "重复提交已识别，沿用原有版本。"
          : "资料已私有保存，解析任务已提交。"
      );
      setActiveJob(await getJob(uploaded.job_id));
      await loadDocuments();
      setSelectedDocumentId(uploaded.document_id);
      formElement.reset();
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? `${reason.message}（${reason.code}）`
          : reason instanceof Error
            ? reason.message
            : "资料上传失败"
      );
    } finally {
      setBusy(false);
    }
  }

  async function retryActiveJob() {
    if (!activeJob) {
      return;
    }
    setBusy(true);
    try {
      await retryJob(activeJob.id);
      setActiveJob(await getJob(activeJob.id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "重试提交失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="document-workspace" aria-labelledby="documents-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M02 · 私有项目资料</p>
          <h2 id="documents-title">资料与原文定位</h2>
          <p>原文件不覆盖；上传时间与手动开始使用日期分开记录。</p>
        </div>
        <span className="status-chip muted">{documents.length} 份资料</span>
      </div>

      <form className="upload-form" onSubmit={(event) => void submitUpload(event)}>
        <label>
          资料名称
          <input name="title" required maxLength={255} defaultValue="合成项目资料" />
        </label>
        <label>
          资料类型
          <select name="document_type" defaultValue="protocol">
            <option value="protocol">方案</option>
            <option value="ib">IB</option>
            <option value="sop">SOP</option>
            <option value="monitoring_plan">监查计划</option>
            <option value="qa">Q&amp;A</option>
            <option value="manual">手册</option>
            <option value="report">历史报告</option>
            <option value="track">Track</option>
            <option value="directory">目录</option>
            <option value="template">模板</option>
            <option value="text">文字</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label>
          业务用途
          <select name="purpose" defaultValue="rule">
            <option value="rule">规则依据</option>
            <option value="fact">事实资料</option>
            <option value="carryover_report">遗留来源报告</option>
            <option value="track">问题Track</option>
            <option value="directory">文件目录对照</option>
            <option value="template">报告模板</option>
            <option value="other">其他</option>
          </select>
        </label>
        <label>
          业务版本
          <input name="version_label" required defaultValue="v1" maxLength={64} />
        </label>
        <label>
          文件发布日期
          <input type="date" name="published_on" />
        </label>
        <label>
          手动开始使用日
          <input type="date" name="user_starts_on" />
        </label>
        <label className="file-field">
          合成资料文件
          <input
            type="file"
            name="file"
            accept=".docx,.pdf,.txt,.csv,.xlsx,.png,.jpg,.jpeg"
            required
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "正在提交…" : "上传并解析"}
          </button>
        </div>
      </form>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}
      {activeJob && (
        <div className="notice" role="status">
          <strong>解析任务：{statusLabel(activeJob.status)}</strong>
          <span>
            尝试 {activeJob.attempts}/{activeJob.max_attempts}
            {activeJob.error_summary
              ? ` · ${activeJob.error_summary}`
              : " · 失败页、背景和未支持项会分别显示"}
          </span>
          {activeJob.status === "failed" &&
            activeJob.attempts < activeJob.max_attempts && (
              <button
                className="text-button"
                type="button"
                onClick={() => void retryActiveJob()}
                disabled={busy}
              >
                重试
              </button>
            )}
        </div>
      )}

      {documents.length === 0 ? (
        <p className="empty-documents">
          当前中心尚无资料。W03 仅接收和定位原文，不自动生成临床结论。
        </p>
      ) : (
        <div className="document-grid">
          <div className="document-list" aria-label="资料列表">
            {documents.map((document) => (
              <button
                type="button"
                key={document.id}
                className={document.id === selectedDocumentId ? "active" : ""}
                onClick={() => setSelectedDocumentId(document.id)}
              >
                {document.title}
                <small>
                  {document.document_type} · {document.purpose} · v
                  {document.revision}
                </small>
              </button>
            ))}
          </div>

          <div className="source-detail">
            {selectedDocument && (
              <>
                <h3>{selectedDocument.title}</h3>
                {selectedVersion ? (
                  <>
                    <div className="source-meta">
                      <span>版本 {selectedVersion.version_label}</span>
                      <span>{statusLabel(selectedVersion.parse_status)}</span>
                      <span>{selectedVersion.original_filename}</span>
                      <span>
                        开始使用 {selectedVersion.user_starts_on ?? "未设置"}
                      </span>
                      <span>SHA {selectedVersion.sha256.slice(0, 10)}…</span>
                    </div>
                    <div className="coverage-summary" aria-label="解析覆盖统计">
                      {Object.entries(coverageCounts).map(([status, count]) => (
                        <span
                          key={status}
                          className={`coverage-pill ${status}`}
                        >
                          {statusLabel(status)} {count}
                        </span>
                      ))}
                    </div>
                    {selectedVersion.media_type === "application/pdf" &&
                      selectedAnchor?.page_number && (
                        <SourcePdfViewer
                          url={documentContentUrl(selectedVersion.id)}
                          pageNumber={selectedAnchor.page_number}
                          bbox={selectedAnchor.bbox}
                        />
                      )}
                    <div className="anchor-list" aria-label="原文锚点">
                      {anchors.map((anchor) => (
                        <article className="anchor-item" key={anchor.id}>
                          <button
                            type="button"
                            onClick={() => setSelectedAnchorId(anchor.id)}
                          >
                            {anchor.text}
                          </button>
                          <small>
                            {anchor.anchor_type} · {anchor.logical_node_id}
                            {anchor.page_number
                              ? ` · 第 ${anchor.page_number} 页`
                              : ""}
                          </small>
                          <p>{anchor.section_path.join(" → ") || "未设章节"}</p>
                        </article>
                      ))}
                    </div>
                    {coverage.some(
                      (unit) =>
                        unit.status === "unsupported" || unit.status === "failed"
                      ) &&
                      anchors.length === 0 && (
                        <p className="empty-documents">
                          该格式当前仅作私有原文件保留，结构化解析由后续任务负责。
                        </p>
                      )}
                  </>
                ) : (
                  <p className="viewer-loading">该资料尚无版本。</p>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
