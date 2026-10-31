# W13 数据版本、统计与复核接手说明

对应：RQ-017及相关原始数据/统计要求；TR-04、TR-06、TR-08、TR-11、TR-12、
TR-17、TR-18、TR-20、TR-25；W13；AT-017。

状态：IMPLEMENTED，未VERIFIED。不可变raw/清理数据版本、预设统计计划、可复现
计算、图表spec和复核记录已通过真实PostgreSQL、API及页面测试；数据真实性、
研究设计正确性、Office导出和W17独立统计/科学审查仍未验证。

## 已交付

- 从知识库不可变CSV/XLSX原件登记Dataset raw版本，不复制后覆盖用户原路径。
- CSV使用UTF-8-sig，拒绝重复/空header、宽度不一致和超行数；XLSX拒绝未重算
  公式；原始值、缺失与导入质量发现保留。
- Dataset manifest记录原文件hash、media type、size、source label、synthetic、
  received/registered时间、数据字典和缺件；DatasetVersion固定行hash和列。
- raw版本只能通过新的derived版本清理；支持显式选列、重命名、数值转换和
  指定列缺失删行，并保存转换理由、父版本和前后行数。
- DatasetRow按版本和row_index独立保存；同一版本行内容不可通过命令覆盖。
- StatisticalPlan在计算前保存问题、终点、方法、分组、分析集、缺失政策、单位、
  alpha、预期组和限制；DatasetVersion变更不会追溯改写已有计划。
- 首轮方法：
  - 连续终点描述统计：n、mean、median、SD、IQR、min/max和正态近似均值区间；
  - 两组均值差：组均值、差、标准误和正态近似区间，不伪造p值；
  - 比例Wilson区间：只接受0/1二分终点。
- AnalysisRun绑定dataset row hash、plan、code version/source hash、Python环境、
  随机种子、输入/输出hash、result和chart spec；相同命令可幂等重放。
- AnalysisReview支持A14/A25/A26角色合同，critical缺陷强制changes_requested。
- 新增6张表并启用FORCE RLS，累计56条策略。
- 数据统计页支持知识库表格导入、版本切换、受限预览、清理、计划、计算、简单
  图表、结果hash和复核；合成数据显示醒目标记。

## 主要路径

- 数据/统计合同：`services/core/src/medical_one_person/domain/datasets.py`
- 导入/清理/计算服务：`services/core/src/medical_one_person/application/datasets.py`
- CSV/XLSX解析：`services/core/src/medical_one_person/infrastructure/tables.py`
- API：`services/core/src/medical_one_person/api/datasets.py`
- 迁移：`services/core/migrations/versions/bee2b2f5fefa_w13_datasets_statistics_reviews.py`
- 页面：`apps/web/src/app/projects/[id]/datasets/page.tsx`
- 合成样例：`fixtures/dataset-study-example.csv`

## 验收

```bash
export MEDICAL_ONE_TEST_DATABASE_URL='postgresql+psycopg://admin@127.0.0.1:5432/medical_one_test'
PATH="/Users/zz/Library/pnpm/bin:$PATH" make test
PATH="/Users/zz/Library/pnpm/bin:$PATH" make lint
PATH="/Users/zz/Library/pnpm/bin:$PATH" make build
```

本轮结果：

```text
71 core tests passed (`make test`)
15 traceability self-tests passed
W13 migration: 2fa7e200f2d9 -> bee2b2f5fefa round-trip passed
RLS: 56 policies; all 6 W13 tables FORCE RLS
Import: missing values retained; duplicate headers and formulas rejected
Versions: raw V1 preserved; cleaned V2 has 6 rows and parent hash
Statistics: mean 14.5, group difference -5, binary proportion 0.5
Analysis: deterministic code/data/environment/result hashes and idempotency
Review: critical accept rejected; A14 review record accepted
API: knowledge CSV upload -> raw import -> cleanup -> plan -> analysis -> review
Browser: dataset preview, version history, chart and review rendered
Ruff and mypy passed
Next.js lint, typecheck and production build passed
```

## 尚未完成

- 这些方法只验证计算合同，不证明数据真实、组间可比、样本量充分或分析集正确。
- 两组均值差使用正态近似区间且没有p值；没有随机化推断、混合模型、回归、
  生存分析、协变量调整或敏感性分析。
- A14/A25/A26复核由workspace owner代表岗位合同记录，不是W17独立Agent或真人
  统计专家意见。
- 当前只支持CSV和首版XLSX；不支持多文件数据包、ZIP、公式重算、复杂表头、
  SAS/SPSS、外部数据库或超10,000行大数据。
- 尚未生成Word/PPT/Excel/PDF统计报告，W14接续。
