# Codex开发入口

本项目目录：`cra system`。技术执行版 v0.5，2026-10-29。

## 最新技术复核

先读[第一性原理v0.4结论](audit/FIRST_PRINCIPLES_REVIEW_V04.md)、[完整实施路径](plan/IMPLEMENTATION_PATH.md)和当前任务的design_refs/entry_conditions/handoff_outputs。W01—W14已完成真实PostgreSQL、S3、API/工作台、资料解析/来源定位、规则候选/确认/启用日、隔离provider探测、结构化患者事实/访视断点、历史遗留/分项确认、EDC快照、源检验文件读取/坐标、先匹配后比较、有依据的安全分析、原ISF/TMF目录对照、项目阶段/交接清单、受控DOCX/XLSX报告输出、两次连续监查、40场景证据验收及复杂扫描/JPEG增强；任意真实规则或报告文本的完整语义、真实模板覆盖、实际医院版式、真实设备和弱网、安全分析临床性能、全流程节时和授权试用仍待后续验证。原业务要求和任务编号保持。

W15部署候选已通过隔离云端容器构建与健康检查，但获准OIDC、私有生产服务、真实恢复和授权试用仍缺失；因此W15是`blocked`，不是verified。

2026-11-01独立审查提出的13项问题已按[关闭映射](validation/REVIEW_REMEDIATION_20261101.md)修复，并在[run 41245438323](https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323)重新完成W01—W09源码绑定CI；旧完成证据保留在`completion_history`。

第二轮复核确认的03/04/08残留已按[补充关闭记录](validation/REMEDIATION_RECHECK_CLOSURE_20261101.md)修复，W04—W09在[run 41248250769](https://github.com/pyzz58/gpt-recommendations/actions/runs/41248250769)重新完成专属CI。诊断探针通过只表示复现预期缺陷，不构成验收。

后续独立正向验收发现的原03分支目标残留已关闭，工程门禁已接入[防复发规范](architecture/REGRESSION_PREVENTION.md)、[当前审核入口](audit/current_findings.json)、选择器和任务证据工具。关闭证据见[分支门禁记录](validation/BRANCH_GATE_AND_PREVENTION_20261101.md)。

W12完成后已在[run 42354648562](https://github.com/pyzz58/gpt-recommendations/actions/runs/42354648562)重新绑定W01—W12源码证据；证据摘要排除了Git-ignored运行产物，关闭发现继续核对成功job日志中的具体`test::case`。


编码和宣称完成前阅读[audit/TECHNICAL_ROUTE_REVIEW_20261029.md](audit/TECHNICAL_ROUTE_REVIEW_20261029.md)及[开放项](audit/findings.json)。本次八点澄清已修改14条理论及相应设计/任务，见[最新决定](theory/DECISIONS_20261029.md)；W04完成的是有来源的规则候选、有限AST、用户确认和启用日，不代表任意方案自动理解或检验核对。历史导入、真实格式覆盖和获准试用等缺口仍须在相应功能交付前修订，不能因为基础CI绿色就忽略。

## 当前状态和第一步

已完成CRA-W00技术基线和**CRA-W01至W14**。本机合成体验与W12稳定性修复在[run 42438384456](https://github.com/pyzz58/gpt-recommendations/actions/runs/42438384456)通过全部源码绑定job；W15授权试用记录仍明确为`BLOCKED`；V1A主线选择器为complete。

先运行只读选择器：

```bash
cd "cra system"
python3 tools/next_task.py
```

它读取实际计划，不修改任务状态。已阻塞或进行中的当前项不能被自动跳过；完成后更新状态和证据，再定位下一项。V1A/W08必须包括支持格式的自动读取；W14只增加声明的复杂格式；W15须在获准环境中完成真实恢复和授权试用。当前版本仍不是临床试用就绪版本。

## 必须阅读

1. 本目录AGENTS.md和README.md。
2. theory/BASELINE.md及theory/REQUIREMENTS.md。
3. architecture/SYSTEM.md及architecture/IMPLEMENTATION_ROUTE.md。
4. traceability/INDEX.md，确认当前理论对应的模块。
5. architecture/REGRESSION_PREVENTION.md、audit/current_findings.json，再读plan/CODEX_TASKS.md、plan/tasks.json和当前任务的plan/work_packages/CRA-Wxx.md。
6. 当前任务引用的模块设计、architecture/DATA_MODEL.md和API_CONTRACTS.md。

当前用户若只要求设计或审阅，就完成该请求，不把任务擅自标为业务已实现。进入编程时，必须交付实际可运行代码，不能用另一份说明、空接口或静态mock页面代替。W15必须有获准环境、身份/私有服务和试用授权后才能开始。

## 可直接交给Codex的首轮指令

使用[plan/CODEX_FIRST_MESSAGE.md](plan/CODEX_FIRST_MESSAGE.md)中的完整指令；先读[复用选择](architecture/REUSE_ASSESSMENT.md)。W01—W14已完成；W15部署候选已备，真实试用需获准环境、授权和外部证据。

后续用户说“继续”，先运行next_task并按实际状态接续；不得只机械把任务号加一。当前W15已由外部条件阻塞，普通“继续”不自动部署、启用外部模型或处理真实资料。恢复工作时先取得环境和授权。

## 每项任务的交付

实际代码/迁移/接口及必要页面；有意义的单元与集成验证；可复现合成结果；真实执行证据；能力和阻塞说明。计划文件与代码路径有偏差时同步修订，不为维持旧文件名而牺牲合理实现。

任务中的available是当前可运行入口；to_implement是本任务需要先实现的命令。目标文件清单是计划，verified时必须实际存在，且W01以后通过tools/task_evidence.py核对绑定源码和任务专属GitHub运行的结构证据。不能用修改状态、增加文档或大量mock测试证明未完成功能。

## 理论变更

业务理论按固定CRA-R编号和来源维护，改动后执行既有SYNC_POLICY。技术文件布局、任务细化或依赖工具选择的调整，不应伪造新的临床决定。接口、存储或供应商变化按实际受影响模块更新，保留历史事实和已签发报告。

最新业务决定：遗留逐项展开，CRA点击确认整改即可；缺数据用户可拒绝并跳过相关路径；list含前后条件和分支；版本手动设开始使用日；目录可直接作对照文件；W08自动检验读取属于主线，手工仅少量例外。45个理论编号保持，14条提高revision。W01—W14已按工程范围完成；W15部署候选已备但实际环境和获授权试用仍阻塞，不能沿用旧的人工V1A验收口径。
