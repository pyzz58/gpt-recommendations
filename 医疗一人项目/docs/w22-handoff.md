# W22 真实连接适配器与离线验收接手说明

对应：RQ-015、RQ-031；TR-07、TR-09、TR-11、TR-13、TR-14、TR-16、
TR-19、TR-24；W22；AT-015、AT-031。

日期：2026-11-07（Pacific/Auckland）。

状态：IN_PROGRESS。模型与 SMTP 适配器代码和离线 transport 测试已完成；
真实模型、真实检索渠道和真实邮箱均未连接，live 验证保持 `not_run`。

新增Alembic迁移`a1c9e7f2d304`只扩展`mail_accounts.state`以允许
`send_only`。downgrade把既有`send_only`保守映射为`connected`后再恢复旧
约束，不删除账号行；该映射只用于回退兼容，不表示收件能力存在。

## OpenAI-compatible 模型适配

- 使用同一 `ModelProvider` 合同，不复制Agent流程或另建服务。
- 只有 `MEDICAL_ONE_APP_MODE=live`、
  `MEDICAL_ONE_MODEL_PROVIDER=openai_compatible` 和
  `MEDICAL_ONE_MODEL_PROVIDER_LIVE_ENABLED=true` 同时成立才构造真实适配器。
- 必须配置获准的 base URL、API key、model ID、最大上下文、最大输出、
  单次费用上限、输入/输出百万token费率和币种。
- URL只允许HTTPS或回环HTTP；认证失败、429、非2xx、非JSON和schema外输出
  分别形成明确错误码或交给既有schema校验/有限修复。
- 调用前以保守字符上界估算输入，加上最大输出token计算费用上界；超过
  `MEDICAL_ONE_MODEL_PROVIDER_MAX_COST_PER_CALL` 时不调用transport。
- API key只进入进程配置和Authorization header，不进入前端能力、日志、
  prompt、数据库或导出。
- AgentRun记录实际provider/model/mode/usage；live adapter配置不证明模型
  科学性、专业能力或数据政策已经通过。

## SMTP 邮件适配

- SMTP按 `MailAdapter` 合同接入，明确标记为 **send-only**；不把SMTP冒充
  IMAP/API收件能力，当前inbox同步明确返回空，不生成伪收件。
- 只有 `MEDICAL_ONE_MAIL_ADAPTER=smtp` 和
  `MEDICAL_ONE_MAIL_SMTP_LIVE_ENABLED=true` 才可能发送。
- 必须配置SMTP host/port/security、from address、非空收件人白名单；
  使用认证时用户名和密码必须同时存在。配置不全显示unconfigured/disabled。
- 发送仍经过项目草稿、内容hash、一次性授权、幂等attempt和未知态门；
  账号可发送不等于可以绕过项目授权。
- 5xx认证/收件人/数据拒绝明确失败；网络中断或非5xx协议异常进入
  `outcome_unknown`。SMTP无法可靠查询已发送文件夹，reconcile返回unknown，
  保持未知并要求人工/provider侧核对，不自动重发或恢复草稿。
- 附件按数据库中的原件版本/hash加载到MIME，不执行邮件正文指令。

## PubMed E-utilities 来源适配

- 仅允许官方 `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`；
- 必须同时满足 `MEDICAL_ONE_NETWORK_MODE=allowlisted`、
  `MEDICAL_ONE_SOURCE_PUBMED_LIVE_ENABLED=true`，并配置tool name和联系邮箱；
  API key可选但只进入请求参数；
- 先调用ESearch JSON获得数字PMID，再调用EFetch XML，复用既有
  `PubMedXmlAdapter` 解析；
- 日期、最大结果数、联系标识和User-Agent显式写入请求；429和非法ID分别
  阻断，结果保留PubMed元数据、预印本/撤稿标记和全文不可用限制；
- 默认离线工厂不创建网络adapter，来源能力保持not_checked；
- 离线测试注入两次transport响应，断言URL、参数和解析，不发起网络请求。
- 项目级入口为`POST /api/v1/projects/{project_id}/sources/search`，调用前
  通过本地会话和项目读取校验owner/workspace边界；
- 未配置adapter返回503，未知/违规策略返回400，429返回限流，transport失败
  返回502；空adapter不会伪装成“0条结果”；
- API当前只返回元数据，不自动入库；真实检索以后仍须核对来源、全文状态和
  项目授权，不能把元数据响应当成科学证据。

## 配置

配置沿用W23单一dotenv入口，可由 `MEDICAL_ONE_CONFIG_FILE`放在仓库外。
文件权限应限制给运行用户；密钥不进入Git。父进程环境变量优先。

模型方需用户另行提供或确认：

- provider是否为OpenAI-compatible，base URL和数据政策；
- 获准model ID、API key保存方式；
- 输入/输出费率、币种和单次费用上限；
- 是否允许对合成任务做一次有限live调用。

邮箱方需用户另行确认：

- SMTP provider、host、port、STARTTLS/SSL；
- 发件地址、认证方式及凭据保存位置；
- 用户控制的测试收件地址白名单；
- 是否授权一封受控测试邮件。

检索方需用户另行确认：

- 是否允许NCBI E-utilities allowlisted网络访问；
- tool name、联系邮箱、API key保存方式和查询上限；
- 首轮允许的合成/公开查询及数据使用范围。

这些缺件只阻止live验收，不阻止离线适配测试。

## 离线测试

- OpenAI transport由测试函数注入并捕获请求，不访问网络；
- 覆盖structured JSON、usage/费率、保守费用上限、认证失败和工厂禁用；
- SMTP由假连接注入，覆盖MIME/附件、STARTTLS+登录、白名单、配置不全、
  5xx拒绝、网络丢失unknown和reconcile保持unknown；
- PubMed由注入transport覆盖ESearch→EFetch、参数/日期、官方域名、结果上限、
  预印本标签、非法ID和429，不访问NCBI；
- 来源API由fake adapter覆盖项目会话、成功响应、未配置503、未知策略400、
  限流429和项目隔离；
- MailService数据库回归验证unknown reconcile不新增attempt、不自动重发；
- 现有科学反馈、W23 readiness/config和全部应用回归继续运行。

## 真实连接验收顺序

模型和邮箱分别验收，不因一个通过而提升另一个：

1. 模型：在明确额度和数据范围内做有限合成任务，记录请求摘要、模型/用量/
   费用、schema结果、错误及是否改变科学判断；不能证明科学可靠性。
2. 邮箱：只向用户控制白名单地址发送一封受控测试邮件，验证原始收件、线程/
   Message-ID、失败或unknown核对；SMTP send-only仍不证明收件能力。
3. 真实检索渠道、专业机构、付款、合同和实验均不属于适配器离线通过。
   检索真实验收需另记查询、返回元数据、来源策略和全文可用边界。

## 已知限制

- 当前没有真实凭据、模型ID、费率、额度、邮箱或测试收件授权；
- OpenAI-compatible不保证任意供应商支持 `response_format=json_object`，
  真实连接前需选择并核验具体provider；
- SMTP没有严格exactly-once，也没有收件/对账能力；
- 真实模型科学质量、数据驻留、隐私、限流和成本仍需独立记录；
- W24仍为PREPARED，本工作不扩大现实外联、采购或实验授权。
