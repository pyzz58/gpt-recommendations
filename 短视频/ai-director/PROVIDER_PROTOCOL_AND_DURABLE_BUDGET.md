# AI 短视频专业导演：供应商协议与持久费用预留（GitHub 离线研发版）

> **实施状态 2026-10-11：已开发 DeepSeek Chat Completions 的无网络请求格式、回应字段解析、来源核验及离线持久费用预留。没有任何真的 DeepSeek HTTP 调用、用户文案传输、API Key 使用或扣费。** 必须单独获得用户对真实模型、原稿上传目的地和额度的明确授权才能开发及开启在线运行链路；本次“开始开发”不等于开通。

源码：[agent_provider_wire.py](agent_provider_wire.py)、[agent_durable_preflight.py](agent_durable_preflight.py)；回归测试：[tests/test_agent_provider_preflight.py](tests/test_agent_provider_preflight.py)。

## 官方 API 依据与当前界面

查询过 DeepSeek 的最新官方文档：

- [DeepSeek 2026-09-10 更新日志](https://api-docs.deepseek.com/updates/)：DeepSeek V4.1 Flash 的 API 名称为 `deepseek-flash`。本项目不使用已退役的 `deepseek-chat` 和 `deepseek-v4-flash` 名称。
- [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)：`POST https://api.deepseek.com/chat/completions`，主要字段 `model`、`messages`、`response_format`、`max_tokens`、`stream`；回复包括 `choices[0].message.content`、`finish_reason`、`usage.prompt_tokens`、`usage.completion_tokens`、`usage.total_tokens` 以及可能的缓存命中/未命中 Token。
- [JSON Output](https://api-docs.deepseek.com/guides/json_mode/)：支持 `response_format={"type":"json_object"}`，但模型仍可能输出空文本，必须严格校验，并设置合理输出上限。JSON 模式不自动等于符合导演岗位的具体 schema。
- [模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)：DeepSeek 费率区分缓存命中、未命中、输出及峰谷时段。本项目不内置实时生效的准确支付报价；由未来获授权的私有运行模块先检查官方价目、以适当的最高费率填写配置，不能依赖本次测试中的单价。

**注意：这是已经根据文档写好的请求/响应数据协议；当前源码没有联网发送函数，所以还不能执行真实供应商调用。**

## 实际新代码在做什么？

`agent_provider_wire.prepare_chat_request` 生成精确的 DeepSeek POST 描述（`endpoint`、`method`、body 与 JSON 输出设置），但标注 `dispatch_authorized=false`。不读 API Key，没有网络栈，不执行 HTTP。

`agent_provider_wire.parse_chat_completion` 解析未来供应商返回的完整 JSON 响应，严格拒绝多候选回复、模型名不匹配、`finish_reason=length` 被截断、空文本、重复 JSON 键、错误用量计数、部分缓存拆分、非合法 JSON 以及超出声明输出 Token 的回复。

`normalize_usage` 采用回复中的 `usage` **供应商申报 Token 计数**，计算按传入单价的费用估计。如果没有完整缓存命中/未命中拆分，就保守地按全部输入为未命中；若供应商只返回半截拆分则阻断并要求人工排查。供应商的自报用量并不等于独立验证过的实际账单或付款扣款记录。

`agent_durable_preflight.PrivateReservationJournal` 采用 POSIX 文件锁（同项目只有一个持锁者）、本地临时文件 + fsync + 原子 replace，先**落盘预留**再获取模拟响应。日志仅存请求 SHA-256、岗位、修订号、费率预留、原始来源哈希、可能的报告用量，**不会保存 prompt、私人文案、API Key 或原始回复**。在接收到对账结果之前，不能返还或重复花费同一笔未知费用。

`agent_durable_preflight.OfflineResponseFrames` 是唯一允许进入新链路的执行器：读取内存中预写好的合成 DeepSeek 风格响应。拒绝任意可执行 HTTP 客户端、插入调用函数、子类和未经授权的真实网络传输；也不会调用旧单体 `local_director.py` 的接口。

## 超时、进程中断和人工核销原则

- 请求前写 `pending_uncertain`。一旦写入但没收到明确响应，不得假设本次免费。
- 模拟超时 → `timeout_unknown`；模拟传输故障 → `transport_unknown`。这些记录在关机/新进程打开文件时仍然存在，并阻断后续新的模拟预留，不自动重试。
- 提供商回复符合协议但岗位内容不合格 → `response_rejected`，预留保留，不自动反复消耗模型。
- 如果供应商报告 Token 按声明价格算出的费用 **高于本次预留金额**，写 `usage_overrun_requires_review` 并阻断继续。Token 代理估算不是已知分词器的上界；超过预留金额是必须人工核算的严重问题。**这道事后门禁不能追回已经产生的真实费用。**
- 岗位回复通过 → `response_accepted`，供应商申报计数与费用估计写入日志，交给原有 `agent_role_contracts.submit_role_output` 更新新的团队状态；旧状态及权威文案不被修改。
- 出现 `pending_uncertain` / `timeout_unknown` / `transport_unknown` / `usage_overrun_requires_review`，系统不会自动“修复账本”继续。未来真实供应商对账需引入授权身份、可核实账单和审计操作记录；本版故意没有开放危险的人工改状态命令。

这只是在 GitHub Actions/Linux 环境进行的**持久化机制和故障状态模拟**。未来需要针对 Mac 本地文件系统/崩溃真机断电、网络分区、容器多实例、供应商结算延迟、账本篡改与灾难恢复再验证；不可把单机文件锁和代理费率称作跨设备、跨实例的绝对支付上限。真实费用上限应配合供应商账户额度/预付余额限制，否则任何客户端只能估算而无法从技术上确保不会被供应商超额扣款。

## 为什么没有直接复用旧 `llm_budget.py`？

旧单体导演实现已有 `llm_budget.BudgetSession` 的文件锁和估价预留，但单个会话只绑定一个模型和单价，且为其原有导演进程设计。本项目新增团队是按岗位分配模型并接入严格剧情契约，因此本轮隔离新增一份**更小的专用无网络示范账本**，不碰旧代码、旧本地工作区与真人 `jobs/`。后续考虑合并必须先完成兼容测试和费用状态迁移，不做两本账并发扣款。

## 仍未实施与未来授权步骤

1. **真实发送 HTTP**：当前没有联网适配器（包括没有可绕过的 `enable_paid_api` JSON 标志），不能调用收费 API。
2. **实际 Token 与付款的强保证**：供应商计数仅供报告；还需核对真实模型账单、峰谷资费和可核验的账户硬限额。
3. **隐私与安全**：必须由用户指定是否允许传输真实文案及上游专业交付、服务商和处理区域，审核留存政策和密钥管理；公开 GitHub 永不存储私人输入、Prompt 包或费用记录。
4. **失败后的继续**：当前禁止一切未知费用的自动恢复。需要未来人工核查并记录身份凭证、供应商日志和核算金额。
5. **Mac 部署与真实短视频**：本阶段完全没有，也不会自动开始。

> 研发完成后真正上云/付款，须先单独取得用户对**模型名、供应商、最高真实花费、最大调用次数、私人素材传输和部署位置**的明确同意。不能用“继续研发”代替。
