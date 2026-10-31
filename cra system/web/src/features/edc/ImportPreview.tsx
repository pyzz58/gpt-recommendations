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
  type EDCMappingProfileView,
  type EDCPreviewView,
  type EDCSnapshotView,
  confirmEdcImport,
  getEdcMappings,
  getEdcPreview,
  getEdcSnapshot,
  previewEdcImport
} from "../../api/client";

ModuleRegistry.registerModules([AllCommunityModule]);

type Props = {
  studyId: string;
  siteId: string;
};

type ColumnMap = Record<string, string>;

type SheetMappingDraft = {
  header_row: number;
  data_start_row: number;
  columns: ColumnMap;
  included: boolean;
};

type MappingDraft = {
  sheets: Record<string, SheetMappingDraft>;
};

type PreviewRow = {
  row_number: number;
  anchor: string;
  display_values: Record<string, string | null>;
};

const REQUIRED_FIELDS = [
  ["subject_external_id", "受试者ID"],
  ["analyte", "检验项目"],
  ["value_raw", "结果"],
  ["collected_on", "采样日期"],
  ["collected_at", "采样时间"],
  ["instance_type", "初检/复查"],
  ["repeat_instance", "重复实例"]
] as const;

const EXTRA_FIELDS = [
  ["visit_key", "访视"],
  ["unit", "单位"],
  ["precision", "精度"],
  ["report_on", "报告日期"],
  ["report_revision", "报告修订"],
  ["specimen", "样本类型"],
  ["lower_limit", "参考下限"],
  ["upper_limit", "参考上限"]
] as const;

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "EDC Excel 导入失败";
}

function suggestedSheets(preview: EDCPreviewView): Record<string, unknown> {
  const suggested = preview.suggested_mapping as {
    sheets?: Record<string, unknown>;
  };
  return suggested.sheets ?? {};
}

export function initialiseEdcMapping(preview: EDCPreviewView): MappingDraft {
  const suggested = suggestedSheets(preview);
  return {
    sheets: Object.fromEntries(
      preview.sheets.map((sheet) => {
        const raw = suggested[sheet.name] as
          | {
              header_row?: number;
              data_start_row?: number;
              columns?: ColumnMap;
              included?: boolean;
            }
          | undefined;
        return [
          sheet.name,
          {
            header_row: raw?.header_row ?? sheet.header_row ?? 1,
            data_start_row:
              raw?.data_start_row ?? (sheet.header_row ?? 1) + 1,
            columns: { ...(raw?.columns ?? {}) },
            included:
              raw?.included ?? preview.included_sheets.includes(sheet.name)
          }
        ];
      })
    )
  };
}

export function missingRequiredMapping(mapping: MappingDraft): string[] {
  return Object.entries(mapping.sheets).flatMap(([sheetName, sheet]) => {
    if (!sheet.included) {
      return [];
    }
    const missing = REQUIRED_FIELDS.slice(0, 3)
      .filter(([field]) => !sheet.columns[field])
      .map(([, label]) => `${sheetName}: ${label}`);
    if (!sheet.columns.collected_on && !sheet.columns.collected_at) {
      missing.push(`${sheetName}: 采样日期/时间`);
    }
    if (!sheet.columns.instance_type && !sheet.columns.repeat_instance) {
      missing.push(`${sheetName}: 初检/复查实例`);
    }
    return missing;
  });
}

function previewRows(preview: EDCPreviewView, sheetName: string): PreviewRow[] {
  const sheet = preview.sheets.find((item) => item.name === sheetName);
  return (sheet?.rows ?? []).map((row) => ({
    row_number: row.row_number,
    anchor: row.anchor,
    display_values: row.display_values
  }));
}

