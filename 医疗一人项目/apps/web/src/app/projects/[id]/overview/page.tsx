"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  fetchOverview,
  fetchProjectPolicy,
  subscribeProjectEvents,
} from "@/lib/api";
import type { ProjectOverview, ProjectPolicyView } from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatDate,
  stateLabel,
  trackLabel,
} from "@/components/ui";

const eventLabels: Record<string, string> = {
  "project.created": "建立项目",
  "opportunity.created": "建立候选方向",
  "opportunity.revised": "修订候选方向",
  "opportunity.selected": "用户选择方向",
  "scientific_brief.created": "建立科学简报",
  "task.created": "建立任务",
  "task.queued": "任务进入队列",
  "knowledge.version_stored": "保存资料版本",
  "knowledge.version_promoted": "更新资料版本",
};

export default function OverviewPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [policy, setPolicy] = useState<ProjectPolicyView | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      const [nextOverview, nextPolicy] = await Promise.all([
        fetchOverview(projectId, signal),
        fetchProjectPolicy(projectId, signal),
      ]);
      setOverview(nextOverview);
      setPolicy(nextPolicy);
    } catch (cause) {
      if (!signal?.aborted) {
        setError(cause instanceof Error ? cause.message : "无法读取项目概览");
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

  useEffect(() => {
    let close: (() => void) | undefined;
    let active = true;
    void subscribeProjectEvents(projectId, 0, (event) => {
      setOverview((current) => {
        if (!current) return current;
        if (current.recent_events.some((item) => item.event_id === event.event_id)) {
          return current;
        }
        return {
          ...current,
          recent_events: [event, ...current.recent_events].slice(0, 12),
        };
      });
    }).then((cleanup) => {
      if (active) close = cleanup;
      else cleanup();
    }).catch(() => undefined);
    return () => {
      active = false;
      close?.();
    };
  }, [projectId]);

  if (loading) return <LoadingPanel />;
  if (error) return <ErrorPanel message={error} onRetry={() => void load()} />;
  if (!overview) return null;

  return (
    <div className="pageStack">
      <section className="overviewHero">
        <div>
          <p className="eyebrow">PROJECT BRIEF</p>
          <h2>从问题、证据到可执行的下一步</h2>
          <p className="heroCopy">
            这里只呈现已保存项目事件和真实对象状态。模拟计划、模型意见和未发生的外部动作不会被显示为进展。
          </p>
        </div>
        <div className="overviewStatus">
          <StatusPill value={overview.project.status} />
          <span>阶段 {stateLabel(overview.project.stage)}</span>
        </div>
      </section>

      <section className="metricGrid">
        <Metric
          label="开放任务"
          value={overview.counts.open_tasks}
          note="尚未接受或取消"
        />
        <Metric label="项目资料" value={overview.counts.documents} note="当前有效版本" />
        <Metric label="候选方向" value={overview.counts.opportunities} note="保留未知与反证" />
        <Metric label="活跃岗位" value={overview.counts.active_agents} note="实际Agent实例" />
      </section>

      <section className="surface">
        <SectionHeader
          eyebrow="POLICY BASELINE"
          title="运行依据与变更范围"
          aside={
            policy?.project_bundle ? (
              <StatusPill value={policy.project_bundle.state} />
            ) : undefined
          }
        />
        {policy?.project_bundle ? (
          <div className="directionCard">
            <span className="trackLabel">项目固定基线</span>
            <h3>{policy.project_bundle.version_label}</h3>
            <p>
              项目 revision {policy.project_revision} · bundle{" "}
              {policy.project_bundle.id.slice(0, 12)}… · 思想{" "}
              {policy.project_bundle.theory_version}
            </p>
            {policy.active_bundle &&
            policy.active_bundle.id !== policy.project_bundle.id ? (
              <p>
                工作区已有新 bundle；项目升级需通过影响检查和迁移操作，当前任务
                不会热替换。
              </p>
            ) : (
              <p>项目与工作区当前 bundle 一致。</p>
            )}
            <p className="mutedText">
              最近影响记录 {policy.impacts.length} 项，迁移操作{" "}
              {policy.migrations.length} 项。固定配置只说明运行依据，不证明科学结论。
            </p>
          </div>
        ) : (
          <EmptyState title="尚无策略基线">
            <p>未绑定 bundle 的项目不能启动新 Agent 任务。</p>
          </EmptyState>
        )}
      </section>

      <div className="splitLayout">
        <section className="surface">
          <SectionHeader eyebrow="CURRENT DIRECTION" title="当前研发方向" />
          {overview.current_direction ? (
            <div className="directionCard">
              <span className="trackLabel">
                {trackLabel(overview.current_direction.track)}
              </span>
              <h3>{overview.current_direction.title}</h3>
              <p>
                当前版本 V{overview.current_direction.current_version}，revision{" "}
                {overview.current_direction.revision}。
              </p>
              <Link
                className="textLink"
                href={`/projects/${projectId}/opportunities`}
              >
                查看比较依据 →
              </Link>
            </div>
          ) : (
            <EmptyState title="尚未选择方向">
              <p>候选比较产生后，用户选择会作为独立决定在此显示。</p>
            </EmptyState>
          )}
        </section>

        <section className="surface">
          <SectionHeader eyebrow="ACTION REQUIRED" title="等待用户或岗位处理" />
          {overview.action_required.length === 0 ? (
            <EmptyState title="当前没有待处理任务">
              <p>空状态不代表 Agent 正在后台工作。</p>
            </EmptyState>
          ) : (
            <div className="actionList">
              {overview.action_required.map((item) => (
                <Link
                  className="actionItem"
                  href={`/projects/${projectId}/tasks`}
                  key={`${item.kind}-${item.object_id}`}
                >
                  <StatusPill value={item.state} />
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="surface">
        <SectionHeader
          eyebrow="PROJECT EVENT LOG"
          title="真实项目事件"
          aside={<span className="mutedText">最新 12 项</span>}
        />
        {overview.recent_events.length === 0 ? (
          <EmptyState title="暂无项目事件">
            <p>页面不会为界面动画生成虚构活动。</p>
          </EmptyState>
        ) : (
          <ol className="timeline">
            {overview.recent_events.map((event) => (
              <li key={event.event_id}>
                <span className="timelineSeq">#{event.project_seq}</span>
                <div>
                  <strong>{eventLabels[event.type] ?? event.type}</strong>
                  <p>
                    {event.object_type} · {event.object_id.slice(0, 8)} ·{" "}
                    {formatDate(event.occurred_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <p className="boundaryNote">
        W10 当前提供项目浏览器与知识界面基础；“输入线索 → 自动核查 → 计划派工”的执行链仍由
        W11 接续，本页不会伪造这些状态。
      </p>
    </div>
  );
}

function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: number;
  note: string;
}) {
  return (
    <article className="metricCard">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
