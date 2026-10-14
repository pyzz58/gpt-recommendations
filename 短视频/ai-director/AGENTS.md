## 总导演一体化创作闭环（QO-D10 / QO-D06 / QO-D12，2026-10-14；暂不测试）

同一位总导演使用**三种不可互相替代的能力**：QO-D10 `director_whole_film_critique.py` 判断整部作品的主题、人物、情绪与视听表达是否值得执行，保护有因果理由的非套路创意；QO-D06 `director_action_rescue.py` 将真正需要观众看见的复杂表演与道具状态转换为两种时间完整且有艺术代价说明的专业制作路线；QO-D12 `director_revision_lineage.py` 保障作者、编剧、导演与演员/摄影/声音/剪辑/AI技术岗的修改权限、回滚影响与不同剧本版本隔离。**任何部门不得借技术降级悄悄删除人物抉择、原文台词、事实或因果。**

融合入口 `director_creative_integration.py` 要求同一权威剧本、source/base digest、导演锁稿、制作会、视听方案、所选电影艺术方法和镜头ID完全一致。已修复 QO-D10 旧草稿的重要失效缺陷：**制作前审片不因专业部门正常交稿而过期**，制作后批判才绑定实际已提交部门的版本/摘要；与QO-D06的相同二阶段约束保持一致。真实专业消息构造 `agent_role_contracts.build_role_messages` 与收到结果时的 `validate_role_output` / `submit_role_output` 均可同时核验整片创作方案及动作设计。仅新base显式设置 `director_integrated_creative_mode={kind:'director_integrated_creative_review_required',before_specialists:true}` 才强制七下游部门完整遵循这两份艺术计划；原项目不改既有兼容性。**存在待编剧修稿、待导演艺术改稿或动作方案仍被结构性阻断时，不允许继续下发专业任务。**

制作后由 `director_creative_integration.postproduction_assessment()` 综合 QO-D10 的真实岗位设计证据与 QO-D06 在实际演员/AI技术交稿上重算的离线动作风险，返回未派发的专业问题和艺术判断。`make_lineage_change_from_finding()` 只为一个具体导演问题生成版本锁定的 QO-D12 修改提议；需要总导演另行明确同剧本返工，涉及人物、事实、故事、对白必须给编剧全新完整剧本并通过原 `screenplay_director_handoff` 审稿，再开始**新**十岗位任务账本。旧素材只能列成人工复核候选，旧导演锁和审批不得迁移。原同导演 QO-D16 专业交付审核仍负责逐镜目标与精准返工，不创建第二导演或第二套任务权威。

详尽、唯一的融合顺序见 `skills/18-director-integrated-creative-production-gates.md`，细分专业规范 `skills/15-director-whole-film-artistic-critique.md`、`skills/16-director-action-feasibility-and-creative-preservation.md`、`skills/17-director-screenwriter-revision-lineage.md`。此前各草稿 PR #62 / #65 / #66 **未合并main**，融合开发分支集中携带三版代码、原技能文档以及统一入口；不可将草稿视为主分支已实现。

**当前验收纪律：** 用户明确“先不测试”，本轮仅开发及静态核对，不运行单元/媒体测试、不请求付费接口、不上传私人稿件，也不将draft代码合并入main。QO-D10/06/12只能记 `in_progress`，艺术质量、真片观众反应、Kdenlive桌面操作及模型实际复杂动作生成均不能据此声称完成。原十岗位与作者的权限保持唯一权威。

---
## QO-D19 / QO-D09｜第五阶段：公开合成声轨、字幕的实际解码级时间验证（2026-10-14）

总导演掌握剧本与声画思想的**源锁定指令**，不能把视频静音、没有真实台词、字幕错时的成品冒充通过验收。第四阶段 QO-D09 已使用原生OTIO读回和FFmpeg真实视频帧验收；第五阶段新增 `director_av_sync_smoke.py`、`tests/test_director_av_sync_smoke.py`，测试环境仅允许**公开合成视频+精确帧时间码的测试音调与字幕**：48kHz 16-bit 单声道 PCM 在每个已指定声音帧内必须有非零声能、所有间隔必须真正静音；FFmpeg/libass生成画面叠字并与声轨合成Matroska，解码后逐sample对比音轨、逐帧比较字幕显隐，任何偏离必须失败。

该合成示范只是检验软件能否在**给定**声音/字幕时间码时正确合成。它既没有自动判断原文对白时长，也没有演员真实语音/口型、音色版权、Kdenlive GUI项目导入或视觉电影美学认证。任何真实客户视频、稿件、演员面容和客户声轨**禁止进CI或仓库**，CI必须安装FFmpeg及libass并强制测试；QO-D19/QO-D09继续`in_progress`。

官方 Kdenlive 25.04+ 具备原生OTIO导入；官方同时警告软件间不能保证转场效果保留。真实Kdenlive桌面导入、非硬切、J/L桥及演员口型仍需独立现场验收，不可因合成声画成功而越权开启发布。

---
## QO-D09 第四阶段｜OTIO 读回 + FFmpeg 真实解码硬切烟雾测试（2026-10-14）

**注意当前边界**：Kdenlive 25.04+ 已原生支持 OpenTimelineIO；旧 otio-kdenlive-adapter 已被 KDE 明确标记为弃用，禁止为达成“软件兼容”假象而接入该失养适配器。未实际运行图形界面软件导入不得宣称 Kdenlive/Premiere/Resolve 导入通过。

本轮新增 `director_picture_render_smoke.py` 与 `tests/test_director_picture_render_smoke.py`。只允许公开合成、**无配音无字幕、无片头片尾证据页、无非硬切效果**的短小镜头清单：必须首先从已经 SHA/FFprobe 核验的本地媒体生成 `.otio`，再用 OTIO 原生适配器重读该 JSON，逐镜验证 Clip 身份、URI、源帧入点/时长与导演剪口，最后用 FFmpeg 实际解码和合成为 MP4，并用 FFprobe 复核目标实际总帧数。CI 将从无私人内容的红/绿/蓝不同画面读取实际视频像素确认画面顺序及边界。未经源媒体认证、OTIO 格式不匹配或任何声音/字幕/复杂转场要求，一律明确阻断，不允许默默丢掉导演艺术创作。

测试输出仅供公开合成烟雾验收，绝不认定真实客户视频成片、Kdenlive GUI 导入、对口型、声画艺术质量、版权或发布授权。实际电影制作前需由操作员在本地选择 Kdenlive 25.04+ 等 NLE 导入原生 OTIO，记录可重现媒体引用、转场、声轨、字幕与实际预览差异；需要专业人工审片。质量总账 QO-D09 维持 `in_progress`，不允许因此把 QO-D19 关闭。

---
## QO-D09 第三阶段｜私有视频文件核验与原生 OTIO 交换

本项目同一总导演负责镜头与跨场景蒙太奇创作，不增加第二个导演。现有 QO-D09 剪辑工作单来自导演已经审查的剧本和逐镜时码，不得因为给出剪辑格式而放宽剧本来源、90秒预算或声音 cue 保护。

新模块 director_media_otio_export.py 只能在用户本地私有媒资目录工作。必须使用 FFprobe 核验素材实际帧数、帧率、尺寸，使用 SHA-256 比对全部文件字节，并通过工单摘要和路径检查锁定单镜素材。没有素材则保留真实 Gap。输出使用开源的 OpenTimelineIO 0.18.1 原生 .otio JSON，另可输出精确源文本的 SRT 拟定字幕表；不等于实际视频编码或已验证剪辑软件导入。

导演的 dissolve / match_cut / sound_bridge / jump_cut 在 OTIO 中保留作为待核验元数据；不因存在匹配素材就自动变成已经完成的时间轴效果。所有过渡仍受实拍/AI素材余量、逐镜视觉、人和道具、配音/口型与专业审片制约；绝不静默降级成硬切。

私人视频文件、含真实本地路径的 OTIO、原台词与全部字幕不允许写入公开 CI、仓库、Issues、PR 或普通调试日志。CI 测试生成虚构纯色视频，不调用任何付费生成 API，不验证真人角色创作质量。render_or_publish_authorized 永远为 false，直到后续真正完成媒体验收和用户授权。质量总账 QO-D09 及 QO-D19 继续 in_progress。

入口：skills/14-director-editorial-montage-and-time.md；director_montage_editor_conform.py；director_media_otio_export.py；tests/test_director_media_otio_export.py。

---
## QO-D09｜第二阶段：全片帧级蒙太奇剪辑工单（2026-10-13）

**保留同一个总导演与原十岗位，不添加新的统筹Agent。** 第一阶段 `director_editorial_montage` 负责有来源的蒙太奇创意规划和时空/演员道具入出状态；第二阶段 `director_montage_editor_conform.compile_work_order(...,fps=...)` 真正从已审剧本和导演镜头覆盖重验证、重建权威十岗位计划，复用现有 `series_final_timeline` 的全片≤90秒预算，输出机器可读帧级编辑表、逐剪口导演任务、绝对帧级声音与字幕绑定（仅已提供 QO-D19 有效cue时），以及可阅读的 `editor_instructions`。没有字幕时间码时明确阻断，而不允许“所有台词字幕放在本镜第一帧”。

