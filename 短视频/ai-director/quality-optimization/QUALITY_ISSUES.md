# AI 视频导演｜质量优化问题清单

> 本文件根据 QUALITY_ISSUES.json 自动生成。勿直接修改状态。
> QO 管理专业创作及 AI 视频质量；现有 AUD-xxx 技术安全问题仍需独立跟踪。

## 总览

- 登记 32 项；编剧 10 项，总导演 12 项，其它部门 10 项。
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
| QO-D01 | director | P0 | partially_addressed | 导演以完成剧本为唯一剧情权威 |
| QO-D02 | director | P0 | confirmed_open | 场次与分镜解耦：一场可多镜，一镜可多节拍 |
| QO-D03 | director | P0 | confirmed_open | 导演视听母题、情绪弧线与视觉叙事 |
| QO-D04 | director | P0 | partially_addressed | 模型能力适配、片段时长与路由决策 |
| QO-D05 | director | P0 | partially_addressed | 演员/服装/道具/场景跨镜一致性 |
| QO-D06 | director | P0 | confirmed_open | 多动作可拍性与模型失败降级 |
| QO-D07 | director | P0 | partially_addressed | 导演级镜头语言与视觉连续性 |
| QO-D08 | director | P1 | partially_addressed | 导演与音效/台词/字幕精确对齐 |
| QO-D09 | director | P1 | confirmed_open | 剪辑节奏、过渡桥与镜头版本选择 |
| QO-D10 | director | P0 | confirmed_open | 专业导演审片标准：不是字段全就是好片 |
| QO-D11 | director | P0 | blocked_external | 真实双镜生成、跨镜验收与风险边界 |
| QO-D12 | director | P1 | confirmed_open | 导演/编剧修订权限冲突与版本谱系 |
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
- 状态历史：2026-10-13:partially_addressed → 2026-10-13:partially_addressed → 2026-10-13:in_progress

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
- 问题：目前自动审核看内容是否填写和引文是否匹配，无法证明剧本不模板化、每场必要、有思想/情绪递进
- 根因：缺职业编剧发展性编辑的具象证据与反例评估
- 方案：定义场景进入前/离开后变化、不可替代性、张力/认知跃迁以及差异化语言审核；对空镜头、套话与独特场面样本盲评
- 完成验收：公开样稿成对A/B盲评；至少2种文体、至少2名独立评审记录理由；重大退步必须返修，不能靠数字评分自动打勾
- AI 视频适配：每段必须有画面或叙事功能，避免科普一段话一张无差别图卡
- 依赖：QO-W01, QO-W02
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

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
- 状态历史：2026-10-13:confirmed_open

### QO-D03 · 导演视听母题、情绪弧线与视觉叙事

- 状态：confirmed_open；优先级：P0；阶段：now_director；负责人：director
- 发现位置：agent_role_contracts director_brief/director_lock; director_workbook.py
- 问题：规范强调填完情绪/摄影字段，但多场图灵示范仍有翻书光标等通用意象，无法证明每镜有不可替代的故事功能
- 根因：缺影像叙事的盲评和主动比较备选构想
- 方案：建立导演 treatment：核心视听母题、场景对照关系、开场/收束视觉呼应、动作触发镜头、声画冲突；给出被否决方案与原因
- 完成验收：盲评能将空泛镜头与主题驱动镜头区分；每镜存在理由可以被回溯；观众不依赖旁白也能理解至少部分情绪/事实变化
- AI 视频适配：高质量不等于强制复杂动作；在单片可生成前提下优先视觉叙事
- 依赖：QO-D02
- 历史问题：无
- 修复证据：PR 未提供；回归 未完成；独立审核 未完成；真实媒体 未完成或不适用
- 状态历史：2026-10-13:confirmed_open

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
