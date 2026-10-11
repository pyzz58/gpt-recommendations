# AI 短视频导演 v0.3 · 中国回国可携带的本地优先版本

> **当前开发状态（2026-10-11）｜仅 GitHub 研发，暂不本地部署。** 用户已决定在明确宣布“可以开始本地运行/部署”之前，只在 GitHub 开发、研究并合规融合成熟开源项目。以下 Mac、Codex、API 命令均是**未来部署参考**，当前不要求执行；现有 Mac 项目副本保留不动。研发优先看 [GITHUB_ONLY_DEVELOPMENT.md](GITHUB_ONLY_DEVELOPMENT.md) 与 [AGENTS.md](AGENTS.md)。没有私人文案或真实本地 job，GitHub 上只能用合成测试验证；不得宣称已经完成真实视频端到端验收。


**状态：可运行的本地工作流原型 / 不是已完成的自动视频生产软件。**

v0.3 的重点不是更换服务，而是把项目脱离 GitHub/ChatGPT 的实时连接依赖。程序与导演规则全在本地，HTML 预演和JSON不需上网；创作阶段可以用用户现有 Codex+DeepSeek，或额外配置 DeepSeek 等兼容 API 实现命令行自动阶段执行。**云端模型并不离线，能否访问取决于当地网络、供应商与账号。**

## Mac 最简单使用方法：沿用 Codex（无额外LLM API Key）

1. 把这个文件夹保存在 Mac 的桌面、GitHub 工作树内或U盘；本目录可独立运行，无需在线GitHub。
2. 打开终端并进入此文件夹，例如：
   `cd ~/Desktop/ai-director-v03`
3. 输入你的文章，使用 TextEdit 保存成 `article.md`（纯文本、UTF-8）。
4. 运行：
   `python3 local_director.py prepare --input article.md --out jobs/my-video`
5. 在**已正常连接 DeepSeek 的 Codex**打开这个文件夹，让 Codex 读 `AGENTS.md` 与 `jobs/my-video/CODEX_TASK.md`，完成其要求的分阶段创意工作。
6. 再输入：
   `python3 local_director.py review --job jobs/my-video`
7. `open jobs/my-video/index.html` 查看本地预演。**仍不是真视频。**

如果 Codex 无法使用，但国产 DeepSeek API 可用，可使用下面的直连方案，不依赖 Codex。若连云端模型也不可用，则仍可浏览/修改已有项目和审片，**不能凭空自动完成创意工作**。可后续接入本地自部署模型兼容接口。

## 独立模型 API 自动化（可选、可能收费）

不要把 API Key 写在Markdown或GitHub仓库。Mac终端先用 `export AI_API_KEY='...'`（建议用安全方式临时设置），然后：

```bash
python3 local_director.py run --input article.md --out jobs/my-video-new --approve-model-cost --max-cost-cny YOUR_APPROVED_CNY_BUDGET
open jobs/my-video-new/index.html
```

- 默认提供 **DeepSeek 官方兼容API** 端点 `https://api.deepseek.com/v1` 与示例模型ID `deepseek-flash`；若供应商日后调整，指定 `--model` 或 `AI_MODEL`。请先检查自己的账号对应实际模型。
- **费用安全现已接入（2026-10-11）**：真实API请求必须同时具备 `--approve-model-cost` 和 `--max-cost-cny` 用户指定人民币预算；默认最多7次请求、0次自动重试、单次最多16,384输出tokens。请求前按官方高峰价格和保守Token估计预留预算，记录在 `api_usage.generated.json`；超过预留金额或次数会阻止调用。空JSON、非法JSON、模型新稿缺结构字段可以在明确设置 `--max-retries 1` 或 `2` 后有限修复；超时、断网和HTTP 5xx不可自动重试。本地预算只是预估保护，**不是供应商账单的绝对上限**。
- 若中途失败，已成功生成的 `series.json`、`plan.json` 会保留。修订草稿后可 `--resume` 续跑；API生成不保证每次一键直接通过质量校验。拒绝把不合格作品伪装成成功。
- 使用别的国内服务：需其兼容 Chat Completions + JSON对象输出；显式设置 `AI_API_BASE_URL` 和 `AI_MODEL`，事先检查收费与服务条款。支持 `http://127.0.0.1:端口/v1` 作为未来本地模型接口（未做实际兼容性测试）。

