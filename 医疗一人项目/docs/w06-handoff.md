# W06 技能注册与沙箱接手说明

对应：RQ-005、RQ-013、RQ-025；TR-03、TR-06、TR-13、TR-16、TR-20、TR-23、
TR-25；W06；AT-013、AT-025的主要基础子项。

状态：IMPLEMENTED，未VERIFIED。内置技能注册、授权、schema和审计有真实测试；
本机没有Docker，因此非root容器、只读挂载、资源限制与网络隔离只通过命令策略
测试，未执行真实容器。科学检索、Evidence、统计、Office和邮件技能仍不可用。

## 已交付

- `config/skills/catalog.yaml`的12项版本化技能合同。
- `data.numeric_summary`与`artifact.hash`两个可执行内置技能。
- 10项科学检索、证据、统计、Office或邮件技能明确标记planned或
  dependency_missing，不因目录存在而冒充ready。
- Registry按执行器、输入/输出schema名和依赖解析真实状态。
- SkillRunner检查岗位allowlist、授权交集、输入大小、schema和输出大小。
- 所有工具执行经ToolGateway和审计；拒绝、无效输入和不可用状态均进入SkillRun。
- 同一任务/技能/输入重放返回既有成功结果，不重复结算或产生第二个执行记录。
- 数值输出仅代表调用方提供数字的描述统计，不评价研究设计或科学有效性。
- SkillRun受项目RLS保护；累计21条RLS策略。
- 容器策略固定`--network none`、`--read-only`、`--cap-drop ALL`、
  `no-new-privileges`、非root用户、CPU/内存/PID限制和三段目录挂载。
- 输入挂载只读，禁止Docker socket；容器镜像必须以sha256 digest固定。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
make schema
```

本轮结果：

```text
38 passed
2 builtin skills ready; 10 explicitly unavailable
Ruff: all checks passed
mypy: no issues found in 54 source files
Alembic: W06 rollback and W02-W06 reapply passed
PostgreSQL: 21 RLS policies
Container policy: offline/read-only/unprivileged/bounded argument test passed
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- Docker未安装，未启动真实容器，也未验证实际文件/网络/资源逃逸。
- `office.docx`、`mail.draft`、`literature.search`等没有执行器，API应继续显示
  不可用；对应实现分别在W14/W15/W07。
- W20才做大范围故障和资源压力回归；W06定向策略测试不替代。
- 尚无真实专业数据库、付费全文、模型调用或外部邮件。
- SkillRunner尚未接入长期worker/API；W07开始接入来源处理链。
