# AI 视频导演｜质量优化问题清单

> 本文件根据 QUALITY_ISSUES.json 自动生成。勿直接修改状态。
> QO 管理专业创作及 AI 视频质量；现有 AUD-xxx 技术安全问题仍需独立跟踪。

## 总览

- 登记 38 项；编剧 11 项，总导演 17 项，其它部门 10 项。
- 全部验收完成 0 项；没有真实独立验证不能自称达到一流水准。
- 现阶段只修编剧及总导演；其它部门保持后续审计状态。

| 编号 | 岗位 | 优先级 | 状态 | 问题 |
| --- | --- | --- | --- | --- |
| QO-W01 | screenwriter | P0 | in_progress | 全稿理解与核心思想覆盖 |
| QO-W02 | screenwriter | P0 | partially_addressed | 不同文体专用改编工序 |
| QO-W03 | screenwriter | P0 | confirmed_open | 故事/论证推进、原创声音与场景功能 |
| QO-W04 | screenwriter | P0 | confirmed_open | 场次内动作/旁白/对白先后关系 |
| QO-W05 | screenwriter | P0 | partially_addressed | 职业级对白、潜台词与说话人辨识 |
| QO-W06 | screenwriter | P0 | partially_addressed | 独立审稿、定点返修和版本冻结 |
| QO-W07 | screenwriter | P0 | partially_addressed | 真实论据、可选片尾与新增事实 |
| QO-W08 | screenwriter | P0 | confirmed_open | 总时长/旁白/留白与片段时间分层 |
| QO-W09 | screenwriter | P0 | partially_addressed | 作者确认/版本不可篡改及编剧导演交接 |
| QO-W10 | screenwriter | P1 | confirmed_open | AI短视频编剧独有交付书 |
| QO-W11 | screenwriter | P0 | in_progress | 编剧场次详述到导演不用猜剧情 |
| QO-D01 | director | P0 | partially_addressed | 导演以完成剧本为唯一剧情权威 |
| QO-D02 | director | P0 | confirmed_open | 场次与分镜解耦：一场可多镜，一镜可多节拍 |
| QO-D03 | director | P0 | in_progress | 导演视听母题、情绪弧线与视觉叙事 |
| QO-D04 | director | P0 | partially_addressed | 模型能力适配、片段时长与路由决策 |
| QO-D05 | director | P0 | partially_addressed | 演员/服装/道具/场景跨镜一致性 |
| QO-D06 | director | P0 | confirmed_open | 多动作可拍性与模型失败降级 |
| QO-D07 | director | P0 | partially_addressed | 导演级镜头语言与视觉连续性 |
| QO-D08 | director | P1 | partially_addressed | 导演与音效/台词/字幕精确对齐 |
| QO-D09 | director | P1 | confirmed_open | 剪辑节奏、过渡桥与镜头版本选择 |
| QO-D10 | director | P0 | confirmed_open | 专业导演审片标准：不是字段全就是好片 |
| QO-D11 | director | P0 | blocked_external | 真实双镜生成、跨镜验收与风险边界 |
| QO-D12 | director | P1 | confirmed_open | 导演/编剧修订权限冲突与版本谱系 |
| QO-D13 | director | P0 | in_progress | 总导演自主分集与单集90秒绝对上限 |
| QO-D14 | director | P0 | in_progress | 总导演主动创意剪辑与重大压缩权 |
| QO-D15 | director | P0 | in_progress | 总导演详尽指挥与协调所有专业部门 |
| QO-D16 | director | P0 | in_progress | 导演审核部门真实交付与基于观众体验的精准跨岗返工 |
| QO-D17 | director | P0 | in_progress | 世界级导演的可迁移艺术判断与周星驰荒诞喜剧的题材适配 |
| QO-F01 | acting | P1 | audit_pending | 演员表演与动作调度专业审计 |
| QO-F02 | cinematography_art | P1 | audit_pending | 摄影/灯光/美术世界观专业审计 |
| QO-F03 | sound_voice | P1 | audit_pending | 配音/对白/拟音/音乐专业审计 |
| QO-F04 | editing_animation | P1 | audit_pending | 剪辑/动效/信息图专业审计 |
| QO-F05 | ai_technical | P0 | audit_pending | AI视频技术导演适配与提示词编译审计 |
| QO-F06 | continuity_qa | P0 | audit_pending | 独立场记/事实/版权与质量门禁审计 |
| QO-F07 | api_privacy_cost | P0 | audit_pending | 真实账号、素材、资费和私有存储生产审计 |
| QO-F08 | media_qc | P0 | audit_pending | 真实视频审片、版本优选与局部返工 |
| QO-F09 | postdelivery | P1 | audit_pending | 最终合成、字幕/无障碍与可选资料尾页 |
| QO-F10 | product_workflow | P1 | audit_pending | 整体制作协调/进度/异常/返工成本的专业审计 |

## 每个问题的根因、解法、验收与证据

### QO-W01 · 全稿理解与核心思想覆盖

