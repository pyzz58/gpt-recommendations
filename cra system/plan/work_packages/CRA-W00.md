# CRA-W00 建立技术基线与同步检查

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：verified；分支路线：baseline。
前置：无。必须按实际verified状态核实。

## 临床工作目标

维护理论和技术对应关系，以后能找到需要修改的模块。

## 对应理论和模块

理论：[CRA-R039](../../theory/REQUIREMENTS.md#cra-r039)、[CRA-R040](../../theory/REQUIREMENTS.md#cra-r040)、[CRA-R044](../../theory/REQUIREMENTS.md#cra-r044)

模块：[M13](../../architecture/modules/M13-traceability.md)、[M14](../../architecture/modules/M14-platform.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `tools/check_traceability.py` | code | 理论/技术同步检查 |
| `tools/traceability_lib.py` | code | 映射、指纹和生成视图 |
| `tests/test_traceability.py` | test | 漏同步拒绝案例 |
| `validation/BASELINE_STATUS.md` | document | 已有云端验证记录 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 固定CRA-R、M、CRA-W、CRA-S编号；变更有对应模块及影响记录。

## 实现步骤

1. 保留已验证基线及编号，不重复建设另一套理论源。
2. 维护生成视图与执行任务卡；技术细化不冒充新增业务决定。
3. 按证据区分设计、基础代码、完整业务实现和实际验证。

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

## 完成标准

原工作包验收：45条理论、14个模块、任务与验收关联；基础检查及反例测试在GitHub Actions运行。

- 已有同步检查及反例测试通过，原验证记录可追溯。

关联完整场景：CRA-S31、CRA-S32、CRA-S33。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- W00完成不代表数据库、界面或34个完整业务场景完成。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
