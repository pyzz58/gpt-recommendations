# 医疗一人项目｜依据与来源

整理日期：2026-10-29。这里记录启示及适用边界，不把新闻案例写成普遍结论，也不以技术产品文档证明药物研发模式已成熟。

## 来源目录

| 编号 | 来源 | 支持什么 | 不支持什么 |
| --- | --- | --- | --- |
| S-001 | Anthropic，Early progress on accelerating drug development with Claude，2026-10-27 | 一个内部精简、借助AI和外部研发网络推进项目的公开案例；人仍决定科学方向与关键事项 | 不能证明无技术基础、少量资金或任意个人能够复现其成果；不能证明药物人体有效 |
| S-002 | OpenAI，Working with academic communities to build scientific understanding，2026-10-26 | AI产生研究材料后仍需要形式化检验和学术共同体解释、核查的协作启示 | 不能据此认为普通Agent模板可获得同等能力，或相关数学能力直接转化为药理判断能力 |
| S-003 | OpenAI，Agent definitions、Orchestration and handoffs | 角色可以由指令、模型、工具及运行设置组成，程序可组织任务调用和交接 | 不证明本项目已完成专业化、业务流程或权限隔离；不意味着必须采用某套SDK |
| S-004 | OpenAI，Evaluate agent workflows | 保留运行记录、明确评价标准、重复评估和改进的工程方法 | 不等于医学/药学能力认证，也不提供本项目现成合格阈值 |
| S-005 | FDA，AI支持药物监管决策的2025年草案 | 针对具体使用场景评价AI输出可信度的风险思路 | 不是本项目中国兽药注册法律结论，草案亦不能写成已生效强制要求 |
| S-006 | Mirataz标签、原始试验索引及中国第793号公告 | 已知药物回放中可核对样本口径、短期终点及批准范围 | 不是本项目的新发现、推荐候选或商业空白证明 |

## 原始链接

- S-001：https://www.anthropic.com/research/early-progress-drug-development
- S-002：https://openai.com/index/building-scientific-understanding-with-academic-communities/
- S-003：https://developers.openai.com/api/docs/guides/agents/define-agents
- S-003：https://developers.openai.com/api/docs/guides/agents/orchestration
- S-004：https://developers.openai.com/api/docs/guides/agent-evals
- S-005：https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological
- S-006：https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=5ff9fdb7-554f-4f91-8cfc-6d05094384c6
- S-006：https://pubmed.ncbi.nlm.nih.gov/30506924/
- S-006：https://xmsyj.moa.gov.cn/zwfw/202405/t20240530_6456403.htm

## 本项目自行提出的方法设计

以下是根据目标形成的组织建议，尚待检验：完整职责与按需运行相结合；专业岗位固定输入输出；交接可追溯；审核能够退回；先评价组织、再评价科学判断和具体项目；保留失败案例；按阶段决定投入。

这些建议不应包装成某篇文献已验证的完整商业模式。后续需要补充实际案例、质量、成本和外部反馈证据。

## 技术维护依据

- Codex项目指令：https://learn.chatgpt.com/docs/agent-configuration/agents-md
- GitHub仓库创建与命名规则：https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository

资料日期和状态需在实际使用时重新核查。引用来源的范围不能超过其原文能够支持的结论。
