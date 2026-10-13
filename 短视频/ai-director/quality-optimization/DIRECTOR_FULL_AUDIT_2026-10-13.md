# AI总导演全模块审计（2026-10-13）：事实、问题及逐项升级门槛

> **审计范围**：GitHub `main` 的总导演/专业创作、长剧本分集、艺术方法（含周星驰荒诞喜剧）、七部门制作会、岗位状态机、真实DeepSeek执行入口、审片返工与后期工作包；所提P0问题以代码实际路径而不是单纯的视觉品味主张为依据。工作分支的修复和本审计不是独立专家证明的一流电影认证。只使用公开虚构样例；不得把任何用户私稿发布或未经同意发付费API。

## 0. 已验证基线

- 主分支实际存在 `director_creative_cut.py`、`director_artistic_methods.py`、`director_visual_language.py`、`director_department_command.py`、`director_delivery_review.py`、`screenplay_series_delivery.py` 和七部门原岗位协议，**不是空架构，也不需要重复造多套总导演**。
- GitHub Actions 最近一次相关成功：Run `38345152297`，**743/743 单元测试通过，整体branch覆盖率88%**；输出 `world_class_proven=false`，零实际媒体/专业艺术完成。工作分支新增测试必须单独重新过CI。
- 审计前 `QUALITY_ISSUES.json` 登记38项；本次又正式登记**QO-D18真实执行器未透传导演创意计划**，现在总计**39项：编剧11、导演18、未来10**，**0项完整达到职业+真实成片验收**；其中导演 `QO-D02`、`QO-D06`、`QO-D09`、`QO-D10`、`QO-D12` 为 confirmed_open，`QO-D11` 为 blocked_external，其他多为 partial/in_progress。
- 用户已批准的艺术原则：思想与情绪的实际表达先于炫技；总导演可质疑冗长母稿并向编剧提出大幅压缩，正式每集≤90秒；必须详细统筹摄影/表演/声音/剪辑/AI/QA；周星驰荒诞技法**仅适合喜剧时启用**。
- **职业一手资料**： [ScreenSkills 电影导演职责](https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/development-film-and-tv-drama-job-profiles/director-film-and-tv-drama/) 要求导演从剧本视觉化到全片剪辑的连续创意领导；[DGA 2023 Basic Agreement 第7条](https://www.dga.org/en/Contracts/Creative-Rights/Basic-Agreement-Article-7) 规范其签约导演与编剧讨论/导演剪辑职责（不是本项目自动生效的授权）；[BAFTA Mike Leigh 2024 完整讲座](https://www.bafta.org/media-centre/press-releases/screenwriters-lecture-series-2024-mike-leigh/) 讨论演员/美术/摄制合作与具体行动、演后剪辑；[周星驰《功夫》本人问答](https://indielondon.co.uk/film/kung_fu_hustle_chow.html) 明确故事结构先于动作喜剧、导演与特技/CG部门一起取舍不切实际镜头。访谈给出不同个性方法，不是固定导演打分模板。

## 1. 真实阻断缺陷（立即修）

| 编号/优先级 | 实证代码位置 | 确认的根因及影响 | 最小修复与自动验收 | 状态 |
| --- | --- | --- | --- | --- |
| A / **P0** | `director_delivery_review.validate` 中验证 `conflicts` 后计算 `next_step` 的条件 **只读 `needs` 和 `pending`** | 已交付的演员要求手部犹豫可见，摄影却裁掉手：若其他已交付都写“支持意图”，文本审片仍可视作可进入真实媒体审查；冲突本身未阻断 | 存在冲突必须明确 `resolve_cross_department_conflict`，不能假“ready”；要求双方真实交稿证据，导演明确仲裁，等待修正/新快照 | **本PR内已定点修复，待CI** |
| B / **P0** | 同一文件 `delivery_quote in json.dumps(state.tasks[dept].deliverable)` | 镜头S02评语可引用只出现在S01的岗位内容，伪装成已审核S02，影响导演定位返工 | `kind=shots` 时证据必须来自**对应shot_id**的实际岗位交付；用借邻镜内容的反例拒绝 | **本PR内已定点修复，待CI** |
| C / **P0** | `agent_live_crew.run_one_locked_role` 调用 `roles.build_role_messages`、`roles.validate_role_output`、`roles.submit_role_output` **都没有传 `department_command`、`audiovisual_plan`、`artistic_method_plan`** | 正式新分集 `build_per_episode_crew` 已把三个mode置为强制；先运行director_brief/script_edit/director_lock不受影响，到 acting/camera 等专业阶段使用该“真实模型”入口会触发 `CREW_DIRECTOR_DEPARTMENT_COMMAND_REQUIRED` 等，而不是让艺术理念真正进入付费执行；旧demo没有新强制mode，可继续成功 | 为合法授权的私有运行器提供已经生成、来源绑定的三个导演决策输入，经过一次共同版本快照前置审计，再交给现有岗位模型/结果校验；提供**纯模拟HTTP**的严肃/喜剧跨岗位测试，无授权不开真实网络 | **PR #41 实际运行入口已修复，774项离线测试成功；真实私有授权长流程与艺术盲评仍未完成** |
| D / **P0** | `screenplay_series_delivery.build_per_episode_crew` 强制 `original_ids == [source beat IDs]` 并一条原beat复制一个原shot | 上游原剧本节拍≠导演电影镜头；一场完整对话可能需要远景→反应→动作特写，合并蒙太奇也可能合为一镜。现在的主线以beat作镜头骨架，导演只能润饰既有shot，难以重构电影覆盖 | 增加导演认可的 `scene/beat ↔ shots` 双向映射（1对N/N对1），绑定角色/事实/台词/时长及场次，改变镜头后重建原岗位来源关系；双人戏+蒙太奇+科普三类正反测试 | **未修复 / QO-D02** |
| E / **P0** | `screenplay_series_delivery.validate_breakdown` 只算 `story+reserved`; `build_per_episode_crew` 把 `series_context` 简化成聚合 `reserved_additional_s`；`production_delivery` 的 `closing_evidence_card.build_card(base)` 再固定追加1.8秒 | 预留证据卡/片头只是数字，没有落地为独立可审轨道。若一集故事恰好90秒但存在可信来源而按旧方案reserved=0，后期还是可能追加1.8秒；即使reserved=1秒，实际信用卡长1.8秒，终片会超90秒；实际是否被其它独立门禁拦截需进一步联检 | 用**实际最终时间线**核算片头、回顾、过渡、结尾、证据页，`end_s<=90`；来源页规划时长与实际1.8秒布局一致，不许隐含自动添加；跑 90秒+1.8、89秒+0、88.2+1.8 等公开反例 | **未修复 / QO-D13 / QO-D09** |

## 2. 较高风险/艺术深度不足（完成P0后）

| 编号/优先级 | 当前证据 | 升级建议 | 状态 |
| --- | --- | --- | --- |
| F / P1 | `episode_director_request` 在 `build_role_messages` 的大小校验**之后**额外注入全部局部dossier；`agent_role_contracts.MAX_CONTEXT_CHARS=220000` | 在最终消息构造完成后统一按目标模型token预算/JSON大小验证；角色收到与其镜头相关的完整高价值资料，而非把重复整剧本/七部门计划逐层复制导致高成本或被截 | 未修 |
| G / P1 | `director_artistic_methods.validate` 要求每镜选名导方法、每镜观众入前/入后文字必须不同；喜剧固定六节拍 `GAG_LADDER` | 不限制导演“必须以几位名导的标记卡作每镜依据”。安静的铺垫、环境建立、纯动作连接无需硬凑一条独立认识变化。周星驰式喜剧可长短组合，六步只作示例，不把角色因果创意限制成唯一公式；科学纪实仍须禁止虚构事实 | 未修 / D17 / D03 |
| H / P1 | `director_visual_language` 已规定视觉母题/剪辑/声音，但只有一种计划与反事实描述，没有系统性演示独立两版 | 对关键场景/关键镜头提出两种实质不同的声画实现及具体利弊，由同一总导演挑选，必要时接纳专业部门建议，减轻对普通镜头过度推演 | 未充分证实 / D03 |
| I / P1 | `build_per_episode_crew` 每集重新开始同一十岗位 ledger，保留文本Bible但**未建立真实跨集图像/音色锚点已存在的证明** | 强制跨集镜头参考资产的真实性、版本/版权、角色/服饰/空间的续接检查，不得假设提示词重复就能稳定脸和道具 | 未做真实媒体 / D05 |
| J / P1 | `director_creative_cut` 可审核600s→3×≤90s候选，但模型请求 `dispatch_allowed=False`，短版新权威剧本仍需真正编剧/审核并生成 | 完成“导演两版真实稿→编剧新版→独立剧本审阅→系列镜头映射”公开合成E2E文本测试；比较短版是否保住思想、人物动机，不因压短自动判优 | 部分实现 / D14 / D01 |
| K / P1 | `quality_review` 和 `director_final` 主要审文字/元数据，现有试验为合成而非实际影片；真实模型生成片段没有输入给实际导演亲看 | 真实媒体审片（人物/剪辑/声音/竖屏字幕/转场/故事效果）与匿名盲评。特别要有失败基线：看起来漂亮但没有让观众理解或有情绪 | 外部验证阻断 / D10/D11 |
| L / P2 | QO-D17有9个大师“艺术方法卡”且周星驰多条，但技法来源适用与反例没有可量化艺术反馈样本 | 逐体裁“有效/无效”的局部案例积累，导演学习的是选择原因而非表演模仿；不将个别导演偏好当行业统一标准 | 研究持续 |

## 3. 优先处理顺序

**第1批（不需要付费模型）**：A/B 真实审查证据与冲突门禁 → E 最终时间线90秒绝对硬约束 → C 私有模型runner与总导演新方案完整同源绑定 → D 场次/beat与镜头真正解耦 → F prompt/token最终边界。每项必须有合成反例与CI。

**第2批（专业创作）**：G 防方法卡机械套用与喜剧节奏自由 → H 关键场景两版声画语言 → J 编剧短版真实文本E2E → I 跨集真实视觉/声音资产机制。

**第3批（需要授权和真人/实际媒体）**：K 逐镜实际AI视频生产和独立盲评；同意才进行费用支出、API密钥使用、真实人物材料上传与发布。不得把第1批测试通过等同于一流导演。

## 4. 验收原则

1. **顶级总导演的价值不在表单多和提示词长**：能提出独立艺术观点、具体观众体验、真正有必要的视听选择、对各专业的详细但尊重专业判断的指导、跨部门裁决和导演剪辑最终版本。
2. **静默不是空镜的失败，笑点不是固定套路**：斯科塞斯/小津/王家卫/迈克·李/诺兰/周星驰方法各自适用，灵活选择、反向质疑，不做简单风格拼贴。
3. **每一处技术阻断给可复现反例**；每一处电影艺术评价都须明确缺少的实际观影证据。不能用测试数冒充作品好坏。
4. **严格保护**：不复制用户作品到public仓库；任何未授权真实API、付款或发布均禁止；如实记录真实已做与没做的事情。
