# F01-00 / F01-01｜表演模块基线与首个公开失败反例

日期：2026-10-26  
范围：`短视频/ai-director/`，现有 acting / acting_coach 岗位与离线校验链。  
状态：**F01-00/01 已完成本轮基线核对与反例；F01-02 至 F01-09 尚未完成。**

本文件不是艺术验收，不新增第二套质量账本。状态仍以 [QUALITY_ISSUES.json](QUALITY_ISSUES.json) 的 QO-F01 为准；本轮将其从 `audit_pending` 推进为 `in_progress`，不标 `complete`。

## 1. 专业方法来源与读取边界

本轮采用的可执行方法：**给定情境 → 人物关系 → 目标 → 障碍 → 行动/策略 → 反应与潜台词 → 观众可读的变化**。这与 Uta Hagen 的六个问题一致：

- Who am I?（我是谁、当下状态）
- What are the circumstances?（时间、地点、对象、前史）
- What are my relationships?（与人物/物件/环境的关系）
- What do I want?（主目标与当下目标）
- What is my obstacle?（外部与内部阻力）
- What do I do to get what I want?（行为、动作、策略）

来源与实际读取：

- [ActBroward — Uta Hagen's Six Steps for Building a Character](https://actbroward.org/uta_hagen.php)：2026-10-26 实际读取公开页面；六个问题及“obstacle/how do I overcome it/behavior/actions”明确列出。
- [Acting Classes Central — Uta Hagen's Six Steps: Applying Them to Any Scene](https://actingclassescentral.com/uta-hagens-six-steps-applying-them-to-any-scene/)：2026-10-26 实际读取公开文章；强调目标必须能“play, not merely recite”，障碍可以内部或外部。
- 上述两篇是**教学性二手整理**，不是 Hagen 原书全文；本轮没有声称读完原书或获得任何机构认证。
- ScreenSkills 的剧本统筹/导演岗位页、BAFTA Guru、SAG-AFTRA AI Resource 在本次网络环境中返回 Cloudflare 403，**未读到全文**；只沿用项目既有 `QO-F01` 计划中的参考入口，不把它们写成已完整审读的一手资料。后续 F01-01 仍需补充可访问的表演/演技一手访谈或教材原文。

内部方法来源（实际源码/文档，不是外部认证）：

- [skills/03-direction.md](../skills/03-direction.md)：导演意图、可拍动作、staging/performance/beats。
- [skills/12-director-shot-coverage.md](../skills/12-director-shot-coverage.md)：场面、节拍与镜头的独立关系。
- [SHOOTABILITY.md](../SHOOTABILITY.md)、[director_shootability.py](../director_shootability.py)：手/道具/时间窗/动作单位的确定性物理审核。

## 2. 现有调用链（F01-00 基线）

```
agent_team (acting / acting_coach DAG)
  → agent_role_contracts.output_schema / validate_role_output
  → director_department_command (七部门工单)
  → film_continuity / continuity_contract (实体状态)
  → director_shootability (物理可执行性)
  → agent_creative_review (建议性创意检测)
  → quality_review / director_final (QA 与导演终审)
  → production_delivery / director_v2 (交付与提示词)
```

- `acting` 仍是原十阶段中的同一岗位；不新增表演 Agent。
- `agent_role_contracts.REQUIRED_OBJECT_FIELDS["acting"]` 要求：`staging.blocking/gaze`、`performance.motivation/facial_microaction/body_microaction/ending_pose`、`continuity.start_state/end_state`，以及 `beats` 的非空时间链。
- `validate_role_output` 会检查 beats 时间窗、cross-shot 实体轨迹（在 editorial handoff 路径）等结构/物理约束。
- `agent_creative_review` 对 acting 的检查目前只验证 `visible_change` 非空，不能判断目标—障碍—策略—反应是否成立。
- `director_shootability` 检查动作单位、手、道具 ID、时间重叠与拆段，不评价表演是否有心理因果。

## 3. 五类 acting 输出与职业方法的映射

| 现有输出 | 现有字段/校验 | 对应职业方法 | 当前覆盖 | 真实缺口 |
|---|---|---|---|---|
| `staging` | `blocking`、`gaze`、`spatial_constraints` | 给定情境、人物关系、空间阻力 | **部分覆盖**：能写站位/视线，但未强制“关系/权力/距离”如何影响动作 | 缺关系张力的可观察后果；缺左右手/道具持有者 |
| `performance` | `motivation`、`facial_microaction`、`body_microaction`、`ending_pose` | 目标、障碍、策略、潜台词、反应 | **只有字段**：`motivation` 常被写成一句情绪/意图，缺 objective vs obstacle vs tactic | 无 objective/obstacle/tactic/subtext/reaction 的独立约束；允许“悲伤地看着”“自然地”蒙混 |
| `beats` | `from_s`、`to_s`、`visible_change`、`performance`、`camera`、`sound` | 行动的变化、反应、停顿、节奏 | **部分覆盖**：时间链与可见变化存在 | 只要求 `visible_change` 非空；不要求 tactic/reaction 变化；可整段重复同一情绪 |
| `continuity` | `start_state`、`end_state`、`locked_entities`、`reference_assets` | 给定情境、关系、物件/身体状态 | **部分覆盖**：有起止状态与实体锁 | 缺左右手/交接/持有关系；`locked_entities` 可只列角色名而不列实际持有状态 |
| `shootability` | `mode`、`action_units`、`fallback` | 物理可执行性（不是表演质量） | **较好覆盖物理层**：手/道具/时间窗/拆段 | 不能证明动作有心理因果；不能替代表演审稿 |

结论：现有系统已经能表达“可拍的动作”，但还不能稳定要求“人物为什么这样做、他/她怎样试图克服阻力、对方如何反应、观众看到什么变化”。这是 F01 的专业缺口，不是再增加一个 schema 字段就能自动解决。

## 4. 首个公开虚构失败反例

反例文件：[examples/acting-f01/public_letter_subtext_failure.json](../examples/acting-f01/public_letter_subtext_failure.json)

虚构场景：母亲问“你到底怎么了？”，女儿回答“我没事。”，同时把一封会改变家庭计划的信藏在袖口。场景、人物和信件均为公开合成，不含用户私稿或真人。

反例中的 acting 输出满足当前结构最小要求：

- `staging` 有 blocking/gaze/spatial_constraints；
- `performance` 四个字段都非空；
- `beats` 覆盖 0–6 秒且 `visible_change` 非空；
- `continuity` 有 start/end/locked_entities；
- `shootability` 有 mode/action_units/fallback。

但它没有真正表演出来：

- `motivation` 只有“想让母亲放心”，没有与“不能让她看到信”这一障碍形成策略；
- `facial_microaction` 是“悲伤地看着母亲”，是情绪标签，不是可执行行为；
- `body_microaction` 是“自然地把信塞进袖口”，“自然地”无法验收，且没有说明哪只手、何时、如何避开视线；
- beats 只有“低头/说我没事/藏信”，没有母亲追问后的反应、停顿、掩饰或策略变化；
- 没有潜台词：台词说“我没事”，行为却在说“别靠近”；
- `continuity` 没有记录信从哪只手到哪只手、何时离开桌面/膝上。

**为什么它能通过当前检查**：`REQUIRED_OBJECT_FIELDS["acting"]` 只要求字段存在且非空；`agent_creative_review` 只检查 `visible_change` 非空；`director_shootability` 只检查物理动作单位。当前没有任何一层要求“目标—障碍—策略—反应”的因果链。

## 5. 根因

1. **结构最小化**：schema 把 motivation 当成一个自由字符串，未区分 objective / obstacle / tactic / subtext / reaction。
2. **物理与心理混层**：shootability 能证明手和道具可追踪，但不能证明人物为何这样做；不能把“可拍”当成“演对”。
3. **创意 QA 是建议性检测**：`agent_creative_review` 的 acting 分支只检查 `visible_change`，没有因果审查。
4. **缺少双人/物件持有合同**：continuity 允许只列角色名，未强制左右手、交接、视线与反应时序。

## 6. 最小下一步（F01-02 / F01-03，不在本轮冒充完成）

在现有 acting 岗位内增加一个**源绑定的表演合同**（不新增 Agent）：

- 每个角色每镜必须写：objective、obstacle、tactic/action、subtext、reaction、observable_change；
- 每项必须能追溯到剧本场次/节拍，不得新增剧情事实；
- 对手/物件必须写关系与持有者；双手动作与道具交接进入 continuity；
- 离线检查同时保留两类信号：**会阻断的硬冲突**（无来源、无目标、无可见变化、手/道具状态矛盾）与**需人工复核的泛词/重复**（“自然表演”“悲伤地看着”等），不能把审美判断伪装成确定错误；
- 用本反例做首个必须被新合同识别为“不充分”的回归用例，同时保留“沉默也可以是有效表演”的反例，避免禁词式审查。

## 7. 本轮证据与边界

- 新增公开反例 JSON 与 `tests/test_f01_acting_baseline.py`；测试只证明当前结构接受该反例、而专业缺口确实存在，不证明任何表演质量。
- 本轮达到 **G1/L1 的基线证据**：能复现结构通过但专业不足；尚未达到 L2（独立盲评）、L3（真实 AI 镜头）或 L4（成片）。
- 不调用付费模型，不使用用户真实文案/人物/媒体，不声称官方认证或行业大师审阅。
