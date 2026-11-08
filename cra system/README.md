# CRA System

技术执行基线 v0.5 · 2026-11-01 · 来源：Notion v0.14、GitHub指示、[用户八点澄清](theory/DECISIONS_20261029.md)及[2026-11-01审查修复](validation/REVIEW_REMEDIATION_20261101.md)。

本系统帮助CRA把项目要求、实际资料、监查问题和后续报告连起来。工作主线是：上次遗留问题 → 按模板选几项形成访前信 → 到中心核实整改及其正确性 → 逐受试者监查 → 报告 → 下次继续追踪。

V1A工程主线W01—W13及V1B复杂格式增强W14已完成。W13结论是：合成端到端路径可演示，但真实医院版式、代表性样本、CRA人工总耗时、OIDC/生产恢复和获授权试用仍未完成，不能称为完整临床试用就绪。W14只新增两页扫描和轻度旋转JPEG的声明范围。验收边界见[V1A验收记录](validation/V1A_ACCEPTANCE.md)及[W14评估](validation/OCR_EVALUATION.md)。

W15已完成部署候选、容器冒烟、配置/恢复检查和反馈模板，但状态保持`blocked`：尚未取得获准OIDC租户、私有生产服务、真实恢复环境和授权CRA试用。详见[授权试用记录](validation/AUTHORIZED_TRIAL.md)和[运行手册](deploy/RUNBOOK.md)。

## 本机合成体验

在Mac上双击`cra-local.command`，或在终端运行：

```bash
./cra-local.command start
```

入口为<http://127.0.0.1:15173>。所有服务只监听本机回环地址，数据库和文件保存在git-ignored的`runtime/`。完整操作顺序、预置资料和实际启用能力见[本机合成体验指南](synthetic_experience/README.md)。这不构成W15试用完成或临床验证。

## 完整技术实施入口

先看[第一性原理复核](audit/FIRST_PRINCIPLES_REVIEW_V04.md)及[完整实施路径](plan/IMPLEMENTATION_PATH.md)，再读[技术总路线](architecture/IMPLEMENTATION_ROUTE.md)和当前任务卡。阶段/里程碑/CI要求来自plan/implementation.json，逐项交付来自tasks.json；不另建独立任务状态。W01—W14已完成；W15部署候选已完成镜像构建、迁移、容器启动和健康检查，但真实授权试用仍阻塞。V1A主线选择器为complete。

## 当前交付和实际状态

本目录包含完整的第一版技术设想、14个模块方案、45条固定编号理论、40个验收场景和16个开发工作包。另有可运行的理论同步检查和少量领域核心示例，用来验证“资料未见不等于漏录”“PD已上报不等于全部整改完成”等关键关系。

**这些还不是可投入真实监查的完整应用。** 数据库、界面、资料自动提取、OCR、模型、导出和实际部署的开发状态以[工作计划](plan/WORK_PLAN.md)为准；不能把“已设计”记为“已实现”，也不能把基础代码检查通过记为临床试用通过。

