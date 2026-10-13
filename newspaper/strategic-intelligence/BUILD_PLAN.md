> **V5 历史资料效力（2026-10-14）**：本文件保留当时的细化、模板或审计证据，不能独立改变[唯一现行 V5 主规格](CANONICAL_SYSTEM_SPEC_V5.md)。旧九栏固定百分比、独立连续情报/雷达、旧版“最高”与读者版“继续观察”等如有冲突，以 V5 为准；未冲突的专业方法和案例可按题参考。

# 内参系统｜从V0样刊到正式运行的逐步建设计划（可交给AI实施）

> 这是**技术落地任务清单**，不是当前已经执行的开发日志。用户2026-10-13当前指令是：**先把系统设计、流程、愿景、项目框架和.md完整建好，来源的剩余百余条暂不继续验证**。未来Codex接手先阅读本文件及[DECISIONS.md](DECISIONS.md)，**不得因看到任务就自行执行生产部署或发邮件**。

## 0. 总体技术原则
- 先使**内容样刊达到世界级顾问解释水平**，后使其自动化；不反过来先造复杂系统。
- 初期只实现一条干净、可复现、可审计的Python管道；九栏目使用配置而非九个独立Agent。
- 免费开放来源优先；合法性、内容完整性和费用是独立门禁。
- 124源是当前**信息源候选名单**，不是一次性必须连接完的施工指标；已放弃6源不能自动恢复。源登录、RSSHub、新闻代理和付费服务都只能按需引入。
- 技术栈选型必须做实际样稿/工具benchmark，优先成熟开源项目，固定版本及许可证审计。
- 一个技术步骤提交清晰、可复现的产物和回归测试，不用“全绿”描述掩盖未覆盖的工序。
- 除用户另行批准，所有工作仅在独立`newspaper/strategic-intelligence/`目录开展；禁止修改父级日报cron、workflow、Secrets、发件人、收件人和历史数据库。

## 1. 分阶段成果总图

| 阶段 | 首要目标 | 交付内容 | 停止条件 |
|---|---|---|---|
| P-0设计基线（本轮） | 让未来AI完整理解需求而无需重问 | 愿景、决策、栏目、来源、研究技能、数据契约、期刊规格、模板、质量门禁、追溯矩阵 | 各项历史要求有对应归档，状态明确 |
| P-1内容V0 | 用真实案例证明研究价值 | 六份完整EvidencePacket+六份深度样稿+独立审稿及成本实测 | 机制教学/事实核查不达标先返工 |
| P-2工程MVP | 用冻结样本把流程串通 | 最小source adapter、事件合并、研究/教学、审核、Markdown/HTML渲染、日志 | 端到端无静默错误 |
| P-3周刊Beta | 独立全球发现与试刊 | 小规模免费来源、内部预演、邮件沙箱/干跑、质量/重试/幂等 | 多期预演无阻断，用户批准方可生产 |
| P-4长期档案+年报 | 保存原始判断，重新评估 | 版本化Theme/Thesis/Concept、年报将全年周报与年度新闻源重新综合、历史判断纠错 | 旧版本可以完整回溯 |
| P-5优化扩展 | 用实际瓶颈决定插件化 | 按需OpenBB/pgvector/监控工具/部分多模型 | 优势经benchmark显著、成本可控 |

## 2. 当前P-0工作包（完善设计，不写生产代码）

| 任务ID | 必须完成的项目文档 | 完成门槛 |
|---|---|---|
| P0-01 | README.md + MASTER_BLUEPRINT.md | 命名、六目标、九板块、日报隔离、周报/年报两种产品可独立理解 |
| P0-02 | DECISIONS.md | “已批准/待批/已放弃”分清，124源口径正确 |
| P0-03 | TRACEABILITY_MATRIX.md | 历次关键观点都能找到责任文档 |
| P0-04 | END_TO_END_WORKFLOW.md | 输入/输出、停止、错误、审核、发布状态完整 |
| P0-05 | DATA_CONTRACTS.md | 未来AI可以从字段规范设计schemas和版本化档案 |
| P0-06 | COGNITIVE_ADVISOR_SKILL.md | 有专业机制研究、通俗教学、反方挑战与落地例子 |
| P0-07 | PUBLICATION_SPEC.md | 周报/年报的真实差异、文章深度和中文新闻质量清楚 |
| P0-08 | QA_AND_METRICS.md | 六成果可衡量、质量门禁与回归测试完整 |
| P0-09 | AGENTS.md、模板、CHANGELOG.md | AI开发时不乱改生产与记录 |

