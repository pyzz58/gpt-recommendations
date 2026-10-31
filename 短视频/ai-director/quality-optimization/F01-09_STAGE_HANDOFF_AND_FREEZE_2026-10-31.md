# F01-09｜表演阶段冻结与 F02 交接

日期：2026-10-31  
机器可读交接：[F01_STAGE_HANDOFF_2026-10-31.json](F01_STAGE_HANDOFF_2026-10-31.json)  
PR：[#78](https://github.com/pyzz58/gpt-recommendations/pull/78)（Draft，stacked 在 #77 上）

## 1. 当前结论

**F01 软件层进入 review-ready；QO-F01 仍为 `audit_pending`。**

这不是“表演模块完成”。当前没有独立专业表演盲评，没有授权的真实表演镜头，没有真实手部/面容/口型/跨镜情绪审片，也没有真实成片。F01-08 保持阻塞。

## 2. 已完成与部分完成

| 子阶段 | 状态 | 证据边界 |
|---|---|---|
| F01-00 | 基线已记录 | 调用链与五类 acting 输出映射 |
| F01-01 | 专业方法基线已记录 | 目标—障碍—策略—潜台词—反应；部分外部页面 403，未冒充全文阅读 |
| F01-02 | 严格合同已实现 | performance_bible、来源 digest、角色关系与 source spans |
| F01-03 | 逐镜合同已实现 | trigger/objective/obstacle/tactic/subtext/reaction/source beat |
| F01-04 | 实体/环境门禁已实现 | physical_state、relationship_map、handoffs、posture、door/window、跨镜跳变 |
| F01-05 | 可行性与替代部分完成 | production_feasibility、能力证据字段、fallback；无供应商实测 |
| F01-06 | 下游版本上下文部分完成 | camera/sound/editing/technical/QA/final 收到 digest 与 revision scope；不改变十岗 DAG |
| F01-07 | 多题材离线回归完成 | 单人、双人、喜剧、零演员、复杂动作；文本比较为自撰，不是人类盲评 |
| F01-08 | 阻塞 | `inspect_media_readiness` 只接受真实授权媒体证据；当前没有 |
| F01-09 | review-ready 交接 | 本文与 JSON manifest |

## 3. F01-08 证据门禁

真实媒体审片至少需要：

- `evidence_type=real_authorized_media`
- 授权引用
- 解码帧证据
- 手/脸/口型审片
- 跨镜情绪审片
- 独立审片人引用
- 返工日志

即使这些字段齐全，软件也只返回 `review_ready`：

- `complete=false`
- `human_approval=false`
- `real_media_verified=false`

最终完成仍需要真人审阅与明确签字，不能由测试自动授予。

## 4. 冻结规则

F01 进入冻结后：

- 不再无边界增加表演 schema 或新 Agent。
- 只接受真实缺陷修复、证据补齐、独立审稿意见和与新证据直接相关的回归。
- 任何改动继续走 PR，不覆盖用户已确认内容。
- PR #78 在 #77 合并后 retarget/rebase 到 `main`；在审阅前保持 Draft。

## 5. 向 F02 交接

F02（摄影、灯光、美术）必须读取：

- `director_acting.py` 的 strict contract 与边界；
- `performance_bible`、`physical_state`、`relationship_map`、`handoffs`、`environment_state`；
- `production_feasibility` 的专业意图/模型风险/fallback 分离；
- `acting_contract_context` 的 digest 与 revision scope；
- [F01-07 回归与文本比较](F01-07_OFFLINE_REGRESSION_AND_TEXT_COMPARISON_2026-10-31.md)。

F02 不得声称：

- F01 已完成或表演质量已验证；
- 供应商模型能力已实测；
- 真实媒体或人类盲评已完成；
- 最终成片已批准。

## 6. 下一项

下一阶段是 **QO-F02 摄影、灯光与美术专业审计**。F01 的真实媒体验收（F01-08）与独立表演盲评继续保持阻塞；取得真实授权素材后再回到 F01-08，不用虚构证据替代。
