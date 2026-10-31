# F02-00｜摄影、灯光、美术基线与严格合同

日期：2026-10-31  
范围：现有 `camera_art` 岗位、`creative_production_handoff.camera_requirements_for_role`、F01 表演/实体约束。  
性质：**离线结构审查与多镜统一测试计划，不是独立摄影审片或真实媒体验收。**

## 1. 现有能力基线

| 领域 | 现有字段/检查 | 已有覆盖 | 真实缺口 |
|---|---|---|---|
| 镜头语言 | start_frame、movement、move_trigger_s、end_frame、lens_feel、reason | 有基本镜头起止和运动原因 | 缺镜头左右侧、eyeline、运动触发事件的结构化绑定 |
| 光学 | creative bridge 的 shot_size、focal_length_mm | 有景别与 14–135mm 焦段 | 未在普通 camera_art schema 中强制；无真实镜头测试 |
| 轴线 | screen_axis | 有物理轴线文字 | 未检查 180 度越轴；无 axis break 说明 |
| 灯光 | light_source、lighting_state、practical_sources、lighting_change_reason | 有灯态、实用光源与变化原因 | 未强制主光位置/方向；跨镜主光跳变没有独立门禁 |
| 美术 | environment、color_path、texture、scene_geometry | 有环境、色彩、材质、场景几何 | 未强制 safe area；几何只在部分 creative bridge 路径检查 |
| 多镜统一 | scene_geometry 按场景一致 | 同场景锚点/主光/轴线一致 | 缺跨镜主光方向、越轴与摄影泛词复核 |

结论：现有结构已经能表达“可拍摄的摄影方案”，但还不能系统地区分有因果的视觉选择与模板字段。F02 在其上增加**轴线、主光、几何、镜头触发和 safe area**的严格合同，不另建摄影 Agent。

## 2. F02 严格合同

启用 `photography_contract_mode` 时，`camera_art` 每镜新增/强制：

- `camera.shot_size`、`focal_length_mm`、`screen_axis`、`camera_side`、`eyeline`、`movement_trigger_event`；
- `camera.axis_break_reason`：只有确实需要越轴时填写，进入人工 review；
- `art.lighting_state`、`practical_sources`、`lighting_change_reason`、`key_light_position`、`key_light_direction`、`safe_area`、`scene_geometry`；
- `scene_geometry` 必须含至少两个锚点、主光位置和 camera axis；
- `art.key_light_position` 必须与 `scene_geometry.key_light_position` 一致。

跨镜门禁：

- 同一声明场景的 `scene_geometry` 不一致 → `PHOTOGRAPHY_GEOMETRY_DRIFT`；
- 左右 camera_side 直接翻转且无 `axis_break_reason` → `PHOTOGRAPHY_AXIS_JUMP`；
- 有明确越轴理由 → review，而不是自动判错；
- 主光位置/方向变化但原因是空或“无变化/unchanged”等 → `PHOTOGRAPHY_LIGHT_SOURCE_JUMP`；
- 有具体物理变化原因 → review，等待人工检查；
- “电影感/高级感/视觉冲击”等泛词 → review，不自动当成专业选择。

现有 `director_shootability` 仍负责动作时间/手/道具；F01 合同负责 body/hand/prop；F02 只负责 camera/art 一侧，不重复这些逻辑。

## 3. 多镜视觉统一测试计划

公开合成样例：[examples/photography-f02/public_dialogue_scene.json](../examples/photography-f02/public_dialogue_scene.json)

| 测试 | 目的 | 预期 |
|---|---|---|
| 正常双镜对话 | 同一场景、同一轴线、同一主光、同一几何 | 通过 |
| 无意越轴 | S02 的 camera_side 从 left 翻到 right，无理由 | 阻断 `PHOTOGRAPHY_AXIS_JUMP` |
| 有意越轴 | 同上，填写具体 axis_break_reason | review，不阻断；由人审 |
| 主光方向跳变 | S02 主光方向改变，原因为“无变化” | 阻断 `PHOTOGRAPHY_LIGHT_SOURCE_JUMP` |
| 有动机主光变化 | 同上，说明实际开灯/换光源 | review，不阻断 |
| 场景几何漂移 | S02 锚点位置改变 | 阻断 `PHOTOGRAPHY_GEOMETRY_DRIFT` |
| 缺少焦段/字段 | 删除 focal_length_mm | 阻断 |
| 摄影泛词 | lens_feel 写“电影感/高级感” | review |

该计划覆盖“多镜视觉统一”的关键阻断点，但**不是**摄影艺术审片，也不证明真实灯光/镜头/场景一致。

## 4. 验收边界

- 本轮达到 **G1/L1 软件层**：相机/灯光/美术字段、同场景几何与轴线主光连续性有正反回归。
- 未达到 **G2/L2**：没有独立摄影指导/DOP 对方案做专业盲评。
- 未达到 **G3/L3**：没有真实摄影机、镜头、灯具、场景或 AI 视频实测。
- 未达到 **G4/L4**：没有真实成片、色彩/光照/构图审片。
- **QO-F02 仍为 `audit_pending`**；不能因为 9 项结构测试通过就关闭摄影专业审计。

## 5. 下一步

1. 独立摄影/灯光/美术审阅公开样例与测试计划。
2. 补充专业摄影指导一手资料与真实场景勘查。
3. 在授权范围内做多镜真实媒体或合成光学测试。
4. 通过后再评估 F02 状态；真实媒体和艺术审片仍单独记录。
