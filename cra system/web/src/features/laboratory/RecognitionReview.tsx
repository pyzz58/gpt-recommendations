import {
  AllCommunityModule,
  ModuleRegistry,
  type ColDef
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  ApiError,
  type LabObservationView,
  type LabReportView,
  addManualLabObservation,
  batchConfirmLabObservations,
  createLabReport,
  documentContentUrl,
  getLabReports,
  reviewLabObservation
} from "../../api/client";
import { SourcePdfViewer } from "../../components/SourcePdfViewer";

ModuleRegistry.registerModules([AllCommunityModule]);

type Props = {
  studyId: string;
  siteId: string;
  onReportSelected?: (report: LabReportView) => void;
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "检验报告读取失败";
}

function sourceBBox(observation: LabObservationView): number[] | null {
  const cells = observation.source_ref.cells as
    | Record<string, { bbox?: number[] | null }>
    | undefined;
  return (
    cells?.analyte?.bbox ??
    cells?.value_raw?.bbox ??
    (observation.source_ref.table_bbox as number[] | null | undefined) ??
    null
  );
}

function editableValues(observation: LabObservationView): Record<string, unknown> {
  return {
    subject_external_id: observation.subject_external_id,
    visit_key: observation.visit_key,
    analyte_raw: observation.analyte,
    specimen: observation.specimen,
    collected_on: observation.collected_on,
    collected_at: observation.collected_at,
    instance_type_raw: observation.instance_type,
    report_on: observation.report_on,
    report_revision: observation.report_revision,
    value_raw: observation.value_raw,
    unit_raw: observation.unit,
    lower_limit_raw: observation.lower_limit,
    upper_limit_raw: observation.upper_limit
  };
}

