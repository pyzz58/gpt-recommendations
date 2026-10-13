## 导演主模块全面代码审计（2026-10-13）

已核查真实 GitHub 模块、真实模型执行入口、分集后的逐镜生产、总导演艺术/周星驰喜剧、七部门会、成果审片与后期90秒成片预算。**新增P0问题QO-D18**：正式系列新导演艺术方法/视听/跨部门工单已强制，但私有真实模型执行入口尚未透传；另发现真实演员摄影冲突不阻断“ready”和跨镜头引用证据，此项有PR40定点修复。旧剧本beat=拍摄shot、片尾固定加1.8秒、长剧本消息边界等仍待完善。**审计后质量总账39项，其中导演18项、0完整艺术媒体验收**；这不表示程序不可运行，也不能表示一流导演已实现。

- [完整证据与修复顺序](quality-optimization/DIRECTOR_FULL_AUDIT_2026-10-13.md) · [正式质量总账](quality-optimization/QUALITY_ISSUES.md) · [审计与P0修复 PR40](https://github.com/pyzz58/gpt-recommendations/pull/40)

## 国际一流导演的艺术判断与周星驰荒诞喜剧（QO-D17）

**创作原则已由用户确认**：思想、情绪与观众体验高于运镜炫技；学习名导如何选择/质疑一种拍法，而非复制“周星驰无厘头/王家卫慢镜/诺兰大声音”的外部风格。周星驰相关技巧只有在适合荒诞、喜剧、讽刺或有人物幽默的戏中使用，严肃科普/纪录不强制搞笑。

- [职业一手资料、源码根因审计与完成标准](quality-optimization/QO-D17_ARTISTIC_METHODOLOGY_AND_CHOW_COMEDY_AUDIT.md) · [Skill 11：专业艺术判断与周星驰喜剧](skills/11-director-artistic-judgment-and-absurd-comedy.md)。
- [director_artistic_methods.py](director_artistic_methods.py) 不是新 Agent，而是现有总导演的**真实艺术判断**：编剧与导演锁稿/七部门会议之后，完整写出故事立意、人物真实愿望、观众前后变化、镜头/声音/表演决定及被拒方案。喜剧开启时必须有合理人物处境、可信期待、视觉或动作的荒诞递进反转和人物意义；关闭时不允许无故插笑点。
- **正式新系列门禁**：`build_per_episode_crew` 将 `director_artistic_mode` 设为必需；各岗位须收到同源版本 `artistic_method_plan` 与绑定 `audiovisual_plan`，才能生成实际本部门 model-facing 任务书，并在提交岗位结果时验证未换稿/偷换导演方法。文本/测试不代表真实电影、名导认证或人审通过。
- 公共仓库只存虚构的例子、专业资料链接及通用 Skill；私稿、AI付费接口、发布和观影证据均不在本阶段自动执行。

## 最新导演视听表达与部门验收（QO-D03 / D16）

- **新系列硬门禁**：`build_per_episode_crew` 产生的正式部门工单，必须在现有导演锁定和 Skill09 制作会后再提交逐镜视听因果 `audiovisual_plan`；专业岗位准备与产物接受双向校验该导演计划，避免只有文字会议而没有真正导演视听决定。
- 导演必须说明**为什么用这一种画面和声音来传递思想及情绪**：人物状态、可观察事件、观众前后理解、场面调度/镜头静动、声音/沉默、真正切点及普通 B-roll 替代会损失什么。新增 [director_visual_language.py](director_visual_language.py)，具体要求见 [Skill 10](skills/10-director-audiovisual-meaning-and-review.md)。
- 原 Skill 09 的七部门制作会并不废止。新增 [director_delivery_review.py](director_delivery_review.py) 检查各部门**真实交付**是否实现导演意图；按镜头/责任岗提出具体返工，复用原十岗位版本状态机，不自动创设第二个总导演或不受控重试。
- [一手导演/剪辑职业访谈与源码根因分析](quality-optimization/QO-D03_D16_AUDIOVISUAL_CRAFT_AND_DELIVERY_AUDIT.md)。这两项目前是离线生产设计能力，**未通过真人成片盲评**，不可标记世界级完成。

## 总导演跨部门制作会与详细专业指挥 · QO-D15（2026-10-13）

**总导演负责“全片要达到什么效果”，还必须把艺术目标分解为各专业部门真实可执行的任务**：每个部门都要明白自己的具体镜头任务、观众感受与人物/思想转折、专业手段、前后部门信息交接、验收条件及失败后的替代方案。不能把「表演自然、画面电影感、音乐动人」当成指挥。

- [一手国际职业标准全文审读和真实源码对标](quality-optimization/QO-D15_DIRECTOR_DEPARTMENT_COMMAND_AUDIT.md)
- [Skill 09：导演部门会议与完整工作标准](skills/09-director-department-command.md)
- [实际功能：director_department_command.py](director_department_command.py)：新系列每集必须先由导演锁定 vision，生成七部门、逐镜头、跨部门可审核任务书，才可将任务传入现有十阶段专业 Agent 工作请求；不增设新导演岗位。
- 当前仅实现工程/离线结构层；尚缺真实模型导演会议、独立专业盲评和真实成片。D02/D03 继续推进而非标完成。

## 国际一流总导演质量优化 · QO-D14（2026-10-13）

- **编剧还没达到最终一流水准验收**：创作流程和详细交接可用，但跨题材独立盲评/真实模型写稿质量尚未完成；目前同步推进导演。
- **总导演不再被强制保留每个原稿节拍**：按职业创作的观众体验决定每场的留、缩、删，先提出两套真正不同的 director's cut，并写清人物/论证意义及情感损失；可把原10分钟稿**建议**剪成3集各≤90秒，但不能因为更短自动认定更好。
- **原稿版本不静默覆盖**：整场删减/剧情对白改变由导演提出精确返修单，原编剧完成新的短版剧本并经独立评审/必要授权后，才交给原有十部门按集制作。没有专业审读，240秒剪辑候选**不是**已批准的成片。
- [DGA/ScreenSkills/BFI完整一手资料和逐模块根因审计](quality-optimization/QO-D14_PRIMARY_SOURCE_DIRECTOR_AUDIT.md) · [Skill 08：专业导演创意剪辑](skills/08-professional-director-story-edit.md) · [代码：导演多版本Cut与编剧返修](director_creative_cut.py)。

## 单集90秒真正约束后期（QO-D13 · PR #42）

- 原剧本时长、单集故事时长、AI clip时长与**后期成片时长**是四种不同计量；最终operator制作包按绝对时间轴逐段叠加片头、回顾、剧情、过渡、片尾和原文确有证据时的唯一末页。仅凭故事时长<=90秒不得放行。
- 证据页由导演决定使用，不因原稿提供链接而强制加；若加则当前实际后期卡长**1.8秒**且严格计入<=90秒。新增 [series_final_timeline.py](series_final_timeline.py) 及 [根因/反例详解](quality-optimization/QO-D13_FINAL_90_SECOND_EDIT_RUNTIME_AUDIT.md)；没有实际视频就不能称已完成剪辑。

## 最新创作与分集硬约束（2026-10-13）

- **职业编剧详述**：剧本动作和场次必须充分清晰，并增加逐场逐节拍的导演可读说明（[screenplay_series_delivery.py](screenplay_series_delivery.py)），不得以简单梗概冒充可拍剧本；具体机位仍归导演。
- **总导演自主拆集**：先读完整剧本，可达十分钟或更长；自主按故事与情绪断点决定2集、3集或更多，**每集最多90秒**，算入所有片头/回顾/结尾/可选最后出处页。**导演拥有创意剪辑提案权**，可以将10分钟剧本实质压缩到例如3集，各节拍保留/浓缩/删除要说明利弊并由编剧审核生成新版本；**经审核的新制作剧本**里的节拍才必须在分集时恰好安排一次。导演不静默修改原作者台词/思想，镜头仍由导演设计。
- **对应问题条目**：QO-W11、QO-D13；关于作品的情绪/思想余韵，继续在 QO-W03 中评审。整部电影原稿时长≠单集时长≠单次 AI 片段时长。

# AI 短视频导演系统

**输入文案，完成导演设计，通过第三方视频 API 制作镜头，经审片、逐镜返工和剪辑合成交付短视频。** 手动导出制作包保留为备用路径。

这是产品目标，当前尚未完成真实成片闭环。现有专业导演编译能力已保留，本轮纠正了旧文档只停在图纸的目标，并补上 Seedance 单镜接口。

## 质量优化阶段（当前最高优先级）

**目标：国际优秀编剧与导演职业标准 × AI 短视频实际生成特点。** 先完整审计和提高前置编剧、总导演的质量；未来其他部门同样审计，但不得因现有测试通过而自称达标。优先修复真实问题，不新增无用 Agent。

- [质量优化总纲：目标、岗位边界、AI 视频约束、完成门槛](quality-optimization/QUALITY_CHARTER.md)
- [QO-W01：职业编剧一手资料全文深读与既有模块逐项审计](quality-optimization/QO-W01_PROFESSIONAL_PRIMARY_SOURCE_AUDIT.md)：解释优秀改编与机械保留的区别，先审计方法、再设计创作流程；结构代码 PR #24 暂缓合并。
- [QO-W01：编剧创作开发能力实际升级](quality-optimization/QO-W01_CREATIVE_DEVELOPMENT_IMPLEMENTATION.md)：读稿诊断 → 不同影视化 take → 独立选案比较 → treatment → 剧本及独立适配审核，核心实现 [screenplay_development.py](screenplay_development.py)；未完成专业真人盲评。
- [独立问题清单：39 项逐条根因、解决方案、验收、状态和修复历史](quality-optimization/QUALITY_ISSUES.md)
- [逐批解决路线：先编剧、再总导演，其他部门持续登记](quality-optimization/EXECUTION_PLAN.md)
- [机器可读问题总账](quality-optimization/QUALITY_ISSUES.json)：改动一个问题就更新一条，CI 拦截无证据假完成、漏问题和状态表不同步。
- [质量阶段 GitHub 总入口 Issue #22](https://github.com/pyzz58/gpt-recommendations/issues/22)：讨论与跨任务导航；真实状态以 JSON 为准。
- 原有 [技术/安全审计](AUDIT_FINDINGS.json) 继续独立生效；媒体未实测、账号未授权均不能被本轮优化消除。


## 国际编剧质量与导演分工

- [国际编剧与导演职责审计](SCREENWRITER_INTERNATIONAL_AUDIT_2026-10-13.md)：对照 Nicholl、Sundance、BBC、Scriptnotes、BAFTA、DGA 的创作标准和职责，并公开现有流程的专业缺陷、已修与待修项。
- [原创编剧工作 Skill](skills/07-professional-screenwriter.md)：小说/纪录片/科普观点分别改编，完整场次与视听动作、独立剧本审阅、定点返修、给导演的清晰权限边界；不保证自动达到一流质量。

## 编剧到导演的独立交接

- [编剧直接交付既有总导演](SCREENWRITER_DIRECTOR_HANDOFF.md)：将经过逐项审阅的完整剧本作为导演岗位的正式 source 文本，保留台词、旁白、场次、剧情动作和来源；不增加导演或视频 Agent。完整小说被旧入口截断时禁止冒充已完成全稿改编。身份可信审核和实际创作质量仍未实测。

## 本轮可检查的结果

- [单镜制作操作流程](SINGLE_SHOT_WORKFLOW.md)：已接入现有程序，串联准备、提交、查询、下载与审片记录，并提供只读审阅页。尚未部署，不是已完成网页控制台。

- [API 路线审查](SEEDANCE_API_AUDIT.md)：已修问题、接口范围、剩余缺口和实际验证证据。
- [S02 的 8 秒 API 请求候选](examples/dinner-dialogue-review/seedance_s02_request.json)：精确对白、生成参数和后期交接可审阅；未授权费用、未发请求、无参考图或真实视频。
- [《先吃饭》48 秒对白导演稿](examples/dinner-dialogue-review/director_workbook.md) 与 [《门后的信》60 秒导演稿](examples/door-letter-review/director_workbook.md)：公开虚构候选，当前会话创作并离线编译，不是十岗位自动创作质量证明。

## 已有与未完成

现有程序能保留故事、表演、摄影美术、剪辑、对白/旁白/音效、字幕和后期安排，导出模型请求候选。新增 seedance_adapter 可在未来授权私人环境显式执行单镜提交、查询和下载；现已接入统一命令行入口和只读审阅页；未部署网页控制台或自动执行器。制作包和后期工作单现完整保存 speech，时间线明确出镜/画外对白。

**仍需完成：真实账号和私人运行环境、参考素材上传/绑定、单镜与跨镜视听验收、局部返工版本选择、实际解码和整片合成。** 当前无真实生成，不以测试通过宣称影片好看。

隔离 Linux/Python 3.12 全量609项通过，本轮新增17项流程回归（上一轮接口新增19项）；GitHub CI 以对应提交 Actions 为准。问题主账29项：15项回归修复、5项确认开放、6项待调查、3项待真实媒体验证；AUD-002/Issue #1 保持P0。

| 入口 | 用途 |
| --- | --- |
| [产品目标](PRODUCT_NORTH_STAR.md) | 从文案到成片的完整边界 |
| [当前计划](PRODUCT_REVIEW_PLAN.md) | 从 S02 单镜验证到跨镜、返工和合成 |
| [问题主账](AUDIT_FINDINGS.json) | 已修和未完成的可核查状态 |
| [开发边界](GITHUB_ONLY_DEVELOPMENT.md) | 当前仅源码研发，未部署到 Mac |
| [开发指令](AGENTS.md) | 当前决定优先于历史阶段排期 |
| [历史 README](HISTORY_README.md) | 历史说明，不作为当前运行授权 |
