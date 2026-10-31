# W12 三领域专业流程与阶段证据门接手说明

对应：RQ-003、RQ-018、RQ-031及相关阶段流程；TR-04、TR-05、TR-08、TR-11、
TR-17、TR-18、TR-20、TR-25；W12；AT-003、AT-018、AT-031的主要合同子项。

状态：IMPLEMENTED，未VERIFIED。三领域流程、阶段判据、阶段决定、配置版本和
现实前置条件阻塞已通过真实PostgreSQL、API与页面测试；W16真实机构/报价/授权
证据、W17独立专业审查以及科学/监管适用性仍未验证。

## 已交付

- `config/workflows/catalog.yaml`固定加载宠物药、IVD、器械三个YAML package。
- 导出`workflow-definition.v1.schema.json`和`criterion-result.v1.schema.json`，
  供配置与阶段评估跨语言校验；JSON Schema通过不证明领域适用性。
- 每个领域使用统一严格schema，但保留四个领域阶段、必要岗位、输入/输出、
  判据、review policy、failure routes、外部前置条件和阶段计划节点。
- 加载时校验三领域完整、stage顺序唯一、岗位存在、plan node依赖有效、配置
  SHA-256固定；任一配置变化会使已提交但未激活的计划拒绝旧版本混用。
- 宠物药覆盖物种/需求、证据与转化/安全/药学缺口、验证设计、外部执行。
- IVD覆盖预期用途/样本、方法与分析性能、临床评价/质量、外部验证。
- 器械覆盖用户场景、设计输入/风险、验证确认/适用评价、原型与外部测试。
- StageAssessment保存workflow id/version/SHA、stage、判据结果、引用、外部
  前置条件、建议、rationale和不可变评估版本。
- 判据结果必须完整；met证据判据必须绑定项目内claim/document/decision/
  opportunity/assessment引用，不能只凭“AI认为通过”。
- 阶段决定独立保存A25/A26角色合同、用户原因和accepted/changes_requested/
  blocked状态；上一阶段未接受时不能评估或创建下一阶段计划。
- 三个领域的最终外部阶段都包含机构、报价/合同/授权、样本/批准或原型/测试
  前置条件。W12固定显示`unverified_w16`，不能用桌面材料或模型输出自行接受。
- 专业流程页展示三领域、四阶段、岗位、输出、判据、失败分支、评估历史、
  外部阻塞和阶段计划按钮；从已选择方向生成计划时使用领域阶段模板。
- W12新增stage_assessments、stage_decisions并给plans增加workflow版本字段；
  新表启用FORCE RLS，累计50条策略。

## 主要路径

- 领域合同与配置加载：`services/core/src/medical_one_person/domain/workflows.py`、
  `infrastructure/workflows/registry.py`
- 配置：`config/workflows/pet_repurposing.yaml`、`ivd.yaml`、`device.yaml`
- 阶段服务：`services/core/src/medical_one_person/application/workflows.py`
- API：`services/core/src/medical_one_person/api/workflows.py`
- 迁移：`services/core/migrations/versions/2fa7e200f2d9_w12_domain_workflows_assessments.py`
- 页面：`apps/web/src/app/projects/[id]/workflows/page.tsx`

## 验收

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
PATH="/Users/zz/Library/pnpm/bin:$PATH" make test
PATH="/Users/zz/Library/pnpm/bin:$PATH" make lint
PATH="/Users/zz/Library/pnpm/bin:$PATH" make build
```

本轮结果：

```text
65 core tests passed (`make test`)
15 traceability self-tests passed
W12 migration: 9ff9aac51d3e -> 2fa7e200f2d9 round-trip passed
RLS: 50 policies; stage_assessments and stage_decisions FORCE RLS
Workflows: 3 tracks x 4 domain-specific stages validated
Gate: complete project evidence required; previous accepted stage required
Domain plan: pet stage 2 materialized from workflow node template
External: real-provider preconditions remain blocked until W16
API: workflow list, stage assessment, stage decision and stage plan passed
Browser: professional workflow page and accepted evidence gate rendered
Ruff and mypy passed
Next.js lint, typecheck and production build passed
```

## 尚未完成

- StageDecision仍由workspace owner代表A25/A26岗位合同记录；W17才实现独立
  Agent/真人专家审查，不能把该记录称为独立科学审计。
- 证据引用只验证项目归属和对象存在，不自动验证全文质量、研究直接性或数字正确。
- 现实前置条件在W12固定阻塞；W16尚未提供真实机构、报价、合同、授权、原始交付
  和外部执行状态的持久记录。
- 配置判据是项目方法基线，不是任何国家/市场注册清单或法律适用结论。
- 阶段计划可以生成并进入W11 DAG，但真实外部阶段仍不能越过W16现实门。
