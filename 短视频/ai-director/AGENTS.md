## 开发优先级：GitHub 成熟方案优先（2026-10-11 起，适用于所有修复与新增功能）

本项目每次遇到缺陷、质量不足、功能扩展、模型兼容、安全/性能/预演/连续性问题，**在编写新实现前优先研究 GitHub 已有成熟项目**，不是先造轮子。遵循下面的实际执行顺序：

1. **明确问题与验收标准**：先说明目前失败证据、需要什么能力；确认现有实现是否已经足够。不要因为第三方项目知名就迁移架构。
2. **GitHub 搜索与比选**：尽可能找 2–3 个真正相关的上游仓库，核实 README、源代码/接口、活跃度（提交、issue、release）、测试、许可证、依赖、Mac/Python 版本、离线运行和中国网络条件；记录可核验仓库链接。无法联网时标记“未完成调研”，不能假称已查。
3. **判定方案**（优先级从高到低）：①合法直接复用稳定接口/库；②只借鉴其设计与数据结构、自己写很薄的适配层；③当现有成熟方案明显不匹配时才自行开发，并说明“不匹配在哪里”。警惕新发布的研究原型、重依赖和需要高性能 GPU 的仓库，不把“新颖”说成“成熟”。
4. **先做最小离线实验**：不改变用户已有 Codex/DeepSeek 全局配置，不联网上传私有故事文本；不擅自安装、克隆大工程、下载模型权重、使用付费接口、生产视频或发布。引入新依赖前检查许可证和安全风险；若第三方许可证要求保留 NOTICE/COPYRIGHT，必须保留。
5. **保存决策账本**：每次实际采纳前记录需求、候选仓库、适配与许可证、是否采用、理由、测试结果和回滚方法。不得把“搜到项目”和“已完成集成”混为一谈。参阅 `GITHUB_REUSE_POLICY.md`。

对现有 `continuity_audit.py`，优先研究 CineCrew/FilmDSL、transitions、Pydantic/jsonschema 的结构化资产状态方案，然后逐步增强；已有零依赖规则检查器保持为可回退基线，不贸然引入庞大框架。

# Codex 任务说明：AI Short Video Director v0.1

## v0.3 · 中国回国可携带与本地模型解耦（优先级最高）

1. **所有导演生产的根目录必须可以整体复制到移动硬盘独立运行**。ChatGPT/GitHub是在线辅助而非运行前提；网络不可用时prepare/review/backup仍要可用。
2. 请阅读 [v0.3 说明](README_V03.md)、[本地启动器](local_director.py)及 `skills/01-series.md` 至 `skills/05-source-credits.md`。
3. 继续使用现有Codex + DeepSeek完成创意，或者在用户明确批准模型API费用后执行本地分阶段 `run`，不得擅自修改模型全局配置。
4. 每篇长文先建 series.json 确定1–3集故事线与全局人物Bible，再逐集plan.json → direction_v02.json → 本地预演；人物形象描述必须跨集一致。真实参考图没有制作前状态为 `not_created`。
5. 人物、场景、道具参考图状态必须如实记录；未来国产AI视频接口可替换，不为当前项目强制安装。
6. 片尾引用卡保持单张5秒静态图、2–3个最重要的真实来源，正文与完整DOI保存在description.md；不得编造来源。
7. 不要上传用户的私有文案到任何公有镜像或公开GitHub；所有外部分享、费用、生成和发布先请求明确授权。


## 片尾研究来源卡 · 最新固定规则（优先级高）

对科学、医学、心理、财经等需要研究引用的作品，**只有片尾研究来源卡需要遵循以下时长设计，不要压缩正文的必要解释**：

1. 每集片尾只能有 **1 张静态 9:16 来源图片卡**，固定 **5 秒**；不要做多张来源翻页，也不需要专门再念一段来源旁白。
2. 优先选 **2–3 条最直接支撑本集核心观点** 的研究。卡片中只放作者（或首作者）+发表年份+期刊名短写+研究类型，必须在手机上可读，保留安全区。
3. **完整文献、DOI、研究限制，以及其他未登上片尾卡的来源** 全部写进每集 `description.md` 或发布时的简介/置顶评论，不删失证据账本，不把精简片尾当作假装只引用这3项。
4. 如研究证据尚未核查，卡片不得声称“权威证实”“全部验证”；不能把相关性描述成因果。片尾仅负责溯源，不替代事实审核。
5. 卡片属于后期图文素材（`text_card` / static image），不要让 AI 视频生成模型直接绘制文字、期刊封面或假论文截图。
6. 对有 `purpose=sources` 镜头的项目，运行 v0.2 校验器验证：单卡、末镜、5秒、2–3来源、无旁白。


## v0.2 专业导演增强（优先适用）

凡用户认为 v0.1 分镜/提示词缺少细节，**优先阅读 `V02_GUIDE.md` 与 `director_v2.py`**，保留 v0.1 完整基础数据。

