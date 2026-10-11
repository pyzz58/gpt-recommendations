# AUD-002 — 付费 DeepSeek 结果的私有持久检查点与人工恢复协议

**状态（2026-10-11）**：代码与离线故障注入已经通过；**真实私人持久运行环境尚未部署/验收，GitHub Issue #1 暂不关闭**。整个修复没有再次请求真实 DeepSeek。

## 为什么必须先做这个

传统调用路径：账本 reserve(fsynchronize) → HTTPS 发出去 → DeepSeek 回复 → 更新 Python 内存团队状态 → 标记账本 accepted → 返回状态。若在“收到模型创意”与“调用方成功保存状态”之间崩溃，可能已经付费但没有留下完整导演创意；另一方面付款账本记了成功，自动重试仍被禁止。

新的持久协议使用 [LangGraph checkpoint](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint)（MIT；研究其 checkpoint 与 pending writes 区分）为设计参考，**没有复制 LangGraph 源码，也没有安装 LangGraph 框架**，以免其 task replay / 自动恢复机制无意间重试收费 API。代码文件为 `private_result_checkpoint.py`。

## 现在的顺序（真实模型路径必须提供结果私有 Vault）

```text
独立逐次消费/资料传输许可
     ↓
检查私人存储是 0700 文件夹且不属于任何 Git 工作树
     ↓
校验已接受的每次请求都有完整私有结果 checkpoint
     ↓
PilotJournal.reserve()   ← durably fsync 账本；防止同角色同版本自动重试
     ↓
HTTPS DeepSeek (exactly one explicitly authorized call)
     ↓
解包 JSON / 源稿 hash / 角色合同 / 连续性等 validation
     ↓
PrivateResultVault.save()  ← fsync 0600 结果文件 + 原子 O_EXCL 链接 + fsync 目录
     ↓
PilotJournal.finish("response_accepted", usage)
     ↓
把已完整 checkpoint 的新 team 状态返回调用方
```

每个结果文件独立 `attempt-0001.json`、`attempt-0002.json`，包含必要的私有**完整团队状态**、输入/输出状态 SHA-256、角色、修订版本、调用 request SHA、价格账本 config digest、报告使用量。**不包含 API Key、Authorization header、全部 HTTP 回应正文**。由于 team 状态本身包含文案/创作成果，这些文件必须只存储在可信私人持久环境：不得复制到公开 GitHub / Actions Artifact、Codex 工作区公共仓库、CI cache 或公开日志。

保存阶段只允许新文件，不能覆盖已经接受过的付费结果。对缓存、远程临时运行机器、外部备份的正确加密/恢复策略仍需未来的私有运行部署验证。

## 四种失败与恢复方式

| 失败点 | Durable journal / result | 程序做什么 | 人工要怎么处理 |
| --- | --- | --- | --- |
| 付款请求 reserve 之前 | 无新记录 / 无文件 | 不发网络请求 | 修复配置/授权后重新评估新的请求 |
| reserve 已持久化，但网络超时、连接断开 | pending/timeout/transport uncertain，无文件 | **禁止自动重试**，不能假设没有扣费 | 核对供应商账单及服务商响应；无私有结果时不可承诺能恢复创意 |
| **模型已经返回，但 result checkpoint 写盘失败** | 仍 pending_uncertain，无可靠结果 | 不记作成功、不重发、后续 blocked | 修复可信存储，并人工核对消费；未保存的回复无法凭空恢复 |
| **result checkpoint 已 fsync，journal.finish 前崩溃** | pending_uncertain，且存在有效 checkpoint | **禁止额外 HTTPS**；只允许人工加载并验证同版本 hash、role、request | 私人运行环境需确认授权后调用 `reconcile_saved_result(..., operator_acknowledgement="RECOVER_SAVED_RESULT_NO_API_CALL")`，只更新本地账本并返回已保存的创意 |
| 成功提交后调用方崩溃 | journal accepted + checkpoint 已存在 | 允许以原角色结果和对应前态 hash 离线 `load()` | 从持久结果继续，不重复向 DeepSeek 发送同一请求 |
| 已知结果丢失、被换源或文件权限不安全 | journal accepted，却无法验证 checkpoint | **禁止再推进新的付费岗位** | 核查私有存储、恢复有效备份；不能静默用旧/伪造创意补齐 |

## 重要入口变化

- `agent_live_pilot.run_one_creative_task(..., result_vault=vault)`：真实 `DeepSeekHTTPSClient` **缺少 Vault 即在预付费阶段被拒绝**。
- `agent_live_crew.run_one_locked_role(..., result_vault=vault)`：所有十岗位走相同原则。摄影视觉/原文编辑类工单由真实且有效的 `team` 状态保存。
- `PrivateResultVault.assert_existing_accepted_checkpoint_chain(state)`：拒绝试图用过期团队状态、错误原稿/版本、缺失已接受结果、新出现不确定付款记录继续发送收费请求。
- `PrivateResultVault.reconcile_saved_result()`：**只能人工确认、永远没有网络调用**；需要保存结果与一致的前态才能恢复。`identity_cryptographically_verified=false` 和 `provider_invoice_verified=false` 始终真实报告。
- `one_time_deepseek_cloud_trial.py` 对虚构公共素材也使用临时 Vault 防止违反新入口合同；但其 runner 随 GitHub Job 结束销毁，**不满足未来私人创作长期恢复目标**。已经成功的旧运行仍保留 GitHub 公开虚构结果 artifact。

## 故障注入和验收

`tests/test_private_result_checkpoint.py` 全部使用虚构文本、静态 HTTPS 帧和临时 0700 文件夹：

- 两岗位先后成功，关闭并重新打开 journal 后 2 个结果仍可完整读取；
- 真实 HTTPS 类型未配置私有 Vault 时**在联网之前阻断**；
- 收到模型答复但写 checkpoint 失败后不得再请求；
- 文件已写但账本未完成，重启后经明确恢复操作原样提取结果，provider_calls=0；
- 反复写同一次响应、改动 req/config/version、过期前态、错误文件权限和路径属于 Git 仓库全部阻断；
- 十岗位导演 + 剧本阶段也用同一套私有结果机制；
- 模拟目录 fsync 抛错，但结果链接已经存在，可在重启后对账恢复，不重发 HTTPS。

CI 是离线的，**不构成真实服务商扣费/持久云备份验证**。

## 后续尚未解决的 P0 条件

1. 在一个**可信、真正长期持久、可备份且不可向公开 GitHub 推送**的私有执行环境启用 Vault（目前没有部署，也不能用 GitHub 一次性临时 runner 假装持久）。
2. 私人 UI 需要**验证真实用户身份**，并提供对账与人工恢复/停止操作；现有确认字符串只表示本地意图，不能代替身份。
3. 发生云提供商已扣费但未返回任何可保存字节时，需要明确供应商账单核对与追查，**不保证能恢复已丢失原始回复**。
4. 尚未使用新协议开展真实 DeepSeek 事故演练；不能宣布 P0 已彻底关闭。

## 上游与合规

- [LangGraph Checkpoint README](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/README.md)：state at superstep、pending writes、checkpointer 接口。许可证 [MIT](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)。
- 本项目**借鉴机制、不直接复制代码**；移植整套 LangGraph 或自动重放节点可能反而带来无意重新付费，不符合项目的“付费调用一律手动授权”要求。
- 不使用官方收费模型，没有真实用户稿件，也不要求在用户 Mac 上运行任何命令。
