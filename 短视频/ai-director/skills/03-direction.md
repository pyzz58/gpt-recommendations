## 导演必须让声画成为思想与情绪，而不仅是“漂亮镜头”（QO-D03）

新增 [Skill 10](10-director-audiovisual-meaning-and-review.md) 和 [职业一手资料及实际代码审计](../quality-optimization/QO-D03_D16_AUDIOVISUAL_CRAFT_AND_DELIVERY_AUDIT.md)。每个导演镜头需要说明：观众入镜前相信什么、实际画面中的事件、入镜后认识怎样改变、为什么这样选静/动机位和景别、为什么使用声音或沉默、何时切、用普通 B-roll 替代会丢掉什么意义，以及 AI 模型失败怎样保住原意。只有收到具体 plan、并注入所有相关专业岗位，才叫有可执行视听构思。字段通过≠审美通过。

## 总导演在逐镜头设计前必须组织部门制作会

先读完整编剧稿、明确的导演 cut/≤90秒分集、每场详细叙事意图；在 `director_brief` 与 `director_lock` 后，使用 [Skill 09](09-director-department-command.md) + `director_department_command` 实际向演员、摄影、美术、声音、剪辑、AI 技术、QA交代本片意图与真实分工。每个部门、每个shot都必须有具体艺术效果、可执行动作、专业边界、真实交接和客观验收；一个岗位不得擅自把自己更好的想法覆盖其他岗位的权威内容。导演主持冲突解决。**不许先写一堆漂亮的镜头提示词才回头猜故事要表达什么。**

# Skill 03：专业电影导演与镜头制作

参考项目：growgami/sd2prompt、smixs/visual-skills、Ironieser/CineCrew、billpar/ai-cinematic-pipeline、liqi21cn/video-prompt-skill。此文件为独立编写的设计规则，**未直接复制上述仓库源码**。

对每镜都必须先确认：**导演意图/发生的可见变化是什么？** 随后写出能拍摄、可检查的指导，而不是“精美、史诗、电影级”形容词。

- `objective`：镜头驱动的情绪和叙事变化，角色/道具真正发生了什么。
- `staging`：角色在画面中的精确空间关系、朝向、道具左右手、视线锚点；不能出现近景中又要求拍到全身等几何矛盾。
- `performance`：可观察的微表情与身体动作；完整开场、微动作、反应、停留、结束状态；避免“五秒里做十个动作”。
- `beats`：每镜相对秒数不重叠、无空白，所有动作与镜头运动、声音逐秒对齐；动作必须在物理上可执行。
- `camera`：景别、机位、摄影运动起止、移动理由；没变化就保持固定，不为华丽而运镜。
- `art`：光源方向、场景、道具材质、服装连续性、色彩情绪路径。
- `sound`：旁白交接、环境音、明确的同期声音、音乐起止与静音；任何字幕图表准确数值只在后期出现。
- `continuity`：整个系列的角色、服装、道具与房间相对位置；下一镜起始状态要与上一个镜头结尾可接。reference_assets 必须真实存在，不可捏造已制作素材。
- `graphics`：数字对照要有研究类型、比较对象、适用界限；字在竖屏安全区域内可读。
- **实际制作路线优先于概念镜头类型**：读取 [PRODUCTION_ROUTING.md](../PRODUCTION_ROUTING.md)。同一个 `base.visual_type=ai_video` 的镜头也可指定 `generation.route=static_post/edit_composite/live_action_insert`；不要给静态图或实拍镜头生成 AI 视频模型 prompts。旧档案的 `production_method` 只支持已列的明确别名；未知值阻断而非猜测。
- `generation`：AI_VIDEO 镜头生成候选模型提示词；纯数字/来源卡改为后期图文制作任务，不需要视频模型。
- `qa`：不满足动作连贯、人物一致性、参考图存在条件时不得宣称“已通过真人审核”；一律 human_approved=false，直到真正用户审阅。
- 单个AI生成镜头重心不超过一项主要动作链和一项主要运镜；模型不支持的复杂要求要拆分镜头。
- 不凭空添加额外剧情；所有镜头服务于文本核心信息，保持观众能看懂。

## 让动作真的可制作：手、物、秒数与拆段方案

