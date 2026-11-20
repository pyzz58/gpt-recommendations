# W22 DeepSeek 模型 live 验收尝试

对应：RQ-031；TR-01、TR-07、TR-08、TR-09、TR-11、TR-15、TR-19、
TR-24；W22；AT-031。

日期：2026-11-21（Pacific/Auckland）。

状态：`FAILED`。已通过项目`OpenAICompatibleProvider`完成一次真实
`deepseek-flash`调用，但供应商输出未形成可解析的JSON，因此
`agent_delivery.v1` schema校验没有开始。W22整体继续为`IN_PROGRESS`，
PR继续为DRAFT。

## 授权与限制

- 用户授权一次合成任务调用，模型`deepseek-flash`，单次上限USD 0.01；
- 复用本机DeepSeek Key；密钥只在进程内读取和发送Authorization header，
  未进入Git、日志、验收产物或PR；
- 网络运输包装器在第二次尝试进入前主动阻断，实际网络尝试为1次；
- 未自动重试、未修改请求后重跑、未调用邮件或外部研发动作；
- 本次不证明科学质量、专业判断、数据政策、限流表现或W22整体完成。

## 调用结果

| 项目 | 实际结果 |
| --- | --- |
| 项目适配器 | `openai-compatible.v1` |
| 请求URL | `https://api.deepseek.com/chat/completions` |
| 请求模型 | `deepseek-flash` |
| 响应模型 | `deepseek-flash` |
| HTTP状态 | 200 |
| 网络尝试 | 1次，无重试 |
| 请求SHA-256 | `10bf44286cddee60fe620192bcf0213e74cbd070862dfbd019273115a31533d4` |
| 响应SHA-256 | `d4fddf69c45d79d9b4b53c681014014a309666354fda677b24bd067142958f0b` |
| 开始/结束（UTC） | `2026-11-20T23:03:21.229141Z` / `2026-11-20T23:03:24.964423Z` |

适配器返回
`ProviderResponseInvalid: Model provider response is not valid JSON`。
因此JSON合同总结果为`failed`，`agent_delivery.v1` schema校验结果为
`not_run`。HTTP 200只说明上游接受了请求，不表示结构化交付通过。

## 供应商原始 token 用量

供应商响应`usage`字段原值：

| 字段 | 值 |
| --- | ---: |
| `prompt_tokens` | 1,985 |
| `prompt_cache_hit_tokens` | 0 |
| `prompt_cache_miss_tokens` | 1,985 |
| `completion_tokens` | 512 |
| `completion_tokens_details.reasoning_tokens` | 512 |
| `total_tokens` | 2,497 |

用量已核实来自实际HTTP响应，不是本地估算。原始嵌套对象保存在
[`w22-model-live-provider-usage.json`](../traceability/logs/w22-model-live-provider-usage.json)。
完整响应正文在适配器抛出错误后未被保留，因此不能据现有产物重建具体
`content`字段；该限制不等于用量缺失。

## 费用估算

调用时为周末非高峰。DeepSeek官方页面在
`2026-11-20T23:02:45Z`显示`deepseek-flash`的USD费率为：

- 输入缓存未命中：`$0.15 / 1M tokens`；
- 输出：`$0.60 / 1M tokens`。

按全部prompt token均按缓存未命中计费进行保守估算：

```text
input:  1,985 × 0.15 / 1,000,000 = $0.00029775
output:   512 × 0.60 / 1,000,000 = $0.00030720
total:                              $0.00060495
```

该费用为按官方公开费率和供应商返回用量计算的估算值，不是供应商账单或
实际扣款证明。调用前适配器按请求字符上界计算的上界为USD 0.0015603，
低于USD 0.01单次上限；实际估算费用占上限6.0495%。

## 观察与后续边界

供应商将512个completion token全部标记为`reasoning_tokens`。这与默认
thinking模式耗尽本次512-token输出上限的情形一致，但完整响应未留存，
不能据此确认具体失败字段。后续若要修正，需要新的明确调用授权；本轮
没有自动重试或调整后重跑。

证据：

- [验证摘要](../traceability/logs/w22-model-live-verification.json)
- [原始token用量](../traceability/logs/w22-model-live-provider-usage.json)
- [HTTP与单次尝试记录](../traceability/logs/w22-model-live-http-status.log)
- [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)
