# AI 短视频导演团队 · 离线执行层 v0.1

> 研发状态：**GitHub-only 的模拟输入执行器（Fixture-only execution harness）**，不是已接入 DeepSeek、CrewAI 或其他真正 LLM 的多 Agent 运行时。本版本不操作用户 Mac、不读取私人 `jobs/`、不联网、不付费、不生成图像/视频。
>
> 核心源码：[`agent_executor.py`](agent_executor.py)；基础岗位 DAG：[`agent_team.py`](agent_team.py)；独立交付检查：[`agent_handoff_audit.py`](agent_handoff_audit.py)。

## 这次新增的是哪一层？

之前 `agent_team.py` 能创建十阶段任务、签出工作包和验收手工提交，但**没有一步步调度并驱动岗位交付的执行循环**。

现在的 `agent_executor.py` 有完整可运行的**离线执行调度循环**，但岗位结果必须来自已有的、人工或测试事先编写好的 JSON fixtures。它确实能够把十阶段任务走完、拒绝错误交付并按 DAG 指定的顺序处理返工；**不具备任何自动写出导演创意的模型能力**。

| 执行责任 | 函数 | 保证 |
|---|---|---|
| 构造岗位输入 | `role_context(base,state,task_id,source_text=...)` | 角色、允许字段、完整权威 base、版本化 packet、可选原始文案，仅暂存内存 |
| 只读模拟岗位 | `FixtureOnlyAdapter(fixtures).supply(context)` | 按任务 ID + 递增 revision 提取预设岗位交付，缺少则停止；不用文本生成 |
| 单步执行 | `execute_one(...)` | 仅允许**精确的** `FixtureOnlyAdapter` 类，经过原有 `team.submit` 字段、状态与依赖版本检查 |
| 连续执行到暂停 | `execute_until_pause(...)` | 逐阶段确定性推进，返回新账本与不含原稿的摘要；`max_steps` 1–50，默认 10 |
| QA 源文案门禁 | `_enforce_base_audit` | QA/总导演不能忽略声音部门对原始旁白的改写或其他依赖原稿才能识别的硬冲突 |
| 导演终审门禁 | `allow_fixture_director_final` | 默认停止在导演终审前；仅显式同意**模拟终审**才能执行预写好的导演决定 |
| 执行收据 | `offline_execution_receipt` | 只给 task_id、角色、revision、状态、调用次数；无原始文案、无完整工作包、无私有素材内容 |

### 十阶段串联顺序

`director_brief → script_edit → director_lock → acting → camera_art → sound → editing_animation → ai_technical → quality_review → director_final`

其中动作、摄影、声音**在 `director_lock` 之后逻辑上并列就绪**；本执行器的离线测试按确定性顺序逐一提交，不是实际并发三模型调用。正式实现并发前必须做到依赖快照不可混用和总 Token/费用限制。

### 为什么要做到“一次一个岗位 + 严格交接”？

例如：总导演为 S02 定义“拿起信封意味着开始面对真相”，动作导演写出右手动作时间，摄影导演写清手部特写，声音导演安排信封摩擦声，剪辑导演读取动作与摄影声音的实际交接结果设计 S02→S03，技术导演选择 AI 视频还是后期。

如果动作导演漏掉需要的字段、偷偷改写摄影机设计，`team.submit` 会拒绝；如果声音导演改写原稿，QA 入口上的权威 base 比对会阻止错误地标为通过；如果总导演需要 S02 返工，依赖版本变更后重审相邻剪辑镜头，摄影声音旧成果可保留。

此处**测试能证明调度/权限/阻断实际可工作**；但没有证明故事讲得好、电影导演判断正确或者 AI 视频可生成。

## 具体安全与隐私约束

