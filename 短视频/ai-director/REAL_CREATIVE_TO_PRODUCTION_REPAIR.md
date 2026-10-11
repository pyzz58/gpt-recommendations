# 从真实 DeepSeek 创意到可执行分镜：首轮缺陷修复（2026-10-11）

## 证据

来源：一次性 GitHub Cloud 公共虚构文案 `《门后的信》`，工作流 run [38115310358](https://github.com/pyzz58/gpt-recommendations/actions/runs/38115310358)，两次真正的 DeepSeek Flash 请求获得接受。**本仓库不保存那次原始模型回复**；请在原运行制品中查阅。此处只记录已核实的工程问题。

- 真实模型建议 8 个镜头，其中 6 个 ai_video、1 个 ai_image、1 个 motion_graphic；然而许多 `candidate_plan.shots[].camera.shot_size` 仍保留 `postproduction`，`angle/lens=n/a`。
- 原始候选 `characters=[]`，AI 视频镜头 `character_ids=[]`，同一场景 `LOC01` 的说明仍是纯后期图卡占位，`art.set_props` 也未更新为实际公寓布局。
- S06 灯从亮切黑、S07 近全黑、S08 门缝/门厅微光：**需要摄影美术提供光源物理解释和统一布光状态**。文本相邻有变化本身不等于逻辑矛盾，程序不能擅自判定真实布光。
- 原先 `editorial_review_lock.lock_planning_snapshot` 只保留 `candidate_plan`，随后十岗位重启时丢掉 `editorial_concept.shot_designs`，新专业岗位可能脱离第一轮真实导演构想各写一套，浪费实际模型推理费用。

## 这轮修复

### 1. 延续第一轮导演的原始设计，不静默重写

`creative_production_handoff.py` 将来源绑定的 `editorial_concept` 与 `candidate_plan_digest`、`episode_source_digest` 装订成 `creative_handoff`；在 `lock_planning_snapshot` 中保存并计算新的 digest。`stage_locked_team` 验证该创意没有丢失、换源、篡改、换镜或被虚假标记人工批准。十岗位 `agent_role_contracts.build_role_messages` 的 `first_director_editor_vision` 将其作为**先前提案**传递给后续角色，并把各岗位待解决的生产缺口传递给总导演、表演、摄影、AI 技术、独立 QA。所有原始文案/模型输出仅保存在**私人状态**，不得提交公开仓库。

### 2. 把缺项明确分给具体专业角色

`inspect_preproduction` 读取候选 plan / pitch，提出有责任归属的镜头级待办：

| 缺项 | 负责人 | 需要真正给出的东西 |
| --- | --- | --- |
| 景别 `postproduction`、角度/镜头 `n/a` | 摄影 | 确定景别、焦段、相机轴线；拒绝使用原图卡模板 |
| 空场景 `LOC01`、摆设 `文字或数据图形` | 摄影美术 | 门、桌、灯、人物路径、机位与墙面相对位置 |
| 有人物表演但 `character_ids=[]` | 表演/连续性 | 提交角色登记与服化参考计划，必要时明确无演员的物镜 |
| 相邻镜头亮度和光源描述变化 | 摄影美术 | 每镜灯光状态、来源和变化事件；必须说明由什么光照亮 |
| `ai_image` / `motion_graphic` 镜头 | AI 技术、后期 | 避免误分配真人运动视频生成任务 |

缺项检查属于结构性预检和待人确认的风险提示，不自行发明新人物长相、真实场地地形或已验收的镜头照片，也不自动拒绝合法的分镜规划锁定——它仍需用于后续岗位完善。

### 3. 摄影部门从“口头说明”升级为可验收的结构化字段

只有来源绑定的专业岗位通道采用**加强的实际输出合同**，避免破坏以前没有原始创意快照的离线/参考样例：

**所有镜头**的 `art` 必须包括：
- `lighting_state`：lit、dim、near_dark、blackout、backlit、transition 之一；
- `practical_sources`：明确光从哪里来（全黑可明确声明无可见实际光源）；
- `lighting_change_reason`：解释光线维持/变化的物理叙事依据，不能把相邻不同灯态说成“灯光不变”。

**每个 `ai_video` 镜头**的 `camera` 额外包括：
- `shot_size`：规范景别名，不允许 `postproduction`；
- `focal_length_mm`：14–135 mm 之间的数字化设计意图；
- `screen_axis`：相对人物/桌子/门的摄影轴线文字说明。

同一镜头 `art.scene_geometry` 额外定义：`anchor_positions`（至少两项可检查的物理锚点，如门与桌）、`key_light_position`、`camera_axis`。同一个 `scene_id` 中的所有 ai_video 镜头必须复用**完全一致**的基准房间布局。程序会拒绝同一房间门从东墙瞬移到北墙。

这些是**专业设计规格的结构/跨镜一致性验证**，不代表焦段已被 Wan/Seedance 实测支持，也不代表灯光真实可布、场地已租赁、参考演员照片已存在。

### 4. 最终工作包保留早期设计的审计线索

`production_delivery.build_locked_crew_delivery` 现在会把初始导演的每镜摄影/灯光/动作/画面目的复制到对应制作镜头，并保留来源 digest 与初期未解决问题。这样导演审片时可对照：

**原始意图 → 专业岗位实际规格 → 最终 AI 视频候选提示词**。

如果原稿、原始创意或锁定方案被修改，系统拒绝继续复用旧的 hash；如没有实际参考图、人物 ID、真人验收和视频试拍，成品仍然 `ready_to_call_video_model=false`、`human_approved=false`、`publishing_allowed=false`。

## 测试

`tests/test_creative_production_handoff.py` 模拟首轮真实报告中发现的结构性错误：图卡景别、无演员登记、空房间、道具占位、S07/S08 灯光变化和篡改先前创意 digest；逐一验证提示和 source lock。更新的 `tests/test_agent_live_crew.py` 确认真实 DeepSeek-compatible 单岗位路径在模型返回错误景别、门墙瞬移、灯态逻辑矛盾时**不写入成功岗位状态、禁止自动重发、保留费用预留与错误状态**。合成全链路仍能输出 Wan/Seedance 候选工作单并保留原始创意。

## 后续真实质量检验

这轮**没有再次调用 DeepSeek，也没有再次扣费**。真实演员 reference、真实镜头和模型出片仍不存在。下一轮若要试验表演、摄影、声音三个模型角色，必须有新的、明确的单次费用和虚构文本授权；不要复用之前的一次性密钥。优先通过现有本地/云端离线合成测试检验角色合同，再由用户决定是否进行新的真实付费试验。

