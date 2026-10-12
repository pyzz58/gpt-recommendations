# 国际职业编剧与导演职责审计｜2026-10-13

## 范围与证据

对照：美国电影艺术与科学学院 Nicholl 评审维度、Sundance Collab 剧本重写教学、BBC 场景/对白格式指南、John August/Craig Mazin《Scriptnotes》创作访谈、BAFTA Tony Gilroy 编剧讲座、DGA 导演职责合同和英国国家职业服务导演岗位说明。上述材料是**不同时代、不同类型的职业指导**，不是存在一个全球唯一的「一流编剧统一认证标准」。本审计提炼可执行工艺，**不抄写、模拟具体编剧独有风格，也不暗示受其认可**。

## 对现有代码的实际审计（改前）

| 严重度 | 位置 | 现存问题 | 处理 |
| --- | --- | --- | --- |
| P0 | `screenplay_adaptation.validate_proposal` | 可判定来源映射/动作/时长/对白字段，却**无法证明场次有效、人物动机可信、潜台词自然、作者声音独特、观众有兴趣** | 新增独立 `screenplay_professional_review.py`，审稿需原文可定位短句、失败原因与返修动作，不能自我授予专家认证 |
| P0 | `agent_team.STAGES` 和 `agent_role_contracts.ROLE_INSTRUCTIONS["script_edit"]` | 前置编剧已完成，旧十阶段中剧本编辑仍负责设钩子、调整节拍、提故事重写，重叠 | **不增加 Agent / 不破坏任务 DAG**；剧本交接标记触发 `script_edit` 的连续性审核岗位语义；剧情改写归还前置编剧 |
| P0 | 旧 `build_editor_request` | 强迫不同文体按人物欲望/冲突/结局改编，历史哲学随笔易产生虚构对白或人工戏剧冲突 | `fiction/documentary/essay/hybrid` 分型，纪实/论述作品优先真实、论证推进和观众认知变化 |
| P1 | `screenplay_director_handoff` | 总导演收到完整剧本，但既有后续岗位没有显示前置编剧的边界，后续可能二次默改 | 新增 **planning-only** 的 `screenplay_handoff_mode`，各岗位收到「只能提编剧返修，不可自行修改权威故事」的指令 |
| P1 | `screenplay_adaptation.render_fountain` | Fountain 场次可以读，但每 beat 固定「动作→旁白→对白」，难表达更复杂的说话与反应交替 | **仍待解决**：需支持剧本场次内事件顺序，而不是只能排序动作块与台词块 |
| P1 | `screenplay_fulltext_intake` → `compile_reviewable_shot_plan` | 1秒 virtual slots / 源单位与重编译拍摄 shot 同名，虽声明占位，容易在创作上混淆 | 本轮再强调来源单位非镜头；**仍待设计**独立 scene/beat 到导演拍摄镜头的中间层 |
| P1 | `screenplay_adaptation` 的 `MAX_SCENES=32, MAX_BEATS=100, runtime<=300s` | 与长篇电影剧本不兼容，不能伪称可改完整电影 | 明确承认为**短视频原型**；长片须分章/分集和更大契约设计 |
| P1 | 事实/论据 | 事实核查未完整引入源文语境验证；原稿没有引用时不应自行加历史日期、文献或片尾卡 | 保留来源完整性人工审查。原文有材料才用；无就不造证据，不自动加尾卡 |
| P2 | 单一编剧 Agent | 仅改编一遍，没有有效的剧情诊断→重写→再审循环 | 新增独立审稿请求/校验；实际文字模型执行与多轮文学审稿仍待私有运行测试 |

## 第一层：哪些工作属于编剧？

编剧决定作品**讲什么、为什么、人物/观点怎么推进和落脚**，写成真正可以让导演读懂戏的完整剧本；包括场次内容、故事和信息因果、演员可感知的动作、自然对白/旁白、人物或思想的变化、结尾回报。