- 状态：in_progress；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_fulltext_intake.prepare_fulltext/editor_request; screenplay_adaptation.build_editor_request/validate_proposal; screenplay_professional_review.validate_review; screenplay_development.py
- 问题：全文字符/来源ID完整不代表专业改编忠于作品内核；当前缺完整原稿创作诊断、多个真正不同的影像改编take、取舍说明与短treatment，可能既误丢原文核心又压制正当创造性删改
- 根因：设计顺序本末倒置：直接从source_ids+JSON字段生成剧本，缺先由编剧理解作者为何写、什么适合被拍、什么可大胆重新组织的专业创作阶段；盲评/剧情质量不能由hash或字段数证明
- 方案：先依据原始职业一手资料形成adaptation brief（核心命题/作者声音/人物与信息关系/事实硬边界/艺术可改项）；产生2–3个差异化film takes及取舍、成本和新事实风险对照；独立编辑审查确定treatment后再写剧本；原稿与剧本分别盲读比对创作成效与意义是否失真；来源映射仅作防静默遗漏的底层QA，不应最大化保留率
- 完成验收：有公开合成小说/纪录/观点各一组加无标题长文；两种差异明显的take+选中理由+treatment+完整剧本；独立审稿能奖励正当有创意的压缩重排又发现错改关键主题，记录盲评样本与反例；作者保护事实不可静默改写；无专业真人验证不得complete
- AI 视频适配：编剧写可见可听的影像等价表达，但单个AI生成clip的时长不反向约束小说/议论文内核；导演自行设计分镜与剪辑，技术岗位编译clip；原文无证据不强造新资料
- 依赖：无
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/19
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/26；回归 tests/test_screenplay_development.py (11 public synthetic cases): creative diagnosis, two takes, editor comparison, treatment, adaptation alignment, director routing, stale-data rejection；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed → 2026-10-13:partially_addressed → 2026-10-13:in_progress → 2026-10-13:in_progress

### QO-W02 · 不同文体专用改编工序

- 状态：partially_addressed；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_fulltext_intake.editor_request; skills/07-professional-screenwriter.md
- 问题：fiction、documentary、essay、hybrid 已有提示，但真实模型仍可能硬套人物冲突与三幕式
- 根因：类型识别只靠用户/调用参数，缺结构性适配质量验证
- 方案：建立类型选择理由及可覆核模式；每型独立审稿量表与非虚构禁杜撰门禁；比较同文案错误类型和正确类型的成稿
- 完成验收：至少小说、访谈、科学史、论说文各2例；无演员历史随笔不因没有主人公扣分；反例能发现编造历史人物对白
- AI 视频适配：短视频可为纯旁白、动态图解或纪录叙事，不能强制演员镜头
- 依赖：QO-W01
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-W03 · 故事/论证推进、原创声音与场景功能

- 状态：confirmed_open；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_professional_review.py; screenplay_adaptation.py
- 问题：目前自动审核看内容是否填写和引文是否匹配，无法证明剧本不模板化、每场必要、有思想/情绪递进；用户本轮真实阅读反馈：当前图灵剧本尚可，但思想与情绪触及心灵的余韵偏弱
- 根因：缺职业编剧发展性编辑的具象证据与反例评估
- 方案：定义场景进入前/离开后变化、不可替代性、张力/认知跃迁以及差异化语言审核；对空镜头、套话与独特场面样本盲评；补充不煽情的意义/情绪回声审阅：具体人类处境、可感选择、独到反差、有意留白，拒绝为分数加空洞抒情
- 完成验收：公开样稿成对A/B盲评；至少2种文体、至少2名独立评审记录理由；重大退步必须返修，不能靠数字评分自动打勾
- AI 视频适配：每段必须有画面或叙事功能，避免科普一段话一张无差别图卡
- 依赖：QO-W01, QO-W02
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open → 2026-10-13:confirmed_open → 2026-10-13:confirmed_open

### QO-W04 · 场次内动作/旁白/对白先后关系

- 状态：confirmed_open；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_adaptation.render_fountain; screenplay_adaptation.validate_proposal
- 问题：每节拍固定先动作后整段旁白再对白，无法表达打断、交叉发言、行动反应，影响可演性
- 根因：当前 schema 将 action/dialogue/voiceover 存为平行块，没有事件顺序
- 方案：兼容旧稿同时设计 ordered screenplay events（action/dialogue/VO/silence），按原顺序输出 Fountain，逐个事件保留来源及审稿记录
- 完成验收：多轮双人对话与无对白反应的公开样例可往返重建；逐事件顺序不丢，旧 v1 样稿不回归
- AI 视频适配：事件顺序是剧本，不等于强制一镜完成；长互动需拆成多次可生成片段
- 依赖：QO-W02
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-W05 · 职业级对白、潜台词与说话人辨识

- 状态：partially_addressed；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_professional_review.py; screenplay_director_handoff._cast
- 问题：台词精确映射已有，但角色声线、潜台词、行动回应及语言自然度仅由文字审稿提案判断
- 根因：缺针对对话的场景级口头试读与声画避免重复测试
- 方案：建立朗读式审阅、说话人匿名辨别、重复解释、人物目标和沉默行动评分；输出针对场次的改写说明
- 完成验收：2人对话公开样例逐句角色可追、拟配音时长合理；盲听/盲读发现故意同质化或解释性对白
- AI 视频适配：长对白优先分段/画外配音，不依赖生成模型一次完成完美口型
- 依赖：QO-W04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-W06 · 独立审稿、定点返修和版本冻结

- 状态：partially_addressed；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_professional_review.py; screenplay_fulltext_intake.reviewed_director_handoff
- 问题：独立审稿及返修请求已具形式，但未对真实编辑模型做两三轮质量对照，审稿者也未认证
- 根因：结构测试≠审稿质量；模型可以用同样的口吻给自己背书
- 方案：评审与改稿分离；至少首稿/专业审核/定点二稿/再审；逐项问题绑定场次、原稿及更改原因；建立客观失败与盲评证据
- 完成验收：缺陷样例能被审稿识别并在返修后确实降低；二稿优于首稿的盲评记录和问题关闭证据可核验
- AI 视频适配：按局部场次返工，不对整部片无益重生成视频
- 依赖：QO-W03, QO-W04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-W07 · 真实论据、可选片尾与新增事实

- 状态：partially_addressed；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：closing_evidence_card.py; screenplay_fulltext_intake.py; skills/05-source-credits.md
- 问题：已禁止没有材料时强加文献卡，但新增史实与作者原文来源的区分仍需实际剧本审查
- 根因：原稿观点、编辑新增事实、外部证据被不同链路混称为同一权威
- 方案：分别记录原稿引用/事实陈述/编剧新增事实/艺术化演绎；新增事实只作待审提案；原稿没有资料则不添加证据页；需要时仅最后单页1–2秒
- 完成验收：分别对无来源虚构、科普无引用、有真实来源、混合推理四组测试；无材料绝不出现参考书目，引用未核实不标已验证
- AI 视频适配：精准文字和文献页应在后期合成，不能让视频模型生成准确长文字
- 依赖：QO-W01
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-W08 · 总时长/旁白/留白与片段时间分层

