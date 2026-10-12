# QO-D15｜世界级总导演“指挥各专业部门”深度审计与首次实现

> 2026-10-13。**先读完职业资料原文及现有团队代码，再实施。** 本文讨论的是导演的领导/叙事传达/多专业协同，不是把“字段齐全”等同世界一流。本次没有调用任何付费 AI 或制作媒体，也不公开用户原文、剧本、钥匙。

## 一、职业一手资料：我们实际读到什么

1. **DGA，2023 Basic Agreement ARTICLE 7-101 / 7-202 / 7-301 / 7-501**（公开原文，非只看摘要）：https://www.dga.org/contracts/creative-rights/basic-agreement-article-7 。原文强调导演参与故事、声音和画面等全部创作层面，并将这些元素统合成一个一致的戏剧与审美整体。与编剧、工作人员的沟通和后期导演剪辑同样在职责之内。**提醒**：这是特定美国签约劳资协议，不是所有国家制作的统一法律或 AI 项目自动拥有的合同权限。
2. **ScreenSkills《Director (Film and TV Drama)》职业岗位完整公开说明**：https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/development-film-and-tv-drama-job-profiles/director-film-and-tv-drama/ 。直接表明导演需将 vision 向不同部门分享，并与摄影、美术、演员、灯光、服装和剪辑等部门合作。真实导演不只是写摄影参数。
3. **Paul Greengrass，BAFTA 2014 David Lean Lecture 完整公开演讲及 Q&A 逐字稿**：https://www.bafta.org/media-centre/press-releases/paul-greengrass-david-lean-lecture/ 。他在讲稿中通过自己的失败与《Bloody Sunday》等作品阐述：理解自己想拍的电影并能**将其明确传达给演员与剧组**，才从“会拍的人”成长为导演；与制片人、演员、摄影和剪辑反复讨论实际场景，而不是导演只守在摄影机后面。他也谈到允许演员在导演意图下寻找剧本之外真实的反应。是导演个人经验，不是算法硬规定。
4. **ScreenSkills《Director of Photography》岗位全文**：https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/technical/director-of-photography-dop/ 。摄影需和导演共同理解剧本及视觉气质，具体决定灯光、构图、机位、演员/摄影机 blocking。这说明导演应讲清**为什么**，并给摄影专家实际选择空间，不能只向摄影下一个“电影级画面”空口号。
5. **ScreenSkills《Production Designer Skills》完整公开技能清单**：https://www.screenskills.com/skills-checklists/scripted-film-and-tv/art-department/production-designer-skills/ 。制片设计/美术负责人要消化 brief，制定视觉方案、协调场景/道具/VFX、确认可行性、提出替代方案，尤其需要跨部门共享理解。因此总导演的原始 brief 应有材质/空间/道具**叙事理由**与实际关联。
6. **ScreenSkills《Editor》完整岗位说明**：https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/post-production/editor-film-and-tv-drama/ 。剪辑师在前期就需和导演一起考虑剧本如何呈现，后期依据素材/表演节奏与导演持续调整，不是随意套转场。
7. **ScreenSkills《Sound Mixer》《Supervising Sound Editor》岗位说明**：https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/technical/sound-mixer/ 和 https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/post-production/supervising-sound-editor/ 。声音岗位参与捕捉与后期修复，和导演、剪辑师协同决定台词可读性、空间声、ADR及音效时机；并非一律配激昂音乐。
8. **ScreenSkills《Script Supervisor Skills》完整公开清单**：https://www.screenskills.com/skills-checklists/scripted-film-and-tv/script-supervisor-department/script-supervisor-skills/ 。场记是导演与剪辑之间的关键桥梁，负责 continuity、时长、镜头覆盖情况，不应只在最终导出时看有没有缺少 JSON key。
9. **AI 视频执行约束**：Runway Gen-4.5 https://help.runwayml.com/hc/en-us/articles/46974685288467-Creating-with-Gen-4-5 和 Google Veo https://ai.google.dev/gemini-api/docs/veo 官方公开资料。视频模型每次 clip 的长度和镜头制作限制随版本/账户变化；导演给艺术目的、技术负责人决定镜头生成或静帧/动效/实拍合成路线。集长≤90秒是另一层上限，不能混淆。

