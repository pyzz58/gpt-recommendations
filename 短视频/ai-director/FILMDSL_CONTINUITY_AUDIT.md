# AUD-003 — 用 CineCrew FilmDSL 思路追踪人物、服装、道具、场景连续性

时间：2026-10-11。**本轮全部是公开 GitHub 上的源代码与虚构夹具的离线测试**，没有重复调用 DeepSeek、上传真实用户文案、视频生成或访问用户 Mac。

## 参考成熟开源项目及范围

[Ironieser/CineCrew](https://github.com/Ironieser/CineCrew)，[Apache-2.0 LICENSE](https://github.com/Ironieser/CineCrew/blob/main/LICENSE)。其 README 将 FilmDSL 结构归纳为 `D = {meta, assets, memory, clips[]}`，包括：
- 统一影片资产库：角色 identity/persona/wardrobe、场景、道具的稳定 ID；
- clip 中区分叙事动作、摄影调度、技术渲染指令；
- 镜间 memory/continuity hook 和可定位的 targeted review。

**我们的实际选择：借鉴数据模型与 QA 原理，不导入整个 CineCrew**。该研究框架并不能证明当前项目生成的视频自然保持同一张脸。CineCrew 自身与视频生成器及模型运行绑定，完整集成需要更多供应商接口、算力、媒体资产、兼容性验证，不适宜为了修两个状态字段而改写当前十岗位 DAG。此次没有复制任何上游源文件。

## 确认的工程风险

早期公开虚构《门后的信》的建议镜头使用 `ai_video`，但部分没有 `character_ids`、`prop_ids`、真实参考资产。原有 `creative_production_handoff` 可以提示缺项，`camera_art` 可以约束一间房门/桌的位置，却没有**逐镜记录角色服装、手里拿的道具、物体打开/关闭状态如何从前一镜延续到后一镜**。仅把 `acting.continuity.start_state / end_state` 写成自然语言，不足以进行确定性比较。

## 新增代码

`film_continuity.py`：

- `inventory(base, source_digest=...)` 从**权威分镜计划**读取 `characters[].id`、`props[].id`、`scenes[].id`、`shots[].character_ids/prop_ids/scene_id`。不允许模型创造未在原始计划登记的资产；错误 ID、重复 ID、虚构场景直接拒绝。所有缺少 reference 图的人物、道具和场景只生成 `reference_status="missing"`、`reference_media_verified=false`；不捏造真实照片、已准备服装或镜头效果。
- `inspect_tracks(base, tracks_by_shot, source_digest=...)`：对每一镜头、每一个已登记人物/道具，验证 `start_state` 和 `end_state` 的四个可比字段 `position,appearance,condition,holder`。出现镜内变化需明确 `events` 中的 `field/from/to/time_s/cause`，并与本镜真实 duration 匹配。
- 同一个 `entity_id` 的前镜 `end_state` 与后镜 `start_state` 必须一致；突然从桌上变到右手、封口突然打开、衣服瞬间变色时会返回 `CONTINUITY_TELEPORT_OR_COSTUME_DRIFT` blocker。允许叙事明确的 `time_jump/offscreen_transition/scene_change`，但只能降低为 `CONTINUITY_OFFSCREEN_CHANGE_REVIEW` 人工确认，而**不是自动判定真实连续性正确**。
- 未填 `character_ids` 或 `prop_ids` 的 `ai_video` 镜头标为 `CONTINUITY_CAST_NOT_DECLARED / CONTINUITY_PROPS_NOT_DECLARED`，保持人工查漏，不会凭空识别原稿画面到底有没有人手或道具。

## 真实执行链路如何使用

1. 来源锁定的导演/表演/摄影部门在 `agent_role_contracts.build_role_messages()` 的 user JSON 内看到 source-bound `source_bound_asset_inventory`；数据仍属于素材而不是 system 指令，预算/真人批准旗标不受其影响。
2. 来源锁定的表演岗位 `execution_output_schema()` 增加 `continuity.scene_id`、`continuity.entity_tracks`（受严格 Draft 2020-12 Schema 控制，逐镜固定角色、道具 ID 数量），标准化 event / cut_break，禁止与其部门字段权限无关的伪造内容。
3. `agent_role_contracts.validate_role_output()` 在模型回复后运行 FilmDSL 跨镜检查；出现确证 blocker 会拒绝本次岗位成果、禁止继续当作已验收。真实 DeepSeek 角色 `agent_live_crew.run_one_locked_role()` 在**局部返工合并后的整部表演交付**再次检查，避免单镜修改让旧镜头衔接断裂。
4. `agent_handoff_audit.audit_handoffs(state,base)` 如果已完成轨迹，会作为独立场记检测以 blocker/review 反馈，不信任“自然”“保持一致”等自述。
5. `production_delivery.build_locked_crew_delivery()` 在导出最终逐镜工单前验证完整人物/道具轨迹，并保存 `film_continuity_evidence` 作为审计依据；显式标注 `media_identity_verified=false`、`requires_human_visual_review=true`。

旧版没有提供角色/道具身份的来源计划**不会被自动补写**；这在当前公开虚构样稿中很重要。空表意味着没有可核实的角色资产，**不是证明画面中没有角色**。本次优先以风险提示+流程硬约束替代猜测，避免用户文案受到无法追溯的变更。

## 离线验收与下一阶段

`tests/test_film_continuity.py` 已包含：封好的信在镜头间瞬移、无因换服装、封口打开必须登记镜内动作、时间跳跃只能人审、未经声明的新道具 ID、源图角色 ID 变动、场景 ID 不一致、事件秒数越界、异常输入、未登记视频人物/道具、独立 QA 检查；来源锁定表演岗位已加入 schema 与合法/异常脚本分支的回归测试。

**仍然开放**：AUD-003 主问题（真实视觉身份、persona、服化道参考资产版本、CV/人工成片验收）不能因为字符串状态相等就关闭。

建议下一步按问题闭环开发：
- 建立真人可核查的角色与道具资产卡（图片 / 来源 / 许可 / 批准版本），只能指向私人受控储存，公开仓库只保留合成样例；
- 设计 `reference_asset_id + version` 关联与修改/替换审计，让角色图跨镜复用；
- 获明确用户授权后再实测视频模型同一人物/道具跨镜一致性，不允许仅靠模型 JSON 测试宣称视觉验证完成。

[审计总账](DEEP_AUDIT_MASTER.md) · [机器问题状态](AUDIT_FINDINGS.json) · [AUD-003 Issue #2](https://github.com/pyzz58/gpt-recommendations/issues/2)
