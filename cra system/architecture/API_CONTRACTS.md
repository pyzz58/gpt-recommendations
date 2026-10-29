# 接口与模块约定

状态：设计草案，后续由FastAPI生成并校验OpenAPI。接口路径在实现时可细化，但固定理论、模块和任务编号不变。

## 1. 共同约定

API前缀/api/v1。身份来自获验证的OIDC会话，服务端推导授权范围。浏览器使用同源会话或经批准的令牌模式；采用Cookie时配置CSRF、SameSite及安全属性。所有写入接收幂等键及expected_revision，审计与业务事务一致提交。请求中不能自行指定操作者冒充其他角色。

回复包含resource_id、revision、status及可核实的source_refs；缺少、未验证、跳过、冲突分别表达。错误至少区分范围不允许、版本冲突、条件不全、匹配歧义、服务不可用、配额耗尽及格式不支持。错误日志避免包含原文件内容。重试不会重复创建问题或报告。

## 2. 服务接口

| 模块 | 计划HTTP接口或内部端口 | 输入与输出约束 |
| --- | --- | --- |
| M01 | GET /me/scopes；authorize(subject,action,resource) | 在读取文件、检索、模型及导出前鉴权；不只在UI隐藏 |
| M02 | POST /studies/{id}/documents；GET /documents/{id}/versions；GET /anchors/{id} | 上传元数据及私有文件引用，解析job_id，原文锚点及覆盖；不能直接返回公开永久下载URL |
| M03 | POST /rule-candidates；PATCH /rules/{id}/confirmation；GET /rules/applicable | 资料用途、对象和时间→候选/适用规则树；写回用户修改与原因 |
| M03 | POST /rule-changes/preview；POST /rule-changes/confirm | 条目级新增/修订/例外/撤销/冲突及影响预览；不是last-write-wins |
| M04 | POST /facts/import；GET /subjects/{id}/timeline；GET /subjects/{id}/visit-requirements | 事实来源、时间、版本和范围→阶段要求与未知条件 |
| M05 | POST /monitoring-visits；GET /monitoring-visits/{id}/workbench；POST /coverage | 阶段、患者及类别范围→引导与断点，正常范围可批量记 |
| M06 | POST /issues；POST /issues/{id}/replies；POST /actions/{id}/verify | 原问题、位置、建议及出处→分项行动及可选沟通历史；verify兼容记录不得成为点击完成的额外门槛 |
| M06 | POST /actions/{id}/confirm-reported | 仅pd_reporting接受用户明确已上报；不强制额外回执，不完成其他类型行动 |
| M06 | GET /issues/carryover；POST /query-links | 按实际类型和状态带出上次遗留；Query需真实编号/时间或明确为草稿 |
| M07 | POST /edc-imports/preview；POST /edc-imports/{id}/confirm | Excel快照、列映射、实例及导出范围确认；返回行级定位和错误 |
| M08 | POST /lab-reports；POST /lab-fields/{id}/confirm-or-skip | 自动提取候选及源定位，结构/身份校验后可比较；低可信/歧义集中复核，候选不冒称CRA已核实 |
| M08 | POST /lab-matches/preview；POST /lab-comparisons | 先核实对象和重复实例，再按批准单位/逻辑规则比对；歧义返回候选不自动挑最接近值 |
| M09 | POST /assessments | 允许范围的事实、明确规则版本及上下文→候选分析、缺口、具体问题、引用，不直接改Action为完成 |
| M10 | POST /document-directories；GET /site-file-status；POST /file-verifications | ISF/TMF目录版本及现状→待补及复核状态 |
| M11 | POST /letters/draft；POST /reports/draft；POST /reports/{id}/snapshot；POST /exports | 模板及选择条目→草稿/Excel；签发状态取实际操作，导出不等于发送 |
| M12 | parse_document、extract_rules、recognize_lab、analyze_case | 受限适配器端口，结构化结果必须经过域层校验；不能直连数据库改业务状态 |
| M13 | tools/check_traceability.py；tools/impact.py | 仓库工程CLI，无临床用户HTTP端点 |
| M14 | GET /health/live；GET /health/ready；GET /capabilities | 分别显示进程、依赖和已配置能力；“服务在线”不等于功能全部具备 |

## 3. 关键对象

SourceRef：document_version_id、anchor_id、section/table/footnote、关键片段或摘要、适用范围。原文片段按权限读取；公开导出不能泄漏范围外材料。

ApplicableRule：rule_version_id、summary、conditions、exceptions、children、source_refs、applicability、unknowns。条件表达式通过白名单AST解释，不运行eval、不执行模型提供代码。

LabComparison：matched_identity、match_status、field_results、rule_refs、unknowns、scope。scope明确本次只核对哪些字段/快照，禁止直接返回clinical_safe=true这类无依据整体结论。

IssueView：original_finding、location、recommendation、recommendation_sources、reported_correction、verification、actions、history、next_steps。一个问题可以包含多个不同完成口径的Action。

ReportSnapshot：template_version、fact_revisions、rule_revisions、issue_revisions、coverage_refs、content_hash、实际报告状态及时间。快照读写不可直接复用可变草稿存储。

## 4. 异步操作

长任务POST返回202及job_id。job保存输入版本/哈希、授权范围、任务类型、租约、重试次数及结果引用。相同幂等输入不重复扣费或创建多个发现。失败可从持久阶段重试；重试前复核权限与源版本，权限撤销后不得继续读取文件。完成通知只更新任务和待查看结果，不自动发送中心邮件或提交EDC。

## 5. 用户澄清后的最小接口

| 入口 | 契约 |
| --- | --- |
| POST /carryover-imports/preview；POST /carryover-imports/{id}/confirm | 上次报告/track/文字→可展开问题候选及未知；重复导入幂等，修正关联后保留原来源 |
| POST /actions/confirm-corrected | 明确action_ids、expected_revision和幂等键；服务器取actor/time，optional_note可空，不要求CRC回复/附件；不代替PD已上报确认 |
| POST /check-decisions；POST /check-decisions/{id}/resume | 显示对象/事项/期间、缺失项和受影响路径；用户拒绝后not_checked_by_user，抑制对应追问，其他判断继续；可主动恢复 |
| POST /version-activations；POST /version-activations/{id}/preview-change | 用户输入starts_on、作用范围及资料版本；保存修订，影响预览不自动重判PD |
| GET /directory-references/{id} | 直接查看原目录和简要状态；reference_only不要求先结构化全部目录 |
| GET /lab-support-profiles；POST /lab-reports/{id}/recognize | 返回实际支持范围/验证等级；W08实际自动读取job输出候选、定位和错误，W14增强复用此入口 |

ApplicableRule补充preconditions、trigger、branches、follow_up、completion、required_facts；branch含condition、target/actions和source_refs。规则三值逻辑、日期边界及分析型条款见WORKFLOW_CONTRACTS.md。

所有结果保留使用的范围、资料/规则版本、source_refs、事实/候选/用户确认类别及unknowns。用户确认整改是实际用户动作，不能因未提供可选材料被拒绝。自动比较候选与人工核实分开；用户跳过的相关路径不能继续生成正常或异常判定。共享全输出契约的完整工程验证仍对应AUD-003开放项。
