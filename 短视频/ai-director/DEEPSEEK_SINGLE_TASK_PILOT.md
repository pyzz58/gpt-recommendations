# DeepSeek 真正运行准备：单岗位试验通道（默认禁用）

**开发状态：2026-10-11，代码已能够建立真实 HTTPS 请求，但尚未取得真实私有用户调用许可，因此未执行任何收费 DeepSeek API 调用。GitHub CI 只使用固定合成响应，绝不发送用户文案。**

代码：[agent_live_pilot.py](agent_live_pilot.py)｜专项测试：[tests/test_agent_live_pilot.py](tests/test_agent_live_pilot.py)

## 本阶段是实质性进展，不是另一套 Agent 架构

- 直接复用已有 `article_intake`、`editorial_storyboard`、`agent_team` 的真实十岗位 DAG 及正式前两个专业创作岗位合同；
- 使用 `agent_provider_wire` 的 DeepSeek Chat Completions 报文编码与 strict JSON 校验；**没有添加第二套响应 Schema 或自动“修复”模型错误**；
- 新增 `DeepSeekHTTPSClient`：只允许 TLS 连接 `api.deepseek.com:443` 的 `POST /chat/completions`，固定供应商、不重定向、不自动重试、不打开第三方网址；私钥只由未来的可信私有调用方传入内存，不读取系统环境、公开仓库或日志；
- 新增 `PilotJournal`：在实际发请求前写入独立的持久预算预留记录，POSIX 排他锁，原子落盘、文件和锁 0600。只保存哈希、任务修订号、费用预留、返回的 token 数量和终态；**不会保存文案、提示词、任何完整模型回复、私钥、用户实名或资产**。
- 增强的 `director_brief` Prompt 和 `script_edit.storyboard_pitch` Prompt 也已连到单次试运行中。收到 JSON 后先经原有专业字段校验、剧本来源一致性与每镜创意验证，通过才生成新团队状态；
- 网络/返回中断时收费是否发生可能未知，因此标记 `timeout_unknown`、`transport_unknown`，强制停止后续任务。完成但回复出错也保留费用预留，不自动重试。同岗位同修订版不重复发，防止重复扣款。**用户应向供应商账单人工核对不确定交易**。
- 一次最多发送**一个**岗位请求；本轮只开放前两个试验角色（总导演 `director_brief` 和剧本编辑 `script_edit`）。其他 8 岗位及真人终审仍不能借此入口直接自动调用。

## 使用时的隐私与费用闸门

当前代码**无自动调用入口**，不会因为有人输入“继续”、“开始”、CI 执行、git push 或自动化定时任务而调用任何收费服务。

未来实际小样运行必须先另行取得具体明确的用户授权（不要把一般继续开发视为授权）：
1. 确定私人执行环境、是否允许将该集的原文与完整角色上下文传给 DeepSeek（跨境第三方处理风险自行知悉；绝不能用公开 GitHub Actions 执行用户私稿）；
2. 确定模型 `deepseek-flash` 或 `deepseek-v4-pro`、具体一次试验的目标岗位、最大输出 token、用户认可的人民币费用上限、官方实时核验的费率；
3. 在身份已验证、权限受控的私有界面取得该次独立 consent，再由系统明确创建内存的 `explicit_pilot_permit`。**这个数据结构只记录操作意向，并不提供用户身份认证、合法签名或无法伪造的同意证明**，可信认证必须由外部私有界面完成；
4. 提供独立保密的 API key；调用前必须确保 `PilotJournal` 已在私人安全目录建立并完成持久预留。不能将 key 加进 Python 示例、git repo、测试、Actions Secret 随意运行或任何日志；
5. 响应经严格金额和岗位校验后仍只是**AI 创意草稿**，不是已经批准的旁白变更、导演正式成果、生成的 MP4 或可以直接发布的医学科普。

`create_pilot_config` 仅提供额度，不等于调用权限；`explicit_pilot_permit` 要求明确完成单次文案隐私与付费同意。调用者必须已经获得上述真实用户授权。技术测试可通过 `StaticHTTPSFrame` 提供假 HTTP 返回；正式客户端 `DeepSeekHTTPSClient` 仍要独立明确传入 key，且**只有被主动调用时才会发送网络数据**。

### 费用的重要局限

输出 token 上限是实际请求限制，输入 token 预留仅用 UTF-8 字节 + 固定开销估算，无法完全代替 DeepSeek 的真实 tokenizer、套餐价格、汇率、供应商额外项目或月末账单。因此“预算预留”**并不是供应商层面的绝对硬封顶**。一旦报告估计成本超过预留，账本会标 `usage_overrun_requires_review` 并停止下游；已经发生的那次请求仍可能产生费用。为达到强收费限额，还必须在供应商账户启用额度或预付限制与私有端监控，不能只信任本模块。

### 真实调用后仍需补的两个工程环节

- 当前函数 `run_one_creative_task` 在一条成功的回复后返回新团队 state；持久预算记录已经独立保存，但**尚未实现可信的私有原子状态存储**。若进程在记录结果后、保存 state 前崩溃，账本会阻止相同任务重发；需手工对账与恢复状态，不能假装成功或自动退款。
- 没有视频模型实机试制、参考资产/演员一致性验证、可信真人身份审批、发布许可。不能把静态 10 阶段模拟测试当作真实 10 个 Agent 已工作；也不能声称真人导演品质已经得到验证。

## 此轮可核验的离线测试

仅合成“信封故事”，测试两个专业岗位与现有原始 DAG 一致、角色 JSON 与创意分镜质量校验、没许可立即拒绝、文案换版本拒绝、模型不符拒绝、模拟网络超时/断线记录为 uncertain、不自动重试、超费用预留拒绝、假身份/接口客户端不能绕过、ledger 不泄露密钥、SDK 不依赖外部安装、固定主机/HTTPS/no redirect 等。

DeepSeek 官方协议接口参考：
- [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)
- [Quick Start](https://api-docs.deepseek.com/)

仓库里既有离线执行器、`agent_durable_preflight` 均保持**严格离线**；此文件只负责独立可控的未来调用实验。所有真实测试须未来明确批准后才能启动。
