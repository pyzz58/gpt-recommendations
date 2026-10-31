# 接口与模块约定

状态：v0.4设计契约，后续由FastAPI生成并校验OpenAPI。接口路径在实现时可细化，但固定理论、模块和任务编号不变。

## 1. 共同约定

API前缀/api/v1。身份来自获验证的OIDC会话；无正式身份源时只允许`synthetic`/`test`环境使用服务端配置的合成会话，生产环境拒绝合成登录。服务端从签名会话推导actor和tenant，再查W01项目/中心授权，不接受客户端通过请求头、查询参数或JSON自报操作者。浏览器使用同源HttpOnly Cookie；正式写入仍需按用途配置CSRF。所有写入接收幂等键及expected_revision，审计与业务事务一致提交。

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
| M09 | POST /safety-assessments | 允许范围的事实、明确规则版本及上下文→候选分析、缺口、具体问题、引用，不直接改Action为完成 |
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

## 6. v0.4执行契约

共同回复采用[EXECUTION_CONTRACTS](EXECUTION_CONTRACTS.md)的OutputEnvelope，按用途提供政策版本、事实/候选/用户确认分类与unknowns/not_checked；临床/时间/模板最低输入按同文定义。CommonPolicySet使用实际原文而非模型记忆。自动检验端口支持范围、值类型和实测指标见[LAB_AUTOMATION](LAB_AUTOMATION.md)。

## 7. W02已实现入口

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/auth/synthetic/session` | 仅在synthetic/test启用；actor与tenant来自服务端配置，响应设置签名HttpOnly Cookie |
| `GET /api/v1/auth/oidc/login`；`GET /api/v1/auth/oidc/callback` | Authlib授权码/OIDC适配；未配置issuer、client和secret时明确返回503；实际身份源尚未提供，不能称正式登录已验证 |
| `POST /api/v1/auth/logout` | 删除CRA签名会话 |
| `GET /api/v1/me/scopes` | 从可信身份调用W01授权服务，仅返回可访问项目/中心及角色 |
| `GET /health/live`；`GET /health/ready`；`GET /capabilities` | 分别表示进程、PostgreSQL依赖和真实已配置能力，不用服务在线替代功能验证 |

错误统一包含`error.code`、`error.message`、`retryable`及可选安全详情，HTTP状态区分401、403、409、422和503。`contracts/openapi.json`从实际FastAPI应用生成，`web/src/api/generated.ts`从该契约生成；两者由`npm --prefix web run api:check`阻止漂移。OutputEnvelope作为OpenAPI组件与运行时Pydantic模型共用同一源。

## 8. W03已实现资料入口

所有资料写入要求有效会话、匹配的`X-CSRF-Token`和`Idempotency-Key`。actor/tenant/中心范围仍由服务端会话及W01授权推导。

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/studies/{study_id}/documents` | 大小/签名/类型校验后私有保存，创建不可变首版本、业务Job和Outbox；返回202及job_id |
| `POST /api/v1/documents/{document_id}/versions` | 以`expected_revision`追加版本；旧版本源字段由数据库触发器禁止更新 |
| `GET /api/v1/studies/{study_id}/documents` | 只列当前已授权中心和范围的资料 |
| `GET /api/v1/documents/{document_id}/versions` | 返回业务版本、发布日期、上传时间、用户手动开始使用信息、解析状态及重复文件引用 |
| `GET /api/v1/document-versions/{version_id}/anchors` | 返回DOCX章节/节点/表格/脚注/格式或PDF页/坐标/表格单元 |
| `GET /api/v1/document-versions/{version_id}/coverage` | 分开返回processed/background/not_applicable/unsupported/failed/pending |
| `GET /api/v1/document-versions/{version_id}/content` | 每次读取前重新授权，以私有、no-store响应返回原文件；不返回永久公开地址 |
| `GET /api/v1/jobs/{job_id}`；`POST /api/v1/jobs/{job_id}/retry` | 查询业务Job/尝试次数；重试沿用同一版本，不新建资料版本 |

上传先使用内容哈希检测重复，但重复只记录`duplicate_of_version_id`，不自动判定版本替代或业务生效。业务写入、Job和Outbox同事务提交；Outbox relay再通过Procrastinate queueing lock幂等入队。worker只收到内部job_id，处理前重新查W01授权。源文件存储使用boto3私有S3适配；开发环境可用不位于Web根目录的本地私有适配。PDF查看器只读取上述授权内容接口，并通过页/bbox叠层定位，不替代OCR或解析覆盖。

