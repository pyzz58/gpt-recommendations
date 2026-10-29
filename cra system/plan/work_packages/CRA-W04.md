# CRA-W04 实现规则候选提取及分层list

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W03。必须按实际verified状态核实。

## 临床工作目标

list能直接显示具体要求、完整条件和例外，并可展开到原文。

## 对应理论和模块

理论：[CRA-R002](../../theory/REQUIREMENTS.md#cra-r002)、[CRA-R004](../../theory/REQUIREMENTS.md#cra-r004)、[CRA-R005](../../theory/REQUIREMENTS.md#cra-r005)、[CRA-R005](../../theory/REQUIREMENTS.md#cra-r005)、[CRA-R006](../../theory/REQUIREMENTS.md#cra-r006)、[CRA-R007](../../theory/REQUIREMENTS.md#cra-r007)、[CRA-R008](../../theory/REQUIREMENTS.md#cra-r008)、[CRA-R009](../../theory/REQUIREMENTS.md#cra-r009)、[CRA-R011](../../theory/REQUIREMENTS.md#cra-r011)、[CRA-R019](../../theory/REQUIREMENTS.md#cra-r019)、[CRA-R034](../../theory/REQUIREMENTS.md#cra-r034)、[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R038](../../theory/REQUIREMENTS.md#cra-r038)、[CRA-R041](../../theory/REQUIREMENTS.md#cra-r041)

模块：[M03](../../architecture/modules/M03-rules.md)、[M12](../../architecture/modules/M12-providers.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/rules/models.py` | code | 规则树及不可变版本 |
| `backend/cra_app/rules/service.py` | code | 适用、确认、关系与影响 |
| `backend/cra_app/rules/evaluator.py` | code | 白名单条件解释 |
| `backend/cra_app/rules/api.py` | code | 候选、确认及适用查询 |
| `backend/cra_app/providers/rule_extraction.py` | code | 候选提取及来源校验 |
| `web/src/features/rules/RuleTree.tsx` | code | 四层list |
| `web/src/features/rules/RuleConfirmation.tsx` | code | 用户增删改 |
| `tests/integration/test_rules.py` | test | 条件、适用性和变更 |
| `backend/cra_app/rules/version_activation.py` | code | 手动开始使用日及按事件时间选择版本 |
| `backend/cra_app/providers/evaluate_rules.py` | code | 实际提取器与独立条件预期的评估入口 |
| `backend/cra_app/rules/common_policy.py` | code | 共性规则包、官方效力与项目/中心启用日分别解析 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- ApplicableRule含summary、conditions、exceptions、children、source_refs、applicability、unknowns。
- 条件计算返回true/false/unknown，unknown不当作正常；表达式不执行eval。
- RuleNode含preconditions/trigger/branches/exceptions/follow_up/completion/required_facts；有限AST及三值逻辑按WORKFLOW_CONTRACTS实现。
- VersionActivation由用户输入开始使用日和范围，按事件时间解析，不用上传日或报告生成时间替代。
- 所有输出使用OutputEnvelope；条件完整性有独立预期，提取模型在开发验证环境完成实际调用，不能只用人工候选验收自动提取。
- CommonPolicySet含共性原文/版本/法域/效力与取得状态，按适用范围装载；手动项目/中心启用日不覆写官方效力或批准条件。

## 进入条件与交接

阶段：P2；CI profile：CRA-W04

- 进入：已解析原文、处理覆盖及授权提取端口可用。
- 交接：候选规则树、用户修正、版本启用解析及独立条件反例结果。

技术输入：[WORKFLOW_CONTRACTS.md](../../architecture/WORKFLOW_CONTRACTS.md)、[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)


## 实现步骤

1. 保存关键摘要、完整条件/例外、子项和原文，全部绑定RuleVersion。
2. 从结构化来源提取候选并校验真实锚点和数字；获准模型经provider接入，未配置显示人工路径。
3. 实现用户确认增删改、明确规则用途文字自动纳入以及逐条变更关系。
4. 实现且/或、边界、单位和日期条件白名单；综合医学判断保持分析型规则。
5. 实现四层展开、处理覆盖、真实冲突及受影响对象提示，不取最新/更严自动裁决。
6. 完整保留前后置与分支；真实引文但漏前提/否定/例外的反例单独验证，无法结构化保留analysis_required。
7. 实现手动启用日、同范围区间边界/冲突及影响预览；使用中补list产生新版本，不改旧报告。

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

- [to_implement] 脚注、边界、例外和更新关系

```bash
uv run --frozen pytest -q tests/integration/test_rules.py
```

- [to_implement] 实际规则提取与独立条件预期比较

```bash
uv run --frozen python -m cra_app.providers.evaluate_rules --dataset tests/fixtures/manifest.json
```

## 完成标准

原工作包验收：从模拟方案自动形成有出处的候选规则；用户确认增删；例外、且或、版本、冲突和修改轨迹可查看。

- 摘要、完整条件和原文一致，用户修正保留历史。
- 新版未提及旧条文不自动撤销；重复邮件不重复确认。
- 假锚点不能形成确定性规则，未配置模型不伪装自动提取。
- 条件C走B、D走F且例外不丢；启用日当天采用新版本，历史事件依据不被覆盖。

关联完整场景：CRA-S04、CRA-S05、CRA-S06、CRA-S07、CRA-S25、CRA-S37、CRA-S38。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不硬编码真实方案数字或替项目组解释冲突。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
