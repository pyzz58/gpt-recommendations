# CRA-W11 实现访视信、报告和Excel导出

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W06、CRA-W09、CRA-W10。必须按实际verified状态核实。

## 临床工作目标

一次记录生成访视信、报告和Excel，并保持事实与状态一致。

## 对应理论和模块

理论：[CRA-R009](../../theory/REQUIREMENTS.md#cra-r009)、[CRA-R022](../../theory/REQUIREMENTS.md#cra-r022)、[CRA-R025](../../theory/REQUIREMENTS.md#cra-r025)、[CRA-R027](../../theory/REQUIREMENTS.md#cra-r027)、[CRA-R029](../../theory/REQUIREMENTS.md#cra-r029)、[CRA-R030](../../theory/REQUIREMENTS.md#cra-r030)、[CRA-R031](../../theory/REQUIREMENTS.md#cra-r031)、[CRA-R043](../../theory/REQUIREMENTS.md#cra-r043)

模块：[M11](../../architecture/modules/M11-reports.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/reports/models.py` | code | 模板、草稿和快照 |
| `backend/cra_app/reports/service.py` | code | 多份输出 |
| `backend/cra_app/reports/docx_export.py` | code | DOCX模板导出 |
| `backend/cra_app/reports/xlsx_export.py` | code | Excel track导出 |
| `backend/cra_app/reports/api.py` | code | 草稿和导出接口 |
| `web/src/features/reports/ReportPreview.tsx` | code | 报告预览 |
| `tests/integration/test_reports.py` | test | 范围、文件和历史快照 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 生成材料引用coverage以及事实/规则/问题版本；实际发送与签发独立。
- 信件选几项不修改问题清单全集；签发后保存不可变内容与引用版本。

## 实现步骤

1. 使用合成模板建立字段映射，留出替换用户实际模板的入口。
2. 同一记录分别生成访前选取、上次问题处理、本次发现、访后事项及track。
3. 校验报告措辞不超实际范围，未知不能润色为无异常；事实更正与文字修改分开。
4. 实现不可变快照及有记录的修订，新进展只进入后续材料。
5. 真正生成DOCX/XLSX并核对内容、表格及中文排版，不只创建导出按钮。

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

- [to_implement] 模板、快照、覆盖及实际文件

```bash
uv run --frozen pytest -q tests/integration/test_reports.py
```

## 完成标准

原工作包验收：模板映射、旧问题与新发现分栏、选取式访视信、报告快照和track一致；草稿和实际提交分开。

- 旧问题处理和新发现都按模板呈现，整改建议来源可回查。
- 后续行动变化不改写签发报告。
- 文档和track字段一致且实际文件可打开。

关联完整场景：CRA-S27、CRA-S28、CRA-S29。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不自动发信、签名、写回EDC，外部Excel双向同步未承诺。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
