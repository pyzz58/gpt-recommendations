import type { ReactNode } from "react";

const stateLabels: Record<string, string> = {
  draft: "草稿",
  needs_input: "缺少输入",
  needs_revision: "需要修订",
  ready_for_review: "待阶段审阅",
  blocked: "现实条件阻塞",
  ready: "已就绪",
  queued: "已排队",
  running: "运行中",
  submitted: "待验收",
  accepted: "已接受",
  changes_requested: "要求重做",
  disputed: "保留争议",
  rework: "需重做",
  waiting_external: "等待外部",
  paused: "已暂停",
  failed: "失败",
  cancelled: "已取消",
  unassigned: "未分配",
  inactive: "未激活",
  active: "活跃",
  proposed: "待比较",
  under_review: "审阅中",
  needs_evidence: "需补证",
  shortlisted: "已入围",
  selected: "已选择",
  watchlist: "观察中",
  rejected: "已排除",
  stored: "已保存",
  extracting: "解析中",
  indexing: "建索引",
  partial: "部分完成",
  not_configured: "未配置",
  not_checked: "未检查",
  unavailable: "不可用",
  succeeded: "已完成",
  unreviewed: "未核查",
  needs_review: "需复核",
  reviewed_for_scope: "范围已核",
  local_only: "仅本地",
  approved_cloud: "已批准云端",
  candidate: "候选",
  contacted: "已联系",
  verified: "已登记核实",
  scope_ready: "范围就绪",
  requested: "已请求",
  quoted: "已收到报价",
  authorized: "已授权",
  executing: "执行记录中",
  delivered: "已交付",
  closed: "已关闭",
  expected: "待交付",
  received: "已接收",
  information_only: "仅信息",
  official_confirmed: "官方来源已核",
  expired: "已过期",
  declined: "已拒绝",
  replied: "已回复",
  limited_review: "有限审阅",
  engaged: "已合作",
};

export function stateLabel(value: string): string {
  return stateLabels[value] ?? value;
}

export function StatusPill({
  value,
  tone,
}: {
  value: string;
  tone?: "neutral" | "good" | "warn" | "bad" | "info";
}) {
  return (
    <span className={`statusPill ${tone ?? statusTone(value)}`}>
      {stateLabel(value)}
    </span>
  );
}

export function statusTone(value: string): "neutral" | "good" | "warn" | "bad" | "info" {
  if (
    [
      "accepted",
      "ready",
      "active",
      "selected",
      "succeeded",
      "verified",
      "official_confirmed",
    ].includes(
      value,
    )
  ) {
    return "good";
  }
  if (
    [
      "failed",
      "rejected",
      "cancelled",
      "unavailable",
      "bad",
      "blocked",
      "expired",
      "declined",
    ].includes(
      value,
    )
  ) {
    return "bad";
  }
  if (
    [
      "needs_input",
      "needs_evidence",
      "needs_revision",
      "rework",
      "submitted",
      "partial",
      "candidate",
      "contacted",
      "requested",
      "expected",
      "information_only",
    ].includes(value)
  ) {
    return "warn";
  }
  if (
    [
      "running",
      "queued",
      "extracting",
      "indexing",
      "shortlisted",
      "ready_for_review",
      "scope_ready",
      "quoted",
      "authorized",
      "executing",
      "delivered",
      "under_review",
      "received",
      "replied",
      "limited_review",
      "engaged",
    ].includes(value)
  ) {
    return "info";
  }
  return "neutral";
}

export function LoadingPanel({ label = "正在读取本地数据…" }: { label?: string }) {
  return (
    <div className="loadingPanel" aria-live="polite">
      <span className="pulseDot" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorPanel({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="errorPanel" role="alert">
      <div>
        <strong>读取失败</strong>
        <p>{message}</p>
      </div>
      {onRetry && (
        <button type="button" className="button secondary" onClick={onRetry}>
          重试
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="emptyState">
      <span className="emptyMark">○</span>
      <div>
        <strong>{title}</strong>
        <div className="emptyCopy">{children}</div>
      </div>
    </div>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  aside,
}: {
  eyebrow: string;
  title: string;
  aside?: ReactNode;
}) {
  return (
    <div className="sectionHeader">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {aside}
    </div>
  );
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatBytes(value: number | null): string {
  if (value === null) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function trackLabel(value: string): string {
  return (
    {
      pet_repurposing: "宠物药",
      ivd: "IVD",
      device: "器械",
    }[value] ?? value
  );
}