- 状态：confirmed_open；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_adaptation.validate_proposal; screenplay_director_handoff._pacing
- 问题：剧本时长依赖预估，单节拍<=30秒、总长<=300秒，仍混淆场次、段落与供应商生成片段
- 根因：缺独立 VO 声速、角色停顿、声音桥与可拆镜策略
- 方案：编剧估算声画节奏与完整短片时长；导演负责拆镜与合成；按真实配音波形回写拍摄时间线，禁把一段30秒剧情硬塞单个生成镜头
- 完成验收：沉默/快慢双场景时长人工审看；可导出不同短视频时长版本仍保留内容；实际配音后时码偏差可记录、返修
- AI 视频适配：编剧节拍可跨多个AI片段，具体片段时长取决于所选模型能力表
- 依赖：QO-W04, QO-D04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-W09 · 作者确认/版本不可篡改及编剧导演交接

- 状态：partially_addressed；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_director_handoff.py; agent_role_contracts.py
- 问题：脚本已有审稿字段与摘要，但 JSON 决定并不是可信身份授权；旧脚本变量与新版本容易混用
- 根因：没有实际私有作者确认动作/角色身份与电子版审稿记录
- 方案：构建私有端审稿确认，绑定原稿、proposal、Fountain 及来源/内容摘要；每次改稿撤销先前决定；总导演拿到完整剧本并可退回编剧
- 完成验收：未审/拒绝/旧版本/换人提交都无法伪装通过；导演看到的剧本与审稿版本逐字一致
- AI 视频适配：短片多段制作仍保留唯一权威剧本版本，局部修改触发影响范围重审
- 依赖：QO-W06
- 历史问题：https://github.com/pyzz58/gpt-recommendations/pull/18
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-W10 · AI短视频编剧独有交付书

- 状态：confirmed_open；优先级：P1；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_adaptation.render_fountain; screenplay_fulltext_intake.editor_request
- 问题：Fountain 有故事动作，但没有明确演员与画外比例、需要的视觉证据、可选后期图文、模型不可生成的核心元素
- 根因：传统剧本文本尚不能充分预警 AI 制作风险
- 方案：增加短片适配附页：声音形态、必须可见的证据/动作、非生成素材需求、敏感文字、候选拆段提示与导演选择权，剧本正文不写焦距和提示词
- 完成验收：总导演收到剧本无需补写剧情即可设计可拍片段；短片制作附页只写意图/约束，不冒充镜头方案
- AI 视频适配：允许无真人/混合AI+静态后期+音效的低成本叙事方式
- 依赖：QO-W04, QO-D04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-W11 · 编剧场次详述到导演不用猜剧情

- 状态：in_progress；优先级：P0；阶段：now_screenwriter；负责人：screenwriter
- 发现位置：screenplay_adaptation.build_editor_request; screenplay_development.screenplay_request; screenplay_series_delivery.dossier_request
- 问题：编剧过去可能只交简短场次摘要和概括动作，导演不得不反向推测具体发生的事件、动机、情绪/认知变化与对白/旁白含义
- 根因：编剧入口缺逐场逐节拍导演可读详情合同；把详述错误等同写机位或增加字数
- 方案：编剧必须交付完整剧本和绑定版本的逐场/逐节拍详细说明：环境/时空、角色初态、行动与反应、因果动机、道具连续、具体对白/旁白/沉默、潜台词、情绪或思想转折、前后衔接；真正叙事不由导演补写，机位仍归导演
- 完成验收：公开多场剧情/论述样例每场每节拍不缺说明、错版本和遗漏被拒；独立导演阅读无需补剧情即可做视听方案；不靠字数冒充质量
- AI 视频适配：整部剧本可长于90秒，编剧说明不应被clip时长限制；导演后续单集90秒规划
- 依赖：无
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/28；回归 tests/test_screenplay_series_delivery.py — 10min fulltext intake, detailed beat coverage, arbitrary 7/10-episode split, <=90s incl extras, rejects loss/reorder/tampering；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:in_progress → 2026-10-13:in_progress

### QO-D01 · 导演以完成剧本为唯一剧情权威

- 状态：partially_addressed；优先级：P0；阶段：now_director；负责人：director
- 发现位置：screenplay_director_handoff.director_request; agent_role_contracts.build_role_messages
- 问题：已由角色提示禁止总导演和旧 script_edit 重写剧情，但模型执行尚无验证
- 根因：依赖提示约束，未有输出差异强约束和真实模型反例
- 方案：核对总导演视听阐释而非改写人物/情节/台词；编剧返修单由编剧回改；字段/文字差异跨版本审计
- 完成验收：故意诱导导演改剧情/人物对白的公开测试被阻断，返修单返回编剧；不阻断导演合理提供视听建议
- AI 视频适配：短片导演可以决定剪辑与视听结构，不得暗改故事内容
- 依赖：QO-W09
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-D02 · 场次与分镜解耦：一场可多镜，一镜可多节拍

- 状态：confirmed_open；优先级：P0；阶段：now_director；负责人：director
- 发现位置：screenplay_adaptation.compile_reviewable_shot_plan; director_v2.py
- 问题：现有编剧节拍编译为同数 text_card 占位；总导演受 shot_id 不增不减约束，缺自由选择覆盖镜头的通路
- 根因：使用原稿来源slot当成物理镜头且十岗位锁镜头数
- 方案：创建 scene/beat/coverage shot 三层，导演拆镜/合镜/插入/反打/空镜，结构调整有来源和剪辑锁版本
- 完成验收：公开对话场：1场->多镜；蒙太奇场：多事件->多镜；重排后来源/台词/时长不丢且所有专业位置重绑定
- AI 视频适配：不同视频生成工具可单镜、多镜头或插帧；不能按原文句子数限制镜头数
- 依赖：QO-D01
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/19
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open → 2026-10-13:confirmed_open

