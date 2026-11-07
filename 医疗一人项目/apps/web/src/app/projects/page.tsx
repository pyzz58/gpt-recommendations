"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { createProject, fetchProjects } from "@/lib/api";
import type { ProjectListItem } from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  StatusPill,
  formatDate,
} from "@/components/ui";

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [scope, setScope] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      setProjects(await fetchProjects(signal));
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取项目");
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

  async function submitProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !scope.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const project = await createProject(
        name.trim(),
        scope.trim(),
        crypto.randomUUID(),
      );
      router.push(`/projects/${project.id}/overview`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法创建项目");
      setSubmitting(false);
    }
  }

  return (
    <div className="appShell projectsLanding">
      <aside className="projectRail">
        <Link className="brand" href="/projects">
          <span className="brandMark">医</span>
          <span>
            <strong>医疗一人项目</strong>
            <small>LOCAL RESEARCH OS</small>
          </span>
        </Link>
        <div className="railSection">
          <p className="railLabel">工作区</p>
          <div className="projectLink active">
            <span>全部项目</span>
            <small>{projects.length} 个独立项目</small>
          </div>
        </div>
        <Link className="navLink" href="/settings">
          <span>设置与连接</span>
          <small>模型、技能与备份状态</small>
        </Link>
        <div className="railBoundary">
          <span className="dot" />
          <div>
            <strong>模拟模式</strong>
            <p>真实模型和外部动作均为未配置状态。</p>
          </div>
        </div>
      </aside>

      <div className="mainColumn">
        <header className="appHeader projectsHeader">
          <div>
            <p className="eyebrow">WORKSPACE</p>
            <h1>项目</h1>
            <p>每个项目拥有独立的资料、任务、决定与预算边界。</p>
          </div>
          <button
            type="button"
            className="button primary"
            onClick={() => setCreating(true)}
          >
            新建项目
          </button>
        </header>

        <main className="pageCanvas">
          {loading && <LoadingPanel />}
          {!loading && error && <ErrorPanel message={error} onRetry={() => void load()} />}

          {!loading && !error && projects.length === 0 && (
            <EmptyState title="尚无项目">
              <p>创建项目后，才能上传资料、建立任务或比较候选方向。</p>
            </EmptyState>
          )}

          {!loading && !error && projects.length > 0 && (
            <section className="projectGrid">
              {projects.map((item) => (
                <Link
                  className="projectCard"
                  href={`/projects/${item.project.id}/overview`}
                  key={item.project.id}
                >
                  <div className="cardTopline">
                    <StatusPill value={item.project.stage} />
                    <span>更新于 {formatDate(item.project.updated_at)}</span>
                  </div>
                  <h2>{item.project.name}</h2>
                  <p>{item.project.scope}</p>
                  <div className="metricStrip">
                    <span>
                      <strong>{item.open_tasks}</strong> 待办
                    </span>
                    <span>
                      <strong>{item.documents}</strong> 资料
                    </span>
                    <span>
                      <strong>{item.opportunities}</strong> 候选
                    </span>
                  </div>
                </Link>
              ))}
            </section>
          )}
        </main>
      </div>

      {creating && (
        <div className="dialogBackdrop" role="presentation">
          <section className="dialogCard" role="dialog" aria-modal="true">
            <div className="dialogHeading">
              <div>
                <p className="eyebrow">NEW PROJECT</p>
                <h2>建立独立项目</h2>
              </div>
              <button
                className="iconButton"
                type="button"
                aria-label="关闭"
                onClick={() => setCreating(false)}
              >
                ×
              </button>
            </div>
            <form className="formStack" onSubmit={(event) => void submitProject(event)}>
              <label>
                项目名称
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="例如：猫用药方向筛选"
                  autoFocus
                  required
                  maxLength={300}
                />
              </label>
              <label>
                当前范围与约束
                <textarea
                  value={scope}
                  onChange={(event) => setScope(event.target.value)}
                  placeholder="说明研究问题、预算边界、排除项与希望何时停止。"
                  required
                  rows={5}
                />
              </label>
              <p className="formNote">
                初始化真实项目不会自动同意邮件、采购、签约或实验。
              </p>
              <button className="button primary" type="submit" disabled={submitting}>
                {submitting ? "正在创建…" : "创建并进入项目"}
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