此表完成**仅说明设计完成**，不等于已建好任何研究引擎。

## 3. P-1：内容V0样刊验证（最应优先做）

**为什么**：整套内参最独特的竞争力是实证和深度教学，不是RSS数量。没有真正六篇令人信服的样稿，任何云架构都过早。

### 具体任务
- P1-01：从合法公开资料选6个可溯源案例（美股2、创业1、政治1、科技1、宏观1）；不需要全测124来源。
- P1-02：固定每例的`as_of`与真正能访问的资料列表（不能使用未来数据）。
- P1-03：根据DATA_CONTRACTS.md填充EvidencePacket和ClaimRegister，不允许在分析稿里首次出现未经核验的重大事实。
- P1-04：用COGNITIVE_ADVISOR_SKILL.md起草完整顾问讲解；先清楚报道后讲机制、例子、反例和观测指标。
- P1-05：另一审稿工序独立做来源核验、竞争解释、假设错误与AI腔质检。
- P1-06：对6篇评估主张准确度、知识迁移、对普通美股投资/创业者的帮助、反茧房和时间成本；收集真实读者意见。
- P1-07：汇总哪些样本不达标、改写前后对比、模型费用，再冻结V0编辑规则。

### 验收
- 重要事实可回查来源，误写/虚构阻断；
- 读者理解一个额外世界运行机制，而非读完一篇摘要；
- 最强反方不是假想稻草人，缺少证据时明确说未知；
- 样稿专业、完整、简洁有力，中文不像逐词翻译；
- 实测Token与费用记录，不得事后虚构或宣传绝对零错误。

## 4. P-2：最小工程MVP（先冻结数据离线跑通）

**建议未来目录结构**（此处大多尚不存在；不能为了满足结构创建空的几十个脚本）：

```text
newspaper/strategic-intelligence/
  README.md
  MASTER_BLUEPRINT.md / DECISIONS.md / AGENTS.md / BUILD_PLAN.md
  ... existing planning, sources, audits, templates/
  src/
    sources/         # low-level legal RSS/API/HTML clients; source health
    discovery/       # Candidate normalization and topic detection
    events/          # dedup, origin links, event clusters
    research/        # evidence packet and research plan
    advisor/         # domain rules, first principles, teaching examples
    review/          # independent claim checks, quality blocking
    editorial/       # issue selection, narrative consistency
    publisher/       # markdown/html/pdf and optional email draft
    archive/         # append-only thesis and concept cards
    common/          # schemas, time/urls, typed errors, run logging
  configs/
    sections.yaml    # nine columns & weights
    discovery.yaml   # active channels and resource budgets
    models.yaml      # model selection and bounded attempts
  schemas/
    candidate.schema.json / dossier.schema.json / review.schema.json
  templates/
    ARTICLE_TEMPLATE.md / WEEKLY_TEMPLATE.md / ANNUAL_TEMPLATE.md
    THESIS_TEMPLATE.md
  tests/
    fixtures/        # minimal permitted synthetic and real-source samples
    unit/             # parsing, mapping, clocks and dedup
    integration/      # workflow and publication
  migrations/         # later schema changes
  jobs/               # later dry-run and publication outputs (private if sensitive)
```

**建议首版只写五条小组件链**：
1. `ingest`：读取少量合法免费已知RSS/JSON或冻结样本 → Candidate；
2. `normalize`：语言时间和同事件URL关系；
3. `research+advisor`：证据包→专业讲解草稿；
4. `review`：独立引用抽查与PASS/REVISE/BLOCK；
5. `render+archive`：Markdown/HTML + 审计JSON（不发邮件）。

**技术最低限**：Python 3.12+（正式实施时依赖/兼容再核对）、标准库/requests/httpx/Pydantic等经评测再选；可从JSONL/SQLite起步，不需要立即PostgreSQL。所有LLM调用有超时、失败状态、token预算、受污染来源隔离、提示词版本号和脱敏日志。

