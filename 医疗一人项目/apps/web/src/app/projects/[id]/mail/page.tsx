"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  authorizeMailDraft,
  createMailDraft,
  fetchArtifactExports,
  fetchMailAccount,
  fetchMailAttempts,
  fetchMailAuthorizations,
  fetchMailDrafts,
  fetchMailThreads,
  linkMailThread,
  notifyProjectChanged,
  reconcileMailSend,
  revokeMailAuthorization,
  sendMailDraft,
  syncMockInbox,
} from "@/lib/api";
import type {
  ArtifactExportView,
  MailAccountView,
  MailAttemptView,
  MailAuthorizationView,
  MailDraftView,
  MailThreadView,
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

type AuthorizationMap = Record<string, MailAuthorizationView[]>;

export default function MailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [account, setAccount] = useState<MailAccountView | null>(null);
  const [threads, setThreads] = useState<MailThreadView[]>([]);
  const [drafts, setDrafts] = useState<MailDraftView[]>([]);
  const [attempts, setAttempts] = useState<MailAttemptView[]>([]);
  const [authorizations, setAuthorizations] = useState<AuthorizationMap>({});
  const [artifacts, setArtifacts] = useState<ArtifactExportView[]>([]);
  const [recipient, setRecipient] = useState("expert@example.test");
  const [subject, setSubject] = useState("请审阅合成研究问题");
  const [body, setBody] = useState(
    "请指出该问题需要哪些原始证据、关键未知和下一项可验证工作。此邮件为本地模拟，不会外发。",
  );
  const [selectedArtifactIds, setSelectedArtifactIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextAccount, nextThreads, nextDrafts, nextAttempts, exportRows] =
          await Promise.all([
            fetchMailAccount(projectId, signal),
            fetchMailThreads(projectId, signal),
            fetchMailDrafts(projectId, signal),
            fetchMailAttempts(projectId, signal),
            fetchArtifactExports(projectId, signal),
          ]);
        const authGroups = await Promise.all(
          nextDrafts.map((draft) =>
            fetchMailAuthorizations(projectId, draft.id, signal),
          ),
        );
        setAccount(nextAccount);
        setThreads(nextThreads);
        setDrafts(nextDrafts);
        setAttempts(nextAttempts);
        setArtifacts(exportRows.filter((item) => item.state === "succeeded"));
        setAuthorizations(
          Object.fromEntries(
            nextDrafts.map((draft, index) => [draft.id, authGroups[index]]),
          ),
        );
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取邮件工作区");
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

  async function run(action: () => Promise<unknown>, message: string, name: string) {
    setBusy(name);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "邮件操作失败");
    } finally {
      setBusy("");
    }
  }

  async function createDraft() {
    if (!recipient.trim() || !subject.trim() || !body.trim()) return;
    await run(
      () =>
        createMailDraft(
          projectId,
          {
            toAddresses: [recipient.trim()],
            subject: subject.trim(),
            bodyText: body.trim(),
            attachmentIds: selectedArtifactIds,
            threadId: null,
          },
          crypto.randomUUID(),
        ),
      "邮件草稿已保存；尚未授权，也未发送。",
      "draft",
    );
    setSelectedArtifactIds([]);
  }

  async function linkThread(thread: MailThreadView) {
    await run(
      () => linkMailThread(projectId, thread.id, thread.revision),
      "未关联线程已由负责人明确关联到当前项目。",
      `link-${thread.id}`,
    );
  }

  async function syncInbox() {
    await run(
      () => syncMockInbox(projectId),
      "已导入本地合成的模拟收件；未进行任何真实邮箱连接。",
      "sync",
    );
  }

  async function authorizeDraft(draft: MailDraftView) {
    await run(
      () => authorizeMailDraft(projectId, draft.id, crypto.randomUUID()),
      "已创建一次性发送授权；仍需单独点击模拟发送。",
      `authorize-${draft.id}`,
    );
  }

  async function revokeAuthorization(authorization: MailAuthorizationView) {
    await run(
      () => revokeMailAuthorization(projectId, authorization.id),
      "发送授权已撤回。",
      `revoke-${authorization.id}`,
    );
  }

  async function simulateSend(
    draft: MailDraftView,
    authorization: MailAuthorizationView,
  ) {
    await run(
      () =>
        sendMailDraft(
          projectId,
          draft.id,
          authorization.id,
          crypto.randomUUID(),
        ),
      "模拟发送已记录；没有连接真实邮箱或真实收件人。",
      `send-${draft.id}`,
    );
  }

  async function reconcile(attempt: MailAttemptView) {
    await run(
      () => reconcileMailSend(projectId, attempt.id),
      "已向模拟适配器核对发送结果；未自动重发。",
      `reconcile-${attempt.id}`,
    );
  }

  return (
    <div className="pageStack">
      <section className="mailIntro">
        <div>
          <p className="eyebrow">W15 · LOCAL MOCK MAIL</p>
          <h2>可审计邮件协作</h2>
          <p>
            收件、草稿、收件人、附件版本、发送授权和模拟投递分别记录。
            “保存草稿”“授予发送”和“模拟发送”是三个独立动作。
          </p>
        </div>
        {account && (
          <div className="overviewStatus">
            <StatusPill value="本地模拟" tone="info" />
            <span>真实外发关闭</span>
          </div>
        )}
      </section>

      {loading && <LoadingPanel label="正在读取模拟邮箱与发送账本…" />}
      {!loading && error && (
        <ErrorPanel message={error} onRetry={() => void load()} />
      )}
      {!loading && notice && <div className="noticePanel">{notice}</div>}

      {!loading && account && (
        <section className="surface mailboxStrip">
          <div>
            <p className="eyebrow">MAILBOX ACCOUNT</p>
            <h3>{account.address}</h3>
            <p className="mutedText">{account.note}</p>
          </div>
          <div className="mailAccountState">
            <StatusPill value={account.state} tone="good" />
            <span>{account.provider_id}</span>
            <span>外部发送：{account.external_send_enabled ? "启用" : "关闭"}</span>
          </div>
        </section>
      )}

      {!loading && (
        <section className="surface">
          <SectionHeader
            eyebrow="INBOX"
            title="收件与线程"
            aside={
              <button
                className="button secondary"
                disabled={busy !== ""}
                onClick={() => void syncInbox()}
                type="button"
              >
                {busy === "sync" ? "正在同步…" : "导入模拟收件"}
              </button>
            }
          />
          {threads.length === 0 ? (
            <EmptyState title="模拟收件箱为空">
              <p>点击“导入模拟收件”载入合成线程；不会连接真实邮箱。</p>
            </EmptyState>
          ) : (
            <div className="mailThreadList">
              {threads.map((thread) => (
                <article className="mailThreadCard" key={thread.id}>
                  <div className="cardTopline">
                    <StatusPill value={thread.link_state} />
                    <span className="mutedText">
                      {thread.messages.length} 封 · {formatDate(thread.last_message_at)}
                    </span>
                  </div>
                  <h3>{thread.subject}</h3>
                  <div className="mailMessageList">
                    {thread.messages.map((message) => (
                      <div className="mailMessage" key={message.id}>
                        <div>
                          <strong>{message.sender}</strong>
                          <small>{formatDate(message.sent_at)}</small>
                        </div>
                        <p>{message.body_text}</p>
                        <span>
                          {message.direction === "inbound" ? "收件" : "模拟发出"} ·{" "}
                          {message.synthetic ? "合成" : message.delivery_state}
                        </span>
                      </div>
                    ))}
                  </div>
                  {thread.link_state === "unlinked" && (
                    <button
                      className="button secondary"
                      disabled={busy !== ""}
                      onClick={() => void linkThread(thread)}
                      type="button"
                    >
                      明确关联到当前项目
                    </button>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {!loading && (
        <section className="surface">
          <SectionHeader
            eyebrow="DRAFT"
            title="创建邮件草稿"
            aside={<span className="mutedText">保存草稿不等于授权或发送</span>}
          />
          <div className="mailComposer">
            <div className="mailFields">
              <label>
                收件人
                <input
                  value={recipient}
                  onChange={(event) => setRecipient(event.target.value)}
                />
              </label>
              <label>
                主题
                <input
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                />
              </label>
              <label className="mailBodyField">
                正文
                <textarea
                  rows={6}
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                />
              </label>
            </div>
            <div className="mailAttachmentPicker">
              <p className="eyebrow">ATTACHMENTS</p>
              {artifacts.length === 0 ? (
                <p className="mutedText">
                  当前没有已完成导出文件可附加。可先在“导出与预览”生成。
                </p>
              ) : (
                artifacts.map((artifact) => (
                  <label key={artifact.id}>
                    <input
                      type="checkbox"
                      checked={selectedArtifactIds.includes(
                        artifact.artifact_version_id!,
                      )}
                      onChange={(event) => {
                        const versionId = artifact.artifact_version_id!;
                        setSelectedArtifactIds((current) =>
                          event.target.checked
                            ? [...current, versionId]
                            : current.filter((item) => item !== versionId),
                        );
                      }}
                    />
                    <span>
                      {artifact.filename}
                      <small>
                        {artifact.format.toUpperCase()} ·{" "}
                        {formatBytes(artifact.size_bytes)}
                      </small>
                    </span>
                  </label>
                ))
              )}
            </div>
            <button
              className="button primary"
              disabled={busy !== ""}
              onClick={() => void createDraft()}
              type="button"
            >
              {busy === "draft" ? "正在保存…" : "仅保存草稿"}
            </button>
          </div>
          <p className="boundaryNote">
            本地模拟适配器只接受 <code>.test</code>、<code>.invalid</code> 或{" "}
            <code>.example</code> 地址。真实邮箱连接、真实收件人和外发授权尚未配置。
          </p>
        </section>
      )}

      {!loading && (
        <section className="surface">
          <SectionHeader
            eyebrow="DRAFTS & AUTHORIZATION"
            title="草稿与发送授权"
            aside={<span className="mutedText">{drafts.length} 个草稿</span>}
          />
          {drafts.length === 0 ? (
            <EmptyState title="还没有邮件草稿">
              <p>草稿会保存正文哈希和附件版本哈希。</p>
            </EmptyState>
          ) : (
            <div className="mailDraftGrid">
              {drafts.map((draft) => {
                const draftAuthorizations = authorizations[draft.id] ?? [];
                const active = draftAuthorizations.find(
                  (item) => item.state === "active",
                );
                const latestAuthorization = draftAuthorizations[0];
                const relatedAttempts = attempts.filter(
                  (item) => item.draft_id === draft.id,
                );
                return (
                  <article className="mailDraftCard" key={draft.id}>
                    <div className="cardTopline">
                      <StatusPill value={draft.state} />
                      {active && <StatusPill value="已授权" tone="warn" />}
                    </div>
                    <h3>{draft.subject}</h3>
                    <p className="mutedText">
                      收件人 {draft.recipients.to.join(", ")} · revision{" "}
                      {draft.revision}
                    </p>
                    <p className="mailDraftBody">{draft.body_text}</p>
                    <div className="mailMetaGrid">
                      <span>
                        正文 SHA-256
                        <code>{draft.body_sha256.slice(0, 24)}…</code>
                      </span>
                      <span>
                        内容 SHA-256
                        <code>{draft.content_sha256.slice(0, 24)}…</code>
                      </span>
                      <span>
                        附件
                        <strong>{draft.attachments.length}</strong>
                      </span>
                      <span>
                        更新时间
                        <strong>{formatDate(draft.updated_at)}</strong>
                      </span>
                    </div>
                    {draft.attachments.length > 0 && (
                      <div className="mailAttachmentList">
                        {draft.attachments.map((attachment) => (
                          <span key={attachment.id}>
                            {attachment.filename} · {attachment.sha256.slice(0, 12)}…
                          </span>
                        ))}
                      </div>
                    )}
                    {latestAuthorization && (
                      <div className="authorizationBox">
                        <span>
                          授权 {latestAuthorization.used_sends}/
                          {latestAuthorization.max_sends}
                        </span>
                        <StatusPill value={latestAuthorization.state} />
                        <small>
                          有效至 {formatDate(latestAuthorization.expires_at)}
                        </small>
                      </div>
                    )}
                    <div className="cardActions">
                      {!active &&
                        ["draft", "ready", "failed"].includes(draft.state) && (
                          <button
                            className="button secondary"
                            disabled={busy !== ""}
                            onClick={() => void authorizeDraft(draft)}
                            type="button"
                          >
                            授权一次
                          </button>
                        )}
                      {active && (
                        <>
                          <button
                            className="button primary"
                            disabled={busy !== ""}
                            onClick={() => void simulateSend(draft, active)}
                            type="button"
                          >
                            模拟发送
                          </button>
                          <button
                            className="button secondary"
                            disabled={busy !== ""}
                            onClick={() =>
                              void revokeAuthorization(active)
                            }
                            type="button"
                          >
                            撤回授权
                          </button>
                        </>
                      )}
                      {relatedAttempts
                        .filter((item) => item.state === "outcome_unknown")
                        .map((attempt) => (
                          <button
                            className="button secondary"
                            disabled={busy !== ""}
                            key={attempt.id}
                            onClick={() => void reconcile(attempt)}
                            type="button"
                          >
                            核对发送结果
                          </button>
                        ))}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      )}

      {!loading && (
        <section className="surface">
          <SectionHeader
            eyebrow="SEND LEDGER"
            title="发送尝试"
            aside={<span className="mutedText">{attempts.length} 个记录</span>}
          />
          {attempts.length === 0 ? (
            <EmptyState title="尚无发送尝试">
              <p>创建授权并点击“模拟发送”后才会出现记录。</p>
            </EmptyState>
          ) : (
            <div className="mailAttemptList">
              {attempts.map((attempt) => (
                <div className="mailAttempt" key={attempt.id}>
                  <div>
                    <StatusPill value={attempt.state} />
                    <strong>{attempt.subject}</strong>
                  </div>
                  <p>
                    {attempt.provider_message_id ?? "无 provider message id"} ·{" "}
                    {formatDate(attempt.completed_at ?? attempt.created_at)}
                  </p>
                  {attempt.outcome_detail && (
                    <small>{attempt.outcome_detail}</small>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
