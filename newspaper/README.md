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
- 2026-10-15 真实启动入口烟雾测试：[Run 38680528022](https://github.com/pyzz58/gpt-recommendations/actions/runs/38680528022) 通过，事件为 marker 文件 `push`，结果为 `ALREADY_SENT`。这是新 GitHub 启动入口测试，**不是外部定时器无人干预和次日真正生成发送的验收**。
- 独立定时服务自身是否可靠，必须结合其真实运行和下一期 GitHub Run ID 继续核查；不能因为配置保存成功就声称完成全链路验收。

历史故障见 [P0 事故审计](P0_TRIGGER_AUDIT_2026-10-15.md)。旧版本中的多条 cron、提前备稿和固定发送时间窗口均属于历史规则。

## 编辑标准

采用重大新闻详尽、普通报道适度精简；美股与全球资本市场为头版，中国与美国合计常态三篇、世界政治及 AI 科技等独立栏目；重大新闻附来源约束的因果解读，期末另设《今日关键变化》。多源事件聚类与交叉验证，保持原文语气、重要数字和当事方立场；尊重来源版权。

## 一般安全约束

PR 和 `dry_run` 都不能读取正式 SMTP Secret。人工 `workflow_dispatch` 默认只预览。真实邮箱发信须经过同日刊期检查与每日凭据检查；无事实来源或 PDF 生成失败不发送空刊。整期模型费当前采用更严格的人民币 ¥1.00 事前上限，不因规范改时间而提升付费额度。
