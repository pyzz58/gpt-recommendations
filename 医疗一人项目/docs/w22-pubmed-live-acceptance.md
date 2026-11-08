# W22 PubMed 来源检索 live 验收

日期：2026-11-08（Pacific/Auckland）。

对应：RQ-011、RQ-031；TR-09、TR-19；W07、W22；AT-011、AT-031。

状态：PubMed 来源检索的单次 live 链路通过；W22整体仍为`IN_PROGRESS`。
真实模型和真实邮箱继续为`not_run`。

## 授权与项目

- 授权人：项目所有者；仅限2026-11-08本轮执行，未建立定时任务；
- 配置位于仓库外`/Users/zz/.config/medical-one-person/medical-one.env`，
  文件权限为`0600`；联系邮箱未写入本报告、日志或Git；
- 只启用PubMed live来源；模型provider和SMTP均保持mock、live开关为false；
- allowlisted网络、官方E-utilities域名、tool name、20秒超时、5条结果上限；
- 未使用API key；未下载全文，未提交私人资料；
- 执行时应用数据库没有既有项目。因此建立一个项目内合成目标用于承载快照，
  项目名明确标记“live验收（合成）”，不冒充既有现实研发项目。

项目ID：`5ce8e636-bc60-46e0-a44d-7d8e6c651011`。

## 实际请求

首轮查询：

```text
(feline OR cats) AND ("antibody-drug conjugate" OR "antibody-drug conjugates")
```

日期范围`2020-01-01`至`2026-11-08`，结果上限5，单次HTTP超时20秒。

- 本地项目级API响应：HTTP 200；
- ESearch与EFetch均通过adapter的2xx成功路径，共2次上游HTTP请求；
- 未重试；
- 返回非空结果并经过EFetch，因此未执行零结果备用查询；
- 实际请求开始时间由命令持续时间推算约为
  `2026-11-08T08:35:06Z`，快照持久化完成时间为
  `2026-11-08T08:35:08.704546Z`；
- adapter拒绝非2xx或限流，故本次成功响应证明两阶段均为2xx；当前未单独记录
  每个上游请求的精确状态码，该细节保留为未观测项。

## 快照与重读

- 项目快照ID：`bc1a5e62-a302-46e9-bfa1-cfd8357e2e98`；
- 执行模式：`live`；
- 实际adapter：`pubmed.eutils.v1`；
- 返回数量：4；
- query SHA-256：
  `d436874a4588d1e4c1e99492448cf7c35f840cf2f87dc1a2efef4f8ecc4bbdc8`；
- result SHA-256：
  `8cbd9e7e83d6ed0bdeb98e88450ccd5368affe289c7f113ad1a30c39b5ee82b4`。

POST响应与GET重读的snapshot ID、政策、查询、adapter、全部记录、数量及
query/result hash一致。两次响应的时间字符串采用不同时区表示，但解析后为同一
UTC时刻。数据库行的项目、模式、adapter、数量和hash也一致。

返回题录：

| PMID | DOI | 出版日期 |
| --- | --- | --- |
| 42655798 | 10.3390/vetsci13080778 | 2026-08-03 |
| 41900948 | 10.3390/life16030430 | 2026-03-06 |
| 39262442 | 10.1093/abt/tbae014 | 2024-07-10 |
| 33919468 | 10.3390/cancers13092007 | 2021-04-21 |

## 边界

- 本次只验证公开题录/摘要元数据的检索、持久化和重读链路；
- 不证明文献质量、猫肿瘤适用性、抗体偶联药物疗效/安全性或任何科学结论；
- 未取得全文，`raw_fulltext_available=false`仍适用；
- 搜索结果不能直接把任何论文升级为项目证据或治疗依据；
- 真实模型、邮箱、真人专家及现实外包验证均未运行；
- 授权中的联系邮箱按原值使用，是否确为所有者预期地址需由所有者自行确认；
- W22继续保持`IN_PROGRESS`，PR继续为DRAFT。
