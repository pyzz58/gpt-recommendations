import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  type CheckDecisionView,
  type ClinicalFactView,
  type CoverageBreakpointView,
  type EvaluateVisitRequirementsResponse,
  type SubjectView,
  confirmSubjectFact,
  createCheckDecision,
  evaluateSubjectVisitRequirements,
  getCheckDecisions,
  getSubjectCoverage,
  getSubjectTimeline,
  getSubjects,
  importSubjectFacts,
  importSubjectFile,
  resumeCheckDecision,
  saveSubjectCoverage
} from "../../api/client";

type Props = {
  studyId: string;
  siteId: string;
};

const STATUS_LABEL: Record<string, string> = {
  in_window: "窗口内",
  out_of_window: "窗口外",
  unknown_anchor: "缺锚点",
  unknown_actual: "缺实际日期",
  not_checked_by_user: "用户选择不核查",
  needs_review: "事实变化，待复核",
  active: "生效中",
  resumed: "已恢复",
  complete: "完成",
  in_progress: "进行中",
  not_checked: "未核查"
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "患者上下文操作失败";
}

function sourceLabel(fact: ClinicalFactView): string {
  switch (fact.source_kind) {
    case "original_record":
      return "授权原始记录";
    case "cra_confirmation":
      return "CRA确认";
    case "other_response":
      return "他人答复";
    case "model_suggestion":
      return "模型建议";
    default:
      return fact.source_kind;
  }
}