- 新文章先得到 `plan.json`，再使用 `director_v2.py scaffold --base <path> --out <path>` 生成 `direction_v02.json` 草稿。`scaffold` 并不会自动做导演创作。
- 使用 `director_v2.py task --base <path> --direction <path> --out <path>` 生成工作说明，由当前 Codex + DeepSeek 逐镜头补齐专业导演决定。
- 逐秒 beat 覆盖本镜头完整时长；必须描述画面可观察的变化、演员走位、镜头移动的触发时机与合理结束状态。
- 对数据/医学镜头必须先设计动态图形后期工作单，禁止交给视频模型生成准确数字或中文。
- `validate` 通过才能 `compile` 与 `preview`；不可改为无需验证直接提交 Prompt。
- `qa.human_approved` 必须保持 false，除非用户明确已审片。即使技术校验通过仍保留医学来源待审与模型实际效果待测。
- 不改变用户全局 DeepSeek 模型选择；不自行付费生成、采购素材或发布。


你在本目录工作的目标是将用户输入的中文文案变成**可以审核、可以逐镜头重做**的前期生产包，而不是直接生成视频。用户当前使用 Codex + DeepSeek；不得擅自替换其模型或修改全局 Codex 配置。

## 工作入口

1. 优先阅读 `README.md`、`director.py` 内的 `SYSTEM_GUIDANCE` 和 `examples/quit-smoking/plan.json`，遵守当前 JSON 结构。
2. 当用户给一篇新文章，保存为 `jobs/<slug>/source.md`，以 `python3 director.py prepare --input jobs/<slug>/source.md --out jobs/<slug>` 生成导演任务说明。
3. 使用当前 Agent 的模型进行创造性写作：内容编辑（删减并记录）→事实断言清单→叙事起伏→镜头语言→完整导演计划；输出 `jobs/<slug>/plan.json`。
4. `python3 director.py validate --plan jobs/<slug>/plan.json`。修正结构错误；**医学/法律/投资内容的待核验警告不能当成小问题屏蔽**。
5. `python3 director.py compile --plan jobs/<slug>/plan.json --out jobs/<slug>/prompts.json`。
6. `python3 director.py preview --plan jobs/<slug>/plan.json --out jobs/<slug>/preview.html`，把 HTML 预演交用户审核。
7. 任何付费调用、真实视频/配音生成或发布，必须先报告供应商、模型、预计成本，并得到用户明确授权。

## 不可越过的边界

- 不把 OR 当 RR，更不要把“超额死亡风险减少90%”变成“所有人的死亡概率减少90%”。
- 没有原始文献或权威来源，不把 `claims.status` 改成 `verified`；严禁虚构 evidence_url。
- 不把预演的文字占位镜头说成真实视频。
- 对所有精确字幕、百分比、图表数字，只由后期叠加，不让视频生成模型直接画中文。
- 单镜头动作设计至少包含 start/action/micro_action/reaction/end；涉及同一个人物必须使用固定 character ID。
- 默认不开任何付费 API 和自动发布行为。
- 先测试，再提交。不要覆盖已有用户工作；不要 force push。
## P0 修复后约束（先于创意执行）

- 复审不得覆盖 `description.md`、`prompts.json`、人工审批记录；程序另写 `*.generated.*` 文件。
- `--resume` 不能重建已存在且由用户确认的 `character_bible.json` / `status.json`。跨集人物对照包括 `description`、`wardrobe`、`identity_anchor` 以及 `visual_bible` 各个系列字段。
- 有研究卡的单集必须生成 `plan.references` 书目数组并绑定每个卡片 claim ID。参考 `skills/05-source-credits.md`；不能用模型捏造 DOI。
- 现阶段真实 DeepSeek API 运行尚未经用户明确费用审批；不得发起任何付费调用，也不要声称已端到端确认。保持 GitHub 为源码和测试仓库，用户明确要求不打包下载至最终验收。

## v0.3 费用与自动修复门禁

- 独立DeepSeek API调用必须同时具备用户明确授权的 `--approve-model-cost` 与 `--max-cost-cny`；未授权具体人民币最高金额，不得联网调用。Codex现有连接不得擅自更换或重新收费。
- 每次请求（含JSON重试和结构修复）都进入 `api_usage.generated.json` 账本，金额保守预留；默认不重试；网络超时、HTTP 5xx、未知扣费状态绝不自动重发。
- 只有模型**新生成的草稿**可以被结构校验后自动修复，绝不能重写用户已手工修改的 plan、人物Bible、字幕和研究说明；失败或金额超限时保留草稿供人工恢复。
- `cost-status` 仅读取本地预留估计；不代表官方账单。不得上传 API Key、原文或用户项目到公开仓库。

## 连续性审查与修订流程（新增）

- 在生成 direction_v02.json 前，必须先用本地 `python3 local_director.py audit --plan <plan.json>` 审查基础计划，并阅读 `continuity_repair.generated.md`。
- 审查中 blocker 未解决时不得继续调用新的付费导演方向模型；review 类问题由人审与 Codex 修改稿核对，不可假设自动通过。
- 修改用户的真实 plan 时，先建立 `plan.proposed.json` 候选；保留原始 JSON、series、原文、手改内容、既有费用账本。不得自行增加 `--max-calls` 或隐式重试。
- 道具位置必须通过可拍动作过渡：拿起、携带、放下；对复杂道具可使用 `continuity_state` 机器可验证字段。请阅读 `CONTINUITY_QA.md`。
- 费用与版权检查独立于连续性；不能因为通过代码测试就宣称视频已生成或获得许可。
