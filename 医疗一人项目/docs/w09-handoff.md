# W09 机会比较与选择接手说明

对应：RQ-003、RQ-008、RQ-021、RQ-028、RQ-031；TR-04、TR-05、TR-11、
TR-16、TR-18、TR-20、TR-25；W09；AT-003、AT-008、AT-021、AT-028、AT-031的
主要合同子项。

状态：IMPLEMENTED，未VERIFIED。机会卡/科学简报版本、概率与成本结构、负责人
选择和历史事件已通过真实PostgreSQL测试；机会页面属于W10，完整计划/派工属于
W11，真实专业意见、询价、科学评价和外部协作均未取得。

## 已交付

- `OpportunityCard`区分宠物药、IVD和器械；要求分列科学、注册、专利、制造
  与商业缺口，并保留下一轮验证、成功/停止条件和重评触发条件。
- 机制事实无引用时拒绝；概率必须绑定事件、条件、期限与成功标准。
- `unknown`概率/成本不能携带伪数值；主观情景不能标为已校准；没有依据的
  empirical/validated模型概率被拒绝。
- 成本按阶段、币种、来源类型和范围记录；真实quote/published/historical来源
  必须有引用，unknown不得写成0。
- Opportunity和OpportunityVersion持久化不可变卡版本，修改使用
  `expected_revision`，旧版本保留。
- ScientificBrief按项目版本化保存，并写项目事件。
- `select_opportunity`只接受已验证的workspace owner；保存候选人、理由、范围、
  证据版本和幂等hash。相同参数重放原decision，参数变化返回冲突。
- 选择证据只接受当前项目的ClaimVersion或KnowledgeDocumentVersion；任意
  UUID、重复ID和其他项目证据被拒绝。
- W09新增4张表全部启用并强制workspace RLS；累计45条策略。
- 导出OpportunityCard、ScientificBrief、ProbabilityEstimate和CostEstimate的
  JSON Schema，并提供明确标为`synthetic_mock`的三领域样例。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
```

本轮结果：

```text
51 core tests passed (`make test`)
15 traceability self-tests passed (`tools/test_traceability.py`)
W09 migration: bc959837d3ea -> a823720b9684 round-trip passed
RLS: 45 policies; all 4 W09 tables FORCE RLS
Three tracks: synthetic pet repurposing, IVD and device
Selection: non-owner, stale revision, missing/cross-project evidence rejected
Idempotency: exact replay equals first result; changed parameters conflict
Versions: opportunity revision and two scientific brief versions preserved
Ruff and mypy passed
Next.js lint, typecheck and production build passed
```

## 尚未完成

- 本页和现有开发骨架不是机会选择UI；W10才实现项目/知识/机会浏览与交互。
- 选择不会自动生成W11有界DAG或派工，不改变项目为active，也不授权费用。
- 合成候选、区间、金额和专业意见不是事实、报价、客户反馈或专家背书。
- 没有真实模型、专业检索连接、专家反馈、机构询价、科学盲测或现实执行。
- 当前无法运行Docker/Compose，容器隔离仍未验证。
