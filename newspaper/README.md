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

## 一般安全约束

PR 和 `dry_run` 都不能读取正式 SMTP Secret。人工 `workflow_dispatch` 默认只预览。真实邮箱发信须经过同日刊期检查与每日凭据检查；无事实来源或 PDF 生成失败不发送空刊。整期模型费当前采用更严格的人民币 ¥1.00 事前上限，不因规范改时间而提升付费额度。
