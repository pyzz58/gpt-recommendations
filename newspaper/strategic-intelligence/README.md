# 内参系统（Global Strategic Intelligence · GSI）

> **正式中文名称：内参系统**｜兼容简称：内参｜历史名称：全球战略内参
>
> **当前设计基线：V4.1 · 2026-10-13**。已完成总体项目框架、需求归档与设计文档；**未完成研究引擎、周报/年报自动生成、知识数据库、正式调度和邮件推送**。
>
> GitHub唯一规范目录：`pyzz58/gpt-recommendations/newspaper/strategic-intelligence/`，中文快速入口：[newspaper/内参系统.md](../内参系统.md)。

## 1. 此系统到底是什么？

内参系统不是每日新闻的增强摘要，而是一套**独立全球发现 → 可核实研究 → 第一性原理与费曼式深度教学 → 反方审核 → 周报/年报 → 长期可追溯的世界判断档案**的私人认知和战略研究系统。

目标不是简单知道头条，而是像获得有严谨来源和独立判断的一流战略顾问长期服务一样，**真正认识世界如何运作，减少信息茧房，形成能迁移的新理解**。参照顶级家族办公室的严谨研究标准，但不假装有内幕、私人数据库或未授权一手消息。

重点是**美股投资和普通人/小团队创业**，同时保持对全球政治、军事、经济、AI、医学、社会、产业和重要突发事件的独立观察。

## 1.1 最重要的新增：**内参必须“把世界的运行机制教会读者”**

原有几个“第一性原理/费曼/苏格拉底”术语严重不足以指导真实研发。根据用户此前明确认可的详细设计，V3.1现要求：

- **[DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md)**：读者要掌握什么、十一道实际教学工序、政治制度/美股/创业/科技医学的系统知识路径、费曼三遍讲解、反证、陌生案例迁移、跨期学习与真实验收；不得只给新闻加短点评。
- **[CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md)**：完整示范政治人物争论背后的**议会、行政、司法、预算、党纪、选举、否决点与博弈**；AI医疗行政创业背后的**使用者/买方、真实节省、毛利、CAC、LTV、留存、采购、监管与规模壁垒**；并有美股和技术商业化实例。所有数字场景都标注为教学假设，真正出刊须换成事实核查后的真实资料。
- **[INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)**：完整保留**新闻机构敏锐度、情报机构连续性、投资研究深度、战略咨询分析方法、家族办公室长周期视角**五种职责，以及**战略判断追踪器、全球商业机会雷达、世界结构变化与反常信号雷达**的字段、触发和审查规则。

这三份为**强制阅读的核心设计文档**，不是可跳过的补充说明。研判的最终质量标准：一个月后读者遇见陌生政治争论、股票估值或创业机会时，能独立提出关键问题、判断证据和反例，而不是复述本周报告的结论。实现仍未开始。

## 2. 用户明确确定的六项成果

1. 懂世界：能解释陌生事件背后的制度、经济、产业、科技和权力约束。
2. 独立思考：自己衡量事实、竞争解释、证据强弱与失效条件。
3. 提升美股投资和创业能力：懂预期差、现金流、风险、PMF、CAC、LTV及商业现实。
4. 长期积累：几年后依关键词召回**当时的完整材料、判断及后来变化**。
5. **跳出信息茧房**：主动接受可靠的陌生议题、不同地区和最强反方，拒绝迎合/伪均衡。
6. **深度、真实、一线、前沿地认识世界**：原始政策、真实统计、财报、专业公开研究、可信现场与工程/医学证据，而不是无根据的神秘叙事。

如何衡量见 [QA_AND_METRICS.md](QA_AND_METRICS.md)。

## 3. 九个研究栏目（初始研究资源权重，不是刊发篇数配额）

| 栏目 | 比重 | 栏目 | 比重 |
|---|---:|---|---:|
| 美股与投资 | 25% | 全球创业与商业机会 | 25% |
| AI与前沿科技 | 12% | 全球宏观与金融 | 10% |
| 中国与美国 | 10% | 全球政治与地缘战略 | 6% |
| 全球企业与产业竞争 | 5% | 社会与消费趋势 | 4% |
| 战略研究室 | 3% | **总计** | **100%** |

