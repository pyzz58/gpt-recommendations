# GitHub 优先复用决策清单（2026-10-11）

> **研发阶段限制（2026-10-11）**：开源借鉴/集成只在 GitHub 代码与非敏感隔离测试中进行；用户未批准前，不能要求 Mac 同步、安装、运行或下载，也不能触发收费模型。集成候选先记录许可证、维护证据与安全评估；详细闸门见 [GITHUB_ONLY_DEVELOPMENT.md](GITHUB_ONLY_DEVELOPMENT.md)。


**固定规则：每次修改、补足功能或修复缺陷前，先检索 GitHub 上的相关成熟仓库，核对代码、许可证、维护状况、测试和运行成本，再决定直接复用、借鉴结构还是自行实现。参见 AGENTS.md。**

状态：仅完成上游仓库的第一轮公开资料调查；没有安装依赖、下载模型权重、执行付费 API、修改用户 Mac 配置或合并第三方代码。实际使用前仍需测试许可证兼容、版本和依赖。

## 2026-10-11 对标仓库和选择

| 改进方向 | GitHub 项目 | 已核实的能力 | 限制与决策 |
|---|---|---|---|
| 角色/道具/场景/镜头的全局约束 | [Ironieser/CineCrew](https://github.com/Ironieser/CineCrew) — Apache-2.0 | FilmDSL 将元数据、资产、镜头和导演约束统一为结构化规范；有角色、场景、道具稳定 ID 与检查/修订阶段 | 2026-09 才公开的研究型项目，不是长期验证的稳定工具。**P0 借鉴数据结构，不整仓引入** |
| 道具与人物合法状态转移 | [pytransitions/transitions](https://github.com/pytransitions/transitions) — MIT | 成熟 Python 有限状态机，明确允许和禁止的状态转移 | 不会理解中文自然语言，必须先把拿起/携带/放下结构化。**P0 小范围评估，保留零依赖基线** |
| 结构化 JSON 与连续性状态校验 | [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) — MIT | JSON Schema、多错误汇总，Python >=3.10 | 不负责故事语义理解。**P0 最先评估可选 Schema 检验** |
| 人物/道具/镜头对象强类型 | [pydantic/pydantic](https://github.com/pydantic/pydantic) — MIT | 数据模型、验证和生成 JSON Schema | 与 jsonschema 功能存在重合。**P1 不要同时为相同任务引入两套框架** |
| 多阶段工作流、恢复和审批节点 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) — MIT | 持久状态与条件流程图 | 当前 local_director 已有流程和费用账本。**P2 借鉴，不迁移** |
| 参考图、人物/场景资产与前后帧衔接 | [billpar/ai-cinematic-pipeline](https://github.com/billpar/ai-cinematic-pipeline) — MIT；CineCrew | 角色/场景/道具资产模板，关键帧接续的工作方法 | 前者主要是生产指南，不是成熟可用的自动一致性引擎。**P1 学其资产管理方法** |
| 本地图片/视频模型工作流 | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) — GPL-3.0 | 可视化节点图、JSON 工作流、当地执行与部分模型集成 | 体量、算力、许可证边界不同。**P2 独立可选，不直接复制 GPL 源码** |
| 字幕/剪辑/音视频合成 | [Zulko/moviepy](https://github.com/Zulko/moviepy) — MIT；[remotion-dev/remotion](https://github.com/remotion-dev/remotion) — 特殊许可证 | MoviePy 程序化剪辑；Remotion 更适合复杂程序化图形/动画 | Remotion 对部分营利组织有授权要求。**P2 首选考察 MoviePy，不为前期导演稿安装** |
| 成片之后的镜头节奏分析 | [Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect) — BSD-3-Clause | 识别已有视频镜头切换 | 不能检查文字故事的物理连续性；没视频就没用。**P3** |
| 模型返回非法 JSON | [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines)、[BoundaryML/baml](https://github.com/BoundaryML/baml) — Apache-2.0 | 结构化生成与校验相关工具 | 不保证与当前 DeepSeek 托管接口即插即用，也不能绕过费用门禁。**P1 先离线验证** |

备选调研：[zetagao/frameline](https://github.com/zetagao/frameline) 有分镜表、演员走位示意图、EDL/FCPXML 输出，但公开历史只有约 3 次提交，Node + OpenRouter，部分关键提示词没有公开：暂作为 UI/数据结构参考，**不列为成熟产品**。

## 直接对应本轮真实样本的 8 项缺陷

1. SCENE_PROP_DOUBLE_BOOK：采用 CineCrew 风格的唯一道具 prop_id、固定道具初始场景与位置，不允许“场景已有书，镜头又从别处拿来同一本”。
2. PROP_TRANSFER_MISSING_PHONE：为道具构建状态轨迹 sofa_arm → hand → drawer；中间缺拾取事件则阻断。
3. PROP_APPEARANCE_UNEXPLAINED_BOOK：追踪书的 coffee_table → hand → desk，不靠两个镜头随意声明“同一本书”。
4. ACTOR_TRANSFER_UNEXPLAINED：定义角色 start/end 空间位置，允许明确标注的跳切/时间省略，但不得让关键物品瞬移。
5. ACTION_OVERLOAD：为短镜头建立动作数量与节奏提示；时间阈值属创作经验，不假装科学测量。
6. REPETITIVE_PHONE_BEATS：检测连续镜头的叙事功能与画面变化；这属于创意质量，不可仅靠简单规则“一键修好”。
7. LICENSE_EVIDENCE_MISSING_MUSIC_LICENSE_CHECK：音乐真正选定之后再登记授权来源、证明与状态；计划不等于授权。
8. LICENSE_EVIDENCE_MISSING_ASSET_LICENSE_CHECK：同样为每一件实际素材保留授权证据；不能把未核验字段改成已核验。

## 2026-10-11 用户批准改为 Showrunner + Specialists 制片团队

- 真实需求：用户文案进入，由总导演提出审稿与整体创作方向，剧本编辑、动作、摄影、美术、剪辑动画、声音及 AI 技术岗位按专业分工交付，独立 QA 后总导演整合，必要时只返工局部；**最终是一份统一导演交付书**，不是多个 Agent 在聊天中争论。
- 已查公开 GitHub 上游：[CineCrew](https://github.com/Ironieser/CineCrew) Apache-2.0，提供 showrunner/story/acting/camera/tech/VO/reviewer 分工与 FilmDSL；[CrewAI](https://github.com/crewAIInc/crewAI) MIT，提供 Crews/Flows 和层级代理任务；[LangGraph](https://github.com/langchain-ai/langgraph) MIT，提供有状态 DAG、恢复和人审机制。
- 复用决定：将现有 `director_workbook.py` 保持为主交付，新增零依赖 `agent_team.py` 负责十阶段有向任务、八类专业角色、统一源稿版本哈希、岗位字段所有权、依赖版本核对、QA 只读、总导演定向返工、与专业交付书合并。**未直接复制上游源码或集成其 Python 包**；GitHub-only 期间不能为多 Agent 名称付出额外框架/模型成本。
- 已有单体 `local_director.py` 在多 Agent 真正执行器经过独立无付费回归、人审和用户批准前仍保持兼容。系统不会私自上传用户文本、视频参考图或触发收费 Agent。
- 详见 [MULTI_AGENT_STUDIO.md](MULTI_AGENT_STUDIO.md)；新增 `tests/test_agent_team.py` 合成/公开示例回归，但提交不等于最新 CI 通过。

## 动作密度与拆段：优先导演可执行性，不扩张视频平台

- 用户核心目标始终是“文案进入→专业导演全面设计剪辑、表演动作、摄影、场景、动画、台词、后期、AI制作工作单”。本轮新增 `director_shootability.py`，以每镜 `shootability.action_units` 明确人物/左手/右手/道具/节拍/时间/结果，并在必要时要求 `split_stitch.segments` 的具体分段与衔接计划。
- 设计吸收 CineCrew 的动作/角色/道具一致性合同和 AI Cinematic Pipeline 的逐镜 action 记录理念；未复制或运行第三方源码。无需引入大型视频生成库或真实模型执行器。
- 风险阈值(如不到0.55秒的精细道具动作、2秒窗口三项道具操作)仅用于**人工复核**，不能据此断言任何特定模型失败。只有资源占用矛盾、非法时间、分段缺口才作为确定性阻断。
- 严守 GitHub-only、不安装本地依赖、不调用付费服务；合成测试文件 `tests/test_director_shootability.py` 已提交但截至本轮尚未取得完整最新 CI 验收结果。

## 跨镜头导演叙事与混合媒介风格一致性（2026-10-11）

- 需求：用户给文案，导演必须说明每个镜头相邻交接的叙事因果、观众期待、情绪节奏、摄影/形状/动作联系，以及 AI 视频/静态图/字幕动画/实拍的视觉语言如何统一。
- 核对 [CineCrew](https://github.com/Ironieser/CineCrew) 公开描述中的跨镜资产/角色/摄影共享约束；[OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) 的专业镜头与轨道分离；[AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline) 的 shot-list 多部门分工。
- 选择：现有导演数据已齐全，无需安装完整 OpenTimelineIO 或多代理视频流水线。新增自有零依赖 `director_narrative_bridges.py` 的**薄创意合同审查**，并接入主要导演交付书。源代码未复制第三方项目，无法宣称已集成外部渲染算法。
- 质量边界：机器只能检测空缺、枚举、无效时长及跨介质注意项，不能替代判断作品是否打动观众、转场好不好看；`production_blueprint_ready` 只是可交接结构完整标志，不是生成验证。

## 时间线剪辑工作单：借鉴 OpenTimelineIO 的轨道抽象

调研 [AcademySoftwareFoundation/OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) 公开 README：它是成熟影视时间线交换框架，提供面向影视编辑的 clips/tracks/time ranges 与多种适配器。当前没有真实源媒体、也不需要向特定 NLE 导出，因此不引入其 Python/原生模块；只借鉴“导演决策 → 可定位的绝对时间事件列表”思想。新增零依赖 `director_timeline.py`，使 `director_workbook.py` 输出 `editor_decision_list`，明确旁白、对白、音效、动作、摄影、动画的时间轨道和待人工核验处。详见 [EDITOR_TIMELINE.md](EDITOR_TIMELINE.md)，没有复制其源码，不承诺当前能导出 FCP/剪映/达芬奇工程。

## 用户重申的产品边界：专业导演中间层为唯一核心

用户再次明确：他提供文案，由系统作为“中转导演层”，**完整设计剪辑、动作、动画、场景、台词、摄影与声音**，并交付适合 AI 视频制作的一整套方案。不能继续只围绕参考图、门禁和工具接入扩张。

本轮核对 [CineCrew](https://github.com/Ironieser/CineCrew) 的 FilmDSL 将镜头、人物、资产、摄影视为共享结构，与 [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline) 的 `shot-list-template.csv` 把动作、表情、对白、旁白、镜头和环境声音逐列设计的做法；因此新增 `director_workbook.py`，从已存在基础分镜和专业方向稿合并成全栏目导演交付书，严格要求 `editing/animation/speech` 的真实创作决策，不引入其视频模型执行框架，也不复制其源码。产品目标写入 [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md)，由 `tests/test_director_workbook.py` 审核关键边界。所有真实示例仍仅能在用户未来明确批准本地运行后验证。

## 模型输入适配预览（2026-10-11）

继续借鉴 CineCrew 的 FilmDSL 资产绑定规则与 AI Cinematic Pipeline 的角色/场景/道具参考图分层。当前供应商 API 格式、计费和角色参考图上传规则未经正式核验，因此优先实现仅有 asset_id、view、role 的`reference_input_preview.py`，保留全部模型无关、不可执行的输出，不直接依赖厂商 SDK；下一次只有完成官方参数核查及用户费用批准，才可以另外设计真实 provider 适配器。新增 [REFERENCE_INPUT_PREVIEW.md](REFERENCE_INPUT_PREVIEW.md) 和合成回归测试，尚未运行最新整仓测试。

## 第五阶段：生成前门禁（2026-10-11）

继续借鉴 CineCrew 的“生产之前统一检查资产、镜头、约束”理念。由于目前**没有真实视频模型执行器**，引入完整多代理视频流水线或付费 SDK 反而增加依赖与费用风险；新增纯 Python `production_gate.py` 最小只读门禁，接入 `director_v2.py` 的编译工作包并配套无付费回归。它只汇报“规划/参考媒体缺什么”，不能通过修改 JSON 来授权真钱的 API 调用，也不会接触用户 Mac。

## 第四阶段：参考资产库复用决定（2026-10-11）

对照 [CineCrew](https://github.com/Ironieser/CineCrew) FilmDSL 的 assets/stable ID 设计，以及 [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline) 的人物多角度参考图、场景与道具表；设计通用、无依赖的资产登记和校验层。借鉴 [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) 的 Draft 2020-12 规范，将可移植结构声明放进 `schemas/reference_assets.schema.json`。

**实际采纳**：稳定资产 ID + 每镜引用 + 缺失资产审查 + 人工审核/来源/许可/哈希门禁。**没有实际集成或复制第三方项目源码**，因为 CineCrew 的完整多智能体/生成依赖超出了当前规划工具需求；`jsonschema` 保持可选，不强制用户电脑安装。

**新增代码**：`reference_assets.py`、`tests/test_reference_assets.py`、`schemas/reference_assets.schema.json`、`REFERENCE_ASSETS.md`，并在 `director_v2.py` 中提供可选参考资产目录校验/编译连接。新流程仍是无付费离线规划，尚未生成任何真实参考图，也未对用户本地私有 `jobs/` 完成实机验证。

## 本轮第三阶段混合制作路由决策（2026-10-11）

- [CineCrew](https://github.com/Ironieser/CineCrew) 的 FilmDSL 明确约束镜头、资产和导演审查；[AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline) 明确视频生成与音频后期/剪辑分离。这里只借鉴`结构化镜头`和`后期路线显式表示`的设计，不安装模型、不复制第三方源码。
- 当前自有 `director_v2.py` 已有单镜基础编译功能，目标仅需区分 **AI 视频/静态/剪辑/实拍/后期** 五种制作来源。整仓引入多模型框架的复杂度与本任务不成比例，因此实施**零额外依赖的路线解析器和合成回归测试**。实现与回滚文件：`director_v2.py`、`tests/test_production_routes.py`、`PRODUCTION_ROUTING.md`。
- 风险和边界：别名仅覆盖已明确登记的写法，未知旧版 `production_method` 失败；编译不能修改配音稿、证明有版权、导出实际成片，也不能在未获批准时自动生成收费视频。**未读取用户 Mac 上私有第三阶段成果，不能宣称真实候选档已在 GitHub 回归通过。**

## 首轮实际采纳决定（2026-10-11）

- **直接采用成熟开放标准**：JSON Schema Draft 2020-12。项目已在 `schemas/continuity_contract.schema.json` 保存正式合同结构。开发隔离环境使用成熟库 `python-jsonschema/jsonschema` 校验 Schema 与合成测试，用户 Mac 运行时仍然零安装依赖。
- **有限借鉴而非引入**：`pytransitions/transitions` 的“显式状态+允许转移”思路和 CineCrew 的稳定资产 ID / 视觉 Bible。为保持项目可携带，最终运行时选用经过离线测试的轻量状态回放器 `continuity_contract.py`；没有声称集成第三方库源码。
- **已接入流程**：新增合同严格时，`local_director.py audit` 对逐镜头状态回放；在付费下一阶段开始前，如存在 blocker 则阻断。合法场外移动仅转人工 review。
- **验证边界**：本地回归测试和真实样本的私有离线验证已运行，但 Mac/真实视频阶段必须再验；规则通过不等于心理刻画、演员实际动作、镜头可生成性已验证。

## 推荐落地顺序（保持现有用户工作不受损）

第一阶段（不用模型费用）：定义统一的状态 Schema，支持各镜头描述道具与人物在镜头前后的确定位置；对同一道具的移动事件逐帧回放，生成错误报告。既有 continuity_audit.py 保留为无依赖后备实现。对真实 13 镜头只生成 plan.proposed.json 候选，不覆盖 plan.json；运行 director.validate + audit 后人工验收。

第二阶段（离线测试）：在独立环境比较 jsonschema 与 Pydantic 的结构校验增益，衡量依赖体积、维护成本、误报和漏报；必要时用 transitions 建立严格迁移约束。**没有测试证据就不要“为了开源而接入开源”**。

第三阶段（视频制作以后）：再评估 ComfyUI、MoviePy、PySceneDetect、角色图像锁定与视频后期质量检测，不要现在付费生成素材，也不要下载大权重到 Mac。

## 每次修复的记录模板

- 问题：现象、复现、影响；期望验收标准。
- GitHub 调研：至少 2 个具体候选及链接；活跃度/最近维护信息、许可证、发行版、测试、Mac/Python 与离线可行性。
- 选择：采用现成库／借鉴成熟架构／有限自写／暂缓；记录选择理由。
- 风险：授权、依赖、性能、隐私、费用与回滚；不可覆盖用户已确认的版本。
- 证据：无付费离线实验的输入、结果、漏报误报与最终验收。
- 进度：**已查到 ≠ 已集成 ≠ 已验证**。三者必须单独标记。

以上为 2026-10-11 公开仓库初筛结论，许可证和维护活跃度日后须重新核查。
## 2026-10-11 后续八专业与总导演终审路由的复用

没有安装第三方运行时和重复 Agent。复用 `agent_live_pilot` 固定 DeepSeek TLS+预算 journal、`editorial_review_lock` 锁定验收、`agent_role_contracts` 严格专业输出合同、`agent_team` DAG、`agent_handoff_audit` 与 `agent_creative_review` 的独立 QA。新代码是最薄的受控桥接，零第三方源码复制。所有供应商模型调用仍未经用户另行授权，CI 只使用合成静态帧。

## 2026-10-11 DeepSeek 单岗位试验的复用与依赖

查阅 DeepSeek 官方当前 [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/) 和 [Quick Start](https://api-docs.deepseek.com/) 确认两个支持模型 `deepseek-flash` / `deepseek-v4-pro` 与标准 HTTPS endpoint。客户端只复用现成 `agent_provider_wire`、`agent_role_contracts`、`editorial_storyboard`、`agent_team`，HTTPS/SSL、durable ledger 使用标准库 `http.client`/`ssl`/`fcntl`，不复制外部源码、不安装未授权 SDK、不开第三方代理。此处的真实 HTTP 能力默认无自动入口，GitHub CI 只用完全离线 mock 验证。当前费率必须待正式小样逐次查看官方最新价格并且由用户认可，不能依据旧数字擅自收费。

## 2026-10-11 逐镜 AI 视频制作包导出策略

优先**直接复用**仓库已有 `director_v2.compile_package` 的 Wan、Seedance 镜头级候选提示词及图形后期路线、`director_workbook.compile_workbook` 的剪辑/动作/声音证据、`agent_team.compile_team_workbook` 的十部门 QA；新文件只负责标准工单重整与严格前置验收。没有搬运外部项目源代码，没有新 third-party SDK，也没有进行真实付费 AI 请求。正式针对特定视频供应商的版本、价格和能力仍须在真实测试前额外核实。

## 2026-10-11 逐镜审阅与来源版本绑定

继续复用已有 `agent_team.fingerprint/start`、`director.validate` 与 `editorial_storyboard` 的候选计划；审核合约、HTML 转义与 SHA-256 使用 Python 标准库，避免新增不必要的外部表单和审核框架依赖。真实用户登录、可信审计、签名和审批服务此阶段未接入，不能把普通 Python 校验/自填 JSON 当身份验证或不可篡改签名。零第三方源码复制、零付费请求、零模型运行。

## 2026-10-11 创意剧本编辑的开源复用决策

本次直接重用本项目既有的 `agent_role_contracts.build_role_messages/submit_role_output`、`agent_team.start`、`article_intake.prepare_episode` 和 `director.validate`；专业扩展对照原岗位文档而不引入新编排框架。创作拓展和源稿哈希验收由标准库实现，没有复制/引入外部 Agent 库，没有变更第三方许可证，也没有进行真实 LLM 调用。先证实合成短故事由总导演与编剧形成“独立具体分镜建议”，再请求后续真实模型的隐私、费用授权，避免把单纯架构扩张误当作导演品质提升。

## 2026-10-11 长文案拆分与导演团队直入

复用仓库现有的 `director.py.validate/render_preview`、`agent_team.start/packet` 和 `agent_role_contracts.build_role_messages`，新拆分器仅使用 Python 标准库（`re`、`hashlib`），避免为了 Markdown 数字标题检索而引入完整多 Agent 或 Markdown 服务框架。此阶段无第三方代码复制、版权依赖、供应商服务调用；复杂上下文的艺术性分集仍需交给专业剧本编辑/总导演而非把正则自动识别宣传成 AI 理解。

## 2026-10-11 DeepSeek 协议与账本实现的参考来源

本轮再次查询 [DeepSeek API 官方更新](https://api-docs.deepseek.com/updates/)、[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)、[JSON Output](https://api-docs.deepseek.com/guides/json_mode/) 和 [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)，确认当前 API 模型名 `deepseek-flash` 对应 V4.1 Flash，响应 usage 包含输入缓存命中/未命中、总输入/输出数，计价区分缓存和峰谷时段。标准库实现小型请求形状与解析器，遵守已有供应商无关 `agent_role_contracts`，未复制第三方代码或导入新的框架。持久预留机制采用 Python 标准库 `fcntl`、`tempfile`、`os.replace`，仅模拟单机 POSIX 锁及断点，不是供应商费用控制保证；实时文档与发票仍需上线前再次验证。参考 CrewAI/LangGraph/LiteLLM/Pydantic AI 的历史选型仍成立，但没有作为本轮依赖纳入。

## 2026-10-11 模型网关复用选型：离线阶段

本轮查看了公开 GitHub 元数据：`BerriAI/litellm`（近期活跃，但 GitHub license 字段 `NOASSERTION`，单凭 API 元数据**不能判定代码许可证和引入权限**）、`pydantic/pydantic-ai`（MIT，近期活跃）、`langchain-ai/langgraph`（MIT，近期活跃）。前者适合未来多供应商网关与使用量集成，后两者适合类型化 agent / DAG，但这次没有核实可运行的供应商 API 版本、目标模型价格和数据传输政策，也没有复制源码或引入依赖。既有 `agent_team`、`agent_role_contracts` 和 `llm_budget.py` 已存在，现阶段选择标准库的声明式路由和精确 Decimal **离线模拟**，先验证职责边界和拦截逻辑。真正需要实时模型调用时再按明确供应商与私人数据规则审查可复用方案，而不是为了宣传“AI 团队”先引入几十个包。

## 2026-10-11 创作 Prompt/结构化输出阶段：第三方项目复核

核对公开 GitHub 元数据：CrewAI（MIT）、LangGraph（MIT）、CineCrew（Apache-2.0）均未归档，最近推送分别在 2026-10-10、2026-10-11 与 2026-09-29。当前已有 `agent_team.py` 角色字段与依赖 DAG，以及 `agent_executor.py` 模拟执行器，真正缺少的是**专业创作指令、动态镜头 Schema、无静默修复的严格输出验收**，不是新流程框架。故本轮新增标准库自研 `agent_role_contracts.py`，没有复制三方源码、增加项目安装体积或版权义务。该模块不自动对接任意模型；未来在获授权后再核实目标提供商的结构化输出兼容性、成本、许可和实时维护证据。

## 2026-10-11 多 Agent 执行器的复用/自研选择

本轮再次通过 GitHub 仓库元数据核对 3 个参考项目：`crewAIInc/crewAI`（MIT，2026-10-10 有推送）、`langchain-ai/langgraph`（MIT，2026-10-11 有推送）、`Ironieser/CineCrew`（Apache-2.0，2026-09-29 有推送），均未归档。元数据更新时间只说明最近有代码活动，**不能证明维护质量、运行成本或兼容性**。由于现有 `agent_team.py` 已负责有向图调度、版本控制、角色所有权和逐镜失效，当前仅用 Python 标准库编写 `agent_executor.py` 的 fixture-only 流程，用合成测试覆盖关键场景。没有复制第三方代码、安装包、访问模型或承担新的许可证依赖。等真正需要异步真实模型和持久检查点时，才针对供应商接口、许可和成本做更细核验；不能把这个 mock-runner 宣称为现成 CrewAI / LangGraph 系统。

## 2026-10-11 专业团队 QA 阶段复用记录

本轮复用**仓库内部已有的** `agent_team.py` 版本化 DAG、`director_v2.validate`、`director_workbook.compile_workbook` 和 `director_narrative_bridges.py` 的 `beat_link` 交接结构。继续参考此前审查的 CineCrew / CrewAI / LangGraph 三类成熟工作流模型，但本次没有重新下载、安装或合并第三方源码，**不把已有候选研究冒充本轮实时复核**。选择零外部依赖的 `agent_handoff_audit.py`，是因为当前问题只需确定性跨字段比对、源文案守恒、审片记录、定向返工与失败即阻断；完整多智能体框架会增加依赖、网络/费用复杂度，并不提高中文影视语义判定的真实性。详见 [CREW_QA_GATE.md](CREW_QA_GATE.md)。

**许可证和回退**：新增模块为本项目独立编写，无第三方复制源文件；沿用现有模块和 git 提交历史回滚。没有经过真实付费/视频提供商试验，完整测试结果仍待核实，不把提交视作已经验证的电影制作功能。