## 9. W04已实现规则入口

规则写入使用有效会话、服务端范围、CSRF和幂等键；状态写入同时保存AUD及expected revision。读取在返回树、来源或适用性前重新检查项目/中心授权。

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/document-versions/{version_id}/rule-candidates` | 只处理已完成/部分解析的规则资料；实际provider读取锚点；重复哈希复用规范版本快照，不重复规则或确认 |
| `GET /api/v1/studies/{study_id}/rules` | 返回稳定规则、当前版本及候选版本；只含授权项目/中心和适用层 |
| `GET /api/v1/rule-versions/{version_id}` | 返回四层RuleNode、不可变版本状态、来源引用和逐条关系 |
| `POST /api/v1/rules/{rule_id}/confirmation` | 以expected_revision和base_version_id确认用户增删改；生成新版本，不覆盖候选/旧版 |
| `GET /api/v1/rule-snapshots/{snapshot_id}/coverage` | 分开返回processed/background/analysis_required/unsupported/failed |
| `POST /api/v1/version-activations` | 用户输入项目/中心实际`starts_on`及可选`ends_before`；上传时间不替代，重叠返回冲突ID |
| `POST /api/v1/version-activations/{id}/preview-change` | 预览更正区间、重叠和受影响规则/版本；不追溯重判历史 |
| `POST /api/v1/rules/applicable` | 按项目、中心、临床事件日和事实返回当前确认规则及OutputEnvelope；同规则多层并列、同层重叠冲突而不自动取最新/更严 |

`RuleNode`包含summary、preconditions、trigger、branches、exceptions、follow_up、completion、required_facts、children和source_refs。条件使用closed AST及true/false/unknown；无结构自由文本返回analysis_required。W04确定性provider仅支持任务卡声明的规则语句子集，不能表述为通用临床文本理解。

## 10. W05已实现患者入口

患者/事实写入要求项目中心和有效会话范围，状态写入使用CSRF、幂等键和审计；读取时间线、窗口、断点或跳过选择前重新授权。

| 接口 | 实现约束 |
| --- | --- |
| `GET /api/v1/studies/{study_id}/subjects` | 只列指定已授权中心患者；阶段从当前确定性事实计算，模型建议不覆盖 |
| `POST /api/v1/studies/{study_id}/subjects` | 创建去标识患者及稳定来源标识 |
| `POST /api/v1/subjects/{id}/identifiers` | 显式映射额外来源ID到既有患者，不按姓名或相似值自动合并 |
| `POST /api/v1/studies/{study_id}/facts/import` | 授权结构化JSON事实导入，保留原值、来源、时间、精度和重复实例 |
| `POST /api/v1/studies/{study_id}/facts/import-file` | 解析已映射JSON/CSV/XLSX，仅为结构化上下文导入，不执行宏或OCR |
| `GET /api/v1/subjects/{id}/timeline` | 返回完整事实修订和当前标记；date-only不增加时分 |
| `POST /api/v1/facts/{id}/confirm` | 生成独立CRA确认修订，原来源和历史保留 |
| `POST /api/v1/subjects/{id}/visit-requirements` | 用事件日适用的已确认W04规则计算日期窗口、所需事实、允许来源、unknown及可继续事项，返回OutputEnvelope |
| `GET /api/v1/subjects/{id}/visit-requirements?event_date=` | 返回已保存的最新规则驱动窗口快照 |
| `POST /api/v1/subjects/{id}/coverage`；`GET .../coverage` | 按类别和范围版本化核查断点，正常范围可简记，未核实范围分开 |
| `POST /api/v1/subjects/{id}/check-decisions` | 保存本患者/事项/期间的missing-data局部跳过及影响范围，不创建Issue |
| `POST /api/v1/subjects/{id}/check-decisions/{decision_id}/resume` | 用户显式恢复；新事实仅把`recovery_available`置为true，不自动恢复 |

`visit_window` OutputEnvelope区分原始/CRA确认事实、规则版本、窗口计算、unknown和`not_checked_by_user`。缺锚点只停止依赖窗口，已识别患者的其他类别工作继续。W05的本地跳过和断点不替代M05完整工作台，也不宣称局部资料是完整病史。

## 11. W06已实现遗留与监查入口

Issue、Action、Query和carryover写入要求有效会话、服务端项目/中心授权、CSRF和幂等键；读取、确认或导入前重新检查范围。`Idempotency-Key`在同一请求体内，批量确认按每个Action的`expected_revision`检查，不静默覆盖并发变化。

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/studies/{study_id}/issues`；`GET /api/v1/studies/{study_id}/issues?site_id=` | 创建或列出中心范围Issue；允许原问题/位置/建议/进展不全时保存，稳定编号只在本项目/中心内唯一 |
| `GET /api/v1/issues/{id}` | 返回原问题、位置、建议及来源、已知进展、分项Action、Query和append-only操作历史 |
| `POST /api/v1/issues/{id}/actions` | 在既有Issue下增加独立完成口径的Action；期限必须与明确依据同时出现 |
| `POST /api/v1/actions/confirm-corrected` | 明确Action IDs和各自expected revision；服务器记录actor/time及`user_confirmation`，不要求回复、附件、位置或额外证明 |
| `POST /api/v1/actions/{id}/confirm-reported` | 仅`pd_reporting`可用；用户明确陈述已上报后只完成该Action，不完成其他整改 |
| `POST /api/v1/actions/{id}/reopen` | 用户发现仍未完成时重开指定Action，保留原确认及历史 |
| `POST /api/v1/issues/{id}/replies` | 可选保存已有沟通/中心报告，不反向完成Action |
| `POST /api/v1/issues/{id}/query-links` | 草稿可缺正式编号；正式Query须有实际外部编号和创建日；有截止日必须有期限来源，缺期限返回unknown而非超期天数 |
| `POST /api/v1/studies/{study_id}/monitoring-visits`；`GET /api/v1/monitoring-visits/{id}/workbench` | 建立本次监查并带入当前中心全部未完Issue；通过M02公开读取已上传资料引用，`reference_only`不冒充M10状态 |
| `POST /api/v1/monitoring-visits/{id}/previsit-selection` | 保存访前选择集合，不删除未选Issue，也不生成最终信件 |
| `POST /api/v1/document-versions/{id}/carryover-imports/preview`；`POST /api/v1/studies/{study_id}/carryover-imports/preview-text` | 从实际DOCX/PDF锚点、XLSX track行或问题文字生成候选；未知字段保留，不调用模型补齐 |
| `GET /api/v1/carryover-imports/{id}`；`POST /api/v1/carryover-imports/{id}/confirm` | 预览→用户修正→确认导入；相同来源哈希和原编号幂等映射，已有Issue复用编号并追加来源/历史 |

