# AI 短视频导演 v0.3 · 中国回国可携带的本地优先版本

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
python3 local_director.py run --input article.md --out jobs/my-video-new --approve-model-cost
open jobs/my-video-new/index.html
```

- 默认提供 **DeepSeek 官方兼容API** 端点 `https://api.deepseek.com/v1` 与示例模型ID `deepseek-flash`；若供应商日后调整，指定 `--model` 或 `AI_MODEL`。请先检查自己的账号对应实际模型。
- **会发生模型费用**：按每阶段 1 次调用，1集至少3次（系列策划+每集基础计划+专业导演稿）；3集通常7次，失败不会自动重试。费用由供应商和Token用量决定，程序目前不会显示实时费用或价格上限。谨慎授权。
- 若中途失败，已成功生成的 `series.json`、`plan.json` 会保留。修订草稿后可 `--resume` 续跑；API生成不保证每次一键直接通过质量校验。拒绝把不合格作品伪装成成功。
- 使用别的国内服务：需其兼容 Chat Completions + JSON对象输出；显式设置 `AI_API_BASE_URL` 和 `AI_MODEL`，事先检查收费与服务条款。支持 `http://127.0.0.1:端口/v1` 作为未来本地模型接口（未做实际兼容性测试）。

## 本地自检与备份

```bash
python3 local_director.py doctor
python3 -m unittest discover -s tests -v
python3 local_director.py backup --project . --out ../ai-director-backup.zip
```

ZIP 可以保存在 Mac、移动硬盘和其他存储位置。不要只保存在GitHub。备份程序排除 `.env`，但文章、人物素材和其他工作文件可能含隐私，请自行妥善保管。

## 功能边界

已实现：逐阶段API调度、Codex任务单、1–3集系列规划数据约束、系列角色Bible、证据状态保守处理、逐镜头v0.1/v0.2结构校验、5秒来源卡规则、本地HTML预览、WAN/Seedance候选提示词、本地ZIP备份与阶段状态保存。

尚未实现：真实的人物多角度参考图片、参考图自动绑定到视频模型、已生成影像的验收和智能重拍、跨镜局部智能重写UI、音频播放的MP4节奏预演、真正的视频生成、数字动画渲染、字幕/配乐合成、模型费用估算、人工一键网页操作。**这次自动化API路径未使用真实模型凭据实测；目前通过的是离线单元测试和模拟LLM调用。**

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
