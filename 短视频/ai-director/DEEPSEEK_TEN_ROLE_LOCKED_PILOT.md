# 十部门专业导演团队：DeepSeek 单岗位受控执行通道

**开发状态：GitHub 代码完成，测试仅用合成故事与静态 HTTP 模拟帧，真实 DeepSeek API 调用次数为 0。**

模块：`agent_live_crew.py`；共用此前的 `agent_live_pilot.PilotJournal` / `DeepSeekHTTPSClient` / `agent_provider_wire` / `agent_role_contracts`；专项测试：`tests/test_agent_live_crew.py`。

## 解决的问题

此前 `agent_live_pilot.run_one_creative_task` 只支持未锁定文章创意阶段的两个角色（总导演创意提纲 `director_brief`、剧本编辑 `script_edit`）。用户要的是完整的专业制作团队，不是一个模型轮流输出笼统分镜。

新模块允许基于**已建立编辑规划快照**的专业团队按十阶段 DAG 分别取任务，并且为每次模型调用**单独**取得合法许可、具体 role/revision、单集原文及锁定方案版本绑定、持久预算预留，最后严格验收岗位输出。它沿用原先真实 OpenAI 兼容 DeepSeek Chat Completions 格式，并不增加新的 Agent 角色或改变模型设置。

## 十阶段与执行依赖

| 岗位 ID | 实际产物 | 前置条件 |
| --- | --- | --- |
| `director_brief` | 总导演创意提纲及不变的真实来源约束 | 锁定版本的首次任务 |
| `script_edit` | 剧本编辑结构、戏剧节拍及未授权改写提案 | `director_brief` |
| `director_lock` | 统一全片视觉、情绪、音频准则和逐镜叙事目标 | `script_edit` |
| `acting` | 逐镜人物站位、动作分拍、道具连续性和单镜可拍性 | `director_lock` |
| `camera_art` | 景别、摄影运动、布光、美术、环境关系 | `director_lock` |
| `sound` | 精确源文配音、配音时间、字幕时间、音乐音效 | `director_lock` |
| `editing_animation` | 镜间剪辑、动画后期、旁白与动作节拍衔接 | 表演、摄影、声音三个部门完成 |
| `ai_technical` | 视频模型/后期制作路线及技术指令 | 剪辑动画部门完成 |
| `quality_review` | 独立跨部门 QA：将矛盾送回负责部门，不虚假批准 | `ai_technical` |
| `director_final` | 总导演整合复核，最多“交付人工审核”，绝不能宣布发布或付费授权 | `quality_review` |

这十个任务都是**代码可调用的专业角色协议**。CI 的静态 JSON 响应并不是十位真实 DeepSeek Agent 已经工作，也不能证明导演艺术质量。调用者要先在未来私有运行环境获取真实身份和逐次授权才可调用 HTTPS。

## 两条不同的入口，互不偷换版本

1. 文章第一轮创意：`agent_live_pilot.run_one_creative_task` 只允许最初两个专业角色。其后须检查创意分镜并经 `editorial_review_lock.lock_planning_snapshot` 生成**规划**版本。
2. 已规划锁定的整队：`agent_live_crew.inspect_locked_role` 与 `run_one_locked_role` 只接受严格核查的锁定快照 + 单集原文 + 对应 ten-team state；每个角色使用既有 `roles.build_role_messages` 和 `roles.submit_role_output`。即使是未改写原文的专业分镜版本，也不能偷用上一轮 `base_digest` 旧任务账本。
3. `locked_crew_overview` 可随时得到 ready/completed/open 角色信息，不泄漏整篇原稿、用户真实文案或完整 Prompt。所有运行默认为 **无自动队列、无后台执行、无自动下一任务、无支付和视频生成**。

## 四道安全/质量硬门槛

**第一道：单次明确授权。** `explicit_pilot_permit` 要求 role、revision、单集原文 SHA256、锁定 plan SHA256、供应商模型、人民币预算上限、一条具体任务的隐私/消费确认。配置对象只是预算，不是授权。用户之前说“继续开发”，不能算真实模型/跨境文本传输许可。普通 JSON permit 不是数字签名，仍需受信任私有 UI 核验真实用户身份。

**第二道：锁定文案。** 每次发包前均重新校对快照、整片方案结构、团队账本 SHA256、单集原文的 SHA256、岗位依赖及版本 revision。错期、漏任务、改稿都在发包之前拒绝。

**第三道：持久预算与不确定失败。** 单任务按保守输入字节代理 + 最大输出 tokens 预留费用，先加写入排他 `PilotJournal`、成功 fsync 后才允许一次 HTTPS POST。网络超时/模型失败/无效 JSON/费用预留不匹配都不自动重试、不当作已退款；存储只含摘要、token 和费用，不记录用户原稿、Prompt、密钥或返回正文。预算不是供应商层面的真实硬封顶，还应在提供方账号单独做额度限制。

**第四道：独立 QA 和总导演审查。** 进入质量审核/总导演终审前，系统读取跨部门交接的来源一致性、动作/相邻节拍、声音、图形 claims、镜头技术路线和创意具体程度。QA 可以在发现问题时要求“返工”，却**不能在已有硬冲突时声明可以进入总导演终审**。终审如尝试宣布“ready_for_user_review”，会检查 QA 及创意阻断项；最终仍是“等待作者审看”，不替用户批准媒体发布。

## 用户可看到的最终产物

十部门经合法真实模型分别执行、后期审稿完成后，`agent_team.compile_team_workbook` / `production_delivery.build_locked_crew_delivery` 仍是权威交付入口，导出针对每个镜头的 Wan/Seedance 视频候选提示词、连续性、声音、时间线与后期工程任务。当前**没有任何已拍视频或真实模特资产**，真人编辑审核、研究证据核验、模型实际能力与支付权限均待未来明确授权完成。

## 当前验收与未来待做

CI 用**虚构信封故事**与合成 DeepSeek 响应跑完整十岗位任务交接（包括跨岗位平行可用阶段）、源文与预算哈希拦截、逐 role+revision 授权、模仿错误声画冲突后 QA 的拒绝/定向返工、缺许可、超时和重复调用阻断。**这验证工程流程和 contract，不验证 DeepSeek 的实际创造力或视频效果。**

下一轮如果真正实机试验，需要先确定：单集测试是否可发给 DeepSeek、私有执行位置、精确模型、当前官方价格、实际人民币上限、供应商 API Key 的安全读取、对账与审片。不能把公开 GitHub CI 用作用户真实私人稿件的试验环境。