BBC 指南明确强调动作描写要服务于能在画面中看到的事情。Scriptnotes 对行动场景、叙事性转场的讨论说明：编剧可以提示重要的影像意图，让读者在阅读时看到电影。**不应制定硬性禁令「编剧不得写任何镜头和转场」**，否则会损害职业编剧的正常表达。

### 不能跳过的专业审稿

1. 原创/非模板：这真的是该作者和该主题的语言吗？
2. 因果与进程：删掉这一场会破坏什么？观众知道了什么新的事？
3. 角色/观念：fiction 看人物欲望、行动、代价与潜台词；documentary/essay 看事实和问题层层递进，不按虚构人物数量给分。
4. 声画：能用行为传达的是否仍被台词重复讲述？能否排除只有演员「抽象表情」的空描述？
5. 事实：新史实/新数字/虚构名人对白要明示，不能藏进看似纪录片的画面和旁白。
6. 自主精修：先修最根本结构和因果，再修对白和节奏；不能以「增加张力」等空评语代替具体返修。

**新结构化审稿合同只校验反馈确实指向剧本原句与明确改稿动作，不判定反馈真假，也不因评分漂亮就认定一流。**

## 第二层：哪些工作属于导演？

导演是已完成剧本的**视听阐释者和整个专业团队的创作整合者**：对剧本和受众需求理解后，决定影像语法、空间轴线、演员排练与行为调度、摄影构图、风格、实际镜头组织和后期整体节奏。DGA 的职业职责包括剧本执行分析、机位构图、演员排演、对白执导和整体完成；英国政府职业说明也承认导演参与与编剧共同开发剧本。职业分工重叠是正常的**创意协作**，不代表重复运行同一任务两次。

**总导演有资格指出剧本的问题，也可能在制作中需要调整内容；但系统应要求提交 `script_revision_request`，返回编剧改稿/作者审核，而非让导演与下游多次自作主张修改新剧本。** 此为系统权限契约，不是声称现实电影组绝无导演改稿。

### 岗位所有权

| 工作 | 主责 | 可协作 |
| --- | --- | --- |
| 原稿深度阅读、题材选型、戏剧/论证结构 | 前置职业编剧 | 总导演提出主题与目标，必要时协商 |
| 小说改编、新增/删改剧情、对白和旁白 | 前置编剧 | 总导演可提书面修改原因，不直接覆写 |
| 必要的戏剧行为、视觉化动作意图 | 编剧 | 表演导演与摄影导演补充可执行实现 |
| 主题的最终视听表达、受众情绪与电影形式 | 总导演 | 编剧、摄影、配音、剪辑协商 |
| 机位、焦距、景别、灯光与镜头覆盖 | 摄影/美术导演（总导演统筹） | 动作导演与演员 |
| 演员排练、blocking、微动作节拍 | 动作/表演导演（总导演统筹） | 编剧提供角色动机 |
| 原对白/旁白的声线、口型、字幕时间码 | 声音导演 | 编剧确认台词文本 |
| 镜头转换、视听节奏、动画/合成 | 剪辑导演 | 总导演终审 |
| 模型安全技术约束、制作候选提示词 | AI 技术导演 | 摄影/动作/剪辑 |
| 版本一致性、原剧本是否被篡改 | 既有 `script_edit`（在已完成编剧分支）、QA | 总导演向编剧提出返修单 |

## 第三层：公开图灵历史思想短片的案例复核

本轮根据此前公开对话中的约 106 秒/8 场剧本示范审核（**人工文本判断，不是实际视频反馈**）：

