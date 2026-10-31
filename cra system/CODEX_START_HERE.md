# Codex开发入口

本项目目录：`cra system`。技术执行版 v0.5，2026-10-29。

## 最新技术复核

先读[第一性原理v0.4结论](audit/FIRST_PRINCIPLES_REVIEW_V04.md)、[完整实施路径](plan/IMPLEMENTATION_PATH.md)和当前任务的design_refs/entry_conditions/handoff_outputs。W01—W09已完成真实PostgreSQL、S3、API/工作台、资料解析/来源定位、规则候选/确认/启用日、隔离provider探测、结构化患者事实/访视断点、历史遗留/分项确认、EDC快照、源检验文件读取/坐标、先匹配后比较及有依据的安全分析；任意真实规则或报告文本的完整语义、实际医院版式、安全分析临床性能、全流程节时和真实授权试用仍待后续工作验证。原业务要求和任务编号保持。

2026-11-01修复已在[run 41245438323](https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323)重新完成W01—W09源码绑定CI；旧完成证据保留在`completion_history`。后续[独立复核快照](audit/REMEDIATION_RECHECK_20261101.md)确认原03/04/08残留。整理期间又新增f66750c修复及[成功CI 41248250769](https://github.com/pyzz58/gpt-recommendations/actions/runs/41248250769)；本次未对新实现独立重验，不能沿用旧反例断言新版本仍错，也不能仅凭绿色CI断言语义问题全部关闭。先读[防复发与回归验收](architecture/REGRESSION_PREVENTION.md)及[只补三项的指令](audit/CODEX_RECHECK_FOLLOWUP_20261101.md)。


编码和宣称完成前阅读[audit/TECHNICAL_ROUTE_REVIEW_20261029.md](audit/TECHNICAL_ROUTE_REVIEW_20261029.md)及[开放项](audit/findings.json)。本次八点澄清已修改14条理论及相应设计/任务，见[最新决定](theory/DECISIONS_20261029.md)；W04完成的是有来源的规则候选、有限AST、用户确认和启用日，不代表任意方案自动理解或检验核对。历史导入、真实格式覆盖和获准试用等缺口仍须在相应功能交付前修订，不能因为基础CI绿色就忽略。

## 当前状态和第一步

已完成CRA-W00技术基线、**CRA-W01数据/权限底座**、**CRA-W02 API/工作台壳**、**CRA-W03资料与来源定位**、**CRA-W04规则候选与分层list**、**CRA-W05患者事实/锚点/核查断点**、**CRA-W06遗留复核/分项确认**、**CRA-W07 EDC检验Excel快照导入**、**CRA-W08检验源文件读取与EDC核对**和**CRA-W09有依据的AE/PD分析**。这些为已有工程交付；最新f66750c在修复复核残留时已将W04—W09重开in_progress，W10仍planned。先核对[最新修复记录](validation/REMEDIATION_RECHECK_CLOSURE_20261101.md)及实际关闭/源码绑定证据，再按当前选择器接续，不能跳过开放项，也不重复开发已正确完成内容。

先运行只读选择器：

```bash
cd "cra system"
python3 tools/next_task.py
```

它读取实际计划，不修改任务状态。已阻塞或进行中的当前项不能被自动跳过；完成后更新状态和证据，再定位下一项。V1A/W08必须包括支持格式的自动读取；V1B复杂格式增强与部署路线单独选择，普通继续不自动部署或启用外部模型。

## 必须阅读

1. 本目录AGENTS.md和README.md。
2. theory/BASELINE.md及theory/REQUIREMENTS.md。
3. architecture/SYSTEM.md及architecture/IMPLEMENTATION_ROUTE.md。
4. traceability/INDEX.md，确认当前理论对应的模块。
5. architecture/REGRESSION_PREVENTION.md、当前审核记录，再读plan/CODEX_TASKS.md、plan/tasks.json和当前任务的plan/work_packages/CRA-Wxx.md。
6. 当前任务引用的模块设计、architecture/DATA_MODEL.md和API_CONTRACTS.md。

当前用户若只要求设计或审阅，就完成该请求，不把任务擅自标为业务已实现。进入编程时，必须交付实际可运行代码，不能用另一份说明、空接口或静态mock页面代替。

## 可直接交给Codex的首轮指令

使用[plan/CODEX_FIRST_MESSAGE.md](plan/CODEX_FIRST_MESSAGE.md)中的完整指令；先读[复用选择](architecture/REUSE_ASSESSMENT.md)。W01—W09已交付并停止；后续先核实独立复核03/04/08的新修复及关闭证据，再从W10继续，不因合成安全分析provider的验证跳过后面的目录、报告或部署。

后续用户说“继续”，先运行next_task并按实际状态接续；不得只机械把任务号加一。默认推进V1A。若用户指定其他工作包，先核实其依赖，说明未完成前置，不隐瞒或擅改理论。

## 每项任务的交付

实际代码/迁移/接口及必要页面；有意义的单元与集成验证；可复现合成结果；真实执行证据；能力和阻塞说明。计划文件与代码路径有偏差时同步修订，不为维持旧文件名而牺牲合理实现。

任务中的available是当前可运行入口；to_implement是本任务需要先实现的命令。目标文件清单是计划，verified时必须实际存在，且W01以后通过tools/task_evidence.py核对绑定源码和任务专属GitHub运行的结构证据。不能用修改状态、增加文档或大量mock测试证明未完成功能。

## 理论变更

业务理论按固定CRA-R编号和来源维护，改动后执行既有SYNC_POLICY。技术文件布局、任务细化或依赖工具选择的调整，不应伪造新的临床决定。接口、存储或供应商变化按实际受影响模块更新，保留历史事实和已签发报告。

最新业务决定：遗留逐项展开，CRA点击确认整改即可；缺数据用户可拒绝并跳过相关路径；list含前后条件和分支；版本手动设开始使用日；目录可直接作对照文件；W08自动检验读取属于主线，手工仅少量例外。45个理论编号保持，14条提高revision。W01—W09已按工程范围实现，W10及之后仍待实现，不能沿用旧的人工V1A验收口径。

## 修复必须留下可执行约束

对照防复发文件的模块/理论索引，保留原反例与正确预期，补相邻边界及真实API/数据库/worker消费者回归。新增用例、验收规范和实际CI应进入既有源码绑定；只写“注意不要再犯”不算完成。现有task_evidence证明来源，不判断所有业务语义；新的审核拦截尚须在下一次修复中接入，不能声称已经自动生效。
