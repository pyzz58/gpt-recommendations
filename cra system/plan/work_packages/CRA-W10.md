# CRA-W10 实现中心文件目录和其他阶段清单

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W04、CRA-W06。必须按实际verified状态核实。

## 临床工作目标

跟进ISF/TMF缺件，提供启动、关闭和简洁交接清单。

## 对应理论和模块

理论：[CRA-R001](../../theory/REQUIREMENTS.md#cra-r001)、[CRA-R003](../../theory/REQUIREMENTS.md#cra-r003)、[CRA-R006](../../theory/REQUIREMENTS.md#cra-r006)、[CRA-R024](../../theory/REQUIREMENTS.md#cra-r024)、[CRA-R028](../../theory/REQUIREMENTS.md#cra-r028)、[CRA-R032](../../theory/REQUIREMENTS.md#cra-r032)、[CRA-R033](../../theory/REQUIREMENTS.md#cra-r033)、[CRA-R045](../../theory/REQUIREMENTS.md#cra-r045)

模块：[M05](../../architecture/modules/M05-monitoring.md)、[M10](../../architecture/modules/M10-site_files.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/site_files/models.py` | code | 目录和文件状态 |
| `backend/cra_app/site_files/service.py` | code | 缺件、更新及复核 |
| `backend/cra_app/site_files/api.py` | code | 目录接口 |
| `backend/cra_app/monitoring/stages.py` | code | 阶段策略 |
| `web/src/features/site-files/DirectoryReview.tsx` | code | 目录核查 |
| `web/src/features/monitoring/StageChecklist.tsx` | code | 分阶段清单 |
| `tests/integration/test_site_files.py` | test | 目录、阶段和交接 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 应有、已取得、已核实合格分别记录；目录更新保留旧缺件历史。
- 交接引用原Issue；关闭记录项目组意见，系统不替其批准。
- reference_only是可用基础对照模式，未识别目录范围不称全部核查合格；补件由用户点击确认即可。

## 进入条件与交接

阶段：P4；CI profile：CRA-W10

- 进入：原目录文件与M06问题服务可用。
- 交接：原目录直接对照及简单缺件状态，启动/关闭/交接复用已有资料和问题。

技术输入：[WORKFLOW_CONTRACTS.md](../../architecture/WORKFLOW_CONTRACTS.md)、[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)


## 实现步骤

1. 直接复用M02上传的原目录，提供reference_only对照和可选页/行/用户标注及简单状态；可识别部分再建立条目，不要求重录整本。
2. 显示上次缺件及新增变化，复用M06行动，不每次重复建问题。
3. 按项目资料配置启动/关闭要求，保存具体来源与缺口。
4. 无遗留简述；有遗留直接交代前因后果、现状及继续工作，不新造审批链。

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

- [to_implement] 目录新增、补齐和阶段复用

```bash
uv run --frozen pytest -q tests/integration/test_site_files.py
```

## 完成标准

原工作包验收：原ISF/TMF目录可直接作为对照，附简要缺件与进展；结构化逐步建立，阶段和简洁交接复用原记录。

- 核实补齐后保留历史，下次不重录整个目录。
- 启动/关闭采用项目要求，清单完成不等于中心获准关闭。
- 交接简洁且后续事项清楚。
- 不先建全量结构目录也可对照原文件，W06已存问题接入后编号/状态不变。

关联完整场景：CRA-S12、CRA-S26。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不扩为eTMF替代产品或复杂中心运营平台。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
