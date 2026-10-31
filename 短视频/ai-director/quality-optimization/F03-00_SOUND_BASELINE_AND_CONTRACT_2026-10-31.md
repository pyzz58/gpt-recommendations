# F03-00｜对白、配音、拟音、音乐基线与严格合同

日期：2026-10-31  
范围：`agent_role_contracts` sound、`director_speech_cues.py`、`director_av_sync_smoke.py`、F01/F02 的音画与空间约束。  
性质：**离线结构/时码审查与公开合成设计，不是真实混音、真人声、音乐授权或成片验收。**

## 1. 现有能力基线

| 领域 | 现有实现 | 已有覆盖 | 真实缺口 |
|---|---|---|---|
| VO/旁白 | `speech.voiceover` 文本、delivery、timing、cues | 旁白必须等于 base narration；cue 有区间 | 缺混音优先级和留白意图 |
| 对白 | dialogue speaker/text/delivery/from/to/kind | 出镜/画外类型、时间窗 | 缺逐句口型策略、清晰度和源对白账本绑定 |
| 字幕 | subtitle_cues | 时间窗 | 文本未强制匹配已说文本 |
| 音乐 | ambient/music/effects | 有文本描述 | 缺音乐 cue、目的、配器、混音等级与授权状态 |
| 拟音/音效 | effects time_s/cue | 时间点 | 缺物理来源、层类型与混音说明 |
| 声桥 | editing.audio_bridge | 剪辑侧有桥接字段 | sound 岗位没有独立声桥决定 |
| 真实媒体验证 | `director_av_sync_smoke.py` | 公开合成音轨/字幕实际解码 | 缺真人声、ASR、真实口型和独立混音审片 |

结论：现有系统能规划基本声画时码，但不能系统区分“有来源的拟音/对白”“只是氛围词”“未授权音乐”。F03 增加严格声音合同，不新增声音 Agent。

## 2. F03 严格合同

启用 `sound_contract_mode` 时：

- `sound.mix`：dialogue_priority、music_level、ambience_level、dynamic_range_note、silence_intent。
- `sound.music_plan`：
  - mode none/cue；
  - cue_id、start_s/end_s、purpose、instrumentation、mix_level；
  - rights_status 只能 unknown/not_selected/unlicensed/cleared；
  - cleared 必须有 license_ref。
- `sound.effects` 每项：time_s、cue、source、layer(foley/ambience/sfx/silence)、mix_note。
- `sound.sound_bridge`：none/j_cut/l_cut/match_cut/room_tone_bridge、duration_s、track、reason。
- `speech.dialogue` 每句：
  - speaker_id、text、delivery、from_s/to_s；
  - kind onscreen_dialogue/offscreen_dialogue；
  - lip_sync：出镜 required/native，画外 none/not_applicable；
  - clarity_note。
- 字幕文本必须匹配已说文本（旁白或对白）并在 shot 内。
- 若 base 有 `dialogue` 源账本，逐句 speaker/text 必须精确匹配；否则进入 review，不伪造来源。
- 泛泛“电影感/氛围感”进入 review，不自动判错。

## 3. 公开测试样例

[examples/sound-f03/public_dialogue_sound.json](../examples/sound-f03/public_dialogue_sound.json)

- S01：旁白 + 出镜对白 + 纸张拟音 + 未知授权钢琴 + J-cut 声桥。
- S02：旁白 + 画外对白 + 椅子拟音 + 无音乐 + 无声桥。

正反测试覆盖：

- 正常两镜通过；
- 缺混音计划；
- 音乐声称 cleared 但无 license_ref；
- 出镜对白未要求口型；
- 画外对白错误驱动口型；
- 字幕与已说文本不一致；
- 缺声桥；
- 泛词 review；
- strict schema/validator 接线；
- 旧 fixture 不强制。

## 4. 验收边界

- 本轮达到 **G1/L1 软件层**：声音结构、时码、对白类型、字幕文本、音乐 rights 状态和声桥有正反回归。
- 未达到 **G2/L2**：没有独立声音设计/混音/对白指导盲评。
- 未达到 **G3/L3**：没有真人声、TTS、真实拟音、实际音乐或模型音频测试。
- 未达到 **G4/L4**：没有真实音轨解码、ASR、口型、动态范围与成片审片。
- **QO-F03 仍为 `audit_pending`**；不能因结构测试通过就关闭声音专业审计。

## 5. 下一步

1. 独立声音设计/混音/对白指导审阅公开样例与测试计划。
2. 选择合法音乐/音效，保留授权证据；没有证据不得写 cleared。
3. 在授权范围内录制/合成真实对白、拟音和环境声，做实际解码与口型/字幕审片。
4. F04 剪辑/动效/信息图可在 F03 软件层之后启动，但必须继承声桥、cue 和字幕约束。
