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
| 34 | 旧月报综合研究原则已于2026-10-13**被年报取代**；年报以全年周报和全年独立新闻源重新分析 | ANNUAL_REPORT_SPEC.md、DECISIONS.md | **SUPERSEDED→ANNUAL** |
| 35 | “首席顾问致决策者”的长篇研究总论转入年报 | ANNUAL_REPORT_SPEC.md、PUBLICATION_SPEC.md | 年报已确认方向 |
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
| 47 | 周报/年报具体发刊日、字数和版式未最终批准 | DECISIONS.md、PUBLICATION_SPEC.md | 待确认 |
| 48 | 六个领域真实样刊（美股2/创业1/政治1/科技1/宏观1）先于大规模编码 | BUILD_PLAN.md、QA_AND_METRICS.md | 研发第一门槛 |
| 49 | 有原创独立判断但必须透明标为推论 | EDITORIAL_POLICY.md、COGNITIVE_ADVISOR_SKILL.md | 已确认 |
| 50 | 尽量用低成本工具在GitHub中可重现、可验证 | BUILD_PLAN.md、DATA_CONTRACTS.md | 设计 |

## V3.1专项补录：过去详细认可、此前.md过度压缩的部分

| 补录编号 | 不可压缩的实际要求 | 完整操作文档 | 检验方式 |
|---|---|---|---|
| 51 | 五种机构能力：新闻敏锐、情报连续、投资研究、咨询因果、家族办公室3/5/10年视角 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§1—2 | 看五种能力是否各有真实产物 |
| 52 | 帝师的真正定义是**教会理解**，不是高深腔调、内幕或AI短评 | [DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md)§1—2 | 读者能否独立分析陌生事件 |
| 53 | 十一道教学动作：事实、问题、知识障碍、资源、因果、类比、反例、竞争解释、情景、迁移、长期记忆 | [DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md)§3 | 每步对应研究输出与失败回退 |
| 54 | 政治争吵背后需讲议会、行政、司法、财政、党纪、选举及合法预算程序 | [CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md)案例一 | 制度权力/否决点/竞争解释/新情境 |
| 55 | 创业新闻需从融资研究到实际客户价值、医院采购、盈利、CAC、LTV、续费、法规、壁垒、小团队可行性 | [CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md)案例二 | 逐项数值和现金兑现边界 |
| 56 | 美股“盈利增长仍下跌”的财务/预期/贴现机制 | [CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md)案例三 | 现实预期差与理论估值区分 |
| 57 | 技术实验→工程可靠→可规模部署→可盈利三重验证 | [CASEBOOK_POLITICS_AND_STARTUP.md](CASEBOOK_POLITICS_AND_STARTUP.md)案例四 | 技术反例与迁移至其它行业 |
| 58 | 战略判断追踪：旧命题、当时证据、后续反例和修正不能覆盖 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§3.1 | 带as_of、版号、原件召回 |
| 59 | 全球商业机会雷达和可执行性，而非只是融资与热点 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§3.2 | 有买方、付款、单位经济与监管 |
| 60 | 世界结构变化与反常雷达主动对比融资/营收、宣传/CapEx、技术性能/实际采用等背离 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§3.3 | 指标、口径、反证和状态明确 |
| 61 | 专业研究团队逻辑角色完整，但不强制部署十多个物理Agent | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§4 | 与最小工程方案吻合 |
| 62 | GPT Researcher / Open Deep Research / OpenBB / changedetection / GraphRAG / n8n候选需比较维护/兼容/费用 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§5 | 没做benchmark前保持候选 |
| 63 | 特刊作为第三出版物设计候选，日报/周报/年报边界清楚，未经授权不得发送 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§7 | 未授权时不建立触发器 |
| 64 | 阅读反馈必须能处理学不懂/学不会/记不住/不会用，不强制考试也不虚报已学会 | [DEEP_LEARNING_ENGINE.md](DEEP_LEARNING_ENGINE.md)§5 | TAUGHT与DEMONSTRATED区分 |
| 65 | 不因学习机制细化而大幅增加架构复杂度 | [INTELLIGENCE_OPERATING_MODEL.md](INTELLIGENCE_OPERATING_MODEL.md)§4和[BUILD_PLAN.md](BUILD_PLAN.md) | 先冻结六例测试质量 |
| 66 | 详细.md并非已安装运行的Skill或模型已经掌握这些专业知识 | [AGENTS.md](AGENTS.md)、[CHANGELOG.md](CHANGELOG.md) | 文件与生产状态区分 |