Issue聚合状态只用于展示；Action分别保存`open/reported_done/completed/needs_correction`。PD上报与数据更正可一完成一待办。导入候选的缺项保持unknown，用户修正与原文位置分别保存；重复文件不会重复建Issue。W06不接入或伪装M10目录全量状态，也不正式提交Query、外发或生成模板化信件。

## 12. W07已实现EDC Excel入口

预览上传先经W03文件签名/大小检查并存入私有源版本；actor、项目/中心和导出范围由服务端鉴权保存。公式只读取工作簿缓存，不执行公式、宏或嵌入内容。

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/studies/{study_id}/edc-imports/preview` | multipart上传macro-free `.xlsx`，保存导出起止时间、范围声明、sheet/row/cell、原值、公式、缓存和建议列映射；相同幂等键不重复预览 |
| `GET /api/v1/edc-imports/{id}` | 返回全部sheet元数据、采样行、公式缓存及同表头已确认映射 |
| `POST /api/v1/edc-imports/{id}/confirm` | 用户确认sheet、表头和标准字段映射后，事务创建不可变快照、原始行及标准检验记录；可保存映射供同表头复用 |
| `GET /api/v1/edc-snapshots/{id}` | 返回快照范围、sheet清单、原始行定位、公式/缓存及标准记录；不返回医学整体结论 |
| `GET /api/v1/studies/{study_id}/edc-snapshots?site_id=` | 列出该授权中心已确认的不可变快照摘要，供M08先匹配再核对；不暴露范围外快照 |
| `POST /api/v1/edc-snapshots/{id}/lookup` | 未命中固定返回`not_seen_in_export`和`edc_omission_inferred=false`，不得改写为EDC漏录 |
| `GET /api/v1/studies/{study_id}/edc-import-mappings` | 按中心及可选表头指纹返回已确认映射，新导出预览复用而非重建 |

映射至少覆盖受试者外部ID、检验项目、结果、采样日期或时间，以及初检/复查实例；同日初检与复查分别保存。标准记录保留operator、Decimal值、原文、单位、采样时间、报告日期、实例键、身份映射状态、验证问题及Excel行定位。相同源哈希、映射和导出范围重复确认返回原快照；更正导出另建快照。

## 13. W08已实现检验源文件与比较入口

上传端先经M02私有存储、文件签名/大小和授权检查，再创建持久`lab_recognition_jobs`记录。文字PDF由pdfplumber读取表结构；清晰PNG/JPEG在`CRA_OCR_PROVIDER=docling`时由隔离Docling进程读取。provider不可用或失败时保留原文件和报告记录，允许少量人工候选或范围跳过，不冒充自动能力完成。

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/studies/{study_id}/lab-reports` | multipart上传合成或获授权源报告；保存源版本/哈希、provider/model、SupportProfile、Job、候选字段、原文/bbox和失败原因 |
| `GET /api/v1/studies/{study_id}/lab-reports`；`GET /api/v1/lab-reports/{id}` | 按授权范围返回报告、候选、最新用户动作和来源位置；自动候选与人工核实分列 |
| `POST /api/v1/lab-reports/{id}/observations/{observation_id}/decision` | confirm/correct/skip追加保存；更正不覆盖自动识别结果，跳过只影响对应路径且不计正常 |
| `POST /api/v1/lab-reports/{id}/observations/batch-confirm` | 仅批量确认通过结构/来源/实例校验的候选，避免逐字段机械点击 |
| `POST /api/v1/lab-reports/{id}/observations` | 仅用于少量不可读/失败路径的人工候选补录，保留补录依据 |
| `POST /api/v1/lab-comparisons` | 同一中心内先匹配再比较；返回`match_status`、`result_status`、字段结果、未知和明确scope，歧义不自动选数值最接近项 |
| `GET /api/v1/lab-comparisons/{id}` | 读取不可变比较快照、已关联M06问题和来源 |
| `POST /api/v1/lab-comparisons/{id}/issues` | 用户选择非一致字段后创建`edc_correction`待办；不自动创建PD上报或完成整改 |