## 新增：离线完整连续性合同和修稿规范

任何已有 `plan.json` 都可以用以下命令免费审查：

```bash
python3 local_director.py audit --plan jobs/live-pilot-001/episodes/ep01/plan.json
```

现支持可选 `continuity_contract` 完整模式：记录全局唯一人物和道具、所有镜头初始与结束位置、顺序移动事件；检测从沙发到抽屉的物品瞬移以及人物未到位的物品操作。完整定义参见 `CONTINUITY_QA.md`、`schemas/continuity_contract.schema.json` 和 Codex 的 `skills/06-continuity-repair.md`。

**不要直接修改原片**。按上述 Codex 工作流先生成 `plan.proposed.json`，然后在本地验证并人工审核。没有采纳整个 CineCrew 或 transitions 包；零运行时额外依赖，无视频或 API 费用。

## 剪辑、旁白、动画的逐秒工作单（当前仅 GitHub 研发）

新增 `director_timeline.py`：把已明确写入专业导演稿的动作节拍、摄影、剪辑入出转场、旁白分句（如有独立时间码）、出镜台词、音效与动画图层整理为绝对秒数的 `editor_decision_list`，让导演交付结果便于后期实际执行。详细见 [EDITOR_TIMELINE.md](EDITOR_TIMELINE.md)。

没有精确时间点时只记录待人工补齐，不伪装成已完成的配音同步或剪辑工程。对于过密中文旁白提示试读；对于超出镜头时长的音效/动画事件做阻断。这个纯 Python 模块不会调用模型、不处理真实素材，也不改变 Mac。

## 产品主线：文案输入 → 一整套短视频导演交付书（当前仅 GitHub 研发）

系统真正需要输出的不是单纯视频 Prompt，而是从文章和故事提炼成逐集、逐镜头专业导演方案，覆盖动作、场景、摄影、演员、动画、台词、配音、音乐音效、剪辑、转场、参考资产、制作手段和后期工作单。详见 [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md)。

已新增 `director_workbook.py`，它将 `plan.json` 和 `direction_v02.json` 汇成 `director_workbook.json` 与 `director_workbook.md`；现有 `local_director.review_job` 也会在未来运行时生成导演交付书并在总预览首页显示。对于旧导演稿缺失的剪辑、动画、台词设计会报告 `creative_design_complete=false`，而不是自动填假内容。严格校验只对补全上述字段后的新稿开放；脚本技术正确不代表已获用户人审。

**用户尚未批准在 Mac 部署**：上述仅指 GitHub 源码设计，不需要用户执行命令，也不声称已完成真实作品端到端视频制作。

## 模型输入参考清单（GitHub-only）

已新增 `reference_input_preview.py` 与 [REFERENCE_INPUT_PREVIEW.md](REFERENCE_INPUT_PREVIEW.md)。它只把“每镜需要哪些人物角度、场景、道具”转换为模型无关的输入预览，不读取图片、不输出私有文件路径、不产生付费请求，不能直接用于 Wan/Seedance 的正式 API。相关 9 项新回归测试已加入源码，尚待在最新仓库完整快照上执行。

## 新增：角色/场景/道具参考资产管理（仅 GitHub 源码）

通过 `reference_assets.py` 可离线生成参考资产清单（每张图默认为 `not_created`）、按镜头检查人物角度/场景/道具引用、检测不存在或哈希不符的文件，并将审核结果附入专业导演编译输出。通用格式为 `schemas/reference_assets.schema.json`，完整使用和边界见 [REFERENCE_ASSETS.md](REFERENCE_ASSETS.md)。

**当前不生成参考图片，不声称人脸跨镜头已经锁定；用户 Mac 不需下载、同步或安装。**

## 生成前阻断与禁止意外付费（仅源码）