export function RecognitionReview({
  studyId,
  siteId,
  onReportSelected
}: Props) {
  const [reports, setReports] = useState<LabReportView[]>([]);
  const [report, setReport] = useState<LabReportView | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selected = useMemo(
    () =>
      report?.observations.find((item) => item.id === selectedId) ?? null,
    [report, selectedId]
  );

  const load = useCallback(async () => {
    const next = await getLabReports(studyId, siteId);
    setReports(next);
    setReport((current) => {
      const resolved = current
        ? next.find((item) => item.id === current.id)
        : next[0];
      return resolved ?? null;
    });
    setSelectedId((current) => {
      if (
        current &&
        next.some((candidate) =>
          candidate.observations.some((item) => item.id === current)
        )
      ) {
        return current;
      }
      return next[0]?.observations[0]?.id ?? null;
    });
  }, [siteId, studyId]);

  useEffect(() => {
    setReport(null);
    setReports([]);
    load().catch((reason) => setError(errorMessage(reason)));
  }, [load]);

  function adopt(next: LabReportView) {
    setReport(next);
    setReports((current) => {
      const found = current.some((item) => item.id === next.id);
      return found
        ? current.map((item) => (item.id === next.id ? next : item))
        : [next, ...current];
    });
    setSelectedId(next.observations[0]?.id ?? null);
    onReportSelected?.(next);
    window.dispatchEvent(new Event("cra-lab-report-updated"));
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("file");
    if (!(file instanceof File) || !file.name) {
      setError("请选择合成检验 PDF、PNG 或 JPEG。");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const next = await createLabReport({
        studyId,
        siteId,
        title: String(form.get("title") ?? "检验报告"),
        versionLabel: String(form.get("version_label") ?? "v1"),
        file
      });
      adopt(next);
      formElement.reset();
      setMessage(
        next.state === "provider_unavailable"
          ? "文件已私有保存；当前 OCR 未启用。可人工少量补录或跳过该范围。"
          : `已从原文件读取 ${next.observations_count} 条候选；复核仅展示低可信、歧义和异常。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function bulkConfirm() {
    if (!report) {
      return;
    }
    const ids = report.observations
      .filter(
        (item) =>
          item.validation_state === "ready_for_match" &&
          item.extraction_state !== "user_skipped"
      )
      .map((item) => item.id);
    if (ids.length === 0) {
      setMessage("没有通过结构校验、可批量确认的候选。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await batchConfirmLabObservations(report, ids);
      adopt(next);
      setMessage(`已批量确认 ${ids.length} 条通过校验的候选。`);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function review(
    action: "confirm" | "correct" | "skip",
    correctedFields?: Record<string, unknown>
  ) {
    if (!report || !selected) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await reviewLabObservation(
        report,
        selected.id,
        {
          action,
          correctedFields,
          note:
            action === "skip"
              ? "CRA 选择本局部不核查；不计正常结论"
              : undefined
        }
      );
      adopt(next);
      setSelectedId(selected.id);
      setMessage(
        action === "skip"
          ? "已保存局部跳过；该范围不会计正常。"
          : action === "correct"
            ? "人工更正已追加保存，源识别结果未被覆盖。"
            : "已保存候选核实状态。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function correct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const corrected = editableValues(selected);
    const fieldMap: Record<string, string> = {
      subject: "subject_external_id",
      visit: "visit_key",
      analyte: "analyte_raw",
      specimen: "specimen",
      collected_on: "collected_on",
      collected_at: "collected_at",
      instance: "instance_type_raw",
      report_on: "report_on",
      report_revision: "report_revision",
      value: "value_raw",
      unit: "unit_raw",
      lower: "lower_limit_raw",
      upper: "upper_limit_raw"
    };
    for (const [input, field] of Object.entries(fieldMap)) {
      corrected[field] = String(form.get(input) ?? "") || null;
    }
    await review("correct", corrected);
  }

  async function addManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!report) {
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const next = await addManualLabObservation(report, {
        subjectExternalId: String(form.get("subject") ?? ""),
        visitKey: String(form.get("visit") ?? ""),
        analyte: String(form.get("analyte") ?? ""),
        specimen: String(form.get("specimen") ?? ""),
        collectedOn: String(form.get("collected_on") ?? ""),
        collectedAt: String(form.get("collected_at") ?? ""),
        instanceType: String(form.get("instance") ?? ""),
        reportRevision: String(form.get("report_revision") ?? ""),
        valueRaw: String(form.get("value") ?? ""),
        unitRaw: String(form.get("unit") ?? ""),
        lowerLimit: String(form.get("lower") ?? ""),
        upperLimit: String(form.get("upper") ?? ""),
        sourceNote: String(form.get("source_note") ?? "")
      });
      adopt(next);
      setMessage("已追加人工候选；与原识别结果分别保存。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const columns: ColDef<LabObservationView>[] = [
    { field: "ordinal", headerName: "#", width: 55 },
    { field: "subject_external_id", headerName: "受试者", width: 130 },
    { field: "visit_key", headerName: "访视", width: 80 },
    { field: "analyte", headerName: "项目", width: 135 },
    { field: "value_raw", headerName: "结果", width: 85 },
    { field: "unit", headerName: "单位", width: 85 },
    {
      field: "collected_at",
      headerName: "采样时间",
      width: 175,
      valueGetter: (params) =>
        params.data?.collected_at ?? params.data?.collected_on ?? ""
    },
    { field: "instance_type", headerName: "实例", width: 100 },
    { field: "validation_state", headerName: "结构校验", width: 120 },
    { field: "extraction_state", headerName: "来源状态", width: 130 },
    {
      colId: "issues",
      headerName: "复核原因",
      flex: 1,
      minWidth: 170,
      valueGetter: (params) => (params.data?.issues ?? []).join("、")
    }
  ];

  const source = selected?.source_ref;
  const page = Number(source?.page ?? 1);
  const isPdf = report?.file_format === "text_pdf";

  return (
    <section className="lab-workspace" aria-labelledby="recognition-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M08 · 检验源文件自动读取</p>
          <h2 id="recognition-title">读取、来源定位与集中复核</h2>
          <p>
            自动候选与 CRA 核实分开保存。低可信、歧义和异常集中呈现；
            通过校验的候选可批量确认。
          </p>
        </div>
        <span className="status-chip muted">
          {report ? `${report.observations_count} 条候选` : "尚未读取"}
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <form className="lab-upload-form" onSubmit={(event) => void upload(event)}>
        <label>
          报告名称
          <input name="title" defaultValue="合成检验报告" required />
        </label>
        <label>
          版本
          <input name="version_label" defaultValue="v1" required />
        </label>
        <label>
          源文件
          <input
            type="file"
            name="file"
            accept=".pdf,.png,.jpg,.jpeg"
            required
          />
        </label>
        <button className="primary-button compact" disabled={busy}>
          读取原文件
        </button>
      </form>

      {reports.length > 0 && (
        <label className="lab-report-picker">
          已有识别报告
          <select
            value={report?.id ?? ""}
            onChange={(event) => {
              const next = reports.find((item) => item.id === event.target.value);
              if (next) {
                adopt(next);
              }
            }}
          >
            {reports.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id.slice(0, 8)} · {item.file_format} · {item.state}
              </option>
            ))}
          </select>
        </label>
      )}

      {report && (
        <>
          <div className="lab-provider-strip">
            <span>Provider {report.provider_name} {report.provider_version}</span>
            <span>状态 {report.state}</span>
            <span>支持范围 {report.support_profile.version as string}</span>
            <span>自动候选不等于 CRA 已核实</span>
          </div>
          {report.warnings.length > 0 && (
            <div className="inline-warning">
              {report.warnings.join("；")}
            </div>
          )}
          <div className="recognition-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={busy || report.observations.length === 0}
              onClick={() => void bulkConfirm()}
            >
              批量确认已通过结构校验的候选
            </button>
            <span className="muted-copy">
              只批量确认来源与匹配所需字段完整者；差异仍需处理。
            </span>
          </div>
          <div className="ag-theme-quartz lab-grid">
            <AgGridReact<LabObservationView>
              theme="legacy"
              rowData={report.observations}
              columnDefs={columns}
              rowSelection="single"
              onRowClicked={(event) => {
                if (event.data) {
                  setSelectedId(event.data.id);
                }
              }}
              defaultColDef={{ sortable: true, filter: true, resizable: true }}
              domLayout="autoHeight"
            />
          </div>

          <div className="lab-review-layout">
            <section className="lab-source-panel" aria-label="源文件定位">
              <p className="eyebrow">源定位</p>
              {selected ? (
                <>
                  <p>
                    第 {page} 页 ·{" "}
                    {String(source?.anchor ?? "来源区域")}
                  </p>
                  {isPdf ? (
                    <SourcePdfViewer
                      url={documentContentUrl(report.source_document_version_id)}
                      pageNumber={page}
                      bbox={sourceBBox(selected)}
                    />
                  ) : (
                    <img
                      className="lab-source-image"
                      src={documentContentUrl(
                        report.source_document_version_id
                      )}
                      alt="合成检验源图"
                    />
                  )}
                </>
              ) : (
                <p>选择一条候选查看原文件位置。</p>
              )}
            </section>

            <form className="lab-review-form" onSubmit={(event) => void correct(event)}>
              <p className="eyebrow">集中复核</p>
              <h3>{selected ? "确认或更正当前候选" : "选择候选"}</h3>
              {selected && (
                <>
                  <div className="lab-critical-fields">
                    <label>
                      受试者
                      <input name="subject" defaultValue={selected.subject_external_id ?? ""} />
                    </label>
                    <label>
                      访视
                      <input name="visit" defaultValue={selected.visit_key ?? ""} />
                    </label>
                    <label>
                      项目
                      <input name="analyte" defaultValue={selected.analyte ?? ""} />
                    </label>
                    <label>
                      结果
                      <input name="value" defaultValue={selected.value_raw ?? ""} />
                    </label>
                    <label>
                      单位
                      <input name="unit" defaultValue={selected.unit ?? ""} />
                    </label>
                    <label>
                      样本
                      <input name="specimen" defaultValue={selected.specimen ?? ""} />
                    </label>
                    <label>
                      采样日
                      <input
                        type="date"
                        name="collected_on"
                        defaultValue={selected.collected_on ?? ""}
                      />
                    </label>
                    <label>
                      采样时间
                      <input
                        type="datetime-local"
                        name="collected_at"
                        defaultValue={selected.collected_at?.slice(0, 16) ?? ""}
                      />
                    </label>
                    <label>
                      初检/复查
                      <input name="instance" defaultValue={selected.instance_type} />
                    </label>
                    <label>
                      报告版本
                      <input
                        name="report_revision"
                        defaultValue={selected.report_revision ?? ""}
                      />
                    </label>
                    <label>
                      报告日
                      <input
                        type="date"
                        name="report_on"
                        defaultValue={selected.report_on ?? ""}
                      />
                    </label>
                    <label>
                      参考下限
                      <input name="lower" defaultValue={selected.lower_limit ?? ""} />
                    </label>
                    <label>
                      参考上限
                      <input name="upper" defaultValue={selected.upper_limit ?? ""} />
                    </label>
                  </div>
                  <div className="recognition-actions">
                    <button className="primary-button compact" disabled={busy}>
                      保存人工更正
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={busy || selected.validation_state !== "ready_for_match"}
                      onClick={() => void review("confirm")}
                    >
                      确认当前候选
                    </button>
                    <button
                      type="button"
                      className="text-button danger"
                      disabled={busy}
                      onClick={() => void review("skip")}
                    >
                      本范围不核查
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>

          {["provider_unavailable", "failed", "partial"].includes(report.state) && (
            <form className="manual-lab-form" onSubmit={(event) => void addManual(event)}>
              <div>
                <p className="eyebrow">少量例外补录</p>
                <h3>人工候选</h3>
                <p>仅用于失败或不可读的少量路径；不会把自动能力标为完成。</p>
              </div>
              <label>
                受试者
                <input name="subject" required />
              </label>
              <label>
                访视
                <input name="visit" />
              </label>
              <label>
                项目
                <input name="analyte" required />
              </label>
              <label>
                结果
                <input name="value" required />
              </label>
              <label>
                单位
                <input name="unit" />
              </label>
              <label>
                样本
                <input name="specimen" />
              </label>
              <label>
                采样日
                <input name="collected_on" type="date" required />
              </label>
              <label>
                采样时间
                <input name="collected_at" type="datetime-local" />
              </label>
              <label>
                初检/复查
                <input name="instance" required />
              </label>
              <label>
                报告版本
                <input name="report_revision" />
              </label>
              <label>
                参考下限
                <input name="lower" />
              </label>
              <label>
                参考上限
                <input name="upper" />
              </label>
              <label className="manual-source-note">
                补录依据
                <input name="source_note" required />
              </label>
              <button className="secondary-button compact" disabled={busy}>
                追加人工候选
              </button>
            </form>
          )}
        </>
      )}
    </section>
  );
}
