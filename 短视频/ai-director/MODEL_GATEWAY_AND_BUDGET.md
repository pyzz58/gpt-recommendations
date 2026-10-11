# 专业导演多 Agent：模型路由与预算预检（离线版 v0.1）

> 状态：**已编写和测试的纯离线模拟程序，不是已开通的模型调用接口**。不发起 DeepSeek、OpenAI 或任何外部模型请求；没有上传用户文案、调用付费 API、使用真实密钥、生成视频或部署 Mac。

对应源码：[agent_model_gateway.py](agent_model_gateway.py)；已有专业指令：[agent_role_contracts.py](agent_role_contracts.py)；原有任务调度：[agent_team.py](agent_team.py)。

## 为什么要加这一层

已有 `agent_team` 管十阶段岗位 DAG、版本与返工；`agent_role_contracts` 生成专业 system/user 提示词并验证严格 JSON；`agent_executor` 用预写好的结构化交付模拟岗位执行。

本次增加的是**未来模型调用前的一层独立模型路由和预算检查**：针对每个岗位声明供应商/模型标识、输入输出 Token 限额和人民币计价费率；构造含岗位提示词与 Schema 的私有请求对象；预检上下文代理用量、预算与调用次数；从只能返回预写 JSON 的 `OfflineMockTransport` 收取模拟响应；交给 `agent_role_contracts.submit_role_output` 校验和入账。全过程没有外部调用。

### 十阶段中的工作过程

```text
用户文案 / 权威分镜（仅在未来获授权的私有执行环境）
  → agent_team.packet：可执行岗位 + source_digest + 上游版本
  → agent_role_contracts.build_role_messages：专业指令 + JSON schema
  → configure_profiles：按岗位选择 provider/model/费率/Token 上限
  → OfflineBudgetBook.quote：估算输入代理和本次输出预留费用
  → OfflineBudgetBook.reserve：检查总限额、尝试次数，预留模拟预算
  → OfflineMockTransport：仅读取预写好的原始 JSON 字符串
  → agent_role_contracts.submit_role_output：严格 JSON + 专业内容检查
  → agent_team：产生新账本、推进 DAG 或由总导演定向返工
```

**没有网络模型适配器，也不能把 arbitrary callable / HTTP 客户端插入当前模拟接口**。`simulate_one` 严格要求 `OfflineMockTransport` 实例的精确类型，拒绝自定义子类或任意外部传输器。与已有 `agent_executor` 的不联网保障保持隔离，不会修改旧链路。

## 可替换的供应商配置（仅声明，不执行）

```python
from agent_model_gateway import configure_profiles, OfflineBudgetBook

# 以下完全是假想单价/供应商 ID，只用于合成测试及解释结构。
# 不能作为 DeepSeek 真实价格、官方模型名称或账户报价。
config = configure_profiles(
    profiles={
        "role_fast": {
            "provider": "synthetic-provider",
            "model": "synthetic-fast",
            "max_input_tokens": 200000,
            "max_output_tokens": 4096,
            "input_cny_per_m": "3.20",
            "output_cny_per_m": "18.90"
        },
        "role_director": {
            "provider": "synthetic-provider",
            "model": "synthetic-director",
            "max_input_tokens": 200000,
            "max_output_tokens": 4096,
            "input_cny_per_m": "4.10",
            "output_cny_per_m": "23.30"
        }
    },
    routing={"*": "role_fast",
             "director_brief": "role_director",
             "director_final": "role_director"},
    cap_cny="5.00",
    max_attempts=10
)
book = OfflineBudgetBook(config)
```

关键含义：
- `routing` 可以为全体岗位配置 `*` 默认模型，并针对总导演、摄影或其他任务指定不同档次的模型。不会自动调用任何一个模型。
- `cap_cny` 是**离线模拟预留金额**的总上限，不是用户已经批准的真实付款额。
- `input_cny_per_m`、`output_cny_per_m` 由调用方显式指定，**本模块不写死/验证供应商现行价格**。真实接入前必须核对模型 ID、输入/输出缓存计价、货币、汇率、平台手续费、供应商账单政策等，并取得用户明确授权。
- `max_input_tokens`、`max_output_tokens` 和 `max_attempts` 都必须是合法整数；拒绝零/负/NaN/Infinity 的费用、无效任务路由和零价格等危险配置。

