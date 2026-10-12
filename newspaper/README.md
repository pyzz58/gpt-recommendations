# Newspaper — 全球新闻双语日报

使用 GitHub Actions 自动收集前一日（北京时间 00:00–24:00）的新闻，在北京时间每天早上 07:00 尝试发送到指定邮箱。支持全球新闻、美股、美联储、创业、AI 科技、医疗科学。

## 运行模式

- 无需新闻平台 API Key，也无需 OpenAI/DeepSeek API Key。免费 RSS、可公开访问的新闻页面与 Argos Translate 离线英中翻译。
- 配置了多个候补来源；如果文章有付费墙、抓取失败、正文太短或无法确认发布日期，就跳过，优先选同一栏目其他来源。
- 每篇包含来源、发布时间、英文标题、中文标题、英文正文阅读选段、对应中文翻译、原文链接。不是仅转载 RSS 摘要；但为了版权与篇幅限制，也不宣称能全文复制所有商业媒体文章。
- 只收集北京时间前一个自然日的新闻。无新闻的栏目不填充旧新闻；某些日子文章不足则少发。
- GitHub Actions 的定时启动可能延迟，GitHub 和邮箱网络也可能影响实际到达时间；不是 07:00 正点投递保证。
- 仅私用阅读；不突破付费墙、登录和反爬访问限制。公开转载内容需另行核对版权和来源条款。

## 部署步骤

1. 将开发分支的 Pull Request 合并进入默认分支 main。GitHub 定时工作流只在默认分支运行。
2. 在用于发信的 QQ 邮箱网页设置中开启 SMTP，并生成【SMTP 授权码】，它不是 QQ 登录密码。收件邮箱可以与发件邮箱不同。
3. 打开仓库 Settings → Secrets and variables → Actions → New repository secret，依次设置：
   - NEWSPAPER_SMTP_FROM：发件 QQ 邮箱地址（如 example@qq.com）
   - NEWSPAPER_SMTP_PASSWORD：该发件 QQ 邮箱对应的 SMTP 授权码
   - NEWSPAPER_TO：日报收件邮箱地址
4. 进入仓库 Actions → Newspaper - Bilingual World News → Run workflow。默认 dry_run=true 仅生成虚构示例供检查，不发邮件。改为 dry_run=false 才会尝试抓取真实新闻并通过 SMTP 发送。
5. 查看运行日志，确认 RSS、正文抓取、翻译模型安装、邮件 SMTP 均通过。首次运行会下载离线翻译模型。

**安全提醒：不要在对话、仓库源代码、日志、Issues、PR 评论或公开文件中粘贴 SMTP 授权码。**

## 结构

- feeds.json：栏目标配额、北京时间、备用 RSS 来源、文章截选上限。
- reader.py：抓取公开可访问的新闻页面，提取正文并按段落取精选选段。
- digest.py：昨日日期过滤、日期与标题去重、跨来源选择、离线翻译和 HTML/TXT 邮件发送。
- requirements.txt：Python 包依赖。
- ../.github/workflows/newspaper.yml：23:00 UTC (= 北京次日 07:00) 定时任务。

## 维护与局限

1. GitHub 公开仓库定时任务可能因连续 60 天无仓库活动而被停用；定期检查 Actions。
2. 真实新闻的完整正文若不可读取，只会标记来源失败并寻找替代，不会凭空扩写。2200 字符上限为可阅读新闻选段，不是对商业原文的全文存储。
3. 机器翻译尤其在财报、药品名称、金融缩写方面可能出错，标题与英文保留供核对。
4. 新闻源有效性会变化。候补列表不是已逐一确认每天都可用的保证。
5. 对 07:00 分钟级时效要求很高时，需要改用更可靠的定时调度服务。

## 本地运行

python -m pip install -r newspaper/requirements.txt
python newspaper/digest.py --demo --output /tmp/newspaper-preview
python newspaper/digest.py --dry-run --output /tmp/newspaper-real-preview

模拟预览不发送邮件。真实预览需联网抓取文章和首次下载翻译模型。
