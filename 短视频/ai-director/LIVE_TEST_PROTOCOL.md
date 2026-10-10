# AI Director v0.3 · 真实 DeepSeek API 测试协议

## 首次真实 DeepSeek 请求结果 · 2026-10-11

- 用户在本机执行一次 `deepseek-flash` 的 `--max-calls 1 --max-retries 0 --max-cost-cny 5` 测试。
- 程序通过HTTP返回并进入模型文本的 `json.loads`，但返回内容不是合法JSON：`ERROR: 模型返回非法JSON；每次重新尝试均会另计预算`。本次没有 `series.json` 产物，不能算导演创作通过。
- 旧解析器没有保存模型原始响应，因此**无法确认具体JSON错误性质**。费用与令牌消耗应以本地 `cost-status` 和服务商账单核对；不能在没有证据时猜测平台最终扣款。
- 已修复下次调用的诊断缺陷：格式错误时本地保存 `jobs/<项目>/diagnostics/series.invalid-response.txt`（create-only），错误会显示解析行列、字符数；加强了JSON提示语，且不会自动增加重试。新回归测试已加入，仍需独立测试及未来单次真实API试跑。
- **不重复本次试验**，必须先核对已经发生的调用及费用记录。仅修改GitHub源码，不打包、不下载、不进行付费调用。

## 首次授权测试：总预算人民币5元（单请求试验）

该金额对应用户批准的这一轮试验上限，不代表任何长期API费用授权。此协议不会自动执行，**只有Mac本地按下面步骤执行时才发生模型费用**；目前真实请求次数仍为0。

1. 只使用一段不含私人信息、未发表研究数据的简短测试文案：例如《下班后的一个小时》，讲一个上班族下班后不断刷手机，最后决定把手机放下、写下一页日记的经历。要求自动给出恰当集数、人物外貌和跨镜头一致性锚点。
2. 运行前请先确认本机代码有 `--max-cost-cny` / `cost-status` 选项；如果没有说明代码过旧，**不要尝试付费执行**。不要用 `git reset --hard` 覆盖旧工作树。
3. 单次运行命令见下；`--max-calls 1` 只允许 `series.json` 第一阶段，后续请求被硬性次数闸门阻止。返回非零退出码是预期保护行为，不能据此认为第一阶段失败。

```bash
python3 local_director.py run --input pilot_article.md --out jobs/live-pilot-001 \
  --model deepseek-flash --base-url https://api.deepseek.com/v1 \
  --approve-model-cost --max-cost-cny 5 --max-calls 1 --max-retries 0 \
  --input-cny-per-million 3 --output-cny-per-million 10 \
  --max-output-tokens 16384
python3 local_director.py cost-status --job jobs/live-pilot-001
```

4. 只在用户的Mac临时会话中设置 `AI_API_KEY`，不保存在任何GitHub文件、终端命令历史或聊天记录。不采用 Codex 已有设置自动扣费路径，因为该路径不受上述 ledger 管控。
5. 预期产物：`series.json`、`character_bible.json`、`api_usage.generated.json`，`index.html` 尚不存在。必须人工审查首轮输出，包括人物设定、集数、故事母题、章节焦点和目标时长。
6. 如果 `series.json` 没有生成，查看本机错误和用量账本；**不要自行将 `--max-calls` 改大，也不要反复运行以碰运气**。测试结果应先审核，再决定是否用剩余预算继续。

**报价核查**：官方目前美元定价为Flash高峰缓存未命中输入 US$0.30/百万tokens、输出 US$1.20/百万tokens（非高峰可更低）。本试验为额外缓冲，按人民币 ¥3/百万输入、¥10/百万输出预留；汇率、供应商价格及计费规则可能变化，预留并非账单绝对硬限。

**完成判据**：实际API明确返回合规JSON，`series.json` 符合结构、故事有意义；凭 `api_usage.generated.json` 能显示恰好1次尝试和 provider tokens（若有返回）；请求上限拦住第二步，未改变旧项目。