资源权重是长期优先级，不能把非热门但影响世界的重要医疗、军事、政治和社会事件在发现阶段排除。九栏**不代表九个独立Agent**。

## 4. 整体逻辑和两种出版物

```text
全球免费公开新闻/投行资管/四大/咨询/政府/军工/医疗/AI/创投/原始数据
                     + [已有日报：可选只读线索，不是前置]
                                     |
                              独立广域发现
                                     |
                   同事件去重 + 来源血缘 + 反茧房检查
                                     |
                        重要性/证据筛选 + 分层预算
                                     |
                      专业研究员生成可查证EvidencePacket
                                     |
              首席认知与战略顾问：原理、案例、反例、认知迁移
                                     |
                   独立事实/因果/强反方审校和主编质量门禁
                                     |
                     每周深度周报  /  每年综合战略年报
                                     |
                文件/交付状态/长期主题/命题版本/原理知识归档
```

周报是独立全球研究而不是7份日报拼接；年报以本年度周报及**全年独立新闻源、机构原始研究**为双重依据，重新进行长期命题审计和综合研究，绝不把全年周报原样合订。版式和“首席顾问致决策者”参见 [PUBLICATION_SPEC.md](PUBLICATION_SPEC.md)。

## 5. 当前来源策略与已验证状态

- **当前活跃源：124条**（A公开入口116、B仅免费部分8），权威机器登记为 [SOURCE_REGISTRY.json](SOURCE_REGISTRY.json)，可读表为 [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md)。
- 用户明确放弃6条难以在当前条件下取得合规内容的来源，[历史记录](SOURCE_ABANDONED_2026-10-13.json)；**不得自行恢复或继续钻研**。
- 已经对一些RSS/JSON做过四轮隔离GitHub Actions专项联网测试；随后用户决定只需从124条随机抽3—4条作采集可行性测试；实际随机4条HTTPS均200，**其中3条读取新闻/研究页面、1条仅API说明文档**。[原始测试结果](audits/random-four-20261013.json)。
- **现在不继续测试余下约120条来源**，把工作重心放到研究质量、架构设计与后续内容样刊。
- **生产来源的连续稳定性和AI内容处理版权许可均未全面核验；正式自动采集上线为0条。**
- 所有来源都必须符合“免费合法访问”和特定处理/转载许可；有商业付费或明确AI处理禁止的产品见 [SOURCE_ACCESS_BLOCKLIST.md](SOURCE_ACCESS_BLOCKLIST.md)。

## 6. 整套项目文档导航

### A. 最优先的V4.1硬性规则（任何AI必读）
- **[OPEN_ENDED_WORLD_MODEL.md](OPEN_ENDED_WORLD_MODEL.md)** — 从真实现象跨学科发现机制，顾问回答现实问题、导师教授可迁移的世界规律，九栏不应成为封闭教学清单。
- **[ARCHITECTURE_LOGIC_AUDIT_V41.md](ARCHITECTURE_LOGIC_AUDIT_V41.md)** — 七层结构、15道工序、实际GitHub资产、严重缺口和修复路线。
- **[HARD_RULES.md](HARD_RULES.md)** — 绝对禁止概念性总结；必须实际步骤/证据/算例/反证/迁移/验收；用户表扬与认可须具体留档；周报+年报是唯一新正式产品。
- **[DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md)** — 九栏目不同学科的逐步深度教学、具体证据、负例与阻断条款。
- **[HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md)** — 利益/权力/信息/人性及中国传统文化的证据化应用。
- **[REAL_CASES_EVIDENCE_FIRST.md](REAL_CASES_EVIDENCE_FIRST.md)** — 基于可核查公开资料的三个真实历史教学案例：2013美国政府拨款停摆、Duolingo 2024年SEC财务披露、伯克希尔2024年10-K。
- **[ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)** — 全年周报+年度独立原始新闻源，十二步生产综合年报。
- **[REAL_CASES_EVIDENCE_FIRST.md](REAL_CASES_EVIDENCE_FIRST.md)** — 以可核实的2013美国政府停摆、Duolingo 2024 SEC报表、伯克希尔2024年报真正示范事实→制度/会计根因→知识与迁移。
- **[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)**、**[HISTORY_RECONCILIATION.md](HISTORY_RECONCILIATION.md)** — 用户认可的详细保存及可回查历史审计。
- **[V4_RECONCILIATION_AND_QA.md](V4_RECONCILIATION_AND_QA.md)** — 已核查文档、现行决策、30份核心Markdown相对链接检查及未完成的真实实施验证。

