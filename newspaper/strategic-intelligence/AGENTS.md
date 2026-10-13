# 内参系统｜Codex / ChatGPT / AI 开发协作规则

> 文件范围：`newspaper/strategic-intelligence/`。正式中文名称为**内参系统**。你正在阅读的是设计与研发护栏，不是自动启动任务的授权。本文件作为本目录未来AI/Codex的工作指引，若用户最新明确指令有冲突以最新用户指令为准，但不得由AI自行假设用户同意了部署。

**V4.2首读：[ADVISOR_MASTER_METHOD.md](ADVISOR_MASTER_METHOD.md)（七问三检验＋多因共同作用及诚实未知）、[MAGAZINE_ARCHITECTURE.md](MAGAZINE_ARCHITECTURE.md)（A新闻→B顾问帝师→C来源与未来核验）、[ISSUE_BACKLOG.md](ISSUE_BACKLOG.md)（工程问题暂只登记）。**

**V4.1历史阅读要求：[OPEN_ENDED_WORLD_MODEL.md](OPEN_ENDED_WORLD_MODEL.md)（由真实现象开放发现机制，栏目不能锁定教学内容）以及[ARCHITECTURE_LOGIC_AUDIT_V41.md](ARCHITECTURE_LOGIC_AUDIT_V41.md)（系统七层/15工序与真实实施缺口）。**

## 1. 开始做任何任务前必读（按顺序）

0. **[HARD_RULES.md](HARD_RULES.md) —— 最高优先级：不许概念性总结，必须方法/步骤/案例/反证/迁移/验收；周报+年报；用户赞同原方案必须保真留档。**
1. [README.md](README.md) —— 最新状态、文档地图与运行边界。
1a. **[DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md)、[HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md)、[ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)（强制）**
1b. **[REAL_CASES_EVIDENCE_FIRST.md](REAL_CASES_EVIDENCE_FIRST.md)——真实公开原始材料的政治/商业/投资逐步教学基准**
2. [DECISIONS.md](DECISIONS.md) —— 用户批准/否决/未决、日报隔离和弃用来源。
3. [MASTER_BLUEPRINT.md](MASTER_BLUEPRINT.md) —— 六目标、九栏目、整体系统与价值。
4. [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) —— 过往讨论归档对应的责任文档；遇不清楚的问题先回证据。
5. 当前任务最相关的专业文档：[END_TO_END_WORKFLOW.md](END_TO_END_WORKFLOW.md)、[DATA_CONTRACTS.md](DATA_CONTRACTS.md)、[COGNITIVE_ADVISOR_SKILL.md](COGNITIVE_ADVISOR_SKILL.md)、[PUBLICATION_SPEC.md](PUBLICATION_SPEC.md)、[QA_AND_METRICS.md](QA_AND_METRICS.md)、[BUILD_PLAN.md](BUILD_PLAN.md)。
6. 来源技术任务才继续查看SOURCE_REGISTRY.json、SOURCE_DISCOVERY.md及历史审计；**当前用户要求来源暂不继续测试**。
7. 回答用户时区分已实现、已测试、仅设计、未批准；不要以建议的项目结构伪称已存在源码。

## 2. 项目唯一定位与核心理念

- “内参”“内参系统”指同一项目；历史名全球战略内参，英文缩写GSI。
- 全球来源发现必须独立于每日早报；即使日报关闭也可以研究。
- 目标是**提高用户认知世界、反茧房、独立深思、美股投资和小团队创业能力**。
- 像顶级家族办公室一样证据严谨，不能声称掌握内幕。
- 每篇有忠实专业报道与深层机制教学，少用空话、不复制长篇受版权保护原文。
- 独立反方调查而不凑虚假均衡；原始证据和历史判断不许被摘要代替。
- 周报、年报是两个独立的研究产品；日报原系统和其北京时间07:00调度不修改。

## 3. 当前确定的范围