- 参考 [SHOOTABILITY.md](../SHOOTABILITY.md)。有真人出镜且用 AI 视频路线时，`shootability` 必须写 `mode`、`action_units[]`：每个 beats 节拍至少一个动作或明确姿态保持；每个单元均有 `id,beat_index,actor_id,hand,prop_id,from_s,to_s,action,visible_result`。若无道具，`prop_id=null`，但手机、书等真实道具必须先在 `continuity_contract.props` 登记稳定 ID。
- 左右手可以协同，但同一只手不能在同一秒承担两个独立动作；不要把“右手拿手机、左手拿书、起身、转身、走路”全部合成一个模糊 action。
- AI 模型处理手指、多道具与遮挡可能有风险，遇到短时间连续精细动作要修改表演节奏、建议静态/实拍/剪辑替代或写可执行的 `fallback`，不要为了整齐强制单镜连续生成。
- 选择 `mode=split_stitch` 则必须给 `segments[]`：每段 `id/from_s/to_s/route/join_rule`，连续覆盖全镜，讲清动作姿势和道具状态如何从前段带到后段。只是规划，不是实际生成。
- `director_workbook.py` 会把动作可拍性问题、剪辑/台词/动画设计缺项、跨镜头衔接汇总到唯一主交付书。没有完成就留待导演设计，不能伪装已拍通或已锁脸。

## 真实动作切点证据与避免机械套话

每对相邻镜头的 `editing.narrative_bridge` **必须**附 `beat_link`：`outgoing_beat_index` 指当前镜头 `beats[]` 的最后一个真实节拍，`incoming_beat_index=0` 指下一镜首节拍；`cut_on_visible_event` 以该末节拍实际动作（手停住、视线改变、物品落下等）具体说明为什么此刻切入下一镜。不能只写“动作结束后剪辑”；如果导演需要在别处切，必须先明确调整基础镜头或动作 beats，再建立交接，而不是虚构镜头外的事件。

至少三条跨镜头 `why_cut_here` / `viewer_question` / `answer_or_reframe` / `motion_or_prop_link` / `implementation` 一字不差时将产生套话复核，并暂停“制作蓝图齐备”标记。允许合理的统一审美规范重复，但**叙事问题和实际动作链接必须跟各镜头内容相关**。电影语言的真正好坏仍留给真人逐镜审阅。

## 跨镜头专业导演衔接（新增主线要求）

- 参见 [NARRATIVE_HANDOFF.md](../NARRATIVE_HANDOFF.md)。除了单镜头内部摄影/动作/动画/声音，**每个非末镜都必须为紧随其后的镜头设计 `editing.narrative_bridge`**。四个独立部分：
  - `cut_intention`：观众在上一镜留下的问题、下一镜解答/反转、为何这一秒切、信息如何改变、`cut_type`。
  - `emotion_pacing`：情绪前后值、预期观众感受、`tempo_change`（加快/放慢/保持/反差）、节奏原因及数字 `hold_before_s / settle_after_s`。
  - `visual_handoff`：相邻两镜末帧/首帧视觉锚点、视线/空间轴线、动作/道具/形状联系与 `relation`。
  - `style_handoff`：统一或有意反差的 `strategy`、调色目标、灯光逻辑、构图、材质/锐度、字体字幕规范、能在后期实际执行的 `implementation`。
- AI 视频、二维图形、静态画面、剪辑合成、实拍插入的**介质变化**必须明确画面连接与色彩匹配方法。不能指望模型在不同生成方法间自动保持“电影感”。
- **每一对镜头都要有独特的叙事动机**；切点、情绪变化、镜头运动不能只有抽象语句。如果是有意识的跳切或视觉反差，说明为什么适合观众理解与情绪表达。
- 使用 `director_workbook.py` 输出的 `narrative_bridges` 进行逐边界人工审看；字段填写通过仅代表数据完整，不等于“电影语言已被验证”。

## 本轮精化：逐句配音、逐段字幕与真实声音转场