## 二、当前源码的实际缺陷（不是笼统“加强统筹”）

| 审核项 | 现有代码 | 根因 | 对照职业工作所欠缺的 |
| --- | --- | --- | --- |
| D15-A（P0） | `agent_team.STAGES` 10步骤；`director_brief` 仅输出几个宏观字段 | 导演的“最终想让观众感受什么”未贯穿全部执行角色的具体镜头任务 | 完整片子愿景→各部门具体职责→每镜观众效果→可验证交付 |
| D15-B（P0） | `director_lock` 只有 `global_direction` 与 `shot_objectives` | 锁定了主题与每镜目标，但未实际传递一个由导演亲自解释的“部门工作会议” | 演员/摄影/声音/剪辑/技术必须知道要做什么、为什么、怎样做、与谁协调、什么不能做 |
| D15-C（P0） | `agent_role_contracts.ROLE_INSTRUCTIONS` 每个岗位模板固定 | 各岗位收到“自然表演”“规划灯光”“做好剪辑”等通用职能，容易独立生成互相不兼容的风格 | 给到每个部门**本片独特**、每个shot独特的创作目的与执行约束 |
| D15-D（P0） | `build_role_messages()` 只包含 base/upstream outputs | “总导演的想法”可能只在报告或 README，而**真正模型角色看不到** | 把真实导演命令作为该部门 model-facing user JSON 发送，系统指令说明必须执行其艺术目标 |
| D15-E（P0） | 剪辑依赖表演/摄影/声音，技术依赖剪辑，QA最后审核 | DAG 只说明“哪步先后”，没有说清上下游什么状态、时码和信息必须交接及冲突归谁 | 跨部门接口逐项登记，表演→摄影/剪辑、声音→剪辑、剪辑→AI、AI→QA、QA→导演 |
| D15-F（P1） | `agent_creative_review` 与 `quality_review` 结构与部分专业检验 | 模板复制到所有镜头可能形式通过、实质没按场次发生新的事情 | 真实逐镜“动作/观众变化/音画对应”的可观察验收标准，显式禁止多镜同一泛句 |
| D15-G（P1） | `screenplay_series_delivery.build_per_episode_crew` 每集独立启动原团队 | 没有声明总导演专业部门会是**发放专业工单前必经阶段** | 新系列模式下 director_lock 后先完成跨部门会；没有这份会议文档，下游岗位不能进入生产请求 |

## 三、从影视主创“自己懂”变成“全团队真懂”的目标工序

```text
正式认可的整篇编剧剧本 + 导演版本决定
 -> 每集 <=90 秒的故事内容与连续性（原有 D14 / D13）
 -> 现有 director_brief：观众目标、冲突、情绪/知识弧、片尾余韵
 -> 现有 script_edit：故事连续性检查 / 编剧返修，而不是另写故事
 -> 现有 director_lock：统一视觉和声音语法、逐镜明确目的
 -> 新增 **导演跨部门制作会 / detailed department command**
    - 7个执行/审查岗位
    - 每岗位目标、观众效果、做法、边界、接口、失败后补救
    - 对本集每个shot单独解释
    - 7组关键跨专业接口有具体交接内容和矛盾仲裁
 -> 专业岗位的真实 model-facing 请求附带“仅属于本岗位”的导演工单
    - 表演 ↔ 摄影/美术 ↔ 声音 ↔ 剪辑/动画 ↔ AI生成 ↔ QA ↔ 总导演
 -> 领域部门完整交付、冲突上报、总导演审阅与定点返工
 -> 经权限批准后的实际媒体试验与独立人审
```

### 各部门实际必须知道的事

