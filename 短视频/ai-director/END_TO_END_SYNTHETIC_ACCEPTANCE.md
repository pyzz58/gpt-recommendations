# 一整条短视频导演链的第一次纵向贯通（只用虚构模拟素材）

本项目此前分别建成文章拆集、创意导演、剧本编辑、审阅锁定、十阶段专业 DAG 与 AI 视频制作工作单导出。但**各个组件分别通过单测不等于它们能够串接运行**。这份纵向验收专门弥补这一缺口。

## 当前测试路径

```
虚构文章「纸灯实验 / 桌上的信」（公开的合成测试数据）
 → article_intake：一条单集，源文位置与 SHA256
 → editorial_storyboard：合成创意导演/剧本编辑响应
 → editorial_review_lock：合成结构化“review decisions”形成规划快照
 → agent_live_crew.run_one_locked_role：10 次独立的模拟 DeepSeek-format JSON
 → 按 DAG 执行 director_brief/script_edit/director_lock
                     acting、camera_art、sound
                     editing_animation/ai_technical/quality_review/director_final
 → agent_handoff_audit + agent_creative_review：独立一致性校验
 → production_delivery.build_locked_crew_delivery：真实制作包编译程序
 → JSON + Markdown：逐镜路线、时码、动作、摄影、配音、字幕、
                    Wan/Seedance 候选提示词、后期图表/音效与镜间编辑时间线
```

这里“执行岗位”的说法只指**运行合同校验与岗位交付流程**：岗位的“创意 JSON”全部是开发者预先写好的合成文本，没有一个岗位通过网络请求 DeepSeek；所以这不是 DeepSeek 创作样片，不证明任何创作质量。合成的“通过审核”也不是用户作过真正的审阅。所有输出永远 `human_approved=false`、`media_generated=false`、`publishing_allowed=false`。

## 运行与下载

GitHub 仓库的 `.github/workflows/ai-director-tests.yml` 现在运行：

```bash
python offline_vertical_demo.py --synthetic-only \
    --output-dir /tmp/ai-director-complete-synthetic-demo
```

CI 会把结果作为 GitHub Actions artifact 上传，名称：

`ai-director-SYNTHETIC-NOT-REAL-AI-operator-pack`

该制品保留 7 天；内含以下内容：

- `SYNTHETIC_DEMO_NOT_REAL_AI.md`：**直接读这个**。具体每镜的镜头目的、配音/动作、镜头运镜、灯光、相邻动作连续性、后期工单、AI 视频候选提示词等。内容来自**虚构合成专业回复**。
- `SYNTHETIC_DEMO_NOT_REAL_AI.json`：完整可机读工作包，后续做前端审片、展示、生成素材可复用。
- `SYNTHETIC_DEMO_EXECUTION_EVIDENCE.json`：每岗位模拟提交证明，阶段数、镜头数、时长、制作路线统计、独立 QA 结果和无实际模型调用证明。
- `README.txt`：明确声明合成数据和无授权。

**实际作者私人稿件与真实 DeepSeek 输出不得通过该 CI 通道运行，也不得上传任何公开 artifact。** 此 CLI 只允许 `--synthetic-only`，它内部使用代码仓库中虚构信封故事的测试 fixture，不接收任何 `--source` / `--api-key` / `--provider` 参数。

## 重点核查的三项假完成

1. 不能只看十个角色 `tasks` 都是 `completed`；必须真正调用 `production_delivery.build_locked_crew_delivery` 完整编译。如果存在遗漏字段、原文不符、镜头时码错误、QA 阻断，要停止，而不是假生成成功制作包。
2. 每个 `ai_video` 镜头应输出 Wan 与 Seedance 两个具体候选提示词；后期图卡/数据镜头**不能**假装有真人 AI 视频 prompt。所有镜头的原文旁白、duration、镜头顺序与锁定 v0.1 计划保持完全相同。
3. 如原稿在中途被篡改，必须阻止输出并重新走人工审核；文件输出永远标记为 **仅供人工复核，不具备真实模型/视频供应商放行权限**。

## 这次实际证明与尚未证明

已证明：人工编写的合成 role JSON，可以在真实已有的 10-role DAG、消息合同、来源/版本校验、跨部门 QA 和生产编译模块中形成可读逐镜工作包。出具的样例 Markdown 是**可见的具体交付**，不只是任务状态表。

未证明：当前 DeepSeek 模型产生的内容是否通过专业岗位合同、是否符合导演审美、某视频模型是否可以高成功率生成、人物连续性是否得到真实素材验证、观众是否愿意看、实际账单/速度等。完成这些只能在用户**独立明确授权**测试文案向供应商发送、单次费用预算及私有运行地点之后，用真实模型和真实视频试制取得证据。

## 下一次研发应该做什么？

先由作者打开本次公开合成制作包，确认这套交付结构是否覆盖自己最重视的“动作、动画、场景、台词、剪辑、导演审查”。随后在可信私有环境用授权的一段虚构稿真正做 1–2 岗位 DeepSeek 小样，量化专业细节、错误率及人工返工量。不要仅以继续增加 Agent/审核模块替代实机评测。
