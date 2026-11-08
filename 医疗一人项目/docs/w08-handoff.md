# W08 检索与证据链接手说明

对应：RQ-011、RQ-012、RQ-023、RQ-026、RQ-034；TR-03、TR-04、TR-07、TR-09、
TR-10、TR-16、TR-18、TR-20、TR-25；W08；AT-011、AT-012、AT-023、AT-034的
主要基础子项。

状态：IMPLEMENTED，未VERIFIED。本地词法索引、检索快照、Citation、
claims/evidence和版本影响已通过真实PostgreSQL测试；知识库UI属于W10，独立
专业审查属于W17，删除/索引恢复属于W18，完整CRO数据闭环属于W21/W24。

## 已交付

- 从有版本 extraction 生成不可变 passage/table chunks，固定`lexical.v1`。
- 中文字符串和英文空格词的本地词法召回；标题和正文均可命中。
- 检索严格限定当前项目、active版本和版本策略；旧版默认排除。
- 每次检索创建RetrievalSnapshot，保存query、permitted versions、chunk IDs、
  content hashes、ACL revision和task。
- Citation必须精确来自chunk原文，保存version、extraction、locator和引文hash；
  核查状态初始为unreviewed。
- Claim和ClaimVersion区分物种/人群、干预、对照、终点、分析集、样本数和直接性。
- EvidenceLink以supports/refutes/context关联citation；支持与反对不会被一个综合
  状态覆盖。
- SourceReview记录版本范围、审阅人、结论和依据；reviewed_for_scope不等于全部
  科学断言正确。
- 当前版本提升使用expected_revision；旧版保留historical，新版current。
- 版本提升生成ImpactReview，定位旧Citation、ClaimVersion、RetrievalSnapshot和
  Task；相关claim标stale，不自动重写报告或重发外部动作。
- `supersedes` provenance edge和项目事件保留版本替换关系。
- W08新增9张表受RLS保护；累计41条策略。

## 测试

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
make test-integration
```

本轮结果：

```text
44 passed
Lexical retrieval: Chinese substring and current-version exclusion tested
Citation: exact quote and invalid quote tested
Claims: support link and V2 stale propagation tested
Snapshot: permitted versions/chunks/hashes persisted
Alembic: W08 rollback and W02-W08 reapply passed
PostgreSQL: 41 RLS policies
Ruff: all checks passed
mypy: no issues found in 66 source files
Next.js: lint, TypeScript and production build passed
```

## 尚未完成

- 没有pgvector/语义检索；不能把词法相似度当证据强度。
- W10才实现知识库上传、列表、详情、引用和版本比较页面；当前是后端服务。
- 尚无项目HTTP知识路由与浏览器认证接线。
- W17才实现独立A25/A26的人工/Agent审查闭环；W08的source review是记录合同。
- W18才实现删除、权限撤销后的索引清理和加密备份恢复。
- 真实外部来源、付费全文、OCR和CRO原始数据仍未接入。
