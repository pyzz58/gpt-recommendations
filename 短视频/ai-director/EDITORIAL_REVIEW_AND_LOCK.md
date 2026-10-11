# 专业导演系统：逐镜作者审阅、返工单与版本锁定

> 2026-10-11：仅 GitHub 上的离线开发与测试。这一层**没有调用 DeepSeek，也没有真人审核或认证身份**。所有测试素材是虚构信封故事，不是用户《上学以后的孩子》原稿。原稿、私人创意方案、审核文本不得提交公开仓库、GitHub Actions 日志或发送未经授权的模型服务。

## 为什么要有这一步？

上一阶段已建立“文章入库→分集→原始旁白→总导演与剧本编辑创意分镜提案”。但**文案出品人需要对每个镜头做决定**：是否按这个形式拍？旁白和事实是否仍忠于原稿？一个 60 秒片段有没有重要信息被省略？未验证研究数字能否直接公布？如果艺术方案没获审阅，不能直接把它发给下一组 Agent。

新模块：[editorial_review_lock.py](editorial_review_lock.py)；专项测试：[tests/test_editorial_review_lock.py](tests/test_editorial_review_lock.py)。

## 工作流程（所有函数仅处理调用方内存数据）

`build_review_sheet(candidate, episode_source)`
- 输入上一版 `editorial_storyboard.propose_directed_storyboard` 返回的候选分镜和该集准确原文。
- 输出私有审阅单：每镜 ID、时长、逐字旁白、拟采用的视频生产类型、导演动作、摄影思路、所涉 claim ID、该镜头内容摘要哈希。还有全片 hook 与风格、原稿被省略的内容、全部未核验 claims、每条改稿提议。
- **所有选择都默认 `None`，不存在预勾选同意**。

`decision_template(sheet)`
- 只生成不含已批准选择的输入模板，供日后经过身份验证的私有审核界面填入；不能被系统视为已收到作者同意。

`evaluate_review(candidate, episode_source, decision)`
- 要求某次决策**覆盖全部镜头且顺序和每镜哈希一致**；禁止把旧审核结果套到新分镜、另一期节目上。
- 镜头三种动作：`keep`、`revise`、`reject`；后两者必须写返工意见。
- 对“全片风格和开场 hook”、旁白删减清单、未核验事实、待改写原稿提案要求单独作出明确决定。用户可选择“不同意这次改写”，**不能借这个操作让 AI 悄悄修改原文**。
- 出现未解决事项则结果为 `revision_required`，提供责任明确的 `shot_rework`，无法进入规划锁定。
- `acknowledge_unverified_for_planning` 仅表示**允许在不声称核验完毕的情况下继续设计**，绝不表示研究结果、医学数据或法规已经核查，更不代表允许发布。

`lock_planning_snapshot(candidate, episode_source, decision)`
- 只有结构完整且无返工事项的审核选择才生成带原文 SHA-256、完整候选计划 SHA-256、完整决策 SHA-256 的规划快照。
- 状态特意命名为 **`planning_locked_identity_unverified`**；这是一次*离线结构校验*，不是电子签名、身份认证、作者同意、模型供应商授权或者媒体发布许可。
- 在代码层只保证传入的候选计划与已有 hash 一致；**不具备防止有权限访问者同时篡改 JSON 和 hash 的可信签名保证**。正式审阅系统上线前必须在安全私有服务层进行账号身份认证、权限校验、审计追加日志、签名/不可篡改历史。

`stage_locked_team(snapshot, episode_source)`
- 再次检查源文章切出的**单集 SHA-256**、计划 SHA-256、合法时间轴和业务 schema；重新启动一份正确绑定新计划的十阶段导演团队账本。
- `status=offline_planning_only_not_authorized_to_dispatch`，只能备好岗位任务，禁止解释为已授权 DeepSeek 网络调用。未来要运行实际付费模型，必须在独立的可信系统中核验作者身份、素材传输同意、供应商、账户预算和安全措施；本模块没有这条能力。

`render_private_review_html(sheet)`
- 输出只在内存中的静态文字分镜审阅网页 HTML，转义所有可能的用户字符串，无联网 JS、无跟踪请求、无“点击即认证”假按钮。它是便于观看的**预览**，不是已经接入真实审稿后台的可操作界面。
- 不要把传入该函数的真实私有草案输出存放公开仓库。

## 一次审阅的示例（不运行模型）

```python
import editorial_review_lock as review

# candidate 来自上一步严格验收的专业创意分镜候选；
# episode_source 为同一期的原文，只在私有运行环境保留。
sheet = review.build_review_sheet(candidate, episode_source)
blank_decision = review.decision_template(sheet)
# 此时所有 choice 均为 None —— 必须由可信审阅入口收集明确的实际决定。
# 没有真人决定前，不要调用 lock_planning_snapshot。
```

## 分工与终局

- 本轮完成的是 **逐镜审阅合约、定向返工建议与离线规划版本锁定**，而不是 AI 自动创作。
- 十阶段团队在锁定版本后仍处于待执行状态；摄影、动作、声音、剪辑和 AI 技术导演须真正工作、各自通过专业 QA。
- 完整 MVP 还需真实模型调用的单独预算/隐私许可和经核实的运行环境；最后要用指定视频模型试制最少一集，观察画面连贯性、人物连续性、数据后期、剪辑结构。**绝不能因本轮测试全部通过就称视频已经可直接生成**。