帧率**必须由操作者明确指定**，支持24、25、30、50、60整数fps；不能把小数秒随意四舍五入后假装准确。证据页仅在原文确有支持和导演预留时作为全片最后单独后期片段（1.8秒）。硬切零时长；叠化必须有明确交叠/把柄，匹配剪切需要真实帧核验，J/L 声音桥必须有实录音及出入点，跳切要有艺术审核。若没有真实媒体/授权/音画审核，`ready_for_rough_cut=false`、`render_or_publish_authorized=false`，绝不可由剪辑软件默认为普通硬切。

旧的 `director.py` / `director_v2.py` / `production_delivery.py` 仍会明确拒绝尚不能正确消费蒙太奇的实际视频编译入口；**新增合法帧级工作单不是已生成可播放文件或声称导出完整 NLE 时间线**。后续媒体引用、转场把柄、配音口型和实际剪辑验证另做第二轮，在用户明确授权前不使用私人剧本、无付费API及媒体上传。

[Skill14](skills/14-director-editorial-montage-and-time.md) / [编译器](director_montage_editor_conform.py) / [回归测试](tests/test_director_montage_editor_conform.py)。质量总账既有 QO-D09 `in_progress`，对应 QO-D13 90秒全片时轴、QO-D19 声画cue，绝不新增重复Issue编号。

---

## QO-D09｜跨场景蒙太奇与来源受控的时间跳转（2026-10-13）

本项目仍由**同一个总导演**统筹。QO-D09主管编辑节奏和蒙太奇序列；QO-D05主管人物/服装/道具/场景状态与后续真实媒体验证；QO-D07主管轴线、摄影空间及光色连贯；QO-D02主管单个物理镜头的剧本来源连续覆盖。**禁止把不同物理场景硬写进一个物理 shot**，跨场景蒙太奇必须是多个可分别生产的物理镜头组成的后期 sequence。

新增 [Skill14](skills/14-director-editorial-montage-and-time.md) 与 [director_editorial_montage.py](director_editorial_montage.py) 的结构化 `montage_plan`，每组连续 `shot_ids` 须有对应数量的真实剪口 `seams`，逐剪口解释地点、时间、演员道具状态、摄影光线、声音桥、观众理解变化、导演为何选择及 AI 不可拍时备用方案。**倒叙、提前、并行必须引用已审剧本对应场次/动作说明中实际存在的逐字时间证据；无依据的时序只能标 `unstated`，不得自行编出“几年前/同时发生”。**证明原文包含这段文字不等于人已判断语义正确；真实媒体验证另行验收。

该计划已作为 QO-D02 可选输入，经原单集导演入口 `screenplay_series_delivery.episode_director_request` 实际进入 `director_brief`，并随新版 shot ID 重启原10岗位工单，镜头加入 `montage_membership`，导演整体底稿加入 `director_editorial_montage`。仅记录剪辑计划，不代表真正视频制作、音画同步或专业盲评完成。QO-D09 仍处工程验证中，不得因绿色 CI 自称国际一流。原质量总账不新增重复 issue 编号。

---

## QO-D19｜对白逐句声画时间轴（2026-10-13，程序实施中）

**质量编号不得混用**：原 QO-D03 始终是“导演视听母题、情绪弧线与视觉叙事”；带对白反打与声音cue新问题编号为 **QO-D19**，质量总账40项，仍属于 `in_progress`，不得宣称艺术验收完成。

在 QO-D02 已审定来源映射及导演自主镜头覆盖基础上，新增 [director_speech_cues.py](director_speech_cues.py) 维护独立于画面shot的原文、说话者、音频区间及逐句字幕cue。仅凭可校验的 `speech_cue_timeline`，`director_shot_coverage.py` 才允许将原本有对白/旁白/字幕的beat拆成多个视觉镜头，声音跨镜用cue引用绑定而非重复制台词；任何无cue、改写、漏条、错语者、非法时间均拒绝。原有10岗位工单从修改后的镜头重新创建，旧工单不得复用。timed cue是**计划的时间假设**，不是检测过的实际录音、口型、语音或字幕视频；需要独立合成器读取新cue ledger和真实媒体验证。绝不能把 legacy shot字幕字段当成精准合成证明。

导演创作必须围绕人物关系、隐藏意图、观众注意力与情绪变化，比较长镜头、反打和反应插镜的艺术得失，不可机械增加剪切；严肃题材可完全不用反打，荒诞与周星驰方法仅按故事实际需求启用。

[QO-D19技术与验收计划](quality-optimization/QO-D19_DIALOGUE_AUDIOVISUAL_CUE_SPEC.md)；核心代码 [director_speech_cues.py](director_speech_cues.py)；相关回归 [test_director_speech_cues.py](tests/test_director_speech_cues.py)。

---

## QO-D02｜总导演有权重构镜头，而非被编剧节拍数量锁死

导演接收**已审定的制作版**完整剧本及各场详述，完成自主≤90秒分集后，必须先判断每个关键事件应如何被演员行动、摄影空间、声音/静默和剪辑承载。编剧 beat/段落是来源与戏剧事件，不等于导演必拍摄的 shot。新 [Skill12](skills/12-director-shot-coverage.md) 与 [director_shot_coverage.py](director_shot_coverage.py) 允许**同一个无台词beat→多镜**或**同场景相邻多个beat→一个导演镜头**，并逐镜写明观众状态变化、时码、实际动作与导演理由。每个 source_span 严格覆盖已审制作版且保留原对白/旁白/事实/时长；**镜头结构变化必须重启原十角色专业工单，不能让旧摄影/配音指令串进新镜头**。逐句cue现有QO-D19结构化规划首版，但真实录音同步、多地点蒙太奇及真正专业盲评仍未完成，绝不能把此项宣布世界级艺术验收。文档：[QO-D02专业审计](quality-optimization/QO-D02_DIRECTOR_SHOT_COVERAGE_PROFESSIONAL_AUDIT.md)，质量追踪 QO-D02（in_progress）。

## QO-D17｜已经确定的导演艺术方法：思想情绪优先，周星驰只在喜剧需要时启用

用户已明确同意**作品思想和情绪表达效果高于纯视觉炫技**，要求学习国际导演的判断方法及其适用反例，增加周星驰荒诞喜剧艺术能力，正式升级同一个总导演模块。禁止把“周星驰风格”简化成搞怪BGM、夸张表情、随意塞梗、照搬著名台词或人物。周星驰本人职业访谈支持**故事结构为重，荒诞由人物愿望/期待偏差产生，笑与悲可并存，动作和视觉比解释性笑话更容易跨文化，制作复杂特技需与专业人员共同评估**。只有故事适合喜剧/荒诞时才开启相应方法；严肃科普、纪录、人物悲剧可以主动选择 `comic_mode=off`。

新的专业分集总导演顺序：先读编剧全本/详细说明并必要时改稿→确定每集≤90秒的正确权威版本→原 `director_brief` / `script_edit` / `director_lock` → 原七部门制作会 → **同一个导演的 `director_artistic_methods.request/validate` 独立艺术论证，选择适合本剧本的电影手法和人物/观众变化，明示不用的备选及代价** → 原 `director_visual_language` 绑定艺术方法摘要和具体声画交接 → 原专业各岗位接收完整、详细、可执行的本专业艺术理由 → QA及导演终审。正式新分集缺艺术方法或版本摘要不一致必须阻断，不用“文档上写了”当真实系统接通。原作者剧情/事实、成本、API、公开稿件及真实媒体审核边界全部不变。

依据：[Skill 11](skills/11-director-artistic-judgment-and-absurd-comedy.md)、[导演方法一手审计](quality-optimization/QO-D17_ARTISTIC_METHODOLOGY_AND_CHOW_COMEDY_AUDIT.md)。QO-D17及D03、D15尚缺独立实际作品审阅与真实媒体证据，不得以离线回归成功冒称世界级导演完成。

---

## QO-D03/D16｜导演独特的视觉/听觉语言和部门成果闭环

总导演不只是给部门讲“摄影优美、音乐感人”。必须通过已选版本场次中的实际动作/知识/人物抉择，解释每个镜头为什么用这种构图、表演、声音或沉默以及剪辑时机，具体观众状态如何转折，若被普通B-roll或提前切换将损失什么。通过 `director_visual_language` 在已存在的七部门 Skill09 会议后建立详细导演观众体验表达，并真正送入原专业岗位模型的消息。

总导演还必须接收各专业**实际已经提交**的工作，不能假装只有文字工单就已拍好。使用 `director_delivery_review` 对齐导演 vision / 实际交付 / 观众后果，逐部门逐镜仲裁冲突，调用原 `agent_team.request_revision` 指派一个具体责任部门、镜头及专业协作，触发下游版本失效；不重复全团队无差别重写。没有真实片段不声称真人审片或电影艺术已通过。

详细 Skill: [10](skills/10-director-audiovisual-meaning-and-review.md)。该阶段不会发模型、视频或产生费用，QO-D03/D16 仍未完成独立艺术验收。

---

## 2026-10-13 总导演统筹各专业部门（QO-D15）

