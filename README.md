# GPT 推荐

这个仓库用于保存 ChatGPT 推荐给我的值得研究、使用或二次开发的 GitHub 开源项目。

每个项目需要记录：

- 项目名称
- GitHub 原始地址
- 项目用途
- 推荐原因
- 可以如何使用
- 与我现有项目可能的结合方式
- 推荐日期
- 后续研究状态

> 说明：本仓库只做「项目索引 + 研究笔记」，**不复制**任何第三方项目的完整源码。
> 所有项目均保留原作者与原始 GitHub 地址，版权归原作者所有。

## 项目索引

| # | 项目 | 原始地址 | 状态 |
| - | ---- | -------- | ---- |
| 1 | yetone/magpie | <https://github.com/yetone/magpie> | 待研究 |
| 2 | KKKKhazix/AIHOT | <https://github.com/KKKKhazix/AIHOT> | 待研究 |
| 3 | Contrastive-LM/CLM | <https://github.com/Contrastive-LM/CLM> | 待研究 |
| 4 | firelex/jeff | <https://github.com/firelex/jeff> | 待研究 |
| 5 | feitangyuan/onetake | <https://github.com/feitangyuan/onetake> | 待研究 |
| 6 | TencentCloud/octop-harness | <https://github.com/TencentCloud/octop-harness> | 待研究 |
| 7 | ufo-ai/ufo-core | <https://github.com/ufo-ai/ufo-core> | 待研究 |
| 8 | storytold/photocraft（Photoshop 复刻） | <https://github.com/storytold/photocraft> | 待研究 |
| 9 | storytold/vectorcraft（Illustrator 复刻） | <https://github.com/storytold/vectorcraft> | 待研究 |
| 10 | storytold/filmcraft（Premiere Pro 复刻） | <https://github.com/storytold/filmcraft> | 待研究 |
| 11 | storytold/lightcraft（Lightroom 复刻） | <https://github.com/storytold/lightcraft> | 待研究 |
| 12 | storytold/pdfcraft（Acrobat 复刻） | <https://github.com/storytold/pdfcraft> | 待研究 |
| 13 | storytold/effectcraft（After Effects 复刻） | <https://github.com/storytold/effectcraft> | 待研究 |
| 14 | storytold/designcraft（InDesign 复刻） | <https://github.com/storytold/designcraft> | 待研究 |
| 15 | storytold/wordcraft（Word 复刻） | <https://github.com/storytold/wordcraft> | 待研究 |
| 16 | storytold/gridcraft（Excel 复刻） | <https://github.com/storytold/gridcraft> | 待研究 |
| 17 | storytold/deckcraft（PowerPoint 复刻） | <https://github.com/storytold/deckcraft> | 待研究 |
| 18 | storytold/cadcraft（AutoCAD 复刻） | <https://github.com/storytold/cadcraft> | 待研究 |
| 19 | storytold/soundcraft（Pro Tools 复刻） | <https://github.com/storytold/soundcraft> | 待研究 |

