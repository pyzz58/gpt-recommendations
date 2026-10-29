# CRA-W07 实现EDC Excel检验快照导入

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W05。必须按实际verified状态核实。

## 临床工作目标

可靠导入EDC检验Excel，并明确本次导出包含的记录范围。

## 对应理论和模块

理论：[CRA-R013](../../theory/REQUIREMENTS.md#cra-r013)、[CRA-R014](../../theory/REQUIREMENTS.md#cra-r014)、[CRA-R015](../../theory/REQUIREMENTS.md#cra-r015)、[CRA-R034](../../theory/REQUIREMENTS.md#cra-r034)

模块：[M07](../../architecture/modules/M07-edc_import.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/edc_import/models.py` | code | 快照、映射和原始行 |
| `backend/cra_app/edc_import/service.py` | code | 预览与幂等确认 |
| `backend/cra_app/edc_import/excel.py` | code | 检验Excel解析 |
| `backend/cra_app/edc_import/api.py` | code | 导入接口 |
| `web/src/features/edc/ImportPreview.tsx` | code | 映射、实例和范围 |
| `tests/integration/test_edc_import.py` | test | 多sheet、公式及导出范围 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- EDCSnapshot保留导出时间/范围、表单、原始行、映射版本和重复实例。
- 本次未见返回not_seen_in_export，不直接判未录入。

## 实现步骤

1. 预览sheet/row/cell，分别保存原始字符串、公式及缓存，不执行宏。
2. 复用已确认列映射，核实新患者/访视/重复实例歧义。
3. 事务保存不可变快照和范围，重复导入幂等，更正版另建快照。
4. 向M08提供标准检验记录，同时保留原值、单位、时间精度和原始定位。

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

- [to_implement] 映射、范围、复导和公式

```bash
uv run --frozen pytest -q tests/integration/test_edc_import.py
```

## 完成标准

原工作包验收：预览、列映射、实例和导出范围确认后导入；复导不复制；导出缺项不直接判漏录。

- 同日初检/复查不被合并。
- 过滤导出不会产生虚假漏录结论。
- 标准字段可回到原Excel位置。

关联完整场景：CRA-S18、CRA-S19。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不写回EDC，不扩展用药/样本自动核对。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