### QO-D03 · 导演视听母题、情绪弧线与视觉叙事

- 状态：in_progress；优先级：P0；阶段：now_director；负责人：director
- 发现位置：agent_role_contracts director_brief/director_lock; director_workbook.py
- 问题：规范强调填完情绪/摄影字段，但多场图灵示范仍有翻书光标等通用意象，无法证明每镜有不可替代的故事功能
- 根因：缺影像叙事的盲评和主动比较备选构想
- 方案：建立导演 treatment：核心视听母题、场景对照关系、开场/收束视觉呼应、动作触发镜头、声画冲突；给出被否决方案与原因；已新增 director_visual_language：要求逐镜编写观众认知变化、画面事件、摄影静动和声音/沉默的具体理由、错位剪切的代价、AI失败时如何保留意图，并注入现有全部部门模型请求；要独立观众实测才算质量达标
- 完成验收：盲评能将空泛镜头与主题驱动镜头区分；每镜存在理由可以被回溯；观众不依赖旁白也能理解至少部分情绪/事实变化
- AI 视频适配：高质量不等于强制复杂动作；在单片可生成前提下优先视觉叙事
- 依赖：QO-D02
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/31；回归 tests/test_director_audiovisual_delivery.py — visual and sound causal reasoning, distinct shot decisions, cross-shot boundary, version binding and real role-prompt injection；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open → 2026-10-13:confirmed_open → 2026-10-13:in_progress → 2026-10-13:in_progress

### QO-D04 · 模型能力适配、片段时长与路由决策

- 状态：partially_addressed；优先级：P0；阶段：now_director；负责人：director
- 发现位置：seedance_adapter.py; video_workflow.py; director_shootability.py
- 问题：当前 Seedance single_take 4–15s 为保守自限；不同模型时长/参考/多镜/音频能力不一
- 根因：缺有来源日期与接口版本的 capability registry 和语义编译边界
- 方案：建立模型/版本/渠道能力表（clip时长、比例、首尾帧、参考、内生音频、多镜、价格/区域待核）；导演先给意图，技术岗位按注册表拆解；超能力范围拒绝而非假造支持
- 完成验收：Runway/Veo/Kling/Seedance 的公开能力配置和反例单元测试；真实目标供应商用其官方API文档单独认证；任意clip符合目标provider约束
- AI 视频适配：Runway4.5 2–10s、Veo3.1 4/6/8s、Kling3多shot、Seedance2多模态不能混成统一上限
- 依赖：QO-D02
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/3
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-D05 · 演员/服装/道具/场景跨镜一致性

- 状态：partially_addressed；优先级：P0；阶段：now_director；负责人：director
- 发现位置：film_continuity.py; asset_reference_manifest.py; director_v2.py
- 问题：已有ID、道具状态和参考卡结构，但未以真实视频验证身份、手部动作与方位保持
- 根因：文本ID与资产摘要不证明视觉像同一个人
- 方案：导演维护角色/道具/场景bible+分镜状态转移；实际照片参考与授权；选择首尾帧/参考图及失败重制策略，完成跨镜实测
- 完成验收：至少两人物+手机/门的跨镜公开视频试镜，评价脸/服装/道具/光源/左右关系，失败镜头可定位修正
- AI 视频适配：跨clip身份与布景漂移是AI关键风险；摘要和相同seed不等于视觉锁定
- 依赖：QO-D02, QO-D04
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/2
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-D06 · 多动作可拍性与模型失败降级

- 状态：confirmed_open；优先级：P0；阶段：now_director；负责人：director
- 发现位置：director_shootability.py; agent_role_contracts acting/camera_art/ai_technical
- 问题：逐秒动作表有了但复杂互动、多个连续变化易在视频生成时失败；没有真实成功率
- 根因：下游直接按理想影视分镜要求一个视频模型完成全部演员动作
- 方案：每镜列关键动作数、人物数量、接触/空间复杂度；选择分拆、静帧、蒙太奇、后期动画替代路径并量化重试预算
- 完成验收：公开故障注入例：双手接触、道具交换、轴线跳变均能触发正确拆段或人工复审；真实成片有效性需单独标未验证
- AI 视频适配：AI模型对多动作/物理交互有概率性，脚本不能假设必然符合提示词
- 依赖：QO-D04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-D07 · 导演级镜头语言与视觉连续性

- 状态：partially_addressed；优先级：P0；阶段：now_director；负责人：director
- 发现位置：agent_role_contracts camera_art; director_v2; director_workbook.py
- 问题：有景别焦距灯光字段，但经常是填模板而非可解释的摄影选择；轴线和转场缺真实审片
- 根因：结构要求与视觉因果质量没有建立直接验收
- 方案：以人物视线/动机触发镜头，检查机位关系、连续运动、构图重心、光源世界观与色彩语法；导演需能阐明每镜选择的叙事原因
- 完成验收：公开短片方案盲评优于机械镜头列表；镜间轴线/光源违例静态阻断；真实视频另审
- AI 视频适配：镜头机位复杂度要可由目标AI模型产生或有转后期替代
- 依赖：QO-D03, QO-D05
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-D08 · 导演与音效/台词/字幕精确对齐

- 状态：partially_addressed；优先级：P1；阶段：now_director；负责人：director
- 发现位置：agent_role_contracts sound; production_delivery; video_workflow
- 问题：已传精确speech与 onscreen/offscreen，但生成后真实语音文字、口型和字幕时间码未核对
- 根因：预算和时码是计划，缺实际声音解码/ASR与人工语音核验
- 方案：按导演意图为每镜决定原生声音或后期配音；保存逐句人声、口型与字幕对应；拒绝无准确信息的错字成片
- 完成验收：两人镜头至少一名说话另一人闭口；真实音视频逐句人工核验，错字有局部修复路径
- AI 视频适配：原生声音未必可控；优先选后期配音/画外声避免错误口型
- 依赖：QO-D04, QO-D05
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/3
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:partially_addressed

