# v0.2 专业导演增强版：小白使用指南

**目前只产出导演方案、可执行候选 Prompt 和 HTML 预演；不会调用付费视频/配音接口，也不会自动发布。**

如果已在 Mac 上 clone 了 `pyzz58/gpt-recommendations`，先打开终端：

```bash
cd ~/GitHub/gpt-recommendations
git pull --ff-only
cd '短视频/ai-director'
python3 -m unittest discover -s tests -v
```

> **当前暂停本地运行**：2026-10-11 起本项目只在 GitHub 研发，以下历史命令仅供将来用户明确授权部署后参考。现代混合制作路线的校验与编译规则参见 [PRODUCTION_ROUTING.md](PRODUCTION_ROUTING.md)，不要再把全部概念 AI 镜头当作付费视频镜头。

## A. 直接看升级后的《戒烟》演示

```bash
python3 director_v2.py validate --base examples/quit-smoking/plan.json --direction examples/quit-smoking/direction_v02.json
python3 director_v2.py preview --base examples/quit-smoking/plan.json --direction examples/quit-smoking/direction_v02.json --out examples/quit-smoking/preview_v02.html
open examples/quit-smoking/preview_v02.html
```

浏览器将显示旧版概略与新版导演设计的并排对比。每镜有时间段、动作和摄影/声音，**这仍然是导演图纸，不是 MP4**。

两段真人 AI 镜头的 Wan / Seedance 候选提示词及六个后期图表/动画工作单：

```bash
python3 director_v2.py compile --base examples/quit-smoking/plan.json --direction examples/quit-smoking/direction_v02.json --out examples/quit-smoking/prompts_v02.json
open -a TextEdit examples/quit-smoking/prompts_v02.json
```

## B. 新文章怎么操作（不懂技术就整段复制给 Codex）

先让 Codex v0.1 从新文案生成 `jobs/<主题>/plan.json`，遵守现有 `AGENTS.md` 和 `README.md`。然后在 Codex 里说：

> 继续用当前 DeepSeek，不修改模型设置。根据 `V02_GUIDE.md` 和 `director_v2.py` 给刚才的 `plan.json` 制作专业导演增强版。
> 第一步运行 `scaffold` 生成 `direction_v02.json`，再运行 `task` 生成 Codex 任务书。
> 请自己阅读任务书，逐镜头完成导演细节，包括逐秒动作、演员空间关系、光线、景别、运镜触发、配乐和后期数据动画。
> 验证后用 `compile` 生成 `prompts_v02.json`，用 `preview` 生成 `preview_v02.html` 并打开浏览器让我审核。
> 不准调用付费生成模型，不准自动发布；有待核验医学/财经/法律事实时保留警告，不要编造证据。

也可以手工按以下通用命令执行（假设你的主题叫 `my-video`）：

```bash
python3 director_v2.py scaffold --base jobs/my-video/plan.json --out jobs/my-video/direction_v02.json
python3 director_v2.py task --base jobs/my-video/plan.json --direction jobs/my-video/direction_v02.json --out jobs/my-video/codex_director_v02.md
# 现在由 Codex 读取任务书完成方向文件，而不是让 scaffold 自己假装生成导演创意。
python3 director_v2.py validate --base jobs/my-video/plan.json --direction jobs/my-video/direction_v02.json
python3 director_v2.py compile --base jobs/my-video/plan.json --direction jobs/my-video/direction_v02.json --out jobs/my-video/prompts_v02.json
python3 director_v2.py preview --base jobs/my-video/plan.json --direction jobs/my-video/direction_v02.json --out jobs/my-video/preview_v02.html
open jobs/my-video/preview_v02.html
```

## v0.2 核心增强

- **导演意图先于形容词**：每镜必须有可观察的视觉转折与动作终点。
- **按镜头内部时间编码**：beat 时间连续且覆盖整镜；单镜的走位、摄影和声音围绕同一变化。
- **物理与连续性**：人物、左右手、光源、道具位置、镜头首末状态可核对；未制作的参考图必须明确“待制作”。
- **模型专用编译**：Wan / Seedance 候选 Prompt 区分连续镜头与后期准确图文，非真人的6段图形不会强行发送视频模型。
- **质量门槛**：动作时间轴断裂、引用未存在研究断言、生成路线冲突、缺人物约束等会报错。

## 当前限制（真实情况）

- 智能写作仍由 **Codex + 现有 DeepSeek** 执行；`scaffold` 本身只生成**带占位符的草稿**，不含智能导演创作，不能通过最终校验。
- 电脑里不一定装有 Wan 或 Seedance，也未进行实际模型 API 的 Prompt 执行测试；模型提示词只是经过规则约束的候选稿。
- HTML 只为文字审片，未加实际画面、配音、背景音乐和编辑时间线；需要后续阶段接入。
- 对戒烟医学数据只是“发布阻断、保留研究口径”，不是事实核查。正式发布要另查可靠的原始文献。