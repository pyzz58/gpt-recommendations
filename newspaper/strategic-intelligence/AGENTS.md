# 内参系统｜未来GPT/Codex唯一现行交接规则（V4.4）

> **必须执行，2026-10-13，仍在用户审核中的设计规范。** 本文件只约束 `newspaper/strategic-intelligence/`，不能作为启动生产工作流/付费API/邮件的授权。所有旧V4.0—V4.3具体讨论保留在GitHub历史，不得因此忽略用户已认可的详细方法。
>
> **最高用户指示**：不要概念性总结；完整保留详细方法、实际步骤、真实证据、失败分支、验收。系统每次更新前读取GitHub最新文件，不能仅靠模型记忆猜测状态。

## 1. 精确优先级和首读顺序（不要从旧七层/十二步开始）

1. **[DECISIONS.md](DECISIONS.md)**：用户同意、明确否决、延期、未授权。最新用户明确指令优先，不能推断“不错”=同意上线。
2. **[CANONICAL_SYSTEM_SPEC_V44.md](CANONICAL_SYSTEM_SPEC_V44.md)**：**唯一完整现行主规格**，包含全部正式产品、六层、选文、报道、研究、推演、年报、数据库、质量与运营。
3. **[HARD_RULES.md](HARD_RULES.md)**：所有硬阻断及不能只写“第一性”“帝师”“深入分析”等概念。
4. **[EDITORIAL_SELECTION_AND_REPORTING.md](EDITORIAL_SELECTION_AND_REPORTING.md)**：S0—S8九工序、真实影响、正负与混合、典型或重大突破、来源证据、研究后二次选文，A新闻5W1H完整、REPORT样本/方法/局限。
5. **[ADVISOR_MASTER_METHOD.md](ADVISOR_MASTER_METHOD.md)**：研究的唯一七问三检验；多机制共存，区别事实/推断/未知，推理的溯因/演绎/归纳，顾问与帝师双向返工。
6. **[SCENARIOS_AND_OPEN_QUESTIONS.md](SCENARIOS_AND_OPEN_QUESTIONS.md)**：读者C段“事件推演与开放性思考”，条件不同的路径与非引导开放问题。
7. **[MAGAZINE_ARCHITECTURE.md](MAGAZINE_ARCHITECTURE.md)**、[templates/ARTICLE_TEMPLATE.md](templates/ARTICLE_TEMPLATE.md)、[templates/WEEKLY_TEMPLATE.md](templates/WEEKLY_TEMPLATE.md)、[templates/ANNUAL_TEMPLATE.md](templates/ANNUAL_TEMPLATE.md)：当前正式读者版刊物和模板。
8. **[QA_AND_METRICS.md](QA_AND_METRICS.md)**、[DATA_CONTRACTS.md](DATA_CONTRACTS.md)、[ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)、[INTELLIGENCE_MEMORY.md](INTELLIGENCE_MEMORY.md)：QA、数据、年度和长期研究。
9. **[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)**、[ISSUE_BACKLOG.md](ISSUE_BACKLOG.md)、[ARCHITECTURE_AUDIT_V44.md](ARCHITECTURE_AUDIT_V44.md)：用户认可过的完整方法、未修问题/实际证据、最新一致性审计。
10. 如主题涉及专业细节，再读[DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md)、[HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md)、[DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md)、[INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)，**九领域知识只是专业工具箱，不是课程封闭清单**。

**有冲突时：最新用户明确决策→正式现行主规格/硬门禁→专用SOP/当前模板→旧版历史说明**。需要修正矛盾应在文档修改记录和问题台账中留证，不得默默运行错误版本。

## 2. 唯一产品和架构

- 正式中文名“内参系统／内参”，只发**WEEKLY周报＋ANNUAL年报**；月报已废止、特别事件特刊未获正式批准。
- **既有日报独立**：不可改父目录 `newspaper/` 的代码、07:00安排、GitHub Actions、Secrets、收件人或生产储存。
- **现行六层**：L1独立全球信息发现→L2事件合并及S0—S8选稿→L3可核原始资料+记者A完整新闻→L4同一顾问帝师认知工作台（B1/B2/C）→L5独立硬审稿→L6主编/周报年报出版及不可覆写档案。**六层是职责，不是六个Agent。**
- 九栏是长期资源权重（美股25%、创业25%、科技12%、宏观10%、中美10%、地缘/军事6%、企业5%、社会4%、战略3%），不按固定篇数分配、不当作全球发现的过滤器。
- 来源登记当前124条活跃候选、6条弃用；历史抽样≠生产接入。**不要自行继续全量来源测试、恢复六个弃源、购买被限制服务或绕付费内容**。