- 当前活跃全球来源登记 `SOURCE_REGISTRY.json` **124个**，A116+B8；六个用户放弃的来源在`SOURCE_ABANDONED_2026-10-13.json`，不要自行恢复。
- 四条随机HTTPS样本已于2026-10-13测试4/4 HTTP200；这不意味着所有124源可以生产爬取或已获得AI处理许可。
- **不在当前阶段继续来源全部测试或扩容**；主任务是系统设计及样稿/研究技术蓝图。
- 未建立内容研究引擎、周报/年报自动生产、知识档案数据库、正式新投递计划。

## 4. 不可未经用户明确授权触碰的内容

1. `newspaper/`父目录原新闻系统的工作流、脚本、定时任务、Secrets、邮件设置、收件地址、生产数据库和历史档案。
2. 正式向用户或第三方发送邮件、部署新cron/新生产workflow、购买服务、自动交易、创建/共享敏感私有资料。
3. 使用未获准许可的商业研报、付费正文、私人账号cookie、内幕数据，或绕过网站收费和安全访问限制。
4. 在公共GitHub仓库写令牌、邮箱、个人投资账户明细、受限原文全文和其他敏感资料。

允许在收到用户明确“开始开发某阶段”指令后，在本目录增量开发和本地/隔离环境测试；生产/外发仍需独立批准。

## 5. 修改流程和证据纪律

1. 先读取当前仓库相关文件**不要从聊天记忆脑补文件结构**。
2. 读DECISIONS.md确定状态：APPROVED_DIRECTION ≠ APPROVED_EXECUTION。
3. 列出最小受影响文件及验收；不会为了显得进度大而先重构全部仓库。
4. 使用独立分支或与日报隔离路径；必要时检查Git状态/分支和权限。
5. 以可复现冻结资料测试；标注源时间与论文状态、来源类型、版权用途。
6. 开发期间，每个工序的输入输出遵循DATA_CONTRACTS.md，输出JSON/Markdown与审核日志。
7. 发现新事实可更新判断版本，不得悄然覆盖旧论断或历史版本。
8. 验收说明必须区分 **“文档已提交”“代码可运行”“一次真实采集”“跨日稳定”“生产交付”** 五类证据。
9. 变更用户决定需更新DECISIONS.md、CHANGELOG.md和TRACEABILITY_MATRIX.md；不改变source ID以免历史失联。
10. 出现重要事实、引用、隐私、来源许可问题即Block，不要用模型自评代替修复。

## 6. 默认技术取舍（建议，不是绑定）

- Python轻量管道 + JSON Schema，Git版本化Markdown + JSON原始研究。
- 先用少量合法公开来源和6个真实样稿证明价值；SQLite/普通全文搜索足够就不要提前造图谱。
- 九栏目是研究规则配置而非九个Agent；可以一个LLM多工序，也可之后按证据使用不同模型。
- 低价值候选程序处理，重要少数才深度LLM研究；成本/失败可观察。
- 独立事实核查和最强反方；写作后必须可回查证据。
- 周报/年报输出Markdown主稿，HTML/PDF可选，真实邮件需要再获用户允许。

## 7. 对用户的每次状态反馈必须说明

```text
任务目的：
本轮读取的权威文件：
新增/修改文件与GitHub路径：
哪些是用户批准，哪些是我们的建议：
实际测试的内容、方法和结果：
哪些仍未实施或无法证明：
是否改动任何日报内容、生产工作流、邮件和Secrets：
下一项最小可执行任务：
```

## 8. 质量红线

凡是“看上去很像专家”却无法给出真实资料、可检验机制、最强反证与约束条件的文章，一律不是达到目标的内参。凡是声称“公开资料＝内部信息”“来源Homepage HTTP200＝全文生产采集”“邮件API接受＝收件人读到”“已讲过原理＝用户学会”的项目报告，必须纠正。

## 9. V4.0用户认可即时归档与逐领域教学硬规则

