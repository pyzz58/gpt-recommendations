# 内参系统｜GitHub项目目录、真实状态和未来工程结构

> 目的：未来AI打开GitHub就能知道**哪些文件真实存在、哪些只是建议未来建立**，避免把设计方案误当已部署模块。2026-10-13 V4.0。

## 1. 规范定位
- 官方项目名：**内参系统**；兼容别名：全球战略内参、Global Strategic Intelligence（GSI）。
- 仓库：`pyzz58/gpt-recommendations`。
- 独立项目根：`newspaper/strategic-intelligence/`。
- 中文入口：`newspaper/内参系统.md` → `strategic-intelligence/README.md`。
- `newspaper/`其它日报源码、工作流、Secrets与历史属于**另一产品**，不受本项目设计工作影响。

## 2. 已经真实存在的核心框架（实际创建文件）

```text
newspaper/
  内参系统.md                     # 中文搜索入口；导航用，不复制系统配置
  strategic-intelligence/
    AGENTS.md                     # Codex / AI 工作边界与阅读顺序
    HARD_RULES.md                # 禁止概念性总结、周报年报、用户赞同归档
    DOMAIN_TEACHING_PROTOCOLS.md # 九栏事实→专业根因→案例→迁移
    HUMAN_NATURE_AND_CLASSICAL_LENSES.md # 博弈、人性和古典文化证据化
    ANNUAL_REPORT_SPEC.md        # 年度来源双输入与十二道年报工序
    ENDORSEMENT_LEDGER.md        # 用户赞同方案的细节档案
    HISTORY_RECONCILIATION.md    # 旧讨论回查与已知遗漏
    README.md                     # 当前状态唯一入口
    MASTER_BLUEPRINT.md          # 产品总纲
    DECISIONS.md                 # 用户确定/未确认/放弃的事项
    TRACEABILITY_MATRIX.md       # 50条讨论内容防遗漏映射
    VISION_AND_SCOPE.md          # 六项目标、九栏目、权重
    EDITORIAL_POLICY.md          # 事实、证据、反茧房、审稿
    ADVISOR_PEDAGOGY.md          # 顾问教学原理
    COGNITIVE_ADVISOR_SKILL.md   # 可转成实际Skill的研究/教学细则
    SOURCE_DISCOVERY.md          # 独立全球发现
    SOURCE_REGISTRY.md
    SOURCE_REGISTRY.json         # 124条活跃来源的机器登记
    SOURCE_ABANDONED_2026-10-13.json # 6条用户放弃的来源历史
    SOURCE_ACCESS_BLOCKLIST.md   # 收费/版权权限限制
    SOURCE_VERIFICATION_PLAYBOOK.md
    SOURCE_TOOLING_RESEARCH.md
    ACCESS_AUDIT_2026-10-13.md
    ACCESS_AUDIT_2026-10-13_FULL.md
    SOURCE_RECOVERY_AUDIT_2026-10-13.md
    SOURCE_CLOUD_SMOKE_AUDIT_2026-10-13.md
    END_TO_END_WORKFLOW.md       # 12道工序与故障/回退
    DATA_CONTRACTS.md            # 每步数据交换与历史版本
    INTELLIGENCE_MEMORY.md       # 主题/判断/概念归档
    PUBLICATION_SPEC.md          # 周报/年报刊物规格
    QA_AND_METRICS.md            # 六项目标测试、100分审核、回归测试
    TECHNICAL_DESIGN.md
    IMPLEMENTATION_ROADMAP.md    # 历史阶段计划（以BUILD_PLAN为最新）
    BUILD_PLAN.md                # 最新执行路线
    PROJECT_STRUCTURE.md        # 真实/预期目录边界
    OPERATIONS_AND_COST.md       # 成本、可靠性、安全和生产门禁
    ACCEPTANCE_AND_HANDOFF.md
    CHANGELOG.md
    内参系统.md                   # 中文搜索入口
    audits/
      source-smoke-20261013.json
      source-smoke-round2-20261013.json
      source-smoke-round3-20261013.json
      source-smoke-round4-20261013.json
      random-four-20261013.json
    templates/
      ARTICLE_TEMPLATE.md
      WEEKLY_TEMPLATE.md
      ANNUAL_TEMPLATE.md           # 正式年报模板
      MONTHLY_TEMPLATE.md          # DEPRECATED历史模板，禁止使用
      THESIS_TEMPLATE.md
    skills/chief_advisor/
      SKILL.md                   # 项目内部的设计Skill，非系统插件安装
    tools/
      source_probe.py           # 低频手动测试脚本，非生产采集器
```

