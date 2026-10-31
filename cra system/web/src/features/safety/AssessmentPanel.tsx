import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type SafetyAssessmentSummaryView,
  type SafetyAssessmentView,
  type SafetyDimensionView,
  type SubjectView,
  createSafetyAssessment,
  getSafetyAssessment,
  getSafetyAssessments,
  getSubjects,
  linkSafetyAssessmentIssue,
  recordMedicalSafetyResponse,
  recordSafetyCraReview
} from "../../api/client";

type Props = {
  studyId: string;
  siteId: string;
};

const DIMENSIONS = [
  ["ae_collection", "AE收集"],
  ["grade", "分级"],
  ["seriousness", "严重性/SAE"],
  ["relatedness", "相关性"],
  ["expectedness", "预期性"],
  ["aesi", "AESI"],
  ["dlt", "DLT"],
  ["reporting_timeliness", "及时报告"],
  ["protocol_deviation", "方案偏离"]
] as const;

const DEFAULT_AE_DIMENSIONS = DIMENSIONS.slice(0, 8).map(([value]) => value);

const DIMENSION_STATUS: Record<string, string> = {
  candidate: "系统候选",
  unknown: "未知",
  not_applicable: "结构化条件未触发",
  not_checked_by_user: "用户已跳过",
  analysis_required: "需分析"
};

const REVIEW_DECISION: Record<string, string> = {
  reviewed_candidate: "已复核候选",
  needs_clarification: "待澄清",
  not_checked_by_user: "本次不核查"
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "安全分析请求失败";
}

function dimensionStatus(item: SafetyDimensionView): string {
  return DIMENSION_STATUS[item.status] ?? item.status;
}