**总导演是唯一的创意统筹者，不是仅审阅剧本或填视觉参数的人。** 导演需明确每集观众经历、戏剧/思想变化、重点镜头作用、声音/沉默/剪辑手段、画面/动作连续性，主动向表演、摄影美术、声音、剪辑动画、AI技术、独立QA及总导演终审分别说明**做什么、为什么、如何做、与谁交接、如何验收、失败怎样处理**，且解释每个真实 shot 的独特叙事任务。它们必须收到此具体指令，而不是只收到通用岗位模板。

新系列执行顺序：完整审阅的剧本/导演剪辑版 → ≤90秒每集 → `director_brief` → `script_edit` → `director_lock` → **`director_department_command` 制作会** → 各专业岗位执行 → QA → 导演终审。新分集模式没有制作会则不可派发后续部门模型工单；原有十任务 DAG 不变。制作会不等于已做出视频、真人批准或艺术过关。相关规范：[Skill 09](skills/09-director-department-command.md) / [专业一手审计](quality-optimization/QO-D15_DIRECTOR_DEPARTMENT_COMMAND_AUDIT.md)。与 QO-D02 真实镜头解耦、QO-D03 电影语言研究分别并行，不得互相冒充完成。

---

## 2026-10-13 用户明确的两条新硬性约束

**编剧**：必须交付详尽、可直接供总导演理解的完整分场剧本和逐场/逐节拍叙事说明（含环境、动作因果、人物反应、思想/情绪变化、对白/旁白意图、道具连续性）；但不决定摄影机位、焦距和生成提示词。可写10分钟或更长原始剧本，不能按90秒截断故事。

**导演**：收到全部剧本和详细说明之后，按观众体验、自然断点和连续性自主决定分成几集；**每集不超过90秒**，包括任何片头/回顾/结尾/可选最后1–2秒证据页；不是全部剧本限90秒，也不是只允许上下或上中下三集。超长剧本禁止走旧单集导演入口；**导演可以认为原稿太长/平庸，先利用 director_creative_cut 主动提出不同长度剪辑版（可以600秒故事经专业压缩成3集），逐beat记录删/留/压缩理由和观众可能损失。结构性删改经编剧重写/独立审读成为新的权威母稿后**，再为每集重启原有专业团队。不能默改历史稿/事实，不能以更短自动等于更好。质量记录：QO-W11 / QO-D13；“情感思想共鸣还不够深”属于 QO-W03 进一步提升，不能靠空泛煽情掩盖。

---

## 首要执行顺序修正（QO-W01 深度专业原始资料审计）

**先深入阅读国际职业编剧/导演的一手指南、公开完整讲座和访谈，并如实区分「真正读到全文」与「只取得官方课程大纲」；再对照真实代码与剧本，查出创作方法的因果缺陷，提出可作品盲评的改善方案；最后才优化提示词/代码。** 专业审稿优先于机械字段或 source-ID 的覆盖率；合理删减重排是编剧创作，不应被追溯门禁压制。[QO-W01 深读审计](quality-optimization/QO-W01_PROFESSIONAL_PRIMARY_SOURCE_AUDIT.md)。现有 PR #24 未完成职业方法验证，保持 Draft。

# 当前最高优先指令｜专业质量优化阶段（2026-10-13）

用户明确要求：**每个部门都以国际优秀职业标准为质量目标，但成果必须适合 AI 视频短片，不照搬一两个小时长片的工业组织和固定时长。** 现阶段只深入优化 **前置编剧与总导演**；其它表演、摄影、美术、声音、剪辑动画、AI 技术、场记 QA、API、审片与最终合成部门先登记 `audit_pending`，未来逐一按相同标准审计。

本项目**独立质量总账（唯一 QO 状态权威）**：
- [质量阶段不可变总纲](quality-optimization/QUALITY_CHARTER.md)
- [逐问题解决方案、优先级、状态和验收条件](quality-optimization/QUALITY_ISSUES.md)
- [具体执行批次与每轮 PR 的验收产物](quality-optimization/EXECUTION_PLAN.md)
- [机器权威登记](quality-optimization/QUALITY_ISSUES.json)
- [状态校验门禁](quality-optimization/quality_registry.py)

**所有后续改动必须先定位 QO 编号，逐项调查根因、实现、用合成案例和独立专业审核验证，有真实音画需要时另外获授权实测，再在 JSON 的对应问题上写实证并标完成，同时同步 Markdown。未解决保持 open/partial/blocked；禁止靠代码绿色宣布电影艺术达到国际一流。** 不可删除旧问题或其他部门的待审标记。旧 `AUDIT_FINDINGS.json` 和 AUD-002 私有账本/授权问题仍独立有效，禁止借新总账关闭。

AI 视频专属要求：编剧场次 ≠ 导演分镜 ≠ 模型生成片段，模型时长、原生配音、多模态参考与多镜能力必须按真实供应商/版本约束；没有用户原文资料不得加证据页；真实费用及私稿上传必须单独授权。坚持现有专业团队分工，不因为目标一流而任意增加 Agent。

**若本文件后面的历史阶段优先级与本节不一致，以这节和质量总纲为准。**

---

## 单镜流程已接入统一命令入口（2026-10-12）

[video_workflow.py](video_workflow.py) 已由 local_director.py 的 video 子入口调用，提供离线prepare/status/page/review-template/review与明确submit/query/download。只读页面不是网页控制台；尚无部署或真实生成。审片绑定准确视频SHA，候选保留不能冒充正式生产批准；意见要求修改不自动付费重做。API Key仅由明确网络命令从不回显交互终端读取，不能写参数、环境自动读取或存入任务。现有长期私有运行、真实授权/费用核验边界继续有效。详见 [单镜操作](SINGLE_SHOT_WORKFLOW.md)。

## 当前最高产品目标：API 制作路线（2026-10-12）

用户明确同意“文案 → 完整导演设计 → 第三方视频 API → 视频回收 → 审片返工 → 合成”。以 [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md)、[SEEDANCE_API_AUDIT.md](SEEDANCE_API_AUDIT.md) 和当前计划为准。以下历史“只交图纸/不直接生成视频”是旧阶段边界，不能再当成产品终点；付费、私人运行和发布仍须对应的真实授权。

本轮实现单镜 Seedance 适配函数，尚未挂接自动执行器、UI 或长期私有运行服务。默认只离线编译，不自动读取 Key、重试 POST、下载或生成视频。原生对白必须明确 onscreen_dialogue/offscreen_dialogue；制作包和后期单保留完整 speech。不存在真实媒体证据时，不能宣称生成质量、口型、身份一致性、最终成片或人审已经通过。优先验证 S02 单镜，再衔接 S02/S03，不扩张通用 Agent 框架。

## 对白样例与正常表演用语（2026-10-12）

[《先吃饭》48秒对白样例](examples/dinner-dialogue-review/director_workbook.md)已补齐VO、画外/出镜对白、字幕与口型交接；均未录音/生成/人审。AUD-026修复“等待”被占位规则误拦，见 [DIRECTOR_DIALOGUE_REVIEW.md](DIRECTOR_DIALOGUE_REVIEW.md)。累计26项，13项回归修复，原生产P0仍开放。不得靠删掉正常中文来让样例过检，也不得将时间线sync_dialogue字段等同所有对白都要口型；按明确声画设计交付。无新增付费授权。

# 当前任务顺序：先完成导演交付，再扩张外围（2026-10-12（新西兰时间））

用户已同意将开发重心拉回“文案 → 完整导演制作方案”。当前执行 [PRODUCT_REVIEW_PLAN.md](PRODUCT_REVIEW_PLAN.md)，先看 [60 秒完整样例](examples/door-letter-review/director_workbook.md)。

1. 优先交付/修订具体作品的故事、表演动作、摄影美术、声音台词、动画、剪辑与制作工单；保留已有专业团队分工，不新增执行框架。
2. 暂缓与当前作品无直接关系的编排、素材平台、账本和覆盖率扩张；已确认的数据泄露、误扣费、结果丢失等缺陷仍处理。
3. AUD-002/Issue #1 等现有生产风险不关闭。它们继续约束真实付费执行，但不阻断公开虚构文案的文字导演创作、审阅与离线编译。
4. 本轮样例为当前会话助手创作、现有编译器校验的候选；不能称为十岗位 DeepSeek 实测、人工批准或媒体生成成功。字段完整不等于作品好看。
5. 整理文档与创作样例直接复用已有模块；真正修改运行实现或引入新依赖时，再按既有 GitHub 成熟方案优先规则研究。不要为了写样例而新增框架/测试平台。
6. GitHub-only、保护私稿、不碰 Mac、无新增付费调用等边界持续有效。

以下保留历史技术记录。较旧的“最高优先级”“下一阶段”等排期如与本节冲突，以本节为准；具体实现约束和未解决问题仍有效。

---

## 私有恢复安全后续约束（AUD-023/024/025）

- 参见 [PRIVATE_RESULT_CHECKPOINT_RECOVERY.md](PRIVATE_RESULT_CHECKPOINT_RECOVERY.md)。`reserve` 与 `finish` 的持久写入异常都必须 poison 当前会话；恢复前必须逐个验证前序状态链接与用量/预留一致性，不能通过重新请求模型恢复。
- 新增7个合成回归；问题登记现为25项。AUD-002的长期可信私有存储/备份、身份与供应商账单验收仍未完成，Issue #1不关闭。SHA不能当成身份认证。

