# W04 可靠调度与预算接手说明

对应：RQ-002、RQ-009、RQ-027；TR-04、TR-05、TR-08、TR-12、TR-16、TR-20、
TR-25；W04；AT-002、AT-009、AT-027的主要基础子项。

状态：IMPLEMENTED，未将完整AT标为VERIFIED。真实PostgreSQL已验证预算竞争、
outbox去重、租约过期、fencing、429重试、断连重连、任务状态和受限mock worker
的失败隔离/租约恢复；W20 killed-worker压力回归和大规模故障注入仍待后续。

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
- 成功输出落库后、job完成前中断时，同语义执行跨租约恢复复用成功run，生命周期
  revision变化不会改变run身份；新输入或新review会生成新run。
- 429/明确可重试错误回到queued并保留尝试记录；不可重试错误进入failed。
- 预算是带currency的NUMERIC记录；原子行锁防止并发任务合计预留超额。
- settle/release/uncertain状态和唯一ledger key防止重复结算；0或未知金额不会被当作免费。
- 默认`python -m medical_one_person.worker`可自动发现唯一workspace；单任务失败
  只由worker结算一次并继续后续ready任务，基础设施迭代错误采用有上限退避。
- W04新增9张表均启用RLS；W03/W04合计18条项目策略。

## 使用顺序

```bash
cp .env.example .env
make db-upgrade
make db-bootstrap
```

业务代码使用`TaskService.enqueue`提交队列意图，再由`OutboxDispatcher`投递，
`JobQueue`由受限mock worker领取执行；`make dev-worker`或
`python -m medical_one_person.worker`启动长期入口。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
```

本轮结果：

```text
112 core tests passed (0 skipped locally)
Ruff: all checks passed
mypy: no issues found in 112 source files
Alembic: W04 rollback and W02/W03/W04 reapply passed
PostgreSQL: 79 RLS policies
Budget: two concurrent 7/10 reservations, exactly one succeeds
Lease: old fence rejected after expiry; second attempt recovers
Worker: one task failure settled once; next ready task still runs
Recovery: successful output reused after lease revision changes
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- 当前worker只执行受限mock Agent；没有live模型或真实外部副作用。
- W20才开始kill进程、数据库重启、429限流和大规模并发压力回归；本轮是定向
  PostgreSQL故障测试，不替代完整故障回归。
- Compose、容器迁移和worker容器仍未在本机执行；没有真实付费调用或外部副作用。
- 1—2万元只是阶段性资金边界，不是系统已分配或已消耗的live预算。