1. **唯一可执行适配器是 `FixtureOnlyAdapter`**。任何新模型适配器、自定义子类、网络客户端、付费服务都被当前执行器显式拒绝。未来接入真正 DeepSeek/Codex 需要**另写经批准的模型适配器及执行授权路径**，不是把配置中的 `llm_requests_enabled` 改为 `true`。
2. 用户私人原始文案如在未来私有环境提供，`role_context` 才能把它作为**暂时的岗位输入**；必须与 `team.start(base,source_text=...)` 的 SHA-256 匹配。公开 GitHub 只能存在源码、合成数据和不含私人文本的测试收据。
3. **不要将 `role_context`、角色请求、模拟 fixtures、真实执行后的 ledger 上传公开仓库**。交付包有可能包含完整分镜及专业文案；收据特意不包含这些内容。
4. `execute_until_pause` 在缺少下一个 fixture 时暂停并返回已完成部分的**新状态**；传入的 state 不被改动。校验不通过时抛错，不做自动重试、自动修稿、自动返工、自动重新分配费用。
5. `allow_fixture_director_final=True` 只放行**测试数据中的预写总导演决定**，它不构成真人批准或身份认证。账本始终 `human_approved=false`、`paid_api_authorized=false`、`media_generated=false`、`publishing_allowed=false`。
6. 没有添加后台服务或监控进程；未来正式运行必须遵守 [GitHub-only 部署限制](GITHUB_ONLY_DEVELOPMENT.md)，并在用户另行批准本机运行前保持禁止。

## 接口（仅说明，当前不要求在 Mac 上执行）

纯 Python API：

```python
import agent_team
import agent_executor

# base 与 fixtures 在未来获授权的私有运行环境准备。
state = agent_team.start(base)
adapter = agent_executor.FixtureOnlyAdapter(fixtures)
new_state, receipt = agent_executor.execute_until_pause(base, state, adapter)
# 默认在 director_final 停止；回传的是模拟结果，非真人创作。
```

CLI 的静态接口：

```text
python agent_executor.py \
  --base BASE_JSON \
  --state TEAM_LEDGER_JSON \
  --fixtures TEST_FIXTURES_JSON \
  --out-state NEW_LEDGER_JSON \
  --out-receipt RECEIPT_JSON \
  --max-steps 10
```

任何现存输出文件都不得被覆盖；若原稿在未来私有环境绑定则需 `--source SOURCE_TEXT_FILE`，会校验指纹；默认模拟循环不替用户批准总导演终审。

### Tests / CI

- [`tests/test_agent_executor.py`](tests/test_agent_executor.py) 包含 14 个合成离线集成测试：全十阶段、终审暂停、缺包停机、定向返工、越权、私有文本不出收据、源指纹冲突、模型适配器拒绝、原稿级 QA、CLI 无覆盖等。
- 2026-10-11 GitHub Actions 对提交 `79d9c3d7bbae10d0c2a252b085c8a3b1aade22ae` 的 [执行 38106703964](https://github.com/pyzz58/gpt-recommendations/actions/runs/38106703964) 报告 **278 项 Python 测试通过、0 失败、0 错误**；最新工作流已额外将 `agent_executor.py` 纳入 `py_compile`。后续改动仍以最终版本的真实 CI 记录为准。
- 两次测试开发期间的红灯均已定位并修复：首先测试 helper 与 `unittest.TestCase.run` 名称冲突；其次测试预期报错文案与实际 `owned sections` 提示不一致。这不是模型系统或真实用户文案运行失败。

## 接下来真正的模型接入前应完成

- 独立定义各专业 Agent 的**创作提示词、严格 JSON 输出形状、原稿不可改约束、上游共享导演圣经**；必须以专业分工解决“电影作品各岗位如何合作”的实际创作问题，不能把通用 prompt 短句算作岗位完成。
- 实现可替换的**供应商传输接口**、结构化 JSON 解析、超时、错误隔离与可审计的 Token 预算；但**未拿到用户对供应商、模型、单次上限及数据传输的明确批准前，只能进行离线模拟，不能联网。**
- 未来对模拟可拍性、叙事节奏、视觉一致性的验证须使用用户批准的公开视频或合成测试数据；不能从文字合同推断模型生成效果。
