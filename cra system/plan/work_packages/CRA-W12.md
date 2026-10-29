# CRA-W12 串联四阶段界面与一次完整监查

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W08、CRA-W09、CRA-W10、CRA-W11。必须按实际verified状态核实。

## 临床工作目标

CRA能连续完成一次监查，并在下一次按原问题继续跟进。

## 对应理论和模块

理论：[CRA-R001](../../theory/REQUIREMENTS.md#cra-r001)、[CRA-R006](../../theory/REQUIREMENTS.md#cra-r006)、[CRA-R012](../../theory/REQUIREMENTS.md#cra-r012)、[CRA-R017](../../theory/REQUIREMENTS.md#cra-r017)、[CRA-R026](../../theory/REQUIREMENTS.md#cra-r026)、[CRA-R028](../../theory/REQUIREMENTS.md#cra-r028)、[CRA-R032](../../theory/REQUIREMENTS.md#cra-r032)、[CRA-R033](../../theory/REQUIREMENTS.md#cra-r033)、[CRA-R037](../../theory/REQUIREMENTS.md#cra-r037)、[CRA-R045](../../theory/REQUIREMENTS.md#cra-r045)

模块：[M05](../../architecture/modules/M05-monitoring.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `web/src/pages/MonitoringVisitPage.tsx` | code | 完整访视工作区 |
| `web/src/pages/SubjectReviewPage.tsx` | code | 患者和分层list |
| `web/src/pages/HandoverPage.tsx` | code | 简洁交接 |
| `web/playwright.config.ts` | config | 实际API端到端配置 |
| `web/tests/e2e/monitoring-flow.spec.ts` | test | 两次监查完整路径 |
| `tests/integration/test_visit_continuity.py` | test | 刷新及重新登录接续 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 完整流程使用真实API和临时PostgreSQL，不能只以静态前端mock证明持久化。
- 界面以服务端事实为准，不维护第二套问题完成算法。

## 进入条件与交接

阶段：P5；CI profile：CRA-W12

- 进入：既有各模块服务及页面实际可用，完整场景使用真实API和临时PostgreSQL。
- 交接：两次监查浏览器流程、刷新/重登/切中心/重试不丢状态，缺口和异常不混同。

技术输入：[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 串联已有服务和页面，保持现场先复核遗留再逐患者的常规顺序。
2. 合成前次DOCX报告/XLSX track整理→访前选择→开始遗留提醒/展开→CRA点击确认→上传检验自动提取/对照→分析及报告→下次继续。
3. 验证正常范围简记、低可信/异常集中复核、缺数据拒绝后仅跳过相关路径和主动恢复，不能以大量补录替代主流程。
4. 刷新、重新登录、切中心及重试后状态正确，紧急入口不被普通顺序挡住。
5. 普通界面使用临床工作语言，必要技术详情放到来源或诊断详情中。

## 验证命令

available表示当前已有入口；to_implement表示本任务必须先实现该入口，不能现在就声称已经运行。进入后续阶段使用合成数据和临时服务。

- [available] 理论/技术/任务卡同步

```bash
python3 tools/check_traceability.py
```

- [available] 现有基础与反例检查

```bash
python3 -m unittest discover -s tests -v
```

- [to_implement] 界面类型

```bash
npm --prefix web run typecheck
```

- [to_implement] 界面构建

```bash
npm --prefix web run build
```

- [to_implement] 真实API两次监查

```bash
npm --prefix web run test:e2e -- --project=chromium
```

- [to_implement] 持久化和接续

```bash
uv run --frozen pytest -q tests/integration/test_visit_continuity.py
```

## 完成标准

原工作包验收：模拟前次报告→访前信→到中心复核→新受试者核查→报告→下一次接续全部完成；用户只需临床操作。

- 重开系统仍能找到同一问题的处理历史。
- 选2条保留全部问题、PD与更正分别完成、下次继续均在完整路径验证。
- 四阶段共享事实而不是四套数据库。
- 真实API端到端路径包含文件自动提取和Excel导入；provider真实验证缺口如实说明，mock成功不能代表识别性能。

关联完整场景：CRA-S09、CRA-S10、CRA-S11、CRA-S12、CRA-S13、CRA-S14、CRA-S21、CRA-S27、CRA-S28、CRA-S29、CRA-S35、CRA-S36、CRA-S39、CRA-S40。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 浏览器演示成功不能称真实临床用途已经验证。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
