"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchCapabilities,
  fetchSession,
  runMockSmoke,
} from "@/lib/api";
import type { CapabilityReport, MockSmokeResponse, SessionView } from "@/lib/api";

import { ErrorPanel, LoadingPanel, SectionHeader, StatusPill } from "@/components/ui";

export default function SettingsPage() {
  const [capabilities, setCapabilities] = useState<CapabilityReport | null>(null);
  const [session, setSession] = useState<SessionView | null>(null);
  const [smoke, setSmoke] = useState<MockSmokeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [smoking, setSmoking] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [nextCapabilities, nextSession] = await Promise.all([
        fetchCapabilities(signal),
        fetchSession(signal),
      ]);
      setCapabilities(nextCapabilities);
      setSession(nextSession);
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取设置");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [load]);

  async function checkMock() {
    setSmoking(true);
    try {
      setSmoke(await runMockSmoke("W10 settings contract check"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "模拟检查失败");
    } finally {
      setSmoking(false);
    }
  }

  return (
    <div className="appShell settingsShell">
      <aside className="projectRail">
        <Link className="brand" href="/projects">
          <span className="brandMark">医</span>
          <span>
            <strong>医疗一人项目</strong>
            <small>LOCAL RESEARCH OS</small>
          </span>
        </Link>
        <Link className="navLink" href="/projects">
          <span>返回项目</span>
          <small>项目列表与工作区</small>
        </Link>
        <div className="projectLink active">
          <span>设置与连接</span>
          <small>能力状态不是已连接</small>
        </div>
      </aside>
      <div className="mainColumn">
        <header className="appHeader">
          <div>
            <p className="eyebrow">SETTINGS</p>
            <h1>连接、模型与边界</h1>
            <p>未配置的账号、模型和外部动作会明确显示，不用假结果填充。</p>
          </div>
        </header>
        <main className="pageCanvas">
          {loading && <LoadingPanel />}
          {!loading && error && !capabilities && (
            <ErrorPanel message={error} onRetry={() => void load()} />
          )}
          {!loading && capabilities && (
            <div className="pageStack">
              {error && <ErrorPanel message={error} onRetry={() => void load()} />}
              <section className="surface">
                <SectionHeader eyebrow="SESSION" title="本地发起人会话" />
                {session && (
                  <div className="settingsGrid">
                    <div>
                      <span>显示名称</span>
                      <strong>{session.display_name}</strong>
                    </div>
                    <div>
                      <span>会话类型</span>
                      <strong>HttpOnly 本地会话</strong>
                    </div>
                    <div>
                      <span>工作区</span>
                      <code>{session.workspace_id}</code>
                    </div>
                  </div>
                )}
              </section>

              <section className="surface">
                <SectionHeader
                  eyebrow="DEPENDENCIES"
                  title="能力与依赖"
                  aside={<StatusPill value={capabilities.mode} tone="warn" />}
                />
                <div className="dependencyGrid">
                  {Object.entries(capabilities.dependencies).map(
                    ([key, dependency]) => (
                      <article key={key}>
                        <div>
                          <strong>{key}</strong>
                          <StatusPill value={dependency.status} />
                        </div>
                        <p>{dependency.detail}</p>
                      </article>
                    ),
                  )}
                </div>
              </section>

              <section className="surface">
                <SectionHeader eyebrow="MOCK PROVIDER" title="确定性模拟适配器" />
                <p className="mutedText">
                  检查只验证固定适配器与 API 合同，不产生科学内容。
                </p>
                <button
                  className="button primary"
                  type="button"
                  onClick={() => void checkMock()}
                  disabled={smoking}
                >
                  {smoking ? "检查中…" : "运行模拟检查"}
                </button>
                {smoke && (
                  <div className="smokeResult">
                    <strong>{smoke.output}</strong>
                    <p>{smoke.disclaimer}</p>
                  </div>
                )}
              </section>

              <section className="surface">
                <SectionHeader eyebrow="LIMITATIONS" title="当前限制" />
                <ul className="limitationList">
                  {capabilities.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
