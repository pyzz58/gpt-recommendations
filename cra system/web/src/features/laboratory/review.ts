import type { LabComparisonFieldView } from "../../api/client";

const STATUS_LABEL: Record<string, string> = {
  agreement: "一致",
  value_difference: "数值差异",
  logic_difference: "范围逻辑差异",
  unit_review: "单位待核实",
  not_seen_in_export: "本次导出未见",
  not_comparable: "不可直接比较",
  unreadable: "无法识别",
  not_checked_by_user: "用户跳过"
};

export function comparisonStatusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status;
}

export function reviewableFieldIds(
  fields: LabComparisonFieldView[]
): string[] {
  return fields
    .filter((field) => field.result_status !== "agreement")
    .map((field) => field.id);
}

export function isPdfFileFormat(fileFormat: string | undefined): boolean {
  return fileFormat === "text_pdf" || fileFormat === "scanned_pdf";
}

export function imageHighlightStyle(
  bbox: number[] | null | undefined,
  size: { width: number; height: number } | null
): Record<string, string> | null {
  if (!bbox || bbox.length !== 4 || !size) {
    return null;
  }
  const [x0, y0, x1, y1] = bbox;
  if (
    ![x0, y0, x1, y1].every(Number.isFinite) ||
    x1 <= x0 ||
    y1 <= y0
  ) {
    return null;
  }
  return {
    left: `${(x0 / size.width) * 100}%`,
    top: `${(y0 / size.height) * 100}%`,
    width: `${((x1 - x0) / size.width) * 100}%`,
    height: `${((y1 - y0) / size.height) * 100}%`
  };
}
