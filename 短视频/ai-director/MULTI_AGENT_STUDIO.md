# 多 Agent AI 影视导演团队（v0.1：零付费调度核心）

**专业岗位创作质量与跨部门验收标准：**[ROLE_CREATIVE_CONTRACTS.md](ROLE_CREATIVE_CONTRACTS.md)。该文件对动作、摄影、声音、剪辑动画、AI技术导演、总导演及 QA 逐一列明实际可检查的交付内容；属于质量合同，不代表已接入真实模型。\n\n## DeepSeek 供应商协议与模拟持久预留（新增）

[PROVIDER_PROTOCOL_AND_DURABLE_BUDGET.md](PROVIDER_PROTOCOL_AND_DURABLE_BUDGET.md) 描述了 DeepSeek Chat Completions **离线协议实现**：构建 `deepseek-flash` 的 JSON 输出 POST body、核对回复中的真实供应商申报 Token 与缓存拆分，并用调用方声明的费率算账。单独的 `PrivateReservationJournal` 可在未来经授权的私有运行环境保存不含文案的状态记录，模拟超时/重启留下未决预留，拒绝未核销的自动重试。当前 **没有真正的网络传输器，也没有真实发票对账**。现有十阶段专业 DAG、输出验证及 QA 无变更。

## 模型路由与模拟预算预检（新增）

[MODEL_GATEWAY_AND_BUDGET.md](MODEL_GATEWAY_AND_BUDGET.md) 对应 `agent_model_gateway.py`。它让既有 10 个岗位的上下文和 JSON 输出合同通过**声明式模型 Profile 路由**连接：每个岗位选择一个供应商/模型别名、Token 限额、最高预估 CNY 单价，并由 `OfflineBudgetBook` 在模拟回复前检查总预算、总次数。成功的合成回复走 `agent_role_contracts.submit_role_output`，非法 JSON、岗位越权及前后剧本冲突仍不能合入团队账本。

重要：唯一可执行的是预写文本 `OfflineMockTransport`；没有真实网络适配器、真实供应商报价核验、模型调用或成片制作。UTF-8 bytes + 1024 的输入代理不是任何供应商 tokenizer 的精确上限；`actual_billed_cny=0` 只说明本次程序没有外部调用。预算账本仅保存在内存，不能当作未来实际消费的崩溃安全付款系统。

## 专业岗位可执行创作合同（新增）

[PROFESSIONAL_AGENT_CONTRACTS.md](PROFESSIONAL_AGENT_CONTRACTS.md) / `agent_role_contracts.py` 已为总导演开题、剧本编辑、锁定导演圣经、动作表演、摄影美术、声音、剪辑动画、AI 技术导演、QA 与总导演终审这十阶段建立**不同的专业创作提示词**、动态岗位 JSON Schema 与严格验收函数。复用原有 `SPECS`、依赖快照、字段所有权和 source_digest；**只处理内存对象，不提供任何网络/模型/付费调用接口**。

核心门禁：剧本改写提案必须标待批准；动作 beats 覆盖真实秒数；旁白逐字保持原稿；剪辑 beat_link 指向真实已交付的动作首末节拍；生产路线、字幕/配音 cue、可执行后期步骤各有结构规则。任何模型自然语言写得多漂亮，也不能越过源稿或数据合同。严格 JSON 通过只能说明可交给原有部门协作和人工创作复核，**不证明艺术品质或成片效果**。

## 多岗位执行器（模拟流程已接入）

[AGENT_EXECUTION_LAYER.md](AGENT_EXECUTION_LAYER.md) / `agent_executor.py` 实现了正式 DAG 的**离线逐岗位提交执行循环**：从 `director_brief` 到 QA 再到导演终审，按同一份上游工作包执行既有权限校验和失效重做；需要预写好的 `FixtureOnlyAdapter` 岗位结果，缺少结果就停止。默认在 `director_final` 前暂停。此层既不是收费模型传输，也不会自己创作剧情、摄影、动作或剪辑；没有真正启动八个 LLM。

