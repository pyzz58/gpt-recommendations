# 专业影视 Agent 创作提示词与严格 JSON 合同 v1.0

> 当前处于 **GitHub-only 离线研发**。新增 `agent_role_contracts.py` 只能生成未来模型可用的岗位消息、输出约束，并验收**外部已提供的文本**；它不会自己调用 DeepSeek、Codex、任何 LLM、网络、视频生成器，不上传数据、不执行付费 API、不部署 Mac，也不能冒充真人审片。

## 本轮真正实现的功能

| 角色任务 | 具体导演职责 | 合同字段与可检验项 |
|---|---|---|
| `director_brief` / 总导演开题 | 观众是谁，核心戏剧冲突、钩子、情绪与结尾回报是什么 | `creative_brief` 内目标观众、核心冲突、情绪、不可动事实、待核查假设 |
| `script_edit` / 剧本编辑 | 开头抓人、逐镜因果关系、剧本节拍与原稿修改建议 | `story_treatment.beat_map` 与所有源镜头一一对应；改稿仅为 `approved=false` 的提案 |
| `director_lock` / 总导演锁定 | 全片视觉、声音、信息图安全、成本与逐镜目的 | `global_direction` 必须具备六大项；每镜 `shot_objectives` 明确情绪、可见变化、视觉焦点 |
| `acting` / 动作表演 | 逐秒动作、人物走位、眼神、面部细节、道具首尾状态和 AI 可拍性 | `beats` 无重叠和时间缺口、覆盖实际 duration；真人 AI 镜必须声明动作可拍性 |
| `camera_art` / 摄影美术 | 景别、构图、镜头运动触发、光线物理逻辑、空间与色彩 | `camera.move_trigger_s` 在镜头范围内；摄影镜头起止、原因、布景光源等必须给出 |
| `sound` / 声音导演 | 旁白、对白、配乐、环境音、音效 cue、字幕时码 | `speech.voiceover.text` 与原稿严格一致；各 cue 不得超镜头 |
| `editing_animation` / 剪辑与动画 | 每个 cut 的因果、视线/动作交接、动画图层与声音桥 | 相邻 `beat_link` 必须引用动作部门末/首 beat；剪辑转场不得偷改 base；片尾无需下一镜 |
| `ai_technical` / AI 技术导演 | 视频/静态/后期路线选择、参考资产需求、候选提示词和降级制作路线 | `generation.route` 白名单；AI 视频需正反向 prompt；后期路线需具体 `postproduction_steps` |
| `quality_review` / QA | 源稿守恒、跨部门矛盾、时间线、连续性，阻断归因和返工建议 | `qa_report.blockers[]` 包含责任岗位、镜头、代码、详情、修改建议；不能忽略硬冲突 |
| `director_final` / 总导演终审 | 核对 QA 后决定是否**仅提交用户审阅**，记录开放风险 | `director_decision.decision` 仅支持请求修改或供用户审阅；不颁发真人、费用或发布批准 |

## 模块调用原则

1. `build_role_messages(base,state,task_id,source_text=...)` 用既有 `agent_executor.role_context` 获取**当前可执行**岗位包，并在内存中组装岗位专属 `system/user` 消息以及动态 `output_json_schema`。原始素材和上游岗位交付只能以数据形式出现；即使素材中包含“忽略规定”等命令式文本，也不能覆盖系统职责。
2. `output_schema(state,task_id)` 将现有 `SPECS`、严格岗位必填项及返工镜头范围转成无额外依赖的 JSON Schema（draft 2020-12）结构。格式约束是一层基础筛选，并**不保证**独立模型提供商一定支持该 Schema。提供商之间可能需要未来的具体适配。
3. `parse_strict_json(raw)` 不接受 Markdown 围栏、多个 JSON、重复键、非法 NaN/Infinity 或超长响应（上限 220,000 字符）；**绝不暗中修复模型输出、替模型填空或删原文**。
4. `validate_role_output(base,state,task_id,raw,source_text=...)` 先校验当前任务确实 ready、权威 base/source 摘要吻合、原有 `team._validate_payload` 岗位字段所有权及准确镜头范围，再执行岗位专业细节校验，并对 QA/总导演执行独立源稿门禁。无额外依赖、无网络调用。
5. `submit_role_output(base,state,task_id,raw,...)` **仅当调用方已提供字符串**，经过上述校验后使用原有 `team.submit` 创建新版本账本；不会将提案静默改写到 base。它不是模型调用接口，也不是自动审批器。

### 私有数据规则

提示词本体在未来运行时可能包含完整原始文案、画面、角色设定和所有上游创作决定，因此 **`build_role_messages` 返回的对象绝对不得保存到公开 GitHub，不能作为公开 Actions 日志、错误追踪或测试快照输出**。本轮只在公共仓库保存不含用户数据的程序与合成测试。

`build_role_messages` 返回 `contains_private_material=true`、`external_model_call_authorized=false`。字符串指令中的“禁止调用外部工具”只能影响模型的行为倾向，**不是安全沙盒保证**。真正的阻断靠当前模块完全没有网络/付款接口、与原有 `FixtureOnlyAdapter` 的精确类型限制；未来真正的提供商适配器需单独核查传输、模型权限和费用预算。

### 精确的改稿与返工边界

- 剧本编辑修改文案只可产生 `source_change_proposals`，且明确 `requires_user_approval=true`、`approved=false`，不得把提案应用到 `base`。
- 动作部门只交自己的 `staging/performance/beats/continuity/shootability`，摄影与声音分别拥有自己的板块；其它部门必须走总导演定向请求，不可将输出混写到同一个自由文本报告里。
- 剪辑部门需读取当前已完成的动作部门 `beats`，实际索引/镜头切点必须对应；即使模型文案写得流畅，索引错了也明确拒绝。
- 多次返工会依据现有 `revision_scope` 精确生成所需镜头的 schema；初次交付必须覆盖所有镜头，不能偷少做。
- 即使严格 JSON 通过，后续仍要经过原有 `agent_team` 审批、`agent_handoff_audit`、`director_v2.validate`、`director_workbook` 的结构/导演交接门禁，以及真正的人审和视频小样验收。

## 后续模型接入须另行批准

当前未实现：网络模型调用、支付、SDK/供应商传输、Token 上限/超时、异步并行、真正 LLM 的上下文与出错重试、视频制作及人工批准身份认证。后续如果用户单独批准供应商/模型/传输私有文案/调用预算与次数，需要增加严格隔离的执行适配器，不能通过修改账本中的 `budget_policy` 绕过这些条件。

## 验证

新增 `tests/test_agent_role_contracts.py` 以合成双镜头故事做真实 Python 结构化测试，不含真实私人文案；覆盖十个岗位的严格提交、提示词/Schema、源稿改写禁令、动作时间码、配音逐字、剪辑索引、后期路线、QA 阻断和定向返工。当前完整结果应以该文件最后一次改动后对应的 GitHub Actions 日志为准，不能把一次成功的早期提交当作最终版本测试通过。
