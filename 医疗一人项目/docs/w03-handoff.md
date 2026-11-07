# W03 隔离与授权接手说明

对应：RQ-005、RQ-013；TR-03、TR-04、TR-13、TR-16、TR-18、TR-20、TR-21、
TR-25；W03；AT-005、AT-013的主要基础子项。

状态：IMPLEMENTED，未将完整AT标为VERIFIED。项目RLS、应用角色和工具网关已有
真实PostgreSQL测试；26岗位配置、技能注册执行和容器沙箱分别等待W05/W06，故
AT-005的Agent实际运行隔离与AT-013的完整技能状态不能由W03代替。

## 已交付

- PostgreSQL `medical_one_app`为LOGIN、非superuser、无BYPASSRLS、NOINHERIT。
- 项目、版本、对话、消息、原件、版本、事件、命令收据和工具审计启用RLS；
  项目相关表共9条策略。
- 事务内设置workspace/user上下文；`SET LOCAL`结束后连接池不残留身份。
- 迁移账号与应用账号分离；Compose增加一次性初始化角色脚本和独立migrate服务。
- 确定性授权交集：用户授权∩项目策略∩岗位能力∩技能要求。
- 工具网关必须在审计写入成功后才执行；拒绝、开始、成功和失败分别记录。
- 未注册工具拒绝；跨项目、越岗位、无网络许可和未授权外部分支拒绝。
- 网络目标按服务器allowlist检查；外部副作用要求未过期明确授权。
- 运行目录按project/task/attempt隔离；输入初始暂存后只读，输出与临时目录分离。
- 路径拒绝绝对路径、`..`、非法段和符号链接逃逸。

## 本地运行

迁移账号与应用账号必须不同：

```bash
cp .env.example .env
# 替换两个本地占位密码
make db-upgrade       # MEDICAL_ONE_MIGRATION_DATABASE_URL
make db-bootstrap     # MEDICAL_ONE_DATABASE_URL，仅DML权限
make dev-api
make dev-web
```

有Docker时，Compose初始化脚本创建应用角色，迁移完成后才启动API/worker：

```bash
docker compose -f deploy/compose.yaml up --build
```

本机没有Docker，`deploy/init-db.sh`已在临时PostgreSQL上验证，但完整Compose
启动未执行。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
```

测试库名称必须以`_test`结尾。应用角色固定连接测试库，业务测试不使用超级用户。

本轮结果：

```text
20 passed
Ruff: all checks passed
mypy: no issues found in 37 source files
Alembic: W03 rollback → W02/W03 reapply passed
PostgreSQL: medical_one_app is non-superuser and has no BYPASSRLS
RLS: 9 policies
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- W03没有开放项目HTTP业务路由、登录/CSRF页面或项目页面。
- W05才配置和运行A01—A26；W06才执行技能容器、CPU/内存/时限和网络隔离。
- `input`目录的只读权限已验证；同用户原生进程仍可主动chmod，因此真正不可逃逸
  边界要由W06非root容器和只读挂载完成，不能把本机权限位冒充强沙箱。
- W04才实现任务、job、outbox、租约、预算和重试；W03运行目录目前没有任务调度。
- Compose容器路径未在本机执行，真实模型/邮箱/外部动作仍未启用。
