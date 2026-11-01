# W01—W20 本地验收记录摘要

被测源码：最终PR修复提交（由验收记录绑定）

验收日期：2026-11-01（Pacific/Auckland）

## 实际执行

| 命令/检查 | 工作目录 | 模式 | 退出码 | 结果 |
| --- | --- | --- | --- | --- |
| Alembic升级到head→降到`d9a7e3f1b420`→再升级→current | `services/core` | 真实PostgreSQL 17.6 | 0 | head `e3b8c4d5f601` |
| PostgreSQL版本与RLS计数 | 项目根目录 | 真实PostgreSQL 17.6 | 0 | `server_version=17.6`，84条RLS策略 |
| `uv run --frozen pytest -ra --junitxml=...` | 项目根目录 | mock + 真实PostgreSQL/API，Office渲染 | 0 | 123 passed，0 skipped；1个Starlette TestClient弃用警告 |
| `uv run --frozen ruff check .` | `services/core` | 静态检查 | 0 | passed |
| `uv run --frozen mypy services/core/src` | 项目根目录 | 严格类型检查 | 0 | 118 source files，no issues |
| `pnpm --dir apps/web lint` | 项目根目录 | Next.js/ESLint | 0 | passed；本地Node 24.22.1，CI锁定22.23.4 |
| `pnpm --dir apps/web typecheck` | 项目根目录 | TypeScript | 0 | passed |
| `pnpm --dir apps/web build` | 项目根目录 | Next.js生产构建 | 0 | 15个路由成功，包含`/recovery` |
| `python3 tools/test_traceability.py` | 项目根目录 | 隔离Git临时仓库 | 0 | 22 tests passed |
| `python3 tools/check_traceability.py check` | 项目根目录 | Git实现路径、源码树及产物hash | 0 | ok，errors为空 |

## 已覆盖

- W02—W18真实PostgreSQL迁移、事务、RLS、幂等和项目隔离；
- W04上游输入失效、调度拒绝、新TaskVersion恢复；
- W04默认CLI自动发现workspace、单任务失败只结算一次、后续任务继续、迟到
  worker按fence拒绝持久化、成功输出在提交前中断后跨租约复用；
- W05返工run键包含revision/input snapshot/review，并注入上一轮output/findings；
- W05语义run键不再随生命周期revision变化，新输入或新review才形成新run；
- W08知识库换版对直接任务和下游的失效传播；
- 已知类型输入严格校验UUID、项目、current/active/use-state，格式错误和回收站
  文档、Citation底层失效来源均fail-closed；
- W11审核接受前输入与审计门槛、真正重做、下游自动入队；
- W12阶段决定检查关联独立审计；
- mock后台worker持续分发、领取、执行和提交；
- W17 A25/A26确定性规则与阻断，未关联目标按直接输入识别，关联上游阻断其
  依赖下游，无关目标不被`None`误匹配；
- W18回收站、索引重建、加密备份、错误口令/篡改、文件校验和独立PostgreSQL回放；
- W19不可变策略bundle、固定运行依据、精确影响传播、迁移dry-run/幂等应用/回滚；
- C01旧worker在新worker成功后不能重置run，成功output/输入快照/结束时间保持不变；
- W20 task/job预算关联、30路并发上界、工具审计correlation、全链可靠性报告、
  外部发送unknown阻断与reconcile恢复、标准任务列表p95门；
- W14实际Office/PDF文件、公式重算和页面渲染；
- 前端生产构建与路由包含W17/W18页面。

## 未覆盖

- live模型、真实邮箱、真人专家和非mock独立Agent审查；
- 真实机构联系、报价、合同、付款、采购或实验；
- 活动数据库原地重放、异地备份介质、密钥丢失和真实主机故障；
- Docker/Compose、强容器隔离和完整进程kill/DB故障性能矩阵；
- Microsoft Office/WPS像素一致性、任意复杂Office模板；
- W21跨包端到端、W22 live连接、W23部署发布和W24模式验证。

该记录是本地验收摘要。完整命令结构、源码SHA、文件hash、四类验证级别和
未覆盖项同时保存在`traceability/acceptance-records.json`。源码提交先于证据提交；
验收记录绑定被测源码SHA，日志和证据提交只用于保存对应命令的真实结果。