### 每步验收
每个函数/工序拥有明确输入数据契约及测试，能用冻结样本复现结果；审稿未通过不能进入发布；HTML/PDF缺章失败会阻断；所有用户隐私和密钥不入公共仓库。

## 5. P-3：周刊Beta与可靠性

- P3-01：从当前124源**选择一小组有合法可重复接口的代表源**，并保留其他源为候选；不要求124全接入。
- P3-02：同时覆盖新闻/官方发布/专业研究/科技医学/创业至少若干不同来源类型，减少美国金融垄断。
- P3-03：实现探索队列和每期覆盖审计；人为模拟日报断流、某聚合器故障。
- P3-04：周刊内部预演，不发送真实用户邮箱；出版物可检查文章引用/版本/链接、顾问教学深度。
- P3-05：版本化内容定稿与渲染；邮件通道先做沙箱、幂等和失败注入。
- P3-06：人工审稿与真实反馈，连续多期验证后提出是否需要正式上线；**用户批准**才修改新项目运行计划/收件设置。
- P3-07：每期保存实际工具使用量、模型与API成本，确定适当L1/L2/L3的计算预算。

**回滚**：发布门禁失败时只生成内部报告；邮件送信故障不影响归档；日报永远不应受新周刊的失败影响。

## 6. P-4：年报与长期情报记忆

- P4-01：为Source/Event/Entity/Theme/Thesis/Concept/Edition建立可迁移数据模型。
- P4-02：引入as_of截点、源文合法引用、老版本不可更改、判断增量。
- P4-03：实现跨月相同主题的差异比对、预测结果检查、Brier等指标仅在概率有定义时使用。
- P4-04：以“首席顾问致决策者”为新的总论组织年报，研究企业/技术/政策相互传导。
- P4-05：构建用户关键词召回，能找到当初完整稿件和资料，不把新语言模型的摘要当旧历史。
- P4-06：反茧房审计检查“是否对某个强大机构观点形成路径依赖”。
- P4-07：备份恢复实测、权限审查与长期可读格式（Markdown、JSON、可迁移SQL）。

## 7. P-5：再决定使用哪些成熟GitHub项目

| 候选 | 仅何时引入 | 验证收益 |
|---|---|---|
| RSSHub | 已合法公开来源但无原生RSS，有可测试的源路由 | 减少维护成本，不突破访问限制 |
| Trafilatura/news-please/newspaper4k | 合规抓取网页后确需高质量正文和元数据 | 真实取样比较文章完整度和误提取 |
| GDELT/Media Cloud | 全球候选量与跨语源覆盖有实际瓶颈 | 发现陌生重要信息的增量 |
| GPT Researcher | 现有检索质量/引用不足 | 对六案例的质量与花费明显提升 |
| OpenBB | 金融研究已有明确数据场景和许可 | 数据准确性/来源对照收益 |
| PostgreSQL | JSONL/SQLite已不能支撑跨期存储或并发 | 易维护性、恢复、可审计性 |
| pgvector/GraphRAG | 原生全文/关系查询实测达不到需求 | 关键词和历史准确召回的提升 |
| Langfuse等 | LLM运行日志不满足成本/错误追踪 | 诊断效率、权限及费用合理 |

任何一个选型都需要：替代方案、许可证、维护状态、实际样例、费用、性能、依赖安全、退出方案。不能“GitHub星多”就接入。

## 8. 研发汇报格式：完成一项就留下这些东西

```text
[Task ID] 和目标：
当前已知的真实状态：
拟修改文件及为何需要：
执行后的文件/提交SHA：
测试命令与原始输出：
审核结果：PASS/REVISE/BLOCK
新发现风险与未解决事项：
实际Token、外部API费用：
是否触及日报/邮件/生产：必须NO，除非用户明确额外授权
下一步可执行最小任务：
```

## 9. 实施前必须解决的未批准细节

周报/年报具体发刊时间、最终语言组合、是否每期PDF附件、新产品发件邮箱/收件人、实际预算、LLM与第三方API供应商、GitHub Actions或其它运行基础设施、长报告存储是否私密、数据服务许可及安全策略。可先用**合理可替换的开发默认值**做冻结样稿/内部测试，不因这些未知阻塞规划，但**不得自行部署或外发**。

