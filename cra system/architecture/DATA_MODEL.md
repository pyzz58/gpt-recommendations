# 数据模型、版本和状态

状态：设计契约；实际DDL和迁移在W01实现。任何实体的技术编号不直接作为受试者身份。

## 1. 共用字段和完整性

所有研究数据保存tenant_id、study_id；中心对象额外site_id。患者相关实体有subject_id。范围由已验证身份和授权推导，不能信任客户端传入的tenant_id。复合外键或服务校验防止把中心A患者链接到中心B问题；每次读取、检索、下载和导出均先鉴权。

可修改记录有revision、created_at、updated_at、actor_id；写入用expected_revision，冲突返回409及最新版本，禁止最后一次静默覆盖。原始材料及签发快照不就地修改。写入和对应audit_event同一事务提交；重要外部处理由outbox发布。幂等键绑定操作者、范围、命令和输入摘要，不能全系统仅按文件名去重。

临床发生时间、采样时间、报告时间、研究者知悉时间、CRA知悉时间、上传时间和实际上报时间分别保存；date-only不臆造时分秒或时区。未提供与已知为空分别记录。精确数值用Decimal和原始字符串，保留比较符号及单位，不先转float。

## 2. 实体

| 对象 | 主要字段或关系 | 历史和来源要求 |
| --- | --- | --- |
| Study / Site / Membership | 研究、中心、获准角色、对象范围、盲态 | 权限在模型和文件访问前执行 |
| SourceDocument / DocumentVersion | 类型、业务版本、文件哈希、发布时间、启用范围、存储键、规则用途或事实用途 | 同文件可多业务版本，不按上传时间自动取代 |
| SourceAnchor | 文档版本、章节、段落、表格单元格/脚注、页定位、图像区域、关键片段 | DOCX逻辑位置和渲染页码区分 |
| ParseCoverage | 原始单元、处理状态、关联规则、背景/不适用/待解释原因 | 未处理不等于无要求 |
| Rule / RuleVersion | 摘要、完整要求、适用对象、前提、条件表达式、例外、子项、原文、有效时间、状态 | 版本不可变；不同角色/并行义务不强行覆盖 |
| RuleRelation | unchanged/new/supplement/exception/replaces/withdraws/restores/conflict | 指向具体旧条目并记录关系依据 |
| Subject / ClinicalFact | 去标识编号、事实类型、值、实际时间、来源或用户确认、修订关系 | AI建议不写入已确认事实字段 |
| VisitPlan / VisitInstance | 锚点及规则版本、计划目标与允许范围、实际发生时间、重复实例 | 实际事实变化产生受影响复核 |
| MonitoringVisit | 工作阶段、中心、范围、可用资料/规则快照、现场顺序及阶段进度 | 顺序引导与问题状态分开 |
| CoverageRecord | 患者/类别/期间、查到哪里、未核实项、用户简记 | 不等同于所有字段正常 |
| Issue | 稳定编号、事实、位置、发现/发生日期、依据、判断状态 | 同一问题跨报告引用，不逐次复制 |
| ActionItem | issue_id、type、要求、完成依据、状态、责任/期限及其来源 | PD上报与EDC更正等各自完成 |
| IssueHistory / Verification | 用户确认、自动操作者/时间，可选回复/修改详情/说明 | 用户点击为完成依据，已有回复非前置；不冒称系统独立验证 |
| QueryLink | 草稿/正式EDC、外部编号、实际创建时间、截止与依据、回复 | 未接入不能假装实时同步 |
| DocumentRequirement / FileStatus | 目录版本、应有条目、适用范围、现状、缺口与位置 | 补齐后保留上次缺件历史 |
| EDCSnapshot / ImportMapping | 导出范围、导出时间、表单/列、原始行定位、导入版本 | 公式/空白/未含表单区别保存 |
| LabObservation / MatchDecision | 项目、样本、采样时间、初检复查、报告修订、值/单位/范围、图像位置、识别及用户修正状态 | 通过身份/结构校验后自动比较候选，歧义集中核实；不要求逐字段确认 |
| Comparison / Assessment | 规则和事实版本、结果、未知条件、计算过程、候选解释及证据 | 数值一致不自动变为医学确认 |
| Template / ReportDraft | 模板版本、字段映射、事实和问题引用、用户文字调整 | 文案调整与事实调整分开 |
| ReportSnapshot / Export | 内容、范围、规则/事实版本、审核/签发等实际状态、文件摘要 | 签发后变化走新版本或修订记录 |
| Job / Outbox / AuditEvent | 幂等输入、租约、阶段、重试、输出、错误和操作者 | 不记录原始敏感提示词于公开日志 |
| ProviderRun | provider/model/prompt版本、允许的数据范围、输出校验、必要成本信息 | 失败不能冒充已完成的临床动作 |

