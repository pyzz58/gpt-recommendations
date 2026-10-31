import { useEffect, useMemo, useState } from "react";

import type { CapabilityResponse, ScopeResponse } from "../../api/client";
import { DocumentWorkspace } from "../documents/DocumentWorkspace";
import {
  type WorkspaceSelection,
  readStoredSelection,
  resolveStoredSelection,
  storeSelection
} from "./selection";

type Props = {
  scopes: ScopeResponse;
  capabilities: CapabilityResponse;
  onLogout: () => Promise<void>;
};

export function WorkspaceSelector({
  scopes,
  capabilities,
  onLogout
}: Props) {
  const [selection, setSelection] = useState<WorkspaceSelection | null>(() =>
    resolveStoredSelection(scopes.studies, readStoredSelection())
  );

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

  function selectStudy(studyId: string) {
    const study = scopes.studies.find((candidate) => candidate.id === studyId);
    const site = study?.sites[0];
    if (!study || !site) {
      setSelection(null);
      return;
    }
    const next = { studyId: study.id, siteId: site.id };
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

  const unavailableProviders = Object.entries(capabilities.providers)
    .filter(([, provider]) => provider.status === "not_configured")
    .map(([name]) => (name === "ocr" ? "检验 OCR" : "模型分析"));

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
          <button className="text-button" onClick={() => void onLogout()}>
            退出
          </button>
        </div>
      </header>

      <main>
        <section className="workspace-heading">
          <div>
            <p className="eyebrow">当前工作范围</p>
            <h1>选择项目与中心</h1>
            <p>
              这里只显示服务端授权范围。切换后将作为后续监查工作的上下文。
            </p>
          </div>
          <div className="scope-counts" aria-label="授权范围统计">
            <span>
              <strong>{scopes.studies.length}</strong> 个项目
            </span>
            <span>
              <strong>
                {scopes.studies.reduce(
                  (total, study) => total + study.sites.length,
                  0
                )}
              </strong>{" "}
              个中心
            </span>
          </div>
        </section>

        <section className="selector-panel" aria-label="项目与中心选择">
          <label>
            <span>项目</span>
            <select
              value={selectedStudy?.id ?? ""}
              onChange={(event) => selectStudy(event.target.value)}
              disabled={scopes.studies.length === 0}
            >
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
              value={selectedSite?.id ?? ""}
              onChange={(event) => selectSite(event.target.value)}
              disabled={!selectedStudy || selectedStudy.sites.length === 0}
            >
              {selectedStudy?.sites.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.code} · {site.name}
                </option>
              ))}
            </select>
          </label>
          <div className="scope-status">
            <span>角色</span>
            <strong>{selectedStudy?.roles.join("、") || "无"}</strong>
          </div>
        </section>

        {scopes.studies.length === 0 && (
          <div className="notice notice-error" role="alert">
            当前账号尚未获授权任何项目或中心。请联系项目管理员配置访问范围。
          </div>
        )}

        {unavailableProviders.length > 0 && (
          <div className="notice" role="status">
            <strong>自动能力未配置</strong>
            <span>
              {unavailableProviders.join("、")}当前不可用，系统不会显示自动完成或
              正常结论。已有资料和人工路径仍可继续建设。
            </span>
          </div>
        )}

        <section className="workspace-grid">
          <article className="context-card active">
            <p className="eyebrow">已选择</p>
            <h2>{selectedStudy?.title ?? "未选择项目"}</h2>
            <p>
              {selectedSite
                ? `${selectedSite.code} · ${selectedSite.name}`
                : "没有可用中心"}
            </p>
            <span className="status-chip">授权范围已验证</span>
          </article>
          <article className="context-card placeholder">
            <p className="eyebrow">当前模块</p>
            <h2>资料与原文</h2>
            <p>
              上传私有合成资料，查看不可变版本、解析覆盖和可回查原文位置；当前页面
              不生成临床结论。
            </p>
            <span className="status-chip">W03 已接入</span>
          </article>
        </section>

        {selectedStudy && selectedSite && (
          <DocumentWorkspace
            studyId={selectedStudy.id}
            siteId={selectedSite.id}
          />
        )}
      </main>
    </div>
  );
}
