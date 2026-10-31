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

## 7. W03实际数据底座

迁移`0002_documents_jobs`增加本轮所需的最小表：

- `source_documents`：项目/中心、标题、类型、规则或事实用途及修订。
- `document_versions`：业务版本、私有storage key、原文件名、媒体类型、SHA-256、大小、发布日期、上传时间/操作者、用户手动开始使用信息、解析状态和重复来源。源字段由PostgreSQL触发器禁止更新，解析状态可由worker更新。
- `source_anchors`：版本、逻辑节点、章节路径、原文、格式、页码、bbox、表格行列和脚注编号。
- `parse_coverage`：版本内的原始处理单元及processed/background/not_applicable/unsupported/failed/pending状态。
- `business_jobs`：内部输入版本、actor/租户/范围、幂等摘要、尝试/租约/最大尝试、安全错误摘要和输出摘要。
- `outbox_events`：业务提交时创建，队列不可用时保留；`dedup_key`防止重复发布。

复合外键将资料、版本和锚点绑定到同一tenant/study/site。Procrastinate拥有通用queue schema；业务Job/Outbox仍由本系统负责。W03不创建规则、患者、问题或报告业务表。

## 8. W04实际规则底座

迁移`0003_rules_versions`增加：

- `rule_snapshots`：绑定一个已解析文档版本及前一快照，保存provider、版本、状态和校验摘要；同一源文档版本只允许一个提取快照。
- `rules`：稳定规则键和项目/中心层，保留当前版本指针和显式revision。
- `rule_versions`：一个稳定规则的具体不可变快照，保存四层树、语义状态、候选/确认/撤销状态、确认依据和继承来源；数据库触发器禁止更新或删除。
- `rule_source_refs`：RuleVersion与真实SourceAnchor、quote摘要和位置绑定，复合外键阻止跨研究锚点。
- `rule_relations`：`unchanged/new/supplement/exception/replaces/withdraws/restores/conflict`逐条关系，不从新版本未提及推定撤销。
- `rule_extraction_coverage`：规则提取对每个锚点的processed/background/analysis_required/unsupported/failed覆盖。
- `version_activations`：文档版本/规则快照、项目或中心、`starts_on`含当天与`ends_before`不含、revision及更正前驱；重叠区间保留并提示，不自动裁决。

新文档版本形成完整规则快照：未改变的旧规则复制为`unchanged_inheritance`，已确认项不要求再次确认；旧规则在新版未提及仍保留。含义变化缺明确关系证据时登记conflict候选，不自动覆盖。W04未创建患者、问题、检验或报告业务表。

## 9. W05实际患者上下文底座

迁移`0004_subjects_coverage`增加：

- `subjects`与`subject_identifiers`：去标识内部ID、项目/中心范围和来源命名空间/外部ID稳定映射。
- `clinical_facts`：append-only事实修订，保存value type/raw/JSON值、日期或时间、精度、单位、重复实例、来源类型/核实状态、来源引用和前驱事实；数据库触发器禁止更新或删除。
- `visit_instances`：从`visit_date`/`planned_visit_date`事实建立的计划/实际访视实例及修订历史。
- `visit_requirements`：规则版本、事件日、锚点/实际事实、允许窗口、所需事实、允许来源、受影响路径、可继续事项、输入事实修订和输出状态。
- `fact_change_impacts`：事实新修订影响到的具体访视要求或CheckDecision，用于`needs_review`追踪。
- `coverage_breakpoints`：患者、类别、范围各自的版本化断点、已核查至位置、正常范围简记及未核实范围。
- `check_decisions`：患者/事项/期间/规则范围的局部不核查选择、reason、缺失键、影响路径、可继续事项、恢复可用标记和显式恢复历史。

确定性事实计算仅使用`original_record`/`cra_confirmed`；`reported_by_other`和`model_candidate`保留但不覆盖事实或生成确定性日期。W05不创建Issue、检验比较或报告表。

## 10. W06实际遗留与监查底座

迁移`0005_issues_monitoring`增加：

- `issues`：项目/中心稳定的Issue编号、原问题、位置、建议来源、已知进展、可选已有沟通、来源资料/锚点和显式revision；问题信息可部分未知。
- `issue_actions`：Issue下稳定Action key、类型、要求、独立状态、`completion_basis`、服务器操作者/时间、可选说明和期限来源；PD上报与数据更正等互不覆盖。
- `issue_history`：Issue/Action创建、上报、CRA确认、重开、沟通、遗留导入和Query关联的append-only历史；数据库触发器禁止更新/删除。
- `query_links`：草稿或正式Query、外部编号/系统、实际创建/回复日、截止日、期限来源及引用；正式Query和有依据期限由数据库约束检查。
- `monitoring_visits`与`monitoring_visit_selections`：本次监查阶段、范围简记、状态、revision及访前选择；选择不删除Issue。
- `carryover_imports`：来源文件版本或文字、SHA-256/解析器指纹、预览/确认状态、解析警告和确认操作者/时间。
- `carryover_candidates`：候选原编号/问题/位置/建议/进展/行动、原文件source_refs、unknown字段、用户修正及导入Issue映射；相同来源、原编号和确认命令幂等。

