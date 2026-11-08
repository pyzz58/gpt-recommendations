import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  type CapabilityResponse,
  type ScopeResponse,
  createSite,
  createStudy,
  updateSite,
  updateStudy
} from "../../api/client";
import { DocumentWorkspace } from "../documents/DocumentWorkspace";
import { CarryoverReview } from "../issues/CarryoverReview";
import { StageChecklist } from "../monitoring/StageChecklist";
import { TemplateReviewConfig } from "../monitoring/TemplateReviewConfig";
import { ReportPreview } from "../reports/ReportPreview";
import { RuleWorkspace } from "../rules/RuleWorkspace";
import { DirectoryReview } from "../site-files/DirectoryReview";
import { MonitoringVisitPage } from "../../pages/MonitoringVisitPage";
import {
  type WorkspaceSelection,
  readStoredSelection,
  resolveStoredSelection,
  storeSelection
} from "./selection";

type Props = {
  scopes: ScopeResponse;
  capabilities: CapabilityResponse;
  onReload: () => Promise<void>;
  onLogout: () => Promise<void>;
};

type WorkspaceModule =
  | "documents"
  | "startup"
  | "previsit"
  | "monitoring"
  | "reports"
  | "closeout";

const MODULES: { key: WorkspaceModule; label: string; detail: string }[] = [
  {
    key: "documents",
    label: "资料与模板",
    detail: "报告模板、方案和规则底稿"
  },
  {
    key: "startup",
    label: "中心启动",
    detail: "目录、阶段清单和来源核查"
  },
  {
    key: "previsit",
    label: "访视前",
    detail: "遗留选择、访前信和范围准备"
  },
  {
    key: "monitoring",
    label: "本次监查",
    detail: "按报告章节和问句逐项核查"
  },
  {
    key: "reports",
    label: "问题与报告",
    detail: "同源记录、报告草稿和签发"
  },
  {
    key: "closeout",
    label: "关闭与交接",
    detail: "阶段清单、遗留和下次接续"
  }
];

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "工作台操作失败";
}