## 3. 三种进度与任务完成

核查覆盖回答“查了什么”；行动状态回答“问题处理到哪里”；交付状态回答“报告到了哪一步”。三者可同时为“已核查、整改未完、报告已提交”。

ActionItem.type至少区分pd_reporting、edc_correction、document_supply、medical_clarification、query_followup、other。pd_reporting收到用户明确已上报即记完成并保存确认来源，日期/编号未知时不编造。整改以CRA用户点击确认完成所选Action为准；系统保存user_confirmation、操作者和时间，不强制CRC回复、修改位置、说明、附件或另一次证明。已有回复可单独保留，用户认为未改好则继续或重开，剩余动作独立。Issue可显示各行动聚合状态，不以一个通用closed布尔值替代。

报告或访视信的选取集合只是展示内容，不是问题清单全集。签发快照保存引用版本与内容摘要，后续状态更新不能改变快照。

## 4. 变更影响与迁移

RuleVersion和ClinicalFact版本通过依赖表关联Assessment、ActionItem、Draft。更正源报告可使具体比较结果待复核，不抹掉原事实和既往上报历史。需要新跟进时新增动作而非回改历史。

数据库迁移采用先增加兼容字段/表、回填并核实、再切换读写；必要时保留旧字段至验证完成。迁移和恢复先用合成数据演练，签发报告、来源定位和问题编号不得丢失。模型输出JSON不是绕过这些数据约束的替代存储。

## 5. 本轮新增或细化对象

| 对象 | 最小约定 | 负责模块 |
| --- | --- | --- |
| VersionActivation | 文档版本、project/site范围、starts_on含当天/ends_before不含、actor、修订；临床事件时间选版本，报告另存输出规则版本 | M03，M02存资料元数据，M04/M11消费 |
| CheckDecision | 明确对象/事项/期间或快照、缺失keys、受影响路径、declined_missing_data/unreadable_skip、actor/time、active/resumed | M04存事实缺口选择，M05管理覆盖，M08消费 |
| CarryoverImport | 来源版本、条目定位/原编号、候选与原Issue映射、导入哈希/确认历史；缺项unknown | M06复用M02来源 |
| DirectoryReference | 原目录版本、可选条目锚点、reference_only/structured状态、简要缺件/状态 | M10复用M02原文件 |
| SupportProfile | 支持格式/图像条件、provider版本、验证范围、关键错误与限制 | M08/M12，M14保存评估证据 |
| ExtractionField | 原文/位置、原值、auto_extracted/user_corrected/unreadable/user_skipped、校验与复核状态 | M08，自动候选与人工核实分别保存 |

缺口选择不是Issue整改；用户跳过后不自动催办。RuleVersion补充分支不会覆盖历史。具体状态和执行语义见[WORKFLOW_CONTRACTS](WORKFLOW_CONTRACTS.md)。

## 6. v0.4执行细化

ExecutionContext/OutputEnvelope、ContextImport/SafetyContext、TemplateMapping和共性规则包按[EXECUTION_CONTRACTS](EXECUTION_CONTRACTS.md)增量实现；字段与计算/来源状态由各模块拥有。provider原调用不保证绝不重复，保存attempt/request与费用，旧输入job输出不静默替代新事实。profile源文件绑定是工程证据，不存真实临床资料。
