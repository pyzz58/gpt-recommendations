# CRA-W15 配置受控云部署并开展授权试用

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：deployment。
前置：CRA-W13。必须按实际verified状态核实。

## 临床工作目标

在获准环境实际试用，以真实CRA操作反馈增量完善。

## 对应理论和模块

理论：[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R037](../../theory/REQUIREMENTS.md#cra-r037)、[CRA-R040](../../theory/REQUIREMENTS.md#cra-r040)、[CRA-R044](../../theory/REQUIREMENTS.md#cra-r044)

模块：[M01](../../architecture/modules/M01-governance.md)、[M14](../../architecture/modules/M14-platform.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `deploy/compose.runtime.yml` | config | 核实后的运行配置 |
| `deploy/RUNBOOK.md` | document | 升级、回退和恢复 |
| `deploy/env.schema.json` | config | 配置要求，不含真实密钥 |
| `validation/AUTHORIZED_TRIAL.md` | document | 实际试用与限制 |
| `validation/FEEDBACK_REGISTER.md` | document | 反馈对应理论及代码 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- 身份、数据库、文件和模型使用获准环境；公开GitHub仅存代码和合成材料。
- 没有部署账户、凭证或授权时该步骤列阻塞，不能假装生产验证完成。
- 实际环境证据与W13离线汇总分别记录；未满足核心自动用途条件不启动或宣称完整授权试用。

## 进入条件与交接

阶段：P7；CI profile：CRA-W15

- 进入：W13工程验收已汇总，实际服务和资料范围获授权；试用范围要求的provider证据有效。
- 交接：受控环境、恢复演练、实际试用、总时间和反馈及能力暂停恢复记录。

技术输入：[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)、[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 核对获准账户、身份、数据库、文件、模型与资料范围，密钥使用安全环境管理。
2. 按锁定镜像和迁移部署，实测最小权限、TLS、备份恢复、审计和中心隔离。
3. 按确定范围执行真实操作，记录总时间、问题及未覆盖用途。
4. 反馈关联CRA-R/M/CRA-W及去标识场景，区分理论变化、资料缺口、代码错误和呈现问题。
5. 监测实际格式下关键错误、人工负担、漂移及反馈；按用途暂停相关自动能力并保留事实/问题工作，修复验证后恢复。
6. 沿用已验证boto3/队列/身份adapter；没有既有身份源时才按实际需要配置Keycloak，核对各包/模型/镜像许可与锁版本，不把可选基础设施变成默认前置。

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

- [to_implement] 部署前既定回归

```bash
uv run --frozen pytest -q tests/acceptance/test_v1a.py
```

- [to_implement] 反馈后对应仍完整

```bash
python3 tools/check_traceability.py
```

## 完成标准

原工作包验收：在获准环境配置身份、私有数据库/文件服务、备份恢复和模型；确认权限后以真实操作评价，记录风险与反馈。

- 具备实际环境、授权、恢复及试用证据，缺项如实列阻塞。
- 不把临时Codespaces当稳定临床托管。
- 反馈能定位到具体区域修改，而非重建全部系统。

关联完整场景：CRA-S01、CRA-S02、CRA-S30、CRA-S33、CRA-S34。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 本轮设计不创建收费资源、上传真实资料或启用外部服务。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
