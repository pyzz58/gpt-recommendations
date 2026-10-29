# CRA-W02 建立云上API和界面框架

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W01。必须按实际verified状态核实。

## 临床工作目标

在浏览器进入正确项目和中心，并看到真实可用能力。

## 对应理论和模块

理论：[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R040](../../theory/REQUIREMENTS.md#cra-r040)

模块：[M01](../../architecture/modules/M01-governance.md)、[M14](../../architecture/modules/M14-platform.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/main.py` | code | FastAPI应用 |
| `backend/cra_app/governance/identity.py` | code | 可信身份适配 |
| `backend/cra_app/governance/api.py` | code | 身份及授权范围 |
| `backend/cra_app/platform/api.py` | code | 健康和能力接口 |
| `web/package.json` | config | React/TypeScript/Vite和检查脚本 |
| `web/package-lock.json` | config | 前端锁 |
| `web/src/main.tsx` | code | 界面入口 |
| `web/src/app/Router.tsx` | code | 页面框架 |
| `web/src/features/workspace/WorkspaceSelector.tsx` | code | 项目/中心选择 |
| `tests/api/test_platform.py` | test | API、身份和能力 |
| `contracts/openapi.json` | config | 从实际API生成的接口契约 |
| `web/src/api/generated.ts` | code | 从契约生成的前端类型 |
| `backend/cra_app/shared/output_contract.py` | code | 共用输出范围、依据版本和事实/候选/用户确认类型 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- GET /api/v1/me/scopes以及/health/live、/health/ready、/capabilities。
- 生产模式不信任客户端自报的tenant、操作者或模拟身份头。
- OutputEnvelope按用途承载scope、purpose、policy_versions、claims、source_refs、unknowns/conflicts和输出状态，不能把不同用途共用一个医疗结论字段。

## 进入条件与交接

阶段：P1；CI profile：CRA-W02

- 进入：W01迁移与隔离测试实际通过。
- 交接：可登录的合成工作台、真实API、能力状态、OpenAPI和前端类型。

技术输入：[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)


## 实现步骤

1. 建立API统一错误和OpenAPI，把W01授权传入请求。
2. 身份通过可替换端口接入；无正式OIDC时，仅允许明确synthetic环境的合成演示，生产拒绝模拟模式。
3. 建立React页面框架、项目/中心选择及错误状态；服务密钥只在后端。
4. 配置Codespaces的Node、数据库及实际启动步骤，保持转发端口private。
5. 增加typecheck/build/test脚本及CI，记录并锁定实际依赖版本。
6. 从实际API生成contracts/openapi.json及前端类型，增加api:check，后续接口变化同步生成，禁止维护两套手写类型。

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

- [to_implement] API和身份

```bash
uv run --frozen pytest -q tests/api/test_platform.py
```

- [to_implement] 安装前端锁定依赖

```bash
npm --prefix web ci
```

- [to_implement] 类型检查

```bash
npm --prefix web run typecheck
```

- [to_implement] 构建

```bash
npm --prefix web run build
```

- [to_implement] 接口契约与前端类型一致

```bash
npm --prefix web run api:check
```

## 完成标准

原工作包验收：在Codespaces启动React界面和FastAPI；私有端口，登录/选择项目/健康检查可用，生成依赖锁与软件清单。

- 可选择授权项目/中心，刷新后上下文正确。
- 模型/OCR未配置时显示不可用，不显示自动完成。
- 实际验证Codespaces启动，未运行的部分明确记录。

关联完整场景：CRA-S01、CRA-S22、CRA-S33。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 页面框架完成不代表受试者监查业务已完成。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
