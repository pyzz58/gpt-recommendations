# 全球形势顾问 — 开源研究代理架构与升级边界

## 愿景

每天北京时间 07:00，按昨日北京时间的事件事实，形成可追溯的全球政治、宏观金融、美股投资、创业商业、AI 科技、医疗科研分析，不局限于罗列新闻。

输出重心是：发生什么 → 证据来自哪里 → 为什么重要 → 不同观点与不确定性 → 对其他行业的连锁影响 → 下一步观察指标。

原始英文证据采用“一句英文、一句对应中文”的相邻排版；顾问自己的中文分析不能伪称来自某媒体的英文原句。取消顶部要闻速览与末尾重点单词，保留每篇有原文依据的语法练习。

## 当前 V0.4：无需 API 的可信基线

证据采集：RSS / Trafilatura；排序聚合：scikit-learn；断句：spaCy；翻译：Argos Translate；领域分析：adviser.py（明确注明是规则与观察框架）。

不能声称：已经使用 GPT Researcher、STORM 或 CrewAI 跑完深度研究；不能声称该规则可以准确预测利率或股票价格；不能把多个媒体同一口径视为独立核实。

## 研究顾问升级（候选成熟项目）

1. 研究计划与问题拆解：参考 [GPT Researcher](https://github.com/assafelovic/gpt-researcher) 的 planner/execution 思路。先为每个领域提出可核实问题，而不是让模型凭空总结。
2. 视角与深度：参考 [STORM](https://github.com/stanford-oval/storm) 的 multi-perspective question asking、提纲与证据引用。每个重大事件至少考虑政策、市场、技术、行业、反方观点。
3. 分工审核：参考 [CrewAI](https://github.com/crewAIInc/crewAI) 的 role-based orchestration。研究员检索证据、分析员列出推论、事实审核员核对出处、主编负责成稿、英语教师做逐句翻译及语法。
4. 本地模型后端：可选 [Ollama](https://github.com/ollama/ollama)，模型运行在用户自己可用的电脑或服务器上，不一定产生云端 API 费用；但需要额外硬件、电力与日常运维。

这些框架仍需要语言模型才能真正分析和生成长文。GitHub Actions 免费共享 CPU runner + 无模型服务，不等于已经具备顶级研究顾问能力。本阶段不要拉取巨大模型强行塞入每日定时任务。

## 未来证据契约

每条可发布的研究论点应能追踪到：

- claim_id, published_at_beijing, event_at_beijing（不能混淆报道日期和发生日期）
- source_url, source_name, source_excerpt（合法、短量引用）, license_notes
- observation（可在来源中核实）, inference（根据观察提出的推论）
- uncertainty 与 alternate_explanation, confidence_label
- verifier_result（可以指出无法核实，不能默认通过）

出稿守则：事实段落和顾问推理分开；至少两种不同来源交叉验证有争议的事实；任何数字要带单位、年份和原始出处；不能将预测当事实；关键论点无法核验则降级或剔除。

## 输出格式

领域状况评估 → 重要变化的多源材料（英文句1/译文1、英文句2/译文2……）→ 顾问解析/行业联动 → 反方或证据不足 → 关注指标 → 英语语法。从领域直接进入，不做顶部新闻要闻排行榜。

## 验收门槛

先在 7 天样本上检验：日期与时区准确性、来源可用率、重复事件覆盖、错译率、逐句双语对齐、推论证据出处、实际交付时间。存在明显幻觉或数值错误的深度模式不应进入自动邮件投递。

在用户同意前，不增加任何必须购买的 API，不要求用户提供密钥或将账户密码提交到仓库。
