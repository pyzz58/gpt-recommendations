import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  type ApplicabilityResponse,
  type DocumentVersionView,
  type DocumentView,
  type RuleListItemView,
  type RuleVersionSummaryView,
  type RuleVersionDetailView,
  confirmRule,
  createVersionActivation,
  extractRuleCandidates,
  getApplicableRules,
  getDocumentVersions,
  getDocuments,
  getRuleVersion,
  getRuleVersions,
  getRules
} from "../../api/client";
import { RuleConfirmation } from "./RuleConfirmation";
import { RuleHistory } from "./RuleHistory";
import { RuleTree } from "./RuleTree";

type Props = {
  studyId: string;
  siteId: string;
};

const STATUS_LABEL: Record<string, string> = {
  candidate: "候选待确认",
  confirmed: "已确认",
  withdrawn: "已撤销",
  ready: "候选已就绪",
  needs_review: "等待用户确认",
  analysis_required: "需要人工分析",
  applicable: "当前适用",
  not_applicable: "当前未触发",
  unknown: "条件未知",
  exception: "例外路径"
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "规则操作失败";
}

export function RuleWorkspace({ studyId, siteId }: Props) {
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [versions, setVersions] = useState<DocumentVersionView[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  );
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    null
  );
  const [rules, setRules] = useState<RuleListItemView[]>([]);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [ruleVersions, setRuleVersions] = useState<RuleVersionSummaryView[]>([]);
  const [selectedRuleVersionId, setSelectedRuleVersionId] = useState<
    string | null
  >(null);
  const [detail, setDetail] = useState<RuleVersionDetailView | null>(null);
  const [applicability, setApplicability] =
    useState<ApplicabilityResponse | null>(null);
  const [eventDate, setEventDate] = useState("2021-01-01");
  const [factsJson, setFactsJson] = useState(
    JSON.stringify(
      {
        study_phase: "screening",
        screening_active: true,
        consent_given: false,
        emergency_treatment: false
      },
      null,
      2
    )
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ruleDocuments = useMemo(
    () => documents.filter((document) => document.purpose === "rule"),
    [documents]
  );
  const selectedVersion = useMemo(
    () => versions.find((version) => version.id === selectedVersionId) ?? null,
    [versions, selectedVersionId]
  );
  const selectedRule = useMemo(
    () => rules.find((rule) => rule.id === selectedRuleId) ?? null,
    [rules, selectedRuleId]
  );

  const loadRules = useCallback(async () => {
    const next = await getRules(studyId, siteId);
    setRules(next);
    setSelectedRuleId((current) =>
      current && next.some((rule) => rule.id === current)
        ? current
        : next[0]?.id ?? null
    );
    return next;
  }, [studyId, siteId]);

  const loadDocumentList = useCallback(async () => {
    const next = await getDocuments(studyId, siteId);
    const ruleOnly = next.filter((document) => document.purpose === "rule");
    setDocuments(next);
    setSelectedDocumentId((current) =>
      current && ruleOnly.some((document) => document.id === current)
        ? current
        : ruleOnly[0]?.id ?? null
    );
  }, [studyId, siteId]);

  useEffect(() => {
    setBusy(true);
    setError(null);
    Promise.all([loadDocumentList(), loadRules()])
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [loadDocumentList, loadRules]);

  useEffect(() => {
    setApplicability(null);
    if (!selectedDocumentId) {
      setVersions([]);
      setSelectedVersionId(null);
      return;
    }
    setBusy(true);
    getDocumentVersions(selectedDocumentId)
      .then((next) => {
        setVersions(next);
        const usable = next.find((version) =>
          ["completed", "partial"].includes(version.parse_status)
        );
        setSelectedVersionId(usable?.id ?? next[0]?.id ?? null);
      })
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [selectedDocumentId]);

  useEffect(() => {
    if (!selectedRule) {
      setRuleVersions([]);
      setSelectedRuleVersionId(null);
      setDetail(null);
      return;
    }
    setBusy(true);
    getRuleVersions(selectedRule.id)
      .then((next) => {
        setRuleVersions(next);
        setSelectedRuleVersionId(
          next.find(
            (version) => version.id === selectedRule.current_version?.id
          )?.id ??
            next[0]?.id ??
            null
        );
      })
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [selectedRule]);

  useEffect(() => {
    if (!selectedRuleVersionId) {
      setDetail(null);
      return;
    }
    setBusy(true);
    getRuleVersion(selectedRuleVersionId)
      .then(setDetail)
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [selectedRuleVersionId]);

  async function extract() {
    if (!selectedVersion) {
      setError("请先选择已解析的规则资料版本。");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await extractRuleCandidates(
        selectedVersion.id,
        crypto.randomUUID()
      );
      setMessage(
        result.duplicate_source
          ? "重复来源已复用原规则快照，没有重复创建或确认。"
          : result.replayed
            ? "同一版本已提取，沿用原规则快照。"
            : `规则快照已建立：${result.confirmed_count} 条直接纳入/继承确认，${result.candidate_count} 条等待确认。`
      );
      const next = await loadRules();
      setSelectedRuleId(next[0]?.id ?? null);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(operations: Record<string, unknown>[]) {
    if (!selectedRule?.current_version || !detail) {
      throw new Error("没有可确认的规则版本");
    }
    setBusy(true);
    setError(null);
    try {
      const confirmed = await confirmRule(selectedRule.id, {
        expectedRevision: selectedRule.revision,
        baseVersionId: detail.version.id,
        reason: "CRA在工作台确认规则候选及修正",
        operations
      });
      await loadRules();
      const history = await getRuleVersions(selectedRule.id);
      setRuleVersions(history);
      setSelectedRuleVersionId(confirmed.rule_version_id);
      setMessage("规则已确认；原候选和修改历史均已保留。");
    } finally {
      setBusy(false);
    }
  }

  async function activate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVersion) {
      setError("请先选择规则资料版本。");
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const result = await createVersionActivation({
        documentVersionId: selectedVersion.id,
        startsOn: String(form.get("starts_on") ?? ""),
        endsBefore: String(form.get("ends_before") ?? ""),
        reason: String(form.get("reason") ?? "")
      });
      setMessage(
        result.conflicts.length > 0
          ? `启用日已保存，但同范围存在 ${result.conflicts.length} 个重叠区间；系统未替你选择。`
          : "手动开始使用日已保存。上传日期没有替代该日期。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function applyAtEvent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const raw = JSON.parse(factsJson) as Record<string, unknown>;
      const facts = Object.fromEntries(
        Object.entries(raw).map(([key, value]) => [
          key,
          value &&
          typeof value === "object" &&
          "value" in (value as Record<string, unknown>)
            ? value
            : { value }
        ])
      );
      setApplicability(
        await getApplicableRules({
          studyId,
          siteId,
          eventDate,
          facts
        })
      );
    } catch (reason) {
      setError(
        reason instanceof SyntaxError
          ? "事实JSON格式不正确。"
          : errorMessage(reason)
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rule-workspace" aria-labelledby="rules-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M03 · 可追溯规则与分层list</p>
          <h2 id="rules-title">规则候选、确认与事件日适用</h2>
          <p>
            关键要求 → 条件与例外 → 分支/子项 → 原文。未知不会默认走另一条分支。
          </p>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={() => {
            setBusy(true);
            Promise.all([loadDocumentList(), loadRules()])
              .catch((reason) => setError(errorMessage(reason)))
              .finally(() => setBusy(false));
          }}
          disabled={busy}
        >
          刷新资料与规则
        </button>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <div className="rule-toolbar">
        <label>
          规则资料
          <select
            value={selectedDocumentId ?? ""}
            onChange={(event) => setSelectedDocumentId(event.target.value)}
          >
            {ruleDocuments.length === 0 && (
              <option value="">尚未上传规则用途资料</option>
            )}
            {ruleDocuments.map((document) => (
              <option key={document.id} value={document.id}>
                {document.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          资料版本
          <select
            value={selectedVersionId ?? ""}
            onChange={(event) => setSelectedVersionId(event.target.value)}
          >
            {versions.length === 0 && <option value="">没有版本</option>}
            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.version_label} · {version.parse_status}
              </option>
            ))}
          </select>
        </label>
        <button
          className="primary-button compact"
          type="button"
          onClick={() => void extract()}
          disabled={busy || !selectedVersion}
        >
          自动提取候选
        </button>
      </div>

      {selectedVersion && (
        <div className="source-meta">
          <span>{selectedVersion.original_filename}</span>
          <span>解析 {selectedVersion.parse_status}</span>
          <span>开始使用 {selectedVersion.user_starts_on ?? "尚未设置"}</span>
        </div>
      )}

      <div className="rule-layout">
        <aside className="rule-index" aria-label="规则索引">
          <h3>{rules.length} 条稳定规则</h3>
          {rules.length === 0 ? (
            <p>选择已解析规则资料并点击“自动提取候选”。</p>
          ) : (
            rules.map((rule) => (
              <button
                key={rule.id}
                type="button"
                className={rule.id === selectedRuleId ? "active" : ""}
                onClick={() => setSelectedRuleId(rule.id)}
              >
                <span>{rule.rule_key}</span>
                {rule.title}
                <small>
                  {STATUS_LABEL[rule.status] ?? rule.status}
                  {rule.current_version
                    ? ` · v${rule.current_version.version_no}`
                    : ""}
                </small>
              </button>
            ))
          )}
        </aside>

        <div className="rule-main">
          {detail ? (
            <>
              <RuleHistory
                versions={ruleVersions}
                selectedVersionId={detail.version.id}
                currentVersionId={selectedRule?.current_version?.id ?? null}
                relations={detail.relations}
                onSelect={setSelectedRuleVersionId}
              />
              <RuleTree tree={detail.tree} />
              {selectedRule?.current_version?.id === detail.version.id ? (
                <RuleConfirmation
                  key={detail.version.id}
                  detail={detail}
                  busy={busy}
                  onConfirm={confirm}
                />
              ) : (
                <p className="notice" role="status">
                  当前查看的是历史版本，只读显示。要修改规则，请切换到“当前”版本。
                </p>
              )}
            </>
          ) : (
            <p className="empty-documents">当前尚无可查看的规则版本。</p>
          )}
        </div>
      </div>

      <div className="rule-runtime-grid">
        <form className="activation-form" onSubmit={(event) => void activate(event)}>
          <p className="eyebrow">按临床事件日期选择依据</p>
          <h3>手动设置开始使用日</h3>
          <p>开始日包含当天，结束日不包含；上传时间不能替代业务启用日。</p>
          <label>
            开始使用日
            <input type="date" name="starts_on" required defaultValue="2021-01-01" />
          </label>
          <label>
            结束于（可选）
            <input type="date" name="ends_before" />
          </label>
          <label>
            依据说明
            <input
              name="reason"
              required
              defaultValue="CRA核对项目/中心实际启用日期"
            />
          </label>
          <button className="secondary-button" type="submit" disabled={busy}>
            保存启用区间
          </button>
        </form>

        <form className="applicability-form" onSubmit={(event) => void applyAtEvent(event)}>
          <p className="eyebrow">事件时点解析</p>
          <h3>查看当时适用的分层list</h3>
          <label>
            临床事件日期
            <input
              type="date"
              value={eventDate}
              onChange={(event) => setEventDate(event.target.value)}
              required
            />
          </label>
          <label>
            已确认事实（JSON）
            <textarea
              value={factsJson}
              onChange={(event) => setFactsJson(event.target.value)}
              rows={8}
            />
          </label>
          <button className="secondary-button" type="submit" disabled={busy}>
            按事件时间解析
          </button>
        </form>
      </div>

      {applicability && (
        <section className="applicable-results" aria-live="polite">
          <div className="applicable-heading">
            <div>
              <p className="eyebrow">OutputEnvelope</p>
              <h3>事件日适用规则</h3>
            </div>
            <span className={`status-chip ${applicability.envelope.status}`}>
              {applicability.envelope.status}
            </span>
          </div>
          <p>
            共性规则包：
            {applicability.common_policy_configured ? "已装载并区分取得状态" : "未配置"}
            ；冲突 {(applicability.envelope.conflicts ?? []).length} 项，未知{" "}
            {(applicability.envelope.unknowns ?? []).length} 项。
          </p>
          {(applicability.envelope.conflicts ?? []).map((conflict) => (
            <div className="notice notice-error" key={conflict.conflict_id}>
              {conflict.description}
            </div>
          ))}
          {applicability.rules.length === 0 ? (
            <p className="empty-documents">
              没有确认且覆盖该事件日期的规则；不会自动取最新版本。
            </p>
          ) : (
            applicability.rules.map((rule) => (
              <RuleTree
                key={`${rule.rule_id}-${rule.rule_version_id}`}
                tree={rule.tree}
                evaluation={rule.evaluation}
              />
            ))
          )}
        </section>
      )}
    </section>
  );
}
