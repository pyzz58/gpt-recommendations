# 多 Agent 专业导演团队：跨部门一致性、返工与交付门禁

> GitHub-only 源码功能（2026-10-11）。只分析私有运行时传入的 JSON；不会访问个人 Mac、外部模型、视频供应商或付费接口。本文件中的命令用于**未来获批准的私有部署**，现阶段不要求用户执行。

## 为什么要有第二道独立 QA？

`agent_creative_review.py` 检查岗位内部的具体创作信息；`agent_handoff_audit.py` 专查**可以直接从两个岗位的结构化字段推导出**的矛盾。

| 冲突 | 谁负责修改 | 如何判断 |
|---|---|---|
| `speech.voiceover.text` 与基础分镜 `narration` 不相同 | 声音导演 `sound` | 原文逐字比较，不允许静默改稿 |
| `editing.narrative_bridge.beat_link` 索引与动作部首/末 `beats` 不相符 | 剪辑动画 `editing_animation` | 只验证真实索引和时码，不从自然语言推理切点好坏 |
| 动作 `beats`、摄影 `move_trigger_s`、音效 `effects[].time_s` 超过镜头时长 | 对应岗位 | 与基础分镜的实际 `duration` 比较 |
| `generation.route` 不是已支持路线 | AI 技术导演 `ai_technical` | 固定值白名单，供应商 API 未接入 |
| `animation.mode=none` 却出现非空 `elements` | 剪辑动画 | 自相矛盾的结构 |
| `graphics.claims_used` 引用了 `base.claims` 没有的 ID | 剪辑动画 | 引用约束，**不证明论据真实** |
| `editing.outgoing_transition` 与锁定的基础转场不同 | 剪辑动画 | 需要上游变更审批，不能静默覆盖 |

未设计剪辑叙事桥、只有空泛形容词、真人动作缺少可拍性方案等仍属于**人工复核或草稿缺项**，不会被简单等同于可证明的跨部门矛盾。现有 `director_v2.validate`、`director_workbook.compile_workbook` 及各独立时间线/连续性审查仍保留。

## 具体执行顺序

1. 剧本/角色/导演锁定由原有 `agent_team` 十阶段 DAG 产生并记录版本。
2. 各岗位交付后，发给 QA 的 `packet()` 自动带 `independent_handoff_audit`。报告列出 `code`、`task_id`、`shot_ids` 和可复核原因。
3. 有结构硬冲突时，QA **不能**提交 `ready_for_director_review`。它可以填写自己的 `qa_report.blockers`，决定 `recommendation=revise`。
4. `propose_director_revisions(base,state)` 只读计算跨岗位硬冲突 + QA 已确认 blocker，按责任岗位合并该轮受影响镜头，并附上版本期望，不直接调用模型。
5. 总导演审核建议后，可明确将其交给 `request_planned_revision(...,showrunner_approved=True)`。该调用检查建议是否仍与当前状态一致，再使用原有 DAG 实施定向重审：修改动作 S02，剪辑需复核 S01–S03，其他无关已交付部门保留；旧版本留在历史中。
6. 总导演审核通过后的 `compile_team_workbook` **重新从权威 base 比对**，而不是信任之前 QA 的声明。有硬冲突、QA blocker 或核心结构 blocker 时，拒绝生成工作单。
7. 无硬冲突却有遗漏时，普通模式生成 `team_delivery_gate.status=draft_needs_review` 的草稿；严格模式 `strict=True` 额外要求既有导演制作蓝图就绪且无创作提醒，才允许返回 `ready_for_human_review`。
8. 工作单的 `human_approved`、`paid_api_authorized`、`actual_video_approved` 仍然必须是 `false`。不因总导演 AI 审核通过而变成最终成片或付款许可。

## 主要 Python API

```python
import agent_team
import agent_handoff_audit

# 以下 base/state 均须由未来经批准的私有运行环境提供
report = agent_handoff_audit.audit_handoffs(state, base)
suggestions = agent_team.propose_director_revisions(base, state)

# 只有在总导演明确决定且建议仍匹配当前版本时，才能请求部门返工：
# revised = agent_team.request_planned_revision(
#     base, state, suggestions["proposals"][0], showrunner_approved=True)

# 通过硬冲突检验的审阅草稿：
# book = agent_team.compile_team_workbook(base, state)
# 严格文字制作蓝图（不是人审/实拍批准）：
# book = agent_team.compile_team_workbook(base, state, strict=True)
```

## CLI 接口（未来部署后才执行）

- `agent_team.py audit-handoffs --state TEAM --base PLAN --out REPORT`
- `agent_team.py propose-revisions --state TEAM --base PLAN --out PROPOSALS`（可选 `--include-reviews`）
- `agent_team.py approve-revision --state TEAM --base PLAN --proposal SINGLE_PROPOSAL --approve-showrunner-rework --out NEW_TEAM`
- `agent_team.py workbook --state TEAM --base PLAN --strict --out WORKBOOK`

命令写出新文件，沿用 `_save_new` 的不覆盖保护。提案文件与 QA 报告必须与私有原稿放在同一**未来私有工作区**，绝不提交公开 GitHub。CLI 的开关只是记录一次总导演流程决策，并**不能证明操作者真实身份**；正式授权与上线人审仍须采用独立机制。

## 已知限制与回滚

- 当前是 **静态、确定性的结构和跨部门约束检查**。不能从中文描述自动验证表演是否合理、剪辑是否好看、音乐版权是否合规；也没有让八个 LLM 实际工作。
- 不保证完全识别所有逻辑矛盾。对于难以自动比较的自然语言冲突，必须由 QA 人审、未来经许可的样片测试判断。
- 没有真实视频生成、DeepSeek 付费测试、Mac 部署。合成回归位于 `tests/test_agent_handoff_audit.py`。**只提交测试源码不等于测试已经运行**，本轮未核实整仓 CI。
- 如需回退，可通过 GitHub 提交历史恢复新增模块及 `agent_team.py` 接入修改；旧 `director_v2.py` 和 `director_workbook.py` 的基础校验未被更改。对现有 `assemble_direction` 保持草稿用途，不将其当成正式出片入口。
