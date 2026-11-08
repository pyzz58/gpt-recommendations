import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type MonitoringJourneyView,
  advanceMonitoringStage,
  createMonitoringVisit,
  getMonitoringJourney,
  getMonitoringVisits
} from "../api/client";
import { DocumentWorkspace } from "../features/documents/DocumentWorkspace";
import { CarryoverReview } from "../features/issues/CarryoverReview";
import { StageChecklist } from "../features/monitoring/StageChecklist";
import { ReportPreview } from "../features/reports/ReportPreview";
import { RuleWorkspace } from "../features/rules/RuleWorkspace";
import { DirectoryReview } from "../features/site-files/DirectoryReview";
import { HandoverPage } from "./HandoverPage";
import { SubjectReviewPage } from "./SubjectReviewPage";

type Props = {
  studyId: string;
  siteId: string;
};

function visitKey(studyId: string, siteId: string): string {
  return `cra.w06.visit.${studyId}.${siteId}`;
}

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "监查流程操作失败";
}

export function MonitoringVisitPage({ studyId, siteId }: Props) {
  const [visits, setVisits] = useState<
    Awaited<ReturnType<typeof getMonitoringVisits>>
  >([]);
  const [journey, setJourney] = useState<MonitoringJourneyView | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoaded(false);
    setBusy(true);
    setError(null);
    try {
      const rows = await getMonitoringVisits(studyId, siteId);
      setVisits(rows);
      const stored = window.localStorage.getItem(visitKey(studyId, siteId));
      const visit =
        rows.find((item) => item.id === stored) ?? rows[0] ?? null;
      if (!visit) {
        setJourney(null);
        return;
      }
      window.localStorage.setItem(visitKey(studyId, siteId), visit.id);
      window.dispatchEvent(new Event("cra-monitoring-visit-updated"));
      setJourney(await getMonitoringJourney(visit.id));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoaded(true);
      setBusy(false);
    }
  }, [siteId, studyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function startVisit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const workbench = await createMonitoringVisit({
        studyId,
        siteId,
        title: String(form.get("title") ?? "本次中心监查"),
        scopeNote: String(form.get("scope_note") ?? ""),
        stage: "previsit"
      });
      window.localStorage.setItem(
        visitKey(studyId, siteId),
        workbench.visit.id
      );
      window.dispatchEvent(new Event("cra-monitoring-visit-updated"));
      setJourney(await getMonitoringJourney(workbench.visit.id));
      setCreating(false);
      await load();
      setMessage("本次监查已建立，先完成访前选择和遗留复核。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function openVisit(visitId: string) {
    window.localStorage.setItem(visitKey(studyId, siteId), visitId);
    window.dispatchEvent(new Event("cra-monitoring-visit-updated"));
    setBusy(true);
    setError(null);
    try {
      setJourney(await getMonitoringJourney(visitId));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function goStage(stage: string) {
    if (!journey) return;
    setBusy(true);
    setError(null);
    try {
      const fresh = await getMonitoringJourney(journey.visit.id);
      const next = await advanceMonitoringStage(fresh.visit, stage);
      setJourney(next);
      setMessage(
        "已切换监查阶段；未完成遗留、unknown 和未核查范围仍保留。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  if (!journey && !loaded) {
    return (
      <section className="workspace-module monitoring-journey">
        <div className="module-heading">
          <p className="eyebrow">W12 · 连续监查</p>
          <h2>正在从服务端恢复本次监查</h2>
          <p>只恢复当前已授权项目和中心，不使用浏览器自报身份。</p>
        </div>
      </section>
    );
  }

  if (!journey) {
    return (
      <section className="workspace-module monitoring-journey" id="monitoring-journey">
        <div className="module-heading">
          <div>
            <p className="eyebrow">W12 · 一次完整监查</p>
            <h2>从访前遗留开始，逐患者核查，最后生成报告</h2>
            <p>
              当前中心尚无本次监查。阶段推进只做导航，不锁定紧急事项或其他必要工作。
            </p>
          </div>
        </div>
        {message && <div className="notice" role="status">{message}</div>}
        {error && <div className="notice notice-error" role="alert">{error}</div>}
        <form
          className="subject-import-form"
          data-testid="start-monitoring-form"
          onSubmit={(event) => void startVisit(event)}
        >
          <label>
            监查标题
            <input name="title" defaultValue="本次中心监查" required />
          </label>
          <label>
            本次范围简记
            <textarea
              name="scope_note"
              rows={3}
              placeholder="例：上次遗留、本次受试者与检验范围"
            />
          </label>
          <button
            className="primary-button compact"
            type="submit"
            data-testid="start-monitoring-visit"
            disabled={busy}
          >
            开始本次监查
          </button>
        </form>
      </section>
    );
  }

  const activeStage = journey.visit.stage;
  return (
    <section className="workspace-module monitoring-journey" id="monitoring-journey">
      <div className="module-heading">
        <div>
          <p className="eyebrow">W12 · 连续监查</p>
          <h2>{journey.visit.title}</h2>
          <p>
            默认顺序为访前、遗留复核、逐患者、报告/交接；紧急事项及各模块详情仍可直接使用。
          </p>
        </div>
        <span className="status-chip">
          {journey.remaining_issue_numbers.length} 项未完
        </span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}
      {journey.urgent_action_count > 0 && (
        <div className="notice notice-error" role="alert">
          <strong>需及时核实 {journey.urgent_action_count} 项</strong>
          <span>紧急安全/上报事项可直接处理，不等待其他阶段或报告。</span>
        </div>
      )}

      <div className="journey-toolbar">
        <label>
          本次监查
          <select
            value={journey.visit.id}
            onChange={(event) => void openVisit(event.target.value)}
          >
            {visits.map((visit) => (
              <option key={visit.id} value={visit.id}>
                {visit.title} · {visit.stage} · {visit.status}
              </option>
            ))}
          </select>
        </label>
        <button className="text-button" type="button" onClick={() => void load()} disabled={busy}>
          从服务端刷新
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={() => setCreating(true)}
          disabled={busy}
        >
          开始下一次监查
        </button>
      </div>

      {creating && (
        <form className="subject-import-form" onSubmit={(event) => void startVisit(event)}>
          <p className="eyebrow">下一次监查</p>
          <label>
            监查标题
            <input name="title" defaultValue="下一次中心监查" required />
          </label>
          <label>
            本次范围简记
            <textarea name="scope_note" rows={3} />
          </label>
          <button className="primary-button compact" type="submit" disabled={busy}>
            建立下一次监查
          </button>
        </form>
      )}

      <nav className="journey-stage-grid" aria-label="监查阶段">
        {journey.stages.map((stage) => (
          <button
            key={stage.key}
            type="button"
            className={stage.key === activeStage ? "active" : ""}
            onClick={() => void goStage(stage.key)}
            disabled={busy}
            aria-current={stage.key === activeStage ? "step" : undefined}
            data-testid={`stage-${stage.key}`}
          >
            <strong>{stage.label}</strong>
            <span>{stage.summary}</span>
            <small>{stage.primary_action}</small>
          </button>
        ))}
      </nav>

      <section className="journey-metrics" aria-label="本次监查进度">
        <span><strong>{journey.subject_count}</strong> 患者</span>
        <span><strong>{journey.coverage_count}</strong> 覆盖记录</span>
        <span><strong>{journey.not_checked_count}</strong> 未核查</span>
        <span><strong>{journey.laboratory_report_count}</strong> 检验报告</span>
        <span><strong>{journey.edc_snapshot_count}</strong> EDC快照</span>
        <span><strong>{journey.report_snapshot_count}</strong> 报告快照</span>
      </section>

      {activeStage === "previsit" && (
        <>
          <CarryoverReview studyId={studyId} siteId={siteId} />
          <ReportPreview studyId={studyId} siteId={siteId} />
          <details className="technical-details">
            <summary>项目资料与规则底稿</summary>
            <DocumentWorkspace studyId={studyId} siteId={siteId} />
            <RuleWorkspace studyId={studyId} siteId={siteId} />
          </details>
        </>
      )}
      {activeStage === "carryover_review" && (
        <>
          <CarryoverReview studyId={studyId} siteId={siteId} />
          <DirectoryReview studyId={studyId} siteId={siteId} />
        </>
      )}
      {activeStage === "subject_review" && (
        <SubjectReviewPage studyId={studyId} siteId={siteId} />
      )}
      {activeStage === "closeout" && (
        <HandoverPage
          studyId={studyId}
          siteId={siteId}
          visitId={journey.visit.id}
        />
      )}
      {activeStage === "handover" && (
        <HandoverPage
          studyId={studyId}
          siteId={siteId}
          visitId={journey.visit.id}
        />
      )}

      <section className="source-reference journey-limitations">
        <p className="eyebrow">继续规则</p>
        {journey.limitations.map((item) => <p key={item}>{item}</p>)}
      </section>
    </section>
  );
}