比较值保留原文、Decimal和可选`< <= > >=`，不同/未知单位返回`unit_review`。原始报告没有缓存或无法解释的文本不猜成数值。确认/更正/跳过使报告revision前进；比较字段按有效来源状态返回`stale`，只有未变化字段可继续关联M06。`not_seen_in_export`沿用W07范围语义，不能改写为EDC漏录。SupportProfile、评估结果和未测范围见`validation/LAB_AUTOMATION_SCOPE.md`。

## 14. W09已实现安全分析入口

安全分析写命令要求有效会话、服务端项目/中心范围、CSRF及幂等键；读取前重新授权。程序使用W04已确认且按事件日生效的有限AST计算维度，模型只在允许解释模板与证据ID中选择，不决定维度、不关闭Action。

| 接口 | 实现约束 |
| --- | --- |
| `POST /api/v1/safety-assessments` | 输入受试者、事件类型/日期、所需维度和可选检验比较ID；保存事实/规则快照、候选/unknown、具体问题、证据与及时线索 |
| `GET /api/v1/safety-assessments/{id}` | 返回固定维度、CRA复核、医学答复、来源、provider状态和OutputEnvelope；不提供全局`clinical_safe`字段 |
| `GET /api/v1/studies/{study_id}/safety-assessments?site_id=&subject_id=` | 只列授权中心内指定受试者的分析记录摘要 |
| `POST /api/v1/safety-assessments/{id}/cra-review` | 追加CRA复核决定；`not_checked_by_user`通过M04/W05局部CheckDecision限定维度和事件日，不计正常 |
| `POST /api/v1/safety-assessments/{id}/medical-response` | 独立保存研究者或医学人员答复，不覆盖系统候选或CRA复核 |
| `POST /api/v1/safety-assessments/{id}/issues` | 用户选择维度后创建M06 `medical_clarification` Action；provider不能完成、上报或关闭该Action |

分析记录不可变；CRA复核、医学答复和M06关联以独立记录追加。AE收集、分级、SAE严重性、相关性、预期性、AESI、DLT、PD及时报告分别保存。缺AESI/DLT/IB/知悉时间或项目时限时保持unknown，不从检验一致推断未发生AE或临床安全。模型自由文本、虚拟引用、越界数字/结论均被拒绝，程序问题和未知保留。
