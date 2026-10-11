# AI Director — 全链路深入审计与问题闭环主账（2026-10-11）

> 这是一份**持续审计机制**，不是声称“所有问题已经查完”。每一轮在 GitHub 更新公开可核验的结果，同时保留**不确定、未做真实视频/模型试验**的状态。系统目标始终是：用户文案 → 专业总导演 → 剧本/表演/摄影美术/声音/剪辑动画/技术提示词/独立 QA → 总导演复审 → 真正能交给视频制作的工单。

## 核心交付在哪里？

- [AUDIT_FINDINGS.json](AUDIT_FINDINGS.json) — 唯一机器可读问题登记（目前 18 项，含单独编号的私有结果 checkpoint 离线修复）。每条必须标明 `AUD-xxx`、P0–P3、领域、状态、证据类型、复现/回归用例、GitHub Issue、修复 commit。
- [audit_registry.py](audit_registry.py) — CI 阻止：重复编号、没有测试却标为已修复、把没有真实素材的验证冒充已完成、P0 重要 Issue 丢失等。
- [GitHub Issues #1–4](https://github.com/pyzz58/gpt-recommendations/issues) — 重要待办有独立讨论、证据和验收点，不能只写在聊天中。
- [GitHub Actions AI Director MVP tests](https://github.com/pyzz58/gpt-recommendations/actions/workflows/ai-director-tests.yml) — 每次相关代码提交执行**离线合成 CI**、成本/隐私边界测试、公开虚构示范、`coverage.py` 多模块分支跟踪与审计登记检查。两个公开 artifact：模块覆盖率和审计状态摘要。没有任何私人稿件、密钥或实际收费 DeepSeek 视频请求。

## 真实证据分级（必须先分级，才能写结论）

| 级别 | 可据此做什么结论 | 禁止据此声称什么 |
| --- | --- | --- |
| A 代码/协议检查 | 发现确定性输入错误、结构合同、hash 漂移、权限缺口 | 真实角色好看、视频一定能生成 |
| B 离线合成故障注入 | 报错、写盘失败、网络超时、角色顺序、返工、防重试等在测试夹具可复现 | 已对真实 API/实拍模型验证 |
| C **已获许可的真实公共虚构 DeepSeek 输出** | 2026-10-11 run 38115310358 证明总导演、剧本编辑两请求成功，并暴露缺演员 ID、摄影占位等质量问题 | 其余八岗位真实表现已被验证 |
| D 真实视频/人工用户审片 | 在独立授权后验证镜头出片、连贯性、可用率、剪辑质量、人工返工 | 未经授权前绝不能开展 |
| E 长期创作产品反馈 | 对用户真实判断、完成时长、返工、留存/观看的实际改善作比较 | 单次虚构短片得到普遍效果 |

## 十二条并行审计线（每线都有负责人、验证方法与阻断条件）

| 线 | 负责链路 | 确定性离线检验 | 深度质量/证据边界 | 当前问题 |
| --- | --- | --- | --- | --- |
| A01 原文收录与分集 | article_intake → editorial_storyboard | 版本指纹、源引用、漏段/重复段、数字来源、长文分集 | 无用户稿，不验证文学质量 | AUD-008/009 |
| A02 总导演与剧本编辑 | director_brief / script_edit | 岗位 JSON、原文不可篡改、分镜一一对应、审片意见 | 仅两次真实公共虚构文本证据 | AUD-004/012 |
| A03 人物与动作 | acting / director_shootability | 人物 ID、左右手与道具、动作节拍与时码、角色跨镜状态 | 无真实人物参考图/动作生成 | AUD-003/017 |
| A04 摄影美术与空间 | camera_art / creative_production_handoff | 焦段、景别、屏幕轴线、同场景固定门/桌/灯、灯态原因 | 只能验证声明内部一致，非真实物理可行性 | AUD-006 fixed，AUD-003 |
| A05 声音对白与字幕 | sound / timeline | 旁白严格对应原稿、cue 时码、对白/静默、图字后期渲染 | 没有成片，无法实测语音音画同步 | AUD-012/013 |
| A06 剪辑、动画和情绪桥 | editing_animation | beat cut、入出点、J/L cuts、混合媒介后期路线 | 尚未进 NLE 验证实际节奏 | AUD-013 |
| A07 视频技术提示词 | ai_technical / production_delivery | Wan/Seedance 候选提示词、route、资产要求、后期 fallback | 没有真实生成模型验收 | AUD-004/017 |
| A08 独立 QA 与总导演终审 | quality_review / director_final | 源错字、结构冲突、有 blocker 拒绝“ready” | 剧情好坏只能人工与真实观众评价 | AUD-012 |
| A09 多 Agent 状态与局部返工 | agent_team / editorial_review_lock / private_result_checkpoint | DAG 前置、依赖版本、source lock、私有结果安全写入、模拟崩溃和人工零网络恢复 | 私有长期主机/账户级对账仍缺失 | AUD-002/007/018 |
| A10 DeepSeek API、成本和故障 | agent_live_pilot / agent_provider_wire | 明确授权、endpoint 固定、消耗预留、网络超时与不重试 | 不能替代真实服务商账单核对 | AUD-001/005 |
| A11 隐私、供应商与 GitHub CI | one_time_deepseek_cloud_trial / workflows | 密钥缺失禁止执行、不得公开私稿、手动运行、禁止旧任务 rerun | GitHub 管理员/供应商账户权限不由 CI 认证 | AUD-009/010/011 |
| A12 艺术质量、视频/后期和授权 | video/media assets/NLE | 视频存在时技术质量、画质、可读字幕、音乐和素材许可证 | 需真实用户授权、真实素材及合法许可 | AUD-004/013/016/017 |

此处每行“正在审计”代表**被纳入范围**，不代表全部通过；技术覆盖率只是代码的控制流测量，不是审美保证。

## 严重程度与持续闭环

- **P0 — 私稿/金钱丢失或不可逆安全事故**：阻断任何真正付费/私人连续多角色调度，先故障注入、重现、修复、再人工审查和外部对账。当前 [#1](https://github.com/pyzz58/gpt-recommendations/issues/1) 已实现私有 checkpoint 离线故障恢复，但缺长期可信私人存储、身份核验、供应商对账，生产 P0 仍未关闭。
- **P1 — 整条短片会无声跑偏、返工或失真**：人物/道具、摄影空间、QA、源文本安全、供应商计费；改代码后必须有最少一个不良用例原先通过而现在阻断。
- **P2 — 功能成熟度/格式适配/指标基础建设**：如 NLE、视觉评估、软件许可、自动化分支覆盖。不能挤占 P0/P1 资源。
- **P3 — 改善体验、优化性能**：仅在主链能提供有价值成片后处理。

每个问题按严格流程：`观察证据 → 复现最小夹具 → 区分代码/模型/媒体/人审 → GitHub 成熟开源项目调查与许可证核实 → 设计最小接入 → 提交回归测试 → 合并修复 → 全 CI → 更新 issue/登记/覆盖率 → 需要时重新审查`。

严禁“自动修复”等于模型自己多跑几遍。对真实收费请求，任何重试都需要新的明确授权，尤其响应已经发生、账单未知的情况。

## Schema 与不可信文本的第二轮专项审计（2026-10-11）

- **AUD-008 回归验证完成**：针对模型收到 JSON Schema 而返回结果没有共用校验的问题，正式融合 MIT `jsonschema==4.25.1`；[role_schema_guard.py](role_schema_guard.py) + `agent_role_contracts.execution_output_schema()` 强制校验所有十岗位，脚本编辑的扩展 `storyboard_pitch` 必须用原提示里的同一份 Schema。缺依赖或 Schema 错误在收费 `reserve` 和 HTTP **之前**拦截；旧业务含义错误码保留。
- **AUD-009 尚未解决**：注入性 `SYSTEM` / `[INST]` / tool 调用文字仍按 source_script JSON 字符串保存；测试证明不会成为 API message role，也不能靠模型输出新增 `human_approved` 字段，但这不等于真实模型不会语义上服从恶意素材。[独立 Issue #5](https://github.com/pyzz58/gpt-recommendations/issues/5) 持续跟踪；不得声称“已完全防注入”。
- 深入复现和上游证据：[RUNTIME_SCHEMA_AND_PROMPT_TRUST_AUDIT.md](RUNTIME_SCHEMA_AND_PROMPT_TRUST_AUDIT.md)。本轮仍是公开虚构离线 CI，无真实模型付费调用。

## 已经完成的第一轮可核验结论

- **已修 AUD-001：写盘异常时账本内存状态不再假装已持久成功。** 修改 `agent_live_pilot.PilotJournal.finish`，提前验证 usage，失败时回滚内存记录并将 journal 标记为 `poisoned`，继续发送一律拒绝；已有磁盘记录仍能由新进程按 `pending_uncertain` 阻止重复付费。注入文件系统失败/NaN token 费用测试。**不等于 AUD-002 私有结果恢复已解决。**
- **已修 AUD-006/007：原导演创意来源绑定与结构化空间/灯光规则**，见 [REAL_CREATIVE_TO_PRODUCTION_REPAIR.md](REAL_CREATIVE_TO_PRODUCTION_REPAIR.md)。仅保留人类未审核设计提案；没有凭空创造真实演员参考。
- **审计工具已集成上游 `coveragepy/coveragepy`（Apache-2.0）：** GitHub CI 在 Python 3.11 上使用 `coverage==7.16.1`；记录指定 21 个核心模块的 statement + branch 基线。早期 run [38116675207](https://github.com/pyzz58/gpt-recommendations/actions/runs/38116675207) 的统计为 **494 测试、83% 综合覆盖率**，模块最低部分有 `agent_team.py 71%`、`one_time_deepseek_cloud_trial.py 73%`、`director_v2.py 73%`、`agent_executor.py 75%`、`production_delivery.py 78%`。具体明细以后以 CI artifact 为准，不能宣称 83% 的业务/美学场景已被覆盖。

## 已核实的成熟 GitHub 仓库与适配策略

以下许可证来自上游 **GitHub LICENSE**（或 MoviePy 官方 pyproject.toml）检查。**不直接复制上游代码、不无条件引入全部框架**；每次要遵守原许可/署名并在必要时建立 license/dependency 列表。更多历史调研见 [GITHUB_REUSE_POLICY.md](GITHUB_REUSE_POLICY.md)。

| 目标 | 官方开源项目 / 许可证 | 本轮决策及实际状态 |
| --- | --- | --- |
| 胶合全镜 FilmDSL、人物与道具共同记忆、镜间资产卡 | [Ironieser/CineCrew](https://github.com/Ironieser/CineCrew) — Apache-2.0 | 与“AI 专业电影导演层”最贴切，但属 2026 研究代码，**优先借鉴 FilmDSL 数据/质检合同，不等于已稳定融合全部源码** |
| 私有结果写盘、durable checkpoints、人工暂停恢复 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) — MIT | 对 [AUD-002](https://github.com/pyzz58/gpt-recommendations/issues/1) 最有价值；审计幂等性/私稿加密存储后局部兼容，不直接替换现有费用保护 |
| 多专业角色/工作流编排 | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) — MIT | 作为层级角色交接参考；当前已有十角色 DAG，整仓迁移只会增加依赖和风险 |
| 多 Agent 生产级工作流 | [microsoft/agent-framework](https://github.com/microsoft/agent-framework) — MIT | 可借鉴 checkpoint/human-in-loop 等设计；不同时接入两个编排框架 |
| 运行级 JSON Schema/不可信模型回复校验 | [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) — MIT | 下一步重点评估：当前代码有 JSON Schema 草稿 + 手写验证，应先离线测试 schemas 和运行成本，再决定是否局部引入 |
| 覆盖率真实基线 | [coveragepy/coveragepy](https://github.com/coveragepy/coveragepy) — Apache-2.0 | **本轮已在 GitHub CI 中实际集成**，不是只参考 |
| 生成好媒体后的混合剪辑 | [Zulko/moviepy](https://github.com/Zulko/moviepy) — MIT | 仅在有真实合法媒体时考虑，当前无素材不安装渲染模块 |
| 已有参考影片的感知画质比较 | [Netflix/vmaf](https://github.com/Netflix/vmaf) — BSD-2-Clause-Patent | 仅能衡量部分视频感知质量，不能给原创性、剧情、人物一致性打分。没有真实媒体，暂不集成 |

## 接下来按优先级执行，不用重复选方向

1. **AUD-002 (#1)：将已完成离线故障注入的[私有 checkpoint 协议](PRIVATE_RESULT_CHECKPOINT_RECOVERY.md)部署到可信私有长期持久环境**，采用源/岗位/revision/idempotency 绑定，不允许公开 repo 落真实用户原文。
2. **AUD-008/009：成熟 JSON Schema 与敌意原稿输入测试**，把模型不合法回复的报告限定为安全错误代码，禁止回复正文泄漏到 CI。
3. **AUD-003 (#2)：依据 CineCrew FilmDSL 建人物/空间/道具资产索引与合法状态迁移，形成演员表与事件表**。
4. **AUD-012：表演/摄影美术/声音/剪辑等跨岗位音画对比质量报告**，人工评分区分可拍与无意义干扰。
5. **AUD-004 (#3) / AUD-017：** 仅在再次明确授权后做真实小规模视频生成检验，报告每镜成功/失败/成本/返工，而不把合成结果冒充真实片源。

> 2026-10-11 这轮全部操作都是**GitHub 代码、公开研究与离线 CI**；没有新调用 DeepSeek、没有提交任何私人稿件、没有重用或读取临时 API Key，也没有操作用户 Mac。