### QO-D09 · 剪辑节奏、过渡桥与镜头版本选择

- 状态：confirmed_open；优先级：P1；阶段：now_director；负责人：director
- 发现位置：agent_role_contracts editing_animation; director_timeline.py; production_delivery.py
- 问题：有J/L cut、转场字段但未以真实影像验证行为连续和情绪节奏；不可默认长镜头一镜过
- 根因：缺由真实媒体帧/音轨回写的编辑视角审计
- 方案：导演审查每个镜头的入点/出点/情绪换挡/声画桥；备选剪辑与失败因果；逐镜选择最佳 take，避免盲目复拍整片
- 完成验收：公开合成方案能量化错误切点；真实2+段小样有可验证片段版本与切点，比对导演剪辑意图
- AI 视频适配：AI片段几秒钟产生，需留头尾缓冲，部分转场后期解决
- 依赖：QO-D02, QO-D08
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-D10 · 专业导演审片标准：不是字段全就是好片

- 状态：confirmed_open；优先级：P0；阶段：now_director；负责人：director
- 发现位置：agent_creative_review.py; tests/test_director_workbook.py
- 问题：现有 QA 检查结构与一致性，但看不到实际镜头、心理驱动和观众投入
- 根因：缺专业观众审阅样本及作品对照盲评
- 方案：至少双样本短片方案、三类体裁，分开评分故事理解/镜头意图/动作可信/声画连贯/整体吸引；归因到编剧还是导演负责
- 完成验收：3题材盲评含反例基线；区分无法自动判断的艺术主观评价；低分片不自动放行
- AI 视频适配：不拿一个模型平台的demo宣称跨模型世界一流水平
- 依赖：QO-D03, QO-D09
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-D11 · 真实双镜生成、跨镜验收与风险边界

- 状态：blocked_external；优先级：P0；阶段：now_director；负责人：director
- 发现位置：SEEDANCE_API_AUDIT.md; video_workflow.py
- 问题：尚无已获授权的 Seedance 真实镜头、人物一致性测试与合成成片
- 根因：私有账号/费用/素材授权、持久运行及成片人工验收未部署
- 方案：先审核私有账号区域、单镜预算和一次性明确批准，再S02+S03双镜真实生成，审片记录并测首次可用率/平均返工/真实费用
- 完成验收：具体镜头、素材、请求、费用、结果哈希、独立真人审片与缺陷记录俱全才可标完成；无授权保持blocked_external
- AI 视频适配：真实片段有随机性；合成视频结果必须按秒/帧检查而非只认API success
- 依赖：QO-D04, QO-D05, QO-D08, QO-F07
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/1, https://github.com/pyzz58/gpt-recommendations/issues/3
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:blocked_external

### QO-D12 · 导演/编剧修订权限冲突与版本谱系

- 状态：confirmed_open；优先级：P1；阶段：now_director；负责人：director
- 发现位置：agent_role_contracts.py; screenplay_director_handoff.py
- 问题：目前岗位提示已限定，但后续实际修改可能改变台词、场景、镜头分配时没有统一revision_request闭环
- 根因：跨部门讨论尚无一个可复核的剧本变更影响列表
- 方案：增加导演返修单->编剧改稿->作者复审->重新绑定镜头和受影响专业工单的完整修改谱系；杜绝旧版本混入新音画制作
- 完成验收：至少3种跨部门改稿触发失效/回滚测试，并验证未受影响镜头可保留
- AI 视频适配：局部返工应避免整片重复生成，高成本动作优先可追踪复用
- 依赖：QO-W09, QO-D02
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

### QO-D13 · 总导演自主分集与单集90秒绝对上限

- 状态：in_progress；优先级：P0；阶段：now_director；负责人：director
- 发现位置：screenplay_director_handoff.director_request; screenplay_series_delivery.director_breakdown_request/validate_breakdown/build_per_episode_crew; skills/01-series.md
- 问题：旧系列Skill允许180秒且此前编剧限300秒，十分钟剧本无法按完整编剧→导演拆分顺畅执行；可能丢节拍、硬凑三集或漏算片头/片尾；新发现：要求每个原剧本节拍按原时长全保留会反过来剥夺导演合法创意压缩权
- 根因：混淆整部故事、导演单集、AI生成单次clip三级时间尺度，缺独立分集时长核验和按集重启原有专业团队
- 方案：导演完整接收编剧剧本与详细说明，自主按叙事/情绪自然断点规划1/2/3或更多集；每集叙事镜头和所有附加时间合计≤90s；所有节拍原顺序恰好一次；长剧本进入分集流程；每集独立启动原有十岗位，全文仍作为上下文，不静默重编故事；创意删减的版本先在QO-D14形成有理由的短版新剧本，然后再使用本项≤90秒分集硬门禁；不再把原稿100%照搬作为影片质量标准
- 完成验收：公开完整10分钟剧本可自主拆7集或10集，每集≤90s；90s+任意片头超时被拒；漏/重复/错序节拍拒绝；每集导演真实岗位请求接收完整上下文、受限镜头工单；未实测成片保持in_progress
- AI 视频适配：每集90秒≠单镜clip长度；含片头、片尾、复述及原稿有来源才可选的最后1–2秒资料页；不得机械均分或制造虚假悬念
- 依赖：QO-W11
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/28；回归 tests/test_screenplay_series_delivery.py — 10min fulltext intake, detailed beat coverage, arbitrary 7/10-episode split, <=90s incl extras, rejects loss/reorder/tampering；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:in_progress → 2026-10-13:in_progress → 2026-10-13:in_progress

