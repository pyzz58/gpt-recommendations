# W22 适配器离线验收

日期：2026-11-07（Pacific/Auckland）。

被测源码：`ecb36c1`（以最终Git提交和验收记录为准）。

状态：离线适配合同通过；真实模型与真实邮箱分别 `not_run`。本文件不把
transport替身、假SMTP或配置构造称为live连接。

## 覆盖

- OpenAI-compatible：请求/响应JSON、usage与费率、费用上界先于transport、
  认证错误、默认live关闭和完整配置工厂；
- SMTP send-only：MIME正文/附件、STARTTLS+登录、收件人白名单、配置不全、
  认证5xx拒绝、网络丢失unknown及reconcile保持unknown；
- PubMed实时适配：官方E-utilities域名、ESearch→EFetch两阶段、查询/日期/
  结果数/tool/email/API key参数、预印本元数据和429/非法ID错误；
- 项目级来源检索API：owner/workspace、成功fake响应、未配置503、未知策略400
  与限流429；
- MailService：SMTP fake transport通过既有草稿/内容hash/一次性授权/
  幂等attempt/账本；unknown reconcile不新增attempt、不自动重发；
- 新迁移`a1c9e7f2d304`允许`send_only`账号状态，downgrade保留账号行并保守
  映射为`connected`；
- 完整应用回归、科学反馈、W23 readiness/配置和84条RLS策略继续通过。

## 未覆盖

- 没有真实模型base URL、凭据、model ID、费率、额度或provider数据政策；
- 没有真实SMTP账号、凭据、发件地址、测试收件或发送授权；
- 没有NCBI allowlisted网络授权、真实查询或返回结果；全文可用性和医学质量
  不能从元数据适配器通过推导；
- 来源API只返回元数据且不自动入库，没有真实响应质量或科学证据验证；
- 没有真实检索渠道、非mock科学质量、真实收件/线程、真实机构或外包；
- OpenAI-compatible具体供应商的JSON模式、限流语义和tokenization需在
  W22真实连接时逐项验证；
- SMTP不提供收件，且无法严格证明跨SMTP的exactly-once。

模型和邮箱的真实验收必须分别记录，不因另一方通过而提升。
