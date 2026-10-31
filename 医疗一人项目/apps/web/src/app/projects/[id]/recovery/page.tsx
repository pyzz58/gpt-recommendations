"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createEncryptedBackup,
  fetchCapabilities,
  fetchKnowledgeDocuments,
  fetchRecoveryWorkspace,
  notifyProjectChanged,
  rebuildKnowledgeIndex,
  restoreKnowledgeDocument,
  runRestoreCheck,
  trashKnowledgeDocument,
} from "@/lib/api";
import type {
  BackupView,
  CapabilityReport,
  KnowledgeDocumentSummary,
  RecoveryWorkspaceView,
  RestoreCheckView,
} from "@/lib/api";

import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  SectionHeader,
  StatusPill,
  formatBytes,
  formatDate,
} from "@/components/ui";

export default function RecoveryPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [workspace, setWorkspace] = useState<RecoveryWorkspaceView | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocumentSummary[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityReport | null>(null);
  const [trashReason, setTrashReason] = useState("用户明确移入回收站，等待复核。");
  const [passphrase, setPassphrase] = useState("");
  const [latestCheck, setLatestCheck] = useState<RestoreCheckView | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextWorkspace, nextDocuments, nextCapabilities] = await Promise.all([
          fetchRecoveryWorkspace(projectId, signal),
          fetchKnowledgeDocuments(projectId, "", signal),
          fetchCapabilities(signal),
        ]);
        setWorkspace(nextWorkspace);
        setDocuments(nextDocuments);
        setCapabilities(nextCapabilities);
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取恢复状态");
        }
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [load]);

  async function runAction(action: () => Promise<unknown>, message: string, key: string) {
    setBusy(key);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "恢复操作失败");
    } finally {
      setBusy("");
    }
  }

  async function trashDocument(document: KnowledgeDocumentSummary) {
    await runAction(
      () => trashKnowledgeDocument(projectId, document.id, trashReason.trim()),
      "文档已进入回收站；原件仍保留，可恢复。",
      `trash-${document.id}`,
    );
  }

  async function rebuildIndex(document: KnowledgeDocumentSummary) {
    if (!document.version_id) return;
    await runAction(
      () => rebuildKnowledgeIndex(projectId, document.version_id!),
      "未引用索引已从解析结果重建。",
      `rebuild-${document.id}`,
    );
  }

  async function restoreDocument(documentId: string) {
    await runAction(
      () => restoreKnowledgeDocument(projectId, documentId),
      "文档及历史版本的访问状态已恢复。",
      `restore-${documentId}`,
    );
  }

  async function createBackup() {
    if (passphrase.length < 12) {
      setError("备份口令至少需要 12 个字符。");
      return;
    }
    await runAction(
      () =>
        createEncryptedBackup(
          projectId,
          passphrase,
          crypto.randomUUID(),
        ),
      "项目数据库快照与原件已加密写入受控备份目录。",
      "backup",
    );
  }

  async function verifyBackup(backup: BackupView) {
    if (passphrase.length < 12) {
      setError("恢复校验需要同一备份口令，至少 12 个字符。");
      return;
    }
    setBusy(`check-${backup.id}`);
    setError("");
    setNotice("");
    try {
      const check = await runRestoreCheck(projectId, backup.id, passphrase);
      setLatestCheck(check);
      setNotice(
        check.state === "verified"
          ? "隔离恢复校验通过；活动数据库未被覆盖。"
          : "隔离恢复校验失败，请检查错误详情。",
      );
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "恢复校验失败");
    } finally {
      setBusy("");
    }
  }

  const network = capabilities?.dependencies.network;
  const displayedCheck = latestCheck ?? workspace?.restore_checks[0] ?? null;

  return (
    <div className="pageStack">
      <section className="surface externalIntro">
        <div>
          <p className="eyebrow">W18 · LOCAL CONTINUITY</p>
          <h2>恢复、离线与加密备份</h2>
          <p>
            默认离线模式可继续访问本地数据库、原件、解析与检索；远程模型、资料抓取和
            邮件工具必须显式切换到 allowlist 模式并完成各自连接验收。
          </p>
        </div>
        <div className="warningBanner">
          恢复校验在隔离目录验证加密档案，不会覆盖活动数据库；也不等于异地备份已完成。
        </div>
      </section>

      {loading && <LoadingPanel />}
      {!loading && error && (
        <ErrorPanel message={error} onRetry={() => void load()} />
      )}
      {!loading && notice && <p className="noticeBanner">{notice}</p>}

      {!loading && (
        <>
          <section className="surface">
            <SectionHeader
              eyebrow="NETWORK POLICY"
              title="当前网络能力"
              aside={<StatusPill value={network?.status ?? "not_checked"} />}
            />
            <div className="recoveryNetwork">
              <strong>{network?.detail ?? "网络策略状态不可用"}</strong>
              <span>
                本地数据库、已存原件、解析文本、词法检索与 mock 流程不依赖公网。
                缓存法规、专利和文献不会被标记为最新。
              </span>
            </div>
          </section>

          <section className="surface">
            <SectionHeader
              eyebrow="INDEX REPAIR"
              title="活动资料与索引重建"
              aside={<span className="mutedText">{documents.length} 份活动资料</span>}
            />
            <label className="recoveryReason">
              移入回收站理由
              <input
                value={trashReason}
                onChange={(event) => setTrashReason(event.target.value)}
              />
            </label>
            {documents.length === 0 ? (
              <EmptyState title="没有活动知识资料">
                <p>先上传资料；回收站恢复后会重新出现在这里。</p>
              </EmptyState>
            ) : (
              <div className="recoveryDocumentList">
                {documents.map((document) => (
                  <article className="recoveryDocumentRow" key={document.id}>
                    <div>
                      <strong>{document.title}</strong>
                      <small>
                        {document.filename} · {document.ingest_state} ·{" "}
                        {document.citations_count} 条引用
                      </small>
                    </div>
                    <span>{formatBytes(document.size_bytes)}</span>
                    <button
                      className="button secondary"
                      disabled={busy !== "" || !document.version_id}
                      onClick={() => void rebuildIndex(document)}
                      type="button"
                    >
                      重建索引
                    </button>
                    <button
                      className="button danger"
                      disabled={busy !== "" || !trashReason.trim()}
                      onClick={() => void trashDocument(document)}
                      type="button"
                    >
                      移入回收站
                    </button>
                  </article>
                ))}
              </div>
            )}
            <p className="formNote">
              有不可变引用的索引会被拒绝重建，以保留 Citation 的 chunk 定位；需要新索引
              版本时另行迁移，不能静默改写引用。
            </p>
          </section>

          <section className="surface">
            <SectionHeader
              eyebrow="TRASH · 30 DAYS"
              title="回收站"
              aside={
                <span className="mutedText">
                  {workspace?.trash.length ?? 0} 份待恢复资料
                </span>
              }
            />
            {!workspace || workspace.trash.length === 0 ? (
              <EmptyState title="回收站为空">
                <p>删除先进入回收站；不会直接清除原件或引用历史。</p>
              </EmptyState>
            ) : (
              <div className="externalRecordGrid">
                {workspace.trash.map((entry) => (
                  <article className="externalRecordCard" key={entry.id}>
                    <div className="cardTopline">
                      <StatusPill value={entry.state} />
                      <span>{entry.reference_count} 条引用</span>
                    </div>
                    <h3>{entry.title}</h3>
                    <p>{entry.reason}</p>
                    {entry.blocked_reason && (
                      <div className="warningBanner">
                        引用保留提示：{entry.blocked_reason}
                      </div>
                    )}
                    <small>
                      删除 {formatDate(entry.deleted_at)} · 最早清理{" "}
                      {formatDate(entry.purge_after)}
                    </small>
                    <button
                      className="button secondary"
                      disabled={busy !== ""}
                      onClick={() => void restoreDocument(entry.document_id)}
                      type="button"
                    >
                      恢复资料
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="surface">
            <SectionHeader
              eyebrow="AES-256-GCM"
              title="加密项目备份"
              aside={<span className="mutedText">口令只用于本次请求</span>}
            />
            <div className="recoveryBackupForm">
              <label>
                备份与恢复口令
                <input
                  autoComplete="new-password"
                  minLength={12}
                  onChange={(event) => setPassphrase(event.target.value)}
                  placeholder="至少12个字符；系统不保存"
                  type="password"
                  value={passphrase}
                />
              </label>
              <button
                className="button primary"
                disabled={busy !== "" || passphrase.length < 12}
                onClick={() => void createBackup()}
                type="button"
              >
                {busy === "backup" ? "正在加密备份…" : "创建加密备份"}
              </button>
            </div>
            <p className="formNote">
              备份包含项目数据库 JSON 快照、知识原件、分析/导出对象和引用关系。
              scrypt 派生 AES-256-GCM 密钥；恢复检查会重新核对 manifest、原件 hash
              和引用链。
            </p>
            {!workspace || workspace.backups.length === 0 ? (
              <EmptyState title="还没有项目备份">
                <p>创建后只显示 hash、对象数和恢复校验状态。</p>
              </EmptyState>
            ) : (
              <div className="recoveryDocumentList">
                {workspace.backups.map((backup) => (
                  <article className="recoveryBackupRow" key={backup.id}>
                    <div>
                      <strong>{formatDate(backup.created_at)}</strong>
                      <small>
                        {backup.file_name} · {formatBytes(backup.encrypted_size_bytes)}
                      </small>
                    </div>
                    <code>{shortHash(backup.backup_sha256 ?? "unavailable")}</code>
                    <button
                      className="button secondary"
                      disabled={busy !== "" || passphrase.length < 12}
                      onClick={() => void verifyBackup(backup)}
                      type="button"
                    >
                      隔离恢复校验
                    </button>
                  </article>
                ))}
              </div>
            )}
            {displayedCheck && <RestoreResult check={displayedCheck} />}
          </section>

          <section className="surface">
            <SectionHeader
              eyebrow="LIMITATIONS"
              title="恢复能力边界"
            />
            <ul className="limitationList">
              {workspace?.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
              <li>
                备份成功后仍未验证异地介质、主机损坏、密钥丢失或完整数据库重放。
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

function RestoreResult({ check }: { check: RestoreCheckView }) {
  return (
    <div className={`recoveryResult ${check.state}`}>
      <div className="cardTopline">
        <StatusPill value={check.state} />
        <span>{check.object_count} 个对象</span>
      </div>
      <p>
        数据库表 {Object.keys(check.table_counts).length} 组；活动数据库覆盖：
        {String(check.detail.active_database_overwritten ?? "unknown")}
      </p>
      {check.state === "verified" ? (
        <small>{String(check.detail.restore_directory ?? "")}</small>
      ) : (
        <small>{String(check.detail.error ?? "恢复校验失败")}</small>
      )}
    </div>
  );
}

function shortHash(value: string): string {
  return value.length > 20 ? `${value.slice(0, 12)}…${value.slice(-8)}` : value;
}
