"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  createExternalAuthorization,
  createExternalContract,
  createExternalDeliverable,
  createExternalEngagement,
  createExternalExpert,
  createExternalOrganization,
  createExternalQuote,
  createProfessionalRecord,
  fetchExternalWorkspace,
  fetchKnowledgeDocuments,
  notifyProjectChanged,
  receiveExternalDeliverable,
  reviewExternalDeliverable,
  transitionExternalContract,
  transitionExternalEngagement,
} from "@/lib/api";
import type {
  ExternalWorkspaceView,
  KnowledgeDocumentSummary,
  ProviderType,
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

const providerLabels: Record<ProviderType, string> = {
  cdmo: "CDMO",
  cro: "CRO",
  smo: "SMO",
  central_lab: "中心实验室",
  testing_lab: "检测实验室",
  sample_provider: "样本提供方",
  prototype_provider: "原型供应方",
  regulatory: "监管机构",
  ethics: "伦理/批准机构",
  other: "其他专业机构",
};

const nextStates: Record<string, string | null> = {
  draft: "scope_ready",
  scope_ready: "requested",
  requested: "quoted",
  quoted: "authorized",
  authorized: "executing",
  executing: "delivered",
  delivered: "under_review",
  under_review: "accepted",
  accepted: "closed",
};

export default function ExternalPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const [workspace, setWorkspace] = useState<ExternalWorkspaceView | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [orgName, setOrgName] = useState("合成合作机构");
  const [orgType, setOrgType] = useState<ProviderType>("cro");
  const [orgCapability, setOrgCapability] = useState(
    "仅登记机构能力材料；尚未联系或核实为真实合作方。",
  );
  const [orgSource, setOrgSource] = useState("manual:provider-source");
  const [expertName, setExpertName] = useState("合成专业审阅人");
  const [expertise, setExpertise] = useState("目标物种药理与统计审阅");
  const [expertSource, setExpertSource] = useState("manual:public-profile");
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");
  const [engagementTitle, setEngagementTitle] = useState("合成方法学验证工作包");
  const [scientificQuestion, setScientificQuestion] = useState(
    "拟议检测方法能否回答预设的技术可行性问题？",
  );
  const [decisionImpact, setDecisionImpact] = useState(
    "决定是否继续准备真实方法学验证。",
  );
  const [deliverableScope, setDeliverableScope] = useState(
    "原始数据;检测报告;方法与偏差记录",
  );
  const [recordKind, setRecordKind] = useState("regulatory");
  const [recordTitle, setRecordTitle] = useState("合成法规分类问题");
  const [recordSource, setRecordSource] = useState("manual:official-source");
  const [recordMarket, setRecordMarket] = useState("待核实市场");
  const [selectedEngagementId, setSelectedEngagementId] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [quoteAmount, setQuoteAmount] = useState("2000.00");
  const [contractTitle, setContractTitle] = useState("合成服务合同草案");
  const [contractTerms, setContractTerms] = useState(
    "仅登记测试条款；未与真实机构签约。",
  );
  const [deliverableTitle, setDeliverableTitle] = useState("合成外部原始交付");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError("");
      try {
        const [nextWorkspace, nextDocuments] = await Promise.all([
          fetchExternalWorkspace(projectId, signal),
          fetchKnowledgeDocuments(projectId, "", signal),
        ]);
        setWorkspace(nextWorkspace);
        setDocuments(nextDocuments.filter((item) => item.version_id));
        setSelectedOrganizationId(
          (current) =>
            current ||
            nextWorkspace.organizations.find(
              (item) => item.verification_state === "verified",
            )?.id ||
            nextWorkspace.organizations[0]?.id ||
            "",
        );
        setSelectedEngagementId(
          (current) => current || nextWorkspace.engagements[0]?.id || "",
        );
        setSelectedDocumentId(
          (current) => current || nextDocuments.find((item) => item.version_id)?.version_id || "",
        );
      } catch (cause) {
        if (!signal?.aborted) {
          setError(cause instanceof Error ? cause.message : "无法读取外部合作记录");
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

  const selectedEngagement =
    workspace?.engagements.find((item) => item.id === selectedEngagementId) ?? null;
  const selectedOrganization = workspace?.organizations.find(
    (item) => item.id === selectedOrganizationId,
  );

  async function run(action: () => Promise<unknown>, message: string, key: string) {
    setBusy(key);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      await load();
      notifyProjectChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "外部记录操作失败");
    } finally {
      setBusy("");
    }
  }

  async function createOrganization() {
    await run(
      () =>
        createExternalOrganization(
          projectId,
          {
            name: orgName.trim(),
            provider_type: orgType,
            capability_summary: orgCapability.trim(),
            source_refs: [orgSource.trim()],
            verification_state: "verified",
          },
          crypto.randomUUID(),
        ),
      "机构记录已保存；来源与“已核实”仅指当前登记范围。",
      "organization",
    );
  }

  async function createExpert() {
    await run(
      () =>
        createExternalExpert(
          projectId,
          {
            name: expertName.trim(),
            expertise: expertise.trim(),
            public_source_refs: [expertSource.trim()],
            contact_email: null,
            conflict_notes: "未核查",
            state: "candidate",
          },
          crypto.randomUUID(),
        ),
      "专家候选已保存；候选人不是已合作或已背书专家。",
      "expert",
    );
  }

  async function createEngagement() {
    if (!selectedOrganizationId) return;
    await run(
      () =>
        createExternalEngagement(
          projectId,
          {
            organization_id: selectedOrganizationId,
            title: engagementTitle.trim(),
            scope: {
              scientific_question: scientificQuestion.trim(),
              decision_impact: decisionImpact.trim(),
              input_requirements: ["项目材料版本"],
              deliverables: splitItems(deliverableScope),
              method_and_quality: ["方法版本、质控、偏差与原始数据清单"],
              rights_and_confidentiality: ["项目私有；对外动作需单独授权"],
              acceptance_responsibility: "A25记录完整性，A26保留科学异议",
              currency: "CNY",
            },
          },
          crypto.randomUUID(),
        ),
      "外部工作包范围已保存，状态仍为 draft。",
      "engagement",
    );
  }

  async function advanceEngagement(engagementId: string, revision: number, state: string) {
    await run(
      () =>
        transitionExternalEngagement(projectId, engagementId, revision, state),
      `工作包已记录为 ${state}；无授权时执行门会拒绝。`,
      `engagement-state-${engagementId}`,
    );
  }

  async function createQuote() {
    if (!selectedEngagementId || !selectedDocumentId) return;
    await run(
      () =>
        createExternalQuote(
          projectId,
          {
            engagement_id: selectedEngagementId,
            amount: quoteAmount,
            currency: "CNY",
            tax_included: false,
            shipping_included: null,
            assumptions: ["合成测试报价"],
            excluded_work: ["复测费用"],
            valid_until: new Date(Date.now() + 14 * 86400000)
              .toISOString()
              .slice(0, 10),
            document_version_id: selectedDocumentId,
            state: "accepted",
          },
          crypto.randomUUID(),
        ),
      "报价原件和金额已登记；税务、运输及排除项仍需审阅。",
      "quote",
    );
  }

  async function createContract() {
    if (!selectedEngagementId) return;
    await run(
      () =>
        createExternalContract(
          projectId,
          {
            engagement_id: selectedEngagementId,
            quote_id: null,
            title: contractTitle.trim(),
            terms_summary: contractTerms.trim(),
            document_version_id: selectedDocumentId || null,
            state: "draft",
          },
          crypto.randomUUID(),
        ),
      "合同草案已登记；草案不等于已签合同。",
      "contract",
    );
  }

  async function signContract(contractId: string, revision: number) {
    if (!selectedDocumentId) return;
    await run(
      () =>
        transitionExternalContract(projectId, contractId, {
          expected_revision: revision,
          state: "signed",
          internal_signed: true,
          external_signed: true,
          document_version_id: selectedDocumentId,
          reason: "页面登记合成签署文档。",
        }),
      "签署状态已登记；仍需核对真实签署方与法律效力。",
      `contract-sign-${contractId}`,
    );
  }

  async function authorizeEngagement() {
    if (!selectedEngagement) return;
    await run(
      () =>
        createExternalAuthorization(
          projectId,
          {
            engagement_id: selectedEngagement.id,
            action_scope: "仅登记合成测试执行状态，不联系、不委托、不付款。",
            amount_max: "2500.00",
            currency: "CNY",
            expires_at: new Date(Date.now() + 3600000).toISOString(),
          },
          crypto.randomUUID(),
        ),
      "外部执行授权已登记；不会触发真实联系或付款。",
      "external-authorization",
    );
  }

  async function createDeliverable() {
    if (!selectedEngagementId) return;
    await run(
      () =>
        createExternalDeliverable(
          projectId,
          {
            engagement_id: selectedEngagementId,
            title: deliverableTitle.trim(),
            kind: "raw_data",
            expected_items: splitItems(deliverableScope),
            due_at: null,
          },
          crypto.randomUUID(),
        ),
      "交付要求已登记，当前为 expected。",
      "deliverable",
    );
  }

  async function receiveDeliverable(deliverableId: string, revision: number) {
    if (!selectedDocumentId) return;
    await run(
      () =>
        receiveExternalDeliverable(projectId, deliverableId, {
          expected_revision: revision,
          knowledge_version_id: selectedDocumentId,
          manifest: { synthetic_ui_test: true },
          missing_items: [],
          summary: "从知识库选择项目私有版本并登记为外部交付。",
        }),
      "原始交付已登记；接收不等于科学接受。",
      `receive-${deliverableId}`,
    );
  }

  async function reviewDeliverable(deliverableId: string, revision: number) {
    await run(
      () =>
        reviewExternalDeliverable(projectId, deliverableId, {
          expected_revision: revision,
          decision: "accepted",
          reviewer_role: "A25",
          summary: "页面记录的文件完整性复核；不代表独立科学审查。",
          findings: [],
          missing_items: [],
        }),
      "交付完整性已记录为 A25 岗位合同接受。",
      `review-${deliverableId}`,
    );
  }

  async function createRecord() {
    const common = {
      kind: recordKind,
      state: recordKind === "regulatory" ? "official_confirmed" : "information_only",
      title: recordTitle.trim(),
      source_tier: recordKind === "commercial" ? "none" : "user_statement",
      source_title: null,
      source_ref: recordKind === "commercial" ? null : recordSource.trim(),
      checked_at:
        recordKind === "regulatory" || recordKind === "patent"
          ? new Date().toISOString().slice(0, 10)
          : null,
      market: recordKind === "regulatory" ? recordMarket.trim() : null,
      product_scope: recordKind === "regulatory" ? "合成测试产品范围" : null,
      jurisdiction: recordKind === "patent" ? "CN（测试）" : null,
      patent_status: recordKind === "patent" ? "search_only" : null,
      financial_event_type:
        recordKind === "financial" ? "budget" : null,
      amount: recordKind === "financial" ? "0.00" : null,
      currency: recordKind === "financial" ? "CNY" : null,
      commercial_evidence_type:
        recordKind === "commercial" ? "unknown" : null,
      facts: [],
      limitations: ["合成UI记录，不构成真实专业意见"],
      metadata: { ui_submitted: true },
    };
    if (recordKind === "regulatory") {
      common.source_tier = "official";
    }
    await run(
      () =>
        createProfessionalRecord(
          projectId,
          common,
          crypto.randomUUID(),
        ),
      "专业记录已保存；请在详情中核对来源、日期和限制。",
      "record",
    );
  }

  return (
    <div className="pageStack">
      <section className="externalIntro">
        <div>
          <p className="eyebrow">W16 · EXTERNAL RECORDS</p>
          <h2>现实合作与专业证据</h2>
          <p>
            机构、联系人、专家、工作范围、报价、合同、交付和验收分别记录。
            页面操作只写入本地记录；不会联系机构、承诺付款或委托实验。
          </p>
        </div>
        <div className="overviewStatus">
          <StatusPill value="现实动作关闭" tone="warn" />
          <span>记录 ≠ 真实验证</span>
        </div>
      </section>

      {loading && <LoadingPanel label="正在读取外部合作与专业记录…" />}
      {!loading && error && (
        <ErrorPanel message={error} onRetry={() => void load()} />
      )}
      {!loading && notice && <div className="noticePanel">{notice}</div>}

      <section className="surface">
        <SectionHeader
          eyebrow="ORGANIZATIONS & EXPERTS"
          title="机构与专家"
          aside={<span className="mutedText">候选不等于合作</span>}
        />
        <div className="externalFormGrid">
          <div className="externalFormCard">
            <h3>登记机构能力材料</h3>
            <label>
              名称
              <input value={orgName} onChange={(event) => setOrgName(event.target.value)} />
            </label>
            <label>
              类型
              <select
                value={orgType}
                onChange={(event) => setOrgType(event.target.value as ProviderType)}
              >
                {Object.entries(providerLabels).map(([value, label]) => (
                  <option value={value} key={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              能力说明
              <textarea
                rows={3}
                value={orgCapability}
                onChange={(event) => setOrgCapability(event.target.value)}
              />
            </label>
            <label>
              来源引用
              <input value={orgSource} onChange={(event) => setOrgSource(event.target.value)} />
            </label>
            <button
              className="button secondary"
              disabled={busy !== ""}
              onClick={() => void createOrganization()}
              type="button"
            >
              保存机构记录
            </button>
          </div>
          <div className="externalFormCard">
            <h3>登记专家候选</h3>
            <label>
              姓名
              <input
                value={expertName}
                onChange={(event) => setExpertName(event.target.value)}
              />
            </label>
            <label>
              专业范围
              <textarea
                rows={3}
                value={expertise}
                onChange={(event) => setExpertise(event.target.value)}
              />
            </label>
            <label>
              公开来源
              <input
                value={expertSource}
                onChange={(event) => setExpertSource(event.target.value)}
              />
            </label>
            <button
              className="button secondary"
              disabled={busy !== ""}
              onClick={() => void createExpert()}
              type="button"
            >
              保存专家候选
            </button>
          </div>
        </div>
        <div className="externalRecordGrid">
          {workspace?.organizations.map((organization) => (
            <article className="externalRecordCard" key={organization.id}>
              <div className="cardTopline">
                <StatusPill value={organization.verification_state} />
                <span>{providerLabels[organization.provider_type]}</span>
              </div>
              <h3>{organization.name}</h3>
              <p>{organization.capability_summary}</p>
              <small>{organization.source_refs.join(" · ")}</small>
            </article>
          ))}
          {workspace?.experts.map((expert) => (
            <article className="externalRecordCard" key={expert.id}>
              <div className="cardTopline">
                <StatusPill value={expert.state} />
                <span>专家候选</span>
              </div>
              <h3>{expert.name}</h3>
              <p>{expert.expertise}</p>
              <small>利益冲突：{expert.conflict_notes}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="surface">
        <SectionHeader
          eyebrow="ENGAGEMENT"
          title="外部工作包"
          aside={<span className="mutedText">范围、报价、合同、执行和验收分层</span>}
        />
        <div className="externalFormCard wide">
          <div className="twoColumnFields">
            <label>
              合作机构
              <select
                value={selectedOrganizationId}
                onChange={(event) => setSelectedOrganizationId(event.target.value)}
              >
                <option value="">选择已核实机构</option>
                {workspace?.organizations
                  .filter((item) => item.verification_state === "verified")
                  .map((organization) => (
                    <option value={organization.id} key={organization.id}>
                      {organization.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              工作包名称
              <input
                value={engagementTitle}
                onChange={(event) => setEngagementTitle(event.target.value)}
              />
            </label>
          </div>
          <label>
            科学问题
            <textarea
              rows={2}
              value={scientificQuestion}
              onChange={(event) => setScientificQuestion(event.target.value)}
            />
          </label>
          <label>
            预期改变的决定
            <textarea
              rows={2}
              value={decisionImpact}
              onChange={(event) => setDecisionImpact(event.target.value)}
            />
          </label>
          <label>
            应交付内容（分号分隔）
            <input
              value={deliverableScope}
              onChange={(event) => setDeliverableScope(event.target.value)}
            />
          </label>
          <button
            className="button primary"
            disabled={busy !== "" || !selectedOrganization}
            onClick={() => void createEngagement()}
            type="button"
          >
            保存工作包范围
          </button>
        </div>
        {workspace && workspace.engagements.length > 0 && (
          <div className="externalRecordGrid">
            {workspace.engagements.map((engagement) => {
              const next = nextStates[engagement.state];
              return (
                <article className="externalRecordCard" key={engagement.id}>
                  <div className="cardTopline">
                    <StatusPill value={engagement.state} />
                    <span>revision {engagement.revision}</span>
                  </div>
                  <h3>{engagement.title}</h3>
                  <p>{engagement.scope.scientific_question}</p>
                  <small>scope {engagement.scope_sha256.slice(0, 18)}…</small>
                  {next && (
                    <button
                      className="button secondary"
                      disabled={busy !== ""}
                      onClick={() =>
                        void advanceEngagement(
                          engagement.id,
                          engagement.revision,
                          next,
                        )
                      }
                      type="button"
                    >
                      记录状态 → {next}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="surface">
        <SectionHeader
          eyebrow="QUOTE & CONTRACT"
          title="报价与合同"
          aside={<span className="mutedText">未知不填零；草案不等同签署</span>}
        />
        <div className="twoColumnFields">
          <label>
            当前工作包
            <select
              value={selectedEngagementId}
              onChange={(event) => setSelectedEngagementId(event.target.value)}
            >
              <option value="">选择工作包</option>
              {workspace?.engagements.map((engagement) => (
                <option value={engagement.id} key={engagement.id}>
                  {engagement.title} · {engagement.state}
                </option>
              ))}
            </select>
          </label>
          <label>
            报价/合同/交付原件
            <select
              value={selectedDocumentId}
              onChange={(event) => setSelectedDocumentId(event.target.value)}
            >
              <option value="">选择知识库版本</option>
              {documents.map((document) => (
                <option key={document.id} value={document.version_id!}>
                  {document.filename ?? document.title} ·{" "}
                  {formatBytes(document.size_bytes)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="externalActionGrid">
          <div className="externalFormCard">
            <h3>登记报价</h3>
            <label>
              金额
              <input
                value={quoteAmount}
                onChange={(event) => setQuoteAmount(event.target.value)}
              />
            </label>
            <button
              className="button secondary"
              disabled={busy !== "" || !selectedEngagement || !selectedDocumentId}
              onClick={() => void createQuote()}
              type="button"
            >
              登记已接受报价
            </button>
          </div>
          <div className="externalFormCard">
            <h3>合同草案</h3>
            <label>
              标题
              <input
                value={contractTitle}
                onChange={(event) => setContractTitle(event.target.value)}
              />
            </label>
            <label>
              条款摘要
              <textarea
                rows={3}
                value={contractTerms}
                onChange={(event) => setContractTerms(event.target.value)}
              />
            </label>
            <button
              className="button secondary"
              disabled={busy !== "" || !selectedEngagement}
              onClick={() => void createContract()}
              type="button"
            >
              仅保存合同草案
            </button>
          </div>
          <div className="externalFormCard">
            <h3>外部执行授权</h3>
            <p className="mutedText">
              仅登记内部授权，不触发联系、采购或付款。
            </p>
            <button
              className="button secondary"
              disabled={busy !== "" || !selectedEngagement}
              onClick={() => void authorizeEngagement()}
              type="button"
            >
              登记合成执行授权
            </button>
          </div>
        </div>
        <div className="externalRecordGrid">
          {workspace?.quotes.map((quote) => (
            <article className="externalRecordCard" key={quote.id}>
              <div className="cardTopline">
                <StatusPill value={quote.state} />
                <span>{quote.currency}</span>
              </div>
              <h3>{quote.amount ?? "金额未知"}</h3>
              <p>不含税：{quote.tax_included === false ? "是" : "未知"}</p>
              <small>{quote.excluded_work.join(" · ") || "无排除项记录"}</small>
            </article>
          ))}
          {workspace?.contracts.map((contract) => (
            <article className="externalRecordCard" key={contract.id}>
              <div className="cardTopline">
                <StatusPill value={contract.state} />
                <span>v{contract.revision}</span>
              </div>
              <h3>{contract.title}</h3>
              <p>{contract.terms_summary}</p>
              {contract.state === "draft" && selectedDocumentId && (
                <button
                  className="button secondary"
                  disabled={busy !== ""}
                  onClick={() => void signContract(contract.id, contract.revision)}
                  type="button"
                >
                  登记为双方签署
                </button>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="surface">
        <SectionHeader
          eyebrow="DELIVERY"
          title="原始交付与验收"
          aside={<span className="mutedText">接收、审阅、接受分开</span>}
        />
        <div className="externalFormCard wide">
          <label>
            交付标题
            <input
              value={deliverableTitle}
              onChange={(event) => setDeliverableTitle(event.target.value)}
            />
          </label>
          <button
            className="button secondary"
            disabled={busy !== "" || !selectedEngagement}
            onClick={() => void createDeliverable()}
            type="button"
          >
            登记预期原始交付
          </button>
        </div>
        <div className="externalRecordGrid">
          {workspace?.deliverables.map((deliverable) => (
            <article className="externalRecordCard" key={deliverable.id}>
              <div className="cardTopline">
                <StatusPill value={deliverable.state} />
                <span>{deliverable.kind}</span>
              </div>
              <h3>{deliverable.title}</h3>
              <p>
                {deliverable.knowledge_version_id
                  ? "原件版本已登记"
                  : "尚无原始交付"}
              </p>
              <small>{deliverable.missing_items.join(" · ") || "未记录缺件"}</small>
              <div className="cardActions">
                {deliverable.state === "expected" && selectedDocumentId && (
                  <button
                    className="button secondary"
                    disabled={busy !== ""}
                    onClick={() =>
                      void receiveDeliverable(
                        deliverable.id,
                        deliverable.revision,
                      )
                    }
                    type="button"
                  >
                    登记接收
                  </button>
                )}
                {deliverable.state === "received" && (
                  <button
                    className="button primary"
                    disabled={busy !== ""}
                    onClick={() =>
                      void reviewDeliverable(
                        deliverable.id,
                        deliverable.revision,
                      )
                    }
                    type="button"
                  >
                    A25记录接受
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="surface">
        <SectionHeader
          eyebrow="REGULATORY · IP · FINANCE · COMMERCIAL"
          title="专业事实记录"
          aside={<span className="mutedText">保留来源日期与边界</span>}
        />
        <div className="externalFormCard wide">
          <div className="twoColumnFields">
            <label>
              记录类型
              <select
                value={recordKind}
                onChange={(event) => setRecordKind(event.target.value)}
              >
                <option value="regulatory">注册问题</option>
                <option value="patent">专利线索</option>
                <option value="financial">财务事件</option>
                <option value="commercial">商业证据</option>
              </select>
            </label>
            <label>
              标题
              <input
                value={recordTitle}
                onChange={(event) => setRecordTitle(event.target.value)}
              />
            </label>
          </div>
          {recordKind === "regulatory" && (
            <label>
              市场
              <input
                value={recordMarket}
                onChange={(event) => setRecordMarket(event.target.value)}
              />
            </label>
          )}
          {recordKind !== "commercial" && (
            <label>
              来源引用
              <input
                value={recordSource}
                onChange={(event) => setRecordSource(event.target.value)}
              />
            </label>
          )}
          <button
            className="button secondary"
            disabled={busy !== ""}
            onClick={() => void createRecord()}
            type="button"
          >
            保存专业事实记录
          </button>
        </div>
        {workspace && workspace.professional_records.length === 0 ? (
          <EmptyState title="还没有专业事实记录">
            <p>注册、专利、预算/承诺/支出和商业假说会分开保存。</p>
          </EmptyState>
        ) : (
          <div className="externalRecordGrid">
            {workspace?.professional_records.map((record) => (
              <article className="externalRecordCard" key={record.id}>
                <div className="cardTopline">
                  <StatusPill value={record.state} />
                  <span>{record.kind}</span>
                </div>
                <h3>{record.title}</h3>
                <p>
                  {record.market ??
                    record.jurisdiction ??
                    record.financial_event_type ??
                    record.commercial_evidence_type ??
                    "信息范围待核实"}
                </p>
                <small>
                  {record.source_ref ?? "无来源引用"} ·{" "}
                  {formatDate(record.checked_at)}
                </small>
                {record.limitations.map((limitation) => (
                  <em key={limitation}>{limitation}</em>
                ))}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function splitItems(value: string): string[] {
  return value
    .split(/[;；,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
