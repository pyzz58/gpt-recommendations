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