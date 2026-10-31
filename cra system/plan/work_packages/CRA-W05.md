# CRA-W05 实现患者事实、锚点与核查断点

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：in_progress；分支路线：v1a。
前置：CRA-W04。必须按实际verified状态核实。

## 临床工作目标

识别当前患者阶段，并按不同资料类别接续核查位置。

## 对应理论和模块

理论：[CRA-R010](../../theory/REQUIREMENTS.md#cra-r010)、[CRA-R011](../../theory/REQUIREMENTS.md#cra-r011)、[CRA-R012](../../theory/REQUIREMENTS.md#cra-r012)、[CRA-R028](../../theory/REQUIREMENTS.md#cra-r028)、[CRA-R034](../../theory/REQUIREMENTS.md#cra-r034)、[CRA-R041](../../theory/REQUIREMENTS.md#cra-r041)、[CRA-R045](../../theory/REQUIREMENTS.md#cra-r045)

模块：[M04](../../architecture/modules/M04-subjects.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/subjects/models.py` | code | 患者、事实、访视与断点 |
| `backend/cra_app/subjects/service.py` | code | 事实复用和修订 |
| `backend/cra_app/subjects/calendar.py` | code | 锚点及窗口 |
| `backend/cra_app/subjects/api.py` | code | 时间线和阶段要求 |
| `web/src/features/subjects/SubjectTimeline.tsx` | code | 患者时间线 |
| `tests/integration/test_subjects.py` | test | 日期精度及分类断点 |
| `backend/cra_app/subjects/context_import.py` | code | 患者锚点与允许结构化上下文导入 |
| `migrations/versions/0004_subjects_coverage.py` | migration | 患者身份映射、不可变事实修订、访视要求、分类断点和局部核查决定 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- ClinicalFact区分原记录、CRA确认、他人答复和模型建议。
- 计算输出采用的锚点和规则版本，未知起点不产生假日期。
- 每项判断列needed_fact_keys/允许来源/受影响路径及可继续事项；CheckDecision保存对象/事项/期间范围，拒绝后not_checked_by_user，不重复追问。

## 进入条件与交接

阶段：P2；CI profile：CRA-W05

- 进入：规则版本和三值逻辑可用，准备患者上下文合成表。
- 交接：患者/锚点/分类断点及缺口拒绝/恢复契约，日期精度和来源保留。

技术输入：[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[WORKFLOW_CONTRACTS.md](../../architecture/WORKFLOW_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 增加患者、事实、访视实例和分类断点迁移，复用M03规则。
2. 从授权结构化输入/EDC或人工记录获取事实，保留身份映射和来源。
3. 分开计划和实际时间；date-only不补时分秒，窗口例外采用实际规则。
4. 各资料类别分别保存正常范围简记和未核实范围，复用已确认信息。
5. 事实修订只使关联判断待复核，保留旧事实及历史报告。
6. 缺锚点等关键数据只提示相应缺口，提供补充或不核查相关路径；拒绝后不再后台推断该缺失数据，其他工作继续。
7. 保存可恢复的跳过选择，输入变化仅提示可恢复，不自动取消；不用跳过产生待整改Issue。

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

- [available] 锚点、日期缺失、修订及断点

```bash
uv run --frozen pytest -q tests/integration/test_subjects.py
```

- [available] 患者事实、访视窗口、断点和局部核查决定的OpenAPI/前端契约

```bash
npm --prefix web run api:check
```

- [available] 患者时间线、局部跳过恢复和分类断点前端

```bash
npm --prefix web test && npm --prefix web run typecheck && npm --prefix web run build
```

## 完成标准

原工作包验收：EDC/源信息或人工事实导入后可复用；按适用规则计算访视要求；不同资料类别断点分别恢复。

- 不同患者及类别断点不混用。
- 已确认信息不重复填写。
- 日期计算和未知结果均解释来源与版本。
- 缺输注日拒绝补充后时间窗路径停止，已具备身份的检验数值核对仍可运行；选择不被扩大到全部患者。

关联完整场景：CRA-S08、CRA-S09、CRA-S36。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不把上传的局部资料称作完整病史。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
