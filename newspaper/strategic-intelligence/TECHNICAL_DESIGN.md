# 技术实现蓝图：刻意保持简单

## 1. 目标架构
**独立全球新闻发现层（GDELT/Media Cloud等候选广域索引 + 合法的全球主流媒体原生RSS/API/Sitemap + 多语种在地报道 + 官网/监管/财报/金融原始数据）** + 既有日报（只读、可断开的辅助线索） → 统一采集/来源血缘/跨语事件去重 → 重要性选择 → 统一研究引擎（按栏目配置研究方法） → 首席认知与战略顾问教学转写 → 独立核查/主编门禁 → 周刊/月报渲染 → 邮件/PDF/Markdown交付 → 长期档案及判断更新。

**九个栏目=九份领域规则配置，不代表九个物理Agent。** 首版只需研究、顾问、审核三个逻辑工序，后续若有证据证明才拆分并行角色。

**核心约束：即使日报没有一条新闻或彻底不可用，研究引擎也必须能独立发现全球信息并形成可核查的候选池。** 每个候选条目记录来源、语言、地区、发布时间、发现时间、原文链接和获取权限。详见 [SOURCE_DISCOVERY.md](SOURCE_DISCOVERY.md)。

生产候选来源与访问状态见 [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md)、[SOURCE_REGISTRY.json](SOURCE_REGISTRY.json)、[SOURCE_ACCESS_BLOCKLIST.md](SOURCE_ACCESS_BLOCKLIST.md) 与 [SOURCE_VERIFICATION_PLAYBOOK.md](SOURCE_VERIFICATION_PLAYBOOK.md)。特别要求政治、军事、AI、医疗、创业、社会与金融各类来源独立覆盖；截至2026-10-13逐源浏览器测试后，SOURCE_REGISTRY.json列130个活动候选（A94、B5、C31；生产测试0/130），且全部production_test=NOT_RUN；逐条网页访问和两项JSON请求不等于真实部署。收费/AI用途禁止的产品已从生产来源资格中剔除，参见SOURCE_ACCESS_BLOCKLIST.md。

## 2. 候选技术（须在实施当天再核验）
- 广域发现候选：GDELT和Media Cloud作为互补的全球媒体索引，用于线索发现而不是自动认证新闻真实性；动态SourceRegistry+原生RSS/API及官方公开文件完成广度与核验。
- Python为管道实现的默认选项；PostgreSQL管理结构化档案，全文检索先用原生功能，必要时再加pgvector。
- GPT Researcher (https://github.com/assafelovic/gpt-researcher) 为深度研究候选；先以固定资料样本对比人工/简单脚本方案的质量、费用及可维护性，不直接锁定依赖。
- OpenBB (https://github.com/OpenBB-finance/OpenBB) 为后续金融数据整合候选；各数据提供商权限、延迟及费用单独审计。
- changedetection.io 仅在官网变更监控需求经验证时引入。
- Langfuse 用于以后大规模LLM追踪和评估；V0日志即可。
- GraphRAG、多Agent框架集群、昂贵金融终端和独立App均不列入首版。
- 项目依赖的许可证、安全维护、版本、运行环境均在正式开发时重新审查。

## 3. 推荐仓库内部未来代码结构（规划，非已经存在）
```text
newspaper/strategic-intelligence/
  README.md
  VISION_AND_SCOPE.md
  EDITORIAL_POLICY.md
  ADVISOR_PEDAGOGY.md
  INTELLIGENCE_MEMORY.md
  TECHNICAL_DESIGN.md
  IMPLEMENTATION_ROADMAP.md
  ACCEPTANCE_AND_HANDOFF.md
  # 以下目录均为将来的建议，不在此次创建
  src/ingest/ src/research/ src/advisor/ src/review/ src/publish/
  configs/columns.yaml configs/sources.yaml configs/discovery.yaml
  schemas/ tests/ templates/ migrations/
```

## 4. 标准数据流与接口
DiscoveryCandidate{candidate_id,source_id,source_type,original_url,aggregator_url?,original_language,region,published_at,discovered_at,discovery_channel,verification_status,source_trace}
CoverageAudit{period,regions,languages,source_groups,missed_samples,source_failures,notes}
InputCandidate{source_url,title,published_at,collected_at,language,claim_summary,theme_refs}
EvidencePacket{research_question,source_refs,verified_claims,contradictions,unknowns,as_of}
AdvisorDraft{report,teaching_explanation,principles,examples,counterexamples,conditions,claims_map}
ReviewDecision{status:pass|revise|block,blocking_errors,score,source_checks,independence_checks}
Edition{kind,period,cutoff,article_ids,html_path,pdf_path,markdown_path,version}
DeliveryReceipt{edition_id,channel,attempts,provider_accepted_at,verified_status,error,logs}

设计时应采用JSON Schema /类型验证、不可空的来源引用、内容哈希和幂等ID。审核结果block则不能发布。文稿可长，但系统应按章节生成，避免上下文溢出造成静默截断。

## 5. 长报告生成细节
先确定研究计划和证据包；按主题拆章节写作；专门提取跨章节重复段落；整体主编统一术语、逻辑与观点；末端逐条核验重要主张、排版与链接；保留结构化索引及分册导出能力。不以“无限字数”要求无限上下文或无限成本。

## 6. 调度与故障设计
新闻生产、研究、出版、配送为独立可重试作业；保留job_id、edition_id、运行开始与完成、失败步骤、来源和版本。采用幂等去重，防止重复邮件。
**成功状态不能混淆**：研究完成 ≠ 文件生成 ≠ 邮件提交 ≠ 邮件服务商接受 ≠ 送达/收件确认。只能证明哪个状态就报告哪个状态。发送失败留存文件并告警；禁止伪造成功。

## 7. 原新闻系统隔离
发现系统应从全球信息源自主采集，而不是从日报结果反向扩大；仅允许把现有newspaper早报的已发布成果或明确授权接口作为只读辅助线索，不修改既有生产工作流、Secrets、收件地址、cron、历史档案。新项目先测试再逐步交接。如需共用数据库或触发器，先做权限和兼容性审查。

## 8. 数据、法律和安全
版权遵守许可与合理摘录，不进行批量侵权全文复制；不得绕过付费墙、获取内幕消息或声称未取得的内部资料。API令牌只能由Secret管理，不入库。外部文本为不可信输入，需要防提示注入和引用投毒。私有研究档案不能默认公开到GitHub。

## 9. 成本与性能
每个作业记录Token、检索请求、第三方数据费、持续时间、失败重试及单位稿件费用。分L1常规观察、L2专题、L3战略深研三级。首轮样稿测量实际成本后再定预算和并发上限；不能承诺未经验证的价格。