export function ImportPreview({ studyId, siteId }: Props) {
  const [profiles, setProfiles] = useState<EDCMappingProfileView[]>([]);
  const [preview, setPreview] = useState<EDCPreviewView | null>(null);
  const [snapshot, setSnapshot] = useState<EDCSnapshotView | null>(null);
  const [mapping, setMapping] = useState<MappingDraft | null>(null);
  const [scopeStatus, setScopeStatus] = useState<"declared" | "unknown">(
    "declared"
  );
  const [declaredComplete, setDeclaredComplete] = useState(false);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadProfiles = useCallback(async () => {
    setProfiles(await getEdcMappings(studyId, siteId));
  }, [studyId, siteId]);

  useEffect(() => {
    loadProfiles().catch((reason) => setError(errorMessage(reason)));
  }, [loadProfiles]);

  const adoptPreview = useCallback((next: EDCPreviewView) => {
    setPreview(next);
    setSnapshot(null);
    setMapping(initialiseEdcMapping(next));
    setActiveSheet(
      next.sheets.find((sheet) => next.included_sheets.includes(sheet.name))
        ?.name ??
        next.sheets[0]?.name ??
        null
    );
    setScopeStatus(next.scope_status);
    setDeclaredComplete(
      Boolean(
        (next.export_scope as { declared_complete?: boolean })
          .declared_complete
      )
    );
  }, []);

  useEffect(() => {
    const previewId = new URLSearchParams(window.location.search).get(
      "edcPreview"
    );
    if (!previewId) {
      return;
    }
    setBusy(true);
    getEdcPreview(previewId)
      .then(async (next) => {
        adoptPreview(next);
        if (next.snapshot_id) {
          setSnapshot(await getEdcSnapshot(next.snapshot_id));
        }
      })
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [adoptPreview]);

  async function previewFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("file");
    if (!(file instanceof File) || !file.name) {
      setError("请选择 EDC 导出的 .xlsx 文件。");
      return;
    }
    const profileId = String(form.get("mapping_profile") ?? "");
    const selectedProfile = profiles.find((item) => item.id === profileId);
    const profileSheets = selectedProfile
      ? Object.keys(
          (
            selectedProfile.mapping as {
              sheets?: Record<string, unknown>;
            }
          ).sheets ?? {}
        )
      : [];
    const startedAt = String(form.get("export_started_at") ?? "").trim();
    const completedAt = String(form.get("export_completed_at") ?? "").trim();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const next = await previewEdcImport({
        studyId,
        siteId,
        title: String(form.get("title") ?? "EDC 检验导出"),
        file,
        exportStartedAt: startedAt ? `${startedAt}:00Z` : "",
        exportCompletedAt: completedAt ? `${completedAt}:00Z` : "",
        includedSheets: profileSheets,
        mappingProfileId: selectedProfile?.id,
        identityNamespace: String(
          form.get("identity_namespace") ?? "edc"
        ),
        exportScope: {
          status: String(form.get("scope_status") ?? "declared"),
          forms: String(form.get("forms") ?? "")
            .split(/[,，;；]/)
            .map((value) => value.trim())
            .filter(Boolean),
          subjects: String(form.get("subjects") ?? "")
            .split(/[,，;；]/)
            .map((value) => value.trim())
            .filter(Boolean),
          sites: String(form.get("sites") ?? "")
            .split(/[,，;；]/)
            .map((value) => value.trim())
            .filter(Boolean),
          date_start: String(form.get("date_start") ?? "") || null,
          date_end: String(form.get("date_end") ?? "") || null,
          filters: {},
          declared_complete: false,
          note: String(form.get("scope_note") ?? "") || null
        }
      });
      adoptPreview(next);
      setMessage(
        next.replayed
          ? "相同预览请求已复用原结果。"
          : `已读取 ${next.sheets.length} 个 sheet；公式与缓存分别保留。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function applyProfile(profileId: string) {
    const profile = profiles.find((item) => item.id === profileId);
    if (!profile) {
      return;
    }
    const mappingValue = profile.mapping as {
      sheets: Record<string, SheetMappingDraft>;
    };
    setMapping({
      sheets: Object.fromEntries(
        Object.entries(mappingValue.sheets).map(([name, sheet]) => [
          name,
          {
            header_row: sheet.header_row,
            data_start_row: sheet.data_start_row,
            columns: { ...sheet.columns },
            included: sheet.included
          }
        ])
      )
    });
  }

  function updateMapping(
    sheetName: string,
    field: "header_row" | "data_start_row" | "included" | string,
    value: string | number | boolean
  ) {
    setMapping((current) => {
      if (!current) {
        return current;
      }
      const sheet = current.sheets[sheetName];
      if (!sheet) {
        return current;
      }
      if (field === "header_row" || field === "data_start_row") {
        return {
          sheets: {
            ...current.sheets,
            [sheetName]: { ...sheet, [field]: Number(value) }
          }
        };
      }
      if (field === "included") {
        return {
          sheets: {
            ...current.sheets,
            [sheetName]: { ...sheet, included: Boolean(value) }
          }
        };
      }
      const columns = { ...sheet.columns };
      if (String(value).trim()) {
        columns[field] = String(value).trim();
      } else {
        delete columns[field];
      }
      return {
        sheets: {
          ...current.sheets,
          [sheetName]: { ...sheet, columns }
        }
      };
    });
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preview || !mapping) {
      return;
    }
    const missing = missingRequiredMapping(mapping);
    if (missing.length > 0) {
      setError(`映射缺少必要字段：${missing.join("；")}`);
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const next = await confirmEdcImport({
        preview,
        mapping: mapping as unknown as Record<string, unknown>,
        exportScope: {
          status: scopeStatus,
          forms: preview.export_scope.forms ?? [],
          subjects: preview.export_scope.subjects ?? [],
          sites: preview.export_scope.sites ?? [],
          date_start: preview.export_scope.date_start ?? null,
          date_end: preview.export_scope.date_end ?? null,
          filters: preview.export_scope.filters ?? {},
          declared_complete:
            scopeStatus === "declared" ? declaredComplete : false,
          note: preview.export_scope.note ?? null
        },
        identityNamespace: preview.identity_namespace,
        saveMappingName: String(form.get("save_mapping_name") ?? "").trim()
      });
      setSnapshot(next);
      setPreview({
        ...preview,
        state: "confirmed",
        revision: preview.revision + 1,
        snapshot_id: next.id
      });
      await loadProfiles();
      setMessage(
        next.replayed
          ? "相同文件、映射和导出范围已识别，未复制快照。"
          : `快照已保存：${next.row_count} 行、${next.record_count} 条标准检验记录。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const activePreviewSheet = preview?.sheets.find(
    (sheet) => sheet.name === activeSheet
  );
  const headers = activePreviewSheet?.headers.filter(Boolean) ?? [];
  const rowData = activeSheet && preview ? previewRows(preview, activeSheet) : [];
  const gridColumns: ColDef<PreviewRow>[] = [
    { field: "row_number", headerName: "Excel行", width: 90, pinned: "left" },
    { field: "anchor", headerName: "原始位置", width: 190, pinned: "left" },
    ...headers.map<ColDef<PreviewRow>>((header) => ({
      headerName: header,
      width: 140,
      valueGetter: (params) => params.data?.display_values[header] ?? ""
    }))
  ];
  const recordColumns: ColDef<EDCSnapshotView["records"][number]>[] = [
    { field: "subject_external_id", headerName: "受试者", width: 130 },
    { field: "visit_key", headerName: "访视", width: 90 },
    { field: "analyte", headerName: "项目", width: 140 },
    { field: "value_raw", headerName: "结果", width: 100 },
    { field: "unit_raw", headerName: "单位", width: 90 },
    {
      field: "collected_at",
      headerName: "采样时间",
      width: 180,
      valueGetter: (params) =>
        params.data?.collected_at ?? params.data?.collected_on ?? ""
    },
    { field: "instance_type", headerName: "实例", width: 100 },
    { field: "identity_status", headerName: "身份", width: 100 },
    { field: "validation_status", headerName: "状态", width: 130 },
    {
      colId: "issues",
      headerName: "缺口",
      flex: 1,
      valueGetter: (params) => (params.data?.issues ?? []).join("、")
    }
  ];

  return (
    <section className="edc-workspace" aria-labelledby="edc-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M07 · EDC Excel 检验快照</p>
          <h2 id="edc-title">导出范围、映射与原始行</h2>
          <p>
            本次没有找到只表示“不在该导出中”，不直接推断 EDC 漏录。公式只读取缓存，
            不执行公式或宏。
          </p>
        </div>
        <span className="status-chip muted">
          {snapshot
            ? `快照 ${snapshot.record_count} 条`
            : preview
              ? "预览待确认"
              : "尚未导入"}
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <form className="edc-upload-form" onSubmit={(event) => void previewFile(event)}>
        <label>
          导出名称
          <input name="title" defaultValue="EDC 检验导出" required />
        </label>
        <label>
          EDC XLSX
          <input type="file" name="file" accept=".xlsx" required />
        </label>
        <label>
          身份命名空间
          <input name="identity_namespace" defaultValue="edc" required />
        </label>
        <label>
          已确认映射（可选）
          <select name="mapping_profile" defaultValue="">
            <option value="">按表头自动建议</option>
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name} · v{profile.revision}
              </option>
            ))}
          </select>
        </label>
        <label>
          导出开始（UTC）
          <input type="datetime-local" name="export_started_at" />
        </label>
        <label>
          导出完成（UTC）
          <input type="datetime-local" name="export_completed_at" />
        </label>
        <label>
          范围状态
          <select
            name="scope_status"
            value={scopeStatus}
            onChange={(event) =>
              setScopeStatus(
                event.target.value as "declared" | "unknown"
              )
            }
          >
            <option value="declared">已声明导出范围</option>
            <option value="unknown">范围未知</option>
          </select>
        </label>
        <label>
          表单
          <input name="forms" placeholder="Hematology, Chemistry" />
        </label>
        <label>
          受试者
          <input name="subjects" placeholder="SYN-EDC-001, SYN-EDC-002" />
        </label>
        <label>
          中心
          <input name="sites" placeholder="S01" />
        </label>
        <label>
          起始日期
          <input type="date" name="date_start" />
        </label>
        <label>
          结束日期
          <input type="date" name="date_end" />
        </label>
        <label>
          范围说明
          <input name="scope_note" placeholder="按项目/受试者/日期过滤" />
        </label>
        <button className="primary-button compact" type="submit" disabled={busy}>
          解析并预览
        </button>
      </form>

      {preview && mapping && (
        <div className="edc-preview-layout">
          <section className="edc-preview-panel">
            <div className="applicable-heading">
              <div>
                <p className="eyebrow">原始 sheet / row / cell</p>
                <h3>Excel 预览</h3>
              </div>
              <span className="status-chip">
                {preview.included_sheets.length} 个纳入 sheet
              </span>
            </div>
            <div className="edc-sheet-tabs">
              {preview.sheets.map((sheet) => (
                <button
                  type="button"
                  key={sheet.name}
                  className={activeSheet === sheet.name ? "active" : ""}
                  onClick={() => setActiveSheet(sheet.name)}
                >
                  {sheet.name}
                  <small>{sheet.state}</small>
                </button>
              ))}
            </div>
            {activePreviewSheet && (
              <>
                <p>
                  表头行 {activePreviewSheet.header_row ?? "未识别"} ·{" "}
                  {activePreviewSheet.populated_rows} 个非空行 · 类型{" "}
                  {Object.entries(activePreviewSheet.value_types)
                    .map(([type, count]) => `${type}:${count}`)
                    .join("，")}
                </p>
                {activePreviewSheet.warnings.length > 0 && (
                  <p className="inline-warning">
                    {activePreviewSheet.warnings.join("；")}
                  </p>
                )}
                <div className="ag-theme-quartz edc-grid">
                  <AgGridReact<PreviewRow>
                    theme="legacy"
                    rowData={rowData}
                    columnDefs={gridColumns}
                    defaultColDef={{ sortable: true, filter: true, resizable: true }}
                    domLayout="autoHeight"
                    suppressCellFocus
                  />
                </div>
                {activePreviewSheet.formula_cells.length > 0 && (
                  <details className="formula-details">
                    <summary>
                      公式与缓存（{activePreviewSheet.formula_cells.length}）
                    </summary>
                    <ul>
                      {activePreviewSheet.formula_cells.map((cell) => (
                        <li key={cell.coordinate}>
                          <strong>{cell.coordinate}</strong>{" "}
                          {cell.formula} → {cell.cached_text ?? "无缓存"}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </>
            )}
          </section>

          <form className="edc-mapping-panel" onSubmit={(event) => void confirm(event)}>
            <div className="applicable-heading">
              <div>
                <p className="eyebrow">列映射与实例</p>
                <h3>确认后才生成不可变快照</h3>
              </div>
            </div>
            <label>
              复用已确认映射
              <select
                defaultValue={preview.mapping_profile_id ?? ""}
                onChange={(event) => applyProfile(event.target.value)}
              >
                <option value="">当前建议映射</option>
                {preview.mapping_profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name} · v{profile.revision}
                  </option>
                ))}
              </select>
            </label>
            {preview.sheets.map((sheet) => {
              const sheetMapping = mapping.sheets[sheet.name];
              if (!sheetMapping) {
                return null;
              }
              return (
                <details
                  key={sheet.name}
                  className="edc-mapping-sheet"
                  open={sheet.name === activeSheet}
                >
                  <summary>
                    <label className="checkbox-line">
                      <input
                        type="checkbox"
                        checked={sheetMapping.included}
                        onChange={(event) =>
                          updateMapping(
                            sheet.name,
                            "included",
                            event.target.checked
                          )
                        }
                      />
                      {sheet.name} · {sheet.state}
                    </label>
                  </summary>
                  <div className="edc-row-settings">
                    <label>
                      表头行
                      <input
                        type="number"
                        min={1}
                        value={sheetMapping.header_row}
                        onChange={(event) =>
                          updateMapping(
                            sheet.name,
                            "header_row",
                            event.target.value
                          )
                        }
                      />
                    </label>
                    <label>
                      数据起始行
                      <input
                        type="number"
                        min={2}
                        value={sheetMapping.data_start_row}
                        onChange={(event) =>
                          updateMapping(
                            sheet.name,
                            "data_start_row",
                            event.target.value
                          )
                        }
                      />
                    </label>
                  </div>
                  <div className="edc-field-grid">
                    {[...REQUIRED_FIELDS, ...EXTRA_FIELDS].map(
                      ([field, label]) => (
                        <label key={field}>
                          {label}
                          <input
                            list={`headers-${sheet.name}`}
                            value={sheetMapping.columns[field] ?? ""}
                            onChange={(event) =>
                              updateMapping(
                                sheet.name,
                                field,
                                event.target.value
                              )
                            }
                          />
                        </label>
                      )
                    )}
                    <datalist id={`headers-${sheet.name}`}>
                      {sheet.headers.filter(Boolean).map((header) => (
                        <option key={header} value={header} />
                      ))}
                    </datalist>
                  </div>
                </details>
              );
            })}
            <label className="checkbox-line">
              <input
                type="checkbox"
                checked={declaredComplete}
                disabled={scopeStatus === "unknown"}
                onChange={(event) =>
                  setDeclaredComplete(event.target.checked)
                }
              />
              用户声明该导出覆盖本次判断所需范围
            </label>
            <label>
              保存映射名称（可选）
              <input
                name="save_mapping_name"
                placeholder="例如 Hematology v1"
              />
            </label>
            <button className="primary-button compact" type="submit" disabled={busy}>
              确认映射并保存快照
            </button>
          </form>
        </div>
      )}

      {snapshot && (
        <section className="edc-snapshot" aria-labelledby="edc-snapshot-title">
          <div className="applicable-heading">
            <div>
              <p className="eyebrow">不可变标准记录</p>
              <h3 id="edc-snapshot-title">
                快照 {snapshot.row_count} 行 / {snapshot.record_count} 条记录
              </h3>
            </div>
            <span className="status-chip">
              {snapshot.scope_status}
            </span>
          </div>
          <p>
            缺失语义固定为 <code>{snapshot.absence_semantics}</code>，
            不代表可直接判定 EDC 漏录。
          </p>
          <div className="ag-theme-quartz edc-grid">
            <AgGridReact<EDCSnapshotView["records"][number]>
              theme="legacy"
              rowData={snapshot.records}
              columnDefs={recordColumns}
              defaultColDef={{ sortable: true, filter: true, resizable: true }}
              domLayout="autoHeight"
              suppressCellFocus
            />
          </div>
        </section>
      )}
    </section>
  );
}