经过 GitHub Actions 检查的版本 `79d9c3d7` 已通过 **278 项离线 Python 测试**（含 14 项新增执行器集成测试）：[执行记录](https://github.com/pyzz58/gpt-recommendations/actions/runs/38106703964)。后续提交需要再次核对对应的实际 CI 状态。

## 产品定位

**用户只输入文案。系统内部组织总导演、剧本编辑、演员动作、摄影美术、声音、剪辑动画、AI 技术导演，以及独立连续性与质量审查，产出一份结构统一的完整短视频导演交付书。**

本项目**不是**让八个 AI 随意聊天，也不是制作模型本身。总导演根据同一份权威源稿及导演圣经分配专业任务；专业部门负责各自交付；QA 只评审、不改稿；总导演合并意见决定是否返工；最终成果仍然是 `director_workbook.py`，不是八份互相矛盾的报告。

## 2026-10-11 GitHub 离线回归验收（已实际执行）

**已核对运行日志：** 代码修复版提交 `3ecfe01d4e82a89c551748c1301c0cfdff426247` 在 GitHub Actions [第 38106308398 次运行](https://github.com/pyzz58/gpt-recommendations/actions/runs/38106308398) 中执行 `python -m unittest discover -s tests -v`，结果 **264 项通过、0 项失败、0 项错误**；原有 `local_director doctor`、戒烟样例与三集长文案的验证、编译和预览步骤均在相同 workflow 里成功执行。运行环境是 GitHub 托管 Ubuntu + Python 3.11.17；**并非用户 Mac 测试，也不是收费模型、真人审片或 MP4 生成验收**。

**兼容性修复：** 原 `actions/checkout@v4` / `actions/setup-python@v5` 因 Node.js 20 停用受到弃用警告；更新为已核对上游 README 的 `@v6`，并将多 Agent 核心模块纳入 `py_compile`。改动后 [第 38106229864 次运行](https://github.com/pyzz58/gpt-recommendations/actions/runs/38106229864) 通过 260 项测试，日志不再含 Node 20 警告；最终上述 264 项运行也无此警告。

**规则误报修复：** 使用权威基础分镜信息判断 `shootability=None` 是否合理——纯二维图表、无真人动作的镜头不再被误标为待拍；最后一镜本身不需要指向不存在的下一镜 `narrative_bridge`，但非末镜仍需交接。新增四项合成回归证明相关边界；严格交付仍要求来源指纹、既有蓝图门禁、质量证据等检查通过。

**历史失败透明记录：** 初次新增四项测试时，提交 `04257f2` 的测试文件因两处 JSON 样式嵌套字典缺少闭合花括号导致一次 CI 失败（[运行 38106280432](https://github.com/pyzz58/gpt-recommendations/actions/runs/38106280432)）；在 `3ecfe01` 修复后成功。该失败是测试代码语法错误，不涉及用户数据与收费调用。

目前结果：**离线源码回归通过**；真实多模型协作/成本核算、影视美学质量、视频生成、Mac 性能和实际发布依然**未验证**。

## 创作交付自动检查（新增）

`agent_creative_review.py` 提供 `review_deliverable` / `review_team` / `review_packet`，对专业交付的具体创作证据作保守检查：镜头缺漏、空泛内容、表演动作可观察性、声音职责、剪辑叙事桥和制作路线。`agent_team.compile_team_workbook()` 现在额外输出 `creative_quality_review`，但**不绕过原有结构审核**，且不自动批准。现阶段为**提示与人工复核**，不是严格创作质量评分；过去的草稿仍可存在并被标记。对应合成单元测试 `tests/test_agent_creative_review.py` 已由上方 GitHub CI 全量回归涵盖；这只证明确定性代码测试通过，不是艺术质量评分。

## 跨部门一致性、总导演返工和最终交付门禁（新增）

- 新增 [agent_handoff_audit.py](agent_handoff_audit.py)：零网络、零模型调用，只核对**可证实的部门冲突**：声音部门 `voiceover.text` 与权威旁白不一致，剪辑 `beat_link` 对不上动作部门实际首末节拍，动作/运镜/音效时码越界，技术部门使用不支持的 route，后期动画自相矛盾，以及图表引用未登记论据或修改已锁定的剪辑转场。没有读取原始 `base` 时，只能执行不依赖原文的检查；原文比对在最终编译时再次执行。
- `agent_team.packet(..., "quality_review")` 会附带独立检测报告；如果检测出明确硬冲突，QA **不能**将建议写成 `ready_for_director_review`。总导演 `director_final` 也不能强行把明确硬冲突判为 `ready_for_user_review`。
- `agent_team.propose_director_revisions(base, state)` 根据独立硬阻断与 QA 自己登记的 blockers，**只生成**按责任部门和受影响镜头汇总的返工建议；默认不包含主观/弱证据问题，可传 `include_reviews=True` 让导演决定是否处理一般提醒。建议不会改写任何状态、文案或生成费。
- `request_planned_revision(base, state, proposal, showrunner_approved=True)` 只有对**当前数据重新计算后仍匹配**的建议，才可交给原有 `request_revision` 执行 DAG 失效、邻镜剪辑重审、历史保留。该布尔值只是编排层批准记录，**不能验证真实人物身份**，不是用户的人审或费用授权。
- `compile_team_workbook(base, state)` 在汇编前重新独立核查原稿、QA 状态与部门硬冲突。有 blocker 会抛出错误，**不会生成最终导演工作单**；没有 blocker 但创作细节不足时，只生成明确标记 `team_delivery_gate.status=draft_needs_review` 的审阅草稿，绝不宣称完整。
- `compile_team_workbook(..., strict=True)` 还要求既有 `director_review.production_blueprint_ready` 为真、没有开放的启发式创作检查或交接提醒，才标 `ready_for_human_review`。这也只是**文字交付准备就绪**，不代表真人批准、实际拍摄、版权验证或付费许可。
- [合成离线回归测试](tests/test_agent_handoff_audit.py) 涵盖跨岗冲突、声画时间码、任务包 QA 阻断、合并返工、审批旗标、版本保护及交付拒绝。测试代码已提交 GitHub，且已在上述 264 项成功的全量 GitHub Actions 回归中执行；不能将其等同于真实收费模型与视频验收。

**边界**：当前并未做语义推理。例如不能从中文形容词中证明人物表演是否合情合理，或仅凭文本判定镜头色彩匹配；这些必须由导演真人审片和未来经批准的实际模型试制解决。现有 `assemble_direction` 是中间方向草稿合并功能，不是最终成片或正式工作单发布接口。

## 本轮真实实现 / 尚未实现

已经在 GitHub 新增 `agent_team.py`：

- **十阶段、八类专业角色的有向依赖图（DAG）**。一集分配一份部门级任务，而不是「每一个镜头 × 每个 Agent」地重复发起大量调用。
- 专业岗位 **字段所有权** 与提交合同；不能越权修改其他专业的 `direction_v02` 字段，不能通过交付包修改原始文案、批准事实、时长和人物 ID。
- 每份工作包携带源稿 SHA-256、上游任务版本、共享上游交付、允许修改的部门字段及本次返工镜头范围；过期/伪造版本不能提交。
- **总导演批准的定向返工**：例如动作部改 S09，剪辑部自动重审 S08/S09/S10，而摄影/声音先前有效成果不必重来。变更请求存进事件流水，不静默抹掉前一版本。
- **总导演最终交接**：编译为现有 `direction_v02` 的各部门字段，可进一步交给 `director_v2.validate()` 与 `director_workbook.compile_workbook()` 做完整导演结构审核。
- **无付费运行接口**：计划、查看下一批任务、准备任务包、提交离线成果、申请定向返工；所有这些函数只处理 Python 字典，不调用 LLM、不生成/上传视频，也不需要联网。

**尚未实现**：真正让模型独立扮演这些岗位、模型间上下文管理、并行 LLM 请求执行器、自动文本内容评判或真人最终批准。当前的 `agent_team.py` 是**可执行的调度与数据合同**，不是「八个 AI 已经开始工作」。为未来接入 DeepSeek/Codex 等模型预留接口，但实际模型调用必须重新获得用户授权、人民币预算与次数上限。

## 团队岗位与协作顺序

| 任务 ID | 负责人 | 依赖 | 允许提交的工作 |
|---|---|---|---|
| `director_brief` | 总导演 | 无 | creative_brief：目标、风格、人物及不可修改信息 |
| `script_edit` | 剧本编辑 | 总导演开题 | story_treatment：钩子、剧本节拍、改写建议（只能提案） |
| `director_lock` | 总导演 | 剧本编辑 | global_direction：统一镜头、灯光、音乐、字幕与成本约束；shot_objectives：每镜情绪、可观察变化和视觉焦点 |
| `acting` | 动作表演导演 | 导演圣经锁定 | staging、performance、beats、continuity、shootability |
| `camera_art` | 摄影美术导演 | 导演圣经锁定 | camera、art |
| `sound` | 声音导演 | 导演圣经锁定 | sound、speech |
| `editing_animation` | 剪辑动画导演 | 动作 + 摄影 + 声音 | editing、animation、graphics |
| `ai_technical` | AI 技术导演 | 剪辑动画 | generation；根据真实设计选择视频、静态图或合成路线 |
| `quality_review` | 独立场记/QA | 技术导演 | qa_report（只读评审、记录责任岗位和具体问题） |
| `director_final` | 总导演 | QA | director_decision：仅批准**提交给用户审阅**，或退回修改 |

`acting`、`camera_art` 和 `sound` 在导演圣经确认后**同时具备条件**。多 Agent 在这里表示专业岗位与交付合同，是否真的并行调用模型由未来专门执行器决定；本轮**没有**任何并行收费调用。

## 共享权威、角色越权与协作返回

项目中只有一份**源文案/基础分镜**，以 `base_digest` 锁定版本。剧本编辑不得未经用户确认就改写 `base.shots[].narration` 或 `claims`；可在 `story_treatment.source_change_proposals` 列明建议，等待总导演协调以及需要时请用户审阅。

总导演在 `director_lock` 产出共享 `global_direction`，为每个专业部门提供相同的视觉语法和故事节奏。工作包 `packet` 会把它及相关上游交付作为上下文，避免各自建立冲突的人物或美术设定。每个部门只修改自己的 `fields`，不能直接覆盖原稿或其他部门成果。

经过 `qa_report` 检查后，问题要指定责任部门和受影响镜头。如果 QA 认为 S09 的右手拿手机动作有误，QA **只能提出建议**；总导演发出 `request_revision(..., "acting", ["S09"], ...)`，会使该部门修改、下游剪辑重审 S08/S09/S10，AI 技术和 QA 随之重新检查。未受影响的摄影美术与声音保持完成状态。这里是**调度层审批记录**，不是身份认证或真人的签名；不能用来授权付费。

## 将专业交付合并到已有工作单

`assemble_direction(base, state)` 在全部协作岗位和总导演终审完成后，将各岗位独有的 `direction_v02` 字段合并，还保留 `qa.human_approved=false`。**不会**把剧本编辑的改写建议偷偷覆盖原文。

`compile_team_workbook(base, state)` 继续使用已有 `director_v2.validate` 和 `director_workbook.compile_workbook`，因此已有剪辑、动作、字幕、叙事跨镜和连续性检查继续生效。团队交接记录附加 `team_handoff`，但即使是总导演 AI 审核完，也仍然要真人审片。未通过现有导演字段校验不能称为完成。

### 未来私有部署时的 CLI 示例（**当前不要在 Mac 执行**）

```bash
python3 agent_team.py plan --base plan.json --out agent_team.private.json
python3 agent_team.py ready --state agent_team.private.json
```

`plan` 不会覆盖同名已有文件；这是防止意外抹掉人工修改和旧审片记录。当前只做 GitHub 代码开发，用户无需执行。任务工作包与提交使用 Python API `packet(state, task_id)`、`submit(state, envelope, payload)`、`request_revision(state, ...)`，新执行器接入前不包含付费/云端行为。

## 为什么暂不直接装 CrewAI / LangGraph？

做了三份上游仓库检查：

| 仓库 | 公开许可证与能力 | 当前选择 |
|---|---|---|
| [CineCrew](https://github.com/Ironieser/CineCrew) | Apache-2.0；Showrunner、Story Editor、Acting Coach、Cinematographer、Technical Director、VO Director、Reviewer 与 FilmDSL 共享规格 | 借鉴专业分工、共享事实库、分层审查；**没有复制上游源码** |
| [CrewAI](https://github.com/crewAIInc/crewAI) | MIT；分层 Crew/Flows、专业任务编排与结构化输出 | 借鉴 manager→specialist 设计；不引入其运行依赖 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | MIT；有状态图、持久执行、条件分支、人审 | 借鉴状态/恢复/定向返工思想；当前零依赖更轻便 |

现在真正的难点是**专业部门如何交接正确的创作结果**，不是是否把它们包进更大的框架。先用零依赖合同验证工作流，未来证明确实需要跨进程持久检查点与真人交互，再做薄适配；避免额外 Python 环境、版本冲突和无意义 Token 消耗。

## GitHub-only 和费用边界

- 源码仅保存到公开仓库 `pyzz58/gpt-recommendations/短视频/ai-director`。不得提交用户真实文案、剧本、真实人物照片、私人 `jobs/`、密码或付费额度。
- **不在用户 Mac 同步、下载、运行或安装**，直到用户明确说可以开始本地运行/部署。
- `budget_policy` 中全部收费调用都是 `false`；`release` 中的 `human_approved`、`paid_api_authorized`、`media_generated`、`publishing_allowed` 永远不能被这个规划模块置为 true。
- `director_ai_review_complete` 仅指“模拟总导演审阅了交付数据”；不代表真人同意、实际画面质量、版权许可或供应商已调用。
- 本轮新增合成测试文件 `tests/test_agent_team.py`（20 项）。包含这些测试在内的整仓 264 项单元测试已由上述同一版本的 GitHub CI 记录确认通过。

### 当前接入的阶段边界

**当前调度器从现有 `plan.json` 开始，而不是直接从原始文案创建全套分镜。** 总导演 `director_brief` 是进入专业协作后的首项任务；已有文案→基础计划的生成入口暂时保留，后续需要再与总导演的原文审稿接成一条完整流水线。不能把这一阶段说成“用户输入文案后八个 Agent 已经自动工作”。

`agent_team.start(base, source_text=...)` 可选择把原始文案的 SHA-256 附在任务账本里，而不保存文案正文；岗位包携带该指纹。真实原文必须由未来私有运行环境提供给获授权的岗位，不能写进公开 GitHub。若不提供原文，`source_review_bound=false`，不会冒充已经审过原文。

专业部门接收 `director_lock.shot_objectives`，因此**每个镜头的具体戏剧任务属于总导演**，摄影、动作等岗位只围绕它执行，不各自重写故事目标。

