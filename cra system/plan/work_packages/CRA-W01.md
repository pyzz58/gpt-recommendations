# CRA-W01 建立数据、权限和历史记录底座

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W00。必须按实际verified状态核实。

## 临床工作目标

让各中心资料和每次修改可靠保存，并保留操作历史。

## 对应理论和模块

理论：[CRA-R002](../../theory/REQUIREMENTS.md#cra-r002)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R040](../../theory/REQUIREMENTS.md#cra-r040)

模块：[M01](../../architecture/modules/M01-governance.md)、[M14](../../architecture/modules/M14-platform.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `pyproject.toml` | config | Python项目及开发依赖 |
| `uv.lock` | config | 精确依赖锁 |
| `.python-version` | config | Python运行版本 |
| `alembic.ini` | config | 迁移配置 |
| `migrations/env.py` | migration | 迁移入口 |
| `migrations/versions/0001_governance.py` | migration | 最小权限与历史底座 |
| `backend/cra_app/shared/db.py` | code | 事务与会话 |
| `backend/cra_app/shared/config.py` | code | 环境配置 |
| `backend/cra_app/governance/models.py` | code | 研究、中心、授权、审计及幂等模型 |
| `backend/cra_app/governance/service.py` | code | 授权与版本化命令 |
| `deploy/compose.dev.yml` | config | 合成开发数据库 |
| `tests/integration/test_governance.py` | test | 真实PostgreSQL隔离与事务 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- ScopeContext来自可信身份，读取和写入均必须携带授权范围。
- 写命令有expected_revision及Idempotency-Key；业务写入与AuditEvent同一事务。

## 进入条件与交接

阶段：P1；CI profile：CRA-W01

- 进入：W00已有证据，完成声明使用新的任务专属CI门槛。
- 交接：数据迁移、授权/事务API、可重现依赖及cra-w01真实数据库CI。

技术输入：[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)


## 实现步骤

1. 建立cra_app包和uv项目，锁定Python及依赖；保留cra_core示例和已有反例。
2. 只迁移当前所需研究、中心、授权、审计和幂等表，不提前为所有模块建立空表。
3. 实现跨研究/中心约束及读取前鉴权；若用RLS，验证实际应用角色和表拥有者例外。
4. 实现旧revision冲突、幂等重放、不同输入复用同键的冲突以及失败回滚。
5. 在专属CI加入临时PostgreSQL和迁移/集成检查；真实数据库检查不能由SQLite代替。
6. 按plan/implementation.json建立cra-w01专属CI job与migrate/test步骤。实际通过后生成绑定源码/规范指纹和GitHub run的completion_evidence，不能用自报文字完成任务。

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

- [to_implement] 安装锁定依赖

```bash
uv sync --frozen --group dev
```

- [to_implement] 空库迁移

```bash
uv run --frozen alembic upgrade head
```

- [to_implement] 权限、事务、幂等和并发

```bash
uv run --frozen pytest -q tests/integration/test_governance.py
```

## 完成标准

原工作包验收：PostgreSQL迁移、研究/中心授权、幂等写入、并发版本和审计事务通过跨范围及重复提交测试。

- 两中心合成数据不能跨范围读取。
- 重复命令不重复写入，旧版本不能覆盖新值。
- 失败事务无半完成业务或审计记录，CI可复现。

关联完整场景：CRA-S01。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不实现全部未来业务表、OCR或报告页面。
- 测试身份不等于正式OIDC已经接入。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
