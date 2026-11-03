# Newspaper — 全球新闻双语日报

**这是新闻日报，不是独立的内参系统。**

## 生产唯一权威入口

- [production_policy.json](production_policy.json)：**唯一机器可读生产合同**（时区、截稿、定时制作、发送窗口、来源与产品原则）。任何改变时刻的提交，必须同步修改 Python、启动器、工作流入口和回归测试，并由 `verify_schedule.py` 校验一致性；禁止凭 README 里的旧时刻上线。
- [V2_IMPLEMENTATION.md](V2_IMPLEMENTATION.md)：详细需求、测试和验收标准。不得出现与上面 JSON 相矛盾的当前操作说明。
- [HISTORY_BEFORE_20261014.md](HISTORY_BEFORE_20261014.md)：旧版说明，仅供追溯，任何旧时间要求均已作废。

## 当前生产启动与交付（V2.5 权威规则）

- 唯一运行计划：独立自动任务每天北京时间 **00:01**，更新 main 分支 `newspaper/.scheduler-tick` 标记文件；GitHub Actions 的 `push` 过滤器只监听此文件，自动执行现有 `.github/workflows/newspaper.yml`。
- GitHub 自身的旧 `schedule` cron 已从正式工作流删除，避免继续积累多条失效触发器；PR 检验和人工 `workflow_dispatch` 仍保留。
- GitHub 启动后，按既有代码制作报纸和 PDF、校验邮件包、立即交给 QQ SMTP。**新闻生成、PDF、QQ 邮件代码均未因这次启动器替换而改变。**
- 本日相同刊期一旦有 SMTP 接受回执，重复启动将显示 `ALREADY_SENT`，不重发。
- 2026-10-15 启动入口烟雾测试：[Run 38680528022](https://github.com/pyzz58/gpt-recommendations/actions/runs/38680528022) 成功，事件为指定 marker 文件的 `push`，回执为 `ALREADY_SENT`。
- 2026-10-15 **外部定时器无人干预测试已成功**：定时任务自动更新 marker，提交 `e07d96f260ffe5079e9e061649fffd1845f789ab` 触发 GitHub [Run 38680948833](https://github.com/pyzz58/gpt-recommendations/actions/runs/38680948833)，`digest=success`，`NEWSPAPER_EXTERNAL_STARTUP_OK`，`ALREADY_SENT`。未改生成及邮件程序，也未重复发信。
- 下一期无人干预的 **生成 PDF + QQ SMTP 接受 + QQ 收件箱到达** 仍需按次日完整链路验收。

历史故障见 [P0 事故审计](P0_TRIGGER_AUDIT_2026-10-15.md)。旧版本中的多条 cron、提前备稿和固定发送时间窗口均属于历史规则。

## 自动启动故障与替代方案（2026-10-15）

- **已证实的限制**：ChatGPT 无人值守定时任务曾成功改写启动标记，但 2026-10-15 的一次性定时邮件测试又在 GitHub 写入操作被安全检查拦截。故这条链路不能作为可靠的正式启动器。普通聊天里手动修改 GitHub 成功，不等于定时任务具备相同授权。
- **新启动器代码已就绪，尚未云端部署**：[startup/worker.js](startup/worker.js) 与 [startup/wrangler.toml](startup/wrangler.toml)。Cloudflare Workers Cron 在 UTC 16:01（北京时间次日 00:01）使用 GitHub 的 `workflow_dispatch` 启动**现有** `.github/workflows/newspaper.yml`。不修改新闻采集、PDF、QQ SMTP 或当日回执代码。Cloudflare 对 Cron Trigger 配置的生效传播可能长达约 15 分钟，首次部署不得将短时未运行误认作故障。
- **部署必需的外部授权**：需要使用者在自己的 Cloudflare 账户中授权一次，并把 GitHub **仅对本仓库具有 Actions: Read and write** 的细粒度令牌存为 Cloudflare Worker Secret `GH_ACTIONS_TOKEN`；不在 GitHub 源码、聊天、日志保存令牌。已存在的 ChatGPT 定时标记入口在新启动器通过实际 GitHub Run ID 验证后停用，不应长期并行。
- 以仓库根目录为当前目录的部署命令（在有 Cloudflare 账户和有效凭据后执行）：
  ```sh
  npx wrangler login
  npx wrangler deploy --config newspaper/startup/wrangler.toml
  npx wrangler secret put GH_ACTIONS_TOKEN --config newspaper/startup/wrangler.toml
  ```
- **验收不是看到 HTTP 204 即结束**：204 只证明 GitHub 接受了启动请求。必须核实实际 `event=workflow_dispatch` 的 GitHub Run ID、PDF 成功生成、`NEWSPAPER_SMTP_ACCEPTED`；QQ 邮箱收件须另行确认。在外部部署及这些验收前，不得声称自动发信完全修复。

## 编辑标准

采用重大新闻详尽、普通报道适度精简；美股与全球资本市场为头版，中国与美国合计常态三篇、世界政治及 AI 科技等独立栏目；重大新闻附来源约束的因果解读，期末另设《今日关键变化》。多源事件聚类与交叉验证，保持原文语气、重要数字和当事方立场；尊重来源版权。

### 2026-11-04 小范围编辑升级（真实样刊待验收）

用户进一步明确问题重点是**新闻正文的写作水平**。在英文成文和离线译文之后，新增 [中文上下文编辑](CHINESE_NEWS_EDITOR.md)：提交本篇全部英文句子及段落关系，修正中文语序、衔接、指代与套话；保持英文、句子对应、段落位置及双语排版。每篇最多请求一次，重要报道优先，共用原整期 ¥1.00 账本。数字、百分比单位、明显否定及不确定条件、缺句或重复 ID 等校验失败时整篇保留原机译；这些机械检查不代替完整的中英语义核对。原生中文来源不重新机译。实际效果仍待付费接口恢复后的同源对照。

[中文写作文风样稿](CHINESE_WRITING_SAMPLE_20261104.md) 为本会话依据官方来源编写，不是运行程序产生的结果；其中直译对照明确为示意，不能冒充历史日报输出。

- [SELECTION_REVIEW.md](SELECTION_REVIEW.md) 将事件的重要性、新信息、证据强度、读者关联与代表稿完整度分开。参考 [AIHOT 评分规则](https://github.com/KKKKhazix/AIHOT/blob/main/industry/prompts/selection-score.md) 和 [BestBlogs 全文评估方法](https://github.com/ginobefun/BestBlogs/blob/main/flows/Dify/ArticleAnalysisFlow.md)，独立实现；未引入其框架或运行服务。
- 在既有抓取与最终选稿之间，按栏目轮询取最多 24 个可读候选，只做一次批量复评。长文只提交明确标注的首尾摘录，不声称完成全文审读。调整排序最多偏离原分数 20 分；稿件完整度作同分比较。原有栏目准入、来源上限、事件去重、地域保留和重大新闻阈值继续生效。
- 所有模型请求共用同一个 `EditionBudget`。复评事前估价最多 ¥0.18，属于整期 ¥1.00 内部额度；保留原有评论预算。超额、接口失败、返回缺项/重复/未知 ID/非法分数，整批保持原有顺序，不重试。预览不调用模型。
- 编辑提示词增加事实优先的导语、正文结构、准确段落映射和逐稿长度合同。短于 300 英文词的来源允许一至两段完整报道，不强迫拆三段；长稿仍要求完整报道。数字只归一等价格式（`5 percent` / `5.0%`、`1,000` / `1000`），新增数字或百分比单位继续拒绝；引语、否定、限制条件仍受原有校验约束。这些规则不构成完整语义核验。
- 日志 `NEWSROOM_EDITOR_REJECTIONS` 汇总固定的拒稿原因；中文原稿未提交英文编辑时不再误计为拒稿。选稿审计增加候选复评分与实际排序值，不记录正文。
- 验证与局限详见 [本轮验收记录](EDITORIAL_UPGRADE_20261104.md)。不得把模拟接口测试、离线标题夹具或误拒修复写成真实成刊质量已经提升。余额可用后，必须对同一批真实候选与成文并排验收；不得因此修改定时、PDF 或 QQ 投递流程。

## 一般安全约束

PR 和 `dry_run` 都不能读取正式 SMTP Secret。人工 `workflow_dispatch` 默认只预览。真实邮箱发信须经过同日刊期检查与每日凭据检查；无事实来源或 PDF 生成失败不发送空刊。整期模型费当前采用更严格的人民币 ¥1.00 事前上限，不因规范改时间而提升付费额度。