### QO-D14 · 总导演主动创意剪辑与重大压缩权

- 状态：in_progress；优先级：P0；阶段：now_director；负责人：director
- 发现位置：screenplay_series_delivery.director_breakdown_request/validate_breakdown/build_per_episode_crew; screenplay_director_handoff.director_request; agent_role_contracts.py
- 问题：当前完整剧本所有beat被强制按原顺序和原长保留，剧本10分钟只能分至少7集；总导演即使认为节奏平庸且3集能有效表达，也不能主动提出删场、压缩、重排及新的导演剪辑版本
- 根因：为了防止静默丢稿，把来源审计完整性错当成最终影片必须逐节拍原样保留；缺导演整体创作诊断、不同长度的导演cut构思、编剧协作返修与新权威拍摄稿的版本链
- 方案：依据DGA导演参与剧本和剪辑的实际职责及ScreenSkills/BFI名导完整访谈，新增导演独立全稿读片诊断和有因果理由的两套剪辑方案；每源beat可retain/condense/omit并逐项解释观众收获及艺术代价、核心事实/人物意义风险；可设计10分钟→3×80秒但不是自动更优秀；涉及剧本正文更改必须发编剧精确返修并重审新版本，原稿不覆盖，批准后的新拍摄剧本再送现有90秒分集专业团队；单纯视听层微调由导演自主
- 完成验收：同一公开虚构10分钟剧本提出3集240秒和较长自然断集两个有差异的cut，逐beat取舍完整且新剪辑时间不超90秒/集；拒绝无理由删除、假来源、篡改授权、伪造已批准；能指出理论命题反转、角色选择失因等阻断；能为正当删改生成定点编剧返修单而不是硬塞全部节拍；独立专业盲审对比两版思想/情绪/节奏后才能认定一流质量
- AI 视频适配：AI片段生成≤数秒/十数秒是镜头技术限制，与90秒每集及整个母稿时长分层；导演先进行无付费故事剪辑，再决定每集镜头/供应商路由；可选资料页仅原稿含实际资料才在最后1-2秒显示且计入上限
- 依赖：QO-D13, QO-D12, QO-W11
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/29；回归 tests/test_director_creative_cut.py — 600s original director cut to 3x≤90s and 10x60; complete editorial audit with omit/condense, fake approvals rejected, sources-page absent, multi-cut comparison, writer revision request；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:in_progress → 2026-10-13:in_progress

### QO-D15 · 总导演详尽指挥与协调所有专业部门

- 状态：in_progress；优先级：P0；阶段：now_director；负责人：director
- 发现位置：agent_team.STAGES; agent_role_contracts.ROLE_INSTRUCTIONS/build_role_messages; screenplay_series_delivery.build_per_episode_crew; director_department_command.py
- 问题：现有十岗位流程有导演宏观圣经和各专业通用提示词，但总导演未把每集独特创作意图、各镜观众体验、实际制作手段、专业部门交接和验收标准讲清楚并传给实际专业岗位；各Agent容易各自发挥形成漂亮但脱节的图纸
- 根因：专业团队 DAG 定义了岗位顺序和输出字段，却缺一个导演亲自主持的跨部门制作会和真正的逐部门/逐镜工作指令；信息共享侧重原计划字段与上游JSON而不是指导专业创作的一致理念
- 方案：依据DGA 7-101/202、ScreenSkills导演/摄影/美术/剪辑/声音/场记岗位全文、BAFTA Paul Greengrass完整导演演讲，实行 director_brief→script_edit→director_lock→导演跨部门专业制作会：7个下游岗位分别有详尽艺术使命、观众效果、逐镜执行、专业边界、验收条件、相互依赖和失败修复。真实模型岗位消息注入该岗位专属指令与必要跨专业接口；导演锁稿变更令原制作会失效；新版90秒系列严格模式无会议单不能发部门工单。真正艺术质量仍需独立盲审和媒体验证；下游真实专业交付的导演收件和定点返工通过QO-D16建立闭环，不能把会议本身冒充成果验收
- 完成验收：公开合成双镜案例覆盖真实10阶段总导演锁稿→制作会→演员/摄影/声音部门真实model-facing输入；七部门、七关键交接及每镜详细意图完整；缺项、复制泛化镜头命令、版本过期、跨专业失联均阻断；独立专业电影/论述/纪录短片盲审证明多部门能按同一个vision制作，真实镜头音画连续才可关闭
- AI 视频适配：先做导演创作协调和具体生产工单，再由技术部门决定 AI clip/静帧/动画/后期路由；单集最终≤90秒，精准AI文字/字幕后期合成，视频生成失败局部替代不得损害角色/核心思想；不以工单多字等于美学水准
- 依赖：QO-D03, QO-D05, QO-D08, QO-D10
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/30；回归 tests/test_director_department_command.py — 7 specialist missions, scene/shot-specific vision, 7 interfaces, model-facing injection, stale lock/data, generic repeat rejection, mandatory production output gate；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:in_progress → 2026-10-13:in_progress → 2026-10-13:in_progress → 2026-10-13:in_progress

### QO-D16 · 导演审核部门真实交付与基于观众体验的精准跨岗返工

