# W11 有界计划、派工与审核接手说明

对应：RQ-008、RQ-009、RQ-010、RQ-022；TR-04、TR-05、TR-08、TR-12、
TR-17、TR-18、TR-20、TR-25；W11；AT-008、AT-009、AT-010、AT-022的主要
合同子项。

状态：IMPLEMENTED，未VERIFIED。计划、依赖、派工、mock运行、审核退回、下游
解锁、暂停恢复和返工上限已通过真实PostgreSQL与浏览器流程；W17独立
A25/A26 Agent或真实专家审查、专业领域工作流和现实外部执行仍未完成。

## 已交付

- `Plan`保存项目内版本、来源机会选择decision、最多20节点、revision、
  max_rework_rounds和draft/active/paused/stopped/completed状态。
- `PlanSpec`在写入前校验唯一node key、未知依赖、自依赖和环依赖；服务按
  拓扑顺序物化Task与TaskDependency。
- 计划提交使用Idempotency-Key；相同请求重放原计划，参数变化返回冲突。
- 激活要求DAG有效、岗位/版本有效、只支持mock/free任务；显式派工才把
  READY/REWORK任务写入outbox，activation和dispatch分开记录。
- 按需mock执行通过已有JobQueue/AgentRunner运行当前计划就绪任务；运行结束
  只把Task置submitted，不自动接受。
- TaskReview绑定具体TaskVersion，保存指定审核岗位、summary、findings、
  request hash和返回payload；禁止产出岗位自审。
- 任何critical发现都强制changes_requested；退回后任务进入rework，下游保持
  needs_input。上游accepted后才逐层解锁所有依赖已接受的节点。
- 返工超过任务上限时任务与计划暂停，恢复必须由用户明确增加返工轮数。
- 暂停取消尚未开始的outbox/job；已running的动作继续记录，不伪称回滚。
- 停止取消未开始/排队/返工/暂停任务，保留accepted、submitted和running历史。
- W11新增plans、plan_nodes、task_reviews三张表并启用FORCE RLS；累计48条策略。
- 任务页可展示计划版本、DAG、审核历史、任务看板，并执行激活、派发、mock
  运行、记录审核、暂停、恢复和停止。

## 主要路径

- 领域合同：`services/core/src/medical_one_person/domain/plans.py`
- 计划/审核状态机：`services/core/src/medical_one_person/application/plans.py`
- 按需mock执行：`services/core/src/medical_one_person/application/plan_execution.py`
- API：`services/core/src/medical_one_person/api/plans.py`
- 迁移：`services/core/migrations/versions/9ff9aac51d3e_w11_plans_dispatch_reviews.py`
- 页面：`apps/web/src/app/projects/[id]/tasks/page.tsx`
- 测试：`services/core/tests/integration/test_w11_plans.py`、
  `test_w11_plan_api.py`、`tests/unit/test_w11_plan_contract.py`

## 验收

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
PATH="/Users/zz/Library/pnpm/bin:$PATH" make test
PATH="/Users/zz/Library/pnpm/bin:$PATH" make lint
PATH="/Users/zz/Library/pnpm/bin:$PATH" make build
```

本轮结果：

```text
60 core tests passed (`make test`)
15 traceability self-tests passed
W11 migration: a823720b9684 -> 9ff9aac51d3e round-trip passed
RLS: 48 policies; plans, plan_nodes and task_reviews FORCE RLS
DAG: duplicate/unknown/cycle dependency tests
Workflow: selected direction -> plan -> activate -> dispatch -> mock run
Review: self-review rejected, critical accept rejected, rework and unlock passed
Limits: rework limit pauses plan; resume requires explicit additional rounds
Controls: pause/resume/stop and unstarted-work cancellation passed
Browser: full plan workflow and critical rework flow passed
Ruff and mypy passed
Next.js lint, typecheck and production build passed
```

## 尚未完成

- 当前审核是验证过的workspace owner代表指定A25/A26岗位合同记录，不等于独立
  Agent完成审查；W17才实现真正独立上下文、人工/专家反馈与反证评测。
- 按需执行仍是mock runner，没有持续后台worker、真实模型、专业检索或外部
  邮件/采购/合同/实验动作。
- W12才提供宠物药、IVD、器械的专门阶段模板、现实前置条件和专业证据包。
- 暂停对已经running的真实外部动作只能记录并核对，不能撤回现实副作用。
- 计划页未提供任意DAG图形编辑器；当前首轮草案由确定性岗位模板产生。
- 完整AT-008/009/010/022跨W12/W17/W21/W24，不能因本轮工作流测试标为VERIFIED。
