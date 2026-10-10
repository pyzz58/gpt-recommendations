# AI 短视频导演 · MVP v0.1

## 三集长文案测试：《不要浪费精力》（2026-10-11）

已把用户原文的25项建议按叙事而非顺序拆成连续三集。各集包含 v0.1 `plan.json`、v0.2 `direction_v02.json`、详细镜头制作单、浏览器文字预演和带 DOI 的出处说明；**均不是已生成的真实视频**。来源卡只是文献追溯，片中效果数字仍须发布前复核论文的具体结果表。

| 集数 | 内容 | 时长（含片尾来源卡） | 预演 |
|---|---|---|---|
| 上 | 注意力、手机干扰、短暂打断、批量邮件 | 84秒 | [浏览](examples/energy-trilogy/ep01-attention/preview.html) |
| 中 | 6小时睡眠、咖啡因、作息、发光屏幕、小睡 | 91秒 | [浏览](examples/energy-trilogy/ep02-sleep/preview.html) |
| 下 | 社交比较、聚光灯效应、反刍、愤怒管理 | 89秒 | [浏览](examples/energy-trilogy/ep03-emotions/preview.html) |

[完整三集说明及删减决策](examples/energy-trilogy/README.md)

Mac 一次打开三集：

```bash
cd ~/GitHub/gpt-recommendations
git pull --ff-only
cd '短视频/ai-director'
open examples/energy-trilogy/ep01-attention/preview.html
open examples/energy-trilogy/ep02-sleep/preview.html
open examples/energy-trilogy/ep03-emotions/preview.html
```

注意：三集已接入原有校验器输入格式，但 GitHub CI 的远端执行是否成功要以 Actions 页面为准，不能只凭文件存在声称验证通过。

---


## v0.2 专业导演增强版（2026-10-11）

原有 v0.1 保持不变，现已加入 **Director Intelligence + Shot Feasibility / Continuity + Wan/Seedance Prompt Compiler**。这一版不是“把更多形容词塞进视频提示词”，而是将导演意图、逐秒动作、人物走位、摄影启动时机、美术、配音与音效、后期图表、参考素材和成片验收，全部写成可以独立审核的镜头合同。

**不会调用收费 API、不会自动渲染 MP4、不会自动发布。** 专业内容仍由你已有的 Codex + DeepSeek 创作；程序负责提供导演规则、检查冲突并编译候选提示词。

👉 **技术小白先看 [v0.2 一步步操作指南](V02_GUIDE.md)**

[旧版预演](examples/quit-smoking/preview.html)｜[专业导演新旧对比](examples/quit-smoking/preview_v02.html)｜[逐秒导演稿](examples/quit-smoking/direction_v02.json)｜[Wan/Seedance及图形制作单](examples/quit-smoking/prompts_v02.json)

```bash
cd ~/GitHub/gpt-recommendations/短视频/ai-director
python3 director_v2.py validate --base examples/quit-smoking/plan.json --direction examples/quit-smoking/direction_v02.json
python3 director_v2.py preview --base examples/quit-smoking/plan.json --direction examples/quit-smoking/direction_v02.json --out examples/quit-smoking/preview_v02.html
open examples/quit-smoking/preview_v02.html
```

目前戒烟样例：53 秒 / 8 镜头（2 个真人 AI 画面，6 个后期数据和医学动画镜头）；**医学事实未经过原始文献复核，禁止直接发布**。本地 v0.1 + v0.2 共 20 项测试通过，但尚未实际调用 Wan 或 Seedance 校验生成效果。

