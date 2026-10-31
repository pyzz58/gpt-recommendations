# W04 可靠调度与预算接手说明

对应：RQ-002、RQ-009、RQ-027；TR-04、TR-05、TR-08、TR-12、TR-16、TR-20、
TR-25；W04；AT-002、AT-009、AT-027的主要基础子项。

状态：IMPLEMENTED，未将完整AT标为VERIFIED。真实PostgreSQL已验证预算竞争、
outbox去重、租约过期、fencing、429重试、断连重连和任务状态；W05 Agent执行、
W11计划/审核、W20 killed-worker压力回归和大规模故障注入仍待后续。

## 已交付

- 12状态任务、不可变任务版本和项目内依赖边。
- 依赖选择、自依赖/环检测；未验收上游不能启动下游任务。
- 上游变更会递归把未完成任务重开为`needs_input`。
- 任务提交只进入`submitted`，没有自动`accepted`路径。
- 任务入队与outbox在同一事务提交；重复入队不产生第二个outbox。
- dispatcher在短事务内用`FOR UPDATE SKIP LOCKED`领取outbox并创建去重job。
- worker用`FOR UPDATE SKIP LOCKED`领取job，递增`fence_token`后释放数据库锁再执行。
- 心跳、完成、失败均校验worker、attempt、fence和未过期lease。
- 租约过期后旧worker写入拒绝；新worker重新领取并留下`interrupted` attempt。
- 429/明确可重试错误回到queued并保留尝试记录；不可重试错误进入failed。
- 预算是带currency的NUMERIC记录；原子行锁防止并发任务合计预留超额。
- settle/release/uncertain状态和唯一ledger key防止重复结算；0或未知金额不会被当作免费。
- W04新增9张表均启用RLS；W03/W04合计18条项目策略。

## 使用顺序

```bash
cp .env.example .env
make db-upgrade
make db-bootstrap
```

业务代码使用`TaskService.enqueue`提交队列意图，再由`OutboxDispatcher`投递，
`JobQueue`由worker领取。HTTP任务路由和长期运行worker入口属于后续集成。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
```

本轮结果：

```text
25 passed
Ruff: all checks passed
mypy: no issues found in 42 source files
Alembic: W04 rollback and W02/W03/W04 reapply passed
PostgreSQL: 18 RLS policies
Budget: two concurrent 7/10 reservations, exactly one succeeds
Lease: old fence rejected after expiry; second attempt recovers
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- W05才把任务交给A01—A26和模型适配器；当前没有Agent产出。
- W11才实现完整计划DAG、派工、审核、退回和用户决定。
- W20才开始kill进程、数据库重启、429限流和大规模并发压力回归；本轮是定向
  PostgreSQL故障测试，不替代完整故障回归。
- Compose、容器迁移和worker容器仍未在本机执行；没有真实付费调用或外部副作用。
- 1—2万元只是阶段性资金边界，不是系统已分配或已消耗的live预算。
