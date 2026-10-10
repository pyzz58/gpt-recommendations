# Skill 02：单集内容编辑与数据账本

工作顺序：核心观点 → 观众体验 → 旁白 → 镜头目标 → 证据 ID，最后才决定 Prompt。

1. 每一集必须独立可看，开头 3–5 秒建立悬念或共鸣，结尾给出具体回报；跨集由一句轻提醒建立关联。
2. 输出完全符合现有 director.py 的 v0.1 `plan.json` 结构；与 series.json 的 character.id、description 和 visual_bible 一致。禁止凭空造不存在的参考素材。
3. 旁白不以篇幅为重：研究的人数、暴露、比较组、终点和研究性质必须准确；没有原始研究来源时 `claims.status=needs_review`。
4. 数据可删减，但在 `editorial.omissions` 明确说明删掉了什么、为什么。禁止自行把风险相对增加解释成绝对发生率。
5. 来源足够时末尾只有一张静态、5 秒、无旁白的 `sources` 镜头，`visual_type=text_card`，引用 2–3 个不同的 claim ID；完整来源移至 `description.md`。若没有可靠参考来源，不制造卡片。
6. 数字动效由后期做；AI_VIDEO 只管可拍摄画面。所有文字和百分比后期叠加。
7. 确保每镜时间轴连续、总时长准确、每个人物角色ID来自 series.json。