"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  downloadKnowledgeVersion,
  fetchKnowledgeDocument,
  fetchKnowledgeDocuments,
  fetchTasks,
  notifyProjectChanged,
  searchKnowledge,
  uploadKnowledgeFile,
} from "@/lib/api";
import type {
  KnowledgeDocumentDetail,
  KnowledgeDocumentSummary,
  KnowledgeSearch,
  TaskView,
} from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatBytes,
  formatDate,
  stateLabel,
} from "@/components/ui";

type UploadProgress = {
  progress: number;
  state: "uploading" | "queued" | "failed";
  message?: string;
};

export default function KnowledgePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const inputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<KnowledgeDocumentSummary[]>([]);
  const [tasks, setTasks] = useState<TaskView[]>([]);
  const [selectedDocument, setSelectedDocument] =
    useState<KnowledgeDocumentDetail | null>(null);
  const [searchResult, setSearchResult] = useState<KnowledgeSearch | null>(null);
  const [query, setQuery] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [taskId, setTaskId] = useState("");
  const [uploads, setUploads] = useState<Record<string, UploadProgress>>({});
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  const loadDocuments = useCallback(
    async (titleQuery = query, signal?: AbortSignal) => {
      const next = await fetchKnowledgeDocuments(projectId, titleQuery, signal);
      setDocuments(next);
      return next;
    },
    [projectId, query],
  );

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [nextDocuments, nextTasks] = await Promise.all([
        fetchKnowledgeDocuments(projectId, "", signal),
        fetchTasks(projectId, signal),
      ]);
      setDocuments(nextDocuments);
      setTasks(nextTasks);
      setTaskId((current) => current || nextTasks[0]?.id || "");
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取知识资料");
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

  async function selectDocument(document: KnowledgeDocumentSummary) {
    setError("");
    try {
      setSelectedDocument(
        await fetchKnowledgeDocument(projectId, document.id),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法读取资料详情");
    }
  }

  async function uploadFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length === 0) return;
    const batchBytes = list.reduce((total, file) => total + file.size, 0);
    setError("");
    for (const file of list) {
      const key = `${file.name}:${file.size}:${file.lastModified}`;
      setUploads((current) => ({
        ...current,
        [key]: { progress: 0, state: "uploading" },
      }));
      try {
        await uploadKnowledgeFile(
          projectId,
          file,
          batchBytes,
          (progress) =>
            setUploads((current) => ({
              ...current,
              [key]: { progress, state: "uploading" },
            })),
        );
        setUploads((current) => ({
          ...current,
          [key]: { progress: 1, state: "queued" },
        }));
        for (let attempt = 0; attempt < 5; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 700));
          const next = await loadDocuments("");
          notifyProjectChanged();
          const ready = next.find((item) => item.filename === file.name);
          if (ready && !["queued", "extracting", "indexing"].includes(ready.ingest_state)) {
            break;
          }
        }
        setUploads((current) => {
          const next = { ...current };
          delete next[key];
          return next;
        });
      } catch (cause) {
        const message =
          cause instanceof Error ? cause.message : "上传或处理失败";
        setUploads((current) => ({
          ...current,
          [key]: { progress: 0, state: "failed", message },
        }));
      }
    }
    if (inputRef.current) inputRef.current.value = "";
  }

  async function runTitleFilter(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await loadDocuments(query);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法筛选资料");
    }
  }

  async function runEvidenceSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!taskId || !searchQuery.trim()) return;
    setSearching(true);
    setError("");
    try {
      setSearchResult(
        await searchKnowledge(projectId, taskId, searchQuery.trim()),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法执行证据检索");
    } finally {
      setSearching(false);
    }
  }

  async function downloadCurrent() {
    if (!selectedDocument?.document.version_id) return;
    try {
      await downloadKnowledgeVersion(
        projectId,
        selectedDocument.document.version_id,
        selectedDocument.document.filename ?? "document",
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法下载原件");
    }
  }

  if (loading) return <LoadingPanel label="正在读取项目资料…" />;
  if (error && documents.length === 0 && !selectedDocument) {
    return <ErrorPanel message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="knowledgePage">
      <div className="knowledgeMain">
        <section className="knowledgeIntro">
          <div>
            <p className="eyebrow">PROJECT KNOWLEDGE</p>
            <h2>保存原件，保留解析与版本状态</h2>
            <p>
              文件默认仅保存在当前项目、仅本地处理。可检索不代表数据真实、科学结论成立或已经过专家复核。
            </p>
          </div>
          <button
            type="button"
            className="button primary"
            onClick={() => inputRef.current?.click()}
          >
            上传资料
          </button>
          <input
            ref={inputRef}
            hidden
            multiple
            type="file"
            accept=".pdf,.docx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.eml"
            onChange={(event) => {
              if (event.target.files) void uploadFiles(event.target.files);
            }}
          />
        </section>

        {error && <ErrorPanel message={error} />}

        <div
          className={`dropZone ${dragging ? "dragging" : ""}`}
          onDragEnter={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            void uploadFiles(event.dataTransfer.files);
          }}
        >
          <strong>拖入文件，或点击“上传资料”</strong>
          <span>PDF / Word / Excel / CSV / 文本 / 图片 / EML</span>
        </div>

        {Object.entries(uploads).length > 0 && (
          <div className="uploadQueue" aria-live="polite">
            {Object.entries(uploads).map(([key, item]) => (
              <div className="uploadRow" key={key}>
                <div>
                  <strong>{key.split(":")[0]}</strong>
                  <span>
                    {item.state === "failed"
                      ? item.message
                      : item.state === "queued"
                        ? "已保存，等待解析与索引"
                        : `上传 ${Math.round(item.progress * 100)}%`}
                  </span>
                </div>
                <div className="progressTrack">
                  <span style={{ width: `${item.progress * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        <form className="filterForm" onSubmit={(event) => void runTitleFilter(event)}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="按文件名筛选当前项目资料…"
          />
          <button className="button secondary" type="submit">
            筛选
          </button>
        </form>

        {documents.length === 0 ? (
          <EmptyState title="还没有保存资料">
            <p>上传成功后即使解析失败，原件仍应可下载并显示真实错误状态。</p>
          </EmptyState>
        ) : (
          <div className="documentTable" role="table" aria-label="项目资料">
            <div className="documentHeader" role="row">
              <span>名称 / 类别</span>
              <span>版本</span>
              <span>处理</span>
              <span>核查</span>
              <span>大小</span>
            </div>
            {documents.map((document) => (
              <button
                className={`documentRow ${
                  selectedDocument?.document.id === document.id ? "selected" : ""
                }`}
                type="button"
                role="row"
                key={document.id}
                onClick={() => void selectDocument(document)}
              >
                <span>
                  <strong>{document.title}</strong>
                  <small>
                    {document.document_kind} · {document.citations_count} 引用
                  </small>
                </span>
                <span>{document.version_label ?? "—"}</span>
                <span>
                  <StatusPill value={document.ingest_state} />
                </span>
                <span>{stateLabel(document.evidence_status)}</span>
                <span>{formatBytes(document.size_bytes)}</span>
              </button>
            ))}
          </div>
        )}

        <section className="surface searchSurface">
          <SectionHeader eyebrow="TASK-SCOPED SEARCH" title="项目证据检索" />
          <p className="mutedText">
            检索会保存快照并绑定任务。文本预览筛选不等于 Agent 引用检索。
          </p>
          <form className="searchForm" onSubmit={(event) => void runEvidenceSearch(event)}>
            <select
              value={taskId}
              onChange={(event) => setTaskId(event.target.value)}
              disabled={tasks.length === 0}
              aria-label="证据检索所属任务"
            >
              {tasks.length === 0 ? (
                <option value="">尚无任务，无法建立快照</option>
              ) : (
                tasks.map((task) => (
                  <option value={task.id} key={task.id}>
                    {task.assignee_role} · {task.goal}
                  </option>
                ))
              )}
            </select>
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="例如：犬模型 疼痛"
              disabled={tasks.length === 0}
            />
            <button
              className="button primary"
              type="submit"
              disabled={!taskId || !searchQuery.trim() || searching}
            >
              {searching ? "检索中…" : "建立检索快照"}
            </button>
          </form>

          {searchResult && (
            <div className="searchResults">
              {searchResult.hits.length === 0 ? (
                <EmptyState title="当前资料中没有词法命中">
                  <p>快照已保存，空结果也是可复核的检索结果。</p>
                </EmptyState>
              ) : (
                searchResult.hits.map((hit) => (
                  <article key={hit.chunk_id}>
                    <div>
                      <strong>{hit.title}</strong>
                      <span>{JSON.stringify(hit.locator)}</span>
                    </div>
                    <p>{hit.excerpt}</p>
                  </article>
                ))
              )}
            </div>
          )}
        </section>
      </div>

      <aside className="sourceInspector">
        <SectionHeader eyebrow="SOURCE DETAIL" title="资料详情与原文" />
        {!selectedDocument ? (
          <EmptyState title="选择一份资料">
            <p>右侧显示原件状态、版本、原文定位和解析质量。</p>
          </EmptyState>
        ) : (
          <>
            <h3>{selectedDocument.document.title}</h3>
            <p className="sourceMeta">
              {selectedDocument.document.version_label} ·{" "}
              {formatBytes(selectedDocument.document.size_bytes)} ·{" "}
              {stateLabel(selectedDocument.document.evidence_status)}
            </p>
            <div className="warningBanner">
              可检索/已解析不代表数据或科学结论已核查。
            </div>
            <dl className="metadataList">
              <div>
                <dt>媒体类型</dt>
                <dd>{selectedDocument.document.media_type ?? "—"}</dd>
              </div>
              <div>
                <dt>处理状态</dt>
                <dd>{stateLabel(selectedDocument.document.ingest_state)}</dd>
              </div>
              <div>
                <dt>云端使用</dt>
                <dd>{stateLabel(selectedDocument.document.cloud_policy)}</dd>
              </div>
              <div>
                <dt>保存时间</dt>
                <dd>{formatDate(selectedDocument.document.ingested_at)}</dd>
              </div>
            </dl>
            <button
              className="button secondary fullWidth"
              type="button"
              onClick={() => void downloadCurrent()}
            >
              下载当前原件
            </button>

            <h4>版本历史</h4>
            <div className="versionList">
              {selectedDocument.versions.map((version) => (
                <div key={version.id}>
                  <strong>{version.version_label}</strong>
                  <span>{version.filename}</span>
                  <small>{formatDate(version.ingested_at)}</small>
                </div>
              ))}
            </div>

            <h4>原文定位</h4>
            {selectedDocument.passages.length === 0 ? (
              <p className="mutedText">
                当前版本没有可显示段落，可能仍在处理、失败或该格式仅支持原件。
              </p>
            ) : (
              <div className="passageList">
                {selectedDocument.passages.slice(0, 20).map((passage) => (
                  <article key={passage.id}>
                    <span>{JSON.stringify(passage.locator)}</span>
                    <p>{passage.text}</p>
                  </article>
                ))}
              </div>
            )}
            {selectedDocument.tables_count > 0 && (
              <p className="mutedText">
                另保存 {selectedDocument.tables_count} 个结构化表格。
              </p>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
