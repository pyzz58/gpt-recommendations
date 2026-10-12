# Newspaper — 全球形势秘书简报 V0.5

> 本次基于用户实际收到的 QQ 邮件反馈重构。**A5 报刊风格 PDF 附件是主交付件**；邮箱正文只含简短说明。所有改造和测试均通过 GitHub Actions，不要求用户本地环境。

## V0.5 现在提供什么

- 主体为**中文**事件和条件性形势分析：封面→编者导语→六个领域→跨领域观察。
- 真实新闻/来源仍采用既有 RSS + Trafilatura 采集；不把记者原文当作“秘书原创深入研究”。当前分析仅为**来源有限的规则型机制解释**，深度短板需如实说明。
- 取消工具式栏目名“英文标题”、“事实材料”、“Grammar Focus”及旧词汇表；英文/中文逐句内容仅在 PDF 最后“英语阅读附录”。
- 英语附录：**英文一句→中文紧下一行→下一句英文**；最多三处语法下划线+数字上标，在附录末尾数字对应一行简明解释，无大段原文重复。
- 视觉：GitHub Actions 在 Ubuntu 上安装开源 Noto CJK 书宋和 Liberation 字体；WeasyPrint 构建**A5 竖版单栏、可选中文可搜索**的 PDF。
- 支持 `--demo` （纯排版）、`--dry-run`（真新闻完整流程，不发邮件）和正式发送。模拟/预览的 GitHub artifact 同时包含 PDF、HTML 和 TXT；正式工作流以 QQ SMTP SSL 将 PDF **真正作为附件**发出。
- 邮件 Secrets 只在 main 发送步骤出现，PR/demo/live 预览没有权限访问；配置名称仍为 `NEWSPAPER_SMTP_FROM`、`NEWSPAPER_SMTP_PASSWORD` 和 `NEWSPAPER_TO`。

详细设计及验收指标：[V05_PRODUCT_SPEC.md](V05_PRODUCT_SPEC.md)。

## 如何直接在 GitHub 测试

