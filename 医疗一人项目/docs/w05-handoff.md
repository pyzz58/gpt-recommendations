# W05 Agent岗位运行接手说明

对应：RQ-004、RQ-005、RQ-006；TR-03、TR-06、TR-07、TR-16、TR-18、TR-20、
TR-25；W05；AT-004、AT-005、AT-006的主要基础子项。

状态：IMPLEMENTED，未将W05整体或跨包AT标为VERIFIED。A01—A26已实际完成
配置加载、数据库任务派发、fake provider调用和结构化输出；真实模型专业能力、
完整审核回流、技能容器及现实验证仍等待后续。

## 已交付

- `config/agents/roles.yaml`包含A01—A26稳定编号、版本、职责/非职责、汇报、
  复核、技能、工具允许/拒绝、来源策略、模型/限额档位和三类别验收案例。
- 启动时验证恰好26岗、无重号、内部引用有效、允许/拒绝工具不相交。
- `agent_delivery.v1`统一交接合同包含事实状态、分析、反证、未知、建议、
  证据引用、限制和独立复核标记。
- 机器可读`agent-roles.v1.schema.json`和`agent-delivery.v1.schema.json`。
- fake/live provider使用同一`generate_structured`请求/响应合同；W05只启用
  fake，live provider明确不可用。
- 每个项目×岗位×版本建立独立`context_namespace`，不共享对话或临时文件。
- Runner固定角色版本、理论hash、policy profile、任务输入快照和provider。
- 输出校验角色/版本/项目/任务、mock标记、独立复核标记和引用子集；允许一次
  有限schema修复，失败进入可检查错误而不伪造完成。
- 首席A02、运营A03、质量A25和反证A26的交付分别保存；A25/A26标记独立上下文。
- Runner只将任务推进到`submitted`，从不写入`accepted`或代替复核。
- agent实例与runs受项目RLS保护；W03/W04/W05合计20条策略。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
make schema
```

本轮结果：

```text
31 passed
26/26 roles loaded and dispatch/run tested
A25/A26 independent_context=true; A02/A03=false
Ruff: all checks passed
mypy: no issues found in 48 source files
Alembic: W05 rollback and W02-W05 reapply passed
PostgreSQL: 20 RLS policies
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- W06才实现可执行技能注册、文档/网络适配器和非root容器限制。
- W17才实现A25/A26完整审查、critical缺陷阻断和返工回流；W11才实现计划/派工审批。
- 当前fake provider不包含科学知识，不代表模型专业化、专家意见或科学结论。
- 尚未配置真实模型价格、额度、provider数据政策或凭据；W22才可做有限live验证。
- 长期worker进程、项目业务HTTP路由和浏览器岗位场景尚未接线。
- Compose容器仍未在本机运行。