- 用户说“你说得对”“同意”“非常好”时，定位其认可的是哪段实际方案，按[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)的记录格式保留原话/时间/具体步骤/赞同边界，**同步具体规范**。后来的明确修改（例如月报→年报）覆盖旧方向，历史不删除。
- 每个文章研究至少有具体事实指针、历史基线、相关学科的第一性约束、各方权力/资金/利益/信息、真实可证机制、带单位或制度过程的例子、最强反方、迁移到陌生事件的判断法、历史Theme版本更新。不能写“深度分析商业模式”就算完成。
- 九栏目必须加载对应[DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md)；涉及人性与中国传统文化，加载[HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md)，古典观点只作为有来源、有局限的思想透镜。
- 缺实际步骤/实例/反方者REVISE；伪造事实、错误法源/公式/临床状态、人性猜测冒充事实者BLOCK，**事实/逻辑审稿具否决权**。
- 现行仅WEEKLY与ANNUAL，年报由全年周报加当年独立新闻/机构数据重新研究，**不得MONTHLY调度或模板复活**。
- 这仍是**文档规则**，未来工程需实际编成机器校验与独立编辑门禁，不假装已经装载到所有外部AI实例。

## 10. V4.1防清单化执行规则

1. 九栏是初步归类和学科核查工具箱，不是封闭课程；先查现实反常、必要条件与竞争性机制，再决定本篇该教什么世界运行规律。
2. 顾问必须对原始证据解释现实问题、资源/权力/收益/约束；导师把最有价值机制教成可迁移的知识。二者需要双向回查，教学发现事实漏洞时退回EvidencePacket。
3. 独立审校复核关键机制箭头、反证、可迁移程度和类比边界。把每篇固定写成“本质是人性/博弈/供需”必须REVISE。
4. 完整方法见[OPEN_ENDED_WORLD_MODEL.md](OPEN_ENDED_WORLD_MODEL.md)，完整审计见[ARCHITECTURE_LOGIC_AUDIT_V41.md](ARCHITECTURE_LOGIC_AUDIT_V41.md)。新Markdown不等于功能已运行。

## 11. V4.2 必须执行的最新规范和开发冻结边界

**首读顺序更新**：在旧九栏/旧12步之前先读[ADVISOR_MASTER_METHOD.md](ADVISOR_MASTER_METHOD.md)和[MAGAZINE_ARCHITECTURE.md](MAGAZINE_ARCHITECTURE.md)。有冲突时七问三检验及杂志A新闻→B顾问+帝师→C未来证据优先。旧12步是详细工具箱，不另部署十二Agent。

整个认知研究只有**一个联合顾问—帝师工作台**；原“世界机制发现”与“顾问/帝师”不能作为两套重复写稿系统。审校环节保持独立否决。认知机制可以多因并存、诚实未知。

当前已审计但未修的真实工程问题由[ISSUE_BACKLOG.md](ISSUE_BACKLOG.md)按NC编号管理；**当前只定杂志设计并记录问题，不去逐项动工**。后续用户批准实际开发时对照Issue的测试与产物，并区分DESIGN_RESOLVED和VERIFIED。父目录日报隔离、旧月报废止、124源继续暂不全量测试。

## 12. V4.3对所有Agent/Codex的记者与选文执行禁令

**新首读**：[EDITORIAL_SELECTION_AND_REPORTING.md](EDITORIAL_SELECTION_AND_REPORTING.md)（有步骤的高影响力/典型/正负事件选择、5W1H标准新闻与机构报告稿）；[SCENARIOS_AND_OPEN_QUESTIONS.md](SCENARIOS_AND_OPEN_QUESTIONS.md)（事件条件推演与开放性问题）。

- 研究输入是事件/真实机构报告/调查结果，不是只挑热搜的新闻标题。先过证据/影响/典型或突破/版权硬门槛、评分带理由、整刊反茧房复审；负面与正面同价值评判。
- A新闻必须让没有读过原文的人在不依赖B分析的情况下真正知道事情经过、事实规模与证据；5W1H完整，机构报告写样本/模型/局限；未做的采访、调查/现场走访**绝不冒称自采**。
- B顾问与帝师分开承担研判与知识讲解；C现行标题**《事件推演与开放性思考》**，条件机制推演和2—4道没有预设正确政治/商业结论的开放题。旧“继续观察”只属后台Thesis监测，不准出现在主文结构模板中。
- 现行总纲：[MAGAZINE_ARCHITECTURE.md](MAGAZINE_ARCHITECTURE.md) V4.3；不改既有日报，不进行未授权源全面测试、实际投递或新生产任务。