---

**当前状态：只完成离线模拟；真实付费调用尚未执行。** 本文是将来测试的验收合同，不包含任何API Key，也不能当作用户已授权费用。

## 强制先决条件

- 用户明确同意将所选测试文案发给该模型服务商，并明确人民币**单次整个项目**的最高试验预算。
- 在用户Mac本机配置API key，不能把凭据写进 GitHub、README 或测试代码。
- 指定模型 `deepseek-flash`（对应2026-10-11官方文档中的V4.1 Flash）、端点及官方高峰时段价格。2026-10-11官网高峰非缓存输入¥2/百万tokens、输出¥8/百万tokens，仅作当前本地保守预留价；价格可能变动，测试前重新核实。
- 每个测试任务独立本地文件夹且**不可提交私人原文**到公开GitHub。

## 渐进试验顺序（各阶段都需要人工判读结果）

1. **首次单请求**：选择短篇原创文案，以 `--max-calls 1 --max-retries 0` 只让模型输出 `series.json`，观察分集和人物圣经是否合理；程序会在尝试第二请求前止步。正常停止是预算闸门生效，不算模型成功跑完。
2. **单集完整结构**：在相同项目 `--resume`，提高 `--max-calls` 为3（不重复第一阶段），审查生成的 `plan.json` 和 `direction_v02.json`，校验时间线、动作节奏、人物和研究口径。
3. **三个主题的新文章**：使用独立任务分别运行无研究的情绪故事、科技讲解和医学研究文案；禁止捏造研究，严禁真实素材自动生成。
4. **长文三集**：最后才使用约2.7万字级测试文案，最多7次正常模型调用。若任务确实拆三集，完成基础计划和导演稿后人工核对完整性；不把任何结构合格等同导演美感好。
5. **失败注入**：空 JSON、非法 JSON、合法但缺字段以及跨集变脸/颜色漂移；显式开启最多1次修复并预留预算。HTTP 5xx、超时、连接断开禁止无确认的自动重试。

## CLI 执行范式（只有取得明确预算授权后使用）

```bash
python3 local_director.py run --input article.md --out jobs/pilot --model deepseek-flash \
  --approve-model-cost --max-cost-cny YOUR_EXPLICIT_CNY_CAP \
  --max-calls 1 --max-retries 0 --max-output-tokens 16384
python3 local_director.py cost-status --job jobs/pilot
```

`YOUR_EXPLICIT_CNY_CAP` 必须替换为用户明确授权的人民币金额。每次调用先按输入UTF-8字节长度+额外开销及完整的 `max-output-tokens` 预留金额；若超过预算或调用次数，则本地停止。**这不是模型提供方账单硬限，也不覆盖其他进程/其他Key的消费。**

## 预期记录

- `series.json`, `episodes/epXX/plan.json`, `episodes/epXX/direction_v02.json` (仅在验证通过后保存)
- `api_usage.generated.json`：按请求阶段、哈希、预留人民币、响应Token数（若返回）、失败及重试状态记录，不记录原始prompt文本
- `draft_invalid.json` / `direction_invalid.json` / `series_invalid.json`：错误时保存新稿而不是覆盖人工编辑
- `cost-status`：离线显示预算预留，而不是宣称它等于服务商账单
- 审片者评价：分集合理性、旁白节奏、人物外观、镜头可拍摄性、语音与画面匹配、事实/研究准确性

## 暂时禁止

- 未获预算数字授权前对任何收费平台发起 API 测试；不擅自使用用户本地Codex的已有Key。
- 没有真实参考资产不得宣称已经锁脸；没有原始论文核查不得宣称研究验证完成。
- 不运行Seedance/Wan/Kling收费生成、不自动发布、不生成打包下载文件。

## 参考

- 官方价格：https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
- JSON模式：https://api-docs.deepseek.com/zh-cn/guides/json_mode/
- HTTP状态：https://api-docs.deepseek.com/zh-cn/quick_start/error_codes/
