# CRA System

技术设计基线 v0.1 · 2026-10-29 · 来源：已讨论确认的 Notion v0.14 及本轮 GitHub 指示。

本系统帮助CRA把项目要求、实际资料、监查问题和后续报告连起来。工作主线是：上次遗留问题 → 按模板选几项形成访前信 → 到中心核实整改及其正确性 → 逐受试者监查 → 报告 → 下次继续追踪。

## 当前交付和实际状态

本目录包含完整的第一版技术设想、14个模块方案、45条固定编号理论、34个验收场景和16个开发工作包。另有可运行的理论同步检查和少量领域核心示例，用来验证“资料未见不等于漏录”“PD已上报不等于全部整改完成”等关键关系。

**这些还不是可投入真实监查的完整应用。** 数据库、界面、资料自动提取、OCR、模型、导出和实际部署的开发状态以[工作计划](plan/WORK_PLAN.md)为准；不能把“已设计”记为“已实现”，也不能把基础代码检查通过记为临床试用通过。

首轮工程检查已在GitHub云端通过：22项单元测试、同步检查及合成流程示例。详见[验证记录](validation/BASELINE_STATUS.md)。这仅完成CRA-W00，不代表下列临床功能已实现。

## 从哪里看

| 你想了解什么 | 入口 |
| --- | --- |
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

V1A先打通完整可试用工作流，包括项目资料、分层list、遗留整改、逐患者核查、EDC检验导入、人工确认源检验字段后的比对、分析支持、文件目录和报告。复杂照片识别按用户已允许的方式作为V1B接入；它仍使用同一比对服务，不重建另一套系统。自动识别范围始终仅限检验报告。

模型未配置时保留人工路径，并明确哪些自动能力不可用；这不等于自动提取已经完成。试用就绪条件另见质量验收，未达到时仅称模拟演示。

## 云上工作

代码、设计、任务和CI都保存在GitHub。本项目有独立GitHub Actions检查及Codespaces配置。除GitHub要求的根级工作流与开发环境入口外，本项目文件都在本目录；不修改其他项目。

当前仓库公开，只能提交可公开的设计、代码和合成案例。方案原件、IB、中心资料、受试者数据和真实导出文件应置于获准的私有存储环境，不能提交Git、写入公开Actions日志或测试附件。

进入Codespaces后可在本目录运行：

```bash
python3 tools/check_traceability.py
python3 -m unittest discover -s tests -v
PYTHONPATH=backend python3 -m cra_core.demo
```

上面执行的是工程基线检查及合成场景，没有真实数据、模型调用、外发消息或EDC写回。

## 理论和技术的维护关系

Git中的 `theory/requirements.json` 是开发可执行基线；Notion是本次临床讨论的来源。后续新增讨论先登记为变更，再在同一个提交/PR中更新对应理论与技术。GitHub检查会拦截漏映射、旧复核指纹、漏验收和缺少变更影响记录。

当前没有运行时Notion自动同步凭证或任务。仅修改Notion而未导入Git的内容，CI无法凭空发现；维护人必须先导入，或者后续实现只读差异导入。系统不会自动替人决定新架构或静默改写已签发报告。
