# GitHub 云端一次性 DeepSeek 测试｜操作说明

当前工作流已开发，并且在 2026-10-11 通过 479 项离线测试。**迄今未调用收费 API。**

目标：只通过 GitHub 云端，对完全虚构的《门后的信》进行一次 `deepseek-flash` 总导演 + 剧本编辑测试；最多两次 DeepSeek 文字请求，参考预算人民币 2 元（本地估算，不是供应商侧的费用硬封顶）。不上传任何用户私人原稿、不生成视频、不使用本地 Mac。公开仓库上的测试结果也可能公开，请不要用于敏感稿件。

## 操作 A：把临时密钥添加到 GitHub 加密 Secret

打开 <https://github.com/pyzz58/gpt-recommendations/settings/secrets/actions>。

1. 点击 **New repository secret**。
2. Name 精确填写 `DEEPSEEK_ONE_TIME_API_KEY`。
3. Secret 填你自己准备的**临时** DeepSeek API Key，点击 **Add secret**。

**绝对不要**把 Key 放进聊天窗口、GitHub Issue、源代码、Actions 普通变量、工作流输入框、PR 或日志。GitHub 的 Secret 是加密存储，但仍不能当作供应商扣费的硬限额。最好在 DeepSeek 后台对这把临时 Key 或账户设低额度，确认可以承受最多约 2 元之外的估算误差风险。

## 操作 B：仅手动执行一次

打开 <https://github.com/pyzz58/gpt-recommendations/actions/workflows/deepseek-one-time-fiction-trial.yml>。

1. 点击 **Run workflow**。
2. Branch 选 **main**。
3. 把 **authorize_two_calls** 勾选为 true。
4. 点击绿色 **Run workflow**，只运行一次，不要再次运行或点 Re-run jobs。

工作流仅允许仓库所有者 `pyzz58` 手动触发，在主分支运行；代码额外阻止 GitHub 同一 run 的第二次尝试；一次工作流内最多调用总导演与剧本编辑各一次。失败停止、不自动重试。**再次发起全新 Run workflow 并不是被代码绝对禁止的**，所以真正的一次性控制仍依赖你立即撤销 Key。

## 操作 C：及时删除和撤销

运行结束（无论成功失败），先到 <https://github.com/pyzz58/gpt-recommendations/settings/secrets/actions> 删除 `DEEPSEEK_ONE_TIME_API_KEY`；再到 [DeepSeek API Keys 后台](https://platform.deepseek.com/api_keys) 撤销/删除这把临时密钥。删除 GitHub Secret 不能代替在 DeepSeek 服务商撤销密钥。

可在同一个 Actions 运行页面查看日志；下方 Artifacts 下载 `DeepSeek-ONE-TIME-PUBLIC-FICTION-REVIEW-NO-KEY`，里面包含虚构故事的模型结果及检查/费用估算报告。若格式失败，仍会留下安全的状态摘要（可能只有一个岗位的输出），需要在 DeepSeek 后台人工检查实际账单。Artifact 保留 3 天，不会保留 API Key。

**如果你想让我评审结果，只需要把这次 GitHub Actions 的运行页面链接发回聊天**。我可以通过已连接的 GitHub 查看执行状态及公开虚构故事的输出。

## 安全边界

- 此次用户允许“云端测试”不等于允许把真实《上学以后的孩子》发送给 DeepSeek；工作流输入只引用公开虚构文案。
- GitHub Secrets 由你自己管理；当前 GitHub 连接没有提供安全的 Secret 创建/删除或手动 dispatch 功能。
- 不能把 JSON 结构和制品成功误当成导演艺术质量已经验证。模型返回需要人逐镜阅读，才能评价剧本专业性。
- 本地成本估算 `¥2` **不保证供应商账单绝对不超过该数值**。如 DeepSeek API 返回超时/异常也可能收费，按供应商实际账单为准。
