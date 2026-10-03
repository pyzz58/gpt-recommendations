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
