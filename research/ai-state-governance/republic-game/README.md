# 《共和国》/ Republic — AI 元首连续文字治国游戏

**游戏版本：v0.6 · 中英文自动切换 · 完全虚构 · 免费游玩**

> 本游戏根据《AI 元治理国家》研究报告提出的制度模型设计。专业内阁负责论证与执行，玩家扮演 AI 元首，监督任免、公平程序、独立审计和重大争议。欢迎任何人体验、批评剧情逻辑及提交改进。

## 直接开始

**[在线玩《共和国》](https://pyzz58.github.io/gpt-recommendations/republic-game/)** · [游戏与研究主页](https://pyzz58.github.io/gpt-recommendations/)

不需要注册、登录、API 密钥或网络新闻接口。GitHub Pages 正常部署后，以上链接可直接用浏览器打开。若要离线使用，请同时保存 [index.html](index.html) 和 [i18n-en.js](i18n-en.js) 到同一文件夹，然后双击 HTML；中文与英文均可离线运行。

## 玩法：你的一届十二日任期

- 开局从 **4 条原创虚构国际危机**中随机抽取 1 条，影响最初的国家指标。
- **12 个工作日、约 24 项裁决**：每日上午阅读国务晨报，接收专业部门呈报的事件背景、具体困难、各方意见与明确待决事项；必要时要求独立审计。
- 每项事务拥有至少三种选择；查看独立审计后，可解锁第四种替代方案，但会产生财政成本。
- 决策有**当下效果与数日后的执行结果**：早前的国内事务会重新送审，要求二次裁决，不能凭一次点击宣告完美结局。
- 国际危机依次经过 **紧急应对 → 执行偏差 → 合同/问责争议 → 长期制度改革** 四个阶段；后续阶段会反映前面做过的决定。
- 审议内容包括高级干部遴选、教育机会、饮水安全、采购反腐、住房、审计权监督、科研预算、网络安全、交通绩效。
- 民生、财政、廉洁、制度信任随决策与延迟报告变化；第 12 日生成任期摘要并保留未结案记录。
- 进度保存在玩家本机浏览器的 Local Storage；可继续本届或重新随机开局。数据不上传服务器。

**语言支持（v0.6）：** 游戏根据浏览器语言优先选择中文（zh）或英文（en），其他语言环境目前默认英文。右上角可以随时手动切换，并记住选择；切换不会重新开始当前游戏。英文剧情、决策与后续回报均已翻译，无需在线翻译服务。

**v0.5 文案调整：** 已按玩家反馈去掉案件中的重复“AI 秘书”套话。现在每份公文直接说明谁来报告、发生了什么、各部门各自主张什么、最后要元首决定什么。国际事件四阶段、国内事项与旧案回访均补充了可理解的虚构数字、机构反馈及可查询的审计证据。

**重要说明：** 事件、机构、地点与人物全部是原创虚构，结局和数值用于互动叙事，不代表真实政策的实际经济、政治或伦理效果。本游戏不是对现行国家、现实政治人物或历史游戏的复制，也不代表 AI 已具备独立治国能力。

## 欢迎参与制作

**[公开讨论 Issue #84](https://github.com/pyzz58/gpt-recommendations/issues/84)**：可以提出政策两难情节、前后因果链、如何避免“每道题都有标准答案”、审计设计和程序正义等方面的建议。

开发者可以 Fork 仓库、编辑单文件 [index.html](index.html)，提交 Pull Request。请勿复制其他游戏的原作剧情、美术或受版权保护的表达；借鉴的是“每日事务—选择—持续后果”的通用玩法。

自动测试：`node smoke-test.cjs`，已纳入 GitHub Pages 发布前校验。测试覆盖多组随机开局、12 天流程、连续国际事件、旧案复审与最终结算。

[中文研究报告](../REPORT_ZH.md) · [English report](../REPORT_EN.md)

## English quick start

**[Play Republic online](https://pyzz58.github.io/gpt-recommendations/republic-game/)**. The game detects your browser language. Chinese browsers display Chinese; English and other browsers display English by default. You can switch between **中文 / English** at any time in the upper-right corner without losing the current game.

Play twelve days as a fictional AI head of state. Read the ministers' reports, consider the disagreement, optionally request an independent audit, and decide. Earlier decisions return as later follow-ups. The game has no accounts, no ads and no translation API. For offline play, download **both** `index.html` and `i18n-en.js` into the same folder.

You can improve the story or translations by opening [Issue #84](https://github.com/pyzz58/gpt-recommendations/issues/84) or proposing a Pull Request. This is a fictional thought experiment, not evidence that AI can govern.