上方列表为V3.0交付计划中的文件；实际核验以GitHub API读取结果为准。如未来部分新增文件因权限/错误未落库，应及时修订而非假装存在。

## 3. 尚未建立的未来工程结构（建议、不代表已完成）

```text
  src/
    sources/
    discovery/
    events/
    research/
    advisor/
    review/
    editorial/
    publisher/
    archive/
    common/
  configs/
    sections.yaml
    models.yaml
    discovery.yaml
  schemas/
    candidate.schema.json
    dossier.schema.json
    review.schema.json
    edition.schema.json
  tests/
    fixtures/
    unit/
    integration/
  migrations/
  jobs/
  private_storage/  # 强烈建议迁出公共GitHub仓库，另行授权
```

**不在本轮创建这些空壳工程代码**。真实实现时先建能通过冻结六案例的小组件；不要在没有真实业务逻辑时创建几十个文件假装完成开发。

## 4. 文档权威与防止多份真相

优先级：用户最新明确指令 → DECISIONS.md里生效决定 → SOURCE_REGISTRY.json当前活跃源状态 → MASTER_BLUEPRINT产品总纲 → 专业规范文档（同领域细节）→ 历史研究/测试材料。

- 历史审计源测试报告中的“130个、A94/B5/C31”等数是**当时历史事实**，不是当前活跃源。当前为124条A116/B8；禁止不注明时间就展示混杂数字。
- 新旧路线图出现来源数量矛盾，以最新BUILD_PLAN和DECISIONS为准，旧路线图要加历史警告。
- 具体数据库表、语言模型、云执行环境尚未定案，方案中的名字不是真实运行资产。
- 历史观点和当时原文不得被新AI总结覆盖；更新采用CHANGELOG与判断版本新增。

## 5. Codex从GitHub开始执行的步骤
1. 进入目录读AGENTS.md及README.md。
2. 对照MASTER_BLUEPRINT、DECISIONS和TRACEABILITY_MATRIX理解需求。
3. 以BUILD_PLAN确定本阶段是否被授权开始；当前只设计。
4. 对需要开发的部分读DATA_CONTRACTS与END_TO_END_WORKFLOW和QA_AND_METRICS。
5. 若只做顾问写作，加载COGNITIVE_ADVISOR_SKILL及skills/chief_advisor/SKILL.md；不要因九栏目创造九个Agent。
6. 对资料库操作需要检查权限、秘密信息和历史源定位，不得把公共GitHub当私有档案云盘。
7. 提交变更后附文件路径、真实测试证据、问题清单和未完成项。

## 6. 文档一致性验收
所有.md内部链接必须存在；不同文档提到来源数量应说明日期与最新状态；AGENTS与README应指向唯一正式路径；没有未授权生产任务和发信动作；源档案与历史日志保持可读；用户所有重要诉求均可在TRACEABILITY_MATRIX查到。

## V4.0变更记录：真实存在与尚未实现

新增HARD_RULES、九栏专业教学、古典与人性透镜、ANNUAL_REPORT_SPEC、ENDORSEMENT_LEDGER、HISTORY_RECONCILIATION以及[templates/ANNUAL_TEMPLATE.md](templates/ANNUAL_TEMPLATE.md)，旧MONTHLY模板仍存在但首行标DEPRECATED，仅为历史追踪。**这些均是Markdown规则/模板，不等于真实研究、教学和审稿程序已实现**。当前正式内参产品只有WEEKLY/ANNUAL，不得生成MONTHLY作业或邮件。
