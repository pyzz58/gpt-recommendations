# 内参系统（Global Strategic Intelligence · GSI）｜项目唯一入口

> **设计版本：V4.4 · 2026-10-13 · 供用户全面审核、尚非生产验收。**  
> 正式中文名称：**内参系统／内参**；历史名称：全球战略内参。  
> 唯一GitHub目录：\`pyzz58/gpt-recommendations/newspaper/strategic-intelligence/\`；中文快捷入口：[newspaper/内参系统.md](../内参系统.md)。
>
> **没有正式上线：**本目录已完成来源注册、历史少量联网试验、多轮设计.md和文章/杂志模板；**未运行完整全球研究—记者—顾问帝师—审稿—出版生产系统**，也未授权邮件、定时任务或收费服务。不能把V4.4已归档描述为软件功能已经通过测试。

## 0. 先阅读唯一完整现行主规格，禁止各读一份旧版本各行其是

**[CANONICAL_SYSTEM_SPEC_V44.md](CANONICAL_SYSTEM_SPEC_V44.md) — 唯一完整现行主规格（全文、非概念性摘要）**。

本规格已逐环写明：使命与五种能力／三大雷达／九栏目权重／源的合法状态／选文S0—S8九道工序／记者A完整5W1H与报告方法／顾问帝师七问三检验和多因共存／C事件条件推演及2—4开放题／周报内容骨架／年报独立双输入和年度十二工序／六层系统输入输出和失败返工／版本档案／真正QA与发布边界。

用户的最新方向优先于旧历史记录。**该主规格与以下精确SOP配合才构成完整交付，不得拿其中一段代替全文**：

| 从哪里开始 | 需要读取的完整规范及用途 |
|---|---|
| 整本杂志及每篇主文 | [MAGAZINE_ARCHITECTURE.md](MAGAZINE_ARCHITECTURE.md)，[templates/WEEKLY_TEMPLATE.md](templates/WEEKLY_TEMPLATE.md)，[templates/ARTICLE_TEMPLATE.md](templates/ARTICLE_TEMPLATE.md) |
| 新闻影响力、典型性、六要素及机构报告 | [EDITORIAL_SELECTION_AND_REPORTING.md](EDITORIAL_SELECTION_AND_REPORTING.md)：S0—S8，新闻/报告/调查区别，拒稿与审核 |
| 顾问研判和帝师教育方法 | [ADVISOR_MASTER_METHOD.md](ADVISOR_MASTER_METHOD.md)：古代帝师/现代智库参考、七问三检验、双返工；[DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md)：九领域专业事实工具箱，**非封闭课程** |
| 事件后续推演和开放问题 | [SCENARIOS_AND_OPEN_QUESTIONS.md](SCENARIOS_AND_OPEN_QUESTIONS.md)：读者文章C段现行唯一规范 |
| 年报年度研究 | [ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)，[templates/ANNUAL_TEMPLATE.md](templates/ANNUAL_TEMPLATE.md) |
| 最高硬约束和独立审稿 | [HARD_RULES.md](HARD_RULES.md)、[QA_AND_METRICS.md](QA_AND_METRICS.md)、[EDITORIAL_POLICY.md](EDITORIAL_POLICY.md) |
| 用户同意、审批边界、历史方案 | [DECISIONS.md](DECISIONS.md)、[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)、[CHANGELOG.md](CHANGELOG.md) |
| 本轮新审计与未来修复清单 | [ARCHITECTURE_AUDIT_V44.md](ARCHITECTURE_AUDIT_V44.md)、[ISSUE_BACKLOG.md](ISSUE_BACKLOG.md)、[GitHub Issue #43](https://github.com/pyzz58/gpt-recommendations/issues/43) |
| Codex进入项目 | [AGENTS.md](AGENTS.md)，[skills/chief_advisor/SKILL.md](skills/chief_advisor/SKILL.md)，并先读本README与现行主规格 |

## 1. 顾问与帝师、记者与编辑怎么协作？

用户阅读一篇主要文章的**固定顺序**：

**A 记者式翔实新闻/机构报告**：完整5W1H、事实与时间线、完整重要数字/样本方法、不同当事人的观点、出处与未知。**必须单独可读，不能只有几句摘要，也不能复制他人付费全文或伪造采访。**

**B1 顾问研判**：分析现实影响、参与者权力/利益/资金、关键问题、竞争或协同机制、可证事实与尚未知、实际风险和有条件判断。**不能复述A**。

**B2 帝师释理**：由已证重要机制选择应该教的政治/制度/经济/人性/历史/科技知识，用定义、真实案例与反例、具体算例或法律流程讲透，并迁移到陌生现实。**不能换一组辞藻复述B1**。

**C 事件推演与开放性思考**：从B1/B2出发推演不同条件会怎样影响现实（谁行动、经过什么传导、谁受益/受损、何种条件导致推演失败），接2—4个不预设答案、训练换位/反证/跨域理解的问题。**读者版C不再是“继续观察”**；历史Thesis的未来核验留在后台研究档案。

后台只使用一套**顾问—帝师联合认知研究工作台**：七问（事/题/势/人/因/断/道）＋事实/反方因果/知识迁移三检验＋发现错误时退回原证据研究。**现实可能多因共存，研究不承诺唯一“终极规律”。**

## 2. 现行系统只有六层（不是七Agent）

\`\`\`text
L1 独立全球来源发现（合法、免费、跨地域/领域/语言）
 ↓
L2 事件聚类与选文委员会（S0—S8，重要现实影响/典型或突破、去热度偏差）
 ↓
L3 原始事实查证与记者A完整报道（5W1H、机构报告研究方法）
 ↓
L4 一套联合顾问—帝师研究工作台（B1+B2+C、七问三检验、可退回L3）
 ↓
L5 独立事实、专业、因果与版权审稿（PASS/REVISE/BLOCK）
 ↓
L6 主编、周报/年报排版、长期档案与经授权才交付
   ↘ 新证据/纠错回L2—L4
\`\`\`

细节、每层输入输出、失败路由及年度做法请读[CANONICAL_SYSTEM_SPEC_V44.md](CANONICAL_SYSTEM_SPEC_V44.md)第十至十四节。

## 3. 九栏目研究资源权重（不是筛选/篇幅配额）

| 研究领域 | 比重 |
|---|---:|
| 美股与投资 | 25% |
| 全球创业与商业机会 | 25% |
| AI与前沿科技（包括医疗科技） | 12% |
| 全球宏观与金融 | 10% |
| 中国与美国 | 10% |
| 全球政治、军事与地缘战略 | 6% |
| 全球企业与产业竞争 | 5% |
| 全球社会与消费趋势 | 4% |
| 战略研究室 | 3% |

全球医学、科学、人口、制度、社会等重大变化不因不在财经优先名单而被排除；中国和美国关注度较高但全球发现不封闭。**编辑栏目不能预设必须教哪种世界规律**，知识由证据与解释力决定。

## 4. 两种正式出版物与来源真实状态

- **WEEKLY周报**：独立全球发现，不把七份日报拼接，记者完整报道＋顾问＋帝师＋推演；本周主编安排随重要性动态变化，九栏不必均有稿。
- **ANNUAL年报**：**全年真实周报原件＋独立回查全年公开新闻和权威机构原始资料**，重新做年度新研究、历史错判/漏报/数据修订/典型正负案例和跨领域规律；不得拼接52期。月报已废止。
- **来源登记**：124条活跃候选（A116/B8）与6条已弃用记录；有历史抽样，但**124源都不是已标生产验证通过**，AI处理/版权许可尚未逐一核定。本轮禁止继续大批量来源测试。资料详情见[来源注册](SOURCE_REGISTRY.json)、[全球发现SOP](SOURCE_DISCOVERY.md)、[历史访问实验](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)。
- **已有日报**：父目录已有早报及北京时间07:00安排，严格隔离。周报/年报发刊日、生产邮寄、付费数据和其它高成本外部动作都**未获授权**。

## 5. 长期世界理解不是“学过术语”

- 保存完整事实原件、发布日期、研究截点、证据与人物/机构/钱/政策/技术联系；
- 一篇新闻可以教不同领域知识，选择哪条机制必须给证据、竞争解释和反例；
- 任何重要判断要存**原话与原时点**，新资料只能加版本，不得以后见之明覆盖；
- 全球创业雷达需要真实付款、利润/留存/单位经济和最小验证方法，不能把融资/试点当商业模式成功；
- 世界反常信号雷达不能把不寻常数据当秘密阴谋，必须有区分解释所需的原始资料；
- 用户的“你说的对/同意”必须记录**当时认可的详细方法和边界**，修改规范和决策，而非只留一句“用户认可”；
- 未得到读者独立练习结果时，文章最多是\`TAUGHT\`，不能声称\`MASTERED\`。

深入规则：[INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)、[INTELLIGENCE_MEMORY.md](INTELLIGENCE_MEMORY.md)、[HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md)、[REAL_CASES_EVIDENCE_FIRST.md](REAL_CASES_EVIDENCE_FIRST.md)。

## 6. 其它完整资料导航（保留原有细节，不在入口粗略抛弃）

**领域/历史研究**：[MASTER_BLUEPRINT.md](MASTER_BLUEPRINT.md)、[DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md)、[CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md)、[ADVISOR_PEDAGOGY.md](ADVISOR_PEDAGOGY.md)、[COGNITIVE_ADVISOR_SKILL.md](COGNITIVE_ADVISOR_SKILL.md)、[OPEN_ENDED_WORLD_MODEL.md](OPEN_ENDED_WORLD_MODEL.md)、[PUBLICATION_SPEC.md](PUBLICATION_SPEC.md)、[VISION_AND_SCOPE.md](VISION_AND_SCOPE.md)。

**程序/数据/运营**：[END_TO_END_WORKFLOW.md](END_TO_END_WORKFLOW.md)、[DATA_CONTRACTS.md](DATA_CONTRACTS.md)、[TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md)、[BUILD_PLAN.md](BUILD_PLAN.md)、[OPERATIONS_AND_COST.md](OPERATIONS_AND_COST.md)、[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)、[ACCEPTANCE_AND_HANDOFF.md](ACCEPTANCE_AND_HANDOFF.md)。

**历史与来源**：[HISTORY_RECONCILIATION.md](HISTORY_RECONCILIATION.md)、[TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md)、[ARCHITECTURE_LOGIC_AUDIT_V41.md](ARCHITECTURE_LOGIC_AUDIT_V41.md)（**旧七层历史审计，不是现行架构**）、[SOURCE_REGISTRY.md](SOURCE_REGISTRY.md)、[SOURCE_ABANDONED_2026-10-13.json](SOURCE_ABANDONED_2026-10-13.json)、[SOURCE_ACCESS_BLOCKLIST.md](SOURCE_ACCESS_BLOCKLIST.md)、[SOURCE_VERIFICATION_PLAYBOOK.md](SOURCE_VERIFICATION_PLAYBOOK.md)、[SOURCE_TOOLING_RESEARCH.md](SOURCE_TOOLING_RESEARCH.md)、[SOURCE_RECOVERY_AUDIT_2026-10-13.md](SOURCE_RECOVERY_AUDIT_2026-10-13.md)、[V4_RECONCILIATION_AND_QA.md](V4_RECONCILIATION_AND_QA.md)。

**模板**：[templates/ARTICLE_TEMPLATE.md](templates/ARTICLE_TEMPLATE.md)、[templates/WEEKLY_TEMPLATE.md](templates/WEEKLY_TEMPLATE.md)、[templates/ANNUAL_TEMPLATE.md](templates/ANNUAL_TEMPLATE.md)、[templates/THESIS_TEMPLATE.md](templates/THESIS_TEMPLATE.md)；[templates/MONTHLY_TEMPLATE.md](templates/MONTHLY_TEMPLATE.md)仅旧历史废止存档。

## 7. 后续执行与签收

**现在只做设计与历史文档一致性审计**。将来用户明确批准开始制作，先做6篇真实、合规、跨领域的完整A/B1/B2/C样稿与独立核查，再开发最小可重放管道、长期召回、周报与年报离线试跑；审核不足即修正，不先堆复杂软件和Agent。完整未修复项：[ISSUE_BACKLOG.md](ISSUE_BACKLOG.md)及[Issue #43](https://github.com/pyzz58/gpt-recommendations/issues/43)。

**警告**：文章.md齐全≠研究软件存在；四条历史网页访问成功≠124条源生产稳定且有AI许可；Markdown中的QA用例≠真正测试通过；发送给服务商≠最终送达用户；模型输出“你学会了”≠读者真实掌握知识。

**对用户的下一次审核应先解释真实设计问题及仍未证实的运行功能，再经过用户选择进行修改**，不得自行启用投递、收费或现有日报修改。
