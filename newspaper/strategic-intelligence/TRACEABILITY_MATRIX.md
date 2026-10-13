# 内参系统｜历史讨论完整性追溯与防遗漏矩阵

> 目标：未来的ChatGPT、Codex或其它AI只需读取本文件和对应设计文档，就能追溯已讨论的关键要求、禁忌、来源变更与实施边界。矩阵是**设计内容映射**，不假装包含用户所有过往对话的逐字档案；过去的原始聊天和GitHub审计文件仍须保留。

| 序号 | 讨论决定、偏好或技术问题 | 主文档（单一责任归档） | 当前状态 |
|---|---|---|---|
| 01 | 正式命名“内参系统”与GitHub中文搜索 | README.md、内参系统.md、../内参系统.md | 已归档 |
| 02 | 整体愿景：一流家族办公室级公开战略情报 | MASTER_BLUEPRINT.md | 已确认 |
| 03 | 不能装作获得秘密消息/内幕信息 | EDITORIAL_POLICY.md、DECISIONS.md | 硬约束 |
| 04 | 六项可检验认知和能力变化 | VISION_AND_SCOPE.md、MASTER_BLUEPRINT.md、QA_AND_METRICS.md | 已确认 |
| 05 | 独立深度思考、避免信息茧房 | EDITORIAL_POLICY.md、COGNITIVE_ADVISOR_SKILL.md、QA_AND_METRICS.md | 硬约束 |
| 06 | 深入真实一线前沿、多语全球来源 | SOURCE_DISCOVERY.md、MASTER_BLUEPRINT.md | 已确认 |
| 07 | 美股和创业为25%+25%双核心 | VISION_AND_SCOPE.md、PUBLICATION_SPEC.md | 已确认 |
| 08 | 全九板块及参考资源配比 | VISION_AND_SCOPE.md、MASTER_BLUEPRINT.md | 已确认 |
| 09 | 中国与美国独立栏目/政治和突发重要 | VISION_AND_SCOPE.md、PUBLICATION_SPEC.md | 已确认；篇数属不同产品 |
| 10 | 不能完全从日报精选再筛选 | SOURCE_DISCOVERY.md、END_TO_END_WORKFLOW.md | 硬约束 |
| 11 | 日报北京07:00不受影响 | DECISIONS.md、AGENTS.md | 已确认隔离 |
| 12 | 全球主流媒体：BBC/Reuters/新华社/人民日报海外版等 | SOURCE_REGISTRY.json/.md | 已归档、当前不再测试 |
| 13 | 摩根大通、贝莱德、先锋、道富、高盛、花旗、美银、摩根士丹利 | SOURCE_REGISTRY.json、SOURCE_DISCOVERY.md | 已归档（仅公开部分） |
| 14 | 伯克希尔历年股东信与年报 | SOURCE_REGISTRY.json、COGNITIVE_ADVISOR_SKILL.md | 已归档 |
| 15 | 四大：PwC、德勤、安永、毕马威 | SOURCE_REGISTRY.json、SOURCE_DISCOVERY.md | 已归档 |
| 16 | 战略咨询：麦肯锡、BCG、贝恩 | SOURCE_REGISTRY.json、SOURCE_DISCOVERY.md | 已归档 |
| 17 | 政策/政治/军事/科技/AI/医疗/创业/社会机构研究 | SOURCE_REGISTRY.json、MASTER_BLUEPRINT.md | 已归档 |
| 18 | 低成本来源采集、免费RSS/API、GitHub成熟项目 | SOURCE_TOOLING_RESEARCH.md、SOURCE_DISCOVERY.md | 有技术调查，未生产 |
| 19 | 付费产品与AI版权限制排除 | SOURCE_ACCESS_BLOCKLIST.md、DECISIONS.md | 硬约束 |
| 20 | 130源历史、放弃最后6源、现124源 | SOURCE_ABANDONED_2026-10-13.json、SOURCE_REGISTRY.json | 已执行 |
| 21 | 用户只要随机3—4源测试，不要全部 | audits/random-four-20261013.json、DECISIONS.md | 已执行4条 |
| 22 | 当前暂停其余来源技术验证，转入全系统设计 | DECISIONS.md、BUILD_PLAN.md | 当前阶段 |
| 23 | 首版保持简约，反对多Agent过度设计 | TECHNICAL_DESIGN.md、BUILD_PLAN.md | 已确认 |
| 24 | 从报道→研究→顾问讲解→审校→出版→存档全链路 | END_TO_END_WORKFLOW.md、MASTER_BLUEPRINT.md | 设计 |
| 25 | 新闻报道忠于原文但不生硬全文复制 | EDITORIAL_POLICY.md、PUBLICATION_SPEC.md | 已确认 |
| 26 | 避免摘要过短、文章不能只有AI式套话 | PUBLICATION_SPEC.md、COGNITIVE_ADVISOR_SKILL.md | 已确认 |
| 27 | 首席顾问深入讲解政治博弈、经济、金融、创业机制 | ADVISOR_PEDAGOGY.md、COGNITIVE_ADVISOR_SKILL.md | 已确认 |
| 28 | 第一性原理、费曼、苏格拉底与反例 | COGNITIVE_ADVISOR_SKILL.md、ADVISOR_PEDAGOGY.md | 已确认 |
| 29 | 顾问按实际证据解释，不能主观意测 | EDITORIAL_POLICY.md、COGNITIVE_ADVISOR_SKILL.md | 硬约束 |
| 30 | 竞争性假设/Steelman，不制造虚假对等 | EDITORIAL_POLICY.md、QA_AND_METRICS.md | 已确认 |
| 31 | 来源独立性、转载归因、跨语言去重 | END_TO_END_WORKFLOW.md、DATA_CONTRACTS.md | 设计 |
| 32 | L1/L2/L3研究成本分级 | TECHNICAL_DESIGN.md、BUILD_PLAN.md | 已确认方向 |
| 33 | 周刊是全新的深度研究刊物 | PUBLICATION_SPEC.md | 已确认 |
| 34 | 月报为战略判断新综合，不拼接周刊 | PUBLICATION_SPEC.md、INTELLIGENCE_MEMORY.md | 已确认 |
| 35 | 月报“首席顾问致决策者” | PUBLICATION_SPEC.md | 规划已讨论 |
| 36 | 超长文章分章节生成、统一主编和链接验证 | END_TO_END_WORKFLOW.md、PUBLICATION_SPEC.md | 设计 |
| 37 | 严格来源引用、事实推断未知分层 | EDITORIAL_POLICY.md、DATA_CONTRACTS.md | 硬约束 |
| 38 | 结构化独立审校、拒稿/返工与阻断错误 | QA_AND_METRICS.md、END_TO_END_WORKFLOW.md | 设计 |
| 39 | 历史来源、研究笔记和旧判断不可覆写 | INTELLIGENCE_MEMORY.md、DATA_CONTRACTS.md | 硬约束 |
| 40 | 知识卡、读者迁移，已讲过不等于已掌握 | COGNITIVE_ADVISOR_SKILL.md、QA_AND_METRICS.md | 设计 |
| 41 | 跨月判断复盘、预先定义证伪指标 | INTELLIGENCE_MEMORY.md、PUBLICATION_SPEC.md | 设计 |
| 42 | 邮件产生、发出、接收状态不能混淆 | END_TO_END_WORKFLOW.md、QA_AND_METRICS.md | 硬约束 |
| 43 | 预算按真实模型和数据开销计，不把日报预算直接套用 | BUILD_PLAN.md、DECISIONS.md | 待测未批准 |
| 44 | 优先复用成熟GitHub组件，逐项benchmark | BUILD_PLAN.md、TECHNICAL_DESIGN.md | 已确认方向 |
| 45 | 版本化.md项目框架与可交接AI指令 | AGENTS.md、BUILD_PLAN.md、TRACEABILITY_MATRIX.md | 本轮交付 |
| 46 | 未经用户授权不发送邮件、不变更日报、不部署付费API | AGENTS.md、DECISIONS.md | 硬约束 |
| 47 | 周刊/月报具体发刊日、字数和版式未最终批准 | DECISIONS.md、PUBLICATION_SPEC.md | 待确认 |
| 48 | 六个领域真实样刊（美股2/创业1/政治1/科技1/宏观1）先于大规模编码 | BUILD_PLAN.md、QA_AND_METRICS.md | 研发第一门槛 |
| 49 | 有原创独立判断但必须透明标为推论 | EDITORIAL_POLICY.md、COGNITIVE_ADVISOR_SKILL.md | 已确认 |
| 50 | 尽量用低成本工具在GitHub中可重现、可验证 | BUILD_PLAN.md、DATA_CONTRACTS.md | 设计 |

## 未来审计方法
1. 发现某个旧谈话要点没在此矩阵：先读相关原始对话/来源记录，精确恢复原意，再加新行，指向单一文档；禁止由AI想象“用户曾批准”。
2. 设计变动：同步更新 [DECISIONS.md](DECISIONS.md)（状态/取代关系）、[CHANGELOG.md](CHANGELOG.md)（文件改变）、本矩阵（引用归属）。
3. 细节冲突：最新明确的用户决定 > DECISIONS.md的明确状态 > 专题设计规范 > 历史草稿和旧测试描述。不能据此重写或删除历史证据。
4. 此表每行描述一个**可核实的用户要求或过去讨论过的建议**，而不是宣称覆盖未实际读取的所有聊天记录。
