# M03 适用规则与分层list

版本：4；状态：W04规则快照、候选提取、用户确认、分层list、启用区间和事件日适用性已实现并有真实PostgreSQL/合成provider证据。代码位置：`backend/cra_app/rules/`。

## 对应理论和任务

理论：CRA-R002、CRA-R004、CRA-R005、CRA-R006、CRA-R007、CRA-R008、CRA-R009、CRA-R011、CRA-R019、CRA-R034、CRA-R041。完整内容及出处见[理论清单](../../theory/REQUIREMENTS.md)与[对照表](../../traceability/INDEX.md)。

工作包：CRA-W04。验收场景：CRA-S04、CRA-S05、CRA-S06、CRA-S07、CRA-S37、CRA-S38。依赖模块：M01、M02。

## 输入、输出和负责的数据

- 输入：版本化原文、规则用途、对象/阶段/时间及项目和中心范围。
- 输出：候选/适用规则树、原文和条件、变更关系、冲突与待确认项。
- 负责的数据：RuleVersion、RuleRelation、ParseCoverage、条件AST和确认历史。

## 实现方法

先结构切片再生成候选，核实引用真实存在；摘要、条件、例外、子list和原文保存在同一版本。白名单表达式解释且/或和边界，无法机械判定的规则保留分析条件。明确邮件/文字无冲突直接纳入，资料初提取按用户确认增删流程处理。

具体服务路径和字段共同遵守[接口](../API_CONTRACTS.md)及[数据模型](../DATA_MODEL.md)。实现时本模块通过公开服务调用依赖，不直接改对方数据表。异步处理、幂等、权限、版本及历史适用共同约定。

## 工作边界

不能最新上传覆盖一切、不能统一取更严、不能把新版未提及当撤销。原文处理覆盖与规则数量分开统计。删除本次任务不删除条款。

## 验收与变更

本模块验收采用场景：CRA-S04、CRA-S05、CRA-S06、CRA-S07。场景期望见[质量验收](../QUALITY.md)，实现证据在完成任务后追加；本文件存在不等于功能实现。

大多数项目规定更新只生成新RuleVersion及影响清单；新增判定结构需更新AST、API、数据迁移和消费者。

理论变更先从固定编号定位到本文件，再确认是否改变配置、服务策略、供应商adapter或数据/API契约，按[同步规则](../../traceability/SYNC_POLICY.md)留下记录。

## 2026-10-29用户决定对应修订

list含前提、触发、分支、例外、后续动作与完成方式，条件C→B、D→F可展开。有限AST和三值逻辑见WORKFLOW_CONTRACTS；真实引用不足以证明条件完整。手动VersionActivation按事件日解析，起始日含当天，中心范围和更正历史保留。用户可在使用中补充分支，不编造来源未提供的可能性。

详细输入、状态、边界与开发阶段按[WORKFLOW_CONTRACTS](../WORKFLOW_CONTRACTS.md)。本节与旧实现方法不一致时采用本节；设计更新不等于功能已经完成。

## v0.4技术实施补齐

共性规则包、版本启用、完整分支和三值条件、实际提取评估。 实现契约见[EXECUTION_CONTRACTS.md](../EXECUTION_CONTRACTS.md)，当前任务的进入条件/交接见[完整实施路径](../../plan/IMPLEMENTATION_PATH.md)。理论和任务编号保持；本轮文档不是业务功能完成证据。

## W04实现记录

已增加规则快照、不可变RuleVersion、来源引用、逐条关系、提取覆盖和手动VersionActivation表。新资料版本会形成完整规则快照；未在新版提及的旧规则以unchanged继承，不自动当撤销；含义改变而无明确replace/withdraw证据时登记conflict，不自动覆盖。用户确认增删改生成新版本并保留候选、旧版本、AUD和来源。

有限AST支持all/any/not、存在、六类比较、in及日期区间，Decimal、单位和日期精度显式处理，unknown不默认走另一分支。确定性`anchored-rule-subset` provider实际读取W03锚点，支持W04声明的结构化规则语法，并拒绝假锚点、不可追溯数字及丢前提/否定/例外的候选。独立评估样本与开发样本分离；该provider不代表任意真实方案都能完整自动提取。

测试真实经过PostgreSQL 18.6、DOCX解析、规则提取、用户确认、v1/v2继承、同范围启用日边界和冲突预览。未使用真实临床资料；复杂自由文本仍保留analysis_required，真实方案格式覆盖、专业语义复核和模型provider验证仍待后续授权环境。
