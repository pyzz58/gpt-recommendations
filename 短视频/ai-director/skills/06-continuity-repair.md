# 06 · 无额外 API 费用的镜头连续性修订工作流

> 启动条件：用户已同意修订某个本地 `jobs/<job>/episodes/<ep>/plan.json`；所有修改都在其本机。禁止改全局 Codex/DeepSeek 设置、提高 `--max-calls`、调用收费视频服务或自动发布。

## 先做：GitHub 复用方案核查

阅读 `GITHUB_REUSE_POLICY.md`、`CONTINUITY_QA.md`。优先沿用现成 Python JSON Schema 契约规范，借鉴 CineCrew 的稳定资产 ID 和 transitions 的有限状态机思路，而非临时用更多中文关键词硬匹配。当前项目保持运行时零第三方依赖；若需新增库，先报告仓库、许可、版本、Mac/离线兼容性和替换成本，用户同意后再最小范围测试。

## 输入

- 只读正式计划 `plan.json`、同集 `continuity_repair.generated.md` 和 `continuity_audit.generated.json`。
- 同时读取上层 `series.json`、`character_bible.json`、`source.md` 和导演风格规则；不得修改这些已经存在的文件。
- 不上传原文或完整私人任务到公共 GitHub；GitHub 只保留通用修订器、合成测试和方法说明。

## 必须产生的候选文件

1. `plan.proposed.json`（新文件，不覆盖 `plan.json`）。
2. `repair_review.generated.md`（变更摘要、每个发现的解决办法、剩余人工核查事项）。
3. 不得把 `production.music_license_check`、`production.asset_license_check` 置 true，除非对应实际素材的证据已经核对。科研出处也不能虚构。

## 核心修订规则

- **物品全局唯一 ID**：同一本书 `PROP_BOOK`、同一手机 `PROP_PHONE` 必须指向唯一实物；人物采用现有 `CH_MAIN` 等角色 ID。补全首次位置。
- **全镜头状态表**：若声明 `continuity_contract = {version: 1, coverage: "complete", props, actors}`，每一镜都必须包含 `continuity_state`：`props_before`、`props_after`、`actors_before`、`actors_after`、`prop_moves`、`actor_moves`。未出镜物品也继续保持上镜头位置。
- **物品合法转移**：桌面 → 人物手中（pickup）→ 同一/另一场景的物品位置（place）；演员带着物品走动时道具仍是手持，不能把“下一镜出现在书桌”写成无动作转移。
- **动作事件排序**：每镜头所有 actor_moves / prop_moves 共用唯一 `order`（整数）；每个事件 `visible` 是布尔值。场外转场可以用 `visible=false`，但必须写 `note` 解释剪辑省略，并留人工 review。
- **图文同步**：修好结构化状态后，同步改 `visual`、`action.start`、`action.action`、`action.end`、`continuity`、`art.set_props`、镜头时长及旁白，不能只伪造一份看似合规的元数据。
- **镜头节奏**：复杂连续动作必须分镜或调整时长；减少三个近景重复刷手机镜头，将部分重复镜头改为环境、物件或时间切换画面。
- **不改变人设**：人物身份、外形、服装、场景风格和原故事主旨与系列设定一致。不得因为加修订而加入没有来源的新研究结论。

## 离线验证（不得联网调用付费模型）

```bash
python3 director.py validate --plan jobs/<job>/episodes/<ep>/plan.proposed.json
python3 local_director.py audit --plan jobs/<job>/episodes/<ep>/plan.proposed.json
```

当候选计划声明完整结构化追踪时，审查器会自动回放每个道具和演员的有序事件。通用 JSON Schema 定义在 `schemas/continuity_contract.schema.json`。若本地恰好已安装 `jsonschema`，可用其额外检验；**不要为了本步骤改动全局 Python 环境**。

验收条件：两个结构测试都通过；阻断问题归零；人工逐项核实原有 review 问题；总时长仍符合目标、旁白/字幕和画面匹配；不得把授权风险标为已通过。**0 个自动检查错误不等于人审通过，也不等于已经生成视频。**

## 回滚、安全

如果修订无法自洽，保留 `plan.proposed.json` 作为未完成草稿，并在 `repair_review.generated.md` 说明仍需决定的冲突；不要覆写原稿，也不要要求额外模型调用。

**审查记录保护**：执行针对 `plan.proposed.json` 的 audit 时，输出 `plan.proposed.continuity_audit.generated.json` 和 `plan.proposed.continuity_repair.generated.md`，不得覆盖正式原稿已有的审查报告。
