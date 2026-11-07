# W23 本地部署、运维与恢复接手说明

对应：RQ-025、RQ-026、RQ-030、RQ-032；TR-01、TR-03、TR-20、TR-21、
TR-23、TR-24、TR-25；W23；AT-025、AT-026、AT-030、AT-032。

日期：2026-11-07（Pacific/Auckland）。

状态：IMPLEMENTED。原生 mock/local 单入口在独立 PostgreSQL 17.6 上完成首次
迁移、启动、ready/能力检查、停止和残留检查；Compose 文件与镜像输入只完成
静态校验，本机没有 Docker，不把静态检查写成容器运行通过。

## 交付范围

- `scripts/medical-one.sh`：统一 `doctor`、`bootstrap`、`start`、`status`、
  `config`、`smoke`、`stop` 和 `logs` 入口；
- `deploy/compose.yaml`：PostgreSQL、一次性迁移、API、worker、web 服务，
  端口只绑定 loopback；
- `services/core/Dockerfile`：包含策略 bundle、审计和运行所需的文档、manifest、
  schemas、全部配置和 W17 fixture；
- 健康接口报告数据库、文件存储、队列 schema 和 worker 心跳，不再使用静态
  `not_checked` 冒充 worker 状态；未就绪明确返回 HTTP 503 和 `not_ready`；
- Shell、Python 和由统一入口启动的 Next.js 读取同一份 dotenv；
- W23 静态检查拒绝错误数据库健康账号、缺失运行资料、缺失备份卷和公网端口；
- 旧 W01/W02/W03 的 Compose 骨架保留，本包只补真实运行缺口。

## 首次设置

1. 安装 uv、pnpm 11.25.0、Python 3.12、Node.js 22.23.4 和 PostgreSQL 17。
   Office/PDF 实际文件验收还需要 LibreOffice 与 Poppler；缺失时这两项明确跳过。
2. 从 `.env.example` 创建配置，替换数据库口令，不提交配置。推荐把文件放在
   仓库外，并在父进程设置：

```bash
export MEDICAL_ONE_CONFIG_FILE=/absolute/outside/repository/medical-one.env
```

   未设置时入口只在项目根目录查找 `.env`。父进程已有的同名环境变量优先于
   文件值。dotenv 不做变量插值；未知键、NUL或敏感值不会静默进入运行环境。
   所有 artifact、run、backup 和 restore 路径必须位于仓库外。
3. 安装锁定依赖：

```bash
make bootstrap
```

4. 创建数据库和迁移账号；数据库 URL 使用独立应用角色。首次建表、创建本地
   owner：

```bash
./scripts/medical-one.sh bootstrap
```

5. 运行完整预检：

```bash
./scripts/medical-one.sh doctor
```

查看已解析的非敏感配置、自定义端口和运行目录：

```bash
./scripts/medical-one.sh config
```

`doctor --structural-only` 只检查源码包、文档、配置、依赖版本和凭据模式，
用于安装前或 CI。普通 `doctor` 还检查 PostgreSQL 迁移 head、五项存储根、
worker 心跳和可选 Office/Poppler。

## 日常启停

```bash
./scripts/medical-one.sh start
./scripts/medical-one.sh status
./scripts/medical-one.sh logs api
./scripts/medical-one.sh stop
```

`start` 默认先升级到当前 Alembic head 并幂等创建本地 owner，再启动 API、worker、
web。只有 `/health/ready` 返回 HTTP 200 且 `status=ok` 才报告启动成功；
503/`not_ready` 会触发失败并停止本次启动的进程。`--skip-bootstrap` 只用于已经
确认数据库版本的情况。运行目录默认在
`$XDG_STATE_HOME/medical-one-person` 或 `~/.local/state/medical-one-person`，
可用 `MEDICAL_ONE_RUNTIME_DIR` 指定；PID、日志和 worker 心跳不进入 Git。

没有桌面会话的自动验收使用：

```bash
./scripts/medical-one.sh smoke
```

`smoke` 在同一个入口内启动、查询 ready/capabilities、访问 web，并停止本次启动
的三个进程。它不替代真实浏览器交互或长期稳定性测试。

## 健康与能力状态