增加独立 `production_gate.py`：检查导演编译包的参考资产就绪状态、逐镜人工审核、真实参考媒体是否已交付，以及视频/静态/后期制作路线。每次 `director_v2.compile_package()` 会在结果附加 `generation_gate`。

**它不具备发起视频或图像生成请求的能力**，默认禁止执行、付费和发布；参见 [GENERATION_GATE.md](GENERATION_GATE.md)。继续只在 GitHub 开发，Mac 保持不变。

## 导演 v0.2 混合制作路线（目前仅 GitHub 研发）

2026-10-11 修复：原编译器把所有 `base.visual_type=ai_video` 的镜头强制送往 AI 视频模型，现在 `generation.route` 可以单独选择 `ai_video`、`static_post`、`edit_composite`、`live_action_insert`、`post_production`。支持部分旧 `production_method` 别名，未知类型显式报错。非视频路线只输出后期/实拍工作单，`production_summary` 给出 AI 视频实际镜头数量。

参见 [PRODUCTION_ROUTING.md](PRODUCTION_ROUTING.md)。这是源码和隔离环境回归测试，**不意味着用户本地私人导演档已验证、生成了视频或获得了素材授权**。Mac 部署继续暂停。

## 本地自检与备份

```bash
python3 local_director.py doctor
python3 -m unittest discover -s tests -v
python3 local_director.py backup --project . --out ../ai-director-backup.zip
```

ZIP 可以保存在 Mac、移动硬盘和其他存储位置。不要只保存在GitHub。备份程序排除 `.env`，但文章、人物素材和其他工作文件可能含隐私，请自行妥善保管。

## 功能边界

已实现：逐阶段API调度、Codex任务单、1–3集系列规划数据约束、系列角色Bible、证据状态保守处理、逐镜头v0.1/v0.2结构校验、5秒来源卡规则、本地HTML预览、WAN/Seedance候选提示词、本地ZIP备份与阶段状态保存。

尚未实现：真实的人物多角度参考图片、参考图自动绑定到视频模型、已生成影像的验收和智能重拍、跨镜局部智能重写UI、音频播放的MP4节奏预演、真正的视频生成、数字动画渲染、字幕/配乐合成、模型费用估算、人工一键网页操作。**2026-10-11 已完成真实 DeepSeek API 部分试验：系列策划 series.json 与第一集 plan.json 已由真实模型返回；首次返回非法 JSON 已保留故障记录；direction_v02.json 与真实视频未验证。本地费用记录不代表官方扣款账单。**

## 回国可用性

- GitHub 是云端远程仓库，网络可能无法稳定访问，**不能依靠它作为唯一备份**；在国内可考虑新建Gitee等备份仓库，但先检查授权、公开性和敏感素材问题，所有推送必须单独确认。
- OpenAI 的 ChatGPT/Codex服务可用地区不包括中国大陆，不能承诺在中国大陆可持续登录访问；本项目不能依赖它们才可以打开或运行。
- DeepSeek 国内云模型也需要联网；服务模型、接口、价格与连接都可能变化。纯本地阶段（prepare/review/backup）无需任何网络；自动创意生成必须有可用LLM。
- 使用 macOS 及 Python3.10+，无 pip 第三方依赖、无 Node/npm 强制依赖。Windows/Linux 可运行Python部分，`open` 为 Mac 命令。

## 上游开源参考

`growgami/sd2prompt`、`smixs/visual-skills`、`Ironieser/CineCrew`、`billpar/ai-cinematic-pipeline`、`liqi21cn/video-prompt-skill` 目前**只借鉴方法论**，v0.3 Skills 为独立创作。尚未直接合并或安装它们的源码。未来挑选可合法复用模块后再逐项移植并附许可信息。

## 技术小白：本地粘贴网页（零API费用）

macOS 可以在终端进入项目目录，运行 `bash '启动AI导演.command'`，或者执行：

```bash
python3 local_ui.py
```

会在Mac浏览器打开 `http://127.0.0.1:8765`：粘贴文章、填英文项目名、点击“保存并生成Codex任务”。文章只在当前Mac保存到 `jobs/<名字>/`，不会上传互联网。之后让本机已连DeepSeek的Codex读取 `CODEX_TASK.md` 并创作，结束执行 `python3 local_director.py review --job jobs/<名字>`。