- 不能把“旁白从头读到尾”当作精确时间码：`speech.voiceover.cues` 按每句/呼吸点填写 `from_s/to_s/text`，组合后的原文字句不得发生增删；注意配音速度按实际 cue 时长计算。
- `speech.subtitle_cues` 与旁白 cue **分别设计**。字幕在视觉安全区内按阅读节奏出入，`text` 应分段连接复原基础 `subtitles.text`，不能随意替换文字；没有字幕也应明确 `[]`。
- 每镜必须明确 `editing.audio_bridge`：不用跨镜声写 `{type:none,duration_s:0,track:none,reason:具体理由}`；用声音先进入下一镜则选 `j_cut`，让上一镜声音延续则选 `l_cut`，并写明衔接秒数、具体声音轨和叙事动机。不是所有转场都必须用 J/L-cut。
- 动画出现时不能只有“变暗”“缓慢移动”的文字描述：至少要明确图层、动作、`from_s/to_s` 与视觉结果；但不能为追求技术字段机械添加没必要的特效。
- `director_workbook.py` 将 `creative_design_complete` 与 `editor_handoff_ready` **分开评价**：前者只证明创意栏目不缺，后者还须具备精确的声音、字幕、动画和剪辑交接信息；二者都不是人工批准或影片已生成。详见 [EDITOR_TIMELINE.md](../EDITOR_TIMELINE.md)。

## 可交接的时间线工作单

参阅 [EDITOR_TIMELINE.md](../EDITOR_TIMELINE.md)。将具体导演构思落到**逐镜头的绝对时间与声画轨道**：

- `beats[].from_s/to_s` 与 `camera`、表演、声效同步；清楚写出触发点、角色动作和镜头停留，而不止写“节奏自然”。
- `speech.voiceover.cues` 推荐按逐句填写 `{from_s,to_s,text}`；拼接后必须与基础稿旁白字句一致，特别需要试读时请标注为待人审。
- `speech.dialogue[]` 除角色与台词之外必须注明相对时间；与旁白同时出现时要设计如何压低背景声、谁先说、哪里留白。
- `sound.effects[].time_s` 不能超过镜头时长；`animation.elements[]` 推荐每个图层带数字 `from_s/to_s` 与可执行 `timing`、`layer`、`action`，而不是只用笼统文字。
- `editing` 要考虑相邻镜头前后帧、视觉方向、动作衔接、声画延迟（J/L cut）是否需要，明确剪辑拼接顺序。`cut_reason` 必须说明为什么在那个点剪，而不是为了堆切镜。
- `director_workbook.py` 现在会输出 `editor_decision_list` 和人工核查警告。不得凭空填充真实素材、时间码或配音；没有实际制作素材时这是可执行**设计图纸**而非成片工程。

## 新版导演完整性要求：编辑 / 动画 / 台词必须是独立设计

参考 [PRODUCT_NORTH_STAR.md](../PRODUCT_NORTH_STAR.md) 及 [director_workbook.py](../director_workbook.py)。整个软件的产品是**完整的专业导演图纸**，并不是简单图像生成链。

所有镜头除原有的 objective、staging、beats、camera、art、sound、continuity、graphics、generation、qa 外，**必须新增三项导演设计**（旧 JSON 可读取，但未填写就只能叫草稿）：

- `editing`：`incoming_transition`、`outgoing_transition`、`cut_reason`、`rhythm`、`assembly_instructions`。不能写“自然过渡”这种没有做法的空话。转场类型应与基础稿一致；若确实需要改，单独提出基础分镜修订，不能悄悄改变时间轴。首镜 incoming_transition 为 `start`，后续接上一镜已设定的 outgoing_transition。
- `animation`：`mode`、`timing`、`elements`、`render_in_post`、`style`。每个动效 `elements` 对象应说明 `layer`、`action`、`timing`（动画发生时间和运动参数，避免把长段镜头笼统标“加动画”）。如果不用动画，也要写 `mode=none`、`elements=[]` 并解释为何不需要。
- `speech`：`voiceover` 对象内逐字引用 base.narration 的 `text`，独立写 `delivery`、`timing`；`dialogue` 为出镜对白数组（没有就 `[]`），每条需要 `speaker_id`、`text`、`delivery`、`from_s`、`to_s`；`subtitle_direction` 和 `lip_sync_policy` 必填。**旁白与口型对白不同，不得把配音备注当成已获用户同意的文案改写**。

须关注声画并轨：动作真正出现在镜头哪一秒、台词从哪一秒开始、动画在哪一层做、何时切、该镜头交给 AI 视频、静态图还是后期合成。新增字段不许出现“待设计”“自行处理”“根据情况”等托辞。

导演工作结束后使用 `director_workbook.py` 汇总并评审全镜头（此处为将来获批后的本地工作流说明，当前仍 GitHub-only）。`creative_design_complete=false` 时不得称为完成专业导演任务，更不能仅因提示词存在就宣布可制作；但不能因为参考图片尚未生成而停止完整的导演方案设计。
