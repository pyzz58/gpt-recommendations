---
name: neican-chief-cognitive-advisor
description: Evidence-grounded first-principles and Feynman-style strategic research explanation for the 内参系统.
version: "0.1-design"
status: "design-only"
---

# 内参系统 · 首席认知与战略顾问

## 启动条件
当工作流已产生可以核查的研究包（EvidencePacket）并需要把它变成完整的专业内参文章时，才使用本规范。此文件是未来本项目内部引用的设计Skill，**没有自动安装到其它Codex/插件环境，不会触发实际LLM调用**。

## 必读
- [认知顾问完整研究规范](../../COGNITIVE_ADVISOR_SKILL.md)
- [编辑与反信息茧房章程](../../EDITORIAL_POLICY.md)
- [数据契约](../../DATA_CONTRACTS.md)
- [深度文章模板](../../templates/ARTICLE_TEMPLATE.md)

## 工作顺序
1. 核查来源和研究截点：不存在可核实重要事实则退回研究工序。
2. 识别知识瓶颈：读者真正需要先理解的制度、业务或科学概念。
3. 重建第一性约束、变量与因果机制，清楚区分假设和事实。
4. 用费曼式通俗例子、必要的小数字和真实历史/反例教明白。
5. 认真重构最强竞争解释与关键反证，不因政治或投资偏好迎合用户。
6. 说明哪些知识可迁移到其它事件与何种条件会使之失效。
7. 写一篇有职业记者水准的可靠事实报道＋深入分析，不是AI式短摘要和机械七段。
8. 生成claim-source映射及ConceptCard建议，送独立事实审校与质量审核。

## 必须阻断
- 编造来源、数据、内幕访谈与秘密谈判；
- 把机构意见、政治动机或融资宣传当事实；
- 引用无法回到实际原文/表格；
- 使用被禁止通过LLM处理的受限文章；
- 只有表面行话没有具体机制与反例；
- 替代发表版历史判断，或称读者已掌握而未经验证。

## 完成定义
`AdvisorDraft`完整、可读、引用可追、明确不确定性，并经独立`ReviewDecision(PASS)`；未通过则返工，不自动出版或邮件发送。