## 10. 任务优先顺序的最简说明

**先证明6篇文章的内容质量，再用一条可复现的管道生成一期离线周刊，接着完善审稿、历史命题、年报和可靠交付。**

不是“先把所有源都跑起来”、不是“先部署九个Agent”、也不是“先重造日报”。这就是本项目的首要执行顺序。

## 12. V4.0项目最高优先级执行路线（取代旧月报实施任务）

**P0本轮要求**：把[HARD_RULES.md](HARD_RULES.md)、[DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md)、[HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md)、[ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)、[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)全部写清：九栏有具体研究输入、研究顺序、可计算/法定步骤、至少一个实例、失效条件和陌生情境迁移。

**P1真实内容样刊**：每篇真实新闻必须输出LearningUnit，逐领域做实际演算和法律/工程/统计查证。每篇有独立事实编辑、知识专家校验、最强反方审核，退稿意见指到缺步骤或证据。可先用已保存的4个虚构案例只测试逻辑规范，绝不能将其当成6篇真实样刊。

**P2研究工序MVP**：由EvidencePacket→DomainLesson→AdvisorDraft→ReviewDecision→WeeklyEdition的一条可重复流水线；九栏加载不同专业规则，重大事实的证据引用和版权门禁不可跳过；不先部署九个Agent。

**P3周报预演**：从全球公开来源独立发现、按周归档事实/知识/判断/观察指标，输出正式周报Markdown和只供内部检查的HTML；不被已有日报精选列表锁死。

**P4年报预演**：首先实现`build_annual_inventory`（全年实际周报/缺期）和`build_annual_primary_source_inventory`（全年独立全球新闻、机构资料），再建立年度事件时间线、修订数据、错判审计、反常信号和跨领域教案；输出[ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)的`ANNUAL-YYYY`，不得依旧模板生成MONTHLY。

**P5真实运营**：若用户另行授权出版渠道、费用与定时任务才设置独立周报/年报调度。没有授权可以制作离线样刊，但不可邮件发送。

**每阶段的可验证交付**：输入/输出文件+真实例子+具体操作命令（代码完成后）+测试日志+审稿缺陷表+成本+失败和补救；不得以“大师级提示词已完成”替代质量试验。

## V4.1实施计划优先更新：研究顾问与帝师的世界机制发现

在真实六篇样稿测试中先增加一个**不得预告教学主题**的盲测：输入不同板块的真实原始文件与事实，要求研究流程先生成Puzzle、MechanismCandidates、CounterEvidence和ChosenMechanism，再决定需要教什么正规学科原理。九栏专业清单只是工具箱，不是验收“必须提到某词”的清单。每次完成AdvisorAnalysis和LearningUnit后，独立审稿发现错因果/不合现实，返回EvidencePacket重新查。对比仅按照栏目清单强行套理论的旧稿，评价实际解释力、专业正确性、未知与迁移，而不是篇幅或模型评分。逐项工程契约在[OPEN_ENDED_WORLD_MODEL.md](OPEN_ENDED_WORLD_MODEL.md)及[ARCHITECTURE_LOGIC_AUDIT_V41.md](ARCHITECTURE_LOGIC_AUDIT_V41.md)中。生产许可仍未授权。

## V4.2开发先决条件（用户本次暂未要求实际开发）

现在先**冻结杂志设计而非开发整个系统**。以后用户再要求开工时，先打开[ISSUE_BACKLOG.md](ISSUE_BACKLOG.md)按NC编号读取问题、具体复现与验收，不把“已写详细规范”当作VERIFIED。第一批应是把[MAGAZINE_ARCHITECTURE.md](MAGAZINE_ARCHITECTURE.md)的A新闻+B顾问/帝师+C未来核查，用真实公开证据做1—3篇离线样稿；联合研究引擎加载[ADVISOR_MASTER_METHOD.md](ADVISOR_MASTER_METHOD.md)七问三检验，非12套分立模型。来源余下全部生产测试、年度自动生成、邮件和日程**继续等待用户明确批准**。
