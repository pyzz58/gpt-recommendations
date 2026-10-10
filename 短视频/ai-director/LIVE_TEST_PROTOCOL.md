# AI Director v0.3 · 真实 DeepSeek API 测试协议

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
