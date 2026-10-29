# Codex开发入口

本项目目录：`cra system`。技术执行版 v0.4，2026-10-29。

## 最新技术复核

先读[第一性原理v0.4结论](audit/FIRST_PRINCIPLES_REVIEW_V04.md)、[完整实施路径](plan/IMPLEMENTATION_PATH.md)和当前任务的design_refs/entry_conditions/handoff_outputs。新增工程门槛已写入代码；首次真实W01正向交付及临床/节时证据尚待完成。原业务要求和任务编号保持。


编码和宣称完成前阅读[audit/TECHNICAL_ROUTE_REVIEW_20261029.md](audit/TECHNICAL_ROUTE_REVIEW_20261029.md)及[开放项](audit/findings.json)。本次八点澄清已修改14条理论及相应设计/任务，见[最新决定](theory/DECISIONS_20261029.md)；没有把业务任务标完成。W01基础实现可以推进；任务完成证据、历史导入、全输出约束和阶段契约等缺口须在相应功能交付前修订，不能因为基础CI绿色就忽略。

## 当前状态和第一步

已完成CRA-W00技术基线；后续业务代码仍待实现。当前默认第一项是**CRA-W01：数据、权限和历史记录底座**。

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
5. plan/CODEX_TASKS.md、plan/tasks.json和当前任务的plan/work_packages/CRA-Wxx.md。
6. 当前任务引用的模块设计、architecture/DATA_MODEL.md和API_CONTRACTS.md。

当前用户若只要求设计或审阅，就完成该请求，不把任务擅自标为业务已实现。进入编程时，必须交付实际可运行代码，不能用另一份说明、空接口或静态mock页面代替。

## 可直接交给Codex的首轮指令

```text
仓库：pyzz58/gpt-recommendations
项目：cra system

先读取该目录的AGENTS.md和CODEX_START_HERE.md，按其中顺序读取理论、
架构、对应表和任务卡。核查实际分支状态，不假定文档中的计划已经实现。

本轮实现CRA-W01，严格按plan/work_packages/CRA-W01.md编写实际代码。
只在本项目及其专属GitHub工作流、Codespaces配置范围内修改，
保留其他项目。使用合成数据，在GitHub云端验证。

先确认W00的已有证据，再完成W01的数据、权限、幂等、版本和审计事务。
目标文件、接口、测试及完成标准以该任务卡为准。
按plan/implementation.json的CRA-W01 profile在专属工作流真正建立cra-w01 job、
migrate/test步骤，使用临时PostgreSQL执行。不要把profile清单写成已经执行。
源码提交通过实际CI后，将tested_commit/run_id/subject_digest等结构证据记入
completion_evidence，再做状态提交；自报文字、只有baseline或被跳过的job不能完成任务。
未实现的命令先创建并验证，不得宣称已经运行。
不要提前做OCR、报告界面或后续业务，不重新用计划代替编码。

完成后记录实际代码路径、迁移、测试命令、CI链接及剩余限制，
更新tasks.json、生成视图并运行同步检查；只有实际达到验收才记verified。
最后报告完成了什么、证据及下一项。若实质阻塞，说明具体缺口，
继续能独立完成的本任务工作，不跳过当前项冒充完成。
```

后续用户说“继续”，先运行next_task并按实际状态接续；不得只机械把任务号加一。默认推进V1A。若用户指定其他工作包，先核实其依赖，说明未完成前置，不隐瞒或擅改理论。

## 每项任务的交付

实际代码/迁移/接口及必要页面；有意义的单元与集成验证；可复现合成结果；真实执行证据；能力和阻塞说明。计划文件与代码路径有偏差时同步修订，不为维持旧文件名而牺牲合理实现。

任务中的available是当前可运行入口；to_implement是本任务需要先实现的命令。目标文件清单是计划，verified时必须实际存在，且W01以后通过tools/task_evidence.py核对绑定源码和任务专属GitHub运行的结构证据。不能用修改状态、增加文档或大量mock测试证明未完成功能。

## 理论变更

业务理论按固定CRA-R编号和来源维护，改动后执行既有SYNC_POLICY。技术文件布局、任务细化或依赖工具选择的调整，不应伪造新的临床决定。接口、存储或供应商变化按实际受影响模块更新，保留历史事实和已签发报告。

最新业务决定：遗留逐项展开，CRA点击确认整改即可；缺数据用户可拒绝并跳过相关路径；list含前后条件和分支；版本手动设开始使用日；目录可直接作对照文件；W08自动检验读取属于主线，手工仅少量例外。45个理论编号保持，14条提高revision。W01及之后仍待实现，不能沿用旧的人工V1A验收口径。
