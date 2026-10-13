# 内参系统｜数据模型、接口契约、状态机与版本治理

> 这是未来AI可直接据此创建 `schemas/` JSON Schema、Python dataclass/Pydantic模型及存储表的规范。**文档只设计，不代表数据库已经创建或生产采集已经启动。** 每个对象都有schema_version、id、created_at、as_of等必要的审计信息；具体SQL名称可实现时统一。

## 1. 数据层次：避免把所有东西塞进一张新闻表

```text
SourceRegistry ──> DiscoveryCandidate ──> EventCluster
                                                |
                                            EvidencePacket ──> Claim
                                                |              |
                                                v              v
Theme ──> ThesisVersion ──> ResearchDossier ──> AdvisorDraft
                |                               |
                +----> ConceptCard              v
                                          ReviewDecision
                                                |
                                                v
                                         Edition / Article
                                                |
                                                v
                                          DeliveryReceipt
                                                |
                                   RunLog / AuditLog / CoverageAudit
```

**定义区分**：
- Source = 发布机构或数据提供商，可有多个Feed/产品。
- Candidate = 一次发现的URL/研究条目，不意味着已确认真实。
- Event = 现实事件，不等于单篇媒体报道；可有多个不独立的转引。
- Claim = “某年某月某机构发布某统计数字”这样可逐条追溯的可证主张。
- Evidence = 支持/反对Claim的具体来源片段、位置和时间；不能把模型解释当证据。
- Theme = 多个事件横跨年份构成的研究主题。
- ThesisVersion = 在特定as_of时点关于主题的可检验判断；历史版本不可悄悄覆盖。
- Concept = 能从多个新闻迁移使用的底层知识原理。
- Edition = 最终周刊或月报的唯一发布版本，不是研究状态。
- DeliveryReceipt = 渠道对投递动作的逐级反馈，不伪造最终送达。

## 2. SourceRegistry（唯一活跃账本）

**规范实物**：`SOURCE_REGISTRY.json`（目前124条活跃A/B来源），`SOURCE_ABANDONED_2026-10-13.json`（6条用户明确弃用）。

建议规范：
```json
{
  "source_id": "SRC-082",
  "canonical_name": "CBS News World",
  "type": "media",
  "regions": ["US", "global"],
  "languages": ["en"],
  "editorial_domains": ["politics", "global"],
  "url": "https://www.cbsnews.com/world/",
  "channels": [
    {"url": "https://www.cbsnews.com/world/", "type": "html", "last_check": null}
  ],
  "availability": "PUBLIC_PAGE",
  "free_subset": true,
  "license_ai_processing": "UNREVIEWED",
  "license_republication": "UNREVIEWED",
  "status": "CANDIDATE_ACTIVE",
  "historic_audit_ref": "audits/random-four-20261013.json",
  "production_test": "NOT_RUN"
}
```
这是**建议未来统一的数据契约**，并非当前 `SOURCE_REGISTRY.json` 的实际字段快照。不要直接拿此示例覆盖既有源账本。当前ID保留，不因6条移出而重新编号；保留废弃来源ID历史，禁止跨年ID重用。

字段必须区别 `source_availability`、`channel_test_status`、`content_rights`、`production_enabled`。网页HTTP200不自动改变后两者。

## 3. DiscoveryCandidate

```json
{
  "schema_version": "1.0",
  "candidate_id": "CAN-20261013-00001",
  "discovered_at": "2026-10-13T02:00:00Z",
  "published_at": "2026-10-12T18:00:00Z",
  "source_id": "SRC-XXX",
  "discovery_channel": "rss|api|manual_search|aggregator|daily_aux",
  "original_url": "https://example.org/...",
  "normalized_url": "https://example.org/...",
  "aggregator_url": null,
  "original_language": "en",
  "regions": ["US"],
  "domains": ["investing"],
  "headline_original": "...",
  "headline_translation": null,
  "abstract_or_allowed_excerpt": "...",
  "original_text_storage_rights": "none|excerpt|licensed",
  "verification_status": "lead_only",
  "event_key": null,
  "content_hash": null,
  "as_of": "2026-10-13T02:00:00Z"
}
```
**外部检索正文可能是不可信指令输入**，不能让网页里的文字覆盖系统规则、密钥管理或调用其他工具。

