# F01-07｜多题材离线回归与表演文本比较

日期：2026-10-31  
范围：严格 acting contract 的公开合成正反例与两份表演方向文本。  
性质：**离线结构/因果回归，不是人类盲评、不是真实演员或成片验收。**

## 1. 回归矩阵

| 场景 | 公开材料/测试 | 本轮结果 | 能证明 | 不能证明 |
|---|---|---|---|---|
| 单人克制 | `tests/test_f01_regression_matrix.py::test_single_restrained_and_dual_conflict_pass` | 通过 | 单人目标/障碍/关系/手部状态可以形成完整合同 | 表演是否动人、镜头是否好看 |
| 双人冲突 | `examples/acting-f01/public_letter_strict_contract.json` + `test_positive_strict_contract_passes` | 通过 | 双人关系对位、潜台词、手部隐藏动作与起止状态自洽 | 真实双人调度质量 |
| 荒诞喜剧 | `test_absurd_comedy_can_use_causal_environment_interaction` | 通过 | 喜剧可以使用可信的门/抽屉式偏差与因果递进，合同不把喜剧误判为违规 | 是否真的好笑、是否符合具体作品基调 |
| 零演员图文 | `test_zero_actor_scene_is_not_forced_into_performance` + `test_zero_actor_shot_needs_reason_and_passes` | 通过 | 无演员时不会被强制虚构表演；`no_performer_reason` 可追溯 | 图文镜头的信息设计与可读性 |
| 三人复杂动作 | `test_three_person_complex_action_with_fallback_passes_with_review` | 通过并产生 single-take review | 三人关系对、交物、姿态变化、环境变化与 fallback 可同时被表达 | 实际模型能否稳定生成、演员能否完成 |
| 无动机交物 | `test_unmotivated_handoff_is_blocked` | 阻断 `ACTING_HANDOFF_MISSING` | 跨角色持有变化需要有序交接事件 | 真实拍摄中的手部细节 |

结论：当前校验能覆盖**结构、因果、实体状态和明显失败模式**；它不能自动评价艺术质量，也不能替代剪辑师、演员导演或观众盲评。测试数量增加不等于表演模块已经达到 L2/L3/L4。

## 2. 同一场景的两份表演方向

材料：[examples/acting-f01/public_performance_directions.json](../examples/acting-f01/public_performance_directions.json)

场景：母亲问“你到底怎么了？”，女儿有一封会改变家庭计划的信。两份方向均为公开虚构，不含真实人物或用户私稿。

### D1｜克制家庭剧

- 目标：先把信藏住，再决定如何解释。
- 障碍：母亲观察她的手，而不是相信她的话。
- 策略：简短回答、保持眼神、左手作为稳定锚点，只在母亲低头时移动信。
- 观众感受：克制、隐忍，母女的关心与隐瞒同时可见。
- 代价：手机小屏上可能过于细微，需要更长的反应停顿或一个合法插入镜。

### D2｜荒诞家庭喜剧

- 目标：在母亲再次打开会响的抽屉前藏住信。
- 障碍：母亲一边聊晚饭，一边在最坏时机反复打开抽屉。
- 策略：用正常晚饭话题掩护，用肘部关抽屉，抽屉响时冻结，再用过度明亮的夸奖盖住声音。
- 观众感受：来自可信的家庭习惯偏差与递进反转的温暖荒诞，而不是随机笑点。
- 代价：可能压过原本安静的主题，只能用于确实需要喜剧语调的作品；严肃科普、纪录或悲剧不应强行启用。

选择标准：服从已审故事与观众体验；不在同一镜无动机混用两种语调；两种方向都**没有**经过人类盲评或真实镜头验证。

## 3. 验收层级与边界

- 本轮达到 **G1/L1**：结构、因果、版本、实体状态和明显失败模式有正反回归。
- 未达到 **G2/L2**：没有独立人员对两份表演方向做盲评，也没有记录审稿原话与版本差异。
- 未达到 **G3/L3**：没有供应商能力实测或真实镜头。
- 未达到 **G4/L4**：没有真实表演、音画、剪辑与成片审片。
- QO-F01 继续保持 `audit_pending`；不能用本文件或绿色测试关闭 F01。