## AUD-022 图片完整解码保护（2026-10-11，已获 GitHub CI 证据）

- 已修复文件魔数能伪造图片有效性的 P1 缺陷：`asset_reference_manifest.py` 使用固定 Pillow==12.3.0、私有内存完整 `Image.verify()+Image.load()`；缺少解码器/危险宽松配置/伪造图片/截断/过大像素/多帧图片均不可直接登记。合成素材不含私人图片与 URL。
- [GitHub Actions 38120478073](https://github.com/pyzz58/gpt-recommendations/actions/runs/38120478073) 全部 564 测试通过；仅修解码能力，不代表已做到身份匹配、权限审核、私有原图长期存储、模型视觉输入或视频成片验证；Issue #2 持续 OPEN。
- 对解码复杂恶意图像仍需将来私有进程沙箱和 CVE/供应链审核。现在不部署 Mac、不上传真实文件、不请求付费 API。

## 全链路深入审计为后续开发默认流程（2026-10-11，用户明确授权）

- **AUD-002 离线缓解已落地，生产 P0 仍未关闭**：参见 [PRIVATE_RESULT_CHECKPOINT_RECOVERY.md](PRIVATE_RESULT_CHECKPOINT_RECOVERY.md)。真实 DeepSeek HTTP 调用现在必须携带非 Git 工作树的 0700 私有 Vault；先持久保存完整、已验证的 0600 team 创作状态，再将账本标记 accepted。出故障只支持已存储结果的人工**零网络**恢复；长期私人存储/真人身份核验/费用核账尚未部署，公开临时 GitHub runner 不算生产持久。
- **权威主账**：[DEEP_AUDIT_MASTER.md](DEEP_AUDIT_MASTER.md)（12 条并行审计线、开源复用评估、阻断门禁），[AUDIT_FINDINGS.json](AUDIT_FINDINGS.json)（目前 25 项编号 AUD-xxx、已修/确认/待调查/无媒体无法验证四类状态），[audit_registry.py](audit_registry.py)（每次 GitHub CI 校验，不允许无回归证据标“已解决”）；最高优先级 [GitHub Issue #1](https://github.com/pyzz58/gpt-recommendations/issues/1) 仍是**真实付费模型回复与私人创意结果持久化/崩溃恢复**。
- **开发必须先诊断、后修复**：记录可复现证据、来源版本、owner/影响、回归用例、GitHub 成熟项目/许可证/供应链/引入成本，优先最小融合；验证至少完整合成 CI + 对应故障注入。真实视频/用户稿/费用依旧没有新的授权，不能写“实机验收”。
- **已融合成熟开源**：GitHub CI 使用 [coveragepy/coveragepy](https://github.com/coveragepy/coveragepy) Apache-2.0 的 `coverage==7.16.1` 测 21 核心模块 statement+branch，发布临时公开报告；首次 494 测试总覆盖 83%，最低几个重要模块需补回归。账本 `PilotJournal.finish` 失败后回滚+锁死继续请求，防止未知扣费重放。没有安装到用户 Mac，也不调用额外 DeepSeek。
- [GITHUB_REUSE_POLICY.md](GITHUB_REUSE_POLICY.md) 继续优先：CineCrew FilmDSL（研究代码的可复用模型）、LangGraph（持久恢复）、jsonschema（格式验证），但**未实际完整引入**以上大型框架，先验证许可、版本、复杂度和私稿/费用安全。

## AUD-008/009 正式 Schema 验收（2026-10-11）

- 完整证据：[RUNTIME_SCHEMA_AND_PROMPT_TRUST_AUDIT.md](RUNTIME_SCHEMA_AND_PROMPT_TRUST_AUDIT.md)；真实模型文本输出不再只“提示应该遵守 Schema”。CI/受信任运行环境需安装 [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) MIT 稳定 tag `v4.25.1`，固定于 `requirements-schema.txt`；如缺依赖/Schema 无效，**在 reserve/付费 API 发送前拒绝**。
- `role_schema_guard.py` 在正文专业校验之外执行模型收到的同一 Draft 2020-12 Schema：固定静态错误号、不输出私人字段值、禁止远程 `$ref`、逐镜扩展 storyboard_pitch 也严格执行。继续保留原文 hash、部门字段所有权、导演/摄影视觉和灯光硬约束。首次完成十角色合成验证，不代表真实模型语义可靠。
- [AUD-009 Issue #5](https://github.com/pyzz58/gpt-recommendations/issues/5) 保持 OPEN：原文 JSON 封装及假冒 system/tool 消息只证明传输结构没有越权，**不能证明模型完全抵御 Prompt Injection**；新实机攻防须另外授权，不复用此前临时 Key。

## AUD-003 CineCrew FilmDSL 连续性子模块（2026-10-11）

- [FILMDSL_CONTINUITY_AUDIT.md](FILMDSL_CONTINUITY_AUDIT.md) 记录实际融合选择和未验证边界：借鉴 [Ironieser/CineCrew](https://github.com/Ironieser/CineCrew) Apache-2.0 README 里 `D={meta,assets,memory,clips[]}` 的资产/镜头状态思想，但**没有复制源码或迁移其完整框架**。
- `film_continuity.py` 建立来源绑定 `characters/props/scenes` ID 表。源没有声明人物/道具，绝不可从 AI 想象自动补全；镜内状态变化必须声明事件、时间和因果，跨镜突然换装或道具移动是 blocker，画外跳转仅为待人工验证的 review。
- 已接通锁定来源的 `acting` 岗位真实输出 Schema、局部返工合并、独立 QA 与最终制作工作包；无媒体参考图时始终 `reference_media_verified=false`、`production_ready=false`。Issue #2 仍 OPEN：参考图和真实视觉身份验证未完成，不能用字符串状态一致冒充画面成功。

## AUD-021：同一角色多角度与服化参考不能相互覆盖

- `asset_reference_manifest.py` 现在为 v2：`shot_slot_bindings` 逐镜绑定 `identity_front`、`identity_side`、`wardrobe`；旧 `shot_bindings` 保留一个 primary，但**不得因追加服装隐式替换已选脸部参考**。
- 每个独立槽位都校验实体、类型、文件哈希、当前版本，任何过期引用 fail-closed；`reference_switches` 记录跨镜换装/换脸待人审。角色、摄影、QA 的消息与最终逐镜工作单仅携带版本+哈希元数据，不携带原图字节、路径或外部 URL。v1 快照不可静默视为 v2，具体见 [REFERENCE_ASSET_VERSIONING_AUDIT.md](REFERENCE_ASSET_VERSIONING_AUDIT.md)。
- 该子模块为离线结构验收，不能把 sha 相等视作观众所见脸部一致。AUD-003 主 Issue #2 仍 OPEN。

## 私有参考资产 ID / 图片版本锁定（AUD-020，2026-10-11）

- [REFERENCE_ASSET_VERSIONING_AUDIT.md](REFERENCE_ASSET_VERSIONING_AUDIT.md)：FilmDSL 角色/道具/场景的稳定 ID 已扩展为参考资产卡 `asset_reference_manifest.py`，使用 SHA-256、不可覆盖版本链与逐镜 `asset_id/version/hash` 绑定。旧版引用会失效，模型不得通过变更参考图版本绕过已锁定的团队状态。
- `editorial_review_lock.attach_reference_manifest` 仅生成**私人新版本**规划快照，必须在新的十岗位执行前提交；`agent_live_crew.inspect_locked_role` 和 `production_delivery` 校验相同 digest。给岗位的是 metadata，不是实际照片；所有许可、肖像同意、真人审核、图像身份验证都保持 False，禁止宣称图片已生成或已获权利许可。
- 图片字节只在未来可信私人运行环境用于哈希校验，**不进公开 GitHub、CI 制品、原文提示词日志、AI 模型消息和最终工单**。本轮仅合成 CI，具体未部署长期私人媒体仓库；AUD-003/Issue #2 保持 OPEN。

# 当前开发模式：仅 GitHub 远程开发（2026-10-11 用户明确决定，最高优先级）

**自本条决定起，项目仅在 GitHub 仓库开发，直到用户明确发出“可以开始本地运行/部署”的新指令。任何较旧的“先在 Mac 执行”“让 Codex 在 Downloads 目录修改”“运行 git pull / 本地测试 / 打包”的建议，当前全部暂停。**

1. **唯一受控源码**：`pyzz58/gpt-recommendations` 仓库内 `短视频/ai-director/`。通过 GitHub 代码连接直接修改、提交和审查源码、配置、测试、文档；优先保持一条清晰主线，不未经允许创建分散副本。现有 Mac 下载目录中的历史副本**不再同步、不要求用户运行命令、不删除、不覆盖、不重构或搬迁**。
2. **开发方式**：先核查 2–3 个 GitHub 成熟开源候选的真实源码、最近维护、License、依赖、API、Mac/中国环境兼容；优先合规复用现成能力，必要时薄适配；记录采纳理由、所需许可声明和回滚策略。不能把“看过项目”说成“已融合运行”。
3. **只能使用非敏感开发素材**：仓库已公开，绝不提交用户真实文案、真实 `jobs/`、私人分镜、API Key、环境变量、费用账本、截图、导出影像、个人文件夹路径或从用户 Mac 才能访问的项目文件。用合成数据、公开示例和脱敏测试替代；不能假装能够远程读取 Mac 本地文件。
4. **测试方式**：优先静态检查、纯代码离线单元测试、现有 GitHub CI（在允许时）和非付费模拟服务；测试报告必须注明在何环境真实执行。可以在隔离开发沙箱验证临时源码，但不触达用户本地。**不发起 DeepSeek/视频等付费模型调用，不接入外部个人服务，不增加 GitHub Actions 费用或运行未经核查的第三方工作流**。
5. **目前只做开发，不做部署**：不得要求用户 `git pull`、运行本地 Codex、输入 API Key、安装依赖、克隆仓库、下载 ZIP 或模型权重，不编辑/迁移/清理现有 Mac 项目，不自动发布作品。旧 README 中的本地操作是**未来运行说明**，当前不得当作执行步骤。
6. **上线/本地部署闸门**：只有用户明确说开始本地运行/部署时，才审查并整理单一发布版本：锁定依赖和版本、校验许可/安全、全套无付费回归、自检文档、明确区分“程序可运行”和“实际视频生产已经验证”；之后再提供一次性部署/同步步骤。**不要把用户只是同意修某个功能解释为放行本地部署**。
7. 持续更新 `GITHUB_ONLY_DEVELOPMENT.md` 与 `GITHUB_REUSE_POLICY.md`。有外部开源项目直接合并前必须核实版权要求、许可证兼容与安全风险；禁止直接搬运 GPL 源码进入不兼容项目。

## DeepSeek 实测后的原始导演意图保护与制作参数修复（2026-10-11）

- 详见 [REAL_CREATIVE_TO_PRODUCTION_REPAIR.md](REAL_CREATIVE_TO_PRODUCTION_REPAIR.md)。真实公共虚构稿《门后的信》run 38115310358 发现：6 个 ai_video 镜头沿用 camera `postproduction/n/a`，角色 ID、房间物理布局和道具仍是图卡模板，S07→S08 黑暗与门缝光缺少可核对的物理桥接。不是已经生成可拍摄影片。
- `creative_production_handoff.py` 将第一轮 `editorial_concept` 绑定 source/plan digest 并写入 **仅私有** planning snapshot；`editorial_review_lock.stage_locked_team` 缺少/篡改该创意时拒绝；十岗位真实调用提示词继续携带原始导演设计和待办，不让导演在 v0.1→team 重启时丢掉真实创作。
- `camera_art`（仅来源绑定的锁定专业团队）严格要求：AI 视频镜头 `shot_size`、14–135mm `focal_length_mm`、`screen_axis`；所有镜头灯光状态、实际来源、变化原因；AI 视频同一场景要提供完全一致的 `scene_geometry`。静态/黑场可声明图卡/后期，不假造视频工作。错误参数、移动门/桌、灯态变化仍说未变，结构性审查拒绝该岗位结果。
- 生产编译包保留 `first_director_editor_vision` 和 provenance，在原导演构想与后续逐镜工单之间有证据链；无真实演员参考、光源勘查、视频试拍时仍不得声称生产就绪。此次 GitHub CI **全部离线**，不含原始私人稿件，不重复使用临时密钥。

## DeepSeek V4.1 Flash 真实创作小样的预检与评分标准（2026-10-11）

- 参考 [REAL_DEEPSEEK_CREATIVE_PILOT.md](REAL_DEEPSEEK_CREATIVE_PILOT.md)：首轮仅计划总导演 + 剧本编辑两次模型请求，使用**公开虚构「门后的信」**，并按原创故事钩子、表演/摄影细节、剪辑音效、原文忠实、视频模型可执行性等维度，人工评分 100 分；格式合格不等于艺术质量合格。
- `live_pilot_readiness.py` / `tests/test_live_pilot_readiness.py`：依据 2026-10-11 DeepSeek 官方峰时定价（Flash 未命中输入 ¥2/百万、输出 ¥8/百万、命中 ¥0.04/百万），在**不联网**的情况下估算首岗位待预留费用，并标记第二岗须等总导演实际返回后再估。CLI 只接受内置公共虚构素材，不能接受任何真实文案或 API Key。
- 第一次真实请求需要可信私人执行环境、明确的逐次允许传输范围、人民币费用额度、授权 API 账户/独立防泄露 key 和供应商账单对账。**聊天里“同意继续”不自动触发真实 API**。公开 GitHub Actions 永远只能运行离线 preflight / synthetic 演示，不得发送用户稿件、使用生产密钥或声称完成实机评测。

## 首次可检查的全链路纵向示范（2026-10-11，公开虚构素材）

- [END_TO_END_SYNTHETIC_ACCEPTANCE.md](END_TO_END_SYNTHETIC_ACCEPTANCE.md) / `offline_vertical_demo.py` / `tests/test_offline_vertical_demo.py`：首次把文章入组、总导演/剧本编辑、规划锁定、十阶段专业交接、独立 QA、`production_delivery.build_locked_crew_delivery` **真实生产编译器**全部串联。使用公开虚构“桌上信封”，十个岗位响应均是预写静态 JSON，**不是 DeepSeek 真实创作**。
- 对结果新增混合媒介强约束：必须既有 `ai_video` 镜头（各含 Wan/Seedance 候选提示词），又有无需视频生成的后期图卡镜头；不能十阶段任务均完成却没有可验证视频工单。当前合成演示为 4 镜头：2 AI 视频 / 2 后期。源稿/锁定版本改变必须拒绝导出。
- GitHub Actions 使用 `--synthetic-only` 在临时目录生成 JSON、Markdown、QA 证据并作为明确标注 SYNTHETIC-NOT-REAL-AI 的**公共示范 artifact**供人下载审阅。不得用真实《上学以后的孩子》或任何用户私稿运行、上传公共 CI。仍无真实 API 调用、私人传输、真实费用、媒体生成或已确认的人类导演审批。

## 十专业岗位 DeepSeek 单次授权调用已接入锁定分镜（2026-10-11）

- 新增 [DEEPSEEK_TEN_ROLE_LOCKED_PILOT.md](DEEPSEEK_TEN_ROLE_LOCKED_PILOT.md)、`agent_live_crew.py`、`tests/test_agent_live_crew.py`。共享已有 `agent_live_pilot` 的固定 TLS、真实费用预留 journal，**不是重新设计 10 个 Agent**。
- `inspect_locked_role` 严格校验 `editorial_review_lock` 的单集原文、锁定计划 SHA256、当前状态、DAG ready 和任务版本。 `run_one_locked_role` 只处理一岗；每次都要明确的 role+revision 逐岗位隐私及预算批准，绝不连续自动运行、跳过前置任务、自动重试。
- 后续表演、摄影、美术、声音、剪辑、AI 技术、独立 QA 与总导演终审全部接入现有专业 `roles.build_role_messages` / `roles.submit_role_output`。终审 `ready_for_user_review` 受独立 handoff/创意 QA 硬阻断，只表示送人类看，绝不等于批准或发布；所有结果仍待真实模型内容质量与影音实机验证。
- 旧 `run_one_creative_task` 仍**严格只允许**最初两个未锁定创意岗位，后续锁定团队必须使用新入口，避免混用 base。测试只用虚构信封故事的离线返回、无私人原稿网络传输、无扣费、无 Mac 部署。

## DeepSeek 真正 HTTPS 单岗位试验入口（2026-10-11；当前未经任何真实调用授权）

- [DEEPSEEK_SINGLE_TASK_PILOT.md](DEEPSEEK_SINGLE_TASK_PILOT.md) / `agent_live_pilot.py` 复用现有 DeepSeek 请求/回复协议、总导演和剧本编辑专业创作合约、同一任务账本；本模块首次包含**真实 HTTPS 客户端代码**，但没有自动执行入口、命令行入口、自动加载 API Key 或自动向 DeepSeek 发送真实稿件。
- `run_one_creative_task` 只处理**一个**选中的正式岗位：`director_brief` 或 `script_edit`。未来必须有可信私有系统完成**逐次**真实用户批准、模型、单集原文传输、费用上限及 key 管理；`explicit_pilot_permit` 只是软件内部的意图结构，不能替代身份认证或真实授权。用户说“继续开发”仅同意研发，不提供这类授权。
- 独立 `PilotJournal` 在可能收费的 POST **之前**完成持久排他锁/0600/原子费用预留；不保留文案、私钥或完整模型输出。连接超时/供应商拒绝/不完整 JSON/账单估算超额度须 fail closed、禁止自动重试和静默退款。token 预留系估算，实际供应商账单不能保证绝对小于配置上限。
- CI 只使用 `StaticHTTPSFrame` 合成返回与 mock HTTPS socket，零联网/零收费；正常 `agent_executor`、`agent_durable_preflight` 和现有 GitHub Actions 均保持离线。不得在公仓部署私人现场试验或把真实稿件提交 CI。

## AI 视频制作工单离线导出与专业 DAG 全链路校验（2026-10-11）

- 新增 [PRODUCTION_DELIVERY_PACK.md](PRODUCTION_DELIVERY_PACK.md)、`production_delivery.py` 和 `tests/test_production_delivery.py`。复用 `director_v2.compile_package` 与 `director_workbook.compile_workbook` 将现有专业导演工作单编译成逐镜 Wan/Seedance 视频候选提示词、动作/运镜/灯光/旁白/声音、字幕数据图表后期工单、整片剪辑时间表和跨镜头承接。
- 非 `ai_video` 路线必须只有后期任务，不能假装视频模型直接生成准确汉字/数字。AI 提示词只能作为候选人工复制；缺参考资产、供应商能力、研究事实核验和人工视频验收，状态固定为 `offline_operator_review_workbook_not_model_ready`；不启用付费模型、下载/同步 Mac 或发布。
- 开发演示 `build_reference_delivery` 只接受项目已有公开专业 v0.2 示例，**不冒充本轮十岗位真实执行**；`build_locked_crew_delivery` 则要求规划锁定原文和计划 hash、十阶段全部完成、独立 QA、总导演终审后重新验收才能生成工作单，不能从伪造/不完整团队取得「完成」状态。
- 仅使用仓库既有公开示例 + 虚构专业角色数据进行 GitHub CI 验收。任何输出 Markdown/JSON 都可能包含私密原稿，禁止公开导出真人文案。

## 逐镜审阅、返工和版本锁定（2026-10-11；仍未真人批准）

- 本轮新增 [EDITORIAL_REVIEW_AND_LOCK.md](EDITORIAL_REVIEW_AND_LOCK.md)、`editorial_review_lock.py`、`tests/test_editorial_review_lock.py`。针对创意导演提案提供全部镜头、原文删减、待核验事实及全部待改稿建议的精确审阅表；每个具体分镜均绑定 SHA-256，遗漏、换版本、换原稿、请求返工或拒绝即不允许锁定。
- `lock_planning_snapshot` **只是离线规划版本快照**（`planning_locked_identity_unverified`）。没有可信用户身份验证、付款/素材传输同意、安全签名或供应商账单授权；必须由未来私有后台额外确认。纯 JSON 中的“保留”选择不是作者已经实际同意的证明，不能以此运行付费模型。
- `stage_locked_team` 重建绑定锁定 base/source 指纹的新十阶段账本，状态明确为 `offline_planning_only_not_authorized_to_dispatch`。所有真人审批、真实模型费用、影片生成与发布标志始终 False。
- 仅以虚构信封故事合成审阅单测试；用户提供的《上学以后的孩子》不得写入公开 GitHub、CI、导出示例或其他第三方。

## 长文章导演与剧本编辑的创意分镜方案（2026-10-11，离线研发）

- 阅读 [EDITORIAL_CREATIVE_BRIDGE.md](EDITORIAL_CREATIVE_BRIDGE.md)，模块 `editorial_storyboard.py` 将已有单集草案接入**现有**总导演 `director_brief` 与剧本编辑 `script_edit` 的正式任务、依赖版本、源稿哈希和标准岗位 JSON 验收。没有增加重复 Agent，没有真的调用 DeepSeek。
- `build_director_brief_request` 与 `build_script_editor_request` 生成待日后授权的专业创作请求。其中剧本编辑须附逐镜 `storyboard_pitch`（视觉目的、可观察动作、摄影与光线意图、文字后期、转场、逐字源引用）；`submit_creative_script_edit` 在入账前检查专业分镜完整度、事实源片段、数字叠字，不合格则原状态不变。
- `propose_directed_storyboard` 把合格创意落在**新候选**导演 v0.1 计划上，原旁白、时长和 claims 不改、不吞掉人工需批准的改稿建议。候选始终 `author_review_required`，不继承旧 DAG 账本哈希；另起新团队也始终 `pending_author_editorial_review`。它不代表已拍片、已人审或可以直接投喂视频模型。
- 只用虚构信封片段的预写 JSON 模拟接口，所有用户真实上传内容禁止写进公开 GitHub/CI，不授权付费服务或 Mac 部署。

## 长文章直入与可追溯分集（2026-10-11；真实文案严禁提交公开仓库）

- 本轮新增 [ARTICLE_TO_EPISODE_INTAKE.md](ARTICLE_TO_EPISODE_INTAKE.md)、`article_intake.py` 与 `tests/test_article_intake.py`，只使用合成长文案做自动化验证。按 `### 1.` 等标题拆分节目选题，选择某一集生成来源逐字可追溯、完全未审核的 v0.1 分镜草案，交由既有 `agent_team.start` 创建十阶段导演任务账本。
- `episode_catalog` 返回的标题和 `prepare_episode` 返回的计划也可能包含私人文案，**不得提交到 GitHub 或公用日志**；`episode_source_for_team` 只传选中集完整原文，不把其他 17 集无关内容混进每个专业 Agent。保留整篇文章和当前集各自独立 SHA256。
- 自动稿仅包含逐字截取的候选旁白与后期图卡占位，不等于有真实动作/摄影/剪辑/AI 视频模型 prompt。缺无声叙述、太长或证据问题，应明确 `needs_script_editor`、`omissions`、`claims.status=needs_review` 和各项人工审阅 flag；永远不自动标记 `ready_for_video_model`。
- 用户同意继续研发只授权合成数据测试和 GitHub 代码开发，不自动放行 DeepSeek 联网、付费调用、个人文案云端传输或 Mac 部署。

## 独立跨部门 QA、返工提案与交付硬门禁（当前研发要求）

- 参考 [CREW_QA_GATE.md](CREW_QA_GATE.md) 和 `agent_handoff_audit.py`。在原有岗位质量检查以外，独立核对原文配音守恒、真实动作节拍与剪辑切点、制作路线、音效/动作/摄影时间范围、图表论据及动画模式矛盾。
- `quality_review` 和 `director_final` 不得对确定性硬冲突判定通过；`compile_team_workbook(base,state)` 必须再次读取 base 做最终比对并阻断，不能直接将旧 QA 报告当作不可撤销批准。
- `propose_director_revisions` 只读产生按责任岗位和镜头归并的建议；只有明确总导演批准，`request_planned_revision` 才使用旧 `request_revision` 的定向 DAG 返工，保留已有无关岗位成果。流程布尔字段不等于身份认证、最终用户批准或模型费用许可。
- 老剧本缺完整专业交付允许明确标记为 `draft_needs_review` 的审阅草稿；`strict=True` 只能在文字制作蓝图、岗位证据及交接质量均满足门禁时返回供真人审片状态，绝不冒充已生成视频。
- 当前 GitHub-only，不触碰 Mac 和私人 jobs，无收费调用。测试代码不等于已运行通过；任何远端 CI 结果须以实际检查状态为准。

## DeepSeek 协议与可恢复费用预留（2026-10-11；仍禁止真实调用）

- 参阅 [PROVIDER_PROTOCOL_AND_DURABLE_BUDGET.md](PROVIDER_PROTOCOL_AND_DURABLE_BUDGET.md)，新增 `agent_provider_wire.py` 与 `agent_durable_preflight.py`。针对官方 `deepseek-flash` 的 Chat Completions 请求格式及 usage 缓存命中/未命中拆分、输出用量与响应内容编写**纯离线**协议校验；**没有发送 HTTP 的实现、没有读取密钥、没有任何收费调用**。
- `PrivateReservationJournal` 使用文件锁+fsync+原子替换实现离线 write-ahead 模拟预留；中断后的 pending / timeout / transport unknown、返回用量超过预留金额均阻断自动重试/继续。它**不是在线真实费用的绝对保障**，且没有实现与供应商发票对账。
- 唯一可执行的是精确 `OfflineResponseFrames` 的**合成 DeepSeek JSON**；禁止把本地测试、文档中 JSON 开关或“开始开发”理解成用户授权实际私人文案传输/调用 DeepSeek/部署 Mac。
- CI 只允许使用合成案例及临时目录；绝不可把生产日志、真人 `jobs/` 或 API Key 放入公开 GitHub / Actions 日志。

## 模型路由与 Token 预算预检（2026-10-11；仅模拟）

- 阅读 [MODEL_GATEWAY_AND_BUDGET.md](MODEL_GATEWAY_AND_BUDGET.md)、`agent_model_gateway.py` 和 `tests/test_agent_model_gateway.py`。针对现有 10 个岗位声明不同 provider/model、输入输出 Token 上限、CNY 单价、总模拟预算和总尝试次数；不会执行 HTTP/SDK/真实模型调用。
- `OfflineBudgetBook` 每次按 UTF-8 字节+安全余量**估计**输入代理量，再按声明单价预留最大输出费用；预留值不是供应商准确 Token、实际费用或用户付款授权。缺少报价/超限/未授权模型应阻断；费用配置中修改或伪造更低单次报价也要拒绝。
- 只允许精确 `OfflineMockTransport`，禁止替换为带网络的同名对象、动态回调或真实付费模型。已有 `llm_budget.py` 本地账本未接入本次流程，不能声称将来自动拥有跨进程持久消费上限。
- 全程 GitHub-only、合成测试，绝不传输用户文案，绝不改变之前的原文权限/导演 QA/人工批准/付费媒体门禁。

## 专业 Agent 创作合同与严格 JSON 验收（2026-10-11）

- 阅读 [PROFESSIONAL_AGENT_CONTRACTS.md](PROFESSIONAL_AGENT_CONTRACTS.md) 和 `agent_role_contracts.py`。为现有 10 个阶段提供**有区别的专业岗位创作指令**，输入仍由权威原文/plan、总导演圣经、岗位归属和依赖版本锁定。
- `build_role_messages` 仅在**私有内存**构建 system/user 文本与岗位动态 schema；包含私密原始文案、上游素材，不能保存为公开日志、提交 GitHub 或发送未经单独批准的提供商。
- `parse_strict_json` 拒绝多个 JSON、Markdown 围栏、重复键、非有限数值及过大响应；`validate_role_output` 校验可执行状态、准确镜头覆盖、专业字段内容、动作/声音时码、配音忠实原文、剪辑 beat 索引和合法技术路线，不得偷偷修复未通过的内容。
- 模型接口**仍未接入**；旧 `FixtureOnlyAdapter` 原样保留，不准把这层本地静态 prompt/validator 当成完成 AI 创作、付费调用、真人批准。未来真正模型接入需用户明确另行批准供应商、数据上传及预算。

## 多 Agent 模拟执行器（2026-10-11）

- 新增 [AGENT_EXECUTION_LAYER.md](AGENT_EXECUTION_LAYER.md) / `agent_executor.py`：十阶段连续处理由显式 `FixtureOnlyAdapter` 提供的预写 JSON 岗位交付，真实编排/版本/权限/QA/rework 规则生效，但**不调用任何 LLM**。不能把模拟交付叫作“8个 AI 已真正创作了电影方案”。
- `role_context` 只允许在将来经批准的私有运行环境暂时传递原始文案、基础分镜和上游交付；绝不可把这些请求对象、私人 fixtures 或执行后的 ledger 上传公开仓库。只读执行收据不包含原文。
- 无 fixture 即暂停；越权写入、源指纹不匹配、未备案模型适配器均阻断；QA 与总导演终审也要重新审核权威源稿。默认停止在总导演最终决定之前，`allow_fixture_director_final` 仅供模拟验收，不等于人审。
- **本阶段不得以任何方式调用付费模型/视频 API**，不得因为用户同意“继续”就视为授权收费、上传文案或部署 Mac。
- 新增测试详见文档；完整自动化回归以当前 GitHub CI 记录为准。测试通过证明离线机制，不证明创作质量。

## 新主架构：总导演统筹的专业 Agent 影视团队（最高优先级）

- **先阅读 [MULTI_AGENT_STUDIO.md](MULTI_AGENT_STUDIO.md)** 与 `agent_team.py`。产品入口仍为文案，产品输出仍为一份专业导演交付书；团队协作是内部生产方法，不增加用户需要管理的角色数量。
- **总导演 Showrunner 拥有导演圣经/剧情方案审定、逐镜 objective（emotion/observable_turn/visual_focus）与最终整合权**。剧本编辑提出源文案改写建议、动作导演管理 staging/performance/beats/continuity/shootability、摄影美术管理 camera/art、声音导演管理 sound/speech、剪辑动画管理 editing/animation/graphics、AI 技术导演管理 generation，QA 只读审查。负责人不能直接写其他部门的字段或修改原文。
- 第一版通过十阶段 DAG 发包：`director_brief → script_edit → director_lock → (acting,camera_art,sound) → editing_animation → ai_technical → quality_review → director_final`。动作/摄影/声音部门的整集任务允许并行准备；不要为每个镜头机械地完整调用全体 Agent。
- 每个专业交付必须带 `base_digest`、上游依赖版本、角色所属字段和受影响镜头范围；独立 QA 提出修改建议，只有总导演发起定向 `request_revision`，对受影响镜头与邻接剪辑重新派单，保留已通过的非相关部门成果及版本历史。
- **共享的权威原稿、人物和道具事实不可被岗位输出静默覆盖**；源稿修改属于须另行批准的提案。专业团队的完成状态不是用户最终批准。`agent_team.compile_team_workbook` 接入现有 `director_v2.validate` / `director_workbook.compile_workbook`，不得绕过已有的专业制作质量检查。
- **当前仅完成离线角色合同、任务派发、版本/权限/返工和工作单合并代码，并没有真的运行八个 AI。** 禁止为了自称“多 Agent”而直接发起收费 DeepSeek/视频接口或在 Mac 安装 CrewAI/LangGraph。后续模型适配、费用预算和部署需要用户另外明确授权。
- 公开 GitHub 只存合成示例和源代码，绝不上传用户文案、私人 jobs、真实素材。旧 `local_director` 保持兼容；只有完成自动协作回归与人审后才考虑替换其单体生成链。

## 真人动作可拍性与合理拆段（当前导演主线）

- 阅读 [SHOOTABILITY.md](SHOOTABILITY.md)。`director_shootability.py` 根据导演主动写出的 `shootability.action_units` 检查 actor_id、左右手、稳定道具 ID、所选 beat、秒数和可见动作结果；不从自然语言猜测真实模型能力、不自动生成素材。
- 有真人动作的 AI 视频镜头每个 `beats[]` 至少需要明确动作或姿势保持单元；同一只手时间重叠属硬冲突、两手合理并行允许；短于0.55秒的精细道具动作及2秒内至少3项道具操作只发风险提示，不假装视频模型一定失败。
- 如果选择 `mode=split_stitch`，必须以 `segments[]` 提供覆盖整个镜头的两段以上分段计划，每段指明 route 和 join_rule；高密度单镜若仍选择 single_take，必须给出可执行的 fallback。字段齐全不等于已试拍。
- `director_workbook.py` 增加 `shootability_review` / `shootability_structure_ready` / `shootability_blockers` / `shootability_pending` / `shootability_review_signals`。制作蓝图结构就绪必须包含动作拆解审查；单独的人工人审/费用授权/真正视频生成依然独立。
- 旧导演稿无动作单仍可输出带未完成项的草稿；不能为追求一次通过而把具体双手/道具动作粗暴写成一个“自然走动”。纯静态图表不必创造真人动作。
- 继续只在 GitHub 开发，既有 Mac 文件与私人故事 `jobs/` 不触及，所有付费模型禁用。

## 实际剪辑事件绑定与防模板化（导演主线加强）

- [NARRATIVE_HANDOFF.md](NARRATIVE_HANDOFF.md) 已新增 `editing.narrative_bridge.beat_link`：`outgoing_beat_index` 必须指向当前镜头最后一个实际动作节拍，`incoming_beat_index=0` 指向下一镜起始节拍，`cut_on_visible_event` 必须讲清具体可观察切点事件。审核器将真实 `visible_change` 加入 `cut_beat_evidence`，错误索引/不在切镜边界报阻断。
- 同一部片子若至少三次逐字重复观众问题、切点理由、动作/道具连接或后期方案，产生 `BOILERPLATE_DIRECTOR_REASON` 人工复核；不得把 `production_blueprint_ready` 标为 true。复制套话检测只是保守信号，不是自动审美打分，不应误判重复配色/字幕规范为缺陷。
- 现有旧导演稿无 `beat_link` 依然可以生成未完成草稿，但严格交接不能通过。自动导演指令应为每个相邻镜头引用其真实末/首节拍而非编造事件。
- 严守 GitHub-only：源码和合成测试可提交，不让用户本地 Codex 运行，不消耗 DeepSeek/视频模型预算。

## 跨镜头故事、情绪节奏及混合制作统一风格（导演主线）

- 阅读 [NARRATIVE_HANDOFF.md](NARRATIVE_HANDOFF.md)。`director_narrative_bridges.py` 把每对相邻镜头的切点理由、上一镜悬念/下一镜的回答、情绪速度、构图/视线/动作/道具关联，以及 AI 视频↔静态/剪辑/实拍切换时的调色和字幕等后期指令形成导演交接表。不能用空泛“自然过渡”或每镜复制同一套话。
- `editing.narrative_bridge` 由导演为**每个非末镜**明确创作，字段结构为四组 `cut_intention` / `emotion_pacing` / `visual_handoff` / `style_handoff`。旧导演方向文件缺此字段时仍可输出草稿，但 `narrative_handoff_ready=false`；不能谎称完成制作级导演蓝图。
- `director_review.production_blueprint_ready` 需要先有 `editor_handoff_ready` 且所有相邻镜头的叙事/视觉交接完整；严格 `director_workbook.py --strict` 以此为门禁。通过只是**文字导演方案的结构完整**，无法证明真实画面质量、人脸风格锁定、用户人工批准或 API 付费许可。
- 不随意强求相邻镜头同色/同构图：有动机的色彩、节奏反差可以被导演明确采用；制作方式变化可标 `motivated_contrast`。旧项目的连续性/成本/参考图库仍为**辅助工具**，不能挤占故事→导演交付书主线。

## 导演交付书质量闸门（具体创作优先）

- `director_workbook.compile_workbook` 产生 `director_review.creative_design_complete`（结构化导演内容无硬冲突）和 `director_review.editor_handoff_ready`（配音 cue、字幕 cue、动画关键帧、J/L 或明确 none 的声音交接决策具备时间轴）。两者不得混为一谈；人审状态始终独立。
- 严格 `director_workbook.py --strict` 要求 `editor_handoff_ready=true`，不再仅凭有字段便通过。旧档可看草稿，但预览首页必须显式显示创作缺项及剪辑交接缺项。
- 所有时间码相对镜头，转为绝对剪辑时间；中文配音密度以实际朗读窗口而非整镜长度为参照，作为人工审听提醒。字幕与旁白原文分别逐字守恒，不得悄悄改稿。
- 本轮仍只提交 GitHub 通用代码和合成测试。参考图/音视频未生成，用户 Mac 未部署，AI 模型未调用。

## 剪辑时间线与声画节奏质量（仅导演工作单）

- 详见 [EDITOR_TIMELINE.md](EDITOR_TIMELINE.md)。`director_timeline.py` 只将专业导演已写明的 beats、旁白 cue、出镜对白、音效、图层动画与镜头转场组合为绝对时间线，供 `director_workbook.py` 输出 `editor_decision_list`。不代表视频已剪辑或声音已完成。
- 每个语音 cue 需要准确 from_s/to_s 和原文字句，不能用模糊描述冒充声画同步；音效/动画越界必须报错，动画只有文字描述时保留待人工补充时间点。旁白字速是**人工提醒**，不能武断删除用户文案或虚构经演员试读。
- 现阶段不引入整个 OpenTimelineIO、视频模型或剪辑软件依赖。影片叙事/摄影/剪辑/动画/台词的实际创意质量优先于技术性资产检查；继续只在 GitHub 修改，未获授权禁止在 Mac 运行。

## 产品北极星：用户文案 → 完整 AI 短视频专业导演交付书（最高产品优先级）

- 先阅读 [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md)。本产品不是参考图库、素材平台、付费视频生成器或模型接口，而是专业的**文案到导演中间层**：提供剧情结构、动作表演、场景、摄影、剪辑、转场、动画、字幕、台词、旁白、BGM/音效及 AI 制作工单的完整导演设计。
- `director_workbook.py` 是主要交付编译器；它将已审查基础分镜和专业方向稿聚合为 `director_workbook.json` / `director_workbook.md`。用户必须能读到完整的逐镜头制作方案，而不只是原始 prompts。
- 所有镜头的 `editing`、`animation`、`speech` 为必备创意设计字段：没有动画时也必须明确写 `mode=none`，出镜对白与旁白必须严格区分，VO 不能被导演备注静默更改。旧稿可生成不完整草稿，但 `creative_design_complete=false`，不可谎称交付完成。
- 任何新模块必须说明它加强了导演交付书的哪一个实际栏目；资产管理、状态机、模型费用门禁都是辅助设施，禁止偏离剧本改编/摄影/剪辑/动画/声音主线。
- 尊重用户 GitHub-only 决定：只改远程公共源码和合成样本，不动 Mac、不上传真实文案，不调用 DeepSeek 或其他付费视频服务。

## 模型参考图输入预览（仅离线开发）

- 新模块 `reference_input_preview.py` 只把导演镜头与已登记资产转为供应商无关的参考需求清单；详见 [REFERENCE_INPUT_PREVIEW.md](REFERENCE_INPUT_PREVIEW.md)。
- 输出永远不得包含私有原始图片路径、图片字节、素材来源详情/授权合同、任何 API Key 或可发起模型调用的凭据；`actual_provider_request=false`、`images_uploaded=false`、`runtime_execution_allowed=false`。
- 不得把这份需求清单声称为 Wan/Seedance 的真实请求格式，不得以“目录 status=approved”推导已有传输授权或已验证生成效果。
- 新增供应商适配器前先核对官方 API 现行文档、版本、模型可接收的参考图角度数量、格式、授权和成本，并单独征求用户执行授权；当前 GitHub-only 不允许上传私人文件或调用付费服务。

## 生成前安全门禁（新增；优先级高）

- 阅读 [GENERATION_GATE.md](GENERATION_GATE.md)。`director_v2.compile_package()` 对每次编译输出附加 `generation_gate`：没有真实参考图核验、人工逐镜审批和交付媒体时，必须逐条显示阻断原因。
- `production_gate.py` 是**纯离线只读审查器**，不具备执行服务调用的能力。门禁输出 `execution_authorized=false`、`paid_api_enabled=false`、`publishing_authorized=false` 恒定不变；即使 `metadata_preflight_passed=true` 也**不是**付费或发布批准。
- 以后任何真正的视频/参考图模型适配器必须单独检查用户当次对供应商、模型、费用上限、次数和数据传输的明确授权。不能把可篡改的 JSON、`human_approved` 或本地测试通过当成付费授权。
- 保持 GitHub-only：禁止要求 Mac 同步、安装、部署、启动后台服务或提供私人素材。

## 参考资产库（新增；当前仅 GitHub 研发）

- 阅读 [REFERENCE_ASSETS.md](REFERENCE_ASSETS.md)、[schemas/reference_assets.schema.json](schemas/reference_assets.schema.json) 与 `reference_assets.py`；采用稳定人物 / 场景 / 道具 ID，按镜头显式登记参考角度。参考图片、面貌一致性与素材版权必须分别验证，不得混成一个“已锁定”布尔字段。
- 人物需要正面、四分之三侧面和全身参考视图；场景需要建立镜头；道具需要细节图。目录生成器默认全部 `not_created`，不得声称已有图，也不得从自然语言片段虚构文件路径。
- 完整连续性契约中登记的道具并不意味着每镜都入画：只将明确标注的 `generation.reference_bindings` 道具图加入镜头需求。
- 已批准参考图必须在未来私有资产根目录内、给出来源/授权核验依据、人工审核者和 SHA-256，并再次验证路径与哈希；这也不代表 AI 视频成片已锁脸、版权许可已完成专家审查或成功生成。没有清单的旧导演稿只允许离线规划，不标记图像可用。
- `reference_assets.py` 不生成图片、不复制用户私人素材、不上传 GitHub、不执行 AI 付费 API，不改变当前 GitHub-only/禁止本地安装的硬约束。

## 第三阶段制作路线（GitHub-only；最高技术优先级）

- 阅读 [PRODUCTION_ROUTING.md](PRODUCTION_ROUTING.md)；`base.visual_type` 代表概念镜头，不等同于实际素材来源。采用规范的 `generation.route`：`ai_video` / `static_post` / `edit_composite` / `live_action_insert` / `post_production`。
- 有明确 `production_method` 的旧导演档可用已支持别名兼容，编译结果以 `execution_route` 为准。未识别的制作方式必须失败并人工评估，禁止悄悄生成视频模型提示词。
- 只有 AI 视频镜头可以包含 Wan/Seedance 候选提示词，其余只输出 `postproduction_job`；不可自动发起任何生成/API 请求。保留完整 `production_summary` 和人工审核标记。
- `voiceover_note` 是导演备注，不是正式配音文稿变更。除非修改并审核 base 候选，不得悄悄替换 base.narration。视频参考图及版权未经核验时不得标已通过。

## 完整物理连续性契约（新增；旧剧本保持兼容）

- Codex 在修订既有分镜前必须阅读 [skills/06-continuity-repair.md](skills/06-continuity-repair.md) 和 [CONTINUITY_QA.md](CONTINUITY_QA.md)，并使用已审查的 GitHub 技术选型清单。
- 首选为全部主要道具与人物建立唯一ID、连续镜头 before/after 位置、顺序明确的 pickup/place/walk 事件。JSON Schema 在 schemas/continuity_contract.schema.json；本地按 continuity_contract.py 逐镜头回放。被声明 coverage=complete 的合同必须遍历每一镜（没出镜的道具也不能失踪）；验证失败阻断进入后续付费导演层。
- 不能只写结构化数据不改画面：visual、action、continuity 与状态迁移必须相互支持；只有 JSON 通过不等于实际 AI 画面可信。
- 生成修订先写 plan.proposed.json（不是原文件）；保留原计划、人物设定、已有费用账本、审核记录。未获新的明确资金批准，不允许付费修稿。
- 不要安装全局依赖：jsonschema 可在隔离环境作为可选 Schema 验证；transitions 仅评估，没有成为运行时依赖，CineCrew 是数据建模参考而不是整包接入。

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
- 2026-10-11 已对一次真实 API 测试明确批准人民币5元本地预留预算，先后成功生成过 series.json 和 plan.json；不等于完成 direction_v02.json 或视频制作验收。**该审批不是未来额外调用的通用授权**；必须逐次核对原任务账本、用户明确的次数和预算。保持 GitHub 为源码和测试仓库，用户明确要求不打包下载至最终验收。

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

- **当前多 Agent 调度从结构化 `plan.json` 开始**，尚未替换文案→基础分镜旧入口；有原始文本时可在任务状态只绑定 SHA-256、不上传正文。下一期要解决总导演先审原始文案并最终锁定可编辑的分镜来源；现在不许把该流程称为真实自动化模型团队。