## 3. 必须真正走过的文章生产环节

1. S0—S8选文，每个候选留原始ID、事实/授权门槛、已证或潜在的正负影响、典型性或突破、试用量化评分理由、二次审查撤稿可能。不能被热搜绑架，重要正面成果必须有公平机会。
2. A记者新闻/机构报告：**5W1H**谁/何事/何时/何地/已知为什么/如何发生，真实导语、时间线、数值/分母、当事人回应、必要历史/法规背景、原始来源与未知。科研/机构报告还须写作者/研究目标/样本/方法/适用局限；不能将稿件缩成短摘要，更不能伪采访/照搬付费版权。
3. B1顾问：现实影响和利益、谁能否决/支付/选择、竞争或协同的解释、最强反方、有条件判断，不重复A。
4. B2帝师：由本事件证据挑选应教的真实学科原理、正规定义、实际传导/算例/程序、正反实例、迁移到陌生国家或行业，不重复B1，不因栏目限定教学范围，古籍/人性需核原典/边界。**不能承诺唯一终极规律。**
5. C条件推演与开放问题：由B1/B2派生至少两条实质不同的条件性路径及正负/二阶后果；建议2—4道非引导、可真正练习批判与迁移的开放问题。**不写固定“继续观察”**，但后台保留未来事实/旧判断审计。
6. 独立核查源与法定/财务/科学事实、反证和因果、教学与开放题、许可；重大错误`BLOCK`，泛泛或不足`REVISE`，通过方可主编排刊。`PASS`只能由实际审核证据支撑，不由模型自报。
7. 周报整刊封面、目录、总编辑卷首、动态栏目与每篇全文、历史纠错、来源索引；年报再加全年独立新闻和机构研究双输入、旧论断审计/漏报/数据修订/年度新综合，不得拼52周。
8. 归档事实原件指针、Source/Event/Claim/Evidence、Article A/B/C、Theme/Concept/ThesisVersion、审稿和Edition版本/更正。新证据改变结论写新版本，不抹去旧研究。

## 4. 任何修改/研发的审批和可复现要求

- 本轮仅按用户要求完善**设计规范、现行模板和问题台账**，不是开始开发生产服务。可对设计文档做一致性修订并明确记录，但不得擅自启用新的云工作流、邮件、收费、交易。
- 修改前查看GitHub真实文件和SHA；遵守原有非本项目资产；更新最少必要文件。
- 重大用户新认可：找出紧邻完整方案（不仅“我同意”四字），把具体步骤、实例、拒绝/修改的边界、用户原话真实片段及影响文件记到[ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)和[DECISIONS.md](DECISIONS.md)；无法取回旧聊天不可捏造。
- 研发阶段的任务必须有输入/输出、失败分支、复现方式、事实样例/负例、人工审校、GitHub commit和验收；留未解决NC编号。**DESIGN_RESOLVED不能改成VERIFIED除非实际代码/样稿已经测试且有证据。**
- 大模型已有广泛知识但不是完整真实世界资料库，最新法律/财报/新闻必须重新查公开原文；无法核事实不得编造。研究中不允许根据政治立场、媒体党派或古典典故直接宣布胜负或隐秘动机。
- 公共仓库禁贴用户身份/账户/收件邮箱/密码/API令牌、商业受限原文、内部未授权文件。对任何未授权外发一律STOP。

## 5. 给用户的报告固定要求

每次完成文档修改或测试，应准确说明：
- 哪些文件已真的提交并从GitHub读回；具体commit/路径；
- 哪条来自用户明确批准、哪条只是编辑提议；
- 完成了哪项**真实检查**，哪些只是设计；
- 旧版冲突是否仍存在（注明是否为历史资料）；
- 哪些生产、数据权限和质量/读者学习效果仍未证明；
- 是否触碰了日报/Actions/邮件/Secrets（未触碰必须明确）；
- 未获授权的未来事项保留在Issue，不应主动执行。
