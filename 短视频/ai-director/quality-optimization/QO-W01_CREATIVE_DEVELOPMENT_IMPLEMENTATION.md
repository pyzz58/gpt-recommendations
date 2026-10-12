# QO-W01｜职业编剧创作开发能力升级（2026-10-13）

> **先读职业原始资料及现有源码，再设计本轮实施。** 一手深度审计见 [QO-W01_PROFESSIONAL_PRIMARY_SOURCE_AUDIT.md](QO-W01_PROFESSIONAL_PRIMARY_SOURCE_AUDIT.md)。本轮新 `screenplay_development.py` 并非「核心思想哈希强制保留器」，而是一个**先研究原作、再选择影视改编方案**的可审阅工作入口。

## 原因—专业方法—实际修改

| 确认的根因 | 职业创作依据 | 对应新增能力 | 能否自动证明艺术质量 |
| --- | --- | --- | --- |
| 原文全文读入后立刻要求一个最终 JSON 剧本 | Gilroy：创作必须首先回答影片到底是什么；August/Mazin：小说或文章与电影有不同的叙事发动机 | `diagnosis_request`：先描述作品内核、作者声音、作者未回答的疑问和观众认知/情绪起终点 | 不能 |
| 无法比较改编方向，只输出第一版方案 | 职业改编中保留、舍弃、合并和重新组织本身属于创作；WGA 对选择安排的认识 | `takes_request`：2–3 个不同的 film take，包含画面表达、实际艺术代价、删改原因、AI 短片制作风险 | 不能，仅能拒绝完全相同的几个关键字段 |
| 未经过创作编辑比较就按默认第一稿发展剧本 | Sundance 公开重写课程大纲及 Nicholl 关于作品声音、观众旅程与技艺的评分维度 | `selection_review_request`：独立开发编辑比较所有方案，也可全部退回修改 | 不得将表单视为真人认证 |
| 缺先行的 Treatment，就直接写满镜头占位 | 职业发展工序先评结构/场次变化，再写对白和最终分场剧本 | `treatment_request`：每一场的初始状态、可见可听事件、认知或人物变化、结束状态、存在理由和时长 | 不得仅因字段填满认为场次有用 |
| 开发方案、最终剧本与导演交接没有版本链 | 编剧→导演交接时作品改动、选案和剧本权威必须可追踪 | `screenplay_request` 真正将选案 treatment 填入既有编剧请求；`screenplay_review_packet` 绑定开发版本；`alignment_review_request` 独立评审剧本创意偏离或无理由丢失；`director_handoff` 再调用**原有**编剧专业审阅与总导演接口 | 不保证审稿者准确，也不能伪造作者批准 |

## 权责清晰

- **编剧负责**：原稿创作性阅读、影视 take 设计、独立比较的修改、完整 treatment、可见可听的动作/旁白/对白、局部编剧重写。
- **总导演负责**：将已经确定的剧本转化为视听方案并安排摄影/表演/剪辑/制作，遇到叙事问题发回编剧；**不是重新编一个故事**。
- **AI 技术团队后续负责**：匹配视频生成模型的长度、首尾参考、声音能力、clip 预算与失败降级。编剧场次的 `estimated_duration_s` 是整片/段落节奏，不是单次视频请求长度。

## 职业质量纠偏重点

1. 来源位置和哈希只用来判断是否静默丢数据，**不是越高越专业**。
2. 合理删减/改写原著可使影像更忠于作品精神；独立编辑须允许 `creative_reinterpretation`，只阻止经过证据说明的 `unjustified_loss`。
3. 无人物的科普论述不需强制英雄、反派、戏剧台词；用观众的理解变化推进也成立。
4. 新增历史事实必须标为待核实提案；原文没有引用资料就**不强制增加证据卡、出处或鸣谢页**。
5. 文学审核和剧本质量需通过案例、独立盲读与实际改稿比较；**CI 无法认证**。

## 公开合成测试所能证明的内容

公开虚构的「村民与一座桥」素材提供两种 take：
- **A** 以人物争论推进，把讲述性材料转为可演行动，优点情绪具体，代价是更偏人物戏、AI 双人交互更复杂。
- **B** 以不完整地图制造可见的哲学/价值问题，以观众认知变化驱动；优点忠于原稿提问，代价可能少人物共情，精确图形要由后期完成。

测试内容：两种截然不同的方案、来源中明确可舍弃的具体句子、独立比较后能选择或者全部拒绝、两场 treatment、真实编剧消息携带所选方案、版本篡改拒绝、独立审稿可接受有价值的改写而阻止无理由损失，随后仍走原团队。**上述数据是为测试编造的合成案例，不是得到名家审阅的优秀剧本。**

## 本轮尚未完成的问题

- 真正模型是否能写出有显著差异的影视 take，避免两个方案只是换词。
- 独立剧本编辑是否能准确识别良好改编与错误篡改，尤其多体裁与小说内心转可演动作。
- 同一原稿旧版单次 prompt 与新版开发流程的**完整剧本**实际可读性和观众盲审比较。
- treatment 到 Fountain 剧本的场次内动作/对白事件精确交替仍在 QO-W04；导演分镜与生成 clip 的解耦仍在 QO-D02；不得掩盖。
- 真实作者许可与评论者职业身份没有通过机器签名认证。

因此 QO-W01 **只从 partially_addressed 更新为 in_progress，不能 complete**。待上述独立文体案例与盲评完成，带真实证明再关闭问题；不向 GitHub 公开私有文案、不发付费模型请求。

## 工程接入点

```python
import screenplay_fulltext_intake as intake
import screenplay_development as dev

source = "作者提供的完整文章（此处只是示意）"
book = intake.prepare_fulltext(source)
diagnosis_prompt = dev.diagnosis_request(book, source, genre="essay")
# 下面的 diagnosis / takes / selection / treatment 必须是真正独立
# 写作/审核产生的候选字典，不能被上面的请求自动生成。
# diagnosis = ...
# options = ...
# selected = ...
# treatment = ...
# packet = dev.development_packet(book, source, diagnosis, options,
#                                  selected, treatment)
# unsent_draft_request = dev.screenplay_request(book, source, packet)
# 尚未调用任何 LLM，也没有作者真实签字或成片生成。
```

所有请求函数返回明确 `dispatch_allowed=False`，不触发模型或经济成本。