专业提示词规则参考：
- [sd2prompt](https://github.com/growgami/sd2prompt)：导演意图、跨段连续性、Prompt 修复、回拍
- [visual-skills](https://github.com/smixs/visual-skills)：表演、阻力、空间、物理细节和剪辑动机
- [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline)：角色/场景素材参考、镜头连续性
- [video-prompt-skill](https://github.com/liqi21cn/video-prompt-skill)：多模型提示词结构；所有模型兼容性须后续实测

**实现方式：参考设计方法、独立编写程序；未拷贝第三方项目代码。**

---


**定位：中文文案 → 结构化制作计划 → AI 视频 Prompt + 审核用 HTML 分镜预演。**

这是**可运行的前期导演系统**，不是完整视频生成器。当前不会生成真实视频、配音或自动发布抖音；也不会默默消费模型 API 费用。

设计参考：
- [CineCrew / FilmDSL](https://github.com/Ironieser/CineCrew) 的分层镜头设计、资产连续性和批评-返工机制（参考思想，不复制其代码）。
- [OpenMontage](https://github.com/calesthio/OpenMontage) 的制作阶段、质量关卡与人工审批（AGPL-3.0；本项目没有复制其代码）。
- [Short Video Maker](https://github.com/chemny/short-video-maker) 的面向 Codex 的脚本/分镜/视频计划分离方式（MIT；本项目未复制其代码）。

## 路线 A：直接用你现有的 Codex + DeepSeek（**不需要额外 API Key**）

1. 进入当前项目目录，把任意中文文案保存为 `my-script.md`。
2. 运行：

```bash
python3 director.py prepare --input my-script.md --out jobs/my-video
```

3. 在 Codex 中让它读取 `jobs/my-video/codex_task.md` 和 `AGENTS.md`，按要求创作 `jobs/my-video/plan.json`。**注意这一步的创造性导演工作是由 Codex 的模型完成，不是 prepare 命令自动完成。**
4. 验证和预览：

```bash
python3 director.py validate --plan jobs/my-video/plan.json
python3 director.py compile --plan jobs/my-video/plan.json --out jobs/my-video/prompts.json
python3 director.py preview --plan jobs/my-video/plan.json --out jobs/my-video/preview.html
open jobs/my-video/preview.html
```

## 路线 B：使用单独的兼容 API（可选，需要费用授权）

**仅在你明确要使用 API、了解其收费并自行配置凭证后使用。**不把密钥写进仓库：

```bash
export AI_API_KEY="在本机安全设置的密钥"
export AI_API_BASE_URL="https://api.deepseek.com/v1"
export AI_MODEL="deepseek-flash"  # 请按实际账户可用的模型 ID 修改
python3 director.py generate --input my-script.md --out jobs/my-video/plan.json
```

`generate` 的 JSON 输出先经过结构校验，失败则不会假装成功；生成后仍需人工复核事实、分镜、时长和视频模型兼容性。DeepSeek JSON Output 可能发生截断或空输出，本版只报错，不自动花钱重试。

## 试验：戒烟，越早越好

`examples/quit-smoking/` 已包含来自实际中文文案的 **53 秒 / 8 镜头**首版制作计划（**人工整理的测试样例，不是模型自动生成的成绩**）：

- `input.md`：原文
- `plan.json`：内容取舍、研究说法、人物/场景、动作链、镜头、摄影、美术、音频、字幕、动画设计
- `prompts.json`：Wan/Seedance 的镜头级 Prompt 示例；目前只为 `ai_video` 镜头编译
- `preview.html`：文字分镜审片页。**不是实际生成的视频。**

试跑：

```bash
python3 director.py validate --plan examples/quit-smoking/plan.json
python3 director.py compile --plan examples/quit-smoking/plan.json --out examples/quit-smoking/prompts.json
python3 director.py preview --plan examples/quit-smoking/plan.json --out examples/quit-smoking/preview.html
open examples/quit-smoking/preview.html
python3 -m unittest discover -s tests -v
```

## 核心规则

1. **编辑**：优先保留结论与必要证据，去除冗余数字、学术细节，并记录 `editorial.omissions`。
2. **数据与事实**：所有可核对说法写入 `claims`，保留 `source_quote`；研究/医学内容未查明文献时一律 `needs_review`。不能混用 OR、RR、HR、绝对风险。**通过技术校验 ≠ 事实已核实。**
3. **叙事**：以观众理解为先，按视觉信息目标拆镜头，旁白与镜头并非逐句对应。
4. **导演**：全片采用 `visual_bible`；每镜含场景、动作五步链、摄影、色调灯光、素材类型、动画、配乐、音效、字幕、转场。
5. **制作**：与 AI 视频模型相关的 Prompt 只写主体、场景、动作、镜头；精确文字、统计图表应放后期合成。
6. **质检**：程序校验时间轴、字段、claim 引用、人物场景 ID 和未核验声明；美术质量和史实仍需人工审片。
7. **审批**：在实际视频生成、支付费用、公开发布前必须单独人工确认。

## 本版已实现 / 尚未实现

| 能力 | v0.1 状态 |
|---|---|
| 任意中文文案进入 Codex 工作包 | ✅ |
| 外部兼容模型可选生成结构化 JSON | ✅（有 API Key 时；本轮未实测 API） |
| 审核 JSON schema 基本完整性/时间线 | ✅ |
| 53 秒戒烟数据样例 | ✅ |
| Wan / Seedance 镜头 Prompt 编译 | ✅（文本 Prompt，不保证平台参数兼容） |
| HTML 文字分镜可视审阅 | ✅ |
| 文献联网核验、医学数据自动审查 | ❌，目前是人工核验阻断 |
| 图片/视频生成、TTS、Remotion/FFmpeg 合成 | ❌ |
| 抖音发布 | ❌ |

下一阶段优先：LLM 两阶段导演拆分、可编辑时间线、Remotion 9:16 第一帧、分镜修订/局部返工，然后再对接视频 Provider。

## 运行环境与许可

Python 3.10+，仅用标准库。此目录代码为本次独立编写；第三方项目仅引用架构思想和原始链接。接入第三方源码时另行检查许可证与服务条款。