此网页目前只是本地输入界面，**不是点按钮就全自动做AI导演**。真正自动的分阶段AI处理，需要前述 `run --approve-model-cost` 和可用的API凭据。本机访问页面时不会向外部发起网络请求。
## v0.3 P0 可靠性修复（2026-10-11）

- **长文输入**：表单接收限额扩大，正文最多45,000字符、UTF-8最多250KB；超限显示错误，不改变原文的首尾空白。用用户真实的27,099字符长文作本地HTTP回归，HTTP 200且文件逐字一致。
- **二次审片保护**：程序更新 `description.generated.md`、`prompts.generated.json`、`review_status.generated.json`；`description.md`、`prompts.json`、`review_status.json` 若已存在，**不覆盖人工内容**。
- **续跑保护**：保留 `character_bible.json`、`status.json`；已手动批准的角色或服装与镜头冲突时报告错误，而不是恢复LLM旧稿。请不要手动改 `series.json` 而忽略角色Bible。
- **文献账本**：来源卡必须有 `plan.references`，每条具备作者、年份、期刊、研究类型、可追溯URL和 `needs_review` 标记；代码并**不能**自动证明论文真实或数字准确。无可靠来源时省略研究卡。
- **测试**：在原29项基础上增加8项离线回归，37项通过；覆盖三集模拟续跑、研究元数据、服装和色调漂移、手动编辑保护与长文输入。**真实收费LLM和国产视频生成仍未实测。**

本轮仅更新代码、规则和测试，没有制作 ZIP / 下载交付，也不接入收费模型。源文件仍由 GitHub 记录修订。


## 下一阶段：有预算的真实模型测试（尚未得到具体金额授权）

当前本地模拟测试 **54项通过**，包括HTTP本机模拟端点、三集续跑、预算拦截、逐次记账、防并行调用、空/非法JSON定量重试和结构修复；真实DeepSeek API尚未测试。

- 默认 `deepseek-flash`（官方列为 V4.1 Flash）高峰预留单价：输入¥2/百万Token（缓存未命中）、输出¥8/百万Token，价格随服务商变化，测试前重新核对。
- 其他模型或第三方接口必须指定 `--input-cny-per-million`、`--output-cny-per-million` 的人民币最高单价。
- 可设置 `--max-calls`、`--max-output-tokens`、`--max-retries`；每次尝试必须重新预留，失败可能仍消耗预算；不重复调用已经完成的阶段。
- 使用 `python3 local_director.py cost-status --job jobs/项目目录` 可读取已记录的预留费用和服务端实际Token用量（如果供应商返回）。
- `--max-cost-cny` 是用户明确授权的本地预算防线，而不是DeepSeek结算金额保证。使用前了解网络请求会发送原文给模型服务商。
- 未获得用户明确的人民币最高测试金额和实际授权前，不进行任何收费调用；不打包、不下载、不发布。

官方参考：[模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) · [JSON 输出](https://api-docs.deepseek.com/zh-cn/guides/json_mode/) · [错误码](https://api-docs.deepseek.com/zh-cn/quick_start/error_codes/)。

## v0.3 物理连续性离线审查（新增）

已生成的 plan.json 可以免费执行：

```bash
python3 local_director.py audit --plan jobs/live-pilot-001/episodes/ep01/plan.json
```

程序在同一集目录写入 `continuity_audit.generated.json` 与 `continuity_repair.generated.md`，不会修改原始 plan。对确认的道具跳跃作阻断、对可能有意的剪辑只提出待核查警告；`run --resume` 在方向稿的付费请求之前检查阻断项。详见 [CONTINUITY_QA.md](CONTINUITY_QA.md)。

**尚未实现**：自动修复所有镜头、真正的视频渲染、人体动作物理模拟以及通用语言语义理解。修订稿应先输出为新的 `plan.proposed.json`，审核后才可替换正式计划；不自动增加付费请求。