- 状态：in_progress；优先级：P0；阶段：now_director；负责人：director
- 发现位置：director_department_command.validate_command/model_facing_role_context; agent_role_contracts.build_role_messages; agent_team.request_revision; agent_creative_review; director_delivery_review.py
- 问题：现有总导演可开详细制作会，把意图交给表演/摄影/声音/剪辑/AI技术/QA，但实际下游交付完成后缺一个把每镜的艺术意图、实收设计和观众可能体验逐项对照、组织责任部门返工的导演闭环
- 根因：只校验导演命令及下游部门JSON结构，无法凭表单确认镜头表达思想/情绪；导演缺依据真实已交稿证据对具体镜头指派协作和定点修改的反馈层
- 方案：复用原导演与部门会议模块，新增director_delivery_review按每镜每部门核实实际交付、意图是否可见、观众认知和情绪变化及证据局限；未交稿必须标pending；导演逐项给出问题证据、责任部门、具体返工动作、协作方、验收方式和冲突仲裁；已确认需返工的单镜经原agent_team.request_revision按原岗位依赖失效机制定点返修，禁止静默改剧情/事实与自动发布
- 完成验收：公开两镜虚构影片中，演员拿信的停顿缺失能被导演定位到S01 acting，明确观众后果及摄影/剪辑协作，并只重新排该岗位指定镜头；缺失岗位被判不可评价；版本变化使旧评论失效；泛泛空话/未经交付声称审过真片遭拒；专业独立人审和实际生成的片段观感仍须验证
- AI 视频适配：短视频每集≤90秒；每镜AI clip与完整视频节奏分层；不同模型的手/道具状态和跨镜声音连续性可能失效，真实媒体验证必须独立授权，不允许以JSON设计假称成片
- 依赖：QO-D03, QO-D15, QO-D11
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/31；回归 tests/test_director_audiovisual_delivery.py — grounded real department-delivery assessment, pending vs completed, precise single-shot revision and staleness rejection；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:in_progress

### QO-D17 · 世界级导演的可迁移艺术判断与周星驰荒诞喜剧的题材适配

- 状态：in_progress；优先级：P0；阶段：now_director；负责人：director
- 发现位置：director_visual_language.py; director_department_command.py; agent_role_contracts.py; new director_artistic_methods.py; skills/11-director-artistic-judgment-and-absurd-comedy.md
- 问题：原导演已有分镜因果与七部门任务书，但未独立证明能根据剧本思想和情绪选择不同名导的可迁移创作方法；普通AI可把喜剧等同搞怪BGM/夸张表情，也可能在严肃科普、纪录片强行塞笑点，导致画面漂亮却人物因果失真
- 根因：现有单镜视听规划有形式字段，但缺艺术方法的适用和失败条件、具体导演选择的反论证、喜剧内在人物需要和世界规则，以及方法选择与部门专业交付之间的版本化一致性；大师风格外观被误当创作机制
- 方案：深入核对斯科塞斯、王家卫、诺兰、迈克李及周星驰本人访谈和小津二手技法研究；新增可迁移创作机制知识卡、导演理由与反向比较、喜剧按题材可关闭或启用，启用时需要人物渴望、合理预期、物理因果荒诞升级、可见反转和不强制煽情的情绪回声；每镜讲清行为/视听/观众变化并绑源/导演锁/会议版本后传现有七部门专业任务；不模仿名家台词画面演员形象
- 完成验收：公开虚构两镜短片分别作为严肃人物戏和人物因果喜剧测试；严肃版不会被强迫喜剧，荒诞版具完整人物诉求/预期/反转逻辑且逐镜观众改变；未知技法、固定套路、剧情版本失效、未选技法、错误角色指令被阻断；现有岗位模型真正收到分专业详细原因而非仅元数据；独立专业盲评人物及笑点成立且真实视频验证后才可完全关闭
- AI 视频适配：每集包含片头回顾片尾尾页最多90秒；荒诞笑点需可见物理行动和反应切点，多个AI短clip可组合但不能篡改剧本事实；可能由2D/静态/后期合成替代无法生成的手部/道具特技；未授权不得发送付费模型或发布任何私稿
- 依赖：QO-D03, QO-D15, QO-D10
- 历史问题：无
- 修复证据：PR https://github.com/pyzz58/gpt-recommendations/pull/36；回归 tests/test_director_artistic_methods.py — genre-specific transfer, serious no-gag gate, character causal comedy ladder, method source/shot/lock validation and model-facing per-department directions；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:in_progress → 2026-10-13:in_progress

### QO-F01 · 演员表演与动作调度专业审计

- 状态：audit_pending；优先级：P1；阶段：future_dept；负责人：acting
- 发现位置：agent_role_contracts acting; director_shootability.py
- 问题：未对照国际表演/场面调度标准并结合AI虚拟演员真实验证
- 根因：专业动作语义与生成模型可执行性的质量差距未知
- 方案：审查意图-策略-可见行为-反应-走位/视线-手部/道具接触；建立易失败动作分拆和镜头替代方案
- 完成验收：专业表演审稿+公开虚构动作片段复核后确定问题；真实媒体另验
- AI 视频适配：多主体交互及手部一致性需按片段限制设计
- 依赖：QO-D04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F02 · 摄影/灯光/美术世界观专业审计

- 状态：audit_pending；优先级：P1；阶段：future_dept；负责人：cinematography_art
- 发现位置：agent_role_contracts camera_art; director_v2
- 问题：尚未独立以职业摄影指导标准审查可拍性、空间/摄影系统及 AI 参考图规划
- 根因：摄影任务结构字段覆盖不证明实际视觉品格
- 方案：梳理景别轴线、光源、反差、运动触发、镜头参考与不同模型光影保持能力
- 完成验收：独立摄影审阅报告+多镜视觉统一测试计划+关键阻断点
- AI 视频适配：参考图和生成时视觉一致性受模型/版次限制
- 依赖：QO-D07
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F03 · 配音/对白/拟音/音乐专业审计

- 状态：audit_pending；优先级：P1；阶段：future_dept；负责人：sound_voice
- 发现位置：agent_role_contracts sound; production_delivery
- 问题：声音专业岗位尚未按真实声音总监标准核查混音、叙事留白和声音衔接
- 根因：音轨工程和口型风险尚无系统性审计
- 方案：独立 VO/角色对白/环境/音乐/拟音层，动态范围、对白清晰度、声画时间线与旁白措辞所有权
- 完成验收：专业审计报告与可重现声画合成小样；不等于自动翻录真人声
- AI 视频适配：AI原生声音与后期音轨共存会产生重读、口型与同步冲突
- 依赖：QO-D08
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F04 · 剪辑/动效/信息图专业审计

