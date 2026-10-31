"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchAgents } from "@/lib/api";
import type { AgentScene } from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatDate,
  stateLabel,
} from "@/components/ui";

type Filter = "assigned" | "all" | "unassigned";

export default function AgentsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [agents, setAgents] = useState<AgentScene[]>([]);
  const [filter, setFilter] = useState<Filter>("assigned");
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      setAgents(await fetchAgents(projectId, signal));
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取岗位状态");
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
  }, [load]);

  const visible = useMemo(() => {
    if (filter === "all") return agents;
    if (filter === "unassigned") {
      return agents.filter((agent) => agent.scene_state === "unassigned");
    }
    return agents.filter((agent) => agent.scene_state !== "unassigned");
  }, [agents, filter]);

  const selected = agents.find((agent) => agent.role_id === selectedRole) ?? null;
  const counts = {
    assigned: agents.filter((agent) => agent.scene_state !== "unassigned").length,
    running: agents.filter((agent) =>
      ["queued", "running", "submitted"].includes(agent.scene_state),
    ).length,
    waiting: agents.filter((agent) =>
      ["needs_input", "rework", "failed"].includes(agent.scene_state),
    ).length,
  };

  if (loading) return <LoadingPanel />;
  if (error) return <ErrorPanel message={error} onRetry={() => void load()} />;

  return (
    <div className="pageStack">
      <section className="agentSummary">
        <div>
          <p className="eyebrow">26 ROLE CATALOG</p>
          <h2>岗位按真实任务与运行记录显示</h2>
          <p>
            未分配表示当前项目没有对应任务，不代表岗位已经运行。当前模型仍是
            deterministic mock。
          </p>
        </div>
        <div className="agentCounts">
          <span>
            <strong>{counts.assigned}</strong> 有任务
          </span>
          <span>
            <strong>{counts.running}</strong> 队列/运行/待审
          </span>
          <span>
            <strong>{counts.waiting}</strong> 需处理
          </span>
        </div>
      </section>

      <div className="filterBar" role="group" aria-label="岗位过滤">
        {(
          [
            ["assigned", "有任务"],
            ["all", "全部26岗"],
            ["unassigned", "未分配"],
          ] as const
        ).map(([value, label]) => (
          <button
            className={filter === value ? "filterButton active" : "filterButton"}
            type="button"
            onClick={() => setFilter(value)}
            key={value}
          >
            {label}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <EmptyState title="没有符合筛选的岗位">
          <p>创建任务后，对应岗位卡片会显示真实任务状态。</p>
        </EmptyState>
      ) : (
        <section className="agentGrid">
          {visible.map((agent) => (
            <button
              className={`agentCard ${
                selectedRole === agent.role_id ? "selected" : ""
              }`}
              type="button"
              key={agent.role_id}
              onClick={() => setSelectedRole(agent.role_id)}
            >
              <div className="agentCardTop">
                <span className="roleId">{agent.role_id}</span>
                <StatusPill value={agent.scene_state} />
              </div>
              <h3>{agent.name}</h3>
              <p>{agent.responsibilities[0]}</p>
              <div className="agentCardMeta">
                <span>汇报至 {agent.reports_to.join(" / ")}</span>
                <span>{agent.latest_run?.mode ?? "未运行"}</span>
              </div>
            </button>
          ))}
        </section>
      )}

      {selected && (
        <section className="surface detailSurface">
          <SectionHeader
            eyebrow={`${selected.role_id} / V${selected.version}`}
            title={selected.name}
            aside={<StatusPill value={selected.scene_state} />}
          />
          <div className="detailGrid">
            <div>
              <h3>职责</h3>
              <ul>
                {selected.responsibilities.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>标准交付</h3>
              <div className="tagCloud">
                {selected.deliverable_types.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
            </div>
            <div>
              <h3>当前工作</h3>
              {selected.latest_task_goal ? (
                <>
                  <p>{selected.latest_task_goal}</p>
                  <p className="mutedText">
                    状态 {stateLabel(selected.latest_task_state ?? "")} ·{" "}
                    {formatDate(selected.updated_at)}
                  </p>
                </>
              ) : (
                <p className="mutedText">当前项目未分配任务。</p>
              )}
            </div>
            <div>
              <h3>最近运行</h3>
              {selected.latest_run ? (
                <>
                  <p>
                    {selected.latest_run.provider_id} /{" "}
                    {selected.latest_run.model_id}
                  </p>
                  <p className="mutedText">
                    {stateLabel(selected.latest_run.state)} ·{" "}
                    {formatDate(selected.latest_run.created_at)}
                  </p>
                </>
              ) : (
                <p className="mutedText">尚无运行记录。</p>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