1. 打开 [Actions / Newspaper](https://github.com/pyzz58/gpt-recommendations/actions/workflows/newspaper.yml)。
2. Run workflow → main → `dry_run=true` → `preview_kind=live`：抓取真实新闻、生成 PDF/HTML/TXT，**不发信**；下载 artifact `newspaper-demo-preview`。
3. 邮箱三个 Secrets 已设置后，Run workflow → main → `dry_run=false`：生成真实新闻并将 PDF 附件发至配置收件箱。
4. 另有一个经本次改造 PR 明确授权的一次性 PDF 测试投递，只有更新 `V05_MAIL_TEST_REQUEST.txt` 的 main 提交，且提交标题包含 `[newspaper-v05-send-once]` 才执行。普通代码提交不会借此发信。

如 GitHub Actions 为红叉，打开失败步骤看日志；不应向聊天或公开仓库发送 QQ 授权码。

---

## V0.4 历史说明（不再代表当前版式）
## 一、当前实际能力

- 六个栏目：全球新闻、美股与投资、美联储与宏观、创业与商业模式、AI 与科技、医疗与科学，合计最多 14 篇／日。
- 预先维护的多个 RSS 入口；根据发布时间筛选昨日报道，使用 scikit-learn 对标题相近事件聚类和规则评分，再尝试从候补来源读取文章。
- 使用 Trafilatura 提取可公开访问的连续英文正文选段，最少约 1400、最多约 6500 英文字符，不随机跳段。收费、打不开或长度不足的文章自动尝试其他候选；不能保证每天填满 14 篇。
- 使用 spaCy 官方英语模型将文章切为原始英文句子，Argos Translate 离线译中。邮件正文严格按**英文一句／下一行中文一句／再下一句英文**排列，不合并、不在两行中间插入空白行。
- 首页直接进入六大领域顾问观察，取消今日新闻速览、TOP5 榜单和词汇表；每篇保留最多 3 个从实际英文句子抽取的语法讲解。
- 每篇加入为什么关注、后续监测指标和证据限制；跨领域关联是可解释的观察路径，**不是事实已验证的专家预测**。
- 不需要付费新闻 API 或 LLM API。GitHub 免费运行器与 QQ SMTP 是否长期可靠仍需实际数据测试。

**现实边界：**顾问文字来自预设规则/框架，不是 GPT Researcher、STORM 或真实大模型自动写出的独立深度报道；专业英语离线翻译可能不准确。读到的正文为原文连续选段，不代表完全授权转载；部署时应注意各新闻网站的使用与版权条款。

## 二、邮箱与安全设置（手机即可）

建议额外准备一个专用 QQ 邮箱用来**发信**，你的常用 QQ 邮箱只作为**收件人**。本仓库是 public：代码与 Actions 日志可公开看见，Repository Secrets 的值不会作为代码显示，但若账号被盗、工作流代码被恶意修改或依赖遭到攻击，授权码仍可能泄露，绝非零风险。

1. 登录发信 QQ 邮箱网页版 mail.qq.com，按页面提示进入【设置】→【账号与安全】，开启所需的 SMTP/IMAP/POP 服务并生成发信**授权码**。它**不是 QQ 账号登录密码**。QQ 页面名称可能变更。请勿把授权码发送给任何聊天机器人或粘贴在公开位置。
2. 打开仓库 Settings → Secrets and variables → Actions → New repository secret；配置以下三项：
   - NEWSPAPER_SMTP_FROM：专用发件 QQ 邮箱地址
   - NEWSPAPER_SMTP_PASSWORD：QQ 邮箱 SMTP 授权码
   - NEWSPAPER_TO：日报收件邮箱地址
3. 允许 GitHub 账号的双因素认证；仅授予可信用户本仓库写权限。不要在公开 Issues、PR 或 Actions logs 写入授权码。建议在发信测试成功后定期检查安全设置；不用了立即撤销 QQ 授权码。

**凭证隔离：**邮件凭证不在工作流的 job-level env 中，普通 pull_request 运行、测试和预览不会注入。只有默认 `main` 分支由 schedule 或人工 dry_run=false 触发的正式发送步骤才获得三个 SMTP secrets；GitHub 默认 Token 被限制为 `contents: read`。此设置降低泄露面，不能保证绝对安全。

## 三、运行 / 测试

进入仓库 → **Actions** → **Newspaper - Bilingual World News** → **Run workflow**。在默认 `main` 分支操作：

| dry_run | preview_kind | 效果 | 发邮件？ |
|---|---|---|---|
| true | demo | 虚构占位内容，用于排版检查 | 否 |
| true | live | 当天真实 RSS、正文选段、机器翻译、语法、顾问规则的完整试跑；生成 HTML/TXT 预览 artifact | 否 |
| false | 不影响 | 正式实时新闻生成并通过 QQ SMTP 发信；必须先配置三个 Secrets | 是 |

预览任务运行完成后，到 Actions 对应任务底部的 Artifacts 下载 `newspaper-demo-preview`（HTML 和 TXT，保存 3 天）。移动端可在 GitHub 手机浏览器切换桌面网站模式查看控制。

如果直播预览抓不到正文/翻译模型下载失败，任务会报错，不会伪造成功邮件。GitHub 定时任务排队可能延迟；公开仓库连续长时间无活动可能导致定时运行停用。

## 四、代码与验收

| 文件 | 功能 |
|---|---|
| feeds.json | RSS、时区、选题配额、每篇阅读长度和顾问模式 |
| reader.py | 连续正文抽取与付费墙的基础过滤 |
| ranking.py | 近似事件合并、可解释评分、备用文章 |
| adviser.py | 规则型领域分析、证据局限与待观察指标 |
| english_lessons.py | 真实原句语法检测 |
| digest.py | 日期筛选、英中对齐、HTML/TXT 和 SMTP 发送 |
| test_*.py | 内容及邮件凭证隔离回归测试 |
| .github/workflows/newspaper.yml | GitHub 定时、模拟／真实预览及发信 |

本地回归：`python -m unittest discover -s newspaper -p 'test_*.py' -v`。
项目深度研究架构的未来选项另见 `ADVISER_ARCHITECTURE.md`；现阶段不新增连续研究能力，优先正式跑通真实新闻和 QQ 发送。
