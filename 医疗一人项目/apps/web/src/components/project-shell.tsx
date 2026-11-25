"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { fetchProject, fetchProjects } from "@/lib/api";
import type { ProjectListItem, ProjectSnapshot } from "@/lib/api";

import { ErrorPanel, LoadingPanel, StatusPill, stateLabel } from "./ui";

const navigation = [
  { slug: "overview", label: "项目概览", note: "目标、判断与待办" },
  { slug: "agents", label: "Agent 工作区", note: "26 个独立岗位" },
  { slug: "tasks", label: "任务与交接", note: "状态与依赖" },
  { slug: "workflows", label: "专业流程", note: "三领域阶段与证据门" },
  { slug: "datasets", label: "数据统计", note: "版本、统计与复核" },
  { slug: "artifacts", label: "导出与预览", note: "Office、PDF与版式检查" },
  { slug: "mail", label: "邮件协作", note: "草稿、授权与模拟发送" },
  { slug: "external", label: "外部合作", note: "机构、报价、交付与专业记录" },
  { slug: "audits", label: "独立审计", note: "A25质量、A26反证与阻断" },
  { slug: "recovery", label: "恢复与离线", note: "回收站、索引与加密备份" },
  { slug: "opportunities", label: "机会比较", note: "证据、概率与成本" },
  { slug: "knowledge", label: "知识资料库", note: "原件、解析与检索" },
];

export function ProjectShell({
  projectId,
  children,
}: {
  projectId: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [project, setProject] = useState<ProjectSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [nextProjects, nextProject] = await Promise.all([
        fetchProjects(signal),
        fetchProject(projectId, signal),
      ]);
      setProjects(nextProjects);
      setProject(nextProject);
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取项目");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [load, pathname]);

  useEffect(() => {
    const refresh = () => void load();
    window.addEventListener("medical-one-project-changed", refresh);
    return () => {
      window.removeEventListener("medical-one-project-changed", refresh);
    };
  }, [load]);

  return (
    <div className="appShell">
      <aside className="projectRail">
        <Link className="brand" href="/projects" aria-label="返回项目列表">
          <span className="brandMark">医</span>
          <span>
            <strong>医疗一人项目</strong>
            <small>LOCAL RESEARCH OS</small>
          </span>
        </Link>

        <div className="railSection">
          <p className="railLabel">独立项目</p>
          <div className="projectList">
            {projects.map((item) => (
              <Link
                className={`projectLink ${
                  item.project.id === projectId ? "active" : ""
                }`}
                href={`/projects/${item.project.id}/overview`}
                key={item.project.id}
              >
                <span>{item.project.name}</span>
                <small>
                  {stateLabel(item.project.stage)} · {item.open_tasks} 待办
                </small>
              </Link>
            ))}
            <Link className="newProjectLink" href="/projects?new=1">
              ＋ 新建项目
            </Link>
          </div>
        </div>

        <div className="railSection currentProjectNav">
          <p className="railLabel">当前项目</p>
          <nav>
            {navigation.map((item) => {
              const href = `/projects/${projectId}/${item.slug}`;
              return (
                <Link
                  className={pathname === href ? "navLink active" : "navLink"}
                  href={href}
                  key={item.slug}
                >
                  <span>{item.label}</span>
                  <small>{item.note}</small>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="railBoundary">
          <span className="dot" />
          <div>
            <strong>本地开发模式</strong>
            <p>模型与邮件为模拟适配器；真实外发、采购、签署与实验未连接。</p>
          </div>
        </div>
      </aside>

      <div className="mainColumn">
        <header className="appHeader">
          <div className="projectIdentity">
            {loading ? (
              <span>正在读取项目…</span>
            ) : project ? (
              <>
                <div className="breadcrumbs">
                  项目 / {project.name}
                </div>
                <h1>{project.name}</h1>
                <p>{project.scope}</p>
              </>
            ) : (
              <span>项目不可用</span>
            )}
          </div>
          {project && (
            <div className="headerStatus">
              <StatusPill value={project.stage} />
              <span>revision {project.revision}</span>
            </div>
          )}
        </header>

        <main className="pageCanvas">
          {loading && <LoadingPanel />}
          {!loading && error && <ErrorPanel message={error} onRetry={() => void load()} />}
          {!loading && !error && children}
        </main>
      </div>
    </div>
  );
}
