# CRA-W09 实现有依据的AE及PD分析

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W04、CRA-W06、CRA-W08。必须按实际verified状态核实。

## 临床工作目标

异常出现后给CRA具体分析和核实问题，并保留研究者或医学答复。

## 对应理论和模块

理论：[CRA-R007](../../theory/REQUIREMENTS.md#cra-r007)、[CRA-R016](../../theory/REQUIREMENTS.md#cra-r016)、[CRA-R018](../../theory/REQUIREMENTS.md#cra-r018)、[CRA-R019](../../theory/REQUIREMENTS.md#cra-r019)、[CRA-R020](../../theory/REQUIREMENTS.md#cra-r020)、[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R038](../../theory/REQUIREMENTS.md#cra-r038)、[CRA-R042](../../theory/REQUIREMENTS.md#cra-r042)

模块：[M09](../../architecture/modules/M09-safety.md)、[M12](../../architecture/modules/M12-providers.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/safety/models.py` | code | 各判断维度和答复 |
| `backend/cra_app/safety/service.py` | code | 事实及规则分析 |
| `backend/cra_app/safety/grounding.py` | code | 引用与数字校验 |
| `backend/cra_app/safety/api.py` | code | 分析及答复接口 |
| `backend/cra_app/providers/case_analysis.py` | code | 受控分析provider |
| `web/src/features/safety/AssessmentPanel.tsx` | code | 事实、分析、缺口和问题 |
| `tests/integration/test_safety.py` | test | 判断维度与及时提醒 |
| `backend/cra_app/providers/evaluate_cases.py` | code | 实际分析模型与独立预期的评估入口 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 事实、系统候选、CRA核实及医学答复分别保存。
- 分级、严重性、相关性、预期性、AESI/DLT等分开，缺条件标unknown。
- 缺数据拒绝后停止相应依赖判断，仍给出已有事实和明确依据；不根据拒绝猜补病史或整体安全。
- SafetyContext字段按评估维度声明required/optional/unknown；缺AE信息不能写未发生AE，检验一致不能写临床安全。

## 进入条件与交接

阶段：P4；CI profile：CRA-W09

- 进入：自动比较结果、规则依据与已有安全上下文可用；缺项允许明确保留未知。
- 交接：按项目标准区分医学维度的候选分析、具体问题及必要及时线索，不自动作最终医学结论。

技术输入：[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 先程序计算可确定条件，再由受限模型解释事实及合理候选原因。
2. 按项目实际版本展开AE及特殊标准，不因外部新版发布而自动替换。
3. 验证数字、条件和来源；虚构引用不能成为确定性建议。
4. 生成具体提问和必要及时提醒，分开事件、知悉和实际上报时间。
5. 关联M06待办及后续答复，provider无权自行关闭行动。
6. 使用W04条件分支与版本启用服务；测试真实引文但条件错误的反例，医学综合条款保持分析型。

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

- [to_implement] 候选与确认、缺资料、假引用和提醒

```bash
uv run --frozen pytest -q tests/integration/test_safety.py
```

- [to_implement] 实际分析模型的事实/来源/条件与答复边界评估

```bash
uv run --frozen python -m cra_app.providers.evaluate_cases --dataset tests/fixtures/manifest.json
```

## 完成标准

原工作包验收：基于事实和规则形成候选结论、缺口、针对性问题及证据；医学维度分开，紧急提示不被报告流程延误。

- 分析给出具体应核实的问题，而非泛泛问医学。
- 候选判断不冒充研究者确认，不用分级替代SAE判断。
- 模拟provider与真实provider验证分开，缺凭证明示能力缺口。

关联完整场景：CRA-S23、CRA-S24、CRA-S25、CRA-S30。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不自动作最终医学判断或无依据的临床处置。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
