> **V5 历史资料效力（2026-10-14）**：本文件保留当时的细化、模板或审计证据，不能独立改变[唯一现行 V5 主规格](../CANONICAL_SYSTEM_SPEC_V5.md)。旧九栏固定百分比、独立连续情报/雷达、旧版“最高”与读者版“继续观察”等如有冲突，以 V5 为准；未冲突的专业方法和案例可按题参考。

# 内参系统｜长期研究主题与判断版本模板

> 目的：几个月乃至几年后，用户能找回**当时完整思想、原始证据、结论与之后变化**，而不是AI重新编造一份连贯“回忆”。`version`只增加，不删除旧版。

```yaml
theme_id: THEME-YYYY-###
canonical_question: "[持续跨月/跨年的真实问题]"
created_at: "[ISO]"
domain_tags: []
relevant_entities: []
current_status: WATCH|ACTIVE|SUSPENDED|CLOSED
linked_event_ids: []
linked_original_files: []
next_review_at: "[日期或事件]"
```

## 原始提问及背景
[用户/原始研究的完整原话定位。允许存储已获授权的内部笔记原件，**不能只保留本模板中的简写**。]

## 资料链
| 证据ID | 来源或原件 | 发表时间 | 实际取得时间 | 主要事实 | 反驳或局限 |
|---|---|---|---|---|---|
| [EVID-...] | [文件路径/URL/页码] | [时间] | [时间] | [事实] | [限制] |

## 判断版本 V1（冻结）
```yaml
thesis_id: THESIS-YYYY-###
version: 1
as_of: "[当时知识截点]"
proposition: "[命题]"
evidence_for_ids: []
evidence_against_ids: []
assumptions: []
expected_horizon: "[若有]"
confidence_type: qualitative|statistical|subjective|not_assigned
confidence_value: null
falsification_indicators: []
status: OPEN|SUPPORTED|REVISED|REFUTED|INCONCLUSIVE
```

## 后续新证据（只追加）
[日期、原件、为何确实改变或不改变旧判断；不要用今天的现实给昨天的资料贴不存在的证据。]

## 判断版本 V2、V3……
[新版本的as_of、改变了的命题、旧命题引用、结论变化理由。]

## 已教授的可迁移知识
- concept_id：[原理]
- 适用范围与重要反例：[说明]
- learner_status：`TAUGHT` / `NOT_ASSESSED` / `DEMONSTRATED`；**不得在没有实际验证时自动认定已掌握**。

## 重新召回测试
询问：“2026年某政策/某公司/某保险合作，我们当时为什么这么认为？后来的事实有哪些变化？”
必须输出旧原件/当时观点、旧证据时间、后续新证据、修订原因、仍然未知。原件不存在则明确说缺失，不得凭空填充。
