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
