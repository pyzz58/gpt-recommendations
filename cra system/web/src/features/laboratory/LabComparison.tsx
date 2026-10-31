import {
  AllCommunityModule,
  ModuleRegistry,
  type ColDef
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type LabComparisonFieldView,
  type LabComparisonView,
  type LabReportView,
  type EDCSnapshotSummaryView,
  createLabComparison,
  documentContentUrl,
  getEdcSnapshots,
  getLabComparison,
  getLabReports,
  linkLabComparisonIssues
} from "../../api/client";
import { SourcePdfViewer } from "../../components/SourcePdfViewer";
import {
  comparisonStatusLabel,
  reviewableFieldIds
} from "./review";

ModuleRegistry.registerModules([AllCommunityModule]);

type Props = {
  studyId: string;
  siteId: string;
};

const MATCH_LABEL: Record<string, string> = {
  unique_validated: "唯一校验匹配",
  ambiguous: "多候选待核实",
  unmatched: "未匹配"
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "检验核对失败";
}

function sourceBBox(field: LabComparisonFieldView): number[] | null {
  const sourceRef = field.matched_identity.source_ref as
    | {
        cells?: Record<string, { bbox?: number[] | null }>;
        table_bbox?: number[] | null;
      }
    | undefined;
  return (
    sourceRef?.cells?.analyte?.bbox ??
    sourceRef?.cells?.value_raw?.bbox ??
    sourceRef?.table_bbox ??
    null
  );
}

