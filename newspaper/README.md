# Newspaper — 个人双语报纸

**当前版本 V0.7：真正的原文阅读，不是 AI 摘要。**

## 每日输出

- 北京时间前一自然日的精选报道；BBC World、The Guardian、CNBC、TechCrunch、Y Combinator 等为候选来源。RSS 抓取/正文识别失败或无法公开阅读时，自动选择其他候选报道，不伪造原文。
- 报纸 PDF 采用用户已认可的 A5 竖版、衬线英文字体、中文宋体风格。每个领域下面排列媒体、作者、英文原标题、中文标题及正文。
- **原记者的英文句子在上，对应中文翻译立即在下一行**；连贯顺序和段落保留。长文在最大 18,000 英文字符以内尽量收录可提取的全部正文，遇到截断明确注明是连续选段。
- 不再把报道缩成标题 + “据媒体报道” + 空洞机制解释；不放编者导语、顾问观察、事实材料、正文英语附录，也不显示原文网页链接。
- 每篇最多三处语法数字标注，解释在紧随正文的位置，不复制大段原句。
- **邮件正文**独立由 DeepSeek 基于当天入选文章生成中文全球形势评论；不让 DeepSeek 修改 PDF 的记者英文原句。

## 费用及安全

- QQ SMTP：`NEWSPAPER_SMTP_FROM`、`NEWSPAPER_SMTP_PASSWORD`、`NEWSPAPER_TO`。
- DeepSeek：`NEWSPAPER_LLM_API_KEY`；默认 `deepseek-flash`，每次正式工作流最多一次请求，无自动重试，`max_tokens=2400`。
- 单次 AI 预算最高人民币 ¥0.20，内部执行预警线 ¥0.18。按照**请求发生的北京时间**判断：周一至周五 09:00–12:00、14:00–18:00 采用高峰价格，其余采用官方低谷价格。中国法定假日保守按普通工作日分类，以避免低估成本。费用估算基于全部缓存未命中的输入及允许的最大输出 tokens。
- 当前报价：Flash 高峰输入 ¥2/百万 tokens、输出 ¥8/百万 tokens；低谷输入 ¥1/百万 tokens、输出 ¥4/百万 tokens。程序在 GitHub 上预估费用，若超出 ¥0.18 则不发出请求。最终结算仍以 DeepSeek 实际收费为准，服务商可能调价。
- API Key 和 QQ 授权码只在 `main` 分支正式发送步骤注入；PR、模拟预览、真实数据 dry-run 全部不调用付费 API 或读取密钥。

## GitHub 操作

1. 打开 [Newspaper Actions](https://github.com/pyzz58/gpt-recommendations/actions/workflows/newspaper.yml)。
2. 主分支 `main`，`dry_run=true` / `preview_kind=live`：只生成真实素材的 PDF、HTML 和 TXT 预览，不发信。
3. 主分支 `main`，`dry_run=false`：抓取真实新闻、生成 PDF、调用最多一次 AI 评论并投递 QQ 邮箱。
4. 每天北京时间早上 07:00 定时尝试发信；GitHub 不保证分秒准时。失败可在 Actions 日志查看具体阶段。

新闻源版权、传播和使用限制应由来源提供方的规则及适用要求另行确认；程序不能突破登录或付费墙，也不能把来源无法获得的文章伪装成完整报道。
