# 短视频

### 片尾来源卡规则：5秒单图

根据最新审片反馈，《不要浪费精力》三集已更新为**每集末尾1张静态来源卡，最多5秒，展示2–3项研究**。完整 DOI、研究方法、其余引用保留在每集 `description.md`。查看[更新的三集预演](./ai-director/examples/energy-trilogy/README.md)。导演验证器已加入硬性约束。


## v0.2：专业导演提示词增强

- [完整指南：专业导演 v0.2](./ai-director/V02_GUIDE.md) — 适合没有编程经验的用户
- [53秒戒烟视频 · 新旧导演分镜对比](./ai-director/examples/quit-smoking/preview_v02.html)
- [逐秒导演合同 JSON](./ai-director/examples/quit-smoking/direction_v02.json)
- [Wan / Seedance 视频镜头 Prompt 与后期图形制作单](./ai-director/examples/quit-smoking/prompts_v02.json)

v0.2 强化：镜头目的、人物走位、微表情与动作、摄影开始与停止时刻、灯光色调、音效、连续性、视频模型差异与可审查验收标准。尚未生成真实视频；健康研究数字仍待来源核验。

**专业提示词参考项目**：
[sd2prompt](https://github.com/growgami/sd2prompt) ·
[visual-skills](https://github.com/smixs/visual-skills) ·
[AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline) ·
[video-prompt-skill](https://github.com/liqi21cn/video-prompt-skill)。

---


## 已启动的实现项目：AI 短视频导演 v0.1

- **[AI Director 源代码与运行说明](./ai-director/README.md)**：可运行的中文文案 → 导演制作计划 → Wan/Seedance Prompt → HTML 分镜预演。
- **[Codex 工作规则](./ai-director/AGENTS.md)**：使用当前 Codex + DeepSeek 做创意导演；不需要重新配置模型。
- **[戒烟测试样例](./ai-director/examples/quit-smoking/plan.json)**：53 秒、8 镜头；保留研究断言与待核验阻断。
- **[文字分镜预演](./ai-director/examples/quit-smoking/preview.html)**：可下载后用浏览器打开；这不是已经生成的视频。

当前进度：**导演数据结构、样例、模型 Prompt 和验证器已实现；真实视频生成、声音与 Remotion 合成尚未接入。**

---

这个目录专门收集和研究 **AI 短视频生产** 相关的 GitHub 项目，重点不是单纯“文生视频”，而是解决下面这条链路：

```text
文案 / 故事
→ 内容理解
→ 分镜拆解
→ Shot List
→ 人物 / 场景 / 风格一致性
→ 模型专用 Prompt
→ AI 视频生成
→ 配音 / 字幕 / 音乐
→ 自动剪辑成片
```

当前优先研究方向：**“文案 → 可供 AI 视频模型执行的中间层”**。

---

## 当前推荐项目

| # | 项目 | 角色 | 推荐级别 | 当前判断 |
|---|---|---|---|---|
| 1 | [reaink/script2video](https://github.com/reaink/script2video) | 文案→分镜→视频→拼片 | ★★★★★ | 最接近完整目标 |
| 2 | [approximatelylinear/story2video](https://github.com/approximatelylinear/story2video) | Story→Storyboard IR→视频 | ★★★★★ | 最值得拆中间层架构 |
| 3 | [teen-boop/AiProductionPipeline](https://github.com/teen-boop/AiProductionPipeline) | Agent Skills 制片流水线 | ★★★★★ | 最适合借鉴到 Codex |
| 4 | [LinHao-city/StoryMind](https://github.com/LinHao-city/StoryMind) | AI Storyboard Director | ★★★★★ | 最值得研究“导演层” |
| 5 | [thoxakihiko/shotlist-forge](https://github.com/thoxakihiko/shotlist-forge) | 概念/Beats→镜头 Prompt | ★★★★☆ | 适合做 Prompt Compiler |

---

## 1. reaink/script2video

- 原项目：<https://github.com/reaink/script2video>
- 核心用途：把书面脚本自动拆成结构化镜头，为每个镜头生成 Prompt，再调用视频模型生成 clip，最后拼接成完整视频。
- 已有能力：
  - AI Storyboarding
  - 镜头角度 / 构图 / 情绪 / 对白 / 音效
  - Veo / Runway / MiniMax Hailuo / Luma 等视频模型
  - 前一镜尾帧 → 下一镜首帧的一致性链路
  - 字幕导出
  - 9:16 竖屏
- 为什么推荐：
  - 与“我已经有文案，但不能直接拿去生成抖音视频”的问题最接近。
  - 它已经证明“Script → Shots → Prompt → Clips → Final Video”这条架构可行。
- 我们最值得借鉴：
  - Shot 数据结构
  - Script 拆镜头逻辑
  - Tail-frame continuity
  - 多模型 Provider 抽象层
- 状态：**第一优先研究**

---

## 2. approximatelylinear/story2video

- 原项目：<https://github.com/approximatelylinear/story2video>
- 核心用途：使用 LLM 把短故事转换成视觉 Storyboard 和 AI 视频片段。
- 为什么推荐：
  - 重点价值不只是生成视频，而是它把“故事理解”和“视频生成”分开。
  - 非常适合研究我们未来自己的 **Storyboard JSON / IR（中间表示）**。
- 我们最值得借鉴：
  - Scene decomposition
  - 结构化 Storyboard
  - Prompt generation
  - 全片风格一致性 Pass
  - Storyboard 可编辑、可重生成的设计
- 理想用途：
  - 把它的中间数据结构改造成适合 30–90 秒抖音内容的短视频 IR。
- 状态：**第一优先研究**

---

## 3. teen-boop/AiProductionPipeline

- 原项目：<https://github.com/teen-boop/AiProductionPipeline>
- 核心用途：一组 AI 电影制作 Agent Skills，从 script / story idea 一直走到 references、shot list、storyboard frame、video prompt。
- 关键特点：
  - Character identity lock
  - Continuity ledgers
  - 人物 / 天气 / 道具 / 服装跨镜头一致性
  - Storyboard shot selection
  - Cinematic prompt writer
  - Seedance prompt writer
  - Video clip continuity chain
- 为什么推荐：
  - 它不是一个单纯 App，而是一套 Agent 工作方法。
  - 与我现在使用 **Codex + DeepSeek** 的方式非常契合。
- 我们最值得借鉴：
  - 把整个短视频生产过程拆成多个 Skills
  - 每一步产生明确文件和中间产物
  - Character / Scene consistency ledger
  - “导演 Agent”负责协调多个子技能
- 状态：**重点研究，优先考虑改造成 Codex Skill**

---

## 4. LinHao-city/StoryMind

- 原项目：<https://github.com/LinHao-city/StoryMind>
- 核心用途：AI Storyboard Director。先像导演一样规划镜头，再生成视频。
- 它的典型流程：

```text
故事 / 文案
→ StoryboardPlanner
→ CharacterSheet
→ SceneConsistencyTracker
→ PromptEnhancer
→ Seedance / Kling / Veo
→ TTS / Music
→ FFmpeg / Remotion
→ Final Video
```

- 为什么推荐：
  - 非常接近我们讨论的“三层结构”：
    1. 内容导演
    2. 分镜导演
    3. Prompt Compiler
  - 它显式使用景别、运镜、灯光和 Character Anchor，而不是直接把原文塞给视频模型。
- 我们最值得借鉴：
  - Storyboard Director
  - Character Sheet
  - Cross-shot consistency
  - Cinematography Prompt Enhancement
  - Pipeline manifest / Skills 架构
- 状态：**重点研究导演层**

---

## 5. thoxakihiko/shotlist-forge

- 原项目：<https://github.com/thoxakihiko/shotlist-forge>
- 核心用途：把一个 concept 或一组 beats 转换成有顺序的 Shot List，并输出视频模型可执行 Prompt。
- 支持方向：Seedance、Kling、Runway、Veo。
- 关键能力：
  - Beats → Shots
  - 自动决定景别和运镜
  - 统一 style / lighting / mood / lens / aspect
  - 9:16 vertical
  - Duration planning
  - JSON 输出
- 为什么推荐：
  - 很适合做我们未来系统最后一层 **Prompt Compiler**。
  - 它非常轻，容易读懂，也容易改。
- 我们最值得借鉴：
  - Shot rhythm pattern
  - Continuity fields
  - JSON 输出
  - 模型无关的镜头描述 → 模型专用 Prompt
- 状态：**适合直接拆代码学习**

---

## 初步结论

目前不建议直接选一个项目全盘照搬。

更合理的路线是组合它们各自最好的部分：

```text
用户文案
↓
Script2Video / Story2Video 思路
【理解原文 + 拆 Scene】

↓
AiProductionPipeline
【角色 / 场景 / 道具 / 服装一致性】

↓
StoryMind
【导演层：景别 / 运镜 / 节奏 / 情绪】

↓
我们自己的 storyboard.json
【统一 IR】

↓
shotlist-forge
【Prompt Compiler】

↓
Seedance / Wan / Kling / Veo
【生成镜头】

↓
FFmpeg / Remotion / 其他剪辑层
【字幕 + 配音 + BGM + 成片】
```

---

## 我们自己的目标项目

暂定方向：**AI Video Director / 短视频导演 Agent**

核心不是再造一个视频生成模型，而是做：

> **“把中文文案编译成可以被不同 AI 视频模型稳定执行的导演级分镜计划。”**

未来最重要的中间文件建议是：

```text
storyboard.json
```

它至少需要包含：

- narration
- shot purpose
- duration
- visual type
- character anchor
- scene anchor
- subject
- action
- shot size
- camera movement
- lighting
- mood
- transition
- continuity constraints
- generation model
- model-specific prompt
- reference assets

这样未来即使 Seedance / Wan / Kling / Veo 更换，也不需要重写前面的导演系统。

---

## 下一步

1. 深挖以上 5 个项目的源码与数据结构。
2. 找出最适合直接复用的模块，而不是重复造轮子。
3. 设计我们自己的 `storyboard.json` Schema。
4. 选择第一版视频模型（优先 Seedance / Wan）。
5. 用一篇真实中文文案做端到端测试。
6. 再决定是 Fork 改造，还是重新组合成一个独立项目。

收录日期：2026-10-10
