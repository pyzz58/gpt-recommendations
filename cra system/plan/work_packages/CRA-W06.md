# CRA-W06 实现遗留整理、提醒与点击确认整改

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W05。必须按实际verified状态核实。

## 临床工作目标

开始时不漏上次遗留，点开知道问题与处理办法，CRA沟通核查后一次点击记录完成。

## 对应理论和模块

理论：[CRA-R001](../../theory/REQUIREMENTS.md#cra-r001)、[CRA-R009](../../theory/REQUIREMENTS.md#cra-r009)、[CRA-R012](../../theory/REQUIREMENTS.md#cra-r012)、[CRA-R020](../../theory/REQUIREMENTS.md#cra-r020)、[CRA-R021](../../theory/REQUIREMENTS.md#cra-r021)、[CRA-R022](../../theory/REQUIREMENTS.md#cra-r022)、[CRA-R023](../../theory/REQUIREMENTS.md#cra-r023)、[CRA-R025](../../theory/REQUIREMENTS.md#cra-r025)、[CRA-R026](../../theory/REQUIREMENTS.md#cra-r026)、[CRA-R027](../../theory/REQUIREMENTS.md#cra-r027)、[CRA-R028](../../theory/REQUIREMENTS.md#cra-r028)、[CRA-R031](../../theory/REQUIREMENTS.md#cra-r031)、[CRA-R041](../../theory/REQUIREMENTS.md#cra-r041)、[CRA-R043](../../theory/REQUIREMENTS.md#cra-r043)、[CRA-R045](../../theory/REQUIREMENTS.md#cra-r045)

模块：[M05](../../architecture/modules/M05-monitoring.md)、[M06](../../architecture/modules/M06-issues.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/issues/models.py` | code | 问题、分项行动和历史 |
| `backend/cra_app/issues/service.py` | code | PD上报与整改复核 |
| `backend/cra_app/issues/deadlines.py` | code | 有依据的Query期限 |
| `backend/cra_app/issues/api.py` | code | 问题与行动接口 |
| `backend/cra_app/monitoring/service.py` | code | 本次监查主线 |
| `backend/cra_app/monitoring/api.py` | code | 工作台与核查范围 |
| `web/src/features/issues/CarryoverReview.tsx` | code | 遗留复核底稿 |
| `web/src/features/issues/PrevisitSelection.tsx` | code | 访前选择几项 |
| `tests/integration/test_issues.py` | test | 分项完成、改错和跨次跟进 |
| `backend/cra_app/issues/carryover_import.py` | code | 历史报告/track/文字自动整理与幂等关联 |
| `tests/integration/test_carryover_import.py` | test | 前次资料进入本次遗留与重复导入 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- IssueView保留原问题、位置、建议及来源、已知进展、动作和历史；旧资料未载明项保持unknown。
- confirm-corrected按明确action_ids记录user_confirmation及服务器actor/time；不要求CRC回复、附件或说明，不能冒称AI独立验证。
- confirm-reported只完成pd_reporting，其他待办各自保留；完整目录M10不是W06前置。

## 实现步骤

1. 把cra_core示例约束吸收进持久服务，原有反例保留，不直接把示例当生产接口。
2. 稳定问题编号下建立Action；信息不全可先保存。提供确认整改按钮，自动记人和时间，可选补充沟通/修改说明。
3. 用户说PD已上报即完成该上报任务，其他补件/数据更正单独处理，不额外强求回执。
4. 区分草稿与正式Query，保存真实日期和期限来源；未知期限不生成超期天数。
5. 本次开始展示完整遗留，单项可展开问题、位置、建议来源和已知进展；点击确认完成对应事项，访前勾选不删问题。
6. 接续新患者监查和范围简记；未完项保留，不发明全局审批锁或阻断紧急事项。
7. 复用W03解析历史DOCX报告/XLSX track或问题文字，预览整理、用户修正并确认导入，关联原编号/位置和幂等键，缺项不编造。
8. W06只通过M02公开来源端口展示上传目录的对照引用；M10状态功能到W10启用，不先行冒称完成。

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

- [to_implement] 分项行动及跨次历史

```bash
uv run --frozen pytest -q tests/integration/test_issues.py
```

- [to_implement] 遗留从文件接续，不靠预置JSON

```bash
uv run --frozen pytest -q tests/integration/test_carryover_import.py
```

## 完成标准

原工作包验收：上次报告/track/文字整理为可展开遗留，本次开始提醒；CRA点击确认即可完成所选整改，保留历史和其他待办；Query期限有依据。

- PD上报已完成、数据更正仍待办可以同时呈现。
- 没有预录CRC回复、附件、说明也能点击确认整改；若用户指出仍未改好则保留/重开相应事项。
- 选2项后完整遗留清单不变，第三次跟进仍为同一问题编号。
- 从前次文件进入本次提醒和展开详情，重复导入不重复建问题；签发历史不变。

关联完整场景：CRA-S10、CRA-S11、CRA-S14、CRA-S15、CRA-S16、CRA-S17、CRA-S27、CRA-S35、CRA-S40。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 本步保存选择和预览，最终模板化信件在W11完成。
- 不正式提交Query或自动外发。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
