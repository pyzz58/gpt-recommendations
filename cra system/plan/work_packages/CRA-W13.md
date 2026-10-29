# CRA-W13 完成V1A模拟验收与试用准备

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

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 工程检查、合成验证和真实授权试用分别报告。
- 能力状态区分implemented/configured/validated/disabled，不能用整体绿色遮住关键缺口。

## 实现步骤

1. 为34场景登记真实证据、失败、修复及未覆盖用途，局部测试不当整场景完成。
2. 统计关键遗漏、误配、误报、错误关闭及查找、录入、复核、报告和返工总时间。
3. 检查权限、作业重试、历史、恢复及provider不可用路径。
4. 给出V1A能力与限制；缺模型、资料或授权时如实说明，不能宣布完整自动试用就绪。

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

## 完成标准

原工作包验收：公布能力/缺口清单、反例结果、总耗时和恢复测试；模型未配置、未授权或关键功能失败不能宣称完整试用就绪。

- 每项宣称具备的能力有证据或标未验证。
- 总时间有实测记录，不编造节时比例。
- 试用范围、人工步骤和实质缺口清楚。

关联完整场景：CRA-S01、CRA-S02、CRA-S03、CRA-S04、CRA-S05、CRA-S06、CRA-S07、CRA-S08、CRA-S09、CRA-S10、CRA-S11、CRA-S12、CRA-S13、CRA-S14、CRA-S15、CRA-S16、CRA-S17、CRA-S18、CRA-S19、CRA-S20、CRA-S21、CRA-S22、CRA-S23、CRA-S24、CRA-S25、CRA-S26、CRA-S27、CRA-S28、CRA-S29、CRA-S30、CRA-S31、CRA-S32、CRA-S33、CRA-S34。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不以22项基础测试或单次成功代表整个系统成熟。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