- **演员/动作**：观众在角色看信封的这个具体时刻需要感到害怕还是释然？为什么手停下？与道具的状态变化如何交接给摄影/剪辑？不能把“自然表演”算说明。
- **摄影/美术**：镜头为何停在手而不在脸？空间轴线、光源和画面元素是否让观众理解选择？应当留出摄影师自主决定手段的空间。
- **声音**：为什么这一刻不是连续 BGM，而是纸张声音盖过其他声？VO/对白/停顿如何与具体动作、剪辑时码共同成立？
- **剪辑/动画**：观众在上一镜知道了什么，又需要在下一镜看到什么？为什么此刻切换、必要文字为何用后期而不是让 AI 生字？
- **AI 技术**：导演本来要的可见动作是什么？如果手指遮挡、多主体/身份漂移导致画面失败，该怎样换镜/静帧/后期合成而**不丢叙事功能**？
- **独立 QA/场记**：哪些细节一旦错误会破坏全片真实感，哪些是要人工看成片才能确定；不能“字段全”就放行。
- **总导演终审**：当摄影、演员、声音意见冲突，谁能重新决定节奏/时长/镜头？为什么这版作品值得观看、人物与哲学问题是否仍有余韵？

## 四、本轮真实代码实施与工程完成界限

- `director_department_command.command_request`：在现有 director_lock 已完成后才可提出真正的**部门制作会请求**，携带导演圣经、各个真实 shot 的导演目标、原权威剧本、来源/锁稿摘要，所有请求 UNSENT。
- `validate_command`：不能缺少 7 个部门、任一真实 shot 的说明、7 组跨部门接口、客观验收条件；不允许多个shot偷懒一模一样的表演/镜头指令。过短或泛泛的文字被退回；这只保证最小信息齐备而非高超艺术。
- `agent_role_contracts.build_role_messages(...,department_command=...)`：把经完整性与锁版校验的各部门**实际任务**置入该角色真正会收到的 JSON 消息，附加专业岗位必须理解的系统说明。不是只存报告供人看；角色不会被允许跨领域随意改稿。
- `screenplay_series_delivery.build_per_episode_crew` 新系列 episode base 带必需导演制作会标记：前置总导演仍能审读和锁定；未携带会议工单则表演/摄影/音频等后续岗位入口会拒绝。老兼容演示保持可读（不等于已经享受新专业机制）。
- **这里还未自动“调用”模型来生成导演工单**，也未经过独立专业人审。要在真实部署中使其运行，需合法接入授权 LLM 以及将 director_command 返回的结构化数据传入 role adapter。测试全绿只证明流程数据路径与版本门禁，不证明导演艺术水平。

## 五、实际世界级能力验收（仍未完成）

1. 至少三体裁（fiction、science essay、documentary）在独立盲评时，各部门完成的专业工单被认为**真正理解导演视角**，且相对通用指令能显著改善可读性/可拍性。
2. 同一原稿对照「旧流程泛角色指令」与「导演召开完整制作会」，盲审每镜是否发生人物/观众变化、有无重复无效场面；对失败有具体导演返工而非再写口号。
3. 尤其评审 AI 短视频：真实生成两镜以上，角色/道具/空间连贯，声画连贯，字幕后期正确，预算/重试清楚，每集最终<=90秒。
4. 多部门接口发生真实冲突时，例如手部动作与镜头遮挡、环境音压倒台词，能有**总导演主持的协调/重新交付**，而不是各部门互相覆盖 JSON。
5. 长稿导演有权先实质压缩剧本（D14）并通过编剧审阅；新制作稿成为唯一权威，导演会议不能拿未经批准的粗剪提案冒充最终 script。
6. 导演会的信息详细并可执行；不把字数阈值/哈希校验当作真正的“世界一流”认证。

**状态：QO-D15 in_progress。** D02（场次与真实镜头解耦）、D03（高级视听语言与思想传递）、D10（作品专业盲评）仍分别开放。这轮优先确保导演命令能真正传到所有专业部门，艺术质量以实际作品评价。