## 4. EventCluster和SourceLineage

```text
EventCluster {
 event_id, event_time, time_precision, primary_description,
 entity_ids[], candidate_ids[], originator_refs[], disputed_facts[],
 updates[], original_languages[], latest_changed_at, review_status
}
SourceLineage {
 article_id, source_id, origin_article_id, syndication_group_id,
 cited_origin_url, independence_level [original/reporting/quoted/unknown],
 provenance_confidence, notes
}
```
当十家媒体统一转载一家通讯社，只算一条原发链；不同记者独立采访、不同数据独立测量则分开登记。不要只用URL相同判断“同一篇新闻”。

## 5. ResearchDossier、EvidencePacket和Claim

```json
{
  "schema_version": "1.0",
  "dossier_id": "RES-20261013-001",
  "topic_id": "TOP-...",
  "question": "原始研究要回答什么？",
  "as_of": "2026-10-13T03:00:00Z",
  "claims": [
    {
      "claim_id": "CLM-001",
      "claim_text": "一个具体可检验命题",
      "kind": "verified_fact|attributed_statement|inference|hypothesis|forecast",
      "evidence": [
        {"source_id": "SRC-XXX", "url": "https://example.org/source",
         "pointer": "page 4 / paragraph 2", "published_at": "...",
         "observed_at": "...", "relation": "supports|refutes|context",
         "independent_origin": true}
      ],
      "verification": "verified|corroborated|disputed|unverified",
      "units": null,
      "assumptions": [],
      "editorial_restrictions": []
    }
  ],
  "strongest_alternative": ["..."],
  "missing_evidence": ["..."],
  "contradictions": ["..."],
  "key_terms_to_teach": ["..."],
  "historical_theme_refs": [],
  "source_license_report": "unreviewed|approved_subset|restricted",
  "report_ready": false
}
```

**门禁**：凡属核心事实，无可定位证据指针或数字没有口径，不能设置report_ready=true；争论方表述需要明确是谁声称，不必强迫一方主张被另两篇媒体“证实”。

## 6. TopicDecision和研究预算对象

```text
TopicDecision {
 topic_id, cluster_ids[], why_now, question, section_ids[],
 queue(core|exploration), score_breakdown{}, evidence_feasibility,
 depth(L1|L2|L3), decision(SELECT|WATCH|REJECT|ESCALATE),
 competing_hypotheses[], editor_reason, as_of
}
ResearchBudget {
 topic_id, planned_depth, token_cap, search_cap, third_party_cost_cap,
 spent_actual, retry_count, stop_reason, human_override_id
}
```
权重、Token和搜索预算均来自未来配置；**尚未批准实际每期成本金额**。发生预算不足要停止/降级研究，不能悄悄降成空洞摘要并报告“已完成”。

## 7. AdvisorDraft、ReviewDecision、Edition

```text
AdvisorDraft {
 draft_id, dossier_id, version, article_markdown_ref,
 factual_reporting_sections[], explanation_sections[], pedagogic_concepts[],
 example_calculations[], alternative_explanations[],
 limitations[], forecast_conditions[], transferable_skill[],
 sentence_claim_map[], source_attribution[], created_at
}
ReviewDecision {
 review_id, draft_id, draft_version, reviewer_id_or_model_version, timestamp,
 status(PASS|REVISE|BLOCK), blocking_errors[], scoring_breakdown{},
 sampled_claims[], counterargument_check[], citation_check[],
 required_revision[], rationale
}
Edition {
 edition_id, kind(WEEKLY|MONTHLY|SPECIAL), period_start, period_end,
 knowledge_cutoff_at, version, article_ids[], section_order[],
 editor_letter_ref, canonical_markdown_ref, html_ref, pdf_ref,
 source_index_ref, quality_status, rendered_hash, publication_state
}
```
`ReviewDecision`是**独立审核工序**，不是起草工序传入一个永远“通过”的标志。每次修改稿件version变化，原审核结果不再无条件有效。