> 第 8–19 项属于同一个家族的「ArtCraft Crafting Apps」，详情见下方 [第 8 节](#8-artcraft-crafting-apps-系列用-rust-重写-adobe-全套)。

---

## 1. yetone/magpie

- 项目名称：magpie（yetone/magpie）
- GitHub 原始地址：<https://github.com/yetone/magpie>
- 项目用途：统一管理 Codex、Claude Code、Gemini CLI、OpenCode 等 AI Agent 使用的模型和 Provider。
- 推荐原因：对我尤其有用，因为我的 Codex 使用 DeepSeek，并且以前遇到过 model 和 model_provider 配置不一致的问题。
- 可以如何使用：用它集中维护各个 CLI Agent 的模型与 Provider 配置，避免每个工具分别手改配置文件导致不一致。
- 与我现有项目可能的结合方式：作为 Codex / DeepSeek 使用环境的标准配置层，配合多 Agent 工作流统一模型入口。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/magpie/README.md`）

## 2. KKKKhazix/AIHOT

- 项目名称：AIHOT（KKKKhazix/AIHOT）
- GitHub 原始地址：<https://github.com/KKKKhazix/AIHOT>
- 项目用途：自动完成信息采集、筛选、独立评分、事件聚类、热点计算和日报生成。
- 推荐原因：值得研究它的 pipeline，并考虑用于我的趋势雷达、信息筛选和研究系统。
- 可以如何使用：拆解 pipeline 的各个阶段（采集 → 筛选 → 评分 → 聚类 → 热点 → 日报），按需复用到自己的信息流。
- 与我现有项目可能的结合方式：趋势雷达、每日情报日报，结合 Codex 自动化做定时运行。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/AIHOT/README.md`）

## 3. Contrastive-LM/CLM

- 项目名称：CLM（Contrastive-LM/CLM）
- GitHub 原始地址：<https://github.com/Contrastive-LM/CLM>
- 项目用途：专门做候选动作选择、Agent routing 和快速判断的 System One 模型。
- 推荐原因：可以用于未来 Agent 的工具选择、第一层筛选和决策 Gate。
- 可以如何使用：作为轻量决策层，在调用大模型之前先完成候选动作选择与 routing 判断，降低延迟和成本。
- 与我现有项目可能的结合方式：Agent 工具选择、第一层筛选、决策 Gate，与 jeff 一起评测后选型。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/CLM/README.md`）

## 4. firelex/jeff

- 项目名称：jeff（firelex/jeff）
- GitHub 原始地址：<https://github.com/firelex/jeff>
- 项目用途：小型、本地运行、速度很快的分类和决策模型。
- 推荐原因：适合做信息分类、Agent 路由、信号评级和工具选择。
- 可以如何使用：在本地做批量分类、打标与评级，替代昂贵的 LLM 调用完成初筛。
- 与我现有项目可能的结合方式：与 CLM 做对比评测，选一个作为本地分类 / 路由 / 评级模型。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/jeff/README.md`）

## 5. feitangyuan/onetake

- 项目名称：onetake（feitangyuan/onetake）
- GitHub 原始地址：<https://github.com/feitangyuan/onetake>
- 项目用途：AI Agent Skill，可以生成一镜到底的产品宣传片和功能 Demo。
- 推荐原因：可以用于以后自己开发的网站、App 和产品展示。
- 可以如何使用：把做好的网站 / App 录制成一镜到底的宣传片与功能 Demo，用于发布和推广。
- 与我现有项目可能的结合方式：接入我自己的网站 / App 项目的发布与展示流程。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/onetake/README.md`）

## 6. TencentCloud/octop-harness

- 项目名称：octop-harness（TencentCloud/octop-harness）
- GitHub 原始地址：<https://github.com/TencentCloud/octop-harness>
- 项目用途：Production-grade AI Agent runtime。包含多模型、长期记忆、Browser、MCP、工具、Agent registry、持久化和权限控制。
- 推荐原因：值得作为未来个人 AI / Jarvis 项目的基础架构参考。
- 可以如何使用：研究其 runtime 架构设计（Agent registry、持久化、权限控制、MCP 接入），作为自建 Agent 平台的参考实现。
- 与我现有项目可能的结合方式：个人 AI / Jarvis 项目的基础架构参考，与 ufo-core 一起对比选型。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/octop-harness/README.md`）

## 7. ufo-ai/ufo-core

- 项目名称：ufo-core（ufo-ai/ufo-core）
- GitHub 原始地址：<https://github.com/ufo-ai/ufo-core>
- 项目用途：自托管 AI Agent runtime。Agent 可以操作文件、执行命令、维护 workspace 和持久任务。
- 推荐原因：可以研究如何构建长期运行的个人 AI 系统。
- 可以如何使用：自托管部署并研究长期运行 Agent 的任务调度、workspace 维护与持久化设计。
- 与我现有项目可能的结合方式：与 octop-harness 对比，作为长期运行个人 AI 系统的候选底座。
- 推荐日期：2026-10-04
- 后续研究状态：待研究（笔记见 `projects/ufo-core/README.md`）

---

## 8. ArtCraft Crafting Apps 系列（用 Rust 重写 Adobe 全套）

- 项目家族：ArtCraft Crafting Apps（GitHub 组织：[storytold](https://github.com/storytold)，官网 [getartcraft.com](https://getartcraft.com)）
- 家族性质：**clean-room 重实现**——不使用 Adobe / Microsoft 的任何源码或资产，全部用纯 Rust 从零写；每个 App 可独立使用。
- 平台：macOS / Windows / Linux / FreeBSD 原生，浏览器里跑 WebAssembly，另提供 CLI 命令行工具，README 专门有 "Built for agents" 一节，可被 Agent 直接驱动。
- 许可证：Apache-2.0（README 标注 MIT / Apache-2.0 双许可）。版权归原作者所有，本仓库只做索引与笔记。
- 当前状态：全部标注为 **early alpha**，适合尝鲜与架构研究，暂不宜作为生产替代品。
- 建仓时间：Adobe 系 7 款为 2026-09-30 起，Microsoft / CAD / 音频系 5 款为 2026-10-07 起。
- 热度快照（2026-10-11 抓取）：12 款合计约 88,950 star，其中 PhotoCraft 单条 41,444。
- 本机状态：macOS 安装包（universal，已签名并公证）已下载到 `~/Downloads/ArtCraft/`，12 个文件共 794 MB 磁盘占用，SHA256 全部与官方校验文件一致；源码 12 个仓库合计约 205 MB。

### 8.1 家族总览：每个项目都是干什么的

| 应用 | 对应商业软件 | 干什么用 | Star | macOS 安装包 |
| ---- | ------------ | -------- | ---- | ------------ |
| PhotoCraft | Adobe Photoshop | 图像编辑：图层、蒙版、调整图层、图层样式、文字、矢量、笔刷，并读写真实 PSD 文件 | 41,444 | 78.7 MB |
| VectorCraft | Adobe Illustrator | 矢量插画与图形设计 | 6,058 | 85.1 MB |
| FilmCraft | Adobe Premiere Pro | 视频剪辑、调色与声音处理 | 8,495 | 66.2 MB |
| LightCraft | Adobe Lightroom | 相片库管理与 RAW 显影 | 8,898 | 94.6 MB |
| PdfCraft | Adobe Acrobat | PDF 阅读、整理与保护 | 7,813 | 83.2 MB |
| EffectCraft | Adobe After Effects | 动效设计与视觉特效 | 4,487 | 58.2 MB |
| DesignCraft | Adobe InDesign | 页面版式与出版 | 2,516 | 72.1 MB |
| WordCraft | Microsoft Word | 文字处理与文档编辑 | 3,054 | 59.4 MB |
| GridCraft | Microsoft Excel | 电子表格与数据计算 | 1,761 | 19.4 MB |
| DeckCraft | Microsoft PowerPoint | 演示文稿与幻灯片 | 1,366 | 75.5 MB |
| CadCraft | AutoCAD | 计算机辅助设计与制图 | 1,786 | 23.1 MB |
| SoundCraft | Avid Pro Tools | 音频录制与编辑 | 1,272 | 19.3 MB |

### 8.2 PhotoCraft（对应 Photoshop）

- 项目名称：PhotoCraft（storytold/photocraft）
- GitHub 原始地址：<https://github.com/storytold/photocraft>
- 项目用途：图像编辑。clean-room 重写 Photoshop，支持图层、蒙版、调整图层、图层样式、文字、矢量、笔刷，并直接读写真实 PSD 文件。
- 推荐原因：整个 Adobe 全家桶被同一个团队用纯 Rust 重写，PhotoCraft 是旗舰项目（2026-10-11 为 41,444 star），是「不订阅 Photoshop 到底行不行」最值得实测的一个。
- 可以如何使用：直接装 macOS / Windows / Linux 原生版试用；也可以用浏览器 WebAssembly 版免安装体验，或用配套 CLI 做无界面批处理。
- 与我现有项目可能的结合方式：为 AI 短视频、产品展示类素材提供本地、可脚本化、可被 Agent 驱动的图像处理能力。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.6.0 安装包，未安装；笔记见 `projects/photocraft/README.md`）

### 8.3 VectorCraft（对应 Illustrator）

- 项目名称：VectorCraft（storytold/vectorcraft）
- GitHub 原始地址：<https://github.com/storytold/vectorcraft>
- 项目用途：矢量插画与图形设计，clean-room 重写 Illustrator。
- 推荐原因：矢量工具是 Adobe 订阅体系里最难替代的部分之一，它选择用 Rust 自研渲染，值得看实现路线。
- 可以如何使用：做 Logo、图标、插画等矢量图；CLI 可用于批量转换与导出。
- 与我现有项目可能的结合方式：给网站 / App 项目产出图标与插画素材，配合 Agent 自动化生成图形。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.8.0 安装包，未安装；笔记见 `projects/vectorcraft/README.md`）

### 8.4 FilmCraft（对应 Premiere Pro）

- 项目名称：FilmCraft（storytold/filmcraft）
- GitHub 原始地址：<https://github.com/storytold/filmcraft>
- 项目用途：视频剪辑，clean-room 重写 Premiere Pro，覆盖剪辑、调色与声音。
- 推荐原因：视频剪辑是 Adobe 全家桶里最吃性能的一环，纯 Rust 的路线如果跑得动，对短视频工作流价值很大。
- 可以如何使用：本地做剪辑与调色；CLI 可接入自动化流水线，做转码、拼接、批量处理。
- 与我现有项目可能的结合方式：接入「AI 短视频」专题里的自动成片环节，承担成片后的剪辑与导出。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.5.0 安装包，未安装；笔记见 `projects/filmcraft/README.md`）

### 8.5 LightCraft（对应 Lightroom）

- 项目名称：LightCraft（storytold/lightcraft）
- GitHub 原始地址：<https://github.com/storytold/lightcraft>
- 项目用途：相片库管理与 RAW 显影，clean-room 重写 Lightroom。
- 推荐原因：RAW 显影涉及色彩管理与解码，是检验这套 Rust 技术栈深度的关键项目（家族里安装包最大，94.6 MB）。
- 可以如何使用：整理相片库、批量调色与导出；支持 RAW 格式处理。
- 与我现有项目可能的结合方式：为需要大量图片素材的项目提供本地批量调色与格式转换。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.5.0 安装包，未安装；笔记见 `projects/lightcraft/README.md`）

### 8.6 PdfCraft（对应 Acrobat）

- 项目名称：PdfCraft（storytold/pdfcraft）
- GitHub 原始地址：<https://github.com/storytold/pdfcraft>
- 项目用途：PDF 阅读、整理与保护，clean-room 重写 Acrobat。
- 推荐原因：替代 Acrobat 的需求面最广也最实用（合并、拆分、加密、签名），且这是全家桶里最容易直接替代的一类工具。
- 可以如何使用：日常 PDF 阅读与整理，如合并、拆分、加水印、加密；CLI 适合批处理。
- 与我现有项目可能的结合方式：文档类产出（如 AI 生成的报告）自动后处理：合并、加密、加水印。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.5.0 安装包，未安装；笔记见 `projects/pdfcraft/README.md`）

### 8.7 EffectCraft（对应 After Effects）

- 项目名称：EffectCraft（storytold/effectcraft）
- GitHub 原始地址：<https://github.com/storytold/effectcraft>
- 项目用途：动效设计与视觉特效，clean-room 重写 After Effects。
- 推荐原因：AE 的合成与特效引擎是最难复刻的模块，该项目 2026-10-01 建仓、10 天左右就上万 star，研究价值高。
- 可以如何使用：制作动效、转场与视觉特效；适合做短视频的包装与片头片尾。
- 与我现有项目可能的结合方式：为 AI 短视频成片增加动效包装层，配合分镜数据自动生成动画。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.7.0 安装包，未安装；笔记见 `projects/effectcraft/README.md`）

### 8.8 DesignCraft（对应 InDesign）

- 项目名称：DesignCraft（storytold/designcraft）
- GitHub 原始地址：<https://github.com/storytold/designcraft>
- 项目用途：页面版式与出版，clean-room 重写 InDesign。
- 推荐原因：排版是自动化链路上最容易被忽略的一环，它可让「内容 → 成稿」全流程摆脱 Adobe 订阅。
- 可以如何使用：做海报、画册、长文档排版与导出；CLI 可用于模板化批量生成。
- 与我现有项目可能的结合方式：把自动生成的内容（报告、图册）批量套版输出，形成可交付成品。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.5.0 安装包，未安装；笔记见 `projects/designcraft/README.md`）

### 8.9 WordCraft（对应 Microsoft Word）

- 项目名称：WordCraft（storytold/wordcraft）
- GitHub 原始地址：<https://github.com/storytold/wordcraft>
- 项目用途：文字处理与文档编辑，clean-room 重写 Microsoft Word。
- 推荐原因：证明这套 Rust 路线不只针对 Adobe，通用办公软件同样能重写。
- 可以如何使用：日常文档撰写与编辑；CLI 可做文档批量转换与处理。
- 与我现有项目可能的结合方式：为文档类自动化产出（总结、报告）提供本地渲染与编辑环节。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.4.0 安装包，未安装；笔记见 `projects/wordcraft/README.md`）

### 8.10 GridCraft（对应 Microsoft Excel）

- 项目名称：GridCraft（storytold/gridcraft）
- GitHub 原始地址：<https://github.com/storytold/gridcraft>
- 项目用途：电子表格与数据计算，clean-room 重写 Microsoft Excel。
- 推荐原因：安装包仅 19.4 MB，是全家桶里最轻的一个，适合快速验证这类 Rust 表格应用的实际体验。
- 可以如何使用：做数据表格、公式计算与整理；CLI 适合批量数据转换。
- 与我现有项目可能的结合方式：为数据整理类任务提供本地表格工具，替代对 Excel 的依赖。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.4.0 安装包，未安装；笔记见 `projects/gridcraft/README.md`）

### 8.11 DeckCraft（对应 Microsoft PowerPoint）

- 项目名称：DeckCraft（storytold/deckcraft）
- GitHub 原始地址：<https://github.com/storytold/deckcraft>
- 项目用途：演示文稿与幻灯片，clean-room 重写 Microsoft PowerPoint。
- 推荐原因：演示文稿是工作高频产出，开源替代品长期稀缺，这个方向值得跟踪。
- 可以如何使用：制作与编辑幻灯片；CLI 可用于模板化批量生成。
- 与我现有项目可能的结合方式：把自动生成的汇报内容直接排版成幻灯片成品。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.4.0 安装包，未安装；笔记见 `projects/deckcraft/README.md`）

### 8.12 CadCraft（对应 AutoCAD）

- 项目名称：CadCraft（storytold/cadcraft）
- GitHub 原始地址：<https://github.com/storytold/cadcraft>
- 项目用途：计算机辅助设计与制图，clean-room 重写 AutoCAD。
- 推荐原因：CAD 属于专业垂直领域，开源可用的替代品极少，这个项目的定位相当少见。
- 可以如何使用：二维制图与工程设计草图的绘制、查看与导出。
- 与我现有项目可能的结合方式：暂无直接结合点，先作为「专业软件开源化」的观察样本。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.4.0 安装包，未安装；笔记见 `projects/cadcraft/README.md`）

### 8.13 SoundCraft（对应 Avid Pro Tools）

- 项目名称：SoundCraft（storytold/soundcraft）
- GitHub 原始地址：<https://github.com/storytold/soundcraft>
- 项目用途：音频录制与编辑，clean-room 重写 Avid Pro Tools。
- 推荐原因：音频是和视频配套的必需环节，补齐了「视频 + 音频」的完整链路。
- 可以如何使用：录音、剪辑与音频修整；可配合视频项目做配音与配乐处理。
- 与我现有项目可能的结合方式：为短视频项目提供本地配音录制与音频处理。
- 推荐日期：2026-10-11
- 后续研究状态：待研究（本机已下载 v0.4.0 安装包，未安装；笔记见 `projects/soundcraft/README.md`）

> 家族通用说明：以上 12 个应用均为第三方开源项目（作者 ArtCraft / storytold），本仓库只记录项目索引与研究笔记，不复制其源码，保留原作者与原始 GitHub 地址。热度与体积数据为 2026-10-11 抓取快照。

---

## 专题目录

- [短视频](./短视频/README.md)：AI 短视频生产研究，重点关注「文案 → 分镜 → Shot List → 模型 Prompt → AI 视频 → 自动成片」的中转层与工作流。
