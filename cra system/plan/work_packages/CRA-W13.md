# CRA-W13 完成自动检验主线验收与试用准备

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W12。必须按实际verified状态核实。

## 临床工作目标

明确第一版哪些功能可用、哪些需人工、哪些尚未验证。

## 对应理论和模块

理论：[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R037](../../theory/REQUIREMENTS.md#cra-r037)、[CRA-R040](../../theory/REQUIREMENTS.md#cra-r040)、[CRA-R044](../../theory/REQUIREMENTS.md#cra-r044)

模块：[M14](../../architecture/modules/M14-platform.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `validation/V1A_ACCEPTANCE.md` | document | 完整场景和能力限制 |
| `validation/capability-manifest.json` | config | 逐能力状态及证据 |
| `tests/acceptance/test_v1a.py` | test | 固定合成反例 |
| `validation/TIME_STUDY.md` | document | 总工作时间 |
| `deploy/restore-check.md` | document | 恢复验证与缺口 |
| `validation/USE_CASE_VALIDATION.md` | document | 按用途风险、独立样本、版本及暂停恢复策略 |
| `tools/build_validation_report.py` | code | 合成/获授权证据的去敏汇总，不虚构试用结果 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 工程检查、合成验证和真实授权试用分别报告。
- 能力状态区分implemented/configured/validated/disabled，不能用整体绿色遮住关键缺口。

## 进入条件与交接

阶段：P5；CI profile：CRA-W13

- 进入：W12端到端通过，开发样例与独立评估已分离。
- 交接：40场景实证、逐用途能力/风险记录、自动覆盖和总耗时、明确可试用范围与未达标结论。

技术输入：[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)、[LAB_AUTOMATION.md](../../architecture/LAB_AUTOMATION.md)


## 实现步骤

1. 为40场景登记输入、正确预期/依据、样本来源及开发/独立评估划分，记录真实证据、失败和未覆盖用途；局部测试不当完整场景通过。
2. 统计关键遗漏、错配、误报、错误关闭、自动读取可用比例、人工更正/补录比例，以及查找/导入/确认/核对/报告/返工总时间，与同一任务原流程比较。
3. 检查权限、作业重试、历史、恢复及provider不可用路径。
4. 给出V1A能力与限制；缺模型、资料或授权时如实说明，不能宣布完整自动试用就绪。
5. 按用途记录错误后果、验证责任和能力暂停/恢复；发布验证职责不增加CRA每次监查审批。
6. 区分离线汇总可完成与核心自动能力未达标，provider在W08/W09有明确验证落点，W15负责实际环境和获授权试用。

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

- [to_implement] 固定验收反例

```bash
uv run --frozen pytest -q tests/acceptance/test_v1a.py
```

- [to_implement] 完整流程回归

```bash
npm --prefix web run test:e2e -- --project=chromium
```

- [to_implement] 逐用途能力/证据/风险和未达标项的汇总检查

```bash
uv run --frozen python tools/build_validation_report.py --check
```

## 完成标准

原工作包验收：逐能力给出40场景、独立样本/实际provider证据、关键错误、自动覆盖及人工负担和总耗时；未验证核心自动能力必须记录未达标，不能以人工版替代。

- 每项宣称具备的能力有证据或标未验证。
- 总时间有实测记录，不编造节时比例。
- 试用范围、人工步骤和实质缺口清楚。
- 无实际识别证据的版本不得被称为实现核心减负；无法获得环境时如实列provider未验证和剩余工作。

关联完整场景：CRA-S01、CRA-S02、CRA-S03、CRA-S04、CRA-S05、CRA-S06、CRA-S07、CRA-S08、CRA-S09、CRA-S10、CRA-S11、CRA-S12、CRA-S13、CRA-S14、CRA-S15、CRA-S16、CRA-S17、CRA-S18、CRA-S19、CRA-S20、CRA-S21、CRA-S22、CRA-S23、CRA-S24、CRA-S25、CRA-S26、CRA-S27、CRA-S28、CRA-S29、CRA-S30、CRA-S31、CRA-S32、CRA-S33、CRA-S34、CRA-S35、CRA-S36、CRA-S37、CRA-S38、CRA-S39、CRA-S40。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不以22项基础测试或单次成功代表整个系统成熟。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
