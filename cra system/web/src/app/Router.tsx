import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type CapabilityResponse,
  type ScopeResponse,
  getCapabilities,
  getScopes,
  loginSynthetic,
  logout,
  oidcLoginUrl
} from "../api/client";
import { WorkspaceSelector } from "../features/workspace/WorkspaceSelector";

type ScreenState =
  | { kind: "loading" }
  | { kind: "login"; capabilities: CapabilityResponse }
  | {
      kind: "workspace";
      capabilities: CapabilityResponse;
      scopes: ScopeResponse;
    }
  | { kind: "error"; message: string };

function capabilityLabel(status: string): string {
  switch (status) {
    case "configured":
      return "已配置，未验证";
    case "validated":
      return "已验证";
    case "not_configured":
      return "未配置";
    case "not_implemented":
      return "尚未实现";
    case "limited":
      return "有限";
    default:
      return "可用";
  }
}

export function Router() {
  const [screen, setScreen] = useState<ScreenState>({ kind: "loading" });
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setActionError(null);
    try {
      const capabilities = await getCapabilities();
      try {
        const scopes = await getScopes();
        setScreen({ kind: "workspace", capabilities, scopes });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          setScreen({ kind: "login", capabilities });
          return;
        }
        throw error;
      }
    } catch (error) {
      setScreen({
        kind: "error",
        message:
          error instanceof Error ? error.message : "无法连接CRA工作台服务"
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function login() {
    if (screen.kind !== "login") {
      return;
    }
    if (
      screen.capabilities.identity_mode === "oidc" &&
      screen.capabilities.identity_configured
    ) {
      window.location.assign(oidcLoginUrl());
      return;
    }
    if (screen.capabilities.identity_mode === "synthetic") {
      setActionError(null);
      try {
        await loginSynthetic();
        await load();
      } catch (error) {
        setActionError(
          error instanceof Error ? error.message : "合成登录失败"
        );
      }
      return;
    }
    setActionError("正式身份服务尚未配置，不能进入工作台。");
  }

  async function signOut() {
    try {
      await logout();
    } finally {
      await load();
    }
  }

  if (screen.kind === "loading") {
    return (
      <main className="center-state" aria-live="polite">
        <div className="loader" />
        <p>正在核对身份与授权范围…</p>
      </main>
    );
  }

  if (screen.kind === "error") {
    return (
      <main className="center-state">
        <p className="eyebrow">连接失败</p>
        <h1>工作台暂时不可用</h1>
        <p>{screen.message}</p>
        <button className="primary-button" onClick={() => void load()}>
          重新连接
        </button>
      </main>
    );
  }

  if (screen.kind === "login") {
    const identityReady =
      screen.capabilities.identity_configured &&
      (screen.capabilities.identity_mode === "synthetic" ||
        screen.capabilities.identity_mode === "oidc");
    return (
      <main className="login-page">
        <section className="login-copy">
          <p className="eyebrow">CRA SYSTEM · V0.2</p>
          <h1>从正确的项目和中心开始监查</h1>
          <p>
            API、数据库范围和操作历史使用同一套授权。页面不接收浏览器自报的
            租户、操作者或模拟身份。
          </p>
          <div className="login-points">
            <span>项目与中心授权后可见</span>
            <span>能力状态如实显示</span>
            <span>仅公开合成演示数据</span>
          </div>
        </section>

        <section className="login-panel">
          <p className="eyebrow">身份与能力</p>
          <h2>
            {screen.capabilities.identity_mode === "synthetic"
              ? "合成工作台"
              : "机构身份登录"}
          </h2>
          <dl className="capability-list">
            <div>
              <dt>身份模式</dt>
              <dd>
                {screen.capabilities.identity_mode === "synthetic"
                  ? "合成演示"
                  : "OIDC"}
              </dd>
            </div>
            <div>
              <dt>模型分析</dt>
              <dd>
                {capabilityLabel(
                  screen.capabilities.providers.model.status
                )}
              </dd>
            </div>
            <div>
              <dt>检验 OCR</dt>
              <dd>
                {capabilityLabel(screen.capabilities.providers.ocr.status)}
              </dd>
            </div>
          </dl>
          <button
            className="primary-button"
            onClick={() => void login()}
            disabled={!identityReady}
          >
            {identityReady
              ? "进入合成工作台"
              : "身份服务尚未配置"}
          </button>
          {actionError && (
            <p className="inline-error" role="alert">
              {actionError}
            </p>
          )}
          <p className="security-note">
            自动能力未配置时不会执行或显示“已完成”的临床判断。
          </p>
        </section>
      </main>
    );
  }

  return (
    <WorkspaceSelector
      scopes={screen.scopes}
      capabilities={screen.capabilities}
      onLogout={signOut}
    />
  );
}
