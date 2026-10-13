> **V5 历史资料效力（2026-10-14）**：本文件保留当时的细化、模板或审计证据，不能独立改变[唯一现行 V5 主规格](CANONICAL_SYSTEM_SPEC_V5.md)。旧九栏固定百分比、独立连续情报/雷达、旧版“最高”与读者版“继续观察”等如有冲突，以 V5 为准；未冲突的专业方法和案例可按题参考。

# 长期情报、历史判断与知识数据设计

> **V3.0协作提示**：本文件的数据库对象是规划候选；已细化的数据接口、历史版本、权限和最小存储路径见[DATA_CONTRACTS.md](DATA_CONTRACTS.md)与[BUILD_PLAN.md](BUILD_PLAN.md)。长期档案尚未部署。

## 1. 首要原则
**原始证据不可被AI摘要覆盖；历史判断不可用未来信息偷改。** 所有研究都要可追溯到当时可得到的来源。

## 2. MVP 数据对象（建议PostgreSQL起步）
- source_registry: source_id, canonical_name, region, primary_language, source_type, original_site, feed_or_api, ownership_group, availability, access_terms, last_checked, quality_notes。**全球媒体发现动态来源库，不是日报新闻条目列表。**
- discovery_candidates: candidate_id, original_url, aggregator_url, discovery_channel, source_id, region, language, discovered_at, published_at, event_key, verification_status, source_trace。明确“发现渠道”和“事实证据来源”不同。
- coverage_audits: period, regions, languages, independent_media_groups, sampling_misses, source_health, limitations。记录来源和议题盲区。
- sources: source_id, title, publisher, url, license/access, published_at, event_at, collected_at, content_hash, archived_excerpt_or_permitted_copy, language, reliability_notes。
- events: event_id, description, occurred_at, sources[], disputed_facts[], revision.
- entities: entity_id, canonical_name, type(country/company/person/regulator), aliases, links. 不记录未经证实的私人敏感资料。
- themes: theme_id, question, scope, importance, related_entities/events, current_state, next_review_at.
- theses: thesis_id, theme_id, proposition, as_of, known_evidence[], counter_evidence[], assumptions, confidence_method, falsification_conditions, target_horizon, status, version.
- editions: edition_id, type(weekly/annual); daily属于独立外部日报系统，special未获批准, coverage_start/end, cutoff_at, article_refs[], editorial_status, delivery_status, artifact_hash.
- concepts: concept_id, definition, lay_explanation, mechanism, applicability, counterexample, linked_themes, learner_status.
- source_claims: claim_id, text, category(fact/attributed_opinion/inference/hypothesis), source_pointer, corroboration, disputes.
- audit_log: action_id, actor, old/new version pointer, timestamp, reason.

不必V0一次建齐全部表，先使用Markdown+JSON或小型SQL原型验证数据需求；V1逐步结构化。

## 3. 时间纪律
至少区分 occurred_at(事件)、published_at(公开)、collected_at(取得)；thesis保存as_of研究截点和各次版本。允许问“当时知道什么？”并只使用该时点之前可获得的证据。纠错追加记录，不静默覆盖。

## 4. 档案关系
全球媒体/机构来源注册表 → 独立发现候选池 → 核验来源 → 证据主张 → 事件/实体 → 永久主题 → 判断版本 → 周报/年报文章 → 知识原理卡片。单事件可关联多个主题，同一主题跨年更新。保留完整原始讨论/研究笔记及独立可发布稿，不把简略总结视为权威替代。

## 5. 一个长期主题模板
THEME-AI-ENERGY-001：“算力瓶颈是否向电力基础设施迁移？”
研究线索：企业CapEx、电力合同、接网许可、芯片交付、电价与数据中心利用率。每周更新新增证据；出现关键新事实时评估解释变化，并在年报进行年度判断审计；有实质反证则记录判断版本。此为样板，不是现实世界当下判断。

## 6. 预测审核
预测记录命题、时限、事件定义、概率来源/方法、失效条件与核验日期。可量化概率可用Brier Score等方式校准；定性判断事先设定验收标准。禁止用现时结果“回填”历史正确性；允许公开标注失败。

## 7. 反信息茧房长期追踪
为高影响主题保存：立场/利益分布、来源独立性、最强反方解释、主流叙事遗漏项、证据动态。遇到支持既有结论的新材料，也要主动搜索有区分力的反证。

## 8. 检索验收
用户问“去年研究某政策为什么认为会通过”，必须返回当时原始证据、旧推断、后来新增证据、最终结果及修正理由，而非编造连贯总结。无来源的记忆检索标注不足，不猜测。

## 9. 数据治理
版本备份、可迁移开放格式、定期恢复演练、权限最小化、原始来源版权与付费条款遵循、删除/纠错审计；避免将私人投资记录或邮件凭证嵌入公开仓库。

## V4.0历史档案与出版周期的约束

长期档案按**周报（WEEKLY）和年报（ANNUAL）**组织，日报属于独立产品，过去的月报设想已被用户2026-10-13新指示覆盖。年报必须既读取真实周报原稿和当时as_of判断，也独立检索全年新闻/机构源，找出漏掉的事件、错误观点和数据修订；具体步骤见[ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)。

重要概念的学习档案须存ConceptCard、MechanismCard及可选实际练习证据；每项重大判断留旧版和新证据/反方，不许新AI根据结果倒写历史。用户表扬过的原提案和具体方法不归并为一条含糊记忆，应通过[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)与[DECISIONS.md](DECISIONS.md)追溯。