## 8. DeliveryReceipt、RunLog和状态机

```text
RunLog {
 job_id, workflow_version, step_name, attempt, started_at, finished_at,
 input_ref, input_hash, output_ref, output_hash, model, token_usage,
 search_calls, external_cost, status, failure_reason
}
DeliveryReceipt {
 receipt_id, edition_id, edition_version, channel,
 recipient_group_token, idempotency_key, attempted_at,
 provider_accepted_at?, provider_message_id?, delivery_confirmed_at?,
 state(DRY_RUN|QUEUED|ATTEMPTED|ACCEPTED|CONFIRMED|FAILED),
 error_code?, evidence_pointer?
}
```
- 不往公开仓库写真实邮件地址/投资账户/私有令牌，群体标识用安全替代ID。
- `ACCEPTED`≠`CONFIRMED`；如果发件服务不提供收件确认，则明确`ACCEPTED`，不要推断最终到达。
- `idempotency_key`至少由edition_id、version、channel、recipient_group构成，重试不能再次发送同一成功版本。
- 可以审计“编辑通过、文件生成、发件调用、服务商接受、送达可核实”每个环节。

## 9. Theme、ThesisVersion和ConceptCard

```text
Theme { theme_id, canonical_question, domain_tags[], entity_ids[], status,
        related_event_ids[], owner, next_review_at, created_at }
ThesisVersion { thesis_id, version, theme_id, proposition, as_of,
                supporting_claim_ids[], opposing_claim_ids[], assumptions[],
                horizon, observable_trigger, confidence_kind, confidence_value?,
                alternatives[], outcome?, changed_reason?, supersedes? }
ConceptCard { concept_id, concept_name, formal_definition, plain_language,
              mechanism, required_preconditions[], counterexamples[],
              examples[], linked_dossier_ids[], linked_thesis_ids[],
              taught_at[], independently_mastered_at?, mastery_evidence? }
```
概率值非必须，若有需标主观/模型/统计方法，不允许未经方法说明写“75%概率”。概念仅“出版过”≠读者已掌握。

## 10. 时间、版本和来源保存规则

- `occurred_at`：事件实际发生；`published_at`：公开发布；`collected_at`：我们采集；`as_of`：写论断时知识截点；不同时间不能混用。
- `created_at`与`updated_at`只是数据库操作时间，不得替代历史事件时间。
- 实现中所有外部时刻优先存ISO8601带时区，UTC权威；媒体本地日期显示需标时区。
- 保存文件哈希、引用路径、版本号、来源可重新定位的唯一ID；观点更改采用append-only版本，不静默重写。
- 对版权不能归档原文全文时保留URL、元数据、授权短摘、来源定位与自己原创研究，明示无法永久再现全部正文的限制。
- 旧源失效、文章更正：新证据与更正记录追加到历史主题，保留当时版本。

## 11. 存储演进（推荐而非已实现）

- **V0**：Markdown/JSON JSONL + 文件目录和Git版本，少量真样稿；
- **V1**：SQLite或PostgreSQL（根据数据量与共享运维条件），全文搜索优先；
- **V2**：数据库迁移、主题/命题关系、许可控制、备份恢复、PDF/HTML归档；
- **V3**：当普通SQL/全文搜索表现不够时再加pgvector或知识图谱。

**权威来源真相**：SOURCE_REGISTRY.json是当前活跃源记录；DECISIONS.md记录用户确认的意图；已发布Edition的原始定稿和ThesisVersion不可由新AI总结覆盖。