W04已在真实PostgreSQL上完成有出处规则候选、项目共享方案的中心独立采用日、普通中文段落/表格/脚注/Q&A保留、三值条件、手动启用日、事件日适用性和四层list；详见[W04交付记录](validation/W04_STATUS.md)。W05已在此底座上完成结构化患者事实、规则驱动访视窗口、门槛/例外与未知日期状态、来源/日期精度保留、分类断点与局部跳过/恢复；详见[W05交付记录](validation/W05_STATUS.md)。W06已完成从合成历史DOCX/XLSX/问题文字预览并确认遗留、稳定Issue与分项Action、PD上报独立确认、CRA点击确认/重开、Query期限依据和访前选择；详见[W06交付记录](validation/W06_STATUS.md)。W07已完成多sheet EDC Excel公式/缓存预览、映射与范围确认、同日初检/复查实例分离及不可变合成检验快照；详见[W07交付记录](validation/W07_STATUS.md)。W08已完成选择文字PDF、清晰合成PNG和中文页眉上下文PDF的实际读取、完整更正链、来源坐标、参考范围独立比较、持久异步识别/重试、集中复核及M06待办关联；详见[W08交付记录](validation/W08_STATUS.md)和[支持范围](validation/LAB_AUTOMATION_SCOPE.md)。W09已完成AE、SAE、相关性、预期性、AESI/DLT及PD维度分离、具体事件事实归属、检验一致异常/跳过/stale衔接、具体问题、医学答复和独立模型运行；固定本地模型只选择允许解释模板和证据ID，不能作最终医学判断；详见[W09交付记录](validation/W09_STATUS.md)。W10已完成原ISF/TMF目录直接对照、增量缺件/补齐/核实状态、跨版本变化、项目来源启动/关闭清单和简洁交接摘要；详见[W10交付记录](validation/W10_STATUS.md)。W11已完成受控DOCX/XLSX模板映射、选取式访视信、旧问题/新发现监查报告、不可变签发快照、同源track及独立交付事件；详见[W11交付记录](validation/W11_STATUS.md)。W12已完成四阶段连续监查、服务端恢复、两次真实浏览器API流程以及平板视口上传/查看/确认与电脑端接续；详见[W12交付记录](validation/W12_STATUS.md)。W13已完成40场景证据账、逐能力状态、机器耗时、未达标项、用途风险及恢复缺口汇总；详见[V1A验收记录](validation/V1A_ACCEPTANCE.md)。W14已完成两页图像扫描、兼容续页表头、键值报告上下文和0.5度JPEG的独立合成验证，并以原图坐标进入既有比较服务；详见[W14评估](validation/OCR_EVALUATION.md)。这些provider只验证声明的合成子集，不代表任意方案自动理解、完整病史、真实医院版式、EDC导出完整、安全分析临床质量或临床安全结论。真实设备、弱网、代表性完整自动检验评估、人工总耗时和真实授权试用仍待后续工作包。