`Issue`聚合完成状态由Action派生，不是替代各Action的通用closed字段。`confirm-corrected`记录`completion_basis=user_confirmation`并由服务器取actor/time；`confirm-reported`仅用于PD上报。来源文件或文字缺位置、建议或行动时保持unknown。W06没有M10目录状态表、报告/信件表、Query自动提交或EDC写回。

## 11. W07实际EDC Excel快照底座

迁移`0006_edc_import`增加：

- `edc_import_previews`：W03源文档版本、源哈希、导出起止时间/范围声明、表头指纹、解析器版本、建议映射、状态和revision。
- `edc_preview_sheets`与`edc_preview_cells`：sheet状态、列标题、行列数量及原始文本、公式、缓存值、单元格类型和格式；不执行工作簿内容。
- `edc_import_mappings`：按项目/中心与表头指纹保存已确认列映射，供后续同格式导出复用。
- `edc_snapshots`：源哈希、映射/范围digest、导出范围、sheet清单、行/记录数量、映射revision和固定的`not_seen_in_export`语义；数据库触发器禁止更新/删除。
- `edc_snapshot_rows`：每行原始值、公式、缓存值、Excel行anchor和内容哈希；不可变。
- `edc_lab_records`：从用户确认映射形成的一行一检验项目标准记录，保留受试者映射、访视、原始/数值/operator、单位、采样精度、初检/复查实例键、报告日期、参考上下限、身份/验证状态及来源位置；不可变。

来源资料用途和类型新增强制值`edc_export`。预览范围未知或为过滤导出时仍可保存快照，但本次未见只表达`not_seen_in_export`；不创建EDC漏录事实。W07不进行M08对象匹配或报告结论，不写回EDC。

## 12. W08实际检验读取与比较底座

迁移`0007_laboratory_comparison`增加：

- `lab_recognition_jobs`：项目/中心、M02源文档版本、操作者/身份来源、幂等摘要、queued/running/succeeded/failed、attempt、错误和输出摘要。
- `lab_report_versions`：M02源文档版本、源哈希、文件格式、provider/model版本、SupportProfile、警告、状态、候选数量和对应识别Job；同一源版本只建立一份报告识别记录。
- `lab_observations`：保留受试者外部ID、访视、项目原文/规范化、样本、采样精度、初检/复查、报告版本、结果原文/Decimal/operator、单位、参考范围、自动/复核状态、问题及原始页/表/行/字段bbox。来源候选和比较结果由数据库触发器禁止更新或删除。
- `lab_observation_decisions`：confirm/correct/skip以append-only动作保存，含人工更正字段、说明、操作者和时间。有效字段由原候选叠加最新动作计算，更正不覆盖原识别结果。
- `lab_comparisons`：绑定报告版本、EDC快照、当时报告revision、比较输入digest、scope和unknowns。
- `lab_comparison_fields`：每项来源候选的match_status、result_status、候选EDC记录、两侧原文/单位、字段结果及原因；多候选保留ambiguous。
- `lab_comparison_issue_links`：显式记录哪些比较字段由用户关联到哪个稳定Issue，不自动把差异变成PD或完成Action。

`edc_lab_records`新增可选`report_revision`映射。OCR不可用时仍可保存源文件、人工候选和局部CheckDecision；自动候选、用户更正及比较结果分层存储。W08不创建报告正文、医学安全结论或EDC写回。

## 13. W09实际安全分析底座

迁移`0008_safety_assessment`增加：

- `safety_assessments`：受试者、事件类型/日期、请求维度、事实/规则快照、provider版本/状态、受限解释、具体问题、及时提醒、unknown、Evidence与OutputEnvelope；数据库触发器禁止更新/删除。
- `safety_dimension_results`：AE收集、分级、SAE严重性、相关性、预期性、AESI、DLT、PD和及时报告各自status、候选动作、unknown、规则版本、证据ID与SourceRef；不可变。
- `safety_cra_reviews`：CRA append-only复核决定、所选维度及可选W05 CheckDecision引用；不修改系统候选。
- `medical_safety_responses`：研究者/医学角色、实际答复、分维度答复和来源说明；与CRA复核分开且不可变。
- `safety_issue_links`：安全分析到M06 Issue的显式关联及维度；不保存或自动改变Action完成状态。

分析键绑定事实修订、适用规则版本、检验比较revision、provider和活动安全跳过决定。相同输入幂等复用；provider替换或新事实/规则/跳过范围可产生新分析，旧维度、复核和医学答复保留。模型解释Claim保持`inference/needs_review`，仅引用实际输入的证据ID，不能成为最终医学结论或自动完成依据。
