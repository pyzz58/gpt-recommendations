# 专业导演第三阶段：实际制作路线与编译器契约（GitHub-only）

## 缺陷与修复（2026-10-11）

真实第三阶段任务报告了一个高优先级问题：`base.shots[].visual_type` 全部标为 `ai_video`，即使专业导演在 `generation.production_method` 里选了“静态图后期/剪辑合成/实拍插入”，原 v0.2 校验器也强制 `generation.route=ai_video`；原编译器只看 base.visual_type，给非视频镜头生成了 Wan / Seedance 候选提示词。结果是制作成本策略并未真正贯彻到生产包。

本次只在 GitHub 修改 `director_v2.py`、测试和开发文档，借鉴 [CineCrew](https://github.com/Ironieser/CineCrew) 的统一镜头约束、[AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline) 的分阶段资产/后期拆分。未合并第三方源码，也不依赖大型框架。

**修复：区分概念镜头类型和执行路线。** 一个 `base.visual_type=ai_video` 的镜头可以改用静态画面或后期；视频模型提示词只针对实际 `execution_route=ai_video` 的镜头生成。

## 规范制作路线

| 新导演文件 `generation.route` | 用途 | 编译输出 |
|---|---|---|
| `ai_video` | 确实需要 AI 视频生成 | Wan、Seedance 候选提示词（不会自动调用）；配音/字幕后期单 |
| `static_post` | 静态图、时间角标、关键帧照明效果 | 不生成视频模型提示词，输出后期工作单 |
| `edit_composite` | 多片段剪辑、合成、蒙太奇、遮挡连接 | 不生成视频模型提示词，输出后期工作单 |
| `live_action_insert` | 手部翻书等需要实拍的素材 | 不生成视频模型提示词，输出人工拍摄/剪辑工作单 |
| `post_production` | 既有文字卡、数据图表等原生非 AI 视频镜头 | 不生成视频模型提示词，保留原片尾/事实审查约束 |

推荐新档案写法（合成示例）：

```json
{
  "shot_id": "S05",
  "generation": {
    "route": "static_post",
    "clip_type": "still_with_time_overlay",
    "negative_constraints": [],
    "reference_roles": [],
    "limits": "准确时间数字和字幕必须后期叠加"
  }
}
```

上述片段只是 `generation` 的演示，并非完整 v0.2 导演档。

### 旧导演文件兼容

以前 `generation.route=ai_video`，而自定义 `production_method` 实际上写了“剪辑合成”“静态图+后期”“静态关键帧+后期灯光”“实拍插入”等时，新版会识别这些**已列在 `METHOD_ALIASES` 的受支持写法**，并在编译结果使用非 AI 路线。下次修订建议直接把 `generation.route` 更新成规范值，让 `route` 与 `production_method` 一致。

为了避免默默生成收费视频提示词，**不能识别的 `production_method`、非法路线或明确冲突的路线一律校验失败**。遇到不支持的写法应先登记并审查新别名，不使用模糊自动猜测。旧档案如完全没有 `production_method`，继续按旧行为编译。

### 输出核查

编译后的每个镜头都会出现 `execution_route`：

- `ai_video`：`prompts.wan / prompts.seedance` 仅候选。
- 其他四种方式：`prompts={}`，`postproduction_job` 包含 `production_route`、原画面、逐秒 `beats`、旁白、后期字幕、效果/音乐、参考资产、备用方案和成本备注。明确 `asset_status=not_verified`、`requires_operator_review=true`。
- 顶层 `production_summary` 包含 `routes` 汇总、`ai_video_jobs`、`non_video_jobs` 和 `media_created=false`，便于估算要付费生成的镜头数；**这不是实际价格，也不代表素材已制作**。

**严禁把只写在 `direction.sound.voiceover_note` 的简化旁白当成实际音轨。** 编译器仍保留 `base.shots[].narration` 作为唯一已选定旁白，`voiceover_source=base.narration` 与 `voiceover_note` 会同时出现在工作单。改变正式配音必须另行修改、审核对应 base 候选稿，保证字幕同步。

## 用户第三阶段报告的状态与限制

用户报告的第三阶段候选档包含 **13 镜、75 秒**，其中 6 镜 AI 视频、3 镜剪辑合成、2 镜静态后期、1 镜灯光静态后期、1 镜手部实拍。候选 `direction_v02.proposed.json` 和私人原始 `jobs/` 位于用户 Mac，不存在于公开 GitHub，因此**本次不能实际打开、解析或重编译这份真实文件**，也不能证明其 `production_method` 与以上别名完全一致。该真实试验已由用户侧 Codex 报告通过，但这份源码修复的验证只基于仓库公开示例和合成回归。

直到用户明确同意本地部署，**不得让用户同步代码、运行 Codex、安装依赖、上传私人分镜、调用付费模型或生成实际视频。** 本轮仅公开源码与合成离线测试。

## 验收判据

- 原有 v0.2 示例和片尾引用卡规则不发生回归。
- 旧格式只要没有 `production_method` 就按原逻辑运行。
- 规范非视频路线以及已支持旧别名会输出后期工作单，无视频模型 prompts。
- 未识别路线、冲突路线、付费执行关键词必须显式报错。
- 完整编译必须标识 `not_generated_video=true`、`publishing_allowed=false`。
- 全程不执行模型推理、不修改计算机或发布作品。实际可生成性和人物参考图一致性需要将来专项验证。
