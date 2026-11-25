"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createArtifactExport,
  downloadArtifactExport,
  fetchArtifactExportRuntime,
  fetchArtifactExports,
  fetchArtifactPreview,
  fetchDatasetAnalyses,
  fetchDatasets,
  notifyProjectChanged,
} from "@/lib/api";
import type {
  AnalysisRunView,
  ArtifactExportFormat,
  ArtifactExportRuntime,
  ArtifactExportView,
  DatasetView,
} from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatBytes,
  formatDate,
} from "@/components/ui";

const formatLabels: Record<ArtifactExportFormat, string> = {
  docx: "Word",
  pptx: "PowerPoint",
  xlsx: "Excel",
  pdf: "PDF",
};

const formatNotes: Record<ArtifactExportFormat, string> = {
  docx: "可编辑研究报告",
  pptx: "可编辑摘要演示",
  xlsx: "公式重算与核对",
  pdf: "只读分页报告",
};

type ReviewedAnalysis = AnalysisRunView & {
  datasetTitle: string;
  versionLabel: string;
};

export default function ArtifactsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [exports, setExports] = useState<ArtifactExportView[]>([]);
  const [runtime, setRuntime] = useState<ArtifactExportRuntime | null>(null);
  const [analyses, setAnalyses] = useState<ReviewedAnalysis[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState("");
  const [title, setTitle] = useState("");
  const [busyFormat, setBusyFormat] = useState<ArtifactExportFormat | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextExports, nextRuntime, datasets] = await Promise.all([
          fetchArtifactExports(projectId, signal),
          fetchArtifactExportRuntime(projectId, signal),
          fetchDatasets(projectId, signal),
        ]);
        const analysisGroups = await Promise.all(
          datasets.map(async (dataset: DatasetView) => {
            const runs = await fetchDatasetAnalyses(
              projectId,
              dataset.current_version.id,
              signal,
            );
            return runs.map((run) => ({
              ...run,
              datasetTitle: dataset.title,
              versionLabel: `v${dataset.current_version.version_number}`,
            }));
          }),
        );
        const availableAnalyses = analysisGroups
          .flat()
          .filter(
            (analysis) =>
              analysis.state === "succeeded" &&
              analysis.latest_review?.decision === "accepted",
          );
        setExports(nextExports);
        setRuntime(nextRuntime);
        setAnalyses(availableAnalyses);
        const nextSelected =
          selectedAnalysisId &&
          availableAnalyses.some((analysis) => analysis.id === selectedAnalysisId)
            ? selectedAnalysisId
            : (availableAnalyses[0]?.id ?? "");
        setSelectedAnalysisId(nextSelected);
        const defaultAnalysis = availableAnalyses.find(
          (analysis) => analysis.id === nextSelected,
        );
        setTitle(
          defaultAnalysis ? `${defaultAnalysis.datasetTitle}｜分析报告` : "",
        );
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取导出记录");
        }
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [projectId, selectedAnalysisId],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [load]);

  const selectedAnalysis =
    analyses.find((analysis) => analysis.id === selectedAnalysisId) ?? null;

  const templateByFormat = useMemo(
    () =>
      Object.fromEntries(
        runtime?.templates.map((template) => [template.format, template]) ?? [],
      ) as Partial<Record<ArtifactExportFormat, ArtifactExportRuntime["templates"][number]>>,
    [runtime],
  );

  async function exportAs(exportFormat: ArtifactExportFormat) {
    if (!selectedAnalysis) return;
    setBusyFormat(exportFormat);
    setError("");
    setNotice("");
    try {
      const template = templateByFormat[exportFormat];
      await createArtifactExport(
        projectId,
        {
          analysisId: selectedAnalysis.id,
          format: exportFormat,
          templateId: template?.template_id ?? null,
          title: title.trim() || null,
        },
        crypto.randomUUID(),
      );
      setNotice(
        `${formatLabels[exportFormat]} 已生成，并完成打开、预览与结构检查。`,
      );
      setExports(await fetchArtifactExports(projectId));
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "导出失败");
    } finally {
      setBusyFormat(null);
    }
  }

  async function openPdf(exportId: string) {
    const popup = window.open("", "_blank");
    try {
      const url = await fetchArtifactPreview(projectId, exportId, "pdf");
      if (popup) {
        popup.location.href = url;
      } else {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.target = "_blank";
        anchor.click();
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (cause) {
      popup?.close();
      setError(cause instanceof Error ? cause.message : "无法打开 PDF 预览");
    }
  }

  async function downloadArtifact(item: ArtifactExportView) {
    setError("");
    try {
      await downloadArtifactExport(projectId, item.id, item.filename);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "下载失败");
    }
  }

  return (
    <div className="pageStack">
      <section className="artifactIntro">
        <div>
          <p className="eyebrow">W14 · OFFICE / PDF</p>
          <h2>版本化导出与真实预览</h2>
          <p>
            从已复核的分析运行生成 Word、PowerPoint、Excel 和 PDF。文件哈希、模板版本、
            数据来源和校验记录随产物保存；生成成功不改变科学结论等级。
          </p>
        </div>
        {runtime && (
          <div className="overviewStatus">
            <StatusPill
              value={runtime.status}
              tone={runtime.status === "ready" ? "good" : "bad"}
            />
            <span>
              {runtime.templates.length} 个固定版本模板 · 服务端渲染
            </span>
          </div>
        )}
      </section>

      {loading && <LoadingPanel label="正在读取分析、模板和导出记录…" />}
      {!loading && error && (
        <ErrorPanel message={error} onRetry={() => void load()} />
      )}
      {!loading && notice && (
        <div className="noticePanel" role="status">
          {notice}
        </div>
      )}

      {!loading && runtime && (
        <section className="surface runtimePanel">
          <div>
            <p className="eyebrow">EXPORT RUNTIME</p>
            <h3>{runtime.detail}</h3>
            <p className="mutedText">
              Word / PowerPoint / Excel 经 LibreOffice 转 PDF；Excel 公式由
              LibreOffice 实际重算，再与 Python 独立计算核对。
            </p>
          </div>
          <div className="toolVersionList">
            {Object.entries(runtime.versions).map(([name, version]) => (
              <span key={name}>
                {name} <strong>{version}</strong>
              </span>
            ))}
          </div>
        </section>
      )}

      {!loading && (
        <section className="surface">
          <SectionHeader
            eyebrow="NEW EXPORT"
            title="从已接受复核生成文件"
            aside={
              <span className="mutedText">
                最新复核必须为 accepted
              </span>
            }
          />
          {analyses.length === 0 ? (
            <EmptyState title="暂无可导出的分析">
              <p>
                先在数据统计页完成分析，并由 A14、A25 或 A26
                记录接受复核。未复核结果不会出现在这里。
              </p>
            </EmptyState>
          ) : (
            <div className="artifactComposer">
              <div className="formStack">
                <label>
                  已复核分析
                  <select
                    value={selectedAnalysisId}
                    onChange={(event) => {
                      const nextId = event.target.value;
                      const nextAnalysis = analyses.find(
                        (analysis) => analysis.id === nextId,
                      );
                      setSelectedAnalysisId(nextId);
                      setTitle(
                        nextAnalysis
                          ? `${nextAnalysis.datasetTitle}｜分析报告`
                          : "",
                      );
                    }}
                  >
                    {analyses.map((analysis) => (
                      <option key={analysis.id} value={analysis.id}>
                        {analysis.datasetTitle} · {analysis.versionLabel} · 分析
                        v{analysis.analysis_version}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  文件标题
                  <input
                    value={title}
                    maxLength={300}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                </label>
              </div>
              {selectedAnalysis && (
                <div className="selectedAnalysis">
                  <div>
                    <span>复核</span>
                    <strong>
                      {selectedAnalysis.latest_review?.reviewer_role} /{" "}
                      {selectedAnalysis.latest_review?.decision}
                    </strong>
                  </div>
                  <div>
                    <span>输入哈希</span>
                    <code>{selectedAnalysis.input_sha256.slice(0, 20)}…</code>
                  </div>
                  <div>
                    <span>输出哈希</span>
                    <code>{selectedAnalysis.output_sha256.slice(0, 20)}…</code>
                  </div>
                </div>
              )}
              <div className="formatGrid">
                {(Object.keys(formatLabels) as ArtifactExportFormat[]).map(
                  (exportFormat) => {
                    const template = templateByFormat[exportFormat];
                    return (
                      <button
                        className="formatButton"
                        disabled={
                          busyFormat !== null ||
                          runtime?.status !== "ready" ||
                          !selectedAnalysis
                        }
                        key={exportFormat}
                        onClick={() => void exportAs(exportFormat)}
                        type="button"
                      >
                        <span className={`formatMark ${exportFormat}`}>
                          {exportFormat.toUpperCase()}
                        </span>
                        <span>
                          <strong>{formatLabels[exportFormat]}</strong>
                          <small>{formatNotes[exportFormat]}</small>
                        </span>
                        <small className="formatVersion">
                          {busyFormat === exportFormat
                            ? "正在生成与检查…"
                            : template
                              ? `${template.template_id} · v${template.version}`
                              : "模板不可用"}
                        </small>
                      </button>
                    );
                  },
                )}
              </div>
            </div>
          )}
          <p className="boundaryNote">
            自动检查覆盖文件能否打开、必需结构、预览页是否空白、PPT
            形状边界，以及 Excel 明确公式格的重算值和独立计算。它不能替代完整视觉校样、
            科学审查或真人专家意见。
          </p>
        </section>
      )}

      {!loading && (
        <section className="surface">
          <SectionHeader
            eyebrow="EXPORT HISTORY"
            title="不可变导出记录"
            aside={<span className="mutedText">{exports.length} 个记录</span>}
          />
          {exports.length === 0 ? (
            <EmptyState title="还没有导出文件">
              <p>选择已复核分析后生成第一份版本化文档。</p>
            </EmptyState>
          ) : (
            <div className="artifactGrid">
              {exports.map((item) => (
                <article
                  className={`artifactCard ${item.state}`}
                  key={item.id}
                >
                  <ArtifactThumbnail
                    exportId={item.id}
                    projectId={projectId}
                    available={item.state === "succeeded"}
                    onError={setError}
                  />
                  <div className="artifactCardBody">
                    <div className="cardTopline">
                      <span className={`formatMark ${item.format}`}>
                        {item.format.toUpperCase()}
                      </span>
                      <StatusPill value={item.state} />
                      {item.validation_status === "passed" && (
                        <StatusPill value="已检查" tone="good" />
                      )}
                    </div>
                    <h3>{item.filename}</h3>
                    <p>
                      {item.template_id} · v{item.template_version} ·{" "}
                      {item.page_count ?? "—"} 页
                    </p>
                    <div className="artifactMeta">
                      <span>
                        数据来源{" "}
                        <strong>
                          {item.data_origin === "synthetic"
                            ? "合成数据"
                            : item.data_origin === "real"
                              ? "已声明真实数据"
                              : "来源性质未知"}
                        </strong>
                      </span>
                      <span>
                        文件版本{" "}
                        <strong>
                          {item.version ? `v${item.version}` : "未生成"}
                        </strong>
                      </span>
                      <span>
                        大小 <strong>{formatBytes(item.size_bytes)}</strong>
                      </span>
                      <span>
                        完成 <strong>{formatDate(item.completed_at)}</strong>
                      </span>
                    </div>
                    {item.art_sha256 && (
                      <code className="hashLine">
                        SHA-256 {item.art_sha256}
                      </code>
                    )}
                    {item.error_message && (
                      <p className="artifactError">{item.error_message}</p>
                    )}
                    {item.validation.formula_checks?.length ? (
                      <div className="validationList">
                        {item.validation.formula_checks.map((check) => (
                          <span key={`${check.sheet}-${check.cell}`}>
                            {check.sheet}!{check.cell} = {String(check.cached_value)}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <div className="cardActions">
                      {item.state === "succeeded" && (
                        <>
                          <button
                            className="button secondary"
                            onClick={() => void openPdf(item.id)}
                            type="button"
                          >
                            打开 PDF 预览
                          </button>
                          <button
                            className="button primary"
                            onClick={() => void downloadArtifact(item)}
                            type="button"
                          >
                            下载原件
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function ArtifactThumbnail({
  projectId,
  exportId,
  available,
  onError,
}: {
  projectId: string;
  exportId: string;
  available: boolean;
  onError: (message: string) => void;
}) {
  const [src, setSrc] = useState("");

  useEffect(() => {
    if (!available) return;
    let active = true;
    let objectUrl = "";
    void fetchArtifactPreview(projectId, exportId, "png")
      .then((url) => {
        objectUrl = url;
        if (active) setSrc(url);
        else URL.revokeObjectURL(url);
      })
      .catch((cause: unknown) => {
        if (active) {
          onError(cause instanceof Error ? cause.message : "无法读取预览图");
        }
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [available, exportId, onError, projectId]);

  if (!available) {
    return (
      <div className="artifactThumbnail unavailable">
        <span>生成未完成</span>
      </div>
    );
  }
  if (!src) {
    return (
      <div className="artifactThumbnail loading">
        <span>正在读取预览…</span>
      </div>
    );
  }
  return (
    <div className="artifactThumbnail">
      {/* Authenticated API bytes are converted to a short-lived object URL. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img alt="导出文件首页预览" src={src} />
    </div>
  );
}
