# v0.3 物理连续性与动作可执行性审查

**修订优先参考成熟 GitHub 项目，而非自造轮子**：先阅读 [GitHub 复用调研与决策清单](GITHUB_REUSE_POLICY.md)，借鉴 CineCrew 的 FilmDSL 资产结构，比较 transitions/jsonschema/Pydantic 等工具的适配成本。仓库调研完成不代表已经安装或集成。

本功能只用本地 Python 标准库；不读取 API Key、不触发 DeepSeek、不生成付费视频，也不修改 Codex 的全局配置。

## 立即检查已有的镜头计划

在 `短视频/ai-director` 目录运行：

```bash
python3 local_director.py audit --plan jobs/live-pilot-001/episodes/ep01/plan.json
```

生成两份仅供审查的文件：

- `episodes/ep01/continuity_audit.generated.json`：机器可读的发现和等级
- `episodes/ep01/continuity_repair.generated.md`：面向人和 Codex 的修改建议

不会覆盖 `plan.json`、`series.json` 或 `direction_v02.json`。

## 阻断与待核查

- **blocker**：有明确位置记录的道具已放下，又在没有拿起/搬运的动作下出现在另一个放置位置；或填写的显式物品状态不自洽。遇到 blocker，`run --resume` 必须停在付费的导演方向阶段之前。
- **review**：基于文字启发式发现的场景道具与手持矛盾、人物跨场景缺失移动、动作过密、重复镜头、授权证据不足。此类发现不应被自动改写，也不强制阻断，以免把正常剪辑认定成错误。

目前仅对“书”和“手机”实现了有限中文自然语言动作追踪。**它不是语义通用 AI 检测器。** 对杯子、钥匙等其他道具，需要在镜头中显式补充 `continuity_state`；没有发现问题不等于已经通过人审。

## 推荐的可机器验证状态规范

镜头可选择包含以下额外字段（不得用它们替代原有的视觉和动作描述）：

```json
{
  "continuity_state": {
    "props_before": {"phone": "sofa_arm", "book": "coffee_table"},
    "prop_moves": [
      {"prop": "phone", "from": "sofa_arm", "to": "hand"},
      {"prop": "book", "from": "coffee_table", "to": "hand"}
    ],
    "props_after": {"phone": "hand", "book": "hand"}
  }
}
```

同一道具在相邻有状态申报的镜头里不得跳过合法的 `prop_moves`。镜头可以主动选择省略人物行走（跳切），但必须写明这属于剪辑选择，不能让关键道具在不同位置凭空出现。

## 修订方法与数据保护

如果发现阻断：

1. 读取 `continuity_repair.generated.md` 和现有 `plan.json`。
2. 让 Codex 先编写一个新的 `plan.proposed.json`，**不得直接覆盖原 plan**；清楚标注动作、道具位置、场景变化和总时长。
3. 离线对候选文件执行同样的 `audit --plan`，然后人工确认效果，只有审过之后才决定是否替换原计划。
4. **不要为修订偷偷调用付费模型或增加 --max-calls**。即便 blocker 清零，也要检查叙事、人物面貌、版权授权、实际可生成性、科研来源与发布审核。

## 本轮真实演练的边界

- 首次真实样本中检测到一次明确的手机位置跳跃，以及书的来源/转移、角色换场、动作超载、重复镜头和没有授权证据的问题。
- 没有上传用户的真实 `plan.json`、原始文案或任何密钥到公共 GitHub。测试使用合成的情境和原本公开的示例。
- 已在本地基线运行离线单元测试；需要用户 Mac 上的 `git pull --ff-only` 和 `python3 -m unittest discover -s tests -q` 再确认最新完整版本。
- 不等于实际视频成功生成、完成导演验收或已经获得素材版权许可。
