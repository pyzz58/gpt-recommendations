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