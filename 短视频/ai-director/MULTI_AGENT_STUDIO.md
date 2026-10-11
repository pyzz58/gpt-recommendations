# 多 Agent AI 影视导演团队（v0.1：零付费调度核心）

## 产品定位

**用户只输入文案。系统内部组织总导演、剧本编辑、演员动作、摄影美术、声音、剪辑动画、AI 技术导演，以及独立连续性与质量审查，产出一份结构统一的完整短视频导演交付书。**

本项目**不是**让八个 AI 随意聊天，也不是制作模型本身。总导演根据同一份权威源稿及导演圣经分配专业任务；专业部门负责各自交付；QA 只评审、不改稿；总导演合并意见决定是否返工；最终成果仍然是 `director_workbook.py`，不是八份互相矛盾的报告。

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
| `director_lock` | 总导演 | 剧本编辑 | global_direction：统一镜头、灯光、音乐、字幕与成本约束 |
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
- 本轮新增合成测试文件 `tests/test_agent_team.py`（20 项）。**最新版完整仓库尚未通过同一份代码快照的 CI 验证**；测试提交不等于已经实际运行通过。