## 未来审计方法
1. 发现某个旧谈话要点没在此矩阵：先读相关原始对话/来源记录，精确恢复原意，再加新行，指向单一文档；禁止由AI想象“用户曾批准”。
2. 设计变动：同步更新 [DECISIONS.md](DECISIONS.md)（状态/取代关系）、[CHANGELOG.md](CHANGELOG.md)（文件改变）、本矩阵（引用归属）。
3. 细节冲突：最新明确的用户决定 > DECISIONS.md的明确状态 > 专题设计规范 > 历史草稿和旧测试描述。不能据此重写或删除历史证据。
4. 此表每行描述一个**可核实的用户要求或过去讨论过的建议**，而不是宣称覆盖未实际读取的所有聊天记录。

## V4.0历史回查及新决策补录（67—78）

| 编号 | 本次完整要求（历史原方案及用户新决定） | 对应具体文档 | 审核要点 |
|---|---|---|---|
| 67 | 禁止概念性总结，必须写方法、步骤、具体证据与案例 | [HARD_RULES.md](HARD_RULES.md) | R001/R010必须过门禁 |
| 68 | 美股模块从股价、实际/预期拆现金流/贴现/资本约束/反例 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §1 | FCF/市场预期/风险都有查法 |
| 69 | 创业从融资拆真实采购/付费、毛利、CAC/LTV、现金兑现与小团队入场 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §2 | 可计算、可推翻、可迁移 |
| 70 | AI科技拆论文/工程/物理/总成本/实际采用 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §3 | Demo不等于商业化 |
| 71 | 宏观拆央行/财政权限、数据口径、期限溢价和传导时滞 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §4 | 实际/名义、存量/流量正确 |
| 72 | 中美与国际政治必须学两国不同制度、法源、财政、党纪、选举、谈判和承诺 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §5—6 | 拒绝人物动机无据确定 |
| 73 | 企业竞争和社会消费分别分析利润池/代理、人口/抽样/制度与行为 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §7—8 | 非万能模板 |
| 74 | 战略研究室从历史旧观点与多个反常指标中形成可证伪世界模型 | [DOMAIN_TEACHING_PROTOCOLS.md](DOMAIN_TEACHING_PROTOCOLS.md) §9 | 旧版不覆盖、指标可查 |
| 75 | 人性：声望、恐惧、身份、互惠、选择集、权力资源要有可核依据 | [HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md) | 不以心理臆测冒充事实 |
| 76 | 中国传统文化：兵法、儒家、法家、史记等作为核原文、有时代边界的思想透镜 | [HUMAN_NATURE_AND_CLASSICAL_LENSES.md](HUMAN_NATURE_AND_CLASSICAL_LENSES.md) | 不强行用典/引用错误 |
| 77 | 正式周报+年报，年报以全年周报与独立全年新闻源双输入，旧月报已取代 | [ANNUAL_REPORT_SPEC.md](ANNUAL_REPORT_SPEC.md)／[templates/ANNUAL_TEMPLATE.md](templates/ANNUAL_TEMPLATE.md) | 年报A01—A12、原始来源/旧判断审计 |
| 78 | 用户任何明确赞同要记录被赞同方案的具体原文/方法及修改历史 | [ENDORSEMENT_LEDGER.md](ENDORSEMENT_LEDGER.md)、[DECISIONS.md](DECISIONS.md) | 无源不编造“过去已批准” |

完整历史审计方法和当前可回收证据边界见[HISTORY_RECONCILIATION.md](HISTORY_RECONCILIATION.md)。