- `/health/live` 只表示 API 进程存活；
- `/health/ready` 同时检查 provider、PostgreSQL 迁移版本、五类可写存储、
  `outbox`/`jobs` schema 以及 15 秒内有效的 worker 心跳；全部 ready 返回 200，
  任一依赖未就绪返回 503/`not_ready`，不会用成功 HTTP 表示未就绪；
- `/api/v1/system/capabilities` 逐项报告 provider、数据库、存储、队列、worker、
  知识库、计划、外部记录、恢复与外部动作边界；
- worker 每 5 秒原子刷新运行目录中的心跳文件，正常停止或心跳失败时清理并退出；
- provider 未配置会阻止 live ready，但离线资料浏览与 mock 能力仍明确标记。

如果 `status` 显示 worker `unavailable`，先查看 `logs worker`。API 进程存在而
worker 缺失不代表后台任务可执行，不能把“网页可打开”写成完整链 ready。
启动脚本和 Compose healthcheck 均检查 `/health/ready`，不是只检查进程存活。

## Compose 使用与边界

有 Docker 的主机可先复制 `.env.example` 为仓库外 compose env 文件，然后执行：

```bash
docker compose --env-file .env -f deploy/compose.yaml up --build
docker compose --env-file .env -f deploy/compose.yaml down
```

Compose 使用命名数据卷保存 PostgreSQL、原件、运行目录、知识暂存、备份和隔离
恢复检查；所有发布端口均为 `127.0.0.1`。API healthcheck 使用 `/health/ready`，
因此 worker 心跳与数据库/队列/存储都通过后才报告健康。

当前本机无 Docker。静态检查只证明文件引用、环境路径、卷和端口结构一致，
不能证明镜像能构建、apt/Node 依赖可解析、容器可启动或 Office 在镜像中可用。
安装 Docker 后必须重新执行 Compose up、ready、smoke、备份/恢复、权限和停止
测试，再提升相关容器验收。

## 备份与恢复操作

1. 在项目的“恢复与离线”页创建 AES-256-GCM 加密备份。口令只在请求中使用，
   不写入数据库或日志。
2. 在隔离 `restore-checks` 目录执行恢复检查，核对 archive/hash、数据库表关系、
   原件、任务、预算和账本数量。
3. 恢复检查不覆盖活动数据库。真实切换前仍需停止写入、对当前库和对象卷做
   独立备份，再按已审阅流程切换；切换失败必须回退并重新核对外部动作状态。
4. 邮件、合同、付款和实验等外部事实不会因本地数据库回滚而撤销。恢复后必须
   逐项对账，不能把本地恢复成功写成现实动作已撤销。

Compose 的命名卷、异地副本、密钥丢失恢复和真实主机故障仍没有验收。

## 本轮验证

- 空库升级至 `f4a2c7d9e601`，owner 初始化，API/worker/web 启动并通过
  live、ready 与 capabilities；
- ready 中数据库、五项存储、`outbox`/`jobs` 和 worker 心跳均为 ready；
- 仓库外 dotenv 在自定义 API/web 端口 `18000/13000` 和外置运行目录下完成同一
  `smoke`；Shell 加载的 API URL 已传给 Next.js；
- worker 心跳缺失和 provider未配置均返回 HTTP 503/`not_ready`；
- `smoke` 后 API、worker、web 均停止，无测试进程残留；
- 独立 PostgreSQL 17.6 完成 `f4a2c7d9e601 → b2e7d4a9c310 → f4a2c7d9e601`；
- 全库 84 条 RLS 策略，应用角色迁移 head 与运行常量一致；
- 应用测试、Ruff、mypy、Next.js lint/typecheck/build、追踪检查按最终源码提交
  另存于 `traceability/acceptance-records.json`。

## 已知限制与下一步

- Docker/Compose 未执行；不得称为容器、生产或公开部署完成；
- 没有真实模型、真实邮箱、专业检索账号、真人专家或现实外包授权；
- 没有异地灾备、活动数据库切换、真实主机故障和长期负载；
- Compose Core 镜像当前只提供 mock 软件链，不宣称 Office/科研技能容器隔离；
- W22 的真实连接验证保持未执行，需用户另行提供 provider/邮箱配置、小额额度
  和明确授权；
- W24 仍为 PREPARED，本交付不扩大现实联系、采购、合同或实验权限。