export function WorkspaceSelector({
  scopes,
  capabilities,
  onReload,
  onLogout
}: Props) {
  const [selection, setSelection] = useState<WorkspaceSelection | null>(() =>
    resolveStoredSelection(scopes.studies, readStoredSelection())
  );
  const [module, setModule] = useState<WorkspaceModule>("previsit");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const resolved = resolveStoredSelection(
      scopes.studies,
      readStoredSelection()
    );
    setSelection(resolved);
    if (resolved) {
      storeSelection(resolved);
    }
  }, [scopes]);

  const selectedStudy = useMemo(
    () =>
      scopes.studies.find((study) => study.id === selection?.studyId) ?? null,
    [scopes.studies, selection?.studyId]
  );
  const selectedSite = useMemo(
    () =>
      selectedStudy?.sites.find((site) => site.id === selection?.siteId) ??
      null,
    [selectedStudy, selection?.siteId]
  );
  const platformAdmin = scopes.platform_roles.includes("platform_admin");
  const canCreateSite =
    platformAdmin || Boolean(selectedStudy?.roles.includes("study_admin"));

  function selectStudy(studyId: string) {
    const study = scopes.studies.find((candidate) => candidate.id === studyId);
    if (!study) {
      setSelection(null);
      return;
    }
    const next = {
      studyId: study.id,
      siteId: study.sites[0]?.id ?? null
    };
    setSelection(next);
    storeSelection(next);
  }

  function selectSite(siteId: string) {
    if (!selectedStudy) {
      return;
    }
    const next = { studyId: selectedStudy.id, siteId };
    setSelection(next);
    storeSelection(next);
  }

  async function saveStudy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const created = await createStudy({
        code: String(form.get("code") ?? "").trim(),
        title: String(form.get("title") ?? "").trim(),
        idempotencyKey: crypto.randomUUID()
      });
      const next = { studyId: created.id, siteId: null };
      setSelection(next);
      storeSelection(next);
      setModule("startup");
      await onReload();
      setMessage("项目已保存。下一步建立至少一个中心。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveStudyTitle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStudy) {
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await updateStudy(
        { id: selectedStudy.id, revision: selectedStudy.revision },
        String(form.get("title") ?? "").trim()
      );
      await onReload();
      setMessage("项目名称已保存。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStudy) {
      setError("请先建立或选择项目。");
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const created = await createSite(selectedStudy.id, {
        code: String(form.get("code") ?? "").trim(),
        name: String(form.get("name") ?? "").trim(),
        idempotencyKey: crypto.randomUUID()
      });
      const next = { studyId: selectedStudy.id, siteId: created.id };
      setSelection(next);
      storeSelection(next);
      setModule("startup");
      await onReload();
      setMessage("中心已保存并切换为当前范围。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveSiteName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedStudy || !selectedSite) {
      return;
    }
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await updateSite(
        selectedStudy.id,
        { id: selectedSite.id, revision: selectedSite.revision },
        String(form.get("name") ?? "").trim()
      );
      await onReload();
      setMessage("中心名称已保存。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function renderModule() {
    if (!selectedStudy) {
      return <EmptyWorkspace />;
    }
    if (!selectedSite) {
      return <NoSiteWorkspace studyTitle={selectedStudy.title} />;
    }
    switch (module) {
      case "documents":
        return (
          <div className="module-stack">
            <DocumentWorkspace
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
            <TemplateReviewConfig
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
            <RuleWorkspace
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
          </div>
        );
      case "startup":
        return (
          <div className="module-stack">
            <DirectoryReview
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
            <StageChecklist
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
          </div>
        );
      case "previsit":
        return (
          <div className="module-stack">
            <CarryoverReview
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
            <ReportPreview
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
          </div>
        );
      case "monitoring":
        return (
          <MonitoringVisitPage
            studyId={selectedStudy.id}
            siteId={selectedSite.id}
          />
        );
      case "reports":
        return (
          <ReportPreview
            studyId={selectedStudy.id}
            siteId={selectedSite.id}
          />
        );
      case "closeout":
        return (
          <div className="module-stack">
            <StageChecklist
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
            <CarryoverReview
              studyId={selectedStudy.id}
              siteId={selectedSite.id}
            />
          </div>
        );
    }
  }

  return (
    <div className="workspace-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="CRA 工作台首页">
          <span className="brand-mark">CRA</span>
          <span>
            <strong>监查工作台</strong>
            <small>合成演示环境</small>
          </span>
        </a>
        <div className="identity">
          <span className="identity-dot" aria-hidden="true" />
          <span>{scopes.actor_id}</span>
          {platformAdmin && <small className="admin-badge">合成管理员</small>}
          <button className="text-button" onClick={() => void onLogout()}>
            退出
          </button>
        </div>
      </header>

      <div className="workspace-frame">
        <aside className="workspace-sidebar" aria-label="当前范围与业务模块">
          <section className="sidebar-scope">
            <p className="eyebrow">当前工作范围</p>
            <h1>项目与中心</h1>
            <label>
              <span>项目</span>
              <select
                aria-label="项目"
                value={selectedStudy?.id ?? ""}
                onChange={(event) => selectStudy(event.target.value)}
                disabled={scopes.studies.length === 0}
              >
                {scopes.studies.length === 0 && (
                  <option value="">尚无项目</option>
                )}
                {scopes.studies.map((study) => (
                  <option key={study.id} value={study.id}>
                    {study.code} · {study.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>中心</span>
              <select
                aria-label="中心"
                value={selectedSite?.id ?? ""}
                onChange={(event) => selectSite(event.target.value)}
                disabled={!selectedStudy || selectedStudy.sites.length === 0}
              >
                {(!selectedStudy || selectedStudy.sites.length === 0) && (
                  <option value="">尚无中心</option>
                )}
                {selectedStudy?.sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.code} · {site.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="scope-status">
              <span>角色</span>
              <strong>{selectedStudy?.roles.join("、") || "待建立"}</strong>
            </div>
          </section>

          <details className="sidebar-create" open={scopes.studies.length === 0}>
            <summary>新建项目</summary>
            {platformAdmin ? (
              <form data-testid="create-study-form" onSubmit={saveStudy}>
                <label>
                  项目编号
                  <input name="code" required maxLength={64} />
                </label>
                <label>
                  项目名称
                  <input name="title" required maxLength={255} />
                </label>
                <button type="submit" disabled={busy}>
                  保存项目
                </button>
              </form>
            ) : (
              <p>当前身份无租户项目管理权限。</p>
            )}
          </details>

          {selectedStudy && (
            <details className="sidebar-create">
              <summary>新建中心</summary>
              {canCreateSite ? (
                <form data-testid="create-site-form" onSubmit={saveSite}>
                  <label>
                    中心编号
                    <input name="code" required maxLength={64} />
                  </label>
                  <label>
                    中心名称
                    <input name="name" required maxLength={255} />
                  </label>
                  <button type="submit" disabled={busy}>
                    保存中心
                  </button>
                </form>
              ) : (
                <p>当前身份无该项目的中心管理权限。</p>
              )}
            </details>
          )}

          <details className="sidebar-create">
            <summary>维护当前名称</summary>
            {selectedStudy && (
              <form onSubmit={saveStudyTitle}>
                <label>
                  项目名称
                  <input
                    key={selectedStudy.revision}
                    name="title"
                    defaultValue={selectedStudy.title}
                    required
                  />
                </label>
                <button type="submit" disabled={busy}>
                  保存项目名称
                </button>
              </form>
            )}
            {selectedStudy && selectedSite && (
              <form onSubmit={saveSiteName}>
                <label>
                  中心名称
                  <input
                    key={selectedSite.revision}
                    name="name"
                    defaultValue={selectedSite.name}
                    required
                  />
                </label>
                <button type="submit" disabled={busy}>
                  保存中心名称
                </button>
              </form>
            )}
          </details>

          <nav className="workspace-module-nav" aria-label="业务模块">
            {MODULES.map((item) => (
              <button
                key={item.key}
                type="button"
                className={module === item.key ? "active" : ""}
                data-testid={`workspace-module-${item.key}`}
                onClick={() => setModule(item.key)}
              >
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </button>
            ))}
          </nav>
        </aside>

        <main className="workspace-main">
          <section className="workspace-context">
            <div>
              <p className="eyebrow">当前范围</p>
              <h2>{selectedStudy?.title ?? "从空白合成项目开始"}</h2>
              <p>
                {selectedSite
                  ? `${selectedSite.code} · ${selectedSite.name}`
                  : selectedStudy
                    ? "该项目尚无中心，请先建立中心。"
                    : "先建立项目和中心，再进入访视前与逐项核查。"}
              </p>
            </div>
            <span className="status-chip">
              {scopes.studies.length} 个项目 ·{" "}
              {scopes.studies.reduce(
                (total, study) => total + study.sites.length,
                0
              )}{" "}
              个中心
            </span>
          </section>

          {message && <div className="notice" role="status">{message}</div>}
          {error && <div className="notice notice-error" role="alert">{error}</div>}

          {Object.values(capabilities.providers).some(
            (provider) => provider.status === "not_configured"
          ) && (
            <div className="notice" role="status">
              <strong>部分自动能力未配置</strong>
              <span>
                系统会持续显示实际能力状态，不会把人工记录或未知结果标成自动完成。
              </span>
            </div>
          )}

          {renderModule()}
        </main>
      </div>
    </div>
  );
}

function EmptyWorkspace() {
  return (
    <section className="workspace-empty">
      <p className="eyebrow">空白工作区</p>
      <h2>建立第一个合成项目</h2>
      <p>
        在左上角输入项目编号和名称并保存，然后为该项目建立中心。无需修改种子脚本。
      </p>
    </section>
  );
}

function NoSiteWorkspace({ studyTitle }: { studyTitle: string }) {
  return (
    <section className="workspace-empty">
      <p className="eyebrow">项目已建立</p>
      <h2>{studyTitle} 尚无中心</h2>
      <p>
        使用左上角“新建中心”保存中心编号和名称。不同项目可以使用相同中心编号，
        但同一项目内重复编号会被服务端拒绝。
      </p>
    </section>
  );
}
