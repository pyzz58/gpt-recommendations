# 导演到 AI 视频制作：逐镜生产工单导出（离线）

**当前状态：可用的“人工复核版制作包”导出器，不是自动生成成片。**

入口 `production_delivery.py` 是这套导演系统中第一个专门将已有 v0.2 专业导演方案整理成**逐镜视频提示词、后期图形/文字制作单、配音声音时间提示、转场与镜间交接**的交付层。复用现有 `director_v2.compile_package`、`director_workbook.compile_workbook` 与专业审核，不新建重复的 10 名导演，也不制造缺失的镜头方案。

## 具体能得到什么

对于正式导演方案中的每一个镜头，它输出：

1. 镜头编号和精确起止时码、画幅及镜头目标；
2. 原文旁白、字幕，完全不自动改写已经锁定的句子；
3. 动作表演、走位节拍、摄影机移动、灯光、场景和连续性说明；
4. 如果该镜的 `execution_route = ai_video`，给出 **Wan 和 Seedance 两份候选视频提示词**。这些来源于已有专业部门的动作、摄影及技术导演成果，而不是导出器现场用套话生成；
5. 如果镜头是数据信息图、字幕卡、动画合成或其他后期路线，**不会伪造 AI 视频模型的提示词**，直接生成待执行的后期工作单；
6. 配音、音效、音乐、准确图表和字幕单独留给后期，禁止让视频模型负责准确生成中文文字、统计数字和可追溯医学引用；
7. 全片剪辑工作台时间线、镜间叙事/动作/色彩交接、需要的参考人物道具资产、独立人工验收检查表；
8. 视频模型功能兼容、素材参考图、事实核验、媒体版权及人工批准均标记待办，不自动放行付费任务。

交付物为结构化 JSON 和一份可打开阅读的 Markdown；两者都可能包含完整私人文案和导演创意，**不得上传到公共仓库、日志或公开存储**。

## 两种严格区分的输入模式

**模式 A：项目既有专业参考方案，用于研发演示。**

`build_reference_delivery(base, direction)` 从仓库既有的专业 v0.2 导演设计导出工作单。**不声称已经运行过十个独立模型 Agent，也不意味着操作者已审核。**

GitHub Actions 本轮实际以原仓库里已存在的 `examples/quit-smoking/plan.json` + `direction_v02.json`（公开参考）执行：

```bash
python production_delivery.py \
  --base examples/quit-smoking/plan.json \
  --direction examples/quit-smoking/direction_v02.json \
  --out-json /tmp/ai-director-operator-work-orders.json \
  --out-md /tmp/ai-director-operator-work-orders.md
```

它确实生成 **8 镜头**的机器可读和 Markdown 生产工单（其中哪些使用 AI 视频由 v0.2 专业设计决定），工作流在临时目录存放，仅作为代码自动验收；**本次没有运行 DeepSeek，也没有生成任何 MP4**。此命令只是 CI 文档，不要求用户现在在 Mac 上执行或同步。

**模式 B：来自上一轮“逐镜审阅/规划锁定”的团队成果。**

`build_locked_crew_delivery(snapshot, episode_source, final_team_state)` 要求：

- `editorial_review_lock.lock_planning_snapshot` 产生的规划锁定快照，里面的原文和计划 hash 要再次对得上；
- 完整的十阶段专业团队实际填满 `team_state`，其中总导演、剧本编辑、动作表演、摄影美术、声音、剪辑动画、AI 技术、独立 QA 与终审均已交付，任务版本正确；
- `agent_team.compile_team_workbook` 重新独立审查 QA/跨部门阻断问题并合并 v0.2 计划；
- 如果导演团队未完成、用错锁定版本、替换源文、跳过 QA 或方向内容不合法，则**报错、停止，不产出伪装为十岗位完成的制作包**。

正式身份认证、私人源文传输授权、用户人工审批仍未接入。即使本函数验证通过，它也只证明数据结构和交接环节完备，而不是用户真正同意调用模型或已经有人看过视频。

## 状态必须如实区分

| 名称 | 含义 |
| --- | --- |
| `existing_v02_reference_not_agent_run` | 仓库里既有的示范专业 v0.2，非本次十 Agent 运行 |
| `locked_ten_role_crew` | 有完整来源和版本绑定的十阶段团队交接 |
| `offline_operator_review_workbook_not_model_ready` | 输出了人工可读的生产工单，但不具备自动调用/上传的批准 |
| `ready_to_call_video_model=false` | 缺真人审批、素材、真实供应商能力验证，不许自动 dispatch |
| `human_approved=false` / `publishing_allowed=false` | 不冒充真实用户签名、授权或影片发布 |
| `external_model_calls=0` / `actual_video_generated=false` | 仅离线编译工作单，没有花钱或渲染视频 |

## 何时真正完成？

目前已将“结构完整的 v0.2 专业导演工作”整理成可以人工复制、转交制作人员的 AI 视频**候选**提示词和后期工作清单。距离用户设想的“一篇文案就自动得到能直接给 AI 视频制作的成熟导演方案”，仍差实际 DeepSeek 生成专业角色内容、可信作者审阅、实际素材资产管理、视频模型小样反馈与针对模型能力的专业迭代。**再多离线测试也不能取代上述实机验证。**

公开仓库代码绝不保存用户上传的真实《上学以后的孩子》。下一步真实调用须独立取得用户同意，明确模型服务商、实际测试文案、是否允许跨服务传输、单次人民币成本上限、失败处理和运行所在的可信私人位置。