export function SubjectTimeline({ studyId, siteId }: Props) {
  const [subjects, setSubjects] = useState<SubjectView[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(
    null
  );
  const [timeline, setTimeline] = useState<ClinicalFactView[]>([]);
  const [coverage, setCoverage] = useState<CoverageBreakpointView[]>([]);
  const [decisions, setDecisions] = useState<CheckDecisionView[]>([]);
  const [visitResult, setVisitResult] =
    useState<EvaluateVisitRequirementsResponse | null>(null);
  const [eventDate, setEventDate] = useState("2021-01-02");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedSubject = useMemo(
    () => subjects.find((subject) => subject.id === selectedSubjectId) ?? null,
    [subjects, selectedSubjectId]
  );
  const currentFacts = useMemo(
    () => timeline.filter((fact) => fact.is_current),
    [timeline]
  );
  const activeDecisions = decisions.filter(
    (decision) => decision.state === "active"
  );

  const loadSubjects = useCallback(async () => {
    const next = await getSubjects(studyId, siteId);
    setSubjects(next);
    setSelectedSubjectId((current) =>
      current && next.some((subject) => subject.id === current)
        ? current
        : next[0]?.id ?? null
    );
    return next;
  }, [studyId, siteId]);

  const loadSubjectContext = useCallback(
    async (subjectId: string) => {
      const [nextTimeline, nextCoverage, nextDecisions] = await Promise.all([
        getSubjectTimeline(subjectId),
        getSubjectCoverage(subjectId),
        getCheckDecisions(subjectId)
      ]);
      setTimeline(nextTimeline);
      setCoverage(nextCoverage);
      setDecisions(nextDecisions);
      setVisitResult(null);
    },
    []
  );

  useEffect(() => {
    setBusy(true);
    loadSubjects()
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [loadSubjects]);

  useEffect(() => {
    if (!selectedSubjectId) {
      setTimeline([]);
      setCoverage([]);
      setDecisions([]);
      setVisitResult(null);
      return;
    }
    setBusy(true);
    loadSubjectContext(selectedSubjectId)
      .catch((reason) => setError(errorMessage(reason)))
      .finally(() => setBusy(false));
  }, [loadSubjectContext, selectedSubjectId]);

  async function importFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("file");
    if (!(file instanceof File) || !file.name) {
      setError("请选择 JSON、CSV 或 XLSX 合成上下文文件。");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await importSubjectFile({
        studyId,
        siteId,
        namespace: String(form.get("namespace") ?? "synthetic-edc"),
        sourceKind: String(form.get("source_kind") ?? "original_record"),
        file
      });
      setMessage(
        result.replayed
          ? "相同上下文请求已识别，沿用原有记录。"
          : `已导入 ${result.inserted_facts} 条事实，涉及 ${result.subject_ids.length} 名合成患者。`
      );
      const next = await loadSubjects();
      setSelectedSubjectId(next[0]?.id ?? null);
      formElement.reset();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function importManualFact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const subjectExternalId =
      String(form.get("subject_external_id") ?? "").trim() ||
      selectedSubject?.identifiers[0]?.external_id ||
      "";
    const factKey = String(form.get("fact_key") ?? "").trim();
    const valueRaw = String(form.get("value_raw") ?? "").trim();
    if (!subjectExternalId || !factKey || !valueRaw) {
      setError("患者标识、事实键和值均为必填。");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await importSubjectFacts({
        studyId,
        siteId,
        namespace: String(form.get("namespace") ?? "manual"),
        sourceKind: String(form.get("source_kind") ?? "original_record"),
        rows: [
          {
            subject_external_id: subjectExternalId,
            fact_key: factKey,
            value_raw: valueRaw,
            value_type:
              String(form.get("value_type") ?? "") || undefined,
            observed_on: String(form.get("observed_on") ?? "") || null,
            precision: "date",
            unit: String(form.get("unit") ?? "") || null,
            repeat_instance: "_",
            visit_key: String(form.get("visit_key") ?? "") || null,
            source_ref: {
              source_type: "record",
              source_id: `synthetic-manual:${crypto.randomUUID()}`,
              locator: "用户手动录入的合成事实"
            }
          }
        ]
      });
      setMessage(
        result.inserted_facts
          ? "合成事实已保存为新的来源记录。"
          : "相同事实已存在，没有重复填写。"
      );
      const next = await loadSubjects();
      const selected = next.find(
        (subject) =>
          subject.id === selectedSubjectId ||
          subject.identifiers.some(
            (identifier) => identifier.external_id === subjectExternalId
          )
      );
      if (selected) {
        setSelectedSubjectId(selected.id);
      }
      formElement.reset();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function confirmFact(fact: ClinicalFactView) {
    setBusy(true);
    setError(null);
    try {
      await confirmSubjectFact(fact.id, fact.revision);
      if (selectedSubjectId) {
        await loadSubjectContext(selectedSubjectId);
      }
      setMessage("该事实已保存为独立 CRA 确认，原来源仍保留。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function evaluate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSubjectId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setVisitResult(
        await evaluateSubjectVisitRequirements(
          selectedSubjectId,
          eventDate
        )
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function skipRequirement(requirement: {
    anchor_fact_key: string;
    affected_paths: string[];
    can_continue: string[];
    rule_version_id: string;
  }) {
    if (!selectedSubjectId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createCheckDecision(selectedSubjectId, {
        category: "visit_window",
        checkType: "visit_window",
        reason: "declined_missing_data",
        scopeStart: eventDate,
        scopeEnd: eventDate,
        missingKeys: [requirement.anchor_fact_key],
        affectedPaths: requirement.affected_paths,
        canContinue: requirement.can_continue,
        ruleVersionId: requirement.rule_version_id
      });
      await loadSubjectContext(selectedSubjectId);
      setVisitResult(
        await evaluateSubjectVisitRequirements(selectedSubjectId, eventDate)
      );
      setMessage(
        "已保存本患者、本次事项和当日的局部不核查选择；未扩大至其他患者。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function resume(decision: CheckDecisionView) {
    if (!selectedSubjectId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resumeCheckDecision(
        selectedSubjectId,
        decision.id,
        decision.revision
      );
      await loadSubjectContext(selectedSubjectId);
      setVisitResult(
        await evaluateSubjectVisitRequirements(selectedSubjectId, eventDate)
      );
      setMessage("已恢复该局部核查路径，无需重新录入已有事实。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveCoverage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSubjectId) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const category = String(form.get("category") ?? "laboratory");
    const current = coverage.find((item) => item.category === category);
    setBusy(true);
    setError(null);
    try {
      await saveSubjectCoverage(selectedSubjectId, {
        expectedRevision: current?.revision ?? 0,
        category,
        scopeKey: String(form.get("scope_key") ?? "screening"),
        status: String(form.get("status") ?? "in_progress"),
        checkedThrough: String(form.get("checked_through") ?? ""),
        normalScopeNote: String(form.get("normal_scope_note") ?? ""),
        unverifiedScope: String(form.get("unverified_scope") ?? "")
          .split(/[,，;；]/)
          .map((item) => item.trim())
          .filter(Boolean)
      });
      await loadSubjectContext(selectedSubjectId);
      setMessage("该资料类别断点已单独保存，其他类别不受影响。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="subject-workspace" aria-labelledby="subjects-title">
      <div className="document-heading">
        <div>
          <p className="eyebrow">M04 · 患者事实与分类断点</p>
          <h2 id="subjects-title">患者时间线与访视窗口</h2>
          <p>
            事实保留来源和日期精度；不同患者、不同资料类别分别保存核查位置。
          </p>
        </div>
        <span className="status-chip muted">{subjects.length} 名合成患者</span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <div className="subject-input-grid">
        <form className="subject-import-form" onSubmit={(event) => void importFile(event)}>
          <p className="eyebrow">结构化上下文</p>
          <h3>导入授权 JSON / CSV / XLSX</h3>
          <label>
            身份命名空间
            <input name="namespace" defaultValue="synthetic-edc" required />
          </label>
          <label>
            来源类别
            <select name="source_kind" defaultValue="original_record">
              <option value="original_record">授权原始记录</option>
              <option value="other_response">他人答复</option>
              <option value="model_suggestion">模型建议（不用于确定计算）</option>
            </select>
          </label>
          <label>
            合成上下文文件
            <input type="file" name="file" accept=".json,.csv,.xlsx" required />
          </label>
          <button className="secondary-button" type="submit" disabled={busy}>
            导入事实
          </button>
        </form>

        <form className="subject-import-form" onSubmit={(event) => void importManualFact(event)}>
          <p className="eyebrow">少量例外补录</p>
          <h3>手动补充一条事实</h3>
          <label>
            患者外部标识
            <input
              name="subject_external_id"
              defaultValue={selectedSubject?.identifiers[0]?.external_id ?? ""}
              placeholder="SYN-001"
            />
          </label>
          <label>
            身份命名空间
            <input name="namespace" defaultValue="manual" required />
          </label>
          <label>
            事实键
            <input name="fact_key" placeholder="infusion_date" required />
          </label>
          <label>
            原值
            <input name="value_raw" required />
          </label>
          <label>
            值类型
            <select name="value_type" defaultValue="">
              <option value="">自动识别</option>
              <option value="date">日期</option>
              <option value="datetime">日期时间</option>
              <option value="decimal">数值</option>
              <option value="string">文字</option>
              <option value="boolean">布尔</option>
              <option value="json">JSON</option>
            </select>
          </label>
          <label>
            观察到日期
            <input type="date" name="observed_on" required />
          </label>
          <label>
            单位
            <input name="unit" />
          </label>
          <label>
            访视标识
            <input name="visit_key" placeholder="V1" />
          </label>
          <label>
            来源
            <select name="source_kind" defaultValue="original_record">
              <option value="original_record">授权记录</option>
              <option value="cra_confirmation">CRA确认</option>
              <option value="other_response">他人答复</option>
            </select>
          </label>
          <button className="secondary-button" type="submit" disabled={busy}>
            保存一条事实
          </button>
        </form>
      </div>

      <div className="subject-layout">
        <aside className="subject-index">
          <h3>患者</h3>
          {subjects.length === 0 ? (
            <p>尚无患者。导入结构化上下文后可复用身份。</p>
          ) : (
            subjects.map((subject) => (
              <button
                type="button"
                key={subject.id}
                className={subject.id === selectedSubjectId ? "active" : ""}
                onClick={() => setSelectedSubjectId(subject.id)}
              >
                {subject.deidentified_label}
                <small>
                  阶段 {subject.current_stage} ·{" "}
                  {subject.identifiers[0]?.external_id ?? "无标识"}
                </small>
              </button>
            ))
          )}
        </aside>

        <div className="subject-detail">
          {selectedSubject ? (
            <>
              <div className="subject-identity">
                <div>
                  <strong>{selectedSubject.deidentified_label}</strong>
                  <span>当前阶段：{selectedSubject.current_stage}</span>
                </div>
                <div className="facts-pills">
                  {selectedSubject.identifiers.map((identifier) => (
                    <span key={identifier.id}>
                      {identifier.identity_namespace}:{identifier.external_id}
                    </span>
                  ))}
                </div>
              </div>

              <form className="event-evaluate-form" onSubmit={(event) => void evaluate(event)}>
                <label>
                  当前临床事件日
                  <input
                    type="date"
                    value={eventDate}
                    onChange={(event) => setEventDate(event.target.value)}
                    required
                  />
                </label>
                <button className="primary-button compact" type="submit" disabled={busy}>
                  计算访视要求
                </button>
              </form>

              <div className="timeline-list" aria-label="患者事实时间线">
                <h3>事实与来源</h3>
                {timeline.length === 0 && <p>尚无已导入事实。</p>}
                {timeline.map((fact) => (
                  <article
                    key={fact.id}
                    className={fact.is_current ? "current" : "history"}
                  >
                    <div>
                      <strong>{fact.fact_key}</strong>
                      <span>{fact.value_raw}{fact.unit ? ` ${fact.unit}` : ""}</span>
                    </div>
                    <small>
                      r{fact.revision} · {sourceLabel(fact)} ·{" "}
                      {fact.observed_on ?? fact.observed_at} · {fact.precision}
                      {fact.is_current ? " · 当前" : " · 历史"}
                    </small>
                    {!["cra_confirmed"].includes(fact.verification_status) &&
                      ["other_response", "model_suggestion"].includes(
                        fact.source_kind
                      ) && (
                        <button
                          className="text-button"
                          type="button"
                          onClick={() => void confirmFact(fact)}
                          disabled={busy}
                        >
                          CRA确认此事实
                        </button>
                      )}
                  </article>
                ))}
              </div>

              {visitResult && (
                <section className="visit-results" aria-live="polite">
                  <div className="applicable-heading">
                    <div>
                      <p className="eyebrow">规则驱动 · 日期精度保留</p>
                      <h3>访视要求与未知</h3>
                    </div>
                    <span className={`status-chip ${visitResult.envelope.status}`}>
                      {visitResult.envelope.status}
                    </span>
                  </div>
                  <p>
                    未知 {(visitResult.envelope.unknowns ?? []).length} 项；用户局部跳过{" "}
                    {(visitResult.envelope.not_checked ?? []).length} 项。
                  </p>
                  {visitResult.requirements.length === 0 ? (
                    <p className="empty-documents">
                      当前没有适用的已确认日期窗口规则。
                    </p>
                  ) : (
                    visitResult.requirements.map((item) => {
                      const requirement = item.requirement;
                      return (
                        <article
                          className="visit-requirement"
                          key={requirement.id}
                        >
                          <div>
                            <strong>{requirement.visit_key}</strong>
                            <span className={`evaluation-state ${requirement.status}`}>
                              {STATUS_LABEL[requirement.status] ?? requirement.status}
                            </span>
                          </div>
                          <p>{item.rule_summary}</p>
                          <dl>
                            <div>
                              <dt>锚点</dt>
                              <dd>
                                {requirement.anchor_fact_key} ={" "}
                                {requirement.anchor_date ?? "未知"}
                              </dd>
                            </div>
                            <div>
                              <dt>实际日期</dt>
                              <dd>{requirement.actual_date ?? "未知"}</dd>
                            </div>
                            <div>
                              <dt>允许窗口</dt>
                              <dd>
                                {requirement.window_start ?? "未知"} 至{" "}
                                {requirement.window_end ?? "未知"}
                              </dd>
                            </div>
                            <div>
                              <dt>所需事实</dt>
                              <dd>{requirement.required_fact_keys.join("、")}</dd>
                            </div>
                            <div>
                              <dt>允许来源</dt>
                              <dd>{requirement.allowed_sources.join("、")}</dd>
                            </div>
                            <div>
                              <dt>可继续事项</dt>
                              <dd>
                                {requirement.can_continue.join("、") || "无"}
                              </dd>
                            </div>
                          </dl>
                          {requirement.status === "unknown_anchor" && (
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => void skipRequirement(requirement)}
                              disabled={busy}
                            >
                              本患者本事项不补充，不核查该窗口
                            </button>
                          )}
                        </article>
                      );
                    })
                  )}
                </section>
              )}

              <section className="decision-list">
                <h3>局部不核查选择</h3>
                {decisions.length === 0 ? (
                  <p>尚无局部跳过记录。</p>
                ) : (
                  decisions.map((decision) => (
                    <article key={decision.id}>
                      <strong>
                        {STATUS_LABEL[decision.state] ?? decision.state}
                      </strong>
                      <p>
                        {decision.reason} · 缺 {decision.missing_keys.join("、")}
                      </p>
                      <small>
                        {decision.scope_start ?? "开放"} 至{" "}
                        {decision.scope_end ?? "开放"}
                        {decision.recovery_available
                          ? " · 新事实可用，可恢复"
                          : ""}
                      </small>
                      {decision.state === "active" && (
                        <button
                          className="text-button"
                          type="button"
                          onClick={() => void resume(decision)}
                          disabled={busy}
                        >
                          恢复核查
                        </button>
                      )}
                    </article>
                  ))
                )}
              </section>
            </>
          ) : (
            <p className="empty-documents">选择或导入患者后开始。</p>
          )}
        </div>
      </div>

      {selectedSubject && (
        <section className="coverage-section">
          <div className="applicable-heading">
            <div>
              <p className="eyebrow">分类断点</p>
              <h3>逐类别接续核查</h3>
            </div>
            <span className="status-chip muted">{coverage.length} 类</span>
          </div>
          <div className="coverage-grid">
            {coverage.map((item) => (
              <article key={item.id}>
                <strong>{item.category}</strong>
                <span>{STATUS_LABEL[item.status] ?? item.status}</span>
                <p>已核查至 {item.checked_through ?? "未记录"}</p>
                <small>
                  {item.normal_scope_note ?? "无正常范围简记"}
                  {item.unverified_scope.length
                    ? ` · 未核实：${item.unverified_scope.join("、")}`
                    : ""}
                </small>
              </article>
            ))}
          </div>
          <form className="coverage-form" onSubmit={(event) => void saveCoverage(event)}>
            <label>
              类别
              <select name="category" defaultValue="laboratory">
                <option value="laboratory">检验</option>
                <option value="documents">文件/目录</option>
                <option value="consent">知情同意</option>
                <option value="medication">用药</option>
                <option value="safety">安全</option>
                <option value="visit_window">访视窗口</option>
              </select>
            </label>
            <label>
              范围
              <input name="scope_key" defaultValue="screening" required />
            </label>
            <label>
              核查至
              <input name="checked_through" placeholder="V3" />
            </label>
            <label>
              状态
              <select name="status" defaultValue="in_progress">
                <option value="in_progress">进行中</option>
                <option value="complete">该类已完成</option>
                <option value="not_checked">未核查</option>
              </select>
            </label>
            <label>
              正常范围简记
              <input name="normal_scope_note" />
            </label>
            <label>
              未核实范围（逗号分隔）
              <input name="unverified_scope" />
            </label>
            <button className="secondary-button" type="submit" disabled={busy}>
              保存该类别断点
            </button>
          </form>
        </section>
      )}
    </section>
  );
}
