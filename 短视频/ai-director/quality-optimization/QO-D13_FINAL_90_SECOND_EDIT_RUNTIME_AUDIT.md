# QO-D13｜90秒不是剧本预估时长，而是成片编辑总时长

日期：2026-10-13。属于《AI 总导演全模块审计》中第1批真实阻断缺陷 E；只修单集最终时间线，不触碰用户私稿、编剧原稿的真实观点和台词。程序回归不等于真实影片已通过艺术审核。

## 原来为什么有问题（真实实现路径）

1. `screenplay_series_delivery.validate_breakdown` 检查各集的 `story + intro + recap + bridge + outro + evidence <=90`，这是正确的**规划**判断。
2. 但 `build_per_episode_crew` 只把这几项保存为 `series_context.reserved_additional_s` 汇总；没有保留每项在时间线中的用途，也未建立相对于故事镜头的绝对剪辑顺序。
3. `closing_evidence_card.build_card` 对给出的真实来源会制作一张固定 **1.8s** 的后期来源/鸣谢页，起始时间默认是 story.duration。在旧版 operator delivery 里，前面规划的 `evidence_s` 可能为0或1，即使配套来源确实存在，仍然按 1.8s 添加；结果可能超90秒。
4. 旧版 `production_delivery._make_bundle` 汇报 `final_edit_duration_s=story.duration+(card?1.8:0)`，不含片头、回顾、桥接和结尾。用户原本明确要求最后证据页只能位于整个视频**最后**1–2秒，所以不能把它插在 outro 前面。

## 本轮实际解决

**创作决定不由代码代替。** 导演在编排每集时仍选择是否需要来源页；原稿提供链接仅代表*可以考虑*，不强制要有页，更不能伪造证据。选择来源页后，正式后期工单的实际静态页长为1.8s，规划时间必须与它一致，否则重编时长而非隐瞒差异。

保留五种独立 `reserved_extra_components_s`：
- `intro_s`：故事镜头前的独立片头预算；
- `recap_s`：故事镜头前必要回顾；
- `bridge_s`：故事结束后的过渡；
- `outro_s`：故事结束之后、最终证据页**之前**的结尾；
- `evidence_s`：有原稿真实资料且导演选用时，最终一张来源/鸣谢卡，现有技术实现固定 1.8s。

执行时绝对编辑时间线次序：
`intro → recap → 所有镜头（相对 start 时间整体顺延）→ bridge → outro → 可选末尾证据卡`

当没有片头/回顾等预算时，该轨道不存在，不生成幽灵素材。每项都有 `start_s/end_s/duration_s`，各项必须连续、无空档或重叠。最后一个片尾证据镜头不是 AI 模型生成，是独立后期静态卡；没有卡片时仍可正常收尾。

强制前后证明以下关系：

```text
episode_story_s ≡ source_base.duration
reserved_additional_s ≡ intro + recap + bridge + outro + evidence
episode_total_planned_s ≡ episode_story_s + reserved_additional_s
实际准备的 credits.duration_s ≡ evidence_s（如计划）
final_editor_timeline[-1].end_s ≡ episode_total_planned_s <= 90秒
```

在来源附有链接而导演未选择放卡片时，必须尊重 `include_final_evidence_card=False`：原来科研来源/论证仍可留在发布说明或审核数据，而不能在视频里临时加上一张尾页。

## 具体文件和质量检验

- `screenplay_series_delivery.py`：保留逐项 extra 的事实和导演放卡决定，绑定 series context；
- `closing_evidence_card.py`：只有明确选择才出该集末页；
- `series_final_timeline.py`：基于剧情原镜头建立**绝对**后期剪辑工作单，拒绝未经核实的额外段、伪造总时间和出界；
- `production_delivery.py`：编译 operator bundle 的最后一关再次检查实际来源卡长度，带出最终绝对时间线；
- `tests/test_series_final_timeline.py`：使用公开合成已有影片样例，测试有 intro/recap/bridge/outro/来源页的顺序、原故事镜头保留、未知来源拒绝、来源卡不强制、1秒预算但实际1.8秒、90秒故事预算再偷偷加1.8秒、伪造累加时长等正反情形。

## 仍不能宣称完成的事项

- 真实编辑软件或 AI provider 尚未用授权素材生成实体片头、回顾、结尾、静态卡，也**没有任何真实媒体**。新编辑工作单每段都明确 `real_media_available=False`，`actual_final_media_verified=False`。
- 此轮只验证数字/时间线，并未解决 QO-D02 剧本事件与镜头多对多拆分、QO-D03 电影化表达的艺术感染力、QO-D05 跨集外观音色真实一致性、QO-D10 真正观众盲评等问题。
- 通过的 code CI 能证明预算约束等程序规则，不能证明影片从艺术或 AI 技术角度真的可用。QO-D13 继续标记 `in_progress`，直到真实授权剪辑样本与独立审片等证据到位。
