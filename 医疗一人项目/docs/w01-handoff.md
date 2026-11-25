# W01 工程骨架接手说明

对应：RQ-025、RQ-032；TR-03、TR-18、TR-20、TR-21、TR-25；W01；AT-025、AT-032。

## 已交付

- Next.js 16 网页：读取 API 存活、mock 就绪和能力报告，可运行一次模拟合同检查。
- FastAPI 服务：`/health/live`、`/health/ready`、`/api/v1/system/capabilities`、
  `/api/v1/system/mock-smoke`。
- 确定性 fake provider：不联网、不需密钥，输出始终带 `mock` 和不代表科学判断的声明。
- Python worker 入口骨架：可启动和优雅停止；W01 不领取任务。
- PostgreSQL/API/worker/web 的 Compose 骨架和固定镜像摘要。
- 依赖锁、直接依赖许可记录、本机兼容矩阵、测试和开发命令。
- 配置文件目录只含说明；26 岗、三类流程和真实技能仍未实现。

## 本地 mock

前置：Python 3.12.14、Node 22.23.4、pnpm 11.25.0、uv。

```bash
make bootstrap
make dev-mock
```

浏览器打开 `http://127.0.0.1:3000`。首次打开若 API 尚未就绪，页面会显示错误，
不会伪造“运行中”状态。

分别启动：

```bash
make dev-api
make dev-web
```

检查：

```bash
make test
make lint
make build
make schema
python3 tools/check_traceability.py check
```

## 未完成与限制

- 本机没有 Docker，没有运行 Compose、容器构建、PostgreSQL 或隔离验证。
- W01 不读写业务数据库，不创建项目，不派工，不调用真实模型，不连接邮箱，
  不联系外部机构，也不产生科学结论。
- W02 才实现项目、版本、会话、事件与首个重启恢复；W03 才实现实际权限和
  工具网关隔离；W24 的现实外包覆盖仍无现实证据。
- 下一步从 W02 开始，但应先获得或安装可用容器运行时并复核 W01 容器路径。
  即使容器仍不可用，也可继续完成不依赖真实 PostgreSQL 的代码脚手架，随后
  在具备环境时补跑 W02 的真实数据库验收。