### B. 先读这六份（快速准确理解项目）
1. [MASTER_BLUEPRINT.md](MASTER_BLUEPRINT.md) — **正式完整总纲**、六项成果、九栏目、十二步、双刊与边界。
2. [DECISIONS.md](DECISIONS.md) — **用户明确同意、尚未批准及已放弃**的各项决定，防止误部署。
3. [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) — **50项历史讨论的需求到文档映射**，防遗漏。
4. [END_TO_END_WORKFLOW.md](END_TO_END_WORKFLOW.md) — **从独立发现到最终归档的全流程工序、产物与错误出口**。
5. [BUILD_PLAN.md](BUILD_PLAN.md) — **分阶段可执行开发任务**，先六案例样刊后工程化。
6. [AGENTS.md](AGENTS.md) — **Codex/AI交接和权限边界**。

### C. 产品、认知教学与质量
- **[DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md) — 深度教学目标、具体十一道机制、领域知识路径、迁移和回访。**
- **[CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md) — 政治、医院AI商业、美股及科技四份详解教学案例。**
- **[INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md) — 五种研究能力、三种雷达与专业岗位分工。**
- [VISION_AND_SCOPE.md](VISION_AND_SCOPE.md) — 六项目标、九栏及已有出版原则。
- [EDITORIAL_POLICY.md](EDITORIAL_POLICY.md) — 严肃新闻、机构利益、反茧房与审稿约束。
- [ADVISOR_PEDAGOGY.md](ADVISOR_PEDAGOGY.md) — 四种教学方法和领域知识的早期规范。
- [COGNITIVE_ADVISOR_SKILL.md](COGNITIVE_ADVISOR_SKILL.md) — 可实际交付研究/撰稿任务的“首席顾问”细化规则。
- [PUBLICATION_SPEC.md](PUBLICATION_SPEC.md) — 周报/年报的内容形态、中文写作、长稿与编辑质量。
- [QA_AND_METRICS.md](QA_AND_METRICS.md) — 100分审稿、硬阻断、六能力检验与测试清单。
- [skills/chief_advisor/SKILL.md](skills/chief_advisor/SKILL.md) — 面向未来Codex的项目内部简化Skill。

### D. 数据、技术、安全及工程
- [DATA_CONTRACTS.md](DATA_CONTRACTS.md) — Source/Event/Claim/Evidence/Thesis/Edition/Delivery数据契约。
- [INTELLIGENCE_MEMORY.md](INTELLIGENCE_MEMORY.md) — 原件保真、跨年召回、知识卡与历史修正。
- [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) — 技术架构和候选成熟开源组件。
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — 实际GitHub文件与**尚未建立的未来src/configs**区分。
- [OPERATIONS_AND_COST.md](OPERATIONS_AND_COST.md) — 模型Token、授权成本、重试、隔离、回滚与生产门禁。
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) — 旧阶段实施规划，现以BUILD_PLAN为更新路线。
- [ACCEPTANCE_AND_HANDOFF.md](ACCEPTANCE_AND_HANDOFF.md) — 原有独立审校及交接规则。
- [CHANGELOG.md](CHANGELOG.md) — 设计/来源历史版本记录。