- 状态：audit_pending；优先级：P1；阶段：future_dept；负责人：editing_animation
- 发现位置：agent_role_contracts editing_animation; director_timeline
- 问题：尚未覆盖动画图表准确性、过渡逻辑、短视频观看节奏、字幕安全区
- 根因：后期工单是否符合可交付剪辑工程质量未验
- 方案：审查切点动机、镜头连续、字幕、动效层、精确数据图形、节奏/空间变化与导出规格
- 完成验收：独立剪辑师审核+多段样片可验收+图表事实QA
- AI 视频适配：文字和精确数据宜后期而非视频模型直接生成
- 依赖：QO-D09
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F05 · AI视频技术导演适配与提示词编译审计

- 状态：audit_pending；优先级：P0；阶段：future_dept；负责人：ai_technical
- 发现位置：seedance_adapter.py; agent_role_contracts ai_technical
- 问题：部分模型只支持单镜，但现有多镜/首尾帧/参考资产能力未适配；跨模型路由可能有隐性假设
- 根因：供应商接口能力更新和渠道差异缺产品级验证
- 方案：分供应商能力注册表、参考素材链路、失败分类、模型适配/降级及成本策略；最小化不确定性
- 完成验收：真实目标供应商参数核对+错误输入拒绝+样本试镜结果
- AI 视频适配：Seedance/Veo/Runway/Kling仅作可选能力，不预设账号必有
- 依赖：QO-D04
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F06 · 独立场记/事实/版权与质量门禁审计

- 状态：audit_pending；优先级：P0；阶段：future_dept；负责人：continuity_qa
- 发现位置：agent_handoff_audit.py; agent_creative_review.py; audit_registry.py
- 问题：既有QA主要检查合同而不是观众感受、媒体事实与版权安全
- 根因：缺独立QA反向恶意样本、审查隔离和来源核对
- 方案：建立三层QA：结构审计/专业盲评/真实音画与权利链；缺任一层不能谎称全验收
- 完成验收：风险样本失败注入、角色修订 owner 复核、来源和肖像授权链记录
- AI 视频适配：模型生成媒体的版权/标志/人物肖像需要实际素材审核
- 依赖：QO-D10
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F07 · 真实账号、素材、资费和私有存储生产审计

- 状态：audit_pending；优先级：P0；阶段：future_dept；负责人：api_privacy_cost
- 发现位置：AUDIT_FINDINGS.json AUD-002; seedance_adapter.py; video_workflow.py
- 问题：缺可靠长期私有执行环境、真人授权和供应商费用账单验证
- 根因：代码中的字符串批准不是真实支付/隐私权限
- 方案：私有API密钥库、配额/费用硬门禁、一次性提交、回执与回收、下载校验、故障恢复、资产授权
- 完成验收：独立安全验证+真实低成本受控验证后才解除；否则持续blocked
- AI 视频适配：供应商费用、内容安全策略和第三方存储需按账号与地域逐项核对
- 依赖：QO-D04
- 历史问题：https://github.com/pyzz58/gpt-recommendations/issues/1
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F08 · 真实视频审片、版本优选与局部返工

- 状态：audit_pending；优先级：P0；阶段：future_dept；负责人：media_qc
- 发现位置：video_workflow.py; production_delivery.py
- 问题：尚无真实视频跨镜质量可重复评价、编辑最佳片段选择和局部返工闭环
- 根因：只验证响应状态/MP4 header与摘要不足以证明画面可用
- 方案：解码/关键帧/声音/字幕/人脸/手部/动作检查，记录take与fail reason，不重发未经批准费用
- 完成验收：真实媒体验收与镜头级版本谱系，剪辑输出经过实际播放及人工批准
- AI 视频适配：AI输出概率变化大、局部返工是成本与质量核心
- 依赖：QO-D11
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F09 · 最终合成、字幕/无障碍与可选资料尾页

- 状态：audit_pending；优先级：P1；阶段：future_dept；负责人：postdelivery
- 发现位置：production_delivery.py; closing_evidence_card.py
- 问题：1.8s资料页是否可读、最终字幕安全区/音量/多格式未做真人成片审查
- 根因：视频交付层只是工单而不是媒体合成实物
- 方案：专业剪辑/后期审查：合成一致、精确字幕、转码质量、标题版权、可选尾页不遮蔽关键信息
- 完成验收：至少竖屏/横屏若支持的真人观影QA；有依据才显示1–2秒尾页，无则不加
- AI 视频适配：不要求视频模型拼准确字幕；片尾1–2秒只放能读的简化出处
- 依赖：QO-F04, QO-F08
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

### QO-F10 · 整体制作协调/进度/异常/返工成本的专业审计

- 状态：audit_pending；优先级：P1；阶段：future_dept；负责人：product_workflow
- 发现位置：agent_team.py; local_director.py; PRODUCT_NORTH_STAR.md
- 问题：没有真实私人制作流程用户体验和交付周期证据
- 根因：模块通过测试但实际从文案到成片可能步骤反复且不可恢复
- 方案：质量阶段每轮只能围绕已登记问题；建立单镜/整片成本与返工次数、专业人员可审的版本责任和追溯日志
- 完成验收：真实低成本作品从输入到导出全程可追、失败可定位恢复，人工决定明晰
- AI 视频适配：每个AI服务不同的限流/缓存/授权并限制用户花费
- 依赖：QO-F07, QO-F08
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:audit_pending

## 修复一项就更新一项

复现缺陷 → 有针对性的解决方案 → 合成反例和回归测试 →
独立专业评审 → 所需的真实媒体/授权人工验收 →
补充证据 → 将对应 JSON 状态改为 complete → 重新生成本文件并通过 CI。

代码绿色仅证明结构与回归；不能代表剧本/导演艺术质量、一流等级或真实成片已验证。
不公开用户稿件、不自动发付费请求，不绕过旧 AUD 安全门禁。
