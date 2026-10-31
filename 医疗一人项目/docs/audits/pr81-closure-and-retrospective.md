# PR #81收口复核与多轮问题复盘

复核日期：2026-11-01。范围仅为`pyzz58/gpt-recommendations/医疗一人项目/`及其专用CI，不含同仓库其他项目。

## 结论与接续决定

项目方向仍符合第一阶段核心目标：验证“一人医药公司＋专业AI Agent＋现实外包机构”的完整研发协作模式。多轮审核主要暴露工程交付、业务规则贯通、输入真实性、故障时序及完成证据的缺口，没有证据表明已改变为优先追求某款产品。

本次收口结论：F01—F03在原问题范围内关闭；F04的跨租约语义身份及新输入/新review分离已关闭，但执行所有权仍有一个同类漏口C01（P2）。未发现新增P1。**先定点修复C01、补真实PostgreSQL时序回归并绑定新源码证据，再直接接续W19。当前不启动W19、不合并main；不重启无范围的全面审核。**

本次提交只维护最高思想、技术路线、追踪与诊断档案，应用源码保持原样，C01没有被文档更新“修复”。W01—W18仍为IMPLEMENTED而非整体VERIFIED；W24仍为PREPARED，现实合作未启动。

## 核对的版本与方法

| 对象 | 版本/证据 |
| --- | --- |
| 草稿PR与分支 | [PR #81](https://github.com/pyzz58/gpt-recommendations/pull/81)，`codex/medical-one-person-w01-w18-20261101`；读取时DRAFT、OPEN、未合并 |
| 本次审阅HEAD | `e2d1560d2bff3a2f1fe600573ac3dc2183a7880c` |
| 本次被测源码 | `4320e35bcd18ab8bb4a143853ed7bdce3267d4e7` |
| HEAD相对被测源码 | 仅验收记录、日志与派生manifest变化；未修改应用实现 |
| 上轮基线 | `6107f06e2b228bc0570e105ba759fa591619de18`，被测源码`a802be772b89619a68fad2273d8cbae613abf089` |
| 独立检查 | 按Git blob SHA还原源码与证据，核对Git祖先/源码树指纹；文档检查通过；22项追踪维护测试通过 |
| 定点诊断 | 执行原函数AST及明确的session/provider doubles：审计范围、输入准入、CLI默认参数、语义身份、单次失败结算、迟到start写入六组；31个原问题预期条件成立，另复现C01 |

诊断脚本：[pr81-closure-probes.py](pr81-closure-probes.py)；原始结果：[pr81-closure-probe-results.json](pr81-closure-probe-results.json)。结果保存被审源码文件SHA-256。脚本退出0表示诊断完成，应读取`findings`；它不是完整应用验收，也没有替代真实PostgreSQL、子进程或真实模型测试。

```bash
# 本项目目录执行；结果写在临时位置，保留本次历史档案
python3 tools/check_traceability.py check
python3 tools/test_traceability.py
python3 docs/audits/pr81-closure-probes.py --output /tmp/pr81-closure-probes.json
```

## F01—F04逐项收口

| 问题组 | 本次核对 | 结论 |
| --- | --- | --- |
| F01 审计范围 | 非空task ID才比较；由实际input_snapshot识别claim/analysis/deliverable消费者；TaskDependency传播到下游；不匹配的目标及任务继续；正常集成测试覆盖消费、下游、解除和无关对象 | 原问题关闭 |
| F02 输入准入 | 已知类型非法UUID拒绝；数据库查询限定项目；document/Citation源版本必须current且active；无效Citation、stale/disputed claim、失败analysis拒绝；未知类型拒绝，fixture/workflow/opaque明确区别 | 原问题关闭；查询/RLS的数据库行为依据源码与CI，不由诊断double证明 |
| F03 后台worker | 默认None传入workspace发现分支；Runner以AgentExecutionFailure返回分类信息，WorkerLoop单一路径结算；错误码保留，下一任务继续；CLI集成测试真实启动进程并SIGTERM退出 | 原问题关闭 |
| F04 执行身份与接管 | run key移除生命周期revision；输入快照或review变化产生新key；成功后提交前崩溃可复用输出；成功/失败结束写入已检查lease/fence | 身份与原恢复反例关闭；启动/重启写入仍存在C01，不能宣称所有AgentRun写入均已受保护 |

关键源码：`application/readiness.py`、`application/tasks.py`、`application/worker_loop.py`、`worker/__main__.py`、`agents/runner.py`。对应真实数据库回归集中在`tests/integration/test_w04_scheduling.py`和`test_w17_audit_service.py`，语义身份另有`tests/unit/test_w04_worker_identity.py`。

## C01（P2，OPEN）：迟到start可以重置接管者已成功的run

位置：[被测源码runner.py第316行起](https://github.com/pyzz58/gpt-recommendations/blob/4320e35bcd18ab8bb4a143853ed7bdce3267d4e7/医疗一人项目/services/core/src/medical_one_person/agents/runner.py#L316)。`_mark_succeeded`和`_mark_failed`已调用`_require_active_claim`；`_start_run`在创建/重启AgentRun前没有调用它，并直接依据之前取得的ExistingRunView进入更新分支。

可达时序：

1. 旧worker读到同一run的`ExistingRunView(state=running)`，在调用`_start_run`之前暂停。
2. 租约过期，新worker取得更高fence，生成并保存成功结果，完成任务提交及job结算。
3. 旧worker恢复；`_start_run`重新读取当前AgentRun行，但未先检查job所有权，也未根据当前行的成功状态分支，直接改为`running`、覆写输入快照和started_at、清空ended_at。
4. 旧worker随后在成功/失败结束写入处被fence挡住，但第3步是此前已独立提交的事务，不能靠后面的拒绝恢复成功历史。

独立诊断对原`_start_run`执行该分支，观察到：租约检查次数0，原成功记录变成running，ended_at被清空，旧上下文写入。此处使用session double构造交错时序，尚未独立运行真实数据库并发测试；代码路径与事务边界支撑该缺陷判断，修复验收须补真实PostgreSQL回归。

影响：Task/Job可能已成功，但AgentRun历史被旧执行者改坏，影响状态展示、审计依据和后续缓存/恢复判断。没有据此声称真实邮件、付款或实验已经重复发生。按已有“无P1/P2再W19”的接续条件，该项先行收口；W19的旧run版本固定本身也依赖可信运行历史。

建议修复与验收：

- 在执行记录每个创建/重启/结束写入事务内，先锁定对应job，核对running、owner、fence和有效lease，再写AgentRun；保持与现有结束写入一致的锁顺序。
- 取得锁后重新判断持久化run的实际状态，不用过时的ExistingRunView重置已成功记录；缓存复用和同一次恢复仍按语义身份处理。
- 增加真实PostgreSQL时序回归：固定“旧读running→新接管并成功→旧start”，断言旧worker被拒，成功状态、output、input_snapshot、started_at/ended_at均不变；正常接管仍能完成，同一语义成功输出仍只生成一次。
- 更新现有迟到worker测试：当前用例只断言旧worker不能持久化成功output，且容许它先创建running记录并调用provider，未覆盖成功历史被重置的窗口。
- 修改实现后重新绑定被测源码、日志与产物，不能沿用`4320e35`声明新代码已验收；只针对C01及受影响路径收口，不要求重开其余已关闭问题。

## 本地112与CI110＋2的核对

本地[pytest-final.xml](../../traceability/logs/pytest-final.xml)记录112 tests、0 failures、0 errors、0 skipped，对应已提交的本地命令/日志。独立检查已验证记录和产物hash、源码范围，但本次环境没有重跑整套应用验收；112通过属于被核对的本地证据，不是本次独立执行结果。

读取时四套GitHub Actions均success：

| 事件/检查 | GitHub运行 |
| --- | --- |
| PR应用CI | [41251201495](https://github.com/pyzz58/gpt-recommendations/actions/runs/41251201495) |
| push应用CI | [41251197650](https://github.com/pyzz58/gpt-recommendations/actions/runs/41251197650) |
| PR文档CI | [41251201511](https://github.com/pyzz58/gpt-recommendations/actions/runs/41251201511) |
| push文档CI | [41251197624](https://github.com/pyzz58/gpt-recommendations/actions/runs/41251197624) |

PR应用job `124684898204`原始日志中，pytest进度为112项，其中110通过、2跳过，跳过原因明确：

- `tests/integration/test_w14_export_api.py:32`：缺LibreOffice/Poppler，未执行W14 API验收。
- `tests/unit/test_w14_exports.py:128`：缺LibreOffice/Poppler，未执行W14文件验收。

这两个环境跳过已披露，不另列为新P1/P2，也不解释为CI完成W14验收。该job同时记录Ruff通过、mypy 112源码文件通过、PostgreSQL迁移往返至`c8f1a6d3e720`、前端检查/构建与追踪自测成功。79条RLS策略属于应用测试/本地记录的检查内容，本次没有独立启动数据库逐条重验。绿色CI未覆盖C01时序，不能单凭绿色将其关闭。

## 多轮全面复核的问题与根因

| 问题类别与原编号 | 根因 | 当前处理与应保留的经验 |
| --- | --- | --- |
| A-01 交付不可见 | 将本地存在当作远端可审核，版本和项目目录未绑定 | 独立分支/PR已有可读源码；交接必须注明项目、远端SHA、被测源码和证据，适当形成小检查点 |
| A-02、R05 完成证据失真风险 | 完成枚举与实现/验收脱节；只保护少数文件；空范围可能得到正常hash；mock可混代现实层级 | 已增加实际Git路径、全配置源码范围、非空检查、源码/产物hash及层级准入，维护反例已进入22项自测；结构检查仍不证明科学真实性 |
| A-03、R03、F02 输入真实性与换版 | 生命周期、输入有效性和历史版本混用；hash字符串不等于解析实际对象；错误类型或不可访问状态默认放行 | 已分离input_validity，保存解析对象/版本快照，换版使消费者及下游失效；继续在动作入口核对，而非只上传时核对 |
| R01、F04 返工和恢复身份混淆 | 首先漏掉review身份，随后误用生命周期revision充当新研究身份 | 新输入/review与同一执行的租约重试已分开，返工注入旧输出/findings；身份定义应在正常、返工、恢复三种时序下共同验证 |
| R02、F01 审核没有贯穿业务 | downstream_blocked只存储；调用方可选link决定实际保护；空ID相等扩大范围 | 已在业务门执行，通过实际输入及依赖推导范围；正反两个方向都测试，既不能漏挡也不能误挡无关工作 |
| R04、F03 后台运行与错误处理 | 内部执行函数可用被当成常驻worker可用；默认CLI未走通；两层同时fail导致原错误被覆盖 | 已接通循环、默认发现、单次结算和实际SIGTERM测试；未来验证用户实际启动方式和后续任务能否继续 |
| C01 接管后写入仍有漏口 | 只保护成功/失败结束，未覆盖创建/重启及旧读取与后续写入之间的时序 | 当前唯一新增P2，待定点修复；所有相关写入都须核对当前所有权，不能用单一成功路径测试推断全部受保护 |
| R06 备份校验与数据库恢复混同 | 文件解密/JSON结构成功被扩大为数据库已恢复 | 独立PostgreSQL回放已有证据；活动数据库切换、异地介质及真实主机灾难恢复继续明确未验证 |
| A-04 现实试点缺口 | 完整研发链设计被误读为现实接口已通 | W24已有具体试点档案，仍PREPARED；真实机构沟通、报价、委托、原始交付与验收各有实际证据后才提升状态 |

共同原因是：**证明“有这个功能或字段”多于证明“业务在异常和变化中仍遵守规则”**。补充最高思想有必要，但应沉淀上述稳定原则；代码行号、某次pytest数量和局部补丁留在本档案，不把思想主文件变成缺陷列表。

## 已同步的长期要求与后续路线

- 《最高思想》V0.10新增§14.5及D-031，固化可审核交付、实际行为、对象准入、历史/执行身份、故障连续性、证据范围与回归收口原则。
- 《技术路线与实施路径》V1.15在TR-19给出永久回归合同，TR-22细化W19的不可变bundle、运行绑定、变更影响、配置/DB迁移回退与集成交接，TR-25给未来Codex明确接手顺序。
- manifest同步既有RQ，不另建平行研发路线；复盘、脚本和结果作为supporting_artifacts纳入变化检测。归档或刷新hash不等于C01关闭。

C01关闭后按原路线继续：W19策略与迁移 → W20可靠性/成本/隔离回归 → W21跨包端到端 → W22明确授权的live接入 → W23部署交接；W24试点准备与现实证据覆盖持续作为主验证目标，不等全部软件打磨完才考虑。开始W19不需要把W01—W18整体标成VERIFIED，也不需要先把真人专家、真实模型、邮箱或现实外包验证“补成已完成”。

给继续开发Codex的具体指令：先只处理C01和受影响的AT-027，更新可审源码及验收；无新增可复现P1/P2后保持草稿，直接按TR-22开始W19。沿用最高思想的现实权限边界，不合并main，不重复向用户索取已获授权的常规工程决定。
