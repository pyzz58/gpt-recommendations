# F01-00 / F01-01｜表演模块基线与首个公开失败反例

日期：2026-10-26  
范围：`短视频/ai-director/`，现有 acting / acting_coach 岗位与离线校验链。  
状态：**F01-00/01 基线已完成；F01-02/03 严格表演合同已实现；F01-04 的实体状态、关系对位、交物/姿态与环境跨镜门禁已完成软件层；F01-05 的制作可行性/替代方案已实现部分；F01-06 至 F01-09 与独立专业审稿仍待完成。QO-F01 仍保持 `audit_pending`。**

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

## 8. F01-02/03 严格表演合同实现更新（2026-10-31）

在上述基线和反例成立后，新增了**可选的严格表演合同**；旧 fixture/旧 base 不受影响，正式新系列由 `screenplay_series_delivery.build_per_episode_crew` 显式启用：

- 新模块 [director_acting.py](../director_acting.py)：
  - 校验导演锁定的 `performance_bible`：source digest、角色、关系、目标、障碍、策略习惯、潜台词、进出状态、source spans；
  - 校验逐镜逐角色合同：trigger、objective、obstacle、tactic、subtext、reaction、visible_change、ending_state、source_beat_id；
  - 校验 `hand_prop`：角色、左右手、道具 ID、时间窗、可见结果；同一手重叠动作阻断；
  - 泛词（“自然地”“悲伤地看着”等）只作为人工复核信号，不自动判错；零演员图文镜要求 `no_performer_reason`，允许沉默/无演员。
- [agent_role_contracts.py](../agent_role_contracts.py)：在 `acting_contract_mode` 下把 `performance_bible`、`character_contracts`、`hand_prop` 写入真实 model-facing schema；`validate_role_output` 在结构检查后调用严格表演校验；不新增 Agent。
- [screenplay_series_delivery.py](../screenplay_series_delivery.py)：正式新系列的每集 base 显式设置 `acting_contract_mode`，旧序列/旧 fixture 保持兼容。
- 新公开正例：[public_letter_strict_contract.json](../examples/acting-f01/public_letter_strict_contract.json)；新测试：`tests/test_director_acting.py`（正例、缺合同、过期圣经、手部重叠、泛词复核、零演员、schema 集成、legacy 不强制）。

边界：

- 这仍是**离线结构与因果合同**，不是专业演员/导演盲评，也不能证明真实 AI 表演质量。
- QO-F01 仍为 `audit_pending`：quality registry 要求未来部门在非 pending 状态前具备独立专业审稿；没有该证据时不得刷状态。
- F01-04 本轮仅完成双人实体状态与交物部分；门/窗环境状态、三人以上复杂互动仍未完成。F01-05（模型可拍性与替代）、F01-06（跨岗位同源版本/定点返修）、F01-07（多题材离线正反回归）、F01-08（真实媒体）和 F01-09（冻结交接）仍未完成。

## 9. F01-04 部分实现：双人实体状态与交物（2026-10-31）

在严格模式下新增并验证：

- `staging.physical_state.start/end`：每名出场角色的 posture、facing、hands.left/right；hand 只允许 `free`/`none` 或 continuity contract 中声明的稳定道具 ID。
- `posture_changes`：镜内坐/站等姿态变化必须写 actor_id/from/to/cause。
- `staging.relationship_map`：双人镜必须分别为两名角色写 target_id、gaze、body_orientation、distance、interaction；群体镜至少要求每个角色有一个合法对手行。
- `staging.handoffs`：交物必须有序、同一镜双方、道具 ID、时间窗、可见动作/结果；场外交接需 `visible=false` + note，并进入人工复核。
- 跨镜：相邻镜的 end→start 手部持有、姿态或门/窗状态变化若无可见动作/环境事件，也没有 `cut_note`，则阻断；写 `cut_note` 表示有意跳切并进入 review，而不是静默瞬移。
- `environment_state.doors/windows`：稳定 ID、open/closed 起止状态、changed_by 与 cause；跨镜门/窗状态跳变同样受门禁。
- 三人及以上：`relationship_map` 至少覆盖每个演员对，避免群体镜只写两名角色而遗漏第三人。
- 测试覆盖：正常交物、缺交物、缺关系对位、缺三人对位、姿态跨镜跳变、手部跨镜跳变、门/窗缺少原因、门/窗跨镜跳变，以及有意 cut_note 的复核路径。

尚未完成：三人以上的复杂调度质量、真实视频中的手部/面容/口型、供应商能力与实拍替代（F01-05/F01-08）。结构门禁通过不等于这些艺术/媒体层验收。

## 10. F01-05 部分实现：制作可行性与替代方案（2026-10-31）

严格模式新增 `staging.production_feasibility`，把专业表演选择与供应商能力判断拆开：

- `professional_intent`：为什么采用当前表演/调度。
- `physical_complexity`：low/medium/high，由交物、三人以上、动作单位数量、道具动作数量与姿态变化辅助复核；低报进入 review。
- `model_risk`：具体的模型风险描述，不声称模型必然成功或失败。
- `capability_evidence`：none/documented/tested；documented/tested 必须提供 `evidence_ref`，tested 还必须提供 `test_environment`；没有真实测试只能写 none。
- `fallback_route` 与 `fallback_preserves_story`：高复杂度 single_take 若没有具体替代路线则阻断；有替代路线时进入 review，而不是宣称模型一定不能做。
- 既有 [director_shootability.py](../director_shootability.py) 继续负责逐动作时间、手/道具、动作密度和单镜失败信号的物理预检；本项只补“表演意图 vs 模型能力”的分离，不重复其逻辑。

仍未完成：经验证的供应商能力表、真实模型试拍、真实表演/手部/口型审片。F01-05 保持部分实现，不能因结构测试通过而关闭。
