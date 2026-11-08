# W22 适配器离线验收

日期：2026-11-08（Pacific/Auckland）。

被测源码：以最终源码提交和`traceability/acceptance-records.json`为准。

状态：适配器已实现，离线合同通过；真实检索、模型与邮箱分别`not_run`。
本文件不把transport替身、假SMTP、本地XML或配置构造称为live连接。

## 覆盖

- OpenAI-compatible：请求/响应JSON、usage与费率、费用上界先于transport、
  认证错误、默认live关闭和完整配置工厂；
- SMTP send-only：MIME正文/附件、STARTTLS+登录、收件人白名单、配置不全、
  认证5xx拒绝、网络丢失unknown及reconcile保持unknown；
- PubMed实时适配：官方E-utilities域名、ESearch→EFetch两阶段、查询/日期/
  结果数/tool/email/API key参数、预印本元数据和429/非法ID错误；
- 项目级来源检索API：owner/workspace、成功fake响应、未配置503、未知策略400
  与限流429；成功结果写入不可变项目快照，可按ID重读；
- 来源执行模式：fake adapter与本地`pubmed.xml.v1`写入`mode=mock`；真实HTTP
  工厂适配器在离线测试中报告`mode=live`但不调用网络；POST、GET和数据库的
  mode、实际adapter列表、记录及hash一致；未匹配adapter不写入列表，混合模式
  返回409且不产生快照。
- MailService：SMTP fake transport通过既有草稿/内容hash/一次性授权/
  幂等attempt/账本；unknown reconcile不新增attempt、不自动重发；
- 新迁移`a1c9e7f2d304`允许`send_only`账号状态，downgrade保留账号行并保守
  映射为`connected`；
- 完整应用回归、科学反馈、W23 readiness/配置和85条RLS策略继续通过。

## 未覆盖

- 没有真实模型base URL、凭据、model ID、费率、额度或provider数据政策；
- 没有真实SMTP账号、凭据、发件地址、测试收件或发送授权；
- 没有NCBI allowlisted网络授权、真实查询或返回结果；全文可用性和医学质量
  不能从元数据适配器通过推导；
- 真实联网检索验收`not_run`；HTTP工厂的`live`模式标记只通过离线构造测试，
  不证明DNS、TLS、NCBI响应、限流或数据质量；
- 来源API只保存元数据快照，不自动取得/导入全文，没有真实响应质量或科学证据验证；
- 没有真实检索渠道、非mock科学质量、真实收件/线程、真实机构或外包；
- OpenAI-compatible具体供应商的JSON模式、限流语义和tokenization需在
  W22真实连接时逐项验证；
- SMTP不提供收件，且无法严格证明跨SMTP的exactly-once。

模型和邮箱的真实验收必须分别记录，不因另一方通过而提升。
