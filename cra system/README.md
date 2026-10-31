# CRA System

技术执行基线 v0.5 · 2026-10-29 · 来源：Notion v0.14、GitHub指示及[用户八点澄清](theory/DECISIONS_20261029.md)。

本系统帮助CRA把项目要求、实际资料、监查问题和后续报告连起来。工作主线是：上次遗留问题 → 按模板选几项形成访前信 → 到中心核实整改及其正确性 → 逐受试者监查 → 报告 → 下次继续追踪。

## 完整技术实施入口

先看[第一性原理复核](audit/FIRST_PRINCIPLES_REVIEW_V04.md)及[完整实施路径](plan/IMPLEMENTATION_PATH.md)，再读[技术总路线](architecture/IMPLEMENTATION_ROUTE.md)和当前任务卡。阶段/里程碑/CI要求来自plan/implementation.json，逐项交付来自tasks.json；不另建独立任务状态。W01数据/权限底座及W02 API/工作台壳已完成；下一项为W03，不代表后续临床功能已实现。

## 当前交付和实际状态

本目录包含完整的第一版技术设想、14个模块方案、45条固定编号理论、40个验收场景和16个开发工作包。另有可运行的理论同步检查和少量领域核心示例，用来验证“资料未见不等于漏录”“PD已上报不等于全部整改完成”等关键关系。

**这些还不是可投入真实监查的完整应用。** 数据库、界面、资料自动提取、OCR、模型、导出和实际部署的开发状态以[工作计划](plan/WORK_PLAN.md)为准；不能把“已设计”记为“已实现”，也不能把基础代码检查通过记为临床试用通过。

W02已在真实PostgreSQL和实际devcontainer中通过API、合成登录、授权中心恢复、前端测试/构建、OpenAPI与运行时smoke；详见[W02交付记录](validation/W02_STATUS.md)。正式机构OIDC尚未取得可用身份源验证，资料、监查、检验、报告和真实试用仍待后续工作包。

历史v0.2技术复核：[2026-10-29审查报告](audit/TECHNICAL_ROUTE_REVIEW_20261029.md)。总体架构保留，已登记10项开放问题及修订/关闭标准；含云端复现的任务完成检查缺口。最新[v0.4复核](audit/FIRST_PRINCIPLES_REVIEW_V04.md)补齐执行契约、自动检验路径、验证和源码绑定完成门槛；W01底座可推进，性能与真实用途证据仍待实现。[本轮澄清及设计响应](audit/USER_CLARIFICATION_RESPONSE_20261029.md)已将用户决定同步到对应区域；审查项未因改完文档而冒称实现或验证完成。

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
npm --prefix web run dev
```

API使用8000、Vite使用5173，两个转发端口均设为private。上面只使用合成数据，没有真实资料、模型调用、外发消息或EDC写回。

## 理论和技术的维护关系

Git中的 `theory/requirements.json` 是开发可执行基线；Notion是本次临床讨论的来源。后续新增讨论先登记为变更，再在同一个提交/PR中更新对应理论与技术。GitHub检查会拦截漏映射、旧复核指纹、漏验收和缺少变更影响记录。

当前没有运行时Notion自动同步凭证或任务。仅修改Notion而未导入Git的内容，CI无法凭空发现；维护人必须先导入，或者后续实现只读差异导入。系统不会自动替人决定新架构或静默改写已签发报告。

最新v0.4工程验证：[40项测试及云端证据](validation/IMPLEMENTATION_V04_STATUS.md)。W01/W02已按源码绑定和任务专属CI完成；W03及之后的临床资料能力仍待实际编程和对应用途验证。

开源复用修订v0.5：[14项目核对与替代边界](architecture/REUSE_ASSESSMENT.md)，[可直接发给Codex的第一段](plan/CODEX_FIRST_MESSAGE.md)。依赖选择已同步到任务；尚未安装、集成或做临床性能验证。