## Token 与费用估算边界

`input_proxy_tokens = len(UTF-8 编码后的消息 JSON) + 1024` 是**对某类 BPE 分词器偏保守的代理值，但不是任何供应商的准确 Token 数，不能作为可靠的实际计费上界**。未来各供应商可能采用不同 tokenizer、图片/多模态附加计费、缓存折扣、推理 Token、特殊消息包装。当前没有硬编码任何真实价目表。

```text
本次模拟预留金额（人民币） =
  [输入代理 Token × 声明的每百万输入 Token 价格
   + 最大允许输出 Token × 声明的每百万输出 Token 价格] / 1,000,000
```

金额用 `Decimal` 计算、向上取到 0.00000001 元；每次尝试必须在模拟预算内。**无实际模型费产生，所以所有账本都标记 `actual_billed_cny=0`、`actual_provider_calls=0`。** 同时保留单次报价、保留金额、修订号、任务 ID、模型路由与是否合格的信息。

测试失败/模型回复无效时，同样保留该次模拟预留并计入尝试次数；不会自动重试、退费、重新生成或重新分配角色。缺少本来应该存在的模拟回复时停止，不增加预算记录。

## 保护机制

1. **不接入任何模型传输**：本次 `OfflineMockTransport` 只能消费在运行前写好、保存在内存里的合成原始 JSON；`simulate_one` 拒绝其他实现或子类，不能用一个同名方法伪装成授权模型。
2. **源稿不得静默更改**：仍经 `role_context` 绑定 `source_digest`、当前基础分镜哈希、岗位字段权限、动作与剪辑时码、旁白逐字匹配和 QA hard blockers。任何结果未通过就不能提交新账本。
3. **私密上下文只能暂存在私有执行内存**：`prepare_request` 可能包含全文和所有已交付专业方案；公开 GitHub / Actions 日志仅存合成数据，不记录原始上下文、私人素材或供应商密钥。预算收据、`safe_summary` 仅含任务/价格/用量元数据，不含私密 prompt 正文。
4. **不能伪造模型资费或降预算**：`OfflineBudgetBook.reserve` 会使用该岗位锁定的配置重算每次报价，核对模型标识、输出上限、输入代理量和费用；修改报价金额、模型路由、token cap 后都会拒绝。
5. **拒绝自动付款和虚假身份批准**：所有配置标记 `live_calls_authorized=false`、`private_data_transfer_authorized=false`，任何 `True` 配置都拒绝。模拟执行不推断用户真人批准、费用许可或已生成媒体。
6. **没有断电恢复/跨进程账本承诺**：本模块只维护内存模拟账本；不能把它当作未来付费任务所需的 crash-safe 持久化保证。原项目 `llm_budget.py` 已有本地文件锁和预留账本，但**本次没有调用或修改它**，不能将两者混为一谈。

## 自动化测试与当前验证

测试位于 [tests/test_agent_model_gateway.py](tests/test_agent_model_gateway.py)，用纯合成双镜头故事验证：十阶段模型档次切换、全部十阶段交付、源稿私密收据、默认终审暂停、预算及次数硬门禁、缺少模拟回复停机、无效 JSON 留下尝试记录、原稿哈希、不受信的费用/模型标识改写、跨岗位返工等。

以**最终提交代码对应的** GitHub CI 结果为准；测试通过只代表无付费模拟模型路由和预算账本的确定性行为正确，不等于真实模型成本被锁死、更不等于片子已经生成。

## 后续真正启用模型之前还缺什么

至少必须额外完成并获得用户明确许可：真实提供商 SDK/HTTP 的安全隔离、私有文案发送地点和数据保留说明、模型官方名称与实时价格核查、准确用量字段解析、超时及不确定费用处理、跨进程和崩溃安全的持久账本、用户可撤销的付款授权，以及人工审核与小样试制验证。届时可以针对**同一套**任务 DAG 和岗位 JSON 合同增加新的独立适配层；**不能在本离线模拟器中开关一个标志就启动付费 API**。
