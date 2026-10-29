# CRA-W08 实现人工录入检验与确定性核对

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W06、CRA-W07。必须按实际verified状态核实。

## 临床工作目标

人工确认源检验字段后，与EDC完成可解释的匹配、核对和差异记录。

## 对应理论和模块

理论：[CRA-R013](../../theory/REQUIREMENTS.md#cra-r013)、[CRA-R015](../../theory/REQUIREMENTS.md#cra-r015)、[CRA-R016](../../theory/REQUIREMENTS.md#cra-r016)、[CRA-R017](../../theory/REQUIREMENTS.md#cra-r017)、[CRA-R034](../../theory/REQUIREMENTS.md#cra-r034)、[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R038](../../theory/REQUIREMENTS.md#cra-r038)

模块：[M08](../../architecture/modules/M08-laboratory.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/laboratory/models.py` | code | 报告、确认、匹配和比较 |
| `backend/cra_app/laboratory/matching.py` | code | 对象和重复实例匹配 |
| `backend/cra_app/laboratory/comparison.py` | code | Decimal与单位/逻辑比较 |
| `backend/cra_app/laboratory/service.py` | code | 确认、跳过及结果复用 |
| `backend/cra_app/laboratory/api.py` | code | 源字段和核对接口 |
| `web/src/features/laboratory/LabComparison.tsx` | code | 并排核查 |
| `tests/integration/test_laboratory.py` | test | 错配、单位、边界和跳过 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- LabComparison返回match_status、field_results、unknowns和scope。
- 手动补录标为用户提供；未确认识别和跳过不得视为已核实。

## 实现步骤

1. 先实现人工源字段确认及对应存储，OCR以后从同一接口进入。
2. 匹配中心、患者、时间、项目、样本、访视、初检复查和报告修订；歧义不按数值近似挑选。
3. 用Decimal及批准映射比较，保留大于小于等符号，未知单位不猜换算。
4. 分别返回一致、差异、单位待核实、本次未见、无法识别和跳过，限定结论范围。
5. 并排查看和记录差异，关联M06待办，不直接自动认定PD或临床安全。

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

- [to_implement] 匹配、单位、精度及人工路径

```bash
uv run --frozen pytest -q tests/integration/test_laboratory.py
```

## 完成标准

原工作包验收：用户确认源检验字段后先匹配再核对；单位、初检复查、修订、跳过和歧义均有明确结果。

- 初检、复查和修订不误配，多候选明确待核实。
- 带比较符结果不被猜成精确值。
- OCR关闭仍可工作，用户跳过后不重复追问且报告不写正常。

关联完整场景：CRA-S13、CRA-S19、CRA-S20、CRA-S21、CRA-S22。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 此步不宣称已有照片识别；由W14接入。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