export function AssessmentPanel({ studyId, siteId }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [subjects, setSubjects] = useState<SubjectView[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [assessments, setAssessments] = useState<
    SafetyAssessmentSummaryView[]
  >([]);
  const [assessment, setAssessment] = useState<SafetyAssessmentView | null>(
    null
  );
  const [eventType, setEventType] = useState("adverse_event");
  const [eventDate, setEventDate] = useState(today);
  const [eventNote, setEventNote] = useState("");
  const [requested, setRequested] = useState<string[]>([
    ...DEFAULT_AE_DIMENSIONS
  ]);
  const [reviewDimensions, setReviewDimensions] = useState<string[]>([]);
  const [reviewDecision, setReviewDecision] =
    useState("reviewed_candidate");
  const [reviewNote, setReviewNote] = useState("");
  const [respondentRole, setRespondentRole] = useState("investigator");
  const [respondentName, setRespondentName] = useState("");
  const [medicalText, setMedicalText] = useState("");
  const [medicalSource, setMedicalSource] = useState("");
  const [issueDimensions, setIssueDimensions] = useState<string[]>([]);
  const [issueRequirement, setIssueRequirement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadSubjects = useCallback(async () => {
    const next = await getSubjects(studyId, siteId);
    setSubjects(next);
    setSubjectId((current) =>
      current && next.some((item) => item.id === current)
        ? current
        : next[0]?.id ?? ""
    );
  }, [siteId, studyId]);

  const loadAssessments = useCallback(
    async (selectedSubjectId: string) => {
      if (!selectedSubjectId) {
        setAssessments([]);
        setAssessment(null);
        return;
      }
      const next = await getSafetyAssessments(
        studyId,
        siteId,
        selectedSubjectId
      );
      setAssessments(next);
      if (assessment && !next.some((item) => item.id === assessment.id)) {
        setAssessment(null);
      }
    },
    [assessment, siteId, studyId]
  );

  useEffect(() => {
    loadSubjects().catch((reason) => setError(errorMessage(reason)));
  }, [loadSubjects]);

  useEffect(() => {
    loadAssessments(subjectId).catch((reason) =>
      setError(errorMessage(reason))
    );
  }, [loadAssessments, subjectId]);

  function toggle(
    value: string,
    current: string[],
    setter: (values: string[]) => void
  ) {
    setter(
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value]
    );
  }

  function applyAssessment(next: SafetyAssessmentView) {
    setAssessment(next);
    setReviewDimensions(next.dimensions.slice(0, 1).map((item) => item.dimension));
    setIssueDimensions(next.dimensions.slice(0, 1).map((item) => item.dimension));
    setReviewNote("");
    setMedicalText("");
    setMedicalSource("");
    setIssueRequirement("");
  }

  async function openAssessment(assessmentId: string) {
    setBusy(true);
    setError(null);
    try {
      applyAssessment(await getSafetyAssessment(assessmentId));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subjectId || requested.length === 0) {
      setError("请选择受试者并至少选择一个安全判断维度。");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const next = await createSafetyAssessment({
        studyId,
        siteId,
        subjectId,
        eventType,
        eventDate,
        requestedDimensions: requested,
        note: eventNote
      });
      applyAssessment(next);
      const summaries = await getSafetyAssessments(
        studyId,
        siteId,
        subjectId
      );
      setAssessments(summaries);
      setMessage(
        next.replayed
          ? "相同输入已复用已有分析记录。"
          : "候选、未知条件、问题和及时提示已按独立维度保存。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assessment || reviewDimensions.length === 0) {
      setError("请选择本次复核涉及的维度。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await recordSafetyCraReview(assessment.id, {
        decision: reviewDecision,
        dimensions: reviewDimensions,
        note: reviewNote
      });
      setAssessment(next);
      setMessage(
        "CRA复核已单独追加；不会把系统候选写成医学确认。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveMedical(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assessment || !medicalText.trim()) {
      setError("请记录研究者或医学人员的实际答复。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await recordMedicalSafetyResponse(assessment.id, {
        respondentRole,
        respondentName,
        responseText: medicalText,
        dimensionResponses: {},
        sourceNote: medicalSource
      });
      setAssessment(next);
      setMessage("医学答复已单独保存，未覆盖CRA复核或系统候选。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function linkIssue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assessment || issueDimensions.length === 0) {
      setError("请选择需要关联M06待办的维度。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const issue = await linkSafetyAssessmentIssue(assessment.id, {
        dimensions: issueDimensions,
        requirement: issueRequirement
      });
      setAssessment(await getSafetyAssessment(assessment.id));
      setMessage(
        `已关联待办 ${issue.issue_number}；Action保持${
          issue.actions[0]?.status ?? "open"
        }，由用户实际处理。`
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="safety-panel" aria-labelledby="safety-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M09 · 有依据的安全分析</p>
          <h2 id="safety-title">AE、SAE、PD及特殊标准分开核查</h2>
          <p>
            程序依据已确认事实和事件时点适用规则计算候选、未知和问题；
            模型只可在允许模板和证据ID内解释，不能确认SAE、PD或关闭Action。
          </p>
        </div>
        <span className="status-chip muted">
          {assessment ? `记录 ${assessment.revision} 版` : "尚未分析"}
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <form className="safety-create-form" onSubmit={(event) => void analyze(event)}>
        <label>
          受试者
          <select
            value={subjectId}
            onChange={(event) => {
              setSubjectId(event.target.value);
              setAssessment(null);
            }}
            required
          >
            <option value="">选择受试者</option>
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.deidentified_label}
              </option>
            ))}
          </select>
        </label>
        <label>
          事件类型
          <select
            value={eventType}
            onChange={(event) => setEventType(event.target.value)}
          >
            <option value="adverse_event">不良事件</option>
            <option value="serious_event_review">严重事件复核</option>
            <option value="laboratory_logic">检验安全线索</option>
            <option value="protocol_deviation">方案偏离候选</option>
            <option value="mixed">混合事项</option>
          </select>
        </label>
        <label>
          事件日期
          <input
            type="date"
            value={eventDate}
            onChange={(event) => setEventDate(event.target.value)}
            required
          />
        </label>
        <label className="safety-wide-field">
          合成备注（可选）
          <input
            value={eventNote}
            onChange={(event) => setEventNote(event.target.value)}
            placeholder="仅记录本次分析范围，不替代事实或医学判断"
          />
        </label>
        <fieldset className="safety-dimension-choice">
          <legend>本次分析维度</legend>
          {DIMENSIONS.map(([value, label]) => (
            <label key={value}>
              <input
                type="checkbox"
                checked={requested.includes(value)}
                onChange={() => toggle(value, requested, setRequested)}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <button className="primary-button compact" disabled={busy}>
          生成有依据的候选与问题
        </button>
      </form>

      {assessments.length > 0 && (
        <div className="safety-history" aria-label="该受试者安全分析历史">
          <span>已有分析</span>
          {assessments.map((item) => (
            <button
              type="button"
              className={assessment?.id === item.id ? "active" : ""}
              key={item.id}
              onClick={() => void openAssessment(item.id)}
            >
              {item.event_date} · {item.event_type} · {item.status}
            </button>
          ))}
        </div>
      )}

      {assessment && (
        <div className="safety-detail">
          <div className="safety-provider-line">
            <span>Provider: {assessment.provider_name}</span>
            <span>状态: {assessment.provider_status}</span>
            <span>模型不能作最终医学结论</span>
          </div>

          {assessment.timely_alerts.map((alert) => (
            <article className="safety-urgent" key={alert.alert_key}>
              <p className="eyebrow">立即核对 · 不等待报告</p>
              <h3>{alert.title}</h3>
              <p>{alert.detail}</p>
              <dl>
                <div>
                  <dt>事件日期</dt>
                  <dd>{alert.event_date}</dd>
                </div>
                <div>
                  <dt>知悉日期</dt>
                  <dd>{alert.awareness_date ?? "未提供"}</dd>
                </div>
                <div>
                  <dt>实际上报日期</dt>
                  <dd>{alert.reported_date ?? "未提供"}</dd>
                </div>
                <div>
                  <dt>时限状态</dt>
                  <dd>{alert.deadline_status}</dd>
                </div>
              </dl>
            </article>
          ))}

          <div className="safety-dimension-grid">
            {assessment.dimensions.map((item) => (
              <article className={`safety-dimension ${item.status}`} key={item.id}>
                <div>
                  <p className="eyebrow">{item.label}</p>
                  <h3>{dimensionStatus(item)}</h3>
                </div>
                {item.candidate_values.length > 0 && (
                  <ul>
                    {item.candidate_values.map((value) => (
                      <li key={value}>{value}</li>
                    ))}
                  </ul>
                )}
                {item.rationale && <p>{item.rationale}</p>}
                {item.uncertainties.length > 0 && (
                  <p className="inline-warning">
                    未知：{item.uncertainties.join("；")}
                  </p>
                )}
                <small>
                  {item.evidence_ids.length} 项依据 ·{" "}
                  {item.rule_version_ids.length} 个规则版本
                </small>
              </article>
            ))}
          </div>

          <section className="safety-questions">
            <div>
              <p className="eyebrow">应核实的具体问题</p>
              <h3>{assessment.questions.length} 项</h3>
            </div>
            <ol>
              {assessment.questions.map((item) => (
                <li key={item.question_key} className={item.priority}>
                  <strong>{item.priority === "timely" ? "及时" : "常规"}</strong>
                  <span>{item.question}</span>
                  <small>{item.reason}</small>
                </li>
              ))}
            </ol>
          </section>

          <section className="safety-evidence">
            <p className="eyebrow">证据与来源</p>
            <div className="safety-evidence-list">
              {assessment.evidence_refs.map((reference, index) => (
                <article key={`${String(reference.source_id)}-${index}`}>
                  <strong>{String(reference.source_type)}</strong>
                  <p>
                    {String(
                      reference.quote ??
                        reference.locator ??
                        reference.source_id
                    )}
                  </p>
                  <small>
                    {String(reference.source_id)}
                    {reference.version
                      ? ` · ${String(reference.version)}`
                      : ""}
                  </small>
                </article>
              ))}
            </div>
            {assessment.provider_output.accepted !== true && (
              <p className="inline-warning">
                模型解释未采用；程序计算候选、未知和具体问题仍保留。
              </p>
            )}
          </section>

          <div className="safety-review-layout">
            <form className="safety-review-card" onSubmit={(event) => void saveReview(event)}>
              <p className="eyebrow">CRA记录</p>
              <h3>复核范围与决定</h3>
              <label>
                决定
                <select
                  value={reviewDecision}
                  onChange={(event) => setReviewDecision(event.target.value)}
                >
                  {Object.entries(REVIEW_DECISION).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="safety-check-list">
                {assessment.dimensions.map((item) => (
                  <label key={item.id}>
                    <input
                      type="checkbox"
                      checked={reviewDimensions.includes(item.dimension)}
                      onChange={() =>
                        toggle(
                          item.dimension,
                          reviewDimensions,
                          setReviewDimensions
                        )
                      }
                    />
                    {item.label}
                  </label>
                ))}
              </div>
              <textarea
                value={reviewNote}
                onChange={(event) => setReviewNote(event.target.value)}
                placeholder="CRA复核说明；不填写研究者医学结论"
              />
              <button className="secondary-button" disabled={busy}>
                追加CRA复核记录
              </button>
            </form>

            <form className="safety-review-card" onSubmit={(event) => void saveMedical(event)}>
              <p className="eyebrow">研究者/医学答复</p>
              <h3>独立保存实际答复</h3>
              <label>
                答复角色
                <select
                  value={respondentRole}
                  onChange={(event) => setRespondentRole(event.target.value)}
                >
                  <option value="investigator">研究者</option>
                  <option value="medical_monitor">医学监查员</option>
                  <option value="medical_reviewer">医学审阅人</option>
                  <option value="other">其他</option>
                </select>
              </label>
              <input
                value={respondentName}
                onChange={(event) => setRespondentName(event.target.value)}
                placeholder="答复人标识（可选）"
              />
              <textarea
                value={medicalText}
                onChange={(event) => setMedicalText(event.target.value)}
                placeholder="记录实际答复；不得由系统代填"
                required
              />
              <input
                value={medicalSource}
                onChange={(event) => setMedicalSource(event.target.value)}
                placeholder="答复来源或沟通记录（可选）"
              />
              <button className="secondary-button" disabled={busy}>
                保存医学答复
              </button>
            </form>
          </div>

          <form className="safety-issue-card" onSubmit={(event) => void linkIssue(event)}>
            <div>
              <p className="eyebrow">M06 后续事项</p>
              <h3>{assessment.issue_id ? "已关联待办" : "选择需要跟进的范围"}</h3>
              <p>仅创建医学澄清Action，不自动完成、上报PD或关闭问题。</p>
            </div>
            <div className="safety-check-list">
              {assessment.dimensions.map((item) => (
                <label key={item.id}>
                  <input
                    type="checkbox"
                    checked={issueDimensions.includes(item.dimension)}
                    onChange={() =>
                      toggle(item.dimension, issueDimensions, setIssueDimensions)
                    }
                  />
                  {item.label}
                </label>
              ))}
            </div>
            <input
              value={issueRequirement}
              onChange={(event) => setIssueRequirement(event.target.value)}
              placeholder="具体待核实要求；留空使用安全默认文本"
            />
            <button className="secondary-button" disabled={busy}>
              {assessment.issue_id ? "查看已关联待办" : "关联M06待办"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