历史v0.2技术复核：[2026-10-29审查报告](audit/TECHNICAL_ROUTE_REVIEW_20261029.md)。总体架构保留，已登记10项开放问题及修订/关闭标准；含云端复现的任务完成检查缺口。最新[v0.4复核](audit/FIRST_PRINCIPLES_REVIEW_V04.md)补齐执行契约、自动检验路径、验证和源码绑定完成门槛。[本轮澄清及设计响应](audit/USER_CLARIFICATION_RESPONSE_20261029.md)已将用户决定同步到对应区域。2026-11-01的13项审查问题已按[关闭映射](validation/REVIEW_REMEDIATION_20261101.md)修复，W01—W09在[run 41245438323](https://github.com/pyzz58/gpt-recommendations/actions/runs/41245438323)重新完成源码绑定验证；这不关闭真实临床资料、代表性和节时验证缺口。

第二轮独立复核只发现的03/04/08三项残留已按[补充关闭记录](validation/REMEDIATION_RECHECK_CLOSURE_20261101.md)修复，W04—W09在[run 41248250769](https://github.com/pyzz58/gpt-recommendations/actions/runs/41248250769)重新通过源码绑定CI；复核探针的“5 passed”仅表示缺陷复现，未作为产品验收。

随后独立正向验收发现的`RuleBranch.target_node_ids`分支目标残留已按[分支门禁与防复发记录](validation/BRANCH_GATE_AND_PREVENTION_20261101.md)修复；W05—W09在[run 41251079001](https://github.com/pyzz58/gpt-recommendations/actions/runs/41251079001)重新通过，当前审核门禁已纳入next_task与task_evidence。

## 从哪里看

| 你想了解什么 | 入口 |
| --- | --- |
| 直接交给Codex从第一项编程 | [Codex开发入口](CODEX_START_HERE.md)及[逐项任务卡](plan/CODEX_TASKS.md) |
| 实际技术路线和代码结构 | [实施路线](architecture/IMPLEMENTATION_ROUTE.md) |
| 系统按临床工作怎样使用 | [第一版业务基线](theory/BASELINE.md) |
| 每条理论到底要求什么 | [45条理论清单](theory/REQUIREMENTS.md) |
| 某条理论对应哪块技术 | [理论—模块—任务—验收对照](traceability/INDEX.md) |
| 整体怎么组成、为什么这样选择技术 | [系统架构](architecture/SYSTEM.md)及[技术决策](architecture/DECISIONS.md) |
| 每一模块具体怎么实现 | [模块目录](architecture/MODULES.md) |
| 数据、接口、AI与文件解析怎么做 | [数据模型](architecture/DATA_MODEL.md)、[接口约定](architecture/API_CONTRACTS.md)、[解析与AI方案](architecture/AI_AND_PARSING.md) |
| 按什么顺序真正开发 | [开发工作计划](plan/WORK_PLAN.md) |
| 理论变更以后怎样同步 | [同步规则](traceability/SYNC_POLICY.md) |
| 如何在GitHub云上开发及验收 | [云上开发与发布](architecture/CLOUD_AND_RELEASE.md)、[质量验收](architecture/QUALITY.md) |

## 第一版范围

四个业务模块：启动、访视、中心关闭、交接。它们共享底层资料、规则、受试者事实、问题与输出，采用不同清单和模板。交接保持简洁。

V1A主线包含项目资料、条件分支list、遗留提醒与用户点击确认、逐患者核查、检验报告自动读取及EDC Excel核对、分析支持、简单目录对照和报告。手动补录只用于少量失败；用户拒绝补数据后跳过依赖路径，其他工作继续。W08交付支持格式的自动读取，V1B/W14只增强复杂格式，不再后置首次自动识别。自动识别范围始终仅限检验报告。

模型未配置时保留人工路径，并明确哪些自动能力不可用；这不等于自动提取已经完成。试用就绪条件另见质量验收，未达到时仅称模拟演示。

## 云上工作

代码、设计、任务和CI都保存在GitHub。本项目有独立GitHub Actions检查及Codespaces配置。除GitHub要求的根级工作流与开发环境入口外，本项目文件都在本目录；不修改其他项目。

当前仓库公开，只能提交可公开的设计、代码和合成案例。方案原件、IB、中心资料、受试者数据和真实导出文件应置于获准的私有存储环境，不能提交Git、写入公开Actions日志或测试附件。

进入Codespaces后，开发容器会安装锁定依赖、启动PostgreSQL、执行迁移并写入公开合成项目。可运行：

```bash
python3 tools/check_traceability.py
uv run --frozen pytest -q
npm --prefix web test
uv run --frozen uvicorn cra_app.main:app --app-dir backend --host 0.0.0.0 --port 8000
uv run --frozen python -m cra_app.documents.worker
npm --prefix web run dev
```

API使用8000、Vite使用5173，两个转发端口均设为private。资料上传后由独立Procrastinate worker解析；本地开发默认只写`runtime/private`，不会公开文件。上面只使用合成数据，没有真实资料、OCR/模型调用、外发消息或EDC写回。

## 理论和技术的维护关系

Git中的 `theory/requirements.json` 是开发可执行基线；Notion是本次临床讨论的来源。后续新增讨论先登记为变更，再在同一个提交/PR中更新对应理论与技术。GitHub检查会拦截漏映射、旧复核指纹、漏验收和缺少变更影响记录。

当前没有运行时Notion自动同步凭证或任务。仅修改Notion而未导入Git的内容，CI无法凭空发现；维护人必须先导入，或者后续实现只读差异导入。系统不会自动替人决定新架构或静默改写已签发报告。

最新工程验证为[本机合成源文件/EDC/安全核查工作台、W12稳定性修复与最终证据审计CI](https://github.com/pyzz58/gpt-recommendations/actions/runs/42447288132)。W01—W14已按源码绑定和任务专属CI完成；W12两轮监查端到端在阶段切换竞态修复后通过，W15仍为外部条件阻塞。真实设备/弱网、代表性完整自动检验评估、人工总耗时、获准生产部署和授权试用仍待后续验证。

新版空白项目模板驱动工作台见[操作指南](synthetic_experience/WORKBENCH_USER_GUIDE.md)和[实际验收结果](validation/WORKBENCH_USABILITY_ACCEPTANCE.md)；旧完成证据保留在任务历史，W15边界不变。

开源复用修订v0.5：[14项目核对与替代边界](architecture/REUSE_ASSESSMENT.md)，[可直接发给Codex的第一段](plan/CODEX_FIRST_MESSAGE.md)。依赖选择已同步到任务；尚未安装、集成或做临床性能验证。
