# W01—W18 本地验收记录摘要

被测源码：最终PR修复提交（由验收记录绑定）

验收日期：2026-11-01（Pacific/Auckland）

## 实际执行

| 命令/检查 | 工作目录 | 模式 | 退出码 | 结果 |
| --- | --- | --- | --- | --- |
| Alembic升级到head→降到`a7c4e2f9b610`→再升级 | `services/core` | 真实PostgreSQL 17.6 | 0 | head `b2e7d4a9c310`，79条RLS |
| `uv run --frozen pytest` | `services/core` | mock + 真实PostgreSQL/API，Office渲染 | 0 | 105 passed；1个Starlette TestClient弃用警告 |
| `uv run --frozen ruff check .` | `services/core` | 静态检查 | 0 | passed |
| `uv run --frozen mypy src` | `services/core` | 严格类型检查 | 0 | 109 source files，no issues |
| `pnpm --dir apps/web lint` | 项目根目录 | Next.js/ESLint | 0 | passed；本机Node 24.22.1触发engine warning，项目锁定22.23.4 |
| `pnpm --dir apps/web typecheck` | 项目根目录 | TypeScript | 0 | passed |
| `pnpm --dir apps/web build` | 项目根目录 | Next.js生产构建 | 0 | 15个路由成功，包含`/recovery` |
| `python3 tools/check_traceability.py check` | 项目根目录 | Git实现路径+证据结构 | 0 | ok，errors为空 |
| `python3 tools/test_traceability.py` | 项目根目录 | 隔离Git临时仓库 | 0 | 18 tests passed |

## 已覆盖

- W02—W18真实PostgreSQL迁移、事务、RLS、幂等和项目隔离；
- W04上游输入失效、调度拒绝、新TaskVersion恢复；
- W05返工run键包含revision/input snapshot/review，并注入上一轮output/findings；
- W08知识库换版对直接任务和下游的失效传播；
- W11审核接受前输入与审计门槛、真正重做、下游自动入队；
- W12阶段决定检查关联独立审计；
- mock后台worker持续分发、领取、执行和提交；
- W17 A25/A26确定性规则与阻断；
- W18回收站、索引重建、加密备份、错误口令/篡改、文件校验和独立PostgreSQL回放；
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
未覆盖项同时保存在`traceability/acceptance-records.json`。