- 适合设定为 `essay` 或 `documentary`，不应为「没有英雄式人物行动和三幕强反转」扣分。
- 原稿真正的命题是「从机械计算走向追问何为智能」。有基础首尾呼应，结尾三个提问也保留了，但故事推进容易退化为「牛顿→爱因斯坦→旧机房→图灵论文」的背景知识罗列；观众认知的**每一场变化**还不够明确。
- 多处场景采用翻书、闪烁光标、旧纸张和空白记录室等通用历史科技包装，**视觉故事性和作者辨识度不足**。独立编剧修订应把可见动作与观念冲突相连，而不是增加更多「电影感」形容词。
- 旧示范引入了明确的 ENIAC/1946 和图灵/1950 文献等原文未逐项列出的新史实。这些是**额外编辑性事实候选**，不能变成「原稿已提供的证据」。应明确保留为可选提案或不增加，严格遵守用户要求：原文没有材料/论据不强行补充。
- 审稿标记：`needs_human_judgment` 且建议 `revise`；这属于专业内容审阅意见而非程序对艺术质量的实测判定。

## 本轮改动及其可验证性

- `skills/07-professional-screenwriter.md` 为内部**原创蒸馏后的角色 skill**，内含题材分流、职业工序、反向阅读与职责矩阵，保留核查链接。
- `screenplay_adaptation.build_editor_request` 明确写作者原文、视听行为、允许的创作空间及非虚构的事实边界。
- `screenplay_professional_review.py` 生成独立审稿的**未发送**请求，覆盖七项创作质量检查，拒绝没有剧本引文支撑的空洞褒奖、遗漏返修、虚构权威和不一致的结论。支持 `build_revision_request`：将定位问题返回编剧定点重写，保护未受影响场次，重新接受来源和作者审核。
- `screenplay_fulltext_intake.reviewed_director_handoff` 是**选择启用的严格审稿交接**：有明确待修问题就拒绝作为完成剧本交导演；没有报告问题仅表示可交给作者审阅，**不等于编剧艺术水准认证**。旧入口保持兼容。
- `screenplay_fulltext_intake.editor_request` 现在明确支持 fiction / documentary / essay / hybrid 四类；历史科普散文不会强制假造人物冲突。
- `screenplay_director_handoff.prepare_handoff` 在编剧交接底稿上增加只读的剧本权威版本标记，`agent_role_contracts.build_role_messages` 根据标记改变现有导演/剧本编辑及下游岗位的权限声明，**不增 Agent，不改 10 阶段 DAG**。
- 单元测试只能证明合同有效，**不能证明编辑意见真能识别逻辑漏洞、语言有大师质感或导演模型真会遵守**；后续实际运行需要真人盲评与逐稿返修、以及授权的私有模型文本调用。

## 研究资料（可核实）

- Academy Nicholl Judging Criteria: https://www.oscars.org/nicholl/about
- Academy Nicholl Rubric PDF: https://www.oscars.org/sites/oscars/files/2025-05/Nicholl_Scoring_Rubric_0.pdf
- Sundance Screenwriting / Rewriting: https://collab.sundance.org/catalog/Screenwriting-Rewriting-Your-Feature
- BBC Screenplay Format: https://downloads.bbc.co.uk/writersroom/scripts/screenplay.pdf
- Scriptnotes John August/Craig Mazin #403: https://johnaugust.com/2019/scriptnotes-ep-403-how-to-write-a-movie-transcript
- Scriptnotes #463: https://johnaugust.com/2020/scriptnotes-episode-463-writing-action-transcript
- Scriptnotes #532: https://johnaugust.com/2022/scriptnotes-episode-532-mistakes-of-yes
- BAFTA Tony Gilroy lecture: https://www.bafta.org/stories/tony-gilroy-screenwriters-lecture/
- DGA Director Responsibilities: https://www.dga.org/-/media/EBF41E3AC63E44CFB1E4FAABE1D7357D.pdf
- UK director role: https://nationalcareers.service.gov.uk/job-profiles/tv-or-film-director
- Fountain screenplay syntax: https://fountain.io/syntax/

**行业资料不等于唯一正确的电影美学，审稿结果必须兼顾主题、文体和作者意图。**