export function LabComparison({ studyId, siteId }: Props) {
  const [reports, setReports] = useState<LabReportView[]>([]);
  const [snapshots, setSnapshots] = useState<EDCSnapshotSummaryView[]>([]);
  const [reportId, setReportId] = useState("");
  const [snapshotId, setSnapshotId] = useState(
    () => new URLSearchParams(window.location.search).get("edcSnapshot") ?? ""
  );
  const [comparison, setComparison] = useState<LabComparisonView | null>(null);
  const [selectedFields, setSelectedFields] = useState<LabComparisonFieldView[]>(
    []
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedReport =
    reports.find((item) => item.id === reportId) ?? reports[0] ?? null;

  const load = useCallback(async () => {
    const [next, snapshotNext] = await Promise.all([
      getLabReports(studyId, siteId),
      getEdcSnapshots(studyId, siteId)
    ]);
    setReports(next);
    setSnapshots(snapshotNext);
    setReportId((current) => current || next[0]?.id || "");
    setSnapshotId(
      (current) => current || snapshotNext[0]?.id || ""
    );
  }, [siteId, studyId]);

  useEffect(() => {
    load().catch((reason) => setError(errorMessage(reason)));
  }, [load]);

  useEffect(() => {
    if (!comparison) {
      return;
    }
    const refresh = () => {
      getLabComparison(comparison.id)
        .then(setComparison)
        .catch((reason) => setError(errorMessage(reason)));
    };
    window.addEventListener("cra-lab-report-updated", refresh);
    return () => {
      window.removeEventListener("cra-lab-report-updated", refresh);
    };
  }, [comparison?.id]);

  async function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedReport || !snapshotId.trim()) {
      setError("请选择识别报告并填写 EDC 快照 ID。");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const next = await createLabComparison({
        reportId: selectedReport.id,
        edcSnapshotId: snapshotId.trim()
      });
      setComparison(next);
      setSelectedFields([]);
      setMessage(
        next.replayed
          ? "相同报告、快照和复核状态已复用原比较。"
          : `已比较 ${next.fields.length} 条候选；范围与未知条件已保存。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function createIssues() {
    if (!comparison || selectedFields.length === 0) {
      return;
    }
    const fieldIds = reviewableFieldIds(selectedFields);
    if (fieldIds.length === 0) {
      setMessage("选中的字段均为一致，不创建整改待办。");
      return;
    }
    if (selectedFields.some((field) => field.stale)) {
      setMessage("所选字段的来源状态已变化，请重新执行匹配和核对后再关联待办。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const linked = await linkLabComparisonIssues(comparison.id, fieldIds);
      const refreshed = await getLabComparison(comparison.id);
      setComparison(refreshed);
      setSelectedFields([]);
      setMessage(`已关联 ${linked.issues.length} 个 EDC 整改待办，未自动判 PD。`);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const columns: ColDef<LabComparisonFieldView>[] = [
    {
      colId: "select",
      headerName: "",
      width: 48,
      checkboxSelection: true,
      headerCheckboxSelection: true
    },
    {
      colId: "subject",
      headerName: "受试者",
      width: 130,
      valueGetter: (params) =>
        params.data?.matched_identity.subject_external_id ?? ""
    },
    {
      colId: "analyte",
      headerName: "项目",
      width: 130,
      valueGetter: (params) => params.data?.matched_identity.analyte ?? ""
    },
    {
      colId: "instance",
      headerName: "实例",
      width: 95,
      valueGetter: (params) =>
        params.data?.matched_identity.instance_type ?? ""
    },
    {
      field: "source_value",
      headerName: "来源结果",
      width: 105
    },
    { field: "source_unit", headerName: "来源单位", width: 95 },
    { field: "edc_value", headerName: "EDC结果", width: 100 },
    { field: "edc_unit", headerName: "EDC单位", width: 90 },
    {
      field: "match_status",
      headerName: "匹配",
      width: 135,
      valueFormatter: (params) =>
        MATCH_LABEL[params.value as string] ?? String(params.value ?? "")
    },
    {
      field: "result_status",
      headerName: "核对",
      width: 130,
      valueFormatter: (params) =>
        comparisonStatusLabel(String(params.value ?? ""))
    },
    {
      field: "linked_issue_id",
      headerName: "待办",
      width: 120,
      valueFormatter: (params) => (params.value ? "已关联" : "未关联")
    },
    {
      field: "stale",
      headerName: "计算状态",
      width: 105,
      valueFormatter: (params) => (params.value ? "待重算" : "当前")
    },
    {
      field: "reason",
      headerName: "范围/原因",
      flex: 1,
      minWidth: 260
    }
  ];

  const focused = selectedFields[0] ?? null;
  const sourceRef = focused?.matched_identity.source_ref as
    | { page?: number; anchor?: string }
    | undefined;

  return (
    <section className="lab-comparison" aria-labelledby="lab-comparison-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M08 · 先匹配再核对</p>
          <h2 id="lab-comparison-title">源检验与 EDC 并排核查</h2>
          <p>
            初检、复查和报告修订先按身份与实例匹配，再用 Decimal 比较；
            歧义不会按数值接近度自动挑选。
          </p>
        </div>
        <span className="status-chip muted">
          {comparison ? `${comparison.fields.length} 条范围` : "尚未比较"}
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <form className="comparison-form" onSubmit={(event) => void compare(event)}>
        <label>
          识别报告
          <select
            value={selectedReport?.id ?? ""}
            onChange={(event) => {
              setReportId(event.target.value);
              setComparison(null);
            }}
            required
          >
            {reports.map((report) => (
              <option key={report.id} value={report.id}>
                {report.id.slice(0, 8)} · {report.provider_name} · {report.state}
              </option>
            ))}
          </select>
        </label>
        <label>
          EDC 快照
          <select
            value={snapshotId}
            onChange={(event) => setSnapshotId(event.target.value)}
            required
          >
            <option value="">选择已确认快照</option>
            {snapshots.map((snapshot) => (
              <option key={snapshot.id} value={snapshot.id}>
                {snapshot.id.slice(0, 8)} · {snapshot.record_count} 条 ·{" "}
                {snapshot.scope_status}
              </option>
            ))}
          </select>
        </label>
        <button
          className="primary-button compact"
          disabled={busy || !reports.length || !snapshots.length}
        >
          匹配并核对
        </button>
      </form>

      {comparison && (
        <>
          <div className="comparison-scope">
            <span>
              EDC范围 {String(comparison.scope.edc_scope_status)}
            </span>
            <span>
              未见语义 {String(comparison.scope.edc_absence_semantics)}
            </span>
            <span>医学安全判断 未执行</span>
          </div>
          {comparison.stale && (
            <div className="notice notice-error" role="alert">
              有 {comparison.stale_field_ids.length} 个字段的来源候选、更正或跳过
              状态已在比较后变化；这些字段请重新执行匹配和核对后再关联待办。
            </div>
          )}
          <div className="recognition-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={
                busy ||
                selectedFields.length === 0 ||
                selectedFields.some((field) => field.stale)
              }
              onClick={() => void createIssues()}
            >
              将所选差异关联 M06 待办
            </button>
            <span className="muted-copy">
              仅创建 EDC 更正待办，不自动认定 PD 或安全事件。
            </span>
          </div>
          <div className="ag-theme-quartz lab-grid">
            <AgGridReact<LabComparisonFieldView>
              theme="legacy"
              rowData={comparison.fields}
              columnDefs={columns}
              rowSelection="multiple"
              onSelectionChanged={(event) =>
                setSelectedFields(event.api.getSelectedRows())
              }
              getRowId={(params) => params.data.id}
              defaultColDef={{ sortable: true, filter: true, resizable: true }}
              domLayout="autoHeight"
            />
          </div>

          {focused && selectedReport && (
            <div className="lab-review-layout">
              <section className="lab-source-panel">
                <p className="eyebrow">源定位</p>
                <p>第 {sourceRef?.page ?? 1} 页 · {sourceRef?.anchor ?? "表格"}</p>
                {selectedReport.file_format === "text_pdf" ? (
                  <SourcePdfViewer
                    url={documentContentUrl(
                      selectedReport.source_document_version_id
                    )}
                    pageNumber={sourceRef?.page ?? 1}
                    bbox={sourceBBox(focused)}
                  />
                ) : (
                  <img
                    className="lab-source-image"
                    src={documentContentUrl(
                      selectedReport.source_document_version_id
                    )}
                    alt="合成检验源图"
                  />
                )}
              </section>
              <section className="comparison-detail">
                <p className="eyebrow">字段范围</p>
                <h3>
                  {String(focused.matched_identity.subject_external_id)} ·{" "}
                  {String(focused.matched_identity.analyte)} ·{" "}
                  {String(focused.matched_identity.instance_type)}
                </h3>
                <dl className="comparison-values">
                  <div>
                    <dt>来源</dt>
                    <dd>{focused.source_value ?? "未识别"} {focused.source_unit ?? ""}</dd>
                  </div>
                  <div>
                    <dt>EDC</dt>
                    <dd>{focused.edc_value ?? "未录/不可用"} {focused.edc_unit ?? ""}</dd>
                  </div>
                  <div>
                    <dt>结论</dt>
                    <dd>{comparisonStatusLabel(focused.result_status)}</dd>
                  </div>
                </dl>
                {focused.unknowns.length > 0 && (
                  <p className="inline-warning">
                    未知/待核实：{focused.unknowns.join("、")}
                  </p>
                )}
                <ul className="field-result-list">
                  {focused.field_results.map((result, index) => (
                    <li key={`${String(result.field)}-${index}`}>
                      <strong>{String(result.field)}</strong>{" "}
                      {comparisonStatusLabel(String(result.status))}
                      {result.detail ? ` · ${String(result.detail)}` : ""}
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          )}
        </>
      )}
    </section>
  );
}