### E. 来源注册与历史核查（本阶段暂停）
- [SOURCE_DISCOVERY.md](SOURCE_DISCOVERY.md) — 全球独立发现、双队列、来源多元。
- [SOURCE_REGISTRY.md](SOURCE_REGISTRY.md) / [SOURCE_REGISTRY.json](SOURCE_REGISTRY.json) — 124个活跃来源。
- [SOURCE_ABANDONED_2026-10-13.json](SOURCE_ABANDONED_2026-10-13.json) — 6个已弃来源。
- [SOURCE_ACCESS_BLOCKLIST.md](SOURCE_ACCESS_BLOCKLIST.md)、[SOURCE_TOOLING_RESEARCH.md](SOURCE_TOOLING_RESEARCH.md)、[SOURCE_VERIFICATION_PLAYBOOK.md](SOURCE_VERIFICATION_PLAYBOOK.md) — 权限/开源工具/采集测试规范。
- [SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md](SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md)、[audits/random-four-20261013.json](audits/random-four-20261013.json) — 真实测试历史；**不是已部署系统**。

### F. 实际内容制作模板
- [templates/ARTICLE_TEMPLATE.md](templates/ARTICLE_TEMPLATE.md) — 文章及来源核验模板。
- [templates/WEEKLY_TEMPLATE.md](templates/WEEKLY_TEMPLATE.md) — 深度周刊编辑框架。
- **[templates/ANNUAL_TEMPLATE.md](templates/ANNUAL_TEMPLATE.md)** — 年报完整编辑/证据/年度错判审计模板。
- [templates/MONTHLY_TEMPLATE.md](templates/MONTHLY_TEMPLATE.md) — 历史废止的月报模板，仅旧版追溯；不使用。
- [templates/THESIS_TEMPLATE.md](templates/THESIS_TEMPLATE.md) — 长期研究及可追溯历史判断版本。

## 7. 开始实施的正确顺序

**第一步**：必须先阅读深度学习引擎、政治/创业实例与五种能力研究模式，再阅读全文、检查决策台账与追溯矩阵；
**第二步**：用**6个真实、可核验的议题**制作完整深度样稿（美股2、创业1、政治1、AI科技1、宏观1），用户审定研究质量；
**第三步**：把证据包→顾问讲解→独立审稿→周刊Markdown/HTML串成可复现的最小流程；
**第四步**：才考虑全球来源的小规模正式接入、周报内部预演、年报与长期知识数据库；
**第五步**：经实际质量/运行/预算/权限验收和用户批准，再进入新刊物生产投递。

关键判断：**我们建设的是一位能够教会你理解世界的长期认知与战略顾问，不是一台高频堆砌摘要的新闻机器**。

## 8. 严格的授权和状态边界

- **已有每日早报**的源代码、运行、北京时间07:00推送、邮箱、Secrets和生产Actions一概不因本项目设计而改变。
- **内参系统没有获得新的周报/年报上线、真实邮件外发、定时任务、付费API或私有存储部署授权**。
- Markdown完成=设计归档；一些来源单次HTTP成功≠124源生产可用；构建了Skill.md≠AI顾问程序已集成；写了栏目权重≠已经发行内刊。
- 有冲突先看DECISIONS.md和最新用户明确指令；历史报告依旧保存，不重写旧来源测试记录。

> **项目下一项真正的研发门槛**：先交付六份有可靠证据、深度机制教学、强反方、优质中文新闻写作的样稿，并取得用户对内容质量的真实判断。之后才决定进一步技术实现。

## V4.1追加：顾问和导师不是栏目附属的固定概念讲解机

现在要求：先用事实、历史变化与竞争机制找到真正解释现实的底层规律，再决定应教什么知识。九栏只指导来源及专业查证，**跨栏目教学完全允许**，但任何解释均需准确证据、因果边界与反证。机制发现M01—M12和两个角色的实际交接见[OPEN_ENDED_WORLD_MODEL.md](OPEN_ENDED_WORLD_MODEL.md)。

现状、证据边界、七层/15工序逻辑总图与缺口见[ARCHITECTURE_LOGIC_AUDIT_V41.md](ARCHITECTURE_LOGIC_AUDIT_V41.md)。本轮规划升级未启用新采集、模型、邮件和定时任务，日报隔离不变。
