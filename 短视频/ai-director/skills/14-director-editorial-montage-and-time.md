# Skill 14｜导演跨场景蒙太奇与非线性时空剪辑（QO-D09）

状态：**首版结构化导演计划；不是实际成片或艺术验收**。本技能由原总导演执行，受 QO-D02 的物理镜头覆盖约束，并由 QO-D05（演员/道具/场景状态）、QO-D07（空间轴线/光色视觉）提供边界。不新建导演 Agent、不拆散原十专业岗位。

## 创作逻辑（先讲为什么，再设计如何剪）
1. 总导演读完整剧本及逐场笔记，确定蒙太奇承担什么思想、人物冲突或情绪功能。先提出“保持原场次顺序/单镜头”的克制备选；如果没有观看收益，不使用蒙太奇。
2. 区分编剧场次、导演的**单个物理镜头**、以及**多个物理镜头构成的后期剪辑序列**。跨地点是两个不同物理镜头的连接，不允许混为一镜。
3. 在转场前后分别写明观众已知的何事、此刻必须知道的地点和时间、以何种动作或声音作衔接、如何避免观众把刻意对照误解为同时发生。
4. 对倒叙、顺叙跳时、并行动作，交出来自**被审定剧本对应进入镜头的场次标题或动作说明**的逐字时间证据。没有这样的证据只能用 `unstated`，不得擅称“几年前”“同时发生”。程序只检查证据逐字属于剧本，时间关系语义仍须编剧/人类专业复核。
5. 导演逐剪口比较硬切、匹配剪切、叠化、声音桥与跳切，说明每种镜头变化如何引发观众认识或感受的变化；不能以“电影感/炫技”代替判断。
6. 以具体演员位置、道具状态、空间轴线、场景光源与声场进行首尾检查。任何 `continuous` 同场动作，公共演员/道具离开与进入状态必须吻合；不同编剧场次不可假装为无断点的一次连续机位移动。
7. 对 AI 生成能力限制写出后期备选，如先独立生成多个 clip，再由剪辑师进行硬切、低风险声画桥和安全的镜头匹配。JSON 时间轴不能冒称视频模型已经成功表现复杂转场。

## 数据与接口
- `director_editorial_montage.py` 的 `validate`：只接收已批准剧本、已验证≤90秒本集和由 QO-D02 产生的有序画面镜头。将 `montage_plan` 作为 `director_shot_coverage` 的可选字段。
- 每个 `sequence` 有一段连续、不重复的真实 shot IDs；每个相邻剪口有独立 `seam`，记录入/出场次、source-time-evidence、edit_type、axis_light_bridge、performer_prop_bridge、sound_intention、viewer_before/after 与 AI fallback。禁止跳号和用一个镜头横跨两个编剧场次。
- 每个切口保存 `exit_state_digest` 与 `entry_state_digest`，分别依据已审 base 内实际权威人物/道具状态计算。状态不一致的同场 `continuous` 明确拒绝。
- `reblock_episode` 重新生成镜头底稿和原十岗位 crew 状态，然后把蒙太奇计划与独立验证结果放到 `base.director_editorial_montage`，每镜记录 `montage_membership`。新 `shot_id` 对旧专业工单一律失效。
- `screenplay_series_delivery.episode_director_request` 将逐剪口和源证据进入真实 `director_brief` 的 model-facing 请求；不是只挂在文档注释。
- 有 QO-D19 `speech_cue_timeline` 时仍需保持独立声音/字幕时间轨；本阶段不绕过其实际媒体安全门禁。\n- 尚不能正确消费蒙太奇剪口的旧版 `director.compile_prompts`、`director_v2.compile_package`、`production_delivery._make_bundle` 和旧预演入口将**安全拒绝导出**，避免设计已存在而成品忽略转场/时间关系。后续实现可信的剪辑器消费并验收后才可解除门禁。

## 三项分离验收
- **离线结构验收**：跨两个编剧场次、真实剧本倒叙、全部 shot/cut/scene ID 准确、来源时间证据属于原稿、镜头顺序连续、每集时长未变、十岗位重新创建；反例涵盖伪造时空、跨场单物理镜、人物道具无故瞬移、过期来源摘要。
- **艺术验收**：真人盲审同一稿的顺序长镜头版与蒙太奇版，分别测信息识别、人物情绪、含义误读、节奏和终点余韵。没有盲评不称一流导演。
- **真实媒体验收**：独立AI clip之间镜头物理连续、人物面部服装、道具位置、光照、声场、字幕与出入点。无外部模型/真实素材许可，本项未验收。

该 Skill 不修改已审剧本，不批准费用、发布、真人作者身份，不打开网上传稿件。

## 帧级剪辑执行工单（QO-D09第二阶段）

`director_montage_editor_conform.compile_work_order(handoff,dossier,breakdown,original_packet,director_coverage,fps=30)` 是**本轮新增的真实软件入口**，只在内存返回可供后期剪辑师逐项执行的源锁定工单；`fps` 由项目/剪辑师明确指定为 24、25、30、50 或 60，程序不能默选。此调用从原始剧本重验证 QO-D02 的镜头覆盖与 QO-D09 的跨场蒙太奇，并重新生成原十岗位工单，**不接受篡改的下游报表当权威**。

工单输出：
- `segments`：采用现有 `series_final_timeline.compile_final_timeline` 的片头/回顾/故事/桥/片尾/证据页最终顺序，以**入帧、出帧（exclusive）**记账。证据页存在时固定为故事及所有其它附加段之后的最后片段，整个成片仍严守≤90秒。
- `montage_cut_jobs`：逐剪口列出 `boundary_frame`、两侧独立shot、实际编剧场次、`edit_type_exact`、时间关系、导演意图、观众前后变化、场面调度、灯光/摄影轴线交接、声音交接和降级方案。
- `speech_events` 与 `subtitle_events`：仅在 QO-D19 时间轴合法、存在时输出原文精确的独立绝对帧事件，保留跨视觉镜头的关联；没有精确 cue 的口语不能被旧镜头级字幕替代。
- `operator_blockers`：未提供原始镜头素材/真实配音/叠字片段与授权时，始终禁止误称实渲染。此阶段没有影像文件输入或编解码消费者，所以 `render_or_publish_authorized=false`。

剪切类型的细则：`hard_cut` 对应纯剪切零长度边界；`dissolve` 必须另有素材余量、交叠帧数与转场长度，当前不可偷取本集额外时长；`match_cut` 必须由真人核验实际匹配的帧；`sound_bridge`（J/L）必须有真实音频素材与跨镜窗口，不能仅据导演一句话生出时间码；`jump_cut` 要有实际画面的导演审核。每一种未满足的功能明确给出独立修复事项，决不静默改成 hard_cut。

`director_montage_editor_conform.editor_instructions(work_order)` 给后期剪辑师阅读版工单，无磁盘写入、云服务、模型调用或收费操作。任何时间码不落所选帧格、跨镜错位、总预算不符、来源篡改一律拒绝。后续真正导入剪辑软件/媒体验收时可通过本接口升级消费层，不应该绕过它调用仍未兼容的旧视频编译入口。原 QO-D09 与 QO-D19 依然 `in_progress`，文字工单不是完成影片。
