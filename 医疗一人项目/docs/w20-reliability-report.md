# W20 成本、全链审计、性能与故障回归接手说明

对应：RQ-002、RQ-005、RQ-027、RQ-029；TR-03、TR-04、TR-07、TR-12、
TR-13、TR-16、TR-21、TR-23；W20；AT-002、AT-005、AT-027、AT-029。

状态：IMPLEMENTED，未将整体AT标为VERIFIED。W20建立项目级可靠性门，
把已有预算、租约、工具审计、策略绑定、邮件未知态和项目隔离放进同一报告；
生产负载、真实数据库重启和真实外部副作用仍未验证。

## 已交付

### 成本上界与 task/job 归属

- `BudgetReservation` 可绑定 task_id/job_id，二者必须属于同一任务、同一项目；
- 预留操作键重放比较 amount/task/job，不允许同一键切换运行范围；
- 预算仍以行锁和 NUMERIC 账本原子预留、结算、释放；
- W20并发回归使用30个并行请求、20单位上限，结果严格为20成功、10拒绝；
- ReliabilityReport分别显示reserved、spent和uncertain金额。

### 全链审计关联

- ToolAuditEvent新增task_id、job_id、correlation_id；
- SkillRunner调用ToolGateway时写入task、skill run correlation；
- ReliabilityService核对Task→Job→TaskAttempt→AgentRun、Task→SkillRun，
  以及TaskVersion、policy bundle和预算预留关系；
- 失去项目/任务/job关联、悬空running attempt、缺失bundle或成功run对应
  失败job均形成阻断finding；
- 授权后未完成的tool audit超过5分钟进入待核对清单。

### 外部副作用不确定态

- MailSendAttempt为`outcome_unknown`时，ReliabilityReport阻断；
- 再次发送同一幂等键仍返回原attempt，不自动重发；
- reconcile后attempt和draft恢复到真实结果，ReliabilityReport解除该阻断；
- 报告不把mock发送或本地reconcile扩大成真实邮件已送达。

### 性能与隔离

- 项目可靠性报告对标准项目任务列表执行12次查询测量，记录p95；
- 默认门为500ms；超限形成`TASK_LIST_P95_OVER_BUDGET`，测量与业务正确性分开；
- 报告查询限定当前workspace/project，RLS继续生效；
- `reliability_evaluations`使用FORCE RLS并纳入项目备份/恢复；
- 当前全库84条RLS策略，新增W20表1条。

### API

- `GET /projects/{id}/reliability`：最近一次可靠性报告和阈值证据；
- `POST /projects/{id}/reliability/evaluate`：运行并持久化新报告；
- 报告包含status、metrics、findings、policy bundle、限制与创建时间。

## 当前阻断码

- `EXPIRED_RUNNING_LEASE`
- `TASK_POLICY_BUNDLE_MISSING`
- `INVALID_INPUT_IN_FLIGHT`
- `ATTEMPT_TASK_CHAIN_MISSING`
- `ATTEMPT_JOB_CHAIN_MISSING`
- `AGENT_RUN_CHAIN_MISSING`
- `AGENT_RUN_POLICY_MISSING`
- `SUCCEEDED_RUN_JOB_FAILED`
- `SKILL_RUN_CHAIN_MISSING`
- `TOOL_AUDIT_UNSETTLED`
- `BUDGET_OUTCOME_UNCERTAIN`
- `EXTERNAL_SEND_OUTCOME_UNKNOWN`
- `AUDIT_FINDING_UNRESOLVED`
- `TASK_LIST_P95_OVER_BUDGET`

## 主要路径

- 领域视图：`services/core/src/medical_one_person/domain/reliability.py`
- 可靠性服务：`services/core/src/medical_one_person/application/reliability.py`
- API：`services/core/src/medical_one_person/api/reliability.py`
- 工具审计关联：`services/core/src/medical_one_person/infrastructure/tool_gateway.py`
- 预算关联：`services/core/src/medical_one_person/application/budgets.py`
- 迁移：`services/core/migrations/versions/e3b8c4d5f601_w20_reliability_regression.py`
- 核心测试：`services/core/tests/integration/test_w20_reliability.py`
- 邮件未知态：`services/core/tests/integration/test_w15_mail.py`
- Skill审计关联：`services/core/tests/integration/test_w06_skill_runner.py`

## 验收范围

- 真实PostgreSQL 17.6与mock provider；
- 30路并发预算上界、task/job预算关联、工具审计correlation；
- 完整mock链通过、过期租约+uncertain预算阻断；
- 外部发送unknown阻断、reconcile后恢复；
- 标准项目任务列表p95门槛；
- 84条RLS策略和W20 FORCE RLS；
- Ruff、mypy、Next.js lint/typecheck/build。

未覆盖：

- 生产级并发、长稳、内存压力和真实模型延迟；
- 强制kill进程矩阵、PostgreSQL重启和部分提交恢复；
- live模型、真实邮件、真实专家/机构、合同、付款或实验；
- 同一外部请求跨系统无法确认时的自动业务裁决。

## 下一包

W21继续两个隔离项目的完整端到端链路，包括选择、派工、退回、外部模拟、
真实文件、重启和停止。W20报告通过不代表现实研发或科学结论已验证。
