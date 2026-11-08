"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createStatisticalPlan,
  deriveDatasetVersion,
  fetchDatasetAnalyses,
  fetchDatasets,
  fetchKnowledgeDocuments,
  importDataset,
  notifyProjectChanged,
  reviewAnalysis,
  runStatisticalAnalysis,
} from "@/lib/api";
import type {
  AnalysisRunView,
  DatasetView,
  KnowledgeDocumentSummary,
  ReviewDecision,
  StatisticalPlanSpecInput,
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

export default function DatasetsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [datasets, setDatasets] = useState<DatasetView[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocumentSummary[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisRunView[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [datasetTitle, setDatasetTitle] = useState("");
  const [sourceLabel, setSourceLabel] = useState("user-upload");
  const [synthetic, setSynthetic] = useState(true);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [numericColumns, setNumericColumns] = useState<string[]>([]);
  const [dropMissingColumns, setDropMissingColumns] = useState<string[]>([]);
  const [cleaningRationale, setCleaningRationale] = useState("");
  const [question, setQuestion] = useState("");
  const [endpointColumn, setEndpointColumn] = useState("");
  const [groupColumn, setGroupColumn] = useState("");
  const [method, setMethod] =
    useState<StatisticalPlanSpecInput["method"]>("descriptive_continuous");
  const [analysisSet, setAnalysisSet] = useState("清理版本全部分析行");
  const [unit, setUnit] = useState("");
  const [expectedGroups, setExpectedGroups] = useState("");
  const [limitations, setLimitations] = useState("合成方法演示，不构成科学结论");
  const [reviewDecision, setReviewDecision] =
    useState<ReviewDecision>("accepted");
  const [reviewerRole, setReviewerRole] = useState("A14");
  const [reviewSummary, setReviewSummary] = useState("");
  const [criticalFinding, setCriticalFinding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextDatasets, nextDocuments] = await Promise.all([
          fetchDatasets(projectId, signal),
          fetchKnowledgeDocuments(projectId, "", signal),
        ]);
        setDatasets(nextDatasets);
        setDocuments(
          nextDocuments.filter(
            (item) =>
              item.version_id &&
              [".csv", ".xlsx"].some((suffix) =>
                item.filename?.toLowerCase().endsWith(suffix),
              ),
          ),
        );
        setSelectedDatasetId((current) => {
          if (current && nextDatasets.some((item) => item.id === current)) {
            return current;
          }
          return nextDatasets[0]?.id ?? null;
        });
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取数据版本");
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

  const selectedDataset =
    datasets.find((dataset) => dataset.id === selectedDatasetId) ?? null;
  const currentVersion = selectedDataset?.current_version ?? null;
  const currentVersionId = currentVersion?.id ?? null;
  const columnsKey = currentVersion?.columns.join("\u0001") ?? "";

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      if (!currentVersionId) {
        setAnalyses([]);
        return;
      }
      try {
        setAnalyses(
          await fetchDatasetAnalyses(projectId, currentVersionId, controller.signal),
        );
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取分析结果");
        }
      }
    }, 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [currentVersionId, projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const columns = columnsKey ? columnsKey.split("\u0001") : [];
      setSelectedColumns(columns);
      setNumericColumns([]);
      setDropMissingColumns([]);
      setEndpointColumn(columns[0] ?? "");
      setGroupColumn("");
      setCleaningRationale("");
    }, 0);
    return () => window.clearTimeout(timer);
  }, [currentVersionId, columnsKey]);

  async function refreshAnalyses() {
    if (!currentVersionId) return;
    try {
      setAnalyses(await fetchDatasetAnalyses(projectId, currentVersionId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法读取分析结果");
    }
  }

  const latestAnalysis = useMemo(() => analyses[0] ?? null, [analyses]);

  async function runAction(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "数据操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function importSelectedDocument() {
    const document = documents.find(
      (item) => item.version_id === selectedDocumentId,
    );
    if (!document?.version_id) return;
    await runAction(
      () =>
        importDataset(
          projectId,
          {
            documentVersionId: document.version_id!,
            title: datasetTitle.trim() || document.title,
            sourceLabel: sourceLabel.trim(),
            synthetic,
            sheetName: null,
          },
          crypto.randomUUID(),
        ),
      "数据原件已登记为不可变raw版本。",
    );
  }

  async function deriveCurrentData() {
    if (!selectedDataset || !currentVersion || !cleaningRationale.trim()) return;
    await runAction(
      () =>
        deriveDatasetVersion(
          projectId,
          selectedDataset.id,
          currentVersion.id,
          {
            select_columns: selectedColumns,
            numeric_columns: numericColumns,
            rename_columns: {},
            drop_missing_columns: dropMissingColumns,
            rationale: cleaningRationale.trim(),
          },
          crypto.randomUUID(),
        ),
      "清理结果已保存为新的派生版本，原始版本保持不变。",
    );
  }

  async function planAndRunAnalysis() {
    if (!currentVersion || !question.trim() || !endpointColumn) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const spec: StatisticalPlanSpecInput = {
        question: question.trim(),
        endpoint_column: endpointColumn,
        method,
        group_column: groupColumn || null,
        analysis_set: analysisSet.trim(),
        missing_policy: "exclude_endpoint_missing",
        unit: unit.trim() || null,
        alpha: 0.05,
        expected_groups:
          method === "two_group_mean_difference"
            ? expectedGroups
                .split(/[\s,，]+/)
                .map((item) => item.trim())
                .filter(Boolean)
            : [],
        limitations: limitations
          .split(/\n+/)
          .map((item) => item.trim())
          .filter(Boolean),
        exploratory: false,
      };
      const plan = await createStatisticalPlan(
        projectId,
        currentVersion.id,
        spec,
        crypto.randomUUID(),
      );
      const analysis = await runStatisticalAnalysis(
        projectId,
        plan.id,
        crypto.randomUUID(),
      );
      setNotice(
        `分析 ${analysis.code_version} 已完成；结果绑定既定数据、代码和计划。`,
      );
      await refreshAnalyses();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "统计计算失败");
    } finally {
      setBusy(false);
    }
  }

  async function submitReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!latestAnalysis || !reviewSummary.trim()) return;
    setBusy(true);
    setError("");
    try {
      await reviewAnalysis(
        projectId,
        latestAnalysis.id,
        {
          reviewerRole,
          decision: criticalFinding ? "changes_requested" : reviewDecision,
          summary: reviewSummary.trim(),
          findings: criticalFinding
            ? [
                {
                  code: "ANALYSIS_CRITICAL",
                  severity: "critical",
                  message: reviewSummary.trim(),
                  evidence_refs: [],
                },
              ]
            : [],
        },
        crypto.randomUUID(),
      );
      setReviewSummary("");
      setCriticalFinding(false);
      setNotice("分析复核记录已保存。");
      await refreshAnalyses();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法保存复核");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingPanel label="正在读取数据版本…" />;
  if (error && datasets.length === 0) {
    return <ErrorPanel message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="pageStack">
      <section className="datasetIntro">
        <div>
          <p className="eyebrow">DATA & REPRODUCIBLE ANALYSIS</p>
          <h2>原件、清理、计划和统计结果分别版本化</h2>
          <p>
            原始表格不从知识库复制后覆盖；清理生成新派生版本，统计结果绑定行hash、计划、代码hash、环境和复核记录。
          </p>
        </div>
        <span className="largeCount">{datasets.length} 个数据集</span>
      </section>

      {(error || notice) && (
        <div className={error ? "errorPanel" : "successPanel"}>
          {error || notice}
        </div>
      )}

      <section className="surface">
        <SectionHeader
          eyebrow="IMPORT FROM IMMUTABLE KNOWLEDGE"
          title="导入CSV / XLSX数据包"
        />
        {documents.length === 0 ? (
          <EmptyState title="没有可导入表格">
            <p>先在知识资料库上传CSV或XLSX，并等待原件保存完成。</p>
          </EmptyState>
        ) : (
          <div className="datasetImportForm">
            <select
              value={selectedDocumentId}
              onChange={(event) => setSelectedDocumentId(event.target.value)}
            >
              <option value="">选择知识库表格版本</option>
              {documents.map((document) => (
                <option value={document.version_id ?? ""} key={document.id}>
                  {document.title} · {document.version_label} ·{" "}
                  {formatBytes(document.size_bytes)}
                </option>
              ))}
            </select>
            <input
              value={datasetTitle}
              onChange={(event) => setDatasetTitle(event.target.value)}
              placeholder="数据集标题（可选）"
            />
            <input
              value={sourceLabel}
              onChange={(event) => setSourceLabel(event.target.value)}
              placeholder="来源标签"
            />
            <label className="checkboxLabel">
              <input
                type="checkbox"
                checked={synthetic}
                onChange={(event) => setSynthetic(event.target.checked)}
              />
              合成/模拟数据
            </label>
            <button
              className="button primary"
              type="button"
              disabled={!selectedDocumentId || busy}
              onClick={() => void importSelectedDocument()}
            >
              登记为raw数据版本
            </button>
          </div>
        )}
      </section>

      {datasets.length > 0 && (
        <div className="datasetSwitcher">
          {datasets.map((dataset) => (
            <button
              className={
                dataset.id === selectedDatasetId
                  ? "planTab active"
                  : "planTab"
              }
              type="button"
              key={dataset.id}
              onClick={() => setSelectedDatasetId(dataset.id)}
            >
              <strong>{dataset.title}</strong>
              <span>V{dataset.current_version.version_number}</span>
            </button>
          ))}
        </div>
      )}

      {selectedDataset && currentVersion && (
        <>
          <section className="surface datasetVersionPanel">
            <SectionHeader
              eyebrow={`DATASET REV ${selectedDataset.revision}`}
              title={`${selectedDataset.title} · V${currentVersion.version_number}`}
              aside={<StatusPill value={currentVersion.state} />}
            />
            <div className="datasetMeta">
              <span>{currentVersion.kind.toUpperCase()}</span>
              <span>{currentVersion.row_count} 行</span>
              <span>{currentVersion.columns.length} 列</span>
              <span>行hash {currentVersion.rows_sha256.slice(0, 12)}</span>
            </div>
            {currentVersion.manifest.synthetic === true && (
              <div className="warningBanner">
                合成/模拟数据。结果仅用于验证流程与统计代码，不代表真实研究。
              </div>
            )}
            <div className="tableScroll">
              <table className="dataTable">
                <thead>
                  <tr>
                    {currentVersion.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {currentVersion.preview.map((row, index) => (
                    <tr key={`${currentVersion.id}-${index}`}>
                      {currentVersion.columns.map((column) => (
                        <td key={column}>{String(row[column] ?? "∅")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details className="criterionDetails">
              <summary>版本历史与导入质量发现</summary>
              <div className="versionList">
                {selectedDataset.versions.map((version) => (
                  <div key={version.id}>
                    <strong>V{version.version_number}</strong>
                    <span>
                      {version.kind} · {version.row_count} 行
                    </span>
                    <small>{formatDate(version.created_at)}</small>
                  </div>
                ))}
              </div>
              <pre className="jsonPreview">
                {JSON.stringify(currentVersion.quality_findings, null, 2)}
              </pre>
            </details>
          </section>

          <div className="analysisGrid">
            <section className="surface">
              <SectionHeader eyebrow="CLEANING DERIVATION" title="生成清理版本" />
              <div className="columnChooser">
                {currentVersion.columns.map((column) => (
                  <div key={column}>
                    <label className="checkboxLabel">
                      <input
                        type="checkbox"
                        checked={selectedColumns.includes(column)}
                        onChange={(event) =>
                          setSelectedColumns((current) =>
                            event.target.checked
                              ? [...current, column]
                              : current.filter((item) => item !== column),
                          )
                        }
                      />
                      保留 {column}
                    </label>
                    <label className="checkboxLabel">
                      <input
                        type="checkbox"
                        checked={numericColumns.includes(column)}
                        onChange={(event) =>
                          setNumericColumns((current) =>
                            event.target.checked
                              ? [...current, column]
                              : current.filter((item) => item !== column),
                          )
                        }
                      />
                      数值
                    </label>
                    <label className="checkboxLabel">
                      <input
                        type="checkbox"
                        checked={dropMissingColumns.includes(column)}
                        onChange={(event) =>
                          setDropMissingColumns((current) =>
                            event.target.checked
                              ? [...current, column]
                              : current.filter((item) => item !== column),
                          )
                        }
                      />
                      缺失则删行
                    </label>
                  </div>
                ))}
              </div>
              <textarea
                value={cleaningRationale}
                onChange={(event) => setCleaningRationale(event.target.value)}
                rows={3}
                placeholder="清理理由与预设排除规则"
              />
              <button
                className="button secondary"
                type="button"
                disabled={
                  busy ||
                  !cleaningRationale.trim() ||
                  selectedColumns.length === 0
                }
                onClick={() => void deriveCurrentData()}
              >
                生成不可变派生版本
              </button>
            </section>

            <section className="surface">
              <SectionHeader eyebrow="PRE-SPECIFIED ANALYSIS" title="统计计划与计算" />
              <div className="formStack">
                <label>
                  研究问题
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    rows={2}
                    placeholder="先写问题、分析集和终点，再计算。"
                  />
                </label>
                <label>
                  方法
                  <select
                    value={method}
                    onChange={(event) =>
                      setMethod(
                        event.target.value as StatisticalPlanSpecInput["method"],
                      )
                    }
                  >
                    <option value="descriptive_continuous">连续终点描述统计</option>
                    <option value="two_group_mean_difference">两组均值差</option>
                    <option value="proportion_wilson">二分比例 Wilson 区间</option>
                  </select>
                </label>
                <div className="twoColumnFields">
                  <label>
                    终点列
                    <select
                      value={endpointColumn}
                      onChange={(event) => setEndpointColumn(event.target.value)}
                    >
                      {currentVersion.columns.map((column) => (
                        <option value={column} key={column}>
                          {column}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    分组列
                    <select
                      value={groupColumn}
                      onChange={(event) => setGroupColumn(event.target.value)}
                      disabled={method !== "two_group_mean_difference"}
                    >
                      <option value="">无</option>
                      {currentVersion.columns.map((column) => (
                        <option value={column} key={column}>
                          {column}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                {method === "two_group_mean_difference" && (
                  <label>
                    预期两组名称（逗号分隔）
                    <input
                      value={expectedGroups}
                      onChange={(event) => setExpectedGroups(event.target.value)}
                      placeholder="control, treatment"
                    />
                  </label>
                )}
                <label>
                  分析集
                  <input
                    value={analysisSet}
                    onChange={(event) => setAnalysisSet(event.target.value)}
                  />
                </label>
                <label>
                  单位（比例方法留空）
                  <input
                    value={unit}
                    onChange={(event) => setUnit(event.target.value)}
                  />
                </label>
                <label>
                  局限（每行一项）
                  <textarea
                    value={limitations}
                    onChange={(event) => setLimitations(event.target.value)}
                    rows={2}
                  />
                </label>
                <button
                  className="button primary"
                  type="button"
                  disabled={busy || !question.trim()}
                  onClick={() => void planAndRunAnalysis()}
                >
                  保存计划并计算
                </button>
              </div>
            </section>
          </div>

          <section className="surface">
            <SectionHeader eyebrow="ANALYSIS RESULTS" title="可复现结果与复核" />
            {!latestAnalysis ? (
              <EmptyState title="尚无统计运行">
                <p>计划和计算结果从未完成状态开始分别记录。</p>
              </EmptyState>
            ) : (
              <div className="analysisResultGrid">
                <div className="resultMetrics">
                  {Object.entries(latestAnalysis.result)
                    .filter(([, value]) =>
                      ["string", "number", "boolean"].includes(typeof value),
                    )
                    .map(([key, value]) => (
                      <div key={key}>
                        <span>{key}</span>
                        <strong>{String(value)}</strong>
                      </div>
                    ))}
                  <div>
                    <span>代码版本</span>
                    <strong>{latestAnalysis.code_version}</strong>
                  </div>
                  <div>
                    <span>结果hash</span>
                    <code>{latestAnalysis.output_sha256.slice(0, 16)}</code>
                  </div>
                </div>
                <SimpleChart analysis={latestAnalysis} />
                <div className="analysisAssumptions">
                  <strong>方法与限制</strong>
                  <pre className="jsonPreview">
                    {JSON.stringify(latestAnalysis.result, null, 2)}
                  </pre>
                  {latestAnalysis.latest_review ? (
                    <div className="reviewResult">
                      <StatusPill value={latestAnalysis.latest_review.decision} />
                      <p>{latestAnalysis.latest_review.summary}</p>
                    </div>
                  ) : (
                    <form
                      className="formStack compactForm"
                      onSubmit={(event) => void submitReview(event)}
                    >
                      <select
                        value={reviewerRole}
                        onChange={(event) => setReviewerRole(event.target.value)}
                      >
                        <option value="A14">A14 生物统计</option>
                        <option value="A25">A25 独立质量</option>
                        <option value="A26">A26 独立反证</option>
                      </select>
                      <select
                        value={reviewDecision}
                        onChange={(event) =>
                          setReviewDecision(event.target.value as ReviewDecision)
                        }
                        disabled={criticalFinding}
                      >
                        <option value="accepted">接受</option>
                        <option value="changes_requested">要求重做</option>
                        <option value="disputed">保留争议</option>
                      </select>
                      <textarea
                        value={reviewSummary}
                        onChange={(event) => setReviewSummary(event.target.value)}
                        rows={2}
                        required
                        placeholder="复核方法、数据、代码与结果"
                      />
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
                        critical缺陷，强制重做
                      </label>
                      <button
                        className="button secondary"
                        type="submit"
                        disabled={busy || !reviewSummary.trim()}
                      >
                        保存复核
                      </button>
                    </form>
                  )}
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function SimpleChart({ analysis }: { analysis: AnalysisRunView }) {
  const chart = analysis.chart_spec;
  const labels = Array.isArray(chart.labels)
    ? chart.labels.map(String)
    : [String(chart.label ?? analysis.result.endpoint_column ?? "结果")];
  const values = Array.isArray(chart.values)
    ? chart.values.map(Number)
    : [Number(chart.value ?? 0)];
  const maximum = Math.max(...values.map((value) => Math.abs(value)), 1);
  return (
    <div className="simpleChart" aria-label="统计结果图">
      <strong>结果概览</strong>
      {labels.map((label, index) => (
        <div key={`${label}-${index}`}>
          <span>{label}</span>
          <div>
            <i style={{ width: `${(Math.abs(values[index] ?? 0) / maximum) * 100}%` }} />
          </div>
          <code>{values[index]?.toFixed(3) ?? "—"}</code>
        </div>
      ))}
      {analysis.chart_spec.lower !== undefined && (
        <small>
          区间 {String(chart.lower ?? "—")} – {String(chart.upper ?? "—")}
        </small>
      )}
    </div>
  );
}
