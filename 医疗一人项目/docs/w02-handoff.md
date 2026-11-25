# W02 本地持久化接手说明

对应：RQ-007、RQ-012、RQ-029、RQ-032；TR-03、TR-04、TR-05、TR-16、TR-18、
TR-20、TR-21、TR-25；W02；AT-007、AT-012、AT-029、AT-032的子项。

状态：IMPLEMENTED，未把完整AT标为VERIFIED。W02的基础行为已有真实PostgreSQL
证据，但AT-007还依赖W10界面，AT-012还依赖W07/W08资料处理，AT-029还依赖后续
运行、邮件和导出能力。

## 已交付

- PostgreSQL 17.6 + SQLAlchemy 2.1 + Alembic迁移。
- workspaces、users、sessions、projects、project_versions、conversations、
  messages、artifacts、artifact_versions、events和command_receipts。
- 项目创建、改名、乐观revision冲突、不可变项目版本和事务内递增事件序号。
- 幂等命令收据：同键同参数重放，同键不同参数拒绝。
- 会话使用随机opaque token，数据库只保存SHA-256摘要，支持过期和撤销。
- 内容寻址原件目录：原子写入、hash校验、同内容复用、路径逃逸拒绝。
- 跨工作区主体在写文件前即被拒绝，数据库事务内再次校验。
- PostgreSQL连接与Alembic revision共同决定readiness；数据库停机时API明确降级。
- Compose新增独立migrate服务，API和worker等待迁移成功。

迁移版本：`12ee06c30409`。迁移已在独立测试库完成
`upgrade head → downgrade base → upgrade head`。

## 本地运行

需要可用的PostgreSQL 17实例。数据卷必须放在仓库外。

```bash
cp .env.example .env
make db-upgrade
make db-bootstrap
make dev-api
make dev-web
```

`db-bootstrap`幂等创建本地工作区与发起人身份，只输出workspace/user UUID，
不生成或打印长期会话令牌。

有Docker时：

```bash
docker compose -f deploy/compose.yaml up --build
```

本机未安装Docker，因此该Compose入口尚未执行，不能把迁移服务写成已容器验收。

## 测试

测试库名称必须以 `_test` 结尾；集成fixture会清空其`public` schema，禁止指向
开发或真实资料库。

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://user@127.0.0.1:5432/medical_one_test'
make test-integration
```

本轮真实PostgreSQL运行结果：

```text
15 passed
Ruff: all checks passed
mypy: no issues found in 32 source files
Next.js: lint, TypeScript and production build passed
Alembic: upgrade head → downgrade base → upgrade head passed
```

本轮原生PostgreSQL运行来源：

- Release：`theseus-rs/postgresql-binaries` `17.6.1`
- Target：`aarch64-apple-darwin`
- Archive SHA-256：`876c025581ee02896e7439783147bd3ec38ce3535234acc9449cf3d78fb72f3e`
- `server_version`：PostgreSQL 17.6

## 尚未完成

- W02没有开放项目业务HTTP路由，也没有项目页面；认证、CSRF和项目RLS属于W03，
  核心项目页面和真实工作场景属于W10。
- ArtifactService目前是内部应用能力；上传协议、文档解析与检索分别属于W07/W08。
- Compose镜像、容器迁移和隔离尚未运行。
- W03—W24仍为计划；没有真实模型、邮件、采购、委托或实验。